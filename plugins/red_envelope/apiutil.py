# -*- coding: UTF-8 -*-
import hashlib
import urllib
import base64
import time
import requests


def set_params(array, key, value):
    array[key] = value


def gen_sign_string(parser):
    uri_str = ''
    for key in sorted(parser.keys()):
        if key == 'app_key':
            continue
        uri_str += "%s=%s&" % (key, urllib.parse.quote(str(parser[key]), safe=''))
    sign_str = uri_str + 'app_key=' + parser['app_key']
    hash_md5 = hashlib.md5(sign_str.encode("utf-8"))
    return hash_md5.hexdigest().upper()


class AiPlat(object):
    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key
        self.data = {}

    @staticmethod
    def invoke(data):
        res = requests.post("https://api.ai.qq.com/fcgi-bin/ocr/ocr_generalocr", data)
        return res
        
    def general_ocr(self, image):
        set_params(self.data, 'app_id', self.app_id)
        set_params(self.data, 'app_key', self.app_key)
        set_params(self.data, 'time_stamp', int(time.time()))
        set_params(self.data, 'nonce_str', int(time.time()))
        image_data = base64.b64encode(image).decode("utf-8")
        set_params(self.data, 'image', image_data)
        set_params(self.data, 'sign', gen_sign_string(self.data))
        res = self.invoke(self.data)
        self.data = {}
        return res
