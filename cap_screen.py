# -*- coding: utf-8 -*-
import os
import time
import threading
import socket
import struct
import select
from PyQt5 import QtCore
from touch import Touch
from logger import logger
import adb_helper

# 不要修改这两个参数，除非minicap协议变更!
MINICAP_HEAD_SIZE = 24
MINICAP_HEAD_UNPACK_FMT = "<BBIIIIIBB"


def safe_receive(sock, n):
    if sock is None:
        return
    count = 0
    buff_list = []
    while count < n:
        try:
            rs, _, es = select.select([sock], [], [sock], 100)
        except ValueError as err:
            logger.debug("value error: %s" % err)
            return
        except OSError as err:
            logger.debug("os error: %s" % err)
            return
        if len(es) > 0:
            logger.error("socket error")
            return
        elif len(rs) > 0:
            if sock.fileno() != -1:
                try:
                    buff = sock.recv(min(8192, n - count))
                except OSError as err:
                    logger.error("%s" % err)
                    return
                count += len(buff)
                buff_list.append(buff)
            else:
                logger.error("socket fileno is -1")
                return

    return b"".join(buff_list)


class CapScreenSignal(QtCore.QObject):

    connect_result = QtCore.pyqtSignal(int)
    minicap_head = QtCore.pyqtSignal(object)
    frame = QtCore.pyqtSignal(bytes)
    minitouch_connect_result = QtCore.pyqtSignal(bool)
    screenshots = QtCore.pyqtSignal(str, bool)

    def __init__(self):
        QtCore.QObject.__init__(self)


class MinicapHead:
    def __init__(self, buff):

        assert len(buff) == MINICAP_HEAD_SIZE, "fatal: bad buff!!"
        self.version, self.head_size, self.pid, self.real_width, \
            self.real_height, self.virtual_width, self.virtual_height, self.orientation, self.bit_flag \
            = struct.unpack(MINICAP_HEAD_UNPACK_FMT, buff)

    def __repr__(self):
        return """Version: {version}
Head size: {head_size}
Pid: {pid}
Real width: {real_width}
Real height: {real_height}
Virtual width: {virtual_width}
Virtual height: {virtual_height}
Orientation: {orientation}
Bit flag: {bit_flag}""".format(version=self.version, head_size=self.head_size,
                               pid=self.pid, real_width=self.real_width,
                               real_height=self.real_height, virtual_width=self.virtual_width,
                               virtual_height=self.virtual_height,
                               orientation=self.orientation, bit_flag=self.bit_flag)


class CapScreen(threading.Thread):

    def __init__(self,
                 on_connect_result,
                 on_mini_cap_head,
                 on_frame,
                 on_mini_touch_connect_result,
                 on_screenshots_result,
                 screen,
                 host="127.0.0.1",
                 port=8081):
        threading.Thread.__init__(self)
        self.signal = CapScreenSignal()
        self.signal.connect_result.connect(on_connect_result)
        self.signal.minicap_head.connect(on_mini_cap_head)
        self.signal.frame.connect(on_frame)
        self.signal.minitouch_connect_result.connect(on_mini_touch_connect_result)
        self.signal.screenshots.connect(on_screenshots_result)
        self.tcpSocket = None
        self.touch = None
        self.host = host
        self.port = port
        self.touch_port = port + 1
        self.head = None
        self.screen = screen
        self.frame_buff = None

    def start_(self):
        # 以下注释代码仅用于开发者调试，请勿打开
        # if util.init_minicap(self.port):
        #     return
        # if util.init_minitouch(self.port + 1):
        #     return
        logger.debug("cap screen start")
        self.tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
        self.tcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
        self.tcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # TCP_NODELAY在linux系统下可能会要求root权限，先屏蔽
        # self.tcpSocket.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)

        self.tcpSocket.settimeout(1)
        ret = self.tcpSocket.connect_ex((self.host, self.port))
        if ret != 0:
            # todo:
            pass
        self.tcpSocket.setblocking(False)
        self.signal.connect_result.emit(ret)
        self.start()

        self.touch = Touch()
        ret = self.touch.start(self.host, self.touch_port)
        if not ret:
            self.signal.minitouch_connect_result.emit(False)
        else:
            self.screen.bind_touch(self.touch)

    def run(self):
        self.head = self.parse_head()
        self.signal.minicap_head.emit(self.head)
        while self.tcpSocket:
            n_buff = safe_receive(self.tcpSocket, 4)
            if n_buff is None:
                break
            n = struct.unpack("I", n_buff)[0]
            self.frame_buff = safe_receive(self.tcpSocket, n)
            if self.frame_buff is None:
                break
            else:
                self.signal.frame.emit(self.frame_buff)

        self.stop()

    def parse_head(self):
        buff = safe_receive(self.tcpSocket, MINICAP_HEAD_SIZE)
        if buff is None:
            pass
        else:
            return MinicapHead(buff)

    def save_screenshots(self, frame, filepath, show_toast=True):
        logger.debug("save screenshots to %s" % filepath)
        path = os.path.dirname(filepath)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(filepath, "wb") as fp:
            fp.write(frame)
        self.signal.screenshots.emit(filepath, show_toast)

    def screenshots(self, filepath, show_toast=True):
        if not self.frame_buff:
            return False
        if not filepath:
            filepath = "./screenshots/{date}/{time}.jpg".format(
                date=time.strftime("%y-%m-%d"), time=time.strftime("%H-%M-%S"))
        t = threading.Thread(target=self.save_screenshots, args=(self.frame_buff, filepath, show_toast))
        t.start()

        return True

    def is_connected(self):
        return self.tcpSocket is not None

    def handle_rpc_event(self, op_dict):
        if not self.touch:
            return False

        cmd = op_dict.get("cmd")
        if cmd == "screenshots":
            self.screenshots(op_dict.get("filepath"), show_toast=False)
        elif cmd == "shell":
            adb_helper.shell(op_dict.get("param"))
        else:
            self.touch.op(op_dict)

    def stop(self):
        if self.tcpSocket:
            self.tcpSocket.close()
            self.tcpSocket = None
            self.signal.frame.emit(b"")

        if self.touch:
            self.touch.close_socket()
