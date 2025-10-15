import threading, time
from typing import Callable

class RepeatedTimer:
    """每 interval 秒执行一次 fn（守护线程）"""
    def __init__(self, interval_sec: int, fn: Callable):
        self._interval = interval_sec
        self._fn = fn
        self._stop = threading.Event()
        self._thr = threading.Thread(target=self._loop, daemon=True)
        self._thr.start()

    def _loop(self):
        while not self._stop.is_set():
            t0 = time.time()
            try:
                self._fn()
            except Exception as e:
                print("RepeatedTimer error:", e)
            # sleep 剩余时间
            dt = time.time() - t0
            to_sleep = max(0.0, self._interval - dt)
            self._stop.wait(to_sleep)

    def stop(self):
        self._stop.set()

