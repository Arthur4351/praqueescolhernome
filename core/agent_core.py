import json
import gc
import os
from pathlib import Path
from core.file_handler import FileHandler
from core.metadata_inspector import MetadataInspector
from core.excel_engine import ExcelEngine

class SophiaAgentCore:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.keywords = self.config.get("sinonimos_atividade", ["atividade", "servico"])
        self.groq_api_key = self.config.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        from core.intent_parser import IntentParser
        self.nlp = IntentParser()
        self.pending_intents = []
        self.args = {}
        self._query_params_pending = None
        self.auto_execute = False
        self._SAFE_INTENTS = {
            "CREATE_FOLDER", "RENAME_FOLDER", "MOVE_FOLDER",
            "INJECT_FORMULA", "QUERY_EXCEL", "QUERY_COUNT_EMPTY",
            "GENERATE_NEW_SKILL", "EDIT_PROJECT_FILE",
            "FORMAT_EXCEL_COLUMNS", "IMPROVE_EXCEL_SENIOR",
            "PROCESSAR_FOTOS", "DATAS", "UPDATE_WHATSAPP", 
            "CONFIGURAR_PADRAO_FOTOS", "REGISTRAR_FATO_LTM", "RUN_AGENT_SKILL"
        }

    def _load_config(self) -> dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as err_log:
                err_log.write(f"AgentCore: Erro carregando {self.config_path} - {e}\n")
            return {"sinonimos_atividade": ["atividade", "servico", "entrada", "saida"]}

    def update_context(self, **kwargs):
        """Wrapper público para atualizar o contexto do NLP sem expor self.nlp."""
        self.nlp.update_context(**kwargs)

    def perform_dry_run_scan(self, target_directory: str) -> str:
        """Escaneia a pasta e retorna um relatorio (Dry Run) sem alterar nada."""
        try:
            report = ["=== SOPHIA DRY RUN REPORT ==="]
            report.append(f"Alvo: {target_directory}\n")
            matched_files = FileHandler.scan_directory(target_directory, self.keywords)
            if not matched_files:
                return "Nenhum arquivo relevante encontrado na varredura."
            report.append(f"Encontrei {len(matched_files)} arquivos relevantes:\n")
            for file in matched_files:
                ext = file.suffix.lower()
                if ext in ['.jpg', '.jpeg', '.png']:
                    info = MetadataInspector.extract_full_metadata(str(file))
                    report.append(f"[IMAGEM] {file.name} | Data: {info['data']} | Cam: {info['camera']}")
                elif ext in ['.xlsx', '.xls', '.xlsm']:
                    has_cols = ExcelEngine.validate_main_columns(file, self.keywords)
                    status = "VALIDO (Colunas Identificadas)" if has_cols else "ATENCAO (Colunas Ausentes)"
                    report.append(f"[EXCEL] {file.name} | Estrutura: {status}")
                else:
                    report.append(f"[OUTRO] {file.name}")
            report.append("\nEu pretendo processar estes itens baseada nas diretrizes atuais. Confirma?")
            return "\n".join(report)
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as err_log:
                err_log.write(f"AgentCore: Falha Critica no Dry Run - {e}\n")
            return "Erro critico durante varredura. Detalhes salvos no log."

    def evaluate_chat(self, user_input: str, user_name: str = "Usuário") -> str:
        """Avalia a conversa via NLP nativo e gera o prompt de Dry Run agrupado para a fila."""
        self.pending_intents = []
        parsed_list = self.nlp.parse_multiple_intents(user_input, user_name)
        from core.response_generator import ResponseGenerator

        actions = [p for p in parsed_list if p["status"] in ("DETECTED", "DETECTED_CLOUD")]
        conversations = [p for p in parsed_list if p["status"] == "CONVERSATIONAL"]

        if actions and actions[0]["intent"] in ("QUERY_EXCEL", "QUERY_COUNT_EMPTY"):
            tipo = actions[0]["intent"]
            params = {"tipo": tipo}
            if "alvo" in actions[0]: params["alvo"] = actions[0]["alvo"]
            if "coluna_desejada" in actions[0]: params["coluna_desejada"] = actions[0]["coluna_desejada"]
            if "coluna" in actions[0]: params["coluna"] = actions[0]["coluna"]
            if len(params) == 1:
                local_params = self.nlp.extract_query_params(user_input)
                params.update(local_params)
            if tipo == "QUERY_EXCEL":
                alvo = params.get("alvo", "")
                coluna = params.get("coluna_desejada", "")
                if alvo and coluna:
                    self._query_params_pending = params
                    return f"🔍 <b>SOPHIA:</b> Beleza, procurando por '<b>{alvo}</b>' para achar a '<b>{coluna}</b>'. Aponta a planilha na janela que vou abrir."
                return "⚠️ SOPHIA: O que exatamente você quer buscar na planilha? Faltou parâmetros."
            elif tipo == "QUERY_COUNT_EMPTY":
                coluna = params.get("coluna", "")
                if coluna:
                    self._query_params_pending = params
                    return f"📊 <b>SOPHIA:</b> Vou contar tudo que falta na '<b>{coluna}</b>'. Aponta a planilha."
                return "⚠️ SOPHIA: E qual coluna é pra contar? Ex: 'quantos dias sem fotos'."

        if not actions and conversations:
            if "resposta" in conversations[0]:
                resp = conversations[0]['resposta']
                if resp.upper().startswith("SOPHIA:"):
                    resp = resp[7:].strip()
                return f"SOPHIA: {resp}"
            return ResponseGenerator.generate(conversations[0]["intent"], user_name, raw_input=user_input)

        if not actions and not conversations:
            return "SOPHIA: Não entendi o comando. Posso consultar planilhas ('acha X e me diz Y'), processar pastas, ou conversar!"

        self.pending_intents = actions

        # Modo Autônomo: executa direto se a intent é segura e tem boa confiança
        if actions:
            all_safe = all(a["intent"] in self._SAFE_INTENTS for a in actions)
            has_cloud = any(a.get("status") == "DETECTED_CLOUD" for a in actions)
            high_confidence = any(a.get("score", 0) >= 0.4 for a in actions)
            self.auto_execute = all_safe and (has_cloud or high_confidence)
        else:
            self.auto_execute = False

        if len(actions) == 1:
            if "resposta" in actions[0]:
                resp = actions[0]['resposta']
                if resp.upper().startswith("SOPHIA:"):
                    resp = resp[7:].strip()
                return f"SOPHIA: {resp}"
            intent = actions[0]["intent"]
            if self.auto_execute:
                return f"SOPHIA: Certo, executando [{intent}] agora..."
            return f"SOPHIA: Entendi que é para executar [{intent}]. Posso fazer isso?"

        report = ["<b>SOPHIA:</b> Detectei um combo de ações. Vou rodar na seguinte ordem:"]
        for idx, act in enumerate(actions):
            report.append(f"{idx+1}) {act['intent']}")
        if self.auto_execute:
            report.append("<br>Executando o lote automaticamente...")
        else:
            report.append("<br>A RAM tá pronta. Posso dar o play?")
        return "<br>".join(report)


    def execute_pending_intents(self, global_args: dict = None) -> str:
        """Executa fisicamente a fila de intenções após confirmação."""
        if not self.pending_intents:
            return "Nenhuma acao pendente."

        if global_args is None:
            global_args = {}

        from core.response_generator import ResponseGenerator
        resultados = []

        try:
            for item in self.pending_intents:
                intent = item["intent"]

                # R2 CORRIGIDO: global_args tem PRIORIDADE sobre contexto NLP
                # Contexto serve como fallback, não como override
                contexto = self.nlp.contexto_ativo
                args = {**contexto, **global_args}

                if intent == "CREATE_FOLDER":
                    base = args.get("base_path", ".")
                    nome = args.get("folder_name", "NovaPasta")
                    subs = args.get("subfolders", None)
                    sucesso = FileHandler.create_folder(base, nome, subs)
                    if sucesso:
                        new_path = str(Path(base) / nome)
                        self.nlp.update_context(ultimo_diretorio=new_path)
                    else:
                        raise Exception(f"Falha ao criar diretório raiz {nome} em {base}")

                elif intent == "RENAME_FOLDER":
                    # R1 CORRIGIDO: agora chama rename_folder que realmente existe
                    FileHandler.rename_folder(args.get("target_path", "."), args.get("new_name", "NovoNome"))

                elif intent == "DELETE_FOLDER":
                    FileHandler.delete_folder(args.get("target_path", "."))

                elif intent == "MOVE_FOLDER":
                    src = args.get("source_path") or args.get("ultimo_arquivo") or args.get("ultimo_diretorio") or "."
                    dest = args.get("dest_path", ".")
                    FileHandler.move_folder(src, dest)

                elif intent == "INJECT_FORMULA":
                    cell = args.get("cell") or args.get("cell_coord")
                    ExcelEngine.inject_formula(args.get("excel_path"), args.get("sheet_name"), cell, args.get("formula"))

                elif intent == "EDIT_PROJECT_FILE":
                    from core.dynamic_coder import DynamicCoder
                    coder = DynamicCoder(self.groq_api_key)
                    target_file = args.get("file", item.get("file", ""))
                    prompt = args.get("prompt", item.get("prompt", ""))
                    res_edit = coder.edit_project_file(target_file, prompt)
                    resultados.append(f"Ação [EDIT_PROJECT_FILE] -> {res_edit}")
                    continue

                elif intent == "GENERATE_NEW_SKILL":
                    from core.dynamic_coder import DynamicCoder
                    coder = DynamicCoder(self.groq_api_key)
                    prompt = args.get("prompt", item.get("prompt", "Automação Python Genérica"))
                    res_dyn = coder.generate_and_run(prompt, args)
                    resultados.append(f"Ação [GENERATE_NEW_SKILL] -> {res_dyn}")
                    continue

                elif intent == "RUN_AGENT_SKILL":
                    from core.dynamic_coder import DynamicCoder
                    coder = DynamicCoder(self.groq_api_key)
                    skill_name = args.get("skill", item.get("skill", ""))
                    prompt = args.get("prompt", item.get("prompt", "Use a habilidade para resolver a tarefa."))
                    
                    skill_file = Path(os.path.dirname(os.path.dirname(__file__))) / ".agent" / "skills" / skill_name / "SKILL.md"
                    skill_content = ""
                    if skill_file.exists():
                        try:
                            skill_content = skill_file.read_text(encoding="utf-8")
                        except: pass
                    
                    full_prompt = f"Você deve utilizar as instruções e princípios desta Habilidade Especializada:\n\n{skill_content}\n\nTarefa do usuário: {prompt}" if skill_content else prompt
                    res_dyn = coder.generate_and_run(full_prompt, args)
                    resultados.append(f"Ação [RUN_AGENT_SKILL ({skill_name})] -> {res_dyn}")
                    continue

                elif intent == "CONFIGURAR_PADRAO_FOTOS":
                    try:
                        regras_raw = args.get("regras", item.get("regras", "{}"))
                        regras = {}
                        if isinstance(regras_raw, str):
                            import json
                            try:
                                regras = json.loads(regras_raw.replace("'", '"'))
                            except:
                                import ast
                                try: regras = ast.literal_eval(regras_raw)
                                except: pass
                        elif isinstance(regras_raw, dict):
                            regras = regras_raw
                        
                        if not regras:
                            raise Exception("Não consegui extrair regras válidas da sua frase.")

                        # Mescla com os padrões já existentes em vez de sobrescrever tudo
                        padroes_atuais = self.config.get("padroes_fotos", {})
                        padroes_atuais.update(regras)
                        self.config["padroes_fotos"] = padroes_atuais
                        
                        with open(self.config_path, 'w', encoding='utf-8') as f:
                            json.dump(self.config, f, indent=4, ensure_ascii=False)
                        
                        resultados.append(f"✅ Padrão de fotos aprendido! Agora eu sei: {regras}")
                    except Exception as e:
                        resultados.append(f"❌ Falha ao aprender padrão: {e}")
                    continue

                resultados.append(f"Ação [{intent}] ✓")

            self.pending_intents = []
            self.args.clear()
            self.nlp.clear_context()
            gc.collect()

            return "✅ Lote executado com sucesso e memória limpa: " + " | ".join(resultados)

        except Exception as e:
            self.pending_intents = []
            self.args.clear()
            self.nlp.clear_context()
            return ResponseGenerator.generate_error(f"executar fila de ações", str(e))
