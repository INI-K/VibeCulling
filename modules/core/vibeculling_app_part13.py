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
