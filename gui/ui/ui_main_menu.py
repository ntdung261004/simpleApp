# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QApplication, QGridLayout, QSizePolicy, QHBoxLayout
)

class Ui_MainMenuWindow(object):
    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        
        # --- 1. LOGIC SCALING ---
        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        scale_factor = screen_height / 1080.0

        def scale_size(base_size):
            return max(1, int(base_size * scale_factor))

        def scale_font(base_size):
            return max(8, int(base_size * scale_factor))

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.main_grid = QGridLayout(self.centralwidget)
        self.main_grid.setContentsMargins(0, 0, 0, 0)
        
        # ============================================================
        # LAYER 1: BACKGROUND
        # ============================================================
        self.layer_background = QWidget(self.centralwidget)
        self.layer_background.setObjectName("layer_background")
        bg_layout = QVBoxLayout(self.layer_background)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        
        self.watermark_logo = QLabel(self.layer_background)
        self.watermark_logo.setObjectName("watermark_logo")
        self.watermark_logo.setAlignment(Qt.AlignCenter)
        self.watermark_logo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        bg_layout.addWidget(self.watermark_logo)
        
        self.main_grid.addWidget(self.layer_background, 0, 0, -1, -1)

        # ============================================================
        # LAYER 2: SIDE LOGOS
        # ============================================================
        self.layer_logos = QWidget(self.centralwidget)
        self.layer_logos.setObjectName("layer_logos")
        self.layer_logos.setAttribute(Qt.WA_TransparentForMouseEvents) 
        
        self.logos_layout = QHBoxLayout(self.layer_logos)
        margin_side = scale_size(40)
        self.logos_layout.setContentsMargins(margin_side, margin_side, margin_side, margin_side)
        
        self.left_logo = QLabel(self.layer_logos)
        self.left_logo.setObjectName("left_logo")
        self.left_logo.setAlignment(Qt.AlignLeft | Qt.AlignTop) 
        self.logos_layout.addWidget(self.left_logo)
        
        self.logos_layout.addStretch()
        
        self.right_logo = QLabel(self.layer_logos)
        self.right_logo.setObjectName("right_logo")
        self.right_logo.setAlignment(Qt.AlignRight | Qt.AlignTop) 
        self.logos_layout.addWidget(self.right_logo)

        self.main_grid.addWidget(self.layer_logos, 0, 0, -1, -1)

        # ============================================================
        # LAYER 3: CONTENT
        # ============================================================
        self.layer_content = QWidget(self.centralwidget)
        self.layer_content.setObjectName("layer_content")
        
        self.content_layout = QVBoxLayout(self.layer_content)
        self.content_layout.setContentsMargins(scale_size(40), scale_size(40), scale_size(40), scale_size(30))
        self.content_layout.setSpacing(scale_size(10)) 

        # Tiêu đề trên
        self.customer_title_label = QLabel(self.layer_content)
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        self.customer_title_label.setWordWrap(True)
        self.customer_title_label.setStyleSheet(f"background: transparent; color: #f1c40f; font-size: {scale_font(26)}px; font-weight: bold; letter-spacing: 2px;")
        self.content_layout.addWidget(self.customer_title_label)
        
        self.title_label = QLabel(self.layer_content)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"background: transparent; color: #ecf0f1; font-size: {scale_font(40)}px; font-weight: 700; text-transform: uppercase;")
        self.content_layout.addWidget(self.title_label)

        # Lò xo đệm
        self.content_layout.addStretch(1) 

        # Buttons Container
        buttons_container = QWidget()
        buttons_container.setObjectName("buttons_container")
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setSpacing(scale_size(25))
        buttons_layout.setAlignment(Qt.AlignCenter)
        
        btn_size = QSize(scale_size(480), scale_size(90)) 

        # 1. Practice
        self.practice_button = QPushButton("LUYỆN TẬP", buttons_container)
        self.practice_button.setObjectName("btn_practice")
        self.practice_button.setMinimumSize(btn_size)
        self.practice_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.practice_button)

        # 2. Manage
        self.stats_button = QPushButton("QUẢN LÝ - THỐNG KÊ", buttons_container)
        self.stats_button.setObjectName("btn_manage")
        self.stats_button.setMinimumSize(btn_size)
        self.stats_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.stats_button)

        # 3. Guide
        self.guide_button = QPushButton("HƯỚNG DẪN SỬ DỤNG", buttons_container)
        self.guide_button.setObjectName("btn_guide")
        self.guide_button.setMinimumSize(btn_size)
        self.guide_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.guide_button)

        # 5. Settings
        self.settings_button = QPushButton("CÀI ĐẶT MẬT KHẨU", buttons_container)
        self.settings_button.setObjectName("btn_settings")
        self.settings_button.setMinimumSize(btn_size)
        self.settings_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.settings_button)
        
        # 4. Exit
        self.exit_button = QPushButton("THOÁT CHƯƠNG TRÌNH", buttons_container)
        self.exit_button.setObjectName("btn_exit")
        self.exit_button.setMinimumSize(btn_size)
        self.exit_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.exit_button)

        self.content_layout.addWidget(buttons_container)
        self.content_layout.addStretch(1)

        # Footer
        self.footer_label = QLabel(self.layer_content)
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet(f"background: transparent; color: #ffffff; font-size: {scale_font(26)}px; font-weight: bold;")
        self.content_layout.addWidget(self.footer_label)

        self.main_grid.addWidget(self.layer_content, 0, 0, -1, -1)
        MainMenuWindow.setCentralWidget(self.centralwidget)

        # --- STYLE SHEET ĐỒNG BỘ ---
        MainMenuWindow.setStyleSheet(f"""
            #MainMenuWindow {{
                background-color: #2c3e50;
            }}
            
            /* Đảm bảo toàn bộ các container và nhãn đều trong suốt, không che mất watermark */
            #centralwidget, #layer_background, #layer_logos, #layer_content, #buttons_container, 
            #watermark_logo, #left_logo, #right_logo {{
                background-color: transparent;
            }}
            
            /* Trạng thái bình thường: Nền xanh ngọc đặc, chữ trắng, viền xanh ngọc */
            QPushButton {{
                background-color: #16a085;
                border: 3px solid #16a085;
                color: #ffffff;
                
                border-radius: {scale_size(20)}px;
                padding: {scale_size(10)}px;
                
                font-family: "Segoe UI";
                font-size: {scale_font(26)}px;
                font-weight: 700;
                letter-spacing: 2px;
                border-style: solid;
            }}

            /* Trạng thái Hover: Nền trong suốt, chữ và viền màu xanh ngọc */
            QPushButton:hover {{
                background-color: transparent;
                color: #ffffff;
                border: 3px solid #ffffff;
            }}

            /* Hiệu ứng khi bấm xuống (Pressed) */
            QPushButton:pressed {{
                background-color: rgba(22, 160, 133, 0.2);
                border-color: #16a085;
            }}
        """)