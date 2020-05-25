# -*- coding: utf-8 -*-
import sys
from ppadb.client import Client as AdbClient
from logger import logger
import config
import share
import util

client = AdbClient(host=config.ADB_HOST, port=config.ADB_PORT)
try:
    devices = client.devices()
except RuntimeError:
    logger.error("Adb server not started")
    sys.exit(-1)
else:
    if not devices:
        logger.error("No any device\bPlease connect your phone and turn on the USB debug mode!")
        sys.exit(-1)


def device_connected(f):
    def inner_func(*args, **kwargs):
        if current_device() is None:
            print("No any device connected")
            return
        try:
            return f(*args, **kwargs)
        except RuntimeError:
            print("Maybe lost device connection")
            return

    return inner_func


def device_serial_no_list():
    if config.DEBUG:
        return ["8BKX1BBRW", "a", "b", "c"]
    return [device.get_serial_no() for device in devices]


def choose_device(serial_no):
    logger.debug("choose device:%s" % serial_no)
    share.current_device = client.device(serial_no)
    return share.current_device


def current_device():
    return share.current_device


@device_connected
def device_real_size():
    size = current_device().wm_size()
    return size.width, size.height


@device_connected
def kill(pid, device=None):
    if pid is None or not pid.isdigit():
        return False
    if device is None:
        device = current_device()
        if device is None:
            return False
    return device.shell("kill -9 %s" % pid) == "" if device else False


@device_connected
def p_kill(process):
    device = current_device()
    pid = device.get_pid(process)
    return kill(pid, device)


@device_connected
def start_mini_touch(port=config.MINITOUCH_PORT):
    device = current_device()
    if device.get_pid(config.MINITOUCH):
        return True
    device.forward("tcp:%d" % port, "localabstract:%s" % config.MINITOUCH)
    util.start_in_progress(device.shell, (config.MINITOUCH_PATH, ))
    return True


@device_connected
def start_mini_cap(port=config.MINICAP_PORT, angle=0, virtual_width=config.DEFAULT_WIDTH):
    device = current_device()
    pid = device.get_pid(config.MINICAP)
    if pid:
        return True
    real_width, real_height = device_real_size()
    rate = real_height / real_width
    virtual_height = int(rate * virtual_width)
    device.forward("tcp:%d" % port, "localabstract:%s" % config.MINICAP)
    cmd = "LD_LIBRARY_PATH={ld_library_path} {minicap_path} -P {real_width}x{real_height}@{virtual_width}x{virtual_height}/{angle} -S".format(
        ld_library_path=config.ANDROID_TMP_PATH, minicap_path=config.MINICAP_PATH,
        real_width=real_width, real_height=real_height,
        virtual_width=virtual_width, virtual_height=virtual_height,
        angle=angle)
    logger.debug("start minicap by cmd:\n%s" % cmd)
    util.start_in_progress(device.shell, (cmd, ))
    return True


@device_connected
def restart_mini_cap(port=config.MINICAP_PORT, angle=0, virtual_width=config.DEFAULT_WIDTH):
    device = current_device()
    pid = device.get_pid(config.MINICAP)
    if pid:
        kill(pid, device)
    return start_mini_cap(port, angle, virtual_width)


@device_connected
def start_rotation_watcher(pipe_file):
    device = current_device()
    pid = device.get_pid("app_process")
    if pid:
        logger.debug("RotationWatcher already started")
        return True

    class_path = device.shell("pm path jp.co.cyberagent.stf.rotationwatcher | tr -d '\r' | cut -d: -f 2")
    if not class_path:
        return False
    class_path = class_path.strip()
    cmd = "\"export CLASSPATH={class_path}; exec app_process /system/bin " \
          "jp.co.cyberagent.stf.rotationwatcher.RotationWatcher\" > {pipe_file}".format(class_path=class_path,
                                                                                        pipe_file=pipe_file)
    logger.debug(cmd)
    util.start_in_progress(target=device.shell, args=(cmd, ))

    return True


@device_connected
def input_text(text):
    device = current_device()
    device.input_text(text)


def rotation(device=None):
    """获取当前手机屏幕方向：0竖 1横"""
    if device is None:
        device = current_device()
        if device is None:
            return 0
    s = device.shell("dumpsys input | grep 'SurfaceOrientation' | awk '{print $2}'").strip()
    try:
        return int(s)
    except ValueError:
        return 0


@device_connected
def shell(param):
    device = current_device()
    return device.shell(param)
