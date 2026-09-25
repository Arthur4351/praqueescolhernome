import sys
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QPropertyAnimation, Property, QEasingCurve, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QPen, QFont, QColor, QFontMetrics

class SophiaSplashScreen(QWidget):
    def __init__(self):
        super().__init__()

        # Configurações de Janela (Sem bordas e sempre no topo)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 400)

        # Centralizar na tela
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

        # Configurações de Estética
        self.bg_color = QColor("#E0FFFF")  # Ciano suave elegante
        self.stroke_color = QColor("#008B8B") # Ciano Escuro para contraste na escrita

        # Preparação da Fonte e do Caminho (Path)
        self.text = "Sophia"
        # Tentativa de fontes cursivas comuns em Windows/Linux/Mac
        font_families = ["Brush Script MT", "Gabriola", "Lucida Handwriting", "Segoe Script", "cursive"]
        self.font = QFont()
        self.font.setFamilies(font_families)
        self.font.setPointSize(120)
        self.font.setItalic(True)

        # Gerar o QPainterPath do texto
        metrics = QFontMetrics(self.font)
        text_rect = metrics.boundingRect(self.text)

        # Posicionamento central do texto no path
        # Ajustamos o Y para considerar o ascent da fonte
        x_pos = (self.width() - text_rect.width()) / 2
        y_pos = (self.height() + metrics.ascent() - metrics.descent()) / 2

        full_path = QPainterPath()
        full_path.addText(x_pos, y_pos, self.font, self.text)

        # "Achatar" o path para garantir que a animação de traçado seja fluida
        self.path = full_path.simplified()

        # Propriedade para animação (0.0 a 1.0)
        self._progress = 0.0

        # Inicializar Animação
        self.animation = QPropertyAnimation(self, b"progress")
        self.animation.setDuration(3500)  # 3.5 segundos conforme requisito
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Ao terminar, chama a transição
        self.animation.finished.connect(self.transition_to_main)

        # Timer para iniciar (pequeno delay para garantir renderização)
        QTimer.singleShot(100, self.animation.start)

    # Definição da Property para o QPropertyAnimation
    @Property(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value
        self.update()  # Força o repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Desenhar Fundo Sólido Elegante com cantos arredondados
        painter.setBrush(self.bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)

        # Configurar Caneta para o traçado do nome
        pen = QPen(self.stroke_color, 3)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        # A mágica: Desenhar apenas uma porção do path baseada no progresso
        # Para um efeito de "escrita", iteramos pelos elementos do path
        partial_path = QPainterPath()
        element_count = self.path.elementCount()
        stop_at = int(element_count * self._progress)

        for i in range(stop_at):
            el = self.path.elementAt(i)
            if el.isMoveTo():
                partial_path.moveTo(el.x, el.y)
            elif el.isLineTo():
                partial_path.lineTo(el.x, el.y)
            elif el.isCurveTo():
                # O simplified() converte a maioria das curvas em segmentos de linha
                # Mas tratamos o elementAt de forma genérica para garantir fluidez
                partial_path.lineTo(el.x, el.y)

        painter.drawPath(partial_path)

    def transition_to_main(self):
        # Pequena pausa no final para apreciação do nome completo
        QTimer.singleShot(500, self.close)

class MainSystem(QMainWindow):
    """Interface Principal do Sistema (Placeholder)"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sophia AI - Sistema Ativo")
        self.resize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        label = QLabel("Bem-vindo ao Sistema Sophia AI\n120Hz Mode Active")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #008B8B; font-weight: bold;")
        layout.addWidget(label)

if __name__ == "__main__":
    # Suporte a High DPI
    app = QApplication(sys.argv)

    splash = SophiaSplashScreen()
    splash.show()

    sys.exit(app.exec())
