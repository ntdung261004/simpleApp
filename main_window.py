import time
import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from core.camera import Camera
from core.processor import run_yolo_on_frame, annotate_bia
from core.storage import StorageManager
from gui.gui import CaptureGUI
from bia_so_4.controller.bia_so_4_controller import BiaSo4Controller
from bia_so_7_8.controller.bia_so_7_8_controller import BiaSo7_8Controller
import cv2

INFERENCE_INTERVAL = 0.25  # giây
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Webcam Capture App")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.gui = CaptureGUI()
        self.layout.addWidget(self.gui)

        # Core
        self.cam = Camera(0)
        self.storage = StorageManager()
        self.controllers = {
            "bia_so_4": BiaSo4Controller(),
            "bia_so_7_8": BiaSo7_8Controller(),
        }

        self.last_inference = 0
        self.cached_vis = None

        # Stream timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33 FPS

        self.gui.btn_capture.clicked.connect(self.on_capture_action)

    def update_frame(self):
        frame = self.cam.grab()
        if frame is None:
            return
        frame = self.crop_to_portrait(frame)
        display = frame.copy()
        now = time.time()
        try:
            if self.gui.yolo_checkbox.isChecked() and (now - self.last_inference) >= INFERENCE_INTERVAL:
                self.last_inference = now
                self.cached_vis = run_yolo_on_frame(frame)
            if self.gui.yolo_checkbox.isChecked() and self.cached_vis is not None:
                display = self.cached_vis
        except Exception:
            logger.exception("Lỗi khi chạy YOLO inference")

        self.gui.display_frame(display)

    def on_capture_action(self):
        if self.gui.current_frame is None:
            return
        frame = self.gui.current_frame
        logger.info("[MainWindow] Nút chụp được bấm")

        annotated, info = annotate_bia(frame)

        if info["detected"] and info["center_in_box"]:
            label = info["label"]
            box = info["box"]
            controller = self.controllers.get(label)
            if controller:
                logger.info(f"Đã phát hiện {label} → TRÚNG")
                processed_image, score_or_error = controller.process_shot_result(frame, box)
                if processed_image is not None:
                    logger.info(f"Điểm số {label}: {score_or_error}")
                    cv2.imshow(f"Warped {label}", processed_image)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                else:
                    logger.warning(f"Xử lý {label} thất bại: {score_or_error}")
        else:
            logger.info("Không có object nào nằm trong tâm → Không gọi controller")

        # Lưu kết quả
        filename, raw_path = self.storage.save_raw(frame)
        processed_path = self.storage.save_processed(annotated, filename)
        self.storage.update_metadata(filename, {
            "processed": True,
            "label": info.get("label"),
            "confidence": info.get("confidence"),
            "hit": info.get("center_in_box"),
        })
        self.gui.add_processed_thumbnail(annotated)

    def crop_to_portrait(self, frame):
        h, w, _ = frame.shape
        target_aspect = 9 / 16
        new_width = int(h * target_aspect)
        if new_width > w:
            return frame
        x_start = (w - new_width) // 2
        x_end = x_start + new_width
        return frame[:, x_start:x_end]

    def closeEvent(self, event):
        try:
            self.cam.release()
        except Exception:
            logger.exception("Lỗi khi release camera")
        super().closeEvent(event)
