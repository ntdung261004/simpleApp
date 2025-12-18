# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QApplication, QGridLayout, QSizePolicy
)

class Ui_MainMenuWindow(object):
    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        
        # --- LOGIC SCALING ---
        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        scale_factor = screen_height / 1080.0

        def scale_size(base_size):
            return max(1, int(base_size * scale_factor))

        def scale_font(base_size):
            return max(8, int(base_size * scale_factor))
        # ---------------------

        # Stylesheet
        MainMenuWindow.setStyleSheet(f"""
            #MainMenuWindow {{
                background-color: #2c3e50; /* Màu nền dự phòng nếu ảnh chưa load */
            }}
            
            /* --- BUTTON STYLE --- */
            QPushButton {{
                background-color: transparent;
                color: #1abc9c;
                border: 2px solid #1abc9c;
                border-radius: {scale_size(15)}px;
                padding: {scale_size(15)}px;
                font-size: {scale_font(20)}px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: #1abc9c;
                color: #ffffff;
                border: 2px solid #1abc9c;
            }}
            QPushButton:pressed {{
                background-color: #16a085;
                border-color: #16a085;
            }}
            
            /* --- NÚT THOÁT --- */
            QPushButton#exitButton {{
                color: #e74c3c;
                border: 2px solid #e74c3c;
            }}
            QPushButton#exitButton:hover {{
                background-color: #e74c3c;
                color: #ffffff;
                border: 2px solid #e74c3c;
            }}
            QPushButton#exitButton:pressed {{
                background-color: #c0392b;
                border-color: #c0392b;
            }}
        """)

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.main_grid = QGridLayout(self.centralwidget)
        self.main_grid.setContentsMargins(0, 0, 0, 0)
        
        # ============================================================
        # LAYER 1: BACKGROUND FULL SCREEN
        # ============================================================
        self.background_container = QWidget(self.centralwidget)
        
        # Layout căn giữa, không margin để ảnh tràn viền
        bg_layout = QVBoxLayout(self.background_container)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)
        
        self.watermark_logo = QLabel(self.background_container)
        self.watermark_logo.setAlignment(Qt.AlignCenter)
        self.watermark_logo.setScaledContents(False) # Tắt auto-stretch để tránh méo, ta sẽ tự scale
        
        # QUAN TRỌNG: Cho phép Label co giãn tự do, không bị giới hạn
        self.watermark_logo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        bg_layout.addWidget(self.watermark_logo)
        self.main_grid.addWidget(self.background_container, 0, 0, -1, -1)

        # ============================================================
        # LAYER 2: FOREGROUND CONTENT
        # ============================================================
        self.foreground_container = QWidget(self.centralwidget)
        self.foreground_container.setStyleSheet("background: transparent;") 
        
        self.content_layout = QVBoxLayout(self.foreground_container)
        self.content_layout.setContentsMargins(scale_size(40), scale_size(40), scale_size(40), scale_size(30))
        self.content_layout.setSpacing(scale_size(20))

        # Tiêu đề
        self.content_layout.addStretch(1)
        
        self.customer_title_label = QLabel(self.foreground_container)
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        self.customer_title_label.setStyleSheet(f"""
            color: #f1c40f; 
            font-size: {scale_font(24)}px; 
            font-weight: bold;
            letter-spacing: 3px;
        """)
        self.content_layout.addWidget(self.customer_title_label)
        
        self.title_label = QLabel(self.foreground_container)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"""
            color: #ecf0f1; 
            font-size: {scale_font(42)}px; 
            font-weight: 700;
            text-transform: uppercase;
        """)
        self.content_layout.addWidget(self.title_label)

        self.content_layout.addStretch(1)

        # Nút bấm
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setSpacing(scale_size(30))
        buttons_layout.setAlignment(Qt.AlignCenter)

        btn_size = QSize(scale_size(450), scale_size(90))

        self.practice_button = QPushButton("LUYỆN TẬP", buttons_container)
        self.practice_button.setMinimumSize(btn_size)
        self.practice_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.practice_button)

        self.stats_button = QPushButton("QUẢN LÝ - THỐNG KÊ", buttons_container)
        self.stats_button.setMinimumSize(btn_size)
        self.stats_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.stats_button)

        self.exit_button = QPushButton("THOÁT CHƯƠNG TRÌNH", buttons_container)
        self.exit_button.setMinimumSize(btn_size)
        self.exit_button.setCursor(Qt.PointingHandCursor)
        self.exit_button.setObjectName("exitButton")
        buttons_layout.addWidget(self.exit_button)

        self.content_layout.addWidget(buttons_container)
        self.content_layout.addStretch(2)

        # Footer
        self.footer_label = QLabel(self.foreground_container)
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet(f"""
            color: rgba(189, 195, 199, 1); 
            font-size: {scale_font(23)}px;
            font-style: italic;
        """)
        self.content_layout.addWidget(self.footer_label)

        self.main_grid.addWidget(self.foreground_container, 0, 0, -1, -1)
        
        MainMenuWindow.setCentralWidget(self.centralwidget)