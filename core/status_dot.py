from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QAntialiasing

class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._opacity = 1.0

        # Animação de Fade (Neon Pulse)
        self.anim = QPropertyAnimation(self, b"dotOpacity")
        self.anim.setDuration(2000)
        self.anim.setStartValue(0.3)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.setLoopCount(-1)
        self.anim.start()

    @Property(float)
    def dotOpacity(self): return self._opacity
    @dotOpacity.setter
    def dotOpacity(self, val):
        self._opacity = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QAntialiasing)

        center = self.rect().center()
        radius = self.width() / 2

        # Glow Effect
        grad = QRadialGradient(center, radius)
        grad.setColorAt(0, QColor(0, 255, 127, int(255 * self._opacity))) # Spring Green Neon
        grad.setColorAt(1, QColor(0, 255, 127, 0))

        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.rect())
