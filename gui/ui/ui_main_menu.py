# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton
)

class Ui_MainMenuWindow(object):
    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        
        MainMenuWindow.setStyleSheet("""
            #MainMenuWindow {
                background-color: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1, 
                                                  stop:0 #34495e, 
                                                  stop:1 #2c3e50);
            }
            QPushButton {
                background-color: #1abc9c;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a085;
            }
            QPushButton:pressed {
                background-color: #148f77;
            }
            QPushButton#exitButton {
                background-color: #e74c3c;
            }
            QPushButton#exitButton:hover {
                background-color: #c0392b;
            }
            QPushButton#exitButton:pressed {
                background-color: #a93226;
            }
        """)

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        # Layout chính
        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(50, 20, 50, 20)
        self.main_layout.setSpacing(15)

        # Vùng chứa tiêu đề
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)

        # Tiêu đề đơn vị khách hàng
        self.customer_title_label = QLabel(title_container)
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        customer_font = QFont()
        customer_font.setPointSize(16)
        self.customer_title_label.setFont(customer_font)
        self.customer_title_label.setStyleSheet("color: #bdc3c7; margin-bottom: 5px;")
        title_layout.addWidget(self.customer_title_label)
        
        # Tiêu đề chính của ứng dụng
        self.title_label = QLabel(title_container)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        self.title_label.setFont(font)
        
        # --- BẮT ĐẦU VÙNG THAY ĐỔI ---
        # Đã xóa thuộc tính 'text-shadow' không được hỗ trợ
        self.title_label.setStyleSheet("color: #ecf0f1;")
        # --- KẾT THÚC VÙNG THAY ĐỔI ---
        
        title_layout.addWidget(self.title_label)

        # Vùng chứa các nút bấm
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(15)
        buttons_layout.setAlignment(Qt.AlignCenter)

        # Các nút
        self.practice_button = QPushButton("LUYỆN TẬP", buttons_container)
        self.practice_button.setMinimumSize(QSize(350, 75))
        buttons_layout.addWidget(self.practice_button)

        self.stats_button = QPushButton("QUẢN LÝ - THỐNG KÊ", buttons_container)
        self.stats_button.setMinimumSize(QSize(350, 75))
        buttons_layout.addWidget(self.stats_button)

        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", buttons_container)
        self.exit_button.setMinimumSize(QSize(350, 75))
        self.exit_button.setObjectName("exitButton")
        buttons_layout.addWidget(self.exit_button)

        # Sắp xếp các vùng chứa vào layout chính
        self.main_layout.addWidget(title_container)
        self.main_layout.addStretch(1)
        self.main_layout.addWidget(buttons_container)
        self.main_layout.addStretch(2)
        
        MainMenuWindow.setCentralWidget(self.centralwidget)