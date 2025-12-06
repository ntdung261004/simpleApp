# file: gui/managers/camera_manager.py
import cv2
import logging
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication
from utils.camera import CameraThread

logger = logging.getLogger(__name__)

class CameraManager(QObject):
    frame_received = Signal(int, object)
    error_occurred = Signal(int, int)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.cameras = {1: None, 2: None}
        self.cam_indices = {1: 0, 2: 1}
        self.zoom_levels = {1: 1.0, 2: 1.0}
        self.calib_centers = {1: None, 2: None}
        self.is_calib_mode = {1: False, 2: False}
        self.clean_frames = {1: None, 2: None}
        self.shot_points = {1: None, 2: None}
        self.final_size = (480, 640)

        try: self.cam_indices[1] = int(self.config.get("camera_index", 0))
        except: pass

    def start_camera(self, cam_id):
        idx = self.cam_indices.get(cam_id)
        if idx is None: return
        self.stop_camera(cam_id)
        QApplication.processEvents()
        try:
            thread = CameraThread(idx)
            if cam_id == 1: thread.frame_received.connect(self._handle_frame_1)
            else: thread.frame_received.connect(self._handle_frame_2)
            thread.error_occurred.connect(lambda err: self.error_occurred.emit(cam_id, err))
            self.cameras[cam_id] = thread
            thread.start()
            logger.info(f"CameraManager: Đã khởi động Cam {cam_id} (Index {idx})")
        except Exception as e:
            logger.error(f"CameraManager: Lỗi khởi động Cam {cam_id}: {e}")

    def stop_camera(self, cam_id):
        self.clean_frames[cam_id] = None
        if self.cameras[cam_id] is not None:
            self.cameras[cam_id].stop(); self.cameras[cam_id].deleteLater(); self.cameras[cam_id] = None

    def stop_all(self):
        self.stop_camera(1); self.stop_camera(2)

    def set_zoom(self, cam_id, value): self.zoom_levels[cam_id] = value / 10.0

    def set_calibration_center(self, cam_id, pos, view_size):
        frame = self.clean_frames.get(cam_id)
        if frame is None: return
        h_img, w_img = frame.shape[:2]; w_view, h_view = view_size
        scale = min(w_view/w_img, h_view/h_img)
        dw, dh = int(w_img * scale), int(h_img * scale)
        ox, oy = (w_view - dw) // 2, (h_view - dh) // 2
        cx = int((pos.x() - ox) / scale); cy = int((pos.y() - oy) / scale)
        cx = max(0, min(cx, w_img - 1)); cy = max(0, min(cy, h_img - 1))
        self.calib_centers[cam_id] = (cx, cy)

    def get_shot_data(self, cam_id):
        return self.clean_frames.get(cam_id), self.shot_points.get(cam_id)

    @Slot(object)
    def _handle_frame_1(self, frame): self._process_frame(1, frame)
    @Slot(object)
    def _handle_frame_2(self, frame): self._process_frame(2, frame)

    def _process_frame(self, cam_id, frame):
        if frame is None: return
        h, w = frame.shape[:2]; target_aspect = 3.0 / 4.0; new_w = int(h * target_aspect)
        if w > new_w: start_x = (w - new_w) // 2; cropped = frame[:, start_x : start_x + new_w]
        else: cropped = frame
        resized = cv2.resize(cropped, self.final_size, interpolation=cv2.INTER_LINEAR)
        zm = self.zoom_levels[cam_id]
        if zm > 1.0:
            h, w = resized.shape[:2]; cw, ch = int(w/zm), int(h/zm); x, y = (w-cw)//2, (h-ch)//2
            zoomed = cv2.resize(resized[y:y+ch, x:x+cw], (w, h), interpolation=cv2.INTER_LINEAR)
        else: zoomed = resized
        self.clean_frames[cam_id] = zoomed
        h, w = zoomed.shape[:2]
        center = self.calib_centers[cam_id] if self.calib_centers[cam_id] else (w//2, h//2)
        self.shot_points[cam_id] = center
        display_frame = zoomed.copy()
        cv2.drawMarker(display_frame, center, (0, 0, 255), cv2.MARKER_CROSS, 20, 1)
        self.frame_received.emit(cam_id, display_frame)