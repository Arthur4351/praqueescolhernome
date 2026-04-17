import sys
import os
import threading
from datetime import datetime
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# =================================================================
# IMPORTAÇÃO SEGURA
# =================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from minhas_habilidades import SophiaExecutor 
    MODULOS_OK = True
except Exception as e:
    print(f"Erro ao carregar 'minhas_habilidades.py': {e}")
    MODULOS_OK = False

# Tentativa de carregar componentes opcionais
try:
    from internet import SophiaIntelligence
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

class SophiaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SOPHIA AI - Assistant Edition")
        self.resize(1000, 800)
        self.executor = SophiaExecutor() if MODULOS_OK else None
        self.ai = SophiaIntelligence() if IA_OK else None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #E0FFFF; }
            QFrame#GlassPanel {
                background-color: rgba(255, 255, 255, 50);
                border: 1px solid rgba(255, 255, 255, 80);
                border-radius: 25px;
            }
            QTextEdit { 
                background: transparent; border: none; 
                color: #004d4d; font-size: 16px;
            }
            QLineEdit { 
                background-color: rgba(255, 255, 255, 120); 
                border-radius: 20px; padding: 15px; color: #004d4d;
            }
            QPushButton {
                background-color: #00838F; color: white; 
                border-radius: 20px; padding: 10px 20px; font-weight: bold;
            }
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
        self.chat_display.setHtml("<b>SOPHIA:</b> Sistema online, Paulo. Comandos: 'processar' ou 'datas'.")
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

    def log_callback(self, texto):
        self.chat_display.append(f"<b>SOPHIA:</b> {texto}")

    def enviar_comando(self):
        txt = self.input_field.text().strip().lower()
        if not txt: return
        self.chat_display.append(f"<div><b>Você:</b> {txt}</div>")

        # COMANDO PROCESSAR
        if "processar" in txt:
            if not self.executor:
                self.log_callback("Erro: Módulo de habilidades não carregado.")
                return
            f = QFileDialog.getExistingDirectory(self, "Selecionar Fotos")
            e = QFileDialog.getOpenFileName(self, "Selecionar Planilha", "", "Excel (*.xlsx *.xlsm)")[0]
            d = QFileDialog.getExistingDirectory(self, "Pasta de Destino")
            if f and e and d:
                threading.Thread(target=self.executor.processar_comando, args=(f, e, d, self.log_callback), daemon=True).start()

        # COMANDO DATAS (ABRE AS JANELAS AUTOMATICAMENTE)
        elif "datas" in txt:
            if not self.executor:
                self.log_callback("Erro: Módulo de habilidades não carregado.")
                return
            e = QFileDialog.getOpenFileName(self, "Planilha para Corrigir Datas", "", "Excel (*.xlsx *.xlsm)")[0]
            f = QFileDialog.getExistingDirectory(self, "Pasta de Fotos (com carimbo de data)")
            if e and f:
                # Aqui você deve garantir que a função atualizar_datas_planilha existe no seu habilidades.py
                if hasattr(self.executor, 'atualizar_datas_planilha'):
                    threading.Thread(target=self.executor.atualizar_datas_planilha, args=(e, f, self.log_callback), daemon=True).start()
                else:
                    self.log_callback("A função de datas ainda não foi implementada no executor.")
        
        else:
            if self.ai:
                self.log_callback(self.ai.processar(txt, user_id="Paulo"))
            else:
                self.log_callback("Comando não reconhecido. Tente 'processar' ou 'datas'.")

        self.input_field.clear()

    def resizeEvent(self, event):
        """Ajuste de indentação corrigido aqui"""
        self.refraction.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Prepara a janela principal, mas NÃO mostra ainda
    window = SophiaApp()

    try:
        from splash_sophia import SophiaSplashScreen
        splash = SophiaSplashScreen()
        splash.show()
        
        # Função para fechar splash e abrir a main
        def finalizar_splash():
            splash.close()
            window.show()

        # Espera 3.5 segundos (tempo da animação) antes de abrir o sistema
        QTimer.singleShot(3500, finalizar_splash)
        
    except Exception as e:
        print(f"Erro ao carregar Splash: {e}")
        window.show() # Se o splash der erro, abre direto para não travar

    sys.exit(app.exec())