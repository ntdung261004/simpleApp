import sqlite3
import logging
from datetime import datetime
import os
import shutil
import sys
from config import APP_DATA_DIR

# Cấu hình logger để theo dõi hoạt động của database
logger = logging.getLogger(__name__)

def get_app_data_path(file_name):
    """
    Lấy đường dẫn tuyệt đối tới file trong APP_DATA_DIR.
    Nếu file chưa tồn tại, sao chép từ file gốc đi kèm ứng dụng.
    """
    # Đây là đường dẫn cuối cùng mà ứng dụng sẽ làm việc
    dest_path = os.path.join(APP_DATA_DIR, file_name)

    # Đảm bảo thư mục tồn tại
    os.makedirs(APP_DATA_DIR, exist_ok=True)

    # Chỉ thực hiện sao chép trong lần chạy đầu tiên
    if not os.path.exists(dest_path):
        logger.info(f"Lần chạy đầu tiên: Sao chép database vào {dest_path}")

        # Tìm file database gốc được đóng gói cùng ứng dụng
        if getattr(sys, 'frozen', False):
            # Khi app đã được build (.exe, .app)
            source_path = os.path.join(sys._MEIPASS, file_name)
        else:
            # Khi chạy từ mã nguồn
            source_path = os.path.join(os.path.abspath("."), file_name)

        if os.path.exists(source_path):
            shutil.copyfile(source_path, dest_path)
        else:
            logger.warning(f"Không tìm thấy file database gốc tại: {source_path}")
            # Ứng dụng có thể tự tạo database trống
            return dest_path

    return dest_path


class DatabaseManager:
    def __init__(self, db_name="shooting_range.db"):
        """Khởi tạo và kết nối tới database SQLite."""
        # SỬA ĐỔI QUAN TRỌNG: Gọi hàm mới để lấy đường dẫn database
        self.db_path = get_app_data_path(db_name)
        self.conn = None
        try:
            # Kết nối tới database, check_same_thread=False cần cho đa luồng
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            logger.info(f"Đã kết nối thành công tới database tại AppData: {self.db_path}")
            # Bật hỗ trợ khóa ngoại
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            # Gọi hàm tạo bảng
            self._create_tables()
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kết nối hoặc tạo database: {e}")
            
    def _create_tables(self):
        """Tạo tất cả các bảng theo cấu trúc mới nếu chúng chưa tồn tại."""
        try:
            # Bảng 1: SOLDIERS (CHIẾN SĨ) - ĐÃ CẬP NHẬT
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS soldiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    class_name TEXT,
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
    def add_soldier(self, name: str, class_name: str) -> int | None:
        """Thêm một chiến sĩ mới và trả về ID của người đó."""
        try:
            sql = "INSERT INTO soldiers (name, class_name, created_at) VALUES (?, ?, ?)"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(sql, (name, class_name, timestamp))
            self.conn.commit()
            new_id = self.cursor.lastrowid
            logger.info(f"Đã thêm chiến sĩ mới: {name} (ID: {new_id})")
            return new_id
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi thêm chiến sĩ: {e}")
            return None

    def get_all_soldiers(self) -> list:
        """Lấy danh sách tất cả chiến sĩ."""
        try:
            self.cursor.execute("SELECT id, name, class_name FROM soldiers ORDER BY class_name ASC, name ASC")
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

    def end_session(self, session_id: int):
        """
        Hàm này được gọi khi một phiên tập kết thúc.
        Hiện tại chỉ ghi log, không thay đổi CSDL.
        """
        if not session_id:
            return
        logger.info(f"Hàm end_session được gọi cho phiên ID: {session_id}. Phiên tập đã hoàn tất.")

    def get_shot_count_for_session(self, session_id: int) -> int:
        """Đếm và trả về tổng số phát bắn trong một phiên."""
        try:
            sql = "SELECT COUNT(id) FROM shots WHERE session_id = ?"
            self.cursor.execute(sql, (session_id,))
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi đếm số phát bắn cho phiên {session_id}: {e}")
            return 0

    def update_session_name(self, session_id: int, name: str):
        """Cập nhật tên/ghi chú cho một phiên bắn."""
        try:
            sql = "UPDATE sessions SET exercise_name = ? WHERE id = ?"
            self.cursor.execute(sql, (name, session_id))
            self.conn.commit()
            logger.info(f"Đã cập nhật tên cho phiên {session_id} thành '{name}'")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi cập nhật tên phiên {session_id}: {e}")

    def delete_session(self, session_id: int):
        """Xóa một phiên bắn khỏi cơ sở dữ liệu."""
        try:
            # Bảng shots đã có ON DELETE CASCADE nên các phát bắn sẽ tự xóa theo
            sql = "DELETE FROM sessions WHERE id = ?"
            self.cursor.execute(sql, (session_id,))
            self.conn.commit()
            logger.info(f"Đã xóa thành công phiên bắn ID: {session_id}")
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa phiên {session_id}: {e}")

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

    def get_session_by_id(self, session_id: int) -> dict | None:
        """Lấy thông tin chi tiết của một phiên bắn cụ thể bằng ID."""
        try:
            sql = "SELECT * FROM sessions WHERE id = ?"
            self.cursor.execute(sql, (session_id,))
            session_data = self.cursor.fetchone()
            if session_data:
                # Chuyển đổi tuple thành dictionary để dễ sử dụng
                return dict(zip([col[0] for col in self.cursor.description], session_data))
            return None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi lấy thông tin phiên bắn ID {session_id}: {e}")
            return None
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

