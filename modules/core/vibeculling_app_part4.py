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



        except Exception as e:
            logging.error(f"get_camera_model_from_exif_or_path에서 오류 ({Path(file_path_str).name}): {e}")
        return LanguageManager.translate("알 수 없는 카메라")

    def get_camera_raw_setting(self, camera_model: str):
        """주어진 카메라 모델에 대한 저장된 RAW 처리 설정을 반환합니다."""
        return self.camera_raw_settings.get(camera_model, None) # 설정 없으면 None 반환

    def set_camera_raw_setting(self, camera_model: str, method: str, dont_ask: bool):
            """주어진 카메라 모델에 대한 RAW 처리 설정을 self.camera_raw_settings에 업데이트하고,
            변경 사항을 메인 상태 파일에 즉시 저장합니다."""
            if not camera_model:
                logging.warning("카메라 모델명 없이 RAW 처리 설정을 저장하려고 시도했습니다.")
                return
                
            self.camera_raw_settings[camera_model] = {
                "method": method,
                "dont_ask": dont_ask
            }
            logging.info(f"카메라별 RAW 설정 업데이트됨 (메모리): {camera_model} -> {self.camera_raw_settings[camera_model]}")
            self.save_state() # 변경 사항을 vibeculling_data.json에 즉시 저장


    def reset_all_camera_raw_settings(self):
            """모든 카메라별 RAW 처리 설정을 초기화하고 메인 상태 파일에 즉시 저장합니다."""
            reply = self.show_themed_message_box(
                QMessageBox.Question,
                LanguageManager.translate("초기화"),
                LanguageManager.translate("저장된 모든 카메라 모델의 RAW 파일 처리 방식을 초기화하시겠습니까? 이 작업은 되돌릴 수 없습니다."),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.camera_raw_settings = {} # 메모리 내 설정 초기화
                self.save_state()
                logging.info("모든 카메라별 RAW 처리 설정이 초기화되었습니다 (메인 상태 파일에 반영).")


    def get_system_memory_gb(self):
        """시스템 메모리 크기 확인 (GB)"""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 * 1024 * 1024)
        except:
            return 8.0  # 기본값 8GB
    

    def check_memory_usage(self):
        """메모리 사용량 모니터링 및 필요시 최적화 조치"""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            
            # 메모리 사용량이 위험 수준일 경우 (85% 이상)
            if memory_percent > 85:
                logging.warning(f"높은 메모리 사용량 감지 ({memory_percent}%): 캐시 정리 수행")
                self.perform_emergency_cleanup()
            
            # 메모리 사용량이 경고 수준일 경우 (75% 이상)
            elif memory_percent > 75:
                logging.warning(f"경고: 높은 메모리 사용량 ({memory_percent}%)")
                self.reduce_cache_size()
        except:
            pass  # psutil 사용 불가 등의 예외 상황 무시

    def perform_emergency_cleanup(self):
        """메모리 사용량이 위험 수준일 때 수행할 긴급 정리 작업"""
        # 1. 이미지 캐시 대폭 축소
        if hasattr(self.image_loader, 'cache'):
            cache_size = len(self.image_loader.cache)
            items_to_keep = min(10, cache_size)  # 최대 10개만 유지
            
            # 현재 표시 중인 이미지는 유지
            current_path = None
            if self.current_image_index >= 0 and self.current_image_index < len(self.image_files):
                current_path = str(self.image_files[self.current_image_index])
            
            # 불필요한 캐시 항목 제거
            keys_to_remove = []
            keep_count = 0
            
            for key in list(self.image_loader.cache.keys()):
                # 현재 표시 중인 이미지는 유지
                if key == current_path:
                    continue
                    
                keys_to_remove.append(key)
                keep_count += 1
                
                if keep_count >= cache_size - items_to_keep:
                    break
            
            # 실제 항목 제거
            for key in keys_to_remove:
                del self.image_loader.cache[key]
            
            logging.info(f"메모리 확보: 이미지 캐시에서 {len(keys_to_remove)}개 항목 제거")
        
        # 2. Fit 모드 캐시 초기화
        self.fit_pixmap_cache.clear()
        self.last_fit_size = (0, 0)
        
        # 3. 그리드 썸네일 캐시 정리
        if hasattr(self, 'grid_thumbnail_cache'):
            for key in self.grid_thumbnail_cache:
                self.grid_thumbnail_cache[key].clear()
        
        # 4. 백그라운드 작업 일부 취소
        for future in self.active_thumbnail_futures:
            future.cancel()
        self.active_thumbnail_futures.clear()
        
        # 5. 가비지 컬렉션 강제 실행
        import gc
        gc.collect()

    def reduce_cache_size(self):
        """메모리 사용량이 경고 수준일 때 캐시 크기 축소"""
        # 이미지 캐시 일부 축소
        if hasattr(self.image_loader, 'cache'):
            cache_size = len(self.image_loader.cache)
            if cache_size > 20:  # 최소 크기 이상일 때만 축소
                items_to_remove = max(5, int(cache_size * 0.15))  # 약 15% 축소
                
                # 최근 사용된 항목 제외하고 제거
                keys_to_remove = list(self.image_loader.cache.keys())[:items_to_remove]
                
                for key in keys_to_remove:
                    del self.image_loader.cache[key]
                
                logging.info(f"메모리 관리: 이미지 캐시에서 {len(keys_to_remove)}개 항목 제거")


    def show_first_run_settings_popup(self):
        """프로그램 최초 실행 시 설정 팝업을 표시"""
        # 설정 팝업창 생성
        self.settings_popup = QDialog(self)
        self.settings_popup.setWindowTitle(LanguageManager.translate("초기 설정"))
        self.settings_popup.setProperty("is_first_run_popup", True)
        self.settings_popup.setMinimumSize(500,350) # 가로, 세로 크기 조정
        # 제목 표시줄 다크 테마 적용 (Windows용)
        apply_dark_title_bar(self.settings_popup)
        # 다크 테마 배경 설정
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        self.settings_popup.setPalette(palette)
        self.settings_popup.setAutoFillBackground(True)
        # ========== 메인 레이아웃 변경: QVBoxLayout (전체) ==========
        # 전체 구조: 세로 (환영 메시지 - 가로(설정|단축키) - 확인 버튼)
        main_layout = QVBoxLayout(self.settings_popup)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        # =========================================================
        self.settings_popup.welcome_label = QLabel(LanguageManager.translate("기본 설정을 선택해주세요."))
        self.settings_popup.welcome_label.setObjectName("first_run_welcome_label")
        self.settings_popup.welcome_label.setStyleSheet(f"color: {ThemeManager.get_color('text')}; font-size: 11pt;")
        self.settings_popup.welcome_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.settings_popup.welcome_label)
        main_layout.addSpacing(10)

        settings_ui_widget = self.setup_settings_ui(
            groups_to_build=["general", "advanced"], 
            is_first_run=True
        )
        main_layout.addWidget(settings_ui_widget)

        # 확인 버튼 추가
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)
        # 🎯 중요: 확인 버튼을 self의 멤버로 만들어서 언어 변경 시 업데이트 가능하게 함
        self.first_run_confirm_button = QPushButton(LanguageManager.translate("확인"))
        # 스타일 적용 (기존 스타일 재사용 또는 새로 정의)
        if platform.system() == "Darwin": # Mac 스타일
            self.first_run_confirm_button.setStyleSheet("""
                QPushButton { background-color: #444444; color: #D8D8D8; border: none; 
                            padding: 8px 16px; border-radius: 4px; min-width: 100px; }
                QPushButton:hover { background-color: #555555; }
                QPushButton:pressed { background-color: #222222; } """)
        else: # Windows/Linux 등
            self.first_run_confirm_button.setStyleSheet(f"""
                QPushButton {{ background-color: {ThemeManager.get_color('bg_secondary')}; color: {ThemeManager.get_color('text')};
                            border: none; padding: 8px 16px; border-radius: 4px; min-width: 100px; }}
                QPushButton:hover {{ background-color: {ThemeManager.get_color('accent_hover')}; }}
                QPushButton:pressed {{ background-color: {ThemeManager.get_color('accent_pressed')}; }} """)
        self.first_run_confirm_button.clicked.connect(self.settings_popup.accept)
        # 🎯 언어 변경 콜백 등록 - 첫 실행 팝업의 텍스트 업데이트
        def update_first_run_popup_texts():
            if hasattr(self, 'settings_popup') and self.settings_popup and self.settings_popup.isVisible():
                self.settings_popup.setWindowTitle(LanguageManager.translate("초기 설정"))
                if hasattr(self.settings_popup, 'welcome_label'):
                    self.settings_popup.welcome_label.setText(LanguageManager.translate("기본 설정을 선택해주세요."))
                if hasattr(self, 'first_run_confirm_button'):
                    self.first_run_confirm_button.setText(LanguageManager.translate("확인"))
                self.update_settings_labels_texts(self.settings_popup)

        LanguageManager.register_language_change_callback(update_first_run_popup_texts)
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.first_run_confirm_button)
        button_layout.addStretch(1)
        main_layout.addWidget(button_container)
        
        # 테마 변경 콜백 등록 - 초기 설정 창용
        ThemeManager.register_theme_change_callback(self._update_first_run_settings_styles)
        
        self.update_all_settings_controls_text()
        self.update_settings_labels_texts(self.settings_popup) # 팝업 내부 라벨도 업데이트

        result = self.settings_popup.exec()
        
        for widget in self.language_group.buttons(): widget.setParent(None)
        self.theme_combo.setParent(None)
        for widget in self.panel_position_group.buttons(): widget.setParent(None)
        self.date_format_combo.setParent(None)
        self.performance_profile_combo.setParent(None)
        self.shortcuts_button.setParent(None)

        if update_first_run_popup_texts in LanguageManager._language_change_callbacks:
            LanguageManager._language_change_callbacks.remove(update_first_run_popup_texts)
        if hasattr(self, 'first_run_confirm_button'):
            delattr(self, 'first_run_confirm_button')
        
        self.settings_popup = None

        if result == QDialog.Accepted:
            logging.info("첫 실행 설정: '확인' 버튼 클릭됨. 상태 저장 실행.")
            self.save_state()
            return True
        else:
            logging.info("첫 실행 설정: '확인' 버튼을 누르지 않음. 상태 저장 안함.")
            return False

    def show_first_run_settings_popup_delayed(self):
        """메인 윈도우 표시 후 첫 실행 설정 팝업을 표시"""
        accepted_first_run = self.show_first_run_settings_popup()
        
        if not accepted_first_run:
            logging.info("VibeCullingApp: 첫 실행 설정이 완료되지 않아 앱을 종료합니다.")
            
            # 🎯 추가 검증: vibeculling_data.json 파일이 생성되지 않았는지 확인
            state_file_path = self.get_script_dir() / self.STATE_FILE
            if state_file_path.exists():
                logging.warning("VibeCullingApp: 첫 실행 설정 취소했으나 상태 파일이 존재함. 삭제합니다.")
                try:
                    state_file_path.unlink()
                    logging.info("VibeCullingApp: 상태 파일 삭제 완료.")
                except Exception as e:
                    logging.error(f"VibeCullingApp: 상태 파일 삭제 실패: {e}")
            
            QApplication.quit()
            return
        
        # 첫 실행 플래그 제거
        if hasattr(self, 'is_first_run'):
            delattr(self, 'is_first_run')
        
        logging.info("VibeCullingApp: 첫 실행 설정 완료")


    def _build_shortcut_html(self):
        """단축키 안내를 위한 HTML 문자열을 생성하는 통합 함수입니다."""
        
        # 현재 운영체제에 맞는 단축키 정의를 선택합니다.
        if sys.platform == 'darwin': # macOS
            definitions = self.SHORTCUT_DEFINITIONS_MAC
        else: # Windows, Linux 등
            definitions = self.SHORTCUT_DEFINITIONS

        # 테이블 스타일 정의
        html = """
        <style>
            table { width: 100%; border-collapse: collapse; font-size: 10pt; }
            th { text-align: left; padding: 12px 8px; color: #FFFFFF; border-bottom: 1px solid #666666; }
            td { padding: 8px; vertical-align: top; }
            td.key { font-weight: bold; color: #E0E0E0; width: 35%; padding-right: 25px; }
            td.desc { color: #B0B0B0; }
            .group-title { 
                padding-top: 45px; 
                font-size: 12pt; 
                font-weight: bold; 
                color: #FFFFFF;
                padding-bottom: 10px;
            }
            .group-title-first {
                padding-top: 15px;
                font-size: 12pt; 
                font-weight: bold; 
                color: #FFFFFF;
                padding-bottom: 10px;
            }
        </style>
        <table>
        """
        first_group = True
        
        # 선택된 definitions 리스트를 순회합니다.
        for item in definitions:
            if len(item) == 2 and item[0] == "group":
                # 그룹 제목 행
                item_type, col1 = item
                group_title = LanguageManager.translate(col1)
                
                if first_group:
                    html += f"<tr><td colspan='2' class='group-title-first' style='text-align: center;'>[ {group_title} ]</td></tr>"
                    first_group = False
                else:
                    html += f"<tr><td colspan='2' class='group-title' style='text-align: center;'>[ {group_title} ]</td></tr>"
            elif len(item) == 3 and item[0] == "key":
                # 단축키 항목 행
                item_type, col1, col2 = item
                key_text = LanguageManager.translate(col1)
                desc_text = LanguageManager.translate(col2)
                html += f"<tr><td class='key'>{key_text}</td><td class='desc'>{desc_text}</td></tr>"
        html += "</table>"
        return html


    def _update_shortcut_label_text(self, label_widget):
        """주어진 라벨 위젯의 텍스트를 현재 언어의 단축키 안내로 업데이트"""
        if label_widget:
            label_widget.setText(self._build_shortcut_html())

    def update_counter_layout(self):
        """Grid 모드 및 컨트롤 패널 위치에 따라 카운터 레이블과 설정 버튼의 레이아웃을 업데이트"""
        # 기존 컨테이너 제거 (있을 경우)
        if hasattr(self, 'counter_settings_container'):
            self.control_layout.removeWidget(self.counter_settings_container)
            self.counter_settings_container.deleteLater()
        
        # 새 컨테이너 생성
        self.counter_settings_container = QWidget()
        
        # 현재 패널 위치 확인
        is_right_panel = getattr(self, 'control_panel_on_right', False)

        if self.grid_mode == "Off":
            # Grid Off 모드: QGridLayout 사용
            counter_settings_layout = QGridLayout(self.counter_settings_container)
            counter_settings_layout.setContentsMargins(0, 0, 0, 0)
            
            # 중앙 컬럼(1)이 확장되도록 설정
            counter_settings_layout.setColumnStretch(1, 1)
            
            # 카운트 레이블은 항상 중앙(컬럼 1)에 위치
            counter_settings_layout.addWidget(self.image_count_label, 0, 1, Qt.AlignCenter)
            
            # 패널 위치에 따라 설정 버튼을 왼쪽(컬럼 0) 또는 오른쪽(컬럼 2)에 배치
            if is_right_panel:
                counter_settings_layout.addWidget(self.settings_button, 0, 2, Qt.AlignRight)
            else:
                counter_settings_layout.addWidget(self.settings_button, 0, 0, Qt.AlignLeft)
        else:
            # Grid On 모드: QHBoxLayout 사용
            counter_settings_layout = QHBoxLayout(self.counter_settings_container)
            counter_settings_layout.setContentsMargins(0, 0, 0, 0)
            counter_settings_layout.setSpacing(10)
            
            # 패널 위치에 따라 위젯 추가 순서 변경
            if is_right_panel:
                # [여백] [카운터] [여백] [버튼]
                counter_settings_layout.addStretch(1)
                counter_settings_layout.addWidget(self.image_count_label)
                counter_settings_layout.addStretch(1)
                counter_settings_layout.addWidget(self.settings_button)
            else:
                # [버튼] [여백] [카운터] [여백] (기존 방식)
                counter_settings_layout.addWidget(self.settings_button)
                counter_settings_layout.addStretch(1)
                counter_settings_layout.addWidget(self.image_count_label)
                counter_settings_layout.addStretch(1)

        last_horizontal_line_index = -1
        for i in range(self.control_layout.count()):
            item = self.control_layout.itemAt(i)
            if item and isinstance(item.widget(), HorizontalLine):
                last_horizontal_line_index = i
        
        if last_horizontal_line_index >= 0:
            insertion_index = last_horizontal_line_index + 2
            self.control_layout.insertWidget(insertion_index, self.counter_settings_container)
        else:
            self.control_layout.addWidget(self.counter_settings_container)
        
        self.update_image_count_label()

    def start_background_thumbnail_preloading(self):
        """Grid Off 상태일 때 그리드 썸네일 백그라운드 생성을 시작합니다."""
        if self.grid_mode != "Off" or not self.image_files:
            return

        logging.info("백그라운드 그리드 썸네일 생성 시작...")
        for future in self.active_thumbnail_futures:
            future.cancel()
        self.active_thumbnail_futures.clear()

        current_index = self.current_image_index
        if current_index < 0:
            return

        # HardwareProfileManager에서 그리드 미리 로딩 한도 비율 가져오기
        limit_factor = HardwareProfileManager.get("preload_grid_bg_limit_factor")
        preload_limit = int(self.image_loader.cache_limit * limit_factor)
        max_preload = min(preload_limit, len(self.image_files))
        
        logging.debug(f"그리드 썸네일 사전 로드 한도: {max_preload}개 (캐시 크기: {self.image_loader.cache_limit}, 비율: {limit_factor})")
        # --- 로직 개선 끝 ---

        preload_range = self.calculate_adaptive_thumbnail_preload_range()
        futures = []
        
        # 우선순위 이미지 (현재 이미지 주변)
        priority_indices = []
        # 중복 추가를 방지하기 위한 set
        added_indices = set()

        for offset in range(preload_range + 1):
            if len(priority_indices) >= max_preload: break
            
            # 현재 위치
            if offset == 0:
                idx = current_index
                if idx not in added_indices:
                    priority_indices.append(idx)
                    added_indices.add(idx)
                continue
                
            # 앞쪽
            idx_fwd = (current_index + offset) % len(self.image_files)
            if idx_fwd not in added_indices:
                priority_indices.append(idx_fwd)
                added_indices.add(idx_fwd)
                if len(priority_indices) >= max_preload: break

            # 뒤쪽
            idx_bwd = (current_index - offset + len(self.image_files)) % len(self.image_files)
            if idx_bwd not in added_indices:
                priority_indices.append(idx_bwd)
                added_indices.add(idx_bwd)
                if len(priority_indices) >= max_preload: break

        # 우선순위 이미지 로드
        for idx in priority_indices:
            img_path = str(self.image_files[idx])
            future = self.grid_thumbnail_executor.submit(
                self._preload_image_for_grid, img_path
            )
            futures.append(future)

        self.active_thumbnail_futures = futures
        logging.info(f"총 {len(futures)}개의 그리드용 이미지 사전 로딩 작업 제출됨.")

    def calculate_adaptive_thumbnail_preload_range(self):
        """시스템 메모리에 따라 프리로딩 범위 결정"""
        try:
            import psutil
            system_memory_gb = psutil.virtual_memory().total / (1024 * 1024 * 1024)
            
            if system_memory_gb >= 24:
                return 8  # 앞뒤 각각 8개 이미지 (총 17개)
            elif system_memory_gb >= 12:
                return 5  # 앞뒤 각각 5개 이미지 (총 11개)
            else:
                return 3  # 앞뒤 각각 3개 이미지 (총 7개)
        except:
            return 3  # 기본값

    def _preload_image_for_grid(self, image_path):
        """
        주어진 이미지 경로의 원본 이미지를 ImageLoader 캐시에 미리 로드합니다.
        백그라운드 스레드에서 실행됩니다.
        """
        try:
            # ImageLoader를 사용하여 원본 이미지 로드 (EXIF 방향 처리 포함)
            # 반환값을 사용하지 않고, 로드 행위 자체로 ImageLoader 캐시에 저장되도록 함
            loaded = self.image_loader.load_image_with_orientation(image_path)
            if loaded and not loaded.isNull():
                # print(f"이미지 사전 로드 완료: {Path(image_path).name}") # 디버깅 로그
                return True
            else:
                # print(f"이미지 사전 로드 실패: {Path(image_path).name}")
                return False
        except Exception as e:
            logging.error(f"백그라운드 이미지 사전 로드 오류 ({Path(image_path).name}): {e}")
            return False
        
    def on_mouse_wheel_action_changed(self, button):
        """마우스 휠 동작 설정 변경 시 호출"""
        if button == self.mouse_wheel_photo_radio:
            self.mouse_wheel_action = "photo_navigation"
            logging.info("마우스 휠 동작: 사진 넘기기로 변경됨")
        elif button == self.mouse_wheel_none_radio:
            self.mouse_wheel_action = "none"
            logging.info("마우스 휠 동작: 없음으로 변경됨")

    def _create_settings_controls(self):
        """설정 창에 사용될 모든 UI 컨트롤들을 미리 생성하고 초기화합니다."""
        # --- 언어 설정 (스타일 설정 제거) ---
        self.language_group = QButtonGroup(self)
        self.english_radio = QRadioButton("English")
        self.korean_radio = QRadioButton("한국어")
        self.language_group.addButton(self.english_radio, 0)
        self.language_group.addButton(self.korean_radio, 1)
        self.language_group.buttonClicked.connect(self.on_language_radio_changed)

        # --- 테마 설정 (스타일 설정 제거) ---
        self.theme_combo = QComboBox()
        for theme_name in ThemeManager.get_available_themes():
            display_text = "Default" if theme_name.lower() == "default" else theme_name.upper()
            self.theme_combo.addItem(display_text, userData=theme_name)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

        # --- 컨트롤 패널 위치 설정 (스타일 설정 제거) ---
        self.panel_position_group = QButtonGroup(self)
        self.panel_pos_left_radio = QRadioButton()
        self.panel_pos_right_radio = QRadioButton()
        self.panel_position_group.addButton(self.panel_pos_left_radio, 0)
        self.panel_position_group.addButton(self.panel_pos_right_radio, 1)
        self.panel_position_group.buttonClicked.connect(self._on_panel_position_changed)
        
        # --- 불러올 이미지 형식 설정 (스타일 설정 제거) ---
        self.ext_checkboxes = {}
        extension_groups = {"JPG": ['.jpg', '.jpeg'], "PNG": ['.png'], "WebP": ['.webp'], "HEIC": ['.heic', '.heif'], "BMP": ['.bmp'], "TIFF": ['.tif', '.tiff']}
        for name, exts in extension_groups.items():
            checkbox = QCheckBox(name)
            checkbox.stateChanged.connect(self.on_extension_checkbox_changed)
            self.ext_checkboxes[name] = checkbox

        # --- 마우스 휠 동작 설정 (스타일 설정 제거) ---
        self.mouse_wheel_group = QButtonGroup(self)
        self.mouse_wheel_photo_radio = QRadioButton()
        self.mouse_wheel_none_radio = QRadioButton()
        self.mouse_wheel_group.addButton(self.mouse_wheel_photo_radio, 0)
        self.mouse_wheel_group.addButton(self.mouse_wheel_none_radio, 1)
        self.mouse_wheel_group.buttonClicked.connect(self.on_mouse_wheel_action_changed)

        # --- 나머지 컨트롤 생성 (기존과 동일, 스타일 설정은 _update_settings_styles가 담당) ---
        self.date_format_combo = QComboBox()
        for format_code in DateFormatManager.get_available_formats():
            self.date_format_combo.addItem(DateFormatManager.get_format_display_name(format_code), format_code)
        self.date_format_combo.currentIndexChanged.connect(self.on_date_format_changed)
        
        self.folder_count_combo = QComboBox()
        for i in range(1, 10): self.folder_count_combo.addItem(str(i), i)
        self.folder_count_combo.setMinimumWidth(80)
        self.folder_count_combo.currentIndexChanged.connect(self.on_folder_count_changed)

        # ... (나머지 컨트롤 생성 코드 계속) ...
        self.viewport_speed_combo = QComboBox()
        for i in range(1, 11): self.viewport_speed_combo.addItem(str(i), i)
        self.viewport_speed_combo.setMinimumWidth(80)
        self.viewport_speed_combo.currentIndexChanged.connect(self.on_viewport_speed_changed)

        self.mouse_wheel_sensitivity_combo = QComboBox()
        self.update_mouse_wheel_sensitivity_combo_text()
        self.mouse_wheel_sensitivity_combo.currentIndexChanged.connect(self.on_mouse_wheel_sensitivity_changed)

        self.mouse_pan_sensitivity_combo = QComboBox()
        self.update_mouse_pan_sensitivity_combo_text()
        self.mouse_pan_sensitivity_combo.currentIndexChanged.connect(self.on_mouse_pan_sensitivity_changed)

        button_style = f"""
            QPushButton {{
                background-color: {ThemeManager.get_color('bg_secondary')}; color: {ThemeManager.get_color('text')};
                border: none; padding: 8px 12px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {ThemeManager.get_color('bg_hover')}; }}
            QPushButton:pressed {{ background-color: {ThemeManager.get_color('bg_pressed')}; }}
        """
        self.reset_camera_settings_button = QPushButton()
        self.reset_camera_settings_button.setStyleSheet(button_style)
        self.reset_camera_settings_button.clicked.connect(self.reset_all_camera_raw_settings)

        self.reset_app_settings_button = QPushButton(LanguageManager.translate("프로그램 설정 초기화"))
        self.reset_app_settings_button.setStyleSheet(button_style)
        self.reset_app_settings_button.clicked.connect(self.reset_application_settings)

        self.session_management_button = QPushButton()
        self.session_management_button.setStyleSheet(button_style)
        self.session_management_button.clicked.connect(self.show_session_management_popup)

        self.shortcuts_button = QPushButton()
        self.shortcuts_button.setStyleSheet(button_style)
        self.shortcuts_button.clicked.connect(self.show_shortcuts_popup)

        self.performance_profile_combo = QComboBox()
        self.update_performance_profile_combo_text()
        self.performance_profile_combo.currentIndexChanged.connect(self.on_performance_profile_changed)


    def update_mouse_pan_sensitivity_combo_text(self):
        """마우스 패닝 감도 콤보박스의 텍스트를 현재 언어에 맞게 업데이트합니다."""
        if not hasattr(self, 'mouse_pan_sensitivity_combo'):
            return
        
        current_data = self.mouse_pan_sensitivity_combo.itemData(self.mouse_pan_sensitivity_combo.currentIndex())
        
        self.mouse_pan_sensitivity_combo.blockSignals(True)
        self.mouse_pan_sensitivity_combo.clear()
        
        self.mouse_pan_sensitivity_combo.addItem(LanguageManager.translate("100% (정확)"), 1.0)
        self.mouse_pan_sensitivity_combo.addItem(LanguageManager.translate("150% (기본값)"), 1.5)
        self.mouse_pan_sensitivity_combo.addItem(LanguageManager.translate("200% (빠름)"), 2.0)
        self.mouse_pan_sensitivity_combo.addItem(LanguageManager.translate("250% (매우 빠름)"), 2.5)
        self.mouse_pan_sensitivity_combo.addItem(LanguageManager.translate("300% (최고 속도)"), 3.0)
        
        if current_data is not None:
            import math
            for i in range(self.mouse_pan_sensitivity_combo.count()):
                if math.isclose(self.mouse_pan_sensitivity_combo.itemData(i), current_data):
                    self.mouse_pan_sensitivity_combo.setCurrentIndex(i)
                    break
        else:
            # 기본값(150%)이 설정되도록 인덱스를 찾아서 설정
            default_index = self.mouse_pan_sensitivity_combo.findData(1.5)
            if default_index != -1:
                self.mouse_pan_sensitivity_combo.setCurrentIndex(default_index)

        self.mouse_pan_sensitivity_combo.blockSignals(False)


    def update_mouse_wheel_sensitivity_combo_text(self):
        """마우스 휠 민감도 콤보박스의 텍스트를 현재 언어에 맞게 업데이트합니다."""
        if not hasattr(self, 'mouse_wheel_sensitivity_combo'):
            return
        
        current_data = self.mouse_wheel_sensitivity_combo.itemData(self.mouse_wheel_sensitivity_combo.currentIndex())
        
        self.mouse_wheel_sensitivity_combo.blockSignals(True)
        self.mouse_wheel_sensitivity_combo.clear()
        
        self.mouse_wheel_sensitivity_combo.addItem(LanguageManager.translate("1 (보통)"), 1)
        self.mouse_wheel_sensitivity_combo.addItem(LanguageManager.translate("1/2 (둔감)"), 2)
        self.mouse_wheel_sensitivity_combo.addItem(LanguageManager.translate("1/3 (매우 둔감)"), 3)
        
        if current_data is not None:
            index = self.mouse_wheel_sensitivity_combo.findData(current_data)
            if index != -1:
                self.mouse_wheel_sensitivity_combo.setCurrentIndex(index)
        
        self.mouse_wheel_sensitivity_combo.blockSignals(False)


    def update_performance_profile_combo_text(self):
        """성능 프로필 콤보박스의 텍스트를 현재 언어에 맞게 업데이트합니다."""
        if not hasattr(self, 'performance_profile_combo'):
            return

        # 현재 선택된 프로필 키를 저장해 둡니다.
        current_key = self.performance_profile_combo.itemData(self.performance_profile_combo.currentIndex())
        
        # 시그널을 잠시 막고 아이템을 다시 채웁니다.
        self.performance_profile_combo.blockSignals(True)
        self.performance_profile_combo.clear()
        
        for profile_key, profile_data in HardwareProfileManager.PROFILES.items():
            # 번역 키를 가져와서 번역합니다.
            translated_name = LanguageManager.translate(profile_data["name"])
            self.performance_profile_combo.addItem(translated_name, profile_key)
        
        # 이전에 선택했던 프로필을 다시 선택합니다.
        if current_key:
            index = self.performance_profile_combo.findData(current_key)
            if index != -1:
                self.performance_profile_combo.setCurrentIndex(index)
                
        self.performance_profile_combo.blockSignals(False)

    def update_all_settings_controls_text(self):
        """현재 언어 설정에 맞게 모든 설정 관련 컨트롤의 텍스트를 업데이트합니다."""
        # --- 라디오 버튼 ---
        self.panel_pos_left_radio.setText(LanguageManager.translate("좌측"))
        self.panel_pos_right_radio.setText(LanguageManager.translate("우측"))
        self.mouse_wheel_photo_radio.setText(LanguageManager.translate("사진 넘기기"))
        self.mouse_wheel_none_radio.setText(LanguageManager.translate("없음"))

        # --- 버튼 ---
        self.reset_camera_settings_button.setText(LanguageManager.translate("RAW 처리 방식 초기화"))
        self.reset_app_settings_button.setText(LanguageManager.translate("프로그램 설정 초기화"))
        self.session_management_button.setText(LanguageManager.translate("세션 관리"))
        self.shortcuts_button.setText(LanguageManager.translate("단축키 확인"))

        # 설정 창이 열려있을 때, 그 내부의 라벨 텍스트들도 업데이트
        if hasattr(self, 'settings_popup') and self.settings_popup and self.settings_popup.isVisible():
            self.update_settings_labels_texts(self.settings_popup)

    def setup_settings_ui(self, groups_to_build=None, is_first_run=False):
        """
        요청된 그룹만 포함하는 설정 UI를 동적으로 구성하고 컨테이너 위젯을 반환합니다.
        """
        if groups_to_build is None:
            # 기본값: 모든 그룹을 빌드
            groups_to_build = ["general", "workflow", "advanced"]

        # 메인 컨테이너와 단일 그리드 레이아웃 생성
        main_container = QWidget()
        grid_layout = QGridLayout(main_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setHorizontalSpacing(25)
        grid_layout.setVerticalSpacing(UIScaleManager.get("settings_layout_vspace", 18))

        current_row = 0
        
        # --- UI 설정 그룹 ---
        if "general" in groups_to_build:
            current_row = self._build_general_settings_group(grid_layout, current_row, is_first_run=is_first_run)
            current_row = self._add_separator_if_needed(grid_layout, current_row, groups_to_build, "general")

        # --- 작업 설정 그룹 ---
        if "workflow" in groups_to_build:
            current_row = self._build_workflow_settings_group(grid_layout, current_row, is_first_run=is_first_run)
            current_row = self._add_separator_if_needed(grid_layout, current_row, groups_to_build, "workflow")

        # --- 도구 및 고급 설정 그룹 ---
        if "advanced" in groups_to_build:
            current_row = self._build_advanced_tools_group(grid_layout, current_row, is_first_run=is_first_run)
        
        # 맨 아래에 Stretch를 추가하여 모든 항목이 위로 붙도록 함
        grid_layout.setRowStretch(current_row, 1)

        return main_container

    def _add_separator_if_needed(self, grid_layout, current_row, all_groups, current_group):
        """그룹 사이에 구분선과 여백을 조건부로 추가하는 헬퍼 함수"""
        # 현재 그룹 다음에 빌드할 그룹이 있는지 확인
        current_group_index = all_groups.index(current_group)
        if current_group_index < len(all_groups) - 1:
            grid_layout.setRowMinimumHeight(current_row, 20)
            current_row += 1
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            separator.setStyleSheet(f"background-color: {ThemeManager.get_color('border')}; max-height: 1px;")
            grid_layout.addWidget(separator, current_row, 0, 1, 2)
            current_row += 1
            grid_layout.setRowMinimumHeight(current_row, 10)
            current_row += 1
        return current_row

    def _build_group_widget(self, title_key, add_widgets_func, show_title=True):
        """설정 그룹 UI를 위한 템플릿 위젯을 생성합니다."""
        group_box = QWidget()
        group_layout = QVBoxLayout(group_box)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(UIScaleManager.get("settings_layout_vspace", 15))
        if show_title:
            title_label = QLabel(f"[ {LanguageManager.translate(title_key)} ]")
            font = QFont(self.font())
            font.setBold(True)
            font.setPointSize(UIScaleManager.get("font_size") + 2) # 11pt -> 12pt (Normal 기준)
            title_label.setFont(font)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet(f"""
                color: {ThemeManager.get_color('text')}; 
                margin-bottom: 15;
                padding-left: 0px;
            """)
            title_label.setObjectName(f"group_title_{title_key.replace(' ', '_')}")
            group_layout.addWidget(title_label)
        add_widgets_func(group_layout)
        return group_box

    def _build_general_settings_group(self, grid_layout, start_row, is_first_run=False):
        """'UI 설정' 그룹 UI를 공유 그리드에 추가합니다."""
        current_row = start_row
        if not is_first_run:
            title_label = QLabel(f"[ {LanguageManager.translate('UI 설정')} ]")
            font = QFont(self.font()); font.setBold(True); font.setPointSize(UIScaleManager.get("font_size") + 2)
            title_label.setFont(font); title_label.setAlignment(Qt.AlignCenter)
            title_spacing = UIScaleManager.get("settings_group_title_spacing")
            title_label.setStyleSheet(f"""
                color: {ThemeManager.get_color('text')}; 
                margin-bottom: {title_spacing}px;
            """)
            title_label.setObjectName("group_title_UI_설정")
            grid_layout.addWidget(title_label, current_row, 0, 1, 2) # 두 열에 걸쳐 추가
            current_row += 1

        self._create_setting_row(grid_layout, current_row, "언어", self._create_language_radios()); current_row += 1
        self._create_setting_row(grid_layout, current_row, "테마", self.theme_combo); current_row += 1
        self._create_setting_row(grid_layout, current_row, "컨트롤 패널", self._create_panel_position_radios()); current_row += 1
        self._create_setting_row(grid_layout, current_row, "날짜 형식", self.date_format_combo); current_row += 1
        
        return current_row

    
    def _build_workflow_settings_group(self, grid_layout, start_row, is_first_run=False):
        """'작업 설정' 그룹 UI를 공유 그리드에 추가합니다."""
        current_row = start_row
        title_label = QLabel(f"[ {LanguageManager.translate('작업 설정')} ]")
        font = QFont(self.font()); font.setBold(True); font.setPointSize(UIScaleManager.get("font_size") + 2)
        title_label.setFont(font); title_label.setAlignment(Qt.AlignCenter)
        title_spacing = UIScaleManager.get("settings_group_title_spacing")
        title_label.setStyleSheet(f"""
            color: {ThemeManager.get_color('text')}; 
            margin-bottom: {title_spacing}px;
        """)
        title_label.setObjectName("group_title_작업_설정")
        grid_layout.addWidget(title_label, current_row, 0, 1, 2)
        current_row += 1

        # '불러올 이미지 형식' 항목을 특별 처리하여 상단 정렬합니다.
        label_key = "불러올 이미지 형식"
        label_text = LanguageManager.translate(label_key)
        checkbox_label = QLabel(label_text)
        checkbox_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        checkbox_label.setStyleSheet(f"color: {ThemeManager.get_color('text')}; font-weight: bold;")
        checkbox_label.setObjectName(f"{label_key.replace(' ', '_')}_label")
        
        # [변경] 라벨을 미세 조정하기 위한 컨테이너 생성
        label_container = QWidget()
        label_layout = QVBoxLayout(label_container)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(0)
        
        # [핵심] 라벨 위에 2px의 고정된 빈 공간을 추가하여 라벨을 아래로 밀어냅니다.
        label_layout.addSpacing(3)
        label_layout.addWidget(checkbox_label)
        
        checkbox_control = self._create_extension_checkboxes()

        # 라벨 컨테이너와 컨트롤을 그리드에 상단 정렬로 추가합니다.
        grid_layout.addWidget(label_container, current_row, 0, Qt.AlignTop | Qt.AlignLeft)
        grid_layout.addWidget(checkbox_control, current_row, 1, Qt.AlignTop)
        current_row += 1

        # 나머지 항목들은 기존 _create_setting_row (AlignVCenter)를 사용합니다.
        self._create_setting_row(grid_layout, current_row, "분류 폴더 개수", self.folder_count_combo); current_row += 1
        self._create_setting_row(grid_layout, current_row, "뷰포트 이동 속도 ⓘ", self.viewport_speed_combo); current_row += 1
        self._create_setting_row(grid_layout, current_row, "마우스 휠 동작", self._create_mouse_wheel_radios()); current_row += 1
        self._create_setting_row(grid_layout, current_row, "마우스 휠 민감도", self.mouse_wheel_sensitivity_combo); current_row += 1
        self._create_setting_row(grid_layout, current_row, "마우스 패닝 감도", self.mouse_pan_sensitivity_combo); current_row += 1

        return current_row


    @Slot(int)
    def on_mouse_pan_sensitivity_changed(self, index):
        """마우스 패닝 감도 설정 변경 시 호출"""
        if index < 0: return
        new_sensitivity = self.mouse_pan_sensitivity_combo.itemData(index)
        if new_sensitivity is not None:
            self.mouse_pan_sensitivity = float(new_sensitivity)
            logging.info(f"마우스 패닝 감도 변경됨: {self.mouse_pan_sensitivity}")

    def _build_advanced_tools_group(self, grid_layout, start_row, is_first_run=False):
        """'도구 및 고급 설정' 그룹 UI를 공유 그리드에 추가합니다."""
        current_row = start_row
        if not is_first_run:
            title_label = QLabel(f"[ {LanguageManager.translate('도구 및 고급 설정')} ]")
            font = QFont(self.font()); font.setBold(True); font.setPointSize(UIScaleManager.get("font_size") + 2)
            title_label.setFont(font); title_label.setAlignment(Qt.AlignCenter)
            title_spacing = UIScaleManager.get("settings_group_title_spacing")
            title_label.setStyleSheet(f"""
                color: {ThemeManager.get_color('text')}; 
                margin-bottom: {title_spacing}px;
            """)
            title_label.setObjectName("group_title_도구_및_고급_설정")
            grid_layout.addWidget(title_label, current_row, 0, 1, 2)
            current_row += 1

            self._create_setting_row(grid_layout, current_row, "성능 설정 ⓘ", self.performance_profile_combo); current_row += 1
            grid_layout.addWidget(self.session_management_button, current_row, 0, 1, 2, Qt.AlignLeft); current_row += 1
            grid_layout.addWidget(self.reset_camera_settings_button, current_row, 0, 1, 2, Qt.AlignLeft); current_row += 1
        
        # [변경] is_first_run 플래그에 따라 '단축키 확인' 버튼의 정렬을 다르게 설정합니다.
        if is_first_run:
            # 초기 설정 창에서는 가운데 정렬
            grid_layout.addWidget(self.shortcuts_button, current_row, 0, 1, 2, Qt.AlignCenter)
        else:
            # 일반 설정 창에서는 왼쪽 정렬
            grid_layout.addWidget(self.shortcuts_button, current_row, 0, 1, 2, Qt.AlignLeft)
        current_row += 1

        if not is_first_run:
            grid_layout.addWidget(self.reset_app_settings_button, current_row, 0, 1, 2, Qt.AlignLeft); current_row += 1
            
        return current_row

    def update_quick_sort_input_style(self):
        """빠른 분류 입력 필드의 활성화/비활성화 스타일을 업데이트합니다."""
        # 활성화 스타일
        active_style = f"""
            QLineEdit {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')};
                padding: 4px; border-radius: 3px;
            }}
            QLineEdit:focus {{ border: 1px solid {ThemeManager.get_color('accent')}; }}
        """
        # 비활성화 스타일
        disabled_style = f"""
            QLineEdit {{
                background-color: {ThemeManager.get_color('bg_disabled')};
                color: {ThemeManager.get_color('text_disabled')};
                border: 1px solid {ThemeManager.get_color('border')};
                padding: 4px; border-radius: 3px;
            }}
        """
        
        self.quick_sort_e_input.setEnabled(self.quick_sort_e_enabled)
        self.quick_sort_e_input.setStyleSheet(active_style if self.quick_sort_e_enabled else disabled_style)

        self.quick_sort_f_input.setEnabled(self.quick_sort_f_enabled)
        self.quick_sort_f_input.setStyleSheet(active_style if self.quick_sort_f_enabled else disabled_style)


    def _is_valid_foldername(self, name):
        """폴더명으로 사용 가능한지 검증하는 헬퍼 메서드"""
        if not name or not name.strip():
            return False
        invalid_chars = '\\/:*?"<>|'
        if any(char in name for char in invalid_chars):
            return False
        return True

    def on_performance_profile_changed(self, index):
        if index < 0: return
        profile_key = self.performance_profile_combo.itemData(index)
        
        HardwareProfileManager.set_profile_manually(profile_key)
        logging.info(f"사용자가 성능 프로필을 '{profile_key}'로 변경했습니다. 앱을 재시작해야 적용됩니다.")
        
        # 번역 키 사용
        title = LanguageManager.translate("설정 변경")
        line1_key = "성능 프로필이 '{profile_name}'(으)로 변경되었습니다."
        line2_key = "이 설정은 앱을 재시작해야 완전히 적용됩니다."
        
        profile_name_key = HardwareProfileManager.get("name")
        
        translated_profile_name = LanguageManager.translate(profile_name_key)
        
        message = (
            LanguageManager.translate(line1_key).format(profile_name=translated_profile_name) +
            "\n\n" +
            LanguageManager.translate(line2_key)
        )
        
        self.show_themed_message_box(QMessageBox.Information, title, message)

    def _create_setting_row(self, grid_layout, row_index, label_key, control_widget):
        """설정 항목 한 줄(라벨 + 컨트롤)을 그리드 레이아웃에 추가합니다."""
        label_text = LanguageManager.translate(label_key)
        label = QLabel(label_text)
        # [변경] 라벨 내부 텍스트도 수직 중앙 정렬로 변경
        label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        label.setStyleSheet(f"color: {ThemeManager.get_color('text')}; font-weight: bold;")
        label.setObjectName(f"{label_key.replace(' ', '_')}_label")

        # 툴팁 추가
        if label_key == "성능 설정 ⓘ":
            tooltip_key = "프로그램을 처음 실행하면 시스템 사양에 맞춰 자동으로 설정됩니다.\n높은 옵션일수록 더 많은 메모리와 CPU 자원을 사용함으로써 더 많은 사진을 백그라운드에서 미리 로드하여 작업 속도를 높입니다.\n프로그램이 시스템을 느리게 하거나 메모리를 너무 많이 차지하는 경우 낮은 옵션으로 변경해주세요.\n특히 고용량 사진을 다루는 경우 높은 옵션은 시스템에 큰 부하를 줄 수 있습니다."
            tooltip_text = LanguageManager.translate(tooltip_key)
            label.setToolTip(tooltip_text)
            label.setCursor(Qt.WhatsThisCursor)
        elif label_key == "뷰포트 이동 속도 ⓘ":
            tooltip_key = "사진 확대 중 Shift + WASD 또는 방향키로 뷰포트(확대 부분)를 이동할 때의 속도입니다."
            tooltip_text = LanguageManager.translate(tooltip_key)
            label.setToolTip(tooltip_text)
            label.setCursor(Qt.WhatsThisCursor)

        grid_layout.addWidget(label, row_index, 0, Qt.AlignVCenter | Qt.AlignLeft)
        if control_widget:
            grid_layout.addWidget(control_widget, row_index, 1, Qt.AlignVCenter)

    def _create_language_radios(self):
        """언어 선택 라디오 버튼 그룹 위젯 생성"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # 라디오 버튼이 없거나 삭제된 경우에만 재생성
        try:
            # 기존 라디오 버튼이 유효한지 확인
            if hasattr(self, 'english_radio') and self.english_radio and not self.english_radio.isWidgetType() == False:
                layout.addWidget(self.english_radio)
                layout.addWidget(self.korean_radio)
            else:
                raise AttributeError("라디오 버튼이 유효하지 않음")
        except (AttributeError, RuntimeError):
            # 현재 언어 설정 저장
            current_language = getattr(self, 'current_language', 'ko')
            
            # 설정 컨트롤 재생성
            self._create_settings_controls()
            
            # 언어 설정 복원
            if current_language == 'en':
                self.english_radio.setChecked(True)
            else:
                self.korean_radio.setChecked(True)
                
            layout.addWidget(self.english_radio)
            layout.addWidget(self.korean_radio)
        
        layout.addStretch(1)
        return container
