# pyphone 
### 简介  
pyphone是Python+PyQt5实现的跨平台Android手机投屏与操控工具，投屏使用[minicap](https://github.com/openstf/minicap)，操控使用[minitouch](https://github.com/openstf/minitouch)  

![](/snapshots/demo1.png)  
![](/snapshots/demo2.png)  

### 初始化   
确认已安装了Python3.6或更高版本。  
安装依赖库（推荐使用pipenv管理虚拟环境）：  
```bash
pip install -r requirements.txt
```

将手机连接到电脑，并确认调试模式已打开。  
```bash
cd tools
python install.py
```
install.py脚本尝试自动安装对应手机版本的minicap/minicap.so/minitouch  
pyphone默认使用**8081**与**8082**端口与手机通信，请确保这两个端口未被其它进程占用。  
若要支持中文输入，请参考下文的**如何输入中文**  

### 环境变量   
	PYDROID_VIRTUAL_AS_SCREEN  
取值true/false  
当设置为true（默认值）时，压缩minicap输出图片尺寸为pyphone窗口控件的实际尺寸，此时图片较小，传输更快。  
当设置为false时，不压缩minicap输出图片尺寸，此时图片较大（为手机实际分辨率尺寸），可用于高清录屏。  

	PYDROID_HEIGHT  
取值为大于0且小于手机实际高度的整数，默认为720。

### 启动  
```bash
python main.py
```

### 共享屏幕  
**请先确认你有一个可用的Redis服务器**  
共享开启后（File->Enable Share），pyphone将屏幕数据发送到Redis服务器队列。其它用户可通过pyphone的Connect remote screen菜单连接到该队列，实现屏幕共享。  
默认的Redis服务器地址在config.py中的REDIS_HOST变量中定义（默认localhost:6379），用户可以修改此地址指向自己的主机。开启共享后，pyphone还允许用户往操控队列中发送控制指令，目前支持的指令和格式如下：  
1. 单击：{"cmd": "click", "x": 1, "y": 2}
2. 滑动：{"cmd": "swipe", "direction": "up|down|left|right", "border": "yes|no"}
3. 输入文本：{"cmd": "text", "text": "HelloWorld123!!"}  
4. 截屏：{"cmd": "screenshots", "filepath": "/tmp/test.jpg"}
4. Shell命令：{"cmd": "shell", "param": "getprop ro.build.version.sdk | tr -d '\r'"}  
示例：  
```python
import redis
import json

r = redis.Redis("localhost", 6379, db=3)
r.ping()

op_str = json.dumps({"cmd": "click", "x": 123, "y": 456})
share_id = 1701
r.lpush("pp-touch:%d" % share_id, op_str)

```

### 如何输入中文  
默认的adb shell input text无法输入中文，可使用开源工具[ADBKeyBoard](https://github.com/senzhk/ADBKeyBoard)解决。安装与使用示例：  
```bash
cd tools
adb install ADBKeyboard.apk # 注意有些安卓手机要求在手机上确认安装过程
adb shell ime set com.android.adbkeyboard/.AdbIME # 切换到ADBKeyboard输入法
adb shell am broadcast -a ADB_INPUT_TEXT --es msg '中文输入'
```
