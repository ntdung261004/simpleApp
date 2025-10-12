# file: utils/handles.py
import cv2
from utils.processing import warp_crop_to_original, calculate_score_bia4b, calculate_score_bia4c
import logging

logger = logging.getLogger(__name__)

def handle_miss(hit_info: dict, original_frame):
    """
    Xử lý khi bắn trượt. Chỉ trả về dữ liệu, không vẽ lên ảnh.
    Việc vẽ tâm ngắm (aim point) sẽ do practice_window thực hiện.
    """
    logger.info("Xử lý kết quả: TRƯỢT")
    shot_point = hit_info.get('shot_point_absolute')
    
    return {
        'target': "Trượt",
        'score': 0,
        'image': original_frame, # Trả về ảnh camera gốc
        'coords': shot_point
    }

def _handle_hit_logic(hit_info, original_frame, original_img, mask, calculate_score_func, target_name_str, original_img_alt=None):
    """
    Logic tính điểm chung khi bắn trúng.
    Trả về ảnh bia giấy đã vẽ điểm chạm màu đỏ.
    """
    obj_crop = hit_info.get('crop')
    shot_point_relative = hit_info.get('shot_point_relative')
    
    processed_image = original_img.copy()
    transformed_point = None
    warp_method = "Không xác định"

    if original_img_alt is not None:
        _, transformed_point = warp_crop_to_original(original_img_alt, obj_crop, shot_point_relative)
        if transformed_point:
            warp_method = "Ảnh tham chiếu webcam"
    
    if transformed_point is None:
        _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
        if transformed_point:
            warp_method = "Ảnh bia gốc"

    if transformed_point is None:
        warp_method = "Fallback (Ước tính)"
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        center_orig = (w_orig / 2, h_orig / 2); center_crop = (w_crop / 2, h_crop / 2)
        offset_x = shot_point_relative[0] - center_crop[0]; offset_y = shot_point_relative[1] - center_crop[1]
        scale_x = w_orig / w_crop; scale_y = h_orig / h_crop
        final_x = int(center_orig[0] + (offset_x * scale_x)); final_y = int(center_orig[1] + (offset_y * scale_y))
        transformed_point = (final_x, final_y)

    logger.info(f"Điểm được tính bằng phương pháp: {warp_method}")
    score = calculate_score_func(transformed_point, original_img, mask)
    
    # Vẽ điểm chạm (hit point) màu đỏ lên ảnh bia giấy
    if transformed_point:
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)

    return {
        'target': target_name_str,
        'score': score,
        'image': processed_image, # Trả về ảnh BIA GỐC đã vẽ điểm chạm
        'coords': transformed_point
    }

def handle_hit_bia_4b(hit_info: dict, original_frame, original_img, mask, original_img_alt=None):
    return _handle_hit_logic(hit_info, original_frame, original_img, mask, calculate_score_bia4b, "Bia 4b", original_img_alt)

def handle_hit_bia_4c(hit_info: dict, original_frame, original_img, mask, original_img_alt=None):
    return _handle_hit_logic(hit_info, original_frame, original_img, mask, calculate_score_bia4c, "Bia 4c", original_img_alt)