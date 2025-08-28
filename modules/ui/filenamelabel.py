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



class FilenameLabel(QLabel):
    """파일명을 표시하는 레이블 클래스, 더블클릭 시 파일 열기"""
    doubleClicked = Signal(str) # 시그널에 파일명(str) 전달

    def __init__(self, text="", fixed_height_padding=40, parent=None):
        super().__init__(parent=parent)
        self._raw_display_text = "" # 아이콘 포함될 수 있는, 화면 표시용 전체 텍스트
        self._actual_filename_for_opening = "" # 더블클릭 시 열어야 할 실제 파일명 (아이콘X)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)

        font = QFont("Arial", UIScaleManager.get("filename_font_size"))
        font.setBold(True)
        self.setFont(font)

        fm = QFontMetrics(font)
        line_height = fm.height()
        fixed_height = line_height + fixed_height_padding
        self.setFixedHeight(fixed_height)

        self.setWordWrap(True)
        self.setStyleSheet(f"color: {ThemeManager.get_color('text')};")
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        
        # 초기 텍스트 설정 (만약 text에 아이콘이 있다면 분리 필요)
        self.set_display_and_actual_filename(text, text.replace("🔗", "")) # 아이콘 제거 시도

    def set_display_and_actual_filename(self, display_text: str, actual_filename: str):
        """표시용 텍스트와 실제 열릴 파일명을 별도로 설정"""
        self._raw_display_text = display_text # 아이콘 포함 가능성 있는 전체 표시 텍스트
        self._actual_filename_for_opening = actual_filename # 아이콘 없는 순수 파일명

        self.setToolTip(self._raw_display_text) # 툴팁에는 전체 표시 텍스트

        # 화면 표시용 텍스트 생략 처리 (아이콘 포함된 _raw_display_text 기준)
        if len(self._raw_display_text) > 17: # 아이콘 길이를 고려하여 숫자 조정 필요 가능성
            # 아이콘이 있다면 아이콘은 유지하면서 앞부분만 생략
            if "🔗" in self._raw_display_text:
                name_part = self._raw_display_text.replace("🔗", "")
                if len(name_part) > 15: # 아이콘 제외하고 15자 초과 시
                    display_text_for_label = name_part[:6] + "..." + name_part[-7:] + "🔗"
                else:
                    display_text_for_label = self._raw_display_text
            else: # 아이콘 없을 때
                display_text_for_label = self._raw_display_text[:6] + "..." + self._raw_display_text[-10:]
        else:
            display_text_for_label = self._raw_display_text

        super().setText(display_text_for_label)

    # setText는 이제 set_display_and_actual_filename을 사용하도록 유도하거나,
    # 이전 setText의 역할을 유지하되 내부적으로 _actual_filename_for_opening을 관리해야 함.
    # 여기서는 set_display_and_actual_filename을 주 사용 메서드로 가정.
    def setText(self, text: str): # 이 메서드는 VibeCullingApp에서 직접 호출 시 주의
        # 아이콘 유무에 따라 실제 열릴 파일명 결정
        actual_name = text.replace("🔗", "")
        self.set_display_and_actual_filename(text, actual_name)

    def text(self) -> str: # 화면에 표시되는 텍스트 반환 (생략된 텍스트)
        return super().text()

    def raw_display_text(self) -> str: # 아이콘 포함된 전체 표시 텍스트 반환
        return self._raw_display_text

    def actual_filename_for_opening(self) -> str: # 실제 열릴 파일명 반환
        return self._actual_filename_for_opening

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """더블클릭 시 _actual_filename_for_opening으로 시그널 발생"""
        if self._actual_filename_for_opening:
            self.doubleClicked.emit(self._actual_filename_for_opening) # 아이콘 없는 파일명 전달

