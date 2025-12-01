# file: utils/processing.py
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

# --- CẤU HÌNH GLOBAL: DỄ DÀNG TINH CHỈNH THÔNG SỐ TẠI ĐÂY ---
# Lưu ý: Các thông số này đang tương ứng với kích thước ảnh gốc trong thư mục assets.
# Nếu thay ảnh có độ phân giải khác, chỉ cần cập nhật lại thông số tại đây.

TARGET_CONFIGS = {
    'bia_so_8': {
        'center': (87, 116), # (x, y)
        # Danh sách các vòng điểm: (Điểm, Rộng, Cao)
        'rings': [
            (10, 42, 63), (9, 84, 126), (8, 126, 190), (7, 172, 258),
            (6, 216, 324), (5, 260, 324), (4, 304, 456), (3, 348, 522),
            (2, 392, 588), (1, 436, 654)
        ]
    },
    'bia_so_7_8': {
        'center': (136, 177),
        'rings': [
            (10, 63, 95), (9, 126, 190), (8, 189, 284), (7, 252, 378),
            (6, 309, 464), (5, 375, 562), (4, 436, 654), (3, 497, 746),
            (2, 557, 836), (1, 613, 920)
        ]
    },
    'bia_so_4': {
        # Bia số 4 tính điểm theo vòng tròn đồng tâm
        # Danh sách vòng: (Điểm, Bán kính r)
        'rings': [
            (10, 56), (9, 116), (8, 173), (7, 230), (6, 285), (5, 320)
        ]
    }
}

# --- KHỞI TẠO CÔNG CỤ XỬ LÝ ẢNH ---
ORB_DETECTOR = cv2.ORB_create(nfeatures=800, scaleFactor=1.2, edgeThreshold=15, patchSize=31)
BF_MATCHER = cv2.BFMatcher(cv2.NORM_HAMMING)

def friendly_object_name(filename: str) -> str:
    base = filename.split('/')[-1]
    name, _ = base.split('.') if '.' in base else (base, '')
    return name.replace('_', ' ')

def check_object_center(detections: List[Dict], image: np.ndarray, calibrated_center: Optional[Tuple[int, int]]) -> Tuple[str, Dict]:
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
            'shot_point_absolute': (center_x, center_y),
            'conf': highest_conf_hit['conf']
        }
        print(f"✅ TRÚNG | Mục tiêu: {hit_info['name']} (Conf: {hit_info['conf']:.2f})")
        return "TRÚNG", hit_info
    
    print("❌ TRƯỢT | Tâm ngắm không nằm trong bất kỳ mục tiêu nào.")
    return "TRƯỢT", {'shot_point': (center_x, center_y)}

def warp_crop_to_original(
    original_img: np.ndarray,
    obj_crop: np.ndarray,
    shot_point: Optional[Tuple[float, float]] = None,
    min_inliers: int = 5,
    ratio_thresh: float = 0.75,
    ransac_thresh: float = 4.0
) -> Tuple[Optional[np.ndarray], Optional[Tuple[float, float]]]:
    if original_img is None or obj_crop is None:
        return None, None

    kp1, des1 = ORB_DETECTOR.detectAndCompute(original_img, None)
    kp2, des2 = ORB_DETECTOR.detectAndCompute(obj_crop, None)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        return None, None

    matches12 = BF_MATCHER.knnMatch(des1, des2, k=2)
    matches21 = BF_MATCHER.knnMatch(des2, des1, k=2)
    
    good12 = [m for m, n in matches12 if m.distance < ratio_thresh * n.distance]
    good21 = [m for m, n in matches21 if m.distance < ratio_thresh * n.distance]

    mutual = []
    reverse_map = {(m.trainIdx, m.queryIdx) for m in good21}
    for m in good12:
        if (m.queryIdx, m.trainIdx) in reverse_map:
            mutual.append(m)

    if len(mutual) < min_inliers:
        return None, None

    src_pts = np.float32([kp1[m.queryIdx].pt for m in mutual]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in mutual]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, ransac_thresh)
    if H is None or abs(np.linalg.det(H)) < 1e-6:
        return None, None

    transformed_point = None
    if shot_point is not None:
        try:
            px, py = float(shot_point[0]), float(shot_point[1])
            src_pt = np.array([[[px, py]]], dtype=np.float32)
            warped_pt = cv2.perspectiveTransform(src_pt, H)[0][0]
            transformed_point = (float(warped_pt[0]), float(warped_pt[1]))
        except Exception:
            pass

    warped = cv2.warpPerspective(obj_crop, H, (original_img.shape[1], original_img.shape[0]), flags=cv2.INTER_LINEAR)
    return warped, transformed_point

# --- LOGIC TÍNH ĐIỂM ĐÃ ĐƯỢC TỐI ƯU HÓA ---

def _calculate_ellipse_score(pt: Tuple[float, float], original_img: np.ndarray, mask: np.ndarray, config: dict) -> int:
    """Hàm tính điểm chung cho các bia hình Elip (7, 8)."""
    if pt is None or mask is None or original_img is None: return 0
    x, y = int(pt[0]), int(pt[1])
    h, w = original_img.shape[:2]
    
    # Kiểm tra biên và mask
    if not (0 <= y < h and 0 <= x < w): return 0
    if mask[y, x] == 0: return 0

    cx, cy = config['center']
    
    # Duyệt qua các vòng điểm từ trong ra ngoài (10 -> 1)
    # Vì config xếp từ 10 xuống 1, vòng nào thỏa mãn trước thì trả về điểm đó ngay
    for score, width, height in config['rings']:
        a, b = width / 2.0, height / 2.0
        # Phương trình Elip: ((x-h)^2 / a^2) + ((y-k)^2 / b^2) <= 1
        if ((x - cx)**2 / a**2) + ((y - cy)**2 / b**2) <= 1:
            return score
    return 0

def calculate_score_bia8(pt: Tuple[float, float], original_img: np.ndarray, mask: np.ndarray) -> int:
    return _calculate_ellipse_score(pt, original_img, mask, TARGET_CONFIGS['bia_so_8'])

def calculate_score_bia7(pt: Tuple[float, float], original_img: np.ndarray, mask: np.ndarray) -> int:
    return _calculate_ellipse_score(pt, original_img, mask, TARGET_CONFIGS['bia_so_7_8'])

def calculate_score_bia4(pt: Tuple[float, float], original_img: np.ndarray, mask: np.ndarray) -> int:
    """Tính điểm cho bia số 4 (Hình tròn)."""
    if pt is None or mask is None or original_img is None: return 0
    x, y = int(pt[0]), int(pt[1])
    h, w = original_img.shape[:2]
    
    if not (0 <= x < w and 0 <= y < h): return 0
    
    # Bia 4 đặc biệt: Tâm là tâm ảnh
    cx, cy = w // 2, h // 2
    distance = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
    
    if mask[y, x] == 255:
        # Duyệt qua các vòng cấu hình
        for score, radius in TARGET_CONFIGS['bia_so_4']['rings']:
            if distance < radius:
                return score
    return 0