# file: gui/ui/ui_setup_competition.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QListWidgetItem, QTextEdit,
    QFrame, QSizePolicy, QAbstractItemView, QCheckBox, QLineEdit
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class Ui_SetupCompetitionWindow(object):
    def setupUi(self, SetupCompetitionWindow):
        SetupCompetitionWindow.setObjectName("SetupCompetitionWindow")

        self.centralwidget = QWidget(SetupCompetitionWindow)
        self.centralwidget.setObjectName("centralwidget")

        # Style chung
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
            QListWidget::item {
                border-bottom: 1px solid #4a6278;
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
            /* === BẮT ĐẦU VÙNG THÊM MỚI === */
            QLineEdit {
                background-color: #34495e;
                border: 1px solid #4a6278;
                border-radius: 6px;
                padding: 8px;
                color: #ecf0f1;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #1abc9c;
            }
            /* === KẾT THÚC VÙNG THÊM MỚI === */
        """)

        main_layout = QHBoxLayout(self.centralwidget)
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

        # Cột phải: Thông tin thi đấu và nút bấm
        right_layout = QVBoxLayout()
        
        # === BẮT ĐẦU VÙNG THAY ĐỔI LAYOUT ===
        competition_info_box = QGroupBox("Thông Tin và Quy Tắc")
        info_layout = QVBoxLayout(competition_info_box)
        info_layout.setSpacing(10) # Thêm khoảng cách giữa các phần tử

        # Thêm label và LineEdit cho tên cuộc thi
        self.competition_name_label = QLabel("Tên cuộc thi:")
        self.competition_name_input = QLineEdit()
        self.competition_name_input.setPlaceholderText("Nhập tên cuộc thi (ví dụ: Hội thao 2024)")
        
        info_layout.addWidget(self.competition_name_label)
        info_layout.addWidget(self.competition_name_input)
        
        # Thêm đường kẻ ngang để phân tách
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("border: 1px solid #4a6278;")
        info_layout.addWidget(separator)

        # Thêm phần quy tắc
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
        info_layout.addWidget(self.rules_text)
        
        right_layout.addWidget(competition_info_box, 1)
        # === KẾT THÚC VÙNG THAY ĐỔI LAYOUT ===

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

        SetupCompetitionWindow.setCentralWidget(self.centralwidget)