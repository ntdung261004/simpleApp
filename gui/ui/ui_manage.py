# gui/ui/ui_manage.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QFrame, QSizePolicy, QAbstractItemView, QHeaderView , QListWidget, QStackedWidget # Thêm import cần thiết
)
from PySide6.QtGui import QFont, QPixmap, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect

class VideoLabel(QLabel):
    """Label hiển thị ảnh, tự động co giãn ảnh cho vừa với kích thước của chính nó."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background-color: #212f3d; border: 1px solid #4a6278; "
            "border-radius: 8px; color: #95a5a6; font-size: 16px;"
        )
        self.setText("Chưa có ảnh")

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        super().setPixmap(self._scaled_pixmap())

    def resizeEvent(self, event):
        if not self._pixmap.isNull():
            super().setPixmap(self._scaled_pixmap())
        super().resizeEvent(event)

    def _scaled_pixmap(self):
        return self._pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
    
class ManageGui(QWidget):
    def __init__(self):
        super().__init__()

        # ===== Style đồng bộ với ui_practice =====
        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Segoe UI';
            }
            QFrame#panel {
                background-color: #34495e;
                border-radius: 12px;
                border: 1px solid #4a6278;
            }
            QLabel#title {
                color: #ecf0f1;
                padding: 10px;
            }
            QLabel.panel-title {
                font-size: 16px;
                font-weight: bold;
                color: #ecf0f1;
            }
            QPushButton {
                background-color: #1abc9c;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                padding: 8px 18px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #16a085; }
            QPushButton#danger { background-color: #e74c3c; }
            QPushButton#danger:hover { background-color: #c0392b; }

            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #4a6278;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 2px 8px;
                background-color: #415a72;
                border-radius: 4px;
            }
            QListWidget {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 6px;
            }
            QTableWidget {
                background-color: #2c3e50;
                border: 1px solid #4a6278;
                border-radius: 6px;
                gridline-color: #4a6278;
            }
            QLabel#resultImage {
                background-color: #212f3d;
                border: 1px solid #4a6278;
                border-radius: 8px;
                color: #95a5a6;
                font-size: 18px;
            }
            QHeaderView::section {
                background-color: #415a72; /* Giống màu tiêu đề GroupBox */
                color: #ecf0f1;
                padding: 4px;
                border: 1px solid #4a6278;
            }
        """)

        # ===== Root layout =====
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 10, 20, 20)
        root_layout.setSpacing(15)

        # Title
        title_label = QLabel("QUẢN LÝ DANH SÁCH CHIẾN SĨ VÀ THỐNG KÊ KẾT QUẢ BẮN")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont('Segoe UI', 18, QFont.Bold)
        title_label.setFont(title_font)
        root_layout.addWidget(title_label)

        # Columns layout (3 cột: 2.5 - 5 - 2.5)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        root_layout.addLayout(columns_layout)

        # Left column (2.5)
        columns_layout.addWidget(self._create_left_column(), 25)
        # Center column (5)
        columns_layout.addWidget(self._create_center_column(), 50)
        # Right column (2.5)
        columns_layout.addWidget(self._create_right_column(), 25)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        panel.setGraphicsEffect(shadow)
        return panel

    def _create_left_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        soldier_box = QGroupBox("Danh sách Chiến sĩ")
        soldier_layout = QVBoxLayout(soldier_box)

        # Tạo bảng
        self.soldier_table = QTableWidget()
        self.soldier_table.setColumnCount(2)
        self.soldier_table.setHorizontalHeaderLabels(["Họ và Tên", "Lớp"])
        self.soldier_table.verticalHeader().setVisible(False)
        self.soldier_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.soldier_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.soldier_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # === THAY ĐỔI 3: CẬP NHẬT CO GIÃN CỘT ===
        header = self.soldier_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) 
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        soldier_layout.addWidget(self.soldier_table)
        layout.addWidget(soldier_box, 1)

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
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        
        #layout.setContentsMargins(0,0,0,0) # QStackedWidget sẽ quản lý margin

        # === THAY ĐỔI: SỬ DỤNG QStackedWidget ===
        self.center_stack = QStackedWidget()
        layout.addWidget(self.center_stack)

        # --- "Trang" 1: Giao diện hiển thị dữ liệu ---
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(15, 15, 15, 15)
        data_layout.setSpacing(15)

        # --- BẮT ĐẦU THAY ĐỔI ---
        analysis_box = QGroupBox("Phân tích Phiên bắn được chọn")
        analysis_layout = QVBoxLayout(analysis_box)

        # 1. Dòng tóm tắt tổng quan, căn giữa
        self.analysis_summary_label = QLabel("Tổng phát bắn: --  |  Tỷ lệ trúng: --  |  Điểm trung bình: --")
        self.analysis_summary_label.setFont(QFont("Segoe UI", 10))
        self.analysis_summary_label.setAlignment(Qt.AlignCenter)
        analysis_layout.addWidget(self.analysis_summary_label)

        # 2. Bảng thống kê cố định 3 dòng theo từng loại bia
        self.analysis_target_table = QTableWidget(3, 4) # Luôn có 3 dòng, 4 cột
        self.analysis_target_table.setHorizontalHeaderLabels(["Loại bia", "Số phát trúng", "Tổng điểm", "Độ chụm"])
        self.analysis_target_table.verticalHeader().setVisible(False)
        self.analysis_target_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.analysis_target_table.setFocusPolicy(Qt.NoFocus)
        self.analysis_target_table.setSelectionMode(QAbstractItemView.NoSelection)

        # Tỉ lệ 4 cột bằng nhau
        header = self.analysis_target_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Điền tên bia và tạo item trống, căn giữa sẵn
        target_names = ["Bia số 4", "Bia số 7", "Bia số 8"]
        # Lưu trữ các widget động để cập nhật từ file logic
        self.analysis_widgets = {}
        self.analysis_view_buttons = {}
        for row, name in enumerate(target_names):
            # Cột 0: Tên bia
            name_item = QTableWidgetItem(name)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.analysis_target_table.setItem(row, 0, name_item)
            
            # Cột 1 và 2: Số lần trúng và Tổng điểm
            for col in range(1, 3): 
                item = QTableWidgetItem("--")
                item.setTextAlignment(Qt.AlignCenter)
                self.analysis_target_table.setItem(row, col, item)

            # Cột 3: Nút "Xem" độ chụm
            view_button = QPushButton("Xem")
            view_button.setStyleSheet("padding: 4px 8px; font-size: 9px;")
            # Lưu lại nút bấm và ánh xạ với tên bia gốc để dùng sau
            target_key = ['bia_so_4', 'bia_so_7_8', 'bia_so_8'][row]
            self.analysis_view_buttons[target_key] = view_button
            
            # Tạo một widget chứa nút để căn giữa trong ô
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0,0,0,0)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(view_button)
            self.analysis_target_table.setCellWidget(row, 3, cell_widget)

        
        analysis_layout.addWidget(self.analysis_target_table)
        
        data_layout.addWidget(analysis_box, 1) # Giữ nguyên tỉ lệ 1
        # --- KẾT THÚC THAY ĐỔI ---

        detail_box = QGroupBox("Thông tin chi tiết từng phát bắn")
        detail_layout = QVBoxLayout(detail_box)

        # === THAY ĐỔI CÁCH TẠO VÀ CẤU HÌNH BẢNG TẠI ĐÂY ===
        self.shot_table = QTableWidget(0, 4)
        # 1. Đổi tên cột "Lần" thành "Phát"
        self.shot_table.setHorizontalHeaderLabels(["Phát", "Thời gian", "Mục tiêu", "Điểm"])
        # 2. Ẩn cột số thứ tự hàng mặc định
        self.shot_table.verticalHeader().setVisible(False)
        # 4. Ngăn sửa và cài đặt chế độ chọn hàng
        self.shot_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shot_table.setSelectionBehavior(QAbstractItemView.SelectRows)


        # 3. Tinh chỉnh bố cục cột cho hài hòa
        header = self.shot_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Cột "Phát" vừa đủ
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Cột "Thời gian" co giãn
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Cột "Mục tiêu" co giãn
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Cột "Điểm" vừa đủ
        # =======================================================

        detail_layout.addWidget(self.shot_table, 1)
        
        # 1. Tạo một QWidget để làm khung chứa bên ngoài
        image_container = QWidget()
        
        # 2. Đặt chiều cao CỐ ĐỊNH cho khung chứa này. 
        #    Bạn có thể thay đổi số 400 thành giá trị mong muốn.
        image_container.setFixedHeight(400)
        
        # 3. Tạo layout cho khung chứa và đặt label ảnh vào bên trong
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.result_image = VideoLabel() 
        self.result_image.setObjectName("resultImage")
        image_container_layout.addWidget(self.result_image)

        # 4. Thêm KHUNG CHỨA vào layout chính với stretch = 0 (không co giãn)
        #    Thay thế cho dòng `detail_layout.addWidget(self.result_image, 3)` cũ.
        detail_layout.addWidget(image_container, 0)
        nav_layout = QHBoxLayout()
        self.prev_shot_button = QPushButton("◀ Trước")
        self.shot_index_label = QLabel("Phát 0/0")
        self.shot_index_label.setAlignment(Qt.AlignCenter)
        self.shot_index_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.next_shot_button = QPushButton("Sau ▶")
        nav_layout.addWidget(self.prev_shot_button)
        nav_layout.addWidget(self.shot_index_label, 1)
        nav_layout.addWidget(self.next_shot_button)
        detail_layout.addLayout(nav_layout)
        data_layout.addWidget(detail_box, 4)

        # --- "Trang" 2: Giao diện hiển thị thông báo ---
        message_widget = QWidget()
        message_layout = QVBoxLayout(message_widget)
        self.center_message_label = QLabel("...")
        self.center_message_label.setAlignment(Qt.AlignCenter)
        self.center_message_label.setStyleSheet("font-size: 16px; color: #95a5a6;")
        message_layout.addWidget(self.center_message_label)
        
        # Thêm các trang vào Stack
        self.center_stack.addWidget(data_widget) # Index 0
        self.center_stack.addWidget(message_widget) # Index 1

        return panel

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        
        #layout.setContentsMargins(0,0,0,0)

        # === THAY ĐỔI: SỬ DỤNG QStackedWidget ===
        self.right_stack = QStackedWidget()
        layout.addWidget(self.right_stack)
        
        # --- "Trang" 1: Giao diện hiển thị dữ liệu ---
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(15, 15, 15, 15)
        data_layout.setSpacing(15)

        history_box = QGroupBox("Lịch sử bắn của Chiến sĩ được chọn")
        history_layout = QVBoxLayout(history_box)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        data_layout.addWidget(history_box)

        # --- "Trang" 2: Giao diện hiển thị thông báo ---
        message_widget = QWidget()
        message_layout = QVBoxLayout(message_widget)
        self.right_message_label = QLabel("...")
        self.right_message_label.setAlignment(Qt.AlignCenter)
        self.right_message_label.setStyleSheet("font-size: 16px; color: #95a5a6;")
        message_layout.addWidget(self.right_message_label)

        # Thêm các trang vào Stack
        self.right_stack.addWidget(data_widget) # Index 0
        self.right_stack.addWidget(message_widget) # Index 1

        return panel
    
    def _create_overview_panel(self) -> QGroupBox:
        """Tạo và trả về GBox chứa bảng tổng quan phiên tập."""
        overview_group = QGroupBox("Tổng quan Phiên tập")
        overview_group.setFont(QFont("Segoe UI", 11, QFont.Bold))
        
        layout = QVBoxLayout(overview_group)
        layout.setContentsMargins(5, 5, 5, 5)

        # Tạo bảng
        self.overview_table = QTableWidget(4, 2)
        layout.addWidget(self.overview_table)
        
        # --- Thiết lập cho bảng ---
        self.overview_table.setVerticalHeaderVisible(False) # Ẩn header dọc
        self.overview_table.setHorizontalHeaderLabels(["Thông số", "Giá trị"])
        self.overview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.overview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.overview_table.setFocusPolicy(Qt.NoFocus) # Bỏ focus
        self.overview_table.setSelectionMode(QAbstractItemView.NoSelection) # Cấm chọn

        # --- Thêm các dòng dữ liệu tĩnh (cột 1) ---
        stat_titles = ["Tổng số phát", "Điểm trung bình", "Điểm cao nhất", "Độ chụm"]
        for row, title in enumerate(stat_titles):
            item = QTableWidgetItem(title)
            item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable) # Cấm chỉnh sửa
            self.overview_table.setItem(row, 0, item)

        # --- Tạo các widget cho dữ liệu động (cột 2) ---
        # Dòng "Tổng số phát"
        self.overview_total_shots_item = QTableWidgetItem("--")
        self.overview_table.setItem(0, 1, self.overview_total_shots_item)

        # Dòng "Điểm trung bình"
        self.overview_avg_score_item = QTableWidgetItem("--")
        self.overview_table.setItem(1, 1, self.overview_avg_score_item)

        # Dòng "Điểm cao nhất"
        self.overview_max_score_item = QTableWidgetItem("--")
        self.overview_table.setItem(2, 1, self.overview_max_score_item)

        # Dòng "Độ chụm" - Kết hợp Label và Button
        grouping_cell_widget = QWidget()
        grouping_layout = QHBoxLayout(grouping_cell_widget)
        grouping_layout.setContentsMargins(5, 0, 0, 0)
        
        self.overview_grouping_label = QLabel("--") # Label để cập nhật giá trị
        self.overview_view_grouping_button = QPushButton("Xem")
        self.overview_view_grouping_button.setFixedSize(50, 28)
        
        grouping_layout.addWidget(self.overview_grouping_label)
        grouping_layout.addStretch()
        grouping_layout.addWidget(self.overview_view_grouping_button)
        
        self.overview_table.setCellWidget(3, 1, grouping_cell_widget)
        
        # Căn giữa cho các item ở cột giá trị
        for row in range(3):
             if self.overview_table.item(row, 1):
                self.overview_table.item(row, 1).setTextAlignment(Qt.AlignCenter)

        return overview_group
