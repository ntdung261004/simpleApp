# gui/gui.py
import cv2
import base64
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QGroupBox, QComboBox
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor, QIcon, QCursor
from PySide6.QtCore import Qt, QSize, QPoint, QByteArray, Signal
from datetime import datetime

REFRESH_ICON_BASE64 = b"iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAANQSURBVFhHzZdrSFRhGMefr2w0C6kUStMvS6tQilBZEKVoIYWoKC2K6EKzCKJd2IqINuIiRIsgEhF0I4joRhZkIRZWQWkJq5A0SjNzi/NzzvmeM/fAnR/24MDB+Z7zPZ/5Z+Z5mIxxjPG/a4CgOoCgOoCgOrQpA611B9B5A+g8AfSeIFrrD6jzA5hRB/CtA/haB/C1A/g1sA7g1wDcM0A3AbQZQLcBtBtAtwH01o3WOgD0ngB6TwC9J4hWawDoPAG0HUCbAbQZoNkE0PYY2bVwA0D7A9T6AXQeQOf3g9Y6Cyg6gKADKDoIOgUouoAgs4/WOgcoOgA6D6DTANoMoNkE0H7AbQdoNwF0f5i1hgKFlFrpDdA5AI2L0GkAbQZoNkE0f4DNBtBuB0i1/gCMaFBrLSAo6QA6L0CnATQZoAkA7QZoN4B2E0C7PaDdA4j2+gMwogGt9QZQUgU0f4DNBtBmAC0D6DTAbgdoN4F2E2gfA9uHwPYhsD0I7M1P97sH0FqPAbTWEUDQCzSfgc4DaDMANgM0AagB2k2g/QzsD8D2YbA9COzNR/e1f3kQWB+M1loAKDoAOr+BpgM0AagB2k3A7A9gfwA2fwCbf8DmA2hzgDb/gM0/YANA9QcwtADtL8BqrQHUEoE2g7/Z/Qc0HUCbAbS/AGt/gNY/YH0I3kQh2P0J9P4A2gpAPf3x0g/QagNoM0CbAdoKQPc3sL8Ia91xZpQ3aL0C2gygzQCaAHSfgd4fQOsHYPsQWB/E6/UDMKIBrXUeUFIBtJlAG4CmA+g8gM4DaD+EdhNofwQ2HwKbh8DmoX35TjYFtNYTQNEFtP/A/gM0GaBJAO0maG0A7Z/B5h/Q5h/Q5gNobQDtJkAbQNuHwPYhsDkI3AaB7S/AWvsjWmsaoCgXtH4AmwHQagBNB2gyQBMg2gPQ3QHaLaCt/WB7ANgehLYHsS103x9gRBda6wCgqAroNIDsDUD3AdpdQLcLaLeAtgdQWz9YN4C17gIKKICi1f4DNDmATQdq3QG1/oDWH2C9HxBtdQJQVAE0HUC3AdotoNsF1BqA1g6gfQzsHwK7h8D2IfDtH2Bt/QCMaEBrPQUUf4DdA9DdA9pdQLcLqDUAa+0GaG0A7Z/B5h/Q5gNobQDtJkAbQNuHwPYhsDkI3AaB7S/AWvsdWmuOAGq9gQDtG0C7H6DNAA0AaDZBswGw/QE0HUC3AdpdQN0E1BqA1g6gfQzsHwK7h8D2IfDtH2Bt/QCMaEBrPQIU7RughwvQdADtL2CtPYBWH2CtH5hRB3CtD8yrD8A6gKADKDoAqx6Aqx6AqgcoOoCgOoCgOoCgj/NPGI4xjhV+AYwU9vTxx/IyAAAAAElFTSuQmCC"

# ======================================================================
# SỬ DỤNG LẠI LỚP VIDEOLABEL ỔN ĐỊNH CỦA BẠN
# với một tinh chỉnh nhỏ ở setSizePolicy để "hòa hợp" với layout
# ======================================================================
# CHÚ THÍCH: Thay đổi trong lớp VideoLabel của file gui.py

