# gui/statistics_window.py
import cv2
import os
import numpy as np
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QWidget, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QFont, QIcon
from datetime import datetime

from gui.ui.ui_practice import VideoLabel
logger = logging.getLogger(__name__)
# ======================================================================
# LỚP WIDGET TÙY CHỈNH CHO ITEM TRONG DANH SÁCH
# ======================================================================
class SessionListItemWidget(QWidget):
    def __init__(self, session_data, parent=None):
        super().__init__(parent)
        
        start_time = datetime.strptime(session_data['start_time'], "%Y-%m-%d %H:%M:%S")
        title_text = f"Lần bắn #{session_data['id']}"
        subtitle_text = start_time.strftime("%H:%M ngày %d/%m/%Y")

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)
        self.main_layout.setSpacing(15)

        icon_label = QLabel()
        
        # ======================================================================
        # CHÚ THÍCH: SỬA LỖI Ở ĐÂY
        # Đổi sang dùng icon SP_ArrowRight, một icon tiêu chuẩn và luôn có sẵn.
        # ======================================================================
        try:
            icon = self.style().standardIcon(getattr(self.style(), 'SP_ArrowRight'))
            icon_label.setPixmap(icon.pixmap(QSize(24, 24)))
        except AttributeError:
            # Fallback phòng trường hợp hy hữu
            logger.warning("Không thể tải icon SP_ArrowRight.")


        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")

        subtitle_label = QLabel(subtitle_text)
        subtitle_label.setStyleSheet("color: #bdc3c7;")

        info_layout.addWidget(title_label)
        info_layout.addWidget(subtitle_label)
        info_layout.addStretch()

        self.main_layout.addWidget(icon_label)
        self.main_layout.addLayout(info_layout, 1)
        
