# -*- coding: utf-8 -*-
import os
from PyQt5.QtCore import QObject, QTimer
from logger import logger
import config


class RotationWatcher(QObject):

    def __init__(self, on_rotation_changed):
        QObject.__init__(self)
        self.on_rotation_changed = on_rotation_changed
        if not os.path.exists(config.ROTATION_WATCHER_PIPE_FILE):
            with open(config.ROTATION_WATCHER_PIPE_FILE, "w") as fp:
                fp.write("")
        self.pipe_fp = open(config.ROTATION_WATCHER_PIPE_FILE, "r")
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timeout)

    def start(self, interval=100):
        self.timer.start(interval)

    def stop(self):
        self.timer.stop()

    def on_timeout(self):
        angle = self.pipe_fp.read()
        if angle == "":
            return
        angle = int(angle)
        logger.debug("RotationChanged: %d" % angle)
        if callable(self.on_rotation_changed):
            self.on_rotation_changed(angle)
