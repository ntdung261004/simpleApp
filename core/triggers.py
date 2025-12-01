# file: core/triggers.py

import logging
import time
from PySide6.QtCore import QObject, Signal
from pynput import keyboard

logger = logging.getLogger(__name__)

class BluetoothTrigger(QObject):
    # Signal gửi về chuỗi 'UP' hoặc 'DOWN'
    triggered = Signal(str)

    def __init__(self, debounce_ms=300):
        super().__init__()
        # CẤU HÌNH PHÍM: Chỉ giữ lại 2 phím Volume
        self.key_map = {
            keyboard.Key.media_volume_up: 'UP',
            keyboard.Key.media_volume_down: 'DOWN'
        }

        self.listener = None
        self.is_active = False
        
        # Cấu hình chống rung (Debounce)
        self.debounce_ms = debounce_ms
        self.last_trigger_time = 0

    def on_press(self, key):
        # Kiểm tra xem phím bấm có trong danh sách hỗ trợ không
        action = self.key_map.get(key)
        
        if action:
            # Logic chống rung (Debounce) bằng thời gian
            current_time = time.time() * 1000
            if current_time - self.last_trigger_time > self.debounce_ms:
                self.last_trigger_time = current_time
                logger.info(f"Trigger: Phím {key} -> Action {action}")
                self.triggered.emit(action)

    def activate(self):
        """
        Bật chức năng lắng nghe.
        LƯU Ý: Đã tắt chế độ suppress=True để tránh lỗi crash trên macOS.
        """
        if not self.is_active:
            logger.info("Trigger: Đang khởi động Listener...")
            try:
                # --- SỬA ĐỔI QUAN TRỌNG: Đổi suppress=True thành False ---
                self.listener = keyboard.Listener(on_press=self.on_press, suppress=False)
                self.listener.start()
                self.is_active = True
                self.last_trigger_time = 0
                logger.info("Trigger đã được BẬT.")
            except Exception as e:
                logger.error(f"Lỗi không thể khởi động Keyboard Listener: {e}")

    def deactivate(self):
        """Tắt chức năng lắng nghe."""
        if self.is_active and self.listener:
            try:
                self.listener.stop()
                self.listener = None
                self.is_active = False
                logger.info("Trigger đã được TẮT.")
            except Exception as e:
                logger.error(f"Lỗi khi dừng Listener: {e}")
                
    def stop_global_listener(self):
        self.deactivate()