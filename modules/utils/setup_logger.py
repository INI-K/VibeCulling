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



def setup_logger():
    # 로그 디렉터리 생성 (실행 파일과 동일한 위치에 logs 폴더 생성)
    if getattr(sys, 'frozen', False):
        # PyInstaller로 패키징된 경우
        app_dir = Path(sys.executable).parent
    else:
        # 일반 스크립트로 실행된 경우
        app_dir = Path(__file__).parent
        
    # 실행 파일과 같은 위치에 logs 폴더 생성
    log_dir = app_dir / "logs"
    os.makedirs(log_dir, exist_ok=True)

    # --- 오래된 로그 파일 정리 로직 ---
    try:
        # 1. 로그 디렉토리 내의 모든 파일 목록 가져오기
        log_files = [f for f in os.listdir(log_dir) if f.startswith("vibeculling_") and f.endswith(".log")]
        
        # 2. 파일이 3개 초과일 경우에만 정리 수행
        if len(log_files) > 3:
            # 3. 파일명을 기준으로 내림차순 정렬 (최신 파일이 위로 오도록)
            log_files.sort(reverse=True)
            
            # 4. 보관할 파일(최신 3개)을 제외한 나머지 파일 목록 생성
            files_to_delete = log_files[3:]
            
            # 5. 오래된 파일 삭제
            for filename in files_to_delete:
                file_path = log_dir / filename
                try:
                    os.remove(file_path)
                    logging.info(f"오래된 로그 파일 삭제: {filename}")
                except OSError as e:
                    logging.warning(f"로그 파일 삭제 실패: {filename}, 오류: {e}")
    except Exception as e:
        # 이 과정에서 오류가 발생해도 로깅 시스템의 핵심 기능은 계속되어야 함
        logging.warning(f"오래된 로그 파일 정리 중 오류 발생: {e}")

    # 현재 날짜로 로그 파일명 생성
    log_filename = datetime.now().strftime("vibeculling_%Y%m%d.log")
    log_path = log_dir / log_filename
    
    # 로그 형식 설정
    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 루트 로거 설정
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 개발 환경에서는 DEBUG, 배포 환경에서는 INFO 또는 WARNING
    
    # 파일 핸들러 설정 (로테이션 적용)
    # RotatingFileHandler의 backupCount는 동일한 실행 세션 내에서의 로테이션을 관리하므로,
    # 앱 시작 시 파일을 정리하는 위의 로직과 함께 사용하면 좋습니다.
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)
    
    # 콘솔 핸들러 설정 (디버깅용)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 콘솔에는 중요한 메시지만 표시
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)
    
    # 버전 및 시작 메시지 로깅
    logging.info("VibeCulling 시작 (버전: 25.08.06)")
    
    return logger
# 로거 초기화
logger = setup_logger()

