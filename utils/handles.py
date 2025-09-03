# utils/handles.py
import cv2
from utils.processing import warp_crop_to_original, calculate_score_bia4, calculate_score_bia7, calculate_score_bia8

# --- CÁC HÀM XỬ LÝ ĐÃ ĐƯỢC NÂNG CẤP ---

def handle_hit_bia_so_4(hit_info, original_frame, original_img, original_img_alt, mask):
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    processed_image = original_img.copy()
    score = 0
    transformed_point = None

    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    if transformed_point:
        score = calculate_score_bia4(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
    elif original_img_alt is not None:
        _, transformed_point_alt = warp_crop_to_original(original_img_alt, obj_crop, shot_point_relative)
        if transformed_point_alt:
            transformed_point = transformed_point_alt # Lưu lại tọa độ
            score = calculate_score_bia4(transformed_point_alt, original_img_alt, mask)
            cv2.drawMarker(processed_image, (int(transformed_point_alt[0]), int(transformed_point_alt[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3)

    # ======================================================================
    # CHÚ THÍCH: LOGIC FALLBACK KHI WARP THẤT BẠI
    # ======================================================================
    if transformed_point is None:
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        
        # Ước tính tọa độ bằng cách phóng to theo tỷ lệ
        scaled_x = int(shot_point_relative[0] * w_orig / w_crop)
        scaled_y = int(shot_point_relative[1] * h_orig / h_crop)
        transformed_point = (scaled_x, scaled_y) # Lưu lại tọa độ ước tính
        
        score = calculate_score_bia4(transformed_point, original_img, mask)
        # Vẽ điểm ước tính bằng màu vàng để phân biệt
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    return {'target': 'Bia số 4', 'score': score, 'image': processed_image, 'coords': transformed_point}

def handle_hit_bia_so_7(hit_info, original_frame, original_img, original_img_alt, mask):
    # (Logic tương tự được áp dụng cho bia 7)
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    processed_image = original_img.copy()
    score = 0
    transformed_point = None
    
    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    if transformed_point:
        score = calculate_score_bia7(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
    elif original_img_alt is not None:
        _, transformed_point_alt = warp_crop_to_original(original_img_alt, obj_crop, shot_point_relative)
        if transformed_point_alt:
            transformed_point = transformed_point_alt
            score = calculate_score_bia7(transformed_point_alt, original_img_alt, mask)
            cv2.drawMarker(processed_image, (int(transformed_point_alt[0]), int(transformed_point_alt[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3)

    if transformed_point is None:
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        scaled_x = int(shot_point_relative[0] * w_orig / w_crop)
        scaled_y = int(shot_point_relative[1] * h_orig / h_crop)
        transformed_point = (scaled_x, scaled_y)
        score = calculate_score_bia7(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)
            
    return {'target': 'Bia số 7', 'score': score, 'image': processed_image, 'coords': transformed_point}
    
def handle_hit_bia_so_8(hit_info, original_frame, original_img, original_img_alt, mask):
    # (Logic tương tự được áp dụng cho bia 8)
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    processed_image = original_img.copy()
    score = 0
    transformed_point = None
    
    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    if transformed_point:
        score = calculate_score_bia8(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
    elif original_img_alt is not None:
        _, transformed_point_alt = warp_crop_to_original(original_img_alt, obj_crop, shot_point_relative)
        if transformed_point_alt:
            transformed_point = transformed_point_alt
            score = calculate_score_bia8(transformed_point_alt, original_img_alt, mask)
            cv2.drawMarker(processed_image, (int(transformed_point_alt[0]), int(transformed_point_alt[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3)

    if transformed_point is None:
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        scaled_x = int(shot_point_relative[0] * w_orig / w_crop)
        scaled_y = int(shot_point_relative[1] * h_orig / h_crop)
        transformed_point = (scaled_x, scaled_y)
        score = calculate_score_bia8(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    return {'target': 'Bia số 8', 'score': score, 'image': processed_image, 'coords': transformed_point}
    
def handle_miss(hit_info, original_frame):
    processed_image = original_frame.copy()
    shot_point = hit_info['shot_point']
    cv2.drawMarker(processed_image, shot_point, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
    return {'target': 'Trượt', 'score': 0, 'image': processed_image, 'coords': None}