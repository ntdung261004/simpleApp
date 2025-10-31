# file: gui/ui/ui_competition.py
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QSizePolicy, QGroupBox, QListWidget, QStackedWidget, QGridLayout,
    QAbstractItemView
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import Qt, QPoint, Signal, QSize
import logging
from utils.resource_path import resource_path

# 1. Import scaler để sử dụng các hàm tính toán tỷ lệ
from utils.scaler import scaler

logger = logging.getLogger(__name__)

# --- Các lớp VideoLabel và SquareImageLabel giữ nguyên, không cần thay đổi ---
class VideoLabel(QLabel):
    clicked = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        self.aspect_ratio = 4.0 / 3.0
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self._is_calibrating = False

    def set_calibration_mode(self, active: bool):
        self._is_calibrating = active
        self.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)
        self.setToolTip("Click để chọn tâm ngắm mới" if active else "")

    def mousePressEvent(self, event):
        if self._is_calibrating and event.button() == Qt.LeftButton: self.clicked.emit(event.pos())
        super().mousePressEvent(event)

    def hasHeightForWidth(self): return True

    def heightForWidth(self, width): return int(width * self.aspect_ratio)

    def setPixmap(self, pixmap: QPixmap): self._pixmap = pixmap; self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - scaled_pixmap.height()) / 2
        painter.drawPixmap(QPoint(int(x), int(y)), scaled_pixmap)

class SquareImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(scaler.scale(50), scaler.scale(50))
        self.setAlignment(Qt.AlignCenter)
        self._pixmap = QPixmap()
        self.hit_points_relative = []

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def add_hit_marker(self, relative_point: tuple[float, float]):
        if relative_point:
            self.hit_points_relative.append(relative_point)
            self.update()

    def clear_hit_markers(self):
        self.hit_points_relative.clear()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if self._pixmap.isNull():
            return
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - scaled_pixmap.width()) / 2
        offset_y = (self.height() - scaled_pixmap.height()) / 2
        painter.drawPixmap(QPoint(int(offset_x), int(offset_y)), scaled_pixmap)
        pen = QPen(QColor("#e74c3c"))
        pen.setWidth(2)
        painter.setPen(pen)
        for rel_x, rel_y in self.hit_points_relative:
            draw_x = offset_x + (rel_x * scaled_pixmap.width())
            draw_y = offset_y + (rel_y * scaled_pixmap.height())
            marker_size = scaler.scale(6)
            painter.drawLine(int(draw_x - marker_size), int(draw_y), int(draw_x + marker_size), int(draw_y))
            painter.drawLine(int(draw_x), int(draw_y - marker_size), int(draw_x), int(draw_y + marker_size))


