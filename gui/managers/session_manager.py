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
            'name': "", 'soldiers': [], 'current_soldier_idx': -1, 'ps_id': None,
            'is_resumed': False 
        }
        self.active_soldiers = {1: None, 2: None}

    def _get_or_create_free_soldier(self):
        soldiers = self.db.get_all_soldiers()
        for s in soldiers:
            if s['name'] == "Khách (Tự do)": return s['id']
        return self.db.add_soldier("Khách (Tự do)", "Hệ thống")

    def has_anyone_practiced(self):
        if not self.is_managed_session: return False
        for s in self.managed_session_data['soldiers']:
            if s.get('shot_count', 0) > 0: return True
        return False

    def are_all_soldiers_finished(self):
        if not self.is_managed_session: return False
        if not self.managed_session_data['soldiers']: return False
        for s in self.managed_session_data['soldiers']:
            if not s.get('finished', False): return False
        return True

    # --- SETUP (TẠO MỚI) ---
    def setup_managed_session(self, name, mode, soldiers, ps_id=None):
        self.is_managed_session = True
        self.is_free_practice = False
        self.shooting_mode = mode
        self.managed_session_data = {
            'name': name, 'soldiers': [], 'current_soldier_idx': -1, 'ps_id': ps_id,
            'is_resumed': False 
        }
        self.active_soldiers = {1: None, 2: None}
        self.next_shot_cam_id = 1
        
        if ps_id is None:
            new_ps_id = self.db.create_practice_session(name, mode)
            self.managed_session_data['ps_id'] = new_ps_id
            for s in soldiers:
                sid = self.db.create_session(s['id'], practice_session_id=new_ps_id)
                soldier_entry = s.copy()
                soldier_entry.update({
                    'db_session_id': sid, 'finished': False, 'last_result': "", 
                    'shot_count': 0, 'total_score': 0,
                    'initial_shot_count': 0, 'initial_total_score': 0,
                    'session_shot_ids': [] # [MỚI] Danh sách ID các phát bắn mới trong phiên này
                })
                self.managed_session_data['soldiers'].append(soldier_entry)

    # --- RESUME (TIẾP TỤC) ---
    def resume_managed_session(self, ps_id, name, mode):
        self.is_managed_session = True
        self.is_free_practice = False
        self.shooting_mode = mode
        self.managed_session_data = {
            'name': name, 'soldiers': [], 'current_soldier_idx': -1, 'ps_id': ps_id,
            'is_resumed': True 
        }
        self.active_soldiers = {1: None, 2: None}
        self.next_shot_cam_id = 1
        
        details = self.db.get_session_details_for_resume(ps_id)
        for row in details:
            s_count = row['shot_count']
            s_score = row['total_score']
            soldier_entry = {
                'id': row['soldier_id'], 'name': row['name'], 'class_name': row['class_name'],
                'db_session_id': row['db_session_id'], 'finished': bool(row['is_finished']),
                'shot_count': s_count, 'total_score': s_score,
                'initial_shot_count': s_count, 'initial_total_score': s_score, 
                'last_result': "",
                'session_shot_ids': [] # [MỚI] Chỉ track những shot THÊM MỚI sau khi resume
            }
            if s_count > 0:
                if mode == "SINGLE":
                    avg = round(s_score / s_count, 1) if s_count > 0 else 0
                    soldier_entry['last_result'] = f"{s_count} phát - {s_score} điểm (TB: {avg})"
                else:
                    soldier_entry['last_result'] = f"Loạt 3: {s_score} điểm"
            self.managed_session_data['soldiers'].append(soldier_entry)

    # --- ROLLBACK (ĐÃ TỐI ƯU AN TOÀN) ---
    def rollback_session_changes(self):
        """Hoàn tác: Xóa chính xác các shot đã thêm trong phiên làm việc này."""
        if not self.is_managed_session: return

        logger.info("Thực hiện Rollback: Xóa dữ liệu mới phát sinh dựa trên ID...")
        for s in self.managed_session_data['soldiers']:
            # Lấy danh sách ID các phát bắn mới thêm
            new_ids = s.get('session_shot_ids', [])
            
            if new_ids:
                # 1. Xóa trong DB: Dùng hàm xóa theo list ID an toàn
                self.db.delete_shots_by_ids(new_ids)

                # 2. Reset RAM về trạng thái initial
                s['shot_count'] = s.get('initial_shot_count', 0)
                s['total_score'] = s.get('initial_total_score', 0)
                
                # Xóa danh sách tracking để sạch sẽ
                s['session_shot_ids'] = []
                
                # Nếu quay về chưa bắn -> Chưa finished
                if s['shot_count'] == 0:
                    s['finished'] = False
                    s['last_result'] = ""
                    try:
                         self.db.cursor.execute("UPDATE sessions SET is_finished = 0 WHERE id = ?", (s['db_session_id'],))
                         self.db.conn.commit()
                    except: pass
                else:
                    # Nếu revert về trạng thái cũ đã bắn rồi, tính lại text hiển thị
                    if self.shooting_mode == "SINGLE":
                        avg = round(s['total_score'] / s['shot_count'], 1)
                        s['last_result'] = f"{s['shot_count']} phát - {s['total_score']} điểm (TB: {avg})"
                    else:
                        s['last_result'] = f"Loạt 3: {s['total_score']} điểm"

    def assign_soldier_to_slot(self, slot, soldier_data):
        target = None
        for s in self.managed_session_data['soldiers']:
            if s['id'] == soldier_data['id']: target = s; break
        if target: self.active_soldiers[slot] = target
        else: self.active_soldiers[slot] = soldier_data
        
        if slot == 1:
            self.next_shot_cam_id = 1
            self.auto_switch_camera.emit(1)

    def clear_active_soldiers(self): self.active_soldiers = {1: None, 2: None}

    def get_soldier_at_session_idx(self, session_idx):
        if self.current_mode == 0 and session_idx == 0: return self.active_soldiers[1]
        return self.active_soldiers.get(session_idx)

    def determine_next_camera_after_shot(self, last_cam):
        if self.shooting_mode != "BURST_3": return 2 if last_cam == 1 else 1
        other_cam = 3 - last_cam
        if not self.is_camera_finished(other_cam): return other_cam
        elif not self.is_camera_finished(last_cam): return last_cam
        return 1

    def cancel_incomplete_burst(self, session_idx):
        if not self.is_managed_session: return
        soldier = self.get_soldier_at_session_idx(session_idx)
        if not soldier: return
        old_sid = self.active_session_ids[session_idx]
        if old_sid: self.db.delete_session(old_sid)
        new_sid = self.db.create_session(soldier['id'], practice_session_id=self.managed_session_data['ps_id'])
        soldier['db_session_id'] = new_sid

        target_in_list = None
        for s in self.managed_session_data['soldiers']:
            if s['id'] == soldier['id']: target_in_list = s; break
        
        if target_in_list:
            current_burst_score = sum(item['score'] for item in self.testing_buffers[session_idx])
            current_burst_count = len(self.testing_buffers[session_idx])
            target_in_list['shot_count'] = max(0, target_in_list['shot_count'] - current_burst_count)
            target_in_list['total_score'] = max(0, target_in_list['total_score'] - current_burst_score)
            target_in_list['last_result'] = "Đã hủy loạt gần nhất" if target_in_list['shot_count'] > 0 else ""
            
            # [MỚI] Xóa các ID của loạt đang bắn dở khỏi danh sách tracking để tránh lỗi khi rollback sau này
            # Lưu ý: Vì đã xóa session (delete_session ở trên) thì các shot trong đó cũng bay màu (cascade delete)
            # Nên ta chỉ cần clear list tracking ID tương ứng trong RAM là đủ, hoặc lọc lại.
            # Tuy nhiên, cách đơn giản nhất là giữ nguyên vì nếu rollback gọi delete_shots_by_ids, 
            # DB sẽ chỉ báo 0 rows deleted nếu chúng đã bị xóa cascade. Vẫn an toàn.
            
            self.active_soldiers[1 if session_idx == 0 and self.current_mode == 0 else session_idx] = target_in_list

        self.end_session(session_idx); self._reset_counters(session_idx)

    def is_burst_in_progress(self, session_idx):
        if self.shooting_mode != "BURST_3": return False
        count = len(self.testing_buffers[session_idx]) + self.pending_shots[session_idx]
        return 0 < count < 3

    def is_any_burst_in_progress(self):
        for i in [0, 1, 2]:
            if self.is_burst_in_progress(i): return True
        return False

    def is_camera_finished(self, session_idx):
        if self.shooting_mode != "BURST_3": return False
        return len(self.testing_buffers[session_idx]) + self.pending_shots[session_idx] >= 3

    def are_all_active_cameras_finished(self):
        if self.current_mode == 0: return self.is_camera_finished(0)
        else: return self.is_camera_finished(1) and self.is_camera_finished(2)

    def retry_burst(self, session_idx):
        if not self.is_managed_session:
            self.end_session(session_idx); self._reset_counters(session_idx); self.start_session(session_idx)
            return
        
        soldier = self.get_soldier_at_session_idx(session_idx)
        if not soldier: return

        old_sid = self.active_session_ids[session_idx]
        if old_sid: self.db.delete_session(old_sid)
        
        target_in_list = None
        for s in self.managed_session_data['soldiers']:
            if s['id'] == soldier['id']: target_in_list = s; break
        
        if target_in_list:
            current_burst_score = sum(item['score'] for item in self.testing_buffers[session_idx])
            current_burst_count = len(self.testing_buffers[session_idx])
            target_in_list['shot_count'] -= current_burst_count
            target_in_list['total_score'] -= current_burst_score
            target_in_list['finished'] = False
            target_in_list['last_result'] = "Đang bắn lại..."
            self.active_soldiers[1 if session_idx == 0 and self.current_mode == 0 else session_idx] = target_in_list

        self.end_session(session_idx); self._reset_counters(session_idx); self.start_session(session_idx)
        if self.current_mode == 1:
            self.next_shot_cam_id = session_idx
            self.auto_switch_camera.emit(session_idx)

    def start_session(self, session_idx):
        if self.session_active_flags[session_idx]: self.end_session(session_idx)
        soldier = None; target_db_sid = None
        if self.is_managed_session:
            soldier = self.get_soldier_at_session_idx(session_idx)
            if soldier:
                target_db_sid = self.db.create_session(soldier['id'], practice_session_id=self.managed_session_data['ps_id'])
                soldier['db_session_id'] = target_db_sid
                if self.shooting_mode == "SINGLE": self.shot_counters[session_idx] = soldier.get('shot_count', 0)
                else: self.shot_counters[session_idx] = 0
            else: return
        else:
            target_db_sid = -1 
            self.shot_counters[session_idx] = 0

        self.testing_buffers[session_idx] = []; self.pending_shots[session_idx] = 0
        self.active_session_ids[session_idx] = target_db_sid
        self.session_active_flags[session_idx] = True
        self.session_state_changed.emit(session_idx, True)

    def end_session(self, session_idx):
        if not self.session_active_flags[session_idx]: return
        if not self.is_managed_session:
            self.session_active_flags[session_idx] = False; self.active_session_ids[session_idx] = None; return

        sid = self.active_session_ids[session_idx]
        if sid and sid > 0:
            if self.shooting_mode == "BURST_3":
                if len(self.testing_buffers[session_idx]) >= 3: self.db.mark_session_finished(sid)
        
        self.session_active_flags[session_idx] = False
        self.active_session_ids[session_idx] = None
        self.session_state_changed.emit(session_idx, False)

    def reset_all(self):
        for i in [0, 1, 2]: self.end_session(i); self._reset_counters(i)
        self.next_shot_cam_id = 1
    def _reset_counters(self, idx):
        self.shot_counters[idx] = 0; self.testing_buffers[idx] = []; self.pending_shots[idx] = 0
    def reset_burst_state(self, idx): self.testing_buffers[idx] = []; self.pending_shots[idx] = 0
    def check_can_shot(self, session_idx):
        if self.shooting_mode == "BURST_3":
            if len(self.testing_buffers[session_idx]) + self.pending_shots[session_idx] >= 3: return False
        return True
    
    def register_pending_shot(self, session_idx):
        self.pending_shots[session_idx] += 1
        
    def rollback_pending_shot(self, session_idx):
        self.pending_shots[session_idx] = max(0, self.pending_shots[session_idx] - 1)

    def process_shot_result(self, res, pix_frame):
        score = res.get('score'); image_path = res.get('image_path')
        session_idx = 0
        try:
            name = os.path.basename(image_path); 
            if name.startswith('s'): session_idx = int(name.split('_')[0][1:])
        except: pass
        
        self.rollback_pending_shot(session_idx)
        
        if self.is_managed_session:
            current_soldier = self.get_soldier_at_session_idx(session_idx)
            if current_soldier:
                target_in_list = None
                for s in self.managed_session_data['soldiers']:
                    if s['id'] == current_soldier['id']: target_in_list = s; break
                if target_in_list:
                    target_in_list['shot_count'] += 1; target_in_list['total_score'] += score
                    if self.shooting_mode == "SINGLE":
                        avg = round(target_in_list['total_score'] / target_in_list['shot_count'], 1)
                        target_in_list['last_result'] = f"{target_in_list['shot_count']} phát - {target_in_list['total_score']} điểm (TB: {avg})"
                    else:
                        target_in_list['last_result'] = f"Loạt 3: {target_in_list['total_score']} điểm"
                    self.active_soldiers[1 if session_idx == 0 and self.current_mode == 0 else session_idx] = target_in_list
        self.shot_counters[session_idx] += 1 
        current_shot_no = self.shot_counters[session_idx]
        if self.is_free_practice:
            score_text = f"Điểm: {score}" if self.shooting_mode == "SINGLE" else f"Phát {current_shot_no}: {score} điểm"
        else:
            score_text = f"Phát {current_shot_no}: {score} điểm (Loạt)" if self.shooting_mode == "BURST_3" else f"Phát {current_shot_no}: {score} điểm"
        self.shot_added.emit(session_idx, score, score, score_text)
        
        sid = self.active_session_ids[session_idx]
        if self.is_managed_session and sid and sid > 0:
            # [MỚI] Nhận ID trả về và lưu vào tracking list
            new_shot_id = self.db.add_shot(sid, self.shot_counters[session_idx], res.get('target_detected_raw'), score, res.get('coords'), image_path)
            if new_shot_id and target_in_list:
                target_in_list['session_shot_ids'].append(new_shot_id)
                
        if self.shooting_mode == "BURST_3":
            self.testing_buffers[session_idx].append({'score': score, 'image': pix_frame})
            self._check_burst_completion(session_idx)
            
    def _check_burst_completion(self, session_idx):
        if len(self.testing_buffers[session_idx]) >= 3:
            self.burst_completed.emit(session_idx, self.testing_buffers[session_idx])
            if self.current_mode == 1:
                other_cam = 3 - session_idx
                if not self.is_camera_finished(other_cam):
                    self.next_shot_cam_id = other_cam
                    self.auto_switch_camera.emit(other_cam)
                else:
                    self.next_shot_cam_id = 1
    def get_auto_switch_target(self, current_target):
        if self.shooting_mode != "BURST_3" or self.current_mode != 1: return None
        cur_total = len(self.testing_buffers[current_target]) + self.pending_shots[current_target]
        if cur_total >= 3:
            other_cam = 2 if current_target == 1 else 1
            other_total = len(self.testing_buffers[other_cam]) + self.pending_shots[other_cam]
            if other_total < 3: return other_cam
            else: return -1
        return None