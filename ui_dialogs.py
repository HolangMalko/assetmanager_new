import unicodedata # 한글 문자 판별을 위해 추가
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QDialogButtonBox, QDateEdit, QMessageBox, QLabel, QCompleter,
    QApplication # QApplication 임포트 추가
)
from PyQt5.QtCore import QDate, Qt, QStringListModel, QRegularExpression, pyqtSignal # pyqtSignal 임포트 추가
from PyQt5.QtGui import QFont, QIntValidator, QRegularExpressionValidator, QValidator # QValidator 임포트 추가

import qtawesome as qta
from utils import parse_date_string_to_qdate
from calculator_dialog import CalculatorDialog # 계산기 다이얼로그 임포트

# 한글/한문 15자, 그 외 모든 언어 (영어, 숫자 등) 30자 제한을 위한 커스텀 유효성 검사기 (이제 직접 사용되지 않음)
class CustomDualLengthValidator(QValidator):
    def __init__(self, max_total_chars, max_fullwidth_chars, parent=None):
        super().__init__(parent)
        self.max_total_chars = max_total_chars
        self.max_fullwidth_chars = max_fullwidth_chars

    def is_fullwidth_char(self, char):
        # A more robust check using unicodedata.east_asian_width
        # 'F': Fullwidth, 'W': Wide, 'A': Ambiguous (often treated as wide in CJK context)
        width = unicodedata.east_asian_width(char)
        return width in ('F', 'W', 'A')

    def validate(self, input_str, pos):
        # Allow empty string
        if not input_str:
            return QValidator.Acceptable, input_str, pos

        # 입력 중인 텍스트가 이미 최대 길이를 초과했는지 확인
        total_chars = len(input_str)
        full_width_chars = sum(1 for char in input_str if self.is_fullwidth_char(char))
        
        # 길이가 제한을 초과하면 Invalid 반환
        if total_chars > self.max_total_chars or full_width_chars > self.max_fullwidth_chars:
            return QValidator.Invalid, input_str, pos
        
        # 현재까지 유효하고, 추가 입력이 가능하다면 Acceptable 반환
        # IME 입력 호환성을 위해 Intermediate 대신 Acceptable을 사용
        return QValidator.Acceptable, input_str, pos


# 이 파일 내에서만 사용할 목록 데이터 파일 이름 정의
ASSET_TYPES_FILE = "asset_types.json"
DETAIL_TYPES_FILE = "detail_types.json"
ASSET_NAMES_FILE = "asset_names.json"

