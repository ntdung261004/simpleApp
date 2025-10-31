# file: gui/ui/ui_setup_competition.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QListWidgetItem, QTextEdit,
    QFrame, QSizePolicy, QAbstractItemView, QCheckBox, QLineEdit
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

# 1. Import scaler để sử dụng các hàm tính toán tỷ lệ
from utils.scaler import scaler

class Ui_SetupCompetitionWindow(object):
    def setupUi(self, SetupCompetitionWindow):
        SetupCompetitionWindow.setObjectName("SetupCompetitionWindow")

        self.centralwidget = QWidget(SetupCompetitionWindow)
        self.centralwidget.setObjectName("centralwidget")

        # 2. Sử dụng f-string và scaler để tạo stylesheet động
        SetupCompetitionWindow.setStyleSheet(f"""
            #centralwidget {{ background-color: #2c3e50; }}
            QGroupBox {{
                font-size: {scaler.scale(16)}px;
                font-weight: bold;
                color: #ecf0f1;
                border: 1px solid #4a6278;
                border-radius: {scaler.scale(8)}px;
                margin-top: {scaler.scale(10)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: {scaler.scale(2)}px {scaler.scale(12)}px;
                background-color: #415a72;
                border-radius: {scaler.scale(4)}px;
            }}
            QPushButton {{
                background-color: #1abc9c; color: white;
                font-size: {scaler.scale(14)}px; font-weight: bold;
                border: none; padding: {scaler.scale(10)}px {scaler.scale(20)}px;
                border-radius: {scaler.scale(8)}px;
            }}
            QPushButton:hover {{ background-color: #16a085; }}
            QPushButton#back_button {{ background-color: #e74c3c; }}
            QPushButton#back_button:hover {{ background-color: #c0392b; }}
            QListWidget {{
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: {scaler.scale(8)}px;
                padding: {scaler.scale(5)}px;
            }}
            QListWidget::item {{
                border-bottom: 1px solid #4a6278;
            }}
            QTextEdit, QLineEdit {{
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #4a6278;
                border-radius: {scaler.scale(8)}px;
                padding: {scaler.scale(10)}px;
                font-size: {scaler.scale(14)}px;
            }}
            QLineEdit:focus {{
                border: 1px solid #1abc9c;
            }}
            QCheckBox {{
                color: #ecf0f1;
                font-size: {scaler.scale(14)}px;
            }}
            QLabel {{
                color: #ecf0f1;
                font-size: {scaler.scale(14)}px;
            }}
        """)

        # 3. Sử dụng scaler để tính toán lề và khoảng cách
        margin = scaler.scale(20)
        spacing = scaler.scale(20)
        main_layout = QHBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(margin, margin, margin, margin)
        main_layout.setSpacing(spacing)

        # Cột trái: Danh sách người bắn
        left_layout = QVBoxLayout()
        soldiers_box = QGroupBox("Chọn Người Bắn")
        soldiers_layout = QVBoxLayout(soldiers_box)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(scaler.scale(5), scaler.scale(5), scaler.scale(5), scaler.scale(5))

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

        # Cột phải: Thông tin thi đấu và nút bấm
        right_layout = QVBoxLayout()
        
        competition_info_box = QGroupBox("Thông Tin và Quy Tắc")
        info_layout = QVBoxLayout(competition_info_box)
        info_layout.setSpacing(scaler.scale(10))

        self.competition_name_label = QLabel("Tên buổi kiểm tra:")
        self.competition_name_input = QLineEdit()
        self.competition_name_input.setPlaceholderText("Nhập tên kiểm tra (ví dụ: kiểm tra bắn súng ngắn k54 sĩ quan 2024)")
        
        info_layout.addWidget(self.competition_name_label)
        info_layout.addWidget(self.competition_name_input)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("border: 1px solid #4a6278;")
        info_layout.addWidget(separator)

        self.rules_text = QTextEdit()
        self.rules_text.setReadOnly(True)
        # 4. Scale font cho QTextEdit một cách riêng biệt
        self.rules_text.setFont(scaler.font(13))
        self.rules_text.setText(
            "QUY TẮC KIỂM TRA - BÀI BẮN SÚNG NGẮN K54 (MÔ PHỎNG)\n\n"
            "I.QUY ĐỊNH BÀI BẮN:\n"
            "  • Số lượng đạn: Tổng 12 viên.\n"
            "  • Thứ tự bia:\n"
            "      - Bia 1 & 2 (06 viên): Bắn vào Bia số 4b.\n"
            "      - Bia 3 & 4 (06 viên): Bắn vào Bia số 4c.\n"
            "  • Cự ly: Mô phỏng 25 mét.\n"
            "  • Tư thế bắn: Đứng bắn 1 tay và đứng bắn 2 tay.\n\n"
            "II. YÊU CẦU VỀ KỸ THUẬT & TÍNH ĐIỂM HỢP LỆ:\n"
            "  1. TUÂN THỦ ĐÚNG THỨ TỰ BIA (QUAN TRỌNG): Để kết quả được tính là hợp lệ, người kiểm tra BẮT BUỘC phải bắn đúng loại bia cho từng giai đoạn.\n"
            "  2. KIỂM TRA KẾT NỐI PHẦN CỨNG: Đảm bảo rằng tất cả các kết nối phần cứng (camera, cò súng) đều hoạt động bình thường trước khi bắt đầu kiểm tra.\n"
        )
        info_layout.addWidget(self.rules_text)
        
        right_layout.addWidget(competition_info_box, 1)

        buttons_layout = QHBoxLayout()
        self.start_competition_button = QPushButton("BẮT ĐẦU KIỂM TRA")
        self.back_button = QPushButton("Quay Lại")
        self.back_button.setObjectName("back_button")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.back_button)
        buttons_layout.addWidget(self.start_competition_button)
        right_layout.addLayout(buttons_layout)
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)

        SetupCompetitionWindow.setCentralWidget(self.centralwidget)