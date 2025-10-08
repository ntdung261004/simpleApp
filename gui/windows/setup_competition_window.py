import base64
from PySide6.QtWidgets import (
    QMainWindow, QListWidgetItem, QMessageBox, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QCheckBox,  QAbstractItemView
)
from PySide6.QtCore import Qt, QSize, QByteArray 
from PySide6.QtGui import QFont, QPixmap

from ..ui.ui_setup_competition import Ui_SetupCompetitionWindow
from core.database import DatabaseManager
from utils.resource_path import resource_path

# LỚP WIDGET TÙY CHỈNH CHO MỖI ITEM TRONG DANH SÁCH
#
class SoldierListItemWidget(QWidget):
    def __init__(self, soldier_id: int, name: str, class_name: str, parent=None):
        super().__init__(parent)
        self.soldier_id = soldier_id
        
        self.setStyleSheet("""
            QWidget { background-color: #34495e; border-radius: 8px; }
            QLabel { background-color: transparent; }
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 15, 15, 15)
        main_layout.setSpacing(20)

        # --- TẢI ICON TỪ FILE ẢNH BẠN VỪA TẠO ---
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        
        # Sử dụng resource_path để lấy đúng đường dẫn đến file icon
        icon_path = resource_path("assets/images/icon/user_icon.png")
        pixmap = QPixmap(icon_path)
        
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setScaledContents(True)
        # ---------------------------------------------

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.name_label = QLabel(name)
        font_name = QFont()
        font_name.setPointSize(12)
        font_name.setBold(True)
        self.name_label.setFont(font_name)
        self.name_label.setStyleSheet("color: #ecf0f1;")
        
        self.class_name_label = QLabel(class_name)
        font_class = QFont()
        font_class.setPointSize(10)
        self.class_name_label.setFont(font_class)
        self.class_name_label.setStyleSheet("color: #bdc3c7;")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.class_name_label)
        
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(QSize(25, 25))
        
        main_layout.addWidget(self.icon_label)
        main_layout.addLayout(info_layout, 1)
        main_layout.addWidget(self.checkbox)
# ==================== KẾT THÚC THÊM MỚI =====================


# Lớp cửa sổ chính (đã được sửa đổi)
class SetupCompetitionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_SetupCompetitionWindow()
        self.ui.setupUi(self)
        
        self.db = DatabaseManager()
        
        self.start_competition_button = self.ui.start_competition_button
        self.back_button = self.ui.back_button
        
        # Tùy chỉnh thêm cho ListWidget để item đẹp hơn
        self.ui.soldier_list.setStyleSheet("""
            QListWidget {
                background-color: #2c3e50; /* Nền của danh sách */
                border: none;
            }
            QListWidget::item {
                background-color: transparent;
                padding: 4px 0px; /* Khoảng cách giữa các item */
                border: none;
            }
            QListWidget::item:selected {
                background-color: transparent; /* Tắt highlight mặc định */
            }
        """)
        self.ui.soldier_list.setSelectionMode(QAbstractItemView.NoSelection) # Tắt chế độ chọn mặc định

    # --- HÀM load_soldiers ĐÃ ĐƯỢC VIẾT LẠI HOÀN TOÀN ---
    def load_soldiers(self):
        """Tải danh sách người lính và hiển thị bằng widget tùy chỉnh."""
        self.ui.soldier_list.clear()
        soldiers = self.db.get_all_soldiers()
        
        if soldiers:
            for soldier in soldiers:
                # 1. Tạo widget tùy chỉnh cho mỗi người lính
                soldier_widget = SoldierListItemWidget(
                    soldier_id=soldier['id'],
                    name=soldier['name'],
                    class_name=soldier['class_name']
                )
                
                # 2. Tạo một QListWidgetItem để làm "vỏ bọc"
                item = QListWidgetItem(self.ui.soldier_list)
                # Đặt kích thước cho vỏ bọc để widget con hiển thị đúng
                size_hint = soldier_widget.sizeHint()
                size_hint.setHeight(size_hint.height() + 10)
                item.setSizeHint(size_hint)
                # ----------------------------------------

                # Thêm vỏ bọc vào danh sách và đặt widget con vào bên trong
                self.ui.soldier_list.addItem(item)
                self.ui.soldier_list.setItemWidget(item, soldier_widget)
        else:
            self.ui.soldier_list.addItem("Chưa có người lính nào trong dữ liệu.")
            
    # --- HÀM get_selected_soldier_ids ĐÃ ĐƯỢC VIẾT LẠI HOÀN TOÀN ---
    def get_selected_soldier_ids(self) -> list:
        """
        Lấy danh sách ID của những người lính được chọn
        dựa trên trạng thái của checkbox.
        """
        selected_ids = []
        for i in range(self.ui.soldier_list.count()):
            item = self.ui.soldier_list.item(i)
            # Lấy lại widget con từ item vỏ bọc
            widget = self.ui.soldier_list.itemWidget(item)
            
            # Kiểm tra xem widget có tồn tại và checkbox có được tích không
            if widget and widget.checkbox.isChecked():
                selected_ids.append(widget.soldier_id)
                
        return selected_ids