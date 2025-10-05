# file: utils/filters.py
import cv2
import numpy as np

def apply_gamma_correction(image, gamma=1.0):
    """
    Áp dụng hiệu chỉnh Gamma lên ảnh.
    - gamma < 1: Làm ảnh sáng hơn.
    - gamma = 1: Không thay đổi.
    - gamma > 1: Làm ảnh tối hơn (phù hợp khi trời nắng gắt).
    """
    if gamma <= 0:  # Tránh lỗi toán học
        return image
        
    # Tạo bảng tra cứu (lookup table) để tăng tốc độ xử lý
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
                      for i in np.arange(0, 256)]).astype("uint8")
    
    # Áp dụng bảng tra cứu lên ảnh
    return cv2.LUT(image, table)