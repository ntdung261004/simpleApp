# file: gui/windows/manage_window.py

import logging
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

# =============================================================================
# === LỚP DIALOG THÊM/SỬA NGƯỜI HỌC ===
# =============================================================================
class AddSoldierDialog(QDialog):
    def __init__(self, config: dict, is_edit_mode: bool = False, parent=None):
        super().__init__(parent)
        self.config = config
        labels = self.config.get("labels", {})

        if is_edit_mode:
            title = labels.get("edit_trainee_dialog_title", "Chỉnh sửa thông tin")
        else:
            title = labels.get("add_trainee_dialog_title", "Thêm mới")
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
        for field in self.inputs:
            field.setStyleSheet(self.default_style)
        data = self.get_data()
        if data["name"]:
            self.accept()
        else:
            self.inputs[0].setStyleSheet(self.error_style)
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền Họ và Tên.")


# =============================================================================
# === LỚP DIALOG HIỂN THỊ ĐỘ CHỤM ===
# =============================================================================
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
# === LỚP CỬA SỔ QUẢN LÝ CHÍNH ===
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
        self.set_panels_state("NO_SOLDIER_SELECTED")
        self.ui.soldier_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.history_list.setContextMenuPolicy(Qt.CustomContextMenu)

    def setup_ui_styles(self):
        # Cập nhật style để tương thích với kích thước động
        padding = int(10 * self.ui.scale_factor)
        self.ui.history_list.setStyleSheet(f"QListWidget::item {{ padding: {padding}px; border-bottom: 1px solid #4a6278; }} QListWidget::item:selected {{ background-color: #1abc9c; color: #2c3e50; border-bottom: 1px solid #16a085; }}")
        table_stylesheet = "QTableWidget::item:selected { background-color: #1abc9c; color: white; }"
        self.ui.soldier_table.setStyleSheet(table_stylesheet)
        self.ui.shot_table.setStyleSheet(table_stylesheet)

    def connect_signals(self):
        self.ui.add_button.clicked.connect(self.open_add_soldier_dialog)
        self.ui.soldier_table.itemSelectionChanged.connect(self.on_soldier_selected)
        self.ui.history_list.itemSelectionChanged.connect(self.on_session_selected)
        self.ui.prev_shot_button.clicked.connect(self.show_previous_shot)
        self.ui.next_shot_button.clicked.connect(self.show_next_shot)
        self.ui.shot_table.itemSelectionChanged.connect(self.on_shot_table_selected)
        self.ui.soldier_table.customContextMenuRequested.connect(self.show_soldier_context_menu)
        self.ui.history_list.customContextMenuRequested.connect(self.show_session_context_menu)
        
        # --- BẮT ĐẦU VÙNG TINH CHỈNH: KẾT NỐI TÍN HIỆU TÌM KIẾM ---
        self.ui.search_box.textChanged.connect(self.filter_soldiers)
        # --- KẾT THÚC VÙNG TINH CHỈNH ---
        
        for target_key, button in self.ui.analysis_view_buttons.items():
            button.clicked.connect(lambda checked=False, key=target_key: self.show_grouping_popup(key))

    # --- BẮT ĐẦU VÙNG TINH CHỈNH: HÀM LOGIC LỌC DANH SÁCH ---
    def filter_soldiers(self):
        """
        Lọc danh sách chiến sĩ trong bảng dựa trên nội dung của thanh tìm kiếm.
        """
        search_text = self.ui.search_box.text().lower()
        for row in range(self.ui.soldier_table.rowCount()):
            name_item = self.ui.soldier_table.item(row, 0)
            class_item = self.ui.soldier_table.item(row, 1)
            
            # Đảm bảo item tồn tại trước khi lấy text
            name_matches = search_text in name_item.text().lower() if name_item else False
            class_matches = search_text in class_item.text().lower() if class_item else False

            # Ẩn/hiện dòng nếu tên hoặc đơn vị khớp
            if name_matches or class_matches:
                self.ui.soldier_table.setRowHidden(row, False)
            else:
                self.ui.soldier_table.setRowHidden(row, True)
    # --- KẾT THÚC VÙNG TINH CHỈNH ---

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

    def on_soldier_selected(self):
        selected_items = self.ui.soldier_table.selectedItems()
        if not selected_items:
            self.current_soldier_id = None
            self.set_panels_state("NO_SOLDIER_SELECTED")
            return

        name_item = self.ui.soldier_table.item(selected_items[0].row(), 0)
        soldier_id = name_item.data(Qt.UserRole)
        soldier_name = name_item.text()

        if soldier_id is not None and self.current_soldier_id != soldier_id:
            self.current_soldier_id = soldier_id
            labels = self.config.get("labels", {})
            title_prefix = labels.get("history_title_prefix", "Lịch sử của")
            self.ui.history_box.setTitle(f"{title_prefix} {soldier_name}")
            self.load_shooting_history(self.current_soldier_id)

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
            logging.info(f"Đã tải {len(sessions)} phiên tập cho chiến sĩ ID {soldier_id}.")
        except Exception as e:
            logging.error(f"Lỗi khi tải lịch sử bắn: {e}", exc_info=True)

    def on_session_selected(self):
        selected_items = self.ui.history_list.selectedItems()
        if not selected_items:
            self.current_session_id = None
            self.set_panels_state("SOLDIER_SELECTED")
            return
        session_item = selected_items[0]
        session_id = session_item.data(Qt.UserRole)
        if session_id is not None:
            self.current_session_id = session_id
            self.set_panels_state("SHOW_DATA")
            self.load_session_details(self.current_session_id)

    def load_session_details(self, session_id):
        logging.info(f"Đang tải chi tiết cho phiên ID: {session_id}")
        self.current_shots = self.db.get_shots_for_session(session_id)
        total_shots = len(self.current_shots)
        hit_shots = [s for s in self.current_shots if s.get('score') is not None and s['score'] > 0]
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
            except (ValueError, TypeError):
                formatted_ts = shot['timestamp']

            items = [QTableWidgetItem(str(shot['shot_number'])), QTableWidgetItem(formatted_ts), QTableWidgetItem(target_display), QTableWidgetItem(str(shot['score']))]
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
        if not selected_rows:
            return
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
        # --- BẮT ĐẦU VÙNG TINH CHỈNH: XÓA NỘI DUNG TÌM KIẾM KHI TẢI LẠI ---
        self.ui.search_box.clear()
        # --- KẾT THÚC VÙNG TINH CHỈNH ---
        self.ui.soldier_table.setRowCount(0)
        try:
            soldiers = self.db.get_all_soldiers()
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

    def show_soldier_context_menu(self, pos):
        item = self.ui.soldier_table.itemAt(pos)
        if not item: return
        row = item.row()
        soldier_id = self.ui.soldier_table.item(row, 0).data(Qt.UserRole)
        soldier_name = self.ui.soldier_table.item(row, 0).text()
        if soldier_id is None: return
        menu = QMenu(self)
        edit_action = menu.addAction("Sửa thông tin")
        edit_action.triggered.connect(lambda: self.edit_soldier(row))
        delete_action = menu.addAction("Xóa người này")
        delete_action.triggered.connect(lambda: self.delete_soldier(soldier_id, soldier_name))
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
        reply = QMessageBox.warning(self, "Xác nhận Xóa", f"Bạn có chắc chắn muốn xóa '{soldier_name}'?\nTOÀN BỘ lịch sử bắn của người này cũng sẽ bị xóa vĩnh viễn.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_soldier(soldier_id):
                QMessageBox.information(self, "Thành công", f"Đã xóa '{soldier_name}'.")
                self.load_soldiers()
                self.set_panels_state("NO_SOLDIER_SELECTED")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xóa người này.")

    def show_session_context_menu(self, pos):
        item = self.ui.history_list.itemAt(pos)
        if not item: return
        session_id = item.data(Qt.UserRole)
        session_name = item.text().split('\n')[0]
        menu = QMenu(self)
        edit_action = menu.addAction("Đổi tên phiên")
        edit_action.triggered.connect(lambda: self.edit_session_name(session_id))
        delete_action = menu.addAction("Xóa phiên")
        delete_action.triggered.connect(lambda: self.delete_session(session_id, session_name))
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
                QMessageBox.warning(self, "Tên bị trùng", f"Người này đã có phiên tập tên '{stripped_name}'.\nVui lòng chọn một tên khác.")
                current_name = stripped_name
                continue
            if self.db.update_session_name(session_id, stripped_name):
                QMessageBox.information(self, "Thành công", "Đã đổi tên phiên tập.")
                self.load_shooting_history(self.current_soldier_id)
                for i in range(self.ui.history_list.count()):
                    if self.ui.history_list.item(i).data(Qt.UserRole) == session_id:
                        self.ui.history_list.setCurrentRow(i)
                        break
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể đổi tên phiên tập.")
            break

    def delete_session(self, session_id, session_name):
        reply = QMessageBox.warning(self, "Xác nhận Xóa", f"Bạn có chắc chắn muốn xóa phiên '{session_name}' không?\nToàn bộ dữ liệu của phiên này sẽ bị xóa vĩnh viễn.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_session(session_id):
                QMessageBox.information(self, "Thành công", f"Đã xóa phiên '{session_name}'.")
                self.load_shooting_history(self.current_soldier_id)
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xóa phiên tập.")