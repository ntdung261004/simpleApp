import cv2
from ultralytics import YOLO
import time

# Load model YOLOv8 (seg hoặc detect) một lần
model = YOLO("/Users/thaiduong/Desktop/python/webcam_capture_app_mac/runs/detect/train2/weights/best.pt")  # đảm bảo file best.pt nằm đúng chỗ

# Bạn có thể in tên class để xác nhận
print("YOLO classes:", model.names)


def annotate_bia(frame):
    """
    Chạy YOLO trên frame, vẽ bounding box cho bia_so_4,
    trả về ảnh đã vẽ và dict thông tin (confidence, có trúng hay không).
    """
    out = frame.copy()
    results = model(frame, verbose=False)[0]
    info = {
        "detected": False,
        "label": None,
        "confidence": 0.0,
        "center_in_box": False,
        "box": None,
    }

    h, w = frame.shape[:2]
    cx, cy = w / 2.0, h / 2.0  # tâm ngắm

    if hasattr(results, "boxes") and results.boxes is not None:
        for box, cls, conf in zip(
            results.boxes.xyxy.cpu().numpy(),
            results.boxes.cls.cpu().numpy(),
            results.boxes.conf.cpu().numpy(),
        ):
            label = model.names[int(cls)]
            if label != "bia_so_4":
                continue

            x1, y1, x2, y2 = map(int, box)
            info["detected"] = True
            info["label"] = label
            info["confidence"] = float(conf)
            info["box"] = [x1, y1, x2, y2]

            # Kiểm tra tâm ngắm nằm trong box (trúng)
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                info["center_in_box"] = True

            # Vẽ box + label
            color = (0, 255, 0) if info["center_in_box"] else (0, 200, 255)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            text = f"{label} {conf:.2f}"
            if info["center_in_box"]:
                text += " (TRÚNG)"
            cv2.putText(out, text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return out, info

def run_yolo_on_frame(frame):
    """
    Chạy inference YOLO trên frame và trả về frame có overlay + detection info.
    Chỉ vẽ class 'bia_so_4'.
    """
    out = frame.copy()
    results = model(frame, verbose=False)[0]

    if hasattr(results, "boxes") and results.boxes is not None:
        for box, cls, conf in zip(
            results.boxes.xyxy.cpu().numpy(),
            results.boxes.cls.cpu().numpy(),
            results.boxes.conf.cpu().numpy(),
        ):
            label = model.names[int(cls)]
            if label != "bia_so_4":
                continue
            x1, y1, x2, y2 = map(int, box)
            # Vẽ bounding box
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Nhãn + confidence
            cv2.putText(out, f"{label} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return out
