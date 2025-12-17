# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                               QFrame, QApplication)
from PySide6.QtGui import QCursor

class Ui_MainMenu(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        
        # --- 1. LOGIC SCALING (GIỐNG FILE MẪU) ---
        # Lấy độ phân giải màn hình chính
        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        
        # [CẤU HÌNH] Kích thước chuẩn thiết kế (Base Height). 
        # Bạn có thể sửa thành 900.0 hoặc 1080.0 tùy màn hình gốc của bạn.
        BASE_DESIGN_HEIGHT = 1080.0 
        scale_factor = screen_height / BASE_DESIGN_HEIGHT

        # Hàm helper để scale kích thước (padding, margin, width, height)
        def scale_size(base_size):
            return max(1, int(base_size * scale_factor))

        # Hàm helper để scale cỡ chữ (font-size)
        def scale_font(base_size):
            return max(10, int(base_size * scale_factor))
        # -----------------------------------------

        # Layout chính
        self.main_layout = QVBoxLayout(Form)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0) 

        # [SPACER TRÊN] Tỷ lệ 2
        self.main_layout.addStretch(2)

        # --- KHỐI CHỮ (TEXT) ---
        # Tại đây bạn có thể chỉnh cỡ chữ chuẩn (ví dụ 24, 48) dễ dàng
        
        # 1. TÊN ĐƠN VỊ
        self.label_unit = QLabel(Form)
        self.label_unit.setObjectName("label_unit")
        self.label_unit.setAlignment(Qt.AlignCenter)
        self.label_unit.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: {scale_font(24)}px; 
            font-weight: 500;
            margin-top: {scale_size(10)}px;
            color: #f1c40f; /* Màu vàng mặc định (sẽ bị ghi đè bởi config nếu có) */
            background: transparent;
            letter-spacing: 1px;
        """)
        self.main_layout.addWidget(self.label_unit)

        # 2. TIÊU ĐỀ CHÍNH
        self.label_title = QLabel(Form)
        self.label_title.setObjectName("label_title")
        self.label_title.setAlignment(Qt.AlignCenter)
        self.label_title.setWordWrap(True)
        self.label_title.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: {scale_font(34)}px; /* Cỡ chữ to */
            font-weight: 600;
            color: white;
            background: transparent;
            margin-top: {scale_size(10)}px;
        """)
        self.main_layout.addWidget(self.label_title)

        # 3. TIÊU ĐỀ PHỤ
        self.label_subtitle = QLabel(Form)
        self.label_subtitle.setObjectName("label_subtitle")
        self.label_subtitle.setAlignment(Qt.AlignCenter)
        self.label_subtitle.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: {scale_font(36)}px; /* Cỡ chữ bằng tiêu đề */
            font-weight: 600;
            color: white;
            background: transparent;
            margin-top: 0px;
        """)
        self.main_layout.addWidget(self.label_subtitle)

        # [SPACER GIỮA] Tỷ lệ 1
        self.main_layout.addStretch(1)

        # --- KHỐI NÚT (BUTTONS) ---
        self.button_container = QFrame(Form)
        self.button_container.setStyleSheet("background: transparent;")
        self.btn_layout = QVBoxLayout(self.button_container)
        self.btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_layout.setSpacing(scale_size(25)) # Khoảng cách giữa các nút

        # Cấu hình kích thước nút chuẩn
        btn_height = scale_size(70) 
        btn_font = scale_font(20)
        btn_padding = scale_size(15)
        btn_padding_left = scale_size(40)
        btn_radius = scale_size(10)
        btn_border = max(1, scale_size(2))

        # CSS Template cho nút
        common_btn_style = f"""
            QPushButton {{
                background-color: #34495e;
                color: white;
                border: {btn_border}px solid #4a6278;
                border-radius: {btn_radius}px;
                padding: {btn_padding}px;
                font-family: 'Segoe UI';
                font-size: {btn_font}px;
                font-weight: bold;
                text-align: left;
                padding-left: {btn_padding_left}px;
            }}
            QPushButton:hover {{
                background-color: #1abc9c;
                border-color: #16a085;
            }}
            QPushButton:pressed {{
                background-color: #16a085;
            }}
        """

        self.practice_button = QPushButton("  BẮT ĐẦU LUYỆN TẬP", self.button_container)
        self.practice_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.practice_button.setStyleSheet(common_btn_style)
        self.practice_button.setMinimumHeight(btn_height)
        self.btn_layout.addWidget(self.practice_button)

        self.stats_button = QPushButton("  QUẢN LÝ && THỐNG KÊ", self.button_container)
        self.stats_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.stats_button.setStyleSheet(common_btn_style)
        self.stats_button.setMinimumHeight(btn_height)
        self.btn_layout.addWidget(self.stats_button)

        self.exit_button = QPushButton("  THOÁT CHƯƠNG TRÌNH", self.button_container)
        self.exit_button.setCursor(QCursor(Qt.PointingHandCursor))
        # Nút Thoát màu đỏ
        self.exit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #c0392b;
                color: white;
                border: {btn_border}px solid #e74c3c;
                border-radius: {btn_radius}px;
                padding: {btn_padding}px;
                font-family: 'Segoe UI';
                font-size: {btn_font}px;
                font-weight: bold;
                text-align: left;
                padding-left: {btn_padding_left}px;
            }}
            QPushButton:hover {{
                background-color: #e74c3c;
            }}
        """)
        self.exit_button.setMinimumHeight(btn_height)
        self.btn_layout.addWidget(self.exit_button)

        # Container căn giữa
        btn_wrapper = QVBoxLayout()
        btn_wrapper.addWidget(self.button_container)
        btn_wrapper.setAlignment(Qt.AlignCenter)
        self.main_layout.addLayout(btn_wrapper)

        # [SPACER DƯỚI] Tỷ lệ 5
        self.main_layout.addStretch(5)

        # 5. FOOTER
        self.label_footer = QLabel(Form)
        self.label_footer.setObjectName("label_footer")
        self.label_footer.setAlignment(Qt.AlignCenter)
        self.label_footer.setStyleSheet(f"""
            color: #7f8c8d; 
            font-family: 'Segoe UI';
            font-size: {scale_font(21)}px; 
            font-style: italic;
            margin-bottom: {scale_size(20)}px;
            background: transparent;
        """)
        self.main_layout.addWidget(self.label_footer)