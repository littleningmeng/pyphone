# -*- coding: utf-8 -*-
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class Toast(QtWidgets.QDialog):

    FIXED_WIDTH = 300
    FIXED_HEIGHT = 40
    TIME_LONG = 5000
    TIME_SHOT = 3000

    def __init__(self, text, t, parent=None):
        super(Toast, self).__init__(parent)
        self.parent = parent
        self.setModal(False)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        # self.setStyleSheet("background-color: rgb(164, 202, 57);")
        self.setStyleSheet("background-color: rgb(65, 65, 65);")
        # self.setStyleSheet("background-color: rgb(19, 34, 122);")
        self.setFixedHeight(self.FIXED_HEIGHT)
        if text is None:
            text = ""
        self.setFixedWidth(len(text) * 7)
        self.move(self.parent.x() + (self.parent.width() - self.width()) / 2,
                  self.parent.y() + self.parent.height() / 3)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.on_timeout)
        if t <= 0:
            t = self.TIME_SHOT
        self.timer.start(t)

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setSizePolicy(size_policy)

        self.gridLayout = QtWidgets.QGridLayout(self)
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setStyleSheet("color: rgb(255, 255, 255);")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label.setText(text)

    def on_timeout(self):
        self.close()

    @classmethod
    def show_(cls, parent, text, t=TIME_SHOT):
        if not isinstance(parent, QtWidgets.QMainWindow) or not isinstance(parent, QtWidgets.QWidget):
            return
        obj = cls(text, t, parent)
        obj.show()
