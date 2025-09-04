# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QSpacerItem, QSizePolicy
)

class Ui_MainMenuWindow(object):
    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        
        # --- THAY ĐỔI 1: Cập nhật màu nền để đồng bộ ---
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
        self.verticalLayout.setSpacing(15) # Thêm khoảng cách đều giữa các widget

        # Title Label
        self.title_label = QLabel(self.centralwidget)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setText("PHẦN MỀM KIỂM TRA ĐƯỜNG NGẮM\nSÚNG TIỂU LIÊN STV")
        self.title_label.setStyleSheet("color: #ecf0f1;") # Dùng màu trắng ngà cho dịu mắt
        self.verticalLayout.addWidget(self.title_label)

        # --- THAY ĐỔI 2: Giảm khoảng cách giữa tiêu đề và nút ---
        # Spacer cố định thay vì co giãn
        spacerItem = QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)

        # --- THAY ĐỔI 3: Cập nhật màu nút để đồng bộ ---
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
        self.stats_button = QPushButton("THỐNG KÊ", self.centralwidget)
        self.stats_button.setMinimumSize(QSize(300, 75))
        self.stats_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.stats_button, 0, Qt.AlignHCenter)

        # List Button
        self.list_button = QPushButton("DANH SÁCH", self.centralwidget)
        self.list_button.setMinimumSize(QSize(300, 75))
        self.list_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.list_button, 0, Qt.AlignHCenter)

        # Guide Button
        self.guide_button = QPushButton("HƯỚNG DẪN", self.centralwidget)
        self.guide_button.setMinimumSize(QSize(300, 75))
        self.guide_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.guide_button, 0, Qt.AlignHCenter)


        # Exit Button (Giữ màu đỏ để phân biệt)
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
        self.exit_button = QPushButton("THOÁT", self.centralwidget)
        self.exit_button.setMinimumSize(QSize(300, 75))
        self.exit_button.setStyleSheet(exit_button_style)
        self.verticalLayout.addWidget(self.exit_button, 0, Qt.AlignHCenter)

        MainMenuWindow.setCentralWidget(self.centralwidget)