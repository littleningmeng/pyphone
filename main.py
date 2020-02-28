# -*- coding: utf-8 -*-
import sys
from PyQt5 import QtWidgets
from widgets.main_window import MainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
