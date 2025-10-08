# file: gui/ui/ui_setup_competition.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QListWidgetItem, QTextEdit,
    QFrame, QSizePolicy, QAbstractItemView
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class Ui_SetupCompetitionWindow(object):
    def setupUi(self, SetupCompetitionWindow):
        SetupCompetitionWindow.setObjectName("SetupCompetitionWindow")
        
        # Style chung
        SetupCompetitionWindow.setStyleSheet("""
            #SetupCompetitionWindow { background-color: #2c3e50; }
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #ecf0f1;
                border: 1px solid #4a6278;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 2px 12px;
                background-color: #415a72;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #1abc9c; color: white;
                font-size: 14px; font-weight: bold;
                border: none; padding: 10px 20px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #16a085; }
            QPushButton#danger { background-color: #e74c3c; }
            QPushButton#danger:hover { background-color: #c0392b; }
            QListWidget {
                background-color: #34495e; border-radius: 6px;
                color: #ecf0f1; font-size: 14px;
            }
            QTextEdit {
                background-color: #34495e; border-radius: 6px;
                color: #bdc3c7; font-size: 14px;
                border: 1px solid #4a6278;
            }
        """)

        self.centralwidget = QWidget(SetupCompetitionWindow)
        root_layout = QVBoxLayout(self.centralwidget)
        root_layout.setContentsMargins(20, 20, 20, 20)
        
        # Tiêu đề
        title_label = QLabel("Thiết Lập Thi Đấu Mới", self.centralwidget)
        title_font = QFont('Segoe UI', 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #ecf0f1; padding-bottom: 20px;")
        root_layout.addWidget(title_label)
        
        columns_layout = QHBoxLayout()
        root_layout.addLayout(columns_layout, 1)

        # Cột trái: Chọn người bắn
        left_box = QGroupBox("Chọn Người Bắn")
        left_layout = QVBoxLayout(left_box)
        
        self.soldier_list = QListWidget()
        self.soldier_list.setSelectionMode(QAbstractItemView.MultiSelection) # Cho phép chọn nhiều
        left_layout.addWidget(self.soldier_list)
        columns_layout.addWidget(left_box, 1)

        # Cột phải: Quy tắc và nút bấm
        right_layout = QVBoxLayout()
        
        rules_box = QGroupBox("Quy Tắc Thi Đấu")
        rules_layout = QVBoxLayout(rules_box)
        self.rules_text = QTextEdit()
        self.rules_text.setReadOnly(True)
        self.rules_text.setText(
            "QUY TẮC BẮN SÚNG NGẮN K54 - BÀI 1\n\n"
            "1. Cự ly bắn: 25 mét.\n"
            "2. Mục tiêu: Bia 4b (thân người) và 4c (vòng tròn).\n"
            "3. Tư thế bắn: Đứng bắn có tỳ tay hoặc không tỳ tay.\n"
            "4. Thời gian: Theo quy định của trọng tài.\n"
            "5. Số lượng đạn: 10 viên.\n\n"
            "YÊU CẦU AN TOÀN:\n"
            "- Luôn tuân thủ mệnh lệnh của người chỉ huy.\n"
            "- Giữ súng hướng về phía mục tiêu.\n"
            "- Ngón tay chỉ đặt vào cò khi đã sẵn sàng bắn."
        )
        rules_layout.addWidget(self.rules_text)
        right_layout.addWidget(rules_box, 1)

        # Các nút bấm
        buttons_layout = QHBoxLayout()
        self.start_competition_button = QPushButton("BẮT ĐẦU THI ĐẤU")
        self.back_button = QPushButton("Quay Lại")
        self.back_button.setObjectName("danger")
        
        buttons_layout.addWidget(self.back_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.start_competition_button)
        
        right_layout.addLayout(buttons_layout)
        columns_layout.addLayout(right_layout, 1)

        SetupCompetitionWindow.setCentralWidget(self.centralwidget)