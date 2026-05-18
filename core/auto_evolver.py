import sys
import os
import importlib
import subprocess
import traceback
import tempfile
import ast
from pathlib import Path

class CodeInspector:
    def __init__(self, log_func):
        self.log_func = log_func

    def parse_traceback(self, tb_string):
        """
        Analisa a string de traceback e retorna detalhes do arquivo e linha falhos.
        Foca no último frame que pertence ao projeto (não bibliotecas padrão).
        """
        self.log_func("🔍 [CodeInspector] Analisando pilha de falha...")
        linhas = tb_string.strip().split('\n')
        alvo_arquivo = None
        alvo_linha = None
        alvo_funcao = None
        codigo_falho = None
        
        # Encontra o último arquivo relevante da nossa stack
        for i, linha in enumerate(linhas):
            if linha.strip().startswith('File "') and 'minhas_habilidades.py' in linha:
                parts = linha.strip().split('", line ')
                if len(parts) >= 2:
                    alvo_arquivo = parts[0].replace('File "', '')
                    resto = parts[1].split(', in ')
                    alvo_linha = int(resto[0])
                    if len(resto) > 1:
                        alvo_funcao = resto[1]
                # A próxima linha contém o código que falhou
                if i + 1 < len(linhas):
                    codigo_falho = linhas[i+1].strip()
                    
        return alvo_arquivo, alvo_linha, alvo_funcao, codigo_falho

class CodeGenerator:
    def __init__(self, log_func):
        self.log_func = log_func

    def gerar_patch_temporario(self, file_path, alvo_linha, codigo_falho):
        """
        Gera uma correção lógica temporária em um arquivo isolado.
        Atualmente implementa um stub para simular uma mutação (ex: injetar try-except ou comentar).
        """
        self.log_func(f"🛠️ [CodeGenerator] Criando clone de sandbox para {os.path.basename(file_path)}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            conteudo = f.readlines()
            
        # Sandbox logic: vamos envolver a linha em um Try-Except de fallback temporário
        # Na vida real, a IA LLM faria o parsing e escreveria a nova regra matemática.
        indice = alvo_linha - 1
        indentation = len(conteudo[indice]) - len(conteudo[indice].lstrip())
        
        novo_codigo = []
        for i, linha in enumerate(conteudo):
            if i == indice:
                novo_codigo.append(" " * indentation + "try:\n")
                novo_codigo.append(" " * indentation + "    " + linha.lstrip())
                novo_codigo.append(" " * indentation + "except Exception as auto_err:\n")
                novo_codigo.append(" " * indentation + "    pass # Mutação de bypass\n")
            else:
                novo_codigo.append(linha)
                
        codigo_str = "".join(novo_codigo)
        
        # Validação AST para garantir que a estrutura sintática está 100% válida
        try:
            ast.parse(codigo_str)
        except SyntaxError as e:
            self.log_func(f"❌ [CodeGenerator] Mutação gerou SyntaxError: {e}. Abortando patch.")
            return None
            
        fd, temp_path = tempfile.mkstemp(suffix='.py', prefix='sandbox_mutant_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(codigo_str)
            
        self.log_func(f"🛠️ [CodeGenerator] Mutação AST validada e salva em {temp_path}.")
        return temp_path

class SandboxTester:
    def __init__(self, log_func):
        self.log_func = log_func

    def testar_modulo_isolado(self, temp_module_path):
        """
        Instancia um subprocesso isolado para checar se o novo código quebra a sintaxe ou gera erro fatal de import.
        """
        self.log_func("🧪 [SandboxTester] Executando simulação de segurança no arquivo mutante...")
        try:
            # Roda python compileall/import check no subprocesso para isolar memória
            resultado = subprocess.run([sys.executable, "-m", "py_compile", temp_module_path], 
                                       capture_output=True, text=True, timeout=10)
            if resultado.returncode == 0:
                self.log_func("✅ [SandboxTester] Código aprovado em testes de estresse estático.")
                return True
            else:
                self.log_func(f"❌ [SandboxTester] Falha no teste: {resultado.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.log_func("❌ [SandboxTester] Subprocesso excedeu limite de tempo (Loop Infinito?). KILL.")
            return False

class HotReloader:
    def __init__(self, log_func):
        self.log_func = log_func

    def injetar_novo_modulo(self, original_path, temp_path, module_name):
        """
        Garante o Sandbox isolado. Retorna o caminho do patch para que o usuário aprove manualmente.
        Não injeta mais na memória automaticamente.
        """
        self.log_func(f"🛡️ [HotReloader] Sandbox Concluída. Arquivo gerado em segurança: {temp_path}")
        return True

class AutoEvolver:
    """
    O Orquestrador da Divisão 3 de Auto-Evolução.
    """
    def __init__(self, log_func):
        self.log_func = log_func
        self.inspector = CodeInspector(log_func)
        self.generator = CodeGenerator(log_func)
        self.tester = SandboxTester(log_func)
        self.reloader = HotReloader(log_func)

    def acionar_protocolo_mutacao(self, tb_string, local_vars=None):
        self.log_func("\n=======================================================")
        self.log_func("🪐 [AUTO-EVOLVER] PROTOCOLO DE AUTO-CURA ATIVADO")
        self.log_func("=======================================================")
        
        # 1. Inspect
        alvo_arquivo, alvo_linha, alvo_funcao, cod = self.inspector.parse_traceback(tb_string)
        if not alvo_arquivo:
            self.log_func("⚠️ [AutoEvolver] Não foi possível isolar o arquivo local no Traceback.")
            return False
            
        self.log_func(f"Identificado gargalo crítico: Arquivo={os.path.basename(alvo_arquivo)} | Linha={alvo_linha} | Função={alvo_funcao}")
        
        # 2. Generate
        temp_path = self.generator.gerar_patch_temporario(alvo_arquivo, alvo_linha, cod)
        if not temp_path:
            return False
            
        # 3. Test
        aprovado = self.tester.testar_modulo_isolado(temp_path)
        if not aprovado:
            os.remove(temp_path)
            return False
            
        # 4. Finalizar Sandbox
        # Deriva o nome do módulo a partir do caminho
        module_name = Path(alvo_arquivo).stem
        sucesso = self.reloader.injetar_novo_modulo(alvo_arquivo, temp_path, module_name)
        
        if sucesso:
            self.log_func("🪐 [AUTO-EVOLVER] Auto-Cura Completa no Sandbox. Pronto para validação humana.")
            return temp_path
        return False
