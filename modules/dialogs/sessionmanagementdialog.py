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



class SessionManagementDialog(QDialog):
    def __init__(self, parent_widget: QWidget, main_app_logic: 'VibeCullingApp'): # 부모 위젯과 로직 객체를 분리
        super().__init__(parent_widget) # QDialog의 부모 설정
        self.parent_app = main_app_logic # VibeCullingApp의 메서드 호출을 위해 저장

        self.setWindowTitle(LanguageManager.translate("세션 관리"))
        self.setMinimumSize(500, 400) # 팝업창 최소 크기

        # 다크 테마 적용
        apply_dark_title_bar(self)
        palette = QPalette(); palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        self.setPalette(palette); self.setAutoFillBackground(True)

        # --- 메인 레이아웃 ---
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        button_style = f"""
            QPushButton {{
                background-color: {ThemeManager.get_color('bg_secondary')}; color: {ThemeManager.get_color('text')};
                border: none; padding: 8px 12px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {ThemeManager.get_color('bg_hover')}; }}
            QPushButton:pressed {{ background-color: {ThemeManager.get_color('bg_pressed')}; }}
            QPushButton:disabled {{
                background-color: {ThemeManager.get_color('bg_disabled')};
                color: {ThemeManager.get_color('text_disabled')};
            }}
        """

        # --- 1. 현재 세션 저장 버튼 ---
        self.save_current_button = QPushButton(LanguageManager.translate("현재 세션 저장"))
        self.save_current_button.setStyleSheet(button_style)
        self.save_current_button.clicked.connect(self.prompt_and_save_session)
        main_layout.addWidget(self.save_current_button)

        # --- 2. 저장된 세션 목록 ---
        list_label = QLabel(LanguageManager.translate("저장된 세션 목록 (최대 20개):"))
        list_label.setStyleSheet(f"color: {ThemeManager.get_color('text')}; margin-top: 10px;")
        main_layout.addWidget(list_label)

        self.session_list_widget = QListWidget()
        self.session_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')};
                border-radius: 3px; padding: 5px;
            }}
            QListWidget::item {{ padding: 3px 2px; }}
            QListWidget::item:selected {{
                background-color: {ThemeManager.get_color('accent')};
                color: white; /* 선택 시 텍스트 색상 */
            }}
        """)
        self.session_list_widget.currentItemChanged.connect(self.update_all_button_states)
        main_layout.addWidget(self.session_list_widget, 1)

        # --- 3. 불러오기 및 삭제 버튼 ---
        buttons_layout = QHBoxLayout()
        self.load_button = QPushButton(LanguageManager.translate("선택 세션 불러오기"))
        self.load_button.setStyleSheet(button_style)
        self.load_button.clicked.connect(self.load_selected_session)
        self.load_button.setEnabled(False)

        self.delete_button = QPushButton(LanguageManager.translate("선택 세션 삭제"))
        self.delete_button.setStyleSheet(button_style)
        self.delete_button.clicked.connect(self.delete_selected_session)
        self.delete_button.setEnabled(False)

        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.load_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch(1)
        main_layout.addLayout(buttons_layout)
        
        self.populate_session_list()
        self.update_all_button_states()

    def populate_session_list(self):
        """VibeCullingApp의 saved_sessions를 가져와 목록 위젯을 채웁니다."""
        self.session_list_widget.clear()
        
        # 타임스탬프를 기준으로 세션을 정렬합니다 (오래된 것이 위로).
        session_items = self.parent_app.saved_sessions.items()
        # 타임스탬프가 없는 경우를 대비하여 기본값("")을 사용하고, 문자열로 정렬합니다.
        sorted_session_items = sorted(
            session_items, 
            key=lambda item: item[1].get("timestamp", "")
        )
        
        for session_name, session_data in sorted_session_items:
            timestamp = session_data.get("timestamp", "")
            display_text = session_name
            if timestamp:
                try: 
                    dt_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    formatted_ts = dt_obj.strftime("%y/%m/%d %H:%M")
                    display_text = f"{session_name} ({formatted_ts})"
                except ValueError:
                    pass 
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, session_name)
            self.session_list_widget.addItem(item)
            
        self.update_all_button_states()


    def update_all_button_states(self): # 새로운 메서드 또는 기존 update_button_states 확장
        """세션 목록 선택 상태 및 이미지 로드 상태에 따라 모든 버튼의 활성화 상태를 업데이트합니다."""
        # 1. 불러오기/삭제 버튼 상태 업데이트 (기존 로직)
        selected_item = self.session_list_widget.currentItem()
        is_item_selected = selected_item is not None
        self.load_button.setEnabled(is_item_selected)
        self.delete_button.setEnabled(is_item_selected)
        logging.debug(f"SessionManagementDialog.update_all_button_states: Item selected={is_item_selected}")

        # 2. "현재 세션 저장" 버튼 상태 업데이트
        # VibeCullingApp의 image_files 목록이 비어있지 않을 때만 활성화
        can_save_session = bool(self.parent_app.image_files) # 이미지 파일 목록이 있는지 확인
        self.save_current_button.setEnabled(can_save_session)
        logging.debug(f"SessionManagementDialog.update_all_button_states: Can save session={can_save_session}")



    def prompt_and_save_session(self):
        default_name = self.parent_app._generate_default_session_name()

        self.parent_app.is_input_dialog_active = True # 메인 앱의 플래그 설정
        try:
            text, ok = QInputDialog.getText(self,
                                             LanguageManager.translate("세션 이름"),
                                             LanguageManager.translate("저장할 세션 이름을 입력하세요:"),
                                             QLineEdit.Normal,
                                             default_name)
        finally:
            self.parent_app.is_input_dialog_active = False # 메인 앱의 플래그 해제

        if ok and text:
            if self.parent_app.save_current_session(text): # 성공 시
                self.populate_session_list() # 목록 새로고침
        elif ok and not text:
            self.parent_app.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("저장 오류"), LanguageManager.translate("세션 이름을 입력해야 합니다."))


    def load_selected_session(self):
        selected_items = self.session_list_widget.selectedItems()
        if selected_items:
            session_name_to_load = selected_items[0].data(Qt.UserRole) # 저장된 실제 이름 가져오기
            
            success = self.parent_app.load_session(session_name_to_load)
            
            if success:
                self.accept() # SessionManagementDialog 닫기
                
                # 부모가 settings_popup인지 확인하고 닫습니다.
                parent_popup = self.parent()
                if parent_popup and hasattr(self.parent_app, 'settings_popup') and parent_popup is self.parent_app.settings_popup:
                    parent_popup.accept()


    def delete_selected_session(self):
        selected_items = self.session_list_widget.selectedItems()
        if selected_items:
            session_name_to_delete = selected_items[0].data(Qt.UserRole)
            reply = self.parent_app.show_themed_message_box(
                QMessageBox.Question,
                LanguageManager.translate("삭제 확인"),
                LanguageManager.translate("'{session_name}' 세션을 정말 삭제하시겠습니까?").format(session_name=session_name_to_delete),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.parent_app.delete_session(session_name_to_delete)
                # self.populate_session_list() # delete_session 내부에서 호출될 것임

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

