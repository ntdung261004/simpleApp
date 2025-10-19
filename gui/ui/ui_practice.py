# file: gui/ui/ui_practice.py

import cv2
import base64
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QGroupBox, QComboBox
)
import logging
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor, QIcon
from PySide6.QtCore import Qt, QSize, QPoint, QByteArray, Signal

logger = logging.getLogger(__name__) 

class VideoLabel(QLabel):
    clicked = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        self.aspect_ratio = 4.0 / 3.0
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setAlignment(Qt.AlignCenter)
        self._is_calibrating = False

    def set_calibration_mode(self, active: bool):
        self._is_calibrating = active
        self.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)
        self.setToolTip("Click để chọn tâm ngắm mới" if active else "")

    def mousePressEvent(self, event):
        if self._is_calibrating and event.button() == Qt.LeftButton:
            self.clicked.emit(event.pos())
        super().mousePressEvent(event)
        
    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return int(width / self.aspect_ratio)

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - scaled_pixmap.height()) / 2
        painter = QPainter(self)
        painter.drawPixmap(QPoint(int(x), int(y)), scaled_pixmap)


class MainGui(QWidget):
    # --- BẮT ĐẦU VÙNG THAY ĐỔI 1 ---
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        # Xóa dòng: self.current_frame = None
        self.setupUi()
        self._apply_labels()
    # --- KẾT THÚC VÙNG THAY ĐỔI 1 ---
        
    def setupUi(self):
        self.setStyleSheet("""
            QWidget { background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }
            QFrame#panel { background-color: #34495e; border-radius: 12px; border: 1px solid #4a6278; }
            QLabel#title { color: #ecf0f1; padding: 10px; }
            QLabel.panel-title { font-size: 16px; font-weight: bold; color: #ecf0f1; padding: 8px 15px; background-color: #415a72; border-radius: 6px; }
            QPushButton { background-color: #1abc9c; color: white; font-size: 14px; font-weight: bold; border: none; padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background-color: #16a085; }
            QPushButton#danger { background-color: #e74c3c; }
            QPushButton#danger:hover { background-color: #c0392b; }
            QPushButton#danger:disabled { background-color: #7f8c8d; }
            QSlider::groove:horizontal { border: 1px solid #2c3e50; height: 4px; background: #2c3e50; margin: 2px 0; border-radius: 2px; }
            QSlider::handle:horizontal { background: #1abc9c; border: 1px solid #1abc9c; width: 18px; margin: -7px 0; border-radius: 9px; }
            VideoLabel { background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6; font-size: 24px; }
            #controlsPanel { padding: 10px; }
            #zoomValueLabel { font-size: 13px; font-weight: bold; color: #1abc9c; min-width: 45px; }
            QComboBox { border: 1px solid #4a6278; border-radius: 4px; padding: 5px; background-color: #5d6d7e; min-width: 120px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #5d6d7e; color: #ecf0f1; }
            #refreshButton { background-color: #5d6d7e; border: 1px solid #4a6278; padding: 5px 10px; border-radius: 4px; min-width: 30px; }
            #refreshButton:hover { background-color: #718090; }
            QGroupBox { font-size: 14px; font-weight: bold; border: 1px solid #4a6278; border-radius: 8px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 2px 8px; background-color: #415a72; border-radius: 4px; }
        """)
        
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 10, 20, 20)
        root_layout.setSpacing(15)
        title_label = QLabel("MÀN HÌNH TẬP LUYỆN")
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

    def _apply_labels(self):
        labels = self.config.get("labels", {})
        trainee_label_text = labels.get("trainee", "Người học")
        self.soldier_select_label.setText(f"{trainee_label_text}:")

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame(); panel.setObjectName("panel")
        shadow_effect = QGraphicsDropShadowEffect(panel)
        shadow_effect.setBlurRadius(20); shadow_effect.setColor(QColor(0, 0, 0, 80)); shadow_effect.setOffset(0, 5)
        panel.setGraphicsEffect(shadow_effect)
        return panel

    def _create_camera_column(self) -> QWidget:
        panel = self._create_styled_panel(); main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(15, 15, 15, 15); main_layout.setSpacing(15)
        title_widget = QWidget(); title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0); title_layout.setSpacing(0)
        title = QLabel("Đường ngắm trực tiếp"); title.setProperty("class", "panel-title"); title.setAlignment(Qt.AlignCenter)
        title_layout.addStretch(1); title_layout.addWidget(title); title_layout.addStretch(1); main_layout.addWidget(title_widget)
        self.camera_view_label = VideoLabel(); self.camera_view_label.setText("Vui lòng kết nối camera"); main_layout.addWidget(self.camera_view_label, 1)
        controls_panel = QWidget(); controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(10, 5, 10, 0); controls_layout.setSpacing(10)
        self.refresh_button = QPushButton("Làm mới"); self.refresh_button.setObjectName("refreshButton"); controls_layout.addWidget(self.refresh_button)
        controls_layout.addStretch(1); zoom_text_label = QLabel("Khoảng cách:")
        self.zoom_slider = QSlider(Qt.Horizontal); self.zoom_slider.setMinimum(10); self.zoom_slider.setMaximum(50); self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x"); self.zoom_value_label.setObjectName("zoomValueLabel")
        controls_layout.addWidget(zoom_text_label); controls_layout.addWidget(self.zoom_slider, 2); controls_layout.addWidget(self.zoom_value_label)
        controls_layout.addStretch(1); self.calibrate_button = QPushButton("Hiệu chỉnh tâm"); controls_layout.addWidget(self.calibrate_button)
        main_layout.addWidget(controls_panel); self.zoom_slider.valueChanged.connect(self._update_zoom_value_label)
        return panel  

    def _update_zoom_value_label(self, value):
        zoom_factor = value / 10.0; self.zoom_value_label.setText(f"{zoom_factor:.1f}x")

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel(); layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(20)
        session_box = QGroupBox("Quản lý Lần bắn"); session_layout = QVBoxLayout(session_box)
        soldier_select_layout = QHBoxLayout(); self.soldier_select_label = QLabel()
        self.soldier_selector = QComboBox(); soldier_select_layout.addWidget(self.soldier_select_label); soldier_select_layout.addWidget(self.soldier_selector, 1)
        session_layout.addLayout(soldier_select_layout); session_buttons_layout = QHBoxLayout()
        self.session_button = QPushButton("Bắt đầu"); self.back_button = QPushButton("Về Menu"); self.back_button.setObjectName("danger")
        session_buttons_layout.addWidget(self.session_button); session_buttons_layout.addWidget(self.back_button)
        session_layout.addLayout(session_buttons_layout); result_box = QGroupBox("Kết quả mới nhất")
        result_layout = QVBoxLayout(result_box); font_info = QFont('Segoe UI', 12)
        self.time_label = QLabel("Thời gian: --:--:--"); self.target_name_label = QLabel("Tên mục tiêu: --"); self.score_label = QLabel("Điểm số: --")
        for label in [self.time_label, self.target_name_label, self.score_label]: label.setFont(font_info); result_layout.addWidget(label)
        result_image_title = QLabel("Ảnh kết quả:"); result_image_title.setFont(font_info); result_layout.addWidget(result_image_title)
        self.result_image_label = VideoLabel(); self.result_image_label.setMinimumHeight(150); result_layout.addWidget(self.result_image_label, 1)
        layout.addWidget(session_box); layout.addWidget(result_box, 1)
        return panel

    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        if cv_img is None: return QPixmap()
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB); h, w, ch = rgb_image.shape; bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888); return QPixmap.fromImage(qt_image)

    # --- BẮT ĐẦU VÙNG THAY ĐỔI 2 ---
    def display_frame(self, frame_bgr):
        if frame_bgr is None: return
        # Xóa dòng: self.current_frame = frame_bgr.copy()
        pixmap = self._convert_cv_to_pixmap(frame_bgr)
        self.camera_view_label.setPixmap(pixmap)
    # --- KẾT THÚC VÙNG THAY ĐỔI 2 ---
        
    def clear_video_feed(self, message: str):
        self.camera_view_label.setPixmap(QPixmap()); self.camera_view_label.setText(message)
        
    def update_results(self, time_str, target_name, score, result_frame):
        self.time_label.setText(f"Thời gian: {time_str}")
        self.target_name_label.setText(f"Tên mục tiêu: {target_name}")
        self.score_label.setText(f"Điểm số: {score}")
        pixmap = self._convert_cv_to_pixmap(result_frame)
        if pixmap.isNull(): self.result_image_label.setText("Không có ảnh kết quả")
        else: self.result_image_label.setPixmap(pixmap)