# file: gui/windows/setup_competition_window.py
from PySide6.QtWidgets import (
    QMainWindow, QListWidgetItem, QMessageBox, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QCheckBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QPixmap

from ..ui.ui_setup_competition import Ui_SetupCompetitionWindow
from core.database import DatabaseManager
from utils.resource_path import resource_path

class SoldierListItemWidget(QWidget):
    def __init__(self, soldier_id: int, name: str, class_name: str, parent=None):
        super().__init__(parent); self.soldier_id = soldier_id
        self.setStyleSheet("QWidget { background-color: #34495e; border-radius: 8px; } QLabel { background-color: transparent; }")
        main_layout = QHBoxLayout(self); main_layout.setContentsMargins(10, 15, 15, 15); main_layout.setSpacing(20)
        icon_label = QLabel(); icon_label.setFixedSize(32, 32); icon_label.setPixmap(QPixmap(resource_path("assets/images/icon/user_icon.png"))); icon_label.setScaledContents(True)
        info_layout = QVBoxLayout(); info_layout.setSpacing(0)
        name_label = QLabel(f"<b>{name}</b>"); name_label.setFont(QFont("Segoe UI", 12))
        class_label = QLabel(class_name); class_label.setStyleSheet("color: #bdc3c7;")
        info_layout.addWidget(name_label); info_layout.addWidget(class_label)
        self.select_checkbox = QCheckBox(); self.select_checkbox.setFixedSize(25, 25)
        main_layout.addWidget(icon_label); main_layout.addLayout(info_layout, 1); main_layout.addWidget(self.select_checkbox)
    def is_selected(self) -> bool: return self.select_checkbox.isChecked()

class SetupCompetitionWindow(QMainWindow):
    start_competition_signal = Signal(str, list)

    def __init__(self):
        super().__init__()
        self.ui = Ui_SetupCompetitionWindow()
        self.ui.setupUi(self)
        self.db = DatabaseManager()
        self.ui.start_competition_button.clicked.connect(self.on_start_competition)
        self.ui.select_all_checkbox.clicked.connect(self.toggle_select_all)

    # === BẮT ĐẦU VÙNG THAY ĐỔI ===
    def reset_form(self):
        """Xóa trắng các trường nhập liệu và lựa chọn về trạng thái ban đầu."""
        self.ui.competition_name_input.clear()
        self.ui.select_all_checkbox.setChecked(False)
        self.toggle_select_all() # Áp dụng việc bỏ chọn cho tất cả
        self.update_selection_count()

    def on_start_competition(self):
        competition_name = self.ui.competition_name_input.text().strip()
        if not competition_name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên cho cuộc thi.")
            return

        # Kiểm tra tên trùng lặp
        if self.db.competition_name_exists(competition_name):
            QMessageBox.warning(self, "Tên Bị Trùng", f"Tên cuộc thi '{competition_name}' đã tồn tại. Vui lòng chọn một tên khác.")
            return
            
        selected_ids = self.get_selected_soldier_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Chưa chọn Xạ thủ", "Vui lòng chọn ít nhất một người để bắt đầu thi đấu.")
            return
            
        self.start_competition_signal.emit(competition_name, selected_ids)
    # === KẾT THÚC VÙNG THAY ĐỔI ===

    def load_soldiers(self):
        self.ui.soldier_list.clear()
        soldiers = self.db.get_all_soldiers()
        if soldiers:
            for soldier in soldiers:
                widget = SoldierListItemWidget(soldier['id'], soldier['name'], soldier['class_name'])
                widget.select_checkbox.stateChanged.connect(self.update_selection_count)
                item = QListWidgetItem(self.ui.soldier_list)
                item.setSizeHint(widget.sizeHint())
                self.ui.soldier_list.addItem(item); self.ui.soldier_list.setItemWidget(item, widget)
        else: self.ui.soldier_list.addItem("Chưa có xạ thủ nào trong dữ liệu.")
        self.update_selection_count()

    def get_selected_soldier_ids(self) -> list:
        return [self.ui.soldier_list.itemWidget(self.ui.soldier_list.item(i)).soldier_id
                for i in range(self.ui.soldier_list.count())
                if isinstance(self.ui.soldier_list.itemWidget(self.ui.soldier_list.item(i)), SoldierListItemWidget) and
                   self.ui.soldier_list.itemWidget(self.ui.soldier_list.item(i)).is_selected()]

    @Slot()
    def toggle_select_all(self):
        is_checked = self.ui.select_all_checkbox.isChecked()
        for i in range(self.ui.soldier_list.count()):
            widget = self.ui.soldier_list.itemWidget(self.ui.soldier_list.item(i))
            if isinstance(widget, SoldierListItemWidget):
                widget.select_checkbox.blockSignals(True); widget.select_checkbox.setChecked(is_checked); widget.select_checkbox.blockSignals(False)
        self.update_selection_count()

    @Slot()
    def update_selection_count(self):
        selected_count = len(self.get_selected_soldier_ids())
        total_items = sum(1 for i in range(self.ui.soldier_list.count()) if isinstance(self.ui.soldier_list.itemWidget(self.ui.soldier_list.item(i)), SoldierListItemWidget))
        self.ui.selected_count_label.setText(f"Đã chọn: {selected_count}")
        self.ui.select_all_checkbox.blockSignals(True)
        self.ui.select_all_checkbox.setChecked(total_items > 0 and selected_count == total_items)
        self.ui.select_all_checkbox.blockSignals(False)