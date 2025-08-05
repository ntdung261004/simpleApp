from pathlib import Path
from datetime import datetime
import cv2

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QSizePolicy, QDialog, QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QCursor


class ImagePreviewDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xem ảnh")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background: #1f242a; color: #e3e6ee;")
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QLabel()
        content.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        content.setAlignment(Qt.AlignCenter)
        scroll.setWidget(content)
        layout.addWidget(scroll)


class CaptureGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Webcam Capture → Xử lý")
        self.resize(1100, 700)
        self.current_frame = None

        # Style
        self.setStyleSheet("""
            QWidget { background: #1f242a; color: #e3e6ee; font-family: system-ui; }
            QPushButton {
                background: #5c6ef8;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-weight: 600;
            }
            QPushButton:hover { background: #7d8fff; }
            QLabel { background: transparent; }
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Aside list
        aside = QVBoxLayout()
        title = QLabel("Ảnh đã xử lý")
        title.setStyleSheet("font-size:16px; font-weight:700;")
        title.setAlignment(Qt.AlignCenter)
        aside.addWidget(title)

        self.thumb_list = QListWidget()
        self.thumb_list.setViewMode(QListWidget.ListMode)
        self.thumb_list.setSpacing(0)
        self.thumb_list.setUniformItemSizes(False)
        self.thumb_list.itemDoubleClicked.connect(self._on_thumb_double)
        aside.addWidget(self.thumb_list, 1)

        root.addLayout(aside, 3)

        # Main area
        main_area = QVBoxLayout()
        # Top toolbar: toggle YOLO
        toolbar = QHBoxLayout()
        self.yolo_checkbox = QCheckBox("Bật YOLO trên stream")
        self.yolo_checkbox.setChecked(True)
        toolbar.addWidget(self.yolo_checkbox)
        toolbar.addStretch()
        main_area.addLayout(toolbar)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setStyleSheet("background: #12151f; border-radius: 10px;")
        main_area.addWidget(self.video_label, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_capture = QPushButton("Chụp & Xử lý")
        self.btn_capture.setFixedHeight(48)
        btn_row.addWidget(self.btn_capture)
        btn_row.addStretch()
        main_area.addLayout(btn_row)

        root.addLayout(main_area, 7)

    def display_frame(self, frame_bgr):
        if frame_bgr is None:
            return
        self.current_frame = frame_bgr
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        from PySide6.QtGui import QImage
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(
            self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pix)

    def add_processed_thumbnail(self, frame_bgr):
        # tạo pixmap từ frame
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        # item layout đơn hàng
        container = QWidget()
        container.setCursor(QCursor(Qt.PointingHandCursor))
        container.setStyleSheet("""
            QWidget {
                background: transparent;
                border-bottom: 1px solid rgba(255,255,255,0.08);
            }
            QWidget:hover {
                background: rgba(255,255,255,0.04);
            }
        """)
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(8, 4, 8, 4)
        h_layout.setSpacing(10)

        thumb = pix.scaled(100, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        thumb_label = QLabel()
        thumb_label.setPixmap(thumb)
        thumb_label.setFixedSize(100, 75)
        h_layout.addWidget(thumb_label)

        info_layout = QHBoxLayout()
        title_text = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size:12px; font-weight:600;")
        info_layout.addWidget(title_label)

        # kích thước
        success, buf = cv2.imencode(".jpg", frame_bgr)
        size_kb = len(buf) // 1024
        size_label = QLabel(f"{size_kb} KB")
        size_label.setStyleSheet("font-size:11px; color: #99a0c1;")
        info_layout.addWidget(size_label)

        info_layout.addStretch()
        h_layout.addLayout(info_layout, 1)

        item = QListWidgetItem(self.thumb_list)
        item.setSizeHint(QSize(0, 90))
        self.thumb_list.addItem(item)
        self.thumb_list.setItemWidget(item, container)
        item.setData(Qt.UserRole, pix)

    def _on_thumb_double(self, item: QListWidgetItem):
        pix = item.data(Qt.UserRole)
        if not isinstance(pix, QPixmap):
            return
        dlg = ImagePreviewDialog(pix, parent=self)
        dlg.exec()
