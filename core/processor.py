import cv2
from ultralytics import YOLO

# Load model YOLOv8 (seg hoặc detect) một lần
model = YOLO("/Users/thaiduong/Desktop/python/webcam_capture_app_mac/my_model.pt")
print("YOLO classes:", model.names)

# Các nhãn muốn hiển thị và màu vẽ
TARGET_LABELS = {"bia_so_4", "bia_so_7_8"}
LABEL_COLORS = {
    "bia_so_4": (0, 255, 0),       # Xanh lá
    "bia_so_7_8": (0, 255, 255),   # Vàng
}

def _draw_boxes(out, results, center=None, return_first_hit=False):
    """
    Vẽ bounding box cho các nhãn mục tiêu. Nếu `return_first_hit=True`, trả về info của object đầu tiên chứa center.
    """
    info = {
        "detected": False,
        "label": None,
        "confidence": 0.0,
        "center_in_box": False,
        "box": None,
    }

    if not hasattr(results, "boxes") or results.boxes is None:
        return out, info

    for box, cls, conf in zip(
        results.boxes.xyxy.cpu().numpy(),
        results.boxes.cls.cpu().numpy(),
        results.boxes.conf.cpu().numpy(),
    ):
        label = model.names[int(cls)]
        if label not in TARGET_LABELS:
            continue

        x1, y1, x2, y2 = map(int, box)

        center_in_box = False
        if center and x1 <= center[0] <= x2 and y1 <= center[1] <= y2:
            center_in_box = True

        color = (0, 255, 0) if center_in_box else LABEL_COLORS.get(label, (0, 200, 255))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf:.2f}" + (" (TRÚNG)" if center_in_box else "")
        cv2.putText(out, text, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if return_first_hit and center_in_box:
            info.update({
                "detected": True,
                "label": label,
                "confidence": float(conf),
                "center_in_box": True,
                "box": [x1, y1, x2, y2],
            })
            break

    return out, info


def annotate_bia(frame):
    """
    Chạy YOLO trên frame, vẽ bounding box, trả về ảnh đã vẽ + thông tin object đầu tiên trúng tâm.
    """
    h, w = frame.shape[:2]
    results = model(frame, verbose=False)[0]
    return _draw_boxes(frame.copy(), results, center=(w/2, h/2), return_first_hit=True)


def run_yolo_on_frame(frame):
    """
    Chạy YOLO trên frame, vẽ tất cả object mục tiêu.
    """
    results = model(frame, verbose=False)[0]
    out, _ = _draw_boxes(frame.copy(), results)
    return out
