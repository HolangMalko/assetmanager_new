print("DEBUG: 스크립트 실행 시작 지점.") # 스크립트 시작 시 출력되는 메시지 추가

import os
from PIL import Image, ImageDraw, ImageFont # ImageFont는 현재 사용되지 않지만, 다른 텍스트 관련 작업에 유용할 수 있으므로 유지
import sys # sys 모듈 추가 (Pillow 버전 확인용)

def create_down_arrow_image(filename="down_arrow_image.png", size=(64, 64), color=(0, 0, 0)):
    """
    지정된 크기와 색상으로 아래쪽 화살표 PNG 이미지를 생성합니다.

    Args:
        filename (str): 저장될 파일 이름 (예: "down_arrow_image.png").
        size (tuple): 이미지의 너비와 높이 (픽셀 단위, 예: (64, 64)).
        color (tuple): 화살표의 색상 (RGB 튜플, 예: (0, 0, 0) for black).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, filename)

    print(f"DEBUG: Python 버전: {sys.version}") # Python 버전 출력
    try:
        from PIL import __version__ as pillow_version
        print(f"DEBUG: Pillow 버전: {pillow_version}") # Pillow 버전 출력
    except Exception:
        print("DEBUG: Pillow 버전 정보를 가져올 수 없습니다.")

    print(f"DEBUG: 현재 작업 디렉토리 (CWD): '{os.getcwd()}'") # 현재 작업 디렉토리 출력
    print(f"DEBUG: 스크립트가 위치한 디렉토리: '{script_dir}'")
    print(f"DEBUG: 이미지 저장 시도 경로: '{output_path}'")

    try:
        # 투명 배경을 가진 새 이미지 생성 (RGBA: Red, Green, Blue, Alpha)
        img = Image.new('RGBA', size, (255, 255, 255, 0)) # 흰색 배경에 완전 투명
        draw = ImageDraw.Draw(img)

        # 화살표 그리기
        # 간단한 삼각형으로 화살표 표현
        width, height = size
        # 화살표 삼각형의 꼭지점 좌표
        points = [
            (width / 2, height / 4),       # 위쪽 꼭지점 (중앙)
            (width / 4, height * 3 / 4),   # 왼쪽 아래 꼭지점
            (width * 3 / 4, height * 3 / 4) # 오른쪽 아래 꼭지점
        ]
        draw.polygon(points, fill=color)

        print(f"DEBUG: 이미지 객체 생성 완료. 파일 저장 시도 중...") # 저장 직전 디버그 정보 추가
        img.save(output_path)
        print(f"'{filename}' 파일이 성공적으로 '{output_path}'에 생성되었습니다.")

    except ImportError:
        print("오류: Pillow 라이브러리가 설치되어 있지 않습니다. 'pip install Pillow'를 실행하여 설치해 주세요.")
    except PermissionError:
        print(f"오류: 파일 쓰기 권한이 없습니다. '{output_path}' 경로에 이미지를 저장할 권한이 있는지 확인해 주세요.")
        print("관리자 권한으로 터미널을 실행하거나 다른 폴더에서 시도해 보세요.")
    except Exception as e:
        print(f"예상치 못한 오류가 발생했습니다: {e}")
        # 오류 발생 시 더 자세한 정보를 위해 traceback 출력
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_down_arrow_image()
