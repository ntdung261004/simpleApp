# utils/handles.py
import cv2
from utils.processing import warp_crop_to_original, calculate_score_bia4, calculate_score_bia7, calculate_score_bia8

def _process_generic_hit(hit_info, original_img, original_img_alt, mask, score_func, target_display_name):
    """
    Hàm xử lý chung cho mọi loại bia để tránh lặp lại code.
    """
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    processed_image = original_img.copy()
    score = 0
    transformed_point = None

    # Bước 1: Thử Warp với ảnh gốc chính
    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    
    if transformed_point:
        score = score_func(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), 
                       (0, 0, 255), cv2.MARKER_CROSS, 15, 1) # markerSize=20, thickness=1
    
    # Bước 2: Nếu thất bại, thử Warp với ảnh thay thế (original_img_alt)
    elif original_img_alt is not None:
        _, transformed_point_alt = warp_crop_to_original(original_img_alt, obj_crop, shot_point_relative)
        if transformed_point_alt:
            transformed_point = transformed_point_alt
            # Lưu ý: Khi dùng alt image để match, vẫn vẽ lên processed_image (bản gốc) 
            # để đảm bảo hiển thị nhất quán, nhưng tính điểm dựa trên tọa độ đã tìm được.
            score = score_func(transformed_point_alt, original_img_alt, mask)
            cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), 
                       (0, 0, 255), cv2.MARKER_CROSS, 15, 1) # markerSize=15, thickness=1

    # Bước 3: Fallback (Ước lượng tỷ lệ) nếu cả 2 cách trên đều thất bại
    if transformed_point is None:
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        
        # Ước tính tọa độ bằng cách phóng to theo tỷ lệ
        if w_crop > 0 and h_crop > 0:
            scaled_x = int(shot_point_relative[0] * w_orig / w_crop)
            scaled_y = int(shot_point_relative[1] * h_orig / h_crop)
            transformed_point = (scaled_x, scaled_y)
            
            score = score_func(transformed_point, original_img, mask)
            cv2.drawMarker(processed_image, transformed_point, (0, 0, 255), cv2.MARKER_CROSS, 15, 1) # Màu vàng

    final_target_name = target_display_name
    if score == 0:
        final_target_name = "Trượt"

    return {
        'target': final_target_name,
        'score': score,
        'image': processed_image,
        'coords': transformed_point
    }

# --- CÁC HÀM GỌI (WRAPPER) ---

def handle_hit_bia_so_4(hit_info, original_frame, original_img, original_img_alt, mask):
    return _process_generic_hit(
        hit_info, original_img, original_img_alt, mask,
        score_func=calculate_score_bia4,
        target_display_name="Bia số 4"
    )

def handle_hit_bia_so_7(hit_info, original_frame, original_img, original_img_alt, mask):
    return _process_generic_hit(
        hit_info, original_img, original_img_alt, mask,
        score_func=calculate_score_bia7,
        target_display_name="Bia số 7"
    )

def handle_hit_bia_so_8(hit_info, original_frame, original_img, original_img_alt, mask):
    return _process_generic_hit(
        hit_info, original_img, original_img_alt, mask,
        score_func=calculate_score_bia8,
        target_display_name="Bia số 8"
    )

def handle_miss(hit_info, original_frame):
    processed_image = original_frame.copy()
    shot_point = hit_info['shot_point']
    cv2.drawMarker(processed_image, shot_point, (0, 0, 255), cv2.MARKER_CROSS, 15, 1)
    return {'target': 'Trượt', 'score': 0, 'image': processed_image, 'coords': None}