# -*- coding: utf-8 -*-
import adb_helper


class KeyEvent:
    CMD = "input keyevent %d"
    HOME = 3
    BACK = 4
    MENU = 82
    POWER = 26

    @classmethod
    def home(cls):
        adb_helper.shell(cls.CMD % cls.HOME)

    @classmethod
    def back(cls):
        adb_helper.shell(cls.CMD % cls.BACK)

    @classmethod
    def menu(cls):
        adb_helper.shell(cls.CMD % cls.MENU)

    @classmethod
    def lock_unlock(cls):
        adb_helper.shell(cls.CMD % cls.POWER)
