# file: gui/dialogs.py
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDialogButtonBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor

class ResultPopup(QDialog):
    def __init__(self, shots_data, camera_name="", allow_retry=True, parent=None):
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
        header_layout.addWidget(self.lbl_score); header_layout.addStretch(); header_layout.addWidget(self.lbl_rank)
        layout.addLayout(header_layout)
        self.img_label = QLabel(); self.img_label.setAlignment(Qt.AlignCenter); self.img_label.setStyleSheet("background-color: #212f3d; border: 2px solid #bdc3c7; border-radius: 5px;")
        self.img_label.setMinimumSize(600, 400); layout.addWidget(self.img_label, 1)
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<< Trước"); self.btn_prev.setMinimumHeight(40); self.btn_prev.clicked.connect(self.prev_image)
        self.lbl_index = QLabel("1/3"); self.lbl_index.setAlignment(Qt.AlignCenter); self.lbl_index.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.btn_next = QPushButton("Sau >>"); self.btn_next.setMinimumHeight(40); self.btn_next.clicked.connect(self.next_image)
        nav_layout.addWidget(self.btn_prev); nav_layout.addWidget(self.lbl_index); nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)
        
        # --- Action Buttons ---
        action_layout = QHBoxLayout()
        
        self.btn_retry = QPushButton("BẮN LẠI LOẠT NÀY")
        self.btn_retry.setStyleSheet("background-color: #e74c3c; font-size: 16px; padding: 10px; font-weight: bold; border-radius: 5px; color: white;")
        self.btn_retry.clicked.connect(self.on_retry_clicked)
        
        # Chỉ hiện nút Bắn lại nếu được phép (Chế độ Managed)
        self.btn_retry.setVisible(allow_retry)
        
        self.btn_continue = QPushButton("TIẾP TỤC"); 
        self.btn_continue.setStyleSheet("background-color: #1abc9c; font-size: 16px; padding: 10px; font-weight: bold; border-radius: 5px; color: white;")
        self.btn_continue.clicked.connect(self.accept)
        
        action_layout.addWidget(self.btn_retry)
        action_layout.addSpacing(20)
        action_layout.addWidget(self.btn_continue)
        layout.addLayout(action_layout)
        
        self.update_view()

    def on_retry_clicked(self):
        self.done(2) 

    def update_view(self):
        if not self.shots_data: return
        data = self.shots_data[self.current_idx]
        pix = data.get('image')
        if isinstance(pix, str) and os.path.exists(pix): pix = QPixmap(pix)
        elif not isinstance(pix, QPixmap): pix = QPixmap()
        if not pix.isNull(): self.img_label.setPixmap(pix.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else: self.img_label.setText("Lỗi: Không hiển thị được ảnh")
        self.lbl_index.setText(f"Phát {self.current_idx + 1}/{len(self.shots_data)}  -  Điểm: {data['score']}")
        self.btn_prev.setEnabled(self.current_idx > 0); self.btn_next.setEnabled(self.current_idx < len(self.shots_data) - 1)
    def prev_image(self):
        if self.current_idx > 0: self.current_idx -= 1; self.update_view()
    def next_image(self):
        if self.current_idx < len(self.shots_data) - 1: self.current_idx += 1; self.update_view()
    def resizeEvent(self, event): self.update_view(); super().resizeEvent(event)

class TraineeSessionPopup(QDialog):
    trainee_selected = Signal(dict)

    def __init__(self, session_name, soldiers_data, current_ids, mode_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"QUẢN LÝ PHIÊN: {session_name.upper()}")
        self.setMinimumSize(950, 500)
        self.setStyleSheet("background-color: #2c3e50; color: white;")
        self.mode_str = mode_str
        
        layout = QVBoxLayout(self)
        
        lbl_title = QLabel(f"DANH SÁCH NGƯỜI TẬP - {session_name}")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1abc9c; margin-bottom: 10px;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        result_header = "Số phát / Điểm (Trung bình)" if mode_str == "SINGLE" else "Kết quả loạt"
        
        self.table = QTableWidget(len(soldiers_data), 4)
        self.table.setHorizontalHeaderLabels(["Họ và Tên", "Đơn vị", "Trạng thái", result_header])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #34495e; border: 1px solid #7f8c8d; font-size: 14px; }
            QHeaderView::section { background-color: #2c3e50; color: #bdc3c7; padding: 8px; border: 1px solid #7f8c8d; font-weight: bold; }
            QTableWidget::item:selected { background-color: #1abc9c; color: white; }
        """)
        
        self.soldiers_data = soldiers_data
        self.populate_table(current_ids, mode_str)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("CHỌN NGƯỜI NÀY")
        self.btn_select.setStyleSheet("background-color: #3498db; font-weight: bold; padding: 12px; font-size: 14px; border-radius: 6px;")
        self.btn_select.clicked.connect(self.on_select)
        
        self.btn_close = QPushButton("ĐÓNG")
        self.btn_close.setStyleSheet("background-color: #95a5a6; font-weight: bold; padding: 12px; font-size: 14px; border-radius: 6px;")
        self.btn_close.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_select)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def populate_table(self, current_ids, mode_str):
        for row, s in enumerate(self.soldiers_data):
            name_item = QTableWidgetItem(s['name'])
            class_item = QTableWidgetItem(s.get('class_name', ''))
            
            is_active = (s['id'] in current_ids)
            is_finished = s.get('finished', False)
            shot_count = s.get('shot_count', 0)
            
            status_str = "Đang chờ"
            bg_color = None
            
            if is_active:
                status_str = "ĐANG TẬP"
                bg_color = QColor("#d35400") # Cam
            elif is_finished or shot_count > 0:
                status_str = "ĐÃ TẬP"
                bg_color = QColor("#27ae60") # Xanh lá
            
            status_item = QTableWidgetItem(status_str)
            status_item.setTextAlignment(Qt.AlignCenter)
            if bg_color: 
                status_item.setBackground(bg_color)
                status_item.setForeground(QColor("white"))
            
            res_text = s.get('last_result', '')
            result_item = QTableWidgetItem(res_text)
            result_item.setTextAlignment(Qt.AlignCenter)
            
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, class_item)
            self.table.setItem(row, 2, status_item)
            self.table.setItem(row, 3, result_item)
            
            name_item.setData(Qt.UserRole, s)
            
            if is_active:
                self.table.selectRow(row)

    def on_select(self):
        selected_rows = self.table.selectedItems()
        if selected_rows:
            soldier_data = selected_rows[0].data(Qt.UserRole)
            if self.mode_str == "BURST_3" and soldier_data.get('finished', False):
                QMessageBox.warning(self, "Không thể chọn", 
                                    f"Chiến sĩ {soldier_data['name']} đã hoàn thành bài bắn loạt.\nKhông thể chọn lại.")
                return
            self.trainee_selected.emit(soldier_data)
            self.accept()
        else:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một người tập từ danh sách.")