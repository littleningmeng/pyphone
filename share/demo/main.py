# -*- coding: utf-8 -*-
import cv2
import redis
import numpy as np

print("connecting redis server ...")
r = redis.Redis("localhost", 6379, db=3)
r.ping()
print("connected")

while 1:
    jpg = r.rpop("f170104_1000")
    if jpg:
        array = np.fromstring(jpg, np.uint8)
        img = cv2.imdecode(array, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        cv2.imshow("demo-pugin", gray)

    cv2.waitKey(1)
