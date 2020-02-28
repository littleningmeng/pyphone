# -*- coding: utf-8 -*-
from multiprocessing import Process
from logger import logger
from tools import install
import config


def start_minicap(port, angle=0, screen_height=None):
    install.kill(install.minicap_bin)
    real_size = install.adb_pipe("adb shell wm size").split("\n")[0].split(":")[1].strip()
    if screen_height is None:
        virtual_size = real_size
        logger.debug("use real size %s" % real_size)
    else:
        tmp = real_size.split("x")
        if len(tmp) != 2:
            logger.warning("adb size output may be error: %s" % real_size)
            virtual_size = real_size
        else:
            real_width, real_height = int(tmp[0].split()[0]), int(tmp[1].split()[0])
            if screen_height > real_height:
                screen_height = real_height
            assert real_height != 0
            rate = 1.0 * screen_height / real_height
            screen_width = int(rate * real_width)
            virtual_size = "%dx%d" % (screen_width, screen_height)
            logger.debug("use scaled size %s" % virtual_size)

    tcp_forward = install.minicap_tcp_forward.format(port=port)
    logger.debug("===========%s==========" % real_size)
    s = "{tcp_forward} && adb shell LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/minicap " \
        "-P {real_size}@{virtual_size}/{angle} -S"
    cmd = s.format(tcp_forward=tcp_forward, real_size=real_size, virtual_size=virtual_size, angle=angle)
    logger.debug("===>>= start minicap cmd: %s" % cmd)
    return install.adb_cmd(cmd)


def start_minitouch(port):
    tcp_forward = install.minitouch_tcp_forward.format(port=port)
    cmd = "{tcp_forward} && adb shell /data/local/tmp/minitouch".format(tcp_forward=tcp_forward)
    logger.debug("**** start minitouch cmd: %s" % cmd)
    return install.adb_cmd(cmd)


def input_text(text=""):
    return install.adb_cmd("adb shell input text \"%s\"" % text)


def start_in_progress(target, args):
    p = Process(target=target, args=args)
    p.start()


def init_minicap(port, angle=0, restart=False, screen_height=None):
    if restart or not install.adb_pipe('adb shell "ps | grep minicap"'):
        logger.debug("start minicap")
        start_in_progress(target=start_minicap, args=(port, angle, screen_height))
        return True
    else:
        logger.debug("minicap tcp forward")
        install.adb_cmd(install.minicap_tcp_forward.format(port=port))
        return False


def init_minitouch(port):
    if not install.adb_pipe('adb shell "ps | grep minitouch"'):
        logger.info("start minitouch")
        start_in_progress(target=start_minitouch, args=(port,))
        return True
    else:
        logger.debug("minitouch tcp forward")
        install.adb_cmd(install.minitouch_tcp_forward.format(port=port))
        return False


def init_rotation_watcher(class_path, pipe_file=config.ROTATION_WATCHER_PIPE_FILE):
    pid = install.get_pid_by_ps("app_process")
    if pid == -1:
        cmd = "adb shell \"export CLASSPATH=\"{class_path}\";" \
              "exec app_process /system/bin " \
              "jp.co.cyberagent.stf.rotationwatcher.RotationWatcher\" " \
              "> {pipe_file}".format(class_path=class_path, pipe_file=pipe_file)
        logger.debug(cmd)
        from multiprocessing import Process
        p = Process(target=install.adb_cmd, args=(cmd, ))
        p.start()
        logger.info("start rotationwatcher")
        from time import sleep
        sleep(1)
        pid = install.get_pid_by_ps("app_process")
        logger.debug("RotationWatcher PID: %d" % pid)

    with open(config.ROTATION_WATCHER_PID_FILE, "w") as fp:
        fp.write("%d" % pid)
