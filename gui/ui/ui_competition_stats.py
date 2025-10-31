# file: gui/ui/ui_competition_stats.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QListWidget, QTableWidget, QStackedWidget,
    QHeaderView, QAbstractItemView, QGridLayout
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt
from utils.resource_path import resource_path

# 1. Import scaler để sử dụng các hàm tính toán tỷ lệ
from utils.scaler import scaler

class CompetitionStatsGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("CompetitionStatsWidget")
        # 2. Sử dụng f-string và scaler để tạo stylesheet động
        self.setStyleSheet(f"""
            #CompetitionStatsWidget {{ background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }}
            QLabel#title {{ font-size: {scaler.scale(20)}px; font-weight: bold; color: #ecf0f1; padding: {scaler.scale(10)}px; }}
            QGroupBox {{ font-size: {scaler.scale(16)}px; font-weight: bold; border: 1px solid #4a6278; border-radius: {scaler.scale(8)}px; margin-top: {scaler.scale(10)}px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: {scaler.scale(2)}px {scaler.scale(12)}px; background-color: #415a72; border-radius: {scaler.scale(4)}px; }}
            QPushButton {{ background-color: #95a5a6; color: white; font-size: {scaler.scale(14)}px; font-weight: bold; border: none; padding: {scaler.scale(10)}px {scaler.scale(20)}px; border-radius: {scaler.scale(8)}px; }}
            QPushButton:hover {{ background-color: #7f8c8d; }}
            QPushButton#danger_button {{ background-color: #e74c3c; }}
            QPushButton#danger_button:hover {{ background-color: #c0392b; }}
            QPushButton:disabled {{ background-color: #566573; color: #95a5a6; }}
            QListWidget {{ background-color: #2c3e50; border: 1px solid #4a6278; border-radius: {scaler.scale(8)}px; padding: {scaler.scale(5)}px; }}
            QListWidget::item {{ border-bottom: 1px solid #4a6278; }}
            QListWidget::item:selected {{ background-color: #1abc9c; border-radius: {scaler.scale(6)}px; }}
            QTableWidget {{ background-color: #34495e; border: 1px solid #4a6278; gridline-color: #4a6278; font-size: {scaler.scale(14)}px; }}
            QHeaderView::section {{ background-color: #415a72; color: white; padding: {scaler.scale(8)}px; font-weight: bold; border: none; }}
            QTableWidget::item {{ padding: {scaler.scale(8)}px; border-bottom: 1px solid #4a6278; }}
            QLabel.message-label {{ font-size: {scaler.scale(16)}px; color: #95a5a6; }}
        """)
        self.setupUi()

    def setupUi(self):
        # 3. Sử dụng scaler để tính toán lề và khoảng cách
        margin = scaler.scale(20)
        spacing = scaler.scale(15)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(margin, scaler.scale(10), margin, margin)
        root_layout.setSpacing(spacing)

        title_label = QLabel("THỐNG KÊ KẾT QUẢ KIỂM TRA")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        # 4. Sử dụng scaler.font() để tạo font động cho tiêu đề
        title_label.setFont(scaler.font(20, bold=True))
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(scaler.scale(20))
        root_layout.addLayout(columns_layout, 1)

        columns_layout.addWidget(self._create_left_column(), 25)
        columns_layout.addWidget(self._create_center_column(), 45)
        columns_layout.addWidget(self._create_right_column(), 30)
        
        bottom_layout = QHBoxLayout()
        self.delete_button = QPushButton("Xóa Phiên đã chọn")
        self.delete_button.setObjectName("danger_button")
        bottom_layout.addWidget(self.delete_button)
        bottom_layout.addStretch(1)
        self.back_button = QPushButton("Về Menu Kiểm tra")
        bottom_layout.addWidget(self.back_button)
        root_layout.addLayout(bottom_layout)

    def _create_left_column(self) -> QWidget:
        panel = QGroupBox("Phiên đã Hoàn thành")
        layout = QVBoxLayout(panel)
        margin = scaler.scale(15)
        layout.setContentsMargins(margin, scaler.scale(25), margin, margin)
        self.completed_list = QListWidget()
        self.completed_list.setSpacing(scaler.scale(5))
        layout.addWidget(self.completed_list)
        return panel

    def _create_center_column(self) -> QWidget:
        panel = QGroupBox("Bảng Xếp hạng")
        layout = QVBoxLayout(panel)
        margin = scaler.scale(15)
        layout.setContentsMargins(margin, scaler.scale(25), margin, margin)
        
        self.center_stack = QStackedWidget()
        layout.addWidget(self.center_stack)

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
        margin = scaler.scale(15)
        layout.setContentsMargins(margin, scaler.scale(25), margin, margin)

        self.right_stack = QStackedWidget()
        layout.addWidget(self.right_stack)
        
        details_page = QWidget()
        details_layout = QVBoxLayout(details_page)
        details_layout.setContentsMargins(0,0,0,0)
        
        self.shooter_name_label = QLabel("Tên: --")
        # 5. Scale font cho label tên người bắn
        self.shooter_name_label.setStyleSheet(f"font-size: {scaler.scale(15)}px; font-weight: bold;")
        
        self.target_details_grid = QGridLayout()
        
        details_layout.addWidget(self.shooter_name_label)
        details_layout.addLayout(self.target_details_grid, 1)

        message_page = QWidget()
        message_layout = QVBoxLayout(message_page)
        message_label = QLabel("◀ Vui lòng chọn một người bắn từ bảng xếp hạng")
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setProperty("class", "message-label")
        message_layout.addWidget(message_label)
        
        self.right_stack.addWidget(message_page)
        self.right_stack.addWidget(details_page)

        return panel