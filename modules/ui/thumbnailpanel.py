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



class ThumbnailPanel(QWidget):
    """썸네일 패널 위젯 - 현재 이미지 주변의 썸네일들을 표시"""
    
    # 시그널 정의
    thumbnailClicked = Signal(int)           # 썸네일 클릭 시 인덱스 전달
    thumbnailDoubleClicked = Signal(int)     # 썸네일 더블클릭 시 인덱스 전달
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent  # VibeCullingApp 참조
        
        # 모델과 델리게이트 생성 (image_loader 전달)
        self.model = ThumbnailModel([], self.parent_app.image_loader if self.parent_app else None, self)
        self.delegate = ThumbnailDelegate(self)

        self.setup_ui()
        self.connect_signals()
        
        # 테마/언어 변경 콜백 등록
        ThemeManager.register_theme_change_callback(self.update_ui_colors)
        
    def setup_ui(self):
        """UI 구성 요소 초기화"""
        # 메인 레이아웃
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(UIScaleManager.get("control_layout_spacing"))
        
        # 썸네일 리스트 뷰
        self.list_view = DraggableThumbnailView()
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setDragEnabled(True)
        
        # 리스트 뷰 설정
        self.list_view.setSelectionMode(QListView.SingleSelection)
        self.list_view.setDragDropMode(QListView.DragOnly)           # 드래그 허용
        self.list_view.setDefaultDropAction(Qt.MoveAction)
        self.list_view.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_view.setSpacing(UIScaleManager.get("thumbnail_item_spacing"))

        # 썸네일 아이템 간격 설정
        item_spacing = UIScaleManager.get("thumbnail_item_spacing")
        
        # 스타일 설정
        self.list_view.setStyleSheet(f"""
            QListView {{
                background-color: {ThemeManager.get_color('bg_primary')};
                border: none;
                outline: none;
                padding: {item_spacing}px;
                spacing: {item_spacing}px;
            }}
            QListView::item {{
                border: none;
                padding: 0px;
                margin-bottom: {item_spacing}px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {ThemeManager.get_color('bg_primary')};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {ThemeManager.get_color('border')};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ThemeManager.get_color('accent_hover')};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        # 레이아웃에 추가
        self.layout.addWidget(self.list_view, 1)  # 확장 가능
        
        # 패널 전체 스타일
        self.setStyleSheet(f"""
            ThumbnailPanel {{
                background-color: {ThemeManager.get_color('bg_primary')};
                border-right: 1px solid {ThemeManager.get_color('border')};
            }}
        """)
        
        # 최소 크기 설정
        min_width = UIScaleManager.get("thumbnail_panel_min_width")
        max_width = UIScaleManager.get("thumbnail_panel_max_width")
        self.setMinimumWidth(min_width)
        self.setMaximumWidth(max_width)
        
    def connect_signals(self):
        """시그널 연결"""
        # 모델 시그널 연결
        logging.info("ThumbnailPanel: 시그널 연결 시작")
        self.model.currentIndexChanged.connect(self.on_current_index_changed)
        
        # 리스트 뷰 시그널 연결
        self.list_view.clicked.connect(self.on_thumbnail_clicked)
        self.list_view.doubleClicked.connect(self.on_thumbnail_double_clicked)

        
        logging.info("ThumbnailPanel: 모든 시그널 연결 완료")
    
    def set_image_files(self, image_files):
        """이미지 파일 목록 설정"""
        logging.info(f"ThumbnailPanel.set_image_files: {len(image_files) if image_files else 0}개 파일 설정")
        self.model.set_image_files(image_files)
        
        # 모델 상태 확인
        logging.debug(f"ThumbnailPanel: 모델 rowCount={self.model.rowCount()}")
                
    def set_current_index(self, index):
        """현재 인덱스 설정 및 스크롤"""
        if not self.model._image_files or index < 0 or index >= len(self.model._image_files):
            return
        
        self.model.set_current_index(index)
        
        self.scroll_to_index(index)
        
        self.preload_surrounding_thumbnails(index)
    
    def scroll_to_index(self, index):
        """지정된 인덱스가 리스트 중앙에 오도록 스크롤 (타이머로 지연 실행)"""
        if index < 0 or index >= self.model.rowCount():
            return
        
        # 10ms의 짧은 지연을 추가하여 뷰가 업데이트될 시간을 확실히 보장합니다.
        QTimer.singleShot(10, lambda: self._perform_scroll(index))

    def _perform_scroll(self, index):
        """실제 스크롤을 수행하는 내부 메서드"""
        # 타이머 콜백 시점에 인덱스가 여전히 유효한지 다시 확인
        if 0 <= index < self.model.rowCount():
            model_index = self.model.createIndex(index, 0)
            
            # 1. 뷰에게 현재 인덱스가 무엇인지 명시적으로 알려줍니다.
            #    이렇게 하면 뷰가 스크롤 위치를 계산하기 전에 올바른 아이템에 집중하게 됩니다.
            self.list_view.setCurrentIndex(model_index)
            
            # 2. 스크롤을 수행합니다.
            self.list_view.scrollTo(model_index, QListView.PositionAtCenter)
    
    def preload_surrounding_thumbnails(self, center_index, radius=5):
        """중심 인덱스 주변의 썸네일 미리 로딩"""
        self.model.preload_thumbnails(center_index, radius)

    
    def on_current_index_changed(self, index):
        """모델의 현재 인덱스 변경 시 호출"""
        # 필요시 추가 처리
        pass
    
    def on_thumbnail_clicked(self, model_index):
        """썸네일 클릭 시 호출"""
        if model_index.isValid():
            index = model_index.row()
            self.thumbnailClicked.emit(index)

    def on_thumbnail_double_clicked(self, model_index):
        """썸네일 더블클릭 시 호출"""
        if model_index.isValid():
            index = model_index.row()
            self.thumbnailDoubleClicked.emit(index)
    
    def get_selected_indexes(self):
        """현재 선택된 인덱스들 반환"""
        selection_model = self.list_view.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        return [index.row() for index in selected_indexes]
    
    def clear_selection(self):
        """선택 해제"""
        self.list_view.clearSelection()
    
    
    def update_ui_colors(self):
        """테마 변경 시 UI 색상 업데이트"""
        self.list_view.setStyleSheet(f"""
            QListView {{
                background-color: {ThemeManager.get_color('bg_primary')};
                border: none;
                outline: none;
            }}
            QListView::item {{
                border: none;
                padding: 0px;
            }}
            QListView::item:selected {{
                background-color: {ThemeManager.get_color('accent')};
                background-color: rgba(255, 255, 255, 30);
            }}
            QScrollBar:vertical {{
                border: none;
                background: {ThemeManager.get_color('bg_primary')};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {ThemeManager.get_color('border')};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ThemeManager.get_color('accent_hover')};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
    



