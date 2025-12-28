# file: gui/ui/ui_guide.py
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QSizePolicy, QApplication
)

class Ui_Guide(object):
    def setupUi(self, GuideWindow):
        GuideWindow.setObjectName("GuideWindow")
        GuideWindow.setStyleSheet("background-color: #2c3e50; color: white;")

        # --- 1. LOGIC SCALING (Đồng bộ với Main Menu) ---
        # Lấy kích thước màn hình hiện tại để tính tỷ lệ
        screen = QApplication.primaryScreen().availableGeometry()
        screen_height = screen.height()
        # Lấy chuẩn 1080p làm gốc. Ví dụ màn 2160p thì factor = 2.0
        scale_factor = screen_height / 1080.0

        def scale_size(base_size):
            """Scale kích thước (width/height/padding/margin)"""
            return max(1, int(base_size * scale_factor))

        def scale_font(base_size):
            """Scale cỡ chữ"""
            return max(8, int(base_size * scale_factor))
        # -----------------------------------------------

        self.verticalLayout = QVBoxLayout(GuideWindow)
        self.verticalLayout.setSpacing(scale_size(10))
        self.verticalLayout.setContentsMargins(scale_size(10), scale_size(10), scale_size(10), scale_size(10))

        # --- 2. HEADER (Nút Quay lại + Tiêu đề) ---
        self.header_frame = QFrame(GuideWindow)
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(scale_size(15))
        
        # Nút Quay lại
        self.btn_back = QPushButton(" QUAY LẠI MENU", self.header_frame)
        self.btn_back.setMinimumSize(QSize(scale_size(180), scale_size(50))) # Tăng kích thước gốc lên chút cho đẹp
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setFont(QFont("Segoe UI", scale_font(14), QFont.Bold))
        self.btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: #e74c3c;
                color: white;
                border-radius: {scale_size(5)}px;
                font-weight: bold;
                border: 1px solid #c0392b;
            }}
            QPushButton:hover {{ background-color: #c0392b; }}
        """)
        
        # Tiêu đề
        self.lbl_title = QLabel("HƯỚNG DẪN SỬ DỤNG PHẦN MỀM", self.header_frame)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setFont(QFont("Segoe UI", scale_font(24), QFont.Bold)) # Font to hơn
        self.lbl_title.setStyleSheet("color: #f1c40f;")

        self.header_layout.addWidget(self.btn_back)
        self.header_layout.addWidget(self.lbl_title)
        self.header_layout.addStretch() 

        self.verticalLayout.addWidget(self.header_frame)

        # --- 3. PDF VIEWER (Khu vực hiển thị nội dung) ---
        self.scroll_area = QScrollArea(GuideWindow)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #34495e; border: none;")
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignCenter)
        self.scroll_layout.setContentsMargins(scale_size(20), scale_size(20), scale_size(20), scale_size(20))
        
        # Label chứa ảnh trang PDF
        self.lbl_page_image = QLabel(self.scroll_content)
        self.lbl_page_image.setAlignment(Qt.AlignCenter)
        self.lbl_page_image.setStyleSheet(f"background-color: white; border: {scale_size(1)}px solid #95a5a6;")
        
        self.scroll_layout.addWidget(self.lbl_page_image)
        self.scroll_area.setWidget(self.scroll_content)
        
        self.verticalLayout.addWidget(self.scroll_area)

        # --- 4. FOOTER (Điều hướng trang) ---
        self.footer_frame = QFrame(GuideWindow)
        self.footer_layout = QHBoxLayout(self.footer_frame)
        self.footer_layout.setSpacing(scale_size(20))
        
        # Nút Trang trước
        self.btn_prev = QPushButton("<< TRANG TRƯỚC", self.footer_frame)
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setMinimumSize(QSize(scale_size(160), scale_size(45)))
        self.btn_prev.setFont(QFont("Segoe UI", scale_font(12), QFont.Bold))
        self.btn_prev.setStyleSheet(f"QPushButton {{ background-color: #3498db; border-radius: {scale_size(5)}px; color: white; }} QPushButton:hover {{ background-color: #2980b9; }}")

        # Số trang
        self.lbl_page_num = QLabel("Trang 0 / 0", self.footer_frame)
        self.lbl_page_num.setAlignment(Qt.AlignCenter)
        self.lbl_page_num.setFont(QFont("Segoe UI", scale_font(14), QFont.Bold))
        self.lbl_page_num.setMinimumWidth(scale_size(150))

        # Nút Trang sau
        self.btn_next = QPushButton("TRANG SAU >>", self.footer_frame)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setMinimumSize(QSize(scale_size(160), scale_size(45)))
        self.btn_next.setFont(QFont("Segoe UI", scale_font(12), QFont.Bold))
        self.btn_next.setStyleSheet(f"QPushButton {{ background-color: #3498db; border-radius: {scale_size(5)}px; color: white; }} QPushButton:hover {{ background-color: #2980b9; }}")

        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.btn_prev)
        self.footer_layout.addWidget(self.lbl_page_num)
        self.footer_layout.addWidget(self.btn_next)
        self.footer_layout.addStretch()

        self.verticalLayout.addWidget(self.footer_frame)