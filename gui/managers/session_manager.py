# file: gui/managers/session_manager.py
from PySide6.QtCore import QObject, Signal
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SessionManager(QObject):
    # Signals báo thay đổi trạng thái
    session_state_changed = Signal(int, bool) # session_idx, is_active
    shot_added = Signal(int, int, int, str) # session_idx, shot_number, score, score_text
    burst_completed = Signal(int, list) # session_idx, buffer_data (để hiện popup)
    auto_switch_camera = Signal(int) # target_cam_id

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        
        # Cấu hình
        self.is_free_practice = False
        self.is_managed_session = False
        self.shooting_mode = "SINGLE" # SINGLE | BURST_3
        self.current_mode = 0 # 0: Single, 1: Dual
        self.next_shot_cam_id = 1

        # Data Structures
        self.active_session_ids = {0: None, 1: None, 2: None}
        self.session_active_flags = {0: False, 1: False, 2: False}
        self.shot_counters = {0: 0, 1: 0, 2: 0}
        self.testing_buffers = {0: [], 1: [], 2: []}
        self.pending_shots = {0: 0, 1: 0, 2: 0}
        
        # Managed Data
        self.managed_data = {} # {0: {...}, 1: {...}, 2: {...}}
        self.selected_soldiers = {0: None, 1: None, 2: None}

        # ID của "Khách vãng lai" cho Free Practice
        self.free_soldier_id = self._get_or_create_free_soldier()

    def _get_or_create_free_soldier(self):
        soldiers = self.db.get_all_soldiers()
        for s in soldiers:
            if s['name'] == "Khách (Tự do)": return s['id']
        return self.db.add_soldier("Khách (Tự do)", "Hệ thống")

    def setup_managed_session(self, name, type, soldiers):
        """Khởi tạo dữ liệu cho chế độ Luyện tập theo phiên."""
        self.is_managed_session = True
        self.is_free_practice = False
        self.shooting_mode = type
        
        init_status = {s['id']: 0 for s in soldiers}
        session_info = {
            'name': name,
            'type': type,
            'soldiers': soldiers,
            'status': init_status
        }
        for i in [0, 1, 2]:
            self.managed_data[i] = session_info.copy()

    def start_session(self, session_idx, soldier_data=None):
        """Bắt đầu một phiên bắn cụ thể (Free hoặc Managed)."""
        if self.session_active_flags[session_idx]:
            self.end_session(session_idx)

        self._reset_counters(session_idx)
        
        if self.is_free_practice:
            sid = self.db.create_session(self.free_soldier_id)
        else:
            # Managed Session
            if not soldier_data: return
            self.selected_soldiers[session_idx] = soldier_data
            sid = self.db.create_session(
                soldier_data['id'], 
                exercise_name=self.managed_data[session_idx]['name']
            )

        self.active_session_ids[session_idx] = sid
        self.session_active_flags[session_idx] = True
        self.session_state_changed.emit(session_idx, True)

    def end_session(self, session_idx):
        """Kết thúc phiên bắn."""
        if not self.session_active_flags[session_idx]: return

        sid = self.active_session_ids[session_idx]
        if sid and sid > 0:
            count = self.db.get_shot_count_for_session(sid)
            if count == 0:
                self.db.delete_session(sid)
            else:
                if self.is_free_practice:
                    auto_name = f"Phiên tự do {datetime.now().strftime('%H:%M %d/%m')}"
                    self.db.update_session_name(sid, auto_name)
                self.db.end_session(sid)

        self.session_active_flags[session_idx] = False
        self.active_session_ids[session_idx] = None
        self.session_state_changed.emit(session_idx, False)

    def reset_all(self):
        """Reset toàn bộ trạng thái (khi đổi mode, back menu)."""
        for i in [0, 1, 2]:
            self.end_session(i)
            self._reset_counters(i)
        self.next_shot_cam_id = 1

    def _reset_counters(self, idx):
        self.shot_counters[idx] = 0
        self.testing_buffers[idx] = []
        self.pending_shots[idx] = 0

    def check_can_shot(self, cam_id):
        """Kiểm tra xem có được phép bắn không (chế độ Burst)."""
        if self.shooting_mode == "BURST_3":
            current = len(self.testing_buffers[cam_id])
            pending = self.pending_shots[cam_id]
            if current + pending >= 3:
                return False
        return True

    def register_pending_shot(self, cam_id):
        """Ghi nhận một viên đạn đang bay (để chặn bắn lố)."""
        if self.shooting_mode == "BURST_3":
            self.pending_shots[cam_id] += 1

    def process_shot_result(self, res):
        """Xử lý kết quả từ Worker trả về."""
        score = res.get('score')
        image_path = res.get('image_path')
        
        # Parse session_idx từ tên file ảnh (quy ước s{idx}_...)
        session_idx = 0
        try:
            name = os.path.basename(image_path)
            if name.startswith('s'): session_idx = int(name.split('_')[0][1:])
        except: pass

        # Giảm pending
        self.pending_shots[session_idx] = max(0, self.pending_shots[session_idx] - 1)

        # Logic hiển thị text
        score_text = f"Điểm: {score}"
        if self.shooting_mode == "BURST_3":
            count = len(self.testing_buffers[session_idx]) + 1
            score_text = f"Điểm: {score} (Phát {count}/3)"
        elif self.session_active_flags[session_idx]:
            current_no = self.shot_counters[session_idx] + 1
            score_text = f"Điểm: {score} | Phát thứ: {current_no}"

        # Emit để update UI ngay lập tức
        self.shot_added.emit(session_idx, score, score, score_text)

        # Lưu DB
        sid = self.active_session_ids[session_idx]
        if self.session_active_flags[session_idx] and sid > 0:
            self.shot_counters[session_idx] += 1
            self.db.add_shot(
                sid, self.shot_counters[session_idx], 
                res.get('target_detected_raw'), score, 
                res.get('coords'), image_path
            )
            
            # Cập nhật Managed Status
            if self.is_managed_session:
                s_data = self.selected_soldiers[session_idx]
                if s_data:
                    current_status = self.managed_data[session_idx]['status']
                    current_status[s_data['id']] = current_status.get(s_data['id'], 0) + 1
                    # Cần emit signal update list status ở window

        # Logic Burst Mode
        if self.shooting_mode == "BURST_3":
            self.testing_buffers[session_idx].append({
                'score': score, 
                'image': res.get('result_frame') # Dạng numpy, Window sẽ convert
            })
            
            # Kiểm tra điều kiện hiện popup
            self._check_burst_completion()

    def _check_burst_completion(self):
        """Kiểm tra xem đã bắn đủ 3 viên chưa để hiện Popup."""
        if self.current_mode == 0:
            # Single Cam Mode
            if len(self.testing_buffers[0]) >= 3:
                self.burst_finished.emit(0, self.testing_buffers[0])
                self._reset_counters(0) # Reset sau khi bắn xong đợt
        elif self.current_mode == 1:
            # Dual Cam Mode
            buf1 = len(self.testing_buffers[1])
            buf2 = len(self.testing_buffers[2])
            pen1 = self.pending_shots[1]
            pen2 = self.pending_shots[2]
            
            # Chỉ hiện khi CẢ 2 đều xong và không còn đạn đang bay
            if buf1 >= 3 and buf2 >= 3 and pen1 == 0 and pen2 == 0:
                self.burst_finished.emit(1, self.testing_buffers[1])
                self.burst_finished.emit(2, self.testing_buffers[2])
                
                self._reset_counters(1)
                self._reset_counters(2)
                self.next_shot_cam_id = 1
                self.auto_switch_camera.emit(1) # Reset về cam 1

    def get_auto_switch_target(self, current_target):
        """Logic tự động chuyển camera khi bắn đủ 3 viên (Dual Mode)."""
        if self.shooting_mode != "BURST_3" or self.current_mode != 1:
            return None
            
        cur_total = len(self.testing_buffers[current_target]) + self.pending_shots[current_target]
        if cur_total >= 3:
            other_cam = 2 if current_target == 1 else 1
            other_total = len(self.testing_buffers[other_cam]) + self.pending_shots[other_cam]
            
            if other_total < 3:
                logger.info(f"SessionManager: Cam {current_target} đầy. Auto-switch -> {other_cam}")
                return other_cam
            else:
                logger.info("SessionManager: Cả 2 Cam đều đầy.")
                return -1 # Chặn bắn
        return None