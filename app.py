# app.py
# -*- coding: utf-8 -*-
import os, time, csv
from io import BytesIO
from datetime import datetime, date
from pathlib import Path
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file, Response
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# ==== 我们的工具 ====
from src.api.sensors import SensorSuite
from src.utils.storage import load_yaml, save_yaml, append_csv, tail_csv_as_dicts
from src.utils.scheduler import RepeatedTimer
from src.utils.auth import init_db, get_user_by_name, create_user_if_not_exists, User
from src.utils.report import generate_pdf_report
from src.pi.hardware import PumpController, SimpleLightController, WS2812Controller

pump = PumpController(pin=23, active_high=False)
light = SimpleLightController(pin=24, pwm=False)
ws = WS2812Controller(led_count=18, gpio_pin=18)

# ==== 摄像头（OpenCV 简易封装）====
import cv2

APP_TITLE = "PlantAI 环境监控"
CFG_PATH = "configs/plantai_config.yaml"

# --- 加载配置 ---
cfg = load_yaml(CFG_PATH, {
    "theme": "auto",
    "log_interval_min": 30,
    "history_csv": "data/history.csv",
    "camera": {"use_libcamera": True, "index": 0},
    "auto_control": {
        "enabled": True,
        "quiet_hours": [23,7],
        "soil_low_threshold": 35,
        "pump_duration_s": 3,
        "light_target_lux": 350,
        "normal_light_brightness": 70,
        "ws2812": {"enabled": False, "mode":"white", "brightness":128, "duration_s":10}
    },
    "users": {
        "default_admin": {"username": "admin", "password": "admin123"}
    }
})

