# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton
)

from utils.scaler import scaler

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

        margin = scaler.scale(50)
        spacing = scaler.scale(15)
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(margin, margin, margin, margin)
        self.verticalLayout.setSpacing(spacing)

        # --- TITLE LABEL ---
        self.title_label = QLabel(self.centralwidget)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # [QUAN TRỌNG] Tính toán size chữ bằng Scaler
        title_size = scaler.scale(26)
        
        # [FIX LỖI] Đưa font-size vào styleSheet để đè Global Style (14px)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: #ecf0f1;
                font-size: {title_size}px;
                font-weight: bold;
                font-family: "Segoe UI", Arial, sans-serif;
            }}
        """)
        
        self.title_label.setText("PHẦN MỀM TẬP LUYỆN VÀ KIỂM TRA\nĐƯỜNG NGẮM SÚNG NGẮN K54")
        self.verticalLayout.addWidget(self.title_label)
        
        self.verticalLayout.addStretch(1)

        # --- BUTTONS ---
        button_padding = scaler.scale(15)
        button_font_size = scaler.scale(17) # Giữ nguyên size to
        
        # Style cho nút (Đã có font-size bên trong nên sẽ không bị ảnh hưởng, nhưng tôi gia cố thêm)
        button_style = f"""
            QPushButton {{
                background-color: #1abc9c;
                color: white;
                border: none;
                border-radius: {scaler.scale(10)}px;
                padding: {button_padding}px;
                font-size: {button_font_size}px;
                font-weight: bold;
                font-family: "Segoe UI", Arial, sans-serif;
            }}
            QPushButton:hover {{
                background-color: #16a085;
            }}
            QPushButton:pressed {{
                background-color: #148f77;
            }}
        """

        min_btn_w = scaler.scale(300)
        min_btn_h = scaler.scale(70)

        self.competition_button = QPushButton("KIỂM TRA", self.centralwidget)
        self.competition_button.setMinimumSize(QSize(min_btn_w, min_btn_h))
        self.competition_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.competition_button, 0, Qt.AlignHCenter)
        
        self.practice_button = QPushButton("TẬP LUYỆN", self.centralwidget)
        self.practice_button.setMinimumSize(QSize(min_btn_w, min_btn_h))
        self.practice_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.practice_button, 0, Qt.AlignHCenter)

        self.stats_button = QPushButton("QUẢN LÝ - THỐNG KÊ", self.centralwidget)
        self.stats_button.setMinimumSize(QSize(min_btn_w, min_btn_h))
        self.stats_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.stats_button, 0, Qt.AlignHCenter)

        # --- EXIT BUTTON ---
        exit_button_style = f"""
            QPushButton {{
                background-color: rgba(231, 76, 60, 0.85);
                color: white;
                border: none;
                border-radius: {scaler.scale(10)}px;
                padding: {button_padding}px;
                font-size: {button_font_size}px;
                font-weight: bold;
                font-family: "Segoe UI", Arial, sans-serif;
            }}
            QPushButton:hover {{
                background-color: rgba(192, 57, 43, 1);
            }}
        """
        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", self.centralwidget)
        self.exit_button.setMinimumSize(QSize(min_btn_w, min_btn_h))
        self.exit_button.setStyleSheet(exit_button_style)
        self.verticalLayout.addWidget(self.exit_button, 0, Qt.AlignHCenter)

        self.verticalLayout.addStretch(2)

        MainMenuWindow.setCentralWidget(self.centralwidget)