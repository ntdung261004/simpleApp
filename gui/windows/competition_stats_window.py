# file: gui/windows/competition_stats_window.py
import logging
import json
from PySide6.QtWidgets import (
    QMainWindow, QListWidgetItem, QTableWidgetItem, QGroupBox, 
    QLabel, QGridLayout, QVBoxLayout
)
from PySide6.QtCore import Signal, Slot, Qt, QPoint
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QPen
from datetime import datetime

from ..ui.ui_competition_stats import CompetitionStatsGui
from ..ui.ui_saved_competitions import SavedCompetitionItemWidget
from core.database import DatabaseManager
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

# === BẮT ĐẦU VÙNG THAY ĐỔI: THÊM WIDGET VẼ VỆT ĐẠN ===
class ShotMarkerLabel(QLabel):
    """Một QLabel tùy chỉnh để hiển thị ảnh bia và vẽ các vệt đạn lên trên."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._pixmap = QPixmap()
        self.hit_points_relative = []

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def add_hit_marker(self, relative_point: tuple[float, float]):
        if relative_point:
            self.hit_points_relative.append(relative_point)
            self.update()

    def clear_hit_markers(self):
        self.hit_points_relative.clear()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if self._pixmap.isNull(): return

        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        offset_x = (self.width() - scaled_pixmap.width()) / 2
        offset_y = (self.height() - scaled_pixmap.height()) / 2
        painter.drawPixmap(QPoint(int(offset_x), int(offset_y)), scaled_pixmap)

        pen = QPen(QColor("#e74c3c"))
        pen.setWidth(2)
        painter.setPen(pen)
        
        for rel_x, rel_y in self.hit_points_relative:
            draw_x = offset_x + (rel_x * scaled_pixmap.width())
            draw_y = offset_y + (rel_y * scaled_pixmap.height())
            marker_size = 5
            painter.drawLine(int(draw_x - marker_size), int(draw_y), int(draw_x + marker_size), int(draw_y))
            painter.drawLine(int(draw_x), int(draw_y - marker_size), int(draw_x), int(draw_y + marker_size))
# === KẾT THÚC VÙNG THAY ĐỔI ===


class CompetitionStatsWindow(QMainWindow):
    back_to_menu_signal = Signal()
    TARGET_DIMENSIONS = {'bia_4b': (500, 500), 'bia_4c': (500, 500)}

    def __init__(self):
        super().__init__()
        self.ui = CompetitionStatsGui()
        self.setCentralWidget(self.ui)
        self.setWindowTitle("Thống kê Kết quả Thi đấu")
        self.db = DatabaseManager()
        self.current_competition_id = None

        self._connect_signals()
        self.set_panels_state("INITIAL")

    def _connect_signals(self):
        self.ui.back_button.clicked.connect(self.back_to_menu_signal.emit)
        self.ui.completed_list.itemSelectionChanged.connect(self._on_competition_selected)
        # === BẮT ĐẦU VÙNG THAY ĐỔI ===
        self.ui.ranking_table.itemSelectionChanged.connect(self._on_shooter_selected)
        # === KẾT THÚC VÙNG THAY ĐỔI ===

    def enter_view(self):
        self.load_completed_competitions()
        self.set_panels_state("INITIAL")

    def load_completed_competitions(self):
        self.ui.completed_list.clear()
        self.current_competition_id = None
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
            return
        
        item = selected_items[0]
        self.current_competition_id = item.data(Qt.UserRole)
        
        if self.current_competition_id:
            ranking_data = self.db.get_competition_ranking(self.current_competition_id)
            self._populate_ranking_table(ranking_data)
            self.set_panels_state("COMPETITION_SELECTED")

    def _populate_ranking_table(self, ranking_data: list):
        self.ui.ranking_table.setRowCount(0)
        rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}

        for i, participant in enumerate(ranking_data):
            rank = i + 1
            self.ui.ranking_table.insertRow(i)
            rank_text = rank_icons.get(rank, f"{rank}")
            rank_item = QTableWidgetItem(rank_text)
            rank_item.setTextAlignment(Qt.AlignCenter)
            if rank <= 3: rank_item.setFont(QFont("Segoe UI", 16))
            rank_item.setData(Qt.UserRole, participant['soldier_id'])
            self.ui.ranking_table.setItem(i, 0, rank_item)
            self.ui.ranking_table.setItem(i, 1, QTableWidgetItem(participant['name']))
            self.ui.ranking_table.setItem(i, 2, QTableWidgetItem(participant['class_name']))
            total_score = participant.get('total_score', 0)
            score_item = QTableWidgetItem(str(total_score))
            score_item.setTextAlignment(Qt.AlignCenter)
            score_item.setFont(QFont("Segoe UI", 14, QFont.Bold))
            score_item.setForeground(QColor("#f1c40f"))
            self.ui.ranking_table.setItem(i, 3, score_item)
    
    # === BẮT ĐẦU VÙNG THAY ĐỔI: LOGIC HIỂN THỊ CHI TIẾT ===
    @Slot()
    def _on_shooter_selected(self):
        """Xử lý khi người dùng chọn một xạ thủ từ bảng xếp hạng."""
        selected_items = self.ui.ranking_table.selectedItems()
        if not selected_items or self.current_competition_id is None:
            self.set_panels_state("COMPETITION_SELECTED")
            return
            
        row = self.ui.ranking_table.row(selected_items[0])
        shooter_id = self.ui.ranking_table.item(row, 0).data(Qt.UserRole)
        shooter_name = self.ui.ranking_table.item(row, 1).text()
        
        if shooter_id:
            shooter_shots = self.db.get_shots_for_competition(self.current_competition_id, shooter_id)
            self._populate_shooter_details(shooter_name, shooter_shots)
            self.set_panels_state("SHOOTER_SELECTED")

    def _clear_grid_layout(self, layout):
        """Xóa tất cả widget khỏi một QGridLayout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _populate_shooter_details(self, shooter_name: str, shots: list):
        """Điền dữ liệu chi tiết của xạ thủ vào cột bên phải."""
        self._clear_grid_layout(self.ui.target_details_grid)
        self.ui.shooter_name_label.setText(f"Tên: {shooter_name}")
        
        # Nhóm 12 phát bắn vào 4 bia
        targets = [shots[i:i + 3] for i in range(0, len(shots), 3)]
        
        for i, target_shots in enumerate(targets):
            target_num = i + 1
            is_4c = target_num > 2
            
            target_box = QGroupBox(f"Bia số {target_num}")
            target_box.setAlignment(Qt.AlignCenter)
            box_layout = QVBoxLayout(target_box)
            
            # Label ảnh bia
            img_label = ShotMarkerLabel()
            img_path = resource_path(f"assets/images/original/bia_{'4c' if is_4c else '4b'}.png")
            img_label.setPixmap(QPixmap(img_path))

            scores = []
            for shot in target_shots:
                scores.append(shot['score'])
                coords_str = shot.get('coords')
                if coords_str:
                    try:
                        coords = json.loads(coords_str)
                        target_name_raw = shot.get('target_detected', 'bia_4b' if not is_4c else 'bia_4c')
                        orig_w, orig_h = self.TARGET_DIMENSIONS.get(target_name_raw, (500, 500))
                        if coords and orig_w > 0 and orig_h > 0:
                            relative_coords = (coords[0] / orig_w, coords[1] / orig_h)
                            img_label.add_hit_marker(relative_coords)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Không thể parse tọa độ cho phát bắn: {shot['id']}")

            # Label điểm
            score_text = " - ".join(map(str, scores))
            score_label = QLabel(f"Điểm: {score_text} (Tổng: {sum(scores)})")
            score_label.setAlignment(Qt.AlignCenter)
            score_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #f1c40f;")
            
            box_layout.addWidget(img_label, 1)
            box_layout.addWidget(score_label)
            
            # Thêm vào grid layout
            row, col = divmod(i, 2)
            self.ui.target_details_grid.addWidget(target_box, row, col)
    # === KẾT THÚC VÙNG THAY ĐỔI ===