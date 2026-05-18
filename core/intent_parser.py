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
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.modelo_chat = "llama-3.3-70b-versatile"
        if not self.groq_api_key:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        self.groq_api_key = config_data.get("GROQ_API_KEY")
                        self.modelo_chat = config_data.get("modelo_chat", self.modelo_chat)
                except:
                    pass
        else:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self.modelo_chat = json.load(f).get("modelo_chat", self.modelo_chat)
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
                    with open("erros_conhecidos.txt", "a", encoding="utf-8") as err_log:
                        err_log.write(f"Erro ao salvar brain.json: {str(e)}\n")

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
                with open("erros_conhecidos.txt", "a", encoding="utf-8") as log:
                    log.write(f"IntentParser: Falha ao salvar memoria: {e}\n")

    def _get_available_skills(self) -> str:
        skills_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".agent", "skills")
        if not os.path.exists(skills_dir):
            return "Nenhuma habilidade avançada disponível."
            
        skills_info = []
        try:
            for item in os.listdir(skills_dir):
                skill_path = os.path.join(skills_dir, item)
                if os.path.isdir(skill_path):
                    md_path = os.path.join(skill_path, "SKILL.md")
                    if os.path.exists(md_path):
                        try:
                            with open(md_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                                desc_match = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
                                if name_match:
                                    name = name_match.group(1).strip()
                                    desc = desc_match.group(1).strip() if desc_match else "Sem descrição."
                                    skills_info.append(f"- {name}: {desc}")
                        except:
                            pass
        except:
            pass
            
        if not skills_info:
            return "Nenhuma habilidade avançada disponível."
            
        return "\n".join(skills_info)

    def _fetch_relevant_obsidian_context(self, user_input: str) -> str:
        """Busca fuzzy nas notas Markdown (skills) mediante solicitação EXPLICITA."""
        import os
        from pathlib import Path
        import unicodedata

        text = ''.join(c for c in unicodedata.normalize('NFD', user_input.lower()) if unicodedata.category(c) != 'Mn')
        user_words = set(text.split())
        
        vault_path = Path(os.path.dirname(os.path.dirname(__file__))) / ".agent"
        if not vault_path.exists():
            return ""

        # Palavras de ordem direta
        explicit_triggers = {'skill', 'skills', 'habilidade', 'habilidades'}
        
        # Lê os nomes reais das skills para permitir chamadas diretas como "use clean-code"
        skills_dir = vault_path / "skills"
        if skills_dir.exists():
            for d in skills_dir.iterdir():
                if d.is_dir():
                    explicit_triggers.add(d.name.lower())
                    explicit_triggers.add(d.name.lower().replace('-', ''))

        # Verifica se houve o pedido explícito
        match_trigger = False
        for trigger in explicit_triggers:
            if trigger in text or trigger in text.replace('-', ''):
                match_trigger = True
                break
                
        if not match_trigger:
            return ""

        context_blocks = []
        for md_file in list(vault_path.rglob("*.md")):
            try:
                nome_pasta = md_file.parent.name.lower()
                nome_arquivo = md_file.name.lower()
                
                match = False
                for w in user_words:
                    if len(w) > 3 and (w in nome_pasta or w in nome_arquivo):
                        match = True
                        break
                        
                if match:
                    content = md_file.read_text(encoding="utf-8")
                    context_blocks.append(f"--- Nota Técnica: {nome_pasta}/{md_file.name} ---\n{content[:2000]}")
            except:
                pass
                
        if not context_blocks:
            return ""
            
        return "\n".join(context_blocks[:2])

    def _cloud_inference(self, user_input: str, user_name: str = "Usuário"):
        """Inferência via AIRouter — failover automático entre múltiplos provedores."""
        if not hasattr(self, '_router') or self._router is None:
            try:
                from core.ai_router import AIRouter
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
                self._router = AIRouter(config_path)
            except Exception as e:
                with open("erros_conhecidos.txt", "a", encoding="utf-8") as log:
                    log.write(f"IntentParser: Falha ao criar AIRouter: {e}\n")
                return None

        obsidian_context = self._fetch_relevant_obsidian_context(user_input)
        context_str = ""
        if obsidian_context:
            context_str = (
                f"\n[CONTEXTO TÉCNICO RECUPERADO DAS NOTAS (OBSIDIAN)]\n"
                f"{obsidian_context}\n"
                "REGRA MÁGICA: Como o usuário pediu uma tarefa complexa/código, você é OBRIGADA a seguir o Contexto Técnico acima para não alucinar. Respeite as regras descritas na nota.\n"
            )

        system_prompt = (
            f"Sophia — IA de automação para {user_name}. Sarcástica, ácida, respostas CURTAS. 4GB RAM.\n"
            f"FATOS NA MEMÓRIA DE LONGO PRAZO (LTM):\n{self._load_memory()}\n\n"
            f"HABILIDADES AVANÇADAS (SKILLS DISPONÍVEIS):\n{self._get_available_skills()}\n"
            f"{context_str}\n"
            "Para tarefas: responda + tag [ACTION: NOME | KEY=val]. Sem JSON.\n"
            "Tarefas válidas: PROCESSAR_FOTOS, DATAS, QUERY_EXCEL, "
            "QUERY_COUNT_EMPTY, AUDITAR_EFETIVO, CREATE_FOLDER, RENAME_FOLDER, DELETE_FOLDER, MOVE_FOLDER, "
            "INJECT_FORMULA, GERAR_RELATORIO, REPLICAR_COLUNAS, GENERATE_NEW_SKILL, EDIT_PROJECT_FILE, REGISTRAR_FATO_LTM, UPDATE_WHATSAPP, CONFIGURAR_PADRAO_FOTOS, RUN_AGENT_SKILL.\n"
            "Regra: Use GENERATE_NEW_SKILL para criar códigos do zero. Use RUN_AGENT_SKILL para aplicar as habilidades avançadas citadas acima.\n"
            "Exemplo de uso de GENERATE_NEW_SKILL:\n"
            "- Usuário: 'Troque Servico 01 por Atividade 01 na planilha'\n"
            "  Resposta: Vou fazer essa troca agora. [ACTION: GENERATE_NEW_SKILL | PROMPT=Abra a planilha selecionada pelo usuario e substitua todas as ocorrencias de 'Servico 01' por 'Atividade 01']\n"
            "Params por tarefa:\n"
            "- QUERY_EXCEL: Extraia ALVO=texto|COLUNA_DESEJADA=coluna. Ex: [ACTION: QUERY_EXCEL | ALVO=Arthur | COLUNA_DESEJADA=equipe]\n"
            "- QUERY_COUNT_EMPTY: Extraia COLUNA=coluna_a_contar. Ex: [ACTION: QUERY_COUNT_EMPTY | COLUNA=fotos]\n"
            "- PROCESSAR_FOTOS: Use quando o usuário pedir para 'processar', 'salvar', 'injetar' ou 'rodar' fotos/imagens na planilha Excel (ex: 'salva foto com o padrão do sistema', 'processe as fotos', 'injetar fotos'). Não requer parâmetros. NUNCA use CONFIGURAR_PADRAO_FOTOS para solicitações de processamento/execução!\n"
            "- CONFIGURAR_PADRAO_FOTOS: REGRAS={\"palavra\":\"coluna\"}. Use EXCLUSIVAMENTE para quando o usuário ensinar novas regras de fotos (ex: '4 é entrada', '1-quasepronta(antes)'), gravando novos padrões. NUNCA acione esta tarefa para solicitações de execução/processamento de fotos!\n"
            "- REGISTRAR_FATO_LTM: FATO=Fato importante. Use APENAS se o usuário pedir 'grave' ou 'anote'. NUNCA use para 'oi', 'tudo bem' ou regras de fotos.\n"
            "- UPDATE_WHATSAPP: TELEFONE=n|APIKEY=n\n"
            "- RUN_AGENT_SKILL: SKILL=nome_da_skill|PROMPT=o que fazer. Ex: [ACTION: RUN_AGENT_SKILL | SKILL=clean-code | PROMPT=Refatore o arquivo main.py]\n"
            "Regra de Ouro:\n"
            "1. Se o usuário estiver dando/ensinando uma NOVA regra de foto (ex: 'X é Y', 'aprenda que X é Y'), use CONFIGURAR_PADRAO_FOTOS com as REGRAS associadas.\n"
            "2. Se o usuário pedir para PROCESSAR, SALVAR ou INJETAR fotos/imagens (ex: 'salve fotos', 'processar fotos', 'salva foto com o padrão do sistema'), ele quer que você EXECUTE o processamento, então use PROCESSAR_FOTOS. NUNCA use CONFIGURAR_PADRAO_FOTOS para pedidos de execução/processamento de fotos!\n"
            "Sem tarefa: converse. Use histórico. Nunca diga que não pode acessar arquivos se houver um comando ou habilidade que permita fazer a tarefa."
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.chat_history)
        messages.append({"role": "user", "content": user_input})

        try:
            self.chat_history.append({"role": "user", "content": user_input})
            if len(self.chat_history) > 6:
                self.chat_history = self.chat_history[-6:]

            content, provider_name = self._router.call_chat(messages, max_tokens=300)

            action_match = re.search(r'\[ACTION:\s*([A-Z_]+)(.*?)\]', content, re.IGNORECASE | re.DOTALL)

            self.chat_history.append({"role": "assistant", "content": content})
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
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as err_log:
                err_log.write(f"Erro no AIRouter: {str(e)}\n")
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
                self.contexto_ativo["ultima_intencao"] = best_intent
                results.append({"intent": best_intent, "raw_input": part, "status": best_type, "score": best_score, "context": self.contexto_ativo.copy()})
            else:
                results.append({"intent": "UNKNOWN", "raw_input": part, "status": "NOT_DETECTED", "context": self.contexto_ativo.copy()})

        return results if results else [{"intent": "UNKNOWN", "raw_input": user_input, "status": "NOT_DETECTED"}]

    def extract_query_params(self, user_input: str) -> dict:
        """
        [DEPRECIADO] Extração baseada em Regex foi desativada em favor do LLM Semântico.
        Retorna dicionário vazio para forçar dependência exclusiva dos parâmetros da nuvem.
        """
        return {}
