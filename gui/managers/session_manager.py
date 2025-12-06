# file: gui/managers/session_manager.py
from PySide6.QtCore import QObject, Signal
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SessionManager(QObject):
    session_state_changed = Signal(int, bool)
    shot_added = Signal(int, int, int, str)
    burst_completed = Signal(int, list)
    auto_switch_camera = Signal(int)

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.is_free_practice = False
        self.is_managed_session = False
        self.shooting_mode = "SINGLE"
        self.current_mode = 0
        self.next_shot_cam_id = 1
        self.active_session_ids = {0: None, 1: None, 2: None}
        self.session_active_flags = {0: False, 1: False, 2: False}
        self.shot_counters = {0: 0, 1: 0, 2: 0}
        self.testing_buffers = {0: [], 1: [], 2: []}
        self.pending_shots = {0: 0, 1: 0, 2: 0}
        self.free_soldier_id = self._get_or_create_free_soldier()

    def _get_or_create_free_soldier(self):
        soldiers = self.db.get_all_soldiers()
        for s in soldiers:
            if s['name'] == "Khách (Tự do)": return s['id']
        return self.db.add_soldier("Khách (Tự do)", "Hệ thống")

    def start_session(self, session_idx):
        if self.session_active_flags[session_idx]: self.end_session(session_idx)
        self._reset_counters(session_idx)
        sid = self.db.create_session(self.free_soldier_id)
        self.active_session_ids[session_idx] = sid
        self.session_active_flags[session_idx] = True
        self.session_state_changed.emit(session_idx, True)

    def end_session(self, session_idx):
        if not self.session_active_flags[session_idx]: return
        sid = self.active_session_ids[session_idx]
        if sid and sid > 0:
            count = self.db.get_shot_count_for_session(sid)
            if count == 0: self.db.delete_session(sid)
            else:
                if self.is_free_practice:
                    auto_name = f"Phiên tự do {datetime.now().strftime('%H:%M %d/%m')}"
                    self.db.update_session_name(sid, auto_name)
                self.db.end_session(sid)
        self.session_active_flags[session_idx] = False
        self.active_session_ids[session_idx] = None
        self.session_state_changed.emit(session_idx, False)

    def reset_all(self):
        for i in [0, 1, 2]:
            self.end_session(i)
            self._reset_counters(i)
        self.next_shot_cam_id = 1

    def _reset_counters(self, idx):
        self.shot_counters[idx] = 0; self.testing_buffers[idx] = []; self.pending_shots[idx] = 0

    def check_can_shot(self, cam_id):
        if self.shooting_mode == "BURST_3":
            if len(self.testing_buffers[cam_id]) + self.pending_shots[cam_id] >= 3: return False
        return True

    def register_pending_shot(self, cam_id):
        if self.shooting_mode == "BURST_3": self.pending_shots[cam_id] += 1

    def process_shot_result(self, res, pix_frame):
        score = res.get('score'); image_path = res.get('image_path')
        session_idx = 0
        try:
            name = os.path.basename(image_path)
            if name.startswith('s'): session_idx = int(name.split('_')[0][1:])
        except: pass
        self.pending_shots[session_idx] = max(0, self.pending_shots[session_idx] - 1)
        score_text = f"Điểm: {score}"
        if self.shooting_mode == "BURST_3":
            count = len(self.testing_buffers[session_idx]) + 1
            score_text = f"Điểm: {score} (Phát {count}/3)"
        self.shot_added.emit(session_idx, score, score, score_text)
        sid = self.active_session_ids[session_idx]
        if self.session_active_flags[session_idx] and sid > 0:
            self.shot_counters[session_idx] += 1
            self.db.add_shot(sid, self.shot_counters[session_idx], res.get('target_detected_raw'), score, res.get('coords'), image_path)
        if self.shooting_mode == "BURST_3":
            self.testing_buffers[session_idx].append({'score': score, 'image': pix_frame})
            self._check_burst_completion()

    def _check_burst_completion(self):
        if self.current_mode == 0:
            if len(self.testing_buffers[0]) >= 3: self.burst_completed.emit(0, self.testing_buffers[0]); self._reset_counters(0)
        elif self.current_mode == 1:
            b1 = len(self.testing_buffers[1]); b2 = len(self.testing_buffers[2])
            p1 = self.pending_shots[1]; p2 = self.pending_shots[2]
            if b1 >= 3 and b2 >= 3 and p1 == 0 and p2 == 0:
                self.burst_completed.emit(1, self.testing_buffers[1]); self.burst_completed.emit(2, self.testing_buffers[2])
                self._reset_counters(1); self._reset_counters(2)
                self.next_shot_cam_id = 1; self.auto_switch_camera.emit(1)

    def get_auto_switch_target(self, current_target):
        if self.shooting_mode != "BURST_3" or self.current_mode != 1: return None
        cur_total = len(self.testing_buffers[current_target]) + self.pending_shots[current_target]
        if cur_total >= 3:
            other_cam = 2 if current_target == 1 else 1
            other_total = len(self.testing_buffers[other_cam]) + self.pending_shots[other_cam]
            if other_total < 3: return other_cam
            else: return -1
        return None