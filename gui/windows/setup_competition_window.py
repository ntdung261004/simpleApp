# file: gui/windows/setup_competition_window.py
import base64
from PySide6.QtWidgets import (
    QMainWindow, QListWidgetItem, QMessageBox, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QCheckBox,  QAbstractItemView
)
from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtGui import QFont, QPixmap

from ..ui.ui_setup_competition import Ui_SetupCompetitionWindow
from core.database import DatabaseManager
from utils.resource_path import resource_path

# Lớp SoldierListItemWidget (Giữ nguyên không thay đổi)
class SoldierListItemWidget(QWidget):
    def __init__(self, soldier_id: int, name: str, class_name: str, parent=None):
        super().__init__(parent)
        self.soldier_id = soldier_id
        self.setStyleSheet("""
            QWidget { background-color: #34495e; border-radius: 8px; }
            QLabel { background-color: transparent; }
        """)
        main_layout = QHBoxLayout(self); main_layout.setContentsMargins(10, 15, 15, 15); main_layout.setSpacing(20)
        
        self.icon_label = QLabel(); self.icon_label.setFixedSize(32, 32)
        icon_path = resource_path("assets/images/icon/user_icon.png")
        self.icon_label.setPixmap(QPixmap(icon_path)); self.icon_label.setScaledContents(True)
        
        info_layout = QVBoxLayout(); info_layout.setSpacing(0)
        self.name_label = QLabel(f"<b>{name}</b>"); self.name_label.setFont(QFont("Segoe UI", 12))
        self.class_label = QLabel(class_name); self.class_label.setStyleSheet("color: #bdc3c7;")
        info_layout.addWidget(self.name_label); info_layout.addWidget(self.class_label)
        
        self.select_checkbox = QCheckBox(); self.select_checkbox.setFixedSize(QSize(25, 25))
        
        main_layout.addWidget(self.icon_label); main_layout.addLayout(info_layout, 1); main_layout.addWidget(self.select_checkbox)
        
    def is_selected(self) -> bool:
        return self.select_checkbox.isChecked()

class SetupCompetitionWindow(QMainWindow):
    start_competition_signal = Signal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_SetupCompetitionWindow()
        self.ui.setupUi(self)
        self.db = DatabaseManager()

        self.back_button = self.ui.back_button
        self.start_competition_button = self.ui.start_competition_button

        self.start_competition_button.clicked.connect(self.on_start_competition)
        
        # === BẮT ĐẦU VÙNG SỬA LỖI ===
        # Thay đổi từ stateChanged sang clicked để đảm bảo logic đơn giản và chính xác hơn
        self.ui.select_all_checkbox.clicked.connect(self.toggle_select_all)
        # === KẾT THÚC VÙNG SỬA LỖI ===

    def on_start_competition(self):
        if not self.get_selected_soldier_ids():
            QMessageBox.warning(self, "Chưa chọn Xạ thủ", "Vui lòng chọn ít nhất một người để bắt đầu thi đấu.")
            return
        self.start_competition_signal.emit()

    def load_soldiers(self):
        self.ui.soldier_list.clear()
        soldiers = self.db.get_all_soldiers()
        if soldiers:
            for soldier in soldiers:
                soldier_widget = SoldierListItemWidget(
                    soldier_id=soldier['id'], name=soldier['name'], class_name=soldier['class_name']
                )
                item = QListWidgetItem(self.ui.soldier_list)
                size_hint = soldier_widget.sizeHint(); size_hint.setHeight(size_hint.height() + 10)
                item.setSizeHint(size_hint)
                
                # Kết nối tín hiệu từ checkbox của từng người lính
                soldier_widget.select_checkbox.stateChanged.connect(self.update_selection_count)
                
                self.ui.soldier_list.addItem(item)
                self.ui.soldier_list.setItemWidget(item, soldier_widget)
        else:
            self.ui.soldier_list.addItem("Chưa có người lính nào trong dữ liệu.")
            
        self.update_selection_count()

    def get_selected_soldier_ids(self) -> list:
        selected_ids = []
        for i in range(self.ui.soldier_list.count()):
            item = self.ui.soldier_list.item(i)
            widget = self.ui.soldier_list.itemWidget(item)
            if widget and isinstance(widget, SoldierListItemWidget) and widget.is_selected():
                selected_ids.append(widget.soldier_id)
        return selected_ids
    
    # === BẮT ĐẦU VÙNG SỬA LỖI ===
    @Slot()
    def toggle_select_all(self):
        """Chọn hoặc bỏ chọn tất cả các mục dựa trên trạng thái của checkbox chính."""
        # Lấy trạng thái hiện tại của checkbox "Chọn tất cả"
        is_checked = self.ui.select_all_checkbox.isChecked()
        
        for i in range(self.ui.soldier_list.count()):
            item = self.ui.soldier_list.item(i)
            widget = self.ui.soldier_list.itemWidget(item)
            if widget and isinstance(widget, SoldierListItemWidget):
                # Tạm khóa tín hiệu để không gọi update_selection_count lặp lại nhiều lần
                widget.select_checkbox.blockSignals(True)
                widget.select_checkbox.setChecked(is_checked)
                widget.select_checkbox.blockSignals(False)
        
        # Cập nhật lại số đếm một lần duy nhất sau khi thay đổi tất cả
        self.update_selection_count()
    # === KẾT THÚC VÙNG SỬA LỖI ===
        
    @Slot()
    def update_selection_count(self):
        """Đếm số mục đã chọn và cập nhật giao diện."""
        selected_count = 0
        total_items = 0
        
        for i in range(self.ui.soldier_list.count()):
            item = self.ui.soldier_list.item(i)
            widget = self.ui.soldier_list.itemWidget(item)
            if widget and isinstance(widget, SoldierListItemWidget):
                total_items += 1
                if widget.is_selected():
                    selected_count += 1
        
        self.ui.selected_count_label.setText(f"Đã chọn: {selected_count}")

        # Đồng bộ trạng thái của checkbox "Chọn tất cả"
        self.ui.select_all_checkbox.blockSignals(True)
        if total_items > 0 and selected_count == total_items:
            self.ui.select_all_checkbox.setChecked(True)
        else:
            self.ui.select_all_checkbox.setChecked(False)
        self.ui.select_all_checkbox.blockSignals(False)