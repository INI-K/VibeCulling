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



class ThumbnailDelegate(QStyledItemDelegate):
    """썸네일 아이템의 렌더링을 담당하는 델리게이트"""
    
    # 썸네일 클릭 시그널
    thumbnailClicked = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._placeholder_pixmap = self._create_placeholder()
    
    def _create_placeholder(self):
        """플레이스홀더 이미지 생성"""
        size = UIScaleManager.get("thumbnail_image_size")
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor("#222222"))
        return pixmap
    
    def paint(self, painter, option, index):
        """썸네일 아이템 렌더링 (테두리 보존 하이라이트)"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # --- 기본 변수 설정 ---
        rect = option.rect
        image_size = UIScaleManager.get("thumbnail_image_size")
        padding = UIScaleManager.get("thumbnail_padding")
        text_height = UIScaleManager.get("thumbnail_text_height")
        border_width = UIScaleManager.get("thumbnail_border_width")
        
        # --- 상태 확인 ---
        is_current = index.data(Qt.UserRole + 1)
        is_selected = option.state & QStyle.State_Selected
        
        # --- 1. 테두리 그리기 (모든 아이템에 동일한 테두리) ---
        # 테두리 색상으로 전체 아이템 영역을 먼저 칠합니다.
        border_color = QColor("#505050")
        painter.fillRect(rect, border_color)

        # --- 2. 배경 그리기 (테두리 안쪽으로) ---
        # 배경을 칠할 영역을 테두리 두께만큼 안쪽으로 축소합니다.
        # rect.adjusted(left, top, right, bottom) - right, bottom은 음수여야 축소됨
        inner_bg_rect = rect.adjusted(border_width, border_width, -border_width, -border_width)

        # 선택 상태에 따라 배경색 결정
        if is_current or is_selected:
            bg_color = QColor("#525252") # 선택 시 밝은 회색
        else:
            bg_color = QColor(ThemeManager.get_color('bg_primary'))   # 비선택 시 어두운 배경색
        
        # 축소된 영역에 배경색을 칠합니다.
        painter.fillRect(inner_bg_rect, bg_color)
            
        # --- 3. 이미지 그리기 ---
        image_path = index.data(Qt.UserRole)
        if image_path:
            pixmap = index.data(Qt.DecorationRole)
            target_pixmap = pixmap if pixmap and not pixmap.isNull() else self._placeholder_pixmap
            
            scaled_pixmap = target_pixmap.scaled(
                image_size, image_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            x_pos = rect.x() + (rect.width() - scaled_pixmap.width()) // 2
            image_area_height = rect.height() - text_height - (padding * 3)
            y_pos = rect.y() + padding + (image_area_height - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x_pos, y_pos, scaled_pixmap)

        # --- 4. 파일명 텍스트 그리기 ---
        filename = index.data(Qt.DisplayRole)
        if filename:
            text_rect = QRect(
                rect.x() + padding,
                rect.y() + padding + image_size + padding,
                rect.width() - (padding * 2),
                text_height
            )
            
            painter.setPen(QColor(ThemeManager.get_color('text')))
            font = QFont("Arial", UIScaleManager.get("font_size", 10))
            font.setPointSize(UIScaleManager.get("font_size"))
            painter.setFont(font)
            
            metrics = painter.fontMetrics()
            elided_text = metrics.elidedText(filename, Qt.ElideMiddle, text_rect.width())
            painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, elided_text)

        painter.restore()


    
    def sizeHint(self, option, index):
        """아이템 크기 힌트"""
        height = UIScaleManager.get("thumbnail_item_height")
        return QSize(0, height)

