# src/api/routes.py
import time
from flask import Blueprint, current_app, request, jsonify, Response
from src.api.inference import load_model, predict_pil
from src.api.sensors import get_all_readings
from src.api.hardware import get_actuators, set_light_rgb_spectrum
from src.api.camera import get_camera_mjpeg_generator
from src.api.storage import history_query, insert_event
from PIL import Image
from io import BytesIO

api_bp = Blueprint("api", __name__)

# 缓存模型
_model = {"impl": None, "labels": []}

@api_bp.before_app_first_request
def _lazy_load():
    if _model["impl"] is None:
        cfg = current_app.config
        _model["impl"], _model["labels"] = load_model(
            cfg["TRAIN_CFG"], cfg["MODEL_ONNX"], cfg["MODEL_TFLITE"], cfg["LABELS_TXT"]
        )
        current_app.logger.info(f"Model loaded: backend={_model['impl'].name}")

@api_bp.get("/status")
def status():
    # 设备负载略：只返回核心信息（可扩展 cpu/mem 等）
    readings = get_all_readings()
    return jsonify({
        "uptime_sec": int(time.monotonic()),
        "sensors": readings,
        "thresholds": current_app.config.get("THRESHOLDS_CACHE", {})
    })

@api_bp.post("/predict")
def predict():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "no file"}), 400
    im = Image.open(BytesIO(request.files["file"].read())).convert("RGB")
    label, conf, probs = predict_pil(_model["impl"], _model["labels"], im)
    insert_event("inference", {"label": label, "confidence": conf})
    return jsonify({"ok": True, "label": label, "confidence": float(conf), "probs": probs})

@api_bp.post("/control")
def control():
    payload = request.get_json(force=True, silent=True) or {}
    pump = payload.get("pump")               # True/False/None
    light = payload.get("light")             # True/False/None
    spectrum = payload.get("spectrum")       # white/red/blue/warm/cool/custom
    rgb = payload.get("custom_rgb")          # [r,g,b]
    brightness = payload.get("brightness")   # 0-255
    duration = int(payload.get("duration_sec") or 0)

    acts = get_actuators()
    state = {}

    # pump
    if pump is not None:
        ok, msg = acts["pump"].switch(bool(pump), duration=duration)
        if not ok:
            return jsonify({"ok": False, "error": msg}), 400
        state["pump"] = bool(pump)

    # light / ws2812
    if light is not None:
        if acts["ws"] is not None:
            if not light:
                acts["ws"].off()
            else:
                set_light_rgb_spectrum(acts["ws"], spectrum, rgb, brightness)
        elif acts["simple_light"] is not None:
            acts["simple_light"].set(bool(light), brightness or 100)
        state["light"] = bool(light)

    insert_event("control", {"payload": payload, "state": state})
    return jsonify({"ok": True, "state": state})

@api_bp.get("/stream")
def stream():
    gen = get_camera_mjpeg_generator()
    return Response(gen, mimetype="multipart/x-mixed-replace; boundary=frame")

@api_bp.get("/history")
def history():
    q = {k: request.args.get(k) for k in ["start", "end", "limit", "format", "aggregate"]}
    items, next_cursor, csv_text = history_query(q)
    if q.get("format") == "csv":
        return Response(csv_text, mimetype="text/csv")
    return jsonify({"items": items, "next_cursor": next_cursor})

@api_bp.get("/events")
def events():
    def _sse():
        # 最简单示例：每秒推一个心跳
        while True:
            time.sleep(1)
            yield f"event: heartbeat\ndata: {int(time.time())}\n\n"
    return Response(_sse(), mimetype="text/event-stream")
