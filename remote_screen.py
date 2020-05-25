# -*- coding: utf-8 -*-
import cv2
import redis
import config
import numpy as np


def start(val, queue, host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB):
    print("Connecting share server %s:%d/%d ..." % (host, port, db))
    r = redis.Redis(host, port, db=db)
    try:
        r.ping()
    except redis.exceptions.ConnectionError:
        print("Unable to connect redis server!")
        return False

    print("Connected, waiting frame ...")
    while 1:
        if val.value == 1:
            break
        data = r.rpop(queue)
        if data:
            img = cv2.imdecode(np.fromstring(data, np.uint8), cv2.IMREAD_COLOR)
            cv2.imshow("Remote screen", img)

        cv2.waitKey(1)

    print("Disconnect remote screen")
    return True
