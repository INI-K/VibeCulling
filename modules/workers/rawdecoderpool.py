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



class RawDecoderPool:
    """RAW 디코더 프로세스 풀"""
    def __init__(self, num_processes=None):
        if num_processes is None:
        # 코어 수에 비례하되 상한선 설정
            available_cores = cpu_count()
            num_processes = min(2, max(1, available_cores // 4))
            # 8코어: 2개, 16코어: 4개, 32코어: 8개로 제한
            
        logging.info(f"RawDecoderPool 초기화: {num_processes}개 프로세스")
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.processes = []
        
        # 디코더 프로세스 시작
        for i in range(num_processes):
            p = Process(
                target=decode_raw_in_process, 
                args=(self.input_queue, self.output_queue),
                daemon=True  # 메인 프로세스가 종료하면 함께 종료
            )
            p.start()
            logging.info(f"RAW 디코더 프로세스 #{i+1} 시작됨 (PID: {p.pid})")
            self.processes.append(p)
        
        self.next_task_id = 0
        self.tasks = {}  # task_id -> callback
        self._running = True
    
    def decode_raw(self, file_path, callback):
        """RAW 디코딩 요청 (비동기)"""
        if not self._running:
            print("RawDecoderPool이 이미 종료됨")
            return None
        
        task_id = self.next_task_id
        self.next_task_id += 1
        self.tasks[task_id] = callback
        
        print(f"RAW 디코딩 요청: {os.path.basename(file_path)} (task_id: {task_id})")
        self.input_queue.put((file_path, task_id))
        return task_id
    
    def process_results(self, max_results=5):
        """완료된 결과 처리 (메인 스레드에서 주기적으로 호출)"""
        if not self._running:
            return 0
            
        processed = 0
        while processed < max_results:
            try:
                # non-blocking 확인
                if self.output_queue.empty():
                    break
                    
                result = self.output_queue.get_nowait()
                task_id = result['task_id']
                
                if task_id in self.tasks:
                    callback = self.tasks.pop(task_id)
                    # 성공 여부와 관계없이 콜백 호출
                    callback(result)
                else:
                    logging.warning(f"경고: task_id {task_id}에 대한 콜백을 찾을 수 없음")
                
                processed += 1
                
            except Exception as e:
                logging.error(f"결과 처리 중 오류: {e}")
                break
                
        return processed
    
    def shutdown(self):
        """프로세스 풀 종료"""
        if not self._running:
            print("RawDecoderPool이 이미 종료됨")
            return
            
        print("RawDecoderPool 종료 중...")
        self._running = False
        
        # 모든 프로세스에 종료 신호 전송
        for _ in range(len(self.processes)):
            try:
                self.input_queue.put(None, timeout=0.1) # 타임아웃 추가
            except queue.Full:
                pass # 큐가 꽉 차서 넣을 수 없어도 계속 진행
        
        # 프로세스 종료 대기
        for i, p in enumerate(self.processes):
            p.join(0.5)  # 각 프로세스별로 최대 0.5초 대기
            if p.is_alive():
                logging.info(f"프로세스 #{i+1} (PID: {p.pid})이 응답하지 않아 강제 종료")
                p.terminate()
                p.join(0.1) # 강제 종료 후 정리 시간
                
        self.processes.clear()
        self.tasks.clear()
        
        # 큐 닫기 (자원 누수 방지)
        self.input_queue.close()
        self.output_queue.close()
        
        logging.info("RawDecoderPool 종료 완료")

