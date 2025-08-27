"""
앱 데이터 유틸리티 모듈
애플리케이션 데이터 디렉토리 관리 함수들
"""

import os
import platform
from pathlib import Path
import sys


def get_app_data_dir():
    """
    플랫폼에 맞는 애플리케이션 데이터 디렉토리 경로를 반환하고,
    해당 디렉토리가 없으면 생성합니다.

    - Windows: C:\\Users\\<Username>\\AppData\\Roaming\\VibeCulling
    - macOS:   ~/Library/Application Support/VibeCulling
    - Linux:   ~/.config/VibeCulling
    """
    app_name = "VibeCulling"
    home = Path.home()

    if sys.platform == "win32":
        app_data_path = home / "AppData" / "Roaming" / app_name
    elif sys.platform == "darwin":
        app_data_path = home / "Library" / "Application Support" / app_name
    else:
        # Linux 및 기타 Unix 계열
        app_data_path = home / ".config" / app_name

    # 디렉토리가 존재하지 않으면 생성합니다.
    # parents=True: 중간 경로가 없어도 생성
    # exist_ok=True: 이미 존재해도 오류 발생 안 함
    app_data_path.mkdir(parents=True, exist_ok=True)
    
    return app_data_path


