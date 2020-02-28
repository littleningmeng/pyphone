# -*- coding: utf-8 -*-
import socket
import struct
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
s.connect_ex(("localhost", 8081))


def receive(s, n):
    count = 0
    buffs = []
    while count < n:
        buff = s.recv(min(8192, n))
        count += len(buff)
        buffs.append(buff)

    return b"".join(buffs)


receive(s, 24)


while 1:
    n_buff = receive(s, 4)
    n = struct.unpack("I", n_buff)[0]
    frame_buff = receive(s, n)
    print("GOT", n)
