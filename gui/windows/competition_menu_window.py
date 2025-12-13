# file: gui/windows/competition_menu_window.py
from PySide6.QtWidgets import QMainWindow
from ..ui.ui_competition_menu import Ui_CompetitionMenuWindow

class CompetitionMenuWindow(QMainWindow):
    """
    Lớp điều khiển logic cho cửa sổ Menu Thi đấu.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_CompetitionMenuWindow()
        self.ui.setupUi(self)
        
        # Gán các nút từ giao diện vào thuộc tính của lớp để main.py có thể truy cập
        self.start_button = self.ui.start_button
        self.saved_button = self.ui.saved_button
        self.stats_button = self.ui.stats_button
        self.back_button = self.ui.back_button