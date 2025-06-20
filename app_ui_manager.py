# app_ui_manager.py
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

class AppUIManager:
    def __init__(self, parent_window):
        self.parent_window = parent_window

    def show_about_dialog(self):
        """'정보' 다이얼로그를 표시합니다."""
        QMessageBox.about(self.parent_window, "자산 관리 프로그램 정보",
                          "<h3>자산 관리 프로그램 v1.0</h3>"
                          "<p>당신의 자산을 효율적으로 관리하도록 돕는 프로그램입니다.</p>"
                          "<p>개발자: Google Gemini</p>"
                          "<p>라이선스: MIT License</p>")

    def open_manual(self):
        """사용 설명서(가정된 URL)를 엽니다."""
        # 실제 사용 설명서 URL 또는 로컬 파일 경로로 변경할 수 있습니다.
        manual_url = "https://www.example.com/asset_manager_manual"
        if not QDesktopServices.openUrl(QUrl(manual_url)):
            QMessageBox.warning(self.parent_window, "오류",
                                "사용 설명서를 열 수 없습니다. URL을 확인해주세요:\n" + manual_url)

