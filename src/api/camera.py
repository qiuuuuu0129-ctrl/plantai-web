import os, time, subprocess
import cv2
from threading import Thread
from flask import Blueprint, Response, jsonify

bp = Blueprint("camera_bp", __name__)

class Camera:
    def __init__(self, index=0, use_libcamera=True):
        self.index = index
        self.use_libcamera = use_libcamera
        self.cap = None
        self.frame = None
        self.running = False
        self.thread = None

    def _has_libcamera(self):
        try:
            r = subprocess.run(["which", "libcamera-hello"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return r.returncode == 0
        except Exception:
            return False

    def open(self):
        if self.use_libcamera and self._has_libcamera():
            # 尝试加载 v4l2
            os.system("sudo modprobe bcm2835-v4l2")
            self.cap = cv2.VideoCapture(0)
        else:
            self.cap = cv2.VideoCapture(self.index)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("无法打开摄像头")
        self.running = True
        self.thread = Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running and self.cap.isOpened():
            ok, frame = self.cap.read()
            if ok:
                self.frame = frame
            else:
                time.sleep(0.05)

    def get_jpeg(self):
        if self.frame is None: return None
        ok, buf = cv2.imencode(".jpg", self.frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return buf.tobytes() if ok else None

    def release(self):
        self.running = False
        time.sleep(0.05)
        if self.cap:
            self.cap.release()

camera = Camera()

@bp.route("/api/camera/start", methods=["POST"])
def start_camera():
    try:
        if not camera.running:
            camera.open()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@bp.route("/api/camera/stop", methods=["POST"])
def stop_camera():
    camera.release()
    return jsonify({"ok": True})

@bp.route("/video_feed")
def video_feed():
    def gen():
        while True:
            frame = camera.get_jpeg()
            if frame is None:
                time.sleep(0.05)
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")
