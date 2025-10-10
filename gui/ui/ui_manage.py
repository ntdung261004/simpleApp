# gui/ui/ui_manage.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QFrame, QSizePolicy, QAbstractItemView, QHeaderView , QListWidget, QStackedWidget
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
    # --- BẮT ĐẦU THAY ĐỔI ---
    def __init__(self, image_height: int): # << Nhận tham số chiều cao
        super().__init__()
        self.image_height = image_height # << Lưu lại chiều cao
    # --- KẾT THÚC THAY ĐỔI ---

        # ===== Style đồng bộ =====
        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI';
            }
            QFrame#panel {
                background-color: #34495e; border-radius: 12px; border: 1px solid #4a6278;
            }
            QLabel#title {
                color: #ecf0f1; padding: 10px;
            }
            QLabel.panel-title {
                font-size: 16px; font-weight: bold; color: #ecf0f1;
            }
            QPushButton {
                background-color: #1abc9c; color: white; font-size: 14px;
                font-weight: bold; border: none; padding: 8px 18px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #16a085; }
            QPushButton#danger { background-color: #e74c3c; }
            QPushButton#danger:hover { background-color: #c0392b; }
            QGroupBox {
                font-size: 14px; font-weight: bold; border: 1px solid #4a6278;
                border-radius: 8px; margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center;
                padding: 2px 8px; background-color: #415a72; border-radius: 4px;
            }
            QListWidget, QTableWidget {
                background-color: #2c3e50; border: 1px solid #4a6278; border-radius: 6px;
                gridline-color: #4a6278;
            }
            QLabel#resultImage {
                background-color: #212f3d; border: 1px solid #4a6278;
                border-radius: 8px; color: #95a5a6; font-size: 18px;
            }
            QHeaderView::section {
                background-color: #415a72; color: #ecf0f1;
                padding: 4px; border: 1px solid #4a6278;
            }
        """)

        # ===== Root layout =====
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 10, 20, 20)
        root_layout.setSpacing(15)

        title_label = QLabel("QUẢN LÝ DANH SÁCH CHIẾN SĨ VÀ THỐNG KÊ KẾT QUẢ BẮN")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont('Segoe UI', 18, QFont.Bold)
        title_label.setFont(title_font)
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        root_layout.addLayout(columns_layout)

        columns_layout.addWidget(self._create_left_column(), 25)
        columns_layout.addWidget(self._create_center_column(), 50)
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

        self.soldier_table = QTableWidget()
        self.soldier_table.setColumnCount(2)
        self.soldier_table.setHorizontalHeaderLabels(["Họ và Tên", "Đơn vị"])
        self.soldier_table.verticalHeader().setVisible(False)
        self.soldier_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.soldier_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.soldier_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
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
        
        self.center_stack = QStackedWidget()
        layout.addWidget(self.center_stack)

        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(15, 15, 15, 15)
        data_layout.setSpacing(15)

        analysis_box = QGroupBox("Phân tích Phiên bắn được chọn")
        analysis_layout = QVBoxLayout(analysis_box)

        self.analysis_summary_label = QLabel("Tổng phát bắn: --  |  Tỷ lệ trúng: --  |  Điểm trung bình: --")
        self.analysis_summary_label.setFont(QFont("Segoe UI", 10))
        self.analysis_summary_label.setAlignment(Qt.AlignCenter)
        analysis_layout.addWidget(self.analysis_summary_label)

        self.analysis_target_table = QTableWidget(3, 4)
        self.analysis_target_table.setHorizontalHeaderLabels(["Loại bia", "Số phát trúng", "Tổng điểm", "Độ chụm"])
        self.analysis_target_table.verticalHeader().setVisible(False)
        self.analysis_target_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.analysis_target_table.setFocusPolicy(Qt.NoFocus)
        self.analysis_target_table.setSelectionMode(QAbstractItemView.NoSelection)

        header = self.analysis_target_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        target_names = ["Bia số 4", "Bia số 7", "Bia số 8"]
        self.analysis_widgets = {}
        self.analysis_view_buttons = {}
        for row, name in enumerate(target_names):
            name_item = QTableWidgetItem(name)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.analysis_target_table.setItem(row, 0, name_item)
            
            for col in range(1, 3): 
                item = QTableWidgetItem("--")
                item.setTextAlignment(Qt.AlignCenter)
                self.analysis_target_table.setItem(row, col, item)

            view_button = QPushButton("Xem")
            view_button.setStyleSheet("padding: 4px 8px; font-size: 9px;")
            target_key = ['bia_so_4', 'bia_so_7_8', 'bia_so_8'][row]
            self.analysis_view_buttons[target_key] = view_button
            
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0,0,0,0)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(view_button)
            self.analysis_target_table.setCellWidget(row, 3, cell_widget)
        
        analysis_layout.addWidget(self.analysis_target_table)
        data_layout.addWidget(analysis_box, 1)

        detail_box = QGroupBox("Thông tin chi tiết từng phát bắn")
        detail_layout = QVBoxLayout(detail_box)

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

        detail_layout.addWidget(self.shot_table, 1)
        
        image_container = QWidget()
        
        # --- BẮT ĐẦU THAY ĐỔI ---
        # Sử dụng chiều cao đã được truyền vào
        image_container.setFixedHeight(self.image_height)
        # --- KẾT THÚC THAY ĐỔI ---
        
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.result_image = VideoLabel() 
        self.result_image.setObjectName("resultImage")
        image_container_layout.addWidget(self.result_image)

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

        message_widget = QWidget()
        message_layout = QVBoxLayout(message_widget)
        self.center_message_label = QLabel("...")
        self.center_message_label.setAlignment(Qt.AlignCenter)
        self.center_message_label.setStyleSheet("font-size: 16px; color: #95a5a6;")
        message_layout.addWidget(self.center_message_label)
        
        self.center_stack.addWidget(data_widget)
        self.center_stack.addWidget(message_widget)

        return panel

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.right_stack = QStackedWidget()
        layout.addWidget(self.right_stack)
        
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(15, 15, 15, 15)
        data_layout.setSpacing(15)

        history_box = QGroupBox("Lịch sử bắn của Chiến sĩ được chọn")
        history_layout = QVBoxLayout(history_box)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        data_layout.addWidget(history_box)

        message_widget = QWidget()
        message_layout = QVBoxLayout(message_widget)
        self.right_message_label = QLabel("...")
        self.right_message_label.setAlignment(Qt.AlignCenter)
        self.right_message_label.setStyleSheet("font-size: 16px; color: #95a5a6;")
        message_layout.addWidget(self.right_message_label)

        self.right_stack.addWidget(data_widget)
        self.right_stack.addWidget(message_widget)

        return panel
    
    # Hàm _create_overview_panel không còn được sử dụng trực tiếp trong layout chính nữa
    # nhưng vẫn có thể giữ lại nếu bạn có kế hoạch dùng nó ở đâu đó khác.
    def _create_overview_panel(self) -> QGroupBox:
        overview_group = QGroupBox("Tổng quan Phiên tập")
        # ... (logic của hàm này giữ nguyên)
        return overview_group