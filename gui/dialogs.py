# file: gui/dialogs.py
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDialogButtonBox, QLineEdit, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QMessageBox, QFrame, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor, QFont, QIcon
from utils.resource_path import resource_path

# --- [MỚI] BỘ HÀM HELPER HỘP THOẠI CÓ ICON APP ---
def _create_msg_box(parent, title, text, icon_type):
    """Hàm nội bộ tạo QMessageBox chuẩn với icon ứng dụng."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(icon_type)
    
    # Thiết lập Icon cho cửa sổ thông báo từ file .ico
    app_icon_path = resource_path("assets/app_icon.ico")
    if os.path.exists(app_icon_path):
        msg.setWindowIcon(QIcon(app_icon_path))
    
    return msg

def show_info(parent, title, text):
    msg = _create_msg_box(parent, title, text, QMessageBox.Information)
    msg.exec()

def show_warning(parent, title, text):
    msg = _create_msg_box(parent, title, text, QMessageBox.Warning)
    msg.exec()

def show_error(parent, title, text):
    msg = _create_msg_box(parent, title, text, QMessageBox.Critical)
    msg.exec()

def show_confirmation(parent, title, text):
    """Trả về True nếu chọn Yes, False nếu chọn No."""
    msg = _create_msg_box(parent, title, text, QMessageBox.Question)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.No)
    return msg.exec() == QMessageBox.Yes

def show_confirmation_custom(parent, title, text, btn_yes_text, btn_no_text, btn_cancel_text=None):
    """Hộp thoại xác nhận tùy chỉnh nút bấm."""
    msg = _create_msg_box(parent, title, text, QMessageBox.Question)
    
    btn_yes = msg.addButton(btn_yes_text, QMessageBox.AcceptRole)
    btn_no = msg.addButton(btn_no_text, QMessageBox.RejectRole)
    btn_cancel = None
    if btn_cancel_text:
        btn_cancel = msg.addButton(btn_cancel_text, QMessageBox.DestructiveRole)
        
    msg.exec()
    
    clicked = msg.clickedButton()
    if clicked == btn_yes: return "YES"
    if clicked == btn_no: return "NO"
    if clicked == btn_cancel: return "CANCEL"
    return None
# -------------------------------------------------

class ResultPopup(QDialog):
    def __init__(self, shots_data, camera_name="", allow_retry=True, parent=None):
        super().__init__(parent)
        
        # --- SCALING ---
        screen = QApplication.primaryScreen().availableGeometry()
        self.scale_factor = screen.height() / 1080.0
        def s(val): return int(val * self.scale_factor)
        # ---------------

        self.setWindowTitle("KẾT QUẢ LUYỆN TẬP")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(s(700), s(650))
        self.setStyleSheet(f"background-color: #2c3e50; color: white; font-size: {s(14)}px;")
        
        # Set Icon App cho Popup
        app_icon_path = resource_path("assets/app_icon.ico")
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))
        
        self.shots_data = shots_data
        self.current_idx = 0
        layout = QVBoxLayout(self)
        
        if camera_name:
            self.lbl_cam = QLabel(camera_name)
            self.lbl_cam.setStyleSheet(f"font-size: {s(20)}px; font-weight: bold; color: #3498db; margin-top: 5px;")
            self.lbl_cam.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.lbl_cam)
            
        total_score = sum(s['score'] for s in self.shots_data)
        if total_score < 15: rank = "KHÔNG ĐẠT"; color = "#95a5a6"
        elif 15 <= total_score <= 18: rank = "ĐẠT"; color = "#f39c12"
        elif 19 <= total_score <= 23: rank = "KHÁ"; color = "#3498db"
        else: rank = "GIỎI"; color = "#2ecc71"
        
        header_layout = QHBoxLayout()
        self.lbl_score = QLabel(f"TỔNG ĐIỂM: {total_score}/30")
        self.lbl_score.setStyleSheet(f"font-size: {s(24)}px; font-weight: bold; color: #ecf0f1;")
        self.lbl_rank = QLabel(rank)
        self.lbl_rank.setStyleSheet(f"font-size: {s(32)}px; font-weight: bold; color: {color};")
        header_layout.addWidget(self.lbl_score); header_layout.addStretch(); header_layout.addWidget(self.lbl_rank)
        layout.addLayout(header_layout)
        
        self.img_label = QLabel(); self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("background-color: #212f3d; border: 2px solid #bdc3c7; border-radius: 5px;")
        self.img_label.setMinimumSize(s(600), s(400))
        layout.addWidget(self.img_label, 1)
        
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<< Trước"); self.btn_prev.setMinimumHeight(s(40)); self.btn_prev.clicked.connect(self.prev_image)
        self.lbl_index = QLabel("1/3"); self.lbl_index.setAlignment(Qt.AlignCenter); self.lbl_index.setStyleSheet(f"font-size: {s(16)}px; font-weight: bold;")
        self.btn_next = QPushButton("Sau >>"); self.btn_next.setMinimumHeight(s(40)); self.btn_next.clicked.connect(self.next_image)
        
        btn_style = f"font-size: {s(14)}px; padding: {s(5)}px; background-color: #1abc9c; border-radius: 5px;"
        self.btn_prev.setStyleSheet(btn_style); self.btn_next.setStyleSheet(btn_style)
        
        nav_layout.addWidget(self.btn_prev); nav_layout.addWidget(self.lbl_index); nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)
        
        action_layout = QHBoxLayout()
        self.btn_retry = QPushButton("BẮN LẠI LOẠT NÀY")
        self.btn_retry.setStyleSheet(f"background-color: #e74c3c; font-size: {s(16)}px; padding: {s(10)}px; font-weight: bold; border-radius: 5px; color: white;")
        self.btn_retry.clicked.connect(self.on_retry_clicked)
        self.btn_retry.setVisible(allow_retry)
        
        self.btn_continue = QPushButton("TIẾP TỤC"); 
        self.btn_continue.setStyleSheet(f"background-color: #1abc9c; font-size: {s(16)}px; padding: {s(10)}px; font-weight: bold; border-radius: 5px; color: white;")
        self.btn_continue.clicked.connect(self.accept)
        
        action_layout.addWidget(self.btn_retry)
        action_layout.addSpacing(s(20))
        action_layout.addWidget(self.btn_continue)
        layout.addLayout(action_layout)
        self.update_view()

    def on_retry_clicked(self): self.done(2) 
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
        
        screen = QApplication.primaryScreen().availableGeometry()
        self.scale_factor = screen.height() / 1080.0
        def s(val): return int(val * self.scale_factor)

        self.setWindowTitle(f"QUẢN LÝ PHIÊN: {session_name.upper()}")
        self.setMinimumSize(s(950), s(500))
        self.setStyleSheet(f"background-color: #2c3e50; color: white; font-size: {s(14)}px;")
        
        # Set Icon App
        app_icon_path = resource_path("assets/app_icon.ico")
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))
        
        self.mode_str = mode_str
        layout = QVBoxLayout(self)
        lbl_title = QLabel(f"DANH SÁCH NGƯỜI TẬP - {session_name}")
        lbl_title.setStyleSheet(f"font-size: {s(20)}px; font-weight: bold; color: #1abc9c; margin-bottom: 10px;")
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
        
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: #34495e; border: 1px solid #7f8c8d; font-size: {s(14)}px; }} 
            QHeaderView::section {{ background-color: #2c3e50; color: #bdc3c7; padding: {s(8)}px; border: 1px solid #7f8c8d; font-weight: bold; font-size: {s(14)}px; }} 
            QTableWidget::item:selected {{ background-color: #1abc9c; color: white; }}
        """)
        
        self.soldiers_data = soldiers_data
        self.populate_table(current_ids, mode_str)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("CHỌN NGƯỜI NÀY")
        self.btn_select.setStyleSheet(f"background-color: #3498db; font-weight: bold; padding: {s(12)}px; font-size: {s(14)}px; border-radius: 6px;")
        self.btn_select.clicked.connect(self.on_select)
        
        self.btn_close = QPushButton("ĐÓNG")
        self.btn_close.setStyleSheet(f"background-color: #95a5a6; font-weight: bold; padding: {s(12)}px; font-size: {s(14)}px; border-radius: 6px;")
        self.btn_close.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_select); btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def populate_table(self, current_ids, mode_str):
        for row, s in enumerate(self.soldiers_data):
            name_item = QTableWidgetItem(s['name'])
            class_item = QTableWidgetItem(s.get('class_name', ''))
            is_active = (s['id'] in current_ids)
            is_finished = s.get('finished', False)
            shot_count = s.get('shot_count', 0)
            status_str = "Đang chờ"; bg_color = None
            if is_active: status_str = "ĐANG TẬP"; bg_color = QColor("#d35400") 
            elif is_finished or shot_count > 0: status_str = "ĐÃ TẬP"; bg_color = QColor("#27ae60") 
            status_item = QTableWidgetItem(status_str); status_item.setTextAlignment(Qt.AlignCenter)
            if bg_color: status_item.setBackground(bg_color); status_item.setForeground(QColor("white"))
            res_text = s.get('last_result', '')
            result_item = QTableWidgetItem(res_text); result_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, name_item); self.table.setItem(row, 1, class_item); self.table.setItem(row, 2, status_item); self.table.setItem(row, 3, result_item)
            name_item.setData(Qt.UserRole, s)
            if is_active: self.table.selectRow(row)

    def on_select(self):
        selected_rows = self.table.selectedItems()
        if selected_rows:
            soldier_data = selected_rows[0].data(Qt.UserRole)
            # Dùng show_warning thay vì QMessageBox trực tiếp
            if self.mode_str == "BURST_3" and soldier_data.get('finished', False):
                show_warning(self, "Không thể chọn", f"Người tập {soldier_data['name']} đã hoàn thành bài bắn loạt.\nKhông thể chọn lại.")
                return
            self.trainee_selected.emit(soldier_data)
            self.accept()
        else: 
            show_warning(self, "Chưa chọn", "Vui lòng chọn một người tập từ danh sách.")

