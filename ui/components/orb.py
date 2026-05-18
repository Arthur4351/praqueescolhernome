from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPointF, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient

class DataOrb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)

        # Ângulos de rotação
        self._outer_angle = 0
        self._middle_angle = 0
        self._core_pulse = 0.8

        # Timer para animação 120Hz (aprox 8ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(8)

        # Animação de Pulso do Núcleo
        self.pulse_anim = QPropertyAnimation(self, b"corePulse")
        self.pulse_anim.setDuration(2000)
        self.pulse_anim.setStartValue(0.6)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        self.pulse_anim.setLoopCount(-1)
        self.pulse_anim.start()

    @Property(float)
    def corePulse(self): return self._core_pulse
    @corePulse.setter
    def corePulse(self, val):
        self._core_pulse = val
        self.update()

    def update_animation(self):
        self._outer_angle = (self._outer_angle + 1) % 360  # Direita
        self._middle_angle = (self._middle_angle - 1.5) % 360  # Esquerda
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPointF(self.width() / 2, self.height() / 2)

        # 1. Anel Externo (Ciano Fino)
        pen_outer = QPen(QColor(0, 255, 255, 100))
        pen_outer.setWidth(2)
        pen_outer.setDashPattern([10, 20])
        painter.setPen(pen_outer)
        painter.save()
        painter.translate(center)
        painter.rotate(self._outer_angle)
        painter.drawEllipse(QPointF(0, 0), 80, 80)
        painter.restore()

        # 2. Anel do Meio
        pen_mid = QPen(QColor(0, 200, 255, 150))
        pen_mid.setWidth(3)
        painter.setPen(pen_mid)
        painter.save()
        painter.translate(center)
        painter.rotate(self._middle_angle)
        painter.drawArc(-60, -60, 120, 120, 0, 250 * 16)
        painter.restore()

        # 3. Núcleo Pulsante (Glow)
        grad = QRadialGradient(center, 40)
        grad.setColorAt(0, QColor(0, 255, 255, int(255 * self._core_pulse)))
        grad.setColorAt(1, QColor(0, 255, 255, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, 40 * self._core_pulse, 40 * self._core_pulse)
