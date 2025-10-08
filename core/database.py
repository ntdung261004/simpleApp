# file: core/database.py
import sqlite3
import logging
from datetime import datetime
import os
import shutil
import sys
from typing import Optional, List, Dict, Any
from config import APP_DATA_DIR
import json # Thêm import json để xử lý coords

# Cấu hình logger
logger = logging.getLogger(__name__)

def get_app_data_path(file_name: str) -> str:
    """
    Lấy đường dẫn tuyệt đối tới file trong APP_DATA_DIR.
    Nếu file chưa tồn tại, sao chép từ file gốc đi kèm ứng dụng.
    """
    dest_path = os.path.join(APP_DATA_DIR, file_name)
    os.makedirs(APP_DATA_DIR, exist_ok=True)

    if not os.path.exists(dest_path):
        logger.info(f"Lần chạy đầu tiên: Sao chép database vào {dest_path}")
        if getattr(sys, 'frozen', False):
            source_path = os.path.join(sys._MEIPASS, file_name)
        else:
            source_path = os.path.join(os.path.abspath("."), file_name)

        if os.path.exists(source_path):
            shutil.copyfile(source_path, dest_path)
        else:
            logger.warning(f"Không tìm thấy file database gốc tại: {source_path}. Sẽ tạo database trống.")
    
    return dest_path


