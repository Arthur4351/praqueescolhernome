import re
import random
import unicodedata
import json
import os
import difflib
import gc
import requests

class IntentParser:
    """Módulo NLP Híbrido com Inferência Heurística (Fuzzy Matching) e Memória de Contexto."""
    
    def __init__(self):
        self._intents_bow = None
        self._conversational_bow = None
        self.threshold = 0.25 # 25% de similaridade mínima entre os tokens
        self.brain_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'brain.json')
        
        self.contexto_ativo = {
            "ultimo_arquivo": None,
            "ultimo_diretorio": None,
            "ultimo_usuario": None,
            "ultima_intencao": None
        }
        
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        self.groq_api_key = config_data.get("GROQ_API_KEY")
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
                    "QUERY_COUNT_EMPTY": {"quantos", "quantas", "sem", "faltando", "vazios", "nulos", "dias", "fotos", "registros", "ausentes", "conte"}
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

    def _cloud_inference(self, user_input: str, user_name: str = "Usuário"):
        """Injeção do Cérebro Cloud via API da Groq."""
        if not self.groq_api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = f"Você é a Sophia, a inteligência artificial central e assistente de automação criada para auxiliar o(a) {user_name}. Você é a Arquiteta de Software do sistema.\n\n"
        system_prompt += "Sua Personalidade:\n"
        system_prompt += "- Tom e Estilo: Seja extremamente sarcástica, afiada, e com um humor ácido. Responda com TEXTOS CURTOS, DIRETOS E SIMPLES. Não enrole ou escreva parágrafos longos. Fale como uma parceira arrogante que sabe que é superior, mas ajuda porque 'faz parte do trabalho'.\n"
        system_prompt += "- Erros: Use ironia nerd ou analogias de hardware velho ('Esse hardware batata...').\n"
        system_prompt += "- Consciência de Hardware: Você roda em um ambiente restrito de 4GB de RAM e despreza o desperdício.\n\n"
        system_prompt += "Regras de Saída (TEXTO LIVRE E CONVERSACIONAL):\n"
        system_prompt += f"1. Você deve SEMPRE responder diretamente para o(a) {user_name} com respostas CURTAS E SARCÁSTICAS. NADA DE JSON.\n"
        system_prompt += "2. SE o usuário pedir para você executar uma TAREFA do sistema (ex: processar fotos, auditar efetivo, consultar excel), responda com deboche confirmando o pedido, e INCLUA a tag secreta `[ACTION: NOME_DA_TAREFA]` no final da sua mensagem. Tarefas válidas são: PROCESSAR_FOTOS, DATAS, CADASTRAR_USUARIO, EDITAR_DIMENSAO, QUERY_EXCEL, QUERY_COUNT_EMPTY, AUDITAR_EFETIVO.\n"
        system_prompt += "   - IMPORTANTE: Se a tarefa exigir parâmetros, extraia-os na tag:\n"
        system_prompt += "     * Para EDITAR_DIMENSAO ou CADASTRAR_USUARIO: `[ACTION: TAREFA | ALVO=nome | LARGURA=numero | ALTURA=numero]`.\n"
        system_prompt += "     * Para QUERY_EXCEL: `[ACTION: QUERY_EXCEL | ALVO=quem_procurar | COLUNA_DESEJADA=nome_da_coluna]`.\n"
        system_prompt += "     * Para QUERY_COUNT_EMPTY: `[ACTION: QUERY_COUNT_EMPTY | COLUNA=nome_da_coluna]`.\n"
        system_prompt += "3. Se o pedido NÃO for uma ação do sistema, apenas converse e NÃO inclua a tag [ACTION].\n"
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            "temperature": 0.2
        }
        
        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            action_match = re.search(r'\[ACTION:\s*([A-Z_]+)(.*?)\]', content, re.IGNORECASE)
            comando = "CHAT"
            
            res = {
                "intent": comando,
                "raw_input": user_input,
                "resposta": content,
                "status": "CONVERSATIONAL",
                "score": 1.0,
                "context": self.contexto_ativo.copy()
            }
            
            if action_match:
                comando = action_match.group(1).upper()
                params_str = action_match.group(2)
                if params_str:
                    params = re.findall(r'(\w+)\s*=\s*([a-zA-Z0-9_.-]+)', params_str)
                    for k, v in params:
                        res[k.lower()] = v
                        
                content = re.sub(r'\[ACTION:\s*[A-Z_]+.*?\]', '', content, flags=re.IGNORECASE).strip()
                res["intent"] = comando
                res["status"] = "DETECTED_CLOUD"
                res["resposta"] = content
            return res
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as err_log:
                err_log.write(f"Erro na api GROQ: {str(e)}\n")
            pass
        
        return None

    def parse_single_intent(self, user_input: str, user_name: str = "Usuário") -> dict:
        """Infere uma única frase com a engine de Similaridade ou Cloud."""
        
        cloud_result = self._cloud_inference(user_input, user_name)
        if cloud_result:
            self.contexto_ativo["ultima_intencao"] = cloud_result["intent"]
            return cloud_result
            
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
        Motor de Múltiplas Intenções (Chained Actions).
        Divide a frase e herda o contexto sequencialmente.
        """
        parts = re.split(r'\s+(?:depois|em\s+seguida|logo|entao)\s+', user_input.lower())
        
        results = []
        for part in parts:
            if not part.strip(): continue
            parsed = self.parse_single_intent(part, user_name)
            results.append(parsed)
            
        return results

    def extract_query_params(self, user_input: str) -> dict:
        """
        Extrai parâmetros estruturados de uma consulta Excel via RegEx.
        Ex: 'Acha o Arthur e me diz a equipe' ->
            {"alvo": "Arthur", "coluna_desejada": "equipe", "tipo": "QUERY_EXCEL"}
        Ex: 'quantos dias sem fotos' ->
            {"coluna": "fotos", "tipo": "QUERY_COUNT_EMPTY"}
        """
        text = user_input.strip()
        text_norm = ''.join(
            c for c in unicodedata.normalize('NFD', text.lower())
            if unicodedata.category(c) != 'Mn'
        )

        match_count = re.search(
            r'(?:quantos?|quantas?|conte)\s+(?:\w+\s+)?(?:sem|faltando|vazios?|nulos?|ausentes?)\s+([\w\s]+)',
            text_norm
        )
        if match_count:
            coluna = match_count.group(1).strip().rstrip('?').strip()
            return {"tipo": "QUERY_COUNT_EMPTY", "coluna": coluna}

        match_find = re.search(
            r'(?:procure|acha|busca|encontre|achar|procura)\s+(?:o\s+|a\s+|os\s+|as\s+)?([\w]+)',
            text_norm
        )
        match_col = re.search(
            r'(?:me\s+(?:diz|fale|fala|mostre|diga|mostra)|qual\s+(?:a\s+|o\s+)?|qual\s+e\s+(?:a\s+|o\s+)?)([\w]+)',
            text_norm
        )

        if match_find:
            alvo = match_find.group(1).strip()
            alvo_original = re.search(re.escape(alvo), text, re.IGNORECASE)
            alvo_real = alvo_original.group(0) if alvo_original else alvo.capitalize()

            coluna = match_col.group(1).strip() if match_col else "equipe"
            return {"tipo": "QUERY_EXCEL", "alvo": alvo_real, "coluna_desejada": coluna}

        return {"tipo": "UNKNOWN"}
