# file: core/database.py
import sqlite3
import logging
from datetime import datetime
import os
import shutil
import sys
from typing import Optional, List, Dict, Any
from config import APP_DATA_DIR
import json
import numpy as np

logger = logging.getLogger(__name__)

# Hàm này vẫn cần thiết cho chức năng Luyện tập (add_shot)
def convert_numpy_types(obj):
    if isinstance(obj, (np.integer, np.int_, np.intc, np.intp, np.int8,
                        np.int16, np.int32, np.int64, np.uint8,
                        np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float_, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    return obj

def get_app_data_path(file_name: str) -> str:
    dest_path = os.path.join(APP_DATA_DIR, file_name)
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    if not os.path.exists(dest_path):
        logger.info(f"Lần chạy đầu tiên: Sao chép database vào {dest_path}")
        try:
            source_path = os.path.join(sys._MEIPASS, file_name)
        except Exception:
            source_path = os.path.join(os.path.abspath("."), file_name)
        if os.path.exists(source_path): shutil.copyfile(source_path, dest_path)
        else: logger.warning(f"Không tìm thấy file database gốc: {source_path}. Sẽ tạo database trống.")
    return dest_path

class DatabaseManager:
    # --- Phần khởi tạo và các hàm khác giữ nguyên ---
    def __init__(self, db_name: str = "shooting_data.db"):
        self.db_path = get_app_data_path(db_name)
        self.conn: Optional[sqlite3.Connection] = None
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self._create_tables()
            self._update_schema()
            logger.info(f"Kết nối thành công tới database: {self.db_path}")
        except sqlite3.Error as e:
            logger.critical(f"Lỗi nghiêm trọng khi kết nối database: {e}")
            self.conn = None; self.cursor = None

    def _create_tables(self):
        if not self.cursor: return
        try:
            self.cursor.execute(""" CREATE TABLE IF NOT EXISTS soldiers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, class_name TEXT) """)
            self.cursor.execute(""" CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, soldier_id INTEGER NOT NULL, exercise_name TEXT, start_time TEXT NOT NULL, end_time TEXT, FOREIGN KEY (soldier_id) REFERENCES soldiers (id) ON DELETE CASCADE) """)
            self.cursor.execute(""" CREATE TABLE IF NOT EXISTS shots (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, shot_number INTEGER NOT NULL, score INTEGER, target_detected TEXT, coords TEXT, image_path TEXT, timestamp TEXT NOT NULL, FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE) """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS competitions (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    state TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            self.cursor.execute(""" CREATE TABLE IF NOT EXISTS competition_participants (id INTEGER PRIMARY KEY, competition_id INTEGER NOT NULL, soldier_id INTEGER NOT NULL, FOREIGN KEY (competition_id) REFERENCES competitions (id) ON DELETE CASCADE, FOREIGN KEY (soldier_id) REFERENCES soldiers (id) ON DELETE CASCADE) """)
            self.cursor.execute(""" CREATE TABLE IF NOT EXISTS competition_shots (id INTEGER PRIMARY KEY, competition_id INTEGER NOT NULL, participant_id INTEGER NOT NULL, shot_number INTEGER NOT NULL, score INTEGER, target_detected TEXT, coords TEXT, image_path TEXT, timestamp TEXT NOT NULL, FOREIGN KEY (competition_id) REFERENCES competitions (id) ON DELETE CASCADE, FOREIGN KEY (participant_id) REFERENCES soldiers (id) ON DELETE CASCADE) """)
            self.conn.commit()
        except sqlite3.Error as e: logger.error(f"Lỗi khi tạo bảng: {e}")

    def _update_schema(self):
        if not self.cursor: return
        try:
            self.cursor.execute("ALTER TABLE competitions ADD COLUMN state TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_competition_name ON competitions(name)')
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi thêm UNIQUE index: {e}")

    # --- Các hàm khác không liên quan đến lỗi giữ nguyên ---
    def add_soldier(self, name: str, class_name: str) -> Optional[int]:
        if not self.conn: return None
        try:
            self.cursor.execute("INSERT INTO soldiers (name, class_name) VALUES (?, ?)", (name, class_name)); self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e: logger.error(f"Lỗi khi thêm người bắn: {e}"); return None

    def get_all_soldiers(self) -> List[Dict[str, Any]]:
        if not self.conn: return []
        try: self.cursor.execute("SELECT * FROM soldiers ORDER BY name ASC"); return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e: logger.error(f"Lỗi khi lấy danh sách người bắn: {e}"); return []
        
    # === BẮT ĐẦU VÙNG THÊM MỚI: Hàm tìm kiếm người tập ===
    def search_soldiers(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Tìm kiếm người tập dựa trên tên hoặc đơn vị.
        """
        if not self.conn:
            return []
        try:
            query = "SELECT * FROM soldiers WHERE name LIKE ? OR class_name LIKE ? ORDER BY name ASC"
            # Thêm ký tự '%' để tìm kiếm một phần của chuỗi
            term = f"%{search_term}%"
            self.cursor.execute(query, (term, term))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tìm kiếm người tập: {e}")
            return []
    # === KẾT THÚC VÙNG THÊM MỚI ===

    def update_soldier(self, soldier_id: int, name: str, class_name: str) -> bool:
        if not self.conn: return False
        try: self.cursor.execute("UPDATE soldiers SET name = ?, class_name = ? WHERE id = ?", (name, class_name, soldier_id)); self.conn.commit(); return True
        except sqlite3.Error as e: logger.error(f"Lỗi khi cập nhật người bắn: {e}"); return False

    def delete_soldier(self, soldier_id: int) -> bool:
        if not self.conn: return False
        try: self.cursor.execute("DELETE FROM soldiers WHERE id = ?", (soldier_id,)); self.conn.commit(); return True
        except sqlite3.Error as e: logger.error(f"Lỗi khi xóa người bắn: {e}"); return False

    def create_session(self, soldier_id: int) -> Optional[int]:
        if not self.conn: return None
        try:
            start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute("INSERT INTO sessions (soldier_id, start_time) VALUES (?, ?)", (soldier_id, start_time)); self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e: logger.error(f"Lỗi khi tạo Phiên tập: {e}"); return None

    def end_session(self, session_id: int):
        if not self.conn: return
        try:
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute("UPDATE sessions SET end_time = ? WHERE id = ?", (end_time, session_id)); self.conn.commit()
        except sqlite3.Error as e: logger.error(f"Lỗi khi kết thúc Phiên tập: {e}")

    def add_shot(self, session_id: int, shot_number: int, score: int, target_detected: str, coords: Optional[tuple], image_path: str):
        if not self.conn: return
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            safe_coords = convert_numpy_types(coords)
            coords_str = json.dumps(safe_coords) if safe_coords is not None else None
            sql = "INSERT INTO shots (session_id, shot_number, score, target_detected, coords, image_path, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)"
            self.cursor.execute(sql, (session_id, shot_number, score, target_detected, coords_str, image_path, timestamp)); self.conn.commit()
        except (sqlite3.Error, TypeError) as e: logger.error(f"Lỗi khi lưu phát bắn (tập luyện): {e}")

    def add_competition_shot(self, competition_id: int, soldier_id: int, score: int, coords: Optional[list], image_path: str, target_name: str):
        if not self.conn:
            return
        try:
            self.cursor.execute("SELECT COUNT(id) FROM competition_shots WHERE competition_id = ? AND participant_id = ?", (competition_id, soldier_id))
            shot_count = self.cursor.fetchone()[0]
            shot_number = shot_count + 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            coords_str = json.dumps(coords) if coords is not None else None
            
            logger.info(f"LOG DATABASE: Chuẩn bị lưu phát bắn cho competition_id={competition_id}, soldier_id={soldier_id}. Chuỗi JSON tọa độ: {coords_str}")

            sql = "INSERT INTO competition_shots (competition_id, participant_id, shot_number, score, target_detected, coords, image_path, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            params = (competition_id, soldier_id, shot_number, score, target_name, coords_str, image_path, timestamp)
            self.cursor.execute(sql, params)
            self.conn.commit()
        except (sqlite3.Error, TypeError) as e: 
            logger.error(f"Lỗi khi thêm phát bắn (kiểm tra): {e}")
            self.conn.rollback()

    def competition_name_exists(self, name: str) -> bool:
        if not self.conn: return True
        try:
            sql = "SELECT 1 FROM competitions WHERE name = ?"
            self.cursor.execute(sql, (name,)); return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kiểm tra tên cuộc thi: {e}"); return True
            
    def create_competition(self, name: str, participant_soldier_ids: list) -> Optional[int]:
        if not self.conn: return None
        try:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute("INSERT INTO competitions (name, created_at, status) VALUES (?, ?, 'in_progress')", (name, created_at))
            competition_id = self.cursor.lastrowid
            participants_data = [(competition_id, soldier_id) for soldier_id in participant_soldier_ids]
            self.cursor.executemany("INSERT INTO competition_participants (competition_id, soldier_id) VALUES (?, ?)", participants_data)
            self.conn.commit()
            return competition_id
        except sqlite3.IntegrityError:
            logger.error(f"Lỗi khi tạo cuộc thi: Tên '{name}' đã tồn tại.")
            self.conn.rollback(); return None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo cuộc thi: {e}"); self.conn.rollback(); return None
            
    def get_sessions_for_soldier(self, soldier_id: int) -> list:
        if not self.conn: return []
        try:
            sql = "SELECT id, exercise_name, start_time AS session_date FROM sessions WHERE soldier_id = ? ORDER BY start_time DESC"
            self.cursor.execute(sql, (soldier_id,)); return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e: logger.error(f"Lỗi khi lấy danh sách Phiên bắn: {e}"); return []

    def get_shots_for_session(self, session_id: int) -> list:
        if not self.conn: return []
        try: self.cursor.execute("SELECT * FROM shots WHERE session_id = ? ORDER BY shot_number ASC", (session_id,)); return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e: logger.error(f"Lỗi khi lấy chi tiết các phát bắn: {e}"); return []

    def session_name_exists(self, name: str, soldier_id: int, exclude_session_id: int = None) -> bool:
        if not self.conn: return True
        try:
            sql, params = ("SELECT 1 FROM sessions WHERE exercise_name = ? AND soldier_id = ? AND id != ?", (name, soldier_id, exclude_session_id)) if exclude_session_id else ("SELECT 1 FROM sessions WHERE exercise_name = ? AND soldier_id = ?", (name, soldier_id))
            self.cursor.execute(sql, params); return self.cursor.fetchone() is not None
        except sqlite3.Error as e: logger.error(f"Lỗi khi kiểm tra tên phiên: {e}"); return True

    def update_session_name(self, session_id: int, new_name: str) -> bool:
        if not self.conn: return False
        try: self.cursor.execute("UPDATE sessions SET exercise_name = ? WHERE id = ?", (new_name, session_id)); self.conn.commit(); return True
        except sqlite3.Error as e: logger.error(f"Lỗi khi đổi tên phiên tập: {e}"); return False

    def delete_session(self, session_id: int) -> bool:
        if not self.conn: return False
        try: self.cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,)); self.conn.commit(); return True
        except sqlite3.Error as e: logger.error(f"Lỗi khi xóa phiên tập: {e}"); return False

    def delete_shots_for_turn(self, competition_id: int, soldier_id: int, num_shots_to_delete: int) -> bool:
        if not self.conn: return False
        try:
            sql_get_ids = "SELECT id FROM competition_shots WHERE competition_id = ? AND participant_id = ? ORDER BY id DESC LIMIT ?"
            self.cursor.execute(sql_get_ids, (competition_id, soldier_id, num_shots_to_delete))
            ids_to_delete = [row[0] for row in self.cursor.fetchall()]
            if not ids_to_delete: return True
            sql_delete = f"DELETE FROM competition_shots WHERE id IN ({','.join('?' for _ in ids_to_delete)})"
            self.cursor.execute(sql_delete, ids_to_delete)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa lượt bắn: {e}"); self.conn.rollback(); return False

    def save_competition_state(self, competition_id: int, state_json: str) -> bool:
        if not self.conn: return False
        try:
            sql = "UPDATE competitions SET state = ? WHERE id = ?"
            self.cursor.execute(sql, (state_json, competition_id)); self.conn.commit(); return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lưu trạng thái: {e}"); self.conn.rollback(); return False

    def get_competition(self, competition_id: int) -> Optional[Dict[str, Any]]:
        if not self.conn: return None
        try:
            sql = "SELECT * FROM competitions WHERE id = ?"
            self.cursor.execute(sql, (competition_id,)); row = self.cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy thông tin cuộc thi: {e}"); return None

    def get_saved_competitions(self) -> List[Dict[str, Any]]:
        if not self.conn: return []
        try:
            sql = """
                SELECT c.id, c.name, c.created_at, COUNT(p.id) as participant_count
                FROM competitions c LEFT JOIN competition_participants p ON c.id = p.competition_id
                WHERE c.status = 'in_progress' GROUP BY c.id ORDER BY c.created_at DESC
            """
            self.cursor.execute(sql); return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy các cuộc thi đã lưu: {e}"); return []

    def get_completed_competitions(self) -> List[Dict[str, Any]]:
        if not self.conn: return []
        try:
            sql = """
                SELECT c.id, c.name, c.created_at, COUNT(p.id) as participant_count
                FROM competitions c LEFT JOIN competition_participants p ON c.id = p.competition_id
                WHERE c.status = 'completed' GROUP BY c.id ORDER BY c.created_at DESC
            """
            self.cursor.execute(sql); return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy các cuộc thi đã hoàn thành: {e}"); return []

    def get_competition_ranking(self, competition_id: int) -> List[Dict[str, Any]]:
        if not self.conn: return []
        try:
            sql = """
                SELECT s.id as soldier_id, s.name, s.class_name, SUM(cs.score) as total_score
                FROM competition_shots cs JOIN soldiers s ON cs.participant_id = s.id
                WHERE cs.competition_id = ? GROUP BY s.id ORDER BY total_score DESC
            """
            self.cursor.execute(sql, (competition_id,)); return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy bảng xếp hạng: {e}"); return []

    def get_shots_for_competition(self, competition_id: int, participant_id: int = None) -> list:
        if not self.conn: return []
        try:
            if participant_id:
                sql = "SELECT * FROM competition_shots WHERE competition_id = ? AND participant_id = ? ORDER BY shot_number ASC"
                params = (competition_id, participant_id)
            else:
                sql = "SELECT * FROM competition_shots WHERE competition_id = ? ORDER BY participant_id, shot_number ASC"
                params = (competition_id,)
            self.cursor.execute(sql, params)
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy chi tiết phát bắn cuộc thi: {e}")
            return []

    def update_competition_status(self, competition_id: int, status: str) -> bool:
        if not self.conn: return False
        try:
            sql = "UPDATE competitions SET status = ? WHERE id = ?"
            self.cursor.execute(sql, (status, competition_id)); self.conn.commit(); return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi cập nhật trạng thái: {e}"); self.conn.rollback(); return False

    def delete_competition(self, competition_id: int) -> bool:
        if not self.conn: return False
        try:
            sql = "DELETE FROM competitions WHERE id = ?"
            self.cursor.execute(sql, (competition_id,)); self.conn.commit(); return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa cuộc thi: {e}"); self.conn.rollback(); return False

    def close(self):
        if self.conn: self.conn.close()