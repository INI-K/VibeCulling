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



class ThemeManager:

    _UI_COLORS_DEFAULT = {
        "accent": "#848484",        # 강조색
        "accent_hover": "#555555",  # 강조색 호버 상태(밝음)
        "accent_pressed": "#222222",# 강조색 눌림 상태(어두움)
        "text": "#D8D8D8",          # 일반 텍스트 색상
        "text_disabled": "#595959", # 비활성화된 텍스트 색상
        "bg_primary": "#333333",    # 기본 배경색
        "bg_secondary": "#444444",  # 버튼 등 배경색
        "bg_hover": "#555555",      # 호버 시 배경색
        "bg_pressed": "#222222",    # 눌림 시 배경색
        "bg_disabled": "#222222",   # 비활성화 배경색
        "border": "#555555",        # 테두리 색상
    }
    _UI_COLORS_SONY = {
        "accent": "#FF6600",
        "accent_hover": "#FF6600",
        "accent_pressed": "#CC5200",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_NIKON = {
        "accent": "#FFE100",
        "accent_hover": "#FFE100",
        "accent_pressed": "#CCB800",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_CANON = {
        "accent": "#CC0000",
        "accent_hover": "#CC0000",
        "accent_pressed": "#A30000",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_FUJIFILM = {
        "accent": "#01916D",
        "accent_hover": "#01916D",
        "accent_pressed": "#016954",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_PANASONIC = {
        "accent": "#0041C0",
        "accent_hover": "#0041C0",
        "accent_pressed": "#002D87",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_LEICA = {
        "accent": "#E20612",
        "accent_hover": "#E20612",
        "accent_pressed": "#B00000",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_OLYMPUS = {
        "accent": "#08107B",
        "accent_hover": "#08107B",
        "accent_pressed": "#050A5B",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_SAMSUNG = {
        "accent": "#1428A0",
        "accent_hover": "#1428A0",
        "accent_pressed": "#101F7A",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_PENTAX = {
        "accent": "#01CA47",
        "accent_hover": "#01CA47",
        "accent_pressed": "#019437",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_RICOH = {
        "accent": "#D61B3E",
        "accent_hover": "#D61B3E",
        "accent_pressed": "#B00030",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }   

    # 모든 테마 저장
    THEMES = {
        "default": _UI_COLORS_DEFAULT,
        "SONY": _UI_COLORS_SONY,
        "CANON": _UI_COLORS_CANON,
        "NIKON": _UI_COLORS_NIKON,
        "FUJIFILM": _UI_COLORS_FUJIFILM,
        "PANASONIC": _UI_COLORS_PANASONIC,
        "RICOH": _UI_COLORS_RICOH,
        "LEICA": _UI_COLORS_LEICA,
        "OLYMPUS": _UI_COLORS_OLYMPUS,
        "PENTAX": _UI_COLORS_PENTAX,
        "SAMSUNG": _UI_COLORS_SAMSUNG,
    }
    
    _current_theme = "default"  # 현재 테마
    _theme_change_callbacks = []  # 테마 변경 시 호출할 콜백 함수 목록
    
    @classmethod
    def generate_radio_button_style(cls):
        """현재 테마와 UI 스케일에 맞는 라디오 버튼 스타일시트를 생성합니다."""
        return f"""
            QRadioButton {{
                color: {cls.get_color('text')};
                padding: {UIScaleManager.get("radiobutton_padding")}px;
            }}
            QRadioButton::indicator {{
                width: {UIScaleManager.get("radiobutton_size")}px;
                height: {UIScaleManager.get("radiobutton_size")}px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {cls.get_color('accent')};
                border: {UIScaleManager.get("radiobutton_border")}px solid {cls.get_color('accent')};
                border-radius: {UIScaleManager.get("radiobutton_border_radius")}px;
            }}
            QRadioButton::indicator:unchecked {{
                background-color: {cls.get_color('bg_primary')};
                border: {UIScaleManager.get("radiobutton_border")}px solid {cls.get_color('border')};
                border-radius: {UIScaleManager.get("radiobutton_border_radius")}px;
            }}
            QRadioButton::indicator:unchecked:hover {{
                border: {UIScaleManager.get("radiobutton_border")}px solid {cls.get_color('text_disabled')};
            }}
        """

    @classmethod
    def generate_checkbox_style(cls):
        """현재 테마와 UI 스케일에 맞는 체크박스 스타일시트를 생성합니다."""
        return f"""
            QCheckBox {{
                color: {cls.get_color('text')};
                padding: {UIScaleManager.get("checkbox_padding")}px;
            }}
            QCheckBox:disabled {{
                color: {cls.get_color('text_disabled')};
            }}
            QCheckBox::indicator {{
                width: {UIScaleManager.get("checkbox_size")}px;
                height: {UIScaleManager.get("checkbox_size")}px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {cls.get_color('accent')};
                border: {UIScaleManager.get("checkbox_border")}px solid {cls.get_color('accent')};
                border-radius: {UIScaleManager.get("checkbox_border_radius")}px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {cls.get_color('bg_primary')};
                border: {UIScaleManager.get("checkbox_border")}px solid {cls.get_color('border')};
                border-radius: {UIScaleManager.get("checkbox_border_radius")}px;
            }}
            QCheckBox::indicator:unchecked:hover {{
                border: {UIScaleManager.get("checkbox_border")}px solid {cls.get_color('text_disabled')};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                border: {UIScaleManager.get("checkbox_border")}px solid {cls.get_color('text_disabled')};
            }}
        """

    @classmethod
    def generate_main_button_style(cls):
        """현재 테마에 맞는 기본 버튼 스타일시트를 생성합니다."""
        return f"""
            QPushButton {{
                background-color: {cls.get_color('bg_secondary')};
                color: {cls.get_color('text')};
                border: none;
                padding: {UIScaleManager.get("button_padding")}px;
                border-radius: 1px;
                min-height: {UIScaleManager.get("button_min_height")}px;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('accent_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('accent_pressed')};
            }}
            QPushButton:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                color: {cls.get_color('text_disabled')};
                opacity: 0.7;
            }}
        """

    @classmethod
    def generate_dynamic_height_button_style(cls):
        """수직 패딩이 없고 수평 패딩만 있는 버튼 스타일을 생성합니다."""
        horizontal_padding = UIScaleManager.get("button_padding")
        return f"""
            QPushButton {{
                background-color: {cls.get_color('bg_secondary')};
                color: {cls.get_color('text')};
                border: none;
                /* 수직 패딩은 0, 수평 패딩은 유지 */
                padding: 0px {horizontal_padding}px;
                border-radius: 1px;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('accent_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('accent_pressed')};
            }}
            QPushButton:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                color: {cls.get_color('text_disabled')};
                opacity: 0.7;
            }}
        """

    @classmethod
    def generate_action_button_style(cls):
        """현재 테마에 맞는 액션 버튼(X, ✓) 스타일시트를 생성합니다."""
        return f"""
            QPushButton {{
                background-color: {cls.get_color('bg_secondary')};
                color: {cls.get_color('text')};
                border: none;
                padding: 4px;
                border-radius: 1px;
                min-height: {UIScaleManager.get("button_min_height")}px;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('accent_hover')};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('accent_pressed')};
                color: white;
            }}
            QPushButton:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                color: {cls.get_color('text_disabled')};
            }}
        """

    @classmethod
    def get_color(cls, color_key):
        """현재 테마에서 색상 코드 가져오기"""
        return cls.THEMES[cls._current_theme][color_key]
    
    @classmethod
    def set_theme(cls, theme_name):
        """테마 변경하고 모든 콜백 함수 호출"""
        if theme_name in cls.THEMES:
            cls._current_theme = theme_name
            # 모든 콜백 함수 호출
            for callback in cls._theme_change_callbacks:
                callback()
            return True
        return False
    
    @classmethod
    def register_theme_change_callback(cls, callback):
        """테마 변경 시 호출될 콜백 함수 등록"""
        if callable(callback) and callback not in cls._theme_change_callbacks:
            cls._theme_change_callbacks.append(callback)
    
    @classmethod
    def get_current_theme_name(cls):
        """현재 테마 이름 반환"""
        return cls._current_theme
    
    @classmethod
    def get_available_themes(cls):
        """사용 가능한 모든 테마 이름 목록 반환"""
        return list(cls.THEMES.keys())

