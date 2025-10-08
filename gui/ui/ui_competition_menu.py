# file: gui/ui/ui_competition_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QSpacerItem, QSizePolicy
)

class Ui_CompetitionMenuWindow(object):
    def setupUi(self, CompetitionMenuWindow):
        CompetitionMenuWindow.setObjectName("CompetitionMenuWindow")
        
        # Tái sử dụng style của màn hình chính
        CompetitionMenuWindow.setStyleSheet("""
            #CompetitionMenuWindow {
                background-color: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1, 
                                                  stop:0 #34495e, 
                                                  stop:1 #2c3e50);
            }
        """)

        self.centralwidget = QWidget(CompetitionMenuWindow)
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
        self.title_label.setText("CHỨC NĂNG THI ĐẤU")
        self.title_label.setStyleSheet("color: #ecf0f1; padding-bottom: 20px;")
        self.verticalLayout.addWidget(self.title_label)
        
        # Spacer
        self.verticalLayout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Các nút chức năng ---
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
        """

        # Start Competition Button
        self.start_button = QPushButton("BẮT ĐẦU THI ĐẤU MỚI", self.centralwidget)
        self.start_button.setMinimumSize(QSize(350, 75))
        self.start_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.start_button, 0, Qt.AlignHCenter)

        # Saved Competitions Button
        self.saved_button = QPushButton("CÁC ĐỢT THI ĐẤU ĐÃ LƯU", self.centralwidget)
        self.saved_button.setMinimumSize(QSize(350, 75))
        self.saved_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.saved_button, 0, Qt.AlignHCenter)

        # Statistics Button
        self.stats_button = QPushButton("THỐNG KÊ KẾT QUẢ", self.centralwidget)
        self.stats_button.setMinimumSize(QSize(350, 75))
        self.stats_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.stats_button, 0, Qt.AlignHCenter)

        # Spacer
        self.verticalLayout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Back Button
        back_button_style = """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """
        self.back_button = QPushButton("VỀ MENU CHÍNH", self.centralwidget)
        self.back_button.setMinimumSize(QSize(350, 70))
        self.back_button.setStyleSheet(back_button_style)
        self.verticalLayout.addWidget(self.back_button, 0, Qt.AlignHCenter)
        
        CompetitionMenuWindow.setCentralWidget(self.centralwidget)