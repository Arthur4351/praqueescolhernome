import sys

class DynamicFilter:
    def __init__(self, expression_str: str = None):
        self.expression_str = expression_str.strip() if expression_str else "True"
        try:
            # Compila a expressão uma vez para validação sintática e performance
            self.code_obj = compile(self.expression_str, "<dynamic_filter>", "eval")
        except Exception:
            # Em caso de erro sintático ou de compilação, invalida o código compilado (assume True como fallback)
            self.code_obj = None

    def evaluate(self, metadata: dict) -> bool:
        """
        Avalia a expressão dinâmica usando os metadados do arquivo como namespace.
        Metadata contém chaves como: dia, hora, camera, equipe, nome, tamanho_bytes.
        """
        if self.code_obj is None:
            return True
        # Escopo seguro com funções built-in permitidas
        safe_globals = {
            "__builtins__": None,
            "int": int,
            "float": float,
            "str": str,
            "len": len,
            "abs": abs,
            "bool": bool
        }
        # Injeta variáveis de metadados no contexto local (evita None)
        local_vars = {k: (v if v is not None else "") for k, v in metadata.items()}
        try:
            return eval(self.code_obj, safe_globals, local_vars)
        except Exception as e:
            # Em caso de erro de tipo ou avaliação, assume True ou loga silenciosamente
            return True
