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



class InfoFolderPathLabel(QLabel):
    """
    JPG/RAW 폴더 경로를 표시하기 위한 QLabel 기반 레이블. (기존 FolderPathLabel)
    2줄 높이, 줄 바꿈, 폴더 드래그 호버 효과를 지원합니다.
    """
    doubleClicked = Signal(str)
    folderDropped = Signal(str) # 폴더 경로만 전달

    def __init__(self, text="", parent=None):
        super().__init__(parent=parent)
        self.full_path = ""
        self.original_style = ""
        self.folder_index = -1 # 기본값 설정
        
        fixed_height_padding = UIScaleManager.get("folder_label_padding")
        
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(LanguageManager.translate("더블클릭하면 해당 폴더가 열립니다 (전체 경로 표시)"))
        font = QFont("Arial", UIScaleManager.get("font_size"))
        self.setFont(font)
        fm = QFontMetrics(font)
        line_height = fm.height()
        default_height = (line_height * 2) + fixed_height_padding
        self.setFixedHeight(default_height)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setAcceptDrops(True)
        
        self.set_style(is_valid=False)
        self.original_style = self.styleSheet()
        self.setText(text)

    def set_folder_index(self, index):
        """폴더 인덱스를 저장합니다."""
        self.folder_index = index

    def set_style(self, is_valid):
        """경로 유효성에 따라 스타일을 설정합니다."""
        if is_valid:
            style = f"""
                QLabel {{
                    color: #AAAAAA;
                    padding: 5px;
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border-radius: 1px;
                }}
            """
        else:
            style = f"""
                QLabel {{
                    color: {ThemeManager.get_color('text_disabled')};
                    padding: 5px;
                    background-color: {ThemeManager.get_color('bg_disabled')};
                    border-radius: 1px;
                }}
            """
        self.setStyleSheet(style)
        self.original_style = style

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and Path(urls[0].toLocalFile()).is_dir():
                event.acceptProposedAction()
                self.setStyleSheet(f"""
                    QLabel {{
                        color: #AAAAAA;
                        padding: 5px;
                        background-color: {ThemeManager.get_color('bg_primary')};
                        border: 2px solid {ThemeManager.get_color('accent')};
                        border-radius: 1px;
                    }}
                """)
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.original_style)

    def dropEvent(self, event):
        self.setStyleSheet(self.original_style)
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            if Path(file_path).is_dir():
                self.folderDropped.emit(file_path)
                event.acceptProposedAction()
                return
        event.ignore()

    def setText(self, text: str):
        self.full_path = text
        self.setToolTip(text)
        
        # 긴 경로 생략 로직
        max_length = 40
        prefix_length = 13
        suffix_length = 24
        # QGuiApplication.primaryScreen()을 사용하여 현재 화면의 비율을 얻는 것이 더 안정적입니다.
        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            aspect_ratio = geometry.width() / geometry.height() if geometry.height() else 0
            if abs(aspect_ratio - 1.6) < 0.1: # 대략 16:10 비율
                max_length=30; prefix_length=11; suffix_length=11

        if len(text) > max_length:
            display_text = text[:prefix_length] + "..." + text[-suffix_length:]
        else:
            display_text = text
        super().setText(display_text)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.full_path and self.full_path != LanguageManager.translate("폴더 경로"):
            self.doubleClicked.emit(self.full_path)

