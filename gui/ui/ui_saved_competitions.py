# file: gui/ui/ui_saved_competitions.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QFrame
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt
from utils.resource_path import resource_path

class SavedCompetitionItemWidget(QWidget):
    """Widget tùy chỉnh để hiển thị một mục trong danh sách các phiên đã lưu."""
    def __init__(self, name: str, date: str, participants: int, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget { background-color: #34495e; border-radius: 8px; }
            QLabel { color: white; background-color: transparent; border: none; }
            #name_label { font-size: 14px; font-weight: bold; }
            #date_label { color: #bdc3c7; font-size: 11px; }
            #count_label { font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: #415a72; }
        """)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(15)

        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setPixmap(QPixmap(resource_path("assets/images/icon/user_icon.png")))
        icon_label.setScaledContents(True)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
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
        self.setStyleSheet("""
            #SavedCompetitionsWidget { background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }
            QFrame#panel { background-color: #34495e; border-radius: 12px; border: 1px solid #4a6278; }
            QLabel#title { font-size: 20px; font-weight: bold; color: #ecf0f1; padding: 10px; }
            QGroupBox { font-size: 16px; font-weight: bold; border: 1px solid #4a6278; border-radius: 8px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 2px 12px; background-color: #415a72; border-radius: 4px; }
            QPushButton { background-color: #1abc9c; color: white; font-size: 14px; font-weight: bold; border: none; padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background-color: #16a085; }
            QPushButton:disabled { background-color: #7f8c8d; color: #bdc3c7; }
            QPushButton#danger { background-color: #e74c3c; }
            QPushButton#danger:hover { background-color: #c0392b; }
            QListWidget { background-color: #2c3e50; border: 1px solid #4a6278; border-radius: 8px; padding: 5px; }
            QListWidget::item { border-bottom: 1px solid #4a6278; }
            QListWidget::item:selected { background-color: #1abc9c; border-radius: 6px; }
        """)
        self.setupUi()

    def setupUi(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 10, 20, 20)
        root_layout.setSpacing(15)

        title_label = QLabel("CÁC PHIÊN KIỂM TRA ĐÃ LƯU")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        root_layout.addLayout(columns_layout)

        columns_layout.addWidget(self._create_left_column(), 2)
        columns_layout.addWidget(self._create_right_column(), 1)

    def _create_left_column(self) -> QWidget:
        panel = QGroupBox("Danh sách Phiên kiểm tra")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 25, 15, 15)

        self.competition_list = QListWidget()
        self.competition_list.setSpacing(5)
        layout.addWidget(self.competition_list)

        return panel

    def _create_right_column(self) -> QWidget:
        panel = QGroupBox("Thao tác")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignTop)

        self.continue_button = QPushButton("Tiếp tục Kiểm tra")
        self.delete_button = QPushButton("Xóa Phiên")
        self.delete_button.setObjectName("danger")
        self.back_button = QPushButton("Về Menu")
        self.back_button.setObjectName("danger")

        layout.addWidget(self.continue_button)
        layout.addWidget(self.delete_button)
        layout.addStretch(1) # Đẩy nút quay lại xuống dưới
        layout.addWidget(self.back_button)

        return panel