# file: gui/ui/ui_competition_stats.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QTableWidget, QStackedWidget,
    QHeaderView, QAbstractItemView, QGridLayout
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt
from utils.resource_path import resource_path

class CompetitionStatsGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("CompetitionStatsWidget")
        self.setStyleSheet("""
            #CompetitionStatsWidget { background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }
            QLabel#title { font-size: 20px; font-weight: bold; color: #ecf0f1; padding: 10px; }
            QGroupBox { font-size: 16px; font-weight: bold; border: 1px solid #4a6278; border-radius: 8px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 2px 12px; background-color: #415a72; border-radius: 4px; }
            QPushButton { background-color: #e74c3c; color: white; font-size: 14px; font-weight: bold; border: none; padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background-color: #c0392b; }
            QListWidget { background-color: #2c3e50; border: 1px solid #4a6278; border-radius: 8px; padding: 5px; }
            QListWidget::item { border-bottom: 1px solid #4a6278; }
            QListWidget::item:selected { background-color: #1abc9c; border-radius: 6px; }
            QTableWidget { background-color: #34495e; border: 1px solid #4a6278; gridline-color: #4a6278; font-size: 14px; }
            QHeaderView::section { background-color: #415a72; color: white; padding: 8px; font-weight: bold; border: none; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #4a6278; }
            QLabel.message-label { font-size: 16px; color: #95a5a6; }
        """)
        self.setupUi()

    def setupUi(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 10, 20, 20)
        root_layout.setSpacing(15)

        title_label = QLabel("THỐNG KÊ KẾT QUẢ KIỂM TRA")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        root_layout.addLayout(columns_layout, 1)

        columns_layout.addWidget(self._create_left_column(), 25)
        columns_layout.addWidget(self._create_center_column(), 45)
        columns_layout.addWidget(self._create_right_column(), 30)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        self.back_button = QPushButton("Về Menu Kiểm tra")
        bottom_layout.addWidget(self.back_button)
        root_layout.addLayout(bottom_layout)

    def _create_left_column(self) -> QWidget:
        panel = QGroupBox("Phiên đã Hoàn thành")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 25, 15, 15)
        self.completed_list = QListWidget()
        self.completed_list.setSpacing(5)
        layout.addWidget(self.completed_list)
        return panel

    def _create_center_column(self) -> QWidget:
        panel = QGroupBox("Bảng Xếp hạng")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 25, 15, 15)
        
        self.center_stack = QStackedWidget()
        layout.addWidget(self.center_stack)

        # Trang hiển thị bảng
        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)
        table_layout.setContentsMargins(0,0,0,0)
        self.ranking_table = QTableWidget()
        self.ranking_table.setColumnCount(4)
        self.ranking_table.setHorizontalHeaderLabels(["Hạng", "Tên Người bắn", "Đơn vị", "Tổng Điểm"])
        self.ranking_table.verticalHeader().setVisible(False)
        self.ranking_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ranking_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ranking_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ranking_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ranking_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table_layout.addWidget(self.ranking_table)
        
        # Trang hiển thị thông báo
        message_page = QWidget()
        message_layout = QVBoxLayout(message_page)
        message_label = QLabel("◀ Vui lòng chọn một phiên kiểm tra để xem kết quả")
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setProperty("class", "message-label")
        message_layout.addWidget(message_label)
        
        self.center_stack.addWidget(message_page)
        self.center_stack.addWidget(table_page)
        
        return panel

    def _create_right_column(self) -> QWidget:
        panel = QGroupBox("Chi tiết Người bắn")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 25, 15, 15)

        self.right_stack = QStackedWidget()
        layout.addWidget(self.right_stack)
        
        # Trang hiển thị chi tiết
        details_page = QWidget()
        details_layout = QVBoxLayout(details_page)
        details_layout.setContentsMargins(0,0,0,0)
        
        self.shooter_name_label = QLabel("Tên: --")
        self.shooter_name_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        
        self.target_details_grid = QGridLayout()
        # Nội dung chi tiết sẽ được thêm vào đây bằng code
        
        details_layout.addWidget(self.shooter_name_label)
        details_layout.addLayout(self.target_details_grid, 1)

        # Trang hiển thị thông báo
        message_page = QWidget()
        message_layout = QVBoxLayout(message_page)
        message_label = QLabel("◀ Vui lòng chọn một người bắn từ bảng xếp hạng")
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setProperty("class", "message-label")
        message_layout.addWidget(message_label)
        
        self.right_stack.addWidget(message_page)
        self.right_stack.addWidget(details_page)

        return panel