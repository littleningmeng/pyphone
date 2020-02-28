# -*- coding: utf-8 -*-
import redis
import json
import threading
from random import randint
from PyQt5.QtCore import pyqtSignal, QObject
from logger import logger


class IpcSignal(QObject):

    SIG_FRAME = 0
    SIG_TOUCH = 1

    rpc_event = pyqtSignal(int, object)

    def __init__(self):
        QObject.__init__(self)


class Ipc(threading.Thread):

    MIN_SHARE_ID = 91040000
    MAX_SHARE_ID = 91049999
    QUEUE_SIZE_LIMIT = 5
    KEY_LIMIT = 100
    # 请勿修改该数字
    MAGIC_NUM = 170104
    # 作为共享提供者，往Redis队列push屏幕数据，并接收Redis操控队列的数据(默认)
    MODE_PRODUCER = 0
    # 作为共享使用者，从Redis队列读取屏幕数据，并往Redis操控队列发送数据
    MODE_CUSTOMER = 1

    FRAME_QUEUE_PREFIX = "f%d_" % MAGIC_NUM
    TOUCH_QUEUE_PREFIX = "t%d_" % MAGIC_NUM

    CMD_STOP = "!STOP"

    def __init__(self, on_rpc_event, mode=MODE_PRODUCER):
        threading.Thread.__init__(self)
        self.redis_client = None
        # self.signal = None
        self.stop_flag = True
        self.on_rpc_event = on_rpc_event
        self.frame_queue = self.FRAME_QUEUE_PREFIX
        self.touch_queue = self.TOUCH_QUEUE_PREFIX
        self.max_frame_queue_size = self.QUEUE_SIZE_LIMIT
        self.share_id = self.MIN_SHARE_ID
        self.mode = mode
        self.first_frame = True

        self.signal = IpcSignal()
        self.signal.rpc_event.connect(self.on_rpc_event)

    @classmethod
    def make_queue(cls, share_id):
        return "%s%d" % (cls.FRAME_QUEUE_PREFIX, share_id), "%s%d" % (cls.TOUCH_QUEUE_PREFIX, share_id)

    def make_share_id(self):
        share_id = self.MIN_SHARE_ID
        tmp_frame_queue, tmp_touch_queue = self.frame_queue, self.touch_queue
        try_limit = 10
        i = 0
        for i in range(try_limit):
            tmp_frame_queue, tmp_touch_queue = self.make_queue(share_id)
            if not (self.redis_client.exists(tmp_frame_queue) or self.redis_client.exists(tmp_touch_queue)):
                break
            else:
                logger.debug("oh, already exists: %s, %s" % (tmp_frame_queue, tmp_touch_queue))
            share_id = randint(self.MIN_SHARE_ID, self.MAX_SHARE_ID)
        logger.debug("use queue: %s, %s" % (tmp_frame_queue, tmp_touch_queue))
        logger.debug("i is %d" % i)
        if i >= try_limit:
            logger.warning("!!!!!!! i tried !!!!!!!")
            share_id = 201701040323

        return share_id

    def is_valid_share_id(self, share_id):
        return self.MIN_SHARE_ID <= share_id <= self.MAX_SHARE_ID

    def get_mode(self):
        return self.mode

    def is_producer(self):
        return self.mode == self.MODE_PRODUCER

    def is_first_frame(self):
        return self.first_frame

    def set_first_frame(self, b):
        self.first_frame = b

    def get_share_id(self):
        return self.share_id

    def connect(self, host, port, db):
        logger.debug("Trying to connect redis server: %s:%s/%d" % (host, port, db))
        self.redis_client = redis.StrictRedis(host=host, port=int(port),
                                              db=db, socket_keepalive=True,
                                              socket_connect_timeout=2)
        ret = True
        try:
            self.redis_client.ping()
            logger.debug("connected")
        except redis.exceptions.TimeoutError:
            logger.error("timeout")
            ret = False
        except redis.exceptions.ConnectionError:
            logger.error("fail to connect redis server")
            ret = False
        finally:
            if not ret:
                self.redis_client = None

            return ret

    def customer_init(self, host, port, db=3, share_id=MIN_SHARE_ID):
        ret = self.connect(host, port, db)
        if ret:
            self.stop_flag = False
        self.share_id = share_id
        return ret

    def producer_init(self, host, port, db=3):
        ret = self.connect(host, port, db)
        if not ret:
            return ret, -1
        self.stop_flag = False
        self.share_id = self.make_share_id()
        self.frame_queue, self.touch_queue = self.make_queue(self.share_id)
        logger.debug("Redis server connected")
        return True, self.share_id

    def producer_run(self):
        while not self.stop_flag:
            try:
                data = self.redis_client.rpop(self.touch_queue)
            except UnicodeDecodeError as err:
                data = None
                logger.warning("rpop data error: %s" % err)
            if data:
                op_dict = json.loads(data)
                logger.debug("touch event: %s" % op_dict)
                self.signal.rpc_event.emit(IpcSignal.SIG_TOUCH, op_dict)

    def customer_run(self, share_id=MIN_SHARE_ID):
        if self.redis_client is None:
            logger.error("redis not connected")
            return False
        self.frame_queue, self.touch_queue = self.make_queue(share_id)
        # 此时不检查队列是否存在，因为可能消费者先启动了（使用末默认的共享id，碰巧也能工作）
        logger.debug("customer is running, using queue: %s, %s" % (self.frame_queue, self.touch_queue))
        while not self.stop_flag:
            data = self.redis_client.rpop(self.frame_queue)
            if data:
                self.signal.rpc_event.emit(IpcSignal.SIG_FRAME, data)

    def run(self):
        if self.mode == self.MODE_PRODUCER:
            self.producer_run()
        elif self.mode == self.MODE_CUSTOMER:
            self.customer_run()
        else:
            logger.error("bad mode, should be %d or %d" % (self.MODE_CUSTOMER, self.MODE_PRODUCER))

    def push_frame(self, frame):
        if not self.redis_client:
            return False
        self.redis_client.lpush(self.frame_queue, frame)
        self.redis_client.ltrim(self.frame_queue, 0, self.max_frame_queue_size)
        return True

    def push_cmd(self, cmd):
        if not self.redis_client:
            return False
        self.redis_client.lpush(cmd)
        return True

    def stop(self):
        if self.redis_client:
            self.stop_flag = True
            self.redis_client.delete(self.frame_queue)
            self.redis_client.delete(self.touch_queue)
            self.redis_client = None
