# file: gui/windows/setup_competition_window.py
import base64
from PySide6.QtWidgets import (
    QMainWindow, QListWidgetItem, QMessageBox, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QCheckBox,  QAbstractItemView
)
# === THAY ĐỔI 1: Import thêm 'Signal' ===
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QPixmap

from ..ui.ui_setup_competition import Ui_SetupCompetitionWindow
from core.database import DatabaseManager
from utils.resource_path import resource_path

# Lớp SoldierListItemWidget (Giữ nguyên)
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
        self.name_label = QLabel(name); self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ecf0f1;")
        self.class_name_label = QLabel(class_name); self.class_name_label.setStyleSheet("font-size: 13px; color: #bdc3c7;")
        info_layout.addWidget(self.name_label); info_layout.addWidget(self.class_name_label)
        self.checkbox = QCheckBox(); self.checkbox.setFixedSize(QSize(30, 30))
        main_layout.addWidget(self.icon_label); main_layout.addLayout(info_layout, 1); main_layout.addWidget(self.checkbox)
    def is_selected(self) -> bool:
        return self.checkbox.isChecked()


class SetupCompetitionWindow(QMainWindow):
    # === THAY ĐỔI 2: Định nghĩa Signal tùy chỉnh ===
    # Tín hiệu này sẽ được phát ra sau khi nút "Bắt đầu" được nhấn và đã kiểm tra hợp lệ
    start_competition_signal = Signal()
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_SetupCompetitionWindow()
        self.ui.setupUi(self)
        self.db = DatabaseManager()
        
        # Kết nối nút bấm với hàm xử lý nội bộ
        self.ui.start_competition_button.clicked.connect(self.handle_start_button)
        # Gán nút back để main.py kết nối
        self.back_button = self.ui.back_button

    def handle_start_button(self):
        """
        Hàm này được gọi khi nút 'Bắt đầu Thi đấu' được nhấn.
        Nó sẽ kiểm tra xem có ai được chọn không, sau đó mới phát tín hiệu.
        """
        if not self.get_selected_soldier_ids():
            QMessageBox.warning(self, "Chưa chọn Xạ thủ", "Vui lòng chọn ít nhất một người để bắt đầu thi đấu.")
            return # Không phát tín hiệu nếu chưa chọn ai
            
        # Nếu đã có người được chọn, phát tín hiệu để main.py xử lý
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
                self.ui.soldier_list.addItem(item)
                self.ui.soldier_list.setItemWidget(item, soldier_widget)
        else:
            self.ui.soldier_list.addItem("Chưa có người lính nào trong dữ liệu.")
            
    def get_selected_soldier_ids(self) -> list:
        selected_ids = []
        for i in range(self.ui.soldier_list.count()):
            item = self.ui.soldier_list.item(i)
            widget = self.ui.soldier_list.itemWidget(item)
            if widget and hasattr(widget, 'is_selected') and widget.is_selected():
                selected_ids.append(widget.soldier_id)
        return selected_ids