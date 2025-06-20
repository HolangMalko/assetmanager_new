import hashlib
import json
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMessageBox, QLabel, QInputDialog, QCheckBox
from PyQt5.QtCore import Qt, QTimer

class PasswordManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.password_file = "master_password.json"
        self.settings_file = "settings.json"
        self._load_password()
        self._load_settings()

    def _load_password(self):
        """저장된 마스터 비밀번호 해시와 솔트를 로드합니다."""
        if os.path.exists(self.password_file):
            try:
                with open(self.password_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.master_password_hash = data.get('hash')
                    self.salt = data.get('salt')
            except (json.JSONDecodeError, FileNotFoundError):
                self.master_password_hash = None
                self.salt = None
        else:
            self.master_password_hash = None
            self.salt = None

    def _save_password(self):
        """마스터 비밀번호 해시와 솔트를 저장합니다."""
        data = {'hash': self.master_password_hash, 'salt': self.salt}
        with open(self.password_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _generate_hash(self, password, salt):
        """비밀번호와 솔트를 사용하여 SHA256 해시를 생성합니다."""
        hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        return hashed_password

    def is_password_set(self):
        """마스터 비밀번호가 설정되어 있는지 여부를 반환합니다."""
        return self.master_password_hash is not None

    def set_password(self, new_password):
        """새로운 마스터 비밀번호를 설정합니다."""
        self.salt = os.urandom(16).hex() # 새로운 솔트 생성
        self.master_password_hash = self._generate_hash(new_password, self.salt)
        self._save_password()
        return True

    def verify_password(self, input_password):
        """입력된 비밀번호가 마스터 비밀번호와 일치하는지 확인합니다."""
        if not self.is_password_set():
            return False # 비밀번호가 설정되지 않았으면 검증 불가
        
        input_hash = self._generate_hash(input_password, self.salt)
        return input_hash == self.master_password_hash

    def change_password_dialog(self):
        """비밀번호 변경 다이얼로그를 표시합니다."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("비밀번호 변경")
        dialog.setFixedSize(350, 250)
        dialog_layout = QVBoxLayout()

        current_password_input = QLineEdit()
        current_password_input.setEchoMode(QLineEdit.Password)
        current_password_input.setPlaceholderText("현재 비밀번호")
        dialog_layout.addWidget(QLabel("현재 비밀번호:"))
        dialog_layout.addWidget(current_password_input)

        new_password_input = QLineEdit()
        new_password_input.setEchoMode(QLineEdit.Password)
        new_password_input.setPlaceholderText("새 비밀번호")
        dialog_layout.addWidget(QLabel("새 비밀번호:"))
        dialog_layout.addWidget(new_password_input)

        confirm_password_input = QLineEdit()
        confirm_password_input.setEchoMode(QLineEdit.Password)
        confirm_password_input.setPlaceholderText("새 비밀번호 확인")
        dialog_layout.addWidget(QLabel("새 비밀번호 확인:"))
        dialog_layout.addWidget(confirm_password_input)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        ok_button.clicked.connect(lambda: self._perform_password_change(
            current_password_input.text(),
            new_password_input.text(),
            confirm_password_input.text(),
            dialog
        ))
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        dialog_layout.addLayout(buttons_layout)

        dialog.setLayout(dialog_layout)
        dialog.exec_()

    def _perform_password_change(self, current_pass, new_pass, confirm_pass, dialog):
        """실제로 비밀번호 변경을 처리합니다."""
        if not self.verify_password(current_pass):
            QMessageBox.warning(dialog, "오류", "현재 비밀번호가 올바르지 않습니다.")
            return

        if not new_pass:
            QMessageBox.warning(dialog, "오류", "새 비밀번호를 입력해주세요.")
            return

        if new_pass != confirm_pass:
            QMessageBox.warning(dialog, "오류", "새 비밀번호가 일치하지 않습니다.")
            return
        
        if new_pass == current_pass:
            QMessageBox.warning(dialog, "오류", "새 비밀번호는 현재 비밀번호와 달라야 합니다.")
            return

        if self.set_password(new_pass):
            QMessageBox.information(dialog, "성공", "비밀번호가 성공적으로 변경되었습니다.")
            dialog.accept()
        else:
            QMessageBox.critical(dialog, "오류", "비밀번호 변경 중 오류가 발생했습니다.")

    def _load_settings(self):
        """설정 파일에서 자동 잠금 시간 등을 로드합니다."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self.settings = {"auto_lock_minutes": 5} # 기본값
        else:
            self.settings = {"auto_lock_minutes": 5} # 기본값

    def _save_settings(self):
        """설정을 파일에 저장합니다."""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def password_option_dialog(self):
        """비밀번호 옵션(예: 자동 잠금 시간) 설정 다이얼로그를 표시합니다."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("비밀번호 옵션")
        dialog.setFixedSize(300, 150)
        dialog_layout = QVBoxLayout()

        # 자동 잠금 시간 설정 (임시로 QLineEdit 사용, 실제로는 QSpinBox가 더 적합)
        auto_lock_label = QLabel("자동 잠금 시간 (분):")
        self.auto_lock_input = QLineEdit(str(self.settings.get("auto_lock_minutes", 5)))
        self.auto_lock_input.setPlaceholderText("분 단위 (기본: 5분)")
        
        # 부모로부터 validator를 받아와 적용 (LoginDialog에서 설정)
        if hasattr(self.parent, 'auto_lock_validator') and self.parent.auto_lock_validator:
            self.auto_lock_input.setValidator(self.parent.auto_lock_validator)
        
        dialog_layout.addWidget(auto_lock_label)
        dialog_layout.addWidget(self.auto_lock_input)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        ok_button.clicked.connect(lambda: self._save_auto_lock_setting(dialog))
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        dialog_layout.addLayout(buttons_layout)

        dialog.setLayout(dialog_layout)
        dialog.exec_()

    def _save_auto_lock_setting(self, dialog):
        """자동 잠금 시간을 저장합니다."""
        try:
            minutes = int(self.auto_lock_input.text())
            if minutes < 1:
                QMessageBox.warning(dialog, "경고", "자동 잠금 시간은 1분 이상이어야 합니다.")
                return
            self.settings["auto_lock_minutes"] = minutes
            self._save_settings()
            QMessageBox.information(dialog, "설정 저장", "자동 잠금 시간이 저장되었습니다.")
            dialog.accept()
        except ValueError:
            QMessageBox.warning(dialog, "오류", "유효한 숫자를 입력해주세요.")

