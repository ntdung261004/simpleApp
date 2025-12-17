# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                               QSpacerItem, QSizePolicy, QFrame)
from PySide6.QtGui import QFont, QCursor

class Ui_MainMenu(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        
        # Layout chính
        self.main_layout = QVBoxLayout(Form)
        self.main_layout.setContentsMargins(40, 20, 40, 20)
        self.main_layout.setSpacing(10) 

        # [1] SPACER TRÊN: 2 phần
        # Giữ chữ nằm ở khoảng 20-25% màn hình (khớp với phần trên của Logo)
        self.main_layout.addStretch(2)

        # --- KHỐI CHỮ ---
        # 1. TÊN ĐƠN VỊ
        self.label_unit = QLabel(Form)
        self.label_unit.setObjectName("label_unit")
        self.label_unit.setAlignment(Qt.AlignCenter)
        self.label_unit.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.main_layout.addWidget(self.label_unit)

        # 2. TIÊU ĐỀ CHÍNH
        self.label_title = QLabel(Form)
        self.label_title.setObjectName("label_title")
        self.label_title.setAlignment(Qt.AlignCenter)
        self.label_title.setWordWrap(True)
        self.label_title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.label_title.setStyleSheet("color: white; margin-top: 5px;")
        self.main_layout.addWidget(self.label_title)

        # 3. TIÊU ĐỀ PHỤ
        self.label_subtitle = QLabel(Form)
        self.label_subtitle.setObjectName("label_subtitle")
        self.label_subtitle.setAlignment(Qt.AlignCenter)
        self.label_subtitle.setFont(QFont("Segoe UI", 28, QFont.Bold)) 
        self.label_subtitle.setStyleSheet("color: white; margin-top: 0px;")
        self.main_layout.addWidget(self.label_subtitle)

        # [2] SPACER GIỮA: 1 phần (Giảm nhỏ lại)
        # Kéo nút lên gần chữ hơn, tạo sự liên kết
        self.main_layout.addStretch(1)

        # --- KHỐI NÚT ---
        self.button_container = QFrame(Form)
        self.button_container.setStyleSheet("background: transparent;")
        self.btn_layout = QVBoxLayout(self.button_container)
        self.btn_layout.setSpacing(20)
        self.btn_layout.setContentsMargins(0, 0, 0, 0)

        btn_style = """
            QPushButton {
                background-color: #34495e;
                color: white;
                border: 2px solid #4a6278;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
                padding-left: 30px;
            }
            QPushButton:hover {
                background-color: #1abc9c;
                border-color: #16a085;
            }
            QPushButton:pressed {
                background-color: #16a085;
            }
        """

        self.practice_button = QPushButton("  BẮT ĐẦU LUYỆN TẬP", self.button_container)
        self.practice_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.practice_button.setStyleSheet(btn_style)
        self.practice_button.setMinimumHeight(55)
        self.btn_layout.addWidget(self.practice_button)

        self.stats_button = QPushButton("  QUẢN LÝ && THỐNG KÊ", self.button_container)
        self.stats_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.stats_button.setStyleSheet(btn_style)
        self.stats_button.setMinimumHeight(55)
        self.btn_layout.addWidget(self.stats_button)

        self.exit_button = QPushButton("  THOÁT CHƯƠNG TRÌNH", self.button_container)
        self.exit_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.exit_button.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
                padding-left: 30px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        self.exit_button.setMinimumHeight(55)
        self.btn_layout.addWidget(self.exit_button)

        # Thêm container nút vào layout chính
        btn_wrapper = QVBoxLayout()
        btn_wrapper.addWidget(self.button_container)
        btn_wrapper.setAlignment(Qt.AlignCenter)
        self.main_layout.addLayout(btn_wrapper)

        # [3] SPACER DƯỚI: 5 phần (Lớn nhất)
        # Đẩy mạnh toàn bộ nội dung lên trên, giúp nút nằm ở khoảng giữa màn hình
        self.main_layout.addStretch(5)

        # 5. FOOTER
        self.label_footer = QLabel(Form)
        self.label_footer.setObjectName("label_footer")
        self.label_footer.setAlignment(Qt.AlignCenter)
        self.label_footer.setStyleSheet("color: #7f8c8d; font-size: 18px; font-style: italic;")
        self.main_layout.addWidget(self.label_footer)