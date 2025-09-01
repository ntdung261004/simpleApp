# utils/audio.py
import logging
import os
import pygame

logger = logging.getLogger(__name__)

# Tự động xác định thư mục gốc của dự án
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class AudioManager:
    """
    Lớp quản lý âm thanh sử dụng pygame.mixer.
    """
    def __init__(self):
        try:
            pygame.mixer.init()
            self.sounds = {}
            logger.info("Pygame mixer đã được khởi tạo thành công.")
            self._load_sounds()
        except pygame.error as e:
            logger.error(f"Lỗi khi khởi tạo pygame.mixer: {e}. Âm thanh sẽ không hoạt động.")
            self.sounds = None

    def _load_sounds(self):
        """Tải các file âm thanh cần thiết: shot, miss, và scores 1-10."""
        if self.sounds is None: return
        logger.info("Đang tải các file âm thanh...")
        
        sounds_dir = os.path.join(os.path.dirname(BASE_DIR), 'sounds')

        # Danh sách các âm thanh cần tải
        sound_names = ['shot', 'miss']
        for i in range(1, 11): # Điểm từ 1 đến 10
            sound_names.append(f"score_{i}")

        for name in sound_names:
            # Chuyển đổi tên logic (ví dụ: 'score_10') thành tên file (ví dụ: '10.mp3')
            file_name = name.replace('score_', '') + '.mp3'
            sound_path = os.path.join(sounds_dir, file_name)
            
            if os.path.exists(sound_path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(sound_path)
                except pygame.error as e:
                    logger.error(f"Lỗi khi tải file âm thanh '{name}': {e}")
            else:
                logger.warning(f"Không tìm thấy file âm thanh: {sound_path}")

    def play_sound(self, name: str):
        """Phát một âm thanh đã được tải dựa theo tên."""
        if self.sounds and name in self.sounds:
            self.sounds[name].play()
        elif self.sounds is None:
            logger.warning("Không thể phát âm thanh vì pygame.mixer chưa được khởi tạo.")
        else:
            logger.warning(f"Không tìm thấy âm thanh có tên: '{name}'")
            
    def play_score(self, score: int):
        """Hàm tiện ích để phát âm thanh cho một điểm số cụ thể."""
        if isinstance(score, int) and 1 <= score <= 10:
            self.play_sound(f"score_{score}")
        else:
            logger.warning(f"Điểm số không hợp lệ để phát âm thanh: {score}")