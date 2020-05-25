DEBUG = False
MINICAP_HOST = "localhost"
MINICAP_PORT = 8081
MINITOUCH_PORT = MINICAP_PORT + 1
VIDEO_DIR = "./video"
# 最大录屏时长（单位min）
MAX_RECORD_MIN = 10

# 用于共享屏幕的Redis服务器地址
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 3

ADB_HOST = "localhost"
ADB_PORT = 5037

TITLE_ERROR = "ERROR"
TITLE_INFO = "TIP"
TITLE_WARNING = "WARNING"

DEFAULT_WIDTH = 720
IMAGE_QUALITIES = [320, 480, 720, 1080]

ANDROID_TMP_PATH = "/data/local/tmp"
MINICAP = "minicap"
MINICAP_PATH = "%s/minicap" % ANDROID_TMP_PATH
MINICAP_SO_PATH = "%s/minicap.so" % ANDROID_TMP_PATH
MINITOUCH = "minitouch"
MINITOUCH_PATH = "%s/minitouch" % ANDROID_TMP_PATH

try:
    from local_settings import *
except ImportError:
    pass
