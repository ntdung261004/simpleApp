# file: gui/windows/practice_window.py
import logging
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import QMainWindow, QMessageBox, QListWidgetItem
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

    def start_camera(self):
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)
        self.setFocus()
        if self.bt_trigger: self.bt_trigger.activate()

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
        self.gui.btn_free_practice.clicked.connect(self.on_free_practice_clicked)
        self.gui.back_to_dashboard_btn.clicked.connect(self.on_return_to_dashboard)
        self.gui.mode_selector.currentIndexChanged.connect(self.controller.handle_mode_change)
        self.gui.shooting_mode_selector.currentIndexChanged.connect(self.controller.handle_shooting_mode_change)
        self.worker.finished.connect(self.controller.on_processing_finished)

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
        mode_data = self.gui.cmb_session_type.currentData()
        rec = "Đề xuất: Mỗi chiến sĩ nên bắn cơ số đạn bằng nhau." if mode_data == "SINGLE" else "Quy định: Mỗi chiến sĩ sẽ thực hiện bắn 1 lượt (3 viên)."
        self.gui.lbl_recommendation.setText(rec)

    def on_confirm_create_session(self):
        name = self.gui.inp_session_name.text().strip()
        if not name: QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên phiên tập."); return
        selected_items = self.gui.list_soldiers_select.selectedItems()
        if not selected_items: QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn ít nhất một người tập."); return
        soldiers = [item.data(Qt.UserRole) for item in selected_items]
        mode = self.gui.cmb_session_type.currentData()
        self.controller.initialize_managed_session(name, mode, soldiers)

    def on_continue_session_clicked(self): QMessageBox.information(self, "Thông báo", "Chức năng tiếp tục phiên đang hoàn thiện.")