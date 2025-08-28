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



def get_app_data_dir():
    """
    플랫폼에 맞는 애플리케이션 데이터 디렉토리 경로를 반환하고,
    해당 디렉토리가 없으면 생성합니다.

    - Windows: C:\\Users\\<Username>\\AppData\\Roaming\\VibeCulling
    - macOS:   ~/Library/Application Support/VibeCulling
    - Linux:   ~/.config/VibeCulling
    """
    app_name = "VibeCulling"
    home = Path.home()

    if sys.platform == "win32":
        app_data_path = home / "AppData" / "Roaming" / app_name
    elif sys.platform == "darwin":
        app_data_path = home / "Library" / "Application Support" / app_name
    else:
        # Linux 및 기타 Unix 계열
        app_data_path = home / ".config" / app_name

    # 디렉토리가 존재하지 않으면 생성합니다.
    # parents=True: 중간 경로가 없어도 생성
    # exist_ok=True: 이미 존재해도 오류 발생 안 함
    app_data_path.mkdir(parents=True, exist_ok=True)
    
    return app_data_path


