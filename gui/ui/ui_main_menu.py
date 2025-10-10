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
        """)

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(50, 50, 50, 50)
        self.verticalLayout.setSpacing(15)

        # --- DÒNG CHỮ THÊM MỚI ---
        self.subtitle_label = QLabel(self.centralwidget)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(18)  # nhỏ hơn tiêu đề
        subtitle_font.setBold(True)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setStyleSheet("color: #bdc3c7;")  # màu xám sáng
        self.subtitle_label.setText("BAN CHỈ HUY QUÂN SỰ PHƯỜNG MÔNG DƯƠNG")
        self.verticalLayout.addWidget(self.subtitle_label)
        # --- HẾT DÒNG CHỮ THÊM MỚI ---

        # Title Label
        self.title_label = QLabel(self.centralwidget)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setText("PHẦN MỀM KIỂM TRA ĐƯỜNG NGẮM\nSÚNG TIỂU LIÊN")
        self.title_label.setStyleSheet("color: #ecf0f1;")
        self.verticalLayout.addWidget(self.title_label)

        # Thêm khoảng trống co giãn ở trên
        self.verticalLayout.addStretch(1)

        # Button style
        button_style = """
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
        """

        # Practice Button
        self.practice_button = QPushButton("TẬP LUYỆN", self.centralwidget)
        self.practice_button.setMinimumSize(QSize(300, 75))
        self.practice_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.practice_button, 0, Qt.AlignHCenter)

        # Statistics Button
        self.stats_button = QPushButton("QUẢN LÝ - THỐNG KÊ", self.centralwidget)
        self.stats_button.setMinimumSize(QSize(300, 75))
        self.stats_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.stats_button, 0, Qt.AlignHCenter)

        # Exit Button
        exit_button_style = """
            QPushButton {
                background-color: rgba(231, 76, 60, 0.85);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(192, 57, 43, 1);
            }
        """
        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", self.centralwidget)
        self.exit_button.setMinimumSize(QSize(300, 75))
        self.exit_button.setStyleSheet(exit_button_style)
        self.verticalLayout.addWidget(self.exit_button, 0, Qt.AlignHCenter)

        # Thêm khoảng trống ở dưới
        self.verticalLayout.addStretch(2)

        MainMenuWindow.setCentralWidget(self.centralwidget)
