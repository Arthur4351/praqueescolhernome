import json
from pathlib import Path
from core.file_handler import FileHandler
from core.metadata_inspector import MetadataInspector
from core.excel_engine import ExcelEngine

class SophiaAgentCore:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.keywords = self.config.get("sinonimos_atividade", ["atividade", "servico"])
        from core.intent_parser import IntentParser
        self.nlp = IntentParser()
        self.pending_intent = None
        
    def _load_config(self) -> dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as err_log:
                err_log.write(f"AgentCore: Erro carregando {self.config_path} - {e}\n")
            return {"sinonimos_atividade": ["atividade", "servico", "entrada", "saida"]}

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
            return f"Erro critico durante varredura. Detalhes salvos no log."

    def evaluate_chat(self, user_input: str, user_name: str = "Usuário") -> str:
        """Avalia a conversa via NLP nativo e gera o prompt de Dry Run agrupado para a fila."""
        self.pending_intents = [] # Reset on new evaluation
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
        
        if len(actions) == 1:
            if "resposta" in actions[0]:
                resp = actions[0]['resposta']
                if resp.upper().startswith("SOPHIA:"):
                    resp = resp[7:].strip()
                return f"SOPHIA: {resp}"
                
            intent = actions[0]["intent"]
            return f"SOPHIA: Entendi que é para executar [{intent}]. Posso fazer isso?"
        
        report = ["<b>SOPHIA:</b> Detectei um combo de ações para a engine. Vou rodar na seguinte ordem:"]
        for idx, act in enumerate(actions):
            report.append(f"{idx+1}) {act['intent']}")
        report.append("<br>A RAM tá pronta. Posso dar o play?")
        
        return "<br>".join(report)

    def execute_pending_intents(self, global_args: dict = None) -> str:
        """Executa fisicamente a fila de intenções após confirmação e invoca gc.collect()"""
        if not hasattr(self, 'pending_intents') or not self.pending_intents:
            return "Nenhuma acao pendente."
            
        if global_args is None: global_args = {}
        
        from core.response_generator import ResponseGenerator
        resultados = []
        
        try:
            for item in self.pending_intents:
                intent = item["intent"]
                
                contexto = self.nlp.contexto_ativo
                args = {**global_args, **contexto}
                
                if intent == "CREATE_FOLDER":
                    base = args.get("base_path", ".")
                    nome = args.get("folder_name", "NovaPasta")
                    new_path = FileHandler.create_folder(base, nome)
                    self.nlp.update_context(ultimo_diretorio=new_path)
                    
                elif intent == "RENAME_FOLDER":
                    FileHandler.rename_folder(args.get("target_path", "."), args.get("new_name", "NovoNome"))
                    
                elif intent == "DELETE_FOLDER":
                    FileHandler.delete_folder(args.get("target_path", "."))
                    
                elif intent == "MOVE_FOLDER":
                    src = args.get("source_path") or args.get("ultimo_arquivo") or args.get("ultimo_diretorio") or "."
                    dest = args.get("dest_path", ".")
                    FileHandler.move_folder(src, dest)
                    
                elif intent == "INJECT_FORMULA":
                    ExcelEngine.inject_formula(args.get("excel_path"), args.get("sheet_name"), args.get("cell"), args.get("formula"))
                
                resultados.append(f"Ação [{intent}] ✓")
            
            self.pending_intents = []
            self.nlp.clear_context()
            import gc
            gc.collect() # Respeito absoluto ao hardware
            
            return "✅ Lote executado com sucesso e memória limpa: " + " | ".join(resultados)
            
        except Exception as e:
            self.pending_intents = []
            self.nlp.clear_context()
            return ResponseGenerator.generate_error(f"executar fila de ações", str(e))
