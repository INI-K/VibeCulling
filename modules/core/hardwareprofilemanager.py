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



class HardwareProfileManager:
    """시스템 하드웨어 및 예상 사용 시나리오를 기반으로 성능 프로필을 결정하고 관련 파라미터를 제공하는 클래스."""
    
    _profile = "balanced"
    _system_memory_gb = 8
    _cpu_cores = 4

    PROFILES = {
        "conservative": {
            "name": "저사양 (8GB RAM)",
            "max_imaging_threads": 2, "max_raw_processes": 1, "cache_size_images": 30,
            "preload_range_adjacent": (5, 2), "preload_range_priority": 2, "preload_grid_bg_limit_factor": 0.3,
            "memory_thresholds": {"danger": 88, "warning": 82, "caution": 75},
            "cache_clear_ratios": {"danger": 0.5, "warning": 0.3, "caution": 0.15},
            "idle_preload_enabled": False,
        },
        "balanced": {
            "name": "표준 (16GB RAM)",
            "max_imaging_threads": 3, "max_raw_processes": lambda cores: min(2, max(1, cores // 4)), "cache_size_images": 60,
            "preload_range_adjacent": (8, 3), "preload_range_priority": 3, "preload_grid_bg_limit_factor": 0.5,
            "memory_thresholds": {"danger": 92, "warning": 88, "caution": 80},
            "cache_clear_ratios": {"danger": 0.5, "warning": 0.3, "caution": 0.15},
            "idle_preload_enabled": True, "idle_interval_ms": 2200,
        },
        "enhanced": {
            "name": "상급 (24GB RAM)",
            "max_imaging_threads": 4, "max_raw_processes": lambda cores: min(2, max(1, cores // 4)), "cache_size_images": 80,
            "preload_range_adjacent": (10, 4), "preload_range_priority": 4, "preload_grid_bg_limit_factor": 0.6,
            "memory_thresholds": {"danger": 94, "warning": 90, "caution": 85},
            "cache_clear_ratios": {"danger": 0.5, "warning": 0.3, "caution": 0.15},
            "idle_preload_enabled": True, "idle_interval_ms": 1800,
        },
        "aggressive": {
            "name": "고성능 (32GB RAM)",
            "max_imaging_threads": 4, "max_raw_processes": lambda cores: min(3, max(2, cores // 3)), "cache_size_images": 120,
            "preload_range_adjacent": (12, 5), "preload_range_priority": 5, "preload_grid_bg_limit_factor": 0.75,
            "memory_thresholds": {"danger": 95, "warning": 92, "caution": 88},
            "cache_clear_ratios": {"danger": 0.4, "warning": 0.25, "caution": 0.1},
            "idle_preload_enabled": True, "idle_interval_ms": 1500,
        },
        "extreme": {
            "name": "초고성능 (64GB RAM)",
            "max_imaging_threads": 4, "max_raw_processes": lambda cores: min(4, max(2, cores // 3)), "cache_size_images": 150,
            "preload_range_adjacent": (18, 6), "preload_range_priority": 6, "preload_grid_bg_limit_factor": 0.8,
            "memory_thresholds": {"danger": 96, "warning": 94, "caution": 90},
            "cache_clear_ratios": {"danger": 0.4, "warning": 0.2, "caution": 0.1},
            "idle_preload_enabled": True, "idle_interval_ms": 1200,
        },
        "dominator": {
            "name": "워크스테이션 (96GB+ RAM)",
            "max_imaging_threads": 5, "max_raw_processes": lambda cores: min(8, max(4, cores // 3)), "cache_size_images": 200,
            "preload_range_adjacent": (20, 8), "preload_range_priority": 7, "preload_grid_bg_limit_factor": 0.9,
            "memory_thresholds": {"danger": 97, "warning": 95, "caution": 92},
            "cache_clear_ratios": {"danger": 0.3, "warning": 0.15, "caution": 0.05},
            "idle_preload_enabled": True, "idle_interval_ms": 800,
        }
    }

    @classmethod
    def initialize(cls):
        try:
            cls._system_memory_gb = psutil.virtual_memory().total / (1024 ** 3)
            physical_cores = psutil.cpu_count(logical=False)
            logical_cores = psutil.cpu_count(logical=True)
            cls._cpu_cores = physical_cores if physical_cores is not None and physical_cores > 0 else logical_cores
        except Exception:
            cls._profile = "conservative"
            logging.warning("시스템 사양 확인 실패. 보수적인 성능 프로필을 사용합니다.")
            return
        
        if cls._system_memory_gb >= 90:
            cls._profile = "dominator"
        elif cls._system_memory_gb >= 45:
            cls._profile = "extreme"
        elif cls._system_memory_gb >= 30:
            cls._profile = "aggressive"
        elif cls._system_memory_gb >= 22:
            cls._profile = "enhanced"
        elif cls._system_memory_gb >= 12:
            cls._profile = "balanced"
        else:
            cls._profile = "conservative"
        
        logging.info(f"시스템 사양: {cls._system_memory_gb:.1f}GB RAM, {cls._cpu_cores} Cores. 성능 프로필 '{cls.PROFILES[cls._profile]['name']}' 활성화.")

    @classmethod
    def get(cls, key):
        param = cls.PROFILES[cls._profile].get(key)
        if callable(param):
            return param(cls._cpu_cores)
        return param

    @classmethod
    def get_current_profile_name(cls):
        return cls.PROFILES[cls._profile]["name"]

    @classmethod
    def get_current_profile_key(cls):
        return cls._profile

    @classmethod
    def set_profile_manually(cls, profile_key):
        if profile_key in cls.PROFILES:
            cls._profile = profile_key
            logging.info(f"사용자가 성능 프로필을 수동으로 '{cls.PROFILES[profile_key]['name']}'(으)로 변경했습니다.")
            return True
        return False

