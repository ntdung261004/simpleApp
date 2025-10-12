# file: gui/ui/ui_competition.py
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QSizePolicy, QGroupBox, QListWidget, QStackedWidget, QGridLayout
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter
from PySide6.QtCore import Qt, QPoint, Signal
import logging
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class VideoLabel(QLabel):
    clicked = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        
        # === THAY ĐỔI 1: Định nghĩa lại tỷ lệ (height / width) cho rõ ràng ===
        self.aspect_ratio = 4.0 / 3.0 # Tỷ lệ 3:4 (width:height) tương đương height/width = 4/3

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        
    def hasHeightForWidth(self): return True
    
    # === THAY ĐỔI 2: Cập nhật công thức tính cho phù hợp ===
    def heightForWidth(self, width):
        return int(width * self.aspect_ratio)

    def setPixmap(self, pixmap: QPixmap): self._pixmap = pixmap; self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event); return
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - scaled_pixmap.height()) / 2
        painter = QPainter(self)
        painter.drawPixmap(QPoint(int(x), int(y)), scaled_pixmap)

# --- Phần còn lại của file giữ nguyên, không thay đổi ---
class SquareImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent); self.setMinimumSize(50, 50); self.setAlignment(Qt.AlignCenter)
    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap; super().setPixmap(self._scaled_pixmap())
    def resizeEvent(self, event):
        if hasattr(self, '_pixmap') and not self._pixmap.isNull(): super().setPixmap(self._scaled_pixmap())
    def _scaled_pixmap(self) -> QPixmap:
        size = min(self.width(), self.height()); return self._pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

class CompetitionGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget { background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }
            QGroupBox { font-size: 16px; font-weight: bold; border: 1px solid #4a6278; border-radius: 8px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 2px 12px; background-color: #415a72; border-radius: 4px; }
            QPushButton { background-color: #1abc9c; color: white; font-size: 13px; font-weight: bold; border: none; padding: 8px 16px; border-radius: 8px; }
            QPushButton:hover { background-color: #16a085; }
            QPushButton#danger { background-color: #e74c3c; }
            QPushButton#danger:hover { background-color: #c0392b; }
            QLabel { font-size: 13px; }
            QSlider::groove:horizontal { height: 4px; background: #212f3d; margin: 2px 0; border-radius: 2px; }
            QSlider::handle:horizontal { background: #1abc9c; border: 1px solid #1abc9c; width: 16px; margin: -6px 0; border-radius: 8px; }
            #zoomValueLabel { color: #1abc9c; font-weight: bold; min-width: 35px; }
            VideoLabel { background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6; font-size: 24px; }
        """)
        root_layout = QVBoxLayout(self); root_layout.setContentsMargins(20, 10, 20, 20)
        title_label = QLabel("MÀN HÌNH THI ĐẤU"); title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont('Segoe UI', 18, QFont.Bold)); title_label.setStyleSheet("padding: 10px;"); root_layout.addWidget(title_label)
        columns_layout = QHBoxLayout(); columns_layout.setSpacing(20)
        columns_layout.addWidget(self._create_participants_column(), 3)
        columns_layout.addWidget(self._create_camera_column(), 4)
        columns_layout.addWidget(self._create_score_column(), 3)
        root_layout.addLayout(columns_layout)
    def _create_participants_column(self) -> QWidget:
        panel = QGroupBox("Danh sách Xạ thủ"); layout = QVBoxLayout(panel); layout.setContentsMargins(15, 25, 15, 15); layout.setSpacing(10)
        self.participants_list = QListWidget(); self.participants_list.setStyleSheet("font-size: 14px; border: 1px solid #4a6278;")
        layout.addWidget(self.participants_list, 1)
        self.back_button = QPushButton("Về Menu Thi đấu"); self.back_button.setObjectName("danger"); layout.addWidget(self.back_button); return panel
    def _create_camera_column(self) -> QWidget:
        panel = QGroupBox("Đường ngắm Trực tiếp"); layout = QVBoxLayout(panel); layout.setContentsMargins(15, 25, 15, 15); layout.setSpacing(10)
        self.camera_view_label = VideoLabel(); self.camera_view_label.setText("Vui lòng kết nối camera"); layout.addWidget(self.camera_view_label, 1)
        controls_panel = QWidget(); controls_layout = QVBoxLayout(controls_panel); controls_layout.setContentsMargins(0, 5, 0, 0); controls_layout.setSpacing(5)
        sliders_layout = QHBoxLayout(); sliders_layout.setSpacing(10)
        zoom_text_label = QLabel("Khoảng cách:"); self.zoom_slider = QSlider(Qt.Horizontal); self.zoom_slider.setRange(10, 50); self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x"); self.zoom_value_label.setObjectName("zoomValueLabel")
        gamma_text_label = QLabel("Ánh sáng:"); self.gamma_slider = QSlider(Qt.Horizontal); self.gamma_slider.setRange(1, 20); self.gamma_slider.setValue(10)
        self.gamma_value_label = QLabel("1.0"); self.gamma_value_label.setObjectName("zoomValueLabel")
        sliders_layout.addWidget(zoom_text_label); sliders_layout.addWidget(self.zoom_slider, 1); sliders_layout.addWidget(self.zoom_value_label)
        sliders_layout.addSpacing(20); sliders_layout.addWidget(gamma_text_label); sliders_layout.addWidget(self.gamma_slider, 1); sliders_layout.addWidget(self.gamma_value_label)
        buttons_layout = QHBoxLayout(); self.refresh_button = QPushButton("Làm mới"); self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        buttons_layout.addWidget(self.refresh_button); buttons_layout.addStretch(1); buttons_layout.addWidget(self.calibrate_button)
        controls_layout.addLayout(sliders_layout); controls_layout.addLayout(buttons_layout); layout.addWidget(controls_panel); return panel
    def _create_score_column(self) -> QWidget:
        panel = QGroupBox("Bảng điểm"); panel_layout = QVBoxLayout(panel); panel_layout.setContentsMargins(15, 25, 15, 15)
        self.score_stack = QStackedWidget(); panel_layout.addWidget(self.score_stack); start_turn_page = QWidget(); start_turn_layout = QVBoxLayout(start_turn_page)
        start_turn_layout.setAlignment(Qt.AlignCenter); self.start_turn_button = QPushButton("BẮT ĐẦU LƯỢT"); self.start_turn_button.setMinimumSize(200, 60)
        self.start_turn_button.setStyleSheet("font-size: 16px;"); start_turn_layout.addWidget(self.start_turn_button); scoreboard_page = QWidget()
        scoreboard_layout = QVBoxLayout(scoreboard_page); scoreboard_layout.setSpacing(10); shooter_info_box = QGroupBox("Thông tin Xạ thủ")
        shooter_info_layout = QVBoxLayout(shooter_info_box); self.shooter_name_label = QLabel("Tên: --"); self.shooter_class_label = QLabel("Đơn vị: --")
        shooter_info_layout.addWidget(self.shooter_name_label); shooter_info_layout.addWidget(self.shooter_class_label)
        targets_grid_layout = QGridLayout(); targets_grid_layout.setSpacing(10)
        self.target_1_widget, self.target_1_score_label = self._create_target_widget("Bia số 1", resource_path("assets/images/original/bia_4b.png"))
        self.target_2_widget, self.target_2_score_label = self._create_target_widget("Bia số 2", resource_path("assets/images/original/bia_4b.png"))
        self.target_3_widget, self.target_3_score_label = self._create_target_widget("Bia số 3", resource_path("assets/images/original/bia_4c.png"))
        self.target_4_widget, self.target_4_score_label = self._create_target_widget("Bia số 4", resource_path("assets/images/original/bia_4c.png"))
        targets_grid_layout.addWidget(self.target_1_widget, 0, 0); targets_grid_layout.addWidget(self.target_2_widget, 0, 1)
        targets_grid_layout.addWidget(self.target_3_widget, 1, 0); targets_grid_layout.addWidget(self.target_4_widget, 1, 1)
        summary_box = QGroupBox("Kết quả"); summary_layout = QVBoxLayout(summary_box)
        self.total_score_label = QLabel("Tổng điểm: 0"); self.ammo_count_label = QLabel("Số đạn còn lại: 12/12")
        font_summary = QFont(); font_summary.setPointSize(14); font_summary.setBold(True)
        self.total_score_label.setFont(font_summary); self.ammo_count_label.setFont(font_summary)
        summary_layout.addWidget(self.total_score_label); summary_layout.addWidget(self.ammo_count_label)
        scoreboard_layout.addWidget(shooter_info_box); scoreboard_layout.addLayout(targets_grid_layout, 1); scoreboard_layout.addWidget(summary_box)
        self.score_stack.addWidget(start_turn_page); self.score_stack.addWidget(scoreboard_page); return panel
    def _create_target_widget(self, title: str, image_path: str) -> tuple[QWidget, QLabel]:
        widget = QGroupBox(title); widget.setAlignment(Qt.AlignCenter); layout = QVBoxLayout(widget); layout.setSpacing(5); layout.setContentsMargins(5, 15, 5, 5)
        image_label = SquareImageLabel(); image_label.setPixmap(QPixmap(image_path))
        score_label = QLabel("Điểm: --"); score_label.setAlignment(Qt.AlignCenter); score_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #f1c40f;")
        layout.addWidget(image_label, 1); layout.addWidget(score_label); return widget, score_label
    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        if cv_img is None: return QPixmap()
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB); h, w, ch = rgb_image.shape; bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888); return QPixmap.fromImage(qt_image)
    def display_frame(self, frame_bgr):
        if frame_bgr is None: return
        pixmap = self._convert_cv_to_pixmap(frame_bgr); self.camera_view_label.setPixmap(pixmap)
    def clear_video_feed(self, message: str):
        self.camera_view_label.setPixmap(QPixmap()); self.camera_view_label.setText(message)