import threading
import time
import usermgr.usermgr

name = "用户管理器"
log = False
_looping = True


def run():
    global _looping
    _looping = True
    threading.Thread(name=name, target=main_loop).start()


def stop():
    global _looping
    usermgr.usermgr.stop_all()
    _looping = False


def main_loop():
    loop = 0
    while _looping:
        loop += 1
        if log:
            print(f"{name} 轮询 {loop}")
        time.sleep(1)
        main()


def main():
    usermgr.usermgr.loop_check()