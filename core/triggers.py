# core/triggers.py
import logging
from PySide6.QtCore import QObject, Signal
from pynput import keyboard

logger = logging.getLogger(__name__)

class BluetoothTrigger(QObject):
    triggered = Signal()

    def __init__(self):
        super().__init__()
        self.trigger_key = keyboard.Key.media_volume_up
        self.listener = None
        self._is_key_pressed = False

    def on_press(self, key):
        if key == self.trigger_key and not self._is_key_pressed:
            self._is_key_pressed = True
            logger.info(f"Phát hiện tín hiệu trigger từ phím: {key}")
            self.triggered.emit()

    def on_release(self, key):
        if key == self.trigger_key:
            self._is_key_pressed = False

    def start_listening(self):
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.listener.start()
            logger.info(f"Bắt đầu lắng nghe tín hiệu trigger từ phím: {self.trigger_key}...")

    def stop_listening(self):
        if self.listener is not None:
            self.listener.stop()
            logger.info("Đã dừng lắng nghe tín hiệu trigger.")