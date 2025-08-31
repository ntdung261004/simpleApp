# core/audio_manager.py
import logging
import os
import pygame # Sử dụng pygame

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AudioManager:
    """
    Lớp quản lý âm thanh sử dụng pygame.mixer.
    """
    def __init__(self):
        # Khởi tạo bộ trộn âm thanh của pygame
        try:
            pygame.mixer.init()
            self.sounds = {}
            logger.info("Pygame mixer đã được khởi tạo thành công.")

            self.sound_files = {
                'shot': 'sounds/shot.mp3', # Bạn có thể dùng mp3 hoặc wav
            }
            self._load_sounds()
        except pygame.error as e:
            logger.error(f"Lỗi khi khởi tạo pygame.mixer: {e}. Âm thanh sẽ không hoạt động.")
            self.sounds = None

    def _load_sounds(self):
        if self.sounds is None: return

        logger.info("Đang tải các file âm thanh...")
        for name, relative_path in self.sound_files.items():
            absolute_path = os.path.join(BASE_DIR, relative_path)
            
            if not os.path.exists(absolute_path):
                logger.error(f"Không tìm thấy file âm thanh: {absolute_path}")
                continue

            try:
                # Tải âm thanh bằng pygame
                sound = pygame.mixer.Sound(absolute_path)
                self.sounds[name] = sound
                logger.info(f"Đã tải thành công âm thanh: '{name}'")
            except pygame.error as e:
                logger.error(f"Lỗi khi tải file âm thanh '{name}' từ '{absolute_path}': {e}")

    def play_sound(self, name: str):
        if self.sounds and name in self.sounds:
            self.sounds[name].play()
        elif self.sounds is None:
            logger.warning("Không thể phát âm thanh vì pygame.mixer chưa được khởi tạo.")
        else:
            logger.warning(f"Không tìm thấy âm thanh có tên: '{name}'")