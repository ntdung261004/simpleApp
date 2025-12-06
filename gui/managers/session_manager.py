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
    soldier_session_started = Signal(str)

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
        
        self.managed_session_data = {
            'name': "", 'soldiers': [], 'current_soldier_idx': -1
        }
        
        self.active_soldiers = {1: None, 2: None}

    def _get_or_create_free_soldier(self):
        soldiers = self.db.get_all_soldiers()
        for s in soldiers:
            if s['name'] == "Khách (Tự do)": return s['id']
        return self.db.add_soldier("Khách (Tự do)", "Hệ thống")

    def setup_managed_session(self, name, mode, soldiers):
        self.is_managed_session = True
        self.is_free_practice = False
        self.shooting_mode = mode
        self.managed_session_data['name'] = name
        self.managed_session_data['soldiers'] = []
        self.active_soldiers = {1: None, 2: None}
        
        for s in soldiers:
            sid = self.db.create_session(s['id'], exercise_name=name)
            soldier_entry = s.copy()
            soldier_entry['db_session_id'] = sid
            soldier_entry['finished'] = False
            soldier_entry['last_result'] = ""
            soldier_entry['shot_count'] = 0
            soldier_entry['total_score'] = 0
            self.managed_session_data['soldiers'].append(soldier_entry)

    def assign_soldier_to_slot(self, slot, soldier_data):
        target = None
        for s in self.managed_session_data['soldiers']:
            if s['id'] == soldier_data['id']:
                target = s
                break
        if target:
            self.active_soldiers[slot] = target
        else:
            self.active_soldiers[slot] = soldier_data

    def clear_active_soldiers(self):
        self.active_soldiers = {1: None, 2: None}

    def get_soldier_at_session_idx(self, session_idx):
        if self.current_mode == 0 and session_idx == 0:
            return self.active_soldiers[1]
        return self.active_soldiers.get(session_idx)

    def cancel_incomplete_burst(self, session_idx):
        if not self.is_managed_session: return

        soldier = self.get_soldier_at_session_idx(session_idx)
        if not soldier: return

        old_sid = self.active_session_ids[session_idx]
        if old_sid:
            self.db.delete_session(old_sid)

        target_in_list = None
        for s in self.managed_session_data['soldiers']:
            if s['id'] == soldier['id']:
                target_in_list = s
                break
        
        if target_in_list:
            current_burst_score = sum(item['score'] for item in self.testing_buffers[session_idx])
            current_burst_count = len(self.testing_buffers[session_idx])
            
            target_in_list['shot_count'] = max(0, target_in_list['shot_count'] - current_burst_count)
            target_in_list['total_score'] = max(0, target_in_list['total_score'] - current_burst_score)
            
            if target_in_list['shot_count'] == 0:
                target_in_list['last_result'] = ""
            else:
                target_in_list['last_result'] = "Đã hủy loạt gần nhất"

            self.active_soldiers[1 if session_idx == 0 and self.current_mode == 0 else session_idx] = target_in_list

        self.end_session(session_idx)
        self._reset_counters(session_idx)

    def is_burst_in_progress(self, session_idx):
        if self.shooting_mode != "BURST_3": return False
        count = len(self.testing_buffers[session_idx]) + self.pending_shots[session_idx]
        return 0 < count < 3

    def is_any_burst_in_progress(self):
        for i in [0, 1, 2]:
            if self.is_burst_in_progress(i): return True
        return False

    def retry_burst(self, session_idx):
        if not self.is_managed_session:
            self.end_session(session_idx)
            self._reset_counters(session_idx)
            self.start_session(session_idx)
            return
        
        soldier = self.get_soldier_at_session_idx(session_idx)
        if not soldier: return

        old_sid = self.active_session_ids[session_idx]
        if old_sid:
            self.db.delete_session(old_sid)
        
        target_in_list = None
        for s in self.managed_session_data['soldiers']:
            if s['id'] == soldier['id']:
                target_in_list = s
                break
        
        if target_in_list:
            current_burst_score = sum(item['score'] for item in self.testing_buffers[session_idx])
            current_burst_count = len(self.testing_buffers[session_idx])
            
            target_in_list['shot_count'] -= current_burst_count
            target_in_list['total_score'] -= current_burst_score
            target_in_list['finished'] = False
            target_in_list['last_result'] = "Đang bắn lại..."
            
            self.active_soldiers[1 if session_idx == 0 and self.current_mode == 0 else session_idx] = target_in_list

        self.end_session(session_idx) 
        self._reset_counters(session_idx) 
        self.start_session(session_idx)

    def start_session(self, session_idx):
        if self.session_active_flags[session_idx]: self.end_session(session_idx)
        
        soldier = None
        target_db_sid = None
        
        if self.is_managed_session:
            soldier = self.get_soldier_at_session_idx(session_idx)
            if soldier:
                target_db_sid = self.db.create_session(soldier['id'], exercise_name=self.managed_session_data['name'])
                soldier['db_session_id'] = target_db_sid
                
                if self.shooting_mode == "SINGLE":
                    self.shot_counters[session_idx] = soldier.get('shot_count', 0)
                else:
                    self.shot_counters[session_idx] = 0
            else:
                return
        else:
            target_db_sid = self.db.create_session(self.free_soldier_id)
            self.shot_counters[session_idx] = 0

        self.testing_buffers[session_idx] = []
        self.pending_shots[session_idx] = 0
        
        if target_db_sid:
            self.active_session_ids[session_idx] = target_db_sid
            self.session_active_flags[session_idx] = True
            self.session_state_changed.emit(session_idx, True)

    def end_session(self, session_idx):
        if not self.session_active_flags[session_idx]: return
        sid = self.active_session_ids[session_idx]
        if sid and sid > 0:
            if self.is_free_practice:
                count = self.db.get_shot_count_for_session(sid)
                if count == 0: self.db.delete_session(sid)
                else:
                    auto_name = f"Phiên tự do {datetime.now().strftime('%H:%M %d/%m')}"
                    self.db.update_session_name(sid, auto_name)
                    self.db.end_session(sid)
            else:
                pass 
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

    def reset_burst_state(self, idx):
        self.testing_buffers[idx] = []; self.pending_shots[idx] = 0

    def check_can_shot(self, session_idx):
        if self.shooting_mode == "BURST_3":
            if len(self.testing_buffers[session_idx]) + self.pending_shots[session_idx] >= 3: return False
        return True

    def register_pending_shot(self, session_idx):
        if self.shooting_mode == "BURST_3": self.pending_shots[session_idx] += 1

    def rollback_pending_shot(self, session_idx):
        if self.shooting_mode == "BURST_3": 
            self.pending_shots[session_idx] = max(0, self.pending_shots[session_idx] - 1)

    def process_shot_result(self, res, pix_frame):
        score = res.get('score'); image_path = res.get('image_path')
        session_idx = 0
        try:
            name = os.path.basename(image_path)
            if name.startswith('s'): session_idx = int(name.split('_')[0][1:])
        except: pass
        
        self.rollback_pending_shot(session_idx)
        
        if self.is_managed_session:
            current_soldier = self.get_soldier_at_session_idx(session_idx)
            if current_soldier:
                target_in_list = None
                for s in self.managed_session_data['soldiers']:
                    if s['id'] == current_soldier['id']:
                        target_in_list = s
                        break
                
                if target_in_list:
                    target_in_list['shot_count'] += 1
                    target_in_list['total_score'] += score
                    
                    if self.shooting_mode == "SINGLE":
                        avg = round(target_in_list['total_score'] / target_in_list['shot_count'], 1)
                        target_in_list['last_result'] = f"{target_in_list['shot_count']} phát - {target_in_list['total_score']} điểm (TB: {avg})"
                    else:
                        target_in_list['last_result'] = f"Loạt 3: {target_in_list['total_score']} điểm"
                    
                    self.active_soldiers[1 if session_idx == 0 and self.current_mode == 0 else session_idx] = target_in_list
        
        current_shot_no = self.shot_counters[session_idx] + 1
        
        # --- LOGIC HIỂN THỊ TEXT ---
        if self.is_free_practice:
            if self.shooting_mode == "SINGLE":
                # Tự do từng viên -> Chỉ hiện điểm
                score_text = f"Điểm: {score}"
            else:
                # Tự do loạt -> Hiện số phát 1/2/3 cho dễ theo dõi loạt
                score_text = f"Phát {current_shot_no}: {score} điểm"
        else:
            # Managed -> Hiện đầy đủ
            if self.shooting_mode == "BURST_3":
                score_text = f"Phát {current_shot_no}: {score} điểm (Loạt)"
            else:
                score_text = f"Phát {current_shot_no}: {score} điểm"
        # ---------------------------
        
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
            if len(self.testing_buffers[0]) >= 3: self.burst_completed.emit(0, self.testing_buffers[0])
        elif self.current_mode == 1:
            b1 = len(self.testing_buffers[1]); b2 = len(self.testing_buffers[2])
            p1 = self.pending_shots[1]; p2 = self.pending_shots[2]
            if b1 >= 3 and b2 >= 3 and p1 == 0 and p2 == 0:
                self.burst_completed.emit(1, self.testing_buffers[1]); self.burst_completed.emit(2, self.testing_buffers[2])
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