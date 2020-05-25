# -*- coding: utf-8 -*-
import sys
import redis
import apiutil
import time
import json

# 这是示例的优图OCR帐号，已无效
app_key = 'littleningmeng'
app_id = '20170104'

print("Pydroid插件示例：OCR抢红包")
print("正在连接Redis服务器: localhost:6379 ...")
r = redis.Redis("localhost", 6379, db=3)
try:
    r.ping()
except redis.exceptions.ConnectionError:
    print("连接失败")
    sys.exit(1)

print("连接成功")

ai_plat = apiutil.AiPlat(app_id, app_key)
t0 = 0

NEW_RED_ENVELOPE = "领取红包"
OPEN = "開"


def match(text, target):
    return text.find(target) > -1


flag = 0
pos = None

while 1:
    print("等待图片数据 ...")
    jpg = r.brpop("frame")[1]
    print("OCR分析中 ...")
    t0 = time.time()
    res = ai_plat.general_ocr(jpg)
    t1 = time.time()
    print("耗时: %0.3f S" % (t1 - t0))
    if res:
        d = res.json()
        if d.get("ret", -1) == 0:
            for item in d["data"]["item_list"]:
                if flag == 0:
                    if match(item["itemstring"], NEW_RED_ENVELOPE):
                        print("=================== 发现红包!! 抢啊 ===================")
                        flag = 1
                        pos = item["itemcoord"][0]
                        break
                elif flag == 1:
                    if match(item["itemstring"], OPEN):
                        print("開红包")
                        flag = 2
                        pos = item["itemcoord"][0]
                        break

            if flag in (1, 2):
                click_x = pos["x"] + pos["width"] / 2
                click_y = pos["y"] + pos["height"] / 2
                op_dict = {"cmd": "click", "x": click_x, "y": click_y}
                r.lpush("touch", json.dumps(op_dict))
                if flag == 2:
                    time.sleep(0.2)
                    r.lpush("touch", json.dumps({"cmd": "swipe", "direction": "right", "border": "yes"}))
                    flag = 0
            else:
                print("没有发现红包:(")
