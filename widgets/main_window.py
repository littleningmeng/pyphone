# -*- coding: utf-8 -*-
import os
import threading
import time
import multiprocessing
from collections import deque
from lang import _
from PyQt5 import QtWidgets, QtGui
from PyQt5 import QtCore

from ui.ui_mainwindow import Ui_MainWindow
from cap_screen import CapScreen
from checker import Checker
from rotation_watcher import RotationWatcher
from tools import install
from logger import logger
from recorder import recorder
from ipc import Ipc, IpcSignal
from widgets.toast import Toast
import remote_screen
import version
import util
import config


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.screen.set_disconnect_callback(self.on_disconnected)
        self.setup_tool_bar()
        self.setup_signal()
        self.cap_screen = None
        self.rw = RotationWatcher(self.on_rotation_changed)
        self.checker = Checker(self.on_check_result)
        self.starting_dialog = None
        self.timer = None
        self.check_code = -1
        self.recording = False
        self.record_frames = []
        self.record_timer = QtCore.QTimer()
        self.record_timer.timeout.connect(self.on_record_timeout)
        self.minicap_head = None
        self.ipc = None
        # 是否连接过本地手机
        self.cap_used = False
        self.is_first_start = True
        self.customer_running = False
        self.device_name = ""

        self.share_proc = None
        self.share_val = multiprocessing.Value("i", 0)

        self.frame_timer = None
        self.frame_queue = deque()

        self.donate_scene = QtWidgets.QGraphicsScene(self)
        self.donate_view = QtWidgets.QGraphicsView(self.donate_scene)
        self.donate_view.setWindowTitle(_("Donate"))
        self.donate_scene.addItem(QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(":/app/icons/app/donate.jpg")))

    def setup_tool_bar(self):
        # spacer用于占位，这样其它三个按钮就会居右对齐了
        spacer = QtWidgets.QWidget(self)
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.ui.tool_bar = QtWidgets.QToolBar(self)
        self.ui.tool_bar.addWidget(spacer)
        lock = QtWidgets.QAction(QtGui.QIcon(":/app/icons/app/menu.png"), "", self)
        lock.triggered.connect(self.KeyEvent.lock_unlock)
        self.ui.tool_bar.addAction(lock)
        home = QtWidgets.QAction(QtGui.QIcon(":/app/icons/app/home.png"), "", self)
        home.triggered.connect(self.KeyEvent.home)
        self.ui.tool_bar.addAction(home)
        back = QtWidgets.QAction(QtGui.QIcon(":/app/icons/app/back.png"), "", self)
        back.triggered.connect(self.KeyEvent.back)
        self.ui.tool_bar.addAction(back)
        self.ui.tool_bar.setEnabled(False)
        self.addToolBar(QtCore.Qt.RightToolBarArea, self.ui.tool_bar)

    def setup_signal(self):
        self.ui.actionStart.triggered.connect(self.on_action_start)
        self.ui.actionStop.triggered.connect(self.on_action_stop)

        self.ui.actionMenu.triggered.connect(self.KeyEvent.menu)
        self.ui.actionHome.triggered.connect(self.KeyEvent.home)
        self.ui.actionBack.triggered.connect(self.KeyEvent.back)
        self.ui.actionLock_Unlocak.triggered.connect(self.KeyEvent.lock_unlock)
        self.ui.actionSend_text.triggered.connect(self.on_action_send_text)

        self.ui.actionRecorder.triggered.connect(self.on_action_recorder)

        self.ui.actionShare.triggered.connect(self.on_action_share)
        self.ui.actionRemote_screen.triggered.connect(self.on_action_remote_screen)

        self.ui.actionAbout.triggered.connect(self.on_action_about)
        self.ui.actionDonate.triggered.connect(self.on_action_donate)

        self.ui.actionQuit.triggered.connect(self.close)

    def update_ui_on_started(self, enable=True):
        self.ui.actionStart.setEnabled(not enable)
        self.ui.actionStop.setEnabled(enable)
        self.ui.actionShare.setEnabled(enable)
        self.ui.tool_bar.setEnabled(enable)
        self.ui.menuEdit.setEnabled(enable)

    def update_ui_on_stopped(self):
        self.update_ui_on_started(enable=False)

    def show_starting_dialog(self, title=_("First start"), text=_("Init env, please wait(about 6 seconds)..."),
                             cap_start=False):
        logger.debug("show starting dialog")
        if self.timer:
            return
        max = 100
        self.timer = QtCore.QTimer()
        self.starting_dialog = QtWidgets.QProgressDialog(self)
        self.starting_dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        self.starting_dialog.setWindowTitle(title)
        self.starting_dialog.setLabelText(text)
        self.starting_dialog.setMaximum(max)
        self.starting_dialog.setCancelButton(None)

        def on_start_up_timer():
            value = self.starting_dialog.value()
            if value >= max:
                value = 0
            self.starting_dialog.setValue(value + 1)
            if self.check_code == Checker.SUCCESS:
                ret = install.get_pid_by_ps(install.minicap_bin)
                if ret != -1:
                    if not cap_start:
                        self.dismiss_starting_dialog()
                        return

                    # 阻塞2秒后再连接，否则可能会因为minicap未启动完成导致的连接失败
                    # 该操作会卡住UI，后面可修改为定时器的方式
                    time.sleep(2)
                    self.dismiss_starting_dialog()
                    self.on_action_start()
                elif value >= 99:
                    self.dismiss_starting_dialog()
                    QtWidgets.QMessageBox.critical(
                        self, _(config.TITLE_ERROR),
                        _("Fatal error occurred, please restart"))
                    self.close()

        self.timer.timeout.connect(on_start_up_timer)
        self.timer.start(60)
        self.starting_dialog.show()

    def dismiss_starting_dialog(self):
        logger.debug("dismiss starting dialog")
        self.starting_dialog.close()
        if self.timer:
            self.timer.stop()
        self.timer = None

    def on_action_stop(self):
        if self.cap_screen is None:
            return
        self.cap_screen.stop()
        self.on_action_disable_share()
        self.cap_screen = None

        self.update_ui_on_stopped()

    def on_screenshots_result(self, filename):
        Toast.show_(self, _("Saved: %s") % filename)

    def on_action_start(self):
        if self.customer_running:
            QtWidgets.QMessageBox.information(
                self, _(config.TITLE_INFO),
                _("You are sharing remote phone(%s), please disconnect at first") % self.ipc.get_share_id())
            return

        if self.is_first_start:
            self.checker.check(config.MINICAP_PORT, config.MINITOUCH_PORT)
            self.show_starting_dialog(cap_start=True)
            return

        self.cap_screen = CapScreen(
            self.on_start_result, self.on_minicap_head,
            self.on_frame, self.on_minitouch_connect_result,
            self.on_screenshots_result, self.ui.screen,
            config.MINICAP_HOST, config.MINICAP_PORT
        )
        self.cap_screen.start_()
        self.cap_used = True
        self.ui.actionStart.setEnabled(False)
        self.ui.actionScreenshots.triggered.connect(self.cap_screen.screenshots)

    def on_start_result(self, ret):
        if ret == 0:
            self.update_ui_on_started()
        else:
            self.dismiss_starting_dialog()
            QtWidgets.QMessageBox.critical(
                self, _(config.TITLE_ERROR),
                _("Connect failed, please retry after reset your USB line"))
            self.close()

    def on_minitouch_connect_result(self, ret):
        if not ret:
            QtWidgets.QMessageBox.warning(
                self, _(config.TITLE_WARNING),
                _("Fail to connect minitouch\nThe screen is OK, but you couldn't control"))

    def on_minicap_head(self, head):
        if head:
            self.minicap_head = head
            logger.debug("minicap head: %s" % head)
            self.ui.screen.fit_size(head.real_height, head.real_width)
            self.setFixedSize(self.sizeHint())

    def on_frame(self, frame):
        self.ui.screen.refresh(frame)
        if self.ipc:
            # 注意：只有在producer模式下
            if self.ipc.is_producer():
                self.frame_queue.append(frame)
            else:
                # 拿到第一张图片时，适配下窗口的尺寸
                # 如果没安装numpy和cv2库的话，那就不适配了，看起来比较丑，但也能用
                if self.ipc.is_first_frame():
                    try:
                        import numpy as np
                        import cv2
                    except ImportError:
                        np = None
                        cv2 = None
                        logger.warning("unable to import numpy and cv2")
                    finally:
                        self.ipc.set_first_frame(False)
                    if np and cv2:
                        img = cv2.imdecode(np.fromstring(frame, np.uint8), cv2.IMREAD_COLOR)
                        height, width, _ = img.shape
                        self.ui.screen.fit_size(height, width)

        if self.recording:
            if frame:
                self.record_frames.append(frame)

    def on_check_result(self, code, text):
        self.check_code = code
        if code != Checker.SUCCESS:
            self.dismiss_starting_dialog()
            QtWidgets.QMessageBox.critical(self, "CHECK FAILED", text, QtWidgets.QMessageBox.Ok)
            self.close()
        else:
            if self.is_first_start:
                self.on_action_start()
                self.is_first_start = False
            self.device_name = text
            self.setWindowTitle("%s(%s)" % (version.app_name, text))
            self.rw.start()

    def closeEvent(self, event):
        if self.cap_screen:
            self.cap_screen.stop(kill_minicap=True, kill_minitouch=True, kill_rotation_watcher=True)
        else:
            # 只要连击过本地手机，关闭时都杀minicap/minitouch/rw
            # 这可能会导致另一个正在连接的进程异常
            if self.cap_used:
                install.kill_all_in_thread()
        if self.ipc:
            self.ipc.stop()

        if self.share_proc:
            self.on_disconnect_remote_screen()

        event.accept()

    def on_rotation_changed(self, angle):
        if self.cap_screen:
            self.cap_screen.stop()
        util.init_minicap(port=config.MINICAP_PORT,
                          angle=angle, restart=True,
                          screen_height=self.ui.screen.get_screen_height())
        self.ui.screen.set_orientation(angle)
        self.show_starting_dialog(title=_("Rotating"), text=_("Adapting screen rotation, wait about 3 seconds"),
                                  cap_start=True)

    def on_disconnected(self):
        self.on_action_stop()
        self.setWindowTitle(version.app_name)
        QtWidgets.QMessageBox.critical(
            self, _("Disconnected"),
            _("USB line pulled out or you closed USB-DEBUG mode"))

    def on_rpc_event(self, sig_id, data):
        if sig_id == IpcSignal.SIG_TOUCH:
            if self.cap_screen:
                # now data is a operation dict
                self.cap_screen.handle_rpc_event(data)
        elif sig_id == IpcSignal.SIG_FRAME:
            # now data is a jpg buffer
            self.on_frame(data)

    def on_action_send_text(self):
        """向设备发送文本"""
        if not self.cap_screen:
            return
        text, ret = QtWidgets.QInputDialog.getText(self, _("Send text"), _("Please input the content"))
        if not ret:
            return
        self.cap_screen.touch.send_text(text)

    def on_disconnect_remote_screen(self):
        self.share_val.value = 1
        self.share_proc = None
        logger.debug("kill share process")
        self.ui.actionRemote_screen.setText(_("Connect remote screen..."))

    def on_action_remote_screen(self):
        if self.share_proc:
            return self.on_disconnect_remote_screen()

        share_id, ret = QtWidgets.QInputDialog.getInt(
            self, _("Remote share"), _("Please input your share id"), value=Ipc.MIN_SHARE_ID)
        if not ret:
            return
        frame_queue, tmp = Ipc.make_queue(share_id)
        self.share_val.value = 0
        self.share_proc = multiprocessing.Process(target=remote_screen.start, args=(self.share_val, frame_queue, ))
        self.share_proc.start()
        Toast.show_(self, _("Remote screen started, waiting frame ..."))
        logger.debug("remote screen started, pid: %d" % self.share_proc.pid)
        self.ui.actionRemote_screen.setText(_("Disconnect remote screen..."))
    # 以下屏蔽的代码用于在本UI窗口内显示共享屏幕，因为此操作与连接本地手机互斥，且状态切换可能导致一些难以处理的错误，暂时屏蔽
    # def on_action_remote_screen(self):
    #     # 只有在未连接手机时才可启动
    #     if self.cap_screen:
    #         QtWidgets.QMessageBox.information(
    #             self, _(config.TITLE_INFO),
    #             _("You already connected to local device\nPlease disconnect before sharing"))
    #         return
    #     if self.customer_running:
    #         if self.ipc:
    #             self.ipc.stop()
    #             self.ipc = None
    #
    #         # 清空当前画面，显示初始的LOGO画面
    #         self.on_frame(None)
    #         self.set_tip_message("")
    #         self.customer_running = False
    #         return
    #
    #     self.ipc = Ipc(self.on_rpc_event, Ipc.MODE_CUSTOMER)
    #     share_id, ret = QtWidgets.QInputDialog.getInt(self, _("Remote share"), _("Please input your share id"))
    #     if not ret:
    #         self.ipc = None
    #         return
    #     if not self.ipc.is_valid_share_id(share_id):
    #         QtWidgets.QMessageBox.critical(self, _(config.TITLE_ERROR), _("Illegal share id: %d") % share_id)
    #         self.ipc = None
    #         return
    #
    #     ret = self.ipc.customer_init(config.REDIS_HOST, config.REDIS_PORT, config.REDIS_DB, share_id=share_id)
    #     if not ret:
    #         self.ipc = None
    #         return
    #
    #     self.ipc.start()
    #     self.customer_running = True
    #     self.set_tip_message(_("Sharing with ID: %d") % share_id)

    def update_frame_in_timer(self):
        size = len(self.frame_queue)
        if size < 1:
            return
        elif size > 4:
            self.frame_queue.popleft()

        if self.ipc:
            self.ipc.push_frame(self.frame_queue.popleft())

    def on_action_share(self):
        if self.ipc is None:
            self.on_action_enable_share()
        else:
            self.on_action_disable_share()

    def on_action_enable_share(self):
        if not self.cap_screen:
            return

        self.ipc = Ipc(self.on_rpc_event)
        ret, share_id = self.ipc.producer_init(config.REDIS_HOST, config.REDIS_PORT, config.REDIS_DB)
        if not ret:
            QtWidgets.QMessageBox.critical(self, _(config.TITLE_ERROR), _("Fail to connect share server"))
            self.ipc = None
            return

        # 若定时器未初始化过，则先初始化并绑定信号槽
        if self.frame_timer is None:
            self.frame_timer = QtCore.QTimer()
            self.frame_timer.timeout.connect(self.update_frame_in_timer)

        self.frame_queue.clear()
        self.frame_timer.start(10)

        self.set_tip_message(_("Sharing with ID: %d") % share_id)
        self.ipc.start()

        self.ui.actionShare.setText(_("Disable share"))

    def on_action_disable_share(self):
        if self.ipc is None:
            logger.error("self.ipc is None")
            return
        self.frame_timer.stop()
        self.ipc.stop()
        self.ipc = None
        self.set_tip_message("")

        self.ui.actionShare.setText(_("Enable share"))

    def on_action_about(self):
        QtWidgets.QMessageBox.information(self, "ABOUT", version.about)

    def on_action_donate(self):
        self.donate_view.move(self.x() + self.width(), self.y())
        self.donate_view.show()

    def on_record_timeout(self):
        self.on_record()

    def on_action_recorder(self):
        if self.recording:
            self.on_action_stop_recorder()
        else:
            self.on_action_start_recorder()

    def on_action_start_recorder(self):
        if len(self.record_frames) > 0:
            QtWidgets.QMessageBox.critical(
                self, _(config.TITLE_INFO),
                _("Please try after current video been saved"))
            return
        self.record_timer.start(config.MAX_RECORD_MIN * 60 * 1000)
        self.recording = True
        self.set_tip_message(_("Recording (time limit %d min)...") % config.MAX_RECORD_MIN)
        mp4file = os.path.join(config.VIDEO_DIR, time.strftime("%y-%m-%d/%H-%M-%S.mp4"))
        _dir = os.path.dirname(mp4file)
        if not os.path.exists(_dir):
            try:
                os.makedirs(_dir)
            except OSError as err:
                logger.error("fail to create video path: %s" % err)
                mp4file = "tmp.mp4"
        orientation = self.ui.screen.get_orientation()
        if orientation == self.ui.screen.VERTICAL:
            logger.debug("VERTICAL recorder")
            width, height = self.minicap_head.virtual_width, self.minicap_head.virtual_height
        else:
            logger.debug("HORIZONTAL recorder")
            width, height = self.minicap_head.virtual_height, self.minicap_head.virtual_width
        recorder.init(mp4file, 40, width, height)
        self.record_frames = []

        self.ui.actionRecorder.setText(_("Stop video recorder ..."))

    def on_action_stop_recorder(self):
        self.recording = False
        if self.record_timer.isActive():
            self.record_timer.stop()

        if len(self.record_frames) < 1:
            QtWidgets.QMessageBox.critical(
                self, _(config.TITLE_ERROR), _("No any frame, your screen didn't change!")
            )
            self.set_tip_message("")
            self.ui.actionRecorder.setText(_("Start video recorder ..."))
            return

        self.set_tip_message(_("Saving video ..."))
        self.ui.actionRecorder.setEnabled(self.recording)

        def save_task(frames):
            recorder.write_frames(frames)
            mp4file = recorder.finish()
            self.set_tip_message("%s" % mp4file.replace("\\", "/"))
            self.record_frames = []
            self.ui.actionRecorder.setEnabled(not self.recording)
            self.ui.actionRecorder.setText(_("Start video recorder ..."))

        task = threading.Thread(target=save_task, args=(self.record_frames,))
        task.start()

    def set_tip_message(self, text):
        if text == "":
            text = "%s(%s)" % (version.app_name, self.device_name)
        self.setWindowTitle(text)

    class KeyEvent:
        CMD = "adb shell input keyevent %d"
        HOME = 3
        BACK = 4
        MENU = 82
        POWER = 26

        @classmethod
        def home(cls):
            install.adb_cmd(cls.CMD % cls.HOME)

        @classmethod
        def back(cls):
            install.adb_cmd(cls.CMD % cls.BACK)

        @classmethod
        def menu(cls):
            install.adb_cmd(cls.CMD % cls.MENU)

        @classmethod
        def lock_unlock(cls):
            install.adb_cmd(cls.CMD % cls.POWER)
