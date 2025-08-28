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



class FileListDialog(QDialog):
    """사진 목록과 미리보기를 보여주는 팝업 대화상자"""
    def __init__(self, image_files, current_index, image_loader, parent=None):
        super().__init__(parent)
        self.image_files = image_files
        self.image_loader = image_loader
        self.preview_size = 750 # --- 미리보기 크기 750으로 변경 ---

        self.setWindowTitle(LanguageManager.translate("사진 목록"))
        # 창 크기 조정 (미리보기 증가 고려)
        self.setMinimumSize(1200, 850)

        # 제목표시줄 다크 테마
        apply_dark_title_bar(self)

        # --- 다크 테마 배경 설정 (이전 코드 유지) ---
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # --- 메인 레이아웃 (이전 코드 유지) ---
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # --- 좌측: 파일 목록 (이전 코드 유지, 스타일 포함) ---
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')};
                border-radius: 4px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 2px 0px;
            }}
            QListWidget::item:selected {{
                background-color: {ThemeManager.get_color('accent')};
                color: {ThemeManager.get_color('bg_primary')};
            }}
        """)
        list_font = parent.default_font if parent and hasattr(parent, 'default_font') else QFont("Arial", UIScaleManager.get("font_size", 10))
        list_font.setPointSize(UIScaleManager.get("font_size") -1)
        self.list_widget.setFont(list_font)

        # 파일 목록 채우기 (이전 코드 유지)
        for i, file_path in enumerate(self.image_files):
            item = QListWidgetItem(file_path.name)
            item.setData(Qt.UserRole, str(file_path))
            self.list_widget.addItem(item)

        # 현재 항목 선택 및 스크롤 (이전 코드 유지)
        if 0 <= current_index < self.list_widget.count():
            self.list_widget.setCurrentRow(current_index)
            self.list_widget.scrollToItem(self.list_widget.item(current_index), QListWidget.PositionAtCenter)

        # --- 우측: 미리보기 레이블 ---
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(self.preview_size, self.preview_size) # --- 크기 750 적용 ---
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(f"background-color: black; border-radius: 4px;")

        # --- 레이아웃에 위젯 추가 (이전 코드 유지) ---
        self.main_layout.addWidget(self.list_widget, 1)
        self.main_layout.addWidget(self.preview_label, 0)

        # --- 미리보기 업데이트 지연 로딩을 위한 타이머 설정 ---
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True) # 한 번만 실행
        self.preview_timer.setInterval(200)  # 200ms 지연
        self.preview_timer.timeout.connect(self.load_preview) # 타이머 만료 시 load_preview 호출

        self.list_widget.currentItemChanged.connect(self.on_selection_changed)
        # --- 더블클릭 시그널 연결 추가 ---
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        # 초기 미리보기 로드 (즉시 로드)
        self.update_preview(self.list_widget.currentItem())

    def on_selection_changed(self, current, previous):
        """목록 선택 변경 시 호출되는 슬롯, 미리보기 타이머 시작/재시작"""
        # 현재 선택된 항목이 유효할 때만 타이머 시작
        if current:
            self.preview_timer.start() # 타이머 시작 (이미 실행 중이면 재시작)
        else:
            # 선택된 항목이 없으면 미리보기 즉시 초기화하고 타이머 중지
            self.preview_timer.stop()
            self.preview_label.clear()
            self.preview_label.setText(LanguageManager.translate("선택된 파일 없음"))
            self.preview_label.setStyleSheet(f"background-color: black; color: white; border-radius: 4px;")


    def load_preview(self):
        """타이머 만료 시 실제 미리보기 로딩 수행"""
        current_item = self.list_widget.currentItem()
        self.update_preview(current_item)


    def update_preview(self, current_item): # current_item 인자 유지
        """선택된 항목의 미리보기 업데이트 (실제 로직)"""
        if not current_item:
            # load_preview 에서 currentItem()을 가져오므로, 여기서 다시 체크할 필요는 적지만 안전하게 둠
            self.preview_label.clear()
            self.preview_label.setText(LanguageManager.translate("선택된 파일 없음"))
            self.preview_label.setStyleSheet(f"background-color: black; color: white; border-radius: 4px;")
            return

        file_path = current_item.data(Qt.UserRole)
        if not file_path:
            self.preview_label.clear()
            self.preview_label.setText(LanguageManager.translate("파일 경로 없음"))
            self.preview_label.setStyleSheet(f"background-color: black; color: white; border-radius: 4px;")
            return

        # 이미지 로더를 통해 이미지 로드 (캐시 활용)
        pixmap = self.image_loader.load_image_with_orientation(file_path)

        if pixmap.isNull():
            self.preview_label.clear()
            self.preview_label.setText(LanguageManager.translate("미리보기 로드 실패"))
            self.preview_label.setStyleSheet(f"background-color: black; color: red; border-radius: 4px;")
        else:
            # 스케일링 속도 개선 (FastTransformation 유지)
            scaled_pixmap = pixmap.scaled(self.preview_size, self.preview_size, Qt.KeepAspectRatio, Qt.FastTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            # 텍스트 제거를 위해 스타일 초기화
            self.preview_label.setStyleSheet(f"background-color: black; border-radius: 4px;")

    # --- 더블클릭 처리 메서드 추가 ---
    def on_item_double_clicked(self, item):
        """리스트 항목 더블클릭 시 호출되는 슬롯"""
        file_path_str = item.data(Qt.UserRole)
        if not file_path_str:
            return

        file_path = Path(file_path_str)
        parent_app = self.parent() # VibeCullingApp 인스턴스 가져오기

        # 부모가 VibeCullingApp 인스턴스이고 필요한 속성/메서드가 있는지 확인
        if parent_app and hasattr(parent_app, 'image_files') and hasattr(parent_app, 'set_current_image_from_dialog'):
            try:
                # VibeCullingApp의 image_files 리스트에서 해당 Path 객체의 인덱스 찾기
                index = parent_app.image_files.index(file_path)
                parent_app.set_current_image_from_dialog(index) # 부모 앱의 메서드 호출
                self.accept() # 다이얼로그 닫기 (성공적으로 처리되면)
            except ValueError:
                logging.error(f"오류: 더블클릭된 파일을 메인 목록에서 찾을 수 없습니다: {file_path}")
                # 사용자를 위한 메시지 박스 표시 등 추가 가능
                QMessageBox.warning(self, 
                                    LanguageManager.translate("오류"), 
                                    LanguageManager.translate("선택한 파일을 현재 목록에서 찾을 수 없습니다.\n목록이 변경되었을 수 있습니다."))
            except Exception as e:
                logging.error(f"더블클릭 처리 중 오류 발생: {e}")
                QMessageBox.critical(self, 
                                     LanguageManager.translate("오류"), 
                                     f"{LanguageManager.translate('이미지 이동 중 오류가 발생했습니다')}:\n{e}")
        else:
            logging.error("오류: 부모 위젯 또는 필요한 속성/메서드를 찾을 수 없습니다.")
            QMessageBox.critical(self, 
                                 LanguageManager.translate("오류"), 
                                 LanguageManager.translate("내부 오류로 인해 이미지로 이동할 수 없습니다."))

