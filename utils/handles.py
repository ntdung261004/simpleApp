# file: utils/handles.py
import cv2
from utils.processing import warp_via_bounding_rect, calculate_score_bia4b, calculate_score_bia4c
import logging

logger = logging.getLogger(__name__)

def handle_miss(hit_info: dict, original_frame):
    """
    Xử lý khi bắn trượt. Trả về ảnh camera gốc.
    Việc vẽ tâm ngắm sẽ do các lớp window thực hiện.
    """
    logger.info("Xử lý kết quả: TRƯỢT")
    shot_point = hit_info.get('shot_point_absolute')
    
    return {
        'target': "Trượt",
        'score': 0,
        'image': original_frame,
        'coords': shot_point
    }

def _handle_hit_logic(hit_info, original_frame, original_img, mask, calculate_score_func, target_name_str, original_img_alt=None):
    """
    Logic tính điểm chung khi bắn trúng, sử dụng thuật toán warp tối ưu.
    """
    obj_crop = hit_info.get('crop')
    shot_point_relative = hit_info.get('shot_point_relative')
    
    if obj_crop is None or shot_point_relative is None:
        return handle_miss(hit_info, original_frame)
    
    processed_image = original_img.copy()
    
    # === THAY ĐỔI: Sử dụng thuật toán warp cuối cùng, chính xác và ổn định nhất ===
    _, transformed_point = warp_via_bounding_rect(original_img, obj_crop, shot_point_relative)

    # Nếu thuật toán mới thất bại, sử dụng phương pháp dự phòng (fallback)
    if transformed_point is None:
        logger.warning("Warp bằng Bounding Rectangle thất bại. Chuyển sang phương pháp dự phòng (ước tính tỷ lệ).")
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
        
        final_x = int(center_orig[0] + (offset_x * scale_x))
        final_y = int(center_orig[1] + (offset_y * scale_y))
        
        transformed_point = (final_x, final_y)

    score = calculate_score_func(transformed_point, original_img, mask)
    
    if transformed_point:
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)

    return {
        'target': target_name_str,
        'score': score,
        'image': processed_image,
        'coords': transformed_point
    }

def handle_hit_bia_4b(hit_info: dict, original_frame, original_img, mask, original_img_alt=None):
    return _handle_hit_logic(hit_info, original_frame, original_img, mask, calculate_score_bia4b, "Bia 4b", original_img_alt)

def handle_hit_bia_4c(hit_info: dict, original_frame, original_img, mask, original_img_alt=None):
    return _handle_hit_logic(hit_info, original_frame, original_img, mask, calculate_score_bia4c, "Bia 4c", original_img_alt)