# pyphone 
### 简介  
pyphone是Python+PyQt5实现的跨平台Android手机投屏与操控工具，投屏使用[minicap](https://github.com/openstf/minicap)，操控使用[minitouch](https://github.com/openstf/minitouch)  

![](/snapshots/demo.gif)  

### 初始化   
确认已安装了Python3.6或更高版本。  
安装依赖库（推荐使用虚拟环境）：  
```bash
pip install -r requirements.txt
```

将手机连接到电脑，并确认调试模式已打开。  
```bash
cd tools
python install.py
```
install.py脚本尝试自动安装minicap、minitouch和RotationWatcher.apk。若RotationWatcher.apk安装失败，则可能是因为手机的安全校验阻塞了安装流程，请手动完成安装。  
pyphone默认使用**8081**与**8082**端口与手机通信，请确保这两个端口未被其它进程占用。  

### 环境变量   
	PYDROID_VIRTUAL_AS_SCREEN  
取值true/false  
当设置为true（默认值）时，压缩minicap输出图片尺寸为pyphone窗口控件的实际尺寸，此时图片较小，传输更快。  
当设置为false时，不压缩minicap输出图片尺寸，此时图片较大（为手机实际分辨率尺寸），可用于高清录屏。  

	PYDROID_HEIGHT  
取值为大于0且小于手机实际高度的整数，默认为1080。

### 启动  
```bash
python main.py
```

### 共享屏幕  
共享开启后（菜单->文件->Enable Share），pyphone将屏幕数据发送到Redis服务器队列。其它用户可通过pyphone的Connect remote screen菜单连接到该队列，实现屏幕共享。  
默认的Redis服务器地址在config.py中的REDIS_HOST变量中定义（默认localhost:6379），用户可以修改此地址指向自己的主机。开启共享后，pyphone还允许用户往操控队列中发送控制指令，目前支持的指令和格式如下：  
1. 单击，格式：{"cmd": "click", "x": 1, "y": 2}
2. 滑动，格式：{"cmd": "swipe", "direction": "up|down|left|right", "border": "yes|no"}
3. 输入文本，格式：{"cmd": "text", "text": "HelloWorld123!!"}  
**注意：**   输入文本暂时只支持ASCII字符，且不包含空格。  Linux（Ubuntu等）环境下的共享功能可能出现如下已知错误：  
    Fatal IO error 11 (Resource temporarily unavailable) on X server

```python
import redis
import json

r = redis.Redis("localhost", 6379, db=3)
r.ping()

op_dict = {"cmd": "click", "x": 123, "y": 456}
share_id = 91040000
r.lpush("t170104_%d" % share_id, json.dumps(op_dict))

```

