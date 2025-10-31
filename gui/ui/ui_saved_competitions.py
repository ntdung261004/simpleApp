# file: gui/ui/ui_saved_competitions.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QFrame
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, QSize
from utils.resource_path import resource_path

# 1. Import scaler để sử dụng các hàm tính toán tỷ lệ
from utils.scaler import scaler

class SavedCompetitionItemWidget(QWidget):
    """Widget tùy chỉnh để hiển thị một mục trong danh sách các phiên đã lưu."""
    def __init__(self, name: str, date: str, participants: int, parent=None):
        super().__init__(parent)
        # 2. Sử dụng f-string và scaler để tạo stylesheet động cho widget item
        self.setStyleSheet(f"""
            QWidget {{ background-color: #34495e; border-radius: {scaler.scale(8)}px; }}
            QLabel {{ color: white; background-color: transparent; border: none; }}
            #name_label {{ font-size: {scaler.scale(14)}px; font-weight: bold; }}
            #date_label {{ color: #bdc3c7; font-size: {scaler.scale(11)}px; }}
            #count_label {{ 
                font-size: {scaler.scale(12)}px; font-weight: bold; 
                padding: {scaler.scale(4)}px {scaler.scale(10)}px; 
                border-radius: {scaler.scale(6)}px; 
                background-color: #415a72; 
            }}
        """)
        main_layout = QHBoxLayout(self)
        # 3. Scale lề và khoảng cách cho layout của item
        margin_v = scaler.scale(10)
        margin_h = scaler.scale(15)
        main_layout.setContentsMargins(margin_h, margin_v, margin_h, margin_v)
        main_layout.setSpacing(scaler.scale(15))

        icon_label = QLabel()
        # 4. Scale kích thước cố định của icon
        icon_size = scaler.scale(32)
        icon_label.setFixedSize(icon_size, icon_size)
        icon_label.setPixmap(QPixmap(resource_path("assets/images/icon/user_icon.png")))
        icon_label.setScaledContents(True)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(scaler.scale(2))
        name_label = QLabel(name)
        name_label.setObjectName("name_label")
        date_label = QLabel(date)
        date_label.setObjectName("date_label")
        info_layout.addWidget(name_label)
        info_layout.addWidget(date_label)

        count_label = QLabel(f"{participants} người")
        count_label.setObjectName("count_label")
        count_label.setAlignment(Qt.AlignCenter)

        main_layout.addWidget(icon_label)
        main_layout.addLayout(info_layout, 1)
        main_layout.addWidget(count_label)


class SavedCompetitionsGui(QWidget):
    """Lớp định nghĩa giao diện chính cho cửa sổ các phiên đã lưu."""
    def __init__(self):
        super().__init__()
        self.setObjectName("SavedCompetitionsWidget")
        # 5. Sử dụng f-string và scaler cho stylesheet của cửa sổ chính
        self.setStyleSheet(f"""
            #SavedCompetitionsWidget {{ background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }}
            QFrame#panel {{ background-color: #34495e; border-radius: {scaler.scale(12)}px; border: 1px solid #4a6278; }}
            QLabel#title {{ font-size: {scaler.scale(20)}px; font-weight: bold; color: #ecf0f1; padding: {scaler.scale(10)}px; }}
            QGroupBox {{ font-size: {scaler.scale(16)}px; font-weight: bold; border: 1px solid #4a6278; border-radius: {scaler.scale(8)}px; margin-top: {scaler.scale(10)}px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: {scaler.scale(2)}px {scaler.scale(12)}px; background-color: #415a72; border-radius: {scaler.scale(4)}px; }}
            QPushButton {{ background-color: #1abc9c; color: white; font-size: {scaler.scale(14)}px; font-weight: bold; border: none; padding: {scaler.scale(10)}px {scaler.scale(20)}px; border-radius: {scaler.scale(8)}px; }}
            QPushButton:hover {{ background-color: #16a085; }}
            QPushButton:disabled {{ background-color: #7f8c8d; color: #bdc3c7; }}
            QPushButton#danger {{ background-color: #e74c3c; }}
            QPushButton#danger:hover {{ background-color: #c0392b; }}
            QListWidget {{ background-color: #2c3e50; border: 1px solid #4a6278; border-radius: {scaler.scale(8)}px; padding: {scaler.scale(5)}px; }}
            QListWidget::item {{ border-bottom: 1px solid #4a6278; }}
            QListWidget::item:selected {{ background-color: #1abc9c; border-radius: {scaler.scale(6)}px; }}
        """)
        self.setupUi()

    def setupUi(self):
        # 6. Sử dụng scaler để tính toán lề và khoảng cách
        margin = scaler.scale(20)
        spacing = scaler.scale(15)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(margin, scaler.scale(10), margin, margin)
        root_layout.setSpacing(spacing)

        title_label = QLabel("CÁC PHIÊN KIỂM TRA ĐÃ LƯU")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        # 7. Sử dụng scaler.font() để tạo font động cho tiêu đề
        title_label.setFont(scaler.font(20, bold=True))
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(scaler.scale(20))
        root_layout.addLayout(columns_layout)

        columns_layout.addWidget(self._create_left_column(), 2)
        columns_layout.addWidget(self._create_right_column(), 1)

    def _create_left_column(self) -> QWidget:
        panel = QGroupBox("Danh sách Phiên kiểm tra")
        layout = QVBoxLayout(panel)
        margin_h = scaler.scale(15)
        layout.setContentsMargins(margin_h, scaler.scale(25), margin_h, margin_h)

        self.competition_list = QListWidget()
        self.competition_list.setSpacing(scaler.scale(5))
        layout.addWidget(self.competition_list)

        return panel

    def _create_right_column(self) -> QWidget:
        panel = QGroupBox("Thao tác")
        layout = QVBoxLayout(panel)
        margin = scaler.scale(20)
        layout.setContentsMargins(margin, scaler.scale(30), margin, margin)
        layout.setSpacing(scaler.scale(15))
        layout.setAlignment(Qt.AlignTop)

        self.continue_button = QPushButton("Tiếp tục Kiểm tra")
        self.delete_button = QPushButton("Xóa Phiên")
        self.delete_button.setObjectName("danger")
        self.back_button = QPushButton("Về Menu")
        self.back_button.setObjectName("danger")

        layout.addWidget(self.continue_button)
        layout.addWidget(self.delete_button)
        layout.addStretch(1)
        layout.addWidget(self.back_button)

        return panel