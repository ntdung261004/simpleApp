# file: gui/ui/ui_practice.py
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame, 
    QSizePolicy, QGraphicsDropShadowEffect, QGroupBox, QComboBox
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QSize, Signal

class VideoLabel(QLabel):
    # Lớp tùy chỉnh để vẽ tâm ngắm và xử lý zoom
    def __init__(self, parent=None):
        super().__init__(parent)
        self.crosshair_pos = None
        self.zoom_factor = 1.0
        self.setScaledContents(False)
        self.setAlignment(Qt.AlignCenter)

    def set_crosshair(self, pos):
        self.crosshair_pos = pos
        self.update()

    def set_zoom(self, factor):
        self.zoom_factor = factor
        self.update()

    def paintEvent(self, event):
        if self.pixmap():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Tính toán vùng hiển thị dựa trên zoom
            pixmap = self.pixmap()
            widget_size = self.size()
            pixmap_size = pixmap.size()
            
            draw_w = pixmap_size.width() / self.zoom_factor
            draw_h = pixmap_size.height() / self.zoom_factor
            draw_x = (pixmap_size.width() - draw_w) / 2
            draw_y = (pixmap_size.height() - draw_h) / 2
            
            source_rect = Qt.QRect(draw_x, draw_y, draw_w, draw_h)
            target_rect = Qt.QRect(0, 0, widget_size.width(), widget_size.height())
            
            painter.drawPixmap(target_rect, pixmap, source_rect)

            if self.crosshair_pos:
                painter.setPen(QColor(255, 0, 0, 200))
                x, y = self.crosshair_pos.x(), self.crosshair_pos.y()
                painter.drawLine(x - 15, y, x + 15, y)
                painter.drawLine(x, y - 15, x, y + 15)
        else:
            super().paintEvent(event)


class MainGui(QWidget):
    def __init__(self):
        super().__init__()
        self.current_frame = None
        self._define_styles()
        self._setup_ui()

    def _define_styles(self):
        # Định nghĩa style tập trung để dễ dàng thay đổi
        self.setStyleSheet("""
            QWidget {
                color: #ecf0f1; /* Màu chữ trắng ngà */
            }
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 1px solid #566573;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #3d5064; /* Màu nền cho groupbox */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 5px 10px;
                background-color: #415a72;
                border-radius: 4px;
            }
            QLabel {
                font-size: 14px;
            }
            QComboBox {
                background-color: #566573;
                border-radius: 5px;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #566573;
                height: 8px;
                background: #566573;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1abc9c;
                border: 1px solid #1abc9c;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)

        self.primary_button_style = """
            QPushButton {
                background-color: #1abc9c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #16a085; }
        """
        self.danger_button_style = """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
        """

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Nền chính
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor("#2c3e50"))
        self.setPalette(p)

        # Cột trái: Camera và Điều khiển
        left_column = self._create_left_column()
        main_layout.addLayout(left_column, 75) # Chiếm 75% chiều rộng

        # Cột phải: Thông tin và Kết quả
        right_column_panel = self._create_right_column()
        main_layout.addWidget(right_column_panel, 25) # Chiếm 25%

    def _create_left_column(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Camera View
        self.camera_view_label = VideoLabel()
        self.camera_view_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_view_label.setStyleSheet("background-color: black; border-radius: 8px;")
        layout.addWidget(self.camera_view_label)

        # Bảng điều khiển
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        return layout

    def _create_right_column(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #34495e; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        
        # Panel thông tin
        info_panel = self._create_info_panel()
        layout.addWidget(info_panel)
        
        # Panel kết quả
        result_panel = self._create_result_panel()
        layout.addWidget(result_panel)

        layout.addStretch() # Đẩy các panel lên trên
        return panel

    def _create_control_panel(self):
        panel = QFrame()
        panel.setFixedHeight(120)
        panel.setStyleSheet("background-color: #34495e; border-radius: 8px;")
        layout = QHBoxLayout(panel)
        layout.setSpacing(20)

        # Group Điều khiển chính
        main_controls_group = QGroupBox("Điều Khiển")
        main_controls_layout = QHBoxLayout(main_controls_group)
        self.calibrateButton = QPushButton("Hiệu Chỉnh Tâm")
        self.calibrateButton.setStyleSheet(self.primary_button_style)
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(["bia_so_4", "bia_so_7_8", "bia_so_8"])
        main_controls_layout.addWidget(self.calibrateButton)
        main_controls_layout.addWidget(self.target_type_combo)
        layout.addWidget(main_controls_group)

        # Group Zoom
        zoom_group = QGroupBox("Phóng To")
        zoom_layout = QVBoxLayout(zoom_group)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(0, 99)
        zoom_layout.addWidget(self.zoom_slider)
        layout.addWidget(zoom_group)
        
        # Group Chức năng
        function_group = QGroupBox("Chức Năng")
        function_layout = QHBoxLayout(function_group)
        self.userButton = QPushButton("Người Bắn")
        self.userButton.setStyleSheet(self.primary_button_style)
        self.statsButton = QPushButton("Thống Kê")
        self.statsButton.setStyleSheet(self.primary_button_style)
        self.backButton = QPushButton("Quay Lại") # Nút mới
        self.backButton.setStyleSheet(self.danger_button_style)
        function_layout.addWidget(self.userButton)
        function_layout.addWidget(self.statsButton)
        function_layout.addWidget(self.backButton)
        layout.addWidget(function_group)

        return panel

    def _create_info_panel(self):
        group = QGroupBox("Thông Tin Phiên Bắn")
        layout = QVBoxLayout(group)
        self.user_name_label = QLabel("Người bắn: Chưa chọn")
        font = self.user_name_label.font(); font.setBold(True); self.user_name_label.setFont(font)
        layout.addWidget(self.user_name_label)
        return group

    def _create_result_panel(self):
        group = QGroupBox("Kết Quả")
        layout = QVBoxLayout(group)
        self.time_label = QLabel("Thời gian: --:--:--")
        self.target_name_label = QLabel("Loại bia: --")
        self.score_label = QLabel("Điểm: --")
        font = self.score_label.font(); font.setPointSize(18); font.setBold(True); self.score_label.setFont(font)
        self.result_image_label = QLabel()
        self.result_image_label.setAlignment(Qt.AlignCenter)
        self.result_image_label.setStyleSheet("background-color: #2c3e50; border-radius: 5px;")
        self.result_image_label.setMinimumHeight(200)

        layout.addWidget(self.time_label)
        layout.addWidget(self.target_name_label)
        layout.addWidget(self.score_label)
        layout.addWidget(self.result_image_label)
        return group
        
    def _convert_cv_to_pixmap(self, cv_img):
        if cv_img is None: return QPixmap()
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_image)

    # --- Các hàm public để control từ bên ngoài ---
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
        self.target_name_label.setText(f"Loại bia: {target_name}")
        self.score_label.setText(f"Điểm: {score}")
        if result_frame is not None:
            pixmap = self._convert_cv_to_pixmap(result_frame)
            self.result_image_label.setPixmap(pixmap.scaled(
                self.result_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def update_user_info(self, name):
        self.user_name_label.setText(f"Người bắn: {name}")

    def get_selected_target_type(self):
        return self.target_type_combo.currentText()

    def set_zoom(self, factor):
        self.camera_view_label.set_zoom(factor)

    def set_crosshair(self, pos):
        self.camera_view_label.set_crosshair(pos)