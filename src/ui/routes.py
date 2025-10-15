# src/ui/routes.py
from flask import Blueprint, render_template

ui_bp = Blueprint("ui", __name__)

@ui_bp.get("/")
def index():
    return render_template("dashboard.html")

@ui_bp.get("/history")
def history():
    return render_template("history.html")

@ui_bp.get("/stream")
def stream():
    return render_template("stream.html")
