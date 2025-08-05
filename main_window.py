# main_window.py
import time
import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from core.camera import Camera
from core.processor import run_yolo_on_frame, annotate_bia
from core.storage import StorageManager
from gui.gui import CaptureGUI
from bia_so_4.controller.bia_so_4_controller import BiaSo4Controller
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

        # GUI view
        self.gui = CaptureGUI()
        self.layout.addWidget(self.gui)

        # Core components
        self.cam = Camera(0)
        self.storage = StorageManager()
        # cho phép dễ thay đổi đường dẫn bằng tham số mặc định
        self.controller = BiaSo4Controller()

        # Inference bookkeeping
        self.last_inference = 0
        self.cached_vis = None

        # Timer stream
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33 FPS

        # Capture button
        self.gui.btn_capture.clicked.connect(self.on_capture_action)

    def update_frame(self):
        frame = self.cam.grab()
        if frame is None:
            return
        #crop về khung 16/9
        frame = self.crop_to_portrait(frame)
        display = frame.copy()
        now = time.time()
        try:
            if self.gui.yolo_checkbox.isChecked() and (now - self.last_inference) >= INFERENCE_INTERVAL:
                self.last_inference = now
                vis = run_yolo_on_frame(frame)
                self.cached_vis = vis
                display = vis
            else:
                if self.cached_vis is not None and self.gui.yolo_checkbox.isChecked():
                    display = self.cached_vis
        except Exception:
            logger.exception("Lỗi khi chạy YOLO inference")

        self.gui.display_frame(display)

    def on_capture_action(self):
        if self.gui.current_frame is None:
            return

        frame = self.gui.current_frame
        logger.info("[MainWindow] nút chụp được bấm")
        self.controller.test_controller()
        hit_check = self.controller.check_bia_hit(frame)
        if hit_check["detected"]:
            if hit_check["center_in_box"]:
                logger.info("Đã phát hiện bia_so_4 và tâm nằm trong box → TRÚNG")
                box = hit_check["box"]
                processed_image, score_or_error = self.controller.process_shot_result(frame, box)

                if processed_image is not None:
                    logger.info(f"Điểm số: {score_or_error}")
                    # Thay vì block bằng cv2.imshow, giữ nguyên nếu bạn thực sự cần debug
                    cv2.imshow("Warped to Original", processed_image)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                else:
                    logger.warning(f"Xử lý thất bại: {score_or_error}")
            else:
                logger.info("Phát hiện bia_so_4 nhưng tâm không nằm trong box → HỤT")
        else:
            logger.info("Không phát hiện bia_so_4 trên frame. -> HỤT")

        # 1. Lưu raw
        filename, raw_path = self.storage.save_raw(frame)
        logger.info(f"[MainWindow] Đã lưu raw: {raw_path}")

        # 2. YOLO & annotate
        annotated, info = annotate_bia(frame)

        # 3. Lưu processed
        processed_path = self.storage.save_processed(annotated, filename)
        logger.info(f"[MainWindow] Đã lưu processed: {processed_path}")

        # 4. Cập nhật metadata
        extra = {
            "processed": True,
            "label": info.get("label"),
            "confidence": info.get("confidence"),
            "hit": info.get("center_in_box"),
        }
        self.storage.update_metadata(filename, extra)

        # 5. Thêm thumbnail
        self.gui.add_processed_thumbnail(annotated)

    def crop_to_portrait(self, frame):
        """Crop khung hình về tỉ lệ 9:16 (dọc) từ giữa"""
        h, w, _ = frame.shape
        target_aspect = 9 / 16
        new_width = int(h * target_aspect)
        if new_width > w:
            # Nếu webcam quá hẹp, không crop được
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