class AssetInputDialog(QDialog):
    # 새로운 사용자 정의 시그널 정의
    asset_added_and_continue_signal = pyqtSignal(dict)

    def __init__(self, parent=None, asset_data=None):
        super().__init__(parent)
        print("AssetInputDialog 초기화됨") # 디버깅용 출력
        self.asset_data = asset_data if asset_data else {}
        self.setWindowTitle("자산 정보 입력")
        self.setMinimumWidth(400) # 다이얼로그 최소 너비를 400으로 조정
        self.setFixedSize(400, 450) # 다이얼로그 고정 크기를 400x450으로 설정
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # 콤보박스 목록 데이터 로드 (클래스 초기화 시 한 번 로드)
        self.asset_types_list = self._load_list_data(ASSET_TYPES_FILE, ["현금", "예금/적금", "투자", "부동산", "자동차", "기타"])
        self.detail_types_list = self._load_list_data(DETAIL_TYPES_FILE)
        self.asset_names_list = self._load_list_data(ASSET_NAMES_FILE)

        # 알림 활성화 상태를 위한 내부 변수
        self._alert_enabled = False 
        # '날짜 없음' 상태를 추적하는 새로운 플래그
        self._due_date_cleared_state = False
        self.calc_dialog = None # 계산기 다이얼로그 인스턴스 저장

        self.init_ui()
        self.load_qss("style.qss") # QSS 로드 먼저

        if self.asset_data:
            self.populate_fields()
        else:
            # 새로운 자산을 추가할 때 콤보박스들을 비어있게 설정하여 입력 가능하도록 함
            self.asset_type_combo.setCurrentText("")
            self.detail_type_combo.setCurrentText("")
            self.asset_name_combo.setCurrentText("")
            self.note_input.setText("") # 비고 필드도 새로운 자산일 때 비어있도록 초기화
            self.amount_input.setText("") # 금액 필드도 새로운 자산일 때 비어있도록 초기화
            # 새 자산은 기본적으로 날짜 기록 상태로 시작
            self._due_date_cleared_state = False 
            self.date_status_combo.setCurrentIndex(0) # '날짜 기록'으로 설정


        # UI 초기화 및 데이터 로드 후 최종적으로 알림 UI 상태 업데이트
        self._update_alert_ui_state()
        self._update_date_status_ui() # 초기 로드 시 날짜 상태 UI 업데이트

    def _load_list_data(self, filename, default_items=None):
        """특정 파일에서 목록 데이터를 로드합니다."""
        import json
        import os
        if default_items is None:
            default_items = []
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return default_items

    def _save_list_data(self, filename, data_list):
        """특정 파일에 목록 데이터를 저장합니다."""
        import json
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data_list, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving list data to {filename}: {e}")

    def init_ui(self):
        main_layout = QVBoxLayout()
        # 이전 `main_layout.setContentsMargins` 변경을 제거하여 기본 마진으로 되돌림
        # form_layout의 마진은 10,10,10,10으로 유지
        
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow) 
        form_layout.setContentsMargins(10, 10, 10, 10)
        # 모든 텍스트와 텍스트 박스 수직 간격을 10px로 변경
        form_layout.setVerticalSpacing(10) 
        
        # QToolTip의 duration은 QApplication에서 직접 제어할 수 없습니다.
        # QToolTip의 스타일시트만 여기에 적용됩니다.

        # --- 자산 종류 (Editable ComboBox + Add/Remove Buttons) ---
        self.asset_type_combo = QComboBox()
        self._setup_editable_combo(self.asset_type_combo, self.asset_types_list, ASSET_TYPES_FILE,
                                   placeholder_text="자산 종류를 입력해주세요.") # 플레이스홀더 텍스트 추가
        self.asset_type_combo.setFixedWidth(285) # 너비 285px로 조정 (400px 총 너비에 맞춤)
        form_layout.addRow("자산 종류", self._create_combo_with_buttons( # 콜론 제거
            self.asset_type_combo, self.asset_types_list, ASSET_TYPES_FILE,
            add_tooltip="자산 종류 추가", remove_tooltip="자산 종류 제거" # 툴팁 추가
        ))

        # --- 세부 분류 (Editable ComboBox + Add/Remove Buttons) ---
        self.detail_type_combo = QComboBox()
        self._setup_editable_combo(self.detail_type_combo, self.detail_types_list, DETAIL_TYPES_FILE,
                                   placeholder_text="세부 분류를 입력해주세요.") # 플레이스홀더 텍스트 추가
        self.detail_type_combo.setFixedWidth(285) # 너비 285px로 조정
        form_layout.addRow("세부 분류", self._create_combo_with_buttons( # 콜론 제거
            self.detail_type_combo, self.detail_types_list, DETAIL_TYPES_FILE,
            add_tooltip="세부 분류 추가", remove_tooltip="세부 분류 제거" # 툴팁 추가
        ))

        # --- 자산 명 (Editable ComboBox + Add/Remove Buttons) ---
        self.asset_name_combo = QComboBox()
        self._setup_editable_combo(self.asset_name_combo, self.asset_names_list, ASSET_NAMES_FILE,
                                   placeholder_text="자산 명을 입력해주세요.") # 플레이스홀더 텍스트 추가
        self.asset_name_combo.setFixedWidth(285) # 너비 285px로 조정
        form_layout.addRow("자산 명", self._create_combo_with_buttons( # 콜론 제거
            self.asset_name_combo, self.asset_types_list, ASSET_NAMES_FILE,
            add_tooltip="자산 명 추가", remove_tooltip="자산 명 제거" # 툴팁 추가
        ))

        # --- 금액 (숫자만 입력, 최대 30자, 천 단위 콤마) ---
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("숫자만 입력 (최대 30자리)")
        reg_ex = QRegularExpression(r"^\d{0,30}$") # 숫자 30자리로 변경
        amount_validator = QRegularExpressionValidator(reg_ex, self.amount_input)
        self.amount_input.setValidator(amount_validator)
        self.amount_input.setMaxLength(30) # 숫자 30자리로 변경
        self.amount_input.textChanged.connect(self._format_amount_input)
        self.amount_input.setMinimumHeight(30)
        self.amount_input.setFixedWidth(283) # 너비를 283px로 조정 (400px 총 너비에 맞춤)

        # 계산기 버튼 (아이콘 제거 및 텍스트 버튼으로 변경)
        self.calculator_button = QPushButton("계산기") # 텍스트 "계산기"로 변경
        self.calculator_button.setObjectName("calculatorButton") # QSS 적용을 위한 objectName 설정
        self.calculator_button.setFixedSize(52, 30) # 너비 52px, 높이 30px로 변경
        self.calculator_button.clicked.connect(self._open_calculator)
        
        # 금액 입력 필드와 계산기 버튼을 담는 QHBoxLayout
        amount_input_layout = QHBoxLayout()
        amount_input_layout.setContentsMargins(0,0,0,0)
        amount_input_layout.setSpacing(5) # 금액 필드와 버튼 사이 간격
        amount_input_layout.addWidget(self.amount_input) # stretch 제거, fixed width 사용
        amount_input_layout.addWidget(self.calculator_button)
        amount_input_layout.addStretch(1) # 우측에 여백 추가 (QFormLayout에 의해 왼쪽 정렬될 수 있도록)

        form_layout.addRow("금액", amount_input_layout) # 콜론 제거


        # --- 만기일 (QDateEdit) ---
        self.due_date_input = QDateEdit(QDate.currentDate()) # 기본값: 오늘 날짜
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDisplayFormat("yyyy-MM-dd")
        self.due_date_input.setMinimumHeight(30)
        self.due_date_input.setFixedWidth(116) # 너비를 116px로 조정
        # 만기일이 변경될 때 _due_date_cleared_state를 False로 설정하고 스타일 업데이트
        self.due_date_input.dateChanged.connect(self._on_due_date_changed)

        # --- '날짜 기록' / '날짜 없음' 콤보박스 ---
        self.date_status_combo = QComboBox()
        self.date_status_combo.addItems(["날짜 기록", "날짜 없음"])
        self.date_status_combo.setFixedSize(65, 30) # 너비 65px로 조정
        self.date_status_combo.setObjectName("dateStatusCombo") # QSS 적용을 위한 objectName
        self.date_status_combo.currentIndexChanged.connect(self._on_date_status_combo_changed)


        # 만기일 위젯들을 담는 QHBoxLayout
        date_input_group_layout = QHBoxLayout() 
        date_input_group_layout.setContentsMargins(0,0,0,0)
        date_input_group_layout.setSpacing(9) # 위젯 간 간격 조정 (5 -> 9)
        date_input_group_layout.addWidget(self.due_date_input, alignment=Qt.AlignVCenter)
        # 기존 clear_date_button 대신 date_status_combo 추가
        date_input_group_layout.addWidget(self.date_status_combo, alignment=Qt.AlignVCenter)
        date_input_group_layout.addStretch(1) # 남은 공간을 채우기 위한 스트레치

        # --- 알림 (QComboBox + 종 모양 아이콘) ---
        self.alert_button = QPushButton() # 알림 버튼 생성
        self.alert_button.setFixedSize(30, 30)
        self.alert_button.setStyleSheet("border: none; background: transparent;")
        self.alert_button.clicked.connect(self._toggle_alert_state)

        self.alert_combo = QComboBox() # 알림 콤보박스 생성
        alert_options = ["없음"] + [f"{i}일 전" for i in range(3, 31, 3)]
        self.alert_combo.addItems(alert_options)
        self.alert_combo.setMinimumHeight(30)
        self.alert_combo.setPlaceholderText("알림 기간 선택")
        self.alert_combo.setFixedWidth(80) # 너비 조정

        # 알림 아이콘과 콤보박스를 묶는 QHBoxLayout
        alert_widgets_hbox = QHBoxLayout()
        alert_widgets_hbox.setContentsMargins(0,0,0,0)
        alert_widgets_hbox.setSpacing(5) # 이 간격은 유지 (요청 없었음)
        alert_widgets_hbox.addWidget(self.alert_button, alignment=Qt.AlignVCenter)
        alert_widgets_hbox.addWidget(self.alert_combo, alignment=Qt.AlignVCenter)
        alert_widgets_hbox.addStretch(1)

        # 만기일 그룹과 알림 그룹을 포함하는 메인 QHBoxLayout
        # 스크린샷처럼 "만기일:" 레이블 옆에 필드들이 오고, 그 다음에 "알림:" 레이블과 알림 위젯들이 오도록 구성
        full_date_and_alert_row_layout = QHBoxLayout()
        full_date_and_alert_row_layout.setContentsMargins(0,0,0,0)
        
        # 만기일 위젯 그룹 추가 (stretch=1은 이 그룹이 사용 가능한 공간을 채우도록 함)
        full_date_and_alert_row_layout.addLayout(date_input_group_layout, 1) 
        
        # "날짜 없음" 버튼과 "알림:" 텍스트 사이 간격 조정 (새로운 9px 간격)
        full_date_and_alert_row_layout.addSpacing(20) # 간격을 20px로 변경

        # "알림:" 텍스트 추가 (스크린샷 위치)
        full_date_and_alert_row_layout.addWidget(QLabel("알림")) # 콜론 제거
        
        # "알림:" 텍스트와 종 아이콘 사이 간격 추가 (스크린샷에 따라 이 간격도 조절)
        full_date_and_alert_row_layout.addSpacing(5) # 스크린샷과 유사하게 작은 간격 유지

        # 알림 위젯 그룹 추가 (stretch=1은 이 그룹이 사용 가능한 공간을 채우도록 함)
        full_date_and_alert_row_layout.addLayout(alert_widgets_hbox, 1) 

        form_layout.addRow("만기일", full_date_and_alert_row_layout) # 콜론 제거


        # --- 비고 (LinedEdit) ---
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("추가적인 비고 사항")
        self.note_input.setFixedWidth(285) # 너비 285px로 조정
        form_layout.addRow("비고", self.note_input) # 콜론 제거
        self.note_input.setMinimumHeight(30)

        main_layout.addLayout(form_layout)

        # 간격 추가: 폼 레이아웃과 버튼 박스 사이
        main_layout.addSpacing(20) 

        # OK, Cancel, Apply(추가입력) 버튼을 가운데로 이동
        # QDialogButtonBox 대신 개별 QPushButton을 사용하여 순서 제어
        self.add_more_button = QPushButton("추가입력")
        self.add_more_button.setIcon(qta.icon('mdi.plus-circle-outline'))
        self.add_more_button.clicked.connect(self._add_more_asset)
        
        self.ok_button = QPushButton("확인") 
        self.ok_button.setIcon(qta.icon('mdi.check'))
        self.ok_button.clicked.connect(self.accept_data)

        self.cancel_button = QPushButton("취소") 
        self.cancel_button.setIcon(qta.icon('mdi.close'))
        self.cancel_button.clicked.connect(self.reject) # self.reject 호출

        # 버튼 박스를 중앙 정렬하기 위한 QHBoxLayout
        button_layout = QHBoxLayout()
        button_layout.addStretch(1) # 왼쪽 여백
        button_layout.addWidget(self.add_more_button)
        button_layout.addSpacing(30) # "추가입력"과 "확인" 사이 간격 30px로 변경
        button_layout.addWidget(self.ok_button)
        button_layout.addSpacing(4) # "확인"과 "취소" 사이 간격 4px로 변경 (절반으로 줄임)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch(1) # 오른쪽 여백
        
        main_layout.addLayout(button_layout) # 메인 레이아웃에 버튼 레이아웃 추가

        self.setLayout(main_layout)
        self.amount_input.setFocus()

    def _format_amount_input(self):
        """금액 입력 필드의 숫자를 천 단위로 포맷하고, 커서 위치를 유지합니다."""
        line_edit = self.amount_input
        original_text = line_edit.text()
        original_cursor_pos = line_edit.cursorPosition()

        # 기존 콤마 제거 및 숫자만 추출
        cleaned_text = original_text.replace(',', '')
        
        # 숫자만 허용하는 유효성 검사기가 있지만, 혹시 모를 경우를 대비해 필터링
        if not cleaned_text.isdigit() and cleaned_text != "": 
            cleaned_text = "".join(filter(str.isdigit, cleaned_text))
            
        if not cleaned_text:
            # 텍스트가 완전히 비워지면 포맷팅 없이 빈 문자열로 설정
            line_edit.blockSignals(True)
            line_edit.setText("")
            line_edit.blockSignals(False)
            return

        try:
            amount = int(cleaned_text)
            formatted_text = f"{amount:,.0f}"
        except ValueError:
            # 숫자로 변환할 수 없는 경우 (유효성 검사기가 대부분 막겠지만)
            # 여기서는 원본 텍스트 (콤마 없는)를 유지
            line_edit.blockSignals(True)
            line_edit.setText(cleaned_text)
            line_edit.blockSignals(False)
            return

        # 텍스트 변경으로 인한 커서 위치 보정
        new_cursor_pos = original_cursor_pos
        # 원본 텍스트의 커서 이전 위치에 있던 콤마 개수
        old_commas_before_cursor = original_text[:original_cursor_pos].count(',')
        
        # 포맷된 텍스트에서 커서 이전 위치에 새로 생긴 콤마 개수
        # cleaned_text 길이 + old_commas_before_cursor는 대략적인 새 텍스트에서의 위치
        # 이 위치까지의 콤마 개수를 세서 실제 커서 위치를 조정
        temp_string_for_new_commas = formatted_text[:len(cleaned_text) + old_commas_before_cursor + 5] # 여유 있게
        new_commas_in_formatted = temp_string_for_new_commas.count(',')

        # 커서 위치 조정 로직
        # 숫자만 있는 텍스트에서의 커서 위치를 기준으로 포맷된 텍스트에서의 실제 커서 위치를 계산
        new_cursor_pos_adjusted = 0
        cleaned_idx = 0
        for char_idx, char in enumerate(formatted_text):
            if char == ',':
                if cleaned_idx <= len(cleaned_text): # 숫자가 끝나기 전의 콤마만 고려
                    new_cursor_pos_adjusted += 1 # 콤마만큼 커서 위치 이동
            else:
                cleaned_idx += 1
            
            # 원본 커서 위치의 숫자 개수에 도달하면 정지
            if cleaned_idx == len(original_text[:original_cursor_pos].replace(',', '')):
                new_cursor_pos_adjusted += formatted_text[:char_idx].count(',') - original_text[:original_cursor_pos].count(',') # 보정
                new_cursor_pos_adjusted = char_idx + 1 # 실제 포맷된 문자열의 인덱스
                break
        else: # 루프가 끝까지 돌면, 커서가 텍스트 맨 끝에 있었음을 의미
            new_cursor_pos_adjusted = len(formatted_text)

        # 예외 처리: 원래 커서가 텍스트 맨 앞이었을 때
        if original_cursor_pos == 0:
            new_cursor_pos_adjusted = 0
        # 예외 처리: 원래 커서가 텍스트 맨 끝이었을 때 (혹시 위의 로직이 제대로 못 잡을 경우)
        elif original_cursor_pos == len(original_text):
            new_cursor_pos_adjusted = len(formatted_text)
        elif original_cursor_pos < len(original_text):
            # 중간 위치 보정: 콤마 추가/제거에 따른 상대적인 커서 위치 조정
            # cleaned_text의 커서 이전 길이
            non_comma_len_before_cursor_original = len(original_text[:original_cursor_pos].replace(',', ''))
            
            # formatted_text에서 해당 길이까지의 콤마 포함 길이 계산
            new_adjusted_pos = 0
            current_non_comma_count = 0
            for char in formatted_text:
                if current_non_comma_count == non_comma_len_before_cursor_original: 
                    break
                if char != ',':
                    current_non_comma_count += 1
                new_adjusted_pos += 1
            new_cursor_pos_adjusted = new_adjusted_pos
            
        # 실제 텍스트 적용 (무한 루프 방지를 위해 시그널 잠시 차단)
        line_edit.blockSignals(True)
        line_edit.setText(formatted_text)
        line_edit.blockSignals(False)
        
        # 커서 위치 설정
        line_edit.setCursorPosition(min(new_cursor_pos_adjusted, len(formatted_text)))

    def _open_calculator(self):
        """
        계산기 다이얼로그를 열고 계산 결과를 금액 입력 필드에 적용합니다.
        계산기 버튼을 다시 누르면 계산기를 닫습니다.
        """
        if self.calc_dialog and self.calc_dialog.isVisible():
            # 계산기가 이미 열려 있으면 닫기
            self.calc_dialog.close()
            self.calc_dialog = None
        else:
            # 새로운 계산기 열기
            current_amount = self.amount_input.text().replace(',', '')
            self.calc_dialog = CalculatorDialog(self, initial_value=current_amount)

            # 계산기 다이얼로그를 비모달로 설정하고 항상 위에 뜨도록 함
            self.calc_dialog.setWindowFlags(Qt.Window | Qt.Tool) 

            # 계산기 다이얼로그를 현재 다이얼로그의 오른쪽에 배치
            parent_pos = self.pos()
            parent_width = self.width()
            self.calc_dialog.move(parent_pos.x() + parent_width, parent_pos.y())

            # 계산기 다이얼로그의 accepted 시그널 연결 (OK 버튼 클릭 시)
            self.calc_dialog.accepted.connect(self._handle_calculator_result)
            # 계산기 다이얼로그가 닫힐 때 (OK/Cancel/Esc) 호출될 시그널 연결
            self.calc_dialog.finished.connect(self._handle_calculator_finished)

            self.calc_dialog.show()

    def _handle_calculator_result(self):
        """계산기 다이얼로그에서 결과를 받아 금액 입력 필드에 적용합니다."""
        if self.calc_dialog:
            calculated_value = self.calc_dialog.get_result()
            if calculated_value:
                self.amount_input.setText(calculated_value)
            # 계산기 다이얼로그는 _handle_calculator_finished에서 None으로 설정됨

    def _handle_calculator_finished(self):
        """계산기 다이얼로그가 닫힐 때 호출되어 calc_dialog 참조를 None으로 설정합니다."""
        print("Calculator dialog finished.")
        self.calc_dialog = None

    def closeEvent(self, event):
        """
        다이얼로그가 닫힐 때 계산기 다이얼로그가 열려 있으면 함께 닫습니다.
        """
        if self.calc_dialog and self.calc_dialog.isVisible():
            self.calc_dialog.close()
            self.calc_dialog = None
        super().closeEvent(event) # 부모 클래스의 closeEvent 호출

    def reject(self):
        """
        취소 버튼 클릭 시 계산기 다이얼로그가 열려 있으면 함께 닫고 다이얼로그를 거부합니다.
        """
        if self.calc_dialog and self.calc_dialog.isVisible():
            self.calc_dialog.close()
            self.calc_dialog = None
        super().reject() # 부모 클래스의 reject 호출


    def _toggle_alert_state(self):
        """알림 활성화/비활성화를 토글하고 UI를 업데이트합니다."""
        self._alert_enabled = not self._alert_enabled
        self._update_alert_ui_state()

    def _update_alert_ui_state(self):
        """알림 활성화 상태에 따라 아이콘 및 콤보박스 상태를 업데이트합니다."""
        if self._alert_enabled:
            self.alert_button.setIcon(qta.icon('mdi.bell', options=[{'color': '#4CAF50'}])) # 활성화 시 초록색 종
            self.alert_combo.setEnabled(True)
            # "없음"으로 설정되어 있었다면 "3일 전"으로 변경 (선택 사항)
            if self.alert_combo.currentText() == "없음" and self.alert_combo.count() > 1:
                self.alert_combo.setCurrentIndex(1) 
        else:
            self.alert_button.setIcon(qta.icon('mdi.bell-off', options=[{'color': '#999999'}])) # 비활성화 시 회색 종
            self.alert_combo.setEnabled(False)
            self.alert_combo.setCurrentText("없음") # 비활성화 시 "없음"으로 강제 설정

    def _on_due_date_changed(self, date):
        """QDateEdit의 날짜가 변경될 때 호출됩니다 (사용자가 캘린더에서 직접 날짜를 선택할 때)."""
        # QDateEdit의 날짜가 변경되면 '날짜 기록' 상태로 간주합니다.
        if date != QDate(1, 1, 2000):
            self._due_date_cleared_state = False
            # 콤보박스의 currentIndexChanged 시그널을 잠시 차단하여 불필요한 재귀 호출 방지
            self.date_status_combo.blockSignals(True)
            self.date_status_combo.setCurrentIndex(0) # "날짜 기록" 선택
            self.date_status_combo.blockSignals(False)
        else: # 캘린더에서 1/1/2000을 직접 선택한 경우 (매우 드물지만 가능성 있음)
            self._due_date_cleared_state = True
            self.date_status_combo.blockSignals(True)
            self.date_status_combo.setCurrentIndex(1) # "날짜 없음" 선택
            self.date_status_combo.blockSignals(False)
        self._update_date_status_ui()


    def _on_date_status_combo_changed(self, index):
        """'날짜 기록' / '날짜 없음' 콤보박스의 선택이 변경될 때 호출됩니다."""
        if index == 1: # "날짜 없음" 선택됨
            print("날짜 없음 콤보박스 선택 감지됨!") # 디버깅용 출력
            self._due_date_cleared_state = True
            self.due_date_input.setEnabled(False) # QDateEdit 비활성화
            
            # QDateEdit의 dateChanged 시그널을 임시 차단하고 날짜를 1/1/2000으로 설정
            self.due_date_input.blockSignals(True)
            self.due_date_input.setDate(QDate(1, 1, 2000))
            self.due_date_input.blockSignals(False)

        else: # index == 0, "날짜 기록" 선택됨
            print("날짜 기록 콤보박스 선택 감지됨!") # 디버깅용 출력
            self._due_date_cleared_state = False
            self.due_date_input.setEnabled(True) # QDateEdit 활성화
            
            # 만약 현재 QDateEdit의 날짜가 1/1/2000 이면 오늘 날짜로 재설정
            if self.due_date_input.date() == QDate.currentDate():
                self.due_date_input.blockSignals(True)
                self.due_date_input.setDate(QDate.currentDate())
                self.due_date_input.blockSignals(False)

        self._update_date_status_ui() # 콤bo_box 선택에 따라 UI 업데이트 강제
        QApplication.processEvents() # 이벤트 즉시 처리하여 UI 업데이트 강제


    def _update_date_status_ui(self):
        """날짜 상태에 따라 콤보박스 및 QDateEdit의 스타일을 업데이트합니다."""
        is_date_cleared = self._due_date_cleared_state 
        print(f"DEBUG: _update_date_status_ui called. Internal cleared state: {is_date_cleared}")
        
        # 콤보박스의 스타일을 직접 설정합니다.
        if is_date_cleared:
            self.date_status_combo.setStyleSheet("""
                #dateStatusCombo {
                    background-color: #D3D3D3; /* 어두운 회색 배경 (날짜 없음 상태) */
                    border: 1px solid #A9A9A9; /* 어두운 회색 테두리 */
                    border-radius: 5px;
                }
                #dateStatusCombo::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 0px; /* 드롭다운 화살표 제거 */
                    border-left-width: 0px; /* 드롭다운 왼쪽 테두리 제거 */
                    border-left-style: solid; /* just to make sure */
                    border-top-right-radius: 3px;
                    border-bottom-right-radius: 3px;
                }
            """)
            self.due_date_input.setEnabled(False) # 날짜 없음 상태일 때 QDateEdit 비활성화
        else:
            self.date_status_combo.setStyleSheet("""
                #dateStatusCombo {
                    background-color: #FFFFFF; /* 흰색 배경 (날짜 기록 상태 - 색 없음) */
                    border: 1px solid #BDBDBD; /* 기본 회색 테두리 */
                    border-radius: 5px;
                }
                #dateStatusCombo::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 0px; /* 드롭다운 화살표 제거 */
                    border-left-width: 0px; /* 드롭다운 왼쪽 테두리 제거 */
                    border-left-style: solid; /* just to make sure */
                    border-top-right-radius: 3px;
                    border-bottom-right-radius: 3px;
                }
            """)
            self.due_date_input.setEnabled(True) # 날짜 기록 상태일 때 QDateEdit 활성화
        
        self.date_status_combo.setProperty("date-cleared", "true" if is_date_cleared else "false")
        self.date_status_combo.style().polish(self.date_status_combo) # 스타일 업데이트 강제 적용
        print(f"DEBUG: 'dateStatusCombo' style updated. Is cleared (from internal flag): {is_date_cleared}. Property: {self.date_status_combo.property('date-cleared')}")


    def _setup_editable_combo(self, combo_box, data_list, filename, placeholder_text=""): # placeholder_text 인자 추가
        """편집 가능한 콤보박스를 설정하고 초기 데이터를 채웁니다."""
        combo_box.setEditable(True)
        combo_box.addItems(data_list)
        combo_box.setMinimumHeight(30)
        combo_box.lineEdit().setPlaceholderText(placeholder_text) # 플레이스홀더 텍스트 설정
        
        # 명시적으로 유효성 검사기 제거
        combo_box.lineEdit().setValidator(None) # <--- 이 줄이 추가/수정되었습니다.
        
        # 자동 완성 기능 추가
        completer = QCompleter(combo_box)
        combo_box.setCompleter(completer)
        model = QStringListModel()
        model.setStringList(data_list)
        completer.setModel(model)
        
        # 콤보박스의 에디터 (QLineEdit) 변경 감지 시 목록에 추가
        # 사용자가 직접 타이핑 후 포커스를 잃었을 때 (또는 Enter) 목록에 자동 추가
        combo_box.lineEdit().editingFinished.connect(lambda: self._add_item_on_edit_finish(combo_box, data_list, filename))

    def _create_combo_with_buttons(self, combo_box, data_list, filename, add_tooltip="", remove_tooltip=""):
        """콤보박스와 +/- 버튼을 포함하는 QHBoxLayout을 생성합니다."""
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0,0,0,0)
        hbox.addWidget(combo_box, 1) # 콤보박스가 공간을 더 차지하도록 stretch

        add_button = QPushButton(qta.icon('mdi.plus'), "")
        add_button.setFixedSize(30, 30)
        add_button.clicked.connect(lambda: self._add_item_to_combo(combo_box, data_list, filename))
        add_button.setToolTip(add_tooltip) # 툴팁 설정
        hbox.addWidget(add_button)

        remove_button = QPushButton(qta.icon('mdi.minus'), "")
        remove_button.setFixedSize(30, 30)
        remove_button.clicked.connect(lambda: self._remove_item_from_combo(combo_box, data_list, filename))
        remove_button.setToolTip(remove_tooltip) # 툴팁 설정
        hbox.addWidget(remove_button)

        return hbox

    def _add_item_on_edit_finish(self, combo_box, data_list, filename):
        """콤보박스 에디터의 편집이 끝났을 때 항목을 목록에 추가하고 저장합니다."""
        text = combo_box.lineEdit().text().strip()
        if text and text not in data_list:
            data_list.append(text)
            data_list.sort()
            self._update_combo_items(combo_box, data_list)
            self._save_list_data(filename, data_list)
            # 새로 추가된 항목이 자동으로 선택되도록 설정
            combo_box.setCurrentText(text)


    def _add_item_to_combo(self, combo_box, data_list, filename):
        """콤보박스의 현재 텍스트를 목록에 추가하고 저장합니다."""
        text = combo_box.currentText().strip()
        if text and text not in data_list:
            data_list.append(text)
            data_list.sort()
            self._update_combo_items(combo_box, data_list)
            self._save_list_data(filename, data_list)
            combo_box.setCurrentText(text)
            QMessageBox.information(self, "항목 추가", f"'{text}' 항목이 추가되었습니다.")
        elif text in data_list:
            QMessageBox.information(self, "항목 추가", f"'{text}' 항목은 이미 존재합니다.")
        else:
            QMessageBox.warning(self, "항목 추가", "추가할 항목을 입력하거나 선택해주세요.")

    def _remove_item_from_combo(self, combo_box, data_list, filename):
        """콤보박스에서 현재 텍스트에 해당하는 항목을 목록에서 제거하고 저장합니다."""
        text_to_remove = combo_box.currentText().strip()
        if text_to_remove and text_to_remove in data_list:
            reply = QMessageBox.question(self, "항목 삭제 확인",
                                         f"'{text_to_remove}' 항목을 목록에서 정말로 삭제하시겠습니까?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                data_list.remove(text_to_remove)
                self._update_combo_items(combo_box, data_list)
                self._save_list_data(filename, data_list)
                combo_box.setCurrentIndex(-1)
                combo_box.lineEdit().setText("") # 삭제 후 텍스트 필드 비우기
                combo_box.setPlaceholderText("항목을 선택하거나 입력하세요")
                QMessageBox.information(self, "항목 삭제", f"'{text_to_remove}' 항목이 삭제되었습니다.")
        elif not text_to_remove:
            QMessageBox.warning(self, "항목 삭제", "삭제할 항목을 입력하거나 선택해주세요.")
        else:
            QMessageBox.warning(self, "항목 삭제", f"'{text_to_remove}' 항목은 목록에 없습니다.")

    def _update_combo_items(self, combo_box, data_list):
        """콤보박스의 항목들을 최신 데이터 리스트로 업데이트합니다."""
        current_text = combo_box.currentText()
        combo_box.clear()
        combo_box.addItems(data_list)
        if current_text in data_list:
            combo_box.setCurrentText(current_text)
        else:
            combo_box.setCurrentIndex(-1)
            combo_box.lineEdit().setText(current_text)


    def load_qss(self, filename):
        """QSS 파일을 로드하여 다이얼로그에 적용합니다."""
        import os
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                qss_content = f.read()
            # QSS 파일 내용과 함께 '날짜 상태' 콤보박스의 스타일을 추가합니다.
            qss_content += """
            #dateStatusCombo {
                /* 초기 로드 시 코드에서 덮어쓰기 예정이지만, 기본 정의 */
                background-color: #FFFFFF; 
                border: 1px solid #BDBDBD; 
                border-radius: 5px;
                padding: 0 5px; /* 텍스트와 테두리 간격 */
            }
            #dateStatusCombo::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 0px; /* 드롭다운 화살표 제거 */
                    border-left-width: 0px; /* 드롭다운 왼쪽 테두리 제거 */
                    border-left-style: solid; /* just to make sure */
                    border-top-right-radius: 3px;
                    border-bottom-right-radius: 3px;
                }
                #dateStatusCombo QAbstractItemView {
                    border: 1px solid #A9A9A9;
                    selection-background-color: #007ACC;
                }
                /* QToolTip 스타일 추가: 모든 QToolTip에 전역적으로 적용됩니다. */
                QToolTip {
                    background-color: white;
                    color: black;
                    border: 1px solid #767676;
                    border-radius: 4px;
                    padding: 4px;
                }
                """
            # QApplication.instance().setStyleSheet()를 사용하여 전역 스타일을 설정합니다.
            # 이 스타일은 모든 QToolTip에 적용되어야 합니다.
            if QApplication.instance(): # QApplication 인스턴스가 존재하는지 확인
                QApplication.instance().setStyleSheet(qss_content)
            else:
                print("Error: QApplication instance not available. Cannot set global stylesheet.")
        except FileNotFoundError:
            print(f"Error: '{filename}' not found for dialog. Applying default QSS for combo box and tooltip.")
            # Fallback for when file is not found
            default_qss = """
            #dateStatusCombo {
                background-color: #FFFFFF; 
                border: 1px solid #BDBDBD; 
                border-radius: 5px;
                padding: 0 5px;
            }
            #dateStatusCombo::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 0px;
                border-left-width: 0px;
                border-left-style: solid;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }
            #dateStatusCombo QAbstractItemView {
                border: 1px solid #A9A9A9;
                selection-background-color: #007ACC;
            }
            QToolTip {
                background-color: white;
                color: black;
                border: 1px solid #767676;
                border-radius: 4px;
                padding: 4px;
            }
            """
            if QApplication.instance():
                QApplication.instance().setStyleSheet(default_qss)
            else:
                print("Error: QApplication instance not available. Cannot set default global stylesheet.")
        except Exception as e:
            print(f"Error loading QSS file for dialog: {e}. Applying default QSS for combo box and tooltip.")
            # Fallback for other exceptions
            default_qss = """
            #dateStatusCombo {
                background-color: #FFFFFF; 
                border: 1px solid #BDBDBD; 
                border-radius: 5px;
                padding: 0 5px;
            }
            #dateStatusCombo::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 0px;
                border-left-width: 0px;
                border-left-style: solid;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }
            #dateStatusCombo QAbstractItemView {
                border: 1px solid #A9A9A9;
                selection-background-color: #007ACC;
            }
            QToolTip {
                background-color: white;
                color: black;
                border: 1px solid #767676;
                border-radius: 4px;
                padding: 4px;
            }
            """
            if QApplication.instance():
                QApplication.instance().setStyleSheet(default_qss)
            else:
                print("Error: QApplication instance not available. Cannot set default global stylesheet.")


    def populate_fields(self):
        """기존 자산 데이터로 필드를 채웁니다."""
        self.asset_type_combo.setCurrentText(self.asset_data.get('자산 종류', ''))
        self.detail_type_combo.setCurrentText(self.asset_data.get('세부 분류', ''))
        self.asset_name_combo.setCurrentText(self.asset_data.get('자산 명', ''))
        
        # 금액 필드 채우기 및 포맷 적용
        amount_raw = self.asset_data.get('금액', '')
        if amount_raw is not None and amount_raw != '':
            self.amount_input.setText(str(amount_raw))
            self._format_amount_input() # 로드 후 포맷 적용
        else:
            self.amount_input.setText("")
        
        due_date_str = self.asset_data.get('만기일', '')
        if due_date_str:
            date_qdate = parse_date_string_to_qdate(due_date_str)
            if date_qdate:
                self.due_date_input.blockSignals(True) # 시그널 블록
                self.due_date_input.setDate(date_qdate)
                self.due_date_input.blockSignals(False) # 시그널 블록 해제
                self._due_date_cleared_state = False # 날짜가 있으면 클리어 상태 아님
                self.date_status_combo.setCurrentIndex(0) # "날짜 기록" 선택
            else:
                self.due_date_input.blockSignals(True) # 시그널 블록
                self.due_date_input.setDate(QDate(1, 1, 2000))
                self.due_date_input.blockSignals(False) # 시그널 블록 해제
                self._due_date_cleared_state = True # 날짜 파싱 실패 시 클리어 상태
                self.date_status_combo.setCurrentIndex(1) # "날짜 없음" 선택
        else:
            self.due_date_input.blockSignals(True) # 시그널 블록
            self.due_date_input.setDate(QDate(1, 1, 2000)) # '날짜 없음'의 의미로 설정
            self.due_date_input.blockSignals(False) # 시그널 블록 해제
            self._due_date_cleared_state = True # 날짜가 없으면 클리어 상태
            self.date_status_combo.setCurrentIndex(1) # "날짜 없음" 선택


        # 알림 콤보박스 및 토글 상태 초기화
        alert_value = self.asset_data.get('알림', '없음')
        self._alert_enabled = (alert_value != "없음" and alert_value != "") # '없음'이 아니거나 비어있지 않으면 활성화
        self.alert_combo.setCurrentText(alert_value)

        self.note_input.setText(self.asset_data.get('비고', ''))
        
        self._update_date_status_ui() # populate_fields 호출 후 날짜 상태 UI 업데이트

    def accept_data(self):
        """입력 데이터 유효성 검사 후 다이얼로그를 수락합니다."""
        # 필수 필드 검사
        asset_type = self.asset_type_combo.currentText().strip()
        asset_name = self.asset_name_combo.currentText().strip()
        amount_text = self.amount_input.text().replace(',', '').strip() # 금액은 콤마 제거 후 검사

        if not asset_type:
            QMessageBox.warning(self, "입력 오류", "자산 종류는 필수로 입력하거나 선택해야 합니다.")
            return
        if not asset_name:
            QMessageBox.warning(self, "입력 오류", "자산 명은 필수로 입력하거나 선택해야 합니다.")
            return
        if not amount_text: # 금액 입력 필드가 비어있으면 오류
            QMessageBox.warning(self, "입력 오류", "금액은 필수로 입력해야 합니다.")
            return
        
        # 금액 유효성 검사 및 변환
        try:
            amount = int(amount_text)
            if amount < 0:
                QMessageBox.warning(self, "입력 오류", "금액은 음수가 될 수 없습니다.")
                return
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "금액은 유효한 숫자로 입력해야 합니다.")
            return
        
        # 확인 버튼 클릭 시 계산기 UI가 떠 있으면 함께 닫습니다.
        if self.calc_dialog and self.calc_dialog.isVisible():
            self.calc_dialog.close()
            self.calc_dialog = None

        # 모든 검사를 통과하면 accept() 호출
        # 데이터를 MainWindow로 전달하는 부분은 _add_more_asset 또는 main_window의 open_asset_input_dialog에서 처리되므로,
        # 여기서는 단순히 다이얼로그를 닫습니다.
        self.accept()

    def _add_more_asset(self):
        """
        '추가입력' 버튼 클릭 시 호출됩니다.
        현재 자산 데이터를 전송하고, 금액과 비고 필드를 초기화하며 다이얼로그는 열려 있습니다.
        """
        # 필수 필드 검사 (accept_data와 동일한 로직)
        asset_type = self.asset_type_combo.currentText().strip()
        asset_name = self.asset_name_combo.currentText().strip()
        amount_text = self.amount_input.text().replace(',', '').strip()

        if not asset_type:
            QMessageBox.warning(self, "입력 오류", "자산 종류는 필수로 입력하거나 선택해야 합니다.")
            return
        if not asset_name:
            QMessageBox.warning(self, "입력 오류", "자산 명은 필수로 입력하거나 선택해야 합니다.")
            return
        if not amount_text:
            QMessageBox.warning(self, "입력 오류", "금액은 필수로 입력해야 합니다.")
            return
        
        try:
            amount = int(amount_text)
            if amount < 0:
                QMessageBox.warning(self, "입력 오류", "금액은 음수가 될 수 없습니다.")
                return
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "금액은 유효한 숫자로 입력해야 합니다.")
            return

        # 유효성 검사를 통과하면 데이터 전송 및 필드 초기화
        current_asset_data = self.get_asset_data()
        self.asset_added_and_continue_signal.emit(current_asset_data) # 시그널 전송

        # 금액 및 비고 필드 초기화
        self.amount_input.setText("")
        self.note_input.setText("")
        
        # 날짜 및 알림 상태도 기본값으로 초기화
        self._due_date_cleared_state = False
        self.date_status_combo.setCurrentIndex(0) # '날짜 기록'으로 설정
        self.due_date_input.setDate(QDate.currentDate())
        
        self._alert_enabled = False # 알림 비활성화 상태로
        self.alert_combo.setCurrentText("없음") # 알림 콤보박스 '없음'으로 설정
        self._update_alert_ui_state() # UI 업데이트 강제
        
        QMessageBox.information(self, "추가 입력 완료", "자산 정보가 기록되었고, 추가 입력을 위해 초기화되었습니다.")
        self.amount_input.setFocus() # 금액 입력 필드에 다시 포커스 설정


    def get_asset_data(self):
        """유효성 검사를 통과한 입력된 자산 데이터를 딕셔너리로 반환합니다."""
        due_date = self.due_date_input.date().toString("yyyy-MM-dd")
        # 내부 플래그를 사용하여 '만기일'을 결정합니다.
        if self._due_date_cleared_state:
            due_date = "" # 플래그가 True이면 빈 문자열
        
        # 알림 값 처리: 토글이 비활성화되어 있으면 '없음'으로 저장
        alert_value = self.alert_combo.currentText().strip()
        if not self._alert_enabled:
            alert_value = "없음"

        # CSV 내보내기/가져오기 시 필드명과 일치하도록 조정
        return {
            "자산 종류": self.asset_type_combo.currentText().strip(),
            "세부 분류": self.detail_type_combo.currentText().strip(),
            "자산 명": self.asset_name_combo.currentText().strip(),
            "금액": int(self.amount_input.text().replace(',', '').strip()), # 금액은 콤마 제거 후 숫자로 저장
            "만기일": due_date,
            "알림": alert_value, # 알림은 콤보박스 텍스트로 저장 (상태에 따라 '없음' 처리됨)
            "비고": self.note_input.text().strip()
        }
