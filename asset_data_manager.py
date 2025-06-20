import json
import os
import csv
import hashlib
from PyQt5.QtCore import QObject, pyqtSignal, QDate

class AssetDataManager(QObject):
    # 탭 목록이 변경되었음을 알리는 시그널 (UI 갱신용)
    tab_list_changed = pyqtSignal()
    # 특정 탭의 데이터가 변경되었음을 알리는 시그널 (변경된 탭 이름 전달)
    data_changed = pyqtSignal(str)
    # 초기 데이터 로드가 완료되었음을 알리는 시그널 (전체 데이터 전달)
    data_loaded = pyqtSignal(dict) 

    def __init__(self, data_file="assets.json"):
        super().__init__()
        self.data_file = data_file
        self.assets = {} # 모든 자산 데이터를 저장할 딕셔너리 {탭이름: [자산1, 자산2, ...]}
        self.last_no = 0 # 자산 고유 번호 생성을 위한 카운터
        self._load_data()

    def _load_data(self):
        """
        데이터 파일을 로드합니다. 파일이 없거나 비어있으면 빈 딕셔너리로 초기화합니다.
        """
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    file_content = f.read().strip()
                    if file_content:
                        self.assets = json.loads(file_content)
                        # self.assets에 저장된 모든 자산의 'no' 값 중 최대값을 찾아 last_no 업데이트
                        self.last_no = self._get_max_asset_no()
                    else:
                        print(f"데이터 파일 '{self.data_file}'이(가) 비어 있습니다. 빈 데이터로 시작합니다.")
                        self.assets = {}
            except json.JSONDecodeError:
                print(f"데이터 파일 '{self.data_file}'이(가) 유효한 JSON 형식이 아닙니다. 빈 데이터로 시작합니다.")
                self.assets = {}
            except Exception as e:
                print(f"데이터 파일 '{self.data_file}' 로드 중 오류 발생: {e}. 빈 데이터로 시작합니다.")
                self.assets = {}
        else:
            print(f"데이터 파일 '{self.data_file}'를 찾을 수 없습니다. 빈 데이터로 시작합니다.")
            self.assets = {}

        # 변경: 기본 '내 자산' 탭 생성 로직 제거
        # if not self.assets:
        #     print("INFO: '내 자산' 탭이 없거나 비어있어 기본 자산 데이터를 추가합니다.")
        #     # AssetDataManager의 add_tab_data 메서드를 직접 호출
        #     self.add_tab_data("내 자산") # 이 메서드는 이미 _save_data와 시그널을 처리합니다.

        # 데이터 로드 완료 시그널 emit
        self.data_loaded.emit(self.assets)


    def _save_data(self):
        """현재 자산 데이터를 파일에 저장합니다."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.assets, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"데이터 파일 '{self.data_file}' 저장 중 오류 발생: {e}")

    def _get_max_asset_no(self):
        """현재 저장된 모든 자산 중 가장 큰 'no' 값을 찾아 반환합니다."""
        max_no = 0
        for tab_name in self.assets:
            for asset in self.assets[tab_name]:
                if 'no' in asset and isinstance(asset['no'], int):
                    max_no = max(max_no, asset['no'])
        return max_no

    def get_all_tab_names(self):
        """현재 존재하는 모든 탭의 이름을 반환합니다."""
        return list(self.assets.keys())

    def get_assets_by_tab(self, tab_name):
        """특정 탭의 모든 자산 목록을 반환합니다. 해당 탭이 없으면 빈 리스트를 반환합니다."""
        return self.assets.get(tab_name, [])

    def add_tab_data(self, tab_name):
        """새로운 탭을 추가하고 파일에 저장합니다."""
        if tab_name in self.assets:
            return False # 이미 존재하는 탭
        self.assets[tab_name] = []
        self._save_data()
        self.tab_list_changed.emit() # 탭 목록 변경 시그널 발생
        return True

    def delete_tab_data(self, tab_name):
        """탭과 해당 탭의 모든 자산 데이터를 삭제합니다."""
        if tab_name not in self.assets:
            return False # 존재하지 않는 탭
        del self.assets[tab_name]
        self._save_data()
        self.tab_list_changed.emit() # 탭 목록 변경 시그널 발생
        return True

    def rename_tab_data_key(self, old_name, new_name):
        """탭 이름을 변경합니다."""
        if old_name not in self.assets:
            return False
        if new_name in self.assets and new_name != old_name:
            return False # 새 이름이 이미 존재함

        # 딕셔너리 순서 유지를 위해 임시 딕셔너리 생성
        temp_assets = {}
        for key, value in self.assets.items():
            if key == old_name:
                temp_assets[new_name] = value
            else:
                temp_assets[key] = value
        self.assets = temp_assets
        
        self._save_data()
        self.tab_list_changed.emit()
        return True

    def add_asset(self, tab_name, asset_data):
        """
        지정된 탭에 새 자산을 추가하고 파일에 저장합니다.
        asset_data 딕셔너리에 'no' 필드를 추가하고,
        만기일이 빈 문자열이면 저장하지 않도록 처리합니다.
        """
        if tab_name not in self.assets:
            print(f"경고: 탭 '{tab_name}'가 존재하지 않아 자산을 추가할 수 없습니다.")
            return False

        self.last_no += 1
        new_asset = asset_data.copy()
        new_asset['no'] = self.last_no
        
        # 만기일이 빈 문자열이면 제거
        if '만기일' in new_asset and not new_asset['만기일'].strip():
            del new_asset['만기일']

        self.assets[tab_name].append(new_asset)
        self._save_data()
        self.data_changed.emit(tab_name) # 해당 탭의 데이터 변경 시그널 발생
        return True

    def update_asset(self, tab_name, original_asset, updated_asset_data):
        """
        지정된 탭에서 기존 자산을 찾아 업데이트하고 파일에 저장합니다.
        original_asset의 'no' 필드를 기준으로 자산을 식별합니다.
        """
        if tab_name not in self.assets:
            print(f"경고: 탭 '{tab_name}'가 존재하지 않습니다.")
            return False

        if 'no' not in original_asset:
            print("오류: 원본 자산에 'no' 필드가 없습니다. 업데이트할 수 없습니다.")
            return False

        original_no = original_asset['no']
        
        found = False
        for i, asset in enumerate(self.assets[tab_name]):
            if 'no' in asset and asset['no'] == original_no:
                # 'no' 필드를 제외한 나머지 필드를 업데이트
                updated_asset_with_no = updated_asset_data.copy()
                updated_asset_with_no['no'] = original_no # 기존 'no' 유지
                
                # 만기일이 빈 문자열이면 제거
                if '만기일' in updated_asset_with_no and not updated_asset_with_no['만기일'].strip():
                    del updated_asset_with_no['만기일']
                elif '만기일' not in updated_asset_with_no:
                     # 만기일이 아예 없으면 (예: 폼에서 입력하지 않은 경우) 기존 데이터에서 만기일이 있다면 제거
                    if '만기일' in self.assets[tab_name][i]:
                        del self.assets[tab_name][i]['만기일']


                self.assets[tab_name][i] = updated_asset_with_no
                found = True
                break
        
        if found:
            self._save_data()
            self.data_changed.emit(tab_name)
            return True
        else:
            print(f"자산 번호 '{original_no}'를 탭 '{tab_name}'에서 찾을 수 없습니다.")
            return False

    def delete_assets(self, tab_name, assets_to_delete):
        """
        지정된 탭에서 선택된 여러 자산을 'no' 필드를 기준으로 삭제합니다.
        """
        if tab_name not in self.assets:
            print(f"경고: 탭 '{tab_name}'가 존재하지 않아 자산을 삭제할 수 없습니다.")
            return False

        original_asset_list = self.assets[tab_name]
        updated_asset_list = []
        deleted_count = 0
        
        # 삭제할 자산의 'no' 값만 집합으로 만듭니다.
        nos_to_delete = {asset['no'] for asset in assets_to_delete if 'no' in asset}

        for asset in original_asset_list:
            if 'no' in asset and asset['no'] in nos_to_delete:
                deleted_count += 1
            else:
                updated_asset_list.append(asset)
        
        self.assets[tab_name] = updated_asset_list
        self._save_data()
        self.data_changed.emit(tab_name)
        
        return deleted_count > 0 # 하나라도 삭제되었으면 True 반환


    def get_total_amount_by_tab(self, tab_name):
        """특정 탭의 모든 자산 금액을 합산하여 반환합니다."""
        total = 0
        for asset in self.assets.get(tab_name, []):
            try:
                # '금액' 필드가 문자열일 경우 숫자만 추출하여 변환
                amount_str = str(asset.get('금액', '0')).replace(',', '').strip()
                total += int(amount_str)
            except ValueError:
                print(f"경고: 유효하지 않은 금액 데이터가 발견되었습니다: {asset.get('금액')}")
                continue
        return total

    def export_data_to_csv(self, tab_name, file_path):
        """
        현재 탭의 자산 데이터를 CSV 파일로 내보냅니다.
        'no' 필드는 CSV에 포함하지 않습니다.
        """
        assets = self.assets.get(tab_name, [])
        if not assets:
            print(f"경고: 탭 '{tab_name}'에 내보낼 자산 데이터가 없습니다.")
            return False

        # CSV 헤더 (No. 필드 제외)
        headers = ["자산 종류", "세부 분류", "자산 명", "금액", "만기일", "알림", "비고"]

        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                for asset in assets:
                    # 'no' 필드를 제외한 딕셔너리 생성
                    row_data = {k: v for k, v in asset.items() if k != 'no'}
                    writer.writerow(row_data)
            return True
        except Exception as e:
            print(f"CSV 파일 내보내기 중 오류 발생: {e}")
            return False

    def import_data_from_csv(self, tab_name, file_path, clear_existing=False):
        """
        CSV 파일에서 자산 데이터를 지정된 탭으로 가져옵니다.
        clear_existing이 True이면 기존 데이터를 삭제하고 가져옵니다.
        """
        if tab_name not in self.assets:
            print(f"오류: 탭 '{tab_name}'이(가) 존재하지 않습니다.")
            return False

        imported_assets = []
        try:
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # CSV 열 이름과 내부 딕셔너리 키를 매핑하여 처리
                    # 필요한 경우 여기서 데이터 유효성 검사 및 타입 변환 수행
                    asset_data = {
                        "자산 종류": row.get("자산 종류", ""),
                        "세부 분류": row.get("세부 분류", ""),
                        "자산 명": row.get("자산 명", ""),
                        "금액": row.get("금액", "0").replace(',', ''), # 금액은 문자열로 읽어와 숫자만 남김
                        "만기일": row.get("만기일", ""),
                        "알림": row.get("알림", ""),
                        "비고": row.get("비고", "")
                    }
                    imported_assets.append(asset_data)
            
            if clear_existing:
                self.assets[tab_name] = [] # 기존 데이터 삭제
            
            # 가져온 각 자산에 새로운 'no' 번호를 할당하여 추가
            for asset in imported_assets:
                self.last_no += 1
                asset['no'] = self.last_no
                self.assets[tab_name].append(asset)

            self._save_data()
            self.data_changed.emit(tab_name)
            return True

        except FileNotFoundError:
            print(f"오류: CSV 파일 '{file_path}'를 찾을 수 없습니다.")
            return False
        except Exception as e:
            print(f"CSV 파일 가져오기 중 오류 발생: {e}")
            return False

