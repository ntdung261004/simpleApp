# file: utils/handles.py
import cv2
from utils.processing import warp_crop_to_original, calculate_score_bia4b, calculate_score_bia4c

# --- HÀM XỬ LÝ VỚI LOGIC DỰ PHÒNG 3 LỚP ---

def handle_hit_bia_4b(hit_info, original_frame, original_img, original_img_alt, mask):
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    processed_image = original_img.copy() 
    score = 0
    transformed_point = None
    warp_method = "Không xác định" # Biến để theo dõi phương pháp thành công

    # === LỚP 1: Thử warp với ảnh gốc CHÍNH (chất lượng cao) ===
    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    if transformed_point:
        warp_method = "Ảnh gốc chính"
        score = calculate_score_bia4b(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)

    # === LỚP 2: Nếu Lớp 1 thất bại, thử warp với ảnh PHỤ (từ webcam) ===
    elif original_img_alt is not None:
        _, transformed_point = warp_crop_to_original(original_img_alt, obj_crop, shot_point_relative)
        if transformed_point:
            warp_method = "Ảnh tham chiếu webcam"
            # Vẫn tính điểm và vẽ lên ảnh gốc chính để đồng nhất hiển thị
            score = calculate_score_bia4b(transformed_point, original_img, mask)
            cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3) # Màu cam

    # === LỚP 3: Nếu cả hai lớp trên thất bại, dùng logic fallback cuối cùng ===
    if transformed_point is None:
        warp_method = "Fallback (Ước tính)"
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        center_orig = (w_orig / 2, h_orig / 2)
        center_crop = (w_crop / 2, h_crop / 2)
        offset_x = shot_point_relative[0] - center_crop[0]
        offset_y = shot_point_relative[1] - center_crop[1]
        scale_x = w_orig / w_crop
        scale_y = h_orig / h_crop
        scaled_offset_x = offset_x * scale_x
        scaled_offset_y = offset_y * scale_y
        final_x = int(center_orig[0] + scaled_offset_x)
        final_y = int(center_orig[1] + scaled_offset_y)
        
        transformed_point = (final_x, final_y)
        score = calculate_score_bia4b(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3) # Màu vàng

    print(f"INFO: Điểm được tính bằng phương pháp: {warp_method}")
    target_name = "Bia số 4b"
    if score == 0:
        target_name = "Trượt"
        
    return {'target': target_name, 'score': score, 'image': processed_image, 'coords': transformed_point}


# Tương tự cho bia 4c
def handle_hit_bia_4c(hit_info, original_frame, original_img, original_img_alt, mask):
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    processed_image = original_img.copy() 
    score = 0
    transformed_point = None
    warp_method = "Không xác định"

    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    if transformed_point:
        warp_method = "Ảnh gốc chính"
        score = calculate_score_bia4c(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)

    elif original_img_alt is not None:
        _, transformed_point = warp_crop_to_original(original_img_alt, obj_crop, shot_point_relative)
        if transformed_point:
            warp_method = "Ảnh tham chiếu webcam"
            score = calculate_score_bia4c(transformed_point, original_img, mask)
            cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3)

    if transformed_point is None:
        warp_method = "Fallback (Ước tính)"
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        center_orig = (w_orig / 2, h_orig / 2)
        center_crop = (w_crop / 2, h_crop / 2)
        offset_x = shot_point_relative[0] - center_crop[0]
        offset_y = shot_point_relative[1] - center_crop[1]
        scale_x = w_orig / w_crop
        scale_y = h_orig / h_crop
        scaled_offset_x = offset_x * scale_x
        scaled_offset_y = offset_y * scale_y
        final_x = int(center_orig[0] + scaled_offset_x)
        final_y = int(center_orig[1] + scaled_offset_y)
        
        transformed_point = (final_x, final_y)
        score = calculate_score_bia4c(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    print(f"INFO: Điểm được tính bằng phương pháp: {warp_method}")
    target_name = "Bia số 4c"
    if score == 0:
        target_name = "Trượt"
        
    return {'target': target_name, 'score': score, 'image': processed_image, 'coords': transformed_point}

    
def handle_miss(hit_info, original_frame):
    processed_image = original_frame.copy()
    shot_point = hit_info.get('shot_point')
    if shot_point:
        cv2.drawMarker(processed_image, (int(shot_point[0]), int(shot_point[1])), (255, 255, 0), cv2.MARKER_CROSS, 40, 2)
    return {'target': 'Trượt', 'score': 0, 'image': processed_image, 'coords': shot_point}