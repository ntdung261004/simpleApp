# file: gui/ui/ui_manage.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QTableWidget, QTableWidgetItem,
    QFrame, QSizePolicy, QAbstractItemView, QHeaderView, QListWidget, QStackedWidget,
    QApplication, QLineEdit
)
from PySide6.QtGui import QFont, QPixmap, QColor, QPainter
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QGraphicsDropShadowEffect

class VideoLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setText("Chưa có ảnh")

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def resizeEvent(self, event):
        self.update()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._pixmap.isNull():
            scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            point = self.rect().center() - scaled_pixmap.rect().center()
            painter.drawPixmap(point, scaled_pixmap)
        else:
            super().paintEvent(event)

class ManageGui(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setObjectName("ManageWidget")

        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        self.scale_factor = screen_height / 1080.0

        def scale_font(base_size):
            return max(9, int(base_size * self.scale_factor))

        self.setStyleSheet(f"""
            #ManageWidget {{
                background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI';
            }}
            QFrame#panel {{
                background-color: #34495e; border-radius: {int(12 * self.scale_factor)}px; border: 1px solid #4a6278;
            }}
            QLabel#title {{
                color: #ecf0f1; padding: {int(10 * self.scale_factor)}px;
            }}
            QGroupBox {{
                font-size: {scale_font(14)}px; font-weight: bold; border: 1px solid #4a6278;
                border-radius: {int(8 * self.scale_factor)}px; margin-top: {int(10 * self.scale_factor)}px; color: #ecf0f1;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top center;
                padding: {int(2 * self.scale_factor)}px {int(8 * self.scale_factor)}px;
                background-color: #415a72; border-radius: {int(4 * self.scale_factor)}px;
            }}
            QPushButton {{
                background-color: #1abc9c; color: white; font-size: {scale_font(14)}px; font-weight: bold;
                border: none; padding: {int(8 * self.scale_factor)}px {int(18 * self.scale_factor)}px;
                border-radius: {int(8 * self.scale_factor)}px;
            }}
            QPushButton:hover {{ background-color: #16a085; }}
            QPushButton#danger {{ background-color: #e74c3c; }}
            QPushButton#danger:hover {{ background-color: #c0392b; }}
            QListWidget, QTableWidget {{
                background-color: #2c3e50; border: 1px solid #4a6278;
                border-radius: {int(6 * self.scale_factor)}px; gridline-color: #4a6278; color: #ecf0f1;
            }}
            QListWidget::item:selected, QTableWidget::item:selected {{
                background-color: #1abc9c; color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: #415a72; color: #ecf0f1;
                padding: {int(4 * self.scale_factor)}px; border: 1px solid #4a6278;
            }}
            VideoLabel {{
                 background-color: #212f3d; border: 1px solid #4a6278;
                 border-radius: {int(8 * self.scale_factor)}px; color: #95a5a6;
                 font-size: {scale_font(16)}px;
            }}
            /* --- BẮT ĐẦU VÙNG TINH CHỈNH: THÊM STYLE CHO THANH TÌM KIẾM --- */
            QLineEdit#searchBox {{
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: {int(6 * self.scale_factor)}px;
                padding: {int(6 * self.scale_factor)}px;
                color: #ecf0f1;
                font-size: {scale_font(13)}px;
            }}
            QLineEdit#searchBox:focus {{
                border: 1px solid #1abc9c;
            }}
            /* --- KẾT THÚC VÙNG TINH CHỈNH --- */
        """)

        self.setupUi()
        self._apply_labels()

    def setupUi(self):
        def scale_font(base_size, weight=QFont.Normal):
            font = QFont('Segoe UI', max(9, int(base_size * self.scale_factor)))
            font.setWeight(weight)
            return font

        margin = int(20 * self.scale_factor)
        spacing = int(15 * self.scale_factor)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(margin, int(10 * self.scale_factor), margin, margin)
        root_layout.setSpacing(spacing)

        self.title_label = QLabel()
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(scale_font(18, QFont.Bold))
        root_layout.addWidget(self.title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(spacing)
        root_layout.addLayout(columns_layout)

        columns_layout.addWidget(self._create_left_column(), 25)
        columns_layout.addWidget(self._create_center_column(), 50)
        columns_layout.addWidget(self._create_right_column(), 25)

    def _apply_labels(self):
        labels = self.config.get("labels", {})
        main_title = labels.get("app_title", "Quản lý")
        self.title_label.setText(main_title.upper())
        self.soldier_box.setTitle(labels.get("trainee_list_title", "Danh sách Người học"))
        header_name = labels.get("trainee_list_header_name", "Họ và Tên")
        header_class = labels.get("trainee_list_header_class", "Đơn vị")
        self.soldier_table.setHorizontalHeaderLabels([header_name, header_class])
        self.history_box.setTitle(labels.get("history_title_prefix", "Lịch sử bắn"))
        
        # Thêm placeholder text cho thanh tìm kiếm
        trainee_term = labels.get("trainee", "chiến sĩ")
        self.search_box.setPlaceholderText(f"Tìm kiếm {trainee_term.lower()}...")


    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(int(15 * self.scale_factor))
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, int(4 * self.scale_factor))
        panel.setGraphicsEffect(shadow)
        return panel

    def _create_left_column(self) -> QWidget:
        panel = self._create_styled_panel()
        margin = int(15 * self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(margin)

        self.soldier_box = QGroupBox()
        soldier_layout = QVBoxLayout(self.soldier_box)

        # --- BẮT ĐẦU VÙNG TINH CHỈNH: THÊM THANH TÌM KIẾM VÀO LAYOUT ---
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        soldier_layout.addWidget(self.search_box)
        # --- KẾT THÚC VÙNG TINH CHỈNH ---

        self.soldier_table = QTableWidget(0, 2)
        self.soldier_table.verticalHeader().setVisible(False)
        self.soldier_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.soldier_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.soldier_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.soldier_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        soldier_layout.addWidget(self.soldier_table)
        layout.addWidget(self.soldier_box, 1)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Thêm mới")
        self.back_button = QPushButton("Quay lại")
        self.back_button.setObjectName("danger")
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.back_button)
        layout.addLayout(buttons_layout)
        return panel
        
    def _create_center_column(self) -> QWidget:
        panel = self._create_styled_panel()
        margin = int(15 * self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)

        self.center_stack = QStackedWidget()
        layout.addWidget(self.center_stack)

        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(margin)

        analysis_box = self._create_analysis_box()
        shot_list_box = self._create_shot_list_box()
        shot_preview_box = self._create_shot_preview_box()

        data_layout.addWidget(analysis_box, 2)
        data_layout.addWidget(shot_list_box, 3)
        data_layout.addWidget(shot_preview_box, 5)

        message_widget = QWidget()
        message_layout = QVBoxLayout(message_widget)
        self.center_message_label = QLabel("...")
        self.center_message_label.setAlignment(Qt.AlignCenter)
        font_size = max(9, int(16 * self.scale_factor))
        self.center_message_label.setStyleSheet(f"font-size: {font_size}px; color: #95a5a6;")
        message_layout.addWidget(self.center_message_label)

        self.center_stack.addWidget(data_widget)
        self.center_stack.addWidget(message_widget)
        return panel

    def _create_analysis_box(self) -> QGroupBox:
        box = QGroupBox("Phân tích Phiên bắn được chọn")
        layout = QVBoxLayout(box)

        def scale_font(base_size, weight=QFont.Normal):
            font = QFont("Segoe UI", max(9, int(base_size * self.scale_factor)))
            font.setWeight(weight)
            return font

        self.analysis_summary_label = QLabel("Tổng phát bắn: -- | Tỷ lệ trúng: -- | Điểm trung bình: --")
        self.analysis_summary_label.setFont(scale_font(10))
        self.analysis_summary_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.analysis_summary_label)

        self.analysis_target_table = QTableWidget(3, 4)
        self.analysis_target_table.setHorizontalHeaderLabels(["Loại bia", "Số phát trúng", "Tổng điểm", "Độ chụm"])
        self.analysis_target_table.verticalHeader().setVisible(False)
        self.analysis_target_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.analysis_target_table.setFocusPolicy(Qt.NoFocus)
        self.analysis_target_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.analysis_target_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.analysis_target_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        row_height = int(32 * self.scale_factor)
        self.analysis_target_table.verticalHeader().setDefaultSectionSize(row_height)
        self.analysis_target_table.setFixedHeight(self.analysis_target_table.horizontalHeader().height() + 3 * row_height + 2)

        target_names = ["Bia số 4", "Bia số 7", "Bia số 8"]
        self.analysis_view_buttons = {}
        for row, name in enumerate(target_names):
            name_item = QTableWidgetItem(name)
            name_item.setFont(scale_font(10, QFont.Bold))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.analysis_target_table.setItem(row, 0, name_item)
            for col in range(1, 3):
                item = QTableWidgetItem("--")
                item.setTextAlignment(Qt.AlignCenter)
                self.analysis_target_table.setItem(row, col, item)

            view_button = QPushButton("Xem")
            font_size = max(8, int(9 * self.scale_factor))
            padding = int(4 * self.scale_factor)
            view_button.setStyleSheet(f"padding: {padding}px {padding*2}px; font-size: {font_size}px;")
            target_key = ['bia_so_4', 'bia_so_7_8', 'bia_so_8'][row]
            self.analysis_view_buttons[target_key] = view_button
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0,0,0,0)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(view_button)
            self.analysis_target_table.setCellWidget(row, 3, cell_widget)
        layout.addWidget(self.analysis_target_table)
        return box

    def _create_shot_list_box(self) -> QGroupBox:
        box = QGroupBox("Chi tiết từng phát bắn")
        layout = QVBoxLayout(box)
        self.shot_table = QTableWidget(0, 4)
        self.shot_table.setHorizontalHeaderLabels(["Phát", "Thời gian", "Mục tiêu", "Điểm"])
        self.shot_table.verticalHeader().setVisible(False)
        self.shot_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shot_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.shot_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.shot_table)
        return box

    def _create_shot_preview_box(self) -> QGroupBox:
        box = QGroupBox("Ảnh kết quả")
        layout = QVBoxLayout(box)
        self.result_image = VideoLabel()
        layout.addWidget(self.result_image, 1)

        nav_layout = QHBoxLayout()
        self.prev_shot_button = QPushButton("◀ Trước")
        self.shot_index_label = QLabel("Phát 0/0")
        self.shot_index_label.setAlignment(Qt.AlignCenter)
        font_size = max(9, int(14 * self.scale_factor))
        self.shot_index_label.setStyleSheet(f"font-size: {font_size}px; font-weight: bold;")
        self.next_shot_button = QPushButton("Sau ▶")

        nav_layout.addWidget(self.prev_shot_button)
        nav_layout.addWidget(self.shot_index_label, 1)
        nav_layout.addWidget(self.next_shot_button)
        layout.addLayout(nav_layout)
        return box

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        margin = int(15 * self.scale_factor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(margin, margin, margin, margin)

        self.right_stack = QStackedWidget()
        layout.addWidget(self.right_stack)

        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(margin)

        self.history_box = QGroupBox()
        history_layout = QVBoxLayout(self.history_box)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        data_layout.addWidget(self.history_box)

        message_widget = QWidget()
        message_layout = QVBoxLayout(message_widget)
        self.right_message_label = QLabel("...")
        self.right_message_label.setAlignment(Qt.AlignCenter)
        font_size = max(9, int(16 * self.scale_factor))
        self.right_message_label.setStyleSheet(f"font-size: {font_size}px; color: #95a5a6;")
        message_layout.addWidget(self.right_message_label)

        self.right_stack.addWidget(data_widget)
        self.right_stack.addWidget(message_widget)
        return panel