# file: gui/windows/practice_window.py
import logging
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import QMainWindow, QMessageBox, QListWidgetItem, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeyEvent

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from core.database import DatabaseManager
from gui.managers.camera_manager import CameraManager
from gui.managers.session_manager import SessionManager
from gui.controllers.shooting_controller import ShootingController

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)
    back_to_menu_signal = Signal()

    def __init__(self, worker, trigger, config: dict):
        super().__init__()
        self.config = config
        self.setWindowTitle(self.config.get("labels", {}).get("app_title", "Phần Mềm Bắn Súng"))
        self.setFocusPolicy(Qt.StrongFocus)
        self.gui = MainGui(self.config)
        self.setCentralWidget(self.gui)
        
        self.worker = worker
        self.bt_trigger = trigger
        self.db_manager = DatabaseManager()
        self.audio_manager = AudioManager()
        
        self.cam_manager = CameraManager(config)
        self.sess_manager = SessionManager(self.db_manager)
        
        self.controller = ShootingController(self.gui, self.config, self.worker, self.bt_trigger, self.cam_manager, self.sess_manager, self.audio_manager, self)
        self._init_connections()
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)

    def _init_connections(self):
        # Menu Navigation
        self.gui.btn_create_session.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_session_menu))
        self.gui.btn_back_main.clicked.connect(self.back_to_menu_signal.emit)
        
        # Session Menu
        self.gui.btn_new_session.clicked.connect(self.on_new_session_clicked)
        self.gui.btn_continue_session.clicked.connect(self.on_continue_session_clicked)
        self.gui.btn_back_dashboard_session.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_dashboard))
        
        # Create Session Page
        self.gui.btn_confirm_setup.clicked.connect(self.on_confirm_create_session)
        self.gui.btn_back_create.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_session_menu))
        self.gui.list_soldiers_select.itemSelectionChanged.connect(self.update_create_session_summary)
        self.gui.cmb_session_type.currentIndexChanged.connect(self.update_create_session_summary)
        
        # Continue Session Page
        self.gui.btn_cont_start.clicked.connect(self.on_continue_start_clicked)
        self.gui.btn_cont_delete.clicked.connect(self.on_continue_delete_clicked)
        self.gui.btn_cont_back.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_session_menu))
        
        # Free Practice
        self.gui.btn_free_practice.clicked.connect(self.on_free_practice_clicked)
        
        # Practice View Header (Các nút điều khiển chính)
        self.gui.btn_back_header.clicked.connect(self.on_back_header_clicked)
        self.gui.back_to_dashboard_btn.clicked.connect(self.on_finish_session_clicked)
        self.gui.btn_save_session.clicked.connect(self.on_save_session_clicked)
        
        # Nút chọn người (Chế độ 1 Cam) - Kết nối Controller để hiện popup
        self.gui.btn_select_trainee.clicked.connect(lambda: self.controller.show_trainee_list(1))
        
        # Core Signals
        self.gui.mode_selector.currentIndexChanged.connect(self.controller.handle_mode_change)
        self.gui.shooting_mode_selector.currentIndexChanged.connect(self.controller.handle_shooting_mode_change)
        self.worker.finished.connect(self.controller.on_processing_finished)

    # --- LOGIC QUAY VỀ (BACK) ---
    def on_back_header_clicked(self):
        # 1. Chế độ Tự do -> Thoát luôn
        if not self.sess_manager.is_managed_session:
            self.on_return_to_dashboard()
            return

        # 2. Kiểm tra bắn dở (Burst in progress)
        if self.sess_manager.is_any_burst_in_progress():
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Đang bắn dở")
            msg_box.setText("Đang có loạt bắn chưa hoàn thành.\nBạn muốn xử lý thế nào?")
            msg_box.setIcon(QMessageBox.Warning)
            
            btn_cancel_burst = msg_box.addButton("Hủy loạt & Tiếp tục thoát", QMessageBox.DestructiveRole)
            btn_stay = msg_box.addButton("Ở lại bắn tiếp", QMessageBox.RejectRole)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == btn_cancel_burst:
                # Hủy các loạt đang bắn dở
                for i in [0, 1, 2]:
                    if self.sess_manager.is_burst_in_progress(i):
                        self.sess_manager.cancel_incomplete_burst(i)
                # Sau khi hủy loạt, tiếp tục xuống logic hỏi Lưu/Thoát
            else:
                return # Ở lại

        # 3. Logic Thoát/Lưu/Hủy
        is_resumed = self.sess_manager.managed_session_data.get('is_resumed', False)
        has_practiced = self.sess_manager.has_anyone_practiced()
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Xác nhận thoát")
        msg_box.setIcon(QMessageBox.Question)
        
        btn_save_exit = msg_box.addButton("Lưu & Thoát", QMessageBox.AcceptRole)
        btn_cancel = msg_box.addButton("Hủy", QMessageBox.RejectRole)
        btn_discard = None

        if is_resumed:
            # Nếu là phiên resume -> Hỏi Lưu hay Hoàn tác (Rollback)
            msg_box.setText("Bạn đang tiếp tục một phiên cũ.\nBạn muốn LƯU thay đổi hay HOÀN TÁC về trạng thái trước khi load?")
            btn_discard = msg_box.addButton("Thoát KHÔNG lưu (Hoàn tác)", QMessageBox.DestructiveRole)
        else:
            # Nếu là phiên mới
            if not has_practiced:
                # Chưa bắn gì -> Hỏi xóa phiên rỗng
                msg_box.setText("Phiên tập chưa có dữ liệu.\nBạn muốn giữ phiên rỗng hay Xóa bỏ?")
                btn_save_exit.setText("Giữ phiên rỗng & Thoát")
                btn_discard = msg_box.addButton("Xóa phiên & Thoát", QMessageBox.DestructiveRole)
            else:
                # Đã bắn -> Hỏi Lưu hay Xóa
                msg_box.setText("Phiên tập mới đã có dữ liệu.\nLưu lại vào danh sách hay Xóa bỏ toàn bộ?")
                btn_discard = msg_box.addButton("Xóa phiên & Thoát", QMessageBox.DestructiveRole)
        
        msg_box.exec()
        clicked = msg_box.clickedButton()

        if clicked == btn_cancel:
            return
        
        if clicked == btn_save_exit:
            # Dữ liệu đã lưu realtime, chỉ cần thoát
            self.on_return_to_dashboard()
        
        elif clicked == btn_discard:
            if is_resumed:
                # Nếu là phiên cũ -> Rollback các shot mới
                self.sess_manager.rollback_session_changes()
                self.on_return_to_dashboard()
            else:
                # Nếu là phiên mới -> Xóa sạch phiên
                ps_id = self.sess_manager.managed_session_data.get('ps_id')
                if ps_id: self.db_manager.delete_practice_session(ps_id)
                self.on_return_to_dashboard()

    # --- LOGIC KẾT THÚC PHIÊN (FINISH) ĐÃ SỬA ---
    def on_finish_session_clicked(self):
        if not self.sess_manager.is_managed_session:
            self.on_return_to_dashboard()
            return

        # Kiểm tra bắn dở
        if self.sess_manager.is_any_burst_in_progress():
            QMessageBox.warning(self, "Cảnh báo", 
                                "Đang có lượt bắn chưa hoàn thành.\nVui lòng bắn hết loạt hoặc Hủy loạt (nút Quay về) trước khi kết thúc.")
            return

        # Kiểm tra có dữ liệu chưa
        has_practiced = self.sess_manager.has_anyone_practiced()
        if not has_practiced:
            reply = QMessageBox.question(self, "Chưa có dữ liệu", 
                                         "Chưa có ai thực hiện bài bắn.\nBạn có muốn XÓA phiên này và thoát không?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                ps_id = self.sess_manager.managed_session_data.get('ps_id')
                if ps_id: self.db_manager.delete_practice_session(ps_id)
                self.on_return_to_dashboard()
            return

        # Kiểm tra người chưa tập
        not_started = []
        for s in self.sess_manager.managed_session_data['soldiers']:
            if s.get('shot_count', 0) == 0:
                not_started.append(s['name'])
        
        if not_started:
            msg = f"Vẫn còn {len(not_started)} người chưa thực hiện bài bắn:\n"
            msg += "\n".join(f"- {name}" for name in not_started[:5])
            if len(not_started) > 5: msg += "\n..."
            msg += "\n\nBạn có chắc chắn muốn kết thúc phiên không?"
            reply = QMessageBox.warning(self, "Chưa hoàn thành", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No: return
            
        # --- CẬP NHẬT TRẠNG THÁI IS_FINISHED VÀO DB ---
        ps_id = self.sess_manager.managed_session_data.get('ps_id')
        if ps_id:
            if self.db_manager.mark_practice_session_finished(ps_id):
                QMessageBox.information(self, "Hoàn tất", "Phiên tập đã kết thúc.\nDữ liệu đã được lưu vào Báo cáo.")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể cập nhật trạng thái kết thúc vào CSDL.")
        # -----------------------------------------------

        self.on_return_to_dashboard()

    # --- LOGIC LƯU PHIÊN (SAVE) ---
    def on_save_session_clicked(self):
        if self.sess_manager.is_any_burst_in_progress():
            QMessageBox.warning(self, "Cảnh báo", 
                                "Đang có lượt bắn chưa hoàn thành.\nVui lòng bắn hết loạt trước khi lưu.")
            return
        QMessageBox.information(self, "Đã lưu", "Đã lưu trạng thái phiên tập hiện tại thành công.")

    # --- CÁC HÀM TIẾP TỤC PHIÊN ---
    def on_continue_session_clicked(self):
        self.gui.stack.setCurrentWidget(self.gui.page_continue_session)
        self.load_unfinished_sessions()

    def load_unfinished_sessions(self):
        try:
            sessions = self.db_manager.get_unfinished_practice_sessions()
            self.gui.tbl_continue.setRowCount(len(sessions))
            for row, s in enumerate(sessions):
                id_item = QTableWidgetItem(str(s['id'])); id_item.setTextAlignment(Qt.AlignCenter)
                date_str = datetime.strptime(s['created_at'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                date_item = QTableWidgetItem(date_str); date_item.setTextAlignment(Qt.AlignCenter)
                name_item = QTableWidgetItem(s['name'])
                mode_map = {'SINGLE': 'Từng viên', 'BURST_3': 'Loạt 3'}
                mode_item = QTableWidgetItem(mode_map.get(s['mode'], s['mode'])); mode_item.setTextAlignment(Qt.AlignCenter)
                prog = f"{s['finished_soldiers']}/{s['total_soldiers']} đã tập"
                prog_item = QTableWidgetItem(prog); prog_item.setTextAlignment(Qt.AlignCenter)
                
                self.gui.tbl_continue.setItem(row, 0, id_item)
                self.gui.tbl_continue.setItem(row, 1, date_item)
                self.gui.tbl_continue.setItem(row, 2, name_item)
                self.gui.tbl_continue.setItem(row, 3, mode_item)
                self.gui.tbl_continue.setItem(row, 4, prog_item)
                id_item.setData(Qt.UserRole, s)
        except Exception as e:
            logger.error(f"Lỗi load session: {e}")

    def on_continue_start_clicked(self):
        selected_row = self.gui.tbl_continue.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một phiên tập để tiếp tục.")
            return
        session_data = self.gui.tbl_continue.item(selected_row, 0).data(Qt.UserRole)
        # Gọi hàm RESTORE
        self.controller.restore_session(ps_id=session_data['id'], name=session_data['name'], mode=session_data['mode'])

    def on_continue_delete_clicked(self):
        selected_row = self.gui.tbl_continue.currentRow()
        if selected_row < 0: return
        session_data = self.gui.tbl_continue.item(selected_row, 0).data(Qt.UserRole)
        reply = QMessageBox.question(self, "Xác nhận xóa", f"Bạn có chắc muốn xóa phiên '{session_data['name']}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_manager.delete_practice_session(session_data['id'])
            self.load_unfinished_sessions()

    # --- CÁC HÀM HỆ THỐNG & KHỞI TẠO ---
    def start_camera(self):
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)
        self.setFocus(); 
        if self.bt_trigger: self.bt_trigger.activate()

    def on_free_practice_clicked(self):
        self.gui.stack.setCurrentWidget(self.gui.page_view)
        self.controller.start_free_practice()

    def on_return_to_dashboard(self):
        self.controller.stop_practice()
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)

    def keyPressEvent(self, event: QKeyEvent):
        if event.isAutoRepeat(): event.ignore(); return
        if event.key() in [Qt.Key_Enter, Qt.Key_Return]:
            event.accept(); self.controller.execute_shot_logic()
        else: super().keyPressEvent(event)

    def mousePressEvent(self, event): self.setFocus(); super().mousePressEvent(event)
    
    def shutdown_components(self):
        if self.bt_trigger: self.bt_trigger.deactivate()
        self.controller.stop_practice()

    def on_new_session_clicked(self):
        self.gui.list_soldiers_select.clear(); soldiers = self.db_manager.get_all_soldiers()
        for s in soldiers:
            item = QListWidgetItem(f"{s['name']} - {s.get('class_name', '')}"); item.setData(Qt.UserRole, s); self.gui.list_soldiers_select.addItem(item)
        self.gui.inp_session_name.setText(f"Phiên tập {datetime.now().strftime('%d/%m/%Y')}")
        self.update_create_session_summary()
        self.gui.stack.setCurrentWidget(self.gui.page_create_session)

    def update_create_session_summary(self):
        count = len(self.gui.list_soldiers_select.selectedItems())
        self.gui.lbl_sum_count.setText(f"{count} người")
        self.gui.lbl_sum_type.setText(self.gui.cmb_session_type.currentText())
        self.gui.lbl_sum_date.setText(datetime.now().strftime("%d/%m/%Y %H:%M"))
        rec = "Đề xuất: Mỗi chiến sĩ nên bắn cơ số đạn bằng nhau." if self.gui.cmb_session_type.currentData() == "SINGLE" else "Quy định: Mỗi chiến sĩ sẽ thực hiện bắn 1 lượt (3 viên)."
        self.gui.lbl_recommendation.setText(rec)

    def on_confirm_create_session(self):
        name = self.gui.inp_session_name.text().strip()
        if not name: QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên phiên tập."); return
        if self.db_manager.check_exercise_name_exists(name): QMessageBox.warning(self, "Lỗi", f"Tên phiên '{name}' đã tồn tại."); return
        selected = self.gui.list_soldiers_select.selectedItems()
        if not selected: QMessageBox.warning(self, "Lỗi", "Vui lòng chọn ít nhất một người tập."); return
        soldiers = [item.data(Qt.UserRole) for item in selected]
        
        # Gọi hàm TẠO MỚI
        self.controller.setup_new_session(name, self.gui.cmb_session_type.currentData(), soldiers)