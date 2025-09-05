# gui/ui/ui_manage.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QFrame, QSizePolicy
)
from PySide6.QtGui import QFont, QPixmap, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect

class VideoLabel(QLabel):
    """Label hiển thị ảnh, luôn giữ tỉ lệ và fit trong khung."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background-color: #212f3d; border: 1px solid #4a6278; "
            "border-radius: 8px; color: #95a5a6; font-size: 16px;"
        )
        self.setText("Chưa có ảnh")

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        super().setPixmap(self._scaled_pixmap())

    def resizeEvent(self, event):
        if not self._pixmap.isNull():
            super().setPixmap(self._scaled_pixmap())
        super().resizeEvent(event)

    def _scaled_pixmap(self):
        return self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

class ManageGui(QWidget):
    def __init__(self):
        super().__init__()

        # ===== Style đồng bộ với ui_practice =====
        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Segoe UI';
            }
            QFrame#panel {
                background-color: #34495e;
                border-radius: 12px;
                border: 1px solid #4a6278;
            }
            QLabel#title {
                color: #ecf0f1;
                padding: 10px;
            }
            QLabel.panel-title {
                font-size: 16px;
                font-weight: bold;
                color: #ecf0f1;
            }
            QPushButton {
                background-color: #1abc9c;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                padding: 8px 18px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #16a085; }
            QPushButton#danger { background-color: #e74c3c; }
            QPushButton#danger:hover { background-color: #c0392b; }

            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #4a6278;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 2px 8px;
                background-color: #415a72;
                border-radius: 4px;
            }
            QListWidget {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 6px;
            }
            QTableWidget {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 6px;
                gridline-color: #4a6278;
            }
            QLabel#resultImage {
                background-color: #212f3d;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: #95a5a6;
                font-size: 18px;
            }
        """)

        # ===== Root layout =====
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 10, 20, 20)
        root_layout.setSpacing(15)

        # Title
        title_label = QLabel("QUẢN LÝ DANH SÁCH CHIẾN SĨ VÀ THỐNG KÊ KẾT QUẢ BẮN")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont('Segoe UI', 18, QFont.Bold)
        title_label.setFont(title_font)
        root_layout.addWidget(title_label)

        # Columns layout (3 cột: 2.5 - 5 - 2.5)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        root_layout.addLayout(columns_layout)

        # Left column (2.5)
        columns_layout.addWidget(self._create_left_column(), 25)
        # Center column (5)
        columns_layout.addWidget(self._create_center_column(), 50)
        # Right column (2.5)
        columns_layout.addWidget(self._create_right_column(), 25)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        panel.setGraphicsEffect(shadow)
        return panel

    def _create_left_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        soldier_box = QGroupBox("Danh sách Chiến sĩ")
        soldier_layout = QVBoxLayout(soldier_box)
        self.soldier_list = QListWidget()
        soldier_layout.addWidget(self.soldier_list)
        layout.addWidget(soldier_box, 1)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Thêm mới")
        self.back_button = QPushButton("Quay lại")
        self.back_button.setObjectName("danger")
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.back_button)
        layout.addLayout(buttons_layout)

        return panel

    def _create_center_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # --- Thông tin tổng thể ---
        overall_box = QGroupBox("Phân tích Phiên bắn được chọn")
        overall_layout = QFormLayout(overall_box)
        self.total_label = QLabel("N/A")
        self.avg_label = QLabel("N/A")
        self.time_label = QLabel("N/A")
        overall_layout.addRow("Tổng phát bắn:", self.total_label)
        overall_layout.addRow("Điểm trung bình:", self.avg_label)
        overall_layout.addRow("Thời gian:", self.time_label)
        layout.addWidget(overall_box, 1)  # chiếm nhiều không gian hơn

        # --- Chi tiết từng phát ---
        detail_box = QGroupBox("Thông tin chi tiết từng phát bắn")
        detail_layout = QVBoxLayout(detail_box)

        # Bảng chi tiết có giới hạn chiều cao (5–7 dòng)
        self.shot_table = QTableWidget(0, 4)
        self.shot_table.setHorizontalHeaderLabels(["Lần", "Thời gian", "Mục tiêu", "Điểm"])
        self.shot_table.horizontalHeader().setStretchLastSection(True)
        self.shot_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Đặt chiều cao tối đa cho bảng (mỗi dòng ~30px, 7 dòng ~210px)
        self.shot_table.setMaximumHeight(210)
        self.shot_table.setMinimumHeight(150)  # ít nhất 5 dòng

        detail_layout.addWidget(self.shot_table, 1)

        # --- Ảnh kết quả ---
        self.result_image = QLabel("Ảnh kết quả")
        self.result_image.setObjectName("resultImage")
        self.result_image.setAlignment(Qt.AlignCenter)
        self.result_image.setMinimumHeight(250)
        self.result_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_image.setScaledContents(False)  # Giữ tỉ lệ ảnh
        detail_layout.addWidget(self.result_image, 3)

        # --- Điều hướng ---
        nav_layout = QHBoxLayout()
        self.prev_shot_button = QPushButton("◀ Trước")

        self.shot_index_label = QLabel("Phát 0/0")
        self.shot_index_label.setAlignment(Qt.AlignCenter)
        self.shot_index_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.next_shot_button = QPushButton("Sau ▶")

        nav_layout.addWidget(self.prev_shot_button)
        nav_layout.addWidget(self.shot_index_label, 1)
        nav_layout.addWidget(self.next_shot_button)

        detail_layout.addLayout(nav_layout)

        layout.addWidget(detail_box, 4)  # detail chiếm nhiều hơn để ảnh rộng

        return panel

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        history_box = QGroupBox("Lịch sử bắn của Chiến sĩ được chọn")
        history_layout = QVBoxLayout(history_box)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        layout.addWidget(history_box)

        return panel
