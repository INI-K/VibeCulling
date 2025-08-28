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



class ZoomScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 부모 참조 저장 (VibeCullingApp 인스턴스)
        self.app_parent = parent

    def wheelEvent(self, event: QWheelEvent):
        # 부모 위젯 (VibeCullingApp) 상태 및 마우스 휠 설정 확인
        if self.app_parent and hasattr(self.app_parent, 'mouse_wheel_action'):
            # Ctrl 키가 눌린 상태에서 Spin 모드일 때 줌 조정
            if (event.modifiers() & Qt.ControlModifier and 
                hasattr(self.app_parent, 'zoom_mode') and 
                self.app_parent.zoom_mode == "Spin"):
                wheel_delta = event.angleDelta().y()
                if wheel_delta != 0:
                    # SpinBox에서 직접 정수 값 가져오기 (부동소수점 오차 방지)
                    if hasattr(self.app_parent, 'zoom_spin'):
                        current_zoom = self.app_parent.zoom_spin.value()  # 이미 정수값
                        # 휠 방향에 따라 10씩 증가/감소
                        if wheel_delta > 0:
                            new_zoom = min(500, current_zoom + 10)  # 최대 500%
                        else:
                            new_zoom = max(10, current_zoom - 10)   # 최소 10%
                        # 값이 실제로 변경되었을 때만 업데이트
                        if new_zoom != current_zoom:
                            # SpinBox 값 먼저 설정 (정확한 정수값 보장)
                            self.app_parent.zoom_spin.setValue(new_zoom)
                    event.accept()
                    return
            # 마우스 휠 동작이 "없음"으로 설정된 경우 기존 방식 사용
            if getattr(self.app_parent, 'mouse_wheel_action', 'photo_navigation') == 'none':
                # 기존 ZoomScrollArea 동작 (100%/Spin 모드에서 휠 이벤트 무시)
                if hasattr(self.app_parent, 'zoom_mode') and self.app_parent.zoom_mode in ["100%", "Spin"]:
                    event.accept()
                    return
                else:
                    super().wheelEvent(event)
                    return
            # 마우스 휠 동작이 "사진 넘기기"로 설정된 경우
            if hasattr(self.app_parent, 'grid_mode'):
                wheel_delta = event.angleDelta().y()
                if wheel_delta == 0:
                    super().wheelEvent(event)
                    return

                ## 민감도 로직 적용 ##
                current_direction = 1 if wheel_delta > 0 else -1

                # 휠 방향이 바뀌면 누적 카운터 초기화
                if self.app_parent.last_wheel_direction != current_direction:
                    self.app_parent.mouse_wheel_accumulator = 0
                    self.app_parent.last_wheel_direction = current_direction
                
                # 카운터 증가
                self.app_parent.mouse_wheel_accumulator += 1
                # 휠 이벤트 발생 시마다 타이머 재시작
                self.app_parent.wheel_reset_timer.start()

                # 민감도 설정값에 도달했는지 확인
                if self.app_parent.mouse_wheel_accumulator >= self.app_parent.mouse_wheel_sensitivity:
                    # 도달했으면 액션 수행 및 카운터 초기화
                    self.app_parent.mouse_wheel_accumulator = 0
                    # 액션 수행 시 타이머 중지
                    self.app_parent.wheel_reset_timer.stop()

                    if self.app_parent.grid_mode == "Off":
                        # === Grid Off 모드: 이전/다음 사진 ===
                        if current_direction > 0:
                            self.app_parent.show_previous_image()
                        else:
                            self.app_parent.show_next_image()
                    elif self.app_parent.grid_mode != "Off":
                        # === Grid 모드: 그리드 셀 간 이동 ===
                        if current_direction > 0:
                            self.app_parent.navigate_grid(-1)
                        else:
                            self.app_parent.navigate_grid(1)
                    
                    event.accept()
                    return
                else:
                    # 민감도에 도달하지 않았으면 이벤트만 소비하고 아무것도 하지 않음
                    event.accept()
                    return
        # 기타 경우에는 기본 스크롤 동작 수행
        super().wheelEvent(event)


