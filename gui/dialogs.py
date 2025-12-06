# file: gui/dialogs.py
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDialogButtonBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox
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
        pix = data.get('image')
        if isinstance(pix, str) and os.path.exists(pix): pix = QPixmap(pix)
        elif not isinstance(pix, QPixmap): pix = QPixmap()
            
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