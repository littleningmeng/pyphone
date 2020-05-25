# -*- coding: utf-8 -*-
import time
import multiprocessing
from PyQt5.QtCore import QObject, QTimer
from logger import logger
import adb_helper
import util


def watch_rotation(q1, q2, device):
    while True:
        if not q2.empty():
            cmd = q2.get()
            if cmd == "stop":
                break
        r = adb_helper.rotation(device)
        q1.put(r)
        time.sleep(0.1)


class RotationWatcher(QObject):
    ROTATION_TO_ANGLE = [0, 90]

    def __init__(self, on_rotation_changed, queue, device):
        QObject.__init__(self)
        self.rotation = -1
        self.q1 = queue
        self.q2 = multiprocessing.Queue()
        self.device = device
        self.watch_process = None
        self.on_rotation_changed = on_rotation_changed
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timeout)

    def start(self, interval=100):
        logger.debug("RotationWatcher start")
        self.watch_process = util.start_in_progress(watch_rotation, (self.q1, self.q2, self.device))
        self.timer.start(interval)

    def stop(self):
        logger.debug("========= stop RotationWatcher =========")
        self.timer.stop()
        self.q2.put("stop")

    def on_timeout(self):
        if self.q1.empty():
            return
        rotation = self.q1.get()
        if rotation != self.rotation:
            logger.debug("Rotation changed")
            if callable(self.on_rotation_changed):
                self.on_rotation_changed(self.ROTATION_TO_ANGLE[rotation])
        self.rotation = rotation
