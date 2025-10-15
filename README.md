# 🌱 PlantAI - 模型训练指南

本说明文档介绍如何在开发机上进行植物识别模型的训练、保存与导出。

---

## 1. 数据准备
1. 确保所有数据放在 `../data/` 目录下（相对于 `training/`）。
2. 每个类别（植物种类）建立一个文件夹，文件夹名就是类别名。

data/
├─ rose/
│   ├─ img_001.jpg
│   ├─ img_002.jpg
│   └─ …
├─ sunflower/
│   ├─ img_001.jpg
│   └─ …

---

## 2. 安装依赖
在开发机上安装 requirements：
```bash
pip install -r ../requirements-dev.txt

如果你只想跑训练代码，也可以单独安装：

pip install torch torchvision opencv-python Pillow pandas tqdm matplotlib


⸻

3. 运行训练

进入 training/ 文件夹，运行：

python train.py

运行后会：
	•	自动加载 ../data/ 下的图片。
	•	用 MobileNetV2 预训练模型进行微调。
	•	训练完成后保存模型到：

../model/model.pth



⸻

4. 模型验证

训练完成后，可以写一个简单的推理脚本（示例）：

import torch
from torchvision import transforms, models
from PIL import Image

# 路径
MODEL_PATH = "../model/model.pth"
IMAGE_PATH = "../data/rose/img_001.jpg"

# 类别（和 data/ 文件夹顺序一致）
classes = ["rose", "sunflower"]

# 模型加载
model = models.mobilenet_v2(weights="IMAGENET1K_V1")
model.classifier[1] = torch.nn.Linear(model.last_channel, len(classes))
model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
model.eval()

# 预处理
transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
])

img = Image.open(IMAGE_PATH).convert("RGB")
input_tensor = transform(img).unsqueeze(0)

# 推理
with torch.no_grad():
    output = model(input_tensor)
    _, predicted = output.max(1)

print(f"预测结果: {classes[predicted]}")


⸻

5. 导出模型（部署用）

在 model/ 文件夹下，你会得到：
	•	model.pth → 训练好的 PyTorch 权重。
	•	使用 torch.onnx.export 可以转换成 ONNX：

python ../convert_to_tflite.py

运行后会得到：

model.onnx
model.tflite



这些文件就能放到 树莓派 上运行了。

⸻

6. 注意事项
	•	数据量要尽量均衡（每类图片数量差不多）。
	•	可以先少量训练（每类 20 张图片）测试流程，确认无误再扩展数据集。
	•	如果 GPU 可用，训练会快很多；CPU 也能跑，但会比较慢。

