# file: gui/windows/manage_window.py
import logging
import json
import numpy as np
import cv2 
import os 
from PySide6.QtWidgets import (
    QMainWindow, QDialog, QFormLayout, QLineEdit, 
    QDialogButtonBox, QMessageBox, QTableWidgetItem,
    QVBoxLayout, QListWidgetItem, QLabel, QSizePolicy,
    QMenu, QInputDialog
)
from datetime import datetime
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from gui.ui.ui_manage import ManageGui 
from core.database import DatabaseManager
from utils.resource_path import resource_path

# Lớp AddSoldierDialog giữ nguyên
class AddSoldierDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm Người học Mới")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #34495e; }
            QLabel { color: #ecf0f1; font-size: 14px; }
            QLineEdit { background-color: #2c3e50; border: 1px solid #4a6278; border-radius: 6px; padding: 8px; color: #ecf0f1; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #1abc9c; }
            QPushButton { background-color: #1abc9c; color: white; font-size: 14px; font-weight: bold; border: none; padding: 8px 18px; border-radius: 8px; }
            QPushButton:hover { background-color: #16a085; }
            QPushButton[objectName="cancelButton"] { background-color: #95a5a6; }
            QPushButton[objectName="cancelButton"]:hover { background-color: #7f8c8d; }
        """)
        main_layout = QVBoxLayout(self)
        title_label = QLabel("Nhập thông tin Người học")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # === THAY ĐỔI: CẬP NHẬT TRƯỜNG NHẬP LIỆU ===
        self.name_input = QLineEdit()
        self.class_name_input = QLineEdit() # Trường mới
        self.inputs = [self.name_input, self.class_name_input] # Chỉ còn 2 trường
        form_layout.addRow("Họ và Tên:", self.name_input)
        form_layout.addRow("Lớp:", self.class_name_input) # Trường mới
        # ========================================

        main_layout.addLayout(form_layout)
        buttons = QDialogButtonBox()
        ok_button = buttons.addButton("Hoàn tất", QDialogButtonBox.AcceptRole)
        cancel_button = buttons.addButton("Hủy", QDialogButtonBox.RejectRole)
        cancel_button.setObjectName("cancelButton")
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        self.default_style = "border: 1px solid #4a6278;"
        self.error_style = "border: 2px solid #e74c3c;"

    def get_data(self):
        # === THAY ĐỔI: TRẢ VỀ DỮ LIỆU MỚI ===
        return {
            "name": self.name_input.text().strip(),
            "class_name": self.class_name_input.text().strip()
        }
        # ===================================
        
    def validate_and_accept(self):
        for field in self.inputs:
            field.setStyleSheet(self.default_style)
        data = self.get_data()
        is_valid = True
        # Chỉ cần kiểm tra họ tên là bắt buộc
        if not data["name"]:
            self.inputs[0].setStyleSheet(self.error_style)
            is_valid = False
        
        if is_valid:
            self.accept()
        else:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền Họ và Tên.")
            
class GroupingDisplayDialog(QDialog):
    """Cửa sổ Popup để hiển thị ảnh độ chụm."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trực quan Độ chụm")
        self.setMinimumSize(600, 800) # Kích thước tối thiểu
        self.setStyleSheet("background-color: #34495e;")

        self.layout = QVBoxLayout(self)
        self.image_label = QLabel("Đang tải ảnh...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.layout.addWidget(self.image_label)

    def update_display(self, image_np: np.ndarray):
        """Nhận một ảnh numpy và hiển thị nó."""
        if image_np is None:
            self.image_label.setText("Không có ảnh để hiển thị.")
            return

        try:
            # Chuyển đổi ảnh OpenCV (BGR) sang QPixmap (RGB)
            h, w, ch = image_np.shape
            bytes_per_line = ch * w
            rgb_image = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            # Scale ảnh cho vừa với QLabel mà vẫn giữ tỉ lệ
            scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logging.error(f"Lỗi khi hiển thị ảnh popup: {e}")
            self.image_label.setText("Lỗi khi hiển thị ảnh.")

    def resizeEvent(self, event):
        """Tự động scale lại ảnh khi thay đổi kích thước cửa sổ."""
        super().resizeEvent(event)
        # Re-draw the pixmap when the dialog is resized
        if self.image_label.pixmap():
            # Create a new scaled pixmap from the original (or re-run the drawing logic if needed)
            # For simplicity, we assume update_display will be called again or we scale the existing pixmap
            scaled_pixmap = self.image_label.pixmap().scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            
class ManageWindow(QMainWindow):
    DATA_PAGE = 0
    MESSAGE_PAGE = 1
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quản lý và Thống kê")
        self.ui = ManageGui()
        self.setCentralWidget(self.ui)
        self.db = DatabaseManager()
        
        # Biến trạng thái
        self.current_soldier_id = None
        self.current_session_id = None
        self.current_shots = [] # Lưu danh sách phát bắn của phiên đang chọn
        self.current_shot_index = -1 # Index của phát bắn đang xem
        self.current_shot_coords = {} # Dùng để lưu tọa độ theo loại bia
        self.setup_ui_styles() # Cải thiện giao diện
        self.connect_signals()
        self.set_panels_state("NO_SOLDIER_SELECTED")
        self.ui.soldier_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
    def setup_ui_styles(self):
        """Áp dụng stylesheet để cải thiện giao diện cho các item."""
        self.ui.history_list.setStyleSheet("""
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #4a6278;
            }
            QListWidget::item:selected {
                background-color: #1abc9c;
                color: #2c3e50;
                border-bottom: 1px solid #16a085;
            }
        """)

        # --- BẮT ĐẦU THAY ĐỔI ---
        # Stylesheet cho cả hai bảng để giữ màu khi mất focus
        table_stylesheet = """
            QTableWidget::item:selected {
                background-color: #1abc9c; /* Màu xanh primary */
                color: white; /* Màu chữ khi được chọn */
            }
        """
        self.ui.soldier_table.setStyleSheet(table_stylesheet)
        self.ui.shot_table.setStyleSheet(table_stylesheet)
        # --- KẾT THÚC THAY ĐỔI ---

    def connect_signals(self):
        self.ui.add_button.clicked.connect(self.open_add_soldier_dialog)
        self.ui.soldier_table.itemSelectionChanged.connect(self.on_soldier_selected)
        self.ui.history_list.itemSelectionChanged.connect(self.on_session_selected)
        
        # Kết nối nút điều hướng ảnh
        self.ui.prev_shot_button.clicked.connect(self.show_previous_shot)
        self.ui.next_shot_button.clicked.connect(self.show_next_shot)
        # Kết nối chọn trong bảng chi tiết
        self.ui.shot_table.itemSelectionChanged.connect(self.on_shot_table_selected)
        self.ui.soldier_table.customContextMenuRequested.connect(self.show_soldier_context_menu)
        self.ui.history_list.customContextMenuRequested.connect(self.show_session_context_menu)
                # --- THÊM KẾT NỐI CHO CÁC NÚT "XEM" ---
        for target_key, button in self.ui.analysis_view_buttons.items():
            # Dùng lambda để truyền đúng target_key cho mỗi nút
            button.clicked.connect(lambda checked=False, key=target_key: self.show_grouping_popup(key))

    def show_grouping_popup(self, target_key: str):
        """Hiển thị popup với các điểm bắn được vẽ trên bia gốc."""
        coords = self.current_shot_coords.get(target_key)
        if not coords:
            QMessageBox.information(self, "Thông báo", "Không có dữ liệu điểm bắn cho loại bia này.")
            return

        # Đường dẫn tới thư mục chứa ảnh bia gốc
        asset_path = resource_path("assets/images/original")
        # Ánh xạ key dữ liệu sang tên file ảnh
        target_image_map = {
            'bia_so_4': 'bia_so_4.png',
            'bia_so_7_8': 'bia_so_7.png', # Model gộp 7, 8 nhưng ta dùng ảnh bia 7
            'bia_so_8': 'bia_so_8.png'
        }
        
        image_file = target_image_map.get(target_key)
        if not image_file: return

        image_path = os.path.join(asset_path, image_file)
        if not os.path.exists(image_path):
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy ảnh bia gốc tại:\n{image_path}")
            return
            
        # Đọc ảnh và vẽ các điểm bắn
        target_image = cv2.imread(image_path)
        for (x, y) in coords:
            # Vẽ dấu + màu đỏ
            cv2.drawMarker(target_image, (int(x), int(y)), (0, 0, 255), 
                           markerType=cv2.MARKER_CROSS, markerSize=40, thickness=3)

        # Hiển thị dialog
        dialog = GroupingDisplayDialog(self)
        dialog.update_display(target_image)
        dialog.exec()

    def set_panels_state(self, state: str):
        # ... (Hàm này giữ nguyên như cũ)
        if state == "NO_SOLDIER_SELECTED":
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.right_stack.setCurrentIndex(self.MESSAGE_PAGE)
            msg = "◀ Vui lòng chọn một người học từ danh sách"
            self.ui.center_message_label.setText(msg)
            self.ui.right_message_label.setText(msg)
        elif state == "NO_SESSIONS":
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.right_stack.setCurrentIndex(self.MESSAGE_PAGE)
            msg = "Người học này chưa thực hiện phiên tập nào"
            self.ui.center_message_label.setText(msg)
            self.ui.right_message_label.setText(msg)
        elif state == "SOLDIER_SELECTED":
            self.ui.right_stack.setCurrentIndex(self.DATA_PAGE)
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.center_message_label.setText("▲ Vui lòng chọn một phiên tập để xem chi tiết")
        elif state == "SHOW_DATA":
            self.ui.center_stack.setCurrentIndex(self.DATA_PAGE)
            self.ui.right_stack.setCurrentIndex(self.DATA_PAGE)

    def on_soldier_selected(self):
        # ... (Hàm này giữ nguyên như cũ)
        selected_items = self.ui.soldier_table.selectedItems()
        if not selected_items:
            self.current_soldier_id = None
            self.set_panels_state("NO_SOLDIER_SELECTED")
            return
        name_item = selected_items[0]
        soldier_id = name_item.data(Qt.UserRole)
        if soldier_id is not None and self.current_soldier_id != soldier_id:
            self.current_soldier_id = soldier_id
            self.load_shooting_history(self.current_soldier_id)

    def load_shooting_history(self, soldier_id):
        """Tải và hiển-thị-lịch-sử-bắn với-định-dạng-thời-gian-mới."""
        self.ui.history_list.clear()
        try:
            sessions = self.db.get_sessions_for_soldier(soldier_id)

            if not sessions:
                self.set_panels_state("NO_SESSIONS")
                return
            
            self.set_panels_state("SOLDIER_SELECTED")
            
            for session in sessions:
                # Dòng 1: Tên phiên (giữ nguyên)
                session_name = session.get('exercise_name') or f"Phiên tập #{session['id']}"
                
                # Dòng 2: Xử-lý và định-dạng-lại-thời-gian
                try:
                    # Chuyển chuỗi từ CSDL thành đối-tượng-datetime
                    date_obj = datetime.strptime(session['session_date'], '%Y-%m-%d %H:%M:%S')
                    # Định-dạng lại theo yêu-cầu: Giờ:Phút - Ngày-Tháng-Năm
                    formatted_date = date_obj.strftime('%H:%M - %d-%m-%Y')
                except ValueError:
                    # Nếu có lỗi, hiển-thị-ngày-tháng-gốc
                    formatted_date = session['session_date']

                # Kết-hợp 2 dòng vào một item duy-nhất
                item_text = f"{session_name}\n{formatted_date}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, session['id'])
                self.ui.history_list.addItem(item)
            
            logging.info(f"Đã-tải {len(sessions)} phiên-tập-cho-chiến-sĩ ID {soldier_id}.")

        except Exception as e:
            logging.error(f"Lỗi-khi-tải-lịch-sử-bắn: {e}", exc_info=True)
    def on_session_selected(self):
        # ... (Hàm này giữ nguyên logic chính)
        selected_items = self.ui.history_list.selectedItems()
        if not selected_items:
            self.current_session_id = None
            self.set_panels_state("SOLDIER_SELECTED")
            return
        session_item = selected_items[0]
        session_id = session_item.data(Qt.UserRole)
        if session_id is not None and self.current_session_id != session_id:
            self.current_session_id = session_id
            self.ui.center_stack.setCurrentIndex(self.DATA_PAGE)
            self.load_session_details(self.current_session_id)

    def load_session_details(self, session_id):
        """Tải, tính toán và hiển thị toàn bộ thông tin chi tiết của một phiên."""
        logging.info(f"Đang tải chi tiết cho phiên ID: {session_id}")
        self.current_shots = self.db.get_shots_for_session(session_id)
        
        # --- A. Chuẩn bị dữ liệu ---
        total_shots = len(self.current_shots)
        hit_shots = [s for s in self.current_shots if s.get('score') is not None and s['score'] > 0]
        total_hits = len(hit_shots)
        valid_scores = [s['score'] for s in hit_shots]
        total_score = sum(valid_scores) # <<< TÍNH TỔNG ĐIỂM
        # --- B. Tính toán và cập nhật DÒNG TÓM TẮT ---
        hit_rate = (total_hits / total_shots * 100) if total_shots > 0 else 0
        # SỬA LẠI CÁCH TÍNH ĐIỂM TRUNG BÌNH THEO LOGIC MỚI
        avg_score = (total_score / total_shots) if total_shots > 0 else 0
        summary_text = (
            f"Tổng phát bắn: {total_shots}  |  "
            f"Tỷ lệ trúng: {hit_rate:.1f}%  |  "
            f"Điểm trung bình: {avg_score:.2f}"
        )
        self.ui.analysis_summary_label.setText(summary_text)

        # --- C. Tính toán và cập nhật BẢNG PHÂN TÍCH THEO BIA ---
        stats_by_target = {
            'bia_so_4': {'scores': [], 'coords': []},
            'bia_so_7_8': {'scores': [], 'coords': []},
            'bia_so_8': {'scores': [], 'coords': []}
        }

        for shot in hit_shots:
            target_key = shot.get('target_detected')
            if target_key in stats_by_target:
                stats_by_target[target_key]['scores'].append(shot['score'])
                if shot.get('hit_coordinate_x') is not None and shot.get('hit_coordinate_y') is not None:
                    coords = (shot['hit_coordinate_x'], shot['hit_coordinate_y'])
                    stats_by_target[target_key]['coords'].append(coords)
        
        # Lưu lại tọa độ để dùng cho popup
        self.current_shot_coords = {key: data['coords'] for key, data in stats_by_target.items()}

        # Điền dữ liệu vào bảng
        target_map_to_row = {'bia_so_4': 0, 'bia_so_7_8': 1, 'bia_so_8': 2}
        
        for target_key, row_index in target_map_to_row.items():
            data = stats_by_target.get(target_key, {'scores': [], 'coords': []})
            hit_count = len(data['scores'])
            total_score = sum(data['scores'])
            
            self.ui.analysis_target_table.item(row_index, 1).setText(str(hit_count))
            self.ui.analysis_target_table.item(row_index, 2).setText(str(total_score))
            # Kích hoạt/Vô hiệu hóa nút "Xem" dựa trên số lượng điểm bắn
            self.ui.analysis_view_buttons[target_key].setEnabled(len(data['coords']) > 0)


        # 2. Cập nhật bảng chi tiết các phát bắn
        self.ui.shot_table.setRowCount(total_shots)
        for row, shot in enumerate(self.current_shots):
            # Dịch tên mục tiêu
            target_raw = shot['target_detected']
            if target_raw == 'bia_so_4': target_display = 'Bia số 4'
            elif target_raw == 'bia_so_7_8': target_display = 'Bia số 7'
            elif target_raw == 'bia_so_8': target_display = 'Bia số 8'
            else: target_display = 'Trượt'

            # === ĐỊNH DẠNG LẠI THỜI GIAN CỦA TỪNG PHÁT BẮN ===
            try:
                ts_obj = datetime.strptime(shot['timestamp'], '%Y-%m-%d %H:%M:%S')
                formatted_ts = ts_obj.strftime('%H:%M:%S - %d-%m-%Y')
            except (ValueError, TypeError):
                formatted_ts = shot['timestamp']
            # ===============================================

            items = [
                QTableWidgetItem(str(shot['shot_number'])),
                QTableWidgetItem(formatted_ts),
                QTableWidgetItem(target_display),
                QTableWidgetItem(str(shot['score']))
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)
                # Lưu toàn bộ dữ liệu của phát bắn vào item đầu tiên của hàng
                if col == 0:
                    item.setData(Qt.UserRole, shot)
                self.ui.shot_table.setItem(row, col, item)

        # 3. Hiển thị ảnh của phát bắn đầu tiên (nếu có)
        if total_shots > 0:
            self.current_shot_index = 0
            self.update_shot_display()
            self.ui.shot_table.selectRow(0)
        else:
            self.current_shot_index = -1
            self.update_shot_display()

    # === THÊM CÁC HÀM MỚI ĐỂ ĐIỀU HƯỚNG VÀ HIỂN THỊ ẢNH ===
    def update_shot_display(self):
        """Cập nhật ảnh và label chỉ số dựa trên self.current_shot_index."""
        total_shots = len(self.current_shots)
        if 0 <= self.current_shot_index < total_shots:
            shot_data = self.current_shots[self.current_shot_index]
            self.ui.shot_index_label.setText(f"Phát {self.current_shot_index + 1}/{total_shots}")
            
            # Hiển thị ảnh
            image_path = shot_data.get('image_path')
            if image_path:
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # --- BẮT ĐẦU THAY ĐỔI ---
                    # Chỉ cần gán pixmap gốc, VideoLabel sẽ tự động co giãn nó
                    self.ui.result_image.setPixmap(pixmap)
                    # --- KẾT THÚC THAY ĐỔI ---
                else:
                    self.ui.result_image.setText("Lỗi tải ảnh")
            else:
                self.ui.result_image.setText("Không có ảnh")
        else:
            # Trường hợp không có phát bắn nào
            self.ui.shot_index_label.setText("Phát 0/0")
            self.ui.result_image.setText("Chưa có phát bắn")
            self.ui.result_image.setPixmap(QPixmap())

    def show_previous_shot(self):
        if self.current_shot_index > 0:
            self.current_shot_index -= 1
            self.ui.shot_table.selectRow(self.current_shot_index)
            self.update_shot_display()

    def show_next_shot(self):
        if self.current_shot_index < len(self.current_shots) - 1:
            self.current_shot_index += 1
            self.ui.shot_table.selectRow(self.current_shot_index)
            self.update_shot_display()
            
    def on_shot_table_selected(self):
        """Được gọi khi chọn một hàng trong bảng chi tiết."""
        selected_rows = self.ui.shot_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        selected_row_index = selected_rows[0].row()
        if self.current_shot_index != selected_row_index:
            self.current_shot_index = selected_row_index
            self.update_shot_display()
            
# gui/windows/manage_window.py

    def open_add_soldier_dialog(self):
        dialog = AddSoldierDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            # Chỉ cần kiểm tra tên là đủ
            if not data["name"]:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền Họ và Tên.")
                return
            try:
                # Lệnh gọi này vẫn đúng vì `data` giờ là {"name": ..., "class_name": ...}
                self.db.add_soldier(**data)
                QMessageBox.information(self, "Thành công", f"Đã thêm người học '{data['name']}'.")
                self.load_soldiers()
            except Exception as e:
                logging.error(f"Lỗi khi thêm người học mới: {e}")
                QMessageBox.critical(self, "Lỗi", f"Không thể thêm người học.\nLỗi: {e}")

    def load_soldiers(self):
        """Tải danh sách người học và hiển thị lên QTableWidget."""
        logging.info("Bắt đầu tải danh sách người học...")
        self.ui.soldier_table.setRowCount(0) # Xóa các hàng cũ

        try:
            soldiers = self.db.get_all_soldiers()

            if not soldiers:
                logging.warning("Không có người học nào trong CSDL.")
                self.ui.soldier_table.setRowCount(1)
                notice_item = QTableWidgetItem("Chưa có người học nào")
                notice_item.setTextAlignment(Qt.AlignCenter)
                notice_item.setFlags(notice_item.flags() & ~Qt.ItemIsEnabled)
                self.ui.soldier_table.setItem(0, 0, notice_item)
                self.ui.soldier_table.setSpan(0, 0, 1, self.ui.soldier_table.columnCount())
                return

            self.ui.soldier_table.setRowCount(len(soldiers))
            # === THAY ĐỔI: VÒNG LẶP ĐIỀN DỮ LIỆU ===
            for row, soldier_data in enumerate(soldiers):
                name_item = QTableWidgetItem(soldier_data['name'])
                class_name_item = QTableWidgetItem(soldier_data.get('class_name', '')) # Dùng .get để an toàn
                
                # Căn giữa cho cột "Lớp"
                class_name_item.setTextAlignment(Qt.AlignCenter)
                
                # Lưu ID ẩn vào item đầu tiên của hàng
                name_item.setData(Qt.UserRole, soldier_data['id'])
                
                # Đặt item vào đúng ô
                self.ui.soldier_table.setItem(row, 0, name_item)
                self.ui.soldier_table.setItem(row, 1, class_name_item)
            # ======================================

            logging.info(f"Đã tải thành công {len(soldiers)} người học.")

        except Exception as e:
            logging.error(f"Lỗi khi tải danh sách người học: {e}", exc_info=True)

# Thêm 3 hàm này vào bên trong class ManageWindow

    def show_soldier_context_menu(self, pos):
        """Hiển thị menu ngữ cảnh cho bảng người học."""
        item = self.ui.soldier_table.itemAt(pos)
        if not item:
            return # Không làm gì nếu không click vào item

        # Lấy thông tin của chiến sĩ được chọn
        soldier_id = self.ui.soldier_table.item(item.row(), 0).data(Qt.UserRole)
        soldier_name = self.ui.soldier_table.item(item.row(), 0).text()

        menu = QMenu(self)
        
        # Tạo action "Sửa"
        edit_action = menu.addAction("Sửa thông tin")
        edit_action.triggered.connect(lambda: self.edit_soldier(item.row()))

        # Tạo action "Xóa"
        delete_action = menu.addAction("Xóa người học")
        delete_action.triggered.connect(lambda: self.delete_soldier(soldier_id, soldier_name))

        # Hiển thị menu tại vị trí con trỏ
        menu.exec(self.ui.soldier_table.mapToGlobal(pos))


    def edit_soldier(self, row):
        """Mở dialog để sửa thông tin chiến sĩ."""
        soldier_id = self.ui.soldier_table.item(row, 0).data(Qt.UserRole)
        # === THAY ĐỔI: LẤY DỮ LIỆU TỪ 2 CỘT ===
        current_data = {
            "name": self.ui.soldier_table.item(row, 0).text(),
            "class_name": self.ui.soldier_table.item(row, 1).text()
        }

        dialog = AddSoldierDialog(self)
        dialog.setWindowTitle("Chỉnh sửa thông tin Người học")
        # === THAY ĐỔI: ĐIỀN DỮ LIỆU CŨ VÀO DIALOG MỚI ===
        dialog.name_input.setText(current_data["name"])
        dialog.class_name_input.setText(current_data["class_name"])
        
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            # Hàm update_soldier đã được sửa ở Bước 1, nên gọi với **new_data vẫn đúng
            if self.db.update_soldier(soldier_id, **new_data):
                QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin người học.")
                # Phần tải lại và chọn lại người học giữ nguyên, hoạt động tốt
                selected_id = self.current_soldier_id
                self.load_soldiers()
                if selected_id is not None:
                    for i in range(self.ui.soldier_table.rowCount()):
                        if self.ui.soldier_table.item(i, 0).data(Qt.UserRole) == selected_id:
                            self.ui.soldier_table.selectRow(i)
                            break
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể cập nhật thông tin.")

    def delete_soldier(self, soldier_id, soldier_name):
        """Xác nhận và xóa một chiến sĩ."""
        reply = QMessageBox.warning(
            self, 
            "Xác nhận Xóa",
            f"Bạn có chắc chắn muốn xóa người học '{soldier_name}'?\n"
            "TOÀN BỘ lịch sử bắn của người học này cũng sẽ bị xóa vĩnh viễn.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.db.delete_soldier(soldier_id):
                QMessageBox.information(self, "Thành công", f"Đã xóa người học '{soldier_name}'.")
                self.load_soldiers() # Tải lại danh sách
                # Xóa các thông tin đang hiển thị nếu chiến sĩ bị xóa là người đang được chọn
                if self.current_soldier_id == soldier_id:
                    self.ui.history_list.clear()
                    self.set_panels_state("NO_SOLDIER_SELECTED")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xóa chiến sĩ.")

# Thêm 3 hàm này vào bên trong class ManageWindow

    def show_session_context_menu(self, pos):
        """Hiển thị menu ngữ cảnh cho danh sách lịch sử bắn."""
        item = self.ui.history_list.itemAt(pos)
        if not item:
            return

        session_id = item.data(Qt.UserRole)
        # Lấy tên phiên từ dòng đầu tiên của item text
        session_name = item.text().split('\n')[0]

        menu = QMenu(self)
        
        edit_action = menu.addAction("Đổi tên phiên")
        edit_action.triggered.connect(lambda: self.edit_session_name(session_id, item))

        delete_action = menu.addAction("Xóa phiên")
        delete_action.triggered.connect(lambda: self.delete_session(session_id, session_name))

        menu.exec(self.ui.history_list.mapToGlobal(pos))

    def edit_session_name(self, session_id, item):
        """Mở dialog để đổi tên phiên tập, có vòng lặp kiểm tra tên trùng theo từng chiến sĩ."""
        current_name = item.text().split('\n')[0]
        
        while True:
            new_name, ok = QInputDialog.getText(
                self, "Đổi tên Phiên tập", "Nhập tên mới:",
                QLineEdit.Normal, current_name
            )
            
            if not ok: break
            
            stripped_name = new_name.strip()
            if not stripped_name: break

            # Kiểm tra tên trùng VỚI self.current_soldier_id
            if self.db.session_name_exists(stripped_name, soldier_id=self.current_soldier_id, exclude_session_id=session_id):
                QMessageBox.warning(self, "Tên bị trùng",
                                    f"Người học này đã có phiên tập tên '{stripped_name}'.\nVui lòng chọn một tên khác.")
                current_name = stripped_name
                continue

            # Tên hợp lệ, tiến hành cập nhật
            if self.db.update_session_name(session_id, stripped_name):
                QMessageBox.information(self, "Thành công", "Đã đổi tên phiên tập.")
                self.load_shooting_history(self.current_soldier_id)
                # Tự động chọn lại item vừa sửa
                for i in range(self.ui.history_list.count()):
                    if self.ui.history_list.item(i).data(Qt.UserRole) == session_id:
                        self.ui.history_list.setCurrentRow(i)
                        break
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể đổi tên phiên tập.")
            
            break
         
    def delete_session(self, session_id, session_name):
        """Xác nhận và xóa một phiên tập."""
        reply = QMessageBox.warning(
            self, 
            "Xác nhận Xóa",
            f"Bạn có chắc chắn muốn xóa phiên '{session_name}' không?\n"
            "Toàn bộ dữ liệu của phiên này sẽ bị xóa vĩnh viễn.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.db.delete_session(session_id):
                QMessageBox.information(self, "Thành công", f"Đã xóa phiên '{session_name}'.")
                self.load_shooting_history(self.current_soldier_id)
                # Nếu phiên bị xóa là phiên đang xem, dọn dẹp giao diện
                if self.current_session_id == session_id:
                    self.set_panels_state("SOLDIER_SELECTED")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xóa phiên tập.")