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

        # Title Label
        self.title_label = QLabel(self.centralwidget)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setText("PHẦN MỀM KIỂM TRA ĐƯỜNG NGẮM\nSÚNG TIỂU LIÊN STV")
        self.title_label.setStyleSheet("color: #ecf0f1;")
        self.verticalLayout.addWidget(self.title_label)

        # Spacer cố định
        spacerItem = QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)

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

        # --- XÓA DÒNG SPACER Ở ĐÂY ---
        # spacerItem_bottom = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        # self.verticalLayout.addItem(spacerItem_bottom)
        # --------------------------------

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

        # Thêm spacer co giãn ở cuối để đẩy tất cả các nút lên trên
        final_spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout.addItem(final_spacer)

        MainMenuWindow.setCentralWidget(self.centralwidget)