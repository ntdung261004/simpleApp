# file: core/database.py
import sqlite3
import logging
from datetime import datetime
import os
import shutil
import sys
from config import APP_DATA_DIR

logger = logging.getLogger(__name__)

def get_app_data_path(file_name):
    dest_path = os.path.join(APP_DATA_DIR, file_name)
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    if not os.path.exists(dest_path):
        if getattr(sys, 'frozen', False):
            source_path = os.path.join(sys._MEIPASS, file_name)
        else:
            source_path = os.path.join(os.path.abspath("."), file_name)
        if os.path.exists(source_path):
            shutil.copyfile(source_path, dest_path)
    return dest_path

class DatabaseManager:
    def __init__(self, db_name="shooting_range.db"):
        self.db_path = get_app_data_path(db_name)
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self._create_tables()
            self._migrate_db()
        except sqlite3.Error as e:
            logger.error(f"Lỗi kết nối DB: {e}")
            
    def _create_tables(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS soldiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    class_name TEXT,
                    note TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS practice_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    mode TEXT DEFAULT 'SINGLE',
                    is_finished INTEGER DEFAULT 0
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    practice_session_id INTEGER,
                    soldier_id INTEGER NOT NULL,
                    session_date TEXT NOT NULL,
                    is_finished INTEGER DEFAULT 0,
                    FOREIGN KEY (practice_session_id) REFERENCES practice_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (soldier_id) REFERENCES soldiers (id) ON DELETE CASCADE
                );
            """)
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
        except sqlite3.Error as e:
            logger.error(f"Lỗi tạo bảng: {e}")

    def _migrate_db(self):
        try:
            self.cursor.execute("PRAGMA table_info(soldiers)")
            columns = [info[1] for info in self.cursor.fetchall()]
            if "note" not in columns:
                logger.info("Đang cập nhật DB: Thêm cột 'note' vào bảng soldiers...")
                self.cursor.execute("ALTER TABLE soldiers ADD COLUMN note TEXT")
                self.conn.commit()
        except Exception as e:
            logger.error(f"Lỗi migrate DB: {e}")

    # --- Soldiers ---
    def add_soldier(self, name: str, class_name: str) -> int | None:
        try:
            sql = "INSERT INTO soldiers (name, class_name, created_at) VALUES (?, ?, ?)"
            self.cursor.execute(sql, (name, class_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.commit(); return self.cursor.lastrowid
        except: return None

    def get_all_soldiers(self) -> list:
        try:
            self.cursor.execute("SELECT * FROM soldiers ORDER BY class_name ASC, name ASC")
            return [dict(zip([c[0] for c in self.cursor.description], row)) for row in self.cursor.fetchall()]
        except: return []

    def update_soldier(self, soldier_id, name, class_name):
        try:
            self.cursor.execute("UPDATE soldiers SET name=?, class_name=? WHERE id=?", (name, class_name, soldier_id))
            self.conn.commit(); return True
        except: return False
    
    def update_soldier_note(self, soldier_id, note):
        try:
            self.cursor.execute("UPDATE soldiers SET note=? WHERE id=?", (note, soldier_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Lỗi update note: {e}")
            return False
    
    def delete_soldier(self, soldier_id):
        try:
            self.cursor.execute("DELETE FROM soldiers WHERE id=?", (soldier_id,))
            self.conn.commit(); return True
        except: return False

    # --- HISTORY & STATS (NEW) ---
    def get_soldier_history(self, soldier_id: int) -> list:
        """Lấy lịch sử tất cả các phiên tập của một người."""
        try:
            # Lấy thông tin phiên tập + tổng điểm + số phát bắn
            query = """
                SELECT 
                    ps.name as session_name,
                    ps.mode,
                    ps.created_at,
                    COUNT(sh.id) as shot_count,
                    SUM(sh.score) as total_score
                FROM sessions s
                JOIN practice_sessions ps ON s.practice_session_id = ps.id
                LEFT JOIN shots sh ON s.id = sh.session_id
                WHERE s.soldier_id = ? AND ps.is_finished = 1
                GROUP BY s.id
                HAVING shot_count > 0
                ORDER BY ps.created_at ASC
            """
            self.cursor.execute(query, (soldier_id,))
            return [dict(zip([c[0] for c in self.cursor.description], row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Lỗi lấy lịch sử cá nhân: {e}")
            return []

    # --- PRACTICE SESSIONS ---
    def create_practice_session(self, name: str, mode: str) -> int | None:
        try:
            sql = "INSERT INTO practice_sessions (name, created_at, mode, is_finished) VALUES (?, ?, ?, 0)"
            self.cursor.execute(sql, (name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mode))
            self.conn.commit(); return self.cursor.lastrowid
        except: return None

    def get_unfinished_practice_sessions(self) -> list:
        try:
            self.cursor.execute("SELECT * FROM practice_sessions WHERE is_finished = 0 ORDER BY created_at DESC")
            sessions = [dict(zip([c[0] for c in self.cursor.description], row)) for row in self.cursor.fetchall()]
            for s in sessions:
                ps_id = s['id']
                self.cursor.execute("SELECT COUNT(DISTINCT soldier_id) FROM sessions WHERE practice_session_id = ?", (ps_id,))
                s['total_soldiers'] = self.cursor.fetchone()[0]
                sql_trained = "SELECT COUNT(DISTINCT s.soldier_id) FROM sessions s JOIN shots sh ON s.id = sh.session_id WHERE s.practice_session_id = ?"
                self.cursor.execute(sql_trained, (ps_id,))
                s['finished_soldiers'] = self.cursor.fetchone()[0]
            return sessions
        except sqlite3.Error as e:
            logger.error(f"Lỗi lấy danh sách phiên: {e}"); return []

    def get_finished_practice_sessions(self) -> list:
        try:
            self.cursor.execute("SELECT * FROM practice_sessions WHERE is_finished = 1 ORDER BY created_at DESC")
            sessions = [dict(zip([c[0] for c in self.cursor.description], row)) for row in self.cursor.fetchall()]
            for s in sessions:
                ps_id = s['id']
                self.cursor.execute("SELECT COUNT(DISTINCT soldier_id) FROM sessions WHERE practice_session_id = ?", (ps_id,))
                s['total_soldiers'] = self.cursor.fetchone()[0]
                sql_trained = "SELECT COUNT(DISTINCT s.soldier_id) FROM sessions s JOIN shots sh ON s.id = sh.session_id WHERE s.practice_session_id = ?"
                self.cursor.execute(sql_trained, (ps_id,))
                s['finished_soldiers'] = self.cursor.fetchone()[0]
            return sessions
        except sqlite3.Error as e:
            logger.error(f"Lỗi lấy lịch sử phiên: {e}"); return []
            
    def get_session_report_data(self, practice_session_id: int) -> list:
        try:
            query = """
                SELECT sol.id as soldier_id, sol.name, sol.class_name, MAX(s.id) as session_id
                FROM sessions s
                JOIN soldiers sol ON s.soldier_id = sol.id
                WHERE s.practice_session_id = ?
                GROUP BY sol.id
            """
            self.cursor.execute(query, (practice_session_id,))
            participants = [dict(zip([c[0] for c in self.cursor.description], row)) for row in self.cursor.fetchall()]
            for p in participants:
                sid = p['session_id']
                self.cursor.execute("SELECT COUNT(*), SUM(score) FROM shots WHERE session_id = ?", (sid,))
                res = self.cursor.fetchone()
                p['shot_count'] = res[0] if res[0] else 0
                p['total_score'] = res[1] if res[1] else 0
            return participants
        except sqlite3.Error as e:
            logger.error(f"Lỗi lấy chi tiết báo cáo: {e}"); return []

    def get_soldier_session_shots(self, practice_session_id: int, soldier_id: int) -> list:
        try:
            query_session = """
                SELECT id FROM sessions 
                WHERE practice_session_id = ? AND soldier_id = ?
                ORDER BY id DESC LIMIT 1
            """
            self.cursor.execute(query_session, (practice_session_id, soldier_id))
            row = self.cursor.fetchone()
            if not row: return []
            session_id = row[0]

            query_shots = """
                SELECT * FROM shots 
                WHERE session_id = ?
                ORDER BY shot_number ASC
            """
            self.cursor.execute(query_shots, (session_id,))
            shots = [dict(zip([c[0] for c in self.cursor.description], r)) for r in self.cursor.fetchall()]
            return shots
        except Exception as e:
            logger.error(f"Lỗi lấy chi tiết shots: {e}"); return []

    def mark_practice_session_finished(self, ps_id: int):
        try:
            self.cursor.execute("UPDATE practice_sessions SET is_finished = 1 WHERE id = ?", (ps_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Lỗi mark practice session finished: {e}")
            return False

    def delete_practice_session(self, ps_id: int):
        try:
            self.cursor.execute("DELETE FROM practice_sessions WHERE id = ?", (ps_id,))
            self.conn.commit(); return True
        except: return False

    def check_exercise_name_exists(self, name: str) -> bool:
        try:
            self.cursor.execute("SELECT 1 FROM practice_sessions WHERE name = ? LIMIT 1", (name,))
            return self.cursor.fetchone() is not None
        except: return False

    # --- Sessions & Shots ---
    def create_session(self, soldier_id: int, practice_session_id: int = None) -> int | None:
        try:
            sql = "INSERT INTO sessions (soldier_id, practice_session_id, session_date, is_finished) VALUES (?, ?, ?, 0)"
            self.cursor.execute(sql, (soldier_id, practice_session_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.commit(); return self.cursor.lastrowid
        except: return None

    def mark_session_finished(self, session_id: int):
        try:
            self.cursor.execute("UPDATE sessions SET is_finished = 1 WHERE id = ?", (session_id,))
            self.conn.commit()
        except: pass

    def get_session_details_for_resume(self, practice_session_id: int) -> list:
        try:
            query = """
                SELECT MAX(s.id) as db_session_id, sol.id as soldier_id, sol.name, sol.class_name, s.is_finished 
                FROM sessions s
                JOIN soldiers sol ON s.soldier_id = sol.id
                WHERE s.practice_session_id = ?
                GROUP BY sol.id
                ORDER BY sol.name ASC
            """
            self.cursor.execute(query, (practice_session_id,))
            rows = [dict(zip([c[0] for c in self.cursor.description], row)) for row in self.cursor.fetchall()]
            for row in rows:
                self.cursor.execute("SELECT count(*), sum(score) FROM shots WHERE session_id = ?", (row['db_session_id'],))
                res = self.cursor.fetchone()
                row['shot_count'] = res[0] if res[0] else 0
                row['total_score'] = res[1] if res[1] else 0
            return rows
        except sqlite3.Error as e:
            logger.error(f"Lỗi lấy chi tiết resume: {e}"); return []

    def get_shot_count_for_session(self, session_id):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM shots WHERE session_id=?", (session_id,))
            return self.cursor.fetchone()[0]
        except: return 0

    def add_shot(self, session_id, shot_number, target_detected, score, coords, image_path):
        try:
            cx = float(coords[0]) if coords else None; cy = float(coords[1]) if coords else None
            sql = "INSERT INTO shots (session_id, shot_number, target_detected, score, hit_coordinate_x, hit_coordinate_y, image_path, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            self.cursor.execute(sql, (session_id, shot_number, target_detected, score, cx, cy, image_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.commit()
        except: pass

    def delete_session(self, session_id):
        try:
            self.cursor.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            self.conn.commit()
        except: pass

    def close(self):
        if self.conn: self.conn.close()