class StatisticsWindow(QDialog):
    def __init__(self, db_manager, user_data, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_data = user_data
        self.all_shots_for_session = []

        self.setWindowTitle(f"Thống kê thành tích - {self.user_data['name']}")
        self.setMinimumSize(QSize(1200, 700))

        # ======================================================================
        # STYLESHEET - BỘ GIAO DIỆN MỚI CHO CỬA SỔ
        # ======================================================================
        self.setStyleSheet("""
            QDialog {
                background-color: #34495e; /* Nền xanh xám đậm */
            }
            QGroupBox {
                color: #ecf0f1; /* Chữ trắng ngà */
                font-size: 16px;
                font-weight: bold;
                border: 1px solid #2c3e50;
                border-radius: 8px;
                margin-top: 1ex; /* Khoảng cách phía trên */
                padding: 15px; /* Thêm padding cho nội dung bên trong */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                left: 10px;
            }
            QListWidget {
                background-color: #2c3e50; /* Nền đậm hơn cho danh sách */
                border-radius: 5px;
                border: none;
                padding: 5px;
            }
            /* Bỏ viền giữa các item để widget tùy chỉnh đẹp hơn */
            QListWidget::item {
                border: none; 
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #3498db; /* Xanh dương sáng khi được chọn */
                border-radius: 4px;
            }
            QListWidget::item:!selected:hover {
                background-color: #46627f; /* Màu nền khi di chuột qua */
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #2c3e50;
                color: #bdc3c7; /* Xám bạc */
                padding: 10px 20px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #46627f; /* Nền của tab đang được chọn */
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #2c3e50;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                border-top-right-radius: 8px;
            }
            QLabel {
                color: #ecf0f1;
                font-size: 14px;
            }
            QTableWidget {
                background-color: #2c3e50;
                color: #ecf0f1;
                border-radius: 5px;
                border: none;
                gridline-color: #34495e;
            }
            QHeaderView::section {
                background-color: #46627f;
                color: white;
                padding: 4px;
                border: none;
                font-weight: bold;
            }
        """)

        self.target_info = {
            'Bia số 4': {'path': 'images/original/bia_so_4.png'},
            'Bia số 7': {'path': 'images/original/bia_so_7.png'},
            'Bia số 8': {'path': 'images/original/bia_so_8.png'},
        }

        # --- Layout chính ---
        main_layout = QHBoxLayout(self)
        
        # --- Cột trái: Lịch sử và Thống kê tổng quan ---
        left_panel = QVBoxLayout()
        session_group = QGroupBox("Lịch sử Lần bắn")
        session_layout = QVBoxLayout(session_group)
        self.session_list_widget = QListWidget()
        self.session_list_widget.setSpacing(3) # Thêm khoảng cách giữa các item
        session_layout.addWidget(self.session_list_widget)
        
        stats_group = QGroupBox("Thống kê Tổng quan")
        stats_layout = QVBoxLayout(stats_group)
        self.total_shots_label = QLabel("Tổng số phát: --")
        self.avg_score_label = QLabel("Điểm trung bình: --")
        stats_layout.addWidget(self.total_shots_label)
        stats_layout.addWidget(self.avg_score_label)
        left_panel.addWidget(session_group, 3)
        left_panel.addWidget(stats_group, 1)

        # --- Cột phải: Phân tích độ chụm theo từng loại bia ---
        right_panel = QGroupBox("Phân tích Độ chụm")
        right_layout = QVBoxLayout(right_panel)
        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)
        
        for target_name in self.target_info.keys():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            shot_grouping_label = VideoLabel(parent=tab)
            shot_grouping_label.setText(f"Chưa có phát bắn nào trúng {target_name}")
            tab_layout.addWidget(shot_grouping_label)
            self.tabs.addTab(tab, target_name)

        main_layout.addLayout(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

        # --- Kết nối tín hiệu ---
        self.session_list_widget.currentItemChanged.connect(self.on_session_selected)
        self.populate_session_list()

    def populate_session_list(self):
        """Sử dụng widget tùy chỉnh để hiển thị danh sách."""
        self.session_list_widget.clear()
        sessions = self.db_manager.get_sessions_for_user(self.user_data['id'])
        if not sessions:
            self.session_list_widget.addItem("Chưa có dữ liệu lần bắn nào.")
            return

        for session in sessions:
            list_item = QListWidgetItem(self.session_list_widget)
            list_item.setData(Qt.UserRole, session)
            item_widget = SessionListItemWidget(session)
            list_item.setSizeHint(item_widget.sizeHint())
            self.session_list_widget.setItemWidget(list_item, item_widget)
    
    def on_session_selected(self, current_item, previous_item):
        if not current_item:
            return
        session_data = current_item.data(Qt.UserRole)
        if session_data is None:
            print("Không có dữ liệu phiên bắn được chọn.")
        # Bạn có thể thêm code để xóa hiển thị cũ ở đây nếu cần
            return # Thoát khỏi hàm sớm để tránh lỗi
        
        self.all_shots_for_session = self.db_manager.get_shots_for_session(session_data['id'])
        self.update_statistics()
        self.update_shot_grouping_tabs()

    def update_statistics(self):
        total_shots = len(self.all_shots_for_session)
        if total_shots > 0:
            total_score = sum(shot['score'] for shot in self.all_shots_for_session)
            avg_score = total_score / total_shots
            self.total_shots_label.setText(f"Tổng số phát: {total_shots}")
            self.avg_score_label.setText(f"Điểm trung bình: {avg_score:.2f}")
        else:
            self.total_shots_label.setText("Tổng số phát: 0")
            self.avg_score_label.setText("Điểm trung bình: 0.0")

    def update_shot_grouping_tabs(self):
        for index, (target_name, info) in enumerate(self.target_info.items()):
            tab_widget = self.tabs.widget(index)
            if not tab_widget: continue
            label_to_update = tab_widget.findChild(VideoLabel)
            if not label_to_update: continue
            
            shots_for_this_target = [
                s for s in self.all_shots_for_session if s['target_name'] == target_name
            ]
            
            hit_count = len(shots_for_this_target)
            self.tabs.setTabText(index, f"{target_name} ({hit_count} trúng)")
            
            self.draw_shot_grouping_on_label(label_to_update, shots_for_this_target, info['path'])

    def draw_shot_grouping_on_label(self, label: VideoLabel, shots: list, image_path: str):
        if not os.path.exists(image_path):
            label.setText(f"Lỗi: Không tìm thấy ảnh gốc tại {image_path}")
            return
        
        target_image = cv2.imread(image_path)
        
        if not shots:
            pass
        else:
            for shot in shots:
                coords = shot.get('coords')
                if coords and coords[0] is not None:
                    point = (int(coords[0]), int(coords[1]))
                    cv2.drawMarker(target_image, point, (50, 50, 255), cv2.MARKER_CROSS, 25, 2)
        
        rgb_image = cv2.cvtColor(target_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        label.setPixmap(pixmap)