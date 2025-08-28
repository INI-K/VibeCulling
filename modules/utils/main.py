# Standard library imports
import ctypes
import datetime
import gc
import io
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import logging
import logging.handlers
from functools import partial
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process, Queue, cpu_count, freeze_support

from pathlib import Path
import platform

# Third-party imports
import numpy as np
import piexif
import psutil
import rawpy
from PIL import Image, ImageQt
import pillow_heif

# PySide6 - Qt framework imports
from PySide6.QtCore import (Qt, QEvent, QMetaObject, QObject, QPoint, Slot, QItemSelectionModel, 
                           QThread, QTimer, QUrl, Signal, Q_ARG, QRect, QPointF,
                           QMimeData, QAbstractListModel, QModelIndex, QSize, QSharedMemory)

from PySide6.QtGui import (QAction, QColor, QColorSpace, QDesktopServices, QFont, QGuiApplication, 
                          QImage, QImageReader, QKeyEvent, QMouseEvent, QPainter, QPalette, QIcon,
                          QPen, QPixmap, QTransform, QWheelEvent, QFontMetrics, QKeySequence, QDrag)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                              QDialog, QFileDialog, QFrame, QGridLayout, 
                              QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                              QListView, QStyledItemDelegate, QStyle,
                              QMainWindow, QMenu, QMessageBox, QPushButton, QRadioButton,
                              QScrollArea, QSizePolicy, QSplitter, QTextBrowser,
                              QVBoxLayout, QWidget, QToolTip, QInputDialog, QLineEdit, 
                              QSpinBox, QProgressDialog, QLayout)



