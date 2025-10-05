# utils/handles.py
import cv2
from utils.processing import warp_crop_to_original, calculate_score_bia4b, calculate_score_bia4c

def handle_hit_bia_4b(hit_info, original_frame, original_img, mask):
    """
    Hàm này nhận 'original_frame' để sửa lỗi TypeError,
    nhưng logic bên trong vẫn vẽ lên 'original_img' theo yêu cầu.
    """
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    # Giữ nguyên logic: vẽ lên ảnh bia gốc
    processed_image = original_img.copy()
    score = 0
    transformed_point = None

    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    if transformed_point:
        score = calculate_score_bia4b(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
    else:
        # Logic fallback khi warp thất bại (giữ nguyên)
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        scaled_x = int(shot_point_relative[0] * w_orig / w_crop)
        scaled_y = int(shot_point_relative[1] * h_orig / h_crop)
        transformed_point = (scaled_x, scaled_y)
        score = calculate_score_bia4b(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    target_name = "Bia số 4b"
    if score == 0:
        target_name = "Trượt"
        
    return {'target': target_name,
            'score': score,
            'image': processed_image, # Trả về ảnh bia gốc đã vẽ
            'coords': transformed_point}


def handle_hit_bia_4c(hit_info, original_frame, original_img, mask):
    """
    Hàm này nhận 'original_frame' để sửa lỗi TypeError,
    nhưng logic bên trong vẫn vẽ lên 'original_img' theo yêu cầu.
    """
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    # Giữ nguyên logic: vẽ lên ảnh bia gốc
    processed_image = original_img.copy()
    score = 0
    transformed_point = None

    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    if transformed_point:
        score = calculate_score_bia4c(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
    else:
        # Logic fallback khi warp thất bại (giữ nguyên)
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        scaled_x = int(shot_point_relative[0] * w_orig / w_crop)
        scaled_y = int(shot_point_relative[1] * h_orig / h_crop)
        transformed_point = (scaled_x, scaled_y)
        score = calculate_score_bia4c(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    target_name = "Bia số 4c"
    if score == 0:
        target_name = "Trượt"
        
    return {'target': target_name,
            'score': score,
            'image': processed_image, # Trả về ảnh bia gốc đã vẽ
            'coords': transformed_point}


def handle_miss(hit_info, original_frame):
    processed_image = original_frame.copy()
    shot_point = hit_info.get('shot_point')
    
    # Thêm kiểm tra để tránh lỗi khi shot_point là None
    if shot_point:
        # Đảm bảo tọa độ là số nguyên
        cv2.drawMarker(processed_image, (int(shot_point[0]), int(shot_point[1])), (255, 255, 0), cv2.MARKER_CROSS, 40, 2)
        
    # Trả về tọa độ điểm bắn thay vì None
    return {'target': 'Trượt', 'score': 0, 'image': processed_image, 'coords': shot_point}