import cv2
import numpy as np
from typing import Optional, Tuple, List
import os

def friendly_object_name(filename: str) -> str:
    base = filename.split('/')[-1]
    name, _ = base.split('.') if '.' in base else (base, '')
    return name.replace('_', ' ')

def check_object_center(detections, image, calibrated_center):
    if calibrated_center:
        center_x, center_y = calibrated_center
    else:
        h, w, _ = image.shape
        center_x, center_y = w // 2, h // 2

    highest_conf_hit = None
    for det in detections:
        x1, y1, x2, y2 = det['box']
        if x1 <= center_x <= x2 and y1 <= center_y <= y2:
            if highest_conf_hit is None or det['conf'] > highest_conf_hit['conf']:
                highest_conf_hit = det

    if highest_conf_hit:
        x1, y1, x2, y2 = highest_conf_hit['box']
        
        hit_info = {
            'name': highest_conf_hit['class_name'],
            'crop': image[y1:y2, x1:x2].copy(),
            'shot_point_relative': (center_x - x1, center_y - y1),
            'shot_point_absolute': (center_x, center_y), # Đảm bảo trả về tọa độ tuyệt đối
            'conf': highest_conf_hit['conf']
        }
        print(f"✅ TRÚNG | Mục tiêu: {hit_info['name']} (Conf: {hit_info['conf']:.2f})")
        return "TRÚNG", hit_info
    
    print("❌ TRƯỢT | Tâm ngắm không nằm trong bất kỳ mục tiêu nào.")
    return "TRƯỢT", {'shot_point': (center_x, center_y)}

def warp_crop_to_original(original_img, cropped_img, shot_point_relative):
    MIN_MATCH_COUNT = 4 # Giữ nguyên ngưỡng
    
    try:
        # --- BẮT ĐẦU NÂNG CẤP ---
        # 1. Chuyển cả hai ảnh sang ảnh xám để loại bỏ yếu tố màu sắc
        original_gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
        cropped_gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)

        # 2. Cân bằng độ sáng để tăng độ tương phản và làm nổi bật các đặc điểm
        original_gray = cv2.equalizeHist(original_gray)
        cropped_gray = cv2.equalizeHist(cropped_gray)
        # --- KẾT THÚC NÂNG CẤP ---

        # Sử dụng SIFT detector, một thuật toán mạnh mẽ
        sift = cv2.SIFT_create()
        
        # Tìm các điểm đặc trưng và mô tả trên ảnh đã xử lý
        kp1, des1 = sift.detectAndCompute(original_gray, None)
        kp2, des2 = sift.detectAndCompute(cropped_gray, None)
        
        if des1 is None or des2 is None or len(des1) < 2 or len(des2) < 2:
            print("[warp_crop_to_original] Không đủ features để so khớp.")
            return None, None

        # Sử dụng FLANN matcher để tìm các cặp điểm tương đồng tốt nhất
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des2, des1, k=2)

        # Lọc ra các cặp điểm "tốt" bằng 'ratio test' của Lowe
        good_matches = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good_matches.append(m)

        print(f"[warp_crop_to_original] Số cặp điểm tốt tìm thấy: {len(good_matches)}")

        if len(good_matches) > MIN_MATCH_COUNT:
            # Lấy tọa độ của các cặp điểm tốt
            src_pts = np.float32([kp2[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            # Tìm ma trận biến đổi (homography)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is None:
                return None, None
            
            # Áp dụng ma trận biến đổi lên tọa độ điểm bắn
            shot_point_np = np.float32([[shot_point_relative]]).reshape(-1, 1, 2)
            transformed_point = cv2.perspectiveTransform(shot_point_np, M)
            
            return M, (transformed_point[0][0][0], transformed_point[0][0][1])
        else:
            return None, None

    except cv2.error as e:
        print(f"[warp_crop_to_original] Lỗi OpenCV: {e}")
        return None, None

#tính điểm bia số 4
def calculate_score_bia4b(pt: Tuple[float, float], original_img: np.ndarray, mask: np.ndarray) -> int:
    if original_img is None or mask is None or pt is None:
        return 0
    x, y = int(pt[0]), int(pt[1])
    h, w = original_img.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return 0

    center_x, center_y = 254, 250
    distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
    
    # Kiểm tra xem điểm chạm có nằm trong vùng hợp lệ của bia không
    if mask[y, x] == 255:
        if distance < 23: return 10
        elif distance < 45: return 9
        elif distance < 69: return 8
        elif distance < 92: return 7
        elif distance < 115: return 6
        elif distance < 137: return 5
        elif distance < 162: return 4
        elif distance < 185: return 3
        elif distance < 208: return 2
        elif distance < 231: return 1

    return 0

def calculate_score_bia4c(pt: Tuple[float, float], original_img: np.ndarray, mask: np.ndarray) -> int:
    if original_img is None or mask is None or pt is None:
        return 0
    x, y = int(pt[0]), int(pt[1])
    h, w = original_img.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return 0

    center_x, center_y = 249, 248.5
    distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
    
    # Kiểm tra xem điểm chạm có nằm trong vùng hợp lệ của bia không
    if mask[y, x] == 255:
        if distance < 46: return 10
        elif distance < 83: return 9
        elif distance < 121: return 8
        elif distance < 158: return 7
        elif distance < 194: return 6
        elif distance < 231: return 5

    return 0