import sys
import os
import threading
import ctypes
import getpass
from enum import Enum, auto
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class AppStatus(Enum):
    LIVRE = auto()
    ESPERANDO_NOME = auto()
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
except:
    MODULOS_OK = False

try:
    from core.agent_core import SophiaAgentCore
    IA_OK = True
except:
    IA_OK = False

try:
    from ui.components.orb import DataOrb
except:
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


class WorkerThread(QThread):
    finished_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.func(*self.args, **self.kwargs)
            if res is None: res = "Tarefa concluída silenciosamente."
            self.finished_signal.emit(str(res))
        except Exception as e:
            self.error_signal.emit(f"Erro Crítico na Thread: {e}")

class SophiaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user = getpass.getuser().capitalize()
        self.setWindowTitle("SOPHIA AI - Assistant Edition")
        self.resize(1000, 800)

        self.executor = SophiaExecutor() if MODULOS_OK else None
        self.ai = SophiaAgentCore() if IA_OK else None
        self.estado_atual = AppStatus.LIVRE
        self.dados_pendentes = {}
        self._load_dimensoes()
        self.init_ui()

    def _load_dimensoes(self):
        import json
        self.dimensoes_file = "dimensoes_usuarios.json"
        self.dimensoes = {
            "kauan": {"largura": 10.6, "altura": 6.22},
            "lucas": {"largura": 7.05, "altura": 4.03},
            "gustavo": {"largura": 7.26, "altura": 5.77}
        }
        if os.path.exists(self.dimensoes_file):
            try:
                with open(self.dimensoes_file, 'r', encoding='utf-8') as f:
                    self.dimensoes.update(json.load(f))
            except:
                pass
        else:
            self._save_dimensoes()

    def _save_dimensoes(self):
        import json
        try:
            with open(self.dimensoes_file, 'w', encoding='utf-8') as f:
                json.dump(self.dimensoes, f, indent=4)
        except:
            pass

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
        self.chat_display.append(f"<b>SOPHIA:</b> {texto}")

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
        self.worker = WorkerThread(run_query)
        self.worker.finished_signal.connect(self.log_callback)
        self.worker.error_signal.connect(self.log_callback)
        self.worker.start()

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
        self.worker = WorkerThread(run_audit)
        self.worker.start()

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
            self.log_callback("<b>SOPHIA:</b> Iniciando auditoria. Aponte a pasta e a planilha nas janelas seguintes.")
            QTimer.singleShot(500, self._execute_auditoria_flow)
            self.input_field.clear()
            return

        if self.estado_atual == AppStatus.ESPERANDO_NOME:
            nome_encontrado = None
            for n in self.dimensoes.keys():
                if n in txt:
                    nome_encontrado = n
                    break
            
            if nome_encontrado:
                dim = self.dimensoes.get(nome_encontrado, {"largura": 10.6, "altura": 6.22})
                self.executor.definir_dimensoes(dim["largura"], dim["altura"])
                nome = nome_encontrado.capitalize()
            else:
                self.log_callback(f"❌ <b>SOPHIA:</b> Usuário não cadastrado. Opções: {', '.join(self.dimensoes.keys())}.")
                self.estado_atual = AppStatus.LIVRE
                self.dados_pendentes.clear()
                self.input_field.clear()
                return

            self.log_callback(f"👤 Usuário confirmado: {nome}. Aplicando dimensões específicas...")
            self.estado_atual = AppStatus.LIVRE
            d_fotos = self.dados_pendentes.get("fotos")
            d_excel = self.dados_pendentes.get("excel")
            d_destino = self.dados_pendentes.get("destino")
            self.dados_pendentes.clear()
            self.log_callback("🚀 SOPHIA: Tudo pronto! Iniciando processamento...")
            
            self.worker = WorkerThread(self.executor.processar_comando, d_fotos, d_excel, d_destino, nome, self.log_callback)
            self.worker.start()
            
            self.input_field.clear()
            return

        if self.estado_atual == AppStatus.ESPERANDO_DRY_RUN:
            if txt in ["sim", "s", "confirmo", "ok", "yes", "manda", "vai", "bora"]:
                if hasattr(self.ai, 'pending_intents') and len(self.ai.pending_intents) > 1:
                    self.estado_atual = AppStatus.CONFIRMANDO_CONTEUDO_PASTA
                    self.log_callback("<b>SOPHIA:</b> Como temos múltiplas ações, selecione a pasta raiz de trabalho no Windows.")
                    d = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecione a Pasta de Trabalho para o Lote")
                    if not d:
                        self.log_callback("❌ Operação em lote cancelada.")
                        self.ai.pending_intents = []
                        self.estado_atual = AppStatus.LIVRE
                    else:
                        self.ai.nlp.update_context(ultimo_diretorio=d)
                        self.log_callback("<b>SOPHIA:</b> Pasta confirmada. Executando fila de ações em background...")
                        
                        args_copy = self.ai.args.copy() if hasattr(self.ai, 'args') else {}
                        def run_batch():
                            return self.ai.execute_pending_intents(args_copy)
                        
                        self.worker = WorkerThread(run_batch)
                        self.worker.finished_signal.connect(self.log_callback)
                        self.worker.error_signal.connect(self.log_callback)
                        self.worker.start()
                        self.estado_atual = AppStatus.LIVRE
                    self.input_field.clear()
                    return
                else:
                    intent = self.ai.pending_intents[0]["intent"] if hasattr(self.ai, 'pending_intents') and self.ai.pending_intents else ""
                    if not hasattr(self.ai, 'args'): self.ai.args = {}
                    self.ai.args.clear()
                
                if intent == "CREATE_FOLDER":
                    self.estado_atual = AppStatus.ESPERANDO_NOME_CRIACAO
                    self.log_callback("<b>SOPHIA:</b> Certo. Qual será o nome da nova pasta?")
                elif intent == "RENAME_FOLDER":
                    try:
                        d = QFileDialog.getExistingDirectory(self, "SOPHIA: Selecione a Pasta Alvo")
                        if not d: raise Exception("Seleção cancelada.")
                        self.ai.args["target_path"] = d
                        
                        from core.file_handler import FileHandler
                        subs = FileHandler.list_subfolders(d)
                        if subs:
                            self.log_callback(f"📂 <b>SOPHIA:</b> Achei as seguintes subpastas: {', '.join(subs[:10])} {'...' if len(subs)>10 else ''}")
                            self.log_callback("<b>SOPHIA:</b> É para renomear a pasta raiz ou as subpastas?")
                        else:
                            self.log_callback("📂 <b>SOPHIA:</b> A pasta está vazia. É para renomear a pasta raiz?")
                            
                        self.estado_atual = AppStatus.ESPERANDO_ESCOPO_RENOMEAR
                    except:
                        self.log_callback("❌ Operação de renomeação cancelada.")
                        self.ai.pending_intents = []
                        self.estado_atual = AppStatus.LIVRE
                elif intent == "INJECT_FORMULA":
                    self.estado_atual = AppStatus.ESPERANDO_ABA_EXCEL
                    self.log_callback("<b>SOPHIA:</b> Ok. Qual é o nome exato da aba do Excel (ex: Planilha1)?")
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
                elif intent in ("CADASTRAR_USUARIO", "EDITAR_DIMENSAO"):
                    self.estado_atual = AppStatus.LIVRE
                    intent_data = self.ai.pending_intents[0] if self.ai.pending_intents else {}
                    self.ai.pending_intents = []
                    
                    alvo = intent_data.get("alvo", "").lower()
                    w = intent_data.get("largura")
                    h = intent_data.get("altura")
                    
                    if not alvo:
                        self.log_callback("❌ <b>SOPHIA:</b> Faltou o nome do alvo. Tente: 'cadastrar o João com 5 de largura e 10 de altura'")
                        return
                    if not w or not h:
                        self.log_callback("❌ <b>SOPHIA:</b> Faltou informar a largura e a altura. Seje específica.")
                        return
                        
                    self.dimensoes[alvo] = {"largura": float(w.replace(',','.')), "altura": float(h.replace(',','.'))}
                    self._save_dimensoes()
                    self.log_callback(f"✅ <b>SOPHIA:</b> Perfil persistido! <b>{alvo.capitalize()}</b> agora usará o grid de <b>{w}cm x {h}cm</b>.")
                    return
                else:
                    self._execute_final_visual_step(intent)
            else:
                self.log_callback("❌ Execução cancelada pelo usuário. Sistema revertido para espera.")
                self.ai.pending_intents = []
                self.estado_atual = AppStatus.LIVRE
            self.input_field.clear()
            return

        if self.estado_atual == AppStatus.ESPERANDO_NOME_CRIACAO:
            self.ai.args["folder_name"] = txt_original
            self.estado_atual = AppStatus.ESPERANDO_SUBPASTAS_CRIACAO
            self.log_callback("<b>SOPHIA:</b> Devo criar subpastas dentro dela? (Digite os nomes separados por vírgula, ou 'nao')")
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
            self.log_callback("<b>SOPHIA:</b> Beleza. Me explica a lógica. Ex: 'equipe 01 ate 20' ou 'igual as abas do excel':")
            self.input_field.clear()
            return
            
        if self.estado_atual == AppStatus.ESPERANDO_LOGICA_RENOMEAR:
            self.ai.args["logic_prompt"] = txt_original
            
            if "excel" in txt or "aba" in txt:
                self.log_callback("<b>SOPHIA:</b> Legal, identifiquei a menção ao Excel. Por favor, aponte a planilha.")
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
            
            self.worker = WorkerThread(run_intent)
            self.worker.finished_signal.connect(self.log_callback)
            self.worker.error_signal.connect(self.log_callback)
            self.worker.start()
            
            self.ai.pending_intents = []
            self.estado_atual = AppStatus.LIVRE
            self.input_field.clear()
            return
            
        if self.estado_atual == AppStatus.ESPERANDO_ABA_EXCEL:
            self.ai.args["sheet_name"] = txt_original
            self.estado_atual = AppStatus.ESPERANDO_CEL_EXCEL
            self.log_callback("<b>SOPHIA:</b> Beleza. E qual é a célula alvo (ex: A1)?")
            self.input_field.clear()
            return
            
        if self.estado_atual == AppStatus.ESPERANDO_CEL_EXCEL:
            self.ai.args["cell"] = txt_original
            self.estado_atual = AppStatus.ESPERANDO_FORMULA_EXCEL
            self.log_callback("<b>SOPHIA:</b> E finalmente, digite a fórmula exata (ex: =SOMA(A1:A5)):")
            self.input_field.clear()
            return
            
        if self.estado_atual == AppStatus.ESPERANDO_FORMULA_EXCEL:
            self.ai.args["formula"] = txt_original
            self._execute_final_visual_step("INJECT_FORMULA")
            self.input_field.clear()
            return

        if "scan" in txt:
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
                        QMetaObject.invokeMethod(self, "log_callback", Qt.QueuedConnection, Q_ARG(str, f"<pre>{res}</pre>"))
                    except Exception as e:
                        QMetaObject.invokeMethod(self, "log_callback", Qt.QueuedConnection, Q_ARG(str, f"Erro: {e}"))
                self.worker = WorkerThread(run_scan)
                self.worker.start()

        elif "processar" in txt:
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
                self.estado_atual = AppStatus.ESPERANDO_NOME
                nomes_disp = ", ".join([k.capitalize() for k in self.dimensoes.keys()])
                self.log_callback(f"❓ Essa planilha é de quem? (Cadastrados: {nomes_disp})")

        elif "datas" in txt:
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
                self.worker = WorkerThread(self.executor.atualizar_datas_planilha, e, f, self.log_callback)
                self.worker.start()

        else:
            if self.ai:
                def run_eval():
                    try:
                        res = self.ai.evaluate_chat(txt_original, self.current_user)
                        QMetaObject.invokeMethod(self, "log_callback", Qt.QueuedConnection, Q_ARG(str, res))
                        if hasattr(self.ai, 'pending_intents') and self.ai.pending_intents:
                            self.estado_atual = AppStatus.ESPERANDO_DRY_RUN
                        
                        if hasattr(self.ai, '_query_params_pending') and self.ai._query_params_pending:
                            params = self.ai._query_params_pending
                            self.ai._query_params_pending = None
                            
                            def open_and_query():
                                from core.excel_engine import ExcelEngine
                                e_files = QFileDialog.getOpenFileName(self, "SOPHIA: Selecionar Planilha", "", "Excel (*.xlsx *.xlsm *.xls)")
                                excel_path = e_files[0] if e_files and e_files[0] else ""
                                if not excel_path:
                                    self.log_callback("⚠️ Operação cancelada.")
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
                                
                                self.log_callback("⏳ <i>Consultando planilha...</i>")
                                self.worker = WorkerThread(run_query)
                                self.worker.finished_signal.connect(self.log_callback)
                                self.worker.error_signal.connect(self.log_callback)
                                self.worker.start()
                            
                            QMetaObject.invokeMethod(self, "_execute_query_flow",
                                                     Qt.QueuedConnection,
                                                     Q_ARG(str, str(params)))
                            self._pending_query_params = params
                    except Exception as e:
                        QMetaObject.invokeMethod(self, "log_callback", Qt.QueuedConnection, Q_ARG(str, f"Erro NLP: {e}"))
                
                self.log_callback("⏳ <i>Processando lógica cognitiva...</i>")
                self.worker = WorkerThread(run_eval)
                self.worker.start()
            else:
                self.log_callback("IA offline no momento.")

        self.input_field.clear()

    def resizeEvent(self, event):
        self.refraction.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)


    def _execute_final_visual_step(self, intent: str):
        self.log_callback("<b>SOPHIA:</b> Ótimo. Para garantir a segurança, aponte a pasta alvo na janela do Windows que acabei de abrir.")
        try:
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
        
        self.worker = WorkerThread(run_intent)
        self.worker.finished_signal.connect(self.log_callback)
        self.worker.error_signal.connect(self.log_callback)
        self.worker.start()
        
        self.ai.pending_intents = []
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