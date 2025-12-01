# file: gui/ui/ui_practice.py

import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QGroupBox, QComboBox, QApplication, QStackedWidget, QLineEdit
)
import logging
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QSize, QPoint, Signal

logger = logging.getLogger(__name__)

class VideoLabel(QLabel):
    clicked = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        self.aspect_ratio = 3.0 / 4.0
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self._is_calibrating = False

    def set_calibration_mode(self, active: bool):
        self._is_calibrating = active
        self.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)
        self.setToolTip("Click để chọn tâm ngắm mới" if active else "")

    def mousePressEvent(self, event):
        if self._is_calibrating and event.button() == Qt.LeftButton:
            self.clicked.emit(event.pos())
        super().mousePressEvent(event)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return int(width / self.aspect_ratio)

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - scaled_pixmap.height()) / 2
        painter = QPainter(self)
        painter.drawPixmap(QPoint(int(x), int(y)), scaled_pixmap)


class MainGui(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setupUi()
        self._apply_labels()

    def setupUi(self):
        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        self.scale_factor = screen_height / 1080.0

        def scale_size(base_size):
            return max(1, int(base_size * self.scale_factor))
        def scale_font(base_size):
            return max(9, int(base_size * self.scale_factor))

        self.setStyleSheet(f"""
            QWidget {{ background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }}
            QFrame#panel {{ background-color: #34495e; border-radius: {scale_size(12)}px; border: 1px solid #4a6278; }}
            QLabel#title {{ color: #ecf0f1; padding: {scale_size(10)}px; }}
            QLabel.panel-title {{ font-size: {scale_font(16)}px; font-weight: bold; color: #ecf0f1; padding: {scale_size(8)}px {scale_size(15)}px; background-color: #415a72; border-radius: {scale_size(6)}px; }}
            QPushButton {{ background-color: #1abc9c; color: white; font-size: {scale_font(14)}px; font-weight: bold; border: none; padding: {scale_size(10)}px {scale_size(20)}px; border-radius: {scale_size(8)}px; }}
            QPushButton:hover {{ background-color: #16a085; }}
            QPushButton#danger {{ background-color: #e74c3c; }}
            QPushButton#danger:hover {{ background-color: #c0392b; }}
            QPushButton:disabled {{ background-color: #7f8c8d; }}
            QSlider::groove:horizontal {{ border: 1px solid #2c3e50; height: {scale_size(4)}px; background: #2c3e50; margin: {scale_size(2)}px 0; border-radius: {scale_size(2)}px; }}
            QSlider::handle:horizontal {{ background: #1abc9c; border: 1px solid #1abc9c; width: {scale_size(18)}px; margin: -{scale_size(7)}px 0; border-radius: {scale_size(9)}px; }}
            VideoLabel {{ background-color: #212f3d; border: 1px solid #4a6278; border-radius: {scale_size(8)}px; color: #95a5a6; font-size: {scale_font(24)}px; }}
            #controlsPanel {{ padding: {scale_size(10)}px; }}
            #zoomValueLabel {{ font-size: {scale_font(13)}px; font-weight: bold; color: #1abc9c; min-width: {scale_size(45)}px; }}
            QComboBox {{ border: 1px solid #4a6278; border-radius: {scale_size(4)}px; padding: {scale_size(5)}px; background-color: #5d6d7e; min-width: {scale_size(100)}px; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{ background-color: #5d6d7e; color: #ecf0f1; }}
            
            /* Style cho ô hiển thị tên người tập */
            QLineEdit {{ background-color: #34495e; border: 1px solid #4a6278; border-radius: {scale_size(4)}px; padding: {scale_size(5)}px; color: #ecf0f1; font-weight: bold; }}
            QLineEdit:read-only {{ background-color: #2c3e50; color: #bdc3c7; }}
            
            #refreshButton {{ background-color: #5d6d7e; border: 1px solid #4a6278; padding: {scale_size(5)}px {scale_size(10)}px; border-radius: {scale_size(4)}px; min-width: {scale_size(30)}px; }}
            #refreshButton:hover {{ background-color: #718090; }}
            QGroupBox {{ font-size: {scale_font(14)}px; font-weight: bold; border: 1px solid #4a6278; border-radius: {scale_size(8)}px; margin-top: {scale_size(10)}px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: {scale_size(2)}px {scale_size(8)}px; background-color: #415a72; border-radius: {scale_size(4)}px; }}
        """)

        margin = scale_size(20)
        spacing = scale_size(15)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(margin, scale_size(10), margin, margin)
        root_layout.setSpacing(spacing)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        title_label = QLabel("MÀN HÌNH TẬP LUYỆN")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont('Segoe UI', scale_font(18), QFont.Bold)
        title_label.setFont(title_font)
        
        self.mode_selector = QComboBox()
        self.mode_selector.addItem("Chế độ 1 Camera")
        self.mode_selector.addItem("Chế độ 2 Camera")
        self.mode_selector.setFixedWidth(200)

        self.back_button = QPushButton("Về Menu")
        self.back_button.setObjectName("danger")
        self.back_button.setFixedWidth(scale_size(150))

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Chế độ:"))
        header_layout.addWidget(self.mode_selector)
        header_layout.addWidget(self.back_button)
        
        root_layout.addLayout(header_layout)

        # --- STACKED WIDGET ---
        self.main_stack = QStackedWidget()
        root_layout.addWidget(self.main_stack)

        self.page_single = QWidget()
        self._setup_original_single_ui(self.page_single, scale_size, scale_font)
        self.main_stack.addWidget(self.page_single)

        self.page_dual = QWidget()
        self._setup_dual_ui(self.page_dual, scale_size, scale_font)
        self.main_stack.addWidget(self.page_dual)

    def _apply_labels(self):
        labels = self.config.get("labels", {})
        trainee_label_text = labels.get("trainee", "Người học")
        self.soldier_select_label.setText(f"{trainee_label_text}:")

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow_effect = QGraphicsDropShadowEffect(panel)
        shadow_effect.setBlurRadius(int(20 * self.scale_factor))
        shadow_effect.setColor(QColor(0, 0, 0, 80))
        shadow_effect.setOffset(0, int(5 * self.scale_factor))
        panel.setGraphicsEffect(shadow_effect)
        return panel

    def _setup_original_single_ui(self, parent, scale_size, scale_font):
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(scale_size(20))

        # Cột Trái
        left_panel = self._create_styled_panel()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(scale_size(15), scale_size(15), scale_size(15), scale_size(15))
        left_layout.setSpacing(scale_size(15))

        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title = QLabel("Đường ngắm trực tiếp")
        title.setProperty("class", "panel-title")
        title.setAlignment(Qt.AlignCenter)
        title_layout.addStretch(1)
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        left_layout.addWidget(title_widget)

        self.camera_view_label = VideoLabel()
        self.camera_view_label.setText("Vui lòng kết nối camera")
        left_layout.addWidget(self.camera_view_label, 1)

        controls_panel = QWidget()
        controls_layout = QHBoxLayout(controls_panel)
        
        self.single_cam_source = QComboBox()
        self.single_cam_source.setToolTip("Chọn nguồn Camera")
        self.single_cam_source.setMinimumWidth(scale_size(150))
        
        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.setObjectName("refreshButton")
        
        controls_layout.addWidget(QLabel("Nguồn:"))
        controls_layout.addWidget(self.single_cam_source)
        controls_layout.addWidget(self.refresh_button)
        controls_layout.addStretch(1)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10); self.zoom_slider.setMaximum(50); self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x")
        controls_layout.addWidget(QLabel("Zoom:"))
        controls_layout.addWidget(self.zoom_slider, 2)
        controls_layout.addWidget(self.zoom_value_label)
        controls_layout.addStretch(1)
        
        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        controls_layout.addWidget(self.calibrate_button)
        left_layout.addWidget(controls_panel)
        
        self.zoom_slider.valueChanged.connect(lambda v: self.zoom_value_label.setText(f"{v/10.0:.1f}x"))

        # Cột Phải
        right_panel = self._create_styled_panel()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(scale_size(20), scale_size(20), scale_size(20), scale_size(20))

        # Session Box
        session_box = QGroupBox("Quản lý Lần bắn")
        session_layout = QVBoxLayout(session_box)
        
        # --- THAY ĐỔI: Sử dụng LineEdit + Button thay cho ComboBox ---
        row1 = QHBoxLayout()
        self.soldier_select_label = QLabel()
        self.soldier_display = QLineEdit()
        self.soldier_display.setReadOnly(True)
        self.soldier_display.setPlaceholderText("Chưa chọn...")
        
        self.btn_select_soldier = QPushButton("Chọn")
        self.btn_select_soldier.setFixedWidth(scale_size(80))
        
        row1.addWidget(self.soldier_select_label)
        row1.addWidget(self.soldier_display, 1)
        row1.addWidget(self.btn_select_soldier)
        session_layout.addLayout(row1)
        # -------------------------------------------------------------

        row_trigger = QHBoxLayout()
        self.trigger_selector = QComboBox()
        row_trigger.addWidget(QLabel("Chọn Cò:"))
        row_trigger.addWidget(self.trigger_selector, 1)
        session_layout.addLayout(row_trigger)
        
        row2 = QHBoxLayout()
        self.session_button = QPushButton("Bắt đầu")
        row2.addWidget(self.session_button)
        session_layout.addLayout(row2)

        # Result Box
        result_box = QGroupBox("Kết quả mới nhất")
        result_layout = QVBoxLayout(result_box)
        
        self.score_label = QLabel("Điểm số: --")
        self.score_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #e74c3c;")
        self.score_label.setAlignment(Qt.AlignCenter)
        
        result_layout.addWidget(self.score_label)
        result_layout.addWidget(QLabel("Ảnh kết quả:"))
        self.result_image_label = VideoLabel()
        result_layout.addWidget(self.result_image_label, 1)

        right_layout.addWidget(session_box, 3)
        right_layout.addWidget(result_box, 7)
        layout.addWidget(left_panel, 6)
        layout.addWidget(right_panel, 4)

    def _setup_dual_ui(self, parent, scale_size, scale_font):
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(scale_size(10))

        def create_vertical_column(title, prefix):
            panel = self._create_styled_panel()
            col_layout = QVBoxLayout(panel)
            col_layout.setContentsMargins(scale_size(10), scale_size(10), scale_size(10), scale_size(10))
            
            header_widget = QWidget(); header_lo = QHBoxLayout(header_widget); header_lo.setContentsMargins(0,0,0,0)
            
            lbl_title = QLabel(title); lbl_title.setProperty("class", "panel-title")
            
            cmb_source = QComboBox(); cmb_source.setToolTip("Chọn nguồn Camera")
            
            cmb_trigger = QComboBox(); cmb_trigger.setToolTip("Chọn phím cò")
            cmb_trigger.setFixedWidth(scale_size(140))
            
            header_lo.addWidget(lbl_title)
            header_lo.addStretch()
            header_lo.addWidget(QLabel("Nguồn:"))
            header_lo.addWidget(cmb_source)
            header_lo.addSpacing(scale_size(10))
            header_lo.addWidget(QLabel("Cò:"))
            header_lo.addWidget(cmb_trigger)
            
            col_layout.addWidget(header_widget)
            
            # --- THAY ĐỔI: Session Control cho Dual Mode ---
            sess_widget = QWidget(); sess_lo = QHBoxLayout(sess_widget); sess_lo.setContentsMargins(0,0,0,0)
            
            txt_soldier = QLineEdit()
            txt_soldier.setReadOnly(True)
            txt_soldier.setPlaceholderText("Chưa chọn...")
            
            btn_select = QPushButton("...")
            btn_select.setFixedWidth(scale_size(40))
            
            btn_session = QPushButton("Bắt đầu"); btn_session.setMinimumWidth(80)
            
            sess_lo.addWidget(QLabel("Người:")); 
            sess_lo.addWidget(txt_soldier, 1); 
            sess_lo.addWidget(btn_select); 
            sess_lo.addWidget(btn_session)
            
            col_layout.addWidget(sess_widget)
            # -----------------------------------------------

            cam_view = VideoLabel(); cam_view.setText(f"Kết nối {title}")
            col_layout.addWidget(cam_view, 5) 
            
            ctrl_widget = QWidget(); ctrl_lo = QHBoxLayout(ctrl_widget); ctrl_lo.setContentsMargins(0,0,0,0)
            btn_refresh = QPushButton("Làm mới")
            sld_zoom = QSlider(Qt.Horizontal); sld_zoom.setRange(10,50); sld_zoom.setValue(10)
            lbl_zoom = QLabel("1.0x")
            sld_zoom.valueChanged.connect(lambda v: lbl_zoom.setText(f"{v/10.0:.1f}x"))
            btn_calib = QPushButton("Hiệu chỉnh")
            ctrl_lo.addWidget(btn_refresh); ctrl_lo.addWidget(QLabel("Zoom:")); ctrl_lo.addWidget(sld_zoom); ctrl_lo.addWidget(lbl_zoom); ctrl_lo.addWidget(btn_calib)
            col_layout.addWidget(ctrl_widget)
            
            grp_res = QGroupBox("Kết quả"); res_lo = QVBoxLayout(grp_res)
            lbl_score = QLabel("Điểm số: --"); lbl_score.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;"); lbl_score.setAlignment(Qt.AlignCenter)
            img_res = VideoLabel(); img_res.setText("Ảnh KQ")
            res_lo.addWidget(lbl_score); res_lo.addWidget(img_res, 1)
            col_layout.addWidget(grp_res, 4)
            
            # Map Attributes (THAY ĐỔI: cmb_soldier -> txt_soldier + btn_select)
            setattr(self, f"{prefix}_view", cam_view)
            setattr(self, f"{prefix}_source", cmb_source)
            setattr(self, f"{prefix}_soldier_display", txt_soldier) # Mới
            setattr(self, f"{prefix}_btn_select", btn_select)      # Mới
            setattr(self, f"{prefix}_session_btn", btn_session)
            setattr(self, f"{prefix}_refresh", btn_refresh)
            setattr(self, f"{prefix}_zoom", sld_zoom)
            setattr(self, f"{prefix}_calib", btn_calib)
            setattr(self, f"{prefix}_score", lbl_score)
            setattr(self, f"{prefix}_result_img", img_res)
            setattr(self, f"{prefix}_trigger", cmb_trigger)
            
            return panel

        col1 = create_vertical_column("CAMERA 1", "dual_cam1")
        col2 = create_vertical_column("CAMERA 2", "dual_cam2")
        layout.addWidget(col1)
        layout.addWidget(col2)

    def display_frame(self, frame_bgr):
        if frame_bgr is not None:
            pix = self._convert_cv_to_pixmap(frame_bgr)
            self.camera_view_label.setPixmap(pix)

    def _convert_cv_to_pixmap(self, cv_img):
        if cv_img is None: return QPixmap()
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return QPixmap.fromImage(QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888))

    def clear_video_feed(self, msg):
        empty = QPixmap()
        self.camera_view_label.setPixmap(empty); self.camera_view_label.setText(msg)
        if hasattr(self, 'dual_cam1_view'): self.dual_cam1_view.setPixmap(empty); self.dual_cam1_view.setText(msg)
        if hasattr(self, 'dual_cam2_view'): self.dual_cam2_view.setPixmap(empty); self.dual_cam2_view.setText(msg)

    def update_results(self, t, n, s, img):
        self.score_label.setText(f"Điểm số: {s}")
        pix = self._convert_cv_to_pixmap(img)
        self.result_image_label.setPixmap(pix if not pix.isNull() else QPixmap())
        self.result_image_label.setText("" if not pix.isNull() else "Chưa có ảnh")