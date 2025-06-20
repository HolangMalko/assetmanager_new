from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from utils import calculate_d_day, format_currency

class AssetTreeView(QTreeWidget):
    # 자산 추가/편집/삭제 요청 시그널
    add_asset_requested = pyqtSignal()
    edit_asset_requested = pyqtSignal()
    delete_asset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection) # 다중 선택 가능
        self.setSelectionBehavior(QAbstractItemView.SelectRows) # 행 단위 선택

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setHeaderLabels([
            "No.", "자산 이름", "수량", "매입 단가", "현재 단가",
            "평가 금액", "수익률", "평가 손익", "매입일", "만기일", "D-Day", "메모"
        ])
        
        # 헤더 설정
        header = self.header()
        header.setSectionResizeMode(QHeaderView.ResizeToContents) # 내용에 맞게 크기 자동 조절
        header.setStretchLastSection(True) # 마지막 컬럼이 남은 공간 채우기
        header.setFont(QFont("맑은 고딕", 10, QFont.Bold)) # 헤더 폰트 설정

        # 특정 컬럼 너비 고정 (예시)
        header.setSectionResizeMode(0, QHeaderView.Fixed) # No. 컬럼 고정
        header.setFixedWidth(50) 
        header.setSectionResizeMode(1, QHeaderView.Stretch) # 자산 이름 늘이기

        # TreeWidget 스타일링 (QSS에서 대부분 처리)
        self.setAlternatingRowColors(True) # 행 색상 교차
        self.setMouseTracking(True) # 마우스 오버 시 하이라이트 등 (QSS와 함께)

    def _connect_signals(self):
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setContextMenuPolicy(Qt.CustomContextMenu) # 컨텍스트 메뉴 정책 설정
        # Enter 키 눌렀을 때 편집 다이얼로그 띄우기
        self.keyPressEvent = self._custom_key_press_event

    def _custom_key_press_event(self, event):
        """Enter 키와 Delete 키 이벤트를 처리합니다."""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.edit_asset_requested.emit()
        elif event.key() == Qt.Key_Delete:
            self.delete_asset_requested.emit()
        else:
            super().keyPressEvent(event) # 기본 동작 유지

    def _on_item_double_clicked(self, item, column):
        """항목 더블 클릭 시 편집 다이얼로그를 띄웁니다."""
        self.edit_asset_requested.emit()

    def _show_context_menu(self, pos):
        """컨텍스트 메뉴를 표시합니다."""
        menu = QMenu(self)

        add_action = menu.addAction("자산 추가")
        edit_action = menu.addAction("자산 편집")
        delete_action = menu.addAction("자산 삭제")
        
        # 선택된 항목이 없으면 편집/삭제 비활성화
        if not self.selectedItems():
            edit_action.setEnabled(False)
            delete_action.setEnabled(False)

        action = menu.exec_(self.mapToGlobal(pos))

        if action == add_action:
            self.add_asset_requested.emit()
        elif action == edit_action:
            self.edit_asset_requested.emit()
        elif action == delete_action:
            self.delete_asset_requested.emit()

    def load_assets(self, assets_data):
        """
        주어진 자산 데이터를 TreeView에 로드하고 표시합니다.
        assets_data: 리스트 of 딕셔너리 (각 딕셔너리는 하나의 자산 데이터)
        """
        self.clear() # 기존 항목 모두 제거
        if not assets_data:
            return

        for idx, asset in enumerate(assets_data):
            # 필요한 필드가 모두 있는지 확인
            required_fields = ["자산 이름", "수량", "매입 단가", "현재 단가", "매입일", "만기일", "메모"]
            if not all(field in asset for field in required_fields):
                print(f"경고: 필수 필드가 누락된 자산 데이터: {asset}")
                continue # 누락된 필드가 있으면 건너뛰기

            # 숫자 필드는 float으로 변환 시도
            try:
                quantity = float(asset.get("수량", 0))
                purchase_price = float(asset.get("매입 단가", 0))
                current_price = float(asset.get("현재 단가", 0))
            except ValueError:
                print(f"경고: 유효하지 않은 숫자 값: {asset}")
                continue

            # 계산된 필드
            evaluation_amount = quantity * current_price
            
            # 매입 단가가 0이 아니고 음수가 아닌 경우에만 수익률 계산
            if purchase_price > 0:
                profit_loss = evaluation_amount - (quantity * purchase_price)
                if quantity * purchase_price != 0:
                    profit_rate = (profit_loss / (quantity * purchase_price)) * 100
                else:
                    profit_rate = 0.0 # 매입 총액이 0이면 수익률 0
            else:
                profit_loss = evaluation_amount # 매입 단가가 없거나 0이면 평가 금액 자체가 손익
                profit_rate = float('inf') if quantity * current_price > 0 else 0.0 # 무한대 또는 0

            d_day = calculate_d_day(asset.get("만기일", ""))

            item = QTreeWidgetItem(self)
            item.setText(0, str(idx + 1)) # No. (0부터 시작하는 인덱스에 1 더함)
            item.setText(1, asset.get("자산 이름", ""))
            item.setText(2, format_currency(quantity))
            item.setText(3, format_currency(purchase_price))
            item.setText(4, format_currency(current_price))
            item.setText(5, format_currency(evaluation_amount))
            item.setText(6, f"{profit_rate:.2f}%" if profit_rate != float('inf') else "N/A") # 수익률
            item.setText(7, format_currency(profit_loss))
            item.setText(8, asset.get("매입일", ""))
            item.setText(9, asset.get("만기일", ""))
            item.setText(10, d_day)
            item.setText(11, asset.get("메모", ""))

            # 숫자형 데이터 정렬을 위해 UserRole에 원본 숫자 값을 저장
            item.setData(2, Qt.UserRole, quantity)
            item.setData(3, Qt.UserRole, purchase_price)
            item.setData(4, Qt.UserRole, current_price)
            item.setData(5, Qt.UserRole, evaluation_amount)
            item.setData(6, Qt.UserRole, profit_rate)
            item.setData(7, Qt.UserRole, profit_loss)

            # 만기일 D-Day 색상 변경 (D-Day는 초록, D+는 빨강)
            if d_day.startswith("D-") and d_day != "D-Day":
                item.setForeground(10, QColor("#28a745")) # Green
            elif d_day.startswith("D+"):
                item.setForeground(10, QColor("#dc3545")) # Red
            elif d_day == "D-Day":
                item.setForeground(10, QColor("#ffc107")) # Orange

            # 수익률에 따른 색상 변경
            if profit_rate > 0:
                item.setForeground(6, QColor("#28a745")) # Green
                item.setForeground(7, QColor("#28a745")) # Green
            elif profit_rate < 0:
                item.setForeground(6, QColor("#dc3545")) # Red
                item.setForeground(7, QColor("#dc3545")) # Red
            else:
                item.setForeground(6, QColor("#6c757d")) # Gray
                item.setForeground(7, QColor("#6c757d")) # Gray

            # 원본 데이터(idx 포함)를 Qt.UserRole에 저장하여 편집/삭제 시 사용
            # self.get_data_from_item()에서 이 데이터를 사용함
            # 실제 AssetDataManager와 통신할 때는 'idx'를 제거하고 보내야 함
            asset_with_idx = asset.copy()
            asset_with_idx['idx'] = idx # UI에서 사용하기 위한 임시 인덱스
            item.setData(0, Qt.UserRole, asset_with_idx) 

        self.sortItems(0, Qt.AscendingOrder) # No.를 기준으로 오름차순 정렬 (초기)

    def get_data_from_item(self, item):
        """QTreeWidgetItem에서 원본 자산 데이터를 추출합니다."""
        # load_assets에서 Qt.UserRole에 저장된 원본 딕셔너리를 반환
        return item.data(0, Qt.UserRole)