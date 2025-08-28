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



def format_camera_name(make, model):
    make_str = (make or "").strip()
    model_str = (model or "").strip()
    # 1. OLYMPUS IMAGING CORP. → OLYMPUS로 치환
    if make_str.upper() == "OLYMPUS IMAGING CORP.":
        make_str = "OLYMPUS"
    # 2. RICOH가 make에 있으면 make 생략
    if "RICOH" in make_str.upper():
        make_str = ""
    if make_str.upper().find("NIKON") != -1 and model_str.upper().startswith("NIKON"):
        return model_str
    if make_str.upper().find("CANON") != -1 and model_str.upper().startswith("CANON"):
        return model_str
    return f"{make_str} {model_str}".strip()