class CompetitionGui(QWidget):
    def __init__(self):
        super().__init__()
        # 2. Sử dụng f-string và scaler để tạo stylesheet động
        self.setStyleSheet(f"""
            QWidget {{ background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }}
            QGroupBox {{ font-size: {scaler.scale(16)}px; font-weight: bold; border: 1px solid #4a6278; border-radius: {scaler.scale(8)}px; margin-top: {scaler.scale(10)}px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: {scaler.scale(2)}px {scaler.scale(12)}px; background-color: #415a72; border-radius: {scaler.scale(4)}px; }}
            QPushButton {{ background-color: #1abc9c; color: white; font-size: {scaler.scale(13)}px; font-weight: bold; border: none; padding: {scaler.scale(8)}px {scaler.scale(16)}px; border-radius: {scaler.scale(8)}px; }}
            QPushButton:hover {{ background-color: #16a085; }} QPushButton:disabled {{ background-color: #7f8c8d; }}
            QPushButton#danger {{ background-color: #e74c3c; }} QPushButton#danger:hover {{ background-color: #c0392b; }}
            QLabel {{ font-size: {scaler.scale(13)}px; }}
            QSlider::groove:horizontal {{ height: {scaler.scale(4)}px; background: #212f3d; margin: {scaler.scale(2)}px 0; border-radius: {scaler.scale(2)}px; }}
            QSlider::handle:horizontal {{ background: #1abc9c; border: 1px solid #1abc9c; width: {scaler.scale(16)}px; margin: -{scaler.scale(6)}px 0; border-radius: {scaler.scale(8)}px; }}
            #zoomValueLabel, #gamma_value_label {{ color: #1abc9c; font-weight: bold; min-width: {scaler.scale(40)}px; }}
            VideoLabel {{ background-color: #212f3d; border: 1px solid #4a6278; border-radius: {scaler.scale(8)}px; color: #95a5a6; font-size: {scaler.scale(24)}px; }}
        """)
        self.setupUi()

    def setupUi(self):
        # 3. Sử dụng scaler để tính toán lề và khoảng cách
        margin = scaler.scale(20)
        spacing = scaler.scale(15)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(margin, scaler.scale(10), margin, margin)

        title_label = QLabel("MÀN HÌNH KIỂM TRA")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        # 4. Sử dụng scaler.font() để tạo font động
        title_label.setFont(scaler.font(18, bold=True))
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(scaler.scale(20))
        columns_layout.addWidget(self._create_participants_column(), 3)
        columns_layout.addWidget(self._create_camera_column(), 4)
        columns_layout.addWidget(self._create_score_column(), 3)
        root_layout.addLayout(columns_layout)

    def _create_participants_column(self) -> QWidget:
        panel = QGroupBox("Danh sách Người bắn")
        layout = QVBoxLayout(panel)
        margin = scaler.scale(15)
        layout.setContentsMargins(margin, scaler.scale(25), margin, margin)
        layout.setSpacing(scaler.scale(10))

        self.participants_list = QListWidget()
        self.participants_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.participants_list.setStyleSheet(f"font-size: {scaler.scale(14)}px; border: 1px solid #4a6278;")
        layout.addWidget(self.participants_list, 1)

        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Lưu Phiên")
        self.back_button = QPushButton("Về Menu Kiểm tra")
        self.back_button.setObjectName("danger")
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.back_button)
        layout.addLayout(buttons_layout)
        
        return panel

    def _create_camera_column(self) -> QWidget:
        panel = QGroupBox("Đường ngắm Trực tiếp")
        layout = QVBoxLayout(panel)
        margin = scaler.scale(15)
        layout.setContentsMargins(margin, scaler.scale(25), margin, margin)
        layout.setSpacing(scaler.scale(10))

        self.camera_view_label = VideoLabel()
        self.camera_view_label.setText("Vui lòng kết nối camera")
        layout.addWidget(self.camera_view_label, 1)

        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setContentsMargins(0, scaler.scale(5), 0, 0)
        controls_layout.setSpacing(scaler.scale(5))

        sliders_layout = QHBoxLayout()
        sliders_layout.setSpacing(scaler.scale(10))
        zoom_text_label = QLabel("Khoảng cách:")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 50)
        self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setObjectName("zoomValueLabel")
        gamma_text_label = QLabel("Ánh sáng:")
        self.gamma_slider = QSlider(Qt.Horizontal)
        self.gamma_slider.setRange(1, 20)
        self.gamma_slider.setValue(10)
        self.gamma_value_label = QLabel("1.0")
        self.gamma_value_label.setObjectName("zoomValueLabel")

        sliders_layout.addWidget(zoom_text_label)
        sliders_layout.addWidget(self.zoom_slider, 1)
        sliders_layout.addWidget(self.zoom_value_label)
        sliders_layout.addSpacing(scaler.scale(20))
        sliders_layout.addWidget(gamma_text_label)
        sliders_layout.addWidget(self.gamma_slider, 1)
        sliders_layout.addWidget(self.gamma_value_label)

        buttons_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Làm mới")
        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.calibrate_button)

        controls_layout.addLayout(sliders_layout)
        controls_layout.addLayout(buttons_layout)
        layout.addWidget(controls_panel)
        return panel

    def _create_score_column(self) -> QWidget:
        panel = QGroupBox("Bảng điểm")
        panel_layout = QVBoxLayout(panel)
        margin = scaler.scale(15)
        panel_layout.setContentsMargins(margin, scaler.scale(25), margin, margin)

        self.score_stack = QStackedWidget()
        panel_layout.addWidget(self.score_stack)

        start_turn_page = QWidget()
        start_turn_layout = QVBoxLayout(start_turn_page)
        start_turn_layout.setAlignment(Qt.AlignCenter)
        self.start_turn_button = QPushButton("BẮT ĐẦU LƯỢT")
        # 5. Scale kích thước tối thiểu và font của nút "Bắt đầu"
        self.start_turn_button.setMinimumSize(scaler.scale(200), scaler.scale(60))
        self.start_turn_button.setStyleSheet(f"font-size: {scaler.scale(16)}px;")
        start_turn_layout.addWidget(self.start_turn_button)

        scoreboard_page = QWidget()
        scoreboard_layout = QVBoxLayout(scoreboard_page)
        scoreboard_layout.setSpacing(scaler.scale(10))
        shooter_info_box = QGroupBox("Thông tin Người bắn")
        shooter_info_layout = QVBoxLayout(shooter_info_box)
        self.shooter_name_label = QLabel("Tên: --")
        self.shooter_class_label = QLabel("Đơn vị: --")
        shooter_info_layout.addWidget(self.shooter_name_label)
        shooter_info_layout.addWidget(self.shooter_class_label)
        
        targets_grid_layout = QGridLayout()
        targets_grid_layout.setSpacing(scaler.scale(10))
        self.target_1_widget, self.target_1_score_label, self.target_1_image_label = self._create_target_widget("Bia số 1 (3 viên)", resource_path("assets/images/original/bia_4b.png"))
        self.target_2_widget, self.target_2_score_label, self.target_2_image_label = self._create_target_widget("Bia số 2 (3 viên)", resource_path("assets/images/original/bia_4b.png"))
        self.target_3_widget, self.target_3_score_label, self.target_3_image_label = self._create_target_widget("Bia số 3 (3 viên)", resource_path("assets/images/original/bia_4c.png"))
        self.target_4_widget, self.target_4_score_label, self.target_4_image_label = self._create_target_widget("Bia số 4 (3 viên)", resource_path("assets/images/original/bia_4c.png"))
        targets_grid_layout.addWidget(self.target_1_widget, 0, 0)
        targets_grid_layout.addWidget(self.target_2_widget, 0, 1)
        targets_grid_layout.addWidget(self.target_3_widget, 1, 0)
        targets_grid_layout.addWidget(self.target_4_widget, 1, 1)
        
        summary_box = QGroupBox("Kết quả")
        summary_layout = QVBoxLayout(summary_box)
        self.total_score_label = QLabel("Tổng điểm: 0")
        self.ammo_count_label = QLabel("Số đạn còn lại: 12/12")
        # 6. Sử dụng scaler.font() cho các label tổng kết
        self.total_score_label.setFont(scaler.font(14, bold=True))
        self.ammo_count_label.setFont(scaler.font(14, bold=True))
        summary_layout.addWidget(self.total_score_label)
        summary_layout.addWidget(self.ammo_count_label)
        
        scoreboard_layout.addWidget(shooter_info_box)
        scoreboard_layout.addLayout(targets_grid_layout, 1)
        scoreboard_layout.addWidget(summary_box)
        
        self.score_stack.addWidget(start_turn_page)
        self.score_stack.addWidget(scoreboard_page)
        return panel

    def _create_target_widget(self, title: str, image_path: str) -> tuple[QWidget, QLabel, SquareImageLabel]:
        widget = QGroupBox(title)
        widget.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(widget)
        spacing = scaler.scale(5)
        margin = scaler.scale(5)
        layout.setSpacing(spacing)
        layout.setContentsMargins(margin, scaler.scale(15), margin, margin)
        
        image_label = SquareImageLabel()
        image_label.setPixmap(QPixmap(image_path))
        
        score_label = QLabel("Điểm: --")
        score_label.setAlignment(Qt.AlignCenter)
        # 7. Scale font cho label điểm của từng bia
        score_label.setStyleSheet(f"font-weight: bold; font-size: {scaler.scale(14)}px; color: #f1c40f;")
        
        layout.addWidget(image_label, 1)
        layout.addWidget(score_label)
        return widget, score_label, image_label

    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        if cv_img is None: return QPixmap()
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_image)

    def display_frame(self, frame_bgr):
        if frame_bgr is None: return
        pixmap = self._convert_cv_to_pixmap(frame_bgr)
        self.camera_view_label.setPixmap(pixmap)

    def clear_video_feed(self, message: str):
        self.camera_view_label.setPixmap(QPixmap())
        self.camera_view_label.setText(message)