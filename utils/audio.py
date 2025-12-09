# utils/audio.py
import logging
import os
import pygame
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class AudioManager:
    """
    Lớp quản lý âm thanh sử dụng pygame.mixer.
    """
    def __init__(self):
        try:
            pygame.mixer.init()
            # Tăng số lượng kênh phát đồng thời để tránh bị cắt tiếng khi bắn nhanh
            pygame.mixer.set_num_channels(16) 
            self.sounds = {}
            logger.info("Pygame mixer đã được khởi tạo thành công.")
            self._load_sounds()
        except pygame.error as e:
            logger.error(f"Lỗi khi khởi tạo pygame.mixer: {e}. Âm thanh sẽ không hoạt động.")
            self.sounds = None

    def _load_sounds(self):
        """Tải các file âm thanh cần thiết."""
        if self.sounds is None: return
        logger.info("Đang tải các file âm thanh...")
        
        sounds_dir = resource_path(os.path.join("assets", "sounds"))

        # Danh sách các âm thanh cần tải
        # [MỚI] Thêm cam1, cam2 vào danh sách
        sound_names = ['shot', 'miss', 'cam1', 'cam2']
        
        for i in range(1, 11): # Điểm từ 1 đến 10
            sound_names.append(f"score_{i}")

        for name in sound_names:
            # Chuyển tên logic (score_10) thành tên file (10.mp3)
            if name.startswith("score_"):
                file_name = name.replace('score_', '') + '.mp3'
            else:
                file_name = name + '.mp3'
                
            sound_path = os.path.join(sounds_dir, file_name)
            
            if os.path.exists(sound_path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(sound_path)
                except pygame.error as e:
                    logger.error(f"Lỗi khi tải file âm thanh '{name}': {e}")
            else:
                # Chỉ cảnh báo, không lỗi, phòng trường hợp chưa có file cam1/cam2
                logger.warning(f"Không tìm thấy file âm thanh: {sound_path}")

    def play_sound(self, name: str):
        """Phát một âm thanh đơn lẻ."""
        if self.sounds and name in self.sounds:
            self.sounds[name].play()
        elif self.sounds is None:
            logger.warning("Không thể phát âm thanh vì pygame.mixer chưa được khởi tạo.")
        # Bỏ qua cảnh báo nếu không tìm thấy, để tránh spam log

    def play_score(self, score: int):
        """Phát âm thanh điểm số."""
        if isinstance(score, int) and 1 <= score <= 10:
            self.play_sound(f"score_{score}")
        else:
            logger.warning(f"Điểm số không hợp lệ để phát âm thanh: {score}")

    def play_sequence(self, name_list: list):
        """
        [MỚI] Phát một chuỗi âm thanh nối tiếp nhau trên cùng một channel.
        Ví dụ: ['cam1', 'score_10'] -> Đọc "Khẩu 1" xong mới đọc "10".
        """
        if not self.sounds or not name_list: return
        
        # Lấy âm thanh đầu tiên để bắt đầu phát
        first_name = name_list[0]
        if first_name not in self.sounds:
            # Nếu file đầu lỗi (ví dụ chưa có cam1.mp3), thử phát tiếp các âm sau
            if len(name_list) > 1:
                self.play_sequence(name_list[1:])
            return
        
        try:
            # Phát âm đầu tiên và lấy Channel object trả về
            channel = self.sounds[first_name].play()
            
            # Nếu lấy được channel (không bị bận), xếp hàng (queue) các âm tiếp theo
            if channel:
                for name in name_list[1:]:
                    if name in self.sounds:
                        channel.queue(self.sounds[name])
        except Exception as e:
            logger.error(f"Lỗi phát chuỗi âm thanh: {e}")