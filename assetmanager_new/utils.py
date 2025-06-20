from PyQt5.QtCore import QDate
from datetime import datetime

def parse_date_string_to_qdate(date_string):
    """
    주어진 날짜 문자열을 QDate 객체로 파싱합니다.
    다양한 형식 (YYYY-MM-DD, MM/DD/YYYY 등)을 시도합니다.
    """
    # QDate.fromString이 처리할 수 있는 다양한 날짜 형식 리스트
    formats = ["yyyy-MM-dd", "yyyy/MM/dd", "yyyy.MM.dd", "MM/dd/yyyy", "dd.MM.yyyy"]
    for fmt in formats:
        qdate = QDate.fromString(date_string, fmt)
        if qdate.isValid():
            return qdate
    return None # 유효한 형식으로 파싱할 수 없는 경우

def calculate_d_day(target_date_str):
    """
    대상 날짜 문자열을 기준으로 오늘까지의 D-Day를 계산합니다.
    (예: "YYYY-MM-DD" 형식)
    """
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        delta = target_date - today
        return delta.days
    except ValueError:
        return None # 날짜 형식 오류 시

def format_currency(amount):
    """숫자를 천 단위 콤마와 '원'을 붙여 통화 형식으로 포맷합니다."""
    try:
        return f"{int(amount):,} 원"
    except (ValueError, TypeError):
        return str(amount) + " 원" # 숫자가 아닌 경우 원본 값에 '원'만 붙여 반환

