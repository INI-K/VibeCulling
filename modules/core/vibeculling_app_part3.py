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




    def _set_drag_accept_style(self, widget):
        """드래그 수락 스타일 적용"""
        try:
            if widget:
                widget.setStyleSheet(f"""
                    QLabel {{
                        color: #AAAAAA;
                        padding: 5px;
                        background-color: {ThemeManager.get_color('bg_primary')};
                        border: 2px solid #08E25F;
                        border-radius: 1px;
                    }}
                """)
        except Exception as e:
            logging.error(f"_set_drag_accept_style 오류: {e}")

    def _set_drag_reject_style(self, widget):
        """드래그 거부 스타일 적용"""
        try:
            if widget:
                widget.setStyleSheet(f"""
                    QLabel {{
                        color: #AAAAAA;
                        padding: 5px;
                        background-color: {ThemeManager.get_color('bg_primary')};
                        border: 2px solid #FF4444;
                        border-radius: 1px;
                    }}
                """)
        except Exception as e:
            logging.error(f"_set_drag_reject_style 오류: {e}")

    def _restore_original_style(self, widget):
        """원래 스타일 복원"""
        try:
            if widget and widget in self.original_label_styles:
                original_style = self.original_label_styles[widget]
                widget.setStyleSheet(original_style)
                del self.original_label_styles[widget]
        except Exception as e:
            logging.error(f"_restore_original_style 오류: {e}")

    def _handle_folder_drop(self, folder_path, target_type):
        """타겟별 폴더 드랍 처리"""
        try:
            if not folder_path or not target_type:
                return False
            
            folder_path_obj = Path(folder_path)
            if not folder_path_obj.is_dir():
                return False
            
            if target_type == "image_folder":
                # 이미지 폴더 처리
                return self._handle_image_folder_drop(folder_path)
            
            elif target_type == "raw_folder":
                # RAW 폴더 처리
                return self._handle_raw_folder_drop(folder_path)
            
            elif target_type.startswith("category_folder_"):
                # 분류 폴더 처리
                folder_index = int(target_type.split("_")[-1])
                return self._handle_category_folder_drop(folder_path, folder_index)
            
            return False
        except Exception as e:
            logging.error(f"_handle_folder_drop 오류: {e}")
            return False

    def _handle_image_folder_drop(self, folder_path):
        """이미지 폴더 드랍 처리"""
        try:
            # 기존 load_images_from_folder 함수 재사용
            success = self.load_images_from_folder(folder_path)
            if success:
                # load_jpg_folder와 동일한 UI 업데이트 로직 추가
                self.current_folder = folder_path
                self.folder_path_label.setText(folder_path)
                self.update_jpg_folder_ui_state()  # UI 상태 업데이트
                self.save_state()  # 상태 저장
                
                # 세션 관리 팝업이 열려있으면 업데이트
                if self.session_management_popup and self.session_management_popup.isVisible():
                    self.session_management_popup.update_all_button_states()
                
                logging.info(f"드래그 앤 드랍으로 이미지 폴더 로드 성공: {folder_path}")
                return True
            else:
                # 실패 시에도 load_images_from_folder 내부에서 UI 초기화가 이미 처리됨
                # 추가로 current_folder도 초기화
                self.current_folder = ""
                self.update_jpg_folder_ui_state()
                
                if self.session_management_popup and self.session_management_popup.isVisible():
                    self.session_management_popup.update_all_button_states()
                
                logging.warning(f"드래그 앤 드랍으로 이미지 폴더 로드 실패: {folder_path}")
                return False
        except Exception as e:
            logging.error(f"_handle_image_folder_drop 오류: {e}")
            return False

    def _prepare_raw_only_load(self, folder_path):
        """RAW 단독 로드 전처리: 파일 스캔, 첫 파일 분석, 사용자 선택 요청 (메인 스레드)"""
        if not folder_path:
            return None, None
        
        # [빠른 작업] 파일 목록 스캔
        target_path = Path(folder_path)
        temp_raw_file_list = []
        for ext in self.raw_extensions:
            temp_raw_file_list.extend(target_path.glob(f'*{ext}'))
            temp_raw_file_list.extend(target_path.glob(f'*{ext.upper()}'))
        
        unique_raw_files = list(set(temp_raw_file_list))
        if not unique_raw_files:
            self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("경고"), LanguageManager.translate("선택한 폴더에 RAW 파일이 없습니다."))
            return None, None

        # [빠른 작업] 첫 파일 분석 및 사용자 선택 다이얼로그
        first_raw_file_path_obj = sorted(unique_raw_files)[0]
        is_raw_compatible, model_name, orig_res, prev_res = self._analyze_first_raw_file(str(first_raw_file_path_obj))
        chosen_method, dont_ask = self._get_user_raw_method_choice(is_raw_compatible, model_name, orig_res, prev_res)

        if chosen_method is None:
            return None, None # 사용자가 취소

        # "다시 묻지 않음" 설정 저장
        if model_name != LanguageManager.translate("알 수 없는 카메라"):
            self.set_camera_raw_setting(model_name, chosen_method, dont_ask)
        
        self.image_loader.set_raw_load_strategy(chosen_method)
        
        # RAW 디코딩 모드일 경우 진행률 대화상자 표시
        if chosen_method == "decode":
            self._show_first_raw_decode_progress()
            
        return unique_raw_files, chosen_method

    def _handle_raw_folder_drop(self, folder_path):
        """RAW 폴더 드랍 처리 (비동기 로딩으로 변경)"""
        try:
            if not self.image_files: # RAW 단독 로드
                raw_files_to_load, chosen_method = self._prepare_raw_only_load(folder_path)
                if raw_files_to_load and chosen_method:
                    self.start_background_loading(
                        mode='raw_only',
                        jpg_folder_path=folder_path,
                        raw_folder_path=None,
                        raw_file_list=raw_files_to_load
                    )
                    return True
                return False
            else: # JPG-RAW 매칭
                self.start_background_loading(
                    mode='jpg_with_raw',
                    jpg_folder_path=self.current_folder,
                    raw_folder_path=folder_path,
                    raw_file_list=None
                )
                return True
        except Exception as e:
            logging.error(f"_handle_raw_folder_drop 오류: {e}")
            return False

    def _analyze_first_raw_file(self, first_raw_file_path_str):
        """첫 번째 RAW 파일을 분석하여 호환성, 모델명, 해상도 정보를 반환합니다."""
        logging.info(f"첫 번째 RAW 파일 분석 시작: {Path(first_raw_file_path_str).name}")
        is_raw_compatible = False
        camera_model_name = LanguageManager.translate("알 수 없는 카메라")
        original_resolution_str = "-"
        preview_resolution_str = "-"
        rawpy_exif_data = {}
        exiftool_path = self.get_exiftool_path()
        exiftool_available = Path(exiftool_path).exists() and Path(exiftool_path).is_file()

        try:
            with rawpy.imread(first_raw_file_path_str) as raw:
                is_raw_compatible = True
                original_width = raw.sizes.width
                original_height = raw.sizes.height
                if original_width > 0 and original_height > 0:
                    original_resolution_str = f"{original_width}x{original_height}"
                
                make = raw.camera_manufacturer.strip() if hasattr(raw, 'camera_manufacturer') and raw.camera_manufacturer else ""
                model = raw.model.strip() if hasattr(raw, 'model') and raw.model else ""
                camera_model_name = format_camera_name(make, model)
                rawpy_exif_data["exif_make"] = make
                rawpy_exif_data["exif_model"] = model
        except Exception as e_rawpy:
            is_raw_compatible = False
            logging.warning(f"rawpy로 첫 파일 분석 중 오류: {e_rawpy}")

        if (not camera_model_name or camera_model_name == LanguageManager.translate("알 수 없는 카메라") or original_resolution_str == "-") and exiftool_available:
            try:
                cmd = [exiftool_path, "-json", "-Model", "-ImageWidth", "-ImageHeight", "-Make", first_raw_file_path_str]
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, creationflags=creationflags)
                if process.returncode == 0 and process.stdout:
                    exif_data = json.loads(process.stdout)[0]
                    model = exif_data.get("Model")
                    make = exif_data.get("Make")
                    if not rawpy_exif_data.get("exif_model") and model:
                        rawpy_exif_data["exif_model"] = model.strip()
                    if not rawpy_exif_data.get("exif_make") and make:
                        rawpy_exif_data["exif_make"] = make.strip()
                    if not camera_model_name or camera_model_name == LanguageManager.translate("알 수 없는 카메라"):
                         camera_model_name = format_camera_name(make, model)
                    if original_resolution_str == "-":
                        width = exif_data.get("ImageWidth")
                        height = exif_data.get("ImageHeight")
                        if width and height and int(width) > 0 and int(height) > 0:
                            original_resolution_str = f"{width}x{height}"
            except Exception as e_exiftool:
                logging.error(f"Exiftool로 정보 추출 중 오류: {e_exiftool}")

        final_camera_model_display = camera_model_name if camera_model_name else LanguageManager.translate("알 수 없는 카메라")
        
        preview_pixmap, preview_width, preview_height = self.image_loader._load_raw_preview_with_orientation(first_raw_file_path_str)
        if preview_pixmap and not preview_pixmap.isNull() and preview_width and preview_height:
            preview_resolution_str = f"{preview_width}x{preview_height}"
        else:
            preview_resolution_str = LanguageManager.translate("정보 없음")

        return is_raw_compatible, final_camera_model_display, original_resolution_str, preview_resolution_str

    def _get_user_raw_method_choice(self, is_compatible, model_name, orig_res, prev_res):
        """저장된 설정을 확인하거나 사용자에게 RAW 처리 방식을 묻는 다이얼로그를 표시합니다."""
        chosen_method = None
        dont_ask = False
        if model_name != LanguageManager.translate("알 수 없는 카메라"):
            saved_setting = self.get_camera_raw_setting(model_name)
            if saved_setting and saved_setting.get("dont_ask"):
                chosen_method = saved_setting.get("method")
                dont_ask = True
                logging.info(f"'{model_name}' 모델에 저장된 '다시 묻지 않음' 설정 사용: {chosen_method}")
                return chosen_method, dont_ask
        
        # 저장된 설정이 없거나 '다시 묻지 않음'이 아닌 경우
        result = self._show_raw_processing_choice_dialog(is_compatible, model_name, orig_res, prev_res)
        if result:
            chosen_method, dont_ask = result
        
        return chosen_method, dont_ask

    def _handle_category_folder_drop(self, folder_path, folder_index):
        """분류 폴더 드랍 처리"""
        try:
            if 0 <= folder_index < len(self.target_folders):
                self.target_folders[folder_index] = folder_path
                # setText 대신 set_state를 사용하여 UI와 상태를 한 번에 업데이트합니다.
                self.folder_path_labels[folder_index].set_state(EditableFolderPathLabel.STATE_SET, folder_path)
                self.save_state()
                logging.info(f"드래그 앤 드랍으로 분류 폴더 {folder_index+1} 설정 완료: {folder_path}")
                return True
            else:
                logging.error(f"잘못된 분류 폴더 인덱스: {folder_index}")
                return False
        except Exception as e:
            logging.error(f"_handle_category_folder_drop 오류: {e}")
            return False
    # === 폴더 경로 레이블 드래그 앤 드랍 관련 코드 끝 === #

    # === 캔버스 영역 드래그 앤 드랍 관련 코드 시작 === #
    def canvas_dragEnterEvent(self, event):
        """캔버스 영역 드래그 진입 시 호출"""
        try:
            # 폴더만 허용
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if len(urls) == 1:  # 하나의 항목만 허용
                    file_path = urls[0].toLocalFile()
                    if file_path and Path(file_path).is_dir():
                        event.acceptProposedAction()
                        logging.debug(f"캔버스 드래그 진입: 폴더 감지됨 - {file_path}")
                        return
            
            # 조건에 맞지 않으면 거부
            event.ignore()
            logging.debug("캔버스 드래그 진입: 폴더가 아니거나 여러 항목 감지됨")
        except Exception as e:
            logging.error(f"canvas_dragEnterEvent 오류: {e}")
            event.ignore()

    def canvas_dragMoveEvent(self, event):
        """캔버스 영역 드래그 이동 시 호출"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if len(urls) == 1:
                    file_path = urls[0].toLocalFile()
                    if file_path and Path(file_path).is_dir():
                        event.acceptProposedAction()
                        return
            
            event.ignore()
        except Exception as e:
            logging.error(f"canvas_dragMoveEvent 오류: {e}")
            event.ignore()

    def canvas_dragLeaveEvent(self, event):
        """캔버스 영역 드래그 벗어날 때 호출"""
        try:
            logging.debug("캔버스 드래그 벗어남")
        except Exception as e:
            logging.error(f"canvas_dragLeaveEvent 오류: {e}")

    def canvas_dropEvent(self, event):
        """캔버스 영역 드랍 시 호출"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if len(urls) == 1:
                    file_path = urls[0].toLocalFile()
                    if file_path and Path(file_path).is_dir():
                        # 캔버스 폴더 드랍 처리
                        success = self._handle_canvas_folder_drop(file_path)
                        
                        if success:
                            event.acceptProposedAction()
                            logging.info(f"캔버스 폴더 드랍 성공: {file_path}")
                        else:
                            event.ignore()
                            logging.warning(f"캔버스 폴더 드랍 실패: {file_path}")
                        return
            
            # 조건에 맞지 않으면 거부
            event.ignore()
            logging.debug("canvas_dropEvent: 유효하지 않은 드랍")
        except Exception as e:
            logging.error(f"canvas_dropEvent 오류: {e}")
            event.ignore()

    def _analyze_folder_contents(self, folder_path):
        """폴더 내용 분석 (RAW 파일, 일반 이미지 파일, 매칭 여부)"""
        try:
            folder_path_obj = Path(folder_path)
            if not folder_path_obj.is_dir():
                return None
            
            # 파일 분류
            raw_files = []
            image_files = []
            
            for file_path in folder_path_obj.iterdir():
                if not file_path.is_file():
                    continue
                
                ext = file_path.suffix.lower()
                if ext in self.raw_extensions:
                    raw_files.append(file_path)
                elif ext in self.supported_image_extensions:
                    image_files.append(file_path)
            
            # 매칭 파일 확인 (이름이 같은 파일)
            raw_stems = {f.stem for f in raw_files}
            image_stems = {f.stem for f in image_files}
            matching_files = raw_stems & image_stems
            
            return {
                'raw_files': raw_files,
                'image_files': image_files,
                'has_raw': len(raw_files) > 0,
                'has_images': len(image_files) > 0,
                'has_matching': len(matching_files) > 0,
                'matching_count': len(matching_files)
            }
        except Exception as e:
            logging.error(f"_analyze_folder_contents 오류: {e}")
            return None

    def _show_folder_choice_dialog(self, has_matching=False):
        """폴더 선택지 팝업 대화상자 (반환 ID 통일)"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(LanguageManager.translate("폴더 불러오기"))
            # 다크 테마 적용
            apply_dark_title_bar(dialog)
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
            dialog.setPalette(palette)
            dialog.setAutoFillBackground(True)
            layout = QVBoxLayout(dialog)
            layout.setSpacing(10)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 메시지 레이블 생성
            message_text = LanguageManager.translate("폴더 내에 일반 이미지 파일과 RAW 파일이 같이 있습니다.\n무엇을 불러오시겠습니까?")
            message_label = QLabel(message_text)
            message_label.setWordWrap(True)
            message_label.setStyleSheet(f"color: {ThemeManager.get_color('text')};")
            layout.addWidget(message_label)

            fm = message_label.fontMetrics()
            lines = message_text.split('\n')
            max_width = 0
            for line in lines:
                line_width = fm.horizontalAdvance(line)
                if line_width > max_width:
                    max_width = line_width
            dialog.setMinimumWidth(max_width + 60)

            # 라디오 버튼 그룹 및 스타일
            radio_group = QButtonGroup(dialog)
            radio_style = f"""
                QRadioButton {{
                    color: {ThemeManager.get_color('text')};
                    padding: 0px;
                }}
                QRadioButton::indicator {{
                    width: {UIScaleManager.get("radiobutton_size")}px;
                    height: {UIScaleManager.get("radiobutton_size")}px;
                }}
                QRadioButton::indicator:checked {{
                    background-color: {ThemeManager.get_color('accent')};
                    border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('accent')};
                    border-radius: {UIScaleManager.get("radiobutton_border_radius")}px;
                }}
                QRadioButton::indicator:unchecked {{
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('border')};
                    border-radius: {UIScaleManager.get("radiobutton_border_radius")}px;
                }}
                QRadioButton::indicator:unchecked:hover {{
                    border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('text_disabled')};
                }}
            """
            
            layout.addSpacing(20)

            if has_matching:
                # 3선택지: 매칭(0), 일반 이미지(1), RAW(2)
                option1 = QRadioButton(LanguageManager.translate("파일명이 같은 이미지 파일과 RAW 파일을 매칭하여 불러오기"))
                option2 = QRadioButton(LanguageManager.translate("일반 이미지 파일만 불러오기"))
                option3 = QRadioButton(LanguageManager.translate("RAW 파일만 불러오기"))
                option1.setStyleSheet(radio_style)
                option2.setStyleSheet(radio_style)
                option3.setStyleSheet(radio_style)
                radio_group.addButton(option1, 0) # ID 0: 매칭
                radio_group.addButton(option2, 1) # ID 1: 일반
                radio_group.addButton(option3, 2) # ID 2: RAW
                option1.setChecked(True)
                layout.addWidget(option1)
                layout.addSpacing(10)
                layout.addWidget(option2)
                layout.addSpacing(10)
                layout.addWidget(option3)
            else:
                # 2선택지: 일반 이미지(1), RAW(2) -> ID를 3선택지와 맞춤
                option1 = QRadioButton(LanguageManager.translate("일반 이미지 파일만 불러오기"))
                option2 = QRadioButton(LanguageManager.translate("RAW 파일만 불러오기"))
                option1.setStyleSheet(radio_style)
                option2.setStyleSheet(radio_style)
                radio_group.addButton(option1, 1) # ID 1: 일반
                radio_group.addButton(option2, 2) # ID 2: RAW
                option1.setChecked(True)
                layout.addWidget(option1)
                layout.addSpacing(10)
                layout.addWidget(option2)

            layout.addSpacing(20)

            # 확인 버튼
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
            
            # 버튼 컨테이너 (가운데 정렬)
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addStretch(1)
            button_layout.addWidget(confirm_button)
            button_layout.addStretch(1)
            layout.addWidget(button_container)

            if dialog.exec() == QDialog.Accepted:
                return radio_group.checkedId()
            else:
                return None
        except Exception as e:
            logging.error(f"_show_folder_choice_dialog 오류: {e}")
            return None

    def _handle_canvas_folder_drop(self, folder_path):
        """캔버스 영역 폴더 드랍 메인 처리 로직 (비동기 로딩 적용)"""
        try:
            if self.image_files:
                reply = self.show_themed_message_box(
                    QMessageBox.Question,
                    LanguageManager.translate("새 폴더 불러오기"),
                    LanguageManager.translate("현재 진행 중인 작업을 종료하고 새로운 폴더를 불러오시겠습니까?"),
                    QMessageBox.Yes | QMessageBox.Cancel,
                    QMessageBox.Cancel
                )
                if reply == QMessageBox.Cancel:
                    return False
                self._reset_workspace()
            
            analysis = self._analyze_folder_contents(folder_path)
            if not analysis:
                return False

            if analysis['has_raw'] and not analysis['has_images']:
                return self._handle_raw_folder_drop(folder_path)
            
            elif analysis['has_images'] and not analysis['has_raw']:
                self.start_background_loading(
                    mode='jpg_only',
                    jpg_folder_path=folder_path,
                    raw_folder_path=None,
                    raw_file_list=None
                )
                return True

            elif analysis['has_raw'] and analysis['has_images']:
                choice_id = self._show_folder_choice_dialog(has_matching=analysis['has_matching'])
                if choice_id is None: return False

                if choice_id == 0: # 매칭
                    self.start_background_loading(
                        mode='jpg_with_raw',
                        jpg_folder_path=folder_path,
                        raw_folder_path=folder_path,
                        raw_file_list=None
                    )
                elif choice_id == 1: # JPG만
                    self.start_background_loading(
                        mode='jpg_only',
                        jpg_folder_path=folder_path,
                        raw_folder_path=None,
                        raw_file_list=None
                    )
                elif choice_id == 2: # RAW만
                    return self._handle_raw_folder_drop(folder_path)
                return True
            
            else:
                self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("경고"), LanguageManager.translate("선택한 폴더에 지원하는 파일이 없습니다."))
                return False

        except Exception as e:
            logging.error(f"_handle_canvas_folder_drop 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

        except Exception as e:
            logging.error(f"_handle_canvas_folder_drop 오류: {e}")
            # 에러 로그에 스택 트레이스를 추가하여 더 자세한 정보 확인
            import traceback
            traceback.print_exc()
            return False
    # === 캔버스 영역 드래그 앤 드랍 관련 코드 끝 === #

    def on_extension_checkbox_changed(self, state):
        # QTimer.singleShot을 사용하여 이 함수의 실행을 이벤트 루프의 다음 사이클로 지연시킵니다.
        # 이렇게 하면 모든 체크박스의 상태 업데이트가 완료된 후에 로직이 실행되어 안정성이 높아집니다.
        QTimer.singleShot(0, self._update_supported_extensions)

    def _update_supported_extensions(self):
        """실제로 지원 확장자 목록을 업데이트하고 UI를 검증하는 내부 메서드"""
        extension_groups = {
            "JPG": ['.jpg', '.jpeg'],
            "HEIC": ['.heic', '.heif'],
            "PNG": ['.png'],
            "WebP": ['.webp'],
            "BMP": ['.bmp'],
            "TIFF": ['.tif', '.tiff']
        }

        # 1. 현재 UI에 표시된 모든 체크박스의 상태를 다시 확인하여 새 목록 생성
        new_supported_extensions = set()
        checked_count = 0
        for name, checkbox in self.ext_checkboxes.items():
            if checkbox.isChecked():
                checked_count += 1
                new_supported_extensions.update(extension_groups[name])

        # 2. 체크된 박스가 하나도 없는지 검증 (사용자가 마지막 남은 하나를 해제하려는 경우)
        if checked_count == 0:
            logging.warning("모든 확장자 선택 해제 감지됨. JPG를 강제로 다시 선택합니다.")
            jpg_checkbox = self.ext_checkboxes.get("JPG")
            if jpg_checkbox:
                # 시그널을 막고 UI를 강제로 다시 체크 상태로 변경
                jpg_checkbox.blockSignals(True)
                jpg_checkbox.setChecked(True)
                jpg_checkbox.blockSignals(False)
            
            # 지원 확장자 목록을 JPG만 포함하도록 재설정
            self.supported_image_extensions = set(extension_groups["JPG"])
        else:
            # 체크된 박스가 하나 이상 있으면, 그 상태를 그대로 데이터에 반영
            self.supported_image_extensions = new_supported_extensions

        logging.info(f"지원 확장자 변경됨: {sorted(list(self.supported_image_extensions))}")

    
    def _trigger_state_save_for_index(self): # 자동저장
        """current_image_index를 포함한 전체 상태를 저장합니다 (주로 타이머에 의해 호출)."""
        logging.debug(f"Index save timer triggered. Saving state (current_image_index: {self.current_image_index}).")
        self.save_state()


    def _save_orientation_viewport_focus(self, orientation_type: str, rel_center: QPointF, zoom_level_str: str):
        """주어진 화면 방향 타입('landscape' 또는 'portrait')에 대한 뷰포트 중심과 줌 레벨을 저장합니다."""
        if orientation_type not in ["landscape", "portrait"]:
            logging.warning(f"잘못된 orientation_type으로 포커스 저장 시도: {orientation_type}")
            return

        focus_point_info = {
            "rel_center": rel_center,
            "zoom_level": zoom_level_str
        }
        self.viewport_focus_by_orientation[orientation_type] = focus_point_info
        logging.debug(f"방향별 뷰포트 포커스 저장: {orientation_type} -> {focus_point_info}")

    def _get_current_view_relative_center(self):
        """현재 image_label의 뷰포트 중심의 상대 좌표를 반환합니다."""
        if not self.original_pixmap or self.zoom_mode == "Fit": # Fit 모드에서는 항상 (0.5,0.5)로 간주 가능
            return QPointF(0.5, 0.5)

        view_rect = self.scroll_area.viewport().rect()
        image_label_pos = self.image_label.pos()
        
        if self.zoom_mode == "100%":
            current_zoom_factor = 1.0
        elif self.zoom_mode == "Spin":
            current_zoom_factor = self.zoom_spin_value
        else: # 예외 상황 (이론상 발생 안 함)
            current_zoom_factor = 1.0
        
        zoomed_img_width = self.original_pixmap.width() * current_zoom_factor
        zoomed_img_height = self.original_pixmap.height() * current_zoom_factor

        if zoomed_img_width <= 0 or zoomed_img_height <= 0: return QPointF(0.5, 0.5)

        viewport_center_x_abs = view_rect.center().x() - image_label_pos.x()
        viewport_center_y_abs = view_rect.center().y() - image_label_pos.y()
        
        rel_x = max(0.0, min(1.0, viewport_center_x_abs / zoomed_img_width))
        rel_y = max(0.0, min(1.0, viewport_center_y_abs / zoomed_img_height))
        return QPointF(rel_x, rel_y)

    def _get_orientation_viewport_focus(self, orientation_type: str, requested_zoom_level: str):
        """
        주어진 화면 방향 타입에 저장된 포커스 정보를 반환합니다.
        저장된 상대 중심과 "요청된" 줌 레벨을 함께 반환합니다.
        정보가 없으면 기본값(중앙, 요청된 줌 레벨)을 반환합니다.
        """
        if orientation_type in self.viewport_focus_by_orientation:
            saved_focus = self.viewport_focus_by_orientation[orientation_type]
            saved_zoom_level = saved_focus.get("zoom_level", "")
            saved_rel_center = saved_focus.get("rel_center", QPointF(0.5, 0.5))
            
            # 200% → Spin 호환성 처리
            if saved_zoom_level == "200%" and requested_zoom_level == "Spin":
                # 기존 200% 데이터를 Spin으로 사용 (2.0 = 200%)
                if not hasattr(self, 'zoom_spin_value') or self.zoom_spin_value != 2.0:
                    self.zoom_spin_value = 2.0
                    if hasattr(self, 'zoom_spin'):
                        self.zoom_spin.setValue(200)
                logging.debug(f"200% → Spin 호환성 처리: zoom_spin_value를 2.0으로 설정")
            
            logging.debug(f"_get_orientation_viewport_focus: 방향 '{orientation_type}'에 저장된 포커스 사용: rel_center={saved_rel_center} (원래 줌: {saved_zoom_level}), 요청 줌: {requested_zoom_level}")
            return saved_rel_center, requested_zoom_level
        
        logging.debug(f"_get_orientation_viewport_focus: 방향 '{orientation_type}'에 저장된 포커스 없음. 중앙 및 요청 줌({requested_zoom_level}) 사용.")
        return QPointF(0.5, 0.5), requested_zoom_level


    def _prepare_for_photo_change(self):
        """사진 변경 직전에 현재 활성 뷰포트와 이전 이미지 상태를 기록합니다."""
        # 현재 활성 뷰포트 정보를 "방향 타입" 고유 포커스로 저장
        if self.grid_mode == "Off" and self.current_active_zoom_level in ["100%", "Spin"] and \
           self.original_pixmap and hasattr(self, 'current_image_orientation') and self.current_image_orientation:
            self._save_orientation_viewport_focus(
                self.current_image_orientation, # 현재 이미지의 방향 타입
                self.current_active_rel_center, 
                self.current_active_zoom_level
            )
        
        # 다음 이미지 로드 시 비교를 위한 정보 저장
        self.previous_image_orientation_for_carry_over = self.current_image_orientation
        self.previous_zoom_mode_for_carry_over = self.current_active_zoom_level # 현재 "활성" 줌 레벨
        self.previous_active_rel_center_for_carry_over = self.current_active_rel_center # 현재 "활성" 중심



    def _generate_default_session_name(self):
        """현재 상태를 기반으로 기본 세션 이름을 생성합니다."""
        base_folder_name = "Untitled"
        if self.is_raw_only_mode and self.raw_folder:
            base_folder_name = Path(self.raw_folder).name
        elif self.current_folder:
            base_folder_name = Path(self.current_folder).name
        
        # 날짜 부분 (YYYYMMDD)
        date_str = datetime.now().strftime("%Y%m%d")
        # 시간 부분 (HHMMSS) - 이름 중복 시 사용
        time_str = datetime.now().strftime("%H%M%S")

        # 기본 이름: 폴더명_날짜
        default_name = f"{base_folder_name}_{date_str}"
        
        # 중복 확인 및 처리 (이름 뒤에 _HHMMSS 또는 (숫자) 추가)
        final_name = default_name
        counter = 1
        while final_name in self.saved_sessions:
            # 방법 1: 시간 추가 (더 고유함)
            # final_name = f"{default_name}_{time_str}" # 이렇게 하면 거의 항상 고유
            # if final_name in self.saved_sessions: # 시간까지 겹치면 숫자
            #     final_name = f"{default_name}_{time_str}({counter})"
            #     counter += 1
            # 방법 2: 숫자 추가 (요구사항에 더 가까움)
            final_name = f"{default_name}({counter})"
            counter += 1
            if counter > 99: # 무한 루프 방지 (극단적인 경우)
                final_name = f"{default_name}_{time_str}" # 최후의 수단으로 시간 사용
                break 
        return final_name

    def _capture_current_session_state(self):
        """현재 작업 상태를 딕셔너리로 캡처하여 반환합니다."""
        # save_state에서 저장하는 항목들 중 필요한 것들만 선택
        actual_current_image_list_index = -1
        if self.grid_mode != "Off":
            if self.image_files and 0 <= self.grid_page_start_index + self.current_grid_index < len(self.image_files):
                actual_current_image_list_index = self.grid_page_start_index + self.current_grid_index
        else:
            if self.image_files and 0 <= self.current_image_index < len(self.image_files):
                actual_current_image_list_index = self.current_image_index

        session_data = {
            "current_folder": str(self.current_folder) if self.current_folder else "",
            "raw_folder": str(self.raw_folder) if self.raw_folder else "",
            "raw_files": {k: str(v) for k, v in self.raw_files.items()}, # Path를 str로
            "move_raw_files": self.move_raw_files,
            "target_folders": [str(f) if f else "" for f in self.target_folders],
            "folder_count": self.folder_count,  # 분류 폴더 개수 저장 추가
            "minimap_visible": self.minimap_toggle.isChecked(), # 현재 UI 상태 반영
            "current_image_index": actual_current_image_list_index, # 전역 인덱스
            "current_grid_index": self.current_grid_index,
            "grid_page_start_index": self.grid_page_start_index,
            "is_raw_only_mode": self.is_raw_only_mode,
            "show_grid_filenames": self.show_grid_filenames,
            "last_used_raw_method": self.image_loader._raw_load_strategy if hasattr(self, 'image_loader') else "preview",
            "zoom_mode": self.zoom_mode,
            "grid_mode": self.grid_mode,
            "previous_grid_mode": self.previous_grid_mode,
            "image_rotations": self.image_rotations,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "compare_mode_active": self.compare_mode_active,
            "image_B_path": str(self.image_B_path) if self.image_B_path else "",
        }
        return session_data


    def save_current_session(self, session_name: str):
        """주어진 이름으로 현재 작업 세션을 저장합니다."""
        if not session_name:
            logging.warning("세션 이름 없이 저장을 시도했습니다.")
            # 사용자에게 알림 (선택 사항)
            self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("저장 오류"), LanguageManager.translate("세션 이름을 입력해야 합니다."))
            return False

        if len(self.saved_sessions) >= 20:
            logging.warning("최대 저장 가능한 세션 개수(20개)에 도달했습니다.")
            self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("저장 한도 초과"), LanguageManager.translate("최대 20개의 세션만 저장할 수 있습니다. 기존 세션을 삭제 후 다시 시도해주세요."))
            return False

        current_state_data = self._capture_current_session_state()
        self.saved_sessions[session_name] = current_state_data
        self.save_state() # 변경된 self.saved_sessions를 vibeculling_data.json에 저장
        logging.info(f"세션 저장됨: {session_name}")
        
        # 세션 관리 팝업이 열려있다면 목록 업데이트
        if self.session_management_popup and self.session_management_popup.isVisible():
            self.session_management_popup.populate_session_list()
        return True

    def delete_session(self, session_name: str):
        """저장된 작업 세션을 삭제합니다."""
        if session_name in self.saved_sessions:
            del self.saved_sessions[session_name]
            self.save_state() # 변경 사항을 vibeculling_data.json에 저장
            logging.info(f"세션 삭제됨: {session_name}")
            # 세션 관리 팝업이 열려있다면 목록 업데이트
            if self.session_management_popup and self.session_management_popup.isVisible():
                self.session_management_popup.populate_session_list()
            return True
        else:
            logging.warning(f"삭제할 세션 없음: {session_name}")
            return False

    def show_session_management_popup(self):
        """세션 저장 및 불러오기 팝업창을 표시합니다."""
        # 현재 활성화된 settings_popup을 부모로 사용하거나, 없으면 self (메인 윈도우)를 부모로 사용
        current_active_popup = QApplication.activeModalWidget() # 현재 활성화된 모달 위젯 찾기
        parent_widget = self # 기본 부모는 메인 윈도우

        if current_active_popup and isinstance(current_active_popup, QDialog):
             # settings_popup이 현재 활성화된 모달 다이얼로그인지 확인
             if hasattr(self, 'settings_popup') and current_active_popup is self.settings_popup:
                 parent_widget = self.settings_popup
                 logging.debug("SessionManagementDialog의 부모를 settings_popup으로 설정합니다.")
             else:
                 # 다른 모달 위젯이 떠 있는 경우, 그 위에 표시되도록 할 수도 있음.
                 # 또는 항상 메인 윈도우를 부모로 할 수도 있음.
                 # 여기서는 settings_popup이 아니면 메인 윈도우를 부모로 유지.
                 logging.debug(f"활성 모달 위젯({type(current_active_popup)})이 settings_popup이 아니므로, SessionManagementDialog의 부모를 메인 윈도우로 설정합니다.")
        
        # SessionManagementDialog가 이미 존재하고 부모가 다른 경우 문제가 될 수 있으므로,
        # 부모가 바뀔 가능성이 있다면 새로 생성하는 것이 안전할 수 있음.
        # 여기서는 일단 기존 인스턴스를 재활용하되, 부모가 의도와 다른지 확인.
        if self.session_management_popup is None or not self.session_management_popup.isVisible():
            # 생성 시 올바른 부모 전달
            self.session_management_popup = SessionManagementDialog(parent_widget, self) 
            logging.debug(f"새 SessionManagementDialog 생성. 부모: {type(parent_widget)}")
        elif self.session_management_popup.parent() is not parent_widget:
            # 부모가 변경되어야 한다면, 이전 팝업을 닫고 새로 생성하거나 setParent 호출.
            # QWidget.setParent()는 주의해서 사용해야 하므로, 새로 생성하는 것이 더 간단할 수 있음.
            logging.warning(f"SessionManagementDialog의 부모가 변경되어야 함. (현재: {type(self.session_management_popup.parent())}, 필요: {type(parent_widget)}) 새로 생성합니다.")
            self.session_management_popup.close() # 이전 것 닫기
            self.session_management_popup = SessionManagementDialog(parent_widget, self)
            
        self.session_management_popup.populate_session_list()
        self.session_management_popup.update_all_button_states() # 팝업 표시 직전에 버튼 상태 강제 업데이트

        
        # exec()를 사용하여 모달로 띄우면 "설정 및 정보" 팝업은 비활성화됨
        # show()를 사용하여 모달리스로 띄우면 두 팝업이 동시에 상호작용 가능할 수 있으나,
        # 이 경우 "설정 및 정보" 팝업이 닫힐 때 함께 닫히도록 처리하거나,
        # "세션 관리" 팝업이 항상 위에 오도록 setWindowFlags(Qt.WindowStaysOnTopHint) 설정 필요.
        # 여기서는 모달로 띄우는 것을 기본으로 가정.
        # self.session_management_popup.show() 
        # self.session_management_popup.activateWindow()
        # self.session_management_popup.raise_()
        
        # "설정 및 정보" 팝업 위에서 "세션 관리" 팝업을 모달로 띄우려면,
        # "설정 및 정보" 팝업을 잠시 hide() 했다가 "세션 관리" 팝업이 닫힌 후 다시 show() 하거나,
        # "세션 관리" 팝업을 모달리스로 하되 항상 위에 있도록 해야 함.
        # 또는, "세션 관리" 팝업 자체를 "설정 및 정보" 팝업 내부에 통합된 위젯으로 만드는 것도 방법.

        # 가장 간단한 접근: "세션 관리" 팝업을 "설정 및 정보" 팝업에 대해 모달로 띄운다.
        # 이렇게 하면 "설정 및 정보"는 "세션 관리"가 닫힐 때까지 비활성화됨.
        self.session_management_popup.exec() # exec()는 블로킹 호출




    def smooth_viewport_move(self):
        """타이머에 의해 호출되어 뷰포트를 부드럽게 이동시킵니다."""
        if not (self.grid_mode == "Off" and self.zoom_mode in ["100%", "Spin"] and self.original_pixmap and self.pressed_keys_for_viewport):
            self.viewport_move_timer.stop() # 조건 안 맞으면 타이머 중지
            return

        move_step_base = getattr(self, 'viewport_move_speed', 5) 
        # 실제 이동량은 setInterval에 따라 조금씩 움직이므로, move_step_base는 한 번의 timeout당 이동량의 기준으로 사용
        # 예를 들어, 속도 5, interval 16ms이면, 초당 약 5 * (1000/16) = 약 300px 이동 효과.
        # 실제로는 방향키 조합에 따라 대각선 이동 시 속도 보정 필요할 수 있음.
        # 여기서는 단순하게 각 방향 이동량을 move_step_base로 사용.
        # 더 부드럽게 하려면 move_step_base 값을 작게, interval도 작게 조절.
        # 여기서는 단계별 이동량이므로, *10은 제거하고, viewport_move_speed 값을 직접 사용하거나 약간의 배율만 적용.
        move_amount = move_step_base * 12 # 한 번의 timeout당 이동 픽셀 (조절 가능)

        dx, dy = 0, 0

        # 8방향 이동 로직 (눌린 키 조합 확인)
        if Qt.Key_Left in self.pressed_keys_for_viewport: dx += move_amount
        if Qt.Key_Right in self.pressed_keys_for_viewport: dx -= move_amount
        if Qt.Key_Up in self.pressed_keys_for_viewport: dy += move_amount
        if Qt.Key_Down in self.pressed_keys_for_viewport: dy -= move_amount
        
        # Shift+WASD 에 대한 처리도 여기에 추가
        # (eventFilter에서 pressed_keys_for_viewport에 WASD도 Arrow Key처럼 매핑해서 넣어줌)

        if dx == 0 and dy == 0: # 이동할 방향이 없으면
            self.viewport_move_timer.stop()
            return

        current_pos = self.image_label.pos()
        new_x, new_y = current_pos.x() + dx, current_pos.y() + dy

        # 패닝 범위 제한 로직 (동일하게 적용)
        if self.zoom_mode == "100%":
            zoom_factor = 1.0
        else: # Spin 모드
            zoom_factor = self.zoom_spin_value
            
        img_width = self.original_pixmap.width() * zoom_factor
        img_height = self.original_pixmap.height() * zoom_factor
        view_width = self.scroll_area.width(); view_height = self.scroll_area.height()
        x_min_limit = min(0, view_width - img_width) if img_width > view_width else (view_width - img_width) // 2
        x_max_limit = 0 if img_width > view_width else x_min_limit
        y_min_limit = min(0, view_height - img_height) if img_height > view_height else (view_height - img_height) // 2
        y_max_limit = 0 if img_height > view_height else y_min_limit
        
        final_x = max(x_min_limit, min(x_max_limit, new_x))
        final_y = max(y_min_limit, min(y_max_limit, new_y))

        if current_pos.x() != final_x or current_pos.y() != final_y:
            self.image_label.move(int(final_x), int(final_y))
            self._sync_viewports()
            if self.minimap_visible and self.minimap_widget.isVisible():
                self.update_minimap()


    def handle_raw_decoding_failure(self, failed_file_path: str):
        """RAW 파일 디코딩 실패 시 호출되는 슬롯"""
        logging.warning(f"RAW 파일 디코딩 실패 감지됨: {failed_file_path}")
        
        # 현재 표시하려던 파일과 실패한 파일이 동일한지 확인
        current_path_to_display = None
        if self.grid_mode == "Off":
            if 0 <= self.current_image_index < len(self.image_files):
                current_path_to_display = str(self.image_files[self.current_image_index])
        else:
            grid_idx = self.grid_page_start_index + self.current_grid_index
            if 0 <= grid_idx < len(self.image_files):
                current_path_to_display = str(self.image_files[grid_idx])

        if current_path_to_display == failed_file_path:
            # 사용자에게 알림 (기존 show_compatibility_message 사용 또는 새 메시지)
            self.show_themed_message_box( # 기존 show_compatibility_message 대신 직접 호출
                QMessageBox.Warning,
                LanguageManager.translate("호환성 문제"),
                LanguageManager.translate("RAW 디코딩 실패. 미리보기를 대신 사용합니다.")
            )

            # 해당 파일에 대해 강제로 "preview" 방식으로 전환하고 이미지 다시 로드 시도
            # (주의: 이로 인해 무한 루프가 발생하지 않도록 ImageLoader에서 처리했는지 확인 필요.
            #  ImageLoader가 실패 시 빈 QPixmap을 반환하므로, VibeCullingApp에서 다시 로드 요청해야 함)
            
            # 카메라 모델 가져오기 (실패할 수 있음)
            camera_model = self.get_camera_model_from_exif_or_path(failed_file_path) # 이 함수는 새로 만들어야 할 수 있음
            
            if camera_model != LanguageManager.translate("알 수 없는 카메라"):
                # 이 카메라 모델에 대해 "preview"로 강제하고, "다시 묻지 않음"은 그대로 두거나 해제할 수 있음
                current_setting = self.get_camera_raw_setting(camera_model)
                dont_ask_original = current_setting.get("dont_ask", False) if current_setting else False
                self.set_camera_raw_setting(camera_model, "preview", dont_ask_original) # 미리보기로 강제, 다시 묻지 않음은 유지
                logging.info(f"'{camera_model}' 모델의 처리 방식을 'preview'로 강제 변경 (디코딩 실패)")
            
            # ImageLoader의 현재 인스턴스 전략도 preview로 변경
            self.image_loader.set_raw_load_strategy("preview")
            
            # 디스플레이 강제 새로고침
            if self.grid_mode == "Off":
                self.force_refresh = True
                self.display_current_image() # 미리보기로 다시 로드 시도
            else:
                self.force_refresh = True # 그리드도 새로고침 필요
                self.update_grid_view()
        else:
            # 현재 표시하려는 파일이 아닌 다른 파일의 디코딩 실패 (예: 백그라운드 프리로딩 중)
            # 이 경우 사용자에게 직접 알릴 필요는 없을 수 있지만, 로깅은 중요
            logging.warning(f"백그라운드 RAW 디코딩 실패: {failed_file_path}")

    def get_camera_model_from_exif_or_path(self, file_path_str: str) -> str:
        """주어진 파일 경로에서 카메라 모델명을 추출 시도 (캐시 우선, 실패 시 exiftool)"""
        if file_path_str in self.exif_cache:
            exif_data = self.exif_cache[file_path_str]
            make = exif_data.get("exif_make", "")
            model = exif_data.get("exif_model", "")
            if make and model: return f"{make} {model}"
            if model: return model
        
        # 캐시에 없으면 exiftool 시도 (간략화된 버전)
        try:
            exiftool_path = self.get_exiftool_path()
            if Path(exiftool_path).exists():
                cmd = [exiftool_path, "-json", "-Model", "-Make", file_path_str]
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, creationflags=creationflags)
                if process.returncode == 0 and process.stdout:
                    exif_data_list = json.loads(process.stdout)
                    if exif_data_list:
                        exif_data = exif_data_list[0]
                        make = exif_data.get("Make")
                        model = exif_data.get("Model")
                        if make and model: return f"{make.strip()} {model.strip()}"
                        if model: return model.strip()
