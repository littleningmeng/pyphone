# -*- coding: utf-8 -*-
"""
    pyphone's install script
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    This py script is used for install minicap/minicap.so and minitouch to your device
    
    :copyright: © 1998-2018 Tecent.
    :author: ehcapa
    :date: 2020/4/27
"""

import os
import sys
from ppadb.client import Client as AdbClient

minicap = "minicap"
minicap_so = "minicap.so"
minitouch = "minitouch"
permission = "rwxr-xr-x"
minicap_path = "../deps/minicap"
minicap_flag_file = os.path.join(minicap_path, ".init")
minitouch_path = "../deps/minitouch"
minitouch_flag_file = os.path.join(minitouch_path, ".init")
dest_path = "/data/local/tmp"
adb_host = "localhost"
adb_port = 5037

client = AdbClient(host=adb_host, port=adb_port)
try:
    devices = client.devices()
except RuntimeError:
    print("Adb server not started")
    sys.exit(-1)
else:
    if not devices:
        print("No any device\bPlease connect your phone and turn on the USB debug mode!")
        sys.exit(-1)


def main():
    count = len(devices)
    if count > 1:
        print("select device\n----------------")
        for i, device in enumerate(devices):
            print("%d\t%s" % (i, device.get_serial_no()))
        while 1:
            index = input(">")
            if index.isdigit() and -1 < int(index) < count:
                break
        device = devices[int(index)]
    elif count == 1:
        device = devices[0]
    else:
        assert False, "never reach here!"

    print("current device is %s" % device.get_serial_no())
    abi = device.shell("getprop ro.product.cpu.abi | tr -d '\r'").strip()
    print("abi:", abi)
    sdk = device.shell("getprop ro.build.version.sdk | tr -d '\r'").strip()
    print("sdk:", sdk)
    minicap_file = "{minicap_path}/libs/{abi}/{minicap}".format(minicap_path=minicap_path, abi=abi, minicap=minicap)
    minicap_so_file = "{minicap_path}/jni/minicap-shared/aosp/libs/android-{sdk}/{abi}/{file}".format(
        minicap_path=minicap_path, sdk=sdk, abi=abi, file=minicap_so)
    minitouch_file = "{minitouch_path}/libs/{abi}/{file}".format(minitouch_path=minitouch_path, abi=abi, file=minitouch)
    print("push these files to device:")
    print(minicap_file)
    print(minicap_so_file)
    print(minitouch_file)
    success = True
    for file in [minicap_file, minicap_so_file, minitouch_file]:
        if not os.path.exists(file):
            print("local file %s not exists" % file)
            success = False
            break
        try:
            filename = os.path.basename(file)
            dest_file = "%s/%s" % (dest_path, filename)
            device.push(file, dest_file)
            device.shell("chmod 777 %s" % dest_file)
            print("ok    -  push %s" % filename)
        except RuntimeError:
            print("error -  push %s" % file)
            success = False
            break
    if success:
        print("install success")
    else:
        print("install failed")


if __name__ == "__main__":
    main()
