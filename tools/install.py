# -*- coding: utf-8 -*-
"""
    pydroid's install script
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    This py script is used for install minicap/minicap.so and minitouch to your device
    If you have not installed NDK, please install it and set to your PATH env
    Also adb tools is required
    NDK:
        https://developer.android.com/ndk/downloads/
    ADB:
        https://developer.android.com/studio/releases/platform-tools

    :copyright: © 1998-2018 Tecent.
    :author: littleningmeng
    :date: 2018/12/13
"""

import os
import sys
import time

env_sep_char = ";"
platform_tools = platform_tools_win = "platform-tools"
platform_tools_mac = "platform-tools-mac"
# 项目中暂时没有Linux版本，用户自己下载吧
platform_tools_linux = "platform-tools-linux"
cur_path = os.path.dirname(os.path.abspath(__file__))
if sys.platform == "darwin":
    platform_tools = platform_tools_mac
    env_sep_char = ":"
elif sys.platform.startswith("linux"):
    platform_tools = platform_tools_linux
    env_sep_char = ":"

if not os.environ["PATH"].endswith(env_sep_char):
    os.environ["PATH"] += env_sep_char
os.environ["PATH"] += os.path.join(cur_path, platform_tools)

minicap_bin = "minicap"
minicap_so = "minicap.so"
minitouch_bin = "minitouch"
permission = "rwxr-xr-x"
minicap_path = "./minicap"
minicap_flag_file = os.path.join(minicap_path, ".init")
minitouch_path = "./minitouch"
minitouch_flag_file = os.path.join(minitouch_path, ".init")
minicap_github_repo = "https://github.com/openstf/minicap.git"
minitouch_github_repo = "https://github.com/openstf/minitouch.git"
rotation_watcher_apk = "./RotationWatcher.apk"
cpu_type_cmd = "adb shell \"getprop ro.product.cpu.abi | tr -d '\r'\""
android_version_cmd = "adb shell \"getprop ro.build.version.sdk | tr -d '\r'\""
screen_size_cmd = "adb shell wm size"
device_type_cmd = "adb shell getprop ro.product.model"

minicap_tcp_forward = "adb forward tcp:{port} localabstract:minicap"
minitouch_tcp_forward = "adb forward tcp:{port} localabstract:minitouch"


def err_quit(msg="^"):
    print("ERR: %s" % msg)
    print("**** INIT FAILED ****")
    sys.exit(-1)


def git_clone(repo, dest):
    ret = os.system("git clone %s %s" % (repo, dest))
    if ret != 0:
        err_quit()


def ndk_build(path, flag_file):
    ret = os.system("cd %s && ndk-build" % path)
    if ret != 0:
        err_quit()
    else:
        with open(flag_file, "w") as fp:
            fp.write(time.strftime("%y-%m-%d %H:%M:%S"))


def adb_pipe(cmd):
    return os.popen(cmd).read().strip()


def adb_cmd(cmd):
    return os.system(cmd)


def get_pid_by_ps(process):
    line = adb_pipe("adb shell \"ps | grep %s\"" % process)
    if line:
        try:
            pid = int([part for part in line.split(" ") if part != ""][1])
            return pid
        except Exception:
            return -1
    else:
        return -1


def kill(process):
    pid = get_pid_by_ps(process)
    if pid != -1:
        return adb_cmd("adb shell kill -9 %d" % pid) == 0
    else:
        return True


def kill_rotation_watcher():
    import config
    rw_pid = -1
    if os.path.exists(config.ROTATION_WATCHER_PID_FILE):
        with open(config.ROTATION_WATCHER_PID_FILE, "r") as fp:
            rw_pid = int(fp.read())
    if rw_pid != -1:
        return adb_cmd("adb shell kill -9 %d" % rw_pid) == 0
    else:
        return True


def kill_all_in_thread():
    def killer():
        kill(minicap_bin)
        kill(minitouch_bin)
        kill_rotation_watcher()
    from threading import Thread
    t = Thread(target=killer)
    t.start()


