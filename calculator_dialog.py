from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QGridLayout, QMessageBox
from PyQt5.QtCore import Qt

class CalculatorDialog(QDialog):
    def __init__(self, parent=None, initial_value=""):
        super().__init__(parent)
        self.setWindowTitle("계산기")
        self.setFixedSize(300, 400)
        self.setWindowFlags(Qt.Window | Qt.Tool) # 비모달, 항상 위에 뜨도록

        self.result_value = initial_value
        self.current_expression = initial_value if initial_value else "0"
        self.last_button_is_operator = False
        self.last_button_is_equals = False

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 결과 표시 라인 에디트
        self.display = QLineEdit(self.current_expression)
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setFixedHeight(50)
        self.display.setStyleSheet("""
            QLineEdit {
                font-size: 24px;
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        main_layout.addWidget(self.display)

        # 버튼 그리드 레이아웃
        buttons_layout = QGridLayout() # 여기를 수정했습니다.
        buttons_layout.setSpacing(10) # 버튼 사이 간격 추가 (10px)

        buttons = [
            ('C', 0, 0), ('CE', 0, 1), ('%', 0, 2), ('/', 0, 3),
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('*', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('-', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('+', 3, 3),
            ('0', 4, 0), ('.', 4, 1), ('=', 4, 2), ('확인', 4, 3) # 확인 버튼 추가
        ]

        for btn_text, row, col in buttons:
            button = QPushButton(btn_text)
            button.setFixedSize(65, 65) # 버튼 크기 통일
            button.setStyleSheet("""
                QPushButton {
                    font-size: 18px;
                    border: 1px solid #bbbbbb;
                    border-radius: 8px;
                    background-color: #e0e0e0;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
                QPushButton[text="C"], QPushButton[text="CE"] {
                    background-color: #f44336; /* Red for Clear buttons */
                    color: white;
                }
                QPushButton[text="C"]:hover, QPushButton[text="CE"]:hover {
                    background-color: #d32f2f;
                }
                QPushButton[text="="], QPushButton[text="확인"] {
                    background-color: #4CAF50; /* Green for Equals/Confirm */
                    color: white;
                }
                QPushButton[text="="]:hover, QPushButton[text="확인"]:hover {
                    background-color: #388E3C;
                }
                QPushButton[text="/"], QPushButton[text="*"], QPushButton[text="-"], QPushButton[text="+"], QPushButton[text="%"] {
                    background-color: #FF9800; /* Orange for Operators */
                    color: white;
                }
                QPushButton[text="/"]:hover, QPushButton[text="*"]:hover, QPushButton[text="-"]:hover, QPushButton[text="+"]:hover, QPushButton[text="%"]:hover {
                    background-color: #F57C00;
                }
            """)
            buttons_layout.addWidget(button, row, col)

        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def button_clicked(self, text):
        if text == '=':
            self.calculate_result()
            self.last_button_is_equals = True
            self.last_button_is_operator = False
        elif text == 'C':
            self.current_expression = "0"
            self.last_button_is_operator = False
            self.last_button_is_equals = False
        elif text == 'CE':
            if self.current_expression == "0":
                pass
            else:
                self.current_expression = self.current_expression[:-1]
                if not self.current_expression:
                    self.current_expression = "0"
            self.last_button_is_operator = False
            self.last_button_is_equals = False
        elif text in ['+', '-', '*', '/', '%']:
            if self.last_button_is_equals: # 이퀄 버튼 직후 연산자 누르면 결과값을 첫 항으로
                self.current_expression = str(self.result_value) + text
            elif self.last_button_is_operator: # 이전 버튼이 연산자면 교체
                self.current_expression = self.current_expression[:-1] + text
            else:
                self.current_expression += text
            self.last_button_is_operator = True
            self.last_button_is_equals = False
        elif text == '확인':
            self.calculate_result() # 확인 버튼 누르면 계산 결과 확정
            self.result_value = self.display.text().replace(',', '') # 콤마 제거 후 저장
            self.accept() # 다이얼로그 닫고 결과 반환
            return # accept() 호출 후에는 추가 동작 없도록
        else: # 숫자 또는 소수점
            if self.last_button_is_equals: # 이퀄 버튼 직후 숫자 누르면 새 계산 시작
                self.current_expression = text
            elif self.current_expression == "0" and text != '.':
                self.current_expression = text
            else:
                self.current_expression += text
            self.last_button_is_operator = False
            self.last_button_is_equals = False
            
        self.display.setText(self.format_expression(self.current_expression))

    def calculate_result(self):
        """현재 표현식을 계산하고 결과를 display에 업데이트합니다."""
        try:
            # 안전하지 않은 eval 대신 ast.literal_eval 또는 자체 파서 사용 권장
            # 여기서는 간단한 예제를 위해 eval 사용 (실제 앱에서는 주의 필요)
            # 퍼센트 연산자 처리: %를 / 100으로 변경
            expression_to_eval = self.current_expression.replace('%', '/100')

            # 마지막 문자가 연산자이면 제거 (예: "123+" -> "123")
            if expression_to_eval and expression_to_eval[-1] in ['+', '-', '*', '/', '.']:
                expression_to_eval = expression_to_eval[:-1]

            result = eval(expression_to_eval)
            # 결과가 정수이면 정수로, 아니면 소수점 두 자리까지 표시
            if result == int(result):
                result_str = str(int(result))
            else:
                result_str = f"{result:.2f}"
                if result_str.endswith('.00'):
                    result_str = result_str[:-3]

            self.current_expression = result_str
            self.result_value = result # 결과값을 result_value에 저장

        except Exception as e:
            QMessageBox.warning(self, "계산 오류", "유효하지 않은 수식입니다.")
            self.current_expression = "Error"
            self.result_value = 0 # 오류 발생 시 결과값 초기화

    def format_expression(self, expression):
        """표현식에서 숫자를 찾아 천 단위 콤마를 적용합니다."""
        # 이 함수는 연산자를 기준으로 숫자를 분리하고 각 숫자에 콤마를 적용합니다.
        # 복잡한 수식의 중간 상태에서는 적용하기 어려울 수 있으므로, 최종 결과에만 적용하는 것이 일반적입니다.
        # 여기서는 입력 중에도 콤마를 보여주기 위해 구현하지만, 완벽하지 않을 수 있습니다.
        
        # 간단하게 숫자 부분만 콤마 처리 (완벽한 파서는 아님)
        parts = []
        num_str = ""
        for char in expression:
            if char.isdigit() or char == '.':
                num_str += char
            else:
                if num_str:
                    try:
                        # 숫자로 변환 가능한 경우에만 포맷
                        if '.' in num_str:
                            parts.append(f"{float(num_str):,}")
                        else:
                            parts.append(f"{int(num_str):,}")
                    except ValueError:
                        parts.append(num_str) # 변환 실패 시 원본 유지
                    num_str = ""
                parts.append(char)
        if num_str:
            try:
                if '.' in num_str:
                    parts.append(f"{float(num_str):,}")
                else:
                    parts.append(f"{int(num_str):,}")
            except ValueError:
                parts.append(num_str)

        return "".join(parts)


    def get_result(self):
        """계산 결과를 반환합니다."""
        return self.display.text().replace(',', '') # 반환 시 콤마 제거
