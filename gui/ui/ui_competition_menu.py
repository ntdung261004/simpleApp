# file: gui/ui/ui_competition_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QSpacerItem, QSizePolicy
)

# 1. Import scaler để sử dụng các hàm tính toán tỷ lệ
from utils.scaler import scaler

class Ui_CompetitionMenuWindow(object):
    def setupUi(self, CompetitionMenuWindow):
        CompetitionMenuWindow.setObjectName("CompetitionMenuWindow")
        
        CompetitionMenuWindow.setStyleSheet("""
            #CompetitionMenuWindow {
                background-color: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1, 
                                                  stop:0 #34495e, 
                                                  stop:1 #2c3e50);
            }
        """)

        self.centralwidget = QWidget(CompetitionMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        # 2. Sử dụng scaler để tính toán lề và khoảng cách
        margin = scaler.scale(50)
        spacing = scaler.scale(15)
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(margin, margin, margin, margin)
        self.verticalLayout.setSpacing(spacing)

        # Title Label
        self.title_label = QLabel(self.centralwidget)
        self.title_label.setAlignment(Qt.AlignCenter)
        # 3. Sử dụng scaler.font() để tạo font động
        self.title_label.setFont(scaler.font(28, bold=True))
        self.title_label.setText("CHỨC NĂNG KIỂM TRA")
        self.title_label.setStyleSheet(f"color: #ecf0f1; padding-bottom: {scaler.scale(20)}px;")
        self.verticalLayout.addWidget(self.title_label)
        
        # Spacer
        self.verticalLayout.addSpacerItem(QSpacerItem(scaler.scale(20), scaler.scale(40), QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Các nút chức năng ---
        # 4. Sử dụng f-string và scaler để tạo stylesheet động cho các nút
        button_padding = scaler.scale(15)
        button_font_size = scaler.scale(20)
        button_radius = scaler.scale(10)
        button_style = f"""
            QPushButton {{
                background-color: #1abc9c;
                color: white;
                border: none;
                border-radius: {button_radius}px;
                padding: {button_padding}px;
                font-size: {button_font_size}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #16a085;
            }}
        """
        
        # 5. Sử dụng scaler để tính toán kích thước tối thiểu
        min_btn_w = scaler.scale(350)
        min_btn_h = scaler.scale(75)

        # Start Competition Button
        self.start_button = QPushButton("BẮT ĐẦU KIỂM TRA MỚI", self.centralwidget)
        self.start_button.setMinimumSize(QSize(min_btn_w, min_btn_h))
        self.start_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.start_button, 0, Qt.AlignHCenter)

        # Saved Competitions Button
        self.saved_button = QPushButton("CÁC ĐỢT KIỂM TRA ĐÃ LƯU", self.centralwidget)
        self.saved_button.setMinimumSize(QSize(min_btn_w, min_btn_h))
        self.saved_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.saved_button, 0, Qt.AlignHCenter)

        # Statistics Button
        self.stats_button = QPushButton("THỐNG KÊ KẾT QUẢ KIỂM TRA", self.centralwidget)
        self.stats_button.setMinimumSize(QSize(min_btn_w, min_btn_h))
        self.stats_button.setStyleSheet(button_style)
        self.verticalLayout.addWidget(self.stats_button, 0, Qt.AlignHCenter)

        # Back Button
        back_button_style = f"""
            QPushButton {{
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: {button_radius}px;
                padding: {button_padding}px;
                font-size: {button_font_size}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
        """
        self.back_button = QPushButton("VỀ MENU CHÍNH", self.centralwidget)
        self.back_button.setMinimumSize(QSize(min_btn_w, scaler.scale(70)))
        self.back_button.setStyleSheet(back_button_style)
        self.verticalLayout.addWidget(self.back_button, 0, Qt.AlignHCenter)
        self.verticalLayout.addStretch(2)
        
        CompetitionMenuWindow.setCentralWidget(self.centralwidget)