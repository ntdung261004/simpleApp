# gui/user_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QDialogButtonBox, QFormLayout
)
from PySide6.QtCore import Qt

class UserDialog(QDialog):
    """
    Một hộp thoại tùy chỉnh để thêm hoặc chỉnh sửa thông tin người bắn.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý Người bắn")
        self.setMinimumWidth(350)

        # Tạo các ô nhập liệu
        self.name_input = QLineEdit()
        self.unit_input = QLineEdit()
        self.position_input = QLineEdit()

        # Sắp xếp layout theo dạng form cho đẹp mắt
        form_layout = QFormLayout()
        form_layout.addRow("Tên người bắn:", self.name_input)
        form_layout.addRow("Đơn vị:", self.unit_input)
        form_layout.addRow("Chức vụ:", self.position_input)

        # Tạo các nút bấm OK và Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept) # Tín hiệu khi nhấn OK
        button_box.rejected.connect(self.reject) # Tín hiệu khi nhấn Cancel
        
        # Sắp xếp layout chính
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(button_box)

    def get_user_data(self) -> dict:
        """Lấy dữ liệu đã được nhập từ các ô."""
        return {
            'name': self.name_input.text().strip(),
            'unit': self.unit_input.text().strip(),
            'position': self.position_input.text().strip()
        }