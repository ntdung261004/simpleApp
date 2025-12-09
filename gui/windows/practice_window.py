# file: gui/windows/practice_window.py
import logging
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import QMainWindow, QListWidgetItem, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QKeyEvent

from gui.ui.ui_practice import MainGui
from utils.audio import AudioManager
from core.database import DatabaseManager
from gui.managers.camera_manager import CameraManager
from gui.managers.session_manager import SessionManager
from gui.controllers.shooting_controller import ShootingController
from gui.dialogs import show_warning, show_info, show_error, show_confirmation, show_confirmation_custom

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
        self.gui.btn_create_session.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_session_menu))
        self.gui.btn_back_main.clicked.connect(self.back_to_menu_signal.emit)
        self.gui.btn_new_session.clicked.connect(self.on_new_session_clicked)
        self.gui.btn_continue_session.clicked.connect(self.on_continue_session_clicked)
        self.gui.btn_back_dashboard_session.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_dashboard))
        self.gui.btn_confirm_setup.clicked.connect(self.on_confirm_create_session)
        self.gui.btn_back_create.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_session_menu))
        self.gui.list_soldiers_select.itemSelectionChanged.connect(self.update_create_session_summary)
        self.gui.cmb_session_type.currentIndexChanged.connect(self.update_create_session_summary)
        self.gui.btn_cont_start.clicked.connect(self.on_continue_start_clicked)
        self.gui.btn_cont_delete.clicked.connect(self.on_continue_delete_clicked)
        self.gui.btn_cont_back.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_session_menu))
        self.gui.btn_free_practice.clicked.connect(self.on_free_practice_clicked)
        self.gui.btn_back_header.clicked.connect(self.on_back_header_clicked)
        self.gui.back_to_dashboard_btn.clicked.connect(self.on_finish_session_clicked)
        self.gui.btn_save_session.clicked.connect(self.on_save_session_clicked)
        self.gui.btn_select_trainee.clicked.connect(lambda: self.controller.show_trainee_list(1))
        self.gui.mode_selector.currentIndexChanged.connect(self.controller.handle_mode_change)
        self.gui.shooting_mode_selector.currentIndexChanged.connect(self.controller.handle_shooting_mode_change)
        self.worker.finished.connect(self.controller.on_processing_finished)

    def on_back_header_clicked(self):
        if not self.sess_manager.is_managed_session:
            self.on_return_to_dashboard()
            return

        if self.sess_manager.is_any_burst_in_progress():
            result = show_confirmation_custom(
                self, "Đang bắn dở", "Đang có loạt bắn chưa hoàn thành.\nBạn muốn xử lý thế nào?",
                btn_yes_text="Hủy loạt & Tiếp tục thoát", btn_no_text="Ở lại bắn tiếp"
            )
            
            if result == "YES":
                for i in [0, 1, 2]:
                    if self.sess_manager.is_burst_in_progress(i):
                        self.sess_manager.cancel_incomplete_burst(i)
                # Sau khi hủy, tiếp tục logic thoát bên dưới
            else:
                return # Ở lại

        is_resumed = self.sess_manager.managed_session_data.get('is_resumed', False)
        has_practiced = self.sess_manager.has_anyone_practiced()
        
        if is_resumed:
            result = show_confirmation_custom(
                self, "Xác nhận thoát", 
                "Bạn đang tiếp tục một phiên cũ.\nBạn muốn LƯU thay đổi hay HOÀN TÁC về trạng thái trước khi load?",
                btn_yes_text="Lưu & Thoát", btn_no_text="Hủy", btn_cancel_text="Thoát KHÔNG lưu (Hoàn tác)"
            )
            
            if result == "YES": self.on_return_to_dashboard()
            elif result == "CANCEL": 
                self.sess_manager.rollback_session_changes()
                self.on_return_to_dashboard()
        else:
            if not has_practiced:
                result = show_confirmation_custom(
                    self, "Xác nhận thoát", "Phiên tập chưa có dữ liệu.\nBạn muốn giữ phiên rỗng hay Xóa bỏ?",
                    btn_yes_text="Giữ phiên rỗng & Thoát", btn_no_text="Hủy", btn_cancel_text="Xóa phiên & Thoát"
                )
            else:
                result = show_confirmation_custom(
                    self, "Xác nhận thoát", "Phiên tập mới đã có dữ liệu.\nLưu lại vào danh sách hay Xóa bỏ toàn bộ?",
                    btn_yes_text="Lưu & Thoát", btn_no_text="Hủy", btn_cancel_text="Xóa phiên & Thoát"
                )
            
            if result == "YES": self.on_return_to_dashboard()
            elif result == "CANCEL":
                ps_id = self.sess_manager.managed_session_data.get('ps_id')
                if ps_id: self.db_manager.delete_practice_session(ps_id)
                self.on_return_to_dashboard()

    def on_finish_session_clicked(self):
        if not self.sess_manager.is_managed_session:
            self.on_return_to_dashboard()
            return

        if self.sess_manager.is_any_burst_in_progress():
            show_warning(self, "Cảnh báo", "Đang có lượt bắn chưa hoàn thành.\nVui lòng bắn hết loạt hoặc Hủy loạt (nút Quay về) trước khi kết thúc.")
            return

        has_practiced = self.sess_manager.has_anyone_practiced()
        if not has_practiced:
            if show_confirmation(self, "Chưa có dữ liệu", "Chưa có ai thực hiện bài bắn.\nBạn có muốn XÓA phiên này và thoát không?"):
                ps_id = self.sess_manager.managed_session_data.get('ps_id')
                if ps_id: self.db_manager.delete_practice_session(ps_id)
                self.on_return_to_dashboard()
            return

        not_started = []
        for s in self.sess_manager.managed_session_data['soldiers']:
            if s.get('shot_count', 0) == 0:
                not_started.append(s['name'])
        
        if not_started:
            msg = f"Vẫn còn {len(not_started)} người chưa thực hiện bài bắn:\n"
            msg += "\n".join(f"- {name}" for name in not_started[:5])
            if len(not_started) > 5: msg += "\n..."
            msg += "\n\nBạn có chắc chắn muốn kết thúc phiên không?"
            if not show_confirmation(self, "Chưa hoàn thành", msg): return
            
        self._finalize_and_exit_session(show_success=True)

    def on_auto_finish_session(self):
        show_info(self, "Hoàn thành", "Tất cả người tập đã hoàn thành bài bắn.\nDữ liệu đã được lưu.\nPhiên tập kết thúc.")
        self._finalize_and_exit_session(show_success=False)

    def _finalize_and_exit_session(self, show_success=True):
        ps_id = self.sess_manager.managed_session_data.get('ps_id')
        if ps_id:
            if self.db_manager.mark_practice_session_finished(ps_id):
                logger.info(f"Đã đánh dấu kết thúc phiên {ps_id}")
                if show_success:
                    show_info(self, "Đã lưu", "Phiên tập đã được lưu thành công.\nBạn có thể xem lại chi tiết trong mục 'Quản lý - Thống kê'.")
            else:
                show_error(self, "Lỗi", "Không thể cập nhật trạng thái kết thúc vào CSDL.")
        
        self.on_return_to_dashboard()

    def on_save_session_clicked(self):
        if self.sess_manager.is_any_burst_in_progress():
            show_warning(self, "Cảnh báo", "Đang có lượt bắn chưa hoàn thành.\nVui lòng bắn hết loạt trước khi lưu.")
            return
        show_info(self, "Đã lưu", "Đã lưu trạng thái phiên tập hiện tại thành công.")

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
            show_warning(self, "Chưa chọn", "Vui lòng chọn một phiên tập để tiếp tục.")
            return
        session_data = self.gui.tbl_continue.item(selected_row, 0).data(Qt.UserRole)
        self.controller.restore_session(ps_id=session_data['id'], name=session_data['name'], mode=session_data['mode'])

    def on_continue_delete_clicked(self):
        selected_row = self.gui.tbl_continue.currentRow()
        if selected_row < 0: return
        session_data = self.gui.tbl_continue.item(selected_row, 0).data(Qt.UserRole)
        if show_confirmation(self, "Xác nhận xóa", f"Bạn có chắc muốn xóa phiên '{session_data['name']}'?"):
            self.db_manager.delete_practice_session(session_data['id'])
            self.load_unfinished_sessions()

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
        
        mode = self.gui.cmb_session_type.currentData()
        if mode == "SINGLE":
            rec = "• Đối với hình thức từng viên:\n" \
                  "Nên cho toàn bộ người tập bắn số phát bắn bằng với nhau để làm cơ sở so sánh số liệu và đánh giá thống kê chính xác khách quan nhất.\n" \
                  "Có thể quay lại lượt bắn đối với người đã tập rồi để đủ phát bắn.\n\n" \
                  "• Đối với chế độ 2 Camera:\n" \
                  "Thứ tự bắn sẽ là luân phiên, camera nào hiển thị viền xanh là camera đó đang trong lượt bắn.\n\n"\
                  "• Quá trình tập luyện:\n" \
                  "Trong quá trình tập luyện, tránh đụng tới các nút thao tác không liên quan để làm ảnh hưởng, gián đoạn kết quả.\n"\
                  "Nhấn Kết thúc để xác nhận hoàn thành buổi tập, kết quả báo cáo thống kê sẽ được lưu trữ ở chức năng Quản Lý - Thống Kê." 
        else: 
            rec = "• Đối với hình thức 3 viên:\n" \
                  "Mỗi người sẽ thực hiện duy nhất một lượt 3 viên tương tự như 1 bài bắn phân đoạn.\n" \
                  "Có thể chọn thực hiện lại loạt bắn khi gặp các vấn đề như nhận diện sai, bắn nhầm.\n\n" \
                  "• Đối với chế độ 2 Camera:\n" \
                  "Thứ tự bắn sẽ là luân phiên, camera nào hiển thị viền xanh là camera đó đang trong lượt bắn.\n\n"\
                  "• Quá trình tập luyện:\n" \
                  "Trong quá trình tập luyện, tránh đụng tới các nút thao tác không liên quan để làm ảnh hưởng, gián đoạn kết quả.\n"\
                  "Nhấn Kết thúc để xác nhận hoàn thành buổi tập, kết quả báo cáo thống kê sẽ được lưu trữ ở chức năng Quản Lý - Thống Kê." 
        self.gui.lbl_recommendation.setText(rec)

    def on_confirm_create_session(self):
        name = self.gui.inp_session_name.text().strip()
        if not name: show_warning(self, "Lỗi", "Vui lòng nhập tên phiên tập."); return
        if self.db_manager.check_exercise_name_exists(name): show_warning(self, "Lỗi", f"Tên phiên '{name}' đã tồn tại."); return
        selected = self.gui.list_soldiers_select.selectedItems()
        if not selected: show_warning(self, "Lỗi", "Vui lòng chọn ít nhất một người tập."); return
        soldiers = [item.data(Qt.UserRole) for item in selected]
        self.controller.setup_new_session(name, self.gui.cmb_session_type.currentData(), soldiers)