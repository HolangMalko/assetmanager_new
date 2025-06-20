import sys
import json
import os
import hashlib
import qtawesome as qta
from datetime import datetime

# PyQt5 위젯 임포트: QHBoxLayout이 여기에 포함되어 있습니다.
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QWidget, QFrame,
    QCheckBox, QCompleter
)
from PyQt5.QtCore import Qt, QTimer, QStringListModel
from PyQt5.QtGui import QFont, QIcon, QPixmap, QIntValidator # QIntValidator 추가

from password_manager import PasswordManager
from main import MainWindow # <--- 'AssetManagerApp' 대신 'MainWindow' 임포트

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("로그인")
        self.setFixedSize(450, 600)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.parent = parent
        
        # QIntValidator 인스턴스 생성 (숫자만 허용)
        # PasswordManager에 이 validator를 전달하여 사용하도록 합니다.
        self.auto_lock_validator = QIntValidator(1, 9999, self) # 1분부터 9999분까지 허용
        self.password_manager = PasswordManager(self) # parent를 self로 전달

        self.init_ui()
        self.load_settings()

        self.update_ui_for_password_status()
        self.password_input.setFocus()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        logo_label = QLabel()
        # 이미지 파일이 존재하고 리소스 시스템에 등록되었다면 해당 경로 사용
        # logo_pixmap = QPixmap(":/icons/icon.png") # 이 경로는 리소스 파일에 의존합니다.
        # 로컬 파일 시스템의 이미지를 사용하려면 다음과 같이 변경:
        # logo_pixmap = QPixmap(os.path.join(os.path.dirname(__file__), 'images', 'icon.png'))
        
        # 이미지 파일이 없거나 경로 문제 시 qtawesome 아이콘 사용
        logo_icon = qta.icon('mdi.lock-outline', options=[{'scale_factor': 2.5, 'color': '#007ACC'}])
        logo_pixmap = logo_icon.pixmap(128, 128) # 더 큰 픽스맵 생성
        
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setPixmap(logo_pixmap)
        main_layout.addWidget(logo_label, alignment=Qt.AlignCenter)

        title_label = QLabel("자산 관리 시스템")
        title_label.setFont(QFont("맑은 고딕", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        password_input_wrapper = QFrame()
        password_input_wrapper.setObjectName("passwordInputWrapper")
        password_input_wrapper.setStyleSheet("""
            #passwordInputWrapper {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: #f8f8f8;
            }
            QLineEdit {
                border: none;
                background-color: transparent;
                font-size: 14pt;
                padding: 5px;
            }
        """)
        password_input_layout = QHBoxLayout(password_input_wrapper)
        password_input_layout.setContentsMargins(0, 0, 0, 0)

        self.password_icon = QLabel()
        self.password_icon.setPixmap(qta.icon('mdi.key', options=[{'scale_factor': 1.2, 'color': '#555'}]).pixmap(24, 24))
        password_input_layout.addWidget(self.password_icon)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("비밀번호를 입력하세요")
        self.password_input.returnPressed.connect(self.accept_login)
        password_input_layout.addWidget(self.password_input)

        self.password_toggle_button = QPushButton()
        self.password_toggle_button.setIcon(qta.icon('mdi.eye-off', options=[{'color': '#555'}]))
        self.password_toggle_button.setFixedSize(30, 30)
        self.password_toggle_button.setStyleSheet("border: none; background: transparent;")
        self.password_toggle_button.clicked.connect(self.toggle_password_visibility)
        password_input_layout.addWidget(self.password_toggle_button)

        main_layout.addWidget(password_input_wrapper)

        self.login_button = QPushButton("로그인")
        self.login_button.setFont(QFont("맑은 고딕", 12, QFont.Bold))
        self.login_button.setMinimumHeight(45)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #005f99;
            }
            QPushButton:pressed {
                background-color: #004c7f;
            }
        """)
        self.login_button.clicked.connect(self.accept_login)
        main_layout.addWidget(self.login_button)

        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)
        options_layout.addStretch(1)

        self.change_password_button = QPushButton("비밀번호 변경")
        self.change_password_button.setIcon(qta.icon('mdi.lock-reset', options=[{'color': '#555'}]))
        self.change_password_button.setStyleSheet("border: none; background: transparent; color: #555;")
        self.change_password_button.clicked.connect(self.password_manager.change_password_dialog)
        options_layout.addWidget(self.change_password_button)

        self.option_button = QPushButton("옵션")
        self.option_button.setIcon(qta.icon('mdi.cog', options=[{'color': '#555'}]))
        self.option_button.setStyleSheet("border: none; background: transparent; color: #555;")
        self.option_button.clicked.connect(self.password_manager.password_option_dialog) # Validator는 PasswordManager 생성 시 전달됨
        options_layout.addWidget(self.option_button)

        options_layout.addStretch(1)
        main_layout.addLayout(options_layout)

        main_layout.addStretch(1)

        self.setLayout(main_layout)

    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.password_toggle_button.setIcon(qta.icon('mdi.eye', options=[{'color': '#555'}]))
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_toggle_button.setIcon(qta.icon('mdi.eye-off', options=[{'color': '#555'}]))

    def update_ui_for_password_status(self):
        if self.password_manager.is_password_set():
            self.password_input.setPlaceholderText("비밀번호를 입력하세요")
            self.login_button.setText("로그인")
            self.change_password_button.setVisible(True)
            self.option_button.setVisible(True)
        else:
            self.password_input.setPlaceholderText("새 마스터 비밀번호를 설정하세요")
            self.login_button.setText("마스터 비밀번호 설정")
            self.change_password_button.setVisible(False)
            self.option_button.setVisible(False)

    def accept_login(self):
        input_password = self.password_input.text()

        if not self.password_manager.is_password_set():
            if not input_password:
                QMessageBox.warning(self, "오류", "마스터 비밀번호를 입력해주세요.")
                return

            reply = QMessageBox.question(self, "마스터 비밀번호 설정",
                                         "입력하신 비밀번호를 마스터 비밀번호로 설정하시겠습니까?\n"
                                         "이 비밀번호는 로그인 및 잠금 해제에 사용됩니다.",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if self.password_manager.set_password(input_password):
                    QMessageBox.information(self, "성공", "마스터 비밀번호가 설정되었습니다.")
                    self.accept()
                else:
                    QMessageBox.critical(self, "오류", "비밀번호 설정 중 오류가 발생했습니다.")
            return

        if self.password_manager.verify_password(input_password):
            self.accept()
        else:
            QMessageBox.warning(self, "로그인 실패", "비밀번호가 올바르지 않습니다.")
            self.password_input.clear()
            self.password_input.setFocus()

    def load_settings(self):
        pass # PasswordManager가 자체적으로 설정을 로드하므로 여기서는 별도 로직 없음

    def closeEvent(self, event):
        if self.result() != QDialog.Accepted:
            QApplication.quit()
        event.accept()

# 메인 실행 부분 (개발 및 테스트용)
if __name__ == '__main__':
    app = QApplication(sys.argv)

    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        # 'main' 모듈에서 'MainWindow' 클래스를 올바르게 임포트합니다.
        from main import MainWindow # <--- 수정된 부분
        main_app = MainWindow()     # <--- 수정된 부분
        main_app.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
