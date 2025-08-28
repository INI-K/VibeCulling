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



                preview_resolution_str = LanguageManager.translate("정보 없음") # 또는 "-"

            logging.info(f"파일 분석 완료: 호환={is_raw_compatible}, 모델='{final_camera_model_display}', 원본={original_resolution_str}, 미리보기={preview_resolution_str}")

            self.last_processed_camera_model = None # 새 폴더 로드 시 이전 카메라 모델 정보 초기화
            
            # --- 2. 저장된 설정 확인 및 메시지 박스 표시 결정 ---
            chosen_method = None # 사용자가 최종 선택한 처리 방식 ("preview" or "decode")
            dont_ask_again_for_this_model = False

            # final_camera_model_display가 유효할 때만 camera_raw_settings 확인
            if final_camera_model_display != LanguageManager.translate("알 수 없는 카메라"):
                saved_setting_for_this_action = self.get_camera_raw_setting(final_camera_model_display)
                if saved_setting_for_this_action: # 해당 모델에 대한 설정이 존재하면
                    # 저장된 "dont_ask" 값을 dont_ask_again_for_this_model의 초기값으로 사용
                    dont_ask_again_for_this_model = saved_setting_for_this_action.get("dont_ask", False)

                    if dont_ask_again_for_this_model: # "다시 묻지 않음"이 True이면
                        chosen_method = saved_setting_for_this_action.get("method")
                        logging.info(f"'{final_camera_model_display}' 모델에 저장된 '다시 묻지 않음' 설정 사용: {chosen_method}")
                    else: # "다시 묻지 않음"이 False이거나 dont_ask 키가 없으면 메시지 박스 표시
                        chosen_method, dont_ask_again_for_this_model_from_dialog = self._show_raw_processing_choice_dialog(
                            is_raw_compatible, final_camera_model_display, original_resolution_str, preview_resolution_str
                        )
                        # 사용자가 대화상자를 닫지 않았을 때만 dont_ask_again_for_this_model 값을 업데이트
                        if chosen_method is not None:
                            dont_ask_again_for_this_model = dont_ask_again_for_this_model_from_dialog
                else: # 해당 모델에 대한 설정이 아예 없으면 메시지 박스 표시
                    chosen_method, dont_ask_again_for_this_model_from_dialog = self._show_raw_processing_choice_dialog(
                        is_raw_compatible, final_camera_model_display, original_resolution_str, preview_resolution_str
                    )
                    if chosen_method is not None:
                        dont_ask_again_for_this_model = dont_ask_again_for_this_model_from_dialog
            else: # 카메라 모델을 알 수 없는 경우 -> 항상 메시지 박스 표시
                logging.info(f"카메라 모델을 알 수 없어, 메시지 박스 표시 (호환성 기반)")
                chosen_method, dont_ask_again_for_this_model_from_dialog = self._show_raw_processing_choice_dialog(
                    is_raw_compatible, final_camera_model_display, original_resolution_str, preview_resolution_str
                )
                if chosen_method is not None:
                    dont_ask_again_for_this_model = dont_ask_again_for_this_model_from_dialog


            if chosen_method is None:
                logging.info("RAW 처리 방식 선택되지 않음 (대화상자 닫힘 등). 로드 취소.")
                return
            
            logging.info(f"사용자 선택 RAW 처리 방식: {chosen_method}")

            # --- "decode" 모드일 경우 진행률 대화상자 표시 ---
            if chosen_method == "decode":
                self._show_first_raw_decode_progress()


            # --- 3. "다시 묻지 않음" 선택 시 설정 저장 ---
            # dont_ask_again_for_this_model은 위 로직을 통해 올바른 값 (기존 값 또는 대화상자 선택 값)을 가짐
            if final_camera_model_display != LanguageManager.translate("알 수 없는 카메라"):
                # chosen_method가 None이 아닐 때만 저장 로직 실행
                self.set_camera_raw_setting(final_camera_model_display, chosen_method, dont_ask_again_for_this_model)
            
            if final_camera_model_display != LanguageManager.translate("알 수 없는 카메라"):
                self.last_processed_camera_model = final_camera_model_display
            else:
                self.last_processed_camera_model = None
            
            # --- 4. ImageLoader에 선택된 처리 방식 설정 및 나머지 파일 로드 ---
            self.image_loader.set_raw_load_strategy(chosen_method)
            logging.info(f"ImageLoader 처리 방식 설정 (새 로드): {chosen_method}")

            # --- RAW 로드 성공 시 ---
            print(f"로드된 RAW 파일 수: {len(unique_raw_files)}")
            self.image_files = unique_raw_files

            # 썸네일 패널에 파일 목록 설정
            self.thumbnail_panel.set_image_files(self.image_files)
            
            self.raw_folder = folder_path
            self.is_raw_only_mode = True

            self.current_folder = ""
            self.raw_files = {} # RAW 전용 모드에서는 이 딕셔너리는 다른 용도로 사용되지 않음
            self.folder_path_label.setText(LanguageManager.translate("폴더 경로"))
            self.update_jpg_folder_ui_state()

            self.raw_folder_path_label.setText(folder_path)
            self.update_raw_folder_ui_state()
            self.update_match_raw_button_state()
            self.load_button.setEnabled(False)

            self.grid_page_start_index = 0
            self.current_grid_index = 0
            self.image_loader.clear_cache() # 이전 캐시 비우기 (다른 전략이었을 수 있으므로)

            self.zoom_mode = "Fit"
            self.fit_radio.setChecked(True)
            self.grid_mode = "Off"
            self.grid_off_radio.setChecked(True)
            self.update_zoom_radio_buttons_state()
            self.save_state()

            self.current_image_index = 0
            # display_current_image() 호출 전에 ImageLoader의 _raw_load_strategy가 설정되어 있어야 함
            logging.info(f"display_current_image 호출 직전 ImageLoader 전략: {self.image_loader._raw_load_strategy} (ID: {id(self.image_loader)})")
            self.display_current_image() 

            if self.grid_mode == "Off":
                self.start_background_thumbnail_preloading()

            if self.session_management_popup and self.session_management_popup.isVisible():
                self.session_management_popup.update_all_button_states()

    def _show_raw_processing_choice_dialog(self, is_compatible, model_name, orig_res, prev_res):
        """RAW 처리 방식 선택을 위한 맞춤형 대화상자를 표시합니다."""
        dialog = QDialog(self)
        dialog.setWindowTitle(LanguageManager.translate("RAW 파일 처리 방식 선택")) # 새 번역 키
        
        # 다크 테마 적용 (메인 윈도우의 show_themed_message_box 참조)
        apply_dark_title_bar(dialog)
        palette = QPalette(); palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        dialog.setPalette(palette); dialog.setAutoFillBackground(True)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        message_label = QLabel()
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"color: {ThemeManager.get_color('text')};")
        message_label.setTextFormat(Qt.RichText)

        radio_group = QButtonGroup(dialog)
        preview_radio = QRadioButton()
        decode_radio = QRadioButton()
        
        # 체크박스 스타일은 VibeCullingApp의 것을 재사용하거나 여기서 정의
        checkbox_style = f"""
            QCheckBox {{ color: {ThemeManager.get_color('text')}; padding: {UIScaleManager.get("checkbox_padding")}px; }}
            QCheckBox::indicator {{ width: {UIScaleManager.get("checkbox_size")}px; height: {UIScaleManager.get("checkbox_size")}px; }}
            QCheckBox::indicator:checked {{ background-color: {ThemeManager.get_color('accent')}; border: {UIScaleManager.get("checkbox_border")}px solid {ThemeManager.get_color('accent')}; border-radius: {UIScaleManager.get("checkbox_border_radius")}px; }}
            QCheckBox::indicator:unchecked {{ background-color: {ThemeManager.get_color('bg_primary')}; border: {UIScaleManager.get("checkbox_border")}px solid {ThemeManager.get_color('border')}; border-radius: {UIScaleManager.get("checkbox_border_radius")}px; }}
            QCheckBox::indicator:unchecked:hover {{ border: {UIScaleManager.get("checkbox_border")}px solid {ThemeManager.get_color('text_disabled')}; }}
        """
        radio_style = f"""
            QRadioButton {{ color: {ThemeManager.get_color('text')}; padding: 0px; }} 
            QRadioButton::indicator {{ width: {UIScaleManager.get("radiobutton_size")}px; height: {UIScaleManager.get("radiobutton_size")}px; }}
            QRadioButton::indicator:checked {{ background-color: {ThemeManager.get_color('accent')}; border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('accent')}; border-radius: {UIScaleManager.get("radiobutton_border_radius")}px; }}
            QRadioButton::indicator:unchecked {{ background-color: {ThemeManager.get_color('bg_primary')}; border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('border')}; border-radius: {UIScaleManager.get("radiobutton_border_radius")}px; }}
            QRadioButton::indicator:unchecked:hover {{ border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('text_disabled')}; }}
        """
        preview_radio.setStyleSheet(radio_style)
        decode_radio.setStyleSheet(radio_style)

        # 1. 번역할 기본 템플릿 문자열 키를 정의합니다.
        checkbox_text_template_key = "{camera_model_placeholder}의 RAW 처리 방식에 대해 다시 묻지 않습니다."
        # 2. 해당 키로 번역된 템플릿을 가져옵니다.
        translated_checkbox_template = LanguageManager.translate(checkbox_text_template_key)
        # 3. 번역된 템플릿에 실제 카메라 모델명을 포맷팅합니다.
        #    model_name이 "알 수 없는 카메라"일 경우, 해당 번역도 고려해야 함.
        #    여기서는 model_name 자체를 그대로 사용.
        final_checkbox_text = translated_checkbox_template.format(camera_model_placeholder=model_name)
        
        dont_ask_checkbox = QCheckBox(final_checkbox_text) # 포맷팅된 최종 텍스트 사용
        dont_ask_checkbox.setStyleSheet(checkbox_style) # checkbox_style은 이미 정의되어 있다고 가정

        confirm_button = QPushButton(LanguageManager.translate("확인"))
        confirm_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ThemeManager.get_color('bg_secondary')};
                    color: {ThemeManager.get_color('text')};
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {ThemeManager.get_color('bg_hover')};
                }}
                QPushButton:pressed {{
                    background-color: {ThemeManager.get_color('bg_pressed')};
                }}
            """)
        confirm_button.clicked.connect(dialog.accept)
        
        chosen_method_on_accept = None # 확인 버튼 클릭 시 선택된 메소드 저장용

        # line-height 스타일 적용 (선택 사항)
        html_wrapper_start = "<div style='line-height: 150%;'>" # 예시 줄 간격
        html_wrapper_end = "</div>"

        if is_compatible:
            dialog.setMinimumWidth(917)
            msg_template_key = ("{model_name_placeholder}의 원본 이미지 해상도는 <b>{orig_res_placeholder}</b>입니다.<br>"
                                "{model_name_placeholder}의 RAW 파일에 포함된 미리보기(프리뷰) 이미지의 해상도는 <b>{prev_res_placeholder}</b>입니다.<br>"
                                "미리보기를 통해 이미지를 보시겠습니까, RAW 파일을 디코딩해서 보시겠습니까?")
            translated_msg_template = LanguageManager.translate(msg_template_key)
            formatted_text = translated_msg_template.format(
                model_name_placeholder=model_name,
                orig_res_placeholder=orig_res,
                prev_res_placeholder=prev_res
            )
            # HTML로 감싸기
            message_label.setText(f"{html_wrapper_start}{formatted_text}{html_wrapper_end}")
            
            preview_radio.setText(LanguageManager.translate("미리보기 이미지 사용 (미리보기의 해상도가 충분하거나 빠른 작업 속도가 중요한 경우.)"))

            # "RAW 디코딩" 라디오 버튼 텍스트 설정 시 \n 포함된 키 사용
            decode_radio_key = "RAW 디코딩 (느림. 일부 카메라 호환성 문제 있음.\n미리보기의 해상도가 너무 작거나 원본 해상도가 반드시 필요한 경우에만 사용 권장.)"
            decode_radio.setText(LanguageManager.translate(decode_radio_key))
            
            radio_group.addButton(preview_radio, 0) # preview = 0
            radio_group.addButton(decode_radio, 1)  # decode = 1
            preview_radio.setChecked(True) # 기본 선택: 미리보기

            layout.addWidget(message_label)
            layout.addSpacing(25) # message_label과 첫 번째 라디오 버튼 사이 간격
            layout.addWidget(preview_radio)
            layout.addSpacing(10)
            layout.addWidget(decode_radio)
            layout.addSpacing(25) # 두 번째 라디오버튼과 don't ask 체크박스 사이 간격
            layout.addWidget(dont_ask_checkbox)
            layout.addSpacing(15) # don't ask 체크박스와 확인 버튼 사이 간격
            layout.addWidget(confirm_button, 0, Qt.AlignCenter)

            if dialog.exec() == QDialog.Accepted:
                chosen_method_on_accept = "preview" if radio_group.checkedId() == 0 else "decode"
                return chosen_method_on_accept, dont_ask_checkbox.isChecked()
            else:
                return None, False # 대화상자 닫힘
        else: # 호환 안됨
            dialog.setMinimumWidth(933)
            msg_template_key_incompatible = ("호환성 문제로 {model_name_placeholder}의 RAW 파일을 디코딩 할 수 없습니다.<br>"
                                             "RAW 파일에 포함된 <b>{prev_res_placeholder}</b>의 미리보기 이미지를 사용하겠습니다.<br>"
                                             "({model_name_placeholder}의 원본 이미지 해상도는 <b>{orig_res_placeholder}</b>입니다.)")
            translated_msg_template_incompatible = LanguageManager.translate(msg_template_key_incompatible)
            formatted_text = translated_msg_template_incompatible.format(
                model_name_placeholder=model_name,
                prev_res_placeholder=prev_res,
                orig_res_placeholder=orig_res
            )
            message_label.setText(f"{html_wrapper_start}{formatted_text}{html_wrapper_end}")

            layout.addWidget(message_label)
            layout.addSpacing(20) # message_label과 don't ask 체크박스 사이 간격
            layout.addWidget(dont_ask_checkbox) # 이 경우에도 다시 묻지 않음은 유효
            layout.addSpacing(15) # don't ask 체크박스와 확인 버튼 사이 간격
            layout.addWidget(confirm_button, 0, Qt.AlignCenter)

            if dialog.exec() == QDialog.Accepted:
                # 호환 안되면 무조건 미리보기 사용
                return "preview", dont_ask_checkbox.isChecked()
            else:
                return None, False # 대화상자 닫힘

    def match_raw_files(self, folder_path, silent=False):
        """JPG 파일과 RAW 파일 매칭 (백그라운드에서 실행)"""
        if not folder_path or not self.current_folder:
            if not silent:
                self.show_themed_message_box(QMessageBox.Warning, "경고", "먼저 JPG 폴더를 로드해야 합니다.")
            return False
            
        logging.info(f"RAW 폴더 매칭 시작: {folder_path}")
        
        self._is_silent_load = silent
        
        self.start_background_loading(
            mode='jpg_with_raw',
            jpg_folder_path=self.current_folder, 
            raw_folder_path=folder_path, 
            raw_file_list=None
        )
        return True


    def get_bundled_exiftool_path(self):
        """애플리케이션 폴더 구조에서 ExifTool 경로 찾기"""
        # 애플리케이션 기본 디렉토리 확인
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 경우
            app_dir = Path(sys.executable).parent
        else:
            # 일반 스크립트로 실행된 경우
            app_dir = Path(__file__).parent
        
        # 1. 먼저 새 구조의 exiftool 폴더 내에서 확인
        exiftool_path = app_dir / "exiftool" / "exiftool.exe"
        if exiftool_path.exists():
            # print(f"ExifTool 발견: {exiftool_path}")
            logging.info(f"ExifTool 발견: {exiftool_path}")
            return str(exiftool_path)
        
        # 2. PyInstaller _internal 폴더 내에서 확인
        exiftool_path = app_dir / "_internal" / "exiftool" / "exiftool.exe"
        if exiftool_path.exists():
            logging.info(f"ExifTool 발견(_internal 경로): {exiftool_path}")
            return str(exiftool_path)
        
        # 3. 이전 구조의 resources 폴더에서 확인 (호환성 유지)
        exiftool_path = app_dir / "resources" / "exiftool.exe"
        if exiftool_path.exists():
            print(f"ExifTool 발견(레거시 경로): {exiftool_path}")
            logging.info(f"ExifTool 발견(레거시 경로): {exiftool_path}")
            return str(exiftool_path)
        
        # 4. 애플리케이션 기본 폴더 내에서 직접 확인
        exiftool_path = app_dir / "exiftool.exe" 
        if exiftool_path.exists():
            # print(f"ExifTool 발견(기본 폴더): {exiftool_path}")
            logging.info(f"ExifTool 발견: {exiftool_path}")
            return str(exiftool_path)
        
        # 4. PATH 환경변수에서 검색 가능하도록 이름만 반환 (선택적)
        logging.warning("ExifTool을 찾을 수 없습니다. PATH에 있다면 기본 이름으로 시도합니다.")
        return "exiftool.exe"

    def get_exiftool_path(self) -> str:
        """운영체제별로 exiftool 경로를 반환합니다."""
        system = platform.system()
        if system == "Darwin":
            # macOS 번들 내부 exiftool 사용
            logging.info(f"맥 전용 exiftool사용")
            bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.argv[0]))
            return os.path.join(bundle_dir, "exiftool")
        elif system == "Windows":
            # Windows: 기존 get_bundled_exiftool_path 로 경로 확인
            return self.get_bundled_exiftool_path()
        else:
            # 기타 OS: 시스템 PATH에서 exiftool 호출
            return "exiftool"

    def show_themed_message_box(self, icon, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.NoButton):
        """스타일 및 제목 표시줄 다크 테마가 적용된 QMessageBox 표시"""
        message_box = QMessageBox(self)
        message_box.setWindowTitle(title)
        message_box.setText(text)
        message_box.setIcon(icon)
        message_box.setStandardButtons(buttons)
        message_box.setDefaultButton(default_button)

        # 메시지 박스 내용 다크 테마 스타일 적용
        message_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {ThemeManager.get_color('bg_primary')};
                color: {ThemeManager.get_color('text')};
            }}
            QLabel {{
                color: {ThemeManager.get_color('text')};
            }}
            QPushButton {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: none;
                padding: 8px;
                border-radius: 4px;
                min-width: 60px;
            }}
            QPushButton:hover {{
                background-color: {ThemeManager.get_color('bg_hover')};
            }}
            QPushButton:pressed {{
                background-color: {ThemeManager.get_color('bg_pressed')};
            }}
        """)

        # 제목 표시줄 다크 테마 적용 (Windows용)
        apply_dark_title_bar(message_box)

        return message_box.exec() # 실행하고 결과 반환
    
    def open_raw_folder_in_explorer(self, folder_path):
        """RAW 폴더 경로를 윈도우 탐색기에서 열기"""
        if not folder_path or folder_path == LanguageManager.translate("RAW 폴더를 선택하세요"):
            return
        
        try:
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            logging.error(f"폴더 열기 실패: {e}")

    def on_raw_toggle_changed(self, checked):
        """RAW 이동 토글 상태 변경 처리"""
        self.move_raw_files = checked
        print(f"RAW 파일 이동 설정: {'활성화' if checked else '비활성화'}")

    def on_folder_image_dropped(self, folder_index, drag_data):
        """
        폴더 레이블(EditableFolderPathLabel)에 이미지가 드롭되었을 때 호출되는 최종 슬롯.
        MIME 데이터를 파싱하여 올바른 컨텍스트로 이미지 이동을 처리합니다.
        """
        try:
            logging.info(f"이미지 드롭 이벤트 수신: 폴더={folder_index}, 데이터='{drag_data}'")

            # 1. 폴더 유효성 검사
            if (folder_index < 0 or
                folder_index >= len(self.target_folders) or
                not self.target_folders[folder_index] or
                not os.path.isdir(self.target_folders[folder_index])):

                self.show_themed_message_box(
                    QMessageBox.Warning,
                    LanguageManager.translate("경고"),
                    LanguageManager.translate("유효하지 않은 폴더입니다.")
                )
                return

            # 2. 드래그 데이터 파싱
            parts = drag_data.split(":")
            if len(parts) < 3 or parts[0] != "image_drag":
                logging.error(f"잘못된 드래그 데이터 형식 수신: {drag_data}")
                return

            mode = parts[1]  # "gridOff", "compareA", "grid" 등
            indices_str = parts[2]

            # 3. 모드에 따른 분기 처리
            if mode == "gridOff" or mode == "compareA":
                # Grid Off 또는 Compare 모드에서 단일 이미지 드래그
                try:
                    image_index = int(indices_str)
                    if 0 <= image_index < len(self.image_files):
                        # 이동할 이미지의 인덱스가 현재 표시 중인 이미지와 다를 수 있으므로,
                        # self.current_image_index를 이동할 이미지의 인덱스로 임시 설정합니다.
                        # move_current_image_to_folder는 self.current_image_index를 참조하기 때문입니다.
                        self.current_image_index = image_index

                        # context_mode를 MIME 데이터에서 직접 가져온 'mode'로 설정합니다.
                        # "compareA" -> "CompareA"
                        # "gridOff" -> "Off"
                        context = "CompareA" if mode == "compareA" else "Off"
                        logging.info(f"단일 이미지 이동 실행: index={image_index}, context='{context}'")
                        self.move_current_image_to_folder(folder_index, context_mode=context)
                    else:
                        logging.error(f"유효하지 않은 이미지 인덱스: {image_index}")
                except ValueError:
                    logging.error(f"이미지 인덱스 파싱 오류: {indices_str}")

            elif mode == "grid":
                # Grid 모드에서 단일 또는 다중 이미지 드래그
                try:
                    # 다중 선택된 이미지를 드래그했는지 확인 (인덱스가 쉼표로 구분됨)
                    if "," in indices_str:
                        selected_indices = [int(idx) for idx in indices_str.split(",")]
                        
                        # 전역 인덱스를 현재 페이지의 로컬 인덱스로 변환
                        grid_indices_to_select = []
                        for global_idx in selected_indices:
                            # 드래그된 이미지가 현재 페이지에 속하는지 확인
                            if self.grid_page_start_index <= global_idx < self.grid_page_start_index + len(self.grid_labels):
                                grid_idx = global_idx - self.grid_page_start_index
                                grid_indices_to_select.append(grid_idx)
                        
                        if grid_indices_to_select:
                            self.selected_grid_indices = set(grid_indices_to_select)
                            logging.info(f"다중 이미지 이동 실행: {len(self.selected_grid_indices)}개")
                            self.move_grid_image(folder_index)
                        else:
                            logging.warning("드래그된 다중 선택 이미지가 현재 페이지에 없습니다.")
                    else:
                        # 단일 이미지를 드래그한 경우
                        global_index = int(indices_str)
                        if 0 <= global_index < len(self.image_files):
                            # 이동할 이미지에 맞게 페이지와 현재 인덱스를 설정
                            rows, cols = self._get_grid_dimensions()
                            num_cells = rows * cols
                            self.grid_page_start_index = (global_index // num_cells) * num_cells
                            self.current_grid_index = global_index % num_cells
                            
                            # 선택 상태를 단일 선택으로 초기화
                            if hasattr(self, 'selected_grid_indices'):
                                self.selected_grid_indices.clear()
                            
                            logging.info(f"그리드 내 단일 이미지 이동 실행: global_index={global_index}")
                            self.move_grid_image(folder_index)
                        else:
                            logging.error(f"유효하지 않은 이미지 인덱스: {global_index}")
                except ValueError:
                    logging.error(f"그리드 인덱스 파싱 오류: {indices_str}")
            
            else:
                logging.error(f"알 수 없는 드래그 모드 수신: {mode}")

        except Exception as e:
            logging.error(f"on_folder_image_dropped에서 예외 발생: {e}", exc_info=True)
            self.show_themed_message_box(
                QMessageBox.Critical,
                LanguageManager.translate("오류"),
                LanguageManager.translate("이미지 이동 중 오류가 발생했습니다.")
            )
        finally:
            self.activateWindow()
            self.setFocus()


    def handle_canvas_to_folder_drop(self, folder_index):
        """캔버스에서 폴더로 드래그 앤 드롭 처리"""
        try:
            # 1. Zoom Fit 상태 확인
            if self.zoom_mode != "Fit":
                self.show_themed_message_box(
                    QMessageBox.Information,
                    LanguageManager.translate("알림"),
                    LanguageManager.translate("Zoom Fit 모드에서만 드래그 앤 드롭이 가능합니다.")
                )
                return False
            
            # 2. 이미지 로드 상태 확인
            if not self.image_files or self.current_image_index < 0 or self.current_image_index >= len(self.image_files):
                self.show_themed_message_box(
                    QMessageBox.Warning,
                    LanguageManager.translate("경고"),
                    LanguageManager.translate("이동할 이미지가 없습니다.")
                )
                return False
            
            # 3. 폴더 유효성 확인
            if (folder_index < 0 or 
                folder_index >= len(self.target_folders) or 
                not self.target_folders[folder_index] or 
                not os.path.isdir(self.target_folders[folder_index])):
                
                self.show_themed_message_box(
                    QMessageBox.Warning,
                    LanguageManager.translate("경고"),
                    LanguageManager.translate("유효하지 않은 폴더입니다.")
                )
                return False
            
            # 4. Grid Off/Grid 모드에 따른 처리
            if self.grid_mode == "Off":
                # Grid Off 모드: move_current_image_to_folder 사용
                logging.info(f"Grid Off 모드: 현재 이미지 ({self.current_image_index}) 폴더 {folder_index}로 이동")
                
                context = "CompareA" if self.compare_mode_active else "Off"
                self.move_current_image_to_folder(folder_index, context_mode=context)
                return True
                
            elif self.grid_mode != "Off":
                # Grid 모드: move_grid_image 사용
                # (이 부분은 다중 선택을 지원하므로 context_mode가 이미 grid_mode로 기록됩니다. 수정 불필요)
                logging.info(f"Grid 모드: 현재 그리드 이미지 폴더 {folder_index}로 이동")
                
                if hasattr(self, 'current_grid_index') and self.current_grid_index >= 0:
                    if hasattr(self, 'selected_grid_indices'):
                        self.selected_grid_indices.clear()
                    
                    self.move_grid_image(folder_index)
                    return True
                else:
                    self.show_themed_message_box(
                        QMessageBox.Warning,
                        LanguageManager.translate("경고"),
                        LanguageManager.translate("선택된 그리드 이미지가 없습니다.")
                    )
                    return False
            else:
                logging.error(f"알 수 없는 그리드 모드: {self.grid_mode}")
                return False
                
        except Exception as e:
            logging.error(f"handle_canvas_to_folder_drop 오류: {e}")
            self.show_themed_message_box(
                QMessageBox.Critical,
                LanguageManager.translate("오류"),
                LanguageManager.translate("이미지 이동 중 오류가 발생했습니다.")
            )
            return False

    def setup_folder_selection_ui(self):
        """분류 폴더 설정 UI를 동적으로 구성하고 컨테이너 위젯을 반환합니다."""
        self.folder_buttons = []
        self.folder_path_labels = []
        self.folder_action_buttons = []
        
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(UIScaleManager.get("category_folder_vertical_spacing"))
        
        # UIScaleManager 값 미리 가져오기
        delete_button_width = UIScaleManager.get("delete_button_width")
        folder_container_spacing = UIScaleManager.get("folder_container_spacing", 5)

        # 버튼 스타일 미리 정의
        number_button_style = ThemeManager.generate_main_button_style()
        action_button_style = ThemeManager.generate_action_button_style()
        
        for i in range(self.folder_count):
            folder_container = QWidget()
            folder_layout = QHBoxLayout(folder_container)
            folder_layout.setContentsMargins(0, 0, 0, 0)
            folder_layout.setSpacing(folder_container_spacing)

            folder_button = QPushButton(f"{i+1}")
            folder_button.setStyleSheet(number_button_style)
            folder_button.clicked.connect(lambda checked=False, idx=i: self.select_category_folder(idx))

            folder_path_label = EditableFolderPathLabel()
            folder_path_label.set_folder_index(i)
            folder_path_label.imageDropped.connect(self.on_folder_image_dropped)
            folder_path_label.folderDropped.connect(lambda index, path: self._handle_category_folder_drop(path, index))
            folder_path_label.doubleClicked.connect(lambda full_path, idx=i: self.open_category_folder(idx, full_path))
            folder_path_label.stateChanged.connect(self.update_folder_action_button)
            folder_path_label.returnPressed.connect(lambda idx=i: self.confirm_subfolder_creation(idx))

            action_button = QPushButton("✕")
            action_button.setStyleSheet(action_button_style)

            action_button.clicked.connect(lambda checked=False, idx=i: self.on_folder_action_button_clicked(idx))
            
            # 버튼 높이 밑 너비 동기화
            fm_label = QFontMetrics(folder_path_label.font())
            label_line_height = fm_label.height()
            padding = UIScaleManager.get("sort_folder_label_padding")
            fixed_height = label_line_height + padding
            folder_button.setFixedHeight(fixed_height)
            action_button.setFixedHeight(fixed_height)
            folder_button.setFixedWidth(delete_button_width)
            action_button.setFixedWidth(delete_button_width)
            
            folder_layout.addWidget(folder_button)
            folder_layout.addWidget(folder_path_label, 1)
            folder_layout.addWidget(action_button)
            
            main_layout.addWidget(folder_container)
            
            self.folder_buttons.append(folder_button)
            self.folder_path_labels.append(folder_path_label)
            self.folder_action_buttons.append(action_button)

        self.update_all_folder_labels_state()
        return main_container


    def update_all_folder_labels_state(self):
        """모든 분류 폴더 레이블의 상태를 현재 앱 상태에 맞게 업데이트합니다."""
        if not hasattr(self, 'folder_path_labels'):
            return

        images_loaded = bool(self.image_files)
        
        for i, label in enumerate(self.folder_path_labels):
            has_path = bool(i < len(self.target_folders) and self.target_folders[i])
            
            if has_path:
                label.set_state(EditableFolderPathLabel.STATE_SET, self.target_folders[i])
            elif images_loaded:
                label.set_state(EditableFolderPathLabel.STATE_EDITABLE)
            else:
                label.set_state(EditableFolderPathLabel.STATE_DISABLED)

    def update_folder_action_button(self, index, state):
        """지정된 인덱스의 액션 버튼('X'/'V')을 상태에 맞게 업데이트합니다."""
        if index < 0 or index >= len(self.folder_action_buttons):
            return
        button = self.folder_action_buttons[index]
        
        if state == EditableFolderPathLabel.STATE_DISABLED:
            button.setText("✕")
            button.setEnabled(False)
        elif state == EditableFolderPathLabel.STATE_EDITABLE:
            button.setText("✓")
            button.setEnabled(True)
        elif state == EditableFolderPathLabel.STATE_SET:
            button.setText("✕")
            button.setEnabled(True)

    def on_folder_action_button_clicked(self, index):
        """분류 폴더의 액션 버튼(X/V) 클릭을 처리하는 통합 핸들러"""
        if index < 0 or index >= len(self.folder_action_buttons):
            return
        
        button = self.folder_action_buttons[index]
        button_text = button.text()

        if button_text == "✓":
            # 체크 표시일 경우: 하위 폴더 생성 로직 호출
            self.confirm_subfolder_creation(index)
        elif button_text == "✕":
            # X 표시일 경우: 폴더 지정 취소 로직 호출
            self.clear_category_folder(index)            

    def confirm_subfolder_creation(self, index):
        """입력된 이름으로 하위 폴더를 생성하고 UI를 업데이트합니다."""
        if index < 0 or index >= len(self.folder_path_labels):
            return
            
        label = self.folder_path_labels[index]
        new_folder_name = label.text().strip()

        # 1. 유효성 검사
        if not self._is_valid_foldername(new_folder_name):
            self.show_themed_message_box(QMessageBox.Warning, 
                                        LanguageManager.translate("경고"), 
                                        LanguageManager.translate("잘못된 폴더명입니다."))
            return

        # 2. 기본 경로 설정
        base_path_str = self.raw_folder if self.is_raw_only_mode else self.current_folder
        if not base_path_str:
            self.show_themed_message_box(QMessageBox.Warning, 
                                        LanguageManager.translate("경고"), 
                                        LanguageManager.translate("기준 폴더가 로드되지 않았습니다."))
            return
            
        base_path = Path(base_path_str)
        new_full_path = base_path / new_folder_name

        # 3. 폴더 생성
        try:
            new_full_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"하위 폴더 생성 성공: {new_full_path}")
        except Exception as e:
            logging.error(f"하위 폴더 생성 실패: {e}")
            self.show_themed_message_box(QMessageBox.Critical, 
                                        LanguageManager.translate("에러"), 
                                        f"{LanguageManager.translate('폴더 생성 실패')}:\n{e}")
            return

        # 4. 상태 업데이트
        self.target_folders[index] = str(new_full_path)
        label.set_state(EditableFolderPathLabel.STATE_SET, str(new_full_path))
        self.save_state()

    def update_folder_buttons(self):
        """폴더 설정 상태에 따라 UI 업데이트"""
        # 안전한 범위 검사 추가
        if not hasattr(self, 'folder_buttons') or not self.folder_buttons:
            return  # 버튼이 아직 생성되지 않았으면 건너뛰기
        
        # 실제 생성된 버튼 개수와 설정된 폴더 개수 중 작은 값 사용
        actual_button_count = len(self.folder_buttons)
        target_count = min(self.folder_count, actual_button_count)
        
        # 모든 폴더 버튼은 항상 활성화
        for i in range(target_count):
            # 폴더 버튼 항상 활성화
            self.folder_buttons[i].setEnabled(True)
            
            # 폴더 경로 레이블 및 X 버튼 상태 설정
            has_folder = bool(i < len(self.target_folders) and self.target_folders[i] and os.path.isdir(self.target_folders[i]))
            
            # 폴더 경로 레이블 상태 설정
            self.folder_path_labels[i].setEnabled(has_folder)
            if has_folder:
                # 폴더가 지정된 경우 - 활성화 및 경로 표시
                self.folder_path_labels[i].setStyleSheet(f"""
                    QLabel {{
                        color: #AAAAAA;
                        padding: 5px;
                        background-color: {ThemeManager.get_color('bg_primary')};
                        border-radius: 1px;
                    }}
                """)
            else:
                # 폴더가 지정되지 않은 경우 - 비활성화 스타일
                self.folder_path_labels[i].setStyleSheet(f"""
                    QLabel {{
                        color: {ThemeManager.get_color('text_disabled')};
                        padding: 5px;
                        background-color: {ThemeManager.get_color('bg_disabled')};
                        border-radius: 1px;
                    }}
                """)
            
            self.folder_path_labels[i].update_original_style(self.folder_path_labels[i].styleSheet())

            # X 버튼 상태 설정
            self.folder_delete_buttons[i].setEnabled(has_folder)
    
    def select_category_folder(self, index):
        """분류 폴더 선택"""
        folder_path = QFileDialog.getExistingDirectory(
            self, f"{LanguageManager.translate('폴더 선택')} {index+1}", "", 
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder_path:
            self.target_folders[index] = folder_path
            # setText 대신 set_state를 사용하여 UI와 상태를 한 번에 업데이트합니다.
            self.folder_path_labels[index].set_state(EditableFolderPathLabel.STATE_SET, folder_path)
            self.save_state()
    
    def clear_category_folder(self, index):
        """분류 폴더 지정 취소"""
        self.target_folders[index] = ""
        # 현재 이미지 로드 상태에 따라 editable 또는 disabled 상태로 변경
        if self.image_files:
            self.folder_path_labels[index].set_state(EditableFolderPathLabel.STATE_EDITABLE)
        else:
            self.folder_path_labels[index].set_state(EditableFolderPathLabel.STATE_DISABLED)
        self.save_state()

    
    def open_category_folder(self, index, folder_path): # folder_path 인자 추가
        """선택된 분류 폴더를 탐색기에서 열기 (full_path 사용)"""
        # folder_path = self.folder_path_labels[index].text() # 이 줄 제거

        # 전달받은 folder_path(전체 경로) 직접 사용
        if not folder_path or folder_path == LanguageManager.translate("폴더를 선택하세요"):
            return

        try:
            if sys.platform == 'win32':
                os.startfile(folder_path) # folder_path 는 이제 전체 경로임
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            logging.error(f"폴더 열기 실패: {e}")
    
    
    def navigate_to_adjacent_page(self, direction):
        """그리드 모드에서 페이지 단위 이동 처리 (순환 기능 추가)"""
        if self.grid_mode == "Off" or not self.image_files:
            return

        rows, cols = self._get_grid_dimensions()
        if rows == 0: return
        num_cells = rows * cols
        total_images = len(self.image_files)
        if total_images == 0: return # 이미지가 없으면 중단

        total_pages = (total_images + num_cells - 1) // num_cells
        if total_pages <= 1: return # 페이지가 1개뿐이면 순환 의미 없음

        current_page = self.grid_page_start_index // num_cells

        # 새 페이지 계산 (모듈러 연산으로 순환)
        new_page = (current_page + direction + total_pages) % total_pages

        # 페이지 이동
        self.grid_page_start_index = new_page * num_cells
        self.current_grid_index = 0  # 새 페이지의 첫 셀 선택

        # 페이지 전환 시 선택 상태 초기화
        self.clear_grid_selection()

        # 그리드 뷰 업데이트
        self.update_grid_view()
    

    def show_previous_image(self):
        if not self.image_files: return
        self._prepare_for_photo_change()
        if self.current_image_index <= 0: self.current_image_index = len(self.image_files) - 1
        else: self.current_image_index -= 1
        self.force_refresh = True
        self.display_current_image()
        # 썸네일 패널 동기화 추가
        self.update_thumbnail_current_index()
    
    def set_current_image_from_dialog(self, index):
        if not (0 <= index < len(self.image_files)): return
        self._prepare_for_photo_change()
        self.current_image_index = index
        self.force_refresh = True
        if self.grid_mode != "Off":
            self.update_grid_view()
        else:
            self.display_current_image()


    def show_next_image(self):
        if not self.image_files: return
        self._prepare_for_photo_change()
        if self.current_image_index >= len(self.image_files) - 1: self.current_image_index = 0
        else: self.current_image_index += 1
        self.force_refresh = True
        self.display_current_image()
        # 썸네일 패널 동기화 추가
        self.update_thumbnail_current_index()
    
    def move_current_image_to_folder(self, folder_index, index_to_move=None, context_mode="Off"):
        """현재 이미지를 지정된 폴더로 이동 (Grid Off 또는 CompareA 모드에서 호출)"""
        current_index = index_to_move if index_to_move is not None else self.current_image_index

        if not self.image_files or not (0 <= current_index < len(self.image_files)):
            return

        target_folder = self.target_folders[folder_index]
        if not target_folder or not os.path.isdir(target_folder):
            return

        current_image_path = self.image_files[current_index]

        if self.compare_mode_active and self.image_B_path == current_image_path:
            self.image_B_path = None
            self.original_pixmap_B = None
            self.image_label_B.clear()
            self.image_label_B.setText(LanguageManager.translate("비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다."))
            self.update_compare_filenames()

        moved_jpg_path = None
        moved_raw_path = None
        raw_path_before_move = None

        try:
            moved_jpg_path = self.move_file(current_image_path, target_folder)
            if moved_jpg_path is None:
                self.show_themed_message_box(QMessageBox.Critical, "에러", f"파일 이동 중 오류 발생: {current_image_path.name}")
                return

            raw_moved_successfully = True
            if self.move_raw_files:
                base_name = current_image_path.stem
                if base_name in self.raw_files:
                    raw_path_before_move = self.raw_files[base_name]
                    moved_raw_path = self.move_file(raw_path_before_move, target_folder)
                    if moved_raw_path:
                        del self.raw_files[base_name]
                    else:
                        raw_moved_successfully = False
                        self.show_themed_message_box(QMessageBox.Warning, "경고", f"RAW 파일 이동 실패: {raw_path_before_move.name}")

            # 모델의 removeItem을 호출하여 부드럽게 제거합니다.
            self.thumbnail_panel.model.removeItem(current_index)
            # VibeCullingApp의 image_files 리스트도 동기화해야 합니다.
            # removeItem 내부에서 pop이 일어나므로, 모델의 리스트를 참조하도록 변경합니다.
            self.image_files = self.thumbnail_panel.model._image_files

            if moved_jpg_path:
                history_entry = {
                    "jpg_source": str(current_image_path),
                    "jpg_target": str(moved_jpg_path),
                    "raw_source": str(raw_path_before_move) if raw_path_before_move else None,
                    "raw_target": str(moved_raw_path) if moved_raw_path and raw_moved_successfully else None,
                    "index_before_move": current_index,
                    "mode": context_mode
                }
                self.add_move_history(history_entry)

            if self.image_files:
                if self.current_image_index >= len(self.image_files):
                    self.current_image_index = len(self.image_files) - 1
                
                self.force_refresh = True
                self.display_current_image()
                self.update_thumbnail_current_index() # 썸네일 패널 동기화
            else:
                self.current_image_index = -1
                self.display_current_image()
                self.thumbnail_panel.set_image_files([]) # 썸네일 패널 비우기
                if self.session_management_popup and self.session_management_popup.isVisible():
                    self.session_management_popup.update_all_button_states()
                if self.minimap_visible:
                    self.minimap_widget.hide()
                    self.minimap_visible = False
                self.show_themed_message_box(QMessageBox.Information, "완료", "모든 이미지가 분류되었습니다.")

        except Exception as e:
            self.show_themed_message_box(QMessageBox.Critical, "에러", f"파일 이동 중 오류 발생: {str(e)}")



    # 파일 이동 안정성 강화(재시도 로직). 파일 이동(shutil.move) 시 PermissionError (주로 Windows에서 다른 프로세스가 파일을 사용 중일 때 발생)가 발생하면, 즉시 실패하는 대신 짧은 시간 대기 후 최대 20번까지 재시도합니다.
    def move_file(self, source_path, target_folder):
        """파일을 대상 폴더로 이동하고, 이동된 최종 경로를 반환"""
        if not source_path or not target_folder:
            return None
        # 대상 폴더 존재 확인
        target_dir = Path(target_folder)
        if not target_dir.exists():
            try: # 폴더 생성 시 오류 처리 추가
                target_dir.mkdir(parents=True)
                logging.info(f"대상 폴더 생성됨: {target_dir}")
            except Exception as e:
                logging.error(f"대상 폴더 생성 실패: {target_dir}, 오류: {e}")
                return None # 폴더 생성 실패 시 None 반환

        # 대상 경로 생성
        target_path = target_dir / source_path.name

        # 이미 같은 이름의 파일이 있는지 확인 (수정: 파일명 중복 처리 로직을 재시도 로직과 분리)
        if target_path.exists():
            counter = 1
            while True:
                new_name = f"{source_path.stem}_{counter}{source_path.suffix}"
                new_target_path = target_dir / new_name
                if not new_target_path.exists():
                    target_path = new_target_path # 최종 타겟 경로 업데이트
                    break
                counter += 1
            logging.info(f"파일명 중복 처리: {source_path.name} -> {target_path.name}")

        # 파일 이동
        delay = 0.1 # 재시도 대기 시간
        for attempt in range(20): # 최대 20번 재시도 (초 단위 2초 대기)
        # 재시도 로직 추가
            try: #  파일 이동 시 오류 처리 추가
                shutil.move(str(source_path), str(target_path))
                logging.info(f"파일 이동: {source_path} -> {target_path}")
                return target_path # 이동 성공 시 최종 target_path 반환
            except PermissionError as e:
                if hasattr(e, 'winerror') and e.winerror == 32:
                    print(f"[{attempt+1}] 파일 점유 중 (WinError 32), 재시도 대기: {source_path}")
                    time.sleep(delay)
                else:
