# file: gui/ui/ui_setup_competition.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QListWidgetItem, QTextEdit,
    QFrame, QSizePolicy, QAbstractItemView, QCheckBox
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class Ui_SetupCompetitionWindow(object):
    def setupUi(self, SetupCompetitionWindow):
        SetupCompetitionWindow.setObjectName("SetupCompetitionWindow")

        # === BẮT ĐẦU VÙNG SỬA LỖI ===
        # 1. Tạo một widget trung tâm để chứa toàn bộ layout và các thành phần khác.
        # Đây là bước quan trọng bị thiếu, gây ra lỗi màn hình trắng.
        self.centralwidget = QWidget(SetupCompetitionWindow)
        self.centralwidget.setObjectName("centralwidget")
        # === KẾT THÚC VÙNG SỬA LỖI ===

        # Style chung (Giữ nguyên)
        SetupCompetitionWindow.setStyleSheet("""
            #centralwidget { background-color: #2c3e50; }
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
            QPushButton#back_button { background-color: #e74c3c; }
            QPushButton#back_button:hover { background-color: #c0392b; }
            QListWidget {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 8px;
                padding: 5px;
            }
            QTextEdit {
                background-color: #34495e;
                color: #bdc3c7;
                border: 1px solid #4a6278;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QCheckBox {
                color: #ecf0f1;
                font-size: 14px;
            }
            QLabel {
                color: #ecf0f1;
                font-size: 14px;
            }
        """)

        # === BẮT ĐẦU VÙNG SỬA LỖI ===
        # 2. Áp dụng layout chính vào `centralwidget` thay vì `SetupCompetitionWindow`
        main_layout = QHBoxLayout(self.centralwidget)
        # === KẾT THÚC VÙNG SỬA LỖI ===
        
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Cột trái: Danh sách người bắn (Giữ nguyên)
        left_layout = QVBoxLayout()
        soldiers_box = QGroupBox("Chọn Người Bắn")
        soldiers_layout = QVBoxLayout(soldiers_box)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(5, 5, 5, 5)

        self.select_all_checkbox = QCheckBox("Chọn tất cả")
        self.selected_count_label = QLabel("Đã chọn: 0")
        self.selected_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        controls_layout.addWidget(self.select_all_checkbox)
        controls_layout.addStretch()
        controls_layout.addWidget(self.selected_count_label)
        
        soldiers_layout.addLayout(controls_layout)

        self.soldier_list = QListWidget()
        self.soldier_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.soldier_list.setFocusPolicy(Qt.NoFocus)
        self.soldier_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.soldier_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        soldiers_layout.addWidget(self.soldier_list)
        left_layout.addWidget(soldiers_box)

        # Cột phải: Quy tắc và nút bấm (Giữ nguyên)
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

        buttons_layout = QHBoxLayout()
        self.start_competition_button = QPushButton("BẮT ĐẦU THI ĐẤU")
        self.back_button = QPushButton("Quay Lại")
        self.back_button.setObjectName("back_button")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.back_button)
        buttons_layout.addWidget(self.start_competition_button)
        right_layout.addLayout(buttons_layout)
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)

        # === BẮT ĐẦU VÙNG SỬA LỖI ===
        # 3. Đặt `centralwidget` làm widget trung tâm cho cửa sổ chính
        SetupCompetitionWindow.setCentralWidget(self.centralwidget)
        # === KẾT THÚC VÙNG SỬA LỖI ===