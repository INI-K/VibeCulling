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



class EditableFolderPathLabel(QLineEdit):
    """
    분류 폴더 경로를 위한 QLineEdit 기반 위젯.
    상태에 따라 편집 가능/읽기 전용 모드를 전환하며 하위 폴더 생성을 지원합니다.
    """
    STATE_DISABLED = 0
    STATE_EDITABLE = 1
    STATE_SET = 2

    doubleClicked = Signal(str)
    imageDropped = Signal(int, str)
    folderDropped = Signal(int, str)
    stateChanged = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.full_path = ""
        self.folder_index = -1
        self._current_state = self.STATE_DISABLED
        self.original_style = ""
        
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.set_state(self.STATE_DISABLED)

    def set_folder_index(self, index):
        self.folder_index = index
        fm = QFontMetrics(self.font())
        line_height = fm.height()
        padding = UIScaleManager.get("sort_folder_label_padding")
        single_line_height = line_height + padding
        self.setFixedHeight(single_line_height)

    def set_state(self, state, path=None):
        self._current_state = state
        
        if self._current_state == self.STATE_DISABLED:
            self.setReadOnly(True)
            self.setCursor(Qt.ArrowCursor)
            style = f"""
                QLineEdit {{
                    color: {ThemeManager.get_color('text_disabled')};
                    background-color: {ThemeManager.get_color('bg_disabled')};
                    border: 1px solid {ThemeManager.get_color('bg_disabled')};
                    padding: 5px; border-radius: 1px;
                }}
            """
            self.setPlaceholderText("")
            self.setText(LanguageManager.translate("폴더 경로"))
            self.setToolTip(LanguageManager.translate("폴더를 드래그하여 지정하세요."))
        elif self._current_state == self.STATE_EDITABLE:
            self.setReadOnly(False)
            self.setCursor(Qt.IBeamCursor)
            style = f"""
                QLineEdit {{
                    color: {ThemeManager.get_color('text')};
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: 1px solid {ThemeManager.get_color('bg_primary')};
                    padding: 5px; border-radius: 1px;
                }}
                QLineEdit:focus {{ border: 1px solid {ThemeManager.get_color('accent')}; }}
            """
            self.setText("")
            self.setPlaceholderText(LanguageManager.translate("폴더 경로"))
            self.setToolTip(LanguageManager.translate("새 폴더명을 입력하거나 폴더를 드래그하여 지정하세요."))
        elif self._current_state == self.STATE_SET:
            self.setReadOnly(True)
            self.setCursor(Qt.PointingHandCursor)
            style = f"""
                QLineEdit {{
                    color: #AAAAAA;
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: 1px solid {ThemeManager.get_color('bg_primary')};
                    padding: 5px; border-radius: 1px;
                }}
            """
            self.setPlaceholderText("")
            if path:
                self.set_path_text(path)
            self.setToolTip(f"{self.full_path}\n{LanguageManager.translate('더블클릭하면 해당 폴더가 열립니다.')}")
        
        self.setStyleSheet(style)
        self.original_style = style
        self.stateChanged.emit(self.folder_index, self._current_state)

    def set_path_text(self, text: str):
        self.full_path = text
        self.setToolTip(text)
        
        max_len = 20  # 기본 최대 길이
        suf_len = 15  # 기본 뒷부분 길이

        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            aspect_ratio = geometry.width() / geometry.height() if geometry.height() > 0 else 0
            # 1.6 (16:10)에 가까운 비율인지 확인 (오차 범위 0.1)
            if abs(aspect_ratio - 1.6) < 0.1:
                logging.debug("16:10 비율 디스플레이 감지됨. EditableFolderPathLabel 텍스트 길이 조정.")
                max_len = 15
                suf_len = 12

        display_text = text
        if len(text) > max_len:
            display_text = "..." + text[-suf_len:]
            
        super().setText(display_text)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self._current_state == self.STATE_SET and self.full_path:
            self.doubleClicked.emit(self.full_path)
        else:
            super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event):
        if self._can_accept_drop(event):
            event.acceptProposedAction()
            self.apply_drag_hover_style()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._can_accept_drop(event):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.restore_original_style()

    def dropEvent(self, event):
        self.restore_original_style()
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            if Path(file_path).is_dir():
                self.folderDropped.emit(self.folder_index, file_path)
                event.acceptProposedAction()
                return
        elif event.mimeData().hasText():
            drag_data = event.mimeData().text()
            if drag_data.startswith("image_drag:"):
                if self.folder_index >= 0 and self._current_state == self.STATE_SET:
                    self.imageDropped.emit(self.folder_index, drag_data)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def _can_accept_drop(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            return len(urls) == 1 and Path(urls[0].toLocalFile()).is_dir()
        
        can_accept_image = (self.folder_index >= 0 and self._current_state == self.STATE_SET)
        if event.mimeData().hasText() and event.mimeData().text().startswith("image_drag:") and can_accept_image:
            return True
            
        return False

    def apply_drag_hover_style(self):
        """드래그 호버 시 테두리만 강조하는 스타일을 적용합니다."""
        hover_style = ""
        if self._current_state == self.STATE_DISABLED:
            hover_style = f"""
                QLineEdit {{
                    color: {ThemeManager.get_color('text_disabled')};
                    background-color: {ThemeManager.get_color('bg_disabled')};
                    border: 2px solid {ThemeManager.get_color('accent')};
                    padding: 4px; border-radius: 1px;
                }}
            """
        elif self._current_state == self.STATE_EDITABLE:
            hover_style = f"""
                QLineEdit {{
                    color: {ThemeManager.get_color('text')};
                    background-color: {ThemeManager.get_color('bg_secondary')};
                    border: 2px solid {ThemeManager.get_color('accent')};
                    padding: 4px; border-radius: 1px;
                }}
                QLineEdit:focus {{ border: 2px solid {ThemeManager.get_color('accent')}; }}
            """
        elif self._current_state == self.STATE_SET:
            hover_style = f"""
                QLineEdit {{
                    color: #AAAAAA;
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: 2px solid {ThemeManager.get_color('accent')};
                    padding: 4px; border-radius: 1px;
                }}
            """
        if hover_style:
            self.setStyleSheet(hover_style)

    def apply_keypress_highlight(self, highlight: bool):
        if self._current_state != self.STATE_SET:
            return

        if highlight:
            style = f"""
                QLineEdit {{
                    color: #FFFFFF;
                    background-color: {ThemeManager.get_color('accent')};
                    border: 1px solid {ThemeManager.get_color('accent')};
                    padding: 5px; border-radius: 1px;
                }}
            """
            self.setStyleSheet(style)
        else:
            self.restore_original_style()

    def restore_original_style(self):
        self.setStyleSheet(self.original_style)

