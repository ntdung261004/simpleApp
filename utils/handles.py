# utils/handles.py
import cv2
from utils.processing import warp_crop_to_original, calculate_score_bia4, calculate_score_bia7, calculate_score_bia8

# THAY ĐỔI: Tên tham số đã được chuẩn hóa
def handle_hit_bia_so_4(hit_info, original_frame, original_img, original_img_alt, mask):
    obj_crop = hit_info['crop']
    shot_point = hit_info['shot_point']
    processed_image = original_img.copy()
    score = 0
    
    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point)
    if transformed_point:
        score = calculate_score_bia4(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
    elif original_img_alt is not None:
        _, transformed_point_alt = warp_crop_to_original(original_img_alt, obj_crop, shot_point)
        if transformed_point_alt:
            score = calculate_score_bia4(transformed_point_alt, original_img_alt, mask)
            cv2.drawMarker(processed_image, (int(transformed_point_alt[0]), int(transformed_point_alt[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3)
        else: # Fallback
            h_orig, w_orig = original_img.shape[:2]
            h_crop, w_crop = obj_crop.shape[:2]
            scaled_shot_point = (int(shot_point[0] * w_orig / w_crop), int(shot_point[1] * h_orig / h_crop))
            score = calculate_score_bia4(scaled_shot_point, original_img, mask)
            cv2.drawMarker(processed_image, scaled_shot_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    return {'target': 'Bia số 4', 'score': score, 'image': processed_image}

# THAY ĐỔI: Tên tham số đã được chuẩn hóa
def handle_hit_bia_so_7(hit_info, original_frame, original_img, original_img_alt, mask):
    obj_crop = hit_info['crop']
    shot_point = hit_info['shot_point']
    processed_image = original_img.copy()
    score = 0
    
    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point)
    if transformed_point:
        score = calculate_score_bia7(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
    elif original_img_alt is not None:
        _, transformed_point_alt = warp_crop_to_original(original_img_alt, obj_crop, shot_point)
        if transformed_point_alt:
            score = calculate_score_bia7(transformed_point_alt, original_img_alt, mask)
            cv2.drawMarker(processed_image, (int(transformed_point_alt[0]), int(transformed_point_alt[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3)
        else: # Fallback
            h_orig, w_orig = original_img.shape[:2]
            h_crop, w_crop = obj_crop.shape[:2]
            scaled_shot_point = (int(shot_point[0] * w_orig / w_crop), int(shot_point[1] * h_orig / h_crop))
            score = calculate_score_bia7(scaled_shot_point, original_img, mask)
            cv2.drawMarker(processed_image, scaled_shot_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)
            
    return {'target': 'Bia số 7', 'score': score, 'image': processed_image}
    
# THAY ĐỔI: Tên tham số đã được chuẩn hóa
def handle_hit_bia_so_8(hit_info, original_frame, original_img, original_img_alt, mask):
    obj_crop = hit_info['crop']
    shot_point = hit_info['shot_point']
    processed_image = original_img.copy()
    score = 0
    
    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point)
    if transformed_point:
        score = calculate_score_bia8(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
    elif original_img_alt is not None:
        _, transformed_point_alt = warp_crop_to_original(original_img_alt, obj_crop, shot_point)
        if transformed_point_alt:
            score = calculate_score_bia8(transformed_point_alt, original_img_alt, mask)
            cv2.drawMarker(processed_image, (int(transformed_point_alt[0]), int(transformed_point_alt[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3)
        else: # Fallback
            h_orig, w_orig = original_img.shape[:2]
            h_crop, w_crop = obj_crop.shape[:2]
            scaled_shot_point = (int(shot_point[0] * w_orig / w_crop), int(shot_point[1] * h_orig / h_crop))
            score = calculate_score_bia8(scaled_shot_point, original_img, mask)
            cv2.drawMarker(processed_image, scaled_shot_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    return {'target': 'Bia số 8', 'score': score, 'image': processed_image}
    
def handle_miss(hit_info, original_frame):
    processed_image = original_frame.copy()
    shot_point = hit_info['shot_point']
    cv2.drawMarker(processed_image, shot_point, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
    return {'target': 'Trượt', 'score': 0, 'image': processed_image}