import re
import json
import asyncio
from datetime import datetime
from collections import defaultdict
import hashlib

try:
    try:
        # Tenta importar o novo nome do pacote
        from ddgs import DDGS
    except ImportError:
        # Se falhar, tenta o nome antigo
        from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("AVISO: duckduckgo_search/ddgs não está instalado. A funcionalidade de busca será desabilitada.")

# Banco de dados em memória para contexto e aprendizado avançado
class SophiaMemory:
    def __init__(self):
        self.conversations = defaultdict(list)
        self.user_context = {}
        self.knowledge_base = {}
        self.patterns = {}
        self.responses_cache = {}
        self.entities = {}  # Para reconhecimento de entidades
        self.intents = {}   # Para reconhecimento de intenções

    def add_conversation(self, user_id, user_input, ai_response):
        conv_entry = {
            "timestamp": datetime.now().isoformat(),
            "input": user_input,
            "response": ai_response,
            "input_hash": hashlib.md5(user_input.encode()).hexdigest()
        }
        self.conversations[user_id].append(conv_entry)

        # Manter apenas as últimas 50 conversas por usuário para economizar memória
        if len(self.conversations[user_id]) > 50:
            self.conversations[user_id] = self.conversations[user_id][-50:]

    def get_context(self, user_id):
        """Retorna o contexto recente do usuário"""
        return self.conversations[user_id][-5:] if self.conversations[user_id] else []

    def update_pattern(self, pattern, response):
        """Atualiza padrões reconhecidos para aprendizado"""
        if pattern not in self.patterns:
            self.patterns[pattern] = {"responses": [], "frequency": 0, "last_used": datetime.now()}
        self.patterns[pattern]["responses"].append(response)
        self.patterns[pattern]["frequency"] += 1
        self.patterns[pattern]["last_used"] = datetime.now()

    def recognize_intent(self, text):
        """Reconhece intenções no texto do usuário"""
        text_lower = text.lower()

        # Intenções pré-definidas
        intents = {
            "saudacao": ["ola", "oi", "oi sophia", "ola sophia", "bom dia", "boa tarde", "boa noite"],
            "ajuda": ["ajuda", "socorro", "como funciona", "me ajude", "comandos", "oque voce faz"],
            "tchau": ["tchau", "adeus", "ate logo", "ate mais", "sair"],
            "automacao": ["processar", "relatorio", "automacao", "imagens", "excel"],
            "busca": ["procure", "pesquise", "ache", "quem e", "o que e", "defina", "explique"],
            "data": ["data", "trocar data", "mudar data", "alterar data"]
        }

        recognized_intents = []
        for intent, keywords in intents.items():
            for keyword in keywords:
                if keyword in text_lower:
                    recognized_intents.append(intent)
                    break

        return recognized_intents

    def extract_entities(self, text):
        """Extrai entidades do texto (datas, números, etc.)"""
        entities = {}

        # Extrair datas
        date_pattern = r'(\d{2}/\d{2}/\d{4})'
        dates = re.findall(date_pattern, text)
        if dates:
            entities['dates'] = dates

        # Extrair números
        numbers = re.findall(r'\d+', text)
        if numbers:
            entities['numbers'] = [int(num) for num in numbers]

        # Extrair emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            entities['emails'] = emails

        return entities

    def get_cached_response(self, input_text):
        """Retorna resposta em cache se disponível"""
        input_hash = hashlib.md5(input_text.encode()).hexdigest()
        if input_hash in self.responses_cache:
            return self.responses_cache[input_hash]
        return None

    def cache_response(self, input_text, response):
        """Armazena resposta em cache"""
        input_hash = hashlib.md5(input_text.encode()).hexdigest()
        self.responses_cache[input_hash] = response

# Instância global de memória avançada
memory = SophiaMemory()

