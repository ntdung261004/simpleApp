# file: gui/dialogs.py
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, 
    QDialogButtonBox, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

class ResultPopup(QDialog):
    def __init__(self, shots_data, camera_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("KẾT QUẢ LUYỆN TẬP")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(700, 650)
        self.setStyleSheet("background-color: #2c3e50; color: white;")
        
        self.shots_data = shots_data
        self.current_idx = 0
        
        layout = QVBoxLayout(self)
        
        if camera_name:
            self.lbl_cam = QLabel(camera_name)
            self.lbl_cam.setStyleSheet("font-size: 20px; font-weight: bold; color: #3498db; margin-top: 5px;")
            self.lbl_cam.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.lbl_cam)

        total_score = sum(s['score'] for s in self.shots_data)
        if total_score < 15: rank = "KHÔNG ĐẠT"; color = "#95a5a6"
        elif 15 <= total_score <= 18: rank = "ĐẠT"; color = "#f39c12"
        elif 19 <= total_score <= 23: rank = "KHÁ"; color = "#3498db"
        else: rank = "GIỎI"; color = "#2ecc71"

        header_layout = QHBoxLayout()
        self.lbl_score = QLabel(f"TỔNG ĐIỂM: {total_score}/30")
        self.lbl_score.setStyleSheet("font-size: 24px; font-weight: bold; color: #ecf0f1;")
        self.lbl_rank = QLabel(rank)
        self.lbl_rank.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        header_layout.addWidget(self.lbl_score)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_rank)
        layout.addLayout(header_layout)
        
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("background-color: #212f3d; border: 2px solid #bdc3c7; border-radius: 5px;")
        self.img_label.setMinimumSize(600, 400)
        layout.addWidget(self.img_label, 1)
        
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<< Trước"); self.btn_prev.setMinimumHeight(40)
        self.btn_prev.clicked.connect(self.prev_image)
        self.lbl_index = QLabel("1/3"); self.lbl_index.setAlignment(Qt.AlignCenter)
        self.lbl_index.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.btn_next = QPushButton("Sau >>"); self.btn_next.setMinimumHeight(40)
        self.btn_next.clicked.connect(self.next_image)
        nav_layout.addWidget(self.btn_prev); nav_layout.addWidget(self.lbl_index); nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)
        
        btn_continue = QPushButton("TIẾP TỤC")
        btn_continue.setStyleSheet("background-color: #1abc9c; font-size: 16px; padding: 10px; font-weight: bold; border-radius: 5px; color: white;")
        btn_continue.clicked.connect(self.accept)
        layout.addWidget(btn_continue)
        
        self.update_view()

    def update_view(self):
        if not self.shots_data: return
        data = self.shots_data[self.current_idx]
        pix = QPixmap()
        if isinstance(data['image'], str) and os.path.exists(data['image']):
            pix = QPixmap(data['image'])
        elif isinstance(data['image'], QPixmap):
            pix = data['image']
            
        if not pix.isNull():
            self.img_label.setPixmap(pix.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else: self.img_label.setText("Lỗi: Không hiển thị được ảnh")
        self.lbl_index.setText(f"Phát {self.current_idx + 1}/{len(self.shots_data)}  -  Điểm: {data['score']}")
        self.btn_prev.setEnabled(self.current_idx > 0)
        self.btn_next.setEnabled(self.current_idx < len(self.shots_data) - 1)

    def prev_image(self):
        if self.current_idx > 0: self.current_idx -= 1; self.update_view()
    def next_image(self):
        if self.current_idx < len(self.shots_data) - 1: self.current_idx += 1; self.update_view()
    def resizeEvent(self, event): self.update_view(); super().resizeEvent(event)


class SelectSoldierDialog(QDialog):
    def __init__(self, soldiers_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn Người Tập")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("QDialog { background-color: #2c3e50; color: white; } QLineEdit { padding: 8px; border-radius: 4px; border: 1px solid #7f8c8d; background: #34495e; color: white; } QTableWidget { background-color: #34495e; gridline-color: #7f8c8d; color: white; border: none; } QHeaderView::section { background-color: #2c3e50; color: white; padding: 4px; border: 1px solid #7f8c8d; } QTableWidget::item:selected { background-color: #1abc9c; color: white; }")
        self.selected_soldier = None; self.soldiers_list = soldiers_list
        layout = QVBoxLayout(self)
        self.search_box = QLineEdit(); self.search_box.setPlaceholderText("🔍 Tìm kiếm tên hoặc đơn vị...")
        self.search_box.textChanged.connect(self.filter_list); layout.addWidget(self.search_box)
        self.table = QTableWidget(); self.table.setColumnCount(2); self.table.setHorizontalHeaderLabels(["Họ Tên", "Đơn vị"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept_selection); layout.addWidget(self.table)
        self.populate_table(self.soldiers_list)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); btn_box.accepted.connect(self.accept_selection); btn_box.rejected.connect(self.reject); layout.addWidget(btn_box)

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for r, s in enumerate(data):
            self.table.setItem(r, 0, QTableWidgetItem(s['name'])); self.table.setItem(r, 1, QTableWidgetItem(s.get('class_name', '')))
            self.table.item(r, 0).setData(Qt.UserRole, s) 

    def filter_list(self):
        text = self.search_box.text().lower()
        for r in range(self.table.rowCount()):
            name = self.table.item(r, 0).text().lower(); unit = self.table.item(r, 1).text().lower()
            self.table.setRowHidden(r, text not in name and text not in unit)

    def accept_selection(self):
        rows = self.table.selectedItems()
        if rows: self.selected_soldier = self.table.item(rows[0].row(), 0).data(Qt.UserRole); self.accept()
        else: QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một người từ danh sách.")