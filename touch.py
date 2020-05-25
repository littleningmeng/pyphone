# -*- coding: utf-8 -*-
import socket
import time
from threading import Thread
from logger import logger
import adb_helper
import config


class Touch:

    CLICK = "click"
    SWIPE = "swipe"
    TEXT = "text"
    # 上滑（从下向上）
    SWIPE_DIR_UP = "up"
    # 下滑（从上向下）
    SWIPE_DIR_DOWN = "down"
    # 左滑（从右向左）
    SWIPE_DIR_LEFT = "left"
    # 右滑（从左向右）
    SWIPE_DIR_RIGHT = "right"

    SWIPE_RANGE = 50
    SWIPE_STEP = 1

    def __init__(self):
        self.pid = -1
        self.tcp_sock = None
        self.rate = 1
        self.max_x = 0
        self.max_y = 0

    def parse_mitouch_head(self):
        buff = []
        try:
            data = self.tcp_sock.recv(1024).decode("utf-8")
            buff.append(data)
        except socket.timeout:
            pass
        head = "".join(buff)
        logger.debug("minitouch head: %s" % head)
        if head.find("$") < 0:
            logger.warning("minitouch pid not found")
            # 此处置0，后面杀进程时并不使用这个pid
            self.pid = 0
        else:
            self.pid = int(head.split("$")[-1].strip())
            logger.info("minitouch pid: %d" % self.pid)

    def start(self, host, port):
        logger.debug("connect minitouch on %s:%d" % (host, port))
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.settimeout(0.8)
        ret = self.tcp_sock.connect_ex((host, port))
        if ret != 0:
            logger.error("failed")
            return False
        logger.debug("connected")
        t = Thread(target=self.parse_mitouch_head)
        t.start()
        return True

    def close_socket(self):
        if self.tcp_sock:
            self.tcp_sock.close()
            self.tcp_sock = None

    def stop(self):
        if self.tcp_sock:
            self.tcp_sock.close()
            self.tcp_sock = None
        if self.pid != -1:
            ret = adb_helper.p_kill(config.MINITOUCH)
            if not ret:
                logger.error("fail to kill minitouch")
            else:
                self.pid = -1

    def send_touch_cmd(self, cmd):
        try:
            self.tcp_sock.sendall(cmd)
        except ConnectionAbortedError as err:
            logger.error("socket already closed by remote: %s" % err)
            return False
        except BrokenPipeError as err:
            logger.error("socket is broken: %s" % err)
            return False
        return True

    def press(self, x, y):
        logger.debug("press at %d, %d" % (x, y))
        return self.send_touch_cmd(b"d 0 %d %d 10\nc\n" % (int(x / self.rate), int(y / self.rate)))

    def release(self):
        logger.debug("release")
        return self.send_touch_cmd(b"u 0\nc\n")

    def swiping(self, x, y):
        # logger.debug("swiping at %d, %d" % (x, y))
        return self.send_touch_cmd(b"m 0 %d %d 10\nc\n" % (int(x / self.rate), int(y / self.rate)))

    def set_rate(self, rate):
        self.rate = rate

    @staticmethod
    def swipe_delay(seconds=0.01):
        if seconds < 0.1:
            for i in range(100000):
                pass
        else:
            time.sleep(seconds)

    @staticmethod
    def _reset_xy(x0, y0, x1, y1):
        if x0 == -1:
            x0 = x1
        if y0 == -1:
            y0 = y1
        return x0, y0
    
    def op(self, op_dict):
        # 如果是滑动操作，则放到单独的线程中去做
        if op_dict.get("cmd") == self.SWIPE:
            t = Thread(target=self._op, args=(op_dict, ))
            t.start()
            return t
        else:
            self._op(op_dict)
        
    def _op(self, op_dict):
        cmd = op_dict.get("cmd")
        if cmd is None:
            return False
        if cmd == self.CLICK:
            x, y = op_dict.get("x", 0), op_dict.get("y", 0)
            self.press(x, y)
        elif cmd == self.SWIPE:
            logger.debug("swipe")
            _dir = op_dict.get("direction", -1)
            from_x, from_y, to_x, to_y = op_dict.get("from_x", -1), op_dict.get("from_y", -1), \
                op_dict.get("to_x", -1), op_dict.get("to_y", -1)
            if _dir not in (self.SWIPE_DIR_UP, self.SWIPE_DIR_DOWN, self.SWIPE_DIR_LEFT, self.SWIPE_DIR_RIGHT):
                logger.error("bad direction: %s" % _dir)
                return False
            target_x, target_y = int(self.max_x / 2), int(self.max_y / 2)
            logger.debug("target_x, target_y = %d, %d" % (target_x, target_y))
            # 特别的，如果指明了这是了"border": "yes"，则从边缘开始操作，一般用于下拉时调出设置面板或右滑动返回上一页面
            border = op_dict.get("border", "no")
            step = op_dict.get("step", 1)
            # 网上滑动做了特别处理，用于解决多屏截图的问题，其它方向暂不修改 comment by apache 2020/4/14
            if _dir == self.SWIPE_DIR_UP:
                logger.debug("up")
                if to_y != -1:
                    target_y = to_y
                elif border == "yes":
                    target_y = self.max_y
                from_x, from_y = Touch._reset_xy(from_x, from_y, target_x, target_y)
                logger.debug("from_x, from_y = %d, %d" % (from_x, from_y))
                self.press(from_x, from_y)
                y = from_y
                while y >= target_y:
                    self.swipe_delay()
                    self.swiping(target_x, y)
                    y -= step

            elif _dir == self.SWIPE_DIR_RIGHT:
                logger.debug("right")
                if border == "yes":
                    target_x = 0
                    target_y = int(self.max_y / 3)
                self.press(target_x, target_y)
                for i in range(0, self.SWIPE_RANGE, self.SWIPE_STEP):
                    if target_x + i > self.max_x:
                        break
                    self.swipe_delay()
                    self.swiping(target_x + i, target_y)
            elif _dir == self.SWIPE_DIR_DOWN:
                logger.debug("down")
                if border == "yes":
                    target_y = 0
                self.press(target_x, target_y)
                for i in range(0, self.SWIPE_RANGE, self.SWIPE_STEP):
                    if target_y + i > self.max_y:
                        break
                    self.swipe_delay()
                    self.swiping(target_x, target_y + i)
            elif _dir == self.SWIPE_DIR_LEFT:
                if border == "yes":
                    target_x = self.max_x
                self.press(target_x, target_y)
                logger.debug("left")
                for i in range(0, self.SWIPE_RANGE, self.SWIPE_STEP):
                    if target_x - i < 0:
                        break
                    self.swipe_delay()
                    self.swiping(target_x - i, target_y)
        elif cmd == self.TEXT:
            text = op_dict.get("text", "")
            if text is None:
                return False
            self.send_text(text)
            return True
        else:
            return False

        if cmd == self.SWIPE:
            self.swipe_delay(1)
        self.release()

        return True

    def set_max_xy(self, x, y):
        logger.debug("max x, y = %d, %d" % (x, y))
        self.max_x, self.max_y = x, y

    @staticmethod
    def send_text(text):
        adb_helper.input_text(text)
