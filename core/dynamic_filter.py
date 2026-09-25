import ast

# Nós de AST permitidos numa expressão de filtro. Qualquer coisa fora desta
# lista (acesso a atributo, indexação, lambda, compreensões, etc.) faz a
# expressão ser REJEITADA antes de compilar -> nunca chega ao eval.
# Isso fecha o clássico escape de sandbox `().__class__.__bases__[0]...`,
# porque os nós `Attribute` e `Subscript` simplesmente não são permitidos:
# sem acesso a atributo não há como sair dos metadados para os builtins reais.
_ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp, ast.And, ast.Or,
    ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.FloorDiv,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn,
    ast.Call,            # somente funções da whitelist ou métodos seguros (validado abaixo)
    ast.Name, ast.Load,
    ast.Attribute,       # somente métodos seguros de string/número (validado abaixo)
    ast.Constant,
    ast.List, ast.Tuple, # para "int(dia) in [1, 2, 3]"
)

# Únicas funções que uma expressão de filtro pode chamar.
_ALLOWED_FUNCS = {"int", "float", "str", "len", "abs", "bool"}

# Únicos métodos (acesso a atributo) permitidos — só operações de texto/número
# puras e não reflexivas. NADA de format/format_map/encode nem dunders, para
# não reabrir escapes do tipo "{0.__class__}".format(x).
_ALLOWED_METHODS = {
    "lower", "upper", "strip", "lstrip", "rstrip", "casefold", "title", "capitalize",
    "startswith", "endswith", "find", "rfind", "count", "replace", "zfill",
    "split", "rsplit", "isdigit", "isalpha", "isalnum", "isspace",
}


class DynamicFilter:
    def __init__(self, expression_str: str = None):
        self.expression_str = expression_str.strip() if expression_str else "True"
        self.code_obj = None
        try:
            tree = ast.parse(self.expression_str, "<dynamic_filter>", mode="eval")
            if self._is_safe(tree):
                # Só compila (e portanto só poderá ser avaliada) uma expressão
                # que passou pela allowlist de AST acima.
                self.code_obj = compile(tree, "<dynamic_filter>", "eval")
        except Exception:
            # Sintaxe inválida OU expressão insegura -> fallback "True" (não filtra).
            self.code_obj = None

    @staticmethod
    def _is_safe(tree) -> bool:
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_NODES):
                return False
            # Acesso a atributo: só métodos seguros da allowlist, nunca dunder.
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("__") or node.attr not in _ALLOWED_METHODS:
                    return False
            # Chamadas: nome simples da whitelist OU método já validado acima.
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    if func.id not in _ALLOWED_FUNCS:
                        return False
                elif not isinstance(func, ast.Attribute):
                    return False
                if node.keywords:
                    return False
            # Defesa extra: bloqueia qualquer identificador dunder.
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                return False
        return True

    def evaluate(self, metadata: dict) -> bool:
        """
        Avalia a expressão de filtro usando os metadados do arquivo como namespace.
        Metadata contém chaves como: dia, hora, camera, equipe, nome, tamanho_bytes.
        A expressão já foi validada por uma allowlist de AST no __init__, portanto
        não consegue acessar atributos, indexar objetos nem alcançar builtins.
        """
        if self.code_obj is None:
            return True
        safe_globals = {
            "__builtins__": {},
            "int": int,
            "float": float,
            "str": str,
            "len": len,
            "abs": abs,
            "bool": bool,
        }
        # Injeta variáveis de metadados no contexto local (evita None).
        local_vars = {k: (v if v is not None else "") for k, v in metadata.items()}
        try:
            return bool(eval(self.code_obj, safe_globals, local_vars))
        except Exception:
            # Erro de tipo/avaliação -> não filtra (assume True), sem quebrar o fluxo.
            return True