def main():
    # PyInstaller로 패키징된 실행 파일을 위한 멀티프로세싱 지원 추가
    freeze_support()

    try:
        pillow_heif.register_heif_opener()
        logging.info("HEIF/HEIC 지원이 활성화되었습니다. (main에서 등록)")
    except Exception as e:
        logging.error(f"HEIF/HEIC 플러그인 등록 실패: {e}")

    # 크로스플랫폼 단일 인스턴스 체크 시작
    lock_file_path = None
    lock_file_handle = None

    try:
        # 1. 플랫폼에 맞는 안전한 앱 데이터 디렉토리 경로 가져오기
        app_data_dir = get_app_data_dir()

        # 2. 잠금 파일 경로 설정
        lock_file_path = app_data_dir / "vibeculling.lock"
        logging.info(f"잠금 파일 위치: {lock_file_path}")

        # 3. 플랫폼별 잠금 로직 (이 부분은 기존과 동일)
        if sys.platform == 'win32':
            # Windows: msvcrt 사용
            import msvcrt
            lock_file_handle = open(str(lock_file_path), 'w')
            msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            # macOS & Linux: fcntl 사용
            import fcntl
            lock_file_handle = open(str(lock_file_path), 'w')
            fcntl.flock(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

    except (IOError, ImportError) as e:
        # 다른 인스턴스가 이미 잠금을 설정했거나 라이브러리 로드 실패
        logging.warning(f"앱이 이미 실행 중이거나 잠금을 획득할 수 없습니다: {e}")
        try:
            temp_app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.warning(None, "VibeCulling", "VibeCulling is already running.")
        except Exception as msg_e:
            logging.error(f"중복 실행 경고창 표시 실패: {msg_e}")
        sys.exit(1)
        # 크로스플랫폼 단일 인스턴스 체크 끝

    # 로그 레벨 설정 (이후 코드는 기존과 동일)
    is_dev_mode = getattr(sys, 'frozen', False) is False
    log_level = logging.DEBUG if is_dev_mode else logging.INFO
    logging.getLogger().setLevel(log_level)
    print(f"VibeCulling 실행 환경: {'개발' if is_dev_mode else '배포'}, 로그 레벨: {logging.getLevelName(log_level)}")

    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

    # 번역 데이터 초기화
    translations = {
        "이미지 불러오기": "Load Images",
        "RAW 불러오기": "Load RAW",
        "폴더 경로": "Folder Path",
        "JPG - RAW 연결": "Link JPG - RAW",
        "JPG + RAW 이동": "Move JPG + RAW",
        "폴더 선택": "Select Folder",
        "미니맵": "Minimap",
        "환산": "Eq. 35mm",
        "테마": "Theme",
        "설정 및 정보": "Settings and Info",
        "정보": "Info",
        "이미지 파일이 있는 폴더 선택": "Select Image Folder",
        "경고": "Warning",
        "선택한 폴더에 JPG 파일이 없습니다.": "No JPG files found in the selected folder.",
        "선택한 폴더에 RAW 파일이 없습니다.": "No RAW files found in the selected folder.",
        "표시할 이미지가 없습니다": "No image to display.",
        "이미지 로드 실패": "Failed to load image",
        "이미지 표시 중 오류 발생": "Error displaying image.",
        "먼저 JPG 파일을 불러와야 합니다.": "Load JPG files first.",
        "RAW 파일이 있는 폴더 선택": "Select RAW Folder",
        "선택한 RAW 폴더에서 매칭되는 파일을 찾을 수 없습니다.": "No matching files found in the selected RAW folder.",
        "RAW 파일 매칭 결과": "RAW File Matching Results",
        "RAW 파일이 매칭되었습니다.\n{count} / {total}": "RAW files matched.\n{count} / {total}",
        "RAW 폴더를 선택하세요": "Select RAW folder",
        "폴더를 선택하세요": "Select folder",
        "완료": "Complete",
        "모든 이미지가 분류되었습니다.": "All images have been sorted.",
        "에러": "Error",
        "오류": "Error",
        "파일 이동 중 오류 발생": "Error moving file.",
        "프로그램 초기화": "Reset App",
        "모든 설정과 로드된 파일을 초기화하시겠습니까?": "Reset all settings and loaded files?",
        "초기화 완료": "Reset Complete",
        "프로그램이 초기 상태로 복원되었습니다.": "App restored to initial state.",
        "상태 로드 오류": "State Load Error",
        "저장된 상태 파일을 읽는 중 오류가 발생했습니다. 기본 설정으로 시작합니다.": "Error reading saved state file. Starting with default settings.",
        "상태를 불러오는 중 오류가 발생했습니다": "Error loading state.",
        "사진 목록": "Photo List",
        "선택된 파일 없음": "No file selected.",
        "파일 경로 없음": "File path not found.",
        "미리보기 로드 실패": "Failed to load preview.",
        "선택한 파일을 현재 목록에서 찾을 수 없습니다.\n목록이 변경되었을 수 있습니다.": "Selected file not found in the current list.\nThe list may have been updated.",
        "이미지 이동 중 오류가 발생했습니다": "Error moving image.",
        "내부 오류로 인해 이미지로 이동할 수 없습니다": "Cannot navigate to image due to internal error.",
        "언어": "Language",
        "날짜 형식": "Date Format",
        "실행 취소 중 오류 발생": "Error during Undo operation.",
        "다시 실행 중 오류 발생": "Error during Redo operation.",
        "초기 설정": "Initial Setup",
        "기본 설정을 선택해주세요.": "Please select your preferences before starting.",
        "확인": "Confirm",
        "컨트롤 패널": "Control Panel",
        "좌측": "Left",
        "우측": "Right",
        "닫기": "Close",
        "단축키 확인": "View Shortcuts",
        "자유롭게 사용, 수정, 배포할 수 있는 오픈소스 소프트웨어입니다.": "Free and open-source software that can be freely used, modified, and distributed.",
        "AGPL-3.0 라이선스 조건에 따라 소스 코드 공개 의무가 있습니다.": "Source code disclosure is required under AGPL-3.0 license terms.",
        "이 프로그램이 마음에 드신다면, 커피 한 잔으로 응원해 주세요.": "If you truly enjoy this app, consider supporting it with a cup of coffee!",
        "QR 코드": "QR Code",
        "후원 QR 코드": "Donation QR Code",
        "네이버페이": "NaverPay",
        "카카오페이": "KakaoPay",
        "피드백 및 업데이트 확인:": "Feedback & Updates:",
        "이미지 로드 중...": "Loading image...",
        "파일명": "Filename",
        "저장된 모든 카메라 모델의 RAW 파일 처리 방식을 초기화하시겠습니까? 이 작업은 되돌릴 수 없습니다.": "Are you sure you want to reset the RAW file processing method for all saved camera models? This action cannot be undone.",
        "모든 카메라의 RAW 처리 방식 설정이 초기화되었습니다.": "RAW processing settings for all cameras have been reset.",
        "알 수 없는 카메라": "Unknown Camera",
        "정보 없음": "N/A",
        "RAW 파일 처리 방식 선택": "Select RAW Processing Method",
        "{camera_model_placeholder}의 RAW 처리 방식에 대해 다시 묻지 않습니다.": "Don't ask again for {camera_model_placeholder} RAW processing method.",
        "{model_name_placeholder}의 원본 이미지 해상도는 <b>{orig_res_placeholder}</b>입니다.<br>{model_name_placeholder}의 RAW 파일에 포함된 미리보기(프리뷰) 이미지의 해상도는 <b>{prev_res_placeholder}</b>입니다.<br>미리보기를 통해 이미지를 보시겠습니까, RAW 파일을 디코딩해서 보시겠습니까?":
            "The original image resolution for {model_name_placeholder} is <b>{orig_res_placeholder}</b>.<br>"
            "The embedded preview image resolution in the RAW file for {model_name_placeholder} is <b>{prev_res_placeholder}</b>.<br>"
            "Would you like to view images using the preview or by decoding the RAW file?",
        "미리보기 이미지 사용 (미리보기의 해상도가 충분하거나 빠른 작업 속도가 중요한 경우.)": "Use Preview Image (if preview resolution is sufficient for you or speed is important.)",
        "RAW 디코딩 (느림. 일부 카메라 호환성 문제 있음.\n미리보기의 해상도가 너무 작거나 원본 해상도가 반드시 필요한 경우에만 사용 권장.)": 
            "Decode RAW File (Slower. Compatibility issues with some cameras.\nRecommended only if preview resolution is too low or original resolution is essential.)",
        "호환성 문제로 {model_name_placeholder}의 RAW 파일을 디코딩 할 수 없습니다.<br>RAW 파일에 포함된 <b>{prev_res_placeholder}</b>의 미리보기 이미지를 사용하겠습니다.<br>({model_name_placeholder}의 원본 이미지 해상도는 <b>{orig_res_placeholder}</b>입니다.)":
            "Due to compatibility issues, RAW files from {model_name_placeholder} cannot be decoded.<br>"
            "The embedded preview image with resolution <b>{prev_res_placeholder}</b> will be used.<br>"
            "(Note: The original image resolution for {model_name_placeholder} is <b>{orig_res_placeholder}</b>.)",
        "RAW 처리 방식 초기화": "Reset RAW Processing Methods",
        "초기화": "Reset",
        "썸네일": "Thumbnails",
        "저장된 모든 카메라 모델의 RAW 파일 처리 방식을 초기화하시겠습니까? 이 작업은 되돌릴 수 없습니다.": "Are you sure you want to reset the RAW file processing method for all saved camera models? This action cannot be undone.",
        "초기화 완료": "Reset Complete",
        "모든 카메라의 RAW 처리 방식 설정이 초기화되었습니다.": "RAW processing settings for all cameras have been reset.",
        "로드된 파일과 현재 작업 상태를 초기화하시겠습니까?": "Are you sure you want to reset loaded files and the current working state?",
        "뷰포트 이동 속도 ⓘ": "Viewport Move Speed ⓘ",
        "사진 확대 중 Shift + WASD 또는 방향키로 뷰포트(확대 부분)를 이동할 때의 속도입니다.": "This is the speed at which the viewport (the zoomed-in area) moves\nwhen you use Shift + WASD or the arrow keys while an image is magnified.",
        "세션 관리": "Session Management", # 팝업창 제목
        "현재 세션 저장": "Save Current Session",
        "세션 이름": "Session Name",
        "저장할 세션 이름을 입력하세요:": "Enter a name for this session:",
        "선택 세션 불러오기": "Load Selected Session",
        "선택 세션 삭제": "Delete Selected Session",
        "저장된 세션 목록 (최대 20개):": "Saved Sessions (Max 20):",
        "저장 오류": "Save Error",
        "세션 이름을 입력해야 합니다.": "Session name cannot be empty.",
        "저장 한도 초과": "Save Limit Exceeded",
        "최대 20개의 세션만 저장할 수 있습니다. 기존 세션을 삭제 후 다시 시도해주세요.": "You can only save up to 20 sessions. Please delete an existing session and try again.",
        "불러오기 오류": "Load Error",
        "선택한 세션을 찾을 수 없습니다.": "The selected session could not be found.",
        "삭제 확인": "Confirm Deletion",
        "'{session_name}' 세션을 정말 삭제하시겠습니까?": "Are you sure you want to delete the session '{session_name}'?",
        "불러오기 완료": "Load Complete",
        "세션을 불러왔습니다.": "Session has been loaded.",
        "불러올 이미지 형식": "Loadable Image Formats",
        "최소 하나 이상의 확장자는 선택되어야 합니다.": "At least one extension must be selected.",
        "선택한 폴더에 지원하는 이미지 파일이 없습니다.": "No supported image files found in the selected folder.",
        "폴더 불러오기": "Load Folder",
        "폴더 내에 일반 이미지 파일과 RAW 파일이 같이 있습니다.\n무엇을 불러오시겠습니까?": "The folder contains both regular image files and RAW files.\nWhat would you like to load?",
        "파일명이 같은 이미지 파일과 RAW 파일을 매칭하여 불러오기": "Match and load image files and RAW files with the same file names",
        "일반 이미지 파일만 불러오기": "Load only regular image files",
        "RAW 파일만 불러오기": "Load only RAW files",
        "선택한 폴더에 지원하는 파일이 없습니다.": "No supported files found in the selected folder.",
        "분류 폴더 개수": "Number of Sorting Folders",
        "마우스 휠 동작": "Mouse Wheel Action",
        "마우스 휠 민감도": "Mouse Wheel Sensitivity",
        "1 (보통)": "1 (Normal)",
        "1/2 (둔감)": "1/2 (Less Sensitive)",
        "1/3 (매우 둔감)": "1/3 (Least Sensitive)",
        "마우스 패닝 감도": "Mouse Panning Sensitivity",
        "100% (정확)": "100% (Precise)",
        "150% (기본값)": "150% (Default)",
        "200% (빠름)": "200% (Fast)",
        "250% (매우 빠름)": "250% (Very Fast)",
        "300% (최고 속도)": "300% (Maximum Speed)",
        "사진 넘기기": "Photo Navigation", 
        "없음": "None",
        "이동 - 폴더 {0}": "Move to Folder {0}",
        "이동 - 폴더 {0} [{1}]": "Move to Folder {0} [{1}]",
        "UI 설정": "UI Settings",
        "작업 설정": "Workflow Settings",
        "도구 및 고급 설정": "Tools & Advanced",
        "새 폴더명을 입력하고 Enter를 누르거나 ✓ 버튼을 클릭하세요.": "Enter a new folder name and press Enter or click the ✓ button.",
        "기준 폴더가 로드되지 않았습니다.": "Base folder has not been loaded.",
        "폴더 생성 실패": "Folder Creation Failed",
        "이미지 이동 중...": "Moving images...",
        "작업 취소됨.\n성공: {success_count}개, 실패: {fail_count}개": "Operation canceled.\nSuccess: {success_count}, Failed: {fail_count}",
        "성공: {success_count}개\n실패: {fail_count}개": "Success: {success_count}\nFailed: {fail_count}",
        "모든 파일 이동 실패: {fail_count}개": "All file moves failed: {fail_count}",
        "파일 열기 실패": "Failed to Open File",
        "연결된 프로그램이 없거나 파일을 열 수 없습니다.": "No associated program or the file cannot be opened.",
        "파일 준비 중": "Preparing Files",
        "쾌적한 작업을 위해 RAW 파일을 준비하고 있습니다.": "Preparing RAW files for a smooth workflow.",
        "잠시만 기다려주세요.": "Please wait a moment.",
        # 단축키 번역 키 시작
        "탐색": "Navigation",
        "WASD / 방향키": "WASD / Arrow Keys",
        "사진 넘기기": "Navigate photos",
        "Shift + WASD/방향키": "Shift + WASD/Arrow Keys",
        "뷰포트 이동 (확대 중에)": "Pan viewport (while zoomed)",
        "Shift + A/D": "Shift + A/D",
        "이전/다음 페이지 (그리드 모드)": "Previous/Next page (in Grid mode)",
        "Enter": "Enter",
        "사진 목록 보기": "Show photo list",
        "F5": "F5",
        "폴더 새로고침": "Refresh folder",
        "보기 설정": "View Settings",
        "G": "G",
        "그리드 모드 켜기/끄기": "Toggle Grid mode",
        "C": "C",
        "A | B 비교 모드 켜기/끄기": "Toggle A | B Compare mode",
        "Space": "Space",
        "줌 전환 (Fit/100%) 또는 그리드에서 확대": "Toggle Zoom (Fit/100%) or Zoom in from Grid",
        "F1 / F2 / F3": "F1 / F2 / F3",
        "줌 모드 변경 (Fit / 100% / 가변)": "Change Zoom mode (Fit / 100% / Variable)",
        "Z / X": "Z / X",
        "줌 아웃 (가변 모드)": "Zoom Out (in Variable mode)",
        "줌 인 (가변 모드)": "Zoom In (in Variable mode)",
        "R": "R",
        "뷰포트 중앙 정렬": "Center viewport",
        "ESC": "ESC",
        "줌 아웃 또는 그리드 복귀": "Zoom out or return to Grid",
        "파일 작업": "File Actions",
        "1 ~ 9": "1 ~ 9",
        "지정한 폴더로 사진 이동": "Move photo to assigned folder",
        "Ctrl + Z": "Ctrl + Z",
        "파일 이동 취소 (Undo)": "Undo file move",
        "Ctrl + Y / Ctrl + Shift + Z": "Ctrl + Y / Ctrl + Shift + Z",
        "파일 이동 다시 실행 (Redo)": "Redo file move",
        "Ctrl + A": "Ctrl + A",
        "페이지 전체 선택 (그리드 모드)": "Select all on page (in Grid mode)",
        "Delete": "Delete",
        "작업 상태 초기화": "Reset working state",
        "G(Grid)": "G(Grid)",
        "C(Compare)": "C(Compare)",
        "Z(Zoom Out) / X(eXpand)": "Z(Zoom Out) / X(eXpand)",
        "R(Reset)": "R(Reset)",
        "Q / E (* 꾹 누르기)": "Q / E (* brief hold)",
        "이미지 회전 (반시계/시계)": "Rotate image (CCW/CW)",
        # 단축키 번역 키 끝
        # EditableFolderPathLabel 및 InfoFolderPathLabel 관련 번역 키
        "새 폴더명을 입력하거나 폴더를 드래그하여 지정하세요.": "Enter a new folder name or drag a folder here.",
        "폴더를 드래그하여 지정하세요.": "Drag a folder here to assign.",
        "더블클릭하면 해당 폴더가 열립니다.": "Double-click to open the folder.",
        "더블클릭하면 해당 폴더가 열립니다 (전체 경로 표시)": "Double-click to open the folder (shows full path).",
        # 누락된 번역키 추가
        "잘못된 폴더명입니다.": "Invalid folder name.",
        "유효하지 않은 폴더입니다.": "Invalid folder.",
        "알림": "Notice",
        "Zoom Fit 모드에서만 드래그 앤 드롭이 가능합니다.": "Drag and drop is only available in Zoom Fit mode.",
        "이동할 이미지가 없습니다.": "No image to move.",
        "선택된 그리드 이미지가 없습니다.": "No grid image selected.",
        "호환성 문제": "Compatibility Issue",
        "RAW 디코딩 실패. 미리보기를 대신 사용합니다.": "RAW decoding failed. Using preview instead.",
        "비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다.": "Drag an image from the thumbnail panel here to compare.\n\n* Images here can only be moved to sorting folders via the right-click menu.",
        "반시계 방향으로 회전": "Rotate 90° CCW",
        "시계 방향으로 회전": "Rotate 90° CW",
        "좌측 이미지와 다른 이미지를 드래그해주세요.": "Please drag a different image from the left canvas.",
        "새 폴더 불러오기": "Load New Folder",
        "현재 진행 중인 작업을 종료하고 새로운 폴더를 불러오시겠습니까?": "Do you want to end the current session and load a new folder?",
        "예": "Yes",
        "취소": "Cancel",
        # 성능 프로필 관련 번역키
        "성능 설정 ⓘ": "Performance Setting ⓘ",
        "저사양 (8GB RAM)": "Low Spec (8GB RAM)",
        "표준 (16GB RAM)": "Standard (16GB RAM, Default)",
        "상급 (24GB RAM)": "Upper-Mid (24GB RAM)",
        "고성능 (32GB RAM)": "Performance (32GB RAM)",
        "초고성능 (64GB RAM)": "Ultra Performance (64GB RAM)",
        "워크스테이션 (96GB+ RAM)": "Workstation (96GB+ RAM)",
        "설정 변경": "Settings Changed",
        "성능 프로필이 '{profile_name}'(으)로 변경되었습니다.": "Performance profile has been changed to '{profile_name}'.",
        "이 설정은 앱을 재시작해야 완전히 적용됩니다.": "This setting will be fully applied after restarting the app.",
        "프로그램을 처음 실행하면 시스템 사양에 맞춰 자동으로 설정됩니다.\n높은 옵션일수록 더 많은 메모리와 CPU 자원을 사용함으로써 더 많은 사진을 백그라운드에서 미리 로드하여 작업 속도를 높입니다.\n프로그램이 시스템을 느리게 하거나 메모리를 너무 많이 차지하는 경우 낮은 옵션으로 변경해주세요.\n특히 고용량 사진을 다루는 경우 높은 옵션은 시스템에 큰 부하를 줄 수 있습니다.":
        "This profile is automatically set based on your system specifications when the app is first launched.\nHigher options use more memory and CPU resources to preload more photos in the background, increasing workflow speed.\nIf the application slows down your system or consumes too much memory, please change to a lower option.\nEspecially when dealing with large, high-resolution photos, higher options can put a significant load on your system.",
        # 프로그램 초기화 관련 번역
        "프로그램 설정 초기화": "Reset App Settings",
        "초기화 확인": "Confirm Reset",
        "모든 설정을 초기화하고 프로그램을 종료하시겠습니까?\n이 작업은 되돌릴 수 없습니다.": "Are you sure you want to reset all settings and exit the application?\nThis action cannot be undone.",
        "재시작 중...": "Restarting...",
        "설정이 초기화되었습니다. 프로그램을 재시작합니다.": "Settings have been reset. The application will now restart.",
        "폴더를 읽는 중입니다...": "Reading folder...",
        "이미지 파일 스캔 중...": "Scanning image files...",
        "파일 정렬 중...": "Sorting files...",
        "RAW 파일 매칭 중...": "Matching RAW files...",
        "RAW 파일 정렬 중...": "Sorting RAW files...",
        "{count}개 선택됨": "Selected: {count}",
        "작업 초기화 확인": "Confirm Action",
        "현재 작업을 종료하고 이미지 폴더를 닫으시겠습니까?": "Are you sure you want to end the current session and close the image folder?",
        "RAW 연결 해제": "Unlink RAW Files",
        "현재 JPG 폴더와의 RAW 파일 연결을 해제하시겠습니까?": "Are you sure you want to unlink the RAW files from the current JPG folder?",
        "지정한 폴더로 사진 복사": "Copy photo to assigned folder",
        "{filename} 복사 완료": "{filename} copied.",
        "이미지 {count}개 복사 완료": "{count} images copied.",
    }
    
    LanguageManager.initialize_translations(translations)

    app = QApplication(sys.argv)

    UIScaleManager.initialize()
    application_font = QFont("Arial", UIScaleManager.get("font_size", 10))
    app.setFont(application_font)

    window = VibeCullingApp()

    if not window.load_state():
        logging.info("main: load_state가 False를 반환하여 애플리케이션을 시작하지 않습니다.")
        sys.exit(0)

    window.show()

    if hasattr(window, 'is_first_run') and window.is_first_run:
        QTimer.singleShot(100, window.show_first_run_settings_popup_delayed)

    exit_code = app.exec()

    # 프로그램 종료 시 잠금 해제 및 파일 삭제
    if lock_file_handle:
        try:
            if sys.platform == 'win32':
                # msvcrt를 다시 import 해야 할 수 있으므로 안전하게 처리
                import msvcrt
                msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
            lock_file_handle.close()
        except Exception as e:
            logging.warning(f"잠금 해제 중 오류: {e}")

    if lock_file_path and lock_file_path.exists():
        try:
            lock_file_path.unlink()
        except Exception as e:
            logging.warning(f"잠금 파일 삭제 중 오류: {e}")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
