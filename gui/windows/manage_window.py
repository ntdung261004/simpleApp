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
    QMenu, QFileDialog, QHeaderView, QLabel, QTableWidget, QSizePolicy
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
# === CÁC CLASS DIALOG HỖ TRỢ ===
# =============================================================================

class ExcelPreviewDialog(QDialog):
    def __init__(self, data_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xác nhận nhập dữ liệu")
        self.setMinimumSize(700, 500)
        self.data_list = data_list

        layout = QVBoxLayout(self)
        lbl_info = QLabel(f"<b>Đã tìm thấy {len(data_list)} bản ghi.</b><br>"
                          "Vui lòng kiểm tra kỹ danh sách bên dưới trước khi nhập.")
        lbl_info.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(lbl_info)

        self.table = QTableWidget(len(data_list), 3)
        self.table.setHorizontalHeaderLabels(["Chọn", "Họ và Tên", "Đơn vị"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
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
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.config = config
        labels = self.config.get("labels", {})
        title = labels.get("edit_trainee_dialog_title", "Chỉnh sửa thông tin") if is_edit_mode else labels.get("add_trainee_dialog_title", "Thêm mới")
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
        
        # Matplotlib Figure
        self.figure = Figure(figsize=(8, 4), dpi=100, facecolor='#2c3e50')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: transparent;")
        self.ui.charts_layout.addWidget(self.canvas)

        self.connect_signals()
        self.show_menu()

    def connect_signals(self):
        self.ui.btn_menu_trainees.clicked.connect(self.show_trainee_list)
        self.ui.btn_menu_sessions.clicked.connect(self.show_session_report)
        self.ui.btn_back_main.clicked.connect(self.back_to_menu_signal.emit)
        
        self.ui.btn_add_trainee.clicked.connect(self.open_add_soldier_dialog)
        self.ui.btn_import_excel.clicked.connect(self.import_excel_handler)
        self.ui.btn_back_to_menu.clicked.connect(self.show_menu)
        self.ui.search_box.textChanged.connect(self.filter_soldiers)
        
        self.ui.soldier_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.soldier_table.customContextMenuRequested.connect(self.show_soldier_context_menu)
        
        self.ui.btn_back_from_session.clicked.connect(self.show_menu)
        self.ui.session_table.itemSelectionChanged.connect(self.on_session_selection_changed)
        self.ui.btn_view_report.clicked.connect(self.show_session_detail)

        self.ui.btn_back_to_session_list.clicked.connect(self.show_session_report)
        self.ui.cmb_sort.currentIndexChanged.connect(self.sort_session_detail)
        self.ui.detail_table.itemSelectionChanged.connect(self.on_detail_selection_changed)
        self.ui.btn_view_personal.clicked.connect(self.on_view_personal_process)
        
        self.ui.cmb_view_mode.currentIndexChanged.connect(self.toggle_view_mode)

    # --- NAVIGATION ---
    def show_menu(self): self.ui.main_stack.setCurrentWidget(self.ui.page_menu)
    def show_trainee_list(self): self.ui.main_stack.setCurrentWidget(self.ui.page_trainees); self.load_soldiers()
    def show_session_report(self): 
        self.ui.main_stack.setCurrentWidget(self.ui.page_sessions)
        self.load_session_history()
        self.ui.btn_view_report.setEnabled(False)

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
        self.ui.btn_view_report.setEnabled(len(self.ui.session_table.selectedItems()) > 0)

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
            stt_item = QTableWidgetItem(str(row + 1)); stt_item.setTextAlignment(Qt.AlignCenter)
            name_item = QTableWidgetItem(p['name']); name_item.setData(Qt.UserRole, p)
            class_item = QTableWidgetItem(p.get('class_name', '')); class_item.setTextAlignment(Qt.AlignCenter)
            score_item = QTableWidgetItem(str(score)); score_item.setTextAlignment(Qt.AlignCenter); score_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            if score > 0: score_item.setForeground(QColor("#f1c40f"))

            self.ui.detail_table.setItem(row, 0, stt_item)
            self.ui.detail_table.setItem(row, 1, name_item)
            self.ui.detail_table.setItem(row, 2, class_item)

            if self.current_session_mode == "BURST_3":
                rank = "Không đạt"; color = QColor("#95a5a6")
                if 15 <= score <= 18: rank = "Đạt"; color = QColor("#f39c12")
                elif 19 <= score <= 23: rank = "Khá"; color = QColor("#3498db")
                elif score > 23: rank = "Giỏi"; color = QColor("#2ecc71")
                rank_item = QTableWidgetItem(rank); rank_item.setTextAlignment(Qt.AlignCenter); rank_item.setForeground(color); rank_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.ui.detail_table.setItem(row, 3, score_item)
                self.ui.detail_table.setItem(row, 4, rank_item)
            else:
                count = p.get('shot_count', 0)
                count_item = QTableWidgetItem(str(count)); count_item.setTextAlignment(Qt.AlignCenter)
                avg = round(score / count, 1) if count > 0 else 0
                avg_item = QTableWidgetItem(str(avg)); avg_item.setTextAlignment(Qt.AlignCenter); avg_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.ui.detail_table.setItem(row, 3, count_item)
                self.ui.detail_table.setItem(row, 4, score_item)
                self.ui.detail_table.setItem(row, 5, avg_item)

    # --- BÁO CÁO TỔNG QUAN (DASHBOARD) ---
    def render_general_report(self):
        if not self.current_detail_data: return
        
        total_soldiers = len(self.current_detail_data)
        self.ui.lbl_card1_title.setText("TỔNG SỐ NGƯỜI")
        self.ui.lbl_card1_value.setText(str(total_soldiers))
        
        # Sắp xếp để tìm Cao nhất/Thấp nhất
        sorted_by_perf = sorted(self.current_detail_data, key=lambda x: x['total_score'] if self.current_session_mode == "BURST_3" else (x['total_score']/x['shot_count'] if x['shot_count']>0 else 0), reverse=True)
        best = sorted_by_perf[0] if sorted_by_perf else None
        worst = sorted_by_perf[-1] if sorted_by_perf else None
        
        self.figure.clear()
        eval_text = ""; rec_text = ""

        if self.current_session_mode == "BURST_3":
            # Thống kê Xếp loại (Loạt 3 viên)
            rank_counts = {"Giỏi": 0, "Khá": 0, "Đạt": 0, "Không đạt": 0}
            for p in self.current_detail_data:
                s = p['total_score']
                if s > 23: rank_counts["Giỏi"] += 1
                elif s >= 19: rank_counts["Khá"] += 1
                elif s >= 15: rank_counts["Đạt"] += 1
                else: rank_counts["Không đạt"] += 1
            
            pass_count = sum(v for k, v in rank_counts.items() if k != "Không đạt")
            pass_rate = (pass_count / total_soldiers * 100) if total_soldiers > 0 else 0
            
            self.ui.lbl_card2_title.setText("TỈ LỆ ĐẠT")
            self.ui.lbl_card2_value.setText(f"{pass_rate:.1f}%")
            self.ui.lbl_card3_title.setText("CAO NHẤT")
            self.ui.lbl_card3_value.setText(f"{best['name']}\n({best['total_score']}đ)" if best else "--")
            self.ui.lbl_card4_title.setText("THẤP NHẤT")
            self.ui.lbl_card4_value.setText(f"{worst['name']}\n({worst['total_score']}đ)" if worst else "--")
            
            eval_text = f"Kết quả loạt bắn (3 viên): {pass_rate:.1f}% chiến sĩ đạt yêu cầu."
            if pass_rate >= 80: rec_text = "Đơn vị nắm vững yếu lĩnh. Duy trì luyện tập nâng cao."
            elif pass_rate >= 50: rec_text = "Cần kèm cặp thêm các đồng chí chưa đạt (chủ yếu lỗi giật súng)."
            else: rec_text = "Tổ chức huấn luyện lại cơ bản: lấy đường ngắm, giữ súng."

            ax1 = self.figure.add_subplot(121)
            labels = [k for k, v in rank_counts.items() if v > 0]
            sizes = [v for v in rank_counts.values() if v > 0]
            colors = ['#2ecc71', '#3498db', '#f39c12', '#95a5a6']
            if sizes:
                wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
                ax1.set_title('Tỉ lệ Xếp loại', color='white')
                for t in texts + autotexts: t.set_color('white')
            
            ax2 = self.figure.add_subplot(122)
            scores = [p['total_score'] for p in self.current_detail_data]
            bins = [0, 15, 19, 24, 31]
            ax2.hist(scores, bins=bins, color='#e74c3c', edgecolor='white', alpha=0.7)
            ax2.set_title('Phân bố Điểm số (0-30)', color='white')
            ax2.set_xlabel('Điểm', color='white'); ax2.tick_params(colors='white')

        else:
            # Thống kê Điểm TB (Từng viên)
            avg_scores = []
            for p in self.current_detail_data:
                sc = p['total_score'] / p['shot_count'] if p['shot_count'] > 0 else 0
                avg_scores.append(sc)
            
            global_avg = sum(avg_scores) / len(avg_scores) if avg_scores else 0
            
            self.ui.lbl_card2_title.setText("ĐIỂM TRUNG BÌNH")
            self.ui.lbl_card2_value.setText(f"{global_avg:.2f} / phát")
            self.ui.lbl_card3_title.setText("CAO NHẤT")
            best_avg = best['total_score'] / best['shot_count'] if best and best['shot_count'] > 0 else 0
            self.ui.lbl_card3_value.setText(f"{best['name']}\n(TB: {best_avg:.1f})" if best else "--")
            self.ui.lbl_card4_title.setText("THẤP NHẤT")
            worst_avg = worst['total_score'] / worst['shot_count'] if worst and worst['shot_count'] > 0 else 0
            self.ui.lbl_card4_value.setText(f"{worst['name']}\n(TB: {worst_avg:.1f})" if worst else "--")
            
            ax1 = self.figure.add_subplot(121)
            cat_counts = {"0-5": 0, "5-8": 0, "8-10": 0}
            for a in avg_scores:
                if a < 5: cat_counts["0-5"] += 1
                elif a < 8: cat_counts["5-8"] += 1
                else: cat_counts["8-10"] += 1
            
            labels = [k for k, v in cat_counts.items() if v > 0]
            sizes = [v for v in cat_counts.values() if v > 0]
            colors = ['#e74c3c', '#f39c12', '#2ecc71']
            if sizes:
                wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
                ax1.set_title('Phân bố chất lượng (Điểm TB)', color='white')
                for t in texts + autotexts: t.set_color('white')

            ax2 = self.figure.add_subplot(122)
            ax2.hist(avg_scores, bins=[0, 2, 4, 6, 8, 10], color='#3498db', edgecolor='white', alpha=0.7)
            ax2.set_title('Phổ điểm Trung bình', color='white')
            ax2.set_xlabel('Điểm TB/Phát', color='white'); ax2.tick_params(colors='white')
            
            eval_text = f"Điểm trung bình toàn phiên: {global_avg:.2f} điểm/phát."
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

    # --- LOGIC QUẢN LÝ NGƯỜI TẬP (CŨ) - ĐÃ KHÔI PHỤC ĐẦY ĐỦ ---
    def load_soldiers(self):
        self.ui.search_box.clear(); self.ui.soldier_table.setRowCount(0)
        soldiers = self.db.get_all_soldiers()
        self.ui.total_count_label.setText(f"Tổng số: {len(soldiers)}")
        if not soldiers: return
        self.ui.soldier_table.setRowCount(len(soldiers))
        for row, s in enumerate(soldiers):
            id_item = QTableWidgetItem(str(s['id'])); id_item.setTextAlignment(Qt.AlignCenter); id_item.setData(Qt.UserRole, s['id'])
            self.ui.soldier_table.setItem(row, 0, id_item)
            self.ui.soldier_table.setItem(row, 1, QTableWidgetItem(s['name']))
            c_item = QTableWidgetItem(s.get('class_name', '')); c_item.setTextAlignment(Qt.AlignCenter)
            self.ui.soldier_table.setItem(row, 2, c_item)

    def filter_soldiers(self):
        txt = self.ui.search_box.text().lower()
        for r in range(self.ui.soldier_table.rowCount()):
            match = txt in self.ui.soldier_table.item(r, 1).text().lower() or txt in self.ui.soldier_table.item(r, 2).text().lower()
            self.ui.soldier_table.setRowHidden(r, not match)

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