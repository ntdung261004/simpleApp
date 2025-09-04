# file: gui/windows/practice_window.py
import logging
from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtCore import QTimer, Signal, QThread, Slot
from PySide6.QtGui import QGuiApplication
import cv2

# THAY ĐỔI: Import cả lớp Camera
from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras, Camera
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):


        """
        Làm mới kết nối, chỉ chọn camera 0 nếu có nhiều hơn 1 camera được phát hiện.
        """
        logger.info("Đang tìm kiếm camera theo logic tùy chỉnh...")
        all_cameras = find_available_cameras()
        
        # THAY ĐỔI: Áp dụng logic mới
        if len(all_cameras) > 1:
            # Nếu có nhiều hơn 1 camera, kết nối với camera 0
            target_index = 0
            logger.info(f"Phát hiện {len(all_cameras)} camera. Kết nối với camera USB tại chỉ số {target_index}.")
            self.connect_camera(target_index)
        elif len(all_cameras) == 1:
            # Nếu chỉ có 1 camera, đó là camera laptop, không kết nối
            logger.warning("Chỉ phát hiện camera laptop. Vui lòng kết nối camera USB.")
            self.disconnect_camera(message="Vui lòng kết nối USB Camera")
        else:
            # Nếu không có camera nào
            logger.warning("Không tìm thấy bất kỳ camera nào.")
            self.disconnect_camera(message="Không tìm thấy camera")