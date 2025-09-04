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
import cv2

def test_all_cameras():
    """
    Hàm này sẽ tìm, kiểm tra và hiển thị hình ảnh từ tất cả camera tìm thấy.
    """
    index = 0
    print("Đang tìm kiếm camera...")
    
    while index < 10: # Thử kiểm tra 10 index đầu tiên
        cap = cv2.VideoCapture(index)
        
        if not cap.isOpened():
            print(f"Không tìm thấy camera ở index {index}.")
        else:
            print(f"Tìm thấy camera ở index {index}! Đang thử lấy khung hình...")
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"  -> THÀNH CÔNG! Hiển thị hình ảnh từ camera index {index}. Nhấn phím bất kỳ để tiếp tục.")
                cv2.imshow(f"Test Camera Index {index}", frame)
                cv2.waitKey(0) # Đợi người dùng nhấn phím
                cv2.destroyAllWindows()
            else:
                print(f"  -> THẤT BẠI: Không thể đọc khung hình từ camera index {index}, có thể nó đang bận.")
        
        cap.release()
        index += 1

    print("\nĐã kiểm tra xong.")

if __name__ == "__main__":
    test_all_cameras()
    # Nếu nhấn phím Escape trên bàn phím thì dừng chương trình
    if key == keyboard.Key.esc:
        return False

# Bắt đầu lắng nghe
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()

print("Đã dừng lắng nghe.")