Path(cfg["history_csv"]).parent.mkdir(parents=True, exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("configs").mkdir(exist_ok=True)

# --- Flask App ---
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("PLANTAI_SECRET", "plantai-secret-key")  # 修改为更安全的key
CORS(app)

# --- 登录管理 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_page"

@login_manager.user_loader
def load_user(user_id: str):
    return User.get(user_id)

# --- 初始化DB与默认账号 ---
init_db("data/app.db")
create_user_if_not_exists("data/app.db",
                          cfg["users"]["default_admin"]["username"],
                          cfg["users"]["default_admin"]["password"])

# --- 传感器 ---
sensors = SensorSuite()

# --- 摄像头简易提供者 ---
class PiCameraProvider:
    def __init__(self, index=0):
        self.index = index
        self.cap = None

    def start(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.index)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头（/dev/video{self.index}）")
        return True

    def read_jpeg(self):
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        if not ok:
            return None
        ret, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes() if ret else None

    def stop(self):
        if self.cap:
            try: self.cap.release()
            except: pass
            self.cap = None

camera = PiCameraProvider(index=int(cfg.get("camera",{}).get("index",0)))

# --- 历史记录器 ---
CSV_HEADER = ["时间", "温度°C", "湿度%", "光照lux", "CO₂ ppm", "TVOC ppb", "土壤湿度%"]

def _record_once():
    d = sensors.read_all()
    append_csv(cfg["history_csv"], CSV_HEADER, [
        time.strftime("%Y-%m-%d %H:%M:%S"),
        d.get("temperature_c"),
        d.get("humidity_pct"),
        d.get("light_lux"),
        d.get("eCO2_ppm"),
        d.get("TVOC_ppb"),
        d.get("soil_moisture_pct"),
    ])
    print("Recorded:", d)

# --- 自动控制器 ---
_last_actions = {"pump": 0, "light": 0, "ws": 0}  # 节流防呆
def _within_quiet_hours(quiets):
    """quiets: [start_hour, end_hour], e.g. [23,7]"""
    try:
        start, end = int(quiets[0]), int(quiets[1])
    except:
        return False
    now_h = datetime.now().hour
    if start < end:
        return start <= now_h < end
    else:
        # 例如 23~7： 23,0,1,...6
        return (now_h >= start) or (now_h < end)

def _actuate_pump(duration_s: int):
    # TODO 接入你的 PumpController，如：pump.on(); sleep; pump.off()
    duration_s = max(1, min(30, int(duration_s)))
    print(f"[自动控制] 启动水泵 {duration_s}s（模拟）")
    # 写动作日志到 CSV（也可写DB）
    append_csv("data/actions.csv", ["time","action","detail"], [
        time.strftime("%Y-%m-%d %H:%M:%S"), "pump_on", f"{duration_s}s"
    ])

def _actuate_light(brightness: int):
    # 普通补光
    brightness = max(0, min(100, int(brightness)))
    print(f"[自动控制] 打开普通补光，亮度 {brightness}%（模拟）")
    append_csv("data/actions.csv", ["time","action","detail"], [
        time.strftime("%Y-%m-%d %H:%M:%S"), "light_on", f"{brightness}%"
    ])

def _actuate_ws(mode: str, brightness: int, duration_s: int):
    print(f"[自动控制] WS2812 {mode}, bri={brightness}, dur={duration_s}s（模拟）")
    append_csv("data/actions.csv", ["time","action","detail"], [
        time.strftime("%Y-%m-%d %H:%M:%S"), "ws_on", f"{mode},{brightness},{duration_s}s"
    ])

def _auto_control_tick():
    ac = cfg.get("auto_control", {})
    if not ac.get("enabled", False):
        return
    d = sensors.read_all()
    now = time.time()
    if _within_quiet_hours(ac.get("quiet_hours",[23,7])):
        # 夜间静音，不浇水、不强制补光
        return

    # 土壤湿度低 -> 浇水
    soil = d.get("soil_moisture_pct")
    if soil is not None and soil < float(ac.get("soil_low_threshold", 35)):
        if now - _last_actions["pump"] > 300:  # 距离上次浇水至少5分钟
            _actuate_pump(ac.get("pump_duration_s", 3))
            _last_actions["pump"] = now

    # 光照不足 -> 补光（优先WS2812）
    lux = d.get("light_lux")
    target = float(ac.get("light_target_lux", 350))
    if lux is not None and lux < target:
        # 若需要补光
        if ac.get("ws2812",{}).get("enabled", False):
            if now - _last_actions["ws"] > 300:
                ws = ac["ws2812"]
                _actuate_ws(ws.get("mode","white"), int(ws.get("brightness",128)), int(ws.get("duration_s",10)))
                _last_actions["ws"] = now
        else:
            if now - _last_actions["light"] > 300:
                _actuate_light(int(ac.get("normal_light_brightness",70)))
                _last_actions["light"] = now

# 定时器：历史记录 + 自动控制（1分钟）
rt_record = RepeatedTimer(max(5, int(cfg.get("log_interval_min",30))*60), _record_once)
rt_auto   = RepeatedTimer(60, _auto_control_tick)

# ===================== 页面（需登录）=====================
@app.route("/login", methods=["GET","POST"])
def login_page():
    if request.method == "GET":
        return render_template("login.html", title="登录", theme=cfg.get("theme","auto"))
    # POST
    u = request.form.get("username","").strip()
    p = request.form.get("password","").strip()
    user = get_user_by_name("data/app.db", u)
    if user and user.verify_password(p):
        login_user(user)
        return redirect(url_for("dashboard"))
    return render_template("login.html", title="登录", theme=cfg.get("theme","auto"), error="用户名或密码错误")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", title=APP_TITLE, theme=cfg.get("theme","auto"))

@app.route("/history")
@login_required
def history_page():
    return render_template("history.html", title=APP_TITLE, theme=cfg.get("theme","auto"))

@app.route("/control")
@login_required
def control_page():
    return render_template("control.html", title=APP_TITLE, theme=cfg.get("theme","auto"))

@app.route("/camera")
@login_required
def camera_page():
    return render_template("camera.html", title=APP_TITLE, theme=cfg.get("theme","auto"))

@app.route("/settings")
@login_required
def settings_page():
    return render_template("settings.html", title=APP_TITLE, theme=cfg.get("theme","auto"))

@app.route("/reports")
@login_required
def reports_page():
    return render_template("reports.html", title=APP_TITLE, theme=cfg.get("theme","auto"))

# ===================== API（需登录）=====================
@app.route("/api/sensors")
@login_required
def api_sensors():
    return jsonify(sensors.read_all())

@app.route("/api/history")
@login_required
def api_history():
    n = request.args.get("n")
    since = request.args.get("since")
    until = request.args.get("until")
    path = cfg["history_csv"]

    def parse_date(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except:
            return None

    if (since or until) and os.path.exists(path):
        rows = []
        sdt = parse_date(since) if since else None
        edt = parse_date(until) if until else None
        with open(path, "r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                t = row.get("时间")
                try:
                    dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
                except:
                    continue
                if sdt and dt.date() < sdt.date():
                    continue
                if edt and dt.date() > edt.date():
                    continue
                rows.append(row)
        return jsonify({"count": len(rows), "items": rows})
    else:
        n = int(n) if n else 200
        items = tail_csv_as_dicts(path, n=n)
        return jsonify({"count": len(items), "items": items})

@app.route("/api/history/download")
@login_required
def api_history_download():
    path = cfg["history_csv"]
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "历史文件不存在"}), 404
    return send_file(path, as_attachment=True, download_name="history.csv")

@app.route("/api/reports/pdf")
@login_required
def api_report_pdf():
    since = request.args.get("since")
    until = request.args.get("until")
    path = cfg["history_csv"]
    outfile = f"data/report_{int(time.time())}.pdf"
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "无历史数据"}), 404
    items = []
    if since or until:
        # 调用 /api/history 逻辑
        res = app.test_client().get(f"/api/history?since={since or ''}&until={until or ''}")
        data = res.get_json()
        items = data.get("items", [])
    else:
        # 末尾200条
        res = app.test_client().get("/api/history?n=200")
        data = res.get_json()
        items = data.get("items", [])
    # 生成PDF
    generate_pdf_report(items, outfile, title="PlantAI 健康报告")
    return send_file(outfile, as_attachment=True, download_name=os.path.basename(outfile))

