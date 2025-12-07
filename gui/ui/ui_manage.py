# file: gui/ui/ui_manage.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTableWidget, QFrame, QStackedWidget, QApplication, QLineEdit,
    QHeaderView, QAbstractItemView, QComboBox, QScrollArea, QGridLayout
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
            /* Style cho các nút Menu chính */
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
            QPushButton.menu-btn#exitBtn:hover {{
                background-color: #c0392b; border-color: #e74c3c;
            }}
            
            /* Style chung cho nút thường */
            QPushButton {{
                background-color: #1abc9c; color: white; font-size: {int(14 * self.scale_factor)}px; font-weight: bold;
                border: none; padding: {int(10 * self.scale_factor)}px {int(20 * self.scale_factor)}px;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: #16a085; }}
            QPushButton:disabled {{ background-color: #95a5a6; color: #bdc3c7; }}
            
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

            /* Combo box */
            QComboBox {{
                background-color: #34495e; color: white; border: 1px solid #4a6278;
                padding: 5px; border-radius: 5px; min-width: 150px; font-weight: bold;
            }}
            QComboBox::drop-down {{ border: none; }}
            
            /* Card trong báo cáo */
            QFrame.report-card {{
                background-color: #34495e; border-radius: 10px; border: 1px solid #4a6278;
            }}
            QLabel.card-title {{
                color: #bdc3c7; font-size: 14px; font-weight: bold;
            }}
            QLabel.card-value {{
                color: #ecf0f1; font-size: 20px; font-weight: bold;
            }}
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
        
        # --- TRANG 2: BÁO CÁO PHIÊN TẬP (LIST) ---
        self.page_sessions = QWidget()
        self._setup_session_list_page()
        self.main_stack.addWidget(self.page_sessions)

        # --- TRANG 3: CHI TIẾT PHIÊN TẬP (DETAIL & REPORT) ---
        self.page_session_detail = QWidget()
        self._setup_session_detail_page()
        self.main_stack.addWidget(self.page_session_detail)

    def _setup_menu_page(self):
        layout = QVBoxLayout(self.page_menu)
        layout.addSpacing(int(60 * self.scale_factor)) 

        lbl_title = QLabel("QUẢN LÝ & THỐNG KÊ")
        lbl_title.setStyleSheet(f"font-size: {int(32 * self.scale_factor)}px; font-weight: bold; color: #ecf0f1;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        layout.addSpacing(int(40 * self.scale_factor))

        btn_container = QFrame()
        btn_container.setFixedWidth(int(550 * self.scale_factor))
        layout.addWidget(btn_container, 0, Qt.AlignCenter)
        
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setSpacing(int(20 * self.scale_factor))

        self.btn_menu_trainees = QPushButton("1. DANH SÁCH NGƯỜI TẬP")
        self.btn_menu_trainees.setProperty("class", "menu-btn")
        self.btn_menu_trainees.setCursor(Qt.PointingHandCursor)
        
        self.btn_menu_sessions = QPushButton("2. BÁO CÁO PHIÊN TẬP")
        self.btn_menu_sessions.setProperty("class", "menu-btn")
        self.btn_menu_sessions.setCursor(Qt.PointingHandCursor)

        self.btn_back_main = QPushButton("◀  VỀ MÀN HÌNH CHÍNH")
        self.btn_back_main.setObjectName("exitBtn") 
        self.btn_back_main.setProperty("class", "menu-btn")
        self.btn_back_main.setCursor(Qt.PointingHandCursor)

        btn_layout.addWidget(self.btn_menu_trainees)
        btn_layout.addWidget(self.btn_menu_sessions)
        
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.btn_back_main)
        layout.addStretch()

    def _setup_trainee_list_page(self):
        layout = QVBoxLayout(self.page_trainees)
        margin = int(30 * self.scale_factor)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(int(15 * self.scale_factor))

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

        footer_layout = QHBoxLayout()
        self.btn_add_trainee = QPushButton("Thêm Mới")
        self.btn_add_trainee.setCursor(Qt.PointingHandCursor)
        self.btn_add_trainee.setMinimumWidth(130); self.btn_add_trainee.setMinimumHeight(40)
        
        self.btn_import_excel = QPushButton("Nhập Excel")
        self.btn_import_excel.setObjectName("importBtn")
        self.btn_import_excel.setCursor(Qt.PointingHandCursor)
        self.btn_import_excel.setMinimumWidth(130); self.btn_import_excel.setMinimumHeight(40)
        
        self.btn_back_to_menu = QPushButton("Quay Lại Menu")
        self.btn_back_to_menu.setObjectName("danger")
        self.btn_back_to_menu.setCursor(Qt.PointingHandCursor)
        self.btn_back_to_menu.setMinimumWidth(130); self.btn_back_to_menu.setMinimumHeight(40)

        footer_layout.addWidget(self.btn_add_trainee)
        footer_layout.addWidget(self.btn_import_excel)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_back_to_menu)
        layout.addLayout(footer_layout)

    def _setup_session_list_page(self):
        layout = QVBoxLayout(self.page_sessions)
        margin = int(30 * self.scale_factor)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(int(15 * self.scale_factor))

        header_layout = QHBoxLayout()
        lbl_title = QLabel("LỊCH SỬ CÁC PHIÊN TẬP")
        lbl_title.setStyleSheet(f"font-size: {int(20 * self.scale_factor)}px; font-weight: bold; color: #1abc9c;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.session_table = QTableWidget(0, 4)
        self.session_table.setHorizontalHeaderLabels(["Ngày tạo", "Tên phiên", "Hình thức", "Tiến độ"])
        self.session_table.verticalHeader().setVisible(False)
        self.session_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.session_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.session_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.session_table.setAlternatingRowColors(True)
        self.session_table.setStyleSheet("alternate-background-color: #3b5266;")
        
        header = self.session_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.session_table)

        footer_layout = QHBoxLayout()
        self.btn_view_report = QPushButton("Xem báo cáo")
        self.btn_view_report.setStyleSheet("background-color: #3498db; color: white;")
        self.btn_view_report.setCursor(Qt.PointingHandCursor)
        self.btn_view_report.setMinimumWidth(130); self.btn_view_report.setMinimumHeight(40)
        self.btn_view_report.setEnabled(False) 

        self.btn_back_from_session = QPushButton("Quay Lại Menu")
        self.btn_back_from_session.setObjectName("danger")
        self.btn_back_from_session.setCursor(Qt.PointingHandCursor)
        self.btn_back_from_session.setMinimumWidth(130); self.btn_back_from_session.setMinimumHeight(40)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_view_report)
        footer_layout.addWidget(self.btn_back_from_session)
        layout.addLayout(footer_layout)

    def _setup_session_detail_page(self):
        layout = QVBoxLayout(self.page_session_detail)
        margin = int(30 * self.scale_factor)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(int(10 * self.scale_factor))

        # --- HEADER: Title + View Option ---
        header_layout = QHBoxLayout()
        self.lbl_detail_title = QLabel("CHI TIẾT PHIÊN TẬP")
        self.lbl_detail_title.setStyleSheet(f"font-size: {int(20 * self.scale_factor)}px; font-weight: bold; color: #f39c12;")
        
        self.cmb_view_mode = QComboBox()
        self.cmb_view_mode.addItem("Danh sách chi tiết", "LIST")
        self.cmb_view_mode.addItem("Báo cáo tổng quan", "REPORT")
        self.cmb_view_mode.setFixedWidth(200)
        self.cmb_view_mode.setStyleSheet("background-color: #34495e; color: white; padding: 5px; font-weight: bold; border: 1px solid #1abc9c;")
        
        header_layout.addWidget(self.lbl_detail_title)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Chế độ xem:"))
        header_layout.addWidget(self.cmb_view_mode)
        layout.addLayout(header_layout)

        # --- CONTENT STACK ---
        self.detail_stack = QStackedWidget()
        layout.addWidget(self.detail_stack)

        # 1. VIEW DANH SÁCH (LIST)
        self.page_detail_list = QWidget()
        list_layout = QVBoxLayout(self.page_detail_list)
        list_layout.setContentsMargins(0, 10, 0, 0)
        
        # Sort option
        sort_layout = QHBoxLayout()
        self.cmb_sort = QComboBox()
        self.cmb_sort.addItem("Sắp xếp: Tên A-Z", "NAME_ASC")
        self.cmb_sort.addItem("Sắp xếp: Điểm cao -> thấp", "SCORE_DESC")
        self.cmb_sort.addItem("Sắp xếp: Điểm thấp -> cao", "SCORE_ASC")
        sort_layout.addStretch()
        sort_layout.addWidget(self.cmb_sort)
        list_layout.addLayout(sort_layout)

        # Table
        self.detail_table = QTableWidget(0, 6)
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.detail_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.detail_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setStyleSheet("alternate-background-color: #3b5266;")
        list_layout.addWidget(self.detail_table)
        self.detail_stack.addWidget(self.page_detail_list)

        # 2. VIEW BÁO CÁO (REPORT)
        self.page_detail_report = QWidget()
        report_layout = QVBoxLayout(self.page_detail_report)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; } QWidget { background-color: transparent; }")
        
        report_content = QWidget()
        self.report_inner_layout = QVBoxLayout(report_content)
        self.report_inner_layout.setSpacing(20)
        
        # A. Stats Cards (Dynamic Titles)
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0,0,0,0)
        stats_layout.setSpacing(15)
        
        def create_card(title, title_obj_name, value_obj_name):
            card = QFrame()
            card.setProperty("class", "report-card")
            card.setMinimumHeight(100)
            cl = QVBoxLayout(card)
            
            l1 = QLabel(title)
            l1.setProperty("class", "card-title")
            l1.setObjectName(title_obj_name) # Để logic có thể truy cập đổi tên
            
            l2 = QLabel("--")
            l2.setProperty("class", "card-value")
            l2.setObjectName(value_obj_name)
            l2.setAlignment(Qt.AlignCenter)
            
            cl.addWidget(l1); cl.addWidget(l2)
            return card, l1, l2

        # Lưu lại tham chiếu Title và Value để đổi tên sau
        card1, self.lbl_card1_title, self.lbl_card1_value = create_card("TỔNG SỐ NGƯỜI", "c1Title", "c1Value")
        card2, self.lbl_card2_title, self.lbl_card2_value = create_card("THẺ 2", "c2Title", "c2Value")
        card3, self.lbl_card3_title, self.lbl_card3_value = create_card("THẺ 3", "c3Title", "c3Value")
        card4, self.lbl_card4_title, self.lbl_card4_value = create_card("THẺ 4", "c4Title", "c4Value")
        
        stats_layout.addWidget(card1); stats_layout.addWidget(card2); stats_layout.addWidget(card3); stats_layout.addWidget(card4)
        self.report_inner_layout.addWidget(stats_container)

        # B. Charts Container
        self.charts_container_widget = QWidget()
        self.charts_layout = QHBoxLayout(self.charts_container_widget)
        self.charts_container_widget.setMinimumHeight(350)
        self.report_inner_layout.addWidget(self.charts_container_widget)

        # C. Evaluation
        eval_group = QFrame()
        eval_group.setStyleSheet("background-color: #34495e; border-radius: 8px; padding: 10px;")
        eval_lo = QVBoxLayout(eval_group)
        
        lbl_eval_title = QLabel("ĐÁNH GIÁ & KIẾN NGHỊ")
        lbl_eval_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1c40f; margin-bottom: 5px;")
        self.lbl_rpt_eval = QLabel("...")
        self.lbl_rpt_eval.setWordWrap(True)
        self.lbl_rpt_eval.setStyleSheet("font-size: 14px; color: #ecf0f1; line-height: 1.4;")
        
        eval_lo.addWidget(lbl_eval_title)
        eval_lo.addWidget(self.lbl_rpt_eval)
        self.report_inner_layout.addWidget(eval_group)
        
        self.report_inner_layout.addStretch()
        scroll.setWidget(report_content)
        report_layout.addWidget(scroll)
        self.detail_stack.addWidget(self.page_detail_report)

        # --- FOOTER ---
        footer_layout = QHBoxLayout()
        self.btn_view_personal = QPushButton("Xem quá trình cá nhân")
        self.btn_view_personal.setStyleSheet("background-color: #27ae60; color: white;")
        self.btn_view_personal.setMinimumWidth(180); self.btn_view_personal.setMinimumHeight(40)
        self.btn_view_personal.setEnabled(False)

        self.btn_back_to_session_list = QPushButton("Quay lại")
        self.btn_back_to_session_list.setObjectName("danger")
        self.btn_back_to_session_list.setMinimumWidth(130); self.btn_back_to_session_list.setMinimumHeight(40)

        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_view_personal)
        footer_layout.addWidget(self.btn_back_to_session_list)
        layout.addLayout(footer_layout)