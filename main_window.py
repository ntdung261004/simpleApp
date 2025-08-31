# main_window.py
import logging
import cv2
from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QScreen

# THAY ĐỔI: Import giao diện mới MainGui
from gui.gui import MainGui
from core.camera import Camera
from core.processor import annotate_bia
from bia_so_4.controller.bia_so_4_controller import BiaSo4Controller
from bia_so_7_8.controller.bia_so_7_8_controller import BiaSo7_8Controller

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm Súng Tiểu Liên STV")

        # TỐI ƯU: Thiết lập cửa sổ toàn màn hình
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen)

        # TỐI ƯU: Tích hợp giao diện mới một cách gọn gàng
        # MainGui là một QWidget, ta đặt nó làm widget trung tâm của QMainWindow
        self.gui = MainGui()
        self.setCentralWidget(self.gui)

        # Core components (Không thay đổi)
        self.cam = Camera(0)
        self.controllers = {
            "bia_so_4": BiaSo4Controller(),
            "bia_so_7_8": BiaSo7_8Controller(),
        }

        # Stream timer (Không thay đổi)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Khoảng 33 FPS

        # --- Kết nối các widget của giao diện mới ---
        # Tên các widget (calibrate_button, zoom_slider) được giữ nguyên
        # nên không cần thay đổi logic kết nối ở đây.
        self.gui.calibrate_button.clicked.connect(self.process_current_frame)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)

    def update_frame(self):
        """Lấy frame từ camera và gọi phương thức hiển thị của GUI."""
        frame = self.cam.grab()
        if frame is None:
            return
        
        # Chỉ gọi hàm display_frame, việc chuyển đổi và hiển thị do GUI quản lý
        self.gui.display_frame(frame)

    def process_current_frame(self):
        """Hàm chính được gọi khi bấm nút 'Hiệu chỉnh tâm'. Logic giữ nguyên."""
        if self.gui.current_frame is None:
            logger.warning("Không có frame nào từ camera để xử lý.")
            return
        
        # Luôn làm việc trên một bản sao để tránh thay đổi frame gốc
        frame = self.gui.current_frame.copy()
        logger.info("[MainWindow] Nút 'Hiệu chỉnh tâm' được bấm, bắt đầu xử lý.")

        # Bước 1: Phát hiện mục tiêu
        annotated_frame, info = annotate_bia(frame)

        # Bước 2: Kiểm tra và gọi controller tương ứng
        if info.get("detected") and info.get("center_in_box"):
            label = info["label"]
            box = info["box"]
            controller = self.controllers.get(label)
            
            if controller:
                logger.info(f"Đã phát hiện '{label}' trong tâm → TRÚNG")
                processed_image, score = controller.process_shot_result(frame, box)
                
                if processed_image is not None:
                    logger.info(f"Điểm số '{label}': {score}")
                    # Cập nhật kết quả lên panel bên phải
                    self.gui.update_results(
                        score=score,
                        target_name=label,
                        processed_frame_bgr=processed_image
                    )
                else:
                    logger.warning(f"Xử lý '{label}' thất bại: {score}")
                    self.gui.update_results(score="Lỗi", target_name=label, processed_frame_bgr=annotated_frame)
            else:
                logger.warning(f"Không tìm thấy controller cho nhãn '{label}'")
        else:
            logger.info("Không có mục tiêu nào nằm trong tâm → TRƯỢT")
            # Cập nhật trạng thái "Trượt" lên GUI
            self.gui.update_results(score=0, target_name="Không xác định", processed_frame_bgr=annotated_frame)

# main_window.py

    def on_zoom_changed(self, value):
        """
        Hàm được gọi khi giá trị slider thay đổi.
        Giá trị `value` nhận được là một số nguyên từ 10 đến 50.
        """
        # Chia cho 10.0 để có được giá trị zoom thực tế (ví dụ: 1.0, 1.1, ..., 5.0)
        zoom_level = value / 10.0
        logger.info(f"Giá trị zoom thay đổi: {zoom_level:.1f}x")
        
        # TODO: Implement logic điều khiển zoom camera (nếu camera hỗ trợ)
        # hoặc zoom kỹ thuật số bằng cách crop ảnh dựa trên `zoom_level`.

    def closeEvent(self, event):
        """Giải phóng camera khi đóng ứng dụng. Logic giữ nguyên."""
        try:
            self.timer.stop()
            self.cam.release()
            logger.info("Camera đã được giải phóng.")
        except Exception as e:
            logger.exception(f"Lỗi khi giải phóng camera: {e}")
        super().closeEvent(event)