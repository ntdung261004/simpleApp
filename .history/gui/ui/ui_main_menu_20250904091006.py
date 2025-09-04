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
        MainMenuWindow.resize(1280, 720)

        # Set background image using stylesheet
        MainMenuWindow.setStyleSheet("""
            #MainMenuWindow {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                                  stop:0 rgba(20, 30, 48, 255), 
                                                  stop:1 rgba(36, 59, 85, 255));
            }
        """)

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(50, 50, 50, 50)

        # Title Label
        self.title_label = QLabel(self.centralwidget)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setText("PHẦN MỀM KIỂM TRA ĐƯỜNG NGẮM\nSÚNG TIỂU LIÊN STV")
        self.title_label.setStyleSheet("color: white;")
        self.verticalLayout.addWidget(self.title_label)

        # Spacer to push buttons down
        spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        # Button common style
        button_style = """
            QPushButton {
                background-color: rgba(0, 78, 151, 0.8);
                color: white;
                border: 2px solid #00BFFF;
                border-radius: 10px;
                padding: 15px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 100, 190, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(0, 50, 120, 0.9);
            }
        """

        # Practice Button
        self.practice_button = QPushButton("TẬP LUYỆN", self.centralwidget)
        self.practice_button.setMinimumSize(QSize(300, 80))
        self.practice_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.practice_button, 0, Qt.AlignHCenter)

        # Statistics Button
        self.stats_button = QPushButton("THỐNG KÊ", self.centralwidget)
        self.stats_button.setMinimumSize(QSize(300, 80))
        self.stats_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.stats_button, 0, Qt.AlignHCenter)

        # List Button
        self.list_button = QPushButton("DANH SÁCH", self.centralwidget)
        self.list_button.setMinimumSize(QSize(300, 80))
        self.list_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.list_button, 0, Qt.AlignHCenter)

        # Guide Button
        self.guide_button = QPushButton("HƯỚNG DẪN", self.centralwidget)
        self.guide_button.setMinimumSize(QSize(300, 80))
        self.guide_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.guide_button, 0, Qt.AlignHCenter)

                # --- THÊM NÚT THOÁT VÀO ĐÂY ---
        # Spacer nhỏ giữa các nút chức năng và nút thoát
        spacerItem_exit = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem_exit)

        # Exit Button
        exit_button_style = """
            QPushButton {
                background-color: rgba(178, 34, 34, 0.8); /* Màu đỏ đậm */
                color: white;
                border: 2px solid #FF6347;
                border-radius: 10px;
                padding: 15px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(205, 92, 92, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(139, 0, 0, 0.9);
            }
        """
        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", self.centralwidget)
        self.exit_button.setMinimumSize(QSize(300, 80))
        self.exit_button.setStyleSheet(exit_button_style)
        self.verticalLayout.addWidget(self.exit_button, 0, Qt.AlignHCenter)
        # ---------------------------------

        # Spacer at the bottom
        spacerItem2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem2)

        self.verticalLayout.setStretch(0, 2) # Title takes more space
        self.verticalLayout.setStretch(1, 1) # Spacer
        self.verticalLayout.setStretch(6, 1) # Bottom spacer

        MainMenuWindow.setCentralWidget(self.centralwidget)