# bia_so_4_model.py
import cv2
import numpy as np
from typing import Dict

def resize_image(src, target):
    return cv2.resize(src, (target.shape[1], target.shape[0]))

def warp_image(
    original,
    result,
    min_inliers=20,
    ratio_thresh=0.75,
    ransac_thresh=4.0,
    max_reproj=5.0,
    crop_center=False,
    debug=False,
) -> Dict:
    # Optionally crop vùng trung tâm (giảm nhiễu khi có nhiều nền)
    def crop_center_roi(img, ratio=0.6):
        h, w = img.shape[:2]
        ch, cw = int(h * ratio), int(w * ratio)
        x1, y1 = (w - cw) // 2, (h - ch) // 2
        return img[y1 : y1 + ch, x1 : x1 + cw]

    img1 = crop_center_roi(original) if crop_center else original.copy()
    img2 = crop_center_roi(result) if crop_center else result.copy()

    # 1. Detect ORB
    orb = cv2.ORB_create(nfeatures=1500, scaleFactor=1.2, edgeThreshold=15, patchSize=31)
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        return {"success": False, "message": "Không đủ đặc trưng để match."}

    # 2. Match descriptors
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches12 = bf.knnMatch(des1, des2, k=2)
    matches21 = bf.knnMatch(des2, des1, k=2)

    # 3. Lowe's ratio test
    good12 = [m for m, n in matches12 if m.distance < ratio_thresh * n.distance]
    good21 = [m for m, n in matches21 if m.distance < ratio_thresh * n.distance]

    # 4. Mutual match (cross-check)
    mutual = []
    reverse_map = {(m.trainIdx, m.queryIdx) for m in good21}
    for m in good12:
        if (m.queryIdx, m.trainIdx) in reverse_map:
            mutual.append(m)

    if len(mutual) < min_inliers:
        return {"success": False, "message": f"Mutual matches quá ít: {len(mutual)} < {min_inliers}"}

    # 5. Homography
    src_pts = np.float32([kp1[m.queryIdx].pt for m in mutual]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in mutual]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, ransac_thresh)
    if H is None or abs(np.linalg.det(H)) < 1e-6:
        return {"success": False, "message": "Homography không hợp lệ hoặc suy biến."}

    inlier_mask = mask.ravel() == 1
    if np.sum(inlier_mask) < min_inliers:
        return {"success": False, "message": f"Inlier quá ít sau RANSAC: {np.sum(inlier_mask)}"}

    # 6. Reprojection error
    src_in = src_pts[inlier_mask]
    dst_in = dst_pts[inlier_mask]
    projected = cv2.perspectiveTransform(dst_in, H)
    errors = np.linalg.norm(src_in - projected, axis=2).flatten()
    reproj_error = float(np.mean(errors)) if len(errors) > 0 else float("inf")

    if reproj_error > max_reproj:
        return {
            "success": False,
            "message": f"Reprojection error quá lớn: {reproj_error:.2f}",
            "reprojection_error": reproj_error,
        }

    # 7. Warp ảnh result về original
    aligned = cv2.warpPerspective(
        result, H, (original.shape[1], original.shape[0]), flags=cv2.INTER_LINEAR
    )

    out = {
        "success": True,
        "aligned": aligned,
        "homography": H,
        "reprojection_error": reproj_error,
        "inlier_count": int(np.sum(inlier_mask)),
        "message": "OK",
    }

    if debug:
        # 8. Vẽ debug
        vis_matches = cv2.drawMatches(
            original,
            kp1,
            result,
            kp2,
            [m for i, m in enumerate(mutual) if inlier_mask[i]],
            None,
            matchColor=(0, 255, 0),
            singlePointColor=(255, 0, 0),
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
        )
        vis_result = result.copy()
        if np.sum(inlier_mask) >= 3:
            hull_pts = cv2.convexHull(
                dst_pts[inlier_mask].reshape(-1, 2).astype(np.float32)
            )
            cv2.polylines(vis_result, [hull_pts.astype(int)], isClosed=True, color=(0, 255, 255), thickness=2)

        out.update(
            {
                "vis_matches": vis_matches,
                "vis_result_with_hull": vis_result,
            }
        )

    return out
