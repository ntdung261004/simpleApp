# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QApplication
)

class Ui_MainMenuWindow(object):
    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        
        # --- [MỚI] TÍNH TOÁN TỶ LỆ MÀN HÌNH ---
        screen = QApplication.primaryScreen().availableGeometry()
        self.scale_factor = screen.height() / 1080.0
        
        def scale_size(size): return max(1, int(size * self.scale_factor))
        def scale_font(size): return max(10, int(size * self.scale_factor))
        # --------------------------------------

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

        # Layout chính
        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(scale_size(50), scale_size(20), scale_size(50), scale_size(20))
        self.main_layout.setSpacing(scale_size(15))

        # Vùng chứa tiêu đề
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(scale_size(5))

        # Tiêu đề đơn vị khách hàng
        self.customer_title_label = QLabel(title_container)
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        customer_font = QFont()
        customer_font.setPointSize(scale_font(16))
        self.customer_title_label.setFont(customer_font)
        self.customer_title_label.setStyleSheet("color: #bdc3c7; margin-bottom: 5px;")
        title_layout.addWidget(self.customer_title_label)
        
        # Tiêu đề chính của ứng dụng
        self.title_label = QLabel(title_container)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(scale_font(28))
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #ecf0f1;")
        
        title_layout.addWidget(self.title_label)

        # Vùng chứa các nút bấm
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(scale_size(15))
        buttons_layout.setAlignment(Qt.AlignCenter)

        # Các nút (Đã áp dụng scale_size)
        self.practice_button = QPushButton("LUYỆN TẬP", buttons_container)
        self.practice_button.setMinimumSize(QSize(scale_size(350), scale_size(75)))
        buttons_layout.addWidget(self.practice_button)

        self.stats_button = QPushButton("QUẢN LÝ - THỐNG KÊ", buttons_container)
        self.stats_button.setMinimumSize(QSize(scale_size(350), scale_size(75)))
        buttons_layout.addWidget(self.stats_button)

        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", buttons_container)
        self.exit_button.setMinimumSize(QSize(scale_size(350), scale_size(75)))
        self.exit_button.setObjectName("exitButton")
        buttons_layout.addWidget(self.exit_button)

        # Sắp xếp các vùng chứa vào layout chính
        self.main_layout.addWidget(title_container)
        self.main_layout.addStretch(1)
        self.main_layout.addWidget(buttons_container)
        self.main_layout.addStretch(2)
        
        MainMenuWindow.setCentralWidget(self.centralwidget)