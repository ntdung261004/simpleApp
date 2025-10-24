# file: utils/handles.py
import cv2
import numpy as np
import logging
from typing import Dict, Any, Optional, Tuple

from utils.processing import warp_via_bounding_rect, calculate_score_bia4b, calculate_score_bia4c

logger = logging.getLogger(__name__)

def handle_miss(hit_info: dict, original_frame: np.ndarray) -> Dict[str, Any]:
    """
    Xử lý khi bắn trượt. Trả về một cấu trúc dữ liệu nhất quán.
    """
    logger.info("Xử lý kết quả: TRƯỢT")
    # Khi trượt, không bao giờ trả về tọa độ để tránh vẽ nhầm.
    return {
        'target': "Trượt",
        'score': 0,
        'image': original_frame,
        'coords': None, # Luôn là None khi trượt
        'target_detected_raw': 'Trượt'
    }

def _handle_hit_logic(
    hit_info: Dict[str, Any],
    original_frame: np.ndarray,
    original_img: np.ndarray,
    mask: np.ndarray,
    calculate_score_func,
    target_name_str: str,
    original_img_alt: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Logic tính điểm chung khi bắn trúng, sử dụng thuật toán warp đã được tối ưu.
    """
    obj_crop = hit_info.get('crop')
    shot_point_relative = hit_info.get('shot_point_relative')

    if obj_crop is None or shot_point_relative is None or obj_crop.size == 0:
        logger.warning("Thông tin bắn trúng không đầy đủ (thiếu ảnh crop hoặc tọa độ tương đối). Xử lý như bắn trượt.")
        return handle_miss(hit_info, original_frame)

    # *** SỬA LỖI QUAN TRỌNG NHẤT ***
    # Sử dụng np.array(copy=True) để tạo một bản sao có thể ghi (writeable).
    # Lệnh .copy() thông thường có thể không hoạt động sau khi đóng gói bằng PyInstaller.
    processed_image = np.array(original_img, copy=True)

    # Cố gắng warp bằng phương pháp chính (ổn định hơn)
    _, transformed_point = warp_via_bounding_rect(original_img, obj_crop, shot_point_relative)

    # Nếu phương pháp chính thất bại, sử dụng phương pháp dự phòng (kém chính xác hơn)
    if transformed_point is None:
        logger.warning("Warp bằng Bounding Rectangle thất bại. Chuyển sang phương pháp dự phòng (scale).")
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]

        if h_crop == 0 or w_crop == 0:
             return handle_miss(hit_info, original_frame)

        center_crop = (w_crop / 2, h_crop / 2)
        offset_x = shot_point_relative[0] - center_crop[0]
        offset_y = shot_point_relative[1] - center_crop[1]

        scale_x = w_orig / w_crop
        scale_y = h_orig / h_crop
        center_orig = (w_orig / 2, h_orig / 2)

        final_x = center_orig[0] + (offset_x * scale_x)
        final_y = center_orig[1] + (offset_y * scale_y)
        transformed_point = (final_x, final_y)

    # Tính điểm dựa trên tọa độ đã được biến đổi
    score = calculate_score_func(transformed_point, original_img, mask)
    logger.info(f"Điểm số được tính: {score} tại tọa độ trên bia gốc: {transformed_point}")

    final_coords = None
    # Chỉ lưu tọa độ và vẽ vết đạn nếu bắn trúng và có điểm
    if score > 0 and transformed_point is not None:
        # Chuyển đổi tường minh tuple (có thể chứa kiểu numpy) thành list [float, float]
        # Đây là bước quan trọng để đảm bảo dữ liệu tương thích với JSON.
        final_coords = [float(p) for p in transformed_point]
        
        # Vẽ vết đạn lên ảnh để hiển thị kết quả tức thì cho người dùng
        # Chuyển đổi về int để vẽ
        draw_point = (int(final_coords[0]), int(final_coords[1]))
        cv2.drawMarker(processed_image, draw_point, (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
        logger.info(f"Đã vẽ vết đạn tại {draw_point}. Tọa độ số thực lưu trữ: {final_coords}")


    return {
        'target': target_name_str if score > 0 else "Trượt",
        'score': score,
        'image': processed_image,
        'coords': final_coords,  # Trả về tọa độ đã được "làm sạch" hoặc None
        'target_detected_raw': hit_info.get('name', 'N/A')
    }

def handle_hit_bia_4b(
    hit_info: Dict[str, Any],
    original_frame: np.ndarray,
    original_img: np.ndarray,
    mask: np.ndarray,
    original_img_alt: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """Hàm xử lý riêng cho Bia 4b."""
    return _handle_hit_logic(
        hit_info, original_frame, original_img, mask, calculate_score_bia4b, "Bia 4b", original_img_alt
    )

def handle_hit_bia_4c(
    hit_info: Dict[str, Any],
    original_frame: np.ndarray,
    original_img: np.ndarray,
    mask: np.ndarray,
    original_img_alt: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """Hàm xử lý riêng cho Bia 4c."""
    return _handle_hit_logic(
        hit_info, original_frame, original_img, mask, calculate_score_bia4c, "Bia 4c", original_img_alt
    )