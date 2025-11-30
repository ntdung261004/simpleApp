# file: core/triggers.py

import logging
from PySide6.QtCore import QObject, Signal
from pynput import keyboard

logger = logging.getLogger(__name__)

class BluetoothTrigger(QObject):
    # Signal gửi về chuỗi 'UP' hoặc 'DOWN' để phân biệt nút bấm
    triggered = Signal(str)

    def __init__(self):
        super().__init__()
        self.key_up = keyboard.Key.media_volume_up
        self.key_down = keyboard.Key.media_volume_down
        self.listener = None
        self.is_active = False
        
        # --- LOGIC GỐC: Dùng cờ trạng thái để chặn lặp phím (Auto-repeat) ---
        # Sử dụng 2 cờ riêng biệt cho 2 nút để tránh xung đột
        self._is_up_pressed = False
        self._is_down_pressed = False

    def on_press(self, key):
        # Chỉ xử lý khi active
        if not self.is_active:
            return

        # NÚT UP (Cò L)
        if key == self.key_up:
            # Chỉ bắn nếu cờ đang False (chưa nhấn)
            if not self._is_up_pressed:
                self._is_up_pressed = True # Khóa lại ngay
                logger.info("Trigger: Nút L (UP) đã bấm")
                self.triggered.emit('UP')
        
        # NÚT DOWN (Cò N)
        elif key == self.key_down:
            # Chỉ bắn nếu cờ đang False (chưa nhấn)
            if not self._is_down_pressed:
                self._is_down_pressed = True # Khóa lại ngay
                logger.info("Trigger: Nút N (DOWN) đã bấm")
                self.triggered.emit('DOWN')

    def on_release(self, key):
        # Khi nhả phím, trả cờ về False để cho phép lần bắn sau
        if key == self.key_up:
            self._is_up_pressed = False
        elif key == self.key_down:
            self._is_down_pressed = False

    def activate(self):
        """Bật chức năng lắng nghe."""
        logger.info("Trigger đã được BẬT.")
        self.is_active = True
        # Reset trạng thái để tránh kẹt phím khi bật lại
        self._is_up_pressed = False
        self._is_down_pressed = False

    def deactivate(self):
        """Tắt chức năng lắng nghe."""
        logger.info("Trigger đã được TẮT.")
        self.is_active = False
        self._is_up_pressed = False
        self._is_down_pressed = False

    def start_global_listener(self):
        """Khởi động luồng lắng nghe một lần duy nhất."""
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.listener.start()
            logger.info(f"Luồng lắng nghe phím bấm toàn cục đã bắt đầu.")

    def stop_global_listener(self):
        """Dừng luồng lắng nghe khi thoát ứng dụng."""
        if self.listener is not None:
            self.listener.stop()
            self.listener.join()
            self.listener = None
            logger.info("Luồng lắng nghe phím bấm toàn cục đã dừng.")