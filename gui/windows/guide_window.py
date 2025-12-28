# file: gui/windows/guide_window.py
import os
import fitz  # PyMuPDF
from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, Signal
from gui.ui.ui_guide import Ui_Guide
from utils.resource_path import resource_path
from config import APP_DATA_DIR

class GuideWindow(QWidget):
    # Signal để báo cho MainController biết người dùng muốn quay lại
    request_back_menu = Signal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_Guide()
        self.ui.setupUi(self)
        
        self.doc = None
        self.current_page_index = 0
        self.total_pages = 0

        # Kết nối nút bấm
        self.ui.btn_back.clicked.connect(self.request_back_menu.emit)
        self.ui.btn_prev.clicked.connect(self.prev_page)
        self.ui.btn_next.clicked.connect(self.next_page)
        
        # Tải file PDF
        self.load_pdf()

    def load_pdf(self):
        """Tìm và tải file PDF HDSD"""
        filename = "HDSD.pdf"
        # Ưu tiên tìm trong thư mục assets
        possible_paths = [
            os.path.join(APP_DATA_DIR, "assets", filename),
            os.path.join(APP_DATA_DIR, filename),
            resource_path(os.path.join("assets", filename)),
            resource_path(filename)
        ]
        
        pdf_path = None
        for path in possible_paths:
            if os.path.exists(path):
                pdf_path = path
                break
        
        if pdf_path:
            try:
                self.doc = fitz.open(pdf_path)
                self.total_pages = len(self.doc)
                self.current_page_index = 0
                self.render_current_page()
            except Exception as e:
                self.ui.lbl_page_image.setText(f"Lỗi đọc file PDF:\n{str(e)}")
        else:
            self.ui.lbl_page_image.setText(f"Không tìm thấy file '{filename}' trong thư mục assets.")
            self.ui.btn_next.setEnabled(False)
            self.ui.btn_prev.setEnabled(False)

    def render_current_page(self):
        """Chuyển trang PDF hiện tại thành ảnh và hiển thị"""
        if not self.doc:
            return

        # Cập nhật số trang
        self.ui.lbl_page_num.setText(f"Trang {self.current_page_index + 1} / {self.total_pages}")
        
        # Cập nhật trạng thái nút
        self.ui.btn_prev.setEnabled(self.current_page_index > 0)
        self.ui.btn_next.setEnabled(self.current_page_index < self.total_pages - 1)

        # Render ảnh
        try:
            page = self.doc.load_page(self.current_page_index)
            
            # Zoom = 2.0 để ảnh nét hơn
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            
            # Chuyển đổi từ định dạng của PyMuPDF sang QImage
            # Định dạng mặc định của pixmap là RGB
            img_format = QImage.Format_RGB888
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, img_format)
            
            # Hiển thị lên Label
            self.ui.lbl_page_image.setPixmap(QPixmap.fromImage(image))
            
            # Cuộn lên đầu trang mỗi khi chuyển trang
            self.ui.scroll_area.verticalScrollBar().setValue(0)
            
        except Exception as e:
            print(f"Lỗi render trang: {e}")

    def next_page(self):
        if self.doc and self.current_page_index < self.total_pages - 1:
            self.current_page_index += 1
            self.render_current_page()

    def prev_page(self):
        if self.doc and self.current_page_index > 0:
            self.current_page_index -= 1
            self.render_current_page()