import cv2

class Camera:
    def __init__(self, index=0):
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Không mở được webcam index {index}")
        self.current_frame = None

    def grab(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        # Vẽ crosshair ở tâm
        h, w, _ = frame.shape
        cx, cy = w // 2, h // 2
        length = 20
        thickness = 2
        color = (0, 0, 255)
        cv2.line(frame, (cx - length, cy), (cx + length, cy), color, thickness)
        cv2.line(frame, (cx, cy - length), (cx, cy + length), color, thickness)
        self.current_frame = frame
        return frame

    def release(self):
        if self.cap:
            self.cap.release()
