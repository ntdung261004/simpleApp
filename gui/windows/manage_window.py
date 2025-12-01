# file: gui/windows/manage_window.py

import logging
import numpy as np
import cv2
import os
import pandas as pd
import unicodedata
from PySide6.QtWidgets import (
    QMainWindow, QDialog, QFormLayout, QLineEdit,
    QDialogButtonBox, QMessageBox, QTableWidgetItem,
    QVBoxLayout, QListWidgetItem, QLabel, QSizePolicy,
    QMenu, QInputDialog, QWidget, QGroupBox, QTableWidget, 
    QAbstractItemView, QHeaderView, QListWidget, QStackedWidget,
    QApplication, QFrame, QFileDialog, QCheckBox, QHBoxLayout, QPushButton
)
from datetime import datetime
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from gui.ui.ui_manage import ManageGui
from core.database import DatabaseManager
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

# =============================================================================
# === CÁC CLASS DIALOG HỖ TRỢ (GIỮ NGUYÊN) ===
# =============================================================================
# (Giữ nguyên class ExcelPreviewDialog, AddSoldierDialog, GroupingDisplayDialog 
# như phiên bản trước - không thay đổi)

class ExcelPreviewDialog(QDialog):
    def __init__(self, data_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xác nhận nhập dữ liệu")
        self.setMinimumSize(700, 500)
        self.data_list = data_list

        layout = QVBoxLayout(self)
        lbl_info = QLabel(f"<b>Đã tìm thấy {len(data_list)} bản ghi.</b><br>"
                          "Vui lòng kiểm tra kỹ danh sách bên dưới trước khi nhập.")
        lbl_info.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(lbl_info)

        self.table = QTableWidget(len(data_list), 3)
        self.table.setHorizontalHeaderLabels(["Chọn", "Họ và Tên", "Đơn vị"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        self.checkboxes = []
        for i, row_data in enumerate(data_list):
            chk_box = QCheckBox()
            chk_box.setChecked(True)
            cell_widget = QWidget()
            chk_layout = QHBoxLayout(cell_widget)
            chk_layout.addWidget(chk_box)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(i, 0, cell_widget)
            self.checkboxes.append(chk_box)
            self.table.setItem(i, 1, QTableWidgetItem(str(row_data.get('name', ''))))
            self.table.setItem(i, 2, QTableWidgetItem(str(row_data.get('class_name', ''))))

        layout.addWidget(self.table)
        btn_layout = QHBoxLayout()
        btn_all = QPushButton("Chọn tất cả")
        btn_all.clicked.connect(lambda: self.toggle_all(True))
        btn_none = QPushButton("Bỏ chọn tất cả")
        btn_none.clicked.connect(lambda: self.toggle_all(False))
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def toggle_all(self, state):
        for chk in self.checkboxes: chk.setChecked(state)
    def get_selected_data(self):
        result = []
        for i, chk in enumerate(self.checkboxes):
            if chk.isChecked(): result.append(self.data_list[i])
        return result

class AddSoldierDialog(QDialog):
    def __init__(self, config: dict, is_edit_mode: bool = False, parent=None):
        super().__init__(parent)
        self.config = config
        labels = self.config.get("labels", {})
        if is_edit_mode: title = labels.get("edit_trainee_dialog_title", "Chỉnh sửa thông tin")
        else: title = labels.get("add_trainee_dialog_title", "Thêm mới")
        self.setWindowTitle(title)
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
        title_label = QLabel(self.windowTitle())
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.name_input = QLineEdit()
        self.class_name_input = QLineEdit()
        self.inputs = [self.name_input, self.class_name_input]
        name_prompt = labels.get("trainee_name_prompt", "Họ và Tên:")
        class_prompt = labels.get("trainee_class_prompt", "Đơn vị:")
        form_layout.addRow(name_prompt, self.name_input)
        form_layout.addRow(class_prompt, self.class_name_input)
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
        return {"name": self.name_input.text().strip(), "class_name": self.class_name_input.text().strip()}
    def validate_and_accept(self):
        for field in self.inputs: field.setStyleSheet(self.default_style)
        data = self.get_data()
        if data["name"]: self.accept()
        else:
            self.inputs[0].setStyleSheet(self.error_style)
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền Họ và Tên.")

class GroupingDisplayDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trực quan Độ chụm")
        self.setMinimumSize(600, 800)
        self.setStyleSheet("background-color: #34495e;")
        self.layout = QVBoxLayout(self)
        self.image_label = QLabel("Đang tải ảnh...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.layout.addWidget(self.image_label)
        self._pixmap = QPixmap()
    def update_display(self, image_np: np.ndarray):
        if image_np is None:
            self.image_label.setText("Không có ảnh để hiển thị.")
            return
        try:
            h, w, ch = image_np.shape
            bytes_per_line = ch * w
            rgb_image = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self._pixmap = QPixmap.fromImage(qt_image)
            self.image_label.setPixmap(self._pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            logging.error(f"Lỗi khi hiển thị ảnh popup: {e}")
            self.image_label.setText("Lỗi khi hiển thị ảnh.")
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._pixmap.isNull():
            self.image_label.setPixmap(self._pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

# =============================================================================
# === MANAGE WINDOW - LOGIC CHÍNH ===
# =============================================================================
class ManageWindow(QMainWindow):
    DATA_PAGE = 0
    MESSAGE_PAGE = 1

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        labels = self.config.get("labels", {})

        app_title = labels.get("app_title", "Quản lý")
        self.setWindowTitle(app_title)

        self.ui = ManageGui(self.config)
        self.setCentralWidget(self.ui)
        self.db = DatabaseManager()

        self.current_soldier_id = None
        self.current_session_id = None
        self.current_shots = []
        self.current_shot_index = -1
        self.current_shot_coords = {}

        self.setup_ui_styles()
        self.connect_signals()
        
        # --- CẤU HÌNH CHỌN NHIỀU (MULTI-SELECT) ---
        self.ui.soldier_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ui.history_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.set_panels_state("NO_SOLDIER_SELECTED")
        self.ui.soldier_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        
        self.load_soldiers()

    def setup_ui_styles(self):
        padding = int(10 * self.ui.scale_factor)
        self.ui.history_list.setStyleSheet(f"QListWidget::item {{ padding: {padding}px; border-bottom: 1px solid #4a6278; }} QListWidget::item:selected {{ background-color: #1abc9c; color: #2c3e50; border-bottom: 1px solid #16a085; }}")
        table_stylesheet = "QTableWidget::item:selected { background-color: #1abc9c; color: white; }"
        self.ui.soldier_table.setStyleSheet(table_stylesheet)
        self.ui.shot_table.setStyleSheet(table_stylesheet)

    def connect_signals(self):
        self.ui.add_button.clicked.connect(self.open_add_soldier_dialog)
        self.ui.import_button.clicked.connect(self.import_excel_handler)
        self.ui.soldier_table.itemSelectionChanged.connect(self.on_soldier_selected)
        self.ui.history_list.itemSelectionChanged.connect(self.on_session_selected)
        self.ui.prev_shot_button.clicked.connect(self.show_previous_shot)
        self.ui.next_shot_button.clicked.connect(self.show_next_shot)
        self.ui.shot_table.itemSelectionChanged.connect(self.on_shot_table_selected)
        
        # Context Menu
        self.ui.soldier_table.customContextMenuRequested.connect(self.show_soldier_context_menu)
        self.ui.history_list.customContextMenuRequested.connect(self.show_session_context_menu)
        
        self.ui.search_box.textChanged.connect(self.filter_soldiers)
        for target_key, button in self.ui.analysis_view_buttons.items():
            button.clicked.connect(lambda checked=False, key=target_key: self.show_grouping_popup(key))

    # --- NHẬP EXCEL (GIỮ NGUYÊN) ---
    def import_excel_handler(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file Excel", "", "Excel Files (*.xlsx *.xls *.csv)")
        if not file_path: return
        try:
            if file_path.endswith('.csv'): df_raw = pd.read_csv(file_path, header=None)
            else: df_raw = pd.read_excel(file_path, header=None)
            
            name_keywords = ['họ và tên', 'họ tên', 'tên chiến sĩ', 'họ & tên', 'ho va ten']
            unit_keywords = ['đơn vị', 'đv', 'lớp', 'trung đội', 'đại đội', 'don vi']
            header_row_idx = -1; name_col_idx = -1; unit_col_idx = -1
            rows_to_scan = min(50, df_raw.shape[0])
            
            for r in range(rows_to_scan):
                row_values = []
                for cell in df_raw.iloc[r]:
                    cell_str = str(cell).strip().lower()
                    cell_str = unicodedata.normalize('NFC', cell_str)
                    row_values.append(cell_str)
                for c, val in enumerate(row_values):
                    if not val or val == 'nan': continue
                    if any(kw in val for kw in name_keywords):
                        header_row_idx = r; name_col_idx = c; break 
                if header_row_idx != -1:
                    for c, val in enumerate(row_values):
                        if c == name_col_idx: continue
                        if any(kw in val for kw in unit_keywords):
                            unit_col_idx = c; break
                    break

            if header_row_idx == -1:
                QMessageBox.warning(self, "Không nhận diện được", "Không tìm thấy cột 'Họ và tên'.")
                return

            data_to_import = []
            total_rows = df_raw.shape[0]
            for i in range(header_row_idx + 1, total_rows):
                row = df_raw.iloc[i]
                raw_name = str(row[name_col_idx]).strip()
                if not raw_name or raw_name.lower() == 'nan': continue
                raw_unit = ""
                if unit_col_idx != -1:
                    val = str(row[unit_col_idx]).strip()
                    if val and val.lower() != 'nan': raw_unit = val
                clean_name = " ".join([w.capitalize() for w in raw_name.split()])
                data_to_import.append({'name': clean_name, 'class_name': raw_unit})

            if not data_to_import:
                QMessageBox.information(self, "Rỗng", "Không có dữ liệu nào dưới dòng tiêu đề.")
                return

            preview_dialog = ExcelPreviewDialog(data_to_import, self)
            if preview_dialog.exec() == QDialog.Accepted:
                selected_data = preview_dialog.get_selected_data()
                count = 0
                for item in selected_data:
                    if self.db.add_soldier(item['name'], item['class_name']): count += 1
                QMessageBox.information(self, "Thành công", f"Đã nhập {count} người.")
                self.load_soldiers()
        except Exception as e:
            logging.error(f"Lỗi nhập Excel: {e}")
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra:\n{e}")

    def filter_soldiers(self):
        search_text = self.ui.search_box.text().lower()
        for row in range(self.ui.soldier_table.rowCount()):
            name_item = self.ui.soldier_table.item(row, 0)
            class_item = self.ui.soldier_table.item(row, 1)
            name_matches = search_text in name_item.text().lower() if name_item else False
            class_matches = search_text in class_item.text().lower() if class_item else False
            self.ui.soldier_table.setRowHidden(row, not (name_matches or class_matches))

    def show_grouping_popup(self, target_key: str):
        coords = self.current_shot_coords.get(target_key)
        if not coords:
            QMessageBox.information(self, "Thông báo", "Không có dữ liệu điểm bắn cho loại bia này.")
            return
        asset_path = resource_path("assets/images/original")
        target_image_map = {'bia_so_4': 'bia_so_4.png', 'bia_so_7_8': 'bia_so_7.png', 'bia_so_8': 'bia_so_8.png'}
        image_file = target_image_map.get(target_key)
        if not image_file: return
        image_path = os.path.join(asset_path, image_file)
        if not os.path.exists(image_path):
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy ảnh bia gốc tại:\n{image_path}")
            return
        target_image = cv2.imread(image_path)
        for (x, y) in coords:
            cv2.drawMarker(target_image, (int(x), int(y)), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=40, thickness=3)
        dialog = GroupingDisplayDialog(self)
        dialog.update_display(target_image)
        dialog.exec()

    def set_panels_state(self, state: str):
        labels = self.config.get("labels", {})
        trainee_term = labels.get("trainee", "Người học")
        msg = ""
        if state == "NO_SOLDIER_SELECTED":
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.right_stack.setCurrentIndex(self.MESSAGE_PAGE)
            prompt = labels.get("manage_select_trainee_prompt", "◀ Vui lòng chọn một {trainee} từ danh sách")
            msg = prompt.format(trainee=trainee_term.lower())
            self.ui.center_message_label.setText(msg)
            self.ui.right_message_label.setText(msg)
        elif state == "NO_SESSIONS":
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.right_stack.setCurrentIndex(self.MESSAGE_PAGE)
            prompt = labels.get("manage_no_sessions_prompt", "{trainee} này chưa thực hiện phiên tập nào")
            msg = prompt.format(trainee=trainee_term.capitalize())
            self.ui.center_message_label.setText(msg)
            self.ui.right_message_label.setText(msg)
        elif state == "SOLDIER_SELECTED":
            self.ui.right_stack.setCurrentIndex(self.DATA_PAGE)
            self.ui.center_stack.setCurrentIndex(self.MESSAGE_PAGE)
            self.ui.center_message_label.setText("▲ Vui lòng chọn một phiên tập để xem chi tiết")
        elif state == "SHOW_DATA":
            self.ui.center_stack.setCurrentIndex(self.DATA_PAGE)
            self.ui.right_stack.setCurrentIndex(self.DATA_PAGE)

    # --- NÂNG CẤP: XỬ LÝ CHỌN NHIỀU NGƯỜI ---
    def on_soldier_selected(self):
        selected_rows = set()
        for item in self.ui.soldier_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            self.current_soldier_id = None
            self.set_panels_state("NO_SOLDIER_SELECTED")
            return

        # Nếu chỉ chọn 1 người -> Hiện chi tiết như cũ
        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            name_item = self.ui.soldier_table.item(row, 0)
            soldier_id = name_item.data(Qt.UserRole)
            soldier_name = name_item.text()
            if soldier_id is not None and self.current_soldier_id != soldier_id:
                self.current_soldier_id = soldier_id
                labels = self.config.get("labels", {})
                title_prefix = labels.get("history_title_prefix", "Lịch sử của")
                self.ui.history_box.setTitle(f"{title_prefix} {soldier_name}")
                self.load_shooting_history(self.current_soldier_id)
        # Nếu chọn nhiều người -> Ẩn chi tiết, chỉ cho phép xóa
        else:
            self.current_soldier_id = None
            self.ui.history_list.clear()
            self.ui.history_box.setTitle(f"Đã chọn {len(selected_rows)} người")
            self.set_panels_state("NO_SESSIONS")

    def load_shooting_history(self, soldier_id):
        self.ui.history_list.clear()
        try:
            sessions = self.db.get_sessions_for_soldier(soldier_id)
            if not sessions:
                self.set_panels_state("NO_SESSIONS")
                return
            self.set_panels_state("SOLDIER_SELECTED")
            for session in sessions:
                session_name = session.get('exercise_name') or f"Phiên tập #{session['id']}"
                try:
                    date_obj = datetime.strptime(session['session_date'], '%Y-%m-%d %H:%M:%S')
                    formatted_date = date_obj.strftime('%H:%M - %d/%m/%Y')
                except (ValueError, TypeError):
                    formatted_date = session['session_date']
                item_text = f"{session_name}\n{formatted_date}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, session['id'])
                self.ui.history_list.addItem(item)
        except Exception as e:
            logging.error(f"Lỗi khi tải lịch sử bắn: {e}")

    # --- NÂNG CẤP: XỬ LÝ CHỌN NHIỀU PHIÊN TẬP ---
    def on_session_selected(self):
        selected_items = self.ui.history_list.selectedItems()
        if not selected_items:
            self.current_session_id = None
            self.set_panels_state("SOLDIER_SELECTED")
            return
        
        if len(selected_items) == 1:
            session_id = selected_items[0].data(Qt.UserRole)
            if session_id is not None:
                self.current_session_id = session_id
                self.set_panels_state("SHOW_DATA")
                self.load_session_details(self.current_session_id)
        else:
            self.current_session_id = None
            # Reset bảng dữ liệu khi chọn nhiều phiên (tránh hiểu nhầm)
            self.ui.analysis_summary_label.setText(f"Đã chọn {len(selected_items)} phiên tập - Vui lòng nhấn chuột phải để Xóa")
            self.ui.shot_table.setRowCount(0)
            self.ui.result_image.clear()
            for r in range(3):
                self.ui.analysis_target_table.item(r, 1).setText("--")
                self.ui.analysis_target_table.item(r, 2).setText("--")

    def load_session_details(self, session_id):
        logging.info(f"Đang tải chi tiết cho phiên ID: {session_id}")
        self.current_shots = self.db.get_shots_for_session(session_id)
        total_shots = len(self.current_shots)
        
        hit_shots = []
        for s in self.current_shots:
            try: score_val = int(s.get('score') or 0)
            except (ValueError, TypeError): score_val = 0
            s['score'] = score_val
            if score_val > 0: hit_shots.append(s)

        total_hits = len(hit_shots)
        valid_scores = [s['score'] for s in hit_shots]
        total_score = sum(valid_scores)
        hit_rate = (total_hits / total_shots * 100) if total_shots > 0 else 0
        avg_score = (total_score / total_hits) if total_hits > 0 else 0
        summary_text = f"Tổng phát bắn: {total_shots}  |  Tỷ lệ trúng: {hit_rate:.1f}%  |  Điểm trung bình: {avg_score:.2f}"
        self.ui.analysis_summary_label.setText(summary_text)

        stats_by_target = {'bia_so_4': {'scores': [], 'coords': []}, 'bia_so_7_8': {'scores': [], 'coords': []}, 'bia_so_8': {'scores': [], 'coords': []}}
        for shot in hit_shots:
            target_key = shot.get('target_detected')
            if target_key in stats_by_target:
                stats_by_target[target_key]['scores'].append(shot['score'])
                if shot.get('hit_coordinate_x') is not None and shot.get('hit_coordinate_y') is not None:
                    coords = (shot['hit_coordinate_x'], shot['hit_coordinate_y'])
                    stats_by_target[target_key]['coords'].append(coords)

        self.current_shot_coords = {key: data['coords'] for key, data in stats_by_target.items()}
        target_map_to_row = {'bia_so_4': 0, 'bia_so_7_8': 1, 'bia_so_8': 2}

        for target_key, row_index in target_map_to_row.items():
            data = stats_by_target.get(target_key, {'scores': [], 'coords': []})
            hit_count = len(data['scores'])
            total_score_target = sum(data['scores'])
            self.ui.analysis_target_table.item(row_index, 1).setText(str(hit_count))
            self.ui.analysis_target_table.item(row_index, 2).setText(str(total_score_target))
            self.ui.analysis_view_buttons[target_key].setEnabled(len(data['coords']) > 0)

        self.ui.shot_table.setRowCount(total_shots)
        for row, shot in enumerate(self.current_shots):
            target_raw = shot['target_detected']
            if target_raw == 'bia_so_4': target_display = 'Bia số 4'
            elif target_raw == 'bia_so_7_8': target_display = 'Bia số 7'
            elif target_raw == 'bia_so_8': target_display = 'Bia số 8'
            else: target_display = 'Trượt'
            try:
                ts_obj = datetime.strptime(shot['timestamp'], '%Y-%m-%d %H:%M:%S')
                formatted_ts = ts_obj.strftime('%H:%M:%S')
            except (ValueError, TypeError): formatted_ts = shot['timestamp']

            items = [
                QTableWidgetItem(str(shot['shot_number'])), 
                QTableWidgetItem(formatted_ts), 
                QTableWidgetItem(target_display), 
                QTableWidgetItem(str(shot['score']))
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)
                self.ui.shot_table.setItem(row, col, item)

        if total_shots > 0:
            self.ui.shot_table.selectRow(0)
            self.current_shot_index = 0
        else:
            self.current_shot_index = -1
            self.update_shot_display()

    def update_shot_display(self):
        total_shots = len(self.current_shots)
        has_shots = 0 <= self.current_shot_index < total_shots
        self.ui.prev_shot_button.setEnabled(has_shots and self.current_shot_index > 0)
        self.ui.next_shot_button.setEnabled(has_shots and self.current_shot_index < total_shots - 1)
        if has_shots:
            shot_data = self.current_shots[self.current_shot_index]
            self.ui.shot_index_label.setText(f"Phát {self.current_shot_index + 1}/{total_shots}")
            image_path = shot_data.get('image_path')
            if image_path and os.path.exists(image_path):
                self.ui.result_image.setPixmap(QPixmap(image_path))
            else:
                self.ui.result_image.setPixmap(QPixmap())
                self.ui.result_image.setText("Không tìm thấy ảnh")
        else:
            self.ui.shot_index_label.setText("Phát 0/0")
            self.ui.result_image.setPixmap(QPixmap())
            self.ui.result_image.setText("Chưa có phát bắn")

    def show_previous_shot(self):
        if self.current_shot_index > 0:
            self.ui.shot_table.selectRow(self.current_shot_index - 1)

    def show_next_shot(self):
        if self.current_shot_index < len(self.current_shots) - 1:
            self.ui.shot_table.selectRow(self.current_shot_index + 1)
            
    def on_shot_table_selected(self):
        selected_rows = self.ui.shot_table.selectionModel().selectedRows()
        if not selected_rows: return
        selected_row_index = selected_rows[0].row()
        if self.current_shot_index != selected_row_index:
            self.current_shot_index = selected_row_index
            self.update_shot_display()

    def open_add_soldier_dialog(self):
        dialog = AddSoldierDialog(self.config, parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                self.db.add_soldier(**data)
                QMessageBox.information(self, "Thành công", f"Đã thêm '{data['name']}'.")
                self.load_soldiers()
            except Exception as e:
                logging.error(f"Lỗi khi thêm người học mới: {e}")
                QMessageBox.critical(self, "Lỗi", f"Không thể thêm người này.\nLỗi: {e}")

    def load_soldiers(self):
        logging.info("Bắt đầu tải danh sách người học...")
        self.ui.search_box.clear()
        self.ui.soldier_table.setRowCount(0)
        try:
            soldiers = self.db.get_all_soldiers()
            # --- MỚI: CẬP NHẬT TỔNG SỐ ---
            total = len(soldiers) if soldiers else 0
            self.ui.total_count_label.setText(f"Tổng số: {total}")
            # -----------------------------
            if not soldiers:
                self.ui.soldier_table.setRowCount(0)
                self.set_panels_state("NO_SOLDIER_SELECTED")
                return
            self.ui.soldier_table.setRowCount(len(soldiers))
            for row, soldier_data in enumerate(soldiers):
                name_item = QTableWidgetItem(soldier_data['name'])
                class_name_item = QTableWidgetItem(soldier_data.get('class_name', ''))
                class_name_item.setTextAlignment(Qt.AlignCenter)
                name_item.setData(Qt.UserRole, soldier_data['id'])
                self.ui.soldier_table.setItem(row, 0, name_item)
                self.ui.soldier_table.setItem(row, 1, class_name_item)
            logging.info(f"Đã tải thành công {len(soldiers)} người học.")
        except Exception as e:
            logging.error(f"Lỗi khi tải danh sách người học: {e}", exc_info=True)

    # --- NÂNG CẤP: MENU NGỮ CẢNH HỖ TRỢ XÓA NHIỀU ---
    def show_soldier_context_menu(self, pos):
        selected_rows = set()
        for item in self.ui.soldier_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows: return

        menu = QMenu(self)
        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            soldier_id = self.ui.soldier_table.item(row, 0).data(Qt.UserRole)
            edit_action = menu.addAction("Sửa thông tin")
            edit_action.triggered.connect(lambda: self.edit_soldier(row))
            delete_action = menu.addAction("Xóa người này")
            delete_action.triggered.connect(lambda: self.delete_multiple_soldiers([soldier_id]))
        else:
            soldier_ids = []
            for r in selected_rows:
                sid = self.ui.soldier_table.item(r, 0).data(Qt.UserRole)
                if sid: soldier_ids.append(sid)
            delete_action = menu.addAction(f"Xóa {len(soldier_ids)} người đã chọn")
            delete_action.triggered.connect(lambda: self.delete_multiple_soldiers(soldier_ids))
        
        menu.exec(self.ui.soldier_table.mapToGlobal(pos))

    def edit_soldier(self, row):
        soldier_id = self.ui.soldier_table.item(row, 0).data(Qt.UserRole)
        current_data = {"name": self.ui.soldier_table.item(row, 0).text(), "class_name": self.ui.soldier_table.item(row, 1).text()}
        dialog = AddSoldierDialog(self.config, is_edit_mode=True, parent=self)
        dialog.name_input.setText(current_data["name"])
        dialog.class_name_input.setText(current_data["class_name"])
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            if self.db.update_soldier(soldier_id, **new_data):
                QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin.")
                if self.current_soldier_id == soldier_id: self.load_soldiers()
                else: self.load_soldiers()
            else: QMessageBox.critical(self, "Lỗi", "Không thể cập nhật thông tin.")

    # --- HÀM XÓA NHIỀU NGƯỜI ---
    def delete_multiple_soldiers(self, soldier_ids):
        count = len(soldier_ids)
        if count == 0: return
        reply = QMessageBox.warning(self, "Xác nhận Xóa", 
                                    f"Bạn có chắc chắn muốn xóa {count} người được chọn?\n"
                                    "TOÀN BỘ dữ liệu lịch sử của họ sẽ bị mất vĩnh viễn.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            deleted_count = 0
            for sid in soldier_ids:
                if self.db.delete_soldier(sid): deleted_count += 1
            QMessageBox.information(self, "Thành công", f"Đã xóa {deleted_count} người.")
            self.load_soldiers()
            self.set_panels_state("NO_SOLDIER_SELECTED")

    # --- NÂNG CẤP: MENU NGỮ CẢNH PHIÊN TẬP ---
    def show_session_context_menu(self, pos):
        selected_items = self.ui.history_list.selectedItems()
        if not selected_items: return

        menu = QMenu(self)
        if len(selected_items) == 1:
            session_id = selected_items[0].data(Qt.UserRole)
            edit_action = menu.addAction("Đổi tên phiên")
            edit_action.triggered.connect(lambda: self.edit_session_name(session_id))
            delete_action = menu.addAction("Xóa phiên")
            delete_action.triggered.connect(lambda: self.delete_multiple_sessions([session_id]))
        else:
            session_ids = [item.data(Qt.UserRole) for item in selected_items]
            delete_action = menu.addAction(f"Xóa {len(session_ids)} phiên đã chọn")
            delete_action.triggered.connect(lambda: self.delete_multiple_sessions(session_ids))
        
        menu.exec(self.ui.history_list.mapToGlobal(pos))

    def edit_session_name(self, session_id):
        session_data = self.db.get_session_by_id(session_id)
        if not session_data: return
        current_name = session_data.get('exercise_name')
        while True:
            new_name, ok = QInputDialog.getText(self, "Đổi tên Phiên tập", "Nhập tên mới:", QLineEdit.Normal, current_name)
            if not ok: break
            stripped_name = new_name.strip()
            if not stripped_name: continue
            if self.db.session_name_exists(stripped_name, soldier_id=self.current_soldier_id, exclude_session_id=session_id):
                QMessageBox.warning(self, "Tên bị trùng", f"Phiên tập '{stripped_name}' đã tồn tại.")
                current_name = stripped_name
                continue
            if self.db.update_session_name(session_id, stripped_name):
                QMessageBox.information(self, "Thành công", "Đã đổi tên phiên tập.")
                self.load_shooting_history(self.current_soldier_id)
                break
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể đổi tên phiên tập.")
            break

    # --- HÀM XÓA NHIỀU PHIÊN ---
    def delete_multiple_sessions(self, session_ids):
        count = len(session_ids)
        reply = QMessageBox.warning(self, "Xác nhận Xóa", 
                                    f"Bạn có chắc chắn muốn xóa {count} phiên tập này không?\n"
                                    "Dữ liệu không thể phục hồi.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            deleted = 0
            for sid in session_ids:
                if self.db.delete_session(sid): deleted += 1
            QMessageBox.information(self, "Thành công", f"Đã xóa {deleted} phiên tập.")
            self.load_shooting_history(self.current_soldier_id)