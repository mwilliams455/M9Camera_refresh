---
license: openrail++
datasets:
- sshao0516/CrowdHuman
language:
- en
base_model:
- pyronear/yolov11s
pipeline_tag: object-detection
tags:
- person
- head
---
# PHD Person + Head Detection — YOLOv11 ONNX

Dual-class detection model (Person Head Detection) based on YOLOv11, exported to ONNX and configured for DeepStream/ONNX Runtime inference. Detects both **persons** (class 0) and **heads** (class 1) simultaneously.

## Files

| File | Description |
|---|---|
| `yolov11_phd_s.onnx` | YOLOv11-small ONNX model weights |
| `inference.py` | Standalone ONNX Runtime inference script |

## Model Details

| Property | Value |
|---|---|
| Architecture | YOLOv11-small |
| Task | Dual-class detection (person + head) |
| Classes | `0` — person, `1` — head |
| Dataset | CrowdHuman |
| Input format | BGR, NCHW |
| Scale factor | 0.0039215697906911373 (≈ 1/255) |

## Running Standalone Inference

### Requirements

```bash
pip install onnxruntime-gpu opencv-python numpy
```

For CPU-only:
```bash
pip install onnxruntime opencv-python numpy
```

### Usage

Place a test image in the same directory, then:

```bash
python inference.py
```

By default the script reads `test_image.jpg`, runs inference, and writes `output.jpg` with bounding boxes drawn.

To change the input image or thresholds, edit the config block at the top of `inference.py`:

```python
CONF_THRESHOLD = 0.2   # pre-cluster-threshold
IOU_THRESHOLD  = 0.6   # nms-iou-threshold
TOPK           = 300
```

### Output

- Console: detection count, bounding boxes, and confidence scores
- `output.jpg`: input image with green bounding boxes and labels overlaid