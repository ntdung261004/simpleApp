# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication, QSizePolicy
)

class Ui_MainMenuWindow(object):
    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        
        # --- LOGIC SCALING ---
        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        scale_factor = screen_height / 1080.0

        def scale_size(base_size):
            return max(1, int(base_size * scale_factor))

        def scale_font(base_size):
            return max(8, int(base_size * scale_factor))
        # ---------------------

        # Stylesheet
        MainMenuWindow.setStyleSheet(f"""
            #MainMenuWindow {{
                background-color: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1, 
                                                  stop:0 #34495e, 
                                                  stop:1 #2c3e50);
            }}
            QPushButton {{
                background-color: #1abc9c;
                color: white;
                border: none;
                border-radius: {scale_size(10)}px;
                padding: {scale_size(15)}px;
                font-size: {scale_font(20)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #16a085;
            }}
            QPushButton:pressed {{
                background-color: #148f77;
            }}
            QPushButton#exitButton {{
                background-color: #e74c3c;
            }}
            QPushButton#exitButton:hover {{
                background-color: #c0392b;
            }}
            QPushButton#exitButton:pressed {{
                background-color: #a93226;
            }}
        """)

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(scale_size(40), scale_size(20), scale_size(40), scale_size(10))
        self.main_layout.setSpacing(scale_size(15))

        # =================================================================
        # VÙNG HEADER (LOGO - TIÊU ĐỀ - LOGO)
        # =================================================================
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(scale_size(20)) # Khoảng cách giữa logo và tiêu đề

        # 1. Logo Trái
        self.logo_left = QLabel(header_widget)
        logo_size = scale_size(240) # Kích thước logo (vuông) đã scale
        self.logo_left.setFixedSize(logo_size, logo_size)
        self.logo_left.setContentsMargins(scale_size(30), scale_size(30), scale_size(30), scale_size(30)    )
        self.logo_left.setScaledContents(True) # Cho phép ảnh tự co giãn vừa khung
        # self.logo_left.setStyleSheet("border: 1px solid red;") # Bật dòng này nếu muốn debug vị trí
        header_layout.addWidget(self.logo_left)

        # 2. Cụm Tiêu Đề (Nằm giữa)
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(scale_size(5))

        self.customer_title_label = QLabel(title_container)
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        customer_font = QFont()
        customer_font.setPixelSize(scale_font(24))
        self.customer_title_label.setFont(customer_font)
        self.customer_title_label.setStyleSheet(f"color: #bdc3c7; margin-bottom: {scale_size(5)}px;")
        title_layout.addWidget(self.customer_title_label)
        
        self.title_label = QLabel(title_container)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPixelSize(scale_font(32))
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #ecf0f1;")
        title_layout.addWidget(self.title_label)
        
        # Thêm cụm tiêu đề vào giữa Header với stretch=1 để nó chiếm hết khoảng trống còn lại
        header_layout.addWidget(title_container, 1)

        # 3. Logo Phải
        self.logo_right = QLabel(header_widget)
        self.logo_right.setFixedSize(logo_size, logo_size)
        self.logo_right.setScaledContents(True)
        self.logo_right.setContentsMargins(scale_size(30), scale_size(30), scale_size(30), scale_size(30)   )
        header_layout.addWidget(self.logo_right)

        # Thêm Header Widget vào Main Layout
        self.main_layout.addWidget(header_widget)
        # =================================================================

        self.main_layout.addStretch(1)

        # Vùng Nút Bấm
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(scale_size(15))
        buttons_layout.setAlignment(Qt.AlignCenter)

        btn_size = QSize(scale_size(350), scale_size(75))

        self.practice_button = QPushButton("LUYỆN TẬP", buttons_container)
        self.practice_button.setMinimumSize(btn_size)
        buttons_layout.addWidget(self.practice_button)

        self.stats_button = QPushButton("QUẢN LÝ - THỐNG KÊ", buttons_container)
        self.stats_button.setMinimumSize(btn_size)
        buttons_layout.addWidget(self.stats_button)

        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", buttons_container)
        self.exit_button.setMinimumSize(btn_size)
        self.exit_button.setObjectName("exitButton")
        buttons_layout.addWidget(self.exit_button)

        self.main_layout.addWidget(buttons_container)
        self.main_layout.addStretch(2)

        # Footer Label
        self.footer_label = QLabel(self.centralwidget)
        self.footer_label.setAlignment(Qt.AlignCenter)
        footer_font = QFont()
        footer_font.setPixelSize(scale_font(18))
        footer_font.setItalic(True)
        self.footer_label.setContentsMargins(scale_size(5), scale_size(5), scale_size(5), scale_size(5))
        self.footer_label.setFont(footer_font)
        self.footer_label.setStyleSheet(f"color: #95a5a6; padding-bottom: {scale_size(5)}px;")
        
        self.main_layout.addWidget(self.footer_label)
        
        MainMenuWindow.setCentralWidget(self.centralwidget)