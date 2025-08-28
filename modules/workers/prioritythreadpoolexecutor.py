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



class PriorityThreadPoolExecutor(ThreadPoolExecutor):
    """우선순위를 지원하는 스레드 풀"""
    
    def __init__(self, max_workers=None, thread_name_prefix=''):
        super().__init__(max_workers=max_workers, thread_name_prefix=thread_name_prefix)
        
        # 우선순위별 작업 큐
        self.task_queues = {
            'high': queue.Queue(),    # 현재 보는 이미지
            'medium': queue.Queue(),  # 다음/인접 이미지
            'low': queue.Queue()      # 나머지 이미지
        }
        
        self.shutdown_flag = False
        self.queue_processor_thread = threading.Thread(
            target=self._process_priority_queues,
            daemon=True,
            name=f"{thread_name_prefix}-QueueProcessor"
        )
        self.queue_processor_thread.start()
    
    def _process_priority_queues(self):
        """우선순위 큐를 처리하는 스레드 함수"""
        while not self.shutdown_flag:
            task_info = None
            
            try:
                # 1. 높은 우선순위 큐 먼저 확인
                task_info = self.task_queues['high'].get_nowait()
            except queue.Empty:
                try:
                    # 2. 중간 우선순위 큐 확인
                    task_info = self.task_queues['medium'].get_nowait()
                except queue.Empty:
                    try:
                        # 3. 낮은 우선순위 큐 확인
                        task_info = self.task_queues['low'].get_nowait()
                    except queue.Empty:
                        # 모든 큐가 비어있으면 잠시 대기
                        time.sleep(0.05)
                        continue  # 루프의 처음으로 돌아가 다시 확인

            # task_info가 성공적으로 가져와졌다면 작업 제출
            if task_info:
                # task_info는 (wrapper_function, args, kwargs) 튜플
                try:
                    super().submit(task_info[0], *task_info[1], **task_info[2])
                except Exception as e:
                    logging.error(f"작업 제출 실패: {e}")
    
    def submit_with_priority(self, priority, fn, *args, **kwargs):
        """우선순위와 함께 작업 제출"""
        if priority not in self.task_queues:
            priority = 'low'  # 기본값
        
        from concurrent.futures import Future
        future = Future()

        # 실제 실행될 함수를 래핑하여 future 결과를 설정하도록 함
        def wrapper():
            try:
                result = fn(*args, **kwargs)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        # 큐에 (래핑된 함수, 빈 인자, 빈 키워드 인자, future 객체)를 추가
        self.task_queues[priority].put((wrapper, (), {}))
        return future
    
    def shutdown(self, wait=True, cancel_futures=False):
        """스레드 풀 종료"""
        self.shutdown_flag = True
        super().shutdown(wait=wait, cancel_futures=cancel_futures)

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

