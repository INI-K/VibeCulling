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



class DateFormatManager:
    """날짜 형식 설정을 관리하는 클래스"""
    
    # 날짜 형식 정보
    DATE_FORMATS = {
        "yyyy-mm-dd": "YYYY-MM-DD",
        "mm/dd/yyyy": "MM/DD/YYYY",
        "dd/mm/yyyy": "DD/MM/YYYY"
    }
    
    # 형식별 실제 변환 패턴
    _format_patterns = {
        "yyyy-mm-dd": "%Y-%m-%d",
        "mm/dd/yyyy": "%m/%d/%Y",
        "dd/mm/yyyy": "%d/%m/%Y"
    }
    
    _current_format = "yyyy-mm-dd"  # 기본 형식
    _format_change_callbacks = []  # 형식 변경 시 호출할 콜백 함수
    
    @classmethod
    def format_date(cls, date_str):
        """날짜 문자열을 현재 설정된 형식으로 변환"""
        if not date_str:
            return "▪ -"
        
        # 기존 형식(YYYY:MM:DD HH:MM:SS)에서 datetime 객체로 변환
        try:
            # EXIF 날짜 형식 파싱 (콜론 포함)
            if ":" in date_str:
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            else:
                # 콜론 없는 형식 시도 (다른 포맷의 가능성)
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            
            # 현재 설정된 형식으로 변환하여 반환
            pattern = cls._format_patterns.get(cls._current_format, "%Y-%m-%d")
            # 시간 정보 추가
            return f"▪ {dt.strftime(pattern)} {dt.strftime('%H:%M:%S')}"
        except (ValueError, TypeError) as e:
            # 다른 형식 시도 (날짜만 있는 경우)
            try:
                if ":" in date_str:
                    dt = datetime.strptime(date_str.split()[0], "%Y:%m:%d")
                else:
                    dt = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                pattern = cls._format_patterns.get(cls._current_format, "%Y-%m-%d")
                return f"▪ {dt.strftime(pattern)}"
            except (ValueError, TypeError):
                # 형식이 맞지 않으면 원본 반환
                return f"▪ {date_str}"
    
    @classmethod
    def set_date_format(cls, format_code):
        """날짜 형식 설정 변경"""
        if format_code in cls.DATE_FORMATS:
            cls._current_format = format_code
            # 형식 변경 시 콜백 함수 호출
            for callback in cls._format_change_callbacks:
                callback()
            return True
        return False
    
    @classmethod
    def register_format_change_callback(cls, callback):
        """날짜 형식 변경 시 호출될 콜백 함수 등록"""
        if callable(callback) and callback not in cls._format_change_callbacks:
            cls._format_change_callbacks.append(callback)
    
    @classmethod
    def get_current_format(cls):
        """현재 날짜 형식 코드 반환"""
        return cls._current_format
    
    @classmethod
    def get_available_formats(cls):
        """사용 가능한 날짜 형식 목록 반환"""
        return list(cls.DATE_FORMATS.keys())
    
    @classmethod
    def get_format_display_name(cls, format_code):
        """날짜 형식 코드에 해당하는 표시 이름 반환"""
        return cls.DATE_FORMATS.get(format_code, format_code)

