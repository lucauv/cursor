import sys
import time
import math
import random
from PySide6 import QtCore, QtGui, QtWidgets

# Overlay offset relative to the cursor
OFFSET_X = 60
OFFSET_Y = 60


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
        # Keep sparkles behind the overlay
        sparkle.lower()

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
        self.base_pixmap = QtGui.QPixmap(image_path)
        assert self.base_pixmap.size() == QtCore.QSize(80, 80)
        self.label.setPixmap(self.base_pixmap)
        self.pixmap_cache = {}
        # overlay offset from cursor
        self.offset_x = OFFSET_X
        self.offset_y = OFFSET_Y

        # Mouse tracking state
        start_pos = QtGui.QCursor.pos()
        self.current_x = start_pos.x()
        self.current_y = start_pos.y()
        self.current_angle = 5

        self.trail_timer = QtCore.QTimer()
        self.trail_timer.timeout.connect(self.spawn_trail)
        self.trail_timer.start(80)

        # Track previous mouse position for sway effect
        self.prev_mouse_x = self.current_x
        self.sway_offset = 70

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_position)
        self.timer.start(10)

    def spawn_trail(self):
        """Spawn sparkle particles at the overlay's position."""
        x = int(self.current_x - 20 + random.randint(-10, 10))
        y = int(self.current_y - 20 + random.randint(-10, 10))
        self.sparkle_layer.add_sparkle(x, y)

    def update_position(self):
        mouse_pos = QtGui.QCursor.pos()

        # Track mouse delta
        dx_mouse = mouse_pos.x() - self.prev_mouse_x
        self.prev_mouse_x = mouse_pos.x()

        # Update sway_offset based on movement
        self.sway_offset += (dx_mouse * 3 + self.sway_offset) * 0.3  # Faster reaction, more dramatic
        self.sway_offset = max(min(self.sway_offset, 80), -80)

        # Combine with static offset
        target_x = mouse_pos.x() + self.offset_x + self.sway_offset
        target_y = mouse_pos.y() + self.offset_y

        # Smooth motion
        smoothing = 0.4
        self.current_x += (target_x - self.current_x) * smoothing
        self.current_y += (target_y - self.current_y) * smoothing

        # Clamp distance from mouse to avoid going too far
        dx_lim = self.current_x - mouse_pos.x()
        dy_lim = self.current_y - mouse_pos.y()
        dist = math.hypot(dx_lim, dy_lim)
        if dist > 70:
            factor = 70.0 / dist
            self.current_x = mouse_pos.x() + dx_lim * factor
            self.current_y = mouse_pos.y() + dy_lim * factor

        # Rotation based on smoothed sway
        target_angle = max(min(self.sway_offset * 0.15, 25), -25)
        self.current_angle += (target_angle - self.current_angle) * 0.2

        # Rotate bunny
        angle_key = int(round(self.current_angle))
        rotated_pixmap = self.pixmap_cache.get(angle_key)
        if rotated_pixmap is None:
            image = self.base_pixmap.toImage()
            rotated_image = image.transformed(
                QtGui.QTransform().rotate(angle_key),
                QtCore.Qt.FastTransformation
            )
            rotated_pixmap = QtGui.QPixmap.fromImage(rotated_image)
            self.pixmap_cache[angle_key] = rotated_pixmap

        # Draw to canvas
        canvas_size = 120
        canvas = QtGui.QPixmap(canvas_size, canvas_size)
        canvas.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(canvas)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.drawPixmap(
            (canvas_size - rotated_pixmap.width()) // 2,
            (canvas_size - rotated_pixmap.height()) // 2,
            rotated_pixmap
        )
        painter.end()

        self.label.setPixmap(canvas)
        self.label.setFixedSize(canvas_size, canvas_size)
        self.resize(canvas_size, canvas_size)

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
