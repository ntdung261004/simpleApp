# file: gui/ui/ui_main_menu.py
from PySide6.QtCore import QSize, Qt, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy
)

class ScalableLabel(QLabel):
    """
    Một QLabel tùy chỉnh có khả năng hiển thị QPixmap và tự động
    co giãn hình ảnh để vừa với kích thước của label mà vẫn giữ đúng tỷ lệ.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update() # Yêu cầu vẽ lại widget

    def resizeEvent(self, event):
        self.update()
        super().resizeEvent(event)

    def paintEvent(self, event):
        if not self._pixmap.isNull():
            painter = QPainter(self)
            # Co giãn pixmap để vừa với kích thước label, giữ tỷ lệ, làm mịn ảnh
            scaled_pixmap = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            # Căn giữa pixmap trong label
            point = self.rect().center() - scaled_pixmap.rect().center()
            painter.drawPixmap(point, scaled_pixmap)
        else:
            super().paintEvent(event)


class Ui_MainMenuWindow(object):
    def setupUi(self, MainMenuWindow):
        MainMenuWindow.setObjectName("MainMenuWindow")
        
        MainMenuWindow.setStyleSheet("""
            #MainMenuWindow {
                background-color: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1, 
                                                  stop:0 #34495e, 
                                                  stop:1 #2c3e50);
            }
            QPushButton {
                background-color: #1abc9c;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a085;
            }
            QPushButton:pressed {
                background-color: #148f77;
            }
            QPushButton#exitButton {
                background-color: #e74c3c;
            }
            QPushButton#exitButton:hover {
                background-color: #c0392b;
            }
            QPushButton#exitButton:pressed {
                background-color: #a93226;
            }
        """)

        self.centralwidget = QWidget(MainMenuWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(50, 20, 50, 20)
        self.main_layout.setSpacing(15)

        # === VÙNG HEADER: Chứa 2 logo và tiêu đề ===
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0,0,0,0)
        
        self.logo_left_label = ScalableLabel()
        self.logo_left_label.setMaximumSize(QSize(250, 150))
        
        self.logo_right_label = ScalableLabel()
        self.logo_right_label.setMaximumSize(QSize(250, 150))

        # --- Vùng chứa tiêu đề (giữ nguyên) ---
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)

        self.customer_title_label = QLabel(title_container)
        self.customer_title_label.setAlignment(Qt.AlignCenter)
        customer_font = QFont(); customer_font.setPointSize(20)
        self.customer_title_label.setFont(customer_font)
        self.customer_title_label.setStyleSheet("color: #bdc3c7; margin-bottom: 5px;")
        title_layout.addWidget(self.customer_title_label)
        
        self.title_label = QLabel(title_container)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont(); font.setPointSize(28); font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #ecf0f1;")
        title_layout.addWidget(self.title_label)

        # --- Sắp xếp Header ---
        header_layout.addWidget(self.logo_left_label, 1) # 1 phần không gian
        header_layout.addWidget(title_container, 3)     # 3 phần không gian (ở giữa)
        header_layout.addWidget(self.logo_right_label, 1)# 1 phần không gian
        
        # === VÙNG NÚT BẤM (giữ nguyên) ===
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(15)
        buttons_layout.setAlignment(Qt.AlignCenter)

        self.practice_button = QPushButton("LUYỆN TẬP", buttons_container)
        self.practice_button.setMinimumSize(QSize(350, 75))
        buttons_layout.addWidget(self.practice_button)

        self.stats_button = QPushButton("QUẢN LÝ - THỐNG KÊ", buttons_container)
        self.stats_button.setMinimumSize(QSize(350, 75))
        buttons_layout.addWidget(self.stats_button)

        self.exit_button = QPushButton("ĐÓNG ỨNG DỤNG", buttons_container)
        self.exit_button.setMinimumSize(QSize(350, 75))
        self.exit_button.setObjectName("exitButton")
        buttons_layout.addWidget(self.exit_button)

        # === VÙNG FOOTER: Chứa thông tin thêm ===
        self.footer_label = QLabel()
        self.footer_label.setAlignment(Qt.AlignCenter)
        footer_font = QFont(); footer_font.setPointSize(20)
        self.footer_label.setFont(footer_font)
        self.footer_label.setStyleSheet("color: #bdc3c7; margin-top: 10px;")

        # === SẮP XẾP BỐ CỤC CHÍNH ===
        self.main_layout.addWidget(header_container)
        self.main_layout.addStretch(1)
        self.main_layout.addWidget(buttons_container)
        self.main_layout.addStretch(1)
        self.main_layout.addWidget(self.footer_label)
        
        MainMenuWindow.setCentralWidget(self.centralwidget)