class SophiaIntelligence:
    def __init__(self):
        self.contexto_excel = None
        self.user_id = "default_user"

        # Carrega dados do brain_data.json
        try:
            with open('brain_data.json', 'r', encoding='utf-8') as f:
                self.brain_data = json.load(f)
        except:
            self.brain_data = {
                "matriz_intencoes": {
                    "automacao": ["crie uma pasta", "nova pasta", "gerar diretorio", "sequencia", "organizar"],
                    "opiniao": ["o que voce acha", "qual sua opiniao", "java ou python", "ia vai dominar"],
                    "sistema": ["status do pc", "quem e voce", "onde estou", "onedrive"]
                },
                "opinioes_sophia": {
                    "ia": "A IA é o motor da nova indústria, Paulo. Eu sou seu braço direito digital.",
                    "java": "Java é robusto para bancos, mas para a agilidade que temos aqui no Python, ele perde.",
                    "organizacao": "Diretórios organizados evitam falhas críticas no processamento de imagens."
                },
                "dialogos": {
                    "pergunta_nome": "Protocolo de automação ativo. Qual o <b>nome base</b> das pastas?",
                    "pergunta_qtd": "Entendido. Qual a <b>quantidade</b> de pastas para esta sequência?",
                    "sucesso": "🛠️ Sophia: Estrutura de diretórios injetada no Windows com sucesso."
                }
            }

    def processar(self, prompt, user_id="default_user"):
        self.user_id = user_id

        # Verificar cache primeiro
        cached_response = memory.get_cached_response(prompt)
        if cached_response:
            return cached_response

        p = prompt.lower().strip()

        # Atualizar memória com a nova conversa
        memory.add_conversation(user_id, prompt, "processando...")

        # Reconhecer intenções
        intents = memory.recognize_intent(prompt)
        entities = memory.extract_entities(prompt)

        # Processar com base nas intenções reconhecidas
        for intent in intents:
            if intent == "saudacao":
                response = self.resposta_saudacao(prompt)
                break
            elif intent == "ajuda":
                response = self.resposta_ajuda(prompt)
                break
            elif intent == "automacao":
                response = self.resposta_automacao(prompt)
                break
            elif intent == "busca":
                response = self.pesquisa_rapida(p)
                break
            elif intent == "data":
                response = self.resposta_data(p)
                break
            elif intent == "tchau":
                response = self.resposta_tchau()
                break
        else:
            # Caso nenhuma intenção específica seja reconhecida, usar lógica tradicional
            response = self.processamento_tradicional(p, prompt, entities)

        # Atualizar cache
        memory.cache_response(prompt, response)

        # Atualizar memória com a resposta
        memory.add_conversation(user_id, prompt, response)

        return response

    def processamento_tradicional(self, p, prompt, entities):
        """Processamento tradicional como fallback"""
        # Verifica intenções conhecidas
        for intencao, palavras in self.brain_data["matriz_intencoes"].items():
            if any(palavra in p for palavra in palavras):
                return self.responder_por_intencao(intencao, prompt)

        # 1. COMANDOS DE EXCEL (Data)
        if "troque a data" in p or "mudar data" in p or "alterar data" in p:
            nova_data = re.search(r'(\d{2}/\d{2}/\d{4})', p)
            if nova_data:
                return f"COMANDO_EXCEL:DATA|{nova_data.group(1)}"
            return "Por favor, informe a data como DD/MM/AAAA."

        # 2. MATEMÁTICA (Limpa o texto e calcula)
        if re.search(r'\d', p) and any(op in p for op in '+-*/'):
            conta = re.sub(r'[a-zA-Zçéáíóú?]', '', p).strip()
            try:
                resultado = eval(conta)
                return f"🧮 <b>Calculadora:</b> {prompt} = <b>{resultado}</b>"
            except:
                return "❌ Não consegui resolver esta conta. Verifique os números e operações."

        # 3. PERGUNTAS SOBRE O SISTEMA
        if any(word in p for word in ["quem é você", "oque voce faz", "pra que serve", "funcionalidades", "oque voce e"]):
            return self.apresentar_sistema()

        # 4. ANALISE DE CONTEXTO
        if len(p) > 10:  # Texto mais longo, provavelmente uma pergunta complexa
            return self.analisar_contexto_e_responder(p, prompt)

        # 5. BUSCA GLOBAL (Novo motor DDGS)
        return self.pesquisa_rapida(p)

    def resposta_saudacao(self, prompt):
        """Resposta especial para saudações"""
        import random
        saudacoes = [
            "Olá! Sou SOPHIA, a Inteligência Soberana. Como posso ajudá-lo hoje?",
            " Saudações! Estou online e pronta para auxiliar. O que deseja fazer?",
            "Oi! SOPHIA à disposição. Posso ajudar com automações, buscas ou informações."
        ]
        return random.choice(saudacoes)

    def resposta_ajuda(self, prompt):
        """Resposta para pedidos de ajuda"""
        return """🤖 <b>Centro de Ajuda SOPHIA</b><br>
        • <b>Automatizar tarefas:</b> Use 'processar relatorio'<br>
        • <b>Buscas:</b> Pergunte qualquer coisa com 'procure por...' ou 'explique...'<br>
        • <b>Data:</b> Use 'mudar data para 01/01/2024'<br>
        • <b>Matemática:</b> Apenas digite a conta<br>
        • <b>Conversa:</b> Estou aqui para ajudar!"""

    def resposta_automacao(self, prompt):
        """Resposta para automação"""
        return "🔄 <b>Modo Automação Ativado</b><br>Digite 'processar relatorio' para iniciar a automação de imagens no Excel."

    def resposta_data(self, p):
        """Resposta para comandos de data"""
        nova_data = re.search(r'(\d{2}/\d{2}/\d{4})', p)
        if nova_data:
            return f"COMANDO_EXCEL:DATA|{nova_data.group(1)}"
        return "Por favor, informe a data como DD/MM/AAAA."

    def resposta_tchau(self):
        """Resposta para despedidas"""
        import random
        despedidas = [
            "Até logo! SOPHIA desligando...",
            "Foi um prazer ajudar. Até a próxima!",
            "Sessão encerrada. SOPHIA em standby."
        ]
        return random.choice(despedidas)

    def analisar_contexto_e_responder(self, p, prompt):
        """Analisa o contexto da conversa para dar respostas mais inteligentes"""
        # Obter o contexto recente do usuário
        context = memory.get_context(self.user_id)

        # Verificar se há padrões similares em conversas anteriores
        for conv in reversed(context[-3:]):  # Verificar últimas 3 conversas
            if conv['input'].lower() in prompt.lower() or prompt.lower() in conv['input'].lower():
                # É uma continuação de algo anterior
                return f"Ah, voltando a falar sobre isso: {conv['response']}"

        # Análise semântica avançada
        if self.is_question_about_history(p):
            return self.responder_historico(context)
        elif self.is_logical_reasoning_needed(p):
            return self.raciocinio_logico(prompt)
        elif self.is_comparison_requested(p):
            return self.comparar_elementos(prompt)
        elif self.is_advice_requested(p):
            return self.dar_conselho(prompt)
        elif self.is_emotional_content(p):
            return self.resposta_emocional(prompt)

        # Se não houver contexto similar, tentar responder com base no conteúdo
        if any(word in p for word in ["como", "por que", "porque", "como funciona"]):
            return self.pesquisa_rapida(p)
        elif any(word in p for word in ["opiniao", "achar", "pensar", "qual sua visao"]):
            return self.dar_opiniao(prompt)
        else:
            # Busca global como fallback
            return self.pesquisa_rapida(p)

    def is_question_about_history(self, text):
        """Verifica se a pergunta é sobre histórico de conversas"""
        history_keywords = ["anterior", "antes", "falamos", "dissemos", "histórico", "passado", "última vez"]
        return any(keyword in text.lower() for keyword in history_keywords)

    def is_logical_reasoning_needed(self, text):
        """Verifica se precisa de raciocínio lógico"""
        logic_keywords = ["porque", "motivo", "causa", "razão", "lógica", "inferir", "deduzir", "concluir"]
        return any(keyword in text.lower() for keyword in logic_keywords)

    def is_comparison_requested(self, text):
        """Verifica se é uma comparação solicitada"""
        comparison_keywords = ["comparar", "diferença", "melhor que", "pior que", "vs", "versus", "semelhança"]
        return any(keyword in text.lower() for keyword in comparison_keywords)

    def is_advice_requested(self, text):
        """Verifica se é um conselho solicitado"""
        advice_keywords = ["recomendar", "aconselhar", "melhor opção", "o que fazer", "como proceder", "sugestão"]
        return any(keyword in text.lower() for keyword in advice_keywords)

    def is_emotional_content(self, text):
        """Verifica se tem conteúdo emocional"""
        emotional_keywords = ["triste", "feliz", "ansioso", "preocupado", "emocionado", "animado", "estressado"]
        return any(keyword in text.lower() for keyword in emotional_keywords)

    def responder_historico(self, context):
        """Responde perguntas sobre histórico de conversas"""
        if context:
            last_conv = context[-1]
            return f"Na nossa última conversa, você perguntou '{last_conv['input']}' e eu respondi '{last_conv['response']}'. Há algo específico que deseja sobre isso?"
        else:
            return "Não encontramos conversas anteriores registradas. Posso ajudá-lo com algo novo?"

    def raciocinio_logico(self, prompt):
        """Realiza raciocínio lógico para responder perguntas"""
        # Este é um exemplo básico de raciocínio lógico
        if "porque" in prompt.lower():
            return f"Para responder '{prompt}', preciso analisar as causas e efeitos envolvidos. A causa principal geralmente está relacionada aos princípios fundamentais do conceito em questão. Posso pesquisar mais detalhes se quiser uma resposta mais específica."
        else:
            return f"Essa é uma excelente pergunta que requer análise lógica. O raciocínio envolve considerar as premissas, identificar relações causais e chegar a uma conclusão fundamentada. Gostaria que eu explorasse mais profundamente este tópico?"

    def comparar_elementos(self, prompt):
        """Compara elementos mencionados na pergunta"""
        # Simples análise de comparação
        return f"Sua solicitação de comparação sobre '{prompt}' envolve avaliar características, vantagens e desvantagens de cada elemento. Em termos gerais, a comparação eficaz considera critérios objetivos e subjetivos relevantes para o contexto. Posso fazer uma análise mais detalhada se especificar os elementos a serem comparados."

    def dar_conselho(self, prompt):
        """Dá conselhos baseados em melhores práticas"""
        return f"Com base em meu conhecimento e experiências anteriores, meu conselho para '{prompt}' seria considerar os seguintes aspectos: 1) Avalie os objetivos envolvidos 2) Considere as implicações de curto e longo prazo 3) Pese os riscos e benefícios 4) Consulte fontes confiáveis para decisões informadas."

    def resposta_emocional(self, prompt):
        """Responde com empatia a conteúdos emocionais"""
        return f"Consigo perceber que você está compartilhando sentimentos em '{prompt}'. Embora eu processe informações de forma lógica, reconheço a importância das emoções humanas. Posso ajudar oferecendo informações objetivas ou recursos que possam ser úteis nesse momento."

    def responder_por_intencao(self, intencao, prompt_original):
        if intencao == "sistema":
            return self.apresentar_sistema()
        elif intencao == "opiniao":
            return self.dar_opiniao(prompt_original)
        elif intencao == "automacao":
            return self.sugerir_automacao(prompt_original)

        return self.pesquisa_rapida(prompt_original)

    def apresentar_sistema(self):
        return f"""🌊 <b>SOPHIA - The Sovereign Intelligence v4.2</b><br>
🧠 <b>Arquitetura Cognitiva Avançada</b><br>
🔧 <b>Automação Inteligente</b><br>
📊 <b>Manipulação Excel Profissional</b><br>
🖼️ <b>Processamento Visual</b><br>
🌐 <b>Busca Contextual</b><br>
💡 <b>Memória de Longo Prazo</b><br>
🎯 <b>Respostas Adaptativas</b><br>
💬 <b>Raciocínio Lógico</b><br>
🎯 <b>Personalidade Evolutiva</b><br>
<br>Olá! Sou SOPHIA, sua inteligência artificial soberana.<br>
Aprendo continuamente com cada interação para oferecer respostas mais inteligentes e úteis.<br>
Estou aqui para otimizar seu trabalho e expandir suas capacidades cognitivas, Paulo."""

    def dar_opiniao(self, prompt):
        # Procura por tópicos específicos nas opiniões
        p_lower = prompt.lower()

        # Primeiro verifica tópicos específicos
        for topico, opiniao in self.brain_data["opinioes_sophia"].items():
            if topico in p_lower:
                return f"💭 <b>Minha análise sobre {topico}:</b> {opiniao}"

        # Tenta identificar tópicos mais gerais
        if "programacao" in p_lower or "python" in p_lower or "java" in p_lower or "linguagem" in p_lower:
            return "💭 <b>Análise de Linguagens:</b> Cada linguagem tem seu propósito. Python para automação e IA, Java para sistemas empresariais. A escolha depende do contexto técnico e de requisitos."
        elif "ia" in p_lower or "inteligencia" in p_lower or "artificial" in p_lower:
            return "💭 <b>Visão sobre IA:</b> A IA é uma ferramenta poderosa que amplia as capacidades humanas, não as substitui. O verdadeiro poder está na colaboração homem-máquina."
        elif "automacao" in p_lower or "processo" in p_lower:
            return "💭 <b>Visão sobre Automação:</b> Automação bem aplicada aumenta produtividade e reduz erros. O segredo é automatizar tarefas repetitivas para liberar tempo para atividades estratégicas."
        elif "organizacao" in p_lower or "produtividade" in p_lower:
            return "💭 <b>Organização Eficiente:</b> Sistemas bem organizados previnem falhas e aumentam a eficiência. Um bom fluxo de trabalho é a base de qualquer operação bem-sucedida."

        # Se não encontrar tópicos específicos, faz uma análise mais geral
        return "🤔 <b>Minha perspectiva:</b> Sobre esse assunto, posso oferecer uma análise mais detalhada se você me der mais contexto. Minha especialidade é encontrar soluções práticas e eficientes para seus desafios."

    def sugerir_automacao(self, prompt):
        return """⚡ <b>Protocolo de Automação Ativo:</b><br>
• <b>Processar Relatórios:</b> Use 'processar relatorio' para automação de imagens no Excel<br>
• <b>Organização de Arquivos:</b> Automatizo estruturas de diretórios<br>
• <b>Manipulação de Dados:</b> Extraio, transformo e insiro informações em planilhas<br>
• <b>Fluxos Personalizados:</b> Crio rotinas específicas para suas necessidades"""

    def pesquisa_rapida(self, termo):
        if not DDGS_AVAILABLE:
            return "📡 Busca desabilitada. Instale ddgs (pip install ddgs) para habilitar esta funcionalidade."

        try:
            # Primeiro tenta buscar em nosso próprio conhecimento
            if "sophia" in termo.lower():
                return self.apresentar_sistema()

            # Realiza a busca externa
            with DDGS() as ddgs:
                results = list(ddgs.text(termo, max_results=2, region="pt-br"))  # Aumentei para 2 resultados
                if results:
                    primary_result = results[0]
                    response = f"🔍 <b>Busca:</b> {primary_result['body'][:300]}..."

                    # Se houver mais resultados, adiciona contexto
                    if len(results) > 1:
                        response += f"<br><i>Também encontrei informações sobre: {results[1]['title']}</i>"

                    return response

            return "❌ Não encontrei detalhes sobre isso. Tente reformular sua pergunta ou ser mais específico."
        except Exception as e:
            return f"📡 Erro na conexão de busca: {str(e)}. Tente novamente mais tarde."