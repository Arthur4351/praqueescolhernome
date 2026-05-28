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
        
    def _clean_code(self, content: str) -> str:
        """Limpa o código gerado removendo blocos de markdown de forma robusta."""
        # Se contiver ``` e fechar com ```
        match = re.search(r'```(?:python)?(.*?)```', content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip('\r\n')
            
        # Caso tenha sido truncado e tenha apenas a abertura de bloco
        if content.strip().startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            content = "\n".join(lines)
            
        # Caso termine com ``` sem abertura (ocorre em continuação às vezes)
        if content.strip().endswith("```"):
            lines = content.splitlines()
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
            
        return content.strip('\r\n')

    def edit_project_file(self, target_file_path: str, instruction: str) -> str:
        """Edita um arquivo real do projeto com base em uma instrução em linguagem natural.
        Cria backup .bak, aplica a mudança, valida sintaxe, faz rollback se falhar."""
        if not self.api_key:
            return "❌ Erro: GROQ_API_KEY não configurada."

        target = Path(target_file_path)
        if not target.exists():
            project_root = Path(os.path.dirname(os.path.dirname(__file__)))
            candidates = list(project_root.rglob(target_file_path))
            if candidates:
                target = candidates[0]
            else:
                return f"❌ Arquivo '{target_file_path}' não encontrado no projeto."

        try:
            original_code = target.read_text(encoding="utf-8")
        except Exception as e:
            return f"❌ Não consegui ler '{target.name}': {e}"

        backup_path = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup_path)

        system_prompt = (
            "Você é um Engenheiro Sênior Python. Receberá o código atual de um arquivo e uma instrução de edição.\n"
            "REGRAS CRÍTICAS:\n"
            "1. Retorne APENAS o código Python completo modificado do arquivo. É terminantemente proibido incluir qualquer tipo de introdução, explicação, comentários verbosos ou conclusão (nada de markdown, nada de ```, nada de explicações verbais). Comece a sua resposta diretamente com a primeira linha de código Python. Qualquer caractere que não seja código Python causará falha de compilação. Foque 100% no código Python.\n"
            "2. Preserve TODA a lógica existente. Só adicione/modifique o que a instrução pede.\n"
            "3. Mantenha encoding UTF-8, indentação e estilo do código original.\n"
            "4. Se a instrução pedir uma nova função, adicione-a ao final da classe ou do módulo.\n"
            "5. Siga rigorosamente as diretivas de Clean Code Python (@python-clean-naming, @python-clean-dry, @python-clean-solid, @python-clean-exceptions, @python-clean-functions)."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Arquivo atual ({target.name}):\n{original_code}\n\nInstrucao: {instruction}"}
        ]

        try:
            new_code, _ = self._router.call_code(messages, max_tokens=3000)
            
            # Loop de continuação caso a resposta tenha sido truncada
            attempts = 0
            while getattr(self._router, "last_was_truncated", False) and attempts < 3:
                attempts += 1
                continuation_messages = messages.copy()
                continuation_messages.append({"role": "assistant", "content": new_code})
                continuation_messages.append({
                    "role": "user",
                    "content": (
                        "O seu código anterior foi cortado/truncado no meio devido ao limite de tokens. "
                        "Por favor, continue a escrever o código Python exatamente a partir do caractere onde parou. "
                        "Retorne APENAS o código Python restante (sem repetir a parte inicial que já foi gerada e sem explicações/markdown)."
                    )
                })
                next_part, _ = self._router.call_code(continuation_messages, max_tokens=3000)
                if next_part:
                    new_code = self._clean_code(new_code) + "\n" + self._clean_code(next_part)
                else:
                    break
                    
            new_code = self._clean_code(new_code)
        except Exception as e:
            backup_path.unlink(missing_ok=True)
            return f"❌ IA não respondeu: {e}"

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
            relatorio += f"**Código Fonte Gerado:**\n```python\n{script_code}\n```\n\n"
            if output:
                relatorio += f"**Output:**\n{output}\n"
            if errors:
                relatorio += f"**Avisos/Erros:**\n{errors}\n"
                
            if result.returncode == 0:
                return relatorio + "✅ Tarefa Dinâmica concluída com sucesso."
            else:
                return relatorio + "❌ O script dinâmico falhou durante a execução."
                
        except subprocess.TimeoutExpired:
            return f"**Código Fonte Gerado:**\n```python\n{script_code}\n```\n\n❌ Erro: Timeout. O script dinâmico demorou mais de 120 segundos e foi abortado."
        except Exception as e:
            return f"**Código Fonte Gerado:**\n```python\n{script_code}\n```\n\n❌ Erro Crítico na execução do script: {e}"
        finally:
            # Ordem Direta: Apagar o arquivo .py após o uso
            if script_path.exists():
                try: script_path.unlink()
                except: pass

    def _load_skills(self, task_prompt: str) -> str:
        """Carrega o conteúdo das habilidades (skills) e injeta diretrizes reais de desenvolvimento no prompt."""
        skills_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "skills"
        if not skills_dir.exists():
            skills_dir = Path.home() / "OneDrive" / "Documents" / "Obsidian Vault" / "_agent" / "skills"
            
        if not skills_dir.exists():
            return ""
            
        skills_to_load = [
            "python-clean-naming", "python-clean-dry", "python-clean-solid", 
            "python-clean-exceptions", "python-clean-functions"
        ]
        
        prompt_lower = task_prompt.lower()
        if any(w in prompt_lower for w in ["bat", "batch", "cmd", "terminal", "lote", "shell"]):
            skills_to_load.extend([
                "batch-windows-syntax", "batch-flow-control", "batch-file-handler", 
                "batch-error-redirect", "batch-python-runner"
            ])
        if any(w in prompt_lower for w in ["excel", "planilha", "sheet", "macro", "vba"]):
            skills_to_load.append("excel-clean-design")
            
        matched_content = []
        for s_name in skills_to_load:
            file_candidates = [
                skills_dir / s_name / f"@{s_name}.md",
                skills_dir / s_name / "SKILL.md",
                skills_dir / f"@{s_name}.md"
            ]
            for file_path in file_candidates:
                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        clean_content = re.sub(r'^---.*?---', '', content, flags=re.DOTALL).strip()
                        matched_content.append(f"### Habilidade {s_name}:\n{clean_content}\n")
                        break
                    except:
                        pass
        if matched_content:
            return "\nDIRETRIZES DE DESENVOLVIMENTO ATIVADAS A PARTIR DA REDE DE SKILLS:\n" + "\n".join(matched_content) + "\n"
        return ""

    def _generate_script(self, task_prompt: str, context_args: dict) -> str:
        """Envia o prompt para a Groq e extrai APENAS o código Python."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        args_str = str(context_args) if context_args else "{}"
        skills_context = self._load_skills(task_prompt)
        
        system_prompt = (
            "Você é um Engenheiro de Software Sênior especializado em automação Python. "
            "Sua tarefa é escrever um script Python (.py) perfeitamente funcional que cumpra a solicitação do usuário.\n\n"
            "Regras CRÍTICAS:\n"
            "1. Responda APENAS com o código Python puramente funcional. É terminantemente proibido incluir qualquer tipo de introdução, explicação, comentários verbosos ou conclusão (absolutamente nada de 'Aqui está o seu código', 'Espero ter ajudado', etc.). Comece a sua resposta diretamente com a primeira linha de código real (ex: imports ou comentário curto de cabeçalho). O texto de sua resposta será salvo e executado diretamente como um script .py, portanto, qualquer caractere não-Python causará erro de execução. Foque 100% no código Python. Economize todos os tokens possíveis para evitar truncamento do código.\n"
            "2. Bibliotecas permitidas: os, sys, shutil, pathlib, re, json, openpyxl, pandas, pyautogui, requests, time, difflib, subprocess, win32com, win32com.client.\n"
            "3. O código deve conter tratamento de exceções (try/except) e printar os resultados ou erros para o STDOUT.\n"
            "4. Não use inputs do usuário no código (`input()`), pois o script rodará em background.\n"
            f"5. Se precisar de contexto, os argumentos conhecidos no momento são: {args_str}\n"
            "   Regra de ouro para chaves de dicionário: Use EXCLUSIVAMENTE as chaves que existem no contexto acima (ex: 'excel_path', 'target_path', etc.). NÃO invente ou assuma chaves como 'caminho_planilha' ou 'caminho_pasta' se elas não estiverem explicitamente listadas no dicionário de contexto. Se o script precisar de um arquivo Excel (.xlsx/.xlsm) ou pasta e esta chave não estiver no contexto, faça o script realizar uma busca automática no diretório atual de trabalho como fallback de segurança (ex: usar glob ou os.listdir para achar arquivos com extensão .xlsx ou .xlsm) invez de falhar com KeyError.\n"
            "   Regra de ouro para caminhos de arquivo: NUNCA use caminhos de diretório absolutos fixos/hardcoded no código (como 'D:\\teste - Copia' ou caminhos de usuários locais específicos do Windows como 'C:\\Users\\paulo\\...'). Todos os caminhos de arquivos e pastas devem ser relativos ao diretório atual de execução ('.') ou obtidos de forma totalmente dinâmica a partir das variáveis de contexto do dicionário fornecido. Se precisar salvar ou ler arquivos na Área de Trabalho (Desktop), Documentos (Documents) ou Downloads do usuário e o caminho não vier no contexto, resolva-os dinamicamente em Python usando a pasta home do usuário (ex: usar Path.home() / 'OneDrive' / 'Desktop' se existir, com fallback para Path.home() / 'Desktop'). Nunca assuma um nome de usuário fixo (como 'paulo' ou 'administrador'). Mesmo que o usuário forneça um caminho absoluto em seu prompt (como 'C:\\Users\\paulo\\OneDrive\\Desktop\\teeste\\planilha.xlsx'), converta-o programaticamente no código gerado para detecção dinâmica baseada em 'Path.home()' ou caminhos relativos para garantir portabilidade corporativa absoluta. NUNCA tente fazer split, parsing ou processamento de string no texto do prompt do usuário dentro do código Python gerado para descobrir caminhos de arquivos (evite splits frágeis como prompt.split('e salve-a em ')). Resolva os caminhos dinamicamente no momento da escrita do script escrevendo diretamente a lógica com Path.home() no script.\n"
            "   Idempotência na criação de diretórios: Sempre use 'os.makedirs(caminho, exist_ok=True)' ou 'Path(caminho).mkdir(parents=True, exist_ok=True)' ao criar pastas, de forma a não falhar caso a pasta já exista.\n"
            "   Para criação de macros, execução de VBA e automação de planilhas/Windows, prefira utilizar a biblioteca 'win32com.client' para despachar instâncias de aplicativos (ex: win32com.client.Dispatch('Excel.Application')) ou 'pyautogui'/'subprocess' para automatizar ações na GUI e no sistema operacional. Sempre que utilizar 'win32com.client' para interagir com o Excel, envolva TODA a lógica da aplicação em um bloco try/finally. No bloco finally, garanta a liberação dos objetos COM chamando 'excel.Quit()' (ou fechando a pasta de trabalho) para evitar o vazamento e acúmulo de processos 'excel.exe' órfãos em background no computador corporativo. IMPORTANTE: Ao abrir arquivos no Excel via interface COM (ex: 'excel.Workbooks.Open(...)'), você DEVE obrigatoriamente passar o caminho de arquivo convertido para absoluto usando 'os.path.abspath(caminho)' ou 'Path(caminho).resolve()'. O Excel executado em background via interface COM não compreende caminhos de arquivos relativos (como '.\\nome.xlsx') e irá falhar com erro de 'Não foi possível encontrar'.\n"
            f"{skills_context}\n"
            "6. Siga rigorosamente as diretrizes das habilidades ativas listadas acima."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Escreva um script para: {task_prompt}"}
        ]

        try:
            content, _ = self._router.call_code(messages, max_tokens=3000)
            
            # Loop de continuação caso a resposta tenha sido truncada
            attempts = 0
            while getattr(self._router, "last_was_truncated", False) and attempts < 3:
                attempts += 1
                continuation_messages = messages.copy()
                continuation_messages.append({"role": "assistant", "content": content})
                continuation_messages.append({
                    "role": "user",
                    "content": (
                        "O seu código anterior foi cortado/truncado no meio devido ao limite de tokens. "
                        "Por favor, continue a escrever o código Python exatamente a partir do caractere onde parou. "
                        "Retorne APENAS o código Python restante (sem repetir a parte inicial que já foi gerada e sem explicações/markdown)."
                    )
                })
                next_part, _ = self._router.call_code(continuation_messages, max_tokens=3000)
                if next_part:
                    content = self._clean_code(content) + "\n" + self._clean_code(next_part)
                else:
                    break
                    
            content = self._clean_code(content)
            return content
        except Exception as e:
            from core.file_handler import FileHandler
            FileHandler.log_error(f"DynamicCoder: Erro no AIRouter: {str(e)}")
            return ""
