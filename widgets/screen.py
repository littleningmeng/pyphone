# -*- coding: utf-8 -*-
from os import getenv
from PyQt5.QtWidgets import QFrame
from PyQt5.QtGui import QPainter, QPixmap, QCursor
from logger import logger


class Screen(QFrame):

    DEFAULT_HEIGHT = 1080
    MIN_HEIGHT = 480
    MAX_HEIGHT = 2340
    try:
        SCREEN_HEIGHT = int(getenv("PYPHONE_HEIGHT", DEFAULT_HEIGHT))
        if SCREEN_HEIGHT < MIN_HEIGHT:
            SCREEN_HEIGHT = MIN_HEIGHT
        elif SCREEN_HEIGHT > MAX_HEIGHT:
            SCREEN_HEIGHT = MAX_HEIGHT
    except ValueError:
        SCREEN_HEIGHT = DEFAULT_HEIGHT
    SWIPE_ACC = 1
    HORIZONTAL = 0
    VERTICAL = 1

    def __init__(self, parent=None):
        QFrame.__init__(self, parent)
        # 注意：此处的parent是centralwidget，而非MainWindow
        self.parent = parent
        self.frame = None
        self.default_pixmap = QPixmap(":/app/icons/app/android.png")
        self.pixmap = QPixmap()
        # 使用自定义的鼠标样式
        self.CLICK_CURSOR = QCursor(QPixmap(":/app/icons/app/click.png"), -1, -1)
        self.FORBIDDEN_CURSOR = QCursor(QPixmap(":/app/icons/app/forbidden.png"), -1, -1)
        self.setCursor(self.FORBIDDEN_CURSOR)
        self.touch = None
        self.press_x = -1
        self.press_y = -1
        self.orientation = self.VERTICAL
        self.angle = 0
        self.screen_width = 0
        self.screen_height = 0
        self.disconnect_callback = None

    def set_disconnect_callback(self, callback):
        self.disconnect_callback = callback

    def bind_touch(self, touch):
        self.setCursor(self.CLICK_CURSOR)
        self.touch = touch

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.frame:
            painter.drawPixmap(0, 0, self.default_pixmap)
            return
        self.pixmap.loadFromData(self.frame)
        if self.orientation == self.VERTICAL:
            scaled_pixmap = self.pixmap.scaledToHeight(self.SCREEN_HEIGHT)
        else:
            scaled_pixmap = self.pixmap.scaledToWidth(self.SCREEN_HEIGHT)
        painter.drawPixmap(0, 0, scaled_pixmap)

    def refresh(self, frame):
        # code for debug
        # with open("112.jpg", "wb") as fp:
        #     fp.write(frame)
        self.frame = frame
        if not self.frame:
            self.touch = None
            self.setCursor(self.FORBIDDEN_CURSOR)
        self.update()

    def rotate_xy(self, x, y):
        _x, _y = x, y
        if self.angle == 270:
            _x, _y = y, self.screen_width - x
        elif self.angle == 90:
            _x, _y = self.screen_height - y, x
        elif self.angle == 180:
            _x, _y = x, self.screen_height - y
        return _x, _y

    def on_disconnected(self):
        if callable(self.disconnect_callback):
            self.disconnect_callback()

    def mousePressEvent(self, event):
        if self.touch is None:
            return
        self.press_x, self.press_y = self.rotate_xy(event.x(), event.y())
        if not self.touch.press(self.press_x, self.press_y):
            self.on_disconnected()

    def mouseReleaseEvent(self, event):
        if self.touch is None:
            return
        if not self.touch.release():
            self.on_disconnected()

    def mouseMoveEvent(self, event):
        if self.touch is None:
            return
        cur_x, cur_y = self.rotate_xy(event.x(), event.y())
        if abs(cur_x - self.press_x) > self.SWIPE_ACC or abs(cur_y - self.press_y) > self.SWIPE_ACC:
            if not self.touch.swiping(cur_x, cur_y):
                self.on_disconnected()
            self.press_x = cur_x
            self.press_y = cur_y

    def fit_size(self, real_height, real_width):
        """设备窗口尺寸
        注意：minicap 头部的宽高信息并不会因为屏幕方向的旋转而变化，它是绝对的物理尺寸，垂直握持手机，横向为宽，竖向为高
        """
        rate = 1.0 * Screen.SCREEN_HEIGHT / real_height
        if self.orientation == self.VERTICAL:
            self.screen_width, self.screen_height = int(rate * real_width), Screen.SCREEN_HEIGHT
        else:
            self.screen_width, self.screen_height = Screen.SCREEN_HEIGHT, int(rate * real_width)
        self.setFixedSize(self.screen_width, self.screen_height)
        self.parent.setFixedSize(self.parent.sizeHint())
        if self.touch:
            self.touch.set_rate(rate)
            self.touch.set_max_xy(self.screen_width, self.screen_height)
        else:
            logger.warning("touch is None, touch op is not available!")

    def horizontal(self):
        """调整为横屏模式"""
        self.orientation = self.HORIZONTAL

    def vertical(self):
        """调整为竖屏模式"""
        self.orientation = self.VERTICAL

    def set_orientation(self, angle):
        self.angle = angle
        if angle in (0, 180):
            self.vertical()
        elif angle in (90, 270):
            self.horizontal()

    def get_orientation(self):
        return self.orientation

    def get_screen_height(self):
        # 默认压缩minicap输出的图片尺寸，以提升传输效率
        # 环境变量PYDROID_VIRTUAL_AS_SCREEN置为false时，按照实际尺寸输出，此时可高清录屏
        if getenv("PYDROID_VIRTUAL_AS_SCREEN", "true") == "true":
            return self.SCREEN_HEIGHT
        else:
            return None