@app.route("/api/settings", methods=["GET","POST"])
@login_required
def api_settings():
    if request.method == "GET":
        return jsonify(cfg)
    data = request.get_json(force=True, silent=True) or {}
    # 主题
    if "theme" in data:
        cfg["theme"] = data["theme"]
    # 采集周期
    if "log_interval_min" in data:
        cfg["log_interval_min"] = max(1, int(data["log_interval_min"]))
        try: rt_record.stop()
        except: pass
        globals()["rt_record"] = RepeatedTimer(cfg["log_interval_min"]*60, _record_once)
    # 自动控制
    if "auto_control" in data and isinstance(data["auto_control"], dict):
        cfg["auto_control"].update(data["auto_control"])
    save_yaml(CFG_PATH, cfg)
    return jsonify({"ok": True, "saved": cfg})

@app.route("/api/control", methods=["POST"])
@login_required
def api_control():
    p = request.get_json(force=True, silent=True) or {}
    # TODO: 对接你的真实控制器（pump / light / ws）
    # 安全限制
    if "pump_duration" in p:
        p["pump_duration"] = max(1, min(30, int(p["pump_duration"])))
    if "brightness" in p:
        p["brightness"] = max(0, min(100, int(p["brightness"])))
    if "ws_brightness" in p:
        p["ws_brightness"] = max(0, min(255, int(p["ws_brightness"])))
    if "ws_duration" in p:
        p["ws_duration"] = max(1, min(60, int(p["ws_duration"])))

    # 模拟执行 + 写动作日志（实际可替换为硬件调用）
    detail = []
    if p.get("pump") is not None:
        state = "on" if p["pump"] else "off"
        sec = p.get("pump_duration", 0)
        detail.append(f"pump:{state}({sec}s)")
    if p.get("light") is not None:
        state = "on" if p["light"] else "off"
        bri = p.get("brightness", "")
        detail.append(f"light:{state}({bri}%)")
    if p.get("ws_enable") is not None:
        state = "on" if p["ws_enable"] else "off"
        detail.append(f"ws:{state}({p.get('ws_mode','white')},{p.get('ws_brightness',128)},{p.get('ws_duration',10)}s)")

    append_csv("data/actions.csv", ["time","action","detail"], [
        time.strftime("%Y-%m-%d %H:%M:%S"), "manual", ";".join(detail)
    ])
    return jsonify({"ok": True, "echo": p})

# 摄像头
@app.route("/camera/start")
@login_required
def camera_start():
    try:
        camera.start()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/camera/stop")
@login_required
def camera_stop():
    camera.stop()
    return jsonify({"ok": True})

def _gen_mjpeg():
    while True:
        buf = camera.read_jpeg()
        if buf is None:
            time.sleep(0.05)
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf + b"\r\n")

@app.route("/video_feed")
@login_required
def video_feed():
    return Response(_gen_mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/ping")
def ping():
    return jsonify({"ok": True, "time": time.time()})

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        try: rt_record.stop()
        except: pass
        try: rt_auto.stop()
        except: pass
        try: camera.stop()
        except: pass
