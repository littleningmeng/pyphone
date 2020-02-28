# -*- coding: utf-8 -*-
from threading import Thread
from PyQt5.QtCore import pyqtSignal, QObject
from tools import install
import util


class CheckerSignal(QObject):
    result = pyqtSignal(int, str)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)


class Checker:
    SUCCESS = 0
    NO_ADB = 1
    NO_DEVICE = 2
    NO_MINICAP = 3
    BAD_MINICAP_PERMISION = 4
    NO_MINICAP_SO = 5
    BAD_MINICAP_SO_PERMISSION = 6
    NO_MINITOUCH = 7
    BAD_MINITOUCH_PERMISSION = 8
    NO_ROTATION_WATCHER = 9

    def __init__(self, on_check_result):
        self.signal = CheckerSignal()
        self.signal.result.connect(on_check_result)

    def __check_permission(self, code1, code2, file):
        permission = install.get_permission_str(file)
        if not permission:
            self.signal.result.emit(code1, "%s not installed, please run tools/install.py" % file)
            return False
        elif not install.is_permission_ok(permission):
            self.signal.result.emit(
                code2, "%s permission error, shoule be %s\nRUN: adb shell chmod 755 /data/local/tmp/%s" % (
                    file, install.permission, file))
            return False

        return True

    def __adb_cmd(self, port, touch_port):
        if install.adb_cmd("adb --version") != 0:
            self.signal.result.emit(self.NO_ADB, "NO ADB TOOL")
            return
        device_type = install.adb_pipe(install.device_type_cmd)
        if not device_type:
            self.signal.result.emit(self.NO_DEVICE, "设备未连接！\n请连接设备并确认已经开启开发者模式")
            return

        if not self.__check_permission(self.NO_MINICAP, self.BAD_MINICAP_PERMISION, install.minicap_bin):
            return
        if not self.__check_permission(self.NO_MINICAP_SO, self.BAD_MINICAP_SO_PERMISSION, install.minicap_so):
            return
        if not self.__check_permission(self.NO_MINITOUCH, self.BAD_MINITOUCH_PERMISSION, install.minitouch_bin):
            return

        class_path = install.adb_pipe("adb shell pm path jp.co.cyberagent.stf.rotationwatcher"
                                      " | tr -d '\r' | cut -d: -f 2")
        if not class_path:
            self.signal.result.emit(
                self.NO_ROTATION_WATCHER,
                "未安装RotationWatcher，请执行tools/install.py完整安装后再试")
            return

        # util.init_minicap(port) # 注释掉这行，是因为需要在接收到RotationWatcher传回的屏幕方向后再启动minicap
        util.init_minitouch(touch_port)
        util.init_rotation_watcher(class_path)

        self.signal.result.emit(self.SUCCESS, device_type)

    def check(self, port, touch_port):
        p = Thread(target=self.__adb_cmd, args=(port, touch_port))
        p.start()
