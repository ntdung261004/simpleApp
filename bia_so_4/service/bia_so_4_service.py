# bia_so_4_service.py
import cv2
import numpy as np
from typing import Optional, Tuple
from bia_so_4.model.bia_so_4_model import warp_image
import logging

logger = logging.getLogger(__name__)

DEFAULT_ORIGINAL_PATH = "images/original/original_bia_so_4.jpg"
DEFAULT_MASK_PATH = "images/mask/mask_bia_so_4.jpg"

class BiaSo4Service:
    def __init__(
        self,
        original_path: str = DEFAULT_ORIGINAL_PATH,
        mask_path: str = DEFAULT_MASK_PATH,
    ):
        self.original_path = original_path
        self.mask_path = mask_path

        self.original = cv2.imread(self.original_path)
        if self.original is None:
            logger.error(f"[BiaSo4Service] Không đọc được ảnh gốc tại '{self.original_path}'")
        self.mask = cv2.imread(self.mask_path, 0)
        if self.mask is None:
            logger.error(f"[BiaSo4Service] Không đọc được mask tại '{self.mask_path}'")

        if self.original is not None and self.mask is not None:
            self.mask = cv2.resize(self.mask, (self.original.shape[1], self.original.shape[0]))

    def check_hit_logic(self, frame_center: Tuple[float, float], box_coordinates) -> bool:
        cx, cy = frame_center
        x1, y1, x2, y2 = box_coordinates
        return x1 <= cx <= x2 and y1 <= cy <= y2

    def extract_and_warp_to_standard(
        self, frame, box, output_size: Tuple[int, int] = (500, 500)
    ) -> Tuple[Optional[np.ndarray], Optional[Tuple[float, float]]]:
        h, w = frame.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        P = np.array([[[cx, cy]]], dtype=np.float32)

        x1, y1, x2, y2 = box
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(w - 1, int(x2)), min(h - 1, int(y2))
        if x2 <= x1 or y2 <= y1:
            return None, None

        src_pts = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
        ow, oh = output_size
        dst_pts = np.array(
            [[0, 0], [ow - 1, 0], [ow - 1, oh - 1], [0, oh - 1]], dtype=np.float32
        )

        H1 = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(frame, H1, (ow, oh), flags=cv2.INTER_LINEAR)
        transformed = cv2.perspectiveTransform(np.array([[[cx, cy]]], dtype=np.float32), H1)[0][0]
        transformed_center = (float(transformed[0]), float(transformed[1]))

        return warped, transformed_center

    def warp_back_to_original(
        self, original_path_or_image, shot_point: Optional[Tuple[float, float]] = None
    ) -> Tuple[Optional[np.ndarray], Optional[Tuple[float, float]]]:
        """
        Warp ảnh đã chụp về ảnh bia gốc để tính điểm.
        original_path_or_image: có thể là đường dẫn hoặc ndarray đã load
        """
        if isinstance(original_path_or_image, str):
            original = cv2.imread(original_path_or_image)
        else:
            original = original_path_or_image

        if original is None:
            logger.error(f"[BiaSo4Service] Không đọc được ảnh gốc tại '{original_path_or_image}'")
            return None, None

        result_image = None
        # Sử dụng result image tạm (đã align)
        warp_result = warp_image(original, result_image if result_image is not None else original)
        if not warp_result.get("success", False):
            logger.error("Warp thất bại: %s", warp_result.get("message"))
            return None, None

        aligned_image = warp_result["aligned"]
        transformed_point = None
        if shot_point is not None:
            H2 = warp_result["homography"]
            px, py = float(shot_point[0]), float(shot_point[1])
            src = np.array([[[px, py]]], dtype=np.float32)
            warped_pt = cv2.perspectiveTransform(src, H2)[0][0]
            transformed_point = (float(warped_pt[0]), float(warped_pt[1]))

        return aligned_image, transformed_point

    def calculate_score(self, pt: Tuple[float, float]) -> int:
        if self.original is None or self.mask is None:
            return 0
        x, y = int(pt[0]), int(pt[1])
        h, w = self.original.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return 0

        if self.mask[y, x] == 255:
            # tâm là giữa ảnh
            center_x, center_y = w // 2, h // 2
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            if distance < 56:
                return 10
            elif distance < 116:
                return 9
            elif distance < 173:
                return 8
            elif distance < 230:
                return 7
            elif distance < 285:
                return 6
            elif distance < 320:
                return 5
        return 0
