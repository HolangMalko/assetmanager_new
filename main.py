import sys
import json
import os
from datetime import datetime
from collections import defaultdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QAction, QMessageBox, QMenu, QToolBar, QSizePolicy, QSystemTrayIcon,
    QPushButton, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog, QLineEdit, QLabel, QFileDialog, QStyle, QStyleOptionTab
)
from PyQt5.QtGui import QIcon, QFont, QDesktopServices, QPixmap
from PyQt5.QtCore import Qt, QSize, QUrl, QDate, QObject, pyqtSignal, QRect

# Font Awesome 대신 QtAwesome 사용을 위해 임포트
import qtawesome as qta

# 다른 모듈들 임포트
from asset_data_manager import AssetDataManager
from password_manager import PasswordManager
from ui_dialogs import AssetInputDialog
from app_ui_manager import AppUIManager
from utils import calculate_d_day, format_currency, parse_date_string_to_qdate

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("자산 관리 프로그램")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)

        # QSS 파일 로드 경로 수정: os.path.join을 사용하여 현재 스크립트 파일의 디렉토리를 기준으로 경로 지정
        self.load_qss(os.path.join(os.path.dirname(__file__), "style.qss"))

        # AssetDataManager를 인스턴스화
        self.asset_manager = AssetDataManager()
        
        # AssetDataManager의 시그널을 슬롯에 연결
        self.asset_manager.tab_list_changed.connect(self.update_tabs_from_data)
        self.asset_manager.data_changed.connect(self.update_current_tab_table_if_active)
        self.asset_manager.data_loaded.connect(self.handle_initial_data_load) # 초기 로드 완료 시그널 처리

        # 앱의 다른 관리자들 (이들은 AssetDataManager와는 별개로 동작)
        self.password_manager = PasswordManager(self)
        self.ui_manager = AppUIManager(self)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 탭 닫기 버튼 (X) 추가
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        # 탭 왼쪽에 + 버튼 추가 (cornerWidget 방식)
        self.add_tab_button = QPushButton()
        self.add_tab_button.setObjectName("addTabButton") # QSS에서 특정 스타일을 지정하기 위한 Object 이름 설정
        self.add_tab_button.setIcon(qta.icon('mdi.plus', options=[{'scale_factor': 1.0, 'color': '#333333'}])) 
        self.add_tab_button.setFixedSize(30, 30) # 버튼 크기
        self.add_tab_button.clicked.connect(self.add_new_tab)
        self.tab_widget.setCornerWidget(self.add_tab_button, Qt.TopLeftCorner)


        # 탭 위젯의 현재 탭 변경 시그널 연결 (탭 변경 시 테이블 새로고침 및 활성화 탭 관리 위함)
        self.tab_widget.currentChanged.connect(self.current_tab_changed)
        
        # 각 탭의 QTableWidget 인스턴스를 저장할 딕셔너리
        self._tab_tables = {}

        self.create_actions()
        self.create_toolbar()
        self.create_menubar()
        self.create_status_bar()
        self.setup_tray_icon()

        # 총 금액 표시를 위한 상태바 라벨
        self.total_amount_label = QLabel("총 금액: 0 원")
        self.total_amount_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.statusBar().addPermanentWidget(self.total_amount_label)
        
        # 초기 데이터 로드는 AssetDataManager에서 처리되고 시그널로 UI 업데이트를 트리거합니다.
        # self.update_tabs_from_data() # _load_data()가 data_loaded 시그널을 emit하여 호출될 것임

    def load_qss(self, file_path):
        """QSS 파일을 로드하여 애플리케이션에 적용합니다."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"Error: '{file_path}' not found. Please ensure 'style.qss' is in the correct directory.")
            QMessageBox.warning(self, "QSS 파일 오류", 
                                f"'{file_path}' 파일을 찾을 수 없습니다.\n"
                                "UI가 제대로 표시되지 않을 수 있습니다.")
        except Exception as e:
            print(f"Error loading QSS file: {e}")
            QMessageBox.warning(self, "QSS 파일 오류", 
                                f"QSS 파일을 로드하는 중 오류가 발생했습니다: {e}\n"
                                "UI가 제대로 표시되지 않을 수 있습니다.")

    def handle_initial_data_load(self, all_assets_data):
        """초기 데이터 로드 완료 시그널을 처리합니다."""
        print("초기 자산 데이터 로드 완료.")
        self.update_tabs_from_data() # 데이터 로드 후 탭 UI를 업데이트
        self.update_total_amount_display() # 초기 로드 후 총 금액 업데이트
        
        # 모든 탭이 추가되고 첫 탭이 선택된 후, UI 업데이트를 강제합니다.
        QApplication.processEvents() 

    def update_tabs_from_data(self):
        """AssetDataManager에 저장된 탭 목록을 기반으로 탭 위젯을 업데이트합니다."""
        print("DEBUG: update_tabs_from_data 호출됨") # Debug print
        current_tab_index = self.tab_widget.currentIndex()
        current_tab_name = self.tab_widget.tabText(current_tab_index) if current_tab_index != -1 else ""

        # 기존 탭과 테이블 인스턴스를 모두 제거
        for i in reversed(range(self.tab_widget.count())):
            tab_widget_item = self.tab_widget.widget(i)
            # 해당 탭 이름으로 저장된 테이블 인스턴스도 _tab_tables에서 삭제
            tab_name_to_remove = self.tab_widget.tabText(i)
            if tab_name_to_remove in self._tab_tables:
                del self._tab_tables[tab_name_to_remove]
            self.tab_widget.removeTab(i)
            tab_widget_item.deleteLater() # 위젯 메모리 해제
        
        # AssetDataManager에서 모든 탭 이름 가져오기
        tab_names = self.asset_manager.get_all_tab_names()
        print(f"DEBUG: AssetDataManager에서 가져온 탭 이름: {tab_names}") # Debug print
        
        new_current_index_to_set = -1

        # 로드된 탭 이름이 있다면 그 탭들을 추가
        if tab_names:
            for i, tab_name in enumerate(tab_names):
                tab_widget_content = self._create_asset_tab_content(tab_name) # 각 탭의 내용 생성
                self.tab_widget.addTab(tab_widget_content, tab_name)
                
                # 변경: 특정 탭 ('내 자산')을 우선 선택하는 로직 제거
                # 이전에 선택된 탭이 존재한다면 해당 탭 선택
                if tab_name == current_tab_name and new_current_index_to_set == -1:
                    new_current_index_to_set = i
            
            # 탭이 업데이트된 후 적절한 탭을 활성화
            if new_current_index_to_set != -1: # 이전 활성화 탭이 존재한다면
                self.tab_widget.setCurrentIndex(new_current_index_to_set)
            elif tab_names: # 그 외 경우, 탭이 존재한다면 첫 번째 탭을 선택
                self.tab_widget.setCurrentIndex(0)
        else:
            print("DEBUG: AssetDataManager에서 유효한 탭을 가져오지 못했습니다. UI에 탭이 추가되지 않았습니다.")


        # 탭이 변경되었으므로 총 금액 업데이트
        self.update_total_amount_display()
        print("DEBUG: 탭 업데이트 완료.") # Debug print

    def _create_asset_tab_content(self, tab_name):
        """각 탭에 들어갈 QTableWidget과 버튼 레이아웃을 생성합니다."""
        tab_content = QWidget()
        main_layout = QVBoxLayout(tab_content)

        # 탭 상단 (버튼 등) 레이아웃
        top_layout = QHBoxLayout()

        add_asset_button = QPushButton("자산 추가")
        add_asset_button.setIcon(qta.icon('mdi.plus-circle'))
        add_asset_button.clicked.connect(lambda _, tn=tab_name: self.add_new_asset(tn)) # 탭 이름 고정
        top_layout.addWidget(add_asset_button)

        delete_asset_button = QPushButton("자산 삭제")
        delete_asset_button.setIcon(qta.icon('mdi.delete'))
        delete_asset_button.clicked.connect(lambda _, tn=tab_name: self.delete_selected_asset(tn)) # 탭 이름 고정
        top_layout.addWidget(delete_asset_button)

        # 여기에 "자세히 보기" 버튼 추가
        view_details_button = QPushButton("자세히 보기")
        view_details_button.setIcon(qta.icon('mdi.chevron-down')) # 대체 아이콘
        view_details_button.clicked.connect(lambda: QMessageBox.information(self, "자세히 보기", "자세히 보기 기능이 여기에 구현됩니다."))
        top_layout.addWidget(view_details_button)
        
        # 검색 기능
        search_label = QLabel("검색:")
        search_input = QLineEdit()
        search_input.setPlaceholderText("자산 명, 종류, 분류 등 검색")
        search_input.textChanged.connect(lambda text, tn=tab_name: self.filter_assets(tn, text)) # 탭 이름 고정
        top_layout.addWidget(search_label)
        top_layout.addWidget(search_input)

        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # QTableWidget 설정
        asset_table = QTableWidget()
        self._tab_tables[tab_name] = asset_table # 테이블 인스턴스 저장
        main_layout.addWidget(asset_table)

        # "No." 셀은 UI에서 제거되었으나, 내부 데이터 모델에는 'no' 필드가 유지되어 고유 식별자로 사용됩니다.
        column_headers = ["자산 종류", "세부 분류", "자산 명", "금액", "만기일", "D-Day", "알림", "비고"]
        asset_table.setColumnCount(len(column_headers))
        asset_table.setHorizontalHeaderLabels(column_headers)

        # 셀 크기를 동일하게 통일 (여기서는 Stretch 모드를 사용하여 균등하게 분배)
        for i in range(len(column_headers)):
            asset_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)

        asset_table.setSortingEnabled(True)

        # 셀 더블 클릭 시 수정 기능 연결
        asset_table.itemDoubleClicked.connect(lambda item, tn=tab_name: self.edit_selected_asset(tn, item)) # 탭 이름 고정

        # 탭 생성 시 해당 탭의 데이터 로드
        self.load_assets_to_table(tab_name)
        
        return tab_content

    def current_tab_changed(self, index):
        """QTabWidget의 현재 탭이 변경될 때 호출되는 슬롯."""
        if index != -1: # 유효한 탭이 선택되었을 때
            tab_name = self.tab_widget.tabText(index)
            # 현재 탭이 바뀌었을 때 테이블 새로고침 (data_changed 시그널이 발생하지 않았더라도)
            self.load_assets_to_table(tab_name)
            self.update_total_amount_display() # 탭 변경 시 총 금액 업데이트
            
    def update_current_tab_table_if_active(self, changed_tab_name):
        """
        AssetDataManager의 data_changed 시그널에 연결되어 테이블을 업데이트합니다.
        변경된 탭이 현재 활성화된 탭이면 해당 테이블을 업데이트하고,
        아니더라도 해당 탭의 테이블을 업데이트합니다.
        """
        # 변경된 탭이 _tab_tables에 등록되어 있는지 확인
        if changed_tab_name in self._tab_tables:
            self.load_assets_to_table(changed_tab_name)
            # 현재 활성화된 탭의 데이터가 변경되었다면 총 금액도 업데이트
            if self.tab_widget.tabText(self.tab_widget.currentIndex()) == changed_tab_name:
                self.update_total_amount_display()
        else:
            print(f"경고: '{changed_tab_name}' 탭의 테이블 인스턴스를 찾을 수 없습니다. (아마 탭이 아직 생성되지 않았거나 삭제됨)")

    def add_new_asset(self, tab_name):
        """
        자산 추가 다이얼로그를 열고 사용자 입력을 처리합니다.
        '추가입력' 또는 '확인' 버튼을 통해 AssetDataManager에 데이터를 추가합니다.
        """
        dialog = AssetInputDialog(self)
        
        # 'asset_added_and_continue_signal'을 AssetDataManager의 add_asset 메서드에 연결
        # 이 시그널은 '추가입력' 버튼이 눌렸을 때 발생합니다.
        dialog.asset_added_and_continue_signal.connect(
            lambda asset_data: self.asset_manager.add_asset(tab_name, asset_data)
        )
        
        # 다이얼로그를 모달로 실행하고 결과를 기다립니다.
        # '확인' 버튼을 눌렀을 때만 이 블록이 실행됩니다.
        if dialog.exec_() == QInputDialog.Accepted:
            final_asset_data = dialog.get_asset_data()
            if final_asset_data:
                self.asset_manager.add_asset(tab_name, final_asset_data)
                QMessageBox.information(self, "자산 추가", f"[{tab_name}] 탭에 새로운 자산이 성공적으로 추가되었습니다.")
            else:
                QMessageBox.warning(self, "자산 추가", "유효한 자산 데이터가 없습니다.")


    def delete_selected_asset(self, tab_name):
        current_table = self._tab_tables.get(tab_name)
        if not current_table: return # 해당 탭의 테이블이 없으면 리턴

        selected_rows = current_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "삭제 오류", "삭제할 자산을 선택해주세요.")
            return

        reply = QMessageBox.question(self, "자산 삭제 확인",
                                     "선택된 자산을 정말로 삭제하시겠습니까?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            assets_to_delete = []
            # UI에서 선택된 행들을 역순으로 정렬하여 올바른 인덱스 삭제
            for index in sorted(selected_rows, reverse=True):
                row = index.row()
                # 첫 번째 컬럼의 Qt.UserRole에서 전체 자산 데이터를 가져옴
                original_asset_dict = current_table.item(row, 0).data(Qt.UserRole)
                if original_asset_dict:
                    assets_to_delete.append(original_asset_dict) # 전체 원본 딕셔너리를 전달

            if self.asset_manager.delete_assets(tab_name, assets_to_delete):
                QMessageBox.information(self, "자산 삭제", "선택된 자산이 삭제되었습니다.")
            else:
                QMessageBox.warning(self, "삭제 실패", "자산 삭제 중 오류가 발생했습니다. 일부 자산이 삭제되지 않았을 수 있습니다.")

    def edit_selected_asset(self, tab_name, item):
        current_table = self._tab_tables.get(tab_name)
        if not current_table: return

        row = item.row()
        # 첫 번째 컬럼의 Qt.UserRole에서 전체 자산 데이터를 가져옴
        original_asset_dict = current_table.item(row, 0).data(Qt.UserRole)
        if not original_asset_dict:
            QMessageBox.warning(self, "수정 오류", "선택된 자산의 정보를 찾을 수 없습니다.")
            return
        
        dialog = AssetInputDialog(self, original_asset_dict) # 기존 데이터로 다이얼로그 초기화
        if dialog.exec_() == QInputDialog.Accepted:
            updated_data = dialog.get_asset_data()
            if updated_data:
                # '만기일'이 공백일 경우 데이터에서 제거하여 None으로 저장되지 않도록 함
                if '만기일' in updated_data and not updated_data['만기일'].strip():
                    del updated_data['만기일']

                if self.asset_manager.update_asset(tab_name, original_asset_dict, updated_data): # 원본 딕셔너리 전달
                    QMessageBox.information(self, "자산 수정", "자산 정보가 성공적으로 수정되었습니다.")
                else:
                    QMessageBox.warning(self, "수정 실패", "자산 정보 수정 중 오류가 발생했습니다.")
            else:
                QMessageBox.warning(self, "자산 수정", "유효한 자산 데이터가 없습니다.")


    def load_assets_to_table(self, tab_name):
        """지정된 탭의 테이블에 자산 데이터를 로드합니다."""
        current_table = self._tab_tables.get(tab_name)
        if not current_table:
            # 탭이 아직 생성되지 않았거나, 현재 존재하지 않는 탭 이름일 경우
            print(f"오류: 탭 '{tab_name}'에 해당하는 테이블 인스턴스를 찾을 수 없습니다.")
            return

        current_table.setSortingEnabled(False) # 데이터 로드 중 정렬 비활성화
        current_table.setRowCount(0) # 기존 행 모두 제거

        assets = self.asset_manager.get_assets_by_tab(tab_name)
        
        for row_idx, asset in enumerate(assets):
            current_table.insertRow(row_idx)

            # 첫 번째 컬럼(이제 자산 종류)의 item에 전체 asset 데이터를 저장하여 데이터 참조 유지
            item_type = QTableWidgetItem(asset.get('자산 종류', ''))
            item_type.setData(Qt.UserRole, asset) # 중요: 전체 asset 딕셔너리 저장 (no 포함)
            item_type.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            current_table.setItem(row_idx, 0, item_type)

            item_detail_type = QTableWidgetItem(asset.get('세부 분류', ''))
            item_detail_type.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            current_table.setItem(row_idx, 1, item_detail_type)

            item_name = QTableWidgetItem(asset.get('자산 명', ''))
            item_name.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            current_table.setItem(row_idx, 2, item_name)

            amount_raw = asset.get('금액', 0)
            item_amount = QTableWidgetItem(format_currency(amount_raw))
            item_amount.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter) # 금액 오른쪽 정렬
            item_amount.setData(Qt.UserRole, amount_raw) # 정렬을 위한 숫자 데이터
            current_table.setItem(row_idx, 3, item_amount)

            due_date_str = asset.get('만기일', '')
            item_due_date = QTableWidgetItem(due_date_str)
            item_due_date.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            current_table.setItem(row_idx, 4, item_due_date)

            d_day_str = ""
            if due_date_str:
                d_day = calculate_d_day(due_date_str)
                if d_day is not None:
                    d_day_str = f"D-{d_day}" if d_day >= 0 else f"D+{abs(d_day)}"
                else:
                    d_day_str = "날짜 오류"
            item_d_day = QTableWidgetItem(d_day_str)
            item_d_day.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            # QDate 객체를 UserRole에 저장하여 정렬 기준으로 사용 (없으면 QDate())
            qdate_due = parse_date_string_to_qdate(due_date_str)
            item_d_day.setData(Qt.UserRole, qdate_due if qdate_due else QDate()) 
            current_table.setItem(row_idx, 5, item_d_day)

            item_alert = QTableWidgetItem(asset.get('알림', ''))
            item_alert.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            current_table.setItem(row_idx, 6, item_alert)

            item_note = QTableWidgetItem(asset.get('비고', ''))
            item_note.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            current_table.setItem(row_idx, 7, item_note)
            
            # 모든 셀을 편집 불가능하게 설정 (더블 클릭 시 편집 다이얼로그로만 편집)
            for col in range(current_table.columnCount()):
                item = current_table.item(row_idx, col)
                if item: # item이 None이 아닐 경우에만 설정
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        current_table.setSortingEnabled(True) # 데이터 로드 후 정렬 활성화
        current_table.sortByColumn(0, Qt.AscendingOrder) # 자산 종류 기준으로 초기 정렬 (선택 사항)


    def filter_assets(self, tab_name, text):
        current_table = self._tab_tables.get(tab_name)
        if not current_table: return # 해당 탭의 테이블이 없으면 리턴

        search_text = text.lower()
        for row in range(current_table.rowCount()):
            row_visible = False
            for col in range(current_table.columnCount()): # 모든 컬럼에서 검색
                item = current_table.item(row, col)
                if item and search_text in item.text().lower():
                    row_visible = True
                    break
            current_table.setRowHidden(row, not row_visible)
            
    # --- 메뉴 및 툴바 액션 정의 ---

    def create_actions(self):
        # 파일 메뉴 액션
        self.exit_action = QAction(qta.icon('mdi.exit-to-app'), "&나가기", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setStatusTip("프로그램 종료")
        self.exit_action.triggered.connect(self.close)

        self.export_csv_action = QAction(qta.icon('mdi.file-export'), "CSV로 내보내기", self)
        self.export_csv_action.setStatusTip("현재 탭의 자산 데이터를 CSV 파일로 내보냅니다.")
        self.export_csv_action.triggered.connect(self.export_current_tab_to_csv)

        self.import_csv_action = QAction(qta.icon('mdi.file-import'), "CSV에서 가져오기", self)
        self.import_csv_action.setStatusTip("CSV 파일에서 자산 데이터를 현재 탭으로 가져옵니다.")
        self.import_csv_action.triggered.connect(self.import_csv_to_current_tab)

        # 설정 메뉴 액션
        self.password_change_action = QAction(qta.icon('mdi.key'), "비밀번호 변경", self)
        self.password_change_action.setStatusTip("로그인 비밀번호를 변경합니다.")
        self.password_change_action.triggered.connect(self.password_manager.change_password_dialog)

        self.password_option_action = QAction(qta.icon('mdi.cog-outline'), "로그인 옵션", self)
        self.password_option_action.setStatusTip("로그인 옵션을 설정합니다.")
        self.password_option_action.triggered.connect(self.password_manager.password_option_dialog)

        # 탭 관리 액션 (이제 '+' 버튼은 cornerWidget으로 이동했으므로 툴바에는 추가하지 않음)
        self.add_tab_action = QAction(qta.icon('mdi.tab-plus'), "새 탭 추가", self)
        self.add_tab_action.setStatusTip("새로운 자산 탭을 추가합니다.")
        self.add_tab_action.triggered.connect(self.add_new_tab)
        
        self.rename_tab_action = QAction(qta.icon('mdi.pencil'), "탭 이름 변경", self)
        self.rename_tab_action.setStatusTip("현재 탭의 이름을 변경합니다.")
        self.rename_tab_action.triggered.connect(self.rename_current_tab)

        self.delete_tab_action = QAction(qta.icon('mdi.tab-remove'), "탭 삭제", self)
        self.delete_tab_action.setStatusTip("현재 탭을 삭제합니다.")
        self.delete_tab_action.triggered.connect(self.delete_current_tab)

        # 도움말 메뉴 액션
        self.about_action = QAction(qta.icon('mdi.information'), "&정보", self)
        self.about_action.setStatusTip("이 프로그램에 대한 정보")
        self.about_action.triggered.connect(self.ui_manager.show_about_dialog)

        self.manual_action = QAction(qta.icon('mdi.book-open-variant'), "사용 설명서", self)
        self.manual_action.setStatusTip("사용 설명서를 엽니다.")
        self.manual_action.triggered.connect(self.ui_manager.open_manual)

        # 새로운 '자세히 보기' 액션 추가 (QSS에서 별도의 아이콘 이미지를 사용하지 않으므로 qtawesome 아이콘으로 대체)
        self.view_details_action = QAction(qta.icon('mdi.chevron-down'), "자세히 보기", self)
        self.view_details_action.setStatusTip("선택된 자산의 상세 정보를 봅니다.")
        self.view_details_action.triggered.connect(lambda: QMessageBox.information(self, "자세히 보기", "툴바에서 자세히 보기 기능이 여기에 구현됩니다."))


    def create_toolbar(self):
        self.toolbar = self.addToolBar("메인")
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False) # 툴바 이동 불가 설정 (디자인 고정)

        # 자산 관리 버튼
        add_asset_toolbar_action = QAction(qta.icon('mdi.plus-circle'), "자산 추가", self)
        add_asset_toolbar_action.triggered.connect(lambda: self.add_new_asset(self.tab_widget.tabText(self.tab_widget.currentIndex())))
        self.toolbar.addAction(add_asset_toolbar_action)

        delete_asset_toolbar_action = QAction(qta.icon('mdi.delete'), "자산 삭제", self)
        delete_asset_toolbar_action.triggered.connect(lambda: self.delete_selected_asset(self.tab_widget.tabText(self.tab_widget.currentIndex())))
        self.toolbar.addAction(delete_asset_toolbar_action)

        self.toolbar.addSeparator()

        # 새로 추가된 '자세히 보기' 액션을 툴바에 추가
        self.toolbar.addAction(self.view_details_action)
        self.toolbar.addSeparator()

        # 비밀번호 관련 버튼
        self.toolbar.addAction(self.password_change_action)
        self.toolbar.addAction(self.password_option_action)
        self.toolbar.addSeparator()
        
        # 탭 관리 버튼 (기존 메뉴 아이템 사용)
        # self.toolbar.addAction(self.add_tab_action) # '+' 버튼이 이제 Corner Widget으로 이동했으므로 툴바에서는 제거
        self.toolbar.addAction(self.rename_tab_action)
        self.toolbar.addAction(self.delete_tab_action)
        self.toolbar.addSeparator()

        # CSV 버튼
        self.toolbar.addAction(self.export_csv_action)
        self.toolbar.addAction(self.import_csv_action)
        self.toolbar.addSeparator()
        
        # 정보 버튼
        self.toolbar.addAction(self.about_action)
        self.toolbar.addAction(self.manual_action)


    def create_menubar(self):
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("&파일")
        file_menu.addAction(self.export_csv_action)
        file_menu.addAction(self.import_csv_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # 설정 메뉴
        settings_menu = menubar.addMenu("&설정")
        settings_menu.addAction(self.password_change_action)
        settings_menu.addAction(self.password_option_action)
        
        # 탭 관리 메뉴
        tab_menu = menubar.addMenu("&탭 관리")
        tab_menu.addAction(self.add_tab_action)
        tab_menu.addAction(self.rename_tab_action)
        tab_menu.addAction(self.delete_tab_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu("&도움말")
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.manual_action)

    def create_status_bar(self):
        self.statusBar().showMessage("준비됨")

    def update_total_amount_display(self):
        """총 금액을 업데이트하는 함수."""
        current_tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
        if current_tab_name:
            total_amount = self.asset_manager.get_total_amount_by_tab(current_tab_name)
            self.total_amount_label.setText(f"총 금액: {format_currency(total_amount)}")
        else:
            self.total_amount_label.setText("총 금액: 0 원")

    # --- 탭 관리 기능 슬롯 ---
    def add_new_tab(self):
        """새 탭 추가 다이얼로그를 열고 사용자 입력을 처리합니다."""
        tab_name, ok = QInputDialog.getText(self, "새 탭 추가", "새 탭 이름:")
        if ok and tab_name:
            stripped_tab_name = tab_name.strip()
            if not stripped_tab_name:
                QMessageBox.warning(self, "탭 추가 실패", "탭 이름은 비워둘 수 없습니다.")
                return

            if stripped_tab_name in self.asset_manager.get_all_tab_names():
                QMessageBox.warning(self, "탭 추가 실패", f"'{stripped_tab_name}' 탭은 이미 존재합니다.")
                return
            
            if self.asset_manager.add_tab_data(stripped_tab_name):
                QMessageBox.information(self, "탭 추가", f"'{stripped_tab_name}' 탭이 추가되었습니다.")
            else:
                QMessageBox.warning(self, "탭 추가 실패", "탭 추가 중 오류가 발생했습니다.")
        elif ok: # 사용자가 텍스트를 입력했으나 빈 문자열인 경우 (strip 후)
            QMessageBox.warning(self, "탭 추가 실패", "탭 이름을 입력해야 합니다.")

    def close_tab(self, index):
        """탭 닫기 버튼을 눌렀을 때 호출됩니다."""
        # 실제 데이터 탭이 하나만 남은 경우
        if self.tab_widget.count() == 1: 
            QMessageBox.warning(self, "탭 삭제 불가", "마지막 남은 자산 탭은 삭제할 수 없습니다. 최소 하나의 자산 탭이 필요합니다.")
            return

        tab_name = self.tab_widget.tabText(index)
        reply = QMessageBox.question(self, "탭 삭제 확인",
                                     f"'{tab_name}' 탭과 그 안의 모든 자산 데이터를 정말로 삭제하시겠습니까?\n"
                                     "이 작업은 되돌릴 수 없습니다.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.asset_manager.delete_tab_data(tab_name):
                QMessageBox.information(self, "탭 삭제", f"'{tab_name}' 탭이 성공적으로 삭제되었습니다.")
            else:
                QMessageBox.warning(self, "탭 삭제 실패", "탭 삭제 중 오류가 발생했습니다.")


    def rename_current_tab(self):
        """현재 선택된 탭의 이름을 변경합니다."""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "탭 이름 변경", "변경할 탭을 선택해주세요.")
            return
        
        old_name = self.tab_widget.tabText(current_index)

        new_name, ok = QInputDialog.getText(self, "탭 이름 변경", "새 탭 이름:", QLineEdit.Normal, old_name)

        if ok and new_name:
            stripped_new_name = new_name.strip()
            if not stripped_new_name:
                QMessageBox.warning(self, "탭 이름 변경 실패", "탭 이름은 비워둘 수 없습니다.")
                return

            if stripped_new_name == old_name:
                QMessageBox.information(self, "탭 이름 변경", "이름이 변경되지 않았습니다.")
                return

            if stripped_new_name in self.asset_manager.get_all_tab_names():
                QMessageBox.warning(self, "탭 이름 변경 실패", f"'{stripped_new_name}' 탭은 이미 존재합니다.")
                return
            
            if self.asset_manager.rename_tab_data_key(old_name, stripped_new_name):
                QMessageBox.information(self, "탭 이름 변경", f"'{old_name}' 탭이 '{stripped_new_name}'(으)로 변경되었습니다.")
                # _tab_tables 딕셔너리 키도 업데이트 (재구축 로직 때문에 필요 없지만 안전하게)
                if old_name in self._tab_tables:
                    self._tab_tables[stripped_new_name] = self._tab_tables.pop(old_name)
            else:
                QMessageBox.warning(self, "탭 이름 변경 실패", "탭 이름 변경 중 오류가 발생했습니다.")
        elif ok: # 사용자가 텍스트를 입력했으나 빈 문자열인 경우 (strip 후)
            QMessageBox.warning(self, "탭 이름 변경 실패", "탭 이름을 입력해야 합니다.")


    def delete_current_tab(self):
        """현재 선택된 탭을 삭제합니다."""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "탭 삭제", "삭제할 탭을 선택해주세요.")
            return
        
        tab_name = self.tab_widget.tabText(current_index)
        
        # 마지막 남은 실제 데이터 탭은 삭제 방지
        if self.tab_widget.count() == 1: 
            QMessageBox.warning(self, "탭 삭제 불가", "마지막 남은 자산 탭은 삭제할 수 없습니다. 최소 하나의 자산 탭이 필요합니다.")
            return

        reply = QMessageBox.question(self, "탭 삭제 확인",
                                     f"'{tab_name}' 탭과 그 안의 모든 자산 데이터를 정말로 삭제하시겠습니까?\n"
                                     "이 작업은 되돌릴 수 없습니다.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.asset_manager.delete_tab_data(tab_name):
                QMessageBox.information(self, "탭 삭제", f"'{tab_name}' 탭이 성공적으로 삭제되었습니다.")
                # 탭 삭제 후 총 금액 업데이트
                self.update_total_amount_display()
            else:
                QMessageBox.warning(self, "탭 삭제 실패", "탭 삭제 중 오류가 발생했습니다.")
                
    # --- CSV 내보내기/가져오기 기능 슬롯 ---
    def export_current_tab_to_csv(self):
        """현재 탭의 자산 데이터를 CSV 파일로 내보냅니다."""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "CSV 내보내기", "내보낼 탭을 선택해주세요.")
            return
        
        tab_name = self.tab_widget.tabText(current_index)

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "CSV 파일로 내보내기", f"{tab_name}_자산.csv", "CSV 파일 (*.csv);;모든 파일 (*)", options=options)
        
        if file_path:
            if self.asset_manager.export_data_to_csv(tab_name, file_path):
                QMessageBox.information(self, "CSV 내보내기 성공", f"'{tab_name}' 탭의 데이터가\n'{file_path}'(으)로 성공적으로 내보내졌습니다.")
            else:
                QMessageBox.warning(self, "CSV 내보내기 실패", "CSV 파일 내보내기 중 오류가 발생했습니다.")

    def import_csv_to_current_tab(self):
        """CSV 파일에서 자산 데이터를 현재 탭으로 가져옵니다."""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "CSV 가져오기", "데이터를 가져올 탭을 선택해주세요.")
            return
        
        tab_name = self.tab_widget.tabText(current_index)

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "CSV 파일 가져오기", "", "CSV 파일 (*.csv);;모든 파일 (*)", options=options)
        
        if file_path:
            reply = QMessageBox.question(self, "CSV 가져오기 옵션",
                                         "기존 탭의 데이터를 지우고 가져오시겠습니까?\n"
                                         "('예'를 누르면 기존 데이터 삭제 후 가져오기, '아니오'를 누르면 기존 데이터에 추가)",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
            
            if reply == QMessageBox.Cancel:
                return

            clear_existing = (reply == QMessageBox.Yes)

            if self.asset_manager.import_data_from_csv(tab_name, file_path, clear_existing=clear_existing):
                QMessageBox.information(self, "CSV 가져오기 성공", f"CSV 파일의 데이터가\n'{tab_name}' 탭으로 성공적으로 가져와졌습니다.")
            else:
                QMessageBox.warning(self, "CSV 가져오기 실패", "CSV 파일 가져오기 중 오류가 발생했습니다.")

    # --- 트레이 아이콘 및 종료 관련 메서드 ---
    def setup_tray_icon(self):
        """시스템 트레이 아이콘을 설정합니다."""
        self.tray_icon = QSystemTrayIcon(qta.icon('mdi.cash-multiple'), self) # 금융 관련 아이콘
        self.tray_icon.setToolTip("자산 관리 프로그램")

        tray_menu = QMenu()
        restore_action = QAction("보이기/숨기기", self)
        restore_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(restore_action)

        exit_action = QAction("종료", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.handle_tray_activation)
        self.tray_icon.show()

    def handle_tray_activation(self, reason):
        """트레이 아이콘 활성화 이벤트를 처리합니다."""
        if reason == QSystemTrayIcon.Trigger: # 클릭 시
            self.toggle_visibility()
        elif reason == QSystemTrayIcon.DoubleClick: # 더블 클릭 시
            self.toggle_visibility()

    def toggle_visibility(self):
        """창의 가시성을 토글합니다."""
        if self.isVisible():
            self.hide()
        else:
            self.showNormal() # 최소화되어 있다면 복원
            self.activateWindow() # 포커스 가져오기

    def closeEvent(self, event):
        """창 닫기 이벤트 핸들러: 트레이 아이콘으로 최소화합니다."""
        if self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            QMessageBox.information(self, "프로그램 최소화", "프로그램이 시스템 트레이로 최소화되었습니다.")
        else:
            event.accept()
