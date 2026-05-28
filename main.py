import sys
import os

# =========================================================================
# INTERCEPTADOR DE LINHA DE COMANDO (EMULADOR PYTHON / SANDBOX CORPORATIVO)
# =========================================================================
if len(sys.argv) > 1:
    # Caso 1: Compilação de código estática (-m py_compile arquivo.py)
    if len(sys.argv) > 3 and sys.argv[1] == "-m" and sys.argv[2] == "py_compile":
        _target_file = sys.argv[3]
        try:
            if os.path.exists(_target_file):
                with open(_target_file, "r", encoding="utf-8") as _f:
                    compile(_f.read(), _target_file, "exec")
                sys.exit(0)
            else:
                sys.stderr.write(f"Arquivo nao encontrado: {_target_file}\n")
                sys.exit(1)
        except Exception as _compile_err:
            sys.stderr.write(f"Erro de compilacao: {str(_compile_err)}\n")
            sys.exit(1)
            
    # Caso 2: Execução de script dinâmico gerado (arquivo.py)
    elif sys.argv[1].endswith(".py") and os.path.exists(sys.argv[1]):
        _script_path = sys.argv[1]
        try:
            with open(_script_path, "r", encoding="utf-8") as _f:
                _code_content = _f.read()
            # Ajusta os argumentos de sys.argv para o script filho
            sys.argv = [_script_path] + sys.argv[2:]
            # Adiciona o diretório do script ao path
            _script_dir = os.path.dirname(os.path.abspath(_script_path))
            if _script_dir not in sys.path:
                sys.path.insert(0, _script_dir)
            # Define o contexto global para execução
            _global_context = {
                "__file__": _script_path,
                "__name__": "__main__",
                "__package__": None,
            }
            import builtins
            _global_context.update(builtins.__dict__)
            exec(_code_content, _global_context)
            sys.exit(0)
        except Exception as _exec_err:
            import traceback
            traceback.print_exc()
            sys.exit(1)

import json
import ctypes
import getpass
from enum import Enum, auto
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

try:
    import pyi_splash
    pyi_splash.close()
except ImportError:
    pass

class AppStatus(Enum):
    LIVRE = auto()
    ESPERANDO_DRY_RUN = auto()
    CONFIRMANDO_CONTEUDO_PASTA = auto()
    ESPERANDO_NOME_CRIACAO = auto()
    ESPERANDO_SUBPASTAS_CRIACAO = auto()
    ESPERANDO_ESCOPO_RENOMEAR = auto()
    ESPERANDO_LOGICA_RENOMEAR = auto()
    ESPERANDO_ABA_EXCEL = auto()
    ESPERANDO_CEL_EXCEL = auto()
    ESPERANDO_FORMULA_EXCEL = auto()

myappid = 'meu.projeto.sophia.v1' 
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from minhas_habilidades import SophiaExecutor
    MODULOS_OK = True
except Exception as _e_mod:
    MODULOS_OK = False
    print(f"[SOPHIA] Módulo de habilidades offline: {_e_mod}")

try:
    from core.agent_core import SophiaAgentCore
    IA_OK = True
except Exception as _e_ia:
    IA_OK = False
    print(f"[SOPHIA] Agent Core offline: {_e_ia}")

try:
    from ui.components.orb import DataOrb
except Exception:
    DataOrb = None


class LightRefraction(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._pos_y = -100

    @Property(int)
    def posY(self): return self._pos_y
    @posY.setter
    def posY(self, val):
        self._pos_y = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, self._pos_y, 0, self._pos_y + 100)
        gradient.setColorAt(0, QColor(255, 255, 255, 0))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 40))
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(self.rect(), gradient)


class WorkerSignals(QObject):
    finished_signal = Signal(str)
    error_signal = Signal(str)
    log_signal = Signal(str)

class Worker(QRunnable):

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.signals = WorkerSignals()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.func(*self.args, **self.kwargs)
            if res is None: res = "Tarefa concluída silenciosamente."
            self.signals.finished_signal.emit(str(res))
        except Exception as e:
            self.signals.error_signal.emit(f"Erro Crítico na Thread: {e}")

class SophiaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user = getpass.getuser().capitalize()
        self.setWindowTitle("SOPHIA AI - Assistant Edition")
        self.resize(1000, 800)

        # Carrega configuração para modo autônomo
        autonomia = False
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as fc:
                    cfg = json.load(fc)
                    autonomia = cfg.get("autonomous_mode", False)
        except Exception:
            pass

        self.executor = SophiaExecutor(autonomous_mode=autonomia) if MODULOS_OK else None
        self.ai = SophiaAgentCore() if IA_OK else None
        self.estado_atual = AppStatus.LIVRE
        self.dados_pendentes = {}
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #E0FFFF; }
            QFrame#GlassPanel {
                background-color: rgba(255, 255, 255, 50);
                border: 1px solid rgba(255, 255, 255, 80);
                border-radius: 25px;
            }
            QTextEdit { background: transparent; border: none; color: #004d4d; font-size: 16px; }
            QLineEdit { background-color: rgba(255, 255, 255, 120); border-radius: 20px; padding: 15px; color: #004d4d; }
            QPushButton { background-color: #00838F; color: white; border-radius: 20px; padding: 10px 20px; font-weight: bold; }
        """)

        self.central_container = QWidget()
        self.setCentralWidget(self.central_container)
        layout = QVBoxLayout(self.central_container)
        layout.setContentsMargins(40, 40, 40, 40)

        if DataOrb:
            self.orb = DataOrb()
            layout.addWidget(self.orb, alignment=Qt.AlignCenter)

        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("GlassPanel")
        chat_layout = QVBoxLayout(self.chat_panel)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setHtml(f"<b>SOPHIA:</b> Sistema online, {self.current_user}. Comandos: 'processar', 'datas', ou 'scan'.")
        chat_layout.addWidget(self.chat_display)
        layout.addWidget(self.chat_panel, stretch=1)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Digite seu comando...")
        self.input_field.returnPressed.connect(self.enviar_comando)
        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self.enviar_comando)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        self.refraction = LightRefraction(self.central_container)

    @Slot(str)
    def log_callback(self, texto):
        import re
        texto_html = str(texto).replace('\n', '<br>')
        texto_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto_html)
        self.chat_display.append(f"<b>SOPHIA:</b> {texto_html}")

    def handle_excel_lock(self, message: str) -> bool:
        """Callback executado pela thread do worker para exibir caixa de diálogo de bloqueio do Excel de forma thread-safe."""
        import threading
        result = [False]
        event = threading.Event()
        QTimer.singleShot(0, lambda: self._show_locked_excel_dialog(message, event, result))
        event.wait()
        return result[0]

    def _show_locked_excel_dialog(self, message: str, event, result_list: list):
        """Abre a caixa de diálogo modal na thread principal e sinaliza a liberação da thread do worker."""
        box = QMessageBox(self)
        box.setWindowTitle("Excel Bloqueado")
        box.setText(message)
        box.setIcon(QMessageBox.Warning)
        btn_retry = box.addButton("Tentar Novamente", QMessageBox.AcceptRole)
        btn_cancel = box.addButton("Cancelar", QMessageBox.RejectRole)
        box.exec()
        result_list[0] = (box.clickedButton() == btn_retry)
        event.set()

    @Slot(str)
    def _on_eval_complete(self, res: str):
        """Slot executado na thread da UI após evaluate_chat terminar."""
        self.log_callback(res)
        if self.ai and self.ai.pending_intents:
            if getattr(self.ai, 'auto_execute', False):
                self.ai.auto_execute = False
                QTimer.singleShot(200, self._auto_execute_pending)
            else:
                self.estado_atual = AppStatus.ESPERANDO_DRY_RUN
        if self.ai and self.ai._query_params_pending:
            params = self.ai._query_params_pending
            self.ai._query_params_pending = None
            self._pending_query_params = params
            QMetaObject.invokeMethod(self, "_execute_query_flow",
                                     Qt.QueuedConnection,
                                     Q_ARG(str, str(params)))

    @Slot()
    def _auto_execute_pending(self):
        """Executa automaticamente intents seguras sem pedir confirmação do usuário."""
        if not self.ai or not self.ai.pending_intents:
            return

        if len(self.ai.pending_intents) > 1:
            d = QFileDialog.getExistingDirectory(self, "SOPHIA: Pasta de Trabalho para o Lote")
            if not d:
                self.log_callback("❌ Lote cancelado: pasta não selecionada.")
                self.ai.pending_intents = []
                self.estado_atual = AppStatus.LIVRE
                return
            self.ai.update_context(ultimo_diretorio=d)
            args_copy = self.ai.args.copy()
            def run_batch():
                return self.ai.execute_pending_intents(args_copy)
            worker = Worker(run_batch)
            worker.signals.finished_signal.connect(self.log_callback)
            worker.signals.error_signal.connect(self.log_callback)
            QThreadPool.globalInstance().start(worker)
            self.estado_atual = AppStatus.LIVRE
            return

        intent_data = self.ai.pending_intents[0]
        intent = intent_data.get("intent", "")
        self.ai.args.clear()
        for k, v in intent_data.items():
            if k not in ["intent", "status", "resposta", "raw_groq", "raw_input", "score", "context"]:
                self.ai.args[k] = v

        if intent == "EDIT_PROJECT_FILE":
            target_file = self.ai.args.get("file", "")
            prompt = self.ai.args.get("prompt", "")
            if not target_file or not prompt:
                self.log_callback("⚠️ SOPHIA: Não consegui identificar qual arquivo editar. Seja mais específico.")
                self.ai.pending_intents = []
                self.estado_atual = AppStatus.LIVRE
                return
            self.log_callback(f"⏳ <i>Editando '{target_file}'... Backup automático ativo.</i>")
            def run_edit():
                from core.dynamic_coder import DynamicCoder
                coder = DynamicCoder(self.ai.groq_api_key)
                return coder.edit_project_file(target_file, prompt)
            worker = Worker(run_edit)
            worker.signals.finished_signal.connect(self.log_callback)
            worker.signals.error_signal.connect(self.log_callback)
            QThreadPool.globalInstance().start(worker)
            self.ai.pending_intents = []
            self.estado_atual = AppStatus.LIVRE
            return

        if intent == "GENERATE_NEW_SKILL":
            prompt = self.ai.args.get("prompt", "")
            self.log_callback("⏳ <i>Gerando nova skill dinâmica...</i>")
            def run_skill():
                from core.dynamic_coder import DynamicCoder
                coder = DynamicCoder(self.ai.groq_api_key)
                return coder.generate_and_run(prompt, self.ai.args)
            worker = Worker(run_skill)
            worker.signals.finished_signal.connect(self.log_callback)
            worker.signals.error_signal.connect(self.log_callback)
            QThreadPool.globalInstance().start(worker)
            self.ai.pending_intents = []
            self.estado_atual = AppStatus.LIVRE
            return

        if intent == "UPDATE_WHATSAPP":
            telefone = self.ai.args.get("telefone")
            apikey = self.ai.args.get("apikey")
            if telefone and apikey:
                config_path = Path(__file__).parent / "config.json"
                try:
                    import json
                    if config_path.exists():
                        with open(config_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                    else:
                        cfg = {}
                    cfg["whatsapp_telefone"] = str(telefone).replace(" ", "").replace("-", "")
                    cfg["whatsapp_apikey"] = str(apikey).strip()
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=4, ensure_ascii=False)
                    self.log_callback(f"✅ <b>SOPHIA:</b> WhatsApp configurado! Relatórios agora irão para o número {cfg['whatsapp_telefone']}.")
                except Exception as e:
                    self.log_callback(f"❌ Erro ao salvar config do WhatsApp: {e}")
            else:
                self.log_callback("❌ SOPHIA: Faltaram parâmetros. Tente: 'Atualizar whatsapp para número X e apikey Y'.")
            self.ai.pending_intents = []
            self.estado_atual = AppStatus.LIVRE
            return



        # Para CREATE_FOLDER, RENAME_FOLDER, etc. — usa o fluxo visual com FileDialog
        self._execute_final_visual_step(intent)


    @Slot(str)
    def _execute_query_flow(self, _params_str: str = ""):
        """Slot executado na Thread da UI para abrir o QFileDialog e disparar a query Pandas."""
        params = getattr(self, '_pending_query_params', None)
        if not params:
            return
        self._pending_query_params = None
        
        from core.excel_engine import ExcelEngine
        e_files = QFileDialog.getOpenFileName(self, "SOPHIA: Selecionar Planilha", "", "Excel (*.xlsx *.xlsm *.xls)")
        excel_path = e_files[0] if e_files and e_files[0] else ""
        if not excel_path:
            self.log_callback("⚠️ Operação de consulta cancelada.")
            return
        
        def run_query():
            if params["tipo"] == "QUERY_EXCEL":
                return ExcelEngine.query_data(
                    excel_path,
                    params.get("alvo", ""),
                    params.get("coluna_desejada", "")
                )
            elif params["tipo"] == "QUERY_COUNT_EMPTY":
                return ExcelEngine.query_count_empty(
                    excel_path,
                    params.get("coluna", "")
                )
            return "⚠️ Tipo de query desconhecido."
        
        self.log_callback("⏳ <i>Consultando planilha via Pandas...</i>")
        worker = Worker(run_query)
        worker.signals.finished_signal.connect(self.log_callback)
        worker.signals.error_signal.connect(self.log_callback)
        QThreadPool.globalInstance().start(worker)

    @Slot()
    def _execute_auditoria_flow(self):
        d_pasta = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecione a Pasta de Efetivo (Raiz)")
        if not d_pasta:
            self.log_callback("⚠️ Operação cancelada.")
            return
        e_files = QFileDialog.getOpenFileName(self, "SOPHIA: Selecionar Planilha Excel", "", "Excel (*.xlsx *.xlsm *.xls)")
        excel_path = e_files[0] if e_files and e_files[0] else ""
        if not excel_path:
            self.log_callback("⚠️ Operação cancelada.")
            return
        def run_audit():
            self.executor.auditar_efetivo(d_pasta, excel_path, self.log_callback)
            return "Auditoria processada."
        self.log_callback("⏳ <i>Cruzando dados na RAM...</i>")
        worker = Worker(run_audit)
        worker.signals.error_signal.connect(self.log_callback)
        QThreadPool.globalInstance().start(worker)

    def enviar_comando(self):
        txt_original = self.input_field.text().strip()
        txt = txt_original.lower()
        if not txt: return
        
        self.chat_display.append(f"<div><b>Você:</b> {txt_original}</div>")

        if txt in ["cancela", "cancelar", "abortar", "esquece", "pare", "parar", "ignora"]:
            self.log_callback("🛑 <b>SOPHIA:</b> Operação abortada a força. Limpei a memória da RAM.")
            self.estado_atual = AppStatus.LIVRE
            self.dados_pendentes.clear()
            if self.ai:
                self.ai.pending_intents = []
                if hasattr(self.ai, '_query_params_pending'):
                    self.ai._query_params_pending = None
            self.input_field.clear()
            return
            
        if "auditar efetivo" in txt or txt == "efetivo" or txt == "auditar":
            self.log_callback("Iniciando auditoria. Aponte a pasta e a planilha nas janelas seguintes.")
            QTimer.singleShot(500, self._execute_auditoria_flow)
            self.input_field.clear()
            return



        if self.estado_atual == AppStatus.ESPERANDO_DRY_RUN:
            if txt in ["sim", "s", "confirmo", "ok", "yes", "manda", "vai", "bora"]:
                if hasattr(self.ai, 'pending_intents') and len(self.ai.pending_intents) > 1:
                    self.estado_atual = AppStatus.CONFIRMANDO_CONTEUDO_PASTA
                    self.log_callback("Como temos múltiplas ações, selecione a pasta raiz de trabalho no Windows.")
                    d = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecione a Pasta de Trabalho para o Lote")
                    if not d:
                        self.log_callback("❌ Operação em lote cancelada.")
                        self.ai.pending_intents = []
                        self.estado_atual = AppStatus.LIVRE
                    else:
                        self.ai.update_context(ultimo_diretorio=d)
                        self.log_callback("Pasta confirmada. Executando fila de ações em background...")
                        
                        args_copy = self.ai.args.copy() if hasattr(self.ai, 'args') else {}
                        def run_batch():
                            return self.ai.execute_pending_intents(args_copy)
                        
                        worker = Worker(run_batch)
                        worker.signals.finished_signal.connect(self.log_callback)
                        worker.signals.error_signal.connect(self.log_callback)
                        QThreadPool.globalInstance().start(worker)
                        self.estado_atual = AppStatus.LIVRE
                    self.input_field.clear()
                    return
                else:
                    intent_data = self.ai.pending_intents[0] if hasattr(self.ai, 'pending_intents') and self.ai.pending_intents else {}
                    intent = intent_data.get("intent", "")
                    self.ai.args.clear()
                    
                    for k, v in intent_data.items():
                        if k not in ["intent", "status", "resposta", "raw_groq", "raw_input", "score", "context"]:
                            self.ai.args[k] = v
                
                if intent == "CREATE_FOLDER":
                    if "folder_name" in self.ai.args:
                        self.log_callback(f"<b>SOPHIA:</b> Nome '{self.ai.args['folder_name']}' extraído do texto. Pulando perguntas...")
                        self._execute_final_visual_step("CREATE_FOLDER")
                        self.input_field.clear()
                        return
                    else:
                        self.estado_atual = AppStatus.ESPERANDO_NOME_CRIACAO
                        self.log_callback("Certo. Qual será o nome da nova pasta?")
                elif intent == "RENAME_FOLDER":
                    try:
                        d = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecione a Pasta com as Subpastas a Renomear")
                        if not d: raise Exception("Seleção cancelada.")
                        self.ai.args["target_path"] = d
                        
                        logic = self.ai.args.get("logic", "").lower()
                        scope = self.ai.args.get("scope", "subpastas").lower()
                        
                        # Detectar se a lógica é baseada em Excel (vem via NLP tag OU via palavras-chave)
                        usa_excel = "excel" in logic or "aba" in logic or logic == "excel_abas"
                        
                        if usa_excel:
                            self.log_callback("📊 Lógica: Renomear pelas ABAS do Excel. Aponte o arquivo:")
                            e_files = QFileDialog.getOpenFileName(self, "SOPHIA: Selecionar Planilha", "", "Excel (*.xlsx *.xlsm)")
                            e = e_files[0] if e_files and e_files[0] else ""
                            if not e: raise Exception("Excel não selecionado.")
                            self.ai.args["excel_path"] = e
                            self.ai.args["logic_prompt"] = "excel_abas"
                            self.ai.args["scope"] = scope
                            
                            self.log_callback("⏳ Lendo abas e renomeando as subpastas...")
                            args_copy = self.ai.args.copy()
                            def run_rename_excel():
                                from core.file_handler import FileHandler
                                sucesso = FileHandler.rename_folders_advanced(
                                    args_copy.get("target_path", ""),
                                    args_copy.get("scope", "subpastas"),
                                    args_copy.get("logic_prompt", "excel_abas"),
                                    args_copy.get("excel_path", "")
                                )
                                if sucesso: return "✅ Subpastas renomeadas pelas abas do Excel com sucesso!"
                                else: raise Exception("Falha na renomeação. Verifique se o Excel tem abas e as subpastas existem.")
                            worker = Worker(run_rename_excel)
                            worker.signals.finished_signal.connect(self.log_callback)
                            worker.signals.error_signal.connect(self.log_callback)
                            QThreadPool.globalInstance().start(worker)
                            self.ai.pending_intents = []
                            self.estado_atual = AppStatus.LIVRE
                        elif logic and logic != "excel_abas":
                            # Tem lógica textual (ex: "equipe 01 ate 20"), executa direto
                            from core.file_handler import FileHandler
                            subs = FileHandler.list_subfolders(d)
                            if subs:
                                self.log_callback(f"📂 <b>SOPHIA:</b> Subpastas: {', '.join(subs[:10])} {'...' if len(subs)>10 else ''}")
                            self.ai.args["scope"] = scope
                            self.estado_atual = AppStatus.ESPERANDO_LOGICA_RENOMEAR
                            self.log_callback(f"<b>SOPHIA:</b> Confirma a lógica '{logic}'? (sim/não ou descreva outra):")
                        else:
                            # Sem parâmetros, faz o fluxo guiado clássico
                            from core.file_handler import FileHandler
                            subs = FileHandler.list_subfolders(d)
                            if subs:
                                self.log_callback(f"📂 <b>SOPHIA:</b> Subpastas encontradas: {', '.join(subs[:10])} {'...' if len(subs)>10 else ''}")
                            self.log_callback("É para renomear as subpastas ou a pasta raiz?")
                            self.estado_atual = AppStatus.ESPERANDO_ESCOPO_RENOMEAR
                    except Exception as ex:
                        self.log_callback(f"❌ Renomeação cancelada: {ex}")
                        self.ai.pending_intents = []
                        self.estado_atual = AppStatus.LIVRE
                elif intent == "INJECT_FORMULA":
                    self.estado_atual = AppStatus.ESPERANDO_ABA_EXCEL
                    self.log_callback("Ok. Qual é o nome exato da aba do Excel (ex: Planilha1)?")
                elif intent == "PROCESSAR_FOTOS":
                    self.estado_atual = AppStatus.LIVRE
                    self.ai.pending_intents = []
                    self.input_field.setText("processar")
                    self.enviar_comando()
                    return
                elif intent == "DATAS" or intent == "AUDITORIA_DATAS":
                    self.estado_atual = AppStatus.LIVRE
                    self.ai.pending_intents = []
                    self.input_field.setText("datas")
                    self.enviar_comando()
                    return

                else:
                    self._execute_final_visual_step(intent)
            elif txt in ["nao", "não", "n", "cancelar", "cancela", "nope", "no"]:
                self.log_callback("❌ Execução cancelada pelo usuário. Sistema revertido para espera.")
                self.ai.pending_intents = []
                self.estado_atual = AppStatus.LIVRE
            else:
                # Usuário deu mais contexto em vez de "sim/não" — reprocessar como novo comando
                self.estado_atual = AppStatus.LIVRE
                self.ai.pending_intents = []
                self.log_callback("♻️ Entendi — você deu mais detalhes. Reprocessando...")
                QTimer.singleShot(100, lambda: self._reprocessar_como_comando(txt_original))
            self.input_field.clear()
            return

        if self.estado_atual == AppStatus.ESPERANDO_NOME_CRIACAO:
            self.ai.args["folder_name"] = txt_original
            self.estado_atual = AppStatus.ESPERANDO_SUBPASTAS_CRIACAO
            self.log_callback("Devo criar subpastas dentro dela? (Digite os nomes separados por vírgula, ou 'nao')")
            self.input_field.clear()
            return

        if self.estado_atual == AppStatus.ESPERANDO_SUBPASTAS_CRIACAO:
            if txt not in ["nao", "não", "none", "nenhuma"]:
                self.ai.args["subfolders"] = [s.strip() for s in txt_original.split(",") if s.strip()]
            self._execute_final_visual_step("CREATE_FOLDER")
            self.input_field.clear()
            return

        if self.estado_atual == AppStatus.ESPERANDO_ESCOPO_RENOMEAR:
            self.ai.args["scope"] = txt_original
            self.estado_atual = AppStatus.ESPERANDO_LOGICA_RENOMEAR
            self.log_callback("Beleza. Me explica a lógica. Ex: 'equipe 01 ate 20' ou 'igual as abas do excel':")
            self.input_field.clear()
            return
            
        if self.estado_atual == AppStatus.ESPERANDO_LOGICA_RENOMEAR:
            self.ai.args["logic_prompt"] = txt_original
            
            if "excel" in txt or "aba" in txt:
                self.log_callback("Legal, identifiquei a menção ao Excel. Por favor, aponte a planilha.")
                e_files = QFileDialog.getOpenFileName(self, "SOPHIA: Selecionar Planilha Base", "", "Excel (*.xlsx *.xlsm)")
                e = e_files[0] if e_files and e_files[0] else ""
                if not e:
                    self.log_callback("❌ Ação cancelada. Excel não foi selecionado.")
                    self.estado_atual = AppStatus.LIVRE
                    self.ai.pending_intents = []
                    self.input_field.clear()
                    return
                self.ai.args["excel_path"] = e
                
            self.log_callback("⏳ Processando lógica gerativa. Aguarde...")
            args_copy = self.ai.args.copy()
            def run_intent():
                from core.file_handler import FileHandler
                sucesso = FileHandler.rename_folders_advanced(
                    args_copy.get("target_path", ""),
                    args_copy.get("scope", "raiz"),
                    args_copy.get("logic_prompt", ""),
                    args_copy.get("excel_path", "")
                )
                if sucesso: return "✅ Renomeação Lógica concluída com sucesso e memória limpa."
                else: raise Exception("Falha na execução do motor lógico (Padrão não reconhecido ou Excel inválido).")
            
            worker = Worker(run_intent)
            worker.signals.finished_signal.connect(self.log_callback)
            worker.signals.error_signal.connect(self.log_callback)
            QThreadPool.globalInstance().start(worker)
            
            self.ai.pending_intents = []
            self.estado_atual = AppStatus.LIVRE
            self.input_field.clear()
            return
            
        if self.estado_atual == AppStatus.ESPERANDO_ABA_EXCEL:
            self.ai.args["sheet_name"] = txt_original
            self.estado_atual = AppStatus.ESPERANDO_CEL_EXCEL
            self.log_callback("Beleza. E qual é a célula alvo (ex: A1)?")
            self.input_field.clear()
            return
            
        if self.estado_atual == AppStatus.ESPERANDO_CEL_EXCEL:
            self.ai.args["cell"] = txt_original
            self.estado_atual = AppStatus.ESPERANDO_FORMULA_EXCEL
            self.log_callback("E finalmente, digite a fórmula exata (ex: =SOMA(A1:A5)):")
            self.input_field.clear()
            return
            
        if self.estado_atual == AppStatus.ESPERANDO_FORMULA_EXCEL:
            self.ai.args["formula"] = txt_original
            self._execute_final_visual_step("INJECT_FORMULA")
            self.input_field.clear()
            return

        if "status ia" in txt or txt in ["status", "provedores"]:
            if self.ai and hasattr(self.ai.nlp, '_router') and self.ai.nlp._router:
                self.log_callback(self.ai.nlp._router.status_report())
            else:
                self.log_callback("⚠️ AIRouter ainda não foi inicializado. Envie um comando para a IA primeiro.")
            self.input_field.clear()
            return

        if txt == "scan":

            self.log_callback("🕵️ Iniciando Scan de integridade local...")
            if not self.ai:
                self.log_callback("Erro: Agent Core offline.")
            else:
                d = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Varredura")
                if not d:
                    self.log_callback("⚠️ Ação cancelada.")
                    return
                self.log_callback("🔍 Escaneando...")
                def run_scan():
                    try:
                        res = self.ai.perform_dry_run_scan(d)
                        return f"<pre>{res}</pre>"
                    except Exception as e:
                        raise Exception(f"Erro no scan: {e}")
                worker = Worker(run_scan)
                worker.signals.finished_signal.connect(self.log_callback)
                worker.signals.error_signal.connect(self.log_callback)
                QThreadPool.globalInstance().start(worker)

        elif txt in ["processar", "fotos", "processar fotos", "processar lote", "iniciar processamento"]:
            if not self.executor:
                self.log_callback("Erro: Módulo de habilidades offline.")
            else:
                f = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Fotos")
                if not f:
                    self.log_callback("⚠️ Ação cancelada: Você não selecionou a **Pasta de Fotos**.")
                    return
                
                e_files = QFileDialog.getOpenFileName(self, "Selecionar Planilha Modelo", "", "Excel (*.xlsx *.xlsm)")
                e = e_files[0] if e_files and e_files[0] else ""
                if not e:
                    self.log_callback("⚠️ Ação cancelada: Você não selecionou a **Planilha Modelo**.")
                    return
                
                d = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Destino")
                if not d:
                    self.log_callback("⚠️ Ação cancelada: Você não selecionou a **Pasta de Destino**.")
                    return
                
                self.dados_pendentes = {"fotos": f, "excel": e, "destino": d}
                self.log_callback("🚀 SOPHIA: Tudo pronto! Iniciando processamento automático...")
                
                worker = Worker(
                    self.executor.processar_comando,
                    f, e, d, "Automático",
                    lambda msg: worker.signals.log_signal.emit(msg),
                    excel_lock_callback=self.handle_excel_lock
                )
                worker.signals.log_signal.connect(self.log_callback)
                worker.signals.error_signal.connect(self.log_callback)
                
                def on_processamento_finished(res):
                    if res and "Tarefa concluída silenciosamente" not in res and self.ai and hasattr(self.ai, 'nlp'):
                        self.ai.nlp.chat_history.append({"role": "assistant", "content": f"Aqui está o último relatório que processei e enviei:\n{res}"})
                        if len(self.ai.nlp.chat_history) > 6:
                            self.ai.nlp.chat_history = self.ai.nlp.chat_history[-6:]
                            
                worker.signals.finished_signal.connect(on_processamento_finished)
                QThreadPool.globalInstance().start(worker)

        elif txt in ["datas", "corrigir datas", "sincronizar datas", "ajustar datas"]:
            if not self.executor:
                self.log_callback("Erro: Módulo de habilidades offline.")
            else:
                e_files = QFileDialog.getOpenFileName(self, "Planilha para Corrigir Datas", "", "Excel (*.xlsx *.xlsm)")
                e = e_files[0] if e_files and e_files[0] else ""
                if not e:
                    self.log_callback("⚠️ Ação cancelada: Você não selecionou a **Planilha**.")
                    return
 
                f = QFileDialog.getExistingDirectory(self, "Pasta de Fotos")
                if not f:
                    self.log_callback("⚠️ Ação cancelada: Você não selecionou a **Pasta de Fotos**.")
                    return
                
                self.log_callback("📅 SOPHIA: Sincronizando datas...")
                worker = Worker(self.executor.atualizar_datas_planilha, e, f, self.log_callback)
                worker.signals.error_signal.connect(self.log_callback)
                QThreadPool.globalInstance().start(worker)

        else:
            if self.ai:
                def run_eval():
                    return self.ai.evaluate_chat(txt_original, self.current_user)

                self.log_callback("⏳ <i>Processando lógica cognitiva...</i>")
                worker = Worker(run_eval)
                worker.signals.finished_signal.connect(self._on_eval_complete)
                worker.signals.error_signal.connect(self.log_callback)
                QThreadPool.globalInstance().start(worker)
            else:
                self.log_callback("IA offline no momento.")

        self.input_field.clear()

    def resizeEvent(self, event):
        self.refraction.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)


    def _reprocessar_como_comando(self, texto: str):
        """Reinjeta um texto como novo comando, preservando o histórico do chat da Groq."""
        self.input_field.setText(texto)
        self.enviar_comando()

    def _execute_final_visual_step(self, intent: str):
        self.log_callback("Ótimo. Para garantir a segurança, aponte a pasta alvo na janela do Windows que acabei de abrir.")
        try:
            # Instancia o DynamicFilter se houver filter_expression
            filter_expr = self.ai.args.get("filter_expression") if self.ai else None
            from core.dynamic_filter import DynamicFilter
            dynamic_filter = DynamicFilter(filter_expr) if filter_expr else None

            if intent == "CREATE_FOLDER":
                d = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecionar Pasta Base para Criação")
                if not d: raise Exception("Operação cancelada pelo usuário.")
                self.ai.args["base_path"] = d
                
            elif intent == "RENAME_FOLDER":
                d = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecionar Pasta Base para Renomear")
                if not d: raise Exception("Operação cancelada.")
                self.ai.args["target_path"] = d
                
            elif intent == "DELETE_FOLDER":
                d = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecionar Pasta para DELETAR")
                if not d: raise Exception("Operação cancelada.")
                self.ai.args["target_path"] = d
                
            elif intent == "MOVE_FOLDER":
                src = QFileDialog.getExistingDirectory(self, "SOPHIA: Pasta Origem (Que será movida)")
                if not src: raise Exception("Operação cancelada.")
                dst = QFileDialog.getExistingDirectory(self, "SOPHIA: Pasta Destino (Para onde vai)")
                if not dst: raise Exception("Operação cancelada.")
                self.ai.args["source_path"] = src
                self.ai.args["dest_path"] = dst
                
            elif intent == "PROCESSAR_FOTOS":
                if "fotos" not in self.ai.args:
                    f = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecionar Pasta de Fotos")
                    if not f: raise Exception("Pasta de fotos não selecionada.")
                    self.ai.args["fotos"] = f
                if "excel" not in self.ai.args:
                    e_files = QFileDialog.getOpenFileName(self, "SOPHIA: Selecionar Planilha Modelo", "", "Excel (*.xlsx *.xlsm)")
                    e = e_files[0] if e_files and e_files[0] else ""
                    if not e: raise Exception("Planilha não selecionada.")
                    self.ai.args["excel"] = e
                if "destino" not in self.ai.args:
                    d = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecionar Pasta de Destino")
                    if not d: raise Exception("Pasta de destino não selecionada.")
                    self.ai.args["destino"] = d
                
                # Se o alvo (nome do usuário) não vier na intenção, prosseguimos no modo automático de célula
                # sem interromper para perguntar 'de quem é a planilha'.
                self.log_callback("🚀 SOPHIA: Iniciando processamento no modo de adaptação automática à célula...")
                
                # Dispara o processamento direto
                worker = Worker(
                    self.executor.processar_comando,
                    self.ai.args["fotos"],
                    self.ai.args["excel"],
                    self.ai.args["destino"],
                    self.ai.args.get("alvo") or "Automático",
                    lambda msg: worker.signals.log_signal.emit(msg),
                    dynamic_filter,
                    excel_lock_callback=self.handle_excel_lock
                )
                def on_processamento_finished(res):
                    self.log_callback(res)
                    if res and "Tarefa concluída silenciosamente" not in res and self.ai and hasattr(self.ai, 'nlp'):
                        self.ai.nlp.chat_history.append({"role": "assistant", "content": f"Aqui está o último relatório que processei:\n{res}"})
                        if len(self.ai.nlp.chat_history) > 6:
                            self.ai.nlp.chat_history = self.ai.nlp.chat_history[-6:]

                worker.signals.log_signal.connect(self.log_callback)
                worker.signals.error_signal.connect(self.log_callback)
                worker.signals.finished_signal.connect(on_processamento_finished)
                QThreadPool.globalInstance().start(worker)
                return
                    

                
            elif intent == "DATAS":
                if "excel" not in self.ai.args:
                    e_files = QFileDialog.getOpenFileName(self, "Planilha para Corrigir Datas", "", "Excel (*.xlsx *.xlsm)")
                    e = e_files[0] if e_files and e_files[0] else ""
                    if not e: raise Exception("Planilha nao selecionada.")
                    self.ai.args["excel"] = e
                if "fotos" not in self.ai.args:
                    f = QFileDialog.getExistingDirectory(self, "Pasta de Fotos")
                    if not f: raise Exception("Pasta de fotos nao selecionada.")
                    self.ai.args["fotos"] = f
                
                self.log_callback("📅 SOPHIA: Sincronizando datas...")
                worker = Worker(self.executor.atualizar_datas_planilha, self.ai.args["excel"], self.ai.args["fotos"], self.log_callback, dynamic_filter)
                worker.signals.error_signal.connect(self.log_callback)
                QThreadPool.globalInstance().start(worker)
                return

            elif intent == "REPLICAR_COLUNAS":
                if "arquivo_origem" not in self.ai.args:
                    f = QFileDialog.getOpenFileName(self, "SOPHIA: Selecionar Planilha de Origem", "", "Excel (*.xlsx *.xlsm)")
                    if not f[0]: raise Exception("Planilha de origem não selecionada.")
                    self.ai.args["arquivo_origem"] = f[0]
                    
                if "aba_origem" not in self.ai.args:
                    text, ok = QInputDialog.getText(self, 'SOPHIA', 'Digite o nome da aba de origem:')
                    if not ok or not text: raise Exception("Aba não informada.")
                    self.ai.args["aba_origem"] = text
                    
                if "pasta_destino" not in self.ai.args:
                    p = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecionar Pasta com as Planilhas Alvo")
                    if not p: raise Exception("Pasta de destino não selecionada.")
                    self.ai.args["pasta_destino"] = p
                    
                self.executor.replicar_formatacao_colunas(
                    self.ai.args["arquivo_origem"],
                    self.ai.args["aba_origem"],
                    self.ai.args["pasta_destino"],
                    self.log_callback
                )
                return

            elif intent == "INJECT_FORMULA":
                e_files = QFileDialog.getOpenFileName(self, "SOPHIA: Selecionar Excel", "", "Excel (*.xlsx *.xlsm)")
                e = e_files[0] if e_files and e_files[0] else ""
                if not e: raise Exception("Excel não selecionado.")
                self.ai.args["excel_path"] = e
                
        except Exception as ex:
            self.log_callback(f"❌ Ação interrompida: {ex}")
            self.ai.pending_intents = []
            self.estado_atual = AppStatus.LIVRE
            return
            
        self.log_callback("⏳ Executando ação nativa no hardware. Aguarde...")
        
        args_copy = self.ai.args.copy()
        
        def run_intent():
            return self.ai.execute_pending_intents(args_copy)
        
        worker = Worker(run_intent)
        worker.signals.finished_signal.connect(self.log_callback)
        worker.signals.error_signal.connect(self.log_callback)
        QThreadPool.globalInstance().start(worker)
        
        self.estado_atual = AppStatus.LIVRE

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SophiaApp()

    try:
        from splash_sophia import SophiaSplashScreen
        splash = SophiaSplashScreen()
        splash.show()
        
        def finalizar_splash():
            try:
                import pyi_splash
                pyi_splash.close()
            except:
                pass
            splash.close()
            window.show()

        QTimer.singleShot(3500, finalizar_splash)
        
    except Exception as e:
        print(f"Erro ao carregar Splash: {e}")
        window.show()

    sys.exit(app.exec())