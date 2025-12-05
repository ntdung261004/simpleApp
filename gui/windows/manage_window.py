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
    QVBoxLayout, QWidget, QCheckBox, QHBoxLayout, QPushButton,
    QMenu, QFileDialog, QHeaderView, QLabel, QTableWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage

from gui.ui.ui_manage import ManageGui
from core.database import DatabaseManager
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

# --- GIỮ NGUYÊN CÁC CLASS DIALOG HỖ TRỢ ---
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

# =============================================================================
# === MANAGE WINDOW - LOGIC CHÍNH ===
# =============================================================================
class ManageWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        labels = self.config.get("labels", {})
        app_title = labels.get("app_title", "Quản lý")
        self.setWindowTitle(app_title)

        self.ui = ManageGui(self.config)
        self.setCentralWidget(self.ui)
        self.db = DatabaseManager()

        self.connect_signals()
        
        # Mặc định hiển thị trang Menu
        self.show_menu()

    def connect_signals(self):
        # Kết nối các nút ở trang Menu
        self.ui.btn_menu_trainees.clicked.connect(self.show_trainee_list)
        self.ui.btn_menu_sessions.clicked.connect(self.show_session_management)
        self.ui.btn_menu_tests.clicked.connect(self.show_test_management)
        
        # Kết nối các nút ở trang Danh sách người tập
        self.ui.btn_add_trainee.clicked.connect(self.open_add_soldier_dialog)
        self.ui.btn_import_excel.clicked.connect(self.import_excel_handler)
        self.ui.btn_back_to_menu.clicked.connect(self.show_menu)
        self.ui.search_box.textChanged.connect(self.filter_soldiers)
        
        # Context Menu cho bảng
        self.ui.soldier_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.soldier_table.customContextMenuRequested.connect(self.show_soldier_context_menu)

    # --- ĐIỀU HƯỚNG ---
    def show_menu(self):
        self.ui.main_stack.setCurrentWidget(self.ui.page_menu)

    def show_trainee_list(self):
        self.ui.main_stack.setCurrentWidget(self.ui.page_trainees)
        self.load_soldiers() # Tải dữ liệu khi vào trang

    def show_session_management(self):
        QMessageBox.information(self, "Thông báo", "Chức năng 'Quản lý Phiên tập' đang được xây dựng (Bước tiếp theo).")

    def show_test_management(self):
        QMessageBox.information(self, "Thông báo", "Chức năng 'Quản lý Kiểm tra' đang được xây dựng (Bước tiếp theo).")

    # --- LOGIC QUẢN LÝ NGƯỜI TẬP ---
    def load_soldiers(self):
        logging.info("Bắt đầu tải danh sách người học...")
        self.ui.search_box.clear()
        self.ui.soldier_table.setRowCount(0)
        try:
            soldiers = self.db.get_all_soldiers()
            total = len(soldiers) if soldiers else 0
            self.ui.total_count_label.setText(f"Tổng số: {total}")
            
            if not soldiers: return

            self.ui.soldier_table.setRowCount(total)
            for row, soldier_data in enumerate(soldiers):
                id_item = QTableWidgetItem(str(soldier_data['id']))
                id_item.setTextAlignment(Qt.AlignCenter)
                id_item.setData(Qt.UserRole, soldier_data['id']) # Lưu ID vào cột 0 luôn cho tiện
                
                name_item = QTableWidgetItem(soldier_data['name'])
                
                class_name_item = QTableWidgetItem(soldier_data.get('class_name', ''))
                class_name_item.setTextAlignment(Qt.AlignCenter)
                
                self.ui.soldier_table.setItem(row, 0, id_item)
                self.ui.soldier_table.setItem(row, 1, name_item)
                self.ui.soldier_table.setItem(row, 2, class_name_item)
            
            logging.info(f"Đã tải thành công {total} người học.")
        except Exception as e:
            logging.error(f"Lỗi khi tải danh sách người học: {e}", exc_info=True)

    def filter_soldiers(self):
        search_text = self.ui.search_box.text().lower()
        for row in range(self.ui.soldier_table.rowCount()):
            name_item = self.ui.soldier_table.item(row, 1)
            class_item = self.ui.soldier_table.item(row, 2)
            name_matches = search_text in name_item.text().lower() if name_item else False
            class_matches = search_text in class_item.text().lower() if class_item else False
            self.ui.soldier_table.setRowHidden(row, not (name_matches or class_matches))

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

    def show_soldier_context_menu(self, pos):
        selected_rows = set()
        for item in self.ui.soldier_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows: return

        menu = QMenu(self)
        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            # ID ở cột 0
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
        # Cột 1 là Tên, Cột 2 là Đơn vị
        current_data = {
            "name": self.ui.soldier_table.item(row, 1).text(),
            "class_name": self.ui.soldier_table.item(row, 2).text()
        }
        dialog = AddSoldierDialog(self.config, is_edit_mode=True, parent=self)
        dialog.name_input.setText(current_data["name"])
        dialog.class_name_input.setText(current_data["class_name"])
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            if self.db.update_soldier(soldier_id, **new_data):
                QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin.")
                self.load_soldiers()
            else: QMessageBox.critical(self, "Lỗi", "Không thể cập nhật thông tin.")

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