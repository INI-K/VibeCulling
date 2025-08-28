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



        
        self.exif_worker.request_process.emit(image_path)

    def on_exif_info_ready(self, exif_data, image_path):
        """ExifWorker에서 정보 추출 완료 시 호출"""
        # 캐시에 저장
        self.exif_cache[image_path] = exif_data
        
        # 현재 표시 중인 이미지와 일치하는지 확인
        if self.current_exif_path == image_path:
            # 현재 이미지에 대한 정보면 UI 업데이트
            self.update_info_ui_from_exif(exif_data, image_path)

    def on_exif_info_error(self, error_msg, image_path):
        """ExifWorker에서 오류 발생 시 호출"""
        logging.error(f"EXIF 정보 추출 오류 ({Path(image_path).name}): {error_msg}")
        
        # 현재 표시 중인 이미지와 일치하는지 확인
        if self.current_exif_path == image_path:
            # 오류 표시 (영어/한국어 언어 감지)
            error_text = "▪ Error" if LanguageManager.get_current_language() == "en" else "▪ 오류"
            self.info_resolution_label.setText(error_text)
            self.info_camera_label.setText(error_text)
            self.info_datetime_label.setText(error_text)
            self.info_exposure_label.setText(error_text)
            self.info_focal_label.setText(error_text)
            self.info_aperture_label.setText(error_text)
            self.info_iso_label.setText(error_text)

    def update_info_ui_from_exif(self, exif_data, image_path):
        """EXIF 데이터로 UI 레이블 업데이트"""
        try:
            # 해상도 정보 설정
            if self.original_pixmap and not self.original_pixmap.isNull():
                display_w = self.original_pixmap.width()
                display_h = self.original_pixmap.height()
                
                if exif_data["exif_resolution"]:
                    res_w, res_h = exif_data["exif_resolution"]
                    if display_w >= display_h:
                        resolution_text = f"▪ {res_w} x {res_h}"
                    else:
                        resolution_text = f"▪ {res_h} x {res_w}"
                    self.info_resolution_label.setText(resolution_text)
                else:
                    # QPixmap 크기 사용
                    if display_w >= display_h:
                        resolution_text = f"▪ {display_w} x {display_h}"
                    else:
                        resolution_text = f"▪ {display_h} x {display_w}"
                    self.info_resolution_label.setText(resolution_text)
            elif exif_data["exif_resolution"]:
                res_w, res_h = exif_data["exif_resolution"]
                if res_w >= res_h:
                    resolution_text = f"▪ {res_w} x {res_h}"
                else:
                    resolution_text = f"▪ {res_h} x {res_w}"
                self.info_resolution_label.setText(resolution_text)
            else:
                self.info_resolution_label.setText("▪ -")

            # 카메라 정보 설정
            make = exif_data["exif_make"]
            model = exif_data["exif_model"]
            camera_info = f"▪ {format_camera_name(make, model)}"
            self.info_camera_label.setText(camera_info if len(camera_info) > 2 else "▪ -")
            
            # 날짜 정보 설정
            datetime_str = exif_data["exif_datetime"]
            if datetime_str:
                try:
                    formatted_datetime = DateFormatManager.format_date(datetime_str)
                    self.info_datetime_label.setText(formatted_datetime)
                except Exception:
                    self.info_datetime_label.setText(f"▪ {datetime_str}")
            else:
                self.info_datetime_label.setText("▪ -")

            # 노출 시간 정보 설정
            exposure_str = "▪ "
            if exif_data["exif_exposure_time"] is not None:
                exposure_val = exif_data["exif_exposure_time"]
                try:
                    if isinstance(exposure_val, (int, float)):
                        if exposure_val >= 1:
                            exposure_str += f"{exposure_val:.1f}s"
                        else:
                            # 1초 미만일 때는 분수로 표시
                            fraction = 1 / exposure_val
                            exposure_str += f"1/{fraction:.0f}s"
                    else:
                        exposure_str += str(exposure_val)
                        if not str(exposure_val).endswith('s'):
                            exposure_str += "s"
                except (ValueError, TypeError, ZeroDivisionError):
                    exposure_str += str(exposure_val)
                self.info_exposure_label.setText(exposure_str)
            else:
                self.info_exposure_label.setText("▪ -")
            
            # 초점 거리 정보 설정
            focal_str = "▪ "
            focal_parts = []
            
            # 1. 숫자 값으로 변환하여 비교 준비
            focal_mm_num = None
            focal_35mm_num = None
            try:
                val = exif_data.get("exif_focal_mm")
                if val is not None:
                    # 정수로 비교하기 위해 float으로 변환 후 int로 캐스팅
                    focal_mm_num = int(float(str(val).lower().replace(" mm", "")))
            except (ValueError, TypeError):
                pass # 변환 실패 시 None 유지
            try:
                val = exif_data.get("exif_focal_35mm")
                if val is not None:
                    focal_35mm_num = int(float(str(val).lower().replace(" mm", "")))
            except (ValueError, TypeError):
                pass

            # 2. 기본 초점 거리(focal_mm)가 있으면 먼저 추가
            if focal_mm_num is not None:
                focal_parts.append(f"{focal_mm_num}mm")

            # 3. 35mm 환산 초점 거리가 있고, 기본 초점 거리와 다를 경우에만 추가
            if focal_35mm_num is not None:
                # 조건: 기본 초점 거리가 없거나(None), 두 값이 다를 때
                if focal_mm_num is None or focal_mm_num != focal_35mm_num:
                    focal_conversion = f"({LanguageManager.translate('환산')}: {focal_35mm_num}mm)"
                    focal_parts.append(focal_conversion)
            
            if focal_parts:
                focal_str += " ".join(focal_parts)
                self.info_focal_label.setText(focal_str)
            else:
                self.info_focal_label.setText("▪ -")

            # 조리개 정보 설정
            aperture_str = "▪ "
            if exif_data["exif_fnumber"] is not None:
                fnumber_val = exif_data["exif_fnumber"]
                try:
                    if isinstance(fnumber_val, (int, float)):
                        aperture_str += f"F{fnumber_val:.1f}"
                    else:
                        aperture_str += f"F{fnumber_val}"
                except (ValueError, TypeError):
                    aperture_str += str(fnumber_val)
                self.info_aperture_label.setText(aperture_str)
            else:
                self.info_aperture_label.setText("▪ -")
            
            # ISO 정보 설정
            iso_str = "▪ "
            if exif_data["exif_iso"] is not None:
                iso_val = exif_data["exif_iso"]
                try:
                    if isinstance(iso_val, (int, float)):
                        iso_str += f"ISO {int(iso_val)}"
                    else:
                        iso_str += f"ISO {iso_val}"
                except (ValueError, TypeError):
                    iso_str += str(iso_val)
                self.info_iso_label.setText(iso_str)
            else:
                self.info_iso_label.setText("▪ -")

        except Exception as e:
            logging.error(f"EXIF 정보 UI 업데이트 오류: {e}")
            # 에러가 발생해도 기본 정보는 표시 시도
            self.info_resolution_label.setText("▪ -")
            self.info_camera_label.setText("▪ -")
            self.info_datetime_label.setText("▪ -")
            self.info_exposure_label.setText("▪ -")
            self.info_focal_label.setText("▪ -")
            self.info_aperture_label.setText("▪ -")
            self.info_iso_label.setText("▪ -")


    def open_current_file_in_explorer(self, filename):
        """전달받은 파일명을 현재 폴더 경로와 조합하여 파일 열기 (RAW 모드 지원)"""
        # --- 모드에 따라 기준 폴더 결정 ---
        if self.is_raw_only_mode:
            base_folder = self.raw_folder
        else:
            base_folder = self.current_folder

        if not base_folder or not filename: # 기준 폴더나 파일명이 없으면 중단
            logging.warning("기준 폴더 또는 파일명이 없어 파일을 열 수 없습니다.")
            return

        file_path = Path(base_folder) / filename # 올바른 기준 폴더 사용
        if not file_path.exists():
            logging.warning(f"파일을 찾을 수 없음: {file_path}")
            return

        try:
            if sys.platform == 'win32':
                os.startfile(str(file_path)) # 파일 경로 전달
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(file_path)])
            else:
                subprocess.run(['xdg-open', str(file_path)])
        except Exception as e:
            logging.error(f"파일 열기 실패: {e}")
            title = LanguageManager.translate("오류")
            line1 = LanguageManager.translate("파일 열기 실패")
            line2 = LanguageManager.translate("연결된 프로그램이 없거나 파일을 열 수 없습니다.")
            self.show_themed_message_box(
                QMessageBox.Warning,
                title,
                f"{line1}: {filename}\n\n{line2}"
            )

    def display_current_image(self):
        force_refresh = getattr(self, 'force_refresh', False)
        if force_refresh:
            self.last_fit_size = (0, 0)
            self.fit_pixmap_cache.clear()
            self.force_refresh = False

        if self.thumbnail_panel and self.thumbnail_panel.model:
            selection_model = self.thumbnail_panel.list_view.selectionModel()
            if self.image_files and 0 <= self.current_image_index < len(self.image_files):
                model_index = self.thumbnail_panel.model.index(self.current_image_index, 0)
                # 이전 선택을 지우고 현재 인덱스만 선택
                selection_model.setCurrentIndex(model_index, QItemSelectionModel.ClearAndSelect)
            else:
                # 이미지가 없으면 선택 모두 해제
                selection_model.clear()

        if self.grid_mode != "Off":
            self.update_grid_view()
            return

        if not self.image_files or self.current_image_index < 0 or self.current_image_index >= len(self.image_files):
            self.image_label.clear()
            self.image_label.setStyleSheet("background-color: transparent;")
            self.setWindowTitle("VibeCulling")
            self.original_pixmap = None
            self.update_file_info_display(None)
            self.previous_image_orientation = None
            self.current_image_orientation = None
            if self.minimap_visible:
                self.minimap_widget.hide()
            self.update_counters()
            self.state_save_timer.stop()
            return
                
        try:
            current_index = self.current_image_index
            image_path = self.image_files[current_index]
            image_path_str = str(image_path)

            logging.info(f"display_current_image 호출: index={current_index}, path='{image_path.name}'")

            self.update_file_info_display(image_path_str)
            self.setWindowTitle(f"VibeCulling - {image_path.name}")
            
            if image_path_str in self.image_loader.cache:
                cached_pixmap = self.image_loader.cache[image_path_str]
                if cached_pixmap and not cached_pixmap.isNull():
                    logging.info(f"display_current_image: 캐시된 이미지 즉시 적용 - '{image_path.name}'")
                    # _on_image_loaded_for_display와 동일한 로직을 사용하여 뷰를 업데이트합니다.
                    # 이 부분이 누락되어 화면이 갱신되지 않았습니다.
                    self._on_image_loaded_for_display(cached_pixmap, image_path_str, current_index)
                    return # 캐시를 사용했으므로 비동기 로딩 없이 함수 종료

            # --- 캐시에 없으면 비동기 로딩 요청 ---
            logging.info(f"display_current_image: 캐시에 없음. 비동기 로딩 시작 및 로딩 인디케이터 타이머 설정 - '{image_path.name}'")
            if not hasattr(self, 'loading_indicator_timer'):
                self.loading_indicator_timer = QTimer(self)
                self.loading_indicator_timer.setSingleShot(True)
                self.loading_indicator_timer.timeout.connect(self.show_loading_indicator)
            
            self.loading_indicator_timer.stop() 
            self.loading_indicator_timer.start(500)

            # UI 새로고침 타이머 시작
            if not self.ui_refresh_timer.isActive():
                logging.debug("UI 새로고침 타이머 시작됨.")
                self.ui_refresh_timer.start()
            
            self.load_image_async(image_path_str, current_index)
            
        except Exception as e:
            logging.error(f"display_current_image에서 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            self.image_label.setText(f"{LanguageManager.translate('이미지 표시 중 오류 발생')}: {str(e)}")
            self.original_pixmap = None
            self.update_counters()
            self.state_save_timer.stop()

        self.update_compare_filenames()
        # 썸네일 패널 업데이트 (함수 끝 부분에 추가)
        self.update_thumbnail_current_index()

    def show_loading_indicator(self):
        """로딩 중 표시 (image_label을 image_container 크기로 설정)"""
        logging.debug("show_loading_indicator: 로딩 인디케이터 표시 시작")

        # 1. image_label의 부모가 image_container인지, 그리고 유효한지 확인
        if self.image_label.parent() is not self.image_container or \
           not self.image_container or \
           self.image_container.width() <= 0 or \
           self.image_container.height() <= 0:
            logging.warning("show_loading_indicator: image_container가 유효하지 않거나 크기가 없어 로딩 인디케이터 중앙 정렬 불가. 기본 동작 수행.")
            # 기존 로직 (크기 설정 없이)
            loading_pixmap = QPixmap(200, 200)
            loading_pixmap.fill(QColor(40, 40, 40))
            self.image_label.setPixmap(loading_pixmap)
            self.image_label.setText(LanguageManager.translate("이미지 로드 중..."))
            self.image_label.setStyleSheet("color: white; background-color: transparent;")
            self.image_label.setAlignment(Qt.AlignCenter) # image_label 내부에서 중앙 정렬
            return

        # 2. image_container의 현재 크기를 가져옵니다.
        container_width = self.image_container.width()
        container_height = self.image_container.height()
        logging.debug(f"  image_container 크기: {container_width}x{container_height}")

        # 3. image_label의 geometry를 image_container의 전체 영역으로 설정합니다.
        #    이렇게 하면 image_label이 image_container를 꽉 채우게 됩니다.
        self.image_label.setGeometry(0, 0, container_width, container_height)
        logging.debug(f"  image_label geometry 설정: 0,0, {container_width}x{container_height}")

        # 4. 로딩 플레이스홀더 픽스맵 생성 (선택 사항: 크기를 image_label에 맞출 수도 있음)
        #    기존 200x200 크기를 유지하고, image_label 내에서 중앙 정렬되도록 합니다.
        #    또는, 로딩 아이콘이 너무 커지는 것을 방지하기 위해 적절한 크기를 유지합니다.
        placeholder_size = min(200, container_width // 2, container_height // 2) # 너무 커지지 않도록 제한
        if placeholder_size < 50: placeholder_size = 50 # 최소 크기 보장
        
        loading_pixmap = QPixmap(placeholder_size, placeholder_size)
        loading_pixmap.fill(QColor(40, 40, 40)) # 어두운 회색 배경

        # 5. image_label에 픽스맵과 텍스트 설정
        self.image_label.setPixmap(loading_pixmap)
        self.image_label.setText(LanguageManager.translate("이미지 로드 중..."))
        
        # 6. image_label의 스타일과 정렬 설정
        #    - 배경은 투명하게 하여 image_container의 검은색 배경이 보이도록 합니다.
        #    - 텍스트 색상은 흰색으로 합니다.
        #    - setAlignment(Qt.AlignCenter)를 통해 픽스맵과 텍스트가 image_label의 중앙에 오도록 합니다.
        #      (image_label이 이제 image_container 전체 크기이므로, 이는 곧 캔버스 중앙 정렬을 의미합니다.)
        self.image_label.setStyleSheet("color: white; background-color: transparent;")
        self.image_label.setAlignment(Qt.AlignCenter)

        logging.debug("show_loading_indicator: 로딩 인디케이터 표시 완료 (중앙 정렬됨)")

    def load_image_async(self, image_path, requested_index):
        """이미지 비동기 로딩 (높은 우선순위)"""
        # 기존 작업 취소
        if hasattr(self, '_current_loading_future') and self._current_loading_future:
            self._current_loading_future.cancel()
        
        # 우선순위 높음으로 현재 이미지 로딩 시작
        self._current_loading_future = self.resource_manager.submit_imaging_task_with_priority(
            'high',  # 높은 우선순위
            self._load_image_task,
            image_path,
            requested_index
        )
        
        # 인접 이미지 미리 로드 시작
        self.preload_adjacent_images(requested_index)

    def _load_image_task(self, image_path, requested_index):
        """백그라운드 스레드에서 실행되는 이미지 로딩 작업. RAW 디코딩은 RawDecoderPool에 위임."""
        try:
            resource_manager = ResourceManager.instance()
            if not resource_manager._running:
                logging.info(f"PhotoSortApp._load_image_task: ResourceManager가 종료 중이므로 작업 중단 ({Path(image_path).name})")
                if hasattr(self, 'image_loader'):
                    QMetaObject.invokeMethod(self.image_loader, "loadFailed", Qt.QueuedConnection,
                                             Q_ARG(str, "ResourceManager_shutdown"),
                                             Q_ARG(str, image_path),
                                             Q_ARG(int, requested_index))
                return False

            file_path_obj = Path(image_path)
            is_raw = file_path_obj.suffix.lower() in self.raw_extensions
            raw_processing_method = self.image_loader._raw_load_strategy

            if is_raw and raw_processing_method == "decode":
                logging.info(f"_load_image_task: RAW 파일 '{file_path_obj.name}'의 'decode' 요청. RawDecoderPool에 제출.")
                
                # 이 콜백은 RawDecoderPool의 결과가 도착했을 때 메인 스레드에서 실행됩니다.
                wrapped_callback = lambda result_dict: self._on_raw_decoded_for_display(
                    result_dict, 
                    requested_index=requested_index,
                    is_main_display_image=True
                )
                
                task_id = self.resource_manager.submit_raw_decoding(image_path, wrapped_callback)
                if task_id is None: 
                    raise RuntimeError("Failed to submit RAW decoding task.")
                return True 
            else:
                # JPG 또는 RAW (preview 모드)는 ImageLoader.load_image_with_orientation을 직접 호출합니다.
                # 이 함수는 ICC 프로파일을 처리하도록 이미 수정되었습니다.
                logging.info(f"_load_image_task: '{file_path_obj.name}' 직접 로드 시도 (JPG 또는 RAW-preview).")
                pixmap = self.image_loader.load_image_with_orientation(image_path)

                if not resource_manager._running: # 로드 후 다시 확인
                    if hasattr(self, 'image_loader'):
                        QMetaObject.invokeMethod(self.image_loader, "loadFailed", Qt.QueuedConnection,
                                                 Q_ARG(str, "ResourceManager_shutdown_post"),
                                                 Q_ARG(str, image_path),
                                                 Q_ARG(int, requested_index))
                    return False
                
                # 결과를 메인 스레드로 안전하게 전달합니다.
                if hasattr(self, 'image_loader'):
                    QMetaObject.invokeMethod(self.image_loader, "loadCompleted", Qt.QueuedConnection,
                                             Q_ARG(QPixmap, pixmap),
                                             Q_ARG(str, image_path),
                                             Q_ARG(int, requested_index))
                return True

        except Exception as e:
            if ResourceManager.instance()._running:
                logging.error(f"_load_image_task 오류 ({Path(image_path).name if image_path else 'N/A'}): {e}")
                import traceback
                traceback.print_exc()
                if hasattr(self, 'image_loader'):
                    QMetaObject.invokeMethod(self.image_loader, "loadFailed", Qt.QueuedConnection,
                                             Q_ARG(str, str(e)),
                                             Q_ARG(str, image_path),
                                             Q_ARG(int, requested_index))
            else:
                logging.info(f"_load_image_task 중 오류 발생했으나 ResourceManager 이미 종료됨 ({Path(image_path).name if image_path else 'N/A'}): {e}")
            return False



    def _on_image_loaded_for_display(self, pixmap, image_path_str_loaded, requested_index):
        if self.ui_refresh_timer.isActive():
            logging.debug(f"UI 새로고침 타이머 중지됨 (일반 로드 완료): {Path(image_path_str_loaded).name}")
            self.ui_refresh_timer.stop()

        if self.current_image_index != requested_index:
            return
        if hasattr(self, 'loading_indicator_timer'): self.loading_indicator_timer.stop()
        if pixmap.isNull():
            self.image_label.setText(f"{LanguageManager.translate('이미지 로드 실패')}")
            self.original_pixmap = None; self.update_counters(); return

        new_image_orientation = "landscape" if pixmap.width() >= pixmap.height() else "portrait"
        
        prev_orientation = getattr(self, 'previous_image_orientation_for_carry_over', None)
        prev_zoom = getattr(self, 'previous_zoom_mode_for_carry_over', "Fit")
        prev_rel_center = getattr(self, 'previous_active_rel_center_for_carry_over', QPointF(0.5, 0.5))

        is_photo_actually_changed = (hasattr(self, 'previous_image_path_for_focus_carry_over') and # 이 변수는 여전히 사진 변경 자체를 판단하는 데 사용
                                     self.previous_image_path_for_focus_carry_over is not None and
                                     self.previous_image_path_for_focus_carry_over != image_path_str_loaded)
        
        if is_photo_actually_changed:
            if prev_zoom in ["100%", "Spin"] and prev_orientation == new_image_orientation:
                # 방향 동일 & 이전 줌: 이전 "활성" 포커스 이어받기
                self.zoom_mode = prev_zoom
                self.current_active_rel_center = prev_rel_center
                self.current_active_zoom_level = self.zoom_mode
                self.zoom_change_trigger = "photo_change_carry_over_focus"
                # 새 사진의 "방향 타입" 포커스를 이전 활성 포커스로 덮어쓰기
                self._save_orientation_viewport_focus(new_image_orientation, self.current_active_rel_center, self.current_active_zoom_level)
            else: # Fit에서 왔거나, 방향이 다르거나, 이전 줌 정보 부적절
                self.zoom_mode = "Fit" # 새 사진은 Fit으로 시작
                self.current_active_rel_center = QPointF(0.5, 0.5)
                self.current_active_zoom_level = "Fit"
                self.zoom_change_trigger = "photo_change_to_fit"
        # else: 사진 변경 아님 (zoom_change_trigger는 다른 곳에서 설정되어 apply_zoom_to_image로 전달됨)

        # 라디오 버튼 UI 동기화 및 나머지 로직 (original_pixmap 설정, apply_zoom_to_image 호출 등)
        if self.zoom_mode == "Fit": self.fit_radio.setChecked(True)
        elif self.zoom_mode == "100%": self.zoom_100_radio.setChecked(True)
        elif self.zoom_mode == "Spin": self.zoom_spin_btn.setChecked(True)
        
        # self.previous_image_orientation = self.current_image_orientation # 이제 _prepare_for_photo_change에서 관리
        self.current_image_orientation = new_image_orientation # 새 이미지의 방향으로 업데이트
        self.original_pixmap = pixmap
        
        self.apply_zoom_to_image() # 여기서 current_active_... 값들이 사용됨
        
        # 임시 변수 초기화
        if hasattr(self, 'previous_image_path_for_focus_carry_over'): self.previous_image_path_for_focus_carry_over = None 
        if hasattr(self, 'previous_image_orientation_for_carry_over'): self.previous_image_orientation_for_carry_over = None
        if hasattr(self, 'previous_zoom_mode_for_carry_over'): self.previous_zoom_mode_for_carry_over = None
        if hasattr(self, 'previous_active_rel_center_for_carry_over'): self.previous_active_rel_center_for_carry_over = None

        if self.minimap_toggle.isChecked(): self.toggle_minimap(True)
        self.update_counters()

        if self.grid_mode == "Off": # Grid Off 모드에서만 이 경로로 current_image_index가 안정화됨
            self.state_save_timer.start()
            logging.debug(f"_on_image_loaded_for_display: Index save timer (re)started for index {self.current_image_index}")
        self.update_compare_filenames()



    def _on_raw_decoded_for_display(self, result: dict, requested_index: int, is_main_display_image: bool = False):
        if is_main_display_image and self.ui_refresh_timer.isActive():
            logging.debug(f"UI 새로고침 타이머 중지됨 (RAW 디코딩 완료): {result.get('file_path')}")
            self.ui_refresh_timer.stop()
            
        file_path = result.get('file_path')
        success = result.get('success', False)
        logging.info(f"_on_raw_decoded_for_display 시작: 파일='{Path(file_path).name if file_path else 'N/A'}', 요청 인덱스={requested_index}, 성공={success}, 메인={is_main_display_image}")

        if not success:
            error_msg = result.get('error', 'Unknown error')
            logging.error(f"  _on_raw_decoded_for_display: RAW 디코딩 실패 ({Path(file_path).name if file_path else 'N/A'}): {error_msg}")
            if is_main_display_image:
                self._close_first_raw_decode_progress()
                self.image_label.setText(f"{LanguageManager.translate('이미지 로드 실패')}: {error_msg}")
                self.original_pixmap = None
                self.update_counters()
                if file_path and hasattr(self, 'image_loader'):
                    self.image_loader.decodingFailedForFile.emit(file_path)
            return

        try:
            data_bytes = result.get('data')
            shape = result.get('shape')
            if not data_bytes or not shape:
                raise ValueError("디코딩 결과 데이터 또는 형태 정보 누락")
            height, width, _ = shape
            qimage = QImage(data_bytes, width, height, width * 3, QImage.Format_RGB888)

            # --- NEW: RAW 이미지에 sRGB 색 공간 정보 태그 ---
            # rawpy.postprocess의 기본 출력은 sRGB이므로, sRGB라고 명시해줍니다.
            # 이 태그가 있으면 Qt가 자동으로 모니터 프로파일에 맞게 색상을 변환합니다.
            srgb_color_space = QColorSpace(QColorSpace.SRgb)
            if qimage and not qimage.isNull() and srgb_color_space.isValid():
                qimage.setColorSpace(srgb_color_space)

            pixmap = QPixmap.fromImage(qimage)
            if pixmap.isNull():
                raise ValueError("디코딩된 데이터로 QPixmap 생성 실패")

            if hasattr(self, 'image_loader'):
                self.image_loader._add_to_cache(file_path, pixmap)
            logging.info(f"  _on_raw_decoded_for_display: RAW 이미지 캐싱 성공: '{Path(file_path).name}'")

        except Exception as e:
            logging.error(f"  _on_raw_decoded_for_display: RAW 디코딩 성공 후 QPixmap 처리 오류 ({Path(file_path).name if file_path else 'N/A'}): {e}")
            return

        current_path_to_display = self.get_current_image_path()
        path_match = file_path and current_path_to_display and Path(file_path).resolve() == Path(current_path_to_display).resolve()

        if is_main_display_image and path_match:
            logging.info(f"  _on_raw_decoded_for_display: 메인 이미지 UI 업데이트 시작. 파일='{Path(file_path).name}'")
            if hasattr(self, 'loading_indicator_timer'):
                self.loading_indicator_timer.stop()

            self.previous_image_orientation = self.current_image_orientation
            self.current_image_orientation = "landscape" if pixmap.width() >= pixmap.height() else "portrait"
            self.original_pixmap = pixmap
            self.apply_zoom_to_image()
            if self.minimap_toggle.isChecked(): self.toggle_minimap(True)
            self.update_counters()
            
            if self.grid_mode == "Off":
                self.state_save_timer.start()
            
            self._close_first_raw_decode_progress()
            self.update_compare_filenames()
            logging.info(f"  _on_raw_decoded_for_display: 메인 이미지 UI 업데이트 완료.")
        else:
            logging.info(f"  _on_raw_decoded_for_display: 프리로드된 이미지 캐싱 완료, UI 업데이트는 건너뜀. 파일='{Path(file_path).name}'")

        logging.info(f"_on_raw_decoded_for_display 종료: 파일='{Path(file_path).name if file_path else 'N/A'}'")


    def process_pending_raw_results(self):
        """ResourceManager를 통해 RawDecoderPool의 완료된 결과들을 처리합니다."""
        if hasattr(self, 'resource_manager') and self.resource_manager:
            # 한 번에 최대 5개의 결과를 처리하도록 시도 (조정 가능)
            processed_count = self.resource_manager.process_raw_results(max_results=5)
            if processed_count > 0:
                logging.debug(f"process_pending_raw_results: {processed_count}개의 RAW 디코딩 결과 처리됨.")
        # else: # ResourceManager가 없는 예외적인 경우
            # logging.warning("process_pending_raw_results: ResourceManager 인스턴스가 없습니다.")

    def _on_image_load_failed(self, image_path, error_message, requested_index):
        if self.ui_refresh_timer.isActive():
            logging.debug(f"UI 새로고침 타이머 중지됨 (로드 실패): {Path(image_path).name}")
            self.ui_refresh_timer.stop()
            
        # 요청 시점의 인덱스와 현재 인덱스 비교 (이미지 변경 여부 확인)
        if self.current_image_index != requested_index:
            print(f"이미지가 변경되어 오류 결과 무시: 요청={requested_index}, 현재={self.current_image_index}")
            return
            
        self.image_label.setText(f"{LanguageManager.translate('이미지 로드 실패')}: {error_message}")
        self.original_pixmap = None
        self.update_counters()

    def _periodic_ui_refresh(self):
        """
        UI 업데이트가 지연될 경우를 대비해 주기적으로 캐시를 확인하고
        이미지가 준비되었다면 강제로 화면을 갱신합니다.
        """
        # 타이머가 실행될 필요 없는 조건들을 먼저 확인하고 중지
        if self.grid_mode != "Off" or not self.image_files or self.current_image_index < 0:
            self.ui_refresh_timer.stop()
            return

        try:
            # 현재 표시해야 할 이미지의 경로를 가져옴
            image_path_str = str(self.image_files[self.current_image_index])

            # 이미지 로더 캐시에 해당 이미지가 있는지 확인
            if image_path_str in self.image_loader.cache:
                cached_pixmap = self.image_loader.cache.get(image_path_str)
                
                # 캐시된 픽스맵이 유효한지 확인
                if cached_pixmap and not cached_pixmap.isNull():
                    # 이미지가 준비되었으므로, 강제 새로고침 실행
                    logging.info(f"UI 새로고침 타이머가 캐시된 이미지 '{Path(image_path_str).name}'를 발견하여 강제 표시합니다.")
                    
                    # 모든 관련 타이머 중지
                    self.ui_refresh_timer.stop()
                    if hasattr(self, 'loading_indicator_timer') and self.loading_indicator_timer.isActive():
                        self.loading_indicator_timer.stop()
                    
                    # 기존의 이미지 표시 완료 로직을 직접 호출하여 UI 업데이트
                    # RAW 디코딩 결과와 일반 로드 결과 모두 이 함수를 거치므로 안전합니다.
                    self._on_image_loaded_for_display(cached_pixmap, image_path_str, self.current_image_index)
        except IndexError:
            # 이미지 목록이 변경되는 도중에 타이머가 실행될 경우를 대비한 예외 처리
            self.ui_refresh_timer.stop()
        except Exception as e:
            logging.error(f"주기적 UI 새로고침 중 오류 발생: {e}")
            self.ui_refresh_timer.stop()



    def preload_adjacent_images(self, current_index):
        """인접 이미지 미리 로드 - 시스템 프로필에 따라 동적으로 범위 조절."""
        if not self.image_files:
            return

        # HardwareProfileManager에서 현재 프로필의 미리 로드 범위 가져오기
        forward_preload_count, backward_preload_count = HardwareProfileManager.get("preload_range_adjacent")
        priority_close_threshold = HardwareProfileManager.get("preload_range_priority")
        
        total_images = len(self.image_files)
        
        # 이동 방향 감지 (기존 로직 유지)
        direction = 1
        if hasattr(self, 'previous_image_index') and self.previous_image_index != current_index:
            if self.previous_image_index < current_index or \
            (self.previous_image_index == total_images - 1 and current_index == 0):
                direction = 1
            elif self.previous_image_index > current_index or \
                (self.previous_image_index == 0 and current_index == total_images - 1):
                direction = -1
        self.previous_image_index = current_index

        # 캐시된 이미지와 현재 로딩 요청된 이미지 확인
        cached_images = set(self.image_loader.cache.keys())
        # (이하 로직은 기존과 거의 동일하나, 범위 변수를 프로필에서 가져온 값으로 사용)
        
        to_preload = []
        if direction >= 0: # 앞으로 이동
            for offset in range(1, forward_preload_count + 1):
                idx = (current_index + offset) % total_images
                if str(self.image_files[idx]) not in cached_images:
                    priority = 'high' if offset <= priority_close_threshold else ('medium' if offset <= priority_close_threshold * 2 else 'low')
                    to_preload.append((idx, priority))
            for offset in range(1, backward_preload_count + 1):
                idx = (current_index - offset + total_images) % total_images
                if str(self.image_files[idx]) not in cached_images:
                    priority = 'medium' if offset <= priority_close_threshold else 'low'
                    to_preload.append((idx, priority))
        else: # 뒤로 이동
            for offset in range(1, forward_preload_count + 1):
                idx = (current_index - offset + total_images) % total_images
                if str(self.image_files[idx]) not in cached_images:
                    priority = 'high' if offset <= priority_close_threshold else ('medium' if offset <= priority_close_threshold * 2 else 'low')
                    to_preload.append((idx, priority))
            for offset in range(1, backward_preload_count + 1):
                idx = (current_index + offset) % total_images
                if str(self.image_files[idx]) not in cached_images:
                    priority = 'medium' if offset <= priority_close_threshold else 'low'
                    to_preload.append((idx, priority))

        # 로드 요청 제출
        for idx, priority in to_preload:
            img_path = str(self.image_files[idx])
            # 여기서는 _preload_image_for_grid를 사용하여 preview만 로드하는 것으로 단순화
            self.resource_manager.submit_imaging_task_with_priority(
                priority,
                self._preload_image_for_grid, 
                img_path
            )


    def on_grid_cell_clicked(self, clicked_widget, clicked_index):
        """그리드 셀 클릭 이벤트 핸들러 (다중 선택 지원, Shift+클릭 범위 선택 추가)"""
        if self.grid_mode == "Off" or not self.grid_labels:
            return

        try:
            # 현재 페이지에 실제로 표시될 수 있는 이미지의 총 개수
            current_page_image_count = min(len(self.grid_labels), len(self.image_files) - self.grid_page_start_index)

            # 클릭된 인덱스가 유효한 범위 내에 있고, 해당 인덱스에 해당하는 이미지가 실제로 존재하는지 확인
            if 0 <= clicked_index < current_page_image_count:
                image_path_property = clicked_widget.property("image_path")

                if image_path_property:
                    # 키 상태 확인
                    modifiers = QApplication.keyboardModifiers()
                    ctrl_pressed = bool(modifiers & Qt.ControlModifier)
                    shift_pressed = bool(modifiers & Qt.ShiftModifier)
                    
                    if shift_pressed and self.last_single_click_index != -1:
                        # Shift+클릭: 범위 선택
                        start_index = min(self.last_single_click_index, clicked_index)
                        end_index = max(self.last_single_click_index, clicked_index)
                        
                        # 범위 내의 모든 유효한 셀 선택
                        self.selected_grid_indices.clear()
                        for i in range(start_index, end_index + 1):
                            if i < current_page_image_count:
                                # 해당 인덱스에 실제 이미지가 있는지 확인
                                if i < len(self.grid_labels):
                                    cell_widget = self.grid_labels[i]
                                    if cell_widget.property("image_path"):
                                        self.selected_grid_indices.add(i)
                        
                        # Primary 선택을 범위의 첫 번째로 설정
                        if self.selected_grid_indices:
                            self.primary_selected_index = self.grid_page_start_index + start_index
                            self.current_grid_index = start_index
                        
                        logging.debug(f"Shift+클릭 범위 선택: {start_index}~{end_index} ({len(self.selected_grid_indices)}개 선택)")
                        
                    elif ctrl_pressed:
                        # Ctrl+클릭: 다중 선택 토글 (기존 코드)
                        if clicked_index in self.selected_grid_indices:
                            self.selected_grid_indices.remove(clicked_index)
                            logging.debug(f"셀 선택 해제: index {clicked_index}")
                            
                            if self.primary_selected_index == self.grid_page_start_index + clicked_index:
                                if self.selected_grid_indices:
                                    first_selected = min(self.selected_grid_indices)
                                    self.primary_selected_index = self.grid_page_start_index + first_selected
                                else:
                                    self.primary_selected_index = -1
                        else:
                            self.selected_grid_indices.add(clicked_index)
                            logging.debug(f"셀 선택 추가: index {clicked_index}")
                            
                            if self.primary_selected_index == -1:
                                self.primary_selected_index = self.grid_page_start_index + clicked_index
                    else:
                        # 일반 클릭: 기존 선택 모두 해제하고 새로 선택
                        self.selected_grid_indices.clear()
                        self.selected_grid_indices.add(clicked_index)
                        self.primary_selected_index = self.grid_page_start_index + clicked_index
                        self.current_grid_index = clicked_index
                        self.last_single_click_index = clicked_index  # 마지막 단일 클릭 인덱스 저장
                        logging.debug(f"단일 셀 선택: index {clicked_index}")

                    # UI 업데이트
                    self.update_grid_selection_border()
                    self.update_window_title_with_selection()

                    # 파일 정보는 primary 선택 이미지로 표시
                    if self.primary_selected_index != -1 and 0 <= self.primary_selected_index < len(self.image_files):
                        selected_image_path = str(self.image_files[self.primary_selected_index])
                        self.update_file_info_display(selected_image_path)
                    else:
                        self.update_file_info_display(None)
                        
                    # 선택이 있으면 타이머 시작
                    if self.selected_grid_indices:
                        self.state_save_timer.start()
                        logging.debug(f"on_grid_cell_clicked: Index save timer (re)started for grid cells {self.selected_grid_indices}")

                    # 카운터 업데이트 추가
                    self.update_counters()

                else:
                    logging.debug(f"빈 셀 클릭됨 (이미지 경로 없음): index {clicked_index}")
                    self.update_file_info_display(None)
            else:
                logging.debug(f"유효하지 않은 셀 클릭됨: index {clicked_index}")
                self.update_file_info_display(None)
        except Exception as e:
            logging.error(f"on_grid_cell_clicked 오류: {e}")
            self.update_file_info_display(None)
             

    def update_image_count_label(self):
        """이미지 및 페이지 카운트 레이블 업데이트"""
        total = len(self.image_files)
        text = "- / -" # 기본값

        if total > 0:
            current_display_index = -1
            if self.grid_mode != "Off":
                # Grid 모드: 이미지 카운트와 페이지 정보 함께 표시
                selected_image_list_index = self.grid_page_start_index + self.current_grid_index
                if 0 <= selected_image_list_index < total:
                    current_display_index = selected_image_list_index + 1

                rows, cols = self._get_grid_dimensions()
                num_cells = rows * cols
                
                # num_cells가 0이 되는 예외 상황을 방지하여 ZeroDivisionError를 막습니다.
                if num_cells == 0:
                    logging.error(f"update_image_count_label: num_cells가 0이지만 grid_mode는 '{self.grid_mode}'입니다. 충돌을 방지합니다.")
                    total_pages = 1
                    current_page = 1
                else:
                    total_pages = (total + num_cells - 1) // num_cells
                    current_page = (self.grid_page_start_index // num_cells) + 1

                count_part = f"{current_display_index} / {total}" if current_display_index != -1 else f"- / {total}"
                page_part = f"Pg. {current_page} / {total_pages}"
                text = f"{count_part} ({page_part})"

            else:
                # Grid Off 모드: 이미지 카운트만 표시
                if 0 <= self.current_image_index < total:
                    current_display_index = self.current_image_index + 1
                text = f"{current_display_index} / {total}" if current_display_index != -1 else f"- / {total}"

        self.image_count_label.setText(text)


    def update_counters(self):
        """이미지 카운터 레이블 업데이트"""
        self.update_image_count_label()

    def get_script_dir(self):
        """실행 파일 또는 스크립트의 디렉토리를 반환"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 등으로 패키징된 경우
            return Path(sys.executable).parent
        else:
            # 일반 스크립트로 실행된 경우
            return Path(__file__).parent

    def save_state(self):
        """현재 애플리케이션 상태를 JSON 파일에 저장"""

        #첫 실행 중에는 상태를 저장하지 않음
        if hasattr(self, 'is_first_run') and self.is_first_run:
            logging.debug("save_state: 첫 실행 중이므로 상태 저장을 건너뜀")
            return
        
        # --- 현재 실제로 선택/표시된 이미지의 '전체 리스트' 인덱스 계산 ---
        actual_current_image_list_index = -1
        if self.grid_mode != "Off":
            if self.image_files and 0 <= self.grid_page_start_index + self.current_grid_index < len(self.image_files):
                actual_current_image_list_index = self.grid_page_start_index + self.current_grid_index
        else: # Grid Off 모드
            if self.image_files and 0 <= self.current_image_index < len(self.image_files):
                actual_current_image_list_index = self.current_image_index
        # --- 계산 끝 ---

        state_data = {
            "current_folder": str(self.current_folder) if self.current_folder else "",
            "raw_folder": str(self.raw_folder) if self.raw_folder else "",
            "raw_files": {k: str(v) for k, v in self.raw_files.items()},
            "move_raw_files": self.move_raw_files,
            "target_folders": [str(f) if f else "" for f in self.target_folders],
            "zoom_mode": self.zoom_mode,
            "zoom_spin_value": self.zoom_spin_value,
            "minimap_visible": self.minimap_toggle.isChecked(),
            "grid_mode": self.grid_mode,
            # "current_image_index": self.current_image_index, # 이전 방식
            "current_image_index": actual_current_image_list_index, # 실제로 보고 있던 이미지의 전역 인덱스 저장
            "current_grid_index": self.current_grid_index, # Grid 모드일 때의 페이지 내 인덱스 (복원 시 참고용)
            "grid_page_start_index": self.grid_page_start_index, # Grid 모드일 때의 페이지 시작 인덱스 (복원 시 참고용)
            "previous_grid_mode": self.previous_grid_mode,
            "language": LanguageManager.get_current_language(),
            "date_format": DateFormatManager.get_current_format(),
            "theme": ThemeManager.get_current_theme_name(),
            "is_raw_only_mode": self.is_raw_only_mode,
            "control_panel_on_right": getattr(self, 'control_panel_on_right', False),
            "show_grid_filenames": self.show_grid_filenames, # 파일명 표시 상태
            "last_used_raw_method": self.image_loader._raw_load_strategy if hasattr(self, 'image_loader') else "preview",
            "camera_raw_settings": self.camera_raw_settings, # 카메라별 raw 설정
            "viewport_move_speed": getattr(self, 'viewport_move_speed', 5), # 키보드 뷰포트 이동속도
            "mouse_wheel_action": getattr(self, 'mouse_wheel_action', 'photo_navigation'),  # 마우스 휠 동작
            "mouse_wheel_sensitivity": getattr(self, 'mouse_wheel_sensitivity', 1),
            "mouse_pan_sensitivity": getattr(self, 'mouse_pan_sensitivity', 1.5),
            "folder_count": self.folder_count,
            "supported_image_extensions": sorted(list(self.supported_image_extensions)),
            "saved_sessions": self.saved_sessions,
            "performance_profile": HardwareProfileManager.get_current_profile_key(),
            "image_rotations": self.image_rotations,
            "compare_mode_active": self.compare_mode_active,
            "image_B_path": str(self.image_B_path) if self.image_B_path else "",
        }

        save_path = self.get_script_dir() / self.STATE_FILE
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=4, ensure_ascii=False)
            logging.info(f"상태 저장 완료: {save_path}")
        except Exception as e:
            logging.error(f"상태 저장 실패: {e}")

    def load_state(self):
        """JSON 파일에서 애플리케이션 상태 불러오기"""
        logging.info(f"VibeCullingApp.load_state: 상태 불러오기 시작")
        load_path = self.get_script_dir() / self.STATE_FILE
        is_first_run = not load_path.exists()
        logging.debug(f"  load_state: is_first_run = {is_first_run}")
        if is_first_run:
            logging.info("VibeCullingApp.load_state: 첫 실행 감지. 초기 설정으로 시작합니다.")
            self.initialize_to_default_state()
            LanguageManager.set_language("en") 
            ThemeManager.set_theme("default")  
            DateFormatManager.set_date_format("yyyy-mm-dd")
            self.supported_image_extensions = {'.jpg', '.jpeg'}
            self.mouse_wheel_action = "photo_navigation"
            if hasattr(self, 'english_radio'): self.english_radio.setChecked(True)
            if hasattr(self, 'panel_pos_left_radio'): self.panel_pos_left_radio.setChecked(True)
            if hasattr(self, 'ext_checkboxes'):
                for name, checkbox in self.ext_checkboxes.items():
                    checkbox.setChecked(name == "JPG")
            if hasattr(self, 'folder_count_combo'):
                index = self.folder_count_combo.findData(self.folder_count)
                if index != -1: self.folder_count_combo.setCurrentIndex(index)
            if hasattr(self, 'viewport_speed_combo'):
                index = self.viewport_speed_combo.findData(self.viewport_move_speed)
                if index != -1: self.viewport_speed_combo.setCurrentIndex(index)
            if hasattr(self, 'mouse_wheel_photo_radio'): self.mouse_wheel_photo_radio.setChecked(True)
            self.update_all_ui_after_load_failure_or_first_run()
            self._sync_performance_profile_ui()
            self.is_first_run = True
            QTimer.singleShot(0, self._apply_panel_position)
            self.setFocus()
            return True
        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            logging.info(f"VibeCullingApp.load_state: 상태 파일 로드 완료 ({load_path})")

            self._is_silent_load = True

            # 1. 기본 설정 복원
            language = loaded_data.get("language", "en")
            LanguageManager.set_language(language)
            date_format = loaded_data.get("date_format", "yyyy-mm-dd")
            DateFormatManager.set_date_format(date_format)
            theme = loaded_data.get("theme", "default")
            ThemeManager.set_theme(theme)
            self.camera_raw_settings = loaded_data.get("camera_raw_settings", {})
            self.control_panel_on_right = loaded_data.get("control_panel_on_right", False)
            self.show_grid_filenames = loaded_data.get("show_grid_filenames", False)
            self.viewport_move_speed = loaded_data.get("viewport_move_speed", 5)
            self.mouse_wheel_action = loaded_data.get("mouse_wheel_action", "photo_navigation")
            self.mouse_wheel_sensitivity = loaded_data.get("mouse_wheel_sensitivity", 1)
            self.mouse_pan_sensitivity = loaded_data.get("mouse_pan_sensitivity", 1.5)
            self.saved_sessions = loaded_data.get("saved_sessions", {})
            self.image_rotations = loaded_data.get("image_rotations", {})
            default_extensions = {'.jpg', '.jpeg'}
            loaded_extensions = loaded_data.get("supported_image_extensions", list(default_extensions))
            self.supported_image_extensions = set(loaded_extensions)
            if hasattr(self, 'ext_checkboxes'):
                extension_groups = {"JPG": ['.jpg', '.jpeg'], "PNG": ['.png'], "WebP": ['.webp'], "HEIC": ['.heic', '.heif'], "BMP": ['.bmp'], "TIFF": ['.tif', '.tiff']}
                for name, checkbox in self.ext_checkboxes.items():
                    is_checked = any(ext in self.supported_image_extensions for ext in extension_groups[name])
                    checkbox.blockSignals(True)
                    checkbox.setChecked(is_checked)
                    checkbox.blockSignals(False)
            self.folder_count = loaded_data.get("folder_count", 3)
            loaded_folders = loaded_data.get("target_folders", [])
            self.target_folders = (loaded_folders + [""] * self.folder_count)[:self.folder_count]
            self.move_raw_files = loaded_data.get("move_raw_files", True)
            self.zoom_mode = loaded_data.get("zoom_mode", "Fit")
            self.zoom_spin_value = loaded_data.get("zoom_spin_value", 2.0)
            
            # previous_grid_mode가 None일 경우 안전한 기본값('2x2')을 사용합니다.
            self.previous_grid_mode = loaded_data.get("previous_grid_mode") or "2x2"
            self.last_active_grid_mode = self.previous_grid_mode
            
            self._pending_view_state = {
                "current_image_index": loaded_data.get("current_image_index", -1),
                "grid_mode": loaded_data.get("grid_mode", "Off"),
                "compare_mode_active": loaded_data.get("compare_mode_active", False),
                "zoom_mode": loaded_data.get("zoom_mode", "Fit"),
                "current_grid_index": loaded_data.get("current_grid_index", 0),
                "grid_page_start_index": loaded_data.get("grid_page_start_index", 0),
                "image_B_path": loaded_data.get("image_B_path", ""),
            }        

            # 2. UI 컨트롤 업데이트
