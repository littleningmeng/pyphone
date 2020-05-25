# -*- coding: utf-8 -*-
from multiprocessing import Process


def start_in_progress(target, args):
    p = Process(target=target, args=args)
    p.start()
    return p
