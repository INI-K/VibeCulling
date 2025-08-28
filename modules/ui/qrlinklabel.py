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



class QRLinkLabel(QLabel):
    """
    마우스 오버 시 QR 코드를 보여주고 (macOS에서는 HTML 툴팁, 그 외 OS에서는 팝업),
    클릭 시 URL을 여는 범용 라벨 클래스.
    """
    def __init__(self, text, url, qr_path=None, parent=None, color="#D8D8D8", qr_display_size=400): # size -> qr_display_size로 변경
        super().__init__(text, parent)
        self.url = url
        self._qr_path = qr_path  # macOS HTML 툴팁과 다른 OS 팝업에서 공통으로 사용
        self._qr_display_size = qr_display_size # QR 코드 표시 크기 (툴팁/팝업 공통)

        self.normal_color = color
        self.hover_color = "#FFFFFF" # 또는 ThemeManager 사용

        # --- 스타일 및 커서 설정 ---
        self.setStyleSheet(f"""
            color: {self.normal_color};
            text-decoration: none; /* 링크 밑줄 제거 원하면 */
            font-weight: normal;
        """)
        self.setCursor(Qt.PointingHandCursor)

        # --- macOS가 아닌 경우에만 사용할 QR 팝업 멤버 ---
        self.qr_popup_widget = None # 실제 팝업 QLabel 위젯 (macOS에서는 사용 안 함)

        # --- macOS가 아닌 경우, 팝업 생성 (필요하다면) ---
        if platform.system() != "Darwin" and self._qr_path:
            self._create_non_mac_qr_popup()

    def _create_non_mac_qr_popup(self):
        """macOS가 아닌 환경에서 사용할 QR 코드 팝업 QLabel을 생성합니다."""
        if not self._qr_path or not Path(self._qr_path).exists():
            return

        self.qr_popup_widget = QLabel(self.window()) # 부모를 메인 윈도우로 설정하여 다른 위젯 위에 뜨도록
        self.qr_popup_widget.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.qr_popup_widget.setAttribute(Qt.WA_TranslucentBackground)
        # 흰색 배경, 둥근 모서리, 약간의 패딩을 가진 깔끔한 팝업 스타일
        self.qr_popup_widget.setStyleSheet(
            "background-color: white; border-radius: 5px; padding: 5px; border: 1px solid #CCCCCC;"
        )

        qr_pixmap = QPixmap(self._qr_path)
        if not qr_pixmap.isNull():
            scaled_pixmap = qr_pixmap.scaled(self._qr_display_size, self._qr_display_size,
                                             Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_popup_widget.setPixmap(scaled_pixmap)
            self.qr_popup_widget.adjustSize() # 콘텐츠 크기에 맞게 조절
        else:
            self.qr_popup_widget = None # Pixmap 로드 실패 시 팝업 사용 안 함

    def enterEvent(self, event):
        """마우스가 위젯에 들어왔을 때 스타일 변경 및 QR 코드/툴팁 표시"""
        self.setStyleSheet(f"""
            color: {self.hover_color};
            text-decoration: none;
            font-weight: bold;
        """)

        if platform.system() == "Darwin":
            if self._qr_path and Path(self._qr_path).exists():
                # macOS: HTML 툴팁 표시
                # QUrl.fromLocalFile을 사용하여 로컬 파일 경로를 올바른 URL 형식으로 변환
                local_file_url = QUrl.fromLocalFile(Path(self._qr_path).resolve()).toString()
                html = f'<img src="{local_file_url}" width="{self._qr_display_size}">'
                QToolTip.showText(self.mapToGlobal(event.position().toPoint()), html, self) # 세 번째 인자로 위젯 전달
            # else: macOS이지만 qr_path가 없으면 아무것도 안 함 (또는 기본 툴팁)
        else:
            # 다른 OS: 생성된 팝업 위젯 표시
            if self.qr_popup_widget and self.qr_popup_widget.pixmap() and not self.qr_popup_widget.pixmap().isNull():
                # 팝업 위치 계산 (마우스 커서 근처 또는 라벨 위 등)
                global_pos = self.mapToGlobal(QPoint(0, self.height())) # 라벨 하단 중앙 기준
                
                # 화면 경계 고려하여 팝업 위치 조정 (간단한 예시)
                screen_geo = QApplication.primaryScreen().availableGeometry()
                popup_width = self.qr_popup_widget.width()
                popup_height = self.qr_popup_widget.height()

                popup_x = global_pos.x() + (self.width() - popup_width) // 2
                popup_y = global_pos.y() + 5 # 라벨 아래에 약간의 간격

                # 화면 오른쪽 경계 초과 방지
                if popup_x + popup_width > screen_geo.right():
                    popup_x = screen_geo.right() - popup_width
                # 화면 왼쪽 경계 초과 방지
                if popup_x < screen_geo.left():
                    popup_x = screen_geo.left()
                # 화면 아래쪽 경계 초과 방지 (위로 올림)
                if popup_y + popup_height > screen_geo.bottom():
                    popup_y = global_pos.y() - popup_height - self.height() - 5 # 라벨 위로 이동
                # 화면 위쪽 경계 초과 방지 (아래로 내림 - 드문 경우)
                if popup_y < screen_geo.top():
                    popup_y = screen_geo.top()

                self.qr_popup_widget.move(popup_x, popup_y)
                self.qr_popup_widget.show()
                self.qr_popup_widget.raise_() # 다른 위젯 위로 올림

        super().enterEvent(event) # 부모 클래스의 enterEvent도 호출 (필요시)

    def leaveEvent(self, event):
        """마우스가 위젯을 벗어났을 때 스타일 복원 및 QR 코드/툴팁 숨김"""
        self.setStyleSheet(f"""
            color: {self.normal_color};
            text-decoration: none;
            font-weight: normal;
        """)

        if platform.system() == "Darwin":
            QToolTip.hideText() # macOS HTML 툴팁 숨김
        else:
            # 다른 OS: 팝업 위젯 숨김
            if self.qr_popup_widget:
                self.qr_popup_widget.hide()

        super().leaveEvent(event) # 부모 클래스의 leaveEvent도 호출

    def mouseReleaseEvent(self, event):
        """마우스 클릭 시 URL 열기"""
        if event.button() == Qt.LeftButton and self.url: # url이 있을 때만
            QDesktopServices.openUrl(QUrl(self.url))
        super().mouseReleaseEvent(event)

    # QR 팝업 위젯의 내용(QR 이미지)을 업데이트해야 할 경우를 위한 메서드 (선택 사항)
    def setQrPath(self, qr_path: str):
        self._qr_path = qr_path
        if platform.system() != "Darwin":
            # 기존 팝업이 있다면 숨기고, 새로 만들거나 업데이트
            if self.qr_popup_widget:
                self.qr_popup_widget.hide()
                # self.qr_popup_widget.deleteLater() # 필요시 이전 팝업 삭제
                self.qr_popup_widget = None
            if self._qr_path:
                self._create_non_mac_qr_popup()
        # macOS에서는 enterEvent에서 바로 처리하므로 별도 업데이트 불필요

