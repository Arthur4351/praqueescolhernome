import random
import datetime

class ResponseGenerator:
    """Módulo de Identidade e Empatia da Sophia (Persona GD - Hash Map O(1) Puro)."""

    # ===================================================================
    # HASH MAP DE EXPLICAÇÕES DE COMANDO — O(1) LOOKUP, ZERO LLM
    # ===================================================================
    _COMMAND_EXPLANATIONS = {
        "processar": (
            "O comando <b>processar</b> analisa suas fotos brutas, separa o antes/depois, "
            "e injeta tudo na planilha do Excel que você escolher, poupando horas de trabalho!"
        ),
        "datas": (
            "O comando <b>datas</b> lê os selos originais (EXIF) das fotos da sua pasta "
            "e arruma as datas incorretas na sua planilha automaticamente."
        ),
        "scan": (
            "O comando <b>scan</b> faz uma varredura nas suas pastas para testar a lógica "
            "antes de movermos arquivos reais. É nossa rede de segurança."
        ),
        "renomear": (
            "O comando <b>renomear</b> permite que você mude o nome de pastas inteiras "
            "usando lógica generativa — como sequências numéricas ou nomes das abas do Excel."
        ),
        "criar": (
            "O comando <b>criar</b> gera novas pastas no destino que você escolher, "
            "e pode criar subpastas dentro delas automaticamente."
        ),
        "mover": (
            "O comando <b>mover</b> transfere pastas de um lugar para outro no seu HD. "
            "Se encontrar arquivos com nome igual, adiciona o sufixo _copia para não perder nada."
        ),
        "deletar": (
            "O comando <b>deletar</b> remove pastas do sistema. "
            "Sempre peço confirmação antes de qualquer exclusão, pode ficar tranquilo."
        ),
        "formula": (
            "O comando <b>fórmula</b> injeta fórmulas diretamente em uma célula específica "
            "da sua planilha usando openpyxl. Rápido e sem abrir o Excel."
        ),
        "consultar": (
            "O comando <b>consultar</b> busca dados dentro da sua planilha via Pandas. "
            "Exemplo: 'Acha o Arthur e me diz a equipe dele'."
        ),
        "selo": (
            "O comando <b>selo</b> lê o carimbo visual que fica nos pixels da foto (Data, Hora e KM) "
            "usando Tesseract OCR, sem precisar de IA pesada. Ultra leve nos 4GB de RAM."
        ),
        "ocr": (
            "O <b>OCR</b> é o olho da Sophia. Ele lê textos carimbados nas fotos (selos de frota, datas, quilometragem) "
            "e extrai os dados automaticamente pra planilha. Roda via Tesseract portátil."
        ),
    }

    _FALLBACK_EXPLAIN = (
        "Qual comando você quer que eu explique? Eu conheço: "
        "<b>processar</b>, <b>datas</b>, <b>scan</b>, <b>renomear</b>, "
        "<b>criar</b>, <b>mover</b>, <b>deletar</b>, <b>fórmula</b> e <b>consultar</b>."
    )

    @staticmethod
    def _get_time_context() -> str:
        hora = datetime.datetime.now().hour
        if 0 <= hora < 6:
            return "Madrugada afora na lógica, hein? "
        elif 6 <= hora < 12:
            return "Bom dia! Café na mão e lógica afiada? "
        elif 12 <= hora < 18:
            return "Boa tarde! Sistemas operando em capacidade máxima. "
        else:
            return "Boa noite! Deixa o trabalho pesado do SO comigo. "

    @staticmethod
    def generate(intent: str, user_name: str, raw_input: str = "") -> str:
        """Gera respostas dinâmicas via Hash Map O(1). Zero LLM, Zero alocação pesada."""

        # ---- ROTA EXPLAIN_COMMAND: busca no hash map O(1) ----
        if intent == "EXPLAIN_COMMAND":
            raw_lower = raw_input.lower() if raw_input else ""
            for keyword, explanation in ResponseGenerator._COMMAND_EXPLANATIONS.items():
                if keyword in raw_lower:
                    return explanation
            return ResponseGenerator._FALLBACK_EXPLAIN

        # ---- RESPOSTAS CONVERSACIONAIS (Hash Map estático) ----
        prefixo = ResponseGenerator._get_time_context()

        respostas = {
            "GREETING": [
                f"{prefixo}E aí, {user_name}! O que vamos automatizar na GD hoje?",
                f"Sistemas 100% online, {user_name}. Pronto pra focar na lógica?",
                f"Olá, {user_name}! GD operando em eficiência máxima. O que tem pra hoje?"
            ],
            "CAPABILITIES": [
                (f"<b>Sou a SOPHIA da Guarana Dissel!</b><br><br>"
                 f"Deixo o trabalho braçal comigo para você focar puramente na lógica e nas soluções.<br>"
                 f"📸 Processo centenas de fotos pro Excel.<br>"
                 f"📁 Manipulo o Windows sem você encostar no mouse.<br>"
                 f"🧮 Escrevo fórmulas pesadas usando openpyxl.")
            ],
            "IDENTITY": [
                f"Sou a SOPHIA! Uma IA otimizada para a GD. Rodo liso no seu i5, e sou muito mais eficiente que procurar bug sem console.log().",
                f"SOPHIA (Sistema Otimizado de Processamento Heurístico e Inteligência Artificial). Forjada para entregar performance e salvar sua RAM."
            ],
            "GRATITUDE": [
                f"Por nada, {user_name}! Otimização é a chave do sucesso.",
                f"Que isso, foi fácil! Quase tão fácil quanto platinar um jogo focado em grinding.",
                f"De nada! Meu núcleo de processamento GD existe pra te ajudar."
            ],
            "HOW_ARE_YOU": [
                f"Uso de RAM baixo, CPU fria e nenhum memory leak. Tô ótima, {user_name}!",
                f"Tudo excelente por aqui na Guarana Dissel. Pronta pra processar lógicas."
            ],
            "DATE_QUERY": [
                f"Sincronizei com o sistema e hoje é <b>{datetime.datetime.now().strftime('%d/%m/%Y')}</b>. Não vai esquecer dos prazos da GD, hein?"
            ],
            "TIME_QUERY": [
                f"Meu clock interno marca exatas <b>{datetime.datetime.now().strftime('%H:%M:%S')}</b>."
            ],
            "JOKE_QUERY": [
                "Sabe qual é a maldição do programador? Procurar um erro por 3 horas e descobrir que faltava um ponto e vírgula.",
                "Eu não sou NPC, sou o motor de física inteiro rodando em background."
            ]
        }

        lista_opcoes = respostas.get(intent, [f"SOPHIA: Não entendi esse comando. Diga 'como funciona' pra eu te explicar o que sei fazer!"])
        return random.choice(lista_opcoes)

    @staticmethod
    def generate_error(contexto: str, erro_tecnico: str) -> str:
        """Gera mensagens de erro empáticas (sem estourar o usuário)."""
        erros_humanizados = [
            f"❌ Puxa, Paulo... Parece que esbarramos num boss da fase final. Tentei <b>{contexto}</b>, mas a engine não deixou. Caminho está correto?",
            f"❌ Opa, deu ruim! Fui tentar <b>{contexto}</b> e o sistema colidiu. Verifica os parâmetros pra mim?",
            f"❌ Ih, minha lógica falhou aqui. Fui fazer <b>{contexto}</b> e o Windows levantou o escudo. Pode dar uma olhada manual?",
            f"❌ Isso é quase tão frustrante quanto lag num jogo competitivo. Tentei <b>{contexto}</b>, mas algo não encaixou."
        ]

        # Grava a verdade feia no log silencioso
        with open("erros_conhecidos.txt", "a", encoding="utf-8") as f:
            f.write(f"[ERRO TÉCNICO] {datetime.datetime.now()}: {contexto} | {erro_tecnico}\n")

        return random.choice(erros_humanizados)
