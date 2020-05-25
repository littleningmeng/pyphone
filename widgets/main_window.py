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
from rotation_watcher import RotationWatcher
from logger import logger
from recorder import recorder
from ipc import Ipc, IpcSignal
from key_event import KeyEvent
from widgets.toast import Toast
import remote_screen
import adb_helper
import version
import config


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.setup_ui()
        self.ui.screen.set_disconnect_callback(self.on_disconnected)
        self.setup_signal()
        self.cap_screen = None
        self.queue = multiprocessing.Queue()
        self.starting_dialog = None
        self.timer = None
        self.check_code = -1
        self.recording = False
        self.record_frames = []
        self.record_timer = QtCore.QTimer()
        self.record_timer.timeout.connect(self.on_record_timeout)
        self.mini_cap_head = None
        self.ipc = None
        # 是否连接过本地手机
        self.cap_used = False
        self.is_first_start = True
        self.customer_running = False
        self.device_name = ""
        self.angle = 0
        self.virtual_width = config.DEFAULT_WIDTH
        self.rotation_watcher = None
        self.share_proc = None
        self.share_val = multiprocessing.Value("i", 0)

        self.frame_timer = None
        self.frame_queue = deque()

        self.donate_scene = QtWidgets.QGraphicsScene(self)
        self.donate_view = QtWidgets.QGraphicsView(self.donate_scene)
        self.donate_view.setWindowTitle(_("Donate"))
        self.donate_scene.addItem(QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap(":/app/icons/app/donate.jpg")))

    def on_image_quality_action_triggered(self, checked, width, height):
        """选择画质"""
        logger.debug("select image quality %dx%d" % (width, height))
        if width == self.virtual_width:
            return
        self.on_rotation_changed(self.angle, width)
        self.virtual_width = width

    def on_device_action_triggered(self, checked, serial_no):
        """选择一个设备"""
        adb_helper.choose_device(serial_no)
        self.setWindowTitle("pyphone(%s)" % serial_no)
        self.ui.actionStart.setEnabled(True)
        real_width, real_height = adb_helper.device_real_size()
        assert real_height > 0, "Ops! real_height less than 0!"
        rate = real_height / real_width
        if real_width not in config.IMAGE_QUALITIES:
            config.IMAGE_QUALITIES.append(real_width)
        logger.debug("Image qualities: %s" % config.IMAGE_QUALITIES)
        self.ui.menuImageQuality.clear()
        for width in config.IMAGE_QUALITIES:
            height = int(rate * width)
            widget = QtWidgets.QRadioButton("%dx%d" % (width, height), self)
            if width == config.DEFAULT_WIDTH:
                widget.setChecked(True)
            action = QtWidgets.QWidgetAction(self)
            action.setDefaultWidget(widget)
            widget.clicked.connect(lambda checked_, width_=width, height_=height:
                                   self.on_image_quality_action_triggered(checked_, width_, height_))
            self.ui.menuImageQuality.addAction(action)

    def setup_ui(self):
        self.ui.setupUi(self)
        serial_no_list = adb_helper.device_serial_no_list()
        logger.debug("devices: %s" % serial_no_list)
        # 只有一个设备时，默认选中
        if len(serial_no_list) == 1:
            self.on_device_action_triggered(True, serial_no_list[0])
        for sn in serial_no_list:
            action = QtWidgets.QAction(sn, self)
            action.triggered.connect(lambda checked_, sn_=sn, action_=action:
                                     self.on_device_action_triggered(checked_, sn_))
            self.ui.menuDevices.addAction(action)

    def setup_signal(self):
        self.ui.actionStart.triggered.connect(self.on_action_start)
        self.ui.actionVertical.triggered.connect(lambda triggered, angle=0: self.on_rotation_changed(angle))
        self.ui.actionHorizontal.triggered.connect(lambda triggered, angle=90: self.on_rotation_changed(angle))
        self.ui.actionStop.triggered.connect(self.on_action_stop)
        self.ui.actionMenu.triggered.connect(KeyEvent.menu)
        self.ui.actionHome.triggered.connect(KeyEvent.home)
        self.ui.actionBack.triggered.connect(KeyEvent.back)
        self.ui.actionLock_Unlocak.triggered.connect(KeyEvent.lock_unlock)
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
        self.ui.menuEdit.setEnabled(enable)
        self.ui.menuDevices.setEnabled(not enable)

    def update_ui_on_stopped(self):
        self.update_ui_on_started(enable=False)

    def show_starting_dialog(self, title=_("First start"),
                             text=_("Init env, please wait(about 6 seconds)..."),
                             cap_start=False):
        logger.debug("show starting dialog")
        if self.timer:
            return
        max_value = 30
        self.timer = QtCore.QTimer()
        self.starting_dialog = QtWidgets.QProgressDialog(self)
        self.starting_dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        self.starting_dialog.setWindowTitle(title)
        self.starting_dialog.setLabelText(text)
        self.starting_dialog.setMaximum(max_value)
        self.starting_dialog.setCancelButton(None)

        def on_start_up_timer():
            value = self.starting_dialog.value()
            self.starting_dialog.setValue(value + 1)
            pid = adb_helper.current_device().get_pid(config.MINICAP)
            if pid:
                logger.debug("minicap pid is %s" % pid)
                if not cap_start:
                    self.dismiss_starting_dialog()
                    return
                self.dismiss_starting_dialog()
                self.on_action_start(ready=True)
                mini_touch_pid = adb_helper.current_device().get_pid(config.MINITOUCH)
                logger.debug("minitouch pid is %s" % mini_touch_pid)
            elif value >= max_value - 1:
                self.dismiss_starting_dialog()
                QtWidgets.QMessageBox.critical(
                    self, _(config.TITLE_ERROR),
                    _("Fatal error occurred, please restart"))
                self.close()

        self.timer.timeout.connect(on_start_up_timer)
        self.timer.start(100)
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
        self.rotation_watcher.stop()

        self.update_ui_on_stopped()

    def on_screenshots_result(self, filename, show_toast=True):
        if show_toast:
            Toast.show_(self, _("Saved: %s") % filename)

    def on_action_start(self, ready=False):
        if not ready:
            self.rotation_watcher = RotationWatcher(self.on_rotation_changed, self.queue, adb_helper.current_device())
            self.rotation_watcher.start()
            adb_helper.start_mini_touch()
            self.show_starting_dialog(cap_start=True)
            return

        self.cap_screen = CapScreen(self.on_start_result,
                                    self.on_mini_cap_head,
                                    self.on_frame,
                                    self.on_mini_touch_connect_result,
                                    self.on_screenshots_result,
                                    self.ui.screen,
                                    config.MINICAP_HOST,
                                    config.MINICAP_PORT)

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

    def on_mini_touch_connect_result(self, ret):
        if not ret:
            QtWidgets.QMessageBox.warning(
                self, _(config.TITLE_WARNING),
                _("Fail to connect minitouch\nThe screen is OK, but you couldn't control"))

    def on_mini_cap_head(self, head):
        if not head:
            return
        self.mini_cap_head = head
        w, h = adb_helper.device_real_size()
        self.ui.screen.set_real_size(w, h)
        self.setFixedSize(self.sizeHint())

    def on_frame(self, frame):
        self.ui.screen.refresh(frame)
        if self.ipc:
            # 注意：只有在producer模式下
            if self.ipc.is_producer():
                self.frame_queue.append(frame)
        if self.recording:
            if frame:
                self.record_frames.append(frame)

    def closeEvent(self, event):
        if self.cap_screen:
            self.cap_screen.stop()

        adb_helper.p_kill(config.MINICAP)
        adb_helper.p_kill(config.MINITOUCH)
        if self.rotation_watcher:
            self.rotation_watcher.stop()

        if self.ipc:
            self.ipc.stop()

        if self.share_proc:
            self.on_disconnect_remote_screen()

        event.accept()

    def on_rotation_changed(self, angle, virtual_width=config.DEFAULT_WIDTH):
        logger.debug("on_rotation_changed. angle={}".format(angle))
        self.angle = angle
        if self.cap_screen:
            self.cap_screen.stop()
        adb_helper.restart_mini_cap(angle=angle, virtual_width=virtual_width)
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
            QtWidgets.QMessageBox.critical(
                self, _(config.TITLE_ERROR),
                _("Fail to connect redis server\n%s:%d" % (config.REDIS_HOST, config.REDIS_PORT)))
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
        QtWidgets.QMessageBox.information(self, _("About"), version.about)

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
            width, height = self.mini_cap_head.virtual_width, self.mini_cap_head.virtual_height
        else:
            logger.debug("HORIZONTAL recorder")
            width, height = self.mini_cap_head.virtual_height, self.mini_cap_head.virtual_width
        recorder.init(mp4file, 40, width, height)
        self.record_frames = []

        self.ui.actionRecorder.setText(_("Stop video recorder ..."))

    def on_action_stop_recorder(self):
        self.recording = False
        if self.record_timer.isActive():
            self.record_timer.stop()

        if len(self.record_frames) < 1:
            QtWidgets.QMessageBox.critical(self, _(config.TITLE_ERROR), _("No any frame, your screen didn't change!"))
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
