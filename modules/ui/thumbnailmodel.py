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



class ThumbnailModel(QAbstractListModel):
    """썸네일 패널을 위한 가상화된 리스트 모델"""
    
    # 시그널 정의
    thumbnailRequested = Signal(str, int)  # 썸네일 로딩 요청 (파일 경로, 인덱스)
    currentIndexChanged = Signal(int)      # 현재 선택 인덱스 변경
    
    def __init__(self, image_files=None, image_loader=None, parent=None):
        super().__init__(parent)
        self._image_files = image_files or []         # ← 첫 번째 버전과 동일하게 _image_files 사용
        self.image_loader = image_loader              # ← 새로 추가
        self._current_index = -1                      # 현재 선택된 인덱스
        self._thumbnail_cache = {}                    # 썸네일 캐시 {파일경로: QPixmap}
        self._thumbnail_size = UIScaleManager.get("thumbnail_image_size")  # 64 → 동적 크기
        self._loading_set = set()                     # 현재 로딩 중인 파일 경로들
        
        # ResourceManager 인스턴스 참조
        self.resource_manager = ResourceManager.instance()
        
    def set_image_files(self, image_files):
        """이미지 파일 목록 설정"""
        self.beginResetModel()
        self._image_files = image_files or []
        self._current_index = -1
        self._thumbnail_cache.clear()
        self._loading_set.clear()
        self.endResetModel()
        
        # 캐시에서 불필요한 항목 제거
        self._cleanup_cache()
        
    def set_current_index(self, index):
        """현재 선택 인덱스 설정"""
        if 0 <= index < len(self._image_files) and index != self._current_index:
            old_index = self._current_index
            self._current_index = index
            
            # 변경된 인덱스들 업데이트
            if old_index >= 0:
                self.dataChanged.emit(self.createIndex(old_index, 0), 
                                    self.createIndex(old_index, 0))
            if self._current_index >= 0:
                self.dataChanged.emit(self.createIndex(self._current_index, 0), 
                                    self.createIndex(self._current_index, 0))
                
            self.currentIndexChanged.emit(self._current_index)
    
    def get_current_index(self):
        """현재 선택 인덱스 반환"""
        return self._current_index
    
    def rowCount(self, parent=QModelIndex()):
        """모델의 행 개수 반환 (가상화 지원)"""
        count = len(self._image_files)
        if count > 0:  # 이미지가 있을 때만 로그 출력
            logging.debug(f"ThumbnailModel.rowCount: {count}개 파일")
        return count
    
    def data(self, index, role=Qt.DisplayRole):
        """모델 데이터 제공"""
        if not index.isValid() or index.row() >= len(self._image_files):
            return None
            
        row = index.row()
        file_path = str(self._image_files[row])
        
        # 기본 호출 로그 추가
        logging.debug(f"ThumbnailModel.data 호출: row={row}, role={role}, file={Path(file_path).name}")
        
        if role == Qt.DisplayRole:
            # 파일명만 반환
            return Path(file_path).name
            
        elif role == Qt.DecorationRole:
            # 썸네일 이미지 반환
            logging.debug(f"ThumbnailModel.data: Qt.DecorationRole 요청 - {Path(file_path).name}")
            return self._get_thumbnail(file_path, row)
            
        elif role == Qt.UserRole:
            # 파일 경로 반환
            return file_path
            
        elif role == Qt.UserRole + 1:
            # 현재 선택 여부 반환
            return row == self._current_index
            
        elif role == Qt.ToolTipRole:
            # 툴팁: 파일명 + 경로
            return f"{Path(file_path).name}\n{file_path}"
            
        return None
    
    def flags(self, index):
        """아이템 플래그 반환 (선택, 드래그 가능)"""
        if not index.isValid():
            return Qt.NoItemFlags
            
        return (Qt.ItemIsEnabled | 
                Qt.ItemIsSelectable | 
                Qt.ItemIsDragEnabled)
    
    def _get_thumbnail(self, file_path, row):
        """썸네일 이미지 반환 (캐시 우선, 없으면 비동기 로딩)"""
        # 캐시에서 확인
        if file_path in self._thumbnail_cache:
            thumbnail = self._thumbnail_cache[file_path]
            if thumbnail and not thumbnail.isNull():
                logging.debug(f"썸네일 캐시 히트: {Path(file_path).name}")
                return thumbnail
        
        # 로딩 중이 아니면 비동기 로딩 요청
        if file_path not in self._loading_set:
            logging.debug(f"썸네일 비동기 로딩 요청: {Path(file_path).name}")
            self._loading_set.add(file_path)
            self.thumbnailRequested.emit(file_path, row)
        else:
            logging.debug(f"썸네일 이미 로딩 중: {Path(file_path).name}")
        
        # 기본 이미지 반환 (로딩 중 표시)
        return self._create_loading_pixmap()
    
    def _create_loading_pixmap(self):
        """로딩 중 표시할 기본 픽스맵 생성"""
        size = UIScaleManager.get("thumbnail_image_size")
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(ThemeManager.get_color('bg_secondary')))
        
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(ThemeManager.get_color('text_disabled')), 1))
        painter.drawRect(0, 0, size-1, size-1)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "...")
        painter.end()
        
        return pixmap
    
    def set_thumbnail(self, file_path, pixmap):
        """썸네일 캐시에 저장 및 UI 업데이트"""
        if not pixmap or pixmap.isNull():
            return
            
        # 캐시에 저장
        self._thumbnail_cache[file_path] = pixmap
        
        # 로딩 상태에서 제거
        self._loading_set.discard(file_path)
        
        # 해당 인덱스 찾아서 UI 업데이트
        for i, image_file in enumerate(self._image_files):
            if str(image_file) == file_path:
                index = self.createIndex(i, 0)
                self.dataChanged.emit(index, index, [Qt.DecorationRole])
                break
    
    def _cleanup_cache(self):
        """불필요한 캐시 항목 제거"""
        if not self._image_files:
            self._thumbnail_cache.clear()
            return
            
        # 현재 이미지 파일 목록에 없는 캐시 항목 제거
        current_paths = {str(f) for f in self._image_files}
        cached_paths = set(self._thumbnail_cache.keys())
        
        for path in cached_paths - current_paths:
            del self._thumbnail_cache[path]
    
    def clear_cache(self):
        """모든 캐시 지우기"""
        self._thumbnail_cache.clear()
        self._loading_set.clear()
    
    def preload_thumbnails(self, center_index, radius=10):
        """중심 인덱스 주변의 썸네일 미리 로딩"""
        if not self._image_files or center_index < 0:
            return
            
        start = max(0, center_index - radius)
        end = min(len(self._image_files), center_index + radius + 1)
        
        for i in range(start, end):
            file_path = str(self._image_files[i])
            if (file_path not in self._thumbnail_cache and 
                file_path not in self._loading_set):
                self._loading_set.add(file_path)
                self.thumbnailRequested.emit(file_path, i)

    def removeItem(self, index_to_remove):
        """지정된 인덱스의 아이템을 모델과 내부 데이터에서 제거합니다."""
        if not (0 <= index_to_remove < len(self._image_files)):
            return False

        logging.debug(f"ThumbnailModel: Removing item at index {index_to_remove}")
        
        # 뷰에게 '곧 이 행이 삭제될 거야'라고 알림
        self.beginRemoveRows(QModelIndex(), index_to_remove, index_to_remove)
        
        # 실제 데이터 삭제
        removed_path = self._image_files.pop(index_to_remove)
        
        # 캐시에서도 해당 항목 제거
        if str(removed_path) in self._thumbnail_cache:
            del self._thumbnail_cache[str(removed_path)]
            
        # 뷰에게 '삭제 작업이 끝났어'라고 알림
        self.endRemoveRows()
        
        return True

    def addItem(self, index_to_insert, file_path):
        """지정된 인덱스에 새 아이템을 모델과 내부 데이터에 추가합니다."""
        if not (0 <= index_to_insert <= len(self._image_files)):
            return False

        logging.debug(f"ThumbnailModel: Inserting item at index {index_to_insert}")
        
        # 뷰에게 '곧 여기에 행이 추가될 거야'라고 알림
        self.beginInsertRows(QModelIndex(), index_to_insert, index_to_insert)
        
        # 실제 데이터 추가
        self._image_files.insert(index_to_insert, file_path)
        
        # 뷰에게 '추가 작업이 끝났어'라고 알림
        self.endInsertRows()
        
        return True


