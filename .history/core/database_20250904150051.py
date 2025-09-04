# core/database.py
import sqlite3
import logging
from datetime import datetime

# Cấu hình logger để theo dõi hoạt động của database
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path="shooting_range.db"):
        """Khởi tạo và kết nối tới database SQLite."""
        self.db_path = db_path
        self.conn = None
        try:
            # Kết nối tới database, check_same_thread=False cần cho đa luồng
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            logger.info(f"Đã kết nối thành công tới database: {self.db_path}")
            # Bật hỗ trợ khóa ngoại
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            # Gọi hàm tạo bảng
            self._create_tables()
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kết nối hoặc tạo database: {e}")

    def _create_tables(self):
        """Tạo tất cả các bảng theo cấu trúc mới nếu chúng chưa tồn tại."""
        try:
            # Bảng 1: SOLDIERS (CHIẾN SĨ)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS soldiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    rank TEXT,
                    position TEXT,
                    unit TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # Bảng 2: SESSIONS (PHIÊN BẮN)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    soldier_id INTEGER NOT NULL,
                    session_date TEXT NOT NULL,
                    exercise_name TEXT,
                    notes TEXT,
                    FOREIGN KEY (soldier_id) REFERENCES soldiers (id) ON DELETE CASCADE
                );
            """)

            # Bảng 3: SHOTS (PHÁT BẮN)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    shot_number INTEGER NOT NULL,
                    target_detected TEXT,
                    score INTEGER,
                    hit_coordinate_x REAL,
                    hit_coordinate_y REAL,
                    image_path TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                );
            """)
            self.conn.commit()
            logger.info("Các bảng đã được kiểm tra và sẵn sàng.")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo bảng: {e}")
            
    # ======================================================================
    # CÁC HÀM QUẢN LÝ CHIẾN SĨ (SOLDIERS)
    # ======================================================================
    def add_soldier(self, name: str, rank: str, position: str, unit: str) -> bool:
        """Thêm một chiến sĩ mới vào database."""
        try:
            sql = "INSERT INTO soldiers (name, rank, position, unit, created_at) VALUES (?, ?, ?, ?, ?)"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(sql, (name, rank, position, unit, timestamp))
            self.conn.commit()
            logger.info(f"Đã thêm chiến sĩ mới: {name}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Chiến sĩ '{name}' đã tồn tại.")
            return False
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi thêm chiến sĩ: {e}")
            return False

    def get_all_soldiers(self) -> list:
        """Lấy danh sách tất cả chiến sĩ."""
        try:
            self.cursor.execute("SELECT id, name, rank, position, unit FROM soldiers ORDER BY name ASC")
            # Trả về list các dictionary để dễ sử dụng
            soldiers = [dict(zip([col[0] for col in self.cursor.description], row)) for row in self.cursor.fetchall()]
            return soldiers
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy danh sách chiến sĩ: {e}")
            return []

    # ======================================================================
    # CÁC HÀM QUẢN LÝ PHIÊN BẮN (SESSIONS) VÀ PHÁT BẮN (SHOTS)
    # ======================================================================
    def create_session(self, soldier_id: int, exercise_name: str = "Bài bắn tự do", notes: str = "") -> int | None:
        """Tạo một phiên bắn mới và trả về ID của phiên đó."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sql = "INSERT INTO sessions (soldier_id, session_date, exercise_name, notes) VALUES (?, ?, ?, ?)"
            self.cursor.execute(sql, (soldier_id, timestamp, exercise_name, notes))
            self.conn.commit()
            session_id = self.cursor.lastrowid
            logger.info(f"Đã bắt đầu Phiên bắn ID: {session_id} cho soldier_id: {soldier_id}")
            return session_id
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi tạo Phiên bắn: {e}")
            return None

    def add_shot(self, session_id: int, shot_number: int, target_detected: str, 
                 score: int, coords: tuple | None, image_path: str):
        """Lưu thông tin một phát bắn vào database."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            coord_x = float(coords[0]) if coords else None
            coord_y = float(coords[1]) if coords else None
            
            sql = """
                INSERT INTO shots 
                (session_id, shot_number, target_detected, score, hit_coordinate_x, hit_coordinate_y, image_path, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(sql, (session_id, shot_number, target_detected, score, coord_x, coord_y, image_path, timestamp))
            self.conn.commit()
            logger.info(f"Đã lưu phát bắn số {shot_number} cho Phiên bắn ID: {session_id}")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lưu phát bắn: {e}")

    # ======================================================================
    # CÁC HÀM TRUY XUẤT DỮ LIỆU ĐỂ THỐNG KÊ
    # ======================================================================
    def get_sessions_for_soldier(self, soldier_id: int) -> list:
        """Lấy tất cả các phiên bắn của một chiến sĩ, sắp xếp mới nhất trước tiên."""
        try:
            sql = "SELECT * FROM sessions WHERE soldier_id = ? ORDER BY session_date DESC"
            self.cursor.execute(sql, (soldier_id,))
            sessions = [dict(zip([col[0] for col in self.cursor.description], row)) for row in self.cursor.fetchall()]
            return sessions
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy danh sách Phiên bắn: {e}")
            return []

    def get_shots_for_session(self, session_id: int) -> list:
        """Lấy tất cả các phát bắn của một phiên bắn cụ thể."""
        try:
            sql = "SELECT * FROM shots WHERE session_id = ? ORDER BY shot_number ASC"
            self.cursor.execute(sql, (session_id,))
            shots = [dict(zip([col[0] for col in self.cursor.description], row)) for row in self.cursor.fetchall()]
            return shots
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy chi tiết các phát bắn: {e}")
            return []

    def close(self):
        """Đóng kết nối database một cách an toàn."""
        if self.conn:
            self.conn.close()
            logger.info("Đã đóng kết nối database.")