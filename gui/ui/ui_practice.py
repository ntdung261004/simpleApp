# file: gui/ui/ui_practice.py
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QGroupBox, QComboBox, QApplication, QStackedWidget, QLineEdit,
    QListWidget, QAbstractItemView, QFormLayout
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QSize, QPoint, Signal

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
        self.default_style = "background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6;"
        self.active_style = "background-color: #212f3d; border: 3px solid #2ecc71; border-radius: 8px; color: #95a5a6;"
        self.setStyleSheet(self.default_style)

    def set_calibration_mode(self, active: bool):
        self._is_calibrating = active
        self.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)
        self.setToolTip("Click để chọn tâm ngắm mới" if active else "")

    def set_active_border(self, is_active: bool):
        if is_active: self.setStyleSheet(self.active_style)
        else: self.setStyleSheet(self.default_style)

    def mousePressEvent(self, event):
        if self._is_calibrating and event.button() == Qt.LeftButton:
            self.clicked.emit(event.pos())
        super().mousePressEvent(event)

    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return int(width / self.aspect_ratio)

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
        self.scale_factor = screen.height() / 1080.0
        def scale_size(base_size): return max(1, int(base_size * self.scale_factor))
        def scale_font(base_size): return max(9, int(base_size * self.scale_factor))

        self.setStyleSheet(f"""
            QWidget {{ background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }}
            QFrame#panel {{ background-color: #34495e; border-radius: {scale_size(12)}px; border: 1px solid #4a6278; }}
            QLabel#title {{ color: #ecf0f1; padding: {scale_size(10)}px; }}
            QLabel.panel-title {{ font-size: {scale_font(16)}px; font-weight: bold; color: #ecf0f1; padding: {scale_size(8)}px {scale_size(15)}px; background-color: #415a72; border-radius: {scale_size(6)}px; }}
            QPushButton.menu-btn {{ background-color: #34495e; color: #ecf0f1; font-size: {scale_font(18)}px; font-weight: bold; border: 2px solid #4a6278; border-radius: 15px; padding: {scale_size(20)}px; text-align: left; padding-left: 30px; }}
            QPushButton.menu-btn:hover {{ background-color: #1abc9c; border-color: #16a085; color: white; }}
            QPushButton {{ background-color: #1abc9c; color: white; font-size: {scale_font(14)}px; font-weight: bold; border: none; padding: {scale_size(10)}px {scale_size(20)}px; border-radius: {scale_size(8)}px; }}
            QPushButton:hover {{ background-color: #16a085; }}
            QPushButton#danger {{ background-color: #e74c3c; }}
            QPushButton#danger:hover {{ background-color: #c0392b; }}
            QSlider::groove:horizontal {{ border: 1px solid #2c3e50; height: {scale_size(4)}px; background: #2c3e50; margin: {scale_size(2)}px 0; border-radius: {scale_size(2)}px; }}
            QSlider::handle:horizontal {{ background: #1abc9c; border: 1px solid #1abc9c; width: {scale_size(18)}px; margin: -{scale_size(7)}px 0; border-radius: {scale_size(9)}px; }}
            VideoLabel {{ font-size: {scale_font(24)}px; }} 
            #zoomValueLabel {{ font-size: {scale_font(13)}px; font-weight: bold; color: #1abc9c; min-width: {scale_size(45)}px; }}
            QComboBox {{ border: 1px solid #4a6278; border-radius: {scale_size(4)}px; padding: {scale_size(5)}px; background-color: #5d6d7e; min-width: {scale_size(100)}px; }}
            QLineEdit {{ background-color: #34495e; border: 1px solid #4a6278; border-radius: {scale_size(4)}px; padding: {scale_size(5)}px; color: #ecf0f1; font-weight: bold; }}
            #refreshButton {{ background-color: #5d6d7e; border: 1px solid #4a6278; padding: {scale_size(5)}px {scale_size(10)}px; border-radius: {scale_size(4)}px; min-width: {scale_size(30)}px; }}
            QGroupBox {{ font-size: {scale_font(14)}px; font-weight: bold; border: 1px solid #4a6278; border-radius: {scale_size(8)}px; margin-top: {scale_size(10)}px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: {scale_size(2)}px {scale_size(8)}px; background-color: #415a72; border-radius: {scale_size(4)}px; }}
            QListWidget {{ background-color: #34495e; border: 1px solid #4a6278; border-radius: 6px; font-size: {scale_font(13)}px; }}
            QListWidget::item {{ padding: 8px; border-bottom: 1px solid #4a6278; }}
            QListWidget::item:selected {{ background-color: #1abc9c; color: white; }}
        """)

        self.stack = QStackedWidget(self)
        
        # Các trang giao diện
        self.page_dashboard = QWidget()
        self._setup_dashboard(self.page_dashboard, scale_size, scale_font)
        self.stack.addWidget(self.page_dashboard)

        self.page_session_menu = QWidget()
        self._setup_session_menu(self.page_session_menu, scale_size, scale_font)
        self.stack.addWidget(self.page_session_menu)

        self.page_create_session = QWidget()
        self._setup_create_session_page(self.page_create_session, scale_size, scale_font)
        self.stack.addWidget(self.page_create_session)

        self.page_view = QWidget()
        self._setup_practice_view(self.page_view, scale_size, scale_font)
        self.stack.addWidget(self.page_view)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.stack)

    def _apply_labels(self):
        pass

    def _setup_dashboard(self, parent, scale_size, scale_font):
        layout = QVBoxLayout(parent); layout.setAlignment(Qt.AlignCenter); layout.setSpacing(scale_size(20)); layout.addSpacing(scale_size(60))
        lbl_title = QLabel("CHẾ ĐỘ LUYỆN TẬP"); lbl_title.setStyleSheet(f"font-size: {scale_font(32)}px; font-weight: bold; color: #ecf0f1;"); lbl_title.setAlignment(Qt.AlignCenter); layout.addWidget(lbl_title)
        layout.addSpacing(scale_size(40))
        btn_container = QFrame(); btn_container.setFixedWidth(scale_size(550)); btn_layout = QVBoxLayout(btn_container); btn_layout.setSpacing(scale_size(20))
        self.btn_create_session = QPushButton("1. LUYỆN TẬP THEO PHIÊN"); self.btn_create_session.setProperty("class", "menu-btn"); self.btn_create_session.setCursor(Qt.PointingHandCursor)
        self.btn_free_practice = QPushButton("2. LUYỆN TẬP TỰ DO"); self.btn_free_practice.setProperty("class", "menu-btn"); self.btn_free_practice.setCursor(Qt.PointingHandCursor)
        self.btn_back_main = QPushButton("◀  VỀ MENU CHÍNH"); self.btn_back_main.setProperty("class", "menu-btn"); self.btn_back_main.setObjectName("danger"); self.btn_back_main.setCursor(Qt.PointingHandCursor)
        btn_layout.addWidget(self.btn_create_session); btn_layout.addWidget(self.btn_free_practice); btn_layout.addSpacing(10); btn_layout.addWidget(self.btn_back_main)
        layout.addWidget(btn_container, 0, Qt.AlignCenter); layout.addStretch()

    def _setup_session_menu(self, parent, scale_size, scale_font):
        layout = QVBoxLayout(parent); layout.setAlignment(Qt.AlignCenter); layout.setSpacing(scale_size(20)); layout.addSpacing(scale_size(60))
        lbl_title = QLabel("LUYỆN TẬP THEO PHIÊN"); lbl_title.setStyleSheet(f"font-size: {scale_font(32)}px; font-weight: bold; color: #ecf0f1;"); lbl_title.setAlignment(Qt.AlignCenter); layout.addWidget(lbl_title)
        layout.addSpacing(scale_size(40))
        btn_container = QFrame(); btn_container.setFixedWidth(scale_size(550)); btn_layout = QVBoxLayout(btn_container); btn_layout.setSpacing(scale_size(20))
        self.btn_new_session = QPushButton("BẮT ĐẦU PHIÊN TẬP MỚI"); self.btn_new_session.setProperty("class", "menu-btn"); self.btn_new_session.setCursor(Qt.PointingHandCursor)
        self.btn_continue_session = QPushButton("TIẾP TỤC PHIÊN TẬP ĐÃ LƯU"); self.btn_continue_session.setProperty("class", "menu-btn"); self.btn_continue_session.setCursor(Qt.PointingHandCursor)
        self.btn_back_dashboard_session = QPushButton("◀  QUAY LẠI"); self.btn_back_dashboard_session.setProperty("class", "menu-btn"); self.btn_back_dashboard_session.setObjectName("danger"); self.btn_back_dashboard_session.setCursor(Qt.PointingHandCursor)
        btn_layout.addWidget(self.btn_new_session); btn_layout.addWidget(self.btn_continue_session); btn_layout.addSpacing(10); btn_layout.addWidget(self.btn_back_dashboard_session)
        layout.addWidget(btn_container, 0, Qt.AlignCenter); layout.addStretch()

    def _setup_create_session_page(self, parent, scale_size, scale_font):
        # Giao diện tạo phiên (sẽ dùng sau)
        main_layout = QVBoxLayout(parent); main_layout.setContentsMargins(scale_size(30), scale_size(30), scale_size(30), scale_size(30)); main_layout.setSpacing(scale_size(20))
        lbl_title = QLabel("THIẾT LẬP PHIÊN TẬP MỚI"); lbl_title.setStyleSheet(f"font-size: {scale_font(24)}px; font-weight: bold; color: #ecf0f1; border-bottom: 2px solid #1abc9c; padding-bottom: 10px;"); main_layout.addWidget(lbl_title)
        content_layout = QHBoxLayout(); content_layout.setSpacing(scale_size(30))
        left_col = QVBoxLayout(); lbl_name = QLabel("Tên phiên tập:"); self.inp_session_name = QLineEdit(); self.inp_session_name.setPlaceholderText("Nhập tên phiên tập...")
        lbl_type = QLabel("Chế độ bắn:"); self.cmb_session_type = QComboBox(); self.cmb_session_type.addItem("Bắn từng phát", "SINGLE"); self.cmb_session_type.addItem("Luyện tập (3 phát)", "BURST_3")
        lbl_list = QLabel("Chọn danh sách chiến sĩ tham gia:"); lbl_hint = QLabel("(Kéo chuột để chọn nhiều)")
        self.list_soldiers_select = QListWidget(); self.list_soldiers_select.setSelectionMode(QAbstractItemView.ExtendedSelection); self.list_soldiers_select.setAlternatingRowColors(True)
        left_col.addWidget(lbl_name); left_col.addWidget(self.inp_session_name); left_col.addSpacing(15); left_col.addWidget(lbl_type); left_col.addWidget(self.cmb_session_type); left_col.addSpacing(15); left_col.addWidget(lbl_list); left_col.addWidget(lbl_hint); left_col.addWidget(self.list_soldiers_select)
        right_col = QVBoxLayout()
        grp_summary = QGroupBox("Thông tin tổng quát"); sum_layout = QFormLayout(grp_summary); self.lbl_sum_date = QLabel("..."); self.lbl_sum_count = QLabel("0 người"); self.lbl_sum_type = QLabel("Bắn từng phát")
        sum_layout.addRow("Ngày:", self.lbl_sum_date); sum_layout.addRow("Số lượng:", self.lbl_sum_count); sum_layout.addRow("Chế độ:", self.lbl_sum_type); right_col.addWidget(grp_summary); right_col.addStretch()
        self.btn_start_session = QPushButton("BẮT ĐẦU LUYỆN TẬP"); self.btn_start_session.setMinimumHeight(scale_size(60))
        self.btn_back_create = QPushButton("QUAY VỀ MENU"); self.btn_back_create.setObjectName("danger"); self.btn_back_create.setMinimumHeight(scale_size(60))
        right_col.addWidget(self.btn_start_session); right_col.addSpacing(10); right_col.addWidget(self.btn_back_create)
        content_layout.addLayout(left_col, 5); content_layout.addLayout(right_col, 5); main_layout.addLayout(content_layout)

    def _setup_practice_view(self, parent, scale_size, scale_font):
        margin = scale_size(20); spacing = scale_size(15)
        root_layout = QVBoxLayout(parent); root_layout.setContentsMargins(margin, scale_size(10), margin, margin); root_layout.setSpacing(spacing)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        self.lbl_session_info = QLabel("LUYỆN TẬP TỰ DO")
        self.lbl_session_info.setStyleSheet(f"font-size: {scale_font(20)}px; font-weight: bold; color: #1abc9c;")
        
        self.shooting_mode_selector = QComboBox()
        self.shooting_mode_selector.addItem("Bắn từng phát", "SINGLE")
        self.shooting_mode_selector.addItem("Luyện tập (3 phát)", "BURST_3")
        self.shooting_mode_selector.setFixedWidth(200)

        self.mode_selector = QComboBox()
        self.mode_selector.addItem("Chế độ 1 Camera")
        self.mode_selector.addItem("Chế độ 2 Camera")
        self.mode_selector.setFixedWidth(200)

        self.back_to_dashboard_btn = QPushButton("Kết thúc")
        self.back_to_dashboard_btn.setObjectName("danger")
        self.back_to_dashboard_btn.setFixedWidth(scale_size(150))

        header_layout.addWidget(self.lbl_session_info)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Chế độ bắn:"))
        header_layout.addWidget(self.shooting_mode_selector)
        header_layout.addWidget(QLabel("Camera:"))
        header_layout.addWidget(self.mode_selector)
        header_layout.addWidget(self.back_to_dashboard_btn)
        
        root_layout.addLayout(header_layout)

        self.main_stack = QStackedWidget()
        root_layout.addWidget(self.main_stack)

        self.page_single = QWidget()
        self._setup_original_single_ui(self.page_single, scale_size, scale_font)
        self.main_stack.addWidget(self.page_single)

        self.page_dual = QWidget()
        self._setup_dual_ui(self.page_dual, scale_size, scale_font)
        self.main_stack.addWidget(self.page_dual)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow_effect = QGraphicsDropShadowEffect(panel)
        shadow_effect.setColor(QColor(0, 0, 0, 80))
        shadow_effect.setOffset(0, 5)
        panel.setGraphicsEffect(shadow_effect)
        return panel

    def _setup_original_single_ui(self, parent, scale_size, scale_font):
        layout = QHBoxLayout(parent); layout.setContentsMargins(0,0,0,0); layout.setSpacing(scale_size(20))
        left_panel = self._create_styled_panel(); left_layout = QVBoxLayout(left_panel)
        title = QLabel("Đường ngắm trực tiếp"); title.setProperty("class", "panel-title"); title.setAlignment(Qt.AlignCenter); left_layout.addWidget(title)
        self.camera_view_label = VideoLabel(); self.camera_view_label.setText("Vui lòng kết nối camera"); left_layout.addWidget(self.camera_view_label, 1)
        
        controls_panel = QWidget(); controls_layout = QHBoxLayout(controls_panel)
        self.single_cam_source = QComboBox(); self.single_cam_source.setMinimumWidth(scale_size(150))
        self.refresh_button = QPushButton("Làm mới"); self.refresh_button.setObjectName("refreshButton")
        self.zoom_slider = QSlider(Qt.Horizontal); self.zoom_slider.setRange(10, 50); self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x"); self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        controls_layout.addWidget(QLabel("Nguồn:")); controls_layout.addWidget(self.single_cam_source); controls_layout.addWidget(self.refresh_button); controls_layout.addStretch(1)
        controls_layout.addWidget(QLabel("Zoom:")); controls_layout.addWidget(self.zoom_slider, 2); controls_layout.addWidget(self.zoom_value_label); controls_layout.addStretch(1); controls_layout.addWidget(self.calibrate_button)
        left_layout.addWidget(controls_panel)
        self.zoom_slider.valueChanged.connect(lambda v: self.zoom_value_label.setText(f"{v/10.0:.1f}x"))

        right_panel = self._create_styled_panel(); right_layout = QVBoxLayout(right_panel)
        session_box = QGroupBox("Quản lý Lần bắn"); session_layout = QVBoxLayout(session_box)
        self.session_button = QPushButton("Bắt đầu"); session_layout.addWidget(self.session_button)
        result_box = QGroupBox("Kết quả mới nhất"); result_layout = QVBoxLayout(result_box)
        self.score_label = QLabel("Điểm số: --"); self.score_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #e74c3c;"); self.score_label.setAlignment(Qt.AlignCenter)
        self.result_image_label = VideoLabel(); result_layout.addWidget(self.score_label); result_layout.addWidget(QLabel("Ảnh kết quả:")); result_layout.addWidget(self.result_image_label, 1)
        right_layout.addWidget(session_box, 2); right_layout.addWidget(result_box, 8)
        layout.addWidget(left_panel, 6); layout.addWidget(right_panel, 4)

    def _setup_dual_ui(self, parent, scale_size, scale_font):
        layout = QHBoxLayout(parent); layout.setContentsMargins(0,0,0,0); layout.setSpacing(scale_size(10))
        def create_vertical_column(title, prefix):
            panel = self._create_styled_panel(); col_layout = QVBoxLayout(panel)
            header_widget = QWidget(); header_lo = QHBoxLayout(header_widget)
            lbl_title = QLabel(title); lbl_title.setProperty("class", "panel-title")
            cmb_source = QComboBox()
            header_lo.addWidget(lbl_title); header_lo.addStretch(); header_lo.addWidget(QLabel("Nguồn:")); header_lo.addWidget(cmb_source); col_layout.addWidget(header_widget)
            btn_session = QPushButton("Bắt đầu"); col_layout.addWidget(btn_session)
            cam_view = VideoLabel(); cam_view.setText(f"Kết nối {title}"); col_layout.addWidget(cam_view, 5) 
            ctrl_widget = QWidget(); ctrl_lo = QHBoxLayout(ctrl_widget)
            btn_refresh = QPushButton("Làm mới"); sld_zoom = QSlider(Qt.Horizontal); sld_zoom.setRange(10,50); sld_zoom.setValue(10); lbl_zoom = QLabel("1.0x")
            sld_zoom.valueChanged.connect(lambda v: lbl_zoom.setText(f"{v/10.0:.1f}x")); btn_calib = QPushButton("Hiệu chỉnh")
            ctrl_lo.addWidget(btn_refresh); ctrl_lo.addWidget(QLabel("Zoom:")); ctrl_lo.addWidget(sld_zoom); ctrl_lo.addWidget(lbl_zoom); ctrl_lo.addWidget(btn_calib); col_layout.addWidget(ctrl_widget)
            grp_res = QGroupBox("Kết quả"); res_lo = QVBoxLayout(grp_res)
            lbl_score = QLabel("Điểm số: --"); lbl_score.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;"); lbl_score.setAlignment(Qt.AlignCenter)
            img_res = VideoLabel(); img_res.setText("Ảnh KQ"); res_lo.addWidget(lbl_score); res_lo.addWidget(img_res, 1); col_layout.addWidget(grp_res, 4)
            
            setattr(self, f"{prefix}_view", cam_view); setattr(self, f"{prefix}_source", cmb_source)
            setattr(self, f"{prefix}_session_btn", btn_session); setattr(self, f"{prefix}_refresh", btn_refresh)
            setattr(self, f"{prefix}_zoom", sld_zoom); setattr(self, f"{prefix}_calib", btn_calib)
            setattr(self, f"{prefix}_score", lbl_score); setattr(self, f"{prefix}_result_img", img_res)
            return panel
        col1 = create_vertical_column("CAMERA 1", "dual_cam1"); col2 = create_vertical_column("CAMERA 2", "dual_cam2")
        layout.addWidget(col1); layout.addWidget(col2)

    def display_frame(self, frame_bgr):
        if frame_bgr is not None: self.camera_view_label.setPixmap(self._convert_cv_to_pixmap(frame_bgr))
    def _convert_cv_to_pixmap(self, cv_img):
        if cv_img is None: return QPixmap()
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB); h, w, ch = rgb.shape
        return QPixmap.fromImage(QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888))
    def clear_video_feed(self, msg):
        empty = QPixmap(); self.camera_view_label.setPixmap(empty); self.camera_view_label.setText(msg)
        if hasattr(self, 'dual_cam1_view'): self.dual_cam1_view.setPixmap(empty); self.dual_cam1_view.setText(msg)
        if hasattr(self, 'dual_cam2_view'): self.dual_cam2_view.setPixmap(empty); self.dual_cam2_view.setText(msg)
    def update_results(self, t, n, s, img):
        self.score_label.setText(f"Điểm số: {s}"); pix = self._convert_cv_to_pixmap(img)
        self.result_image_label.setPixmap(pix if not pix.isNull() else QPixmap()); self.result_image_label.setText("" if not pix.isNull() else "Chưa có ảnh")