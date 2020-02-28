ROTATION_WATCHER_PID_FILE = ".rotation.pid"
ROTATION_WATCHER_PIPE_FILE = ".rotation.txt"
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


TITLE_ERROR = "ERROR"
TITLE_INFO = "TIP"
TITLE_WARNING = "WARNING"

try:
    from local_settings import *
except ImportError:
    pass
