# file: gui/windows/saved_competitions_window.py
import logging
from PySide6.QtWidgets import QMainWindow, QListWidgetItem, QMessageBox
from PySide6.QtCore import Signal, Slot, Qt
from datetime import datetime
import json

from ..ui.ui_saved_competitions import SavedCompetitionsGui, SavedCompetitionItemWidget
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class SavedCompetitionsWindow(QMainWindow):
    resume_competition_signal = Signal(dict)
    back_to_menu_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #2c3e50;")
        self.ui = SavedCompetitionsGui()
        self.setCentralWidget(self.ui)
        self.setWindowTitle("Các Phiên Thi Đấu Đã Lưu")
        self.db = DatabaseManager()
        self.current_selected_id = None
        self._connect_signals()

    def _connect_signals(self):
        self.ui.competition_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.ui.continue_button.clicked.connect(self._resume_competition)
        self.ui.delete_button.clicked.connect(self._delete_competition)
        self.ui.back_button.clicked.connect(self.back_to_menu_signal.emit)

    def enter_view(self):
        """Hàm được gọi mỗi khi màn hình này được hiển thị."""
        self.load_competitions()

    def load_competitions(self):
        """Tải danh sách các cuộc thi đang diễn ra từ CSDL và hiển thị."""
        self.ui.competition_list.clear()
        self.current_selected_id = None
        self._on_selection_changed() # Cập nhật trạng thái nút bấm

        try:
            saved_competitions = self.db.get_saved_competitions()
            if not saved_competitions:
                self.ui.competition_list.addItem("Không có phiên thi đấu nào đang diễn ra.")
                return

            for comp in saved_competitions:
                try:
                    date_obj = datetime.strptime(comp['created_at'], '%Y-%m-%d %H:%M:%S')
                    date_str = date_obj.strftime('%H:%M - %d/%m/%Y')
                except (ValueError, TypeError):
                    date_str = "Không rõ ngày"

                widget = SavedCompetitionItemWidget(
                    name=comp['name'],
                    date=date_str,
                    participants=comp['participant_count']
                )
                item = QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                # Lưu ID của cuộc thi vào item để truy xuất sau này
                item.setData(Qt.UserRole, comp['id'])
                self.ui.competition_list.addItem(item)
                self.ui.competition_list.setItemWidget(item, widget)

        except Exception as e:
            logger.error(f"Lỗi khi tải danh sách cuộc thi đã lưu: {e}")
            self.ui.competition_list.addItem("Lỗi khi tải dữ liệu từ database.")

    @Slot()
    def _on_selection_changed(self):
        """Kích hoạt/Vô hiệu hóa các nút dựa trên việc có item nào được chọn không."""
        selected_items = self.ui.competition_list.selectedItems()
        is_item_selected = bool(selected_items)
        
        self.ui.continue_button.setEnabled(is_item_selected)
        self.ui.delete_button.setEnabled(is_item_selected)

        if is_item_selected:
            self.current_selected_id = selected_items[0].data(Qt.UserRole)
        else:
            self.current_selected_id = None

    @Slot()
    def _resume_competition(self):
        """Xử lý khi nhấn nút 'Tiếp tục'."""
        if self.current_selected_id is None:
            return

        competition_data = self.db.get_competition(self.current_selected_id)
        if not competition_data:
            QMessageBox.critical(self, "Lỗi", "Không tìm thấy dữ liệu của cuộc thi này.")
            self.load_competitions() # Tải lại vì có thể nó đã bị xóa
            return
            
        state_json = competition_data.get('state')
        if not state_json:
            QMessageBox.critical(self, "Lỗi Dữ liệu", "Cuộc thi này không có trạng thái đã lưu hợp lệ.")
            return

        try:
            state_dict = json.loads(state_json)
            self.resume_competition_signal.emit(state_dict)
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Lỗi Dữ liệu", "Không thể đọc trạng thái đã lưu của cuộc thi.")

    @Slot()
    def _delete_competition(self):
        """Xử lý khi nhấn nút 'Xóa'."""
        if self.current_selected_id is None:
            return

        reply = QMessageBox.warning(
            self,
            "Xác nhận Xóa",
            "Bạn có chắc chắn muốn xóa vĩnh viễn phiên thi đấu này không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.db.delete_competition(self.current_selected_id)
            if success:
                QMessageBox.information(self, "Thành công", "Đã xóa phiên thi đấu.")
                self.load_competitions() # Tải lại danh sách
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xóa phiên thi đấu khỏi database.")