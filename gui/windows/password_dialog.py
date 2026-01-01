# file: gui/windows/password_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QMessageBox, QWidget
)
from PySide6.QtCore import Qt
from utils.password_manager import is_enabled, verify_password, set_password, clear_password, enable_password, disable_password

COMMON_STYLE = """
QDialog { background-color: #34495e; }
QLabel { color: #ecf0f1; font-size: 14px; }
QLineEdit { background-color: #2c3e50; border: 1px solid #4a6278; border-radius: 6px; padding: 8px; color: #ecf0f1; font-size: 14px; }
QPushButton { background-color: #1abc9c; color: white; font-size: 14px; font-weight: bold; border: none; padding: 8px 18px; border-radius: 8px; }
QPushButton:hover { background-color: #16a085; }
QPushButton.secondary { background-color: #95a5a6; }
QPushButton.secondary:hover { background-color: #7f8c8d; }
"""


class PasswordEntryDialog(QDialog):
    """Dialog nhập mật khẩu (đẹp, đồng bộ)"""
    def __init__(self, parent=None, title="Yêu cầu mật khẩu", message="Vui lòng nhập mật khẩu:"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setStyleSheet(COMMON_STYLE)

        layout = QVBoxLayout(self)
        label = QLabel(message)
        layout.addWidget(label)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_ok = QPushButton("Đăng nhập")
        self.btn_cancel = QPushButton("Huỷ")
        self.btn_cancel.setProperty("class", "secondary")
        self.btn_cancel.setStyleSheet("QPushButton.secondary { background-color: #95a5a6; }")

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        layout.addLayout(btn_row)

        self.btn_ok.clicked.connect(self._on_ok)
        self.btn_cancel.clicked.connect(self.reject)

    def _on_ok(self):
        pwd = self.input.text() or ""
        if verify_password(pwd):
            self.accept()
        else:
            QMessageBox.warning(self, "Sai mật khẩu", "Mật khẩu không đúng.")

    @staticmethod
    def get_password(parent=None, title="Yêu cầu mật khẩu", message="Vui lòng nhập mật khẩu:"):
        dlg = PasswordEntryDialog(parent, title, message)
        result = dlg.exec()
        return (dlg.input.text(), result == QDialog.Accepted)


class PasswordManagerDialog(QDialog):
    """Dialog quản lý mật khẩu với UI đồng bộ."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý mật khẩu")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet(COMMON_STYLE)

        self.layout = QVBoxLayout(self)

        self.status_label = QLabel("")
        self.layout.addWidget(self.status_label)

        # Action buttons
        btn_row = QHBoxLayout()
        self.btn_set = QPushButton("Đặt mật khẩu")
        self.btn_change = QPushButton("Đổi mật khẩu")
        self.btn_remove = QPushButton("Xóa mật khẩu")
        self.btn_enable = QPushButton("Bật mật khẩu")
        self.btn_disable = QPushButton("Tắt mật khẩu")
        self.btn_close = QPushButton("Đóng")
        self.btn_close.setProperty("class", "secondary")

        for b in (self.btn_set, self.btn_change, self.btn_remove, self.btn_enable, self.btn_disable):
            btn_row.addWidget(b)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_close)
        self.layout.addLayout(btn_row)

        # Inline area for setting/changing password
        self.form_widget = QWidget()
        form_layout = QVBoxLayout(self.form_widget)
        self.new_input = QLineEdit()
        self.new_input.setEchoMode(QLineEdit.Password)
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(QLabel("Mật khẩu mới:"))
        form_layout.addWidget(self.new_input)
        form_layout.addWidget(QLabel("Xác nhận mật khẩu:"))
        form_layout.addWidget(self.confirm_input)
        save_row = QHBoxLayout()
        self.btn_save = QPushButton("Lưu")
        self.btn_cancel_set = QPushButton("Hủy")
        self.btn_cancel_set.setProperty("class", "secondary")
        save_row.addStretch()
        save_row.addWidget(self.btn_cancel_set)
        save_row.addWidget(self.btn_save)
        form_layout.addLayout(save_row)
        self.layout.addWidget(self.form_widget)

        self.form_widget.setVisible(False)

        # Connections
        self.btn_set.clicked.connect(self._show_set_form)
        self.btn_change.clicked.connect(self._show_set_form)
        self.btn_remove.clicked.connect(self._remove_password)
        self.btn_enable.clicked.connect(self._enable_password)
        self.btn_disable.clicked.connect(self._disable_password)
        self.btn_close.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save_new_password)
        self.btn_cancel_set.clicked.connect(lambda: self.form_widget.setVisible(False))

        self._refresh_status()

    def _refresh_status(self):
        enabled = is_enabled()
        self.status_label.setText("Mật khẩu hiện đang bật." if enabled else "Mật khẩu hiện đang tắt.")
        # Enable/disable buttons sensibly
        self.btn_enable.setEnabled(not enabled)
        self.btn_disable.setEnabled(enabled)
        self.btn_remove.setEnabled(enabled)
        self.btn_change.setEnabled(enabled)

    def _show_set_form(self):
        self.new_input.clear()
        self.confirm_input.clear()
        self.form_widget.setVisible(True)

    def _save_new_password(self):
        p1 = self.new_input.text() or ""
        p2 = self.confirm_input.text() or ""
        if not p1:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu không được để trống.")
            return
        if p1 != p2:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu xác nhận không khớp.")
            return
        set_password(p1)
        QMessageBox.information(self, "Thành công", "Đã lưu mật khẩu mới.")
        self.form_widget.setVisible(False)
        self._refresh_status()

    def _remove_password(self):
        confirm = QMessageBox.question(self, "Xác nhận", "Bạn chắc chắn muốn xóa mật khẩu?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            clear_password()
            QMessageBox.information(self, "Đã xóa", "Mật khẩu đã bị xóa.")
            self._refresh_status()

    def _enable_password(self):
        # Nếu chưa có mật khẩu, yêu cầu đặt ngay
        cfg_enabled = is_enabled()
        if not cfg_enabled:
            QMessageBox.information(self, "Chú ý", "Bạn cần đặt mật khẩu trước khi bật.")
            self._show_set_form()
            return
        enable_password()
        QMessageBox.information(self, "Đã bật", "Mật khẩu đã được bật.")
        self._refresh_status()

    def _disable_password(self):
        confirm = QMessageBox.question(self, "Xác nhận", "Tắt mật khẩu sẽ cho phép truy cập mà không cần mật khẩu. Tiếp tục?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            disable_password()
            QMessageBox.information(self, "Đã tắt", "Mật khẩu đã được tắt.")
            self._refresh_status()

    @staticmethod
    def open(parent=None):
        dlg = PasswordManagerDialog(parent)
        dlg.exec()
