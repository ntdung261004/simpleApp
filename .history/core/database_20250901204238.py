# core/database.py
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    # ... (hàm __init__, _create_tables giữ nguyên) ...
    def __init__(self, db_path="shooting_range.db"):
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            logger.info(f"Đã kết nối thành công tới database: {self.db_path}")
            self._create_tables()
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kết nối hoặc tạo database: {e}")

    def _create_tables(self):
        try:
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    unit TEXT,
                    position TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    target_type TEXT,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    target_name_detected TEXT,
                    coord_x INTEGER,
                    coord_y INTEGER,
                    result_image_path TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                );
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo bảng: {e}")

    def add_user(self, name: str, unit: str = None, position: str = None) -> bool:
        try:
            sql = "INSERT INTO users (name, unit, position) VALUES (?, ?, ?)"
            self.cursor.execute(sql, (name, unit, position))
            self.conn.commit()
            logger.info(f"Đã thêm người bắn mới: {name}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Người bắn '{name}' đã tồn tại.")
            return False
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi thêm người bắn: {e}")
            return False

    def get_all_users(self) -> list:
        try:
            self.cursor.execute("SELECT id, name, unit, position FROM users ORDER BY name ASC")
            users = [{'id': row[0], 'name': row[1], 'unit': row[2], 'position': row[3]} for row in self.cursor.fetchall()]
            return users
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy danh sách người bắn: {e}")
            return []
    
    # ======================================================================
    # CHÚ THÍCH: CÁC HÀM MỚI ĐỂ QUẢN LÝ LẦN BẮN VÀ PHÁT BẮN
    # ======================================================================
    def create_session(self, user_id: int) -> int | None: # Bỏ tham số target_type
        """Tạo một lần bắn mới và trả về ID của nó."""
        try:
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Luôn đặt target_type là 'Hỗn hợp' để thể hiện sự linh hoạt
            sql = "INSERT INTO sessions (user_id, start_time, target_type) VALUES (?, ?, ?)"
            self.cursor.execute(sql, (user_id, start_time, "Hỗn hợp"))
            self.conn.commit()
            session_id = self.cursor.lastrowid
            logger.info(f"Đã bắt đầu Lần bắn mới (ID: {session_id}) cho user ID: {user_id}")
            return session_id
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo Lần bắn: {e}")
            return None

    def end_session(self, session_id: int):
        """Cập nhật thời gian kết thúc cho một Lần bắn."""
        try:
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sql = "UPDATE sessions SET end_time = ? WHERE id = ?"
            self.cursor.execute(sql, (end_time, session_id))
            self.conn.commit()
            logger.info(f"Đã kết thúc Lần bắn (ID: {session_id})")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kết thúc Lần bắn: {e}")

    def add_shot(self, session_id: int, score: int, target_name: str, 
                 coords: tuple | None, image_path: str):
        """Lưu thông tin một phát bắn vào database."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            coord_x = int(coords[0]) if coords else None
            coord_y = int(coords[1]) if coords else None
            
            sql = """
                INSERT INTO shots 
                (session_id, timestamp, score, target_name_detected, coord_x, coord_y, result_image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(sql, (session_id, timestamp, score, target_name, coord_x, coord_y, image_path))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lưu phát bắn: {e}")

    # ======================================================================
    # CHÚ THÍCH: CÁC HÀM MỚI ĐỂ TRUY XUẤT DỮ LIỆU
    # ======================================================================
    def get_sessions_for_user(self, user_id: int) -> list:
        """Lấy tất cả các lần bắn của một người dùng, sắp xếp mới nhất trước tiên."""
        try:
            sql = "SELECT id, start_time, end_time, target_type FROM sessions WHERE user_id = ? ORDER BY start_time DESC"
            self.cursor.execute(sql, (user_id,))
            sessions = [{'id': row[0], 'start_time': row[1], 'end_time': row[2], 'target_type': row[3]} 
                        for row in self.cursor.fetchall()]
            return sessions
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy danh sách Lần bắn: {e}")
            return []

    def get_shots_for_session(self, session_id: int) -> list:
        """Lấy tất cả các phát bắn của một lần bắn cụ thể."""
        try:
            sql = """
                SELECT id, timestamp, score, target_name_detected, coord_x, coord_y, result_image_path 
                FROM shots WHERE session_id = ? ORDER BY timestamp ASC
            """
            self.cursor.execute(sql, (session_id,))
            shots = [{'id': row[0], 'timestamp': row[1], 'score': row[2], 'target_name': row[3], 
                      'coords': (row[4], row[5]), 'image_path': row[6]} 
                     for row in self.cursor.fetchall()]
            return shots
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy chi tiết các phát bắn: {e}")
            return []


    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Đã đóng kết nối database.")