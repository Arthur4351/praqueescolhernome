import os
import sys
import uuid
import re
import shutil
import requests
import subprocess
from pathlib import Path

class DynamicCoder:
    """Motor de Self-Coding para geração e execução de scripts dinâmicos."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.skills_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "dynamic_skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.modelo_codigo = "llama-3.3-70b-versatile"
        config_path = Path(os.path.dirname(os.path.dirname(__file__))) / "config.json"
        if config_path.exists():
            try:
                import json as _json
                self.modelo_codigo = _json.loads(config_path.read_text(encoding="utf-8")).get("modelo_codigo", self.modelo_codigo)
            except:
                pass
        from core.ai_router import AIRouter
        self._router = AIRouter(str(config_path))
        
    def edit_project_file(self, target_file_path: str, instruction: str) -> str:
        """Edita um arquivo real do projeto com base em uma instrução em linguagem natural.
        Cria backup .bak, aplica a mudança, valida sintaxe, faz rollback se falhar."""
        if not self.api_key:
            return "\u274c Erro: GROQ_API_KEY n\u00e3o configurada."

        target = Path(target_file_path)
        if not target.exists():
            project_root = Path(os.path.dirname(os.path.dirname(__file__)))
            candidates = list(project_root.rglob(target_file_path))
            if candidates:
                target = candidates[0]
            else:
                return f"\u274c Arquivo '{target_file_path}' n\u00e3o encontrado no projeto."

        try:
            original_code = target.read_text(encoding="utf-8")
        except Exception as e:
            return f"\u274c N\u00e3o consegui ler '{target.name}': {e}"

        backup_path = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup_path)

        system_prompt = (
            "Voc\u00ea \u00e9 um Engenheiro S\u00eanior Python. Receber\u00e1 o c\u00f3digo atual de um arquivo e uma instru\u00e7\u00e3o de edi\u00e7\u00e3o.\n"
            "REGRAS CR\u00cdTICAS:\n"
            "1. Retorne APENAS o arquivo COMPLETO modificado. Sem markdown, sem ```, sem explica\u00e7\u00f5es.\n"
            "2. Preserve TODA a l\u00f3gica existente. S\u00f3 adicione/modifique o que a instru\u00e7\u00e3o pede.\n"
            "3. Mantenha encoding UTF-8, indenta\u00e7\u00e3o e estilo do c\u00f3digo original.\n"
            "4. Se a instru\u00e7\u00e3o pedir uma nova fun\u00e7\u00e3o, adicione-a ao final da classe ou do m\u00f3dulo."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Arquivo atual ({target.name}):\n{original_code}\n\nInstrucao: {instruction}"}
        ]

        try:
            new_code, _ = self._router.call_code(messages, max_tokens=4000)
            match = re.search(r'```(?:python)?(.*?)```', new_code, re.IGNORECASE | re.DOTALL)
            if match:
                new_code = match.group(1).strip()
            else:
                new_code = new_code.strip()
        except Exception as e:
            backup_path.unlink(missing_ok=True)
            return f"\u274c IA n\u00e3o respondeu: {e}"

        target.write_text(new_code, encoding="utf-8")

        syntax_check = subprocess.run(
            [sys.executable, "-m", "py_compile", str(target)],
            capture_output=True, text=True
        )
        if syntax_check.returncode != 0:
            shutil.copy2(backup_path, target)
            backup_path.unlink(missing_ok=True)
            return f"\u274c Erro de sintaxe no c\u00f3digo gerado. Arquivo restaurado.\nDetalhe: {syntax_check.stderr.strip()}"

        backup_path.unlink(missing_ok=True)
        return f"\u2705 '{target.name}' editado com sucesso. Backup descartado."

    def generate_and_run(self, task_prompt: str, context_args: dict = None) -> str:
        if not self.api_key:
            return "❌ Erro: GROQ_API_KEY não configurada para o DynamicCoder."

        # 1. Gerar Código via LLM
        script_code = self._generate_script(task_prompt, context_args)

        if not script_code:
            return "❌ Erro: Falha ao gerar o código dinâmico."
            
        # 2. Salvar em Arquivo
        script_name = f"skill_{uuid.uuid4().hex[:8]}.py"
        script_path = self.skills_dir / script_name
        
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_code)
                
            # 3. Executar o Script Isoladamente
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=120 # Limite de 120 segundos (2 minutos)
            )
            
            output = result.stdout.strip()
            errors = result.stderr.strip()
            
            relatorio = f"⚙️ **Script Executado ({script_name})**\n"
            if output:
                relatorio += f"**Output:**\n{output}\n"
            if errors:
                relatorio += f"**Avisos/Erros:**\n{errors}\n"
                
            if result.returncode == 0:
                return relatorio + "✅ Tarefa Dinâmica concluída com sucesso."
            else:
                return relatorio + "❌ O script dinâmico falhou durante a execução."
                
        except subprocess.TimeoutExpired:
            return "❌ Erro: Timeout. O script dinâmico demorou mais de 60 segundos e foi abortado."
        except Exception as e:
            return f"❌ Erro Crítico na execução do script: {e}"
        finally:
            # Ordem Direta: Apagar o arquivo .py após o uso
            if script_path.exists():
                try: script_path.unlink()
                except: pass

    def _generate_script(self, task_prompt: str, context_args: dict) -> str:
        """Envia o prompt para a Groq e extrai APENAS o código Python."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        args_str = str(context_args) if context_args else "{}"
        
        system_prompt = (
            "Você é um Engenheiro de Software Sênior especializado em automação Python. "
            "Sua tarefa é escrever um script Python (.py) perfeitamente funcional que cumpra a solicitação do usuário.\n\n"
            "Regras CRÍTICAS:\n"
            "1. Responda APENAS com código Python. Sem markdown, sem explicações, sem ```python. O texto será salvo diretamente em um .py e rodado.\n"
            "2. Bibliotecas permitidas: os, sys, shutil, pathlib, re, json, openpyxl, pandas, pyautogui, requests, time, difflib.\n"
            "3. O código deve conter tratamento de exceções (try/except) e printar os resultados ou erros para o STDOUT.\n"
            "4. Não use inputs do usuário no código (`input()`), pois o script rodará em background.\n"
            f"5. Se precisar de contexto, os argumentos conhecidos no momento são: {args_str}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Escreva um script para: {task_prompt}"}
        ]

        try:
            content, _ = self._router.call_code(messages, max_tokens=2000)
            match = re.search(r'```(?:python)?(.*?)```', content, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
            else:
                content = content.strip()
            return content
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as err_log:
                err_log.write(f"DynamicCoder: Erro no AIRouter: {str(e)}\n")
            return ""
