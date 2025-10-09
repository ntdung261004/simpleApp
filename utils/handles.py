# file: utils/handles.py
import cv2
from utils.processing import warp_crop_to_original, calculate_score_bia4b, calculate_score_bia4c
import logging

logger = logging.getLogger(__name__)

# === BẮT ĐẦU SỬA ĐỔI: NÂNG CẤP HÀM XỬ LÝ KHI BẮN TRƯỢT ===
def handle_miss(hit_info: dict, original_frame):
    """
    Xử lý khi bắn trượt. Vẽ một dấu chữ thập đỏ lên vị trí tâm ngắm
    trên frame ảnh gốc để biết đã ngắm vào đâu.
    """
    logger.info("Xử lý kết quả: TRƯỢT")
    
    # Lấy tọa độ tâm ngắm tuyệt đối trên frame ảnh (được gửi từ processing.py)
    shot_point = hit_info.get('shot_point_absolute')
    
    # Tạo một bản sao của frame gốc để vẽ lên, tránh thay đổi ảnh gốc
    result_image = original_frame.copy()
    
    # Nếu có tọa độ tâm ngắm, vẽ dấu chữ thập màu đỏ
    if shot_point:
        px, py = shot_point
        cv2.drawMarker(result_image, (int(px), int(py)), (0, 0, 255), 
                       markerType=cv2.MARKER_CROSS, markerSize=40, thickness=3)
        
    return {
        'target': "Trượt",
        'score': 0,
        'image': result_image, # Trả về ảnh đã được vẽ tâm ngắm
        'coords': None # Không có tọa độ trên bia khi trượt
    }
# === KẾT THÚC SỬA ĐỔI ===


def handle_hit_bia_4b(hit_info, original_frame, original_img, original_img_alt, mask):
    # (Hàm này giữ nguyên như trong file của bạn)
    obj_crop = hit_info['crop']
    shot_point_relative = hit_info['shot_point_relative']
    processed_image = original_img.copy() 
    score = 0
    transformed_point = None
    warp_method = "Không xác định"

    _, transformed_point = warp_crop_to_original(original_img, obj_crop, shot_point_relative)
    if transformed_point:
        warp_method = "Ảnh gốc chính"
        score = calculate_score_bia4b(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 0, 255), cv2.MARKER_CROSS, 40, 3)

    elif original_img_alt is not None:
        _, transformed_point = warp_crop_to_original(original_img_alt, obj_crop, shot_point_relative)
        if transformed_point:
            warp_method = "Ảnh tham chiếu webcam"
            score = calculate_score_bia4b(transformed_point, original_img, mask)
            cv2.drawMarker(processed_image, (int(transformed_point[0]), int(transformed_point[1])), (0, 165, 255), cv2.MARKER_CROSS, 40, 3)

    if transformed_point is None:
        warp_method = "Fallback (Ước tính)"
        h_orig, w_orig = original_img.shape[:2]
        h_crop, w_crop = obj_crop.shape[:2]
        center_orig = (w_orig / 2, h_orig / 2); center_crop = (w_crop / 2, h_crop / 2)
        offset_x = shot_point_relative[0] - center_crop[0]; offset_y = shot_point_relative[1] - center_crop[1]
        scale_x = w_orig / w_crop; scale_y = h_orig / h_crop
        final_x = int(center_orig[0] + (offset_x * scale_x)); final_y = int(center_orig[1] + (offset_y * scale_y))
        transformed_point = (final_x, final_y)
        score = calculate_score_bia4b(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    print(f"INFO: Điểm được tính bằng phương pháp: {warp_method}")
    target_name = "Bia số 4b"
    if score == 0:
        target_name = "Trượt"
        
    return {'target': target_name, 'score': score, 'image': processed_image, 'coords': transformed_point}


def handle_hit_bia_4c(hit_info, original_frame, original_img, original_img_alt, mask):
    # (Hàm này giữ nguyên như trong file của bạn)
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
        center_orig = (w_orig / 2, h_orig / 2); center_crop = (w_crop / 2, h_crop / 2)
        offset_x = shot_point_relative[0] - center_crop[0]; offset_y = shot_point_relative[1] - center_crop[1]
        scale_x = w_orig / w_crop; scale_y = h_orig / h_crop
        final_x = int(center_orig[0] + (offset_x * scale_x)); final_y = int(center_orig[1] + (offset_y * scale_y))
        transformed_point = (final_x, final_y)
        score = calculate_score_bia4c(transformed_point, original_img, mask)
        cv2.drawMarker(processed_image, transformed_point, (0, 255, 255), cv2.MARKER_CROSS, 40, 3)

    print(f"INFO: Điểm được tính bằng phương pháp: {warp_method}")
    target_name = "Bia số 4c"
    if score == 0:
        target_name = "Trượt"
        
    return {'target': target_name, 'score': score, 'image': processed_image, 'coords': transformed_point}