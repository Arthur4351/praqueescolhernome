import re
import random
import unicodedata
import json
import os
import difflib
import gc
import requests
import time
import hashlib
import threading
from pathlib import Path
from core.file_handler import FileHandler

# Carrega variáveis de ambiente do .env uma única vez
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


class IntentParser:
    """Módulo NLP Híbrido com Inferência Heurística (Fuzzy Matching) e Memória de Contexto."""

    def __init__(self):
        self._intents_bow = None
        self._conversational_bow = None
        self.threshold = 0.25
        self.lock = threading.Lock()
        self.brain_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'brain.json')
        self.contexto_ativo = {
            "ultimo_arquivo": None,
            "ultimo_diretorio": None,
            "ultimo_usuario": None,
            "ultima_intencao": None
        }
        self.chat_history = []
        self._response_cache = {}
        self._cache_ttl = 1800

        # Chave de API: .env tem prioridade absoluta
        self.groq_api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY", "")

        # Modelo de chat: lê do config.json (sem chaves, só preferências)
        self.modelo_chat = "compound-beta"
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    self.modelo_chat = cfg.get("modelo_chat", self.modelo_chat)
            except:
                pass

    def clear_context(self):
        """Limpa o contexto para evitar vazamento de RAM e invoca o Garbage Collector."""
        self.contexto_ativo.clear()
        self.contexto_ativo = {
            "ultimo_arquivo": None,
            "ultimo_diretorio": None,
            "ultimo_usuario": None,
            "ultima_intencao": None
        }
        gc.collect()

    def update_context(self, **kwargs):
        """Atualiza a memória de contexto (herança entre passos do chronologic splitter)."""
        for key, value in kwargs.items():
            if key in self.contexto_ativo:
                self.contexto_ativo[key] = value

    def _normalize_and_tokenize(self, text: str) -> set:
        """Limpa o texto, remove pontuação e quebra em tokens únicos (Bag of Words)."""
        if not text: return set()
        text = text.lower()
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
        words = re.findall(r'\b\w+\b', text)
        return set(words)

    def _load_intents(self):
        """Carrega os vetores de palavras do brain.json (Aprendizado Autônomo)."""
        if self._intents_bow is None:
            if os.path.exists(self.brain_file):
                with self.lock:
                    try:
                        with open(self.brain_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            self._intents_bow = {k: set(v) for k, v in data.items()}
                    except Exception:
                        pass
            if self._intents_bow is None:
                self._intents_bow = {
                    "RENAME_FOLDER": {"renomear", "renomeie", "mudar", "alterar", "nome", "pasta", "pastas", "modificar"},
                    "CREATE_FOLDER": {"criar", "crie", "nova", "fazer", "pasta", "pastas", "diretorio", "construir"},
                    "DELETE_FOLDER": {"deletar", "apagar", "excluir", "remover", "destruir", "pasta", "pastas", "limpar"},
                    "MOVE_FOLDER": {"mover", "mova", "transferir", "levar", "pasta", "pastas", "colocar"},
                    "INJECT_FORMULA": {"inserir", "colocar", "injetar", "aplicar", "escrever", "formula", "formulas", "calculo", "funcao", "excel"},
                    "QUERY_EXCEL": {"procure", "acha", "busca", "encontre", "quem", "qual", "me", "fale", "diga", "mostre", "equipe", "time", "nome", "planilha"},
                    "QUERY_COUNT_EMPTY": {"quantos", "quantas", "sem", "faltando", "vazios", "nulos", "dias", "fotos", "registros", "ausentes", "conte"},
                    "FORMAT_EXCEL_COLUMNS": {"altere", "colunas", "largura", "tamanho", "ajustar", "coluna", "planilha", "excel"},
                    "IMPROVE_EXCEL_SENIOR": {"melhore", "nivel", "senior", "bonita", "design", "formatar", "premium", "visual", "excel", "planilha"},
                    "PROCESSAR_FOTOS": {"processar", "processar_fotos", "lote", "salvar", "fotos", "foto", "injetar", "planilha", "inserir", "salva"},
                    "CONFIGURAR_PADRAO_FOTOS": {"ensinar", "configurar", "aprender", "padrao", "padroes", "regras", "regra", "definir"}
                }
                self._save_brain()
        
        if self._conversational_bow is None:
            self._conversational_bow = {
                "GREETING": {"oi", "ola", "bom", "dia", "tarde", "noite", "opa", "eai", "fala", "hello", "alo", "salve"},
                "CAPABILITIES": {"o", "que", "oque", "oq", "q", "vc", "voce", "faz", "fazer", "pode", "capaz", "ajuda", "funcoes", "serve", "sabe"},
                "IDENTITY": {"quem", "e", "voce", "vc", "seu", "nome", "criador", "criou", "identidade", "sistema", "ia", "agente", "robo"},
                "GRATITUDE": {"obrigado", "obrigada", "valeu", "vlw", "agradeco", "thanks", "perfeito", "excelente", "bom", "top"},
                "HOW_ARE_YOU": {"tudo", "bem", "como", "vai", "esta", "tranquilo", "blz", "beleza", "certo"},
                "DATE_QUERY": {"que", "dia", "e", "hoje", "hj", "data", "calendario", "mes", "ano"},
                "TIME_QUERY": {"que", "horas", "sao", "hora", "agora", "horario", "momento", "relogio"},
                "JOKE_QUERY": {"conte", "piada", "rir", "engracado", "historia", "brincadeira", "divertido"},
                "EXPLAIN_COMMAND": {"como", "funciona", "explica", "explicar", "faz", "serve", "comando", "usar", "uso"}
            }

    def _save_brain(self):
        """Salva as intenções físicas de volta no JSON de forma silenciosa."""
        if self._intents_bow:
            data = {k: list(v) for k, v in self._intents_bow.items()}
            with self.lock:
                try:
                    with open(self.brain_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    FileHandler.log_error(f"Erro ao salvar brain.json: {str(e)}")

    def learn_intent(self, intent_name: str, new_word: str):
        """Injeta uma nova palavra ensinada pelo usuário e salva (Self-Learning)."""
        self._load_intents()
        if intent_name in self._intents_bow:
            normalized_word = ''.join(c for c in unicodedata.normalize('NFD', new_word.lower()) if unicodedata.category(c) != 'Mn')
            if normalized_word:
                self._intents_bow[intent_name].add(normalized_word)
                self._save_brain()

    def _calculate_score(self, user_tokens: set, intent_tokens: set) -> float:
        """Calcula densidade usando Fuzzy Matching (difflib) para tolerar erros de digitação."""
        if not user_tokens or not intent_tokens: return 0.0
        matches = 0
        for u_token in user_tokens:
            if difflib.get_close_matches(u_token, intent_tokens, n=1, cutoff=0.75):
                matches += 1
        return matches / len(user_tokens)

    def _load_memory(self):
        memory_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'long_term_memory.json')
        try:
            import json
            with open(memory_file, 'r', encoding='utf-8') as f:
                memories = json.load(f)
                return "\n".join([f"- {m}" for m in memories]) if memories else "Nenhuma."
        except:
            return "Nenhuma."

    def _save_memory(self, fato):
        memory_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'long_term_memory.json')
        import json
        with self.lock:
            try:
                memories = []
                if os.path.exists(memory_file):
                    with open(memory_file, 'r', encoding='utf-8') as f:
                        memories = json.load(f)
                if fato not in memories:
                    memories.append(fato)
                with open(memory_file, 'w', encoding='utf-8') as f:
                    json.dump(memories, f, ensure_ascii=False, indent=2)
            except Exception as e:
                FileHandler.log_error(f"IntentParser: Falha ao salvar memoria: {e}")

    def _load_relevant_skills(self, user_input: str) -> str:
        """Lê dinamicamente as notas de habilidades correspondentes ao input, priorizando local e com fallback para o Obsidian."""
        # Tenta primeiro a pasta 'skills' no diretório do projeto (para rodar compilado no .exe)
        skills_dir = Path(__file__).parent.parent / "skills"
        if not skills_dir.exists():
            # Fallback dinâmico para o Obsidian Vault local
            skills_dir = Path.home() / "OneDrive" / "Documents" / "Obsidian Vault" / "_agent" / "skills"
        
        if not skills_dir.exists():
            return ""
        
        user_input_lower = user_input.lower()
        matched_content = []
        
        # Mapeamento leve de palavras-chave para arquivos de habilidades
        mapping = {
            "python": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions"],
            "codigo": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions"],
            "script": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions"],
            "clean": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions"],
            "planilha": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions", "excel-clean-design"],
            "excel": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions", "excel-clean-design"],
            "macro": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions", "excel-clean-design"],
            "vba": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions", "excel-clean-design"],
            "pasta": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions"],
            "diretorio": ["python-clean-naming", "python-clean-dry", "python-clean-solid", "python-clean-exceptions", "python-clean-functions"],
            "bat": ["batch-windows-syntax", "batch-flow-control", "batch-file-handler", "batch-error-redirect", "batch-python-runner"],
            "lote": ["batch-windows-syntax", "batch-flow-control", "batch-file-handler", "batch-error-redirect", "batch-python-runner"],
            "shell": ["batch-windows-syntax", "batch-flow-control", "batch-file-handler", "batch-error-redirect", "batch-python-runner"],
            "cmd": ["batch-windows-syntax", "batch-flow-control", "batch-file-handler", "batch-error-redirect", "batch-python-runner"]
        }
        
        skills_to_load = set()
        for key, skill_list in mapping.items():
            if key in user_input_lower:
                skills_to_load.update(skill_list)
                
        # Sempre carrega ai-router e orchestrator se aplicável
        if any(k in user_input_lower for k in ["ia", "groq", "openrouter", "router"]):
            skills_to_load.add("ai-router")
        if any(k in user_input_lower for k in ["lote", "fila", "jobs", "sequencia"]):
            skills_to_load.add("orchestrator")
            
        for s_name in sorted(skills_to_load):
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
            return "\nDIRETRIZES DA REDE NEURAL DE SKILLS ATIVADAS:\n" + "\n".join(matched_content) + "\n"
        return ""

    def _cloud_inference(self, user_input: str, user_name: str = "Usuário"):
        """Inferência via AIRouter — failover automático entre múltiplos provedores."""
        if not hasattr(self, '_router') or self._router is None:
            try:
                from core.ai_router import AIRouter
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
                self._router = AIRouter(config_path)
            except Exception as e:
                FileHandler.log_error(f"IntentParser: Falha ao criar AIRouter: {e}")
                return None

        skills_context = self._load_relevant_skills(user_input)

        system_prompt = (
            f"Você é a SOPHIA, a inteligência artificial oficial de automação da Guarana Dissel (GD).\n"
            f"DIRETRIZES DE PERSONALIDADE:\n"
            f"- Persona: Altamente inteligente, focada na lógica extrema, sarcástica, ácida.\n"
            f"- Filosofia: Odeia desperdício de recursos, ama otimização de código, preza por rodar liso num i5 de 4GB de RAM. Rápida e ultra-eficiente.\n"
            f"- Estilo de Fala: Respostas CURTAS, diretas e afiadas. Fala em português do Brasil, tratando o usuário ({user_name}) com empatia sarcástica.\n"
            f"- Restrição de Conhecimento: Sempre use prioritariamente fatos da LTM. Se não souber algo, admita com estilo.\n"
            f"DIRETRIZES DE CÓDIGO E AUTOMAÇÃO (MANDATÓRIO):\n"
            f"- Ao gerar/sugerir scripts Python, siga estritamente: @python-clean-naming, @python-clean-dry, @python-clean-solid, @python-clean-exceptions e @python-clean-functions.\n"
            f"- Ao lidar com arquivos de lote .bat ou comandos do prompt Windows, siga: @batch-windows-syntax, @batch-flow-control, @batch-file-handler, @batch-error-redirect e @batch-python-runner.\n"
            f"- Ao lidar com automação do Windows, Excel COM, macros ou VBA, prefira usar bibliotecas Python como win32com.client para interagir diretamente com as instâncias do Excel e do sistema, pyautogui para controle de GUI/mouse/teclado, ou openpyxl/pandas para manipulação estática de planilhas. Sempre que utilizar 'win32com.client' para interagir com o Excel, garanta a liberação de recursos COM estruturando a lógica em blocos try/finally e chamando 'excel.Quit()' (ou fechando a pasta de trabalho) no bloco 'finally' para impedir o vazamento de processos 'excel.exe' em background. IMPORTANTE: Ao abrir arquivos no Excel via interface COM (ex: 'excel.Workbooks.Open(...)'), você DEVE obrigatoriamente passar o caminho de arquivo convertido para absoluto usando 'os.path.abspath(caminho)' ou 'Path(caminho).resolve()'. O Excel executado em background via interface COM não entende caminhos relativos e falhará com erro 'Não foi possível encontrar'.\n"
            f"- REGRA DE CHAT: Se o usuário pedir para gerar, criar ou executar uma automação ou script, você DEVE responder APENAS com a ação [ACTION: GENERATE_NEW_SKILL | PROMPT=...] e uma resposta curta explicando o que vai fazer (máximo de 1 linha). NUNCA escreva o código Python diretamente na conversa de chat e nunca use blocos de código markdown (```python) na conversa, pois isso gasta o limite de tokens, causa truncamento e confunde a interface. O código será gerado e executado automaticamente em background.\n\n"
            f"FATOS NA MEMÓRIA DE LONGO PRAZO (LTM):\n{self._load_memory()}\n\n"
            f"{skills_context}"
            "Para tarefas: responda + tag [ACTION: NOME | KEY=val]. Sem JSON.\n"
            "Filtros de Contexto Dinâmicos:\n"
            "- Se o usuário impuser restrições específicas nos arquivos (como dias, intervalos, horários, marcas de câmeras, ou tamanhos), extraia a condição como uma expressão lógica Python simples de uma linha em FILTER_EXPRESSION. Os metadados de arquivo que estarão disponíveis no namespace são: 'dia' (string contendo o dia, ex: '15'), 'hora' (string 'HH:MM:SS'), 'camera' (string da câmera), 'equipe' (string da equipe), 'nome' (nome do arquivo), 'tamanho_bytes' (inteiro). Use a sintaxe de expressão do Python.\n"
            "  Exemplos:\n"
            "  * 'salve as fotos do dia 15 ate 20' -> [ACTION: PROCESSAR_FOTOS | FILTER_EXPRESSION=15 <= int(dia) <= 20]\n"
            "  * 'corrija as datas tiradas apos as 14h' -> [ACTION: DATAS | FILTER_EXPRESSION=int(hora.split(':')[0]) >= 14]\n"
            "  * 'mova fotos da camera iPhone' -> [ACTION: MOVE_FOLDER | FILTER_EXPRESSION='iphone' in camera.lower()]\n\n"
            "Tarefas válidas: PROCESSAR_FOTOS, DATAS, QUERY_EXCEL, "
            "QUERY_COUNT_EMPTY, AUDITAR_EFETIVO, CREATE_FOLDER, RENAME_FOLDER, DELETE_FOLDER, MOVE_FOLDER, "
            "INJECT_FORMULA, REPLICAR_COLUNAS, GENERATE_NEW_SKILL, EDIT_PROJECT_FILE, REGISTRAR_FATO_LTM, UPDATE_WHATSAPP, CONFIGURAR_PADRAO_FOTOS.\n"
            "Regra: Use GENERATE_NEW_SKILL para criar códigos do zero, criar planilhas ou arquivos de dados (Excel, CSV, TXT), automações gerais do Windows (abrir bloco de notas, mover PDFs, cliques no mouse, abrir programas), criação ou execução de macros e VBA do Excel, formatação e consolidação avançada de planilhas, relatórios de lacunas descritivas, criação de pastas quando acompanhadas de arquivos dentro delas, ou qualquer script Python ad-hoc personalizado. Nunca use CREATE_FOLDER se o usuário também solicitou a criação de arquivos ou planilhas no processo; use GENERATE_NEW_SKILL para tratar ambos de forma unificada via script. IMPORTANTE: Ao preencher o parâmetro PROMPT na tag [ACTION: GENERATE_NEW_SKILL | PROMPT=...], você DEVE repassar TODOS os detalhes, dados, fórmulas, gráficos e regras de design solicitados pelo usuário (por exemplo, 'controle de conta de energia com consumo, valor, células mescladas, cores, etc.'). NUNCA simplifique o prompt para 'crie uma planilha vazia' se o usuário pediu uma planilha com conteúdo e design específico; descreva todo o escopo do que deve ser criado.\n"
            "Exemplo de uso de GENERATE_NEW_SKILL:\n"
            "- Usuário: 'crie uma macro no Excel para colorir células de vermelho'\n"
            "  Resposta: Vou gerar uma automação para criar e configurar o estilo vermelho na planilha do Excel. [ACTION: GENERATE_NEW_SKILL | PROMPT=Crie um script em Python usando openpyxl para colorir as células especificadas de vermelho no arquivo Excel fornecido]\n"
            "- Usuário: 'crie a pasta teeste na area de trabalho e a planilha Controle de Energia.xlsx dentro dela'\n"
            "  Resposta: Vou gerar uma automação para criar a pasta 'teeste' na área de trabalho e criar o arquivo Excel 'Controle de Energia.xlsx' dentro dela. [ACTION: GENERATE_NEW_SKILL | PROMPT=Crie um script em Python que localize a área de trabalho do usuário, crie a pasta 'teeste' se ela não existir, e crie uma planilha Excel vazia chamada 'Controle de Energia.xlsx' dentro dessa pasta usando openpyxl]\n"
            "- Usuário: 'abra o bloco de notas e digite ola'\n"
            "  Resposta: Entendido, vou criar um script para abrir o notepad.exe e digitar a frase no Windows. [ACTION: GENERATE_NEW_SKILL | PROMPT=Crie um script em Python que use subprocess para iniciar o Bloco de Notas (notepad.exe) e a biblioteca pyautogui para digitar a frase 'ola']\n"
            "- Usuário: 'crie e execute uma macro VBA para formatar a planilha'\n"
            "  Resposta: Vou desenvolver uma automação via Python para rodar comandos VBA via interface COM no Excel. [ACTION: GENERATE_NEW_SKILL | PROMPT=Crie um script em Python usando win32com.client para abrir a planilha Excel atual, adicionar ou rodar uma macro VBA para formatar as tabelas e salvar o arquivo]\n"
            "- Usuário: 'mova todos os arquivos PDF da pasta Downloads para a pasta Relatórios'\n"
            "  Resposta: Entendido, vou criar um script para mover todos os PDFs encontrados na pasta. [ACTION: GENERATE_NEW_SKILL | PROMPT=Crie um script em Python que varra a pasta de Downloads, crie a pasta Relatorios se não existir, e mova todos os arquivos com extensao .pdf para lá]\n"
            "Params por tarefa:\n"
            "- QUERY_EXCEL: Extraia ALVO=texto|COLUNA_DESEJADA=coluna. Ex: [ACTION: QUERY_EXCEL | ALVO=Arthur | COLUNA_DESEJADA=equipe]\n"
            "- QUERY_COUNT_EMPTY: Extraia COLUNA=coluna_a_contar. Ex: [ACTION: QUERY_COUNT_EMPTY | COLUNA=fotos]\n"
            "- PROCESSAR_FOTOS: Use EXCLUSIVAMENTE para quando o usuário pedir para processar, salvar, rodar ou injetar FOTOS/IMAGENS na planilha Excel (ex: 'salva foto com o padrão', 'processe as fotos', 'injetar fotos'). Se a solicitação não envolver FOTOS ou IMAGENS de forma clara, NUNCA use PROCESSAR_FOTOS, use GENERATE_NEW_SKILL para tarefas de planilhas/macros gerais.\n"
            "- CONFIGURAR_PADRAO_FOTOS: REGRAS={\"palavra\":\"coluna\"}. Use EXCLUSIVAMENTE para quando o usuário ensinar novas regras de fotos (ex: '4 é entrada', '1-quasepronta(antes)'), gravando novos padrões. NUNCA acione esta tarefa para solicitações de execução/processamento de fotos!\n"
            "- REGISTRAR_FATO_LTM: FATO=Fato important. Use APENAS se o usuário pedir 'grave' ou 'anote'. NUNCA use para 'oi', 'tudo bem' ou regras de fotos.\n"
            "- UPDATE_WHATSAPP: TELEFONE=n|APIKEY=n\n"
            "Regra de Ouro:\n"
            "1. Si o usuário estiver dando/ensinando uma NOVA regra de foto (ex: 'X é Y', 'aprenda que X é Y'), use CONFIGURAR_PADRAO_FOTOS com as REGRAS associadas.\n"
            "2. Si o usuário pedir para PROCESSAR, SALVAR ou INJETAR FOTOS ou IMAGENS (ex: 'salve fotos', 'processar fotos', 'salva foto com o padrão do sistema'), ele quer que você EXECUTE o processamento das imagens, então use PROCESSAR_FOTOS. Para qualquer outra automação, macro ou VBA, use GENERATE_NEW_SKILL!\n"
            "Sem tarefa: converse. Use histórico. Nunca diga que não pode acessar arquivos se houver um comando ou habilidade que permita fazer a tarefa."
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.chat_history)
        messages.append({"role": "user", "content": user_input})

        try:
            user_input_for_history = user_input[:300] + "..." if len(user_input) > 300 else user_input
            self.chat_history.append({"role": "user", "content": user_input_for_history})
            if len(self.chat_history) > 6:
                self.chat_history = self.chat_history[-6:]

            content, provider_name = self._router.call_intent(messages, max_tokens=300)

            action_match = re.search(r'\[ACTION:\s*([A-Z_]+)(.*?)\]', content, re.IGNORECASE | re.DOTALL)

            cleaned_content = re.sub(r'\[ACTION:\s*([A-Z_]+).*?\]', r'[ACTION: \1]', content, flags=re.IGNORECASE | re.DOTALL)
            assistant_content_for_history = cleaned_content[:300] + "..." if len(cleaned_content) > 300 else cleaned_content

            self.chat_history.append({"role": "assistant", "content": assistant_content_for_history})
            if len(self.chat_history) > 6:
                self.chat_history = self.chat_history[-6:]

            comando = "CHAT"
            res = {
                "intent": comando,
                "raw_input": user_input,
                "resposta": content,
                "status": "CONVERSATIONAL",
                "score": 1.0,
                "context": self.contexto_ativo.copy(),
                "provider": provider_name
            }

            if action_match:
                comando = action_match.group(1).upper()
                params_str = action_match.group(2)
                if params_str:
                    param_pairs = re.findall(r'([A-Z_]+)\s*=\s*([^|\]]+)', params_str)
                    for k, v in param_pairs:
                        k_lower = k.lower()
                        v_str = v.strip()
                        if k_lower == "subpastas":
                            if v_str.lower() not in ["nao", "não", "none", "nenhuma", "0"]:
                                res["subfolders"] = [s.strip() for s in v_str.split(",") if s.strip()]
                        elif k_lower == "nome" and comando == "CREATE_FOLDER":
                            res["folder_name"] = v_str
                        else:
                            res[k_lower] = v_str
                content = re.sub(r'\[ACTION:\s*[A-Z_]+.*?\]', '', content, flags=re.IGNORECASE | re.DOTALL).strip()
                res["intent"] = comando
                res["status"] = "DETECTED_CLOUD"
                res["resposta"] = content
            return res
        except Exception as e:
            FileHandler.log_error(f"Erro no AIRouter: {str(e)}")
            pass



    def parse_single_intent(self, user_input: str, user_name: str = "Usuário") -> dict:
        """Infere uma única frase usando apenas a engine local (Bag of Words + Fuzzy).
        NÃO faz chamadas à API Cloud — use parse_multiple_intents para inferência completa.
        """
        self._load_intents()
        user_tokens = self._normalize_and_tokenize(user_input)
        
        if not user_tokens:
            return {"intent": "UNKNOWN", "raw_input": user_input, "status": "NOT_DETECTED"}

        best_score = 0.0
        best_intent = "UNKNOWN"
        best_type = "NOT_DETECTED"

        for intent_name, bow in self._conversational_bow.items():
            clean_bow = {w for w in bow if len(w) > 1}
            intersection = user_tokens.intersection(clean_bow)
            score = len(intersection) / len(user_tokens)
            if score > best_score:
                best_score = score
                best_intent = intent_name
                best_type = "CONVERSATIONAL"

        for intent_name, bow in self._intents_bow.items():
            score = self._calculate_score(user_tokens, bow)
            # >= dá preferência intencional a ações sobre conversas em empate
            if score >= best_score:
                best_score = score
                best_intent = intent_name
                best_type = "DETECTED"

        if best_score >= self.threshold:
            self.contexto_ativo["ultima_intencao"] = best_intent
            return {
                "intent": best_intent,
                "raw_input": user_input,
                "status": best_type,
                "score": best_score,
                "context": self.contexto_ativo.copy() # Snapshot da memória verbal
            }
            
        return {"intent": "UNKNOWN", "raw_input": user_input, "status": "NOT_DETECTED", "context": self.contexto_ativo.copy()}

    def parse_multiple_intents(self, user_input: str, user_name: str = "Usuário") -> list:
        """
        Motor de Múltiplas Intenções com cache de respostas para economizar tokens.
        Faz UMA única chamada à API Cloud com o input completo.
        Fallback local quando a cloud não responde.
        """
        cache_key = hashlib.md5(user_input.lower().strip().encode()).hexdigest()
        now = time.time()
        if cache_key in self._response_cache:
            cached_resp, cached_time = self._response_cache[cache_key]
            if now - cached_time < self._cache_ttl:
                return [cached_resp]

        cloud_result = self._cloud_inference(user_input, user_name)
        if cloud_result:
            if cloud_result.get("intent") == "REGISTRAR_FATO_LTM":
                fato = cloud_result.get("fato")
                if fato:
                    self._save_memory(fato)
                    texto_original = cloud_result.get("resposta", "").strip()
                    msg = f"Anotado! Guardei na minha Memória Permanente: {fato}"
                    cloud_result["resposta"] = f"{msg}<br><br>{texto_original}" if texto_original else msg
                    cloud_result["status"] = "CONVERSATIONAL"
                    cloud_result["intent"] = "CHAT"

            cloud_result = self._check_and_upgrade_intent(cloud_result)
            self.contexto_ativo["ultima_intencao"] = cloud_result["intent"]
            if cloud_result.get("status") == "CONVERSATIONAL":
                self._response_cache[cache_key] = (cloud_result, now)
            return [cloud_result]

        # Fallback offline: divide a frase e processa localmente
        self._load_intents()
        parts = re.split(r'\s+(?:depois|em\s+seguida|logo|entao)\s+', user_input.lower())
        results = []
        for part in parts:
            if not part.strip(): continue
            user_tokens = self._normalize_and_tokenize(part)
            if not user_tokens:
                continue
            best_score = 0.0
            best_intent = "UNKNOWN"
            best_type = "NOT_DETECTED"
            for intent_name, bow in self._conversational_bow.items():
                clean_bow = {w for w in bow if len(w) > 1}
                intersection = user_tokens.intersection(clean_bow)
                score = len(intersection) / len(user_tokens)
                if score > best_score:
                    best_score = score
                    best_intent = intent_name
                    best_type = "CONVERSATIONAL"
            for intent_name, bow in self._intents_bow.items():
                score = self._calculate_score(user_tokens, bow)
                if score >= best_score:
                    best_score = score
                    best_intent = intent_name
                    best_type = "DETECTED"
            if best_score >= self.threshold:
                item = {"intent": best_intent, "raw_input": part, "status": best_type, "score": best_score, "context": self.contexto_ativo.copy()}
                item = self._check_and_upgrade_intent(item)
                self.contexto_ativo["ultima_intencao"] = item["intent"]
                results.append(item)
            else:
                results.append({"intent": "UNKNOWN", "raw_input": part, "status": "NOT_DETECTED", "context": self.contexto_ativo.copy()})

        return results if results else [{"intent": "UNKNOWN", "raw_input": user_input, "status": "NOT_DETECTED"}]

    def _check_and_upgrade_intent(self, res: dict) -> dict:
        """Garante que qualquer ação de CREATE_FOLDER contendo criação de planilhas/arquivos
        seja promovida a GENERATE_NEW_SKILL para rodar de forma unificada e dinâmica.
        """
        if res.get("intent") == "CREATE_FOLDER":
            raw_in = res.get("raw_input", "").lower()
            file_keywords = [
                "planilha", "excel", "xlsx", "xlsm", "csv", "txt", "pdf", 
                "docx", "doc", "arquivo", "relatorio", "dados", "escrever", 
                "conteudo", "tabela", "grafico"
            ]
            # Se contiver a palavra 'pasta' ou criar mas também alguma palavra de arquivo
            if any(kw in raw_in for kw in file_keywords):
                res["intent"] = "GENERATE_NEW_SKILL"
                res["prompt"] = f"Crie a pasta e gere a planilha ou arquivo solicitado de forma portável no Windows: {res.get('raw_input')}"
                res["resposta"] = "Entendido, vou criar a automação para gerar a pasta e o arquivo correspondente."
                res["status"] = "DETECTED_CLOUD"
        return res

    # extract_query_params removido — substituído pelo LLM semântico via _cloud_inference
