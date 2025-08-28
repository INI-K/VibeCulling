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



class CopyWorker(QObject):
    """백그라운드 스레드에서 파일 복사를 순차적으로 처리하는 워커"""
    copyFinished = Signal(str)
    copyFailed = Signal(str) # <-- 실패 신호 추가

    def __init__(self, copy_queue, parent_app):
        super().__init__()
        self.copy_queue = copy_queue
        self.parent_app = parent_app
        self._is_running = True

    def stop(self):
        self._is_running = False

    def _copy_single_file(self, source_path, target_folder):
        """파일을 대상 폴더로 복사하고, 이름 충돌 시 새 이름을 부여합니다."""
        if not source_path or not target_folder:
            return None, "Source or target is missing." # 오류 메시지 반환
        target_dir = Path(target_folder)
        target_path = target_dir / source_path.name

        if target_path.exists():
            counter = 1
            while True:
                new_name = f"{source_path.stem}_{counter}{source_path.suffix}"
                new_target_path = target_dir / new_name
                if not new_target_path.exists():
                    target_path = new_target_path
                    break
                counter += 1
        
        try:
            shutil.copy2(str(source_path), str(target_path))
            logging.info(f"파일 복사: {source_path} -> {target_path}")
            return target_path, None # 성공 시 (경로, None) 반환
        except Exception as e:
            error_message = f"{source_path.name}: {str(e)}"
            logging.error(f"파일 복사 실패: {error_message}")
            return None, error_message # 실패 시 (None, 오류 메시지) 반환

    @Slot()
    def process_queue(self):
        """큐에 작업이 들어올 때까지 대기하고, 작업을 순차적으로 처리합니다."""
        while self._is_running:
            try:
                task = self.copy_queue.get()

                if task is None or not self._is_running:
                    break

                files_to_copy, target_folder, raw_files_dict, copy_raw_flag = task
                
                copied_count = 0
                failed_files = []
                for jpg_path in files_to_copy:
                    _, error = self._copy_single_file(jpg_path, target_folder)
                    if error:
                        failed_files.append(error)
                    else:
                        copied_count += 1
                        if copy_raw_flag:
                            raw_path = raw_files_dict.get(jpg_path.stem)
                            if raw_path:
                                _, raw_error = self._copy_single_file(raw_path, target_folder)
                                if raw_error:
                                    failed_files.append(raw_error)

                if failed_files:
                    fail_msg_key = "다음 파일 복사에 실패했습니다:\n\n"
                    self.copyFailed.emit(LanguageManager.translate(fail_msg_key) + "\n".join(failed_files))

                if copied_count > 0:
                    if len(files_to_copy) == 1:
                        filename = files_to_copy[0].name
                        msg_key = "{filename} 복사 완료"
                        message = LanguageManager.translate(msg_key).format(filename=filename)
                    else:
                        msg_key = "이미지 {count}개 복사 완료"
                        message = LanguageManager.translate(msg_key).format(count=copied_count)
                    
                    self.copyFinished.emit(message)

            except Exception as e:
                logging.error(f"CopyWorker 처리 중 오류: {e}")



