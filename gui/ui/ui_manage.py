# file: gui/ui/ui_manage.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTableWidget, QFrame, QStackedWidget, QApplication, QLineEdit,
    QHeaderView, QAbstractItemView
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect

class ManageGui(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setObjectName("ManageWidget")

        # Tính toán tỷ lệ màn hình
        screen = QApplication.primaryScreen().availableGeometry()
        self.scale_factor = screen.height() / 1080.0

        self.setStyleSheet(f"""
            #ManageWidget {{
                background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI';
            }}
            /* Style cho các nút Menu chính (Bao gồm cả nút Về màn hình chính) */
            QPushButton.menu-btn {{
                background-color: #34495e; color: #ecf0f1;
                font-size: {int(18 * self.scale_factor)}px; font-weight: bold;
                border: 2px solid #4a6278; border-radius: 15px;
                padding: {int(20 * self.scale_factor)}px;
                text-align: left; padding-left: 30px;
            }}
            QPushButton.menu-btn:hover {{
                background-color: #1abc9c; border-color: #16a085; color: white;
            }}
            /* Riêng nút thoát có thể có hiệu ứng hover màu đỏ nhẹ nếu muốn, hoặc giữ nguyên xanh */
            QPushButton.menu-btn#exitBtn:hover {{
                background-color: #c0392b; border-color: #e74c3c;
            }}
            
            /* Style chung cho nút thường (ở các trang con) */
            QPushButton {{
                background-color: #1abc9c; color: white; font-size: {int(14 * self.scale_factor)}px; font-weight: bold;
                border: none; padding: {int(10 * self.scale_factor)}px {int(20 * self.scale_factor)}px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: #16a085; }}
            
            QPushButton#importBtn {{ background-color: #3498db; }}
            QPushButton#importBtn:hover {{ background-color: #2980b9; }}

            QPushButton#danger {{ background-color: #e74c3c; }}
            QPushButton#danger:hover {{ background-color: #c0392b; }}
            
            /* Style cho Table */
            QTableWidget {{
                background-color: #34495e; border: 1px solid #4a6278;
                border-radius: 8px; gridline-color: #4a6278; color: #ecf0f1;
                font-size: {int(14 * self.scale_factor)}px;
            }}
            QTableWidget::item {{ padding: 5px; }}
            QTableWidget::item:selected {{
                background-color: #1abc9c; color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: #2c3e50; color: #bdc3c7;
                padding: 8px; border: none; border-bottom: 2px solid #1abc9c;
                font-weight: bold; font-size: {int(14 * self.scale_factor)}px;
            }}
            
            /* Thanh tìm kiếm */
            QLineEdit#searchBox {{
                background-color: #34495e; border: 1px solid #4a6278;
                border-radius: 20px; padding: 8px 15px;
                color: #ecf0f1; font-size: {int(14 * self.scale_factor)}px;
            }}
            QLineEdit#searchBox:focus {{ border: 1px solid #1abc9c; }}
        """)

        self.setupUi()

    def setupUi(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_stack = QStackedWidget()
        main_layout.addWidget(self.main_stack)

        # --- TRANG 0: MENU QUẢN LÝ ---
        self.page_menu = QWidget()
        self._setup_menu_page()
        self.main_stack.addWidget(self.page_menu)

        # --- TRANG 1: DANH SÁCH NGƯỜI TẬP ---
        self.page_trainees = QWidget()
        self._setup_trainee_list_page()
        self.main_stack.addWidget(self.page_trainees)

    def _setup_menu_page(self):
        layout = QVBoxLayout(self.page_menu)
        
        # 1. Đẩy tiêu đề lên cao hơn bằng cách thêm spacing ở trên ít hơn ở dưới
        layout.addSpacing(int(60 * self.scale_factor)) 

        # Tiêu đề
        lbl_title = QLabel("QUẢN LÝ & THỐNG KÊ")
        lbl_title.setStyleSheet(f"font-size: {int(32 * self.scale_factor)}px; font-weight: bold; color: #ecf0f1;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        layout.addSpacing(int(40 * self.scale_factor))

        # Container cho các nút menu
        btn_container = QFrame()
        btn_container.setFixedWidth(int(550 * self.scale_factor)) # Tăng chiều rộng một chút cho đẹp
        
        # Canh giữa container
        layout.addWidget(btn_container, 0, Qt.AlignCenter)
        
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setSpacing(int(20 * self.scale_factor))

        # Nút 1
        self.btn_menu_trainees = QPushButton("1. DANH SÁCH NGƯỜI TẬP")
        self.btn_menu_trainees.setProperty("class", "menu-btn")
        self.btn_menu_trainees.setCursor(Qt.PointingHandCursor)
        
        # Nút 2
        self.btn_menu_sessions = QPushButton("2. QUẢN LÝ PHIÊN TẬP")
        self.btn_menu_sessions.setProperty("class", "menu-btn")
        self.btn_menu_sessions.setCursor(Qt.PointingHandCursor)
        
        # Nút 3
        self.btn_menu_tests = QPushButton("3. QUẢN LÝ KIỂM TRA")
        self.btn_menu_tests.setProperty("class", "menu-btn")
        self.btn_menu_tests.setCursor(Qt.PointingHandCursor)

        # Nút 4: Về màn hình chính (Được thiết kế giống hệt các nút trên)
        self.btn_back_main = QPushButton("◀  VỀ MÀN HÌNH CHÍNH")
        self.btn_back_main.setObjectName("exitBtn") # Đặt ID để có thể style riêng (ví dụ hover đỏ)
        self.btn_back_main.setProperty("class", "menu-btn")
        self.btn_back_main.setCursor(Qt.PointingHandCursor)

        btn_layout.addWidget(self.btn_menu_trainees)
        btn_layout.addWidget(self.btn_menu_sessions)
        btn_layout.addWidget(self.btn_menu_tests)
        
        # Thêm một chút khoảng cách trước nút thoát cho thoáng
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.btn_back_main)
        
        # Đẩy toàn bộ nội dung lên phía trên (Khoảng trống phía dưới sẽ chiếm hết phần còn lại)
        layout.addStretch()

    def _setup_trainee_list_page(self):
        layout = QVBoxLayout(self.page_trainees)
        margin = int(30 * self.scale_factor)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(int(15 * self.scale_factor))

        # Header
        header_layout = QHBoxLayout()
        lbl_title = QLabel("DANH SÁCH NGƯỜI TẬP")
        lbl_title.setStyleSheet(f"font-size: {int(20 * self.scale_factor)}px; font-weight: bold; color: #1abc9c;")
        
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("🔍 Tìm kiếm theo tên hoặc đơn vị...")
        self.search_box.setFixedWidth(int(350 * self.scale_factor))
        
        self.total_count_label = QLabel("Tổng số: 0")
        self.total_count_label.setStyleSheet("font-style: italic; color: #bdc3c7; font-size: 14px;")

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.search_box)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.total_count_label)
        layout.addLayout(header_layout)

        # Table
        self.soldier_table = QTableWidget(0, 3)
        self.soldier_table.setHorizontalHeaderLabels(["ID", "Họ và Tên", "Đơn vị"])
        self.soldier_table.verticalHeader().setVisible(False)
        self.soldier_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.soldier_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.soldier_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.soldier_table.setAlternatingRowColors(True)
        self.soldier_table.setStyleSheet("alternate-background-color: #3b5266;")
        
        header = self.soldier_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        layout.addWidget(self.soldier_table)

        # Footer
        footer_layout = QHBoxLayout()
        
        self.btn_add_trainee = QPushButton("Thêm Mới")
        self.btn_add_trainee.setCursor(Qt.PointingHandCursor)
        self.btn_add_trainee.setMinimumWidth(130)
        self.btn_add_trainee.setMinimumHeight(40)
        
        self.btn_import_excel = QPushButton("Nhập Excel")
        self.btn_import_excel.setObjectName("importBtn")
        self.btn_import_excel.setCursor(Qt.PointingHandCursor)
        self.btn_import_excel.setMinimumWidth(130)
        self.btn_import_excel.setMinimumHeight(40)
        
        self.btn_back_to_menu = QPushButton("Quay Lại Menu")
        self.btn_back_to_menu.setObjectName("danger")
        self.btn_back_to_menu.setCursor(Qt.PointingHandCursor)
        self.btn_back_to_menu.setMinimumWidth(130)
        self.btn_back_to_menu.setMinimumHeight(40)

        footer_layout.addWidget(self.btn_add_trainee)
        footer_layout.addWidget(self.btn_import_excel)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_back_to_menu)
        
        layout.addLayout(footer_layout)