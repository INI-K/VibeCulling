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



class DraggableThumbnailView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_start_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position().toPoint()
        # 기본 mousePressEvent를 호출하지 않아 즉시 선택되는 것을 방지
        # super().mousePressEvent(event) 

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.drag_start_position:
            return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # 드래그 시작
        drag = QDrag(self)
        mime_data = QMimeData()
        
        index = self.indexAt(self.drag_start_position)
        if not index.isValid():
            return
        
        # 드래그 데이터에 이미지 인덱스 저장
        mime_data.setText(f"thumbnail_drag:{index.row()}")
        drag.setMimeData(mime_data)

        # 드래그 시 보여줄 썸네일 이미지 설정
        pixmap = index.data(Qt.DecorationRole)
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            drag.setPixmap(scaled_pixmap)
            drag.setHotSpot(QPoint(32, 32))

        drag.exec(Qt.CopyAction)
        self.drag_start_position = None # 드래그 후 초기화

    def mouseReleaseEvent(self, event):
        # 드래그가 시작되지 않았다면, 일반 클릭으로 간주하여 선택 처리
        if self.drag_start_position is not None:
            # 마우스 누른 위치와 뗀 위치가 거의 같다면 클릭으로 처리
            if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                # 기본 QListView의 클릭 동작을 여기서 수행
                super().mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, event.position().toPoint(), event.globalPosition().toPoint(), event.button(), event.buttons(), event.modifiers()))
                super().mouseReleaseEvent(event)
        self.drag_start_position = None