# Thêm 4 hàm này vào bên trong class DatabaseManager của file core/database.py

    def update_soldier(self, soldier_id: int, name: str, class_name: str):
        """Cập nhật thông tin cho một chiến sĩ."""
        try:
            sql = """
                UPDATE soldiers 
                SET name = ?, class_name = ?
                WHERE id = ?
            """
            self.cursor.execute(sql, (name, class_name, soldier_id))
            self.conn.commit()
            logger.info(f"Đã cập nhật thông tin cho chiến sĩ ID: {soldier_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi cập nhật chiến sĩ: {e}")
            return False

    def delete_soldier(self, soldier_id: int):
        """Xóa một chiến sĩ và tất cả dữ liệu liên quan (phiên, phát bắn)."""
        try:
            # PRAGMA foreign_keys = ON; đã được bật, CSDL sẽ tự xóa các phiên và phát bắn liên quan
            self.cursor.execute("DELETE FROM soldiers WHERE id = ?", (soldier_id,))
            self.conn.commit()
            logger.info(f"Đã xóa chiến sĩ ID: {soldier_id} và tất cả dữ liệu liên quan.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa chiến sĩ: {e}")
            return False

    def update_session_name(self, session_id: int, new_name: str):
        """Cập nhật (đổi tên) cho một phiên tập."""
        try:
            sql = "UPDATE sessions SET exercise_name = ? WHERE id = ?"
            self.cursor.execute(sql, (new_name, session_id))
            self.conn.commit()
            logger.info(f"Đã đổi tên phiên tập ID: {session_id} thành '{new_name}'")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi đổi tên phiên tập: {e}")
            return False

    def delete_session(self, session_id: int):
        """Xóa một phiên tập và các phát bắn liên quan."""
        try:
            # CSDL sẽ tự xóa các phát bắn liên quan do có foreign key
            self.cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self.conn.commit()
            logger.info(f"Đã xóa phiên tập ID: {session_id} và các phát bắn liên quan.")
            return True
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi xóa phiên tập: {e}")
            return False

    def session_name_exists(self, name: str, soldier_id: int, exclude_session_id: int = None) -> bool:
        """
        Kiểm tra xem tên phiên tập đã tồn tại cho một chiến sĩ cụ thể hay chưa.
        """
        try:
            # Nếu đang sửa tên, loại trừ chính phiên đó ra khỏi kiểm tra
            if exclude_session_id:
                sql = "SELECT 1 FROM sessions WHERE exercise_name = ? AND soldier_id = ? AND id != ?"
                params = (name, soldier_id, exclude_session_id)
            # Nếu tạo mới, kiểm tra tất cả các phiên của chiến sĩ đó
            else:
                sql = "SELECT 1 FROM sessions WHERE exercise_name = ? AND soldier_id = ?"
                params = (name, soldier_id)
            
            self.cursor.execute(sql, params)
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Lỗi khi kiểm tra tên phiên: {e}")
            return True # Mặc định trả về True để tránh ghi đè dữ liệu

    def close(self):
        """Đóng kết nối database một cách an toàn."""
        if self.conn:
            self.conn.close()
            logger.info("Đã đóng kết nối database.")