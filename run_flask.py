# run_flask.py
import os, socket, subprocess, webbrowser, qrcode, io
from PIL import Image

def find_free_port(start=5000, end=5100):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError("❌ 没有可用端口！")

def kill_port(port):
    try:
        result = subprocess.run(
            ["sudo", "lsof", "-t", f"-i:{port}"], capture_output=True, text=True
        )
        pids = result.stdout.strip().splitlines()
        for pid in pids:
            subprocess.run(["sudo", "kill", "-9", pid])
        if pids:
            print(f"💀 已结束端口 {port} 的进程: {', '.join(pids)}")
    except Exception as e:
        print("⚠️ 无法结束旧进程:", e)

def get_local_ip():
    """获取树莓派局域网 IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def show_qr(url: str):
    """在终端显示二维码"""
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    print("\n📱 使用手机扫描二维码访问：")
    img.show()

def main():
    base_port = 5000
    port = find_free_port(base_port)
    if port != base_port:
        print(f"⚙️ 端口 {base_port} 被占用，改用 {port}")
    else:
        kill_port(base_port)

    ip = get_local_ip()
    url = f"http://{ip}:{port}"

    print(f"\n🚀 Flask 服务启动中...")
    print(f"🌐 访问地址：{url}")
    show_qr(url)

    # 自动打开浏览器（若在桌面环境）
    try:
        webbrowser.open(url)
    except Exception:
        print("⚠️ 无法自动打开浏览器")

    os.environ["FLASK_APP"] = "app.py"
    os.environ["FLASK_ENV"] = "production"
    os.system(f"flask run --host=0.0.0.0 --port={port}")

if __name__ == "__main__":
    main()
