# file: utils/scaler.py
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

# Độ phân giải chiều cao cơ sở mà bạn dùng để thiết kế giao diện (ví dụ: Full HD)
BASE_HEIGHT = 1080.0

class Scaler:
    def __init__(self):
        """Khởi tạo và tính toán hệ số scale một lần duy nhất."""
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            self._scale_factor = screen.height() / BASE_HEIGHT
            print(f"UI Scaler: Màn hình cao {screen.height()}px, hệ số scale là {self._scale_factor:.2f}")
        except Exception:
            # Fallback nếu QApplication chưa được khởi tạo
            self._scale_factor = 1.0

    def scale(self, base_value: int) -> int:
        """
        Tính toán kích thước pixel mới cho một giá trị (margin, padding, size...)
        dựa trên hệ số scale.
        """
        return max(1, int(base_value * self._scale_factor))

    def font(self, base_size: int, weight: QFont.Weight = QFont.Weight.Normal, bold: bool = False) -> QFont:
        """
        Tạo một đối tượng QFont đã được scale kích thước.
        """
        font = QFont("Segoe UI")
        scaled_size = max(9, int(base_size * self._scale_factor))
        font.setPointSize(scaled_size)
        font.setWeight(weight)
        font.setBold(bold)
        return font

# Tạo một đối tượng scaler duy nhất để toàn bộ ứng dụng sử dụng.
# Điều này đảm bảo hệ số scale chỉ được tính một lần khi ứng dụng khởi động.
scaler = Scaler()