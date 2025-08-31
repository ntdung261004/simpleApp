# gui/gui.py (Cập nhật - Tách biệt điều khiển, zoom chi tiết)
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QSize, QPoint
from datetime import datetime

# =============================================================================
# LỚP TÙY CHỈNH ĐỂ HIỂN THỊ VIDEO MỘT CÁCH ỔN ĐỊNH
# =============================================================================
class VideoLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return

        scaled_pixmap = self._pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - scaled_pixmap.height()) / 2
        
        painter = QPainter(self)
        painter.drawPixmap(QPoint(int(x), int(y)), scaled_pixmap)

# =============================================================================
# LỚP GIAO DIỆN CHÍNH (ĐÃ CẬP NHẬT)
# =============================================================================
class MainGui(QWidget):
    def __init__(self):
        super().__init__()
        self.current_frame = None

        self.setStyleSheet("""
            QWidget {
                background-color: #F8F8F8; color: #333333; font-family: 'Segoe UI';
            }
            QFrame#panel {
                background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E0E0E0;
            }
            QLabel#title {
                color: #0078D4; padding: 10px;
            }
            QLabel.panel-title {
                font-size: 16px; font-weight: bold; color: #333333;
            }
            QPushButton {
                background-color: #0078D4; color: #FFFFFF; font-size: 14px;
                font-weight: bold; border: none; padding: 10px 20px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #005A9E; }
            QPushButton:pressed { background-color: #004578; }
            QSlider::groove:horizontal {
                border: 1px solid #CCCCCC; height: 4px; background: #CCCCCC;
                margin: 2px 0; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #0078D4; border: 1px solid #0078D4;
                width: 18px; margin: -7px 0; border-radius: 9px;
            }
            VideoLabel {
                background-color: #EFEFEF; border: 2px dashed #B0B0B0;
                border-radius: 8px; color: #888888; font-size: 30px;
            }
            #controlsPanel { /* Style cho vùng điều khiển mới */
                background-color: #FDFDFD;
                border-top: 1px solid #E0E0E0;
                padding: 10px;
            }
            #zoomValueLabel {
                font-size: 13px; font-weight: bold; color: #0078D4; min-width: 45px;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 10, 20, 20)
        root_layout.setSpacing(15)

        title_label = QLabel("PHẦN MỀM KIỂM TRA ĐƯỜNG NGẮM SÚNG TIỂU LIÊN STV")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont('Segoe UI', 18, QFont.Bold)
        title_label.setFont(title_font)
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        columns_layout.addWidget(self._create_camera_column(), 6)
        columns_layout.addWidget(self._create_right_column(), 4)
        root_layout.addLayout(columns_layout)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        
        shadow_effect = QGraphicsDropShadowEffect(panel)
        shadow_effect.setBlurRadius(15)
        shadow_effect.setColor(QColor(0, 0, 0, 40))
        shadow_effect.setOffset(0, 5)
        panel.setGraphicsEffect(shadow_effect)
        return panel

    def _create_camera_column(self) -> QWidget:
        panel = self._create_styled_panel()
        # ======================================================================
        # THAY ĐỔI: Bỏ QStackedLayout, dùng QVBoxLayout đơn giản
        # setContentsMargins và setSpacing về 0 để video chiếm toàn bộ không gian trên
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # ======================================================================

        # Widget chứa tiêu đề và video
        video_area = QWidget()
        video_area_layout = QVBoxLayout(video_area)
        video_area_layout.setContentsMargins(20, 20, 20, 15)
        video_area_layout.setSpacing(15)

        title = QLabel("Camera lắp trên súng")
        title.setProperty("class", "panel-title")
        video_area_layout.addWidget(title)
        
        self.camera_view_label = VideoLabel()
        self.camera_view_label.setText("Đang chờ tín hiệu camera...")
        self.camera_view_label.setAlignment(Qt.AlignCenter)
        self.camera_view_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_area_layout.addWidget(self.camera_view_label)

        main_layout.addWidget(video_area) # Thêm vùng video vào layout chính

        # Widget chứa các điều khiển (nằm bên dưới)
        controls_panel = QFrame()
        controls_panel.setObjectName("controlsPanel")
        
        controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(15, 10, 15, 10)
        controls_layout.setSpacing(10)

        # Thanh trượt Zoom
        zoom_text_label = QLabel("Zoom:")
        zoom_text_label.setFont(QFont('Segoe UI', 12))

        # ======================================================================
        # THAY ĐỔI: Cấu hình slider cho giá trị lẻ
        # Phạm vi từ 10 đến 50, sẽ được chia cho 10 để ra 1.0 -> 5.0
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(50)
        self.zoom_slider.setValue(10) # Mặc định 1.0x
        # ======================================================================

        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setObjectName("zoomValueLabel")
        self.zoom_value_label.setFont(QFont('Segoe UI', 12))

        controls_layout.addWidget(zoom_text_label)
        controls_layout.addWidget(self.zoom_slider)
        controls_layout.addWidget(self.zoom_value_label)
        controls_layout.addStretch() # Đẩy nút hiệu chỉnh sang phải

        # Nút Hiệu chỉnh tâm
        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        controls_layout.addWidget(self.calibrate_button)
        
        main_layout.addWidget(controls_panel) # Thêm vùng điều khiển vào layout chính
        
        self.zoom_slider.valueChanged.connect(self._update_zoom_value_label)

        return panel

    def _update_zoom_value_label(self, value):
        # Chia cho 10.0 và định dạng với 1 chữ số thập phân
        zoom_factor = value / 10.0
        self.zoom_value_label.setText(f"{zoom_factor:.1f}x")

    def _create_right_column(self) -> QWidget:
        # Hàm này không thay đổi
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Kết quả mới nhất")
        title.setProperty("class", "panel-title")
        layout.addWidget(title)

        font_info = QFont('Segoe UI', 12)
        self.time_label = QLabel("Thời gian: --:--:--")
        self.target_name_label = QLabel("Tên mục tiêu: _______")
        self.score_label = QLabel("Điểm số: __")
        
        for label in [self.time_label, self.target_name_label, self.score_label]:
            label.setFont(font_info)
            layout.addWidget(label)
        
        result_image_title = QLabel("Ảnh kết quả:")
        result_image_title.setFont(font_info)
        layout.addWidget(result_image_title)
        
        self.result_image_label = VideoLabel()
        self.result_image_label.setMinimumSize(QSize(150, 150))
        self.result_image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.result_image_label)
        
        layout.addStretch()
        return panel

    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_image)

    def display_frame(self, frame_bgr):
        if frame_bgr is None: return
        self.current_frame = frame_bgr.copy()
        pixmap = self._convert_cv_to_pixmap(frame_bgr)
        self.camera_view_label.setPixmap(pixmap)

    def update_results(self, score: float, target_name: str, processed_frame_bgr):
        self.time_label.setText(f"Thời gian: {datetime.now().strftime('%H:%M:%S')}")
        self.target_name_label.setText(f"Tên mục tiêu: {target_name}")
        self.score_label.setText(f"Điểm số: {score}")
        
        if processed_frame_bgr is not None:
            pixmap = self._convert_cv_to_pixmap(processed_frame_bgr)
            self.result_image_label.setPixmap(pixmap)