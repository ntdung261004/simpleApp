# file: gui/ui/ui_manage.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTableWidget, QFrame, QStackedWidget, QApplication, QLineEdit,
    QHeaderView, QAbstractItemView, QComboBox, QScrollArea, QGridLayout,
    QTextEdit, QGroupBox
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
            
            /* TextEdit ghi chú */
            QTextEdit {{
                background-color: #2c3e50; border: 1px solid #4a6278; color: white;
                border-radius: 6px; padding: 5px; font-size: 14px;
            }}
            
            /* Style chung cho GroupBox để tránh đè title */
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #7f8c8d;
                border-radius: 5px;
                margin-top: 20px; /* Quan trọng: Tạo khoảng trống cho title */
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
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
        
        # --- TRANG 4: THỐNG KÊ CÁ NHÂN (NEW) ---
        self.page_personal_stats = QWidget()
        self._setup_personal_stats_page()
        self.main_stack.addWidget(self.page_personal_stats)

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

        # --- HEADER 1: Title ---
        title_layout = QHBoxLayout()
        lbl_title = QLabel("DANH SÁCH NGƯỜI TẬP")
        lbl_title.setStyleSheet(f"font-size: {int(24 * self.scale_factor)}px; font-weight: bold; color: #1abc9c;")
        title_layout.addWidget(lbl_title)
        title_layout.addStretch()
        self.total_count_label = QLabel("Tổng số: 0")
        self.total_count_label.setStyleSheet("font-style: italic; color: #bdc3c7; font-size: 14px; font-weight: bold;")
        title_layout.addWidget(self.total_count_label)
        layout.addLayout(title_layout)

        # --- HEADER 2: Filter & Sort Controls ---
        controls_layout = QHBoxLayout()
        
        # Search Box
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("🔍 Tìm theo tên...")
        self.search_box.setFixedWidth(int(250 * self.scale_factor))
        
        # Filter Unit ComboBox
        self.cmb_filter_unit = QComboBox()
        self.cmb_filter_unit.setPlaceholderText("Tất cả đơn vị")
        self.cmb_filter_unit.addItem("Tất cả đơn vị", "ALL")
        self.cmb_filter_unit.setMinimumWidth(int(150 * self.scale_factor))
        
        # Sort ComboBox
        self.cmb_sort_trainees = QComboBox()
        self.cmb_sort_trainees.addItem("Sắp xếp: Tên A-Z", "NAME_ASC")
        self.cmb_sort_trainees.addItem("Sắp xếp: Tên Z-A", "NAME_DESC")
        self.cmb_sort_trainees.addItem("Sắp xếp: Đơn vị", "UNIT")
        self.cmb_sort_trainees.setMinimumWidth(int(180 * self.scale_factor))

        controls_layout.addWidget(self.search_box)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(QLabel("Lọc:"))
        controls_layout.addWidget(self.cmb_filter_unit)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(QLabel("Xếp:"))
        controls_layout.addWidget(self.cmb_sort_trainees)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # --- TABLE ---
        self.soldier_table = QTableWidget(0, 4)
        self.soldier_table.setHorizontalHeaderLabels(["STT", "Họ và Tên", "Đơn vị", "Ghi chú"])
        self.soldier_table.verticalHeader().setVisible(False)
        self.soldier_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # --- [TINH CHỈNH] CHO PHÉP CHỌN NHIỀU DÒNG (KÉO THẢ) ---
        self.soldier_table.setSelectionMode(QAbstractItemView.ExtendedSelection) 
        # --------------------------------------------------------
        
        self.soldier_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.soldier_table.setAlternatingRowColors(True)
        self.soldier_table.setStyleSheet("alternate-background-color: #3b5266;")
        
        header = self.soldier_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.soldier_table)

        # --- FOOTER ---
        footer_layout = QHBoxLayout()
        
        self.btn_add_trainee = QPushButton("Thêm Mới")
        self.btn_add_trainee.setCursor(Qt.PointingHandCursor)
        self.btn_add_trainee.setMinimumHeight(40)
        
        self.btn_import_excel = QPushButton("Nhập Excel")
        self.btn_import_excel.setObjectName("importBtn")
        self.btn_import_excel.setCursor(Qt.PointingHandCursor)
        self.btn_import_excel.setMinimumHeight(40)
        
        self.btn_note = QPushButton("Thêm/Sửa Ghi chú")
        self.btn_note.setStyleSheet("background-color: #f39c12; color: white;")
        self.btn_note.setCursor(Qt.PointingHandCursor)
        self.btn_note.setMinimumHeight(40)
        self.btn_note.setEnabled(False) 
        
        self.btn_personal_stats = QPushButton("Xem Thống kê Cá nhân")
        self.btn_personal_stats.setStyleSheet("background-color: #9b59b6; color: white;")
        self.btn_personal_stats.setCursor(Qt.PointingHandCursor)
        self.btn_personal_stats.setMinimumHeight(40)
        self.btn_personal_stats.setEnabled(False)

        self.btn_back_to_menu = QPushButton("Quay Lại Menu")
        self.btn_back_to_menu.setObjectName("danger")
        self.btn_back_to_menu.setCursor(Qt.PointingHandCursor)
        self.btn_back_to_menu.setMinimumHeight(40)

        footer_layout.addWidget(self.btn_add_trainee)
        footer_layout.addWidget(self.btn_import_excel)
        footer_layout.addSpacing(15)
        footer_layout.addWidget(self.btn_note)
        footer_layout.addWidget(self.btn_personal_stats)
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

        self.btn_delete_session = QPushButton("Xóa phiên")
        self.btn_delete_session.setObjectName("danger")
        self.btn_delete_session.setCursor(Qt.PointingHandCursor)
        self.btn_delete_session.setMinimumWidth(130); self.btn_delete_session.setMinimumHeight(40)
        self.btn_delete_session.setEnabled(False)

        self.btn_back_from_session = QPushButton("Quay Lại Menu")
        self.btn_back_from_session.setObjectName("danger")
        self.btn_back_from_session.setCursor(Qt.PointingHandCursor)
        self.btn_back_from_session.setMinimumWidth(130); self.btn_back_from_session.setMinimumHeight(40)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_view_report)
        footer_layout.addSpacing(10)
        footer_layout.addWidget(self.btn_delete_session)
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
            l1.setObjectName(title_obj_name) 
            
            l2 = QLabel("--")
            l2.setProperty("class", "card-value")
            l2.setObjectName(value_obj_name)
            l2.setAlignment(Qt.AlignCenter)
            
            cl.addWidget(l1); cl.addWidget(l2)
            return card, l1, l2

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

    # --- SETUP TRANG THỐNG KÊ CÁ NHÂN (NEW) ---
    def _setup_personal_stats_page(self):
        main_lo = QVBoxLayout(self.page_personal_stats)
        main_lo.setContentsMargins(int(20*self.scale_factor), int(20*self.scale_factor), int(20*self.scale_factor), int(20*self.scale_factor))
        
        # 1. Header
        header_lo = QHBoxLayout()
        self.btn_back_from_personal = QPushButton("◀ Quay lại Danh sách")
        self.btn_back_from_personal.setObjectName("danger")
        self.btn_back_from_personal.setMinimumHeight(40)
        
        self.lbl_personal_name = QLabel("NGUYỄN VĂN A - C1")
        self.lbl_personal_name.setStyleSheet("font-size: 24px; font-weight: bold; color: #f1c40f;")
        
        # --- THÊM: ComboBox chọn chế độ xem ---
        self.cmb_stats_filter = QComboBox()
        self.cmb_stats_filter.addItem("Xem: Bắn từng viên", "SINGLE")
        self.cmb_stats_filter.addItem("Xem: Bắn loạt 3", "BURST_3")
        self.cmb_stats_filter.setMinimumWidth(200)
        self.cmb_stats_filter.setMinimumHeight(40)
        self.cmb_stats_filter.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; border: 1px solid #1abc9c; padding: 5px;")
        
        header_lo.addWidget(self.btn_back_from_personal)
        header_lo.addSpacing(20)
        header_lo.addWidget(self.lbl_personal_name)
        header_lo.addStretch()
        header_lo.addWidget(QLabel("Chế độ xem:"))
        header_lo.addWidget(self.cmb_stats_filter) # Add combo box
        main_lo.addLayout(header_lo)
        
        # 2. Content (Splitter or HBox)
        content_lo = QHBoxLayout()
        
        # LEFT: Lịch sử các phiên (Table)
        left_group = QGroupBox("Lịch sử tham gia")
        left_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #7f8c8d; border-radius: 5px; margin-top: 20px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        l_lo = QVBoxLayout(left_group)
        
        self.personal_table = QTableWidget(0, 3) # Giảm xuống 3 cột cho gọn (Ngày, Tên phiên, Kết quả)
        self.personal_table.setHorizontalHeaderLabels(["Ngày", "Phiên tập", "Kết quả"])
        self.personal_table.verticalHeader().setVisible(False)
        self.personal_table.setAlternatingRowColors(True)
        self.personal_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.personal_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.personal_table.setStyleSheet("alternate-background-color: #3b5266;")
        
        h = self.personal_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        l_lo.addWidget(self.personal_table)
        content_lo.addWidget(left_group, 4) # Tỷ lệ 40%
        
        # RIGHT: Thống kê & Ghi chú
        right_widget = QWidget()
        r_lo = QVBoxLayout(right_widget)
        r_lo.setContentsMargins(0,0,0,0)
        
        # Cards
        cards_lo = QHBoxLayout()
        def mk_mini_card(title, obj_val):
            fr = QFrame()
            fr.setStyleSheet("background-color: #34495e; border-radius: 5px; border: 1px solid #1abc9c;")
            v = QVBoxLayout(fr)
            v.setContentsMargins(5,5,5,5)
            l1 = QLabel(title); l1.setStyleSheet("color:#bdc3c7; font-size:12px; font-weight:bold;")
            l2 = QLabel("--"); l2.setObjectName(obj_val); l2.setStyleSheet("color:white; font-size:18px; font-weight:bold;")
            l2.setAlignment(Qt.AlignCenter)
            v.addWidget(l1); v.addWidget(l2)
            return fr, l2
            
        c1, self.lbl_p_sessions = mk_mini_card("SỐ PHIÊN TẬP", "vp1")
        c2, self.lbl_p_avg = mk_mini_card("TRUNG BÌNH", "vp2") # Title động sẽ set trong logic
        c3, self.lbl_p_best = mk_mini_card("TỐT NHẤT", "vp3")
        
        cards_lo.addWidget(c1); cards_lo.addWidget(c2); cards_lo.addWidget(c3)
        r_lo.addLayout(cards_lo)
        
        # Chart Area
        self.personal_chart_container = QWidget()
        self.personal_chart_layout = QVBoxLayout(self.personal_chart_container)
        self.personal_chart_container.setMinimumHeight(250)
        self.personal_chart_container.setStyleSheet("background-color: #2c3e50; border: 1px solid #4a6278; border-radius: 5px;")
        r_lo.addWidget(self.personal_chart_container)
        
        # System Evaluation
        self.lbl_p_eval = QLabel("Đánh giá hệ thống...")
        self.lbl_p_eval.setWordWrap(True)
        self.lbl_p_eval.setStyleSheet("color: #ecf0f1; font-style: italic; margin: 5px;")
        r_lo.addWidget(self.lbl_p_eval)
        
        # Notes
        note_group = QGroupBox("Ghi chú & Nhận xét (Giáo Viên / Cán Bộ)")
        note_group.setStyleSheet("QGroupBox { font-weight: bold; color: #f39c12; border: 1px solid #f39c12; margin-top: 20px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        n_lo = QVBoxLayout(note_group)
        self.txt_personal_note = QTextEdit()
        self.txt_personal_note.setPlaceholderText("Nhập nhận xét về quá trình luyện tập...")
        self.btn_save_p_note = QPushButton("Lưu Ghi chú")
        self.btn_save_p_note.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_save_p_note.setCursor(Qt.PointingHandCursor)
        
        n_lo.addWidget(self.txt_personal_note)
        n_lo.addWidget(self.btn_save_p_note)
        r_lo.addWidget(note_group)
        
        content_lo.addWidget(right_widget, 6) # Tỷ lệ 60%
        main_lo.addLayout(content_lo)