class DatabaseManager:
    """Lớp quản lý tập trung tất cả các thao tác với cơ sở dữ liệu SQLite."""
    
    def __init__(self, db_name: str = "shooting_data.db"):
        """Khởi tạo và kết nối tới database, bật khóa ngoại."""
        self.db_path = get_app_data_path(db_name)
        self.conn: Optional[sqlite3.Connection] = None
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Cho phép truy cập cột bằng tên
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON;") # Bật hỗ trợ khóa ngoại
            self._create_tables()
            logger.info(f"Kết nối thành công tới database: {self.db_path}")
        except sqlite3.Error as e:
            logger.critical(f"Lỗi nghiêm trọng khi kết nối database: {e}")
            self.conn = None
            self.cursor = None

    def _create_tables(self):
        """Tạo tất cả các bảng cần thiết nếu chúng chưa tồn tại."""
        if not self.cursor: return
        try:
            # --- CÁC BẢNG CƠ BẢN ---
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS soldiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    class_name TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    soldier_id INTEGER NOT NULL,
                    exercise_name TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    FOREIGN KEY (soldier_id) REFERENCES soldiers (id) ON DELETE CASCADE
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    shot_number INTEGER NOT NULL,
                    score INTEGER,
                    target_detected TEXT,
                    coords TEXT,
                    image_path TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            
            # --- CÁC BẢNG MỚI CHO CHỨC NĂNG THI ĐẤU ---
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS competitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    status TEXT DEFAULT 'ongoing', -- Các trạng thái: 'ongoing', 'finished'
                    created_at TEXT NOT NULL
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS competition_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competition_id INTEGER NOT NULL,
                    soldier_id INTEGER NOT NULL,
                    FOREIGN KEY (competition_id) REFERENCES competitions (id) ON DELETE CASCADE,
                    FOREIGN KEY (soldier_id) REFERENCES soldiers (id) ON DELETE CASCADE
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS competition_shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competition_id INTEGER NOT NULL,
                    participant_id INTEGER NOT NULL, -- Tham chiếu đến competition_participants.id
                    shot_number INTEGER NOT NULL,
                    score INTEGER,
                    target_detected TEXT,
                    coords TEXT,
                    image_path TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (competition_id) REFERENCES competitions (id) ON DELETE CASCADE,
                    FOREIGN KEY (participant_id) REFERENCES competition_participants (id) ON DELETE CASCADE
                )
            """)
            
            self.conn.commit()
            logger.info("Kiểm tra và tạo các bảng thành công.")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo bảng: {e}")

    # === QUẢN LÝ NGƯỜI BẮN (SOLDIERS) ===
    def add_soldier(self, name: str, class_name: str) -> Optional[int]:
        if not self.conn: return None
        try:
            self.cursor.execute("INSERT INTO soldiers (name, class_name) VALUES (?, ?)", (name, class_name))
            self.conn.commit()
            new_id = self.cursor.lastrowid
            logger.info(f"Đã thêm người bắn: {name} (ID: {new_id})")
            return new_id
        except sqlite3.IntegrityError:
             logger.warning(f"Người bắn '{name}' - Lớp '{class_name}' đã tồn tại.")
             return None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi thêm người bắn: {e}")
            return None

    def get_all_soldiers(self) -> List[Dict[str, Any]]:
        if not self.conn: return []
        try:
            self.cursor.execute("SELECT * FROM soldiers ORDER BY name ASC")
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy danh sách người bắn: {e}")
            return []

    def update_soldier(self, soldier_id: int, name: str, class_name: str) -> bool:
        if not self.conn: return False
        try:
            self.cursor.execute("UPDATE soldiers SET name = ?, class_name = ? WHERE id = ?", (name, class_name, soldier_id))
            self.conn.commit()
            logger.info(f"Đã cập nhật thông tin cho người bắn ID: {soldier_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi cập nhật người bắn: {e}")
            return False

    def delete_soldier(self, soldier_id: int) -> bool:
        if not self.conn: return False
        try:
            self.cursor.execute("DELETE FROM soldiers WHERE id = ?", (soldier_id,))
            self.conn.commit()
            logger.info(f"Đã xóa người bắn ID: {soldier_id} và tất cả dữ liệu liên quan.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa người bắn: {e}")
            return False

    # === QUẢN LÝ PHIÊN TẬP (SESSIONS) ===
    def create_session(self, soldier_id: int) -> Optional[int]:
        if not self.conn: return None
        try:
            start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute("INSERT INTO sessions (soldier_id, start_time, exercise_name) VALUES (?, ?, ?)", (soldier_id, start_time, "Bài bắn tự do"))
            self.conn.commit()
            session_id = self.cursor.lastrowid
            logger.info(f"Đã bắt đầu Phiên tập ID: {session_id} cho soldier_id: {soldier_id}")
            return session_id
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo Phiên tập: {e}")
            return None

    def end_session(self, session_id: int):
        if not self.conn: return
        try:
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute("UPDATE sessions SET end_time = ? WHERE id = ?", (end_time, session_id))
            self.conn.commit()
            logger.info(f"Đã kết thúc Phiên tập ID: {session_id}")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kết thúc Phiên tập: {e}")

    def add_shot(self, session_id: int, shot_number: int, score: int, target_detected: str, coords: Optional[tuple], image_path: str):
        if not self.conn: return
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            coords_str = json.dumps(coords) if coords else None
            sql = "INSERT INTO shots (session_id, shot_number, score, target_detected, coords, image_path, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)"
            self.cursor.execute(sql, (session_id, shot_number, score, target_detected, coords_str, image_path, timestamp))
            self.conn.commit()
            logger.info(f"Đã lưu phát bắn số {shot_number} cho Phiên tập ID: {session_id}")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lưu phát bắn: {e}")

    def update_session_name(self, session_id: int, new_name: str) -> bool:
        if not self.conn: return False
        try:
            self.cursor.execute("UPDATE sessions SET exercise_name = ? WHERE id = ?", (new_name, session_id))
            self.conn.commit()
            logger.info(f"Đã đổi tên phiên tập ID: {session_id} thành '{new_name}'")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi đổi tên phiên tập: {e}")
            return False

    def delete_session(self, session_id: int) -> bool:
        if not self.conn: return False
        try:
            self.cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self.conn.commit()
            logger.info(f"Đã xóa phiên tập ID: {session_id} và các phát bắn liên quan.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa phiên tập: {e}")
            return False
            
    def get_shot_count_for_session(self, session_id: int) -> int:
        if not self.conn: return 0
        try:
            self.cursor.execute("SELECT COUNT(id) FROM shots WHERE session_id = ?", (session_id,))
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi đếm số phát bắn cho phiên {session_id}: {e}")
            return 0

    def get_sessions_for_soldier(self, soldier_id: int) -> list:
        if not self.conn: return []
        try:
            self.cursor.execute("SELECT * FROM sessions WHERE soldier_id = ? ORDER BY start_time DESC", (soldier_id,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy danh sách Phiên bắn: {e}")
            return []

    def get_shots_for_session(self, session_id: int) -> list:
        if not self.conn: return []
        try:
            self.cursor.execute("SELECT * FROM shots WHERE session_id = ? ORDER BY shot_number ASC", (session_id,))
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy chi tiết các phát bắn: {e}")
            return []
            
    def session_name_exists(self, name: str, soldier_id: int, exclude_session_id: int = None) -> bool:
        if not self.conn: return True
        try:
            if exclude_session_id:
                sql = "SELECT 1 FROM sessions WHERE exercise_name = ? AND soldier_id = ? AND id != ?"
                params = (name, soldier_id, exclude_session_id)
            else:
                sql = "SELECT 1 FROM sessions WHERE exercise_name = ? AND soldier_id = ?"
                params = (name, soldier_id)
            
            self.cursor.execute(sql, params)
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kiểm tra tên phiên: {e}")
            return True

    # === QUẢN LÝ THI ĐẤU (COMPETITIONS) ===
    def create_competition(self, name: str, participant_ids: list) -> Optional[int]:
        """Tạo một cuộc thi mới và thêm danh sách người tham gia."""
        if not self.conn: return None
        try:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute("INSERT INTO competitions (name, created_at) VALUES (?, ?)", (name, created_at))
            competition_id = self.cursor.lastrowid
            
            participants_data = [(competition_id, soldier_id) for soldier_id in participant_ids]
            self.cursor.executemany("INSERT INTO competition_participants (competition_id, soldier_id) VALUES (?, ?)", participants_data)
            
            self.conn.commit()
            logger.info(f"Đã tạo cuộc thi mới ID: {competition_id} với {len(participant_ids)} người tham gia.")
            return competition_id
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo cuộc thi: {e}")
            self.conn.rollback()
            return None
        
    def add_competition_shot(self, competition_id: int, shooter_id: int, score: int, coords: str, image_path: str, target_name: str) -> Optional[int]:
        """Lưu thông tin một phát bắn trong cuộc thi vào CSDL."""
        if not self.conn: return None
        try:
            sql = """
                INSERT INTO competition_shots 
                (competition_id, soldier_id, score, coords, image_path, target_name, shot_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            shot_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            params = (competition_id, shooter_id, score, coords, image_path, target_name, shot_time)
            self.cursor.execute(sql, params)
            self.conn.commit()
            shot_id = self.cursor.lastrowid
            logger.info(f"Đã lưu phát bắn ID {shot_id} cho cuộc thi ID {competition_id}.")
            return shot_id
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi thêm phát bắn vào cuộc thi: {e}")
            self.conn.rollback()
            return None
            
    def close(self):
        """Đóng kết nối database một cách an toàn."""
        if self.conn:
            self.conn.close()
            logger.info("Đã đóng kết nối database.")