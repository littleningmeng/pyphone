# -*- coding: utf-8 -*-
import socket
import struct
import os
import sys


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
s.connect_ex(("localhost", 8081))


def receive(sock, size):
    count = 0
    buffs = []
    while count < size:
        buff = sock.recv(min(8192, size))
        count += len(buff)
        buffs.append(buff)

    return b"".join(buffs)


receive(s, 24)


tmpdir = "./tmp"
if not os.path.exists(tmpdir):
    try:
        os.makedirs(tmpdir)
    except OSError:
        print("fail to create tmpdir")
        sys.exit(1)

seq = 1
while 1:
    n_buff = receive(s, 4)
    n = struct.unpack("I", n_buff)[0]
    frame_buff = receive(s, n)
    filename = os.path.join(tmpdir, "%d.jpg" % seq)
    seq += 1
    with open(filename, "wb") as fp:
        fp.write(frame_buff)
    print("GOT", n)