class VideoLabel(QLabel):
    clicked = Signal(QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.aspect_ratio = 3.0 / 4.0
        # THAY ĐỔI: Chuyển sang Expanding để widget tự co giãn theo chiều rộng
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setAlignment(Qt.AlignCenter)
        self._is_calibrating = False

    # ... (Các hàm còn lại của VideoLabel giữ nguyên) ...
    def set_calibration_mode(self, active: bool):
        self._is_calibrating = active
        if active:
            self.setCursor(Qt.CrossCursor)
            self.setToolTip("Click để chọn tâm ngắm mới")
        else:
            self.setCursor(Qt.ArrowCursor)
            self.setToolTip("")

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
    def __init__(self):
        super().__init__()
        self.current_frame = None
        self.setStyleSheet("""
            QWidget { background-color: #F8F8F8; color: #333333; font-family: 'Segoe UI'; }
            QFrame#panel { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E0E0E0; }
            QLabel#title { color: #0078D4; padding: 10px; }
            QLabel.panel-title { font-size: 16px; font-weight: bold; color: #333333; }
            QPushButton {
                background-color: #0078D4; color: #FFFFFF; font-size: 14px;
                font-weight: bold; border: none; padding: 10px 20px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #005A9E; }
            QSlider::groove:horizontal { border: 1px solid #CCCCCC; height: 4px; background: #CCCCCC; margin: 2px 0; border-radius: 2px; }
            QSlider::handle:horizontal { background: #0078D4; border: 1px solid #0078D4; width: 18px; margin: -7px 0; border-radius: 9px; }
            VideoLabel { background-color: #EFEFEF; border: 2px dashed #B0B0B0; border-radius: 8px; color: #888888; font-size: 30px; }
            #controlsPanel { background-color: #FDFDFD; border-top: 1px solid #E0E0E0; padding: 10px; }
            #zoomValueLabel { font-size: 13px; font-weight: bold; color: #0078D4; min-width: 45px; }
            QComboBox { border: 1px solid #CCCCCC; border-radius: 4px; padding: 5px; background-color: white; min-width: 120px; }
            #refreshButton { background-color: #EFEFEF; border: 1px solid #DDD; padding: 5px 10px; border-radius: 4px; min-width: 30px; }
            #refreshButton:hover { background-color: #E0E0E0; }
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
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        video_area = QWidget()
        video_area_layout = QVBoxLayout(video_area)
        video_area_layout.setContentsMargins(20, 20, 20, 15)
        video_area_layout.setSpacing(15)
        title = QLabel("Đường ngắm")
        title.setProperty("class", "panel-title")
        video_area_layout.addWidget(title)

        self.camera_view_label = VideoLabel()
        self.camera_view_label.setText("Vui lòng kết nối camera và nhấn 'Làm mới'")
        video_area_layout.addWidget(self.camera_view_label)
        main_layout.addWidget(video_area)
        controls_panel = QFrame()
        controls_panel.setObjectName("controlsPanel")
        controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(15, 10, 15, 10)
        controls_layout.setSpacing(10)
        self.refresh_button = QPushButton("Làm mới Camera")
        self.refresh_button.setObjectName("refreshButton")
        icon_data = QByteArray.fromBase64(REFRESH_ICON_BASE64)
        pixmap = QPixmap()
        pixmap.loadFromData(icon_data)
        icon = QIcon(pixmap)
        self.refresh_button.setIcon(icon)
        
        controls_layout.addWidget(self.refresh_button)
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        controls_layout.addWidget(separator)
        zoom_text_label = QLabel("Khoảng cách:")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(50)
        self.zoom_slider.setValue(10)
        
        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setObjectName("zoomValueLabel")
        controls_layout.addWidget(zoom_text_label)
        controls_layout.addWidget(self.zoom_slider)
        controls_layout.addWidget(self.zoom_value_label)
        controls_layout.addStretch()
        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        
        controls_layout.addWidget(self.calibrate_button)
        main_layout.addWidget(controls_panel)
        self.zoom_slider.valueChanged.connect(self._update_zoom_value_label)
        return panel

    def _update_zoom_value_label(self, value):
        zoom_factor = value / 10.0
        self.zoom_value_label.setText(f"{zoom_factor:.1f}x")

# CHÚ THÍCH: Thay đổi trong hàm _create_right_column của file gui.py

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignTop)
        
                # ======================================================================
        # CHÚ THÍCH: THÊM KHU VỰC QUẢN LÝ LẦN BẮN
        # ======================================================================
        session_box = QGroupBox("Quản lý Lần bắn")
        session_layout = QVBoxLayout(session_box)
        
        # Layout cho việc chọn người bắn
        user_select_layout = QHBoxLayout()
        user_select_label = QLabel("Người bắn:")
        self.user_selector = QComboBox()
        user_select_layout.addWidget(user_select_label)
        user_select_layout.addWidget(self.user_selector, 1) # Cho combobox chiếm nhiều không gian hơn
        session_layout.addLayout(user_select_layout)
        
        # Layout cho các nút điều khiển
        session_buttons_layout = QHBoxLayout()
        self.userbutton = QPushButton("Quản lý")
        self.session_button = QPushButton("Bắt đầu Lần bắn")
        self.stats_button = QPushButton("Xem Thống kê") # NÚT MỚI
        session_buttons_layout.addWidget(self.manage_users_button)
        session_buttons_layout.addWidget(self.stats_button)
        session_buttons_layout.addWidget(self.session_button)
        session_layout.addLayout(session_buttons_layout)
        
        layout.addWidget(session_box)
        # ======================================================================

        
        title = QLabel("Kết quả mới nhất")
        title.setProperty("class", "panel-title")
        layout.addWidget(title)
        
        font_info = QFont('Segoe UI', 12)
        self.time_label = QLabel("Thời gian: --:--:--")
        self.target_name_label = QLabel("Tên mục tiêu: --")
        self.score_label = QLabel("Điểm số: --")
        for label in [self.time_label, self.target_name_label, self.score_label]:
            label.setFont(font_info)
            layout.addWidget(label)
            
        result_image_title = QLabel("Ảnh kết quả:")
        result_image_title.setFont(font_info)
        layout.addWidget(result_image_title)
        
        self.result_image_label = VideoLabel()
        

        layout.addWidget(self.result_image_label)
        layout.addStretch() # Giữ addStretch để các label dồn lên trên

        return panel
    
    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        if cv_img is None: return QPixmap()
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

    def clear_video_feed(self, message: str):
        self.camera_view_label.setPixmap(QPixmap())
        self.camera_view_label.setText(message)

    def update_results(self, time_str, target_name, score, result_frame):
        self.time_label.setText(f"Thời gian: {time_str}")
        self.target_name_label.setText(f"Tên mục tiêu: {target_name}")
        self.score_label.setText(f"Điểm số: {score}")
        
        pixmap = self._convert_cv_to_pixmap(result_frame)
        if pixmap.isNull():
            self.result_image_label.setText("Không có ảnh kết quả")
        else:
            self.result_image_label.setPixmap(pixmap)