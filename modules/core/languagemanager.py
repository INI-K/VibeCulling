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



class LanguageManager:
    """언어 설정 및 번역을 관리하는 클래스"""
    
    # 사용 가능한 언어
    LANGUAGES = {
        "en": "English",
        "ko": "한국어"
    }
    
    # 번역 데이터
    _translations = {
        "en": {},  # 영어 번역 데이터는 아래에서 초기화
        "ko": {}   # 한국어는 기본값이므로 필요 없음
    }
    
    _current_language = "en"  # 기본 언어
    _language_change_callbacks = []  # 언어 변경 시 호출할 콜백 함수 목록
    
    @classmethod
    def initialize_translations(cls, translations_data):
        """번역 데이터 초기화"""
        # 영어는 key-value 반대로 저장 (한국어->영어 매핑)
        for ko_text, en_text in translations_data.items():
            cls._translations["en"][ko_text] = en_text
    
    @classmethod
    def translate(cls, text_id):
        """텍스트 ID에 해당하는 번역 반환"""
        if cls._current_language == "ko":
            return text_id  # 한국어는 원래 ID 그대로 사용
        
        translations = cls._translations.get(cls._current_language, {})
        return translations.get(text_id, text_id)  # 번역 없으면 원본 반환
    
    @classmethod
    def set_language(cls, language_code):
        """언어 설정 변경"""
        if language_code in cls.LANGUAGES:
            cls._current_language = language_code
            # 언어 변경 시 콜백 함수 호출
            for callback in cls._language_change_callbacks:
                callback()
            return True
        return False
    
    @classmethod
    def register_language_change_callback(cls, callback):
        """언어 변경 시 호출될 콜백 함수 등록"""
        if callable(callback) and callback not in cls._language_change_callbacks:
            cls._language_change_callbacks.append(callback)
    
    @classmethod
    def get_current_language(cls):
        """현재 언어 코드 반환"""
        return cls._current_language
    
    @classmethod
    def get_available_languages(cls):
        """사용 가능한 언어 목록 반환"""
        return list(cls.LANGUAGES.keys())
    
    @classmethod
    def get_language_name(cls, language_code):
        """언어 코드에 해당하는 언어 이름 반환"""
        return cls.LANGUAGES.get(language_code, language_code)

