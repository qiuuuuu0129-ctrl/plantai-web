from pathlib import Path
import numpy as np
from PIL import Image
import yaml

def _load_preprocess(cfg_path: str):
    size = 224
    mean = np.array([0.485,0.456,0.406], dtype=np.float32)
    std  = np.array([0.229,0.224,0.225], dtype=np.float32)
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        short = cfg.get("preprocess",{}).get("resize",{}).get("short_side", None)
        if short: size = int(short)
    except Exception: pass
    return size, mean, std

class AutoPlantModel:
    def __init__(self, cfg_path, onnx_path, tflite_path, labels_path):
        self.backend_name = "unavailable"
        self._impl = None
        size, mean, std = _load_preprocess(cfg_path)
        labels = Path(labels_path).read_text(encoding="utf-8").splitlines() if Path(labels_path).exists() else []

        # 先 ONNX
        if onnx_path and Path(onnx_path).exists():
            try:
                import onnxruntime as ort
                self.sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
                self.input = self.sess.get_inputs()[0].name
                self.size = size; self.mean = mean; self.std = std; self.labels = labels
                self.backend_name = "onnxruntime"
                self._impl = "onnx"
                return
            except Exception as e:
                print("ONNX 初始化失败：", e)

        # 若需要再扩展 TFLite 版本
        # ...

    def predict_pil(self, im: Image.Image):
        if self._impl != "onnx":
            return "unavailable", 0.0, []
        x = im.resize((self.size, self.size), Image.BILINEAR)
        x = np.array(x).astype(np.float32)/255.0
        x = (x - self.mean) / self.std
        x = x.transpose(2,0,1)[None, ...]
        prob = self.sess.run(None, {self.input: x})[0][0]
        ex = np.exp(prob - np.max(prob)); probs = ex/np.sum(ex)
        idx = int(np.argmax(probs))
        label = self.labels[idx] if idx < len(self.labels) else str(idx)
        return label, float(probs[idx]), probs.tolist()
