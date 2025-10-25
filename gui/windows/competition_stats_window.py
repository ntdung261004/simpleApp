# file: gui/windows/competition_stats_window.py
import logging
import json
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QListWidgetItem, QTableWidgetItem, QGroupBox,
    QLabel, QGridLayout, QVBoxLayout, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Signal, Slot, Qt, QPoint
from PySide6.QtGui import QFont, QColor, QPixmap, QImage, QPainter
from datetime import datetime

from ..ui.ui_competition_stats import CompetitionStatsGui
from ..ui.ui_saved_competitions import SavedCompetitionItemWidget
from core.database import DatabaseManager
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

# === BẮT ĐẦU VÙNG SỬA ĐỔI: SỬ DỤNG LỚP WIDGET GIỐNG HỆT COMPETITION_WINDOW ===
class SquareImageLabel(QLabel):
    """
    Một QLabel tùy chỉnh với paintEvent được ghi đè để luôn vẽ ảnh
    với tỷ lệ co giãn được giữ nguyên (hình vuông) ở chính giữa.
    Đây là logic được lấy từ ui_competition.py để đảm bảo sự nhất quán.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(50, 50)
        self.setAlignment(Qt.AlignCenter)
        self._pixmap = QPixmap()

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update() # Yêu cầu vẽ lại widget

    def paintEvent(self, event):
        # Không gọi super().paintEvent() vì chúng ta sẽ tự vẽ mọi thứ.
        painter = QPainter(self)
        
        if self._pixmap.isNull():
            # Nếu không có ảnh, hãy để QLabel gốc tự xử lý (ví dụ: vẽ background)
            super().paintEvent(event)
            return

        # Tính toán để vẽ pixmap đã co giãn và căn giữa
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - scaled_pixmap.width()) / 2
        offset_y = (self.height() - scaled_pixmap.height()) / 2
        
        # Vẽ pixmap tại vị trí đã tính toán
        painter.drawPixmap(QPoint(int(offset_x), int(offset_y)), scaled_pixmap)
# === KẾT THÚC VÙNG SỬA ĐỔI ===

class CompetitionStatsWindow(QMainWindow):
    back_to_menu_signal = Signal()
    TARGET_DIMENSIONS = {'bia_4b': (500, 500), 'bia_4c': (500, 500)}

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #2c3e50;")
        self.ui = CompetitionStatsGui()
        self.setCentralWidget(self.ui)
        self.setWindowTitle("Thống kê Kết quả Thi đấu")
        self.db = DatabaseManager()
        self.current_competition_id = None

        self._connect_signals()
        self.set_panels_state("INITIAL")
        self.ui.delete_button.setEnabled(False)

    def _connect_signals(self):
        self.ui.back_button.clicked.connect(self.back_to_menu_signal.emit)
        self.ui.completed_list.itemSelectionChanged.connect(self._on_competition_selected)
        self.ui.ranking_table.itemSelectionChanged.connect(self._on_shooter_selected)
        self.ui.delete_button.clicked.connect(self._delete_competition)

    def enter_view(self):
        self.load_completed_competitions()
        self.set_panels_state("INITIAL")

    def load_completed_competitions(self):
        self.ui.completed_list.clear()
        self.current_competition_id = None
        self.ui.delete_button.setEnabled(False)
        try:
            completed_competitions = self.db.get_completed_competitions()
            if not completed_competitions:
                self.ui.completed_list.addItem("Chưa có phiên thi đấu nào hoàn thành.")
                return

            for comp in completed_competitions:
                try:
                    date_obj = datetime.strptime(comp['created_at'], '%Y-%m-%d %H:%M:%S')
                    date_str = date_obj.strftime('%H:%M - %d/%m/%Y')
                except (ValueError, TypeError): date_str = "Không rõ ngày"
                widget = SavedCompetitionItemWidget(comp['name'], date_str, comp['participant_count'])
                item = QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                item.setData(Qt.UserRole, comp['id'])
                self.ui.completed_list.addItem(item)
                self.ui.completed_list.setItemWidget(item, widget)
        except Exception as e:
            logger.error(f"Lỗi khi tải DS cuộc thi đã hoàn thành: {e}")
            self.ui.completed_list.addItem("Lỗi khi tải dữ liệu.")

    def set_panels_state(self, state: str):
        if state == "INITIAL":
            self.ui.center_stack.setCurrentIndex(0)
            self.ui.right_stack.setCurrentIndex(0)
        elif state == "COMPETITION_SELECTED":
            self.ui.center_stack.setCurrentIndex(1)
            self.ui.right_stack.setCurrentIndex(0)
        elif state == "SHOOTER_SELECTED":
            self.ui.center_stack.setCurrentIndex(1)
            self.ui.right_stack.setCurrentIndex(1)

    @Slot()
    def _on_competition_selected(self):
        selected_items = self.ui.completed_list.selectedItems()
        if not selected_items:
            self.set_panels_state("INITIAL")
            self.current_competition_id = None
            self.ui.delete_button.setEnabled(False)
            return

        item = selected_items[0]
        self.current_competition_id = item.data(Qt.UserRole)
        self.ui.delete_button.setEnabled(True)

        if self.current_competition_id:
            ranking_data = self.db.get_competition_ranking(self.current_competition_id)
            self._populate_ranking_table(ranking_data)
            self.set_panels_state("COMPETITION_SELECTED")

    @Slot()
    def _delete_competition(self):
        if self.current_competition_id is None: return
        selected_items = self.ui.completed_list.selectedItems()
        if not selected_items: return
        
        try:
            item_widget = self.ui.completed_list.itemWidget(selected_items[0])
            competition_name = item_widget.findChild(QLabel, "name_label").text()
        except AttributeError:
            competition_name = "Đã chọn"


        reply = QMessageBox.warning(
            self, "Xác nhận Xóa", f"Bạn có chắc chắn muốn xóa vĩnh viễn phiên kiểm tra:\n\n'{competition_name}'\n\nToàn bộ dữ liệu liên quan sẽ bị mất.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.db.delete_competition(self.current_competition_id):
                QMessageBox.information(self, "Thành công", "Đã xóa phiên kiểm tra thành công.")
                self.load_completed_competitions()
                self.set_panels_state("INITIAL")
            else: QMessageBox.critical(self, "Lỗi", "Không thể xóa phiên kiểm tra khỏi cơ sở dữ liệu.")

    def _populate_ranking_table(self, ranking_data: list):
        self.ui.ranking_table.setRowCount(0)
        rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}

        for i, participant in enumerate(ranking_data):
            rank = i + 1; self.ui.ranking_table.insertRow(i)
            rank_text = rank_icons.get(rank, f"{rank}"); rank_item = QTableWidgetItem(rank_text)
            rank_item.setTextAlignment(Qt.AlignCenter)
            if rank <= 3: rank_item.setFont(QFont("Segoe UI", 16))
            rank_item.setData(Qt.UserRole, participant['soldier_id']); self.ui.ranking_table.setItem(i, 0, rank_item)
            self.ui.ranking_table.setItem(i, 1, QTableWidgetItem(participant['name']))
            self.ui.ranking_table.setItem(i, 2, QTableWidgetItem(participant['class_name']))
            total_score = participant.get('total_score', 0); score_item = QTableWidgetItem(str(total_score))
            score_item.setTextAlignment(Qt.AlignCenter); score_item.setFont(QFont("Segoe UI", 14, QFont.Bold)); score_item.setForeground(QColor("#f1c40f"))
            self.ui.ranking_table.setItem(i, 3, score_item)

    @Slot()
    def _on_shooter_selected(self):
        selected_items = self.ui.ranking_table.selectedItems()
        if not selected_items or self.current_competition_id is None:
            self.set_panels_state("COMPETITION_SELECTED")
            return

        row = self.ui.ranking_table.row(selected_items[0]); shooter_id = self.ui.ranking_table.item(row, 0).data(Qt.UserRole)
        shooter_name = self.ui.ranking_table.item(row, 1).text()
        if shooter_id:
            all_shooter_shots = self.db.get_shots_for_competition(self.current_competition_id, shooter_id)
            all_shooter_shots.sort(key=lambda s: s.get('shot_number', 0))
            self._populate_shooter_details(shooter_name, all_shooter_shots)
            self.set_panels_state("SHOOTER_SELECTED")

    def _clear_grid_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _create_target_image_with_shots(self, target_type: str, shots: list) -> QPixmap:
        image_path = resource_path(f"assets/images/original/bia_{target_type}.png")
        logger.info(f"Thống kê: Đang tải ảnh bia '{target_type}' từ: {image_path}")

        base_image = cv2.imread(image_path)
        if base_image is None:
            logger.error(f"Thống kê: Lỗi nghiêm trọng - Không thể tải ảnh bia gốc tại {image_path}")
            return QPixmap()

        for shot in shots:
            coords_str = shot.get('coords')
            if not coords_str:
                continue
            try:
                coords = json.loads(coords_str)
                if isinstance(coords, list) and len(coords) == 2:
                    draw_point = (int(coords[0]), int(coords[1]))
                    logger.info(f"Thống kê: Đang vẽ vết đạn cho phát bắn số {shot.get('shot_number')} tại {draw_point}")
                    cv2.drawMarker(base_image, draw_point, (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Thống kê: Bỏ qua vẽ vết đạn cho ID {shot.get('id')} do lỗi parse tọa độ: '{coords_str}'")

        rgb_image = cv2.cvtColor(base_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_image)

    def _populate_shooter_details(self, shooter_name: str, all_shots: list):
        self._clear_grid_layout(self.ui.target_details_grid)
        self.ui.shooter_name_label.setText(f"Tên: {shooter_name}")
        
        target_definitions = [
            {'title': "Bia 1 (Bia 4b)", 'shots': all_shots[0:3], 'type': '4b'},
            {'title': "Bia 2 (Bia 4b)", 'shots': all_shots[3:6], 'type': '4b'},
            {'title': "Bia 3 (Bia 4c)", 'shots': all_shots[6:9], 'type': '4c'},
            {'title': "Bia 4 (Bia 4c)", 'shots': all_shots[9:12], 'type': '4c'},
        ]

        for i, target_info in enumerate(target_definitions):
            target_box = QGroupBox(target_info['title'])
            target_box.setAlignment(Qt.AlignCenter)
            box_layout = QVBoxLayout(target_box)

            final_pixmap = self._create_target_image_with_shots(target_info['type'], target_info['shots'])

            # === BẮT ĐẦU VÙNG SỬA ĐỔI: SỬ DỤNG LỚP WIDGET ĐÃ SỬA LỖI MÉO HÌNH ===
            img_label = SquareImageLabel() # Sử dụng lớp mới để đảm bảo khung hình vuông
            img_label.setPixmap(final_pixmap)
            # Không cần setScaledContents(True) vì paintEvent đã xử lý
            # === KẾT THÚC VÙNG SỬA ĐỔI ===

            scores = [shot.get('score', 0) for shot in target_info['shots']]
            score_text = " - ".join(map(str, scores))
            score_label = QLabel(f"Điểm: {score_text} (Tổng: {sum(scores)})")
            score_label.setAlignment(Qt.AlignCenter)
            score_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #f1c40f;")

            box_layout.addWidget(img_label, 1) # Tham số '1' cho phép widget co giãn
            box_layout.addWidget(score_label)

            row, col = divmod(i, 2)
            self.ui.target_details_grid.addWidget(target_box, row, col)