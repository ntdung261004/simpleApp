# file: gui/windows/manage_window.py

import logging
import numpy as np
import cv2
import os
import pandas as pd
import unicodedata
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QDialog, QFormLayout, QLineEdit,
    QDialogButtonBox, QMessageBox, QTableWidgetItem,
    QVBoxLayout, QWidget, QCheckBox, QHBoxLayout, QPushButton,
    QMenu, QFileDialog, QHeaderView, QLabel, QTableWidget, QSizePolicy,
    QInputDialog, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QColor, QFont

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from gui.ui.ui_manage import ManageGui
from gui.dialogs import PersonalProcessDialog
from core.database import DatabaseManager
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

# =============================================================================
# === CÁC CLASS DIALOG HỖ TRỢ (ĐÃ TỐI ƯU SCALE) ===
# =============================================================================

class ExcelPreviewDialog(QDialog):
    def __init__(self, data_list, parent=None):
        super().__init__(parent)
        # --- SCALING ---
        screen = QApplication.primaryScreen().availableGeometry()
        self.scale_factor = screen.height() / 1080.0
        def s(val): return int(val * self.scale_factor)
        # ---------------

        self.setWindowTitle("Xác nhận nhập dữ liệu")
        self.setMinimumSize(s(700), s(500))
        self.data_list = data_list

        layout = QVBoxLayout(self)
        lbl_info = QLabel(f"<b>Đã tìm thấy {len(data_list)} bản ghi.</b><br>"
                          "Vui lòng kiểm tra kỹ danh sách bên dưới trước khi nhập.")
        lbl_info.setStyleSheet(f"font-size: {s(14)}px; margin-bottom: 10px;")
        layout.addWidget(lbl_info)

        self.table = QTableWidget(len(data_list), 3)
        self.table.setHorizontalHeaderLabels(["Chọn", "Họ và Tên", "Đơn vị"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setStyleSheet(f"font-size: {s(14)}px;")
        
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
        
        btn_style = f"font-size: {s(14)}px; padding: 5px;"
        btn_all.setStyleSheet(btn_style); btn_none.setStyleSheet(btn_style)
        
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet(f"QPushButton {{ font-size: {s(14)}px; padding: 5px; }}")
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
        # --- SCALING ---
        screen = QApplication.primaryScreen().availableGeometry()
        self.scale_factor = screen.height() / 1080.0
        def s(val): return int(val * self.scale_factor)
        # ---------------

        self.config = config
        labels = self.config.get("labels", {})
        title = labels.get("edit_trainee_dialog_title", "Chỉnh sửa thông tin") if is_edit_mode else labels.get("add_trainee_dialog_title", "Thêm mới")
        self.setWindowTitle(title)
        self.setMinimumWidth(s(400))
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: #34495e; }}
            QLabel {{ color: #ecf0f1; font-size: {s(14)}px; }}
            QLineEdit {{ background-color: #2c3e50; border: 1px solid #4a6278; border-radius: 6px; padding: {s(8)}px; color: #ecf0f1; font-size: {s(14)}px; }}
            QLineEdit:focus {{ border: 1px solid #1abc9c; }}
            QPushButton {{ background-color: #1abc9c; color: white; font-size: {s(14)}px; font-weight: bold; border: none; padding: {s(8)}px {s(18)}px; border-radius: {s(8)}px; }}
            QPushButton:hover {{ background-color: #16a085; }}
            QPushButton[objectName="cancelButton"] {{ background-color: #95a5a6; }}
            QPushButton[objectName="cancelButton"]:hover {{ background-color: #7f8c8d; }}
        """)
        
        main_layout = QVBoxLayout(self)
        title_label = QLabel(self.windowTitle())
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"font-size: {s(18)}px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.name_input = QLineEdit()
        self.class_name_input = QLineEdit()
        self.inputs = [self.name_input, self.class_name_input]
        
        form_layout.addRow(labels.get("trainee_name_prompt", "Họ và Tên:"), self.name_input)
        form_layout.addRow(labels.get("trainee_class_prompt", "Đơn vị:"), self.class_name_input)
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
        if self.name_input.text().strip(): self.accept()
        else:
            self.inputs[0].setStyleSheet(self.error_style)
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền Họ và Tên.")

# =============================================================================
# === MANAGE WINDOW - LOGIC CHÍNH ===
# =============================================================================
class ManageWindow(QMainWindow):
    back_to_menu_signal = Signal()

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setWindowTitle(self.config.get("labels", {}).get("app_title", "Quản lý"))
        self.ui = ManageGui(self.config)
        self.setCentralWidget(self.ui)
        self.db = DatabaseManager()
        self.current_detail_data = [] 
        self.current_session_mode = "SINGLE"
        self.current_practice_session_id = None
        self.all_soldiers_data = [] # Cache dữ liệu
        
        # Matplotlib Figure (General Report)
        self.figure = Figure(figsize=(8, 4), dpi=100, facecolor='#2c3e50')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: transparent;")
        self.ui.charts_layout.addWidget(self.canvas)

        # Matplotlib Figure (Personal Stats) - NEW
        self.p_figure = Figure(figsize=(6, 3), dpi=100, facecolor='#2c3e50')
        self.p_canvas = FigureCanvas(self.p_figure)
        self.p_canvas.setStyleSheet("background-color: transparent;")
        self.ui.personal_chart_layout.addWidget(self.p_canvas)
        
        self.current_viewing_soldier_id = None

        self.connect_signals()
        self.show_menu()

    def connect_signals(self):
        self.ui.btn_menu_trainees.clicked.connect(self.show_trainee_list)
        self.ui.btn_menu_sessions.clicked.connect(self.show_session_report)
        self.ui.btn_back_main.clicked.connect(self.back_to_menu_signal.emit)
        
        self.ui.btn_add_trainee.clicked.connect(self.open_add_soldier_dialog)
        self.ui.btn_import_excel.clicked.connect(self.import_excel_handler)
        self.ui.btn_back_to_menu.clicked.connect(self.show_menu)
        
        # Filter & Sort
        self.ui.search_box.textChanged.connect(self.reload_soldier_table_view)
        self.ui.cmb_filter_unit.currentIndexChanged.connect(self.reload_soldier_table_view)
        self.ui.cmb_sort_trainees.currentIndexChanged.connect(self.reload_soldier_table_view)
        
        # Table interactions
        self.ui.soldier_table.itemSelectionChanged.connect(self.on_soldier_selection_changed)
        self.ui.btn_note.clicked.connect(self.on_edit_note_clicked)
        
        self.ui.soldier_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.soldier_table.customContextMenuRequested.connect(self.show_soldier_context_menu)
        
        # Session List
        self.ui.btn_back_from_session.clicked.connect(self.show_menu)
        self.ui.session_table.itemSelectionChanged.connect(self.on_session_selection_changed)
        self.ui.btn_view_report.clicked.connect(self.show_session_detail)
        self.ui.btn_delete_session.clicked.connect(self.on_delete_session_clicked)

        # Session Detail
        self.ui.btn_back_to_session_list.clicked.connect(self.show_session_report)
        self.ui.cmb_sort.currentIndexChanged.connect(self.sort_session_detail)
        self.ui.detail_table.itemSelectionChanged.connect(self.on_detail_selection_changed)
        self.ui.btn_view_personal.clicked.connect(self.on_view_personal_process)
        self.ui.cmb_view_mode.currentIndexChanged.connect(self.toggle_view_mode)
        
        # Personal Stats (NEW)
        self.ui.btn_personal_stats.clicked.connect(self.on_view_personal_stats_clicked)
        self.ui.btn_back_from_personal.clicked.connect(self.show_trainee_list)
        self.ui.btn_save_p_note.clicked.connect(self.save_personal_note_direct)
        
        # Kết nối ComboBox lọc chế độ trong trang cá nhân
        self.ui.cmb_stats_filter.currentIndexChanged.connect(self.refresh_personal_stats_view)

    # --- NAVIGATION ---
    def show_menu(self): self.ui.main_stack.setCurrentWidget(self.ui.page_menu)
    def show_trainee_list(self): self.ui.main_stack.setCurrentWidget(self.ui.page_trainees); self.load_soldiers()
    def show_session_report(self): 
        self.ui.main_stack.setCurrentWidget(self.ui.page_sessions)
        self.load_session_history()
        self.ui.btn_view_report.setEnabled(False)
        self.ui.btn_delete_session.setEnabled(False)

    # --- THỐNG KÊ CÁ NHÂN (LOGIC MỚI) ---
    def on_view_personal_stats_clicked(self):
        selected_rows = self.ui.soldier_table.selectedItems()
        if not selected_rows: return
        row = selected_rows[0].row()
        
        # Lấy ID và thông tin cơ bản
        soldier_id = self.ui.soldier_table.item(row, 0).data(Qt.UserRole)
        name = self.ui.soldier_table.item(row, 1).text()
        unit = self.ui.soldier_table.item(row, 2).text()
        note = self.ui.soldier_table.item(row, 3).text()
        
        # Lấy lịch sử từ DB
        self.current_history_cache = self.db.get_soldier_history(soldier_id)
        
        self.current_viewing_soldier_id = soldier_id
        
        # Setup UI
        self.ui.lbl_personal_name.setText(f"{name.upper()} - {unit}")
        self.ui.txt_personal_note.setPlainText(note)
        
        # Reset Filter về SINGLE
        self.ui.cmb_stats_filter.blockSignals(True)
        self.ui.cmb_stats_filter.setCurrentIndex(0)
        self.ui.cmb_stats_filter.blockSignals(False)
        
        self.refresh_personal_stats_view()
        self.ui.main_stack.setCurrentWidget(self.ui.page_personal_stats)

    def refresh_personal_stats_view(self):
        """Hàm vẽ lại giao diện thống kê dựa trên chế độ đang chọn (Single/Burst)"""
        mode_filter = self.ui.cmb_stats_filter.currentData() # "SINGLE" or "BURST_3"
        
        # Lọc dữ liệu theo chế độ
        filtered_history = [h for h in self.current_history_cache if h['mode'] == mode_filter] if self.current_history_cache else []
        
        # --- A. CẬP NHẬT BẢNG LỊCH SỬ ---
        self.ui.personal_table.setRowCount(len(filtered_history))
        scores_for_chart = []
        dates_for_chart = []
        
        total_score_accum = 0
        
        for i, h in enumerate(filtered_history):
            date_str = datetime.strptime(h['created_at'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m")
            sc = h['total_score']
            cnt = h['shot_count']
            
            # Tính giá trị hiển thị
            if mode_filter == "BURST_3":
                res_str = f"{sc} điểm / 30"
                chart_val = sc
            else: # SINGLE
                avg = sc / cnt if cnt > 0 else 0
                res_str = f"{avg:.1f} điểm/phát ({cnt} viên)"
                chart_val = avg
                
            scores_for_chart.append(chart_val)
            dates_for_chart.append(date_str)
            total_score_accum += chart_val
            
            self.ui.personal_table.setItem(i, 0, QTableWidgetItem(date_str))
            self.ui.personal_table.setItem(i, 1, QTableWidgetItem(h['session_name']))
            self.ui.personal_table.setItem(i, 2, QTableWidgetItem(res_str))

        # --- B. CẬP NHẬT THẺ CHỈ SỐ VÀ ĐÁNH GIÁ (LOGIC TINH CHỈNH) ---
        count = len(filtered_history)
        self.ui.lbl_p_sessions.setText(f"{count} lần")

        if mode_filter == "BURST_3":
            self.ui.lbl_p_avg.parent().findChild(QLabel).setText("ĐIỂM TB / LOẠT")
        else:
            self.ui.lbl_p_avg.parent().findChild(QLabel).setText("ĐIỂM TB / PHÁT")

        # --- XỬ LÝ CÁC TRƯỜNG HỢP DỮ LIỆU ---
        eval_msg = ""; level_msg = ""
        MIN_DATA_THRESHOLD = 3 

        if count == 0:
            self.ui.lbl_p_avg.setText("--")
            self.ui.lbl_p_best.setText("--")
            self.ui.lbl_p_eval.setText(f"ℹ Chưa có dữ liệu tập luyện ở chế độ {mode_filter}.\nHãy thực hiện các bài bắn để hệ thống bắt đầu ghi nhận và phân tích thành tích.")
            self.p_figure.clear()
            self.p_canvas.draw()
            return

        avg_global = total_score_accum / count
        best_val = max(scores_for_chart)
        
        if mode_filter == "BURST_3":
            self.ui.lbl_p_avg.setText(f"{avg_global:.1f}")
            self.ui.lbl_p_best.setText(f"{best_val}")
        else:
            self.ui.lbl_p_avg.setText(f"{avg_global:.2f}")
            self.ui.lbl_p_best.setText(f"{best_val:.2f}")

        if count < MIN_DATA_THRESHOLD:
            missing = MIN_DATA_THRESHOLD - count
            eval_msg = "📊 Đang thu thập dữ liệu cơ sở."
            level_msg = f"Cần tập luyện thêm {missing} buổi nữa để hệ thống có đủ dữ liệu vẽ biểu đồ tiến độ và đánh giá trình độ khách quan hơn."
            self.ui.lbl_p_eval.setText(f"{eval_msg}\n{level_msg}")
        else:
            recent = scores_for_chart[-3:] 
            trend = recent[-1] - recent[0]
            if trend > 0.5: eval_msg = "📈 Đang có sự TIẾN BỘ trong các buổi tập gần đây."
            elif trend < -0.5: eval_msg = "📉 Phong độ đang ĐI XUỐNG, cần ổn định tâm lý và yếu lĩnh."
            else: eval_msg = "➡ Phong độ ỔN ĐỊNH."

            if mode_filter == "BURST_3":
                if avg_global >= 23: level_msg = "Khả năng ghìm súng RẤT TỐT (Giỏi)."
                elif avg_global >= 19: level_msg = "Khả năng ghìm súng TỐT (Khá)."
                elif avg_global >= 15: level_msg = "Khả năng ghìm súng ĐẠT YÊU CẦU."
                else: level_msg = "Yếu lĩnh ghìm súng còn YẾU (Hay giật), cần rèn luyện thêm."
            else:
                if avg_global >= 8.0: level_msg = "Đường ngắm rất chính xác (Giỏi)."
                elif avg_global >= 6.5: level_msg = "Đường ngắm khá (Khá)."
                elif avg_global >= 5.0: level_msg = "Đường ngắm đạt yêu cầu."
                else: level_msg = "Đường ngắm chưa chuẩn (Yếu), cần tập ke đường ngắm cơ bản."
            
            self.ui.lbl_p_eval.setText(f"{eval_msg}\n{level_msg}")

        # --- D. VẼ BIỂU ĐỒ ---
        self.p_figure.clear()
        ax = self.p_figure.add_subplot(111)
        line_color = '#3498db' if mode_filter == "SINGLE" else '#e67e22'
        y_limit = 10 if mode_filter == "SINGLE" else 30
        ax.plot(range(len(scores_for_chart)), scores_for_chart, marker='o', linestyle='-', color=line_color, linewidth=2)
        ax.set_xticks(range(len(dates_for_chart)))
        ax.set_xticklabels(dates_for_chart, color='white', rotation=0, fontsize=8)
        title_chart = "BIỂU ĐỒ TIẾN ĐỘ" if count >= MIN_DATA_THRESHOLD else "BIỂU ĐỒ KẾT QUẢ (Dữ liệu ban đầu)"
        ax.set_title(title_chart, color='white', fontsize=10)
        ax.set_ylim(0, y_limit + (y_limit*0.1))
        ax.tick_params(colors='white')
        ax.grid(True, linestyle='--', alpha=0.3)
        for x, y in enumerate(scores_for_chart):
            ax.text(x, y + (y_limit*0.02), f"{y:.1f}" if mode_filter == "SINGLE" else f"{int(y)}", 
                    color='white', ha='center', fontsize=8)
        self.p_canvas.draw()

    def save_personal_note_direct(self):
        if self.current_viewing_soldier_id is None: return
        text = self.ui.txt_personal_note.toPlainText().strip()
        if self.db.update_soldier_note(self.current_viewing_soldier_id, text):
            QMessageBox.information(self, "Đã lưu", "Cập nhật ghi chú thành công.")
            self.ui.txt_personal_note.clear() 
            for s in self.all_soldiers_data:
                if s['id'] == self.current_viewing_soldier_id:
                    s['note'] = text
                    break
        else:
            QMessageBox.warning(self, "Lỗi", "Không thể lưu ghi chú.")

    # --- BÁO CÁO PHIÊN TẬP (LIST) ---
    def load_session_history(self):
        self.ui.session_table.setRowCount(0)
        try:
            sessions = self.db.get_finished_practice_sessions()
            if not sessions: return
            self.ui.session_table.setRowCount(len(sessions))
            for row, s in enumerate(sessions):
                date_str = s.get('created_at', '')
                try: dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S"); date_display = dt.strftime("%d/%m/%Y %H:%M")
                except: date_display = date_str
                mode_raw = s.get('mode', 'SINGLE'); mode_map = {'SINGLE': 'Từng viên', 'BURST_3': 'Loạt 3'}
                mode_display = mode_map.get(mode_raw, mode_raw)
                finished = s.get('finished_soldiers', 0); total = s.get('total_soldiers', 0)
                prog_display = f"{finished} / {total} người"
                d_item = QTableWidgetItem(date_display); d_item.setTextAlignment(Qt.AlignCenter); d_item.setData(Qt.UserRole, s)
                n_item = QTableWidgetItem(s['name'])
                m_item = QTableWidgetItem(mode_display); m_item.setTextAlignment(Qt.AlignCenter)
                p_item = QTableWidgetItem(prog_display); p_item.setTextAlignment(Qt.AlignCenter)
                if total > 0 and finished >= total: p_item.setForeground(QColor("#2ecc71")); p_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                self.ui.session_table.setItem(row, 0, d_item); self.ui.session_table.setItem(row, 1, n_item)
                self.ui.session_table.setItem(row, 2, m_item); self.ui.session_table.setItem(row, 3, p_item)
        except Exception as e: logging.error(f"Lỗi tải lịch sử phiên: {e}")

    def on_session_selection_changed(self):
        has_selection = len(self.ui.session_table.selectedItems()) > 0
        self.ui.btn_view_report.setEnabled(has_selection)
        self.ui.btn_delete_session.setEnabled(has_selection)

    def on_delete_session_clicked(self):
        selected_rows = self.ui.session_table.selectedItems()
        if not selected_rows: return
        row = selected_rows[0].row()
        session_data = self.ui.session_table.item(row, 0).data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa", 
            f"Bạn có chắc chắn muốn xóa phiên tập:\n'{session_data['name']}'?\n\nDữ liệu không thể khôi phục.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_practice_session(session_data['id']):
                QMessageBox.information(self, "Thành công", "Đã xóa phiên tập.")
                self.load_session_history()
                self.ui.btn_delete_session.setEnabled(False)
                self.ui.btn_view_report.setEnabled(False)
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xóa phiên tập này.")

    # --- CHI TIẾT PHIÊN TẬP ---
    def show_session_detail(self):
        selected_rows = self.ui.session_table.selectedItems()
        if not selected_rows: return
        row = selected_rows[0].row()
        session_data = self.ui.session_table.item(row, 0).data(Qt.UserRole)
        self.current_session_mode = session_data.get('mode', 'SINGLE')
        self.current_practice_session_id = session_data['id']
        self.ui.lbl_detail_title.setText(f"CHI TIẾT: {session_data['name'].upper()}")
        
        self.ui.cmb_view_mode.blockSignals(True)
        self.ui.cmb_view_mode.setCurrentIndex(0)
        self.ui.cmb_view_mode.blockSignals(False)
        self.ui.detail_stack.setCurrentWidget(self.ui.page_detail_list)
        
        self.ui.main_stack.setCurrentWidget(self.ui.page_session_detail)
        self.load_session_detail_data(session_data['id'])

    def toggle_view_mode(self, index):
        if index == 0:
            self.ui.detail_stack.setCurrentWidget(self.ui.page_detail_list)
            self.ui.btn_view_personal.setVisible(True)
        else:
            self.ui.detail_stack.setCurrentWidget(self.ui.page_detail_report)
            self.ui.btn_view_personal.setVisible(False)
            self.render_general_report()

    def load_session_detail_data(self, ps_id):
        self.current_detail_data = self.db.get_session_report_data(ps_id)
        self.ui.cmb_sort.blockSignals(True); self.ui.cmb_sort.setCurrentIndex(0); self.ui.cmb_sort.blockSignals(False)
        self.sort_session_detail()

    def sort_session_detail(self):
        criteria = self.ui.cmb_sort.currentData()
        if not self.current_detail_data: self.render_detail_table(); return
        if criteria == "NAME_ASC": self.current_detail_data.sort(key=lambda x: x['name'])
        elif criteria == "SCORE_DESC": self.current_detail_data.sort(key=lambda x: x['total_score'], reverse=True)
        elif criteria == "SCORE_ASC": self.current_detail_data.sort(key=lambda x: x['total_score'])
        self.render_detail_table()

    def render_detail_table(self):
        self.ui.detail_table.setRowCount(0)
        self.ui.btn_view_personal.setEnabled(False)
        header = self.ui.detail_table.horizontalHeader()
        
        if self.current_session_mode == "BURST_3":
            self.ui.detail_table.setColumnCount(5)
            self.ui.detail_table.setHorizontalHeaderLabels(["STT", "Họ và Tên", "Đơn vị", "Tổng điểm", "Xếp loại"])
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        else:
            self.ui.detail_table.setColumnCount(6)
            self.ui.detail_table.setHorizontalHeaderLabels(["STT", "Họ và Tên", "Đơn vị", "Số phát", "Tổng điểm", "Trung bình"])
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        if not self.current_detail_data: return
        self.ui.detail_table.setRowCount(len(self.current_detail_data))
        
        for row, p in enumerate(self.current_detail_data):
            score = p.get('total_score', 0)
            shot_count = p.get('shot_count', 0)
            
            stt_item = QTableWidgetItem(str(row + 1)); stt_item.setTextAlignment(Qt.AlignCenter)
            name_item = QTableWidgetItem(p['name']); name_item.setData(Qt.UserRole, p)
            class_item = QTableWidgetItem(p.get('class_name', '')); class_item.setTextAlignment(Qt.AlignCenter)
            score_item = QTableWidgetItem(str(score)); score_item.setTextAlignment(Qt.AlignCenter); score_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            if score > 0: score_item.setForeground(QColor("#f1c40f"))

            self.ui.detail_table.setItem(row, 0, stt_item)
            self.ui.detail_table.setItem(row, 1, name_item)
            self.ui.detail_table.setItem(row, 2, class_item)

            if self.current_session_mode == "BURST_3":
                rank = ""; color = QColor("white")
                
                if shot_count == 0:
                    rank = "Chưa tập"; color = QColor("#7f8c8d") 
                    score_item.setText("--")
                else:
                    if score > 23: rank = "Giỏi"; color = QColor("#2ecc71")
                    elif score >= 19: rank = "Khá"; color = QColor("#3498db")
                    elif score >= 15: rank = "Đạt"; color = QColor("#f39c12")
                    else: rank = "Không đạt"; color = QColor("#e74c3c")
                
                rank_item = QTableWidgetItem(rank); rank_item.setTextAlignment(Qt.AlignCenter); rank_item.setForeground(color); rank_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.ui.detail_table.setItem(row, 3, score_item)
                self.ui.detail_table.setItem(row, 4, rank_item)
            else:
                count_item = QTableWidgetItem(str(shot_count)); count_item.setTextAlignment(Qt.AlignCenter)
                avg_text = "--"
                if shot_count > 0:
                    avg = round(score / shot_count, 1)
                    avg_text = str(avg)
                
                avg_item = QTableWidgetItem(avg_text); avg_item.setTextAlignment(Qt.AlignCenter); avg_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                
                if shot_count == 0:
                    count_item.setForeground(QColor("#7f8c8d"))
                    score_item.setText("--"); score_item.setForeground(QColor("#7f8c8d"))
                    avg_item.setForeground(QColor("#7f8c8d"))

                self.ui.detail_table.setItem(row, 3, count_item)
                self.ui.detail_table.setItem(row, 4, score_item)
                self.ui.detail_table.setItem(row, 5, avg_item)

    # --- BÁO CÁO TỔNG QUAN (DASHBOARD) ---
    def render_general_report(self):
        if not self.current_detail_data: return
        
        total_assigned = len(self.current_detail_data)
        
        active_participants = [p for p in self.current_detail_data if p.get('shot_count', 0) > 0]
        active_count = len(active_participants)
        
        self.ui.lbl_card1_title.setText("QUÂN SỐ")
        self.ui.lbl_card1_value.setText(f"{active_count} / {total_assigned}")
        
        if active_count == 0:
            self.ui.lbl_card2_value.setText("--")
            self.ui.lbl_card3_value.setText("--")
            self.ui.lbl_card4_value.setText("--")
            self.ui.lbl_rpt_eval.setText("Chưa có dữ liệu bắn thực tế để đánh giá.")
            self.figure.clear()
            self.canvas.draw()
            return

        if self.current_session_mode == "BURST_3":
            sorted_by_perf = sorted(active_participants, key=lambda x: x['total_score'], reverse=True)
        else:
            sorted_by_perf = sorted(active_participants, key=lambda x: (x['total_score']/x['shot_count']), reverse=True)
            
        best = sorted_by_perf[0]
        worst = sorted_by_perf[-1]
        
        self.figure.clear()
        eval_text = ""; rec_text = ""

        if self.current_session_mode == "BURST_3":
            rank_counts = {"Giỏi": 0, "Khá": 0, "Đạt": 0, "Không đạt": 0}
            for p in active_participants:
                s = p['total_score']
                if s > 23: rank_counts["Giỏi"] += 1
                elif s >= 19: rank_counts["Khá"] += 1
                elif s >= 15: rank_counts["Đạt"] += 1
                else: rank_counts["Không đạt"] += 1
            
            pass_count = sum(v for k, v in rank_counts.items() if k != "Không đạt")
            pass_rate = (pass_count / active_count * 100) 
            
            self.ui.lbl_card2_title.setText("TỈ LỆ ĐẠT")
            self.ui.lbl_card2_value.setText(f"{pass_rate:.1f}%")
            self.ui.lbl_card3_title.setText("CAO NHẤT")
            self.ui.lbl_card3_value.setText(f"{best['name']}\n({best['total_score']}đ)")
            self.ui.lbl_card4_title.setText("THẤP NHẤT")
            self.ui.lbl_card4_value.setText(f"{worst['name']}\n({worst['total_score']}đ)")
            
            eval_text = f"Kết quả trên {active_count} đồng chí đã bắn: {pass_rate:.1f}% đạt yêu cầu."
            if pass_rate >= 80: rec_text = "Đơn vị nắm vững yếu lĩnh. Duy trì luyện tập nâng cao."
            elif pass_rate >= 50: rec_text = "Cần kèm cặp thêm các đồng chí chưa đạt (chủ yếu lỗi giật súng)."
            else: rec_text = "Tổ chức huấn luyện lại cơ bản: lấy đường ngắm, giữ súng."

            ax1 = self.figure.add_subplot(121)
            labels = [k for k, v in rank_counts.items() if v > 0]
            sizes = [v for v in rank_counts.values() if v > 0]
            colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
            if sizes:
                wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90, colors=colors)
                ax1.set_title('Tỉ lệ Xếp loại', color='white', fontsize=10)
                for t in texts + autotexts: t.set_color('white'); t.set_fontsize(8)

            ax2 = self.figure.add_subplot(122)
            top_n = sorted_by_perf[:10][::-1] 
            names = [p['name'].split()[-1] for p in top_n]
            scores = [p['total_score'] for p in top_n]
            
            y_pos = range(len(names))
            bars = ax2.barh(y_pos, scores, color='#1abc9c', height=0.6)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(names, color='white', fontsize=9)
            ax2.set_title(f'Top {len(top_n)} Thành Tích Tốt Nhất', color='white', fontsize=10)
            ax2.set_xlim(0, 32)
            ax2.tick_params(axis='x', colors='white')
            for i, v in enumerate(scores):
                ax2.text(v + 0.5, i, str(v), color='white', va='center', fontweight='bold')

        else:
            avg_scores = []
            for p in active_participants:
                avg_scores.append(p['total_score'] / p['shot_count'])
            
            global_avg = sum(avg_scores) / len(avg_scores) if avg_scores else 0
            
            self.ui.lbl_card2_title.setText("ĐIỂM TRUNG BÌNH")
            self.ui.lbl_card2_value.setText(f"{global_avg:.2f}")
            self.ui.lbl_card3_title.setText("CAO NHẤT")
            best_avg = best['total_score'] / best['shot_count']
            self.ui.lbl_card3_value.setText(f"{best['name']}\n(TB: {best_avg:.1f})")
            self.ui.lbl_card4_title.setText("THẤP NHẤT")
            worst_avg = worst['total_score'] / worst['shot_count']
            self.ui.lbl_card4_value.setText(f"{worst['name']}\n(TB: {worst_avg:.1f})")
            
            ax1 = self.figure.add_subplot(121)
            cat_counts = {"Kém (<5)": 0, "TB (5-8)": 0, "Giỏi (>8)": 0}
            for a in avg_scores:
                if a < 5: cat_counts["Kém (<5)"] += 1
                elif a < 8: cat_counts["TB (5-8)"] += 1
                else: cat_counts["Giỏi (>8)"] += 1
            
            labels = [k for k, v in cat_counts.items() if v > 0]
            sizes = [v for v in cat_counts.values() if v > 0]
            colors = ['#e74c3c', '#f39c12', '#2ecc71']
            if sizes:
                wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90, colors=colors)
                ax1.set_title('Phân loại (Điểm TB)', color='white', fontsize=10)
                for t in texts + autotexts: t.set_color('white'); t.set_fontsize(8)

            ax2 = self.figure.add_subplot(122)
            top_n = sorted_by_perf[:10][::-1]
            names = [p['name'].split()[-1] for p in top_n]
            scores = [round(p['total_score']/p['shot_count'], 1) for p in top_n]
            
            y_pos = range(len(names))
            ax2.barh(y_pos, scores, color='#3498db', height=0.6)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(names, color='white', fontsize=9)
            ax2.set_title(f'Top {len(top_n)} Điểm TB Cao Nhất', color='white', fontsize=10)
            ax2.set_xlim(0, 11)
            ax2.tick_params(axis='x', colors='white')
            for i, v in enumerate(scores):
                ax2.text(v + 0.2, i, str(v), color='white', va='center', fontweight='bold')
            
            eval_text = f"Điểm trung bình thực tế: {global_avg:.2f} điểm/phát."
            if global_avg >= 8.0: rec_text = "Thành tích rất tốt. Đa số bắn trúng vòng 9, 10."
            elif global_avg >= 5.0: rec_text = "Thành tích đạt yêu cầu. Cần cải thiện độ ổn định."
            else: rec_text = "Thành tích thấp. Cần rèn luyện lại kỹ năng ngắm bắn cơ bản."

        self.ui.lbl_rpt_eval.setText(f"{eval_text}\n\n👉 Kiến nghị: {rec_text}")
        self.figure.tight_layout()
        self.canvas.draw()

    def on_detail_selection_changed(self):
        self.ui.btn_view_personal.setEnabled(len(self.ui.detail_table.selectedItems()) > 0)

    def on_view_personal_process(self):
        selected_rows = self.ui.detail_table.selectedItems()
        if not selected_rows: return
        row = selected_rows[0].row()
        soldier_info = self.ui.detail_table.item(row, 1).data(Qt.UserRole)
        shots = self.db.get_soldier_session_shots(self.current_practice_session_id, soldier_info['soldier_id'])
        dlg = PersonalProcessDialog(soldier_info, shots, self)
        dlg.exec()

    # --- LOGIC QUẢN LÝ NGƯỜI TẬP (MỚI) ---
    def load_soldiers(self):
        self.all_soldiers_data = self.db.get_all_soldiers() 
        
        units = sorted(list(set(s.get('class_name', '') for s in self.all_soldiers_data if s.get('class_name'))))
        self.ui.cmb_filter_unit.blockSignals(True)
        self.ui.cmb_filter_unit.clear()
        self.ui.cmb_filter_unit.addItem("Tất cả đơn vị", "ALL")
        for u in units:
            self.ui.cmb_filter_unit.addItem(u, u)
        self.ui.cmb_filter_unit.blockSignals(False)
        
        self.reload_soldier_table_view()

    def reload_soldier_table_view(self):
        if not hasattr(self, 'all_soldiers_data'): return
        
        filtered_data = self.all_soldiers_data[:]
        
        search_txt = self.ui.search_box.text().strip().lower()
        if search_txt:
            filtered_data = [s for s in filtered_data if search_txt in s['name'].lower()]
            
        unit_filter = self.ui.cmb_filter_unit.currentData()
        if unit_filter and unit_filter != "ALL":
            filtered_data = [s for s in filtered_data if s.get('class_name') == unit_filter]
            
        sort_mode = self.ui.cmb_sort_trainees.currentData()
        if sort_mode == "NAME_ASC":
            filtered_data.sort(key=lambda x: x['name'].split()[-1]) 
        elif sort_mode == "NAME_DESC":
            filtered_data.sort(key=lambda x: x['name'].split()[-1], reverse=True)
        elif sort_mode == "UNIT":
            filtered_data.sort(key=lambda x: (x.get('class_name', ''), x['name']))

        self.ui.soldier_table.setRowCount(len(filtered_data))
        self.ui.total_count_label.setText(f"Tổng số: {len(filtered_data)}")
        
        for row, s in enumerate(filtered_data):
            stt_item = QTableWidgetItem(str(row + 1))
            stt_item.setTextAlignment(Qt.AlignCenter)
            stt_item.setData(Qt.UserRole, s['id']) 
            
            name_item = QTableWidgetItem(s['name'])
            unit_item = QTableWidgetItem(s.get('class_name', ''))
            unit_item.setTextAlignment(Qt.AlignCenter)
            
            note_content = s.get('note', '')
            note_item = QTableWidgetItem(note_content)
            if note_content:
                note_item.setForeground(QColor("#f1c40f")) 
                note_item.setToolTip(note_content)

            self.ui.soldier_table.setItem(row, 0, stt_item)
            self.ui.soldier_table.setItem(row, 1, name_item)
            self.ui.soldier_table.setItem(row, 2, unit_item)
            self.ui.soldier_table.setItem(row, 3, note_item)
            
        self.ui.btn_note.setEnabled(False)
        self.ui.btn_personal_stats.setEnabled(False)

    def filter_soldiers(self):
        self.reload_soldier_table_view()

    def open_add_soldier_dialog(self):
        d = AddSoldierDialog(self.config, parent=self)
        if d.exec() == QDialog.Accepted: self.db.add_soldier(**d.get_data()); self.load_soldiers()

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
            soldier_id = self.ui.soldier_table.item(row, 0).data(Qt.UserRole)
            edit_action = menu.addAction("Sửa thông tin"); edit_action.triggered.connect(lambda: self.edit_soldier(row))
            delete_action = menu.addAction("Xóa người này"); delete_action.triggered.connect(lambda: self.delete_multiple_soldiers([soldier_id]))
        else:
            soldier_ids = [self.ui.soldier_table.item(r, 0).data(Qt.UserRole) for r in selected_rows]
            delete_action = menu.addAction(f"Xóa {len(soldier_ids)} người đã chọn"); delete_action.triggered.connect(lambda: self.delete_multiple_soldiers(soldier_ids))
        menu.exec(self.ui.soldier_table.mapToGlobal(pos))
        
    def on_soldier_selection_changed(self):
        # --- [TINH CHỈNH] LOGIC CHỌN NHIỀU NGƯỜI ---
        # Tính số dòng thực tế được chọn (loại bỏ trùng lặp cột)
        selected_rows = set(item.row() for item in self.ui.soldier_table.selectedItems())
        count = len(selected_rows)
        
        # Chỉ bật nút Ghi chú và Thống kê khi chọn ĐÚNG 1 người
        is_single = (count == 1)
        self.ui.btn_note.setEnabled(is_single)
        self.ui.btn_personal_stats.setEnabled(is_single)
        # -------------------------------------------

    def on_edit_note_clicked(self):
        selected_rows = self.ui.soldier_table.selectedItems()
        if not selected_rows: return
        
        row = selected_rows[0].row()
        soldier_id = self.ui.soldier_table.item(row, 0).data(Qt.UserRole)
        current_name = self.ui.soldier_table.item(row, 1).text()
        current_note = self.ui.soldier_table.item(row, 3).text()
        
        text, ok = QInputDialog.getMultiLineText(
            self, 
            "Ghi chú", 
            f"Nhập ghi chú cho chiến sĩ: {current_name}", 
            current_note
        )
        
        if ok:
            if self.db.update_soldier_note(soldier_id, text):
                note_item = QTableWidgetItem(text)
                if text: note_item.setForeground(QColor("#f1c40f"))
                self.ui.soldier_table.setItem(row, 3, note_item)
                
                for s in self.all_soldiers_data:
                    if s['id'] == soldier_id:
                        s['note'] = text
                        break
                QMessageBox.information(self, "Thành công", "Đã lưu ghi chú.")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể lưu ghi chú.")

    def edit_soldier(self, row):
        soldier_id = self.ui.soldier_table.item(row, 0).data(Qt.UserRole)
        d = AddSoldierDialog(self.config, is_edit_mode=True, parent=self)
        d.name_input.setText(self.ui.soldier_table.item(row, 1).text())
        d.class_name_input.setText(self.ui.soldier_table.item(row, 2).text())
        if d.exec() == QDialog.Accepted:
            if self.db.update_soldier(soldier_id, **d.get_data()):
                QMessageBox.information(self, "Thành công", "Đã cập nhật thông tin."); self.load_soldiers()
            else: QMessageBox.critical(self, "Lỗi", "Không thể cập nhật thông tin.")

    def delete_multiple_soldiers(self, soldier_ids):
        if not soldier_ids: return
        if QMessageBox.warning(self, "Xác nhận Xóa", f"Bạn có chắc chắn muốn xóa {len(soldier_ids)} người được chọn?\nTOÀN BỘ dữ liệu lịch sử sẽ mất.", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            c = 0
            for sid in soldier_ids:
                if self.db.delete_soldier(sid): c += 1
            QMessageBox.information(self, "Thành công", f"Đã xóa {c} người."); self.load_soldiers()