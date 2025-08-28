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



def decode_raw_in_process(input_queue, output_queue):
    """별도 프로세스에서 RAW 디코딩 처리"""
    logging.info(f"RAW 디코더 프로세스 시작됨 (PID: {os.getpid()})")
    try:
        import rawpy
        import numpy as np
    except ImportError as e:
        logging.error(f"RAW 디코더 프로세스 초기화 오류 (모듈 로드 실패): {e}")
        return
    
    memory_warning_shown = False
    last_memory_log_time = 0  # 마지막 메모리 경고 로그 시간
    memory_log_cooldown = 60  # 메모리 경고 로그 출력 간격 (초)
    
    while True:
        try:
            task = input_queue.get()
            if task is None:  # 종료 신호
                logging.info(f"RAW 디코더 프로세스 종료 신호 수신 (PID: {os.getpid()})")
                break
                
            file_path, task_id = task
            
            # 작업 시작 전 메모리 확인
            try:
                memory_percent = psutil.virtual_memory().percent
                current_time = time.time()
                
                # 메모리 경고 로그는 일정 간격으로만 출력
                if memory_percent > 85 and not memory_warning_shown and current_time - last_memory_log_time > memory_log_cooldown:
                    logging.warning(f"경고: 높은 메모리 사용량 ({memory_percent}%) 상태에서 RAW 디코딩 작업 시작")
                    memory_warning_shown = True
                    last_memory_log_time = current_time
                elif memory_percent <= 75:
                    memory_warning_shown = False
                    
                # 메모리가 매우 부족하면 작업 연기 (95% 이상)
                if memory_percent > 95:
                    logging.warning(f"심각한 메모리 부족 ({memory_percent}%): RAW 디코딩 작업 {os.path.basename(file_path)} 연기")
                    # 작업을 큐에 다시 넣고 잠시 대기
                    input_queue.put((file_path, task_id))
                    time.sleep(5)  # 조금 더 길게 대기
                    continue
            except:
                pass  # psutil 사용 불가 시 무시
            
            try:
                with rawpy.imread(file_path) as raw:
                    # 이미지 처리 전 가비지 컬렉션 실행
                    try:
                        import gc
                        gc.collect()
                    except:
                        pass
                        
                    # 이미지 처리
                    rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
                    
                    # 결과 메타데이터 준비
                    result = {
                        'task_id': task_id,
                        'width': rgb.shape[1],
                        'height': rgb.shape[0],
                        'success': True,
                        'file_path': file_path
                    }
                    
                    # 데이터 형태 확인하고 전송 준비
                    if rgb.dtype == np.uint8 and rgb.ndim == 3:
                        # 메모리 공유를 위해 numpy 배열을 바이트로 직렬화
                        result['data'] = rgb.tobytes()
                        result['shape'] = rgb.shape
                        result['dtype'] = str(rgb.dtype)
                        
                        # 큰 데이터는 로그에 출력하지 않음
                        data_size_mb = len(result['data']) / (1024*1024)
                        logging.info(f"RAW 디코딩 완료: {os.path.basename(file_path)} - {rgb.shape}, {data_size_mb:.2f}MB")
                    else:
                        # 예상치 못한 데이터 형식인 경우
                        logging.warning(f"디코딩된 데이터 형식 문제: {rgb.dtype}, shape={rgb.shape}")
                        result['success'] = False
                        result['error'] = f"Unexpected data format: {rgb.dtype}, shape={rgb.shape}"
                    
                    # 처리 결과 전송 전 메모리에서 큰 객체 제거
                    rgb = None
                    
                    # 명시적 가비지 컬렉션
                    try:
                        import gc
                        gc.collect()
                    except:
                        pass
                    
                    output_queue.put(result)
                    
            except Exception as e:
                logging.error(f"RAW 디코딩 중 오류: {os.path.basename(file_path)} - {e}")
                import traceback
                traceback.print_exc()
                output_queue.put({
                    'task_id': task_id, 
                    'success': False, 
                    'file_path': file_path,
                    'error': str(e)
                })
                
        except Exception as main_error:
            logging.error(f"RAW 디코더 프로세스 주 루프 오류: {main_error}")
            import traceback
            traceback.print_exc()
            # 루프 계속 실행: 한 작업이 실패해도 프로세스는 계속 실행

    logging.info(f"RAW 디코더 프로세스 종료 (PID: {os.getpid()})")

