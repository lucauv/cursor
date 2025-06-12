import sys
import time
import math
import random
from PySide6 import QtCore, QtGui, QtWidgets


class Sparkle(QtWidgets.QLabel):
    def __init__(self, x, y, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        if not hasattr(Sparkle, "_pixmap"):
            Sparkle._pixmap = QtGui.QPixmap("stars.png").scaled(
                40, 40, QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        self.setPixmap(Sparkle._pixmap)
        self.move(x, y)
        self.opacity = 1.0

        self.effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setOpacity(self.opacity)

        self.fade_timer = QtCore.QTimer(self)
        self.fade_timer.timeout.connect(self.fade)
        self.fade_timer.start(30)

        self.show()

    def fade(self):
        self.opacity -= 0.05
        if self.opacity <= 0:
            self.fade_timer.stop()
            self.deleteLater()
        else:
            self.effect.setOpacity(self.opacity)


class SparkleLayer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        screen_geometry = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geometry)
        self.show()

    def add_sparkle(self, x, y):
        sparkle = Sparkle(x, y, parent=self)
        sparkle.show()

class BunnyOverlay(QtWidgets.QWidget):
    def __init__(self, image_path, sparkle_layer):
        super().__init__()
        self.sparkle_layer = sparkle_layer
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint |
                            QtCore.Qt.Tool |
                            QtCore.Qt.X11BypassWindowManagerHint)

        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setFixedSize(80, 80)
        self.resize(80, 80)  # Never resize after this

        # Load base image
        self.base_pixmap = QtGui.QPixmap(image_path).scaled(
            80, 80, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        self.label.setPixmap(self.base_pixmap)
        self.pixmap_cache = {}
        # overlay offset from cursor
        self.offset_x = 1000
        self.offset_y = 700

        # Mouse tracking state
        start_pos = QtGui.QCursor.pos()
        self.current_x = start_pos.x()
        self.current_y = start_pos.y()
        self.current_angle = 0

        self.trail_timer = QtCore.QTimer()
        self.trail_timer.timeout.connect(self.spawn_trail)
        self.trail_timer.start(80)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_position)
        self.timer.start(10)

    def spawn_trail(self):
        cursor = QtGui.QCursor.pos()
        x = cursor.x() + random.randint(-50, 50)
        y = cursor.y() + random.randint(-50, 50)
        self.sparkle_layer.add_sparkle(x, y)

    def update_position(self):
        mouse_pos = QtGui.QCursor.pos()
        target_x = mouse_pos.x() + self.offset_x
        target_y = mouse_pos.y() + self.offset_y

        # Smooth toward cursor
        smoothing = 0.15
        self.current_x += (target_x - self.current_x) * smoothing
        self.current_y += (target_y - self.current_y) * smoothing

        dx_lim = self.current_x - mouse_pos.x()
        dy_lim = self.current_y - mouse_pos.y()
        dist = math.hypot(dx_lim, dy_lim)
        if dist > 50:
            factor = 50.0 / dist
            self.current_x = mouse_pos.x() + dx_lim * factor
            self.current_y = mouse_pos.y() + dy_lim * factor

        # Rotation based on smoothed horizontal movement
        dx = mouse_pos.x() - self.current_x
        target_angle = max(min(dx * 2, 15), -15)
        self.current_angle += (target_angle - self.current_angle) * 0.2

        # Rotate and draw bunny into fixed-size canvas
        angle_key = int(round(self.current_angle))
        rotated_pixmap = self.pixmap_cache.get(angle_key)
        if rotated_pixmap is None:
            rotated_pixmap = self.base_pixmap.transformed(
                QtGui.QTransform().rotate(angle_key),
                QtCore.Qt.SmoothTransformation
            )
            self.pixmap_cache[angle_key] = rotated_pixmap

        canvas = QtGui.QPixmap(80, 80)
        canvas.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(canvas)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawPixmap(
            (canvas.width() - rotated_pixmap.width()) // 2,
            (canvas.height() - rotated_pixmap.height()) // 2,
            rotated_pixmap
        )
        painter.end()

        self.label.setPixmap(canvas)

        # Gentle vertical bob
        wobble = math.sin(time.time() * 8) * 5
        self.move(
            int(self.current_x - self.width() // 2),
            int(self.current_y - self.height() // 2 + wobble)
        )

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    sparkle_layer = SparkleLayer()
    overlay = BunnyOverlay("hachiware.png", sparkle_layer)
    overlay.show()
    overlay.raise_()
    sparkle_layer.lower()

    sys.exit(app.exec())