class PersonalProcessDialog(QDialog):
    def __init__(self, soldier_info, shots_data, parent=None):
        super().__init__(parent)
        
        screen = QApplication.primaryScreen().availableGeometry()
        self.scale_factor = screen.height() / 1080.0
        def s(val): return int(val * self.scale_factor)

        self.setWindowTitle(f"QUẢN LÝ: {soldier_info['name'].upper()}")
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(s(900), s(700))
        self.setStyleSheet(f"background-color: #2c3e50; color: white; font-size: {s(14)}px;")
        
        # Set Icon App
        app_icon_path = resource_path("assets/app_icon.ico")
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))
        
        self.shots_data = shots_data
        self.current_idx = 0
        
        layout = QVBoxLayout(self)
        
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #34495e; border-radius: 8px;")
        info_layout = QHBoxLayout(info_frame)
        
        lbl_name = QLabel(f"Họ tên: <b>{soldier_info['name']}</b>")
        lbl_class = QLabel(f"Đơn vị: <b>{soldier_info.get('class_name','')}</b>")
        total_score = sum(s.get('score', 0) for s in shots_data)
        count = len(shots_data)
        lbl_summary = QLabel(f"Tổng: <b>{count} phát</b> - Điểm: <b style='color:#f1c40f; font-size:{s(16)}px;'>{total_score}</b>")
        
        for lbl in [lbl_name, lbl_class, lbl_summary]:
            lbl.setStyleSheet(f"font-size: {s(16)}px; padding: 5px;")
            info_layout.addWidget(lbl)
        layout.addWidget(info_frame)
        
        layout.addSpacing(10)

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("background-color: #212f3d; border: 2px solid #7f8c8d; border-radius: 5px;")
        self.img_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.img_label, 1)

        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<< Phát trước")
        self.btn_prev.setMinimumHeight(s(50))
        self.btn_prev.setStyleSheet(f"background-color: #3498db; font-weight: bold; border-radius: 5px; font-size: {s(14)}px;")
        self.btn_prev.clicked.connect(self.prev_shot)
        
        self.lbl_shot_info = QLabel("...")
        self.lbl_shot_info.setAlignment(Qt.AlignCenter)
        self.lbl_shot_info.setStyleSheet(f"font-size: {s(18)}px; font-weight: bold; color: #ecf0f1; min-width: {s(200)}px;")
        
        self.btn_next = QPushButton("Phát sau >>")
        self.btn_next.setMinimumHeight(s(50))
        self.btn_next.setStyleSheet(f"background-color: #3498db; font-weight: bold; border-radius: 5px; font-size: {s(14)}px;")
        self.btn_next.clicked.connect(self.next_shot)
        
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_shot_info)
        nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)
        
        btn_close = QPushButton("Đóng")
        btn_close.setMinimumHeight(s(40))
        btn_close.setStyleSheet(f"background-color: #95a5a6; border-radius: 5px; font-size: {s(14)}px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        if not self.shots_data:
            self.img_label.setText("Chưa có dữ liệu bắn nào.")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
        else:
            self.update_view()

    def update_view(self):
        if not self.shots_data: return
        data = self.shots_data[self.current_idx]
        
        img_path = data.get('image_path')
        pix = QPixmap()
        if img_path and os.path.exists(img_path):
            pix = QPixmap(img_path)
        
        if not pix.isNull():
            self.img_label.setPixmap(pix.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.img_label.setText(f"Không tìm thấy ảnh: {os.path.basename(img_path) if img_path else 'N/A'}")
            
        score = data.get('score', 0)
        result_text = "TRÚNG" if score > 0 else "TRƯỢT"
        
        info_str = f"Phát thứ {data.get('shot_number', self.current_idx + 1)}/{len(self.shots_data)}\n"
        info_str += f"Điểm: {score} ({result_text})"
        self.lbl_shot_info.setText(info_str)
        
        self.btn_prev.setEnabled(self.current_idx > 0)
        self.btn_next.setEnabled(self.current_idx < len(self.shots_data) - 1)

    def prev_shot(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.update_view()

    def next_shot(self):
        if self.current_idx < len(self.shots_data) - 1:
            self.current_idx += 1
            self.update_view()
            
    def resizeEvent(self, event):
        self.update_view()
        super().resizeEvent(event)