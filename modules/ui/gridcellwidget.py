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



class GridCellWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._filename = ""
        self._show_filename = False
        self._is_selected = False
        self.setMinimumSize(1, 1) # 최소 크기 설정 중요

        # 드래그 앤 드롭 관련 변수
        self.drag_start_pos = QPoint(0, 0)
        self.is_potential_drag = False
        self.drag_threshold = 10
        
        # 마우스 추적 활성화
        self.setMouseTracking(True)

    def setPixmap(self, pixmap):
        if pixmap is None:
            self._pixmap = QPixmap()
        else:
            self._pixmap = pixmap
        self.update() # 위젯을 다시 그리도록 요청

    def setText(self, text):
        if self._filename != text: # 텍스트가 실제로 변경될 때만 업데이트
            self._filename = text
            self.update() # 변경 시 다시 그리기

    def setShowFilename(self, show):
        if self._show_filename != show: # 상태가 실제로 변경될 때만 업데이트
            self._show_filename = show
            self.update() # 변경 시 다시 그리기

    def setSelected(self, selected):
        self._is_selected = selected
        self.update()

    def pixmap(self):
        return self._pixmap

    def text(self):
        return self._filename

    def mousePressEvent(self, event):
        """마우스 클릭 이벤트 처리 - 드래그 시작 준비"""
        try:
            # 부모 앱 참조 얻기
            app = self.get_parent_app()
            if not app:
                super().mousePressEvent(event)
                return
            
            # === Fit 모드에서 드래그 앤 드롭 시작 준비 ===
            if (event.button() == Qt.LeftButton and 
                app.zoom_mode == "Fit" and 
                app.image_files and 
                0 <= app.current_image_index < len(app.image_files)):
                
                # 드래그 시작 준비
                self.drag_start_pos = event.position().toPoint()
                self.is_potential_drag = True
                logging.debug(f"Grid 셀에서 드래그 시작 준비: {self.drag_start_pos}")
                return
            
            # 기존 이벤트 처리
            super().mousePressEvent(event)
            
        except Exception as e:
            logging.error(f"GridCellWidget.mousePressEvent 오류: {e}")
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트 처리 - 드래그 시작 감지"""
        try:
            # 부모 앱 참조 얻기
            app = self.get_parent_app()
            if not app:
                super().mouseMoveEvent(event)
                return
            
            # === Fit 모드에서 드래그 시작 감지 ===
            if (self.is_potential_drag and 
                app.zoom_mode == "Fit" and 
                app.image_files and 
                0 <= app.current_image_index < len(app.image_files)):
                
                current_pos = event.position().toPoint()
                move_distance = (current_pos - self.drag_start_pos).manhattanLength()
                
                if move_distance > self.drag_threshold:
                    # 드래그 시작
                    app.start_image_drag()
                    self.is_potential_drag = False
                    logging.debug("Grid 셀에서 드래그 시작됨")
                    return
            
            # 기존 이벤트 처리
            super().mouseMoveEvent(event)
            
        except Exception as e:
            logging.error(f"GridCellWidget.mouseMoveEvent 오류: {e}")
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """마우스 릴리스 이벤트 처리 - 드래그 상태 초기화"""
        try:
            # 드래그 상태 초기화
            if self.is_potential_drag:
                self.is_potential_drag = False
                logging.debug("Grid 셀에서 드래그 시작 준비 상태 해제")
            
            # 기존 이벤트 처리
            super().mouseReleaseEvent(event)
            
        except Exception as e:
            logging.error(f"GridCellWidget.mouseReleaseEvent 오류: {e}")
            super().mouseReleaseEvent(event)

    def get_parent_app(self):
        """부모 위젯을 타고 올라가면서 VibeCullingApp 인스턴스 찾기"""
        try:
            current_widget = self.parent()
            while current_widget:
                if hasattr(current_widget, 'start_image_drag'):
                    return current_widget
                current_widget = current_widget.parent()
            return None
        except Exception as e:
            logging.error(f"get_parent_app 오류: {e}")
            return None

    # 그리드 파일명 상단 좌측
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = self.rect()

        painter.fillRect(rect, QColor("black"))

        if not self._pixmap.isNull():
            scaled_pixmap = self._pixmap.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (rect.width() - scaled_pixmap.width()) / 2
            y = (rect.height() - scaled_pixmap.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled_pixmap)

        if self._show_filename and self._filename:
            font = QFont("Arial", UIScaleManager.get("font_size", 10)) # 파일명 폰트 먼저 설정
            if self._is_selected:
                font.setBold(True)  # 선택된 셀이면 볼드체 적용
            else:
                font.setBold(False) # 선택되지 않았으면 볼드체 해제
            painter.setFont(font)   # painter에 (볼드체가 적용되거나 해제된) 폰트 적용
            font_metrics = QFontMetrics(painter.font()) # painter에 적용된 폰트로 metrics 가져오기
            
            # 파일명 축약 (elidedText 사용)
            # 셀 너비에서 좌우 패딩(예: 각 5px)을 뺀 값을 기준으로 축약
            available_text_width = rect.width() - 10 
            elided_filename_for_paint = font_metrics.elidedText(self._filename, Qt.ElideRight, available_text_width)

            text_height = font_metrics.height()
            
            # 배경 사각형 위치 및 크기 (상단 좌측)
            bg_rect_height = text_height + 4 # 상하 패딩
            bg_rect_y = 1 # 테두리 바로 아래부터
            
            # 배경 너비: 축약된 텍스트 너비 + 좌우 패딩, 또는 셀 너비의 일정 비율 등
            # 여기서는 축약된 텍스트 너비 + 약간의 패딩으로 설정
            bg_rect_width = min(font_metrics.horizontalAdvance(elided_filename_for_paint) + 10, rect.width() - 4)
            bg_rect_x = 2 # 좌측에서 약간의 패딩 (테두리 두께 1px + 여백 1px)
            
            text_bg_rect = QRect(int(bg_rect_x), bg_rect_y, int(bg_rect_width), bg_rect_height)
            painter.fillRect(text_bg_rect, QColor(0, 0, 0, 150)) # 반투명 검정 (alpha 150)

            painter.setPen(QColor("white"))
            # 텍스트를 배경 사각형의 좌측 상단에 (약간의 내부 패딩을 주어) 그리기
            # Qt.AlignLeft | Qt.AlignVCenter 를 사용하면 배경 사각형 내에서 세로 중앙, 가로 좌측 정렬
            text_draw_x = bg_rect_x + 3 # 배경 사각형 내부 좌측 패딩
            text_draw_y = bg_rect_y + 2 # 배경 사각형 내부 상단 패딩 (텍스트 baseline 고려)
            
            # drawText는 QPointF와 문자열을 받을 수 있습니다.
            # 또는 QRectF와 정렬 플래그를 사용할 수 있습니다.
            # 여기서는 QRectF를 사용하여 정렬 플래그로 제어합니다.
            text_paint_rect = QRect(int(text_draw_x), int(text_draw_y),
                                    int(bg_rect_width - 6), # 좌우 패딩 제외한 너비
                                    text_height)
            painter.drawText(text_paint_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_filename_for_paint)


        pen_color = QColor("white") if self._is_selected else QColor("#555555")
        pen = QPen(pen_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        painter.end()