def get_permission_str(file):
    pstr = adb_pipe("adb shell ls -l /data/local/tmp/%s" % file)
    return pstr.split(" ")[0]


def push_to_device(file):
    if os.system("adb push %s /data/local/tmp/" % file) != 0:
        err_quit("fail to push %s" % file)
    if adb_cmd("adb shell chmod 0755 /data/local/tmp/%s" % os.path.basename(file)) != 0:
        err_quit("")


def build_repo(repo, path, flag_file):
    if not os.path.exists(path):
        git_clone(repo, path)
    if not os.path.exists(flag_file):
        if os.system("cd %s && git submodule init && git submodule update" % path) != 0:
            err_quit("")
        ndk_build(path, flag_file)
    else:
        date = open(flag_file, "r").read()
        print("Here is a tip:\n built at %s\nIf you want to REBUILD, "
              "please delete the file: %s" % (date, flag_file))


def is_permission_ok(my_permission):
    return my_permission[1:] == permission


def install(repo, path, bin_file, local_file, flag_file):
    s = get_permission_str(bin_file)
    if not s:
        build_repo(repo=repo, path=path, flag_file=flag_file)
        if not os.path.exists(local_file):
            try:
                os.remove(flag_file)
            except OSError as err:
                print("PLEASE REMOVE FILE %s. FOR ERROR: %s" % (flag_file, err))
            finally:
                err_quit("FILE NOT FOUND ERROR, PLEASE RESTART THIS SCRIPT!!!")
        else:
            push_to_device(local_file)
    elif not is_permission_ok(s):
        print("Reset permission to %s" % permission)
        if adb_cmd("adb shell chmod 0755 /data/local/tmp/%s" % bin_file) != 0:
            err_quit("SET PERMISSION FAILED!!!")
    else:
        print("%s already installed" % bin_file)


def init():
    if os.system("adb --version") != 0:
        err_quit("ADB TOOLS NOT FOUND!!!\n"
                 "If you already installed, please set it to you PATH environment.\n"
                 "Or you can download it here: https://developer.android.com/studio/releases/platform-tools")

    device_type = adb_pipe(device_type_cmd)
    if not device_type:
        err_quit("PLEASE CONNECT YOUR DEVICE!!!")
    abi = adb_pipe(cpu_type_cmd)
    sdk = adb_pipe(android_version_cmd)
    print("------------------------------------------\n"
          "Device: %s, ABI: %s, SDK: %s\n"
          "------------------------------------------" % (device_type, abi, sdk))

    # INSTALL MINICAP
    # clone minicap from github
    # after ndk-build, we'll get minicap and minicap.so file
    # then we copy these two file to our android device's /data/local/tmp path
    # and do not forget to set the right permission: 0755
    local_file = "{minicap_path}/libs/{abi}/{file}".format(minicap_path=minicap_path, abi=abi, file=minicap_bin)
    install(minicap_github_repo, minicap_path, minicap_bin, local_file, minicap_flag_file)
    local_file = os.path.join(minicap_path,
                              "jni/minicap-shared/aosp/libs/android-{sdk}/{abi}/{file}"
                              .format(sdk=sdk, abi=abi, file=minicap_so))
    install(minicap_github_repo, minicap_path, minicap_so, local_file, minicap_flag_file)

    # INSTALL MINITOUCH
    # ref to minicap
    local_file = "{minitouch_path}/libs/{abi}/{file}".format(minitouch_path=minitouch_path, abi=abi, file=minitouch_bin)
    install(minitouch_github_repo, minitouch_path, minitouch_bin, local_file, minitouch_flag_file)

    # INSTALL RotationWatcher
    if not adb_pipe("adb shell pm path jp.co.cyberagent.stf.rotationwatcher | tr -d '\r' | cut -d: -f 2"):
        print("正在安装RotationWatcher，该程序用于检测屏幕方向，请按手机提示完成安装")
        ret = adb_cmd("adb install %s" % rotation_watcher_apk)
        if ret != 0:
            err_quit("")
    else:
        print("RotationWatcher already installed")

    print("Install success")


if __name__ == "__main__":
    init()
