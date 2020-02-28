# -*- coding: utf-8 -*-
import cv2
import numpy as np
from logger import logger


class __Recorder:

    def __init__(self):
        self.writer = None
        self.mp4file = None
        self.width = 0
        self.height = 0

    def init(self, mp4file, fps, width, height):
        logger.debug("init record fps=%d, width=%d, height=%d" % (fps, width, height))
        self.mp4file = mp4file
        self.width, self.height = width, height
        self.writer = cv2.VideoWriter(mp4file, cv2.VideoWriter_fourcc(*"MP4V"), fps, (width, height))

    def write_frames(self, frames):
        if not self.writer:
            return

        for frame in frames:
            array = np.fromstring(frame, np.uint8)
            image = cv2.imdecode(array, cv2.IMREAD_COLOR)
            height, width, channels = image.shape
            # VideoWriter 要求图片的尺寸必须与创建writer对象时传入的参数一致
            # 因此当屏幕旋转时，需要先创建一张与原尺寸一致的底图，再讲图片进行尺寸变换后贴上去
            if width > self.width:
                full_size_image = np.zeros((self.height, self.width, 3), np.uint8)
                rate = 1.0 * self.width / width
                scale_image = cv2.resize(image, (self.width, int(height * rate)), cv2.INTER_CUBIC)
                y_offset = int((self.height - scale_image.shape[0]) / 2)
                full_size_image[y_offset:y_offset + scale_image.shape[0], 0: scale_image.shape[1]] = scale_image
                image = full_size_image
            elif height > self.height:
                full_size_image = np.zeros((self.height, self.width, 3), np.uint8)
                rate = 1.0 * self.height / height
                scale_image = cv2.resize(image, (int(rate * width), self.height), cv2.INTER_CUBIC)
                x_offset = int((self.width - scale_image.shape[1]) / 2)
                full_size_image[0:scale_image.shape[0], x_offset:x_offset + scale_image.shape[1]] = scale_image
                image = full_size_image

            self.writer.write(image)

    def finish(self):
        self.writer.release()
        return self.mp4file


recorder = __Recorder()
