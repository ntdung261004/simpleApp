# file: utils/license_manager.py
import hashlib
import logging
import subprocess # <<< THÊM MỚI

logger = logging.getLogger(__name__)
SECRET_SALT = "0986534710" # Giữ nguyên chuỗi bí mật của bạn

# --- BẮT ĐẦU VÙNG SỬA ĐỔI: CHUYỂN HOÀN TOÀN SANG DÙNG UUID ---
def get_system_uuid() -> str:
    """
    Lấy UUID của bo mạch chủ. Đây là định danh ổn định và đáng tin cậy nhất.
    """
    try:
        # Chạy lệnh của Windows để lấy UUID
        command = "wmic csproduct get uuid"
        uuid = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.DEVNULL)
        
        # Kết quả trả về có chứa tiêu đề và các dòng trống, cần làm sạch
        clean_uuid = uuid.strip().split('\n')[-1].strip()
        
        if clean_uuid and len(clean_uuid) > 5:
             logger.info(f"Lấy được System UUID: {clean_uuid}")
             return clean_uuid
        else:
            logger.error("Lệnh wmic không trả về UUID hợp lệ.")
            return "UUID_NOT_FOUND"
            
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng khi lấy System UUID: {e}")
        return "UUID_ERROR"


def generate_key(system_id: str) -> str:
    """Tạo license key từ một định danh hệ thống (UUID) và chuỗi bí mật."""
    s = hashlib.sha256()
    data = f"{system_id.strip().upper()}-{SECRET_SALT}"
    s.update(data.encode('utf-8'))
    return s.hexdigest()[:24].upper()

def verify_key(license_key: str) -> bool:
    """Kiểm tra xem license key có hợp lệ với máy tính hiện tại không."""
    current_uuid = get_system_uuid()
    
    if "UUID_" in current_uuid:
        logger.error(f"Không thể xác thực key vì không lấy được UUID. Mã lỗi: {current_uuid}")
        return False
        
    expected_key = generate_key(current_uuid)
    is_valid = (license_key.strip().upper() == expected_key)
    
    if not is_valid:
        logger.warning(f"Xác thực thất bại. Key cung cấp: {license_key}, Key mong đợi cho UUID ({current_uuid}): {expected_key}")
        
    return is_valid
# --- KẾT THÚC VÙNG SỬA ĐỔI ---