# -*- coding: utf-8 -*-
import sys
import os
import logging


def create_logger(name, logfile, level=logging.DEBUG, with_console=True):
    log = logging.getLogger(name)
    log.setLevel(level)

    formatter = logging.Formatter("[%(levelname)-7s][%(asctime)s]"
                                  "[%(filename)s:%(lineno)3d] %(message)s", "%Y/%m/%d %H:%M:%S")

    if with_console:
        h1 = logging.StreamHandler(sys.stdout)
        h1.setFormatter(formatter)
        log.addHandler(h1)

    d = os.path.dirname(logfile)
    if d != "" and not os.path.exists(d):
        try:
            os.makedirs(os.path.dirname(logfile))
        except OSError as e:
            log.warning("Unable to create log file at %s, Exp -> %s" % (logfile, repr(e)))
            return log

    h2 = logging.FileHandler(logfile)
    h2.setFormatter(formatter)
    log.addHandler(h2)

    return log


logger = create_logger(__name__, './pyphone.log')

if __name__ == "__main__":
    logger = create_logger(__name__, "./log.txt")
    logger.debug("Hello World")
