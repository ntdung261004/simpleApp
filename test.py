# check_key.py
from pynput import keyboard
import time

print("Đang lắng nghe... Vui lòng nhấn nút trên remote của bạn.")
print("Nhấn phím 'Esc' trên bàn phím để thoát.")

def on_press(key):
    """Hàm này sẽ được gọi mỗi khi có phím được nhấn."""
    try:
        # In ra ký tự thông thường (ví dụ: 'a', 'b', 'c')
        print(f"Phím đã nhấn: '{key.char}'")
    except AttributeError:
        # In ra các phím đặc biệt (ví dụ: Key.up, Key.media_volume_up)
        print(f"Phím đã nhấn: {key}")

    # Nếu nhấn phím Escape trên bàn phím thì dừng chương trình
    if key == keyboard.Key.esc:
        return False

# Bắt đầu lắng nghe
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()

print("Đã dừng lắng nghe.")