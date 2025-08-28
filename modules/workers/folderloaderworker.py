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



class FolderLoaderWorker(QObject):
    """백그라운드 스레드에서 폴더 스캔, 파일 매칭, 정렬 작업을 수행하는 워커"""
    startProcessing = Signal(str, str, str, list, list)
    
    finished = Signal(list, dict, str, str, str)
    progress = Signal(str)
    error = Signal(str, str)

    def __init__(self, raw_extensions, get_datetime_func):
        super().__init__()
        self.raw_extensions = raw_extensions
        self.get_datetime_from_file_fast = get_datetime_func
        self._is_running = True
        
        self.startProcessing.connect(self.process_folders)


    def stop(self):
        self._is_running = False

    @Slot(str, str, str, list, list)
    def process_folders(self, jpg_folder_path, raw_folder_path, mode, raw_file_list_from_main, supported_extensions):
        """메인 처리 함수 (mode에 따라 분기)"""
        self._is_running = True
        try:
            image_files = []
            raw_files = {}

            if mode == 'raw_only':
                self.progress.emit(LanguageManager.translate("RAW 파일 정렬 중..."))
                image_files = sorted(raw_file_list_from_main, key=self.get_datetime_from_file_fast)
            
            else: # 'jpg_with_raw' or 'jpg_only'
                self.progress.emit(LanguageManager.translate("이미지 파일 스캔 중..."))
                target_path = Path(jpg_folder_path)
                temp_image_files = []
                for file_path in target_path.iterdir():
                    if not self._is_running: return
                    if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                        temp_image_files.append(file_path)
                
                if not temp_image_files:
                    self.error.emit(LanguageManager.translate("선택한 폴더에 지원하는 이미지 파일이 없습니다."), LanguageManager.translate("경고"))
                    return

                self.progress.emit(LanguageManager.translate("파일 정렬 중..."))
                image_files = sorted(temp_image_files, key=self.get_datetime_from_file_fast)

                if mode == 'jpg_with_raw' and raw_folder_path:
                    self.progress.emit(LanguageManager.translate("RAW 파일 매칭 중..."))
                    jpg_filenames = {f.stem: f for f in image_files}
                    for file_path in Path(raw_folder_path).iterdir():
                        if not self._is_running: return
                        if file_path.is_file() and file_path.suffix.lower() in self.raw_extensions:
                            if file_path.stem in jpg_filenames:
                                raw_files[file_path.stem] = file_path
            
            if not self._is_running: return
            self.finished.emit(image_files, raw_files, jpg_folder_path, raw_folder_path, mode)

        except Exception as e:
            logging.error(f"백그라운드 폴더 로딩 중 오류: {e}")
            self.error.emit(str(e), LanguageManager.translate("오류"))

