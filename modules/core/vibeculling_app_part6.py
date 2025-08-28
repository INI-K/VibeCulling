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



                return (self.splitter.widget(0) != self.control_panel or
                        self.splitter.widget(1) != self.image_panel or
                        self.splitter.widget(2) != self.thumbnail_panel)
        except:
            return True  # 오류 발생 시 재구성

    def _reorganize_splitter_widgets(self, control_on_right):
        """스플리터 위젯 재구성 (항상 3패널 구조)"""
        # 모든 위젯을 스플리터에서 제거
        while self.splitter.count() > 0:
            widget = self.splitter.widget(0)
            if widget:
                widget.setParent(None)
        
        # 썸네일 패널은 항상 보이도록 설정
        self.thumbnail_panel.show()
        
        # 위젯을 올바른 순서로 다시 추가 (항상 3패널)
        if control_on_right:
            # [썸네일] [이미지] [컨트롤]
            self.splitter.addWidget(self.thumbnail_panel)
            self.splitter.addWidget(self.image_panel)
            self.splitter.addWidget(self.control_panel)
        else:
            # [컨트롤] [이미지] [썸네일]
            self.splitter.addWidget(self.control_panel)
            self.splitter.addWidget(self.image_panel)
            self.splitter.addWidget(self.thumbnail_panel)

    def resizeEvent(self, event):
            """창 크기 변경 이벤트 처리"""
            super().resizeEvent(event)
            self.adjust_layout()
            self.update_minimap_position()

            if hasattr(self, 'feedback_label') and self.feedback_label.isVisible():
                # self.image_panel이 유효한지 확인
                if hasattr(self, 'image_panel') and self.image_panel:
                    panel_rect = self.image_panel.rect()
                    label_size = self.feedback_label.size()
                    self.feedback_label.move(
                        (panel_rect.width() - label_size.width()) // 2,
                        (panel_rect.height() - label_size.height()) // 2
                    )
            
            # 비교 모드 닫기 버튼 위치 업데이트
            if self.compare_mode_active and self.close_compare_button.isVisible():
                padding = 10
                btn_size = self.close_compare_button.width()
                # B 캔버스(scroll_area_B)의 우측 상단에 위치
                new_x = self.scroll_area_B.width() - btn_size - padding
                new_y = padding
                self.close_compare_button.move(new_x, new_y)
    
    def load_jpg_folder(self):
        """JPG 등 이미지 파일이 있는 폴더 선택 및 백그라운드 로드 시작"""
        folder_path = QFileDialog.getExistingDirectory(
            self, LanguageManager.translate("이미지 파일이 있는 폴더 선택"), "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder_path:
            logging.info(f"이미지(JPG) 폴더 선택: {folder_path}")
            self.clear_raw_folder()
            self.start_background_loading(
                mode='jpg_only',
                jpg_folder_path=folder_path, 
                raw_folder_path=None, 
                raw_file_list=None
            )

    def on_match_raw_button_clicked(self):
        """ "JPG - RAW 연결" 또는 "RAW 불러오기" 버튼 클릭 시 호출 """
        if self.is_raw_only_mode:
            # 현재 RAW 모드이면 이 버튼은 동작하지 않아야 하지만, 안전 차원에서 추가
            print("RAW 전용 모드에서는 이 버튼이 비활성화되어야 합니다.")
            return
        elif self.image_files: # JPG가 로드된 상태 -> 기존 RAW 연결 로직
            self.load_raw_folder()
        else: # JPG가 로드되지 않은 상태 -> RAW 단독 로드 로직
            self.load_raw_only_folder()


    def get_datetime_from_file_fast(self, file_path):
        """파일에서 촬영 시간을 빠르게 추출 (캐시 우선 사용)"""
        file_key = str(file_path)
        
        # 1. 캐시에서 먼저 확인
        if file_key in self.exif_cache:
            cached_data = self.exif_cache[file_key]
            if 'exif_datetime' in cached_data:
                cached_value = cached_data['exif_datetime']
                # 캐시된 값이 문자열이면 datetime 객체로 변환
                if isinstance(cached_value, str):
                    try:
                        return datetime.strptime(cached_value, '%Y:%m:%d %H:%M:%S')
                    except:
                        pass
                elif isinstance(cached_value, datetime):
                    return cached_value
        
        # 2. RAW 파일의 경우 rawpy로 빠른 메타데이터 추출
        if file_path.suffix.lower() in self.raw_extensions:
            try:
                import rawpy
                with rawpy.imread(str(file_path)) as raw:
                    # rawpy는 exiftool보다 훨씬 빠름
                    if hasattr(raw, 'metadata') and 'DateTimeOriginal' in raw.metadata:
                        datetime_str = raw.metadata['DateTimeOriginal']
                        return datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
            except:
                pass
        
        # 3. JPG/HEIC의 경우 piexif 사용 (이미 구현됨)
        try:
            import piexif
            exif_data = piexif.load(str(file_path))
            if piexif.ExifIFD.DateTimeOriginal in exif_data['Exif']:
                datetime_str = exif_data['Exif'][piexif.ExifIFD.DateTimeOriginal].decode()
                return datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
        except:
            pass
        
        # 4. 마지막 수단: 파일 수정 시간
        return datetime.fromtimestamp(file_path.stat().st_mtime)

    def load_images_from_folder(self, folder_path):
        """
        폴더에서 이미지 로드를 시작하는 통합 트리거 함수.
        실제 로딩은 백그라운드에서 수행됩니다.
        """
        if not folder_path:
            return False
        
        self.start_background_loading(
            mode='jpg_with_raw',
            jpg_folder_path=folder_path, 
            raw_folder_path=self.raw_folder, 
            raw_file_list=None
        )
        return True

    
    def start_background_loading(self, mode, jpg_folder_path, raw_folder_path, raw_file_list=None):
        """백그라운드 로딩을 시작하고 로딩창을 표시합니다."""
        if not self._is_silent_load:
            self._reset_workspace()

        self.loading_progress_dialog = QProgressDialog(
            LanguageManager.translate("폴더를 읽는 중입니다..."),
            "", 0, 0, self
        )
        self.loading_progress_dialog.setCancelButton(None)
        self.loading_progress_dialog.setWindowModality(Qt.WindowModal)
        self.loading_progress_dialog.setMinimumDuration(0)
        apply_dark_title_bar(self.loading_progress_dialog)
        self.loading_progress_dialog.setStyleSheet(f"""
            QProgressDialog {{
                background-color: {ThemeManager.get_color('bg_primary')};
                color: {ThemeManager.get_color('text')};
            }}
            QProgressBar {{
                text-align: center;
            }}
        """)
        
        # 대화상자를 메인 윈도우 중앙에 위치시키는 로직
        parent_geometry = self.geometry()
        self.loading_progress_dialog.adjustSize()
        dialog_size = self.loading_progress_dialog.size()
        new_x = parent_geometry.x() + (parent_geometry.width() - dialog_size.width()) // 2
        new_y = parent_geometry.y() + (parent_geometry.height() - dialog_size.height()) // 2
        self.loading_progress_dialog.move(new_x, new_y)

        self.loading_progress_dialog.show()
        # 이 방식은 복잡한 Python 타입을 더 안정적으로 처리합니다.
        jpg_path_str = jpg_folder_path if jpg_folder_path is not None else ""
        raw_path_str = raw_folder_path if raw_folder_path is not None else ""
        current_supported_extensions = list(self.supported_image_extensions)
        self.folder_loader_worker.startProcessing.emit(
            jpg_path_str,
            raw_path_str,
            mode,
            raw_file_list if raw_file_list is not None else [],
            current_supported_extensions
        )

    def force_grid_refresh(self):
        """그리드 뷰를 강제로 리프레시"""
        if self.grid_mode != "Off":
            # 이미지 로더의 활성 작업 취소
            for future in self.image_loader.active_futures:
                future.cancel()
            self.image_loader.active_futures.clear()
            
            # 페이지 다시 로드 요청
            cells_per_page = 4 if self.grid_mode == "2x2" else 9
            self.image_loader.preload_page(self.image_files, self.grid_page_start_index, cells_per_page)
            
            # 그리드 UI 업데이트
            self.update_grid_view()    

    def load_image_with_orientation(self, file_path):
        """EXIF 방향 정보를 고려하여 이미지를 올바른 방향으로 로드 (캐시 활용)"""
        return self.image_loader.load_image_with_orientation(file_path)

    def _apply_zoom_to_canvas(self, canvas_id):
        """지정된 캔버스(A 또는 B)에 현재 줌 모드와 뷰포트를 적용합니다."""
        # 1. canvas_id에 따라 사용할 위젯과 데이터 소스를 결정합니다.
        if canvas_id == 'A':
            scroll_area = self.scroll_area
            image_label = self.image_label
            image_container = self.image_container
            original_pixmap = self.original_pixmap
            image_path = self.get_current_image_path()
        elif canvas_id == 'B':
            scroll_area = self.scroll_area_B
            image_label = self.image_label_B
            image_container = self.image_container_B
            original_pixmap = self.original_pixmap_B
            image_path = str(self.image_B_path) if self.image_B_path else None
        else:
            return

        # 2. 원본 이미지가 없으면 캔버스를 비우고 종료합니다.
        if not original_pixmap or original_pixmap.isNull():
            image_label.clear()
            image_label.setText(LanguageManager.translate("비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다.") if canvas_id == 'B' else "")
            return
            
        # 회전 적용 로직 추가
        pixmap_to_display = original_pixmap
        if image_path and image_path in self.image_rotations:
            angle = self.image_rotations[image_path]
            if angle != 0:
                transform = QTransform().rotate(angle)
                pixmap_to_display = original_pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # 3. 기존 apply_zoom_to_image의 로직을 그대로 가져와서,
        #    self.xxx 대신 지역 변수(scroll_area, image_label 등)를 사용하도록 수정합니다.
        view_width = scroll_area.width()
        view_height = scroll_area.height()
        img_width_orig = pixmap_to_display.width()
        img_height_orig = pixmap_to_display.height()
        
        # Fit 모드 처리
        if self.zoom_mode == "Fit":
            scaled_pixmap = self.high_quality_resize_to_fit(pixmap_to_display, scroll_area)
            image_label.setPixmap(scaled_pixmap)
            image_label.setGeometry(
                (view_width - scaled_pixmap.width()) // 2, (view_height - scaled_pixmap.height()) // 2,
                scaled_pixmap.width(), scaled_pixmap.height()
            )
            image_container.setMinimumSize(1, 1)
            return # Fit 모드는 여기서 종료

        # Zoom 100% 또는 Spin 모드 처리
        if self.zoom_mode == "100%":
            new_zoom_factor = 1.0
        elif self.zoom_mode == "Spin":
            new_zoom_factor = self.zoom_spin_value
        else:
            return
            
        new_zoomed_width = img_width_orig * new_zoom_factor
        new_zoomed_height = img_height_orig * new_zoom_factor

        # B 캔버스는 항상 A 캔버스의 뷰포트를 따라가므로, 뷰포트 계산은 A 캔버스에서만 수행합니다.
        if canvas_id == 'A':
            final_target_rel_center = QPointF(0.5, 0.5)
            trigger = self.zoom_change_trigger
            image_orientation_type = self.current_image_orientation
            if trigger == "double_click":
                scaled_fit_pixmap = self.high_quality_resize_to_fit(original_pixmap, scroll_area)
                fit_img_rect = QRect((view_width - scaled_fit_pixmap.width()) // 2, (view_height - scaled_fit_pixmap.height()) // 2, scaled_fit_pixmap.width(), scaled_fit_pixmap.height())
                if fit_img_rect.width() > 0 and fit_img_rect.height() > 0:
                    rel_x = (self.double_click_pos.x() - fit_img_rect.x()) / fit_img_rect.width()
                    rel_y = (self.double_click_pos.y() - fit_img_rect.y()) / fit_img_rect.height()
                    final_target_rel_center = QPointF(max(0.0, min(1.0, rel_x)), max(0.0, min(1.0, rel_y)))
                self.current_active_rel_center = final_target_rel_center
                self.current_active_zoom_level = "100%"
                self._save_orientation_viewport_focus(image_orientation_type, self.current_active_rel_center, "100%")
            elif trigger in ["space_key_to_zoom", "radio_button", "photo_change_carry_over_focus", "photo_change_central_focus"]:
                 final_target_rel_center = self.current_active_rel_center
                 self._save_orientation_viewport_focus(image_orientation_type, final_target_rel_center, self.current_active_zoom_level)
            else:
                final_target_rel_center, new_active_zoom = self._get_orientation_viewport_focus(image_orientation_type, self.zoom_mode)
                self.current_active_rel_center = final_target_rel_center
                self.current_active_zoom_level = new_active_zoom
                self._save_orientation_viewport_focus(image_orientation_type, self.current_active_rel_center, self.current_active_zoom_level)

            target_abs_x = final_target_rel_center.x() * new_zoomed_width
            target_abs_y = final_target_rel_center.y() * new_zoomed_height
            new_x = view_width / 2 - target_abs_x
            new_y = view_height / 2 - target_abs_y
            
            if new_zoomed_width <= view_width: new_x = (view_width - new_zoomed_width) // 2
            else: new_x = min(0, max(view_width - new_zoomed_width, new_x))
            if new_zoomed_height <= view_height: new_y = (view_height - new_zoomed_height) // 2
            else: new_y = min(0, max(view_height - new_zoomed_height, new_y))

            # 계산된 위치를 image_label에 적용
            if self.zoom_mode == "100%":
                image_label.setPixmap(pixmap_to_display)
            else: # Spin 모드
                scaled_pixmap = pixmap_to_display.scaled(
                    int(new_zoomed_width), int(new_zoomed_height), 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                image_label.setPixmap(scaled_pixmap)
            image_label.setGeometry(int(new_x), int(new_y), int(new_zoomed_width), int(new_zoomed_height))
            image_container.setMinimumSize(int(new_zoomed_width), int(new_zoomed_height))
            self.zoom_change_trigger = None
        
        # B 캔버스는 A 캔버스와 동일한 줌/패닝을 적용받습니다.
        elif canvas_id == 'B':
            # B 캔버스에 동일한 줌 레벨의 Pixmap을 설정합니다.
            if self.zoom_mode == "100%":
                image_label.setPixmap(pixmap_to_display)
            else: # Spin 모드
                scaled_pixmap = pixmap_to_display.scaled(
                    int(new_zoomed_width), int(new_zoomed_height), 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                image_label.setPixmap(scaled_pixmap)
            
            # B 캔버스의 크기만 설정합니다. 위치(position)는 설정하지 않습니다.
            image_label.resize(int(new_zoomed_width), int(new_zoomed_height))
            image_container.setMinimumSize(int(new_zoomed_width), int(new_zoomed_height))


    def apply_zoom_to_image(self):
        """A 캔버스에 줌을 적용하고, 비교 모드이면 B 캔버스도 동기화하는 래퍼 함수."""
        if self._is_reorganizing_layout:
            return
        if self.grid_mode != "Off": return

        # 1. A 캔버스의 내용물(크기, 이미지)과 위치를 먼저 업데이트합니다.
        self._apply_zoom_to_canvas('A')
        
        # 2. B 캔버스의 내용물(크기, 이미지)만 업데이트합니다. (위치는 아직 동기화 전)
        if self.compare_mode_active:
            self._apply_zoom_to_canvas('B')
        
        def finalize_sync():
            """A 캔버스의 모든 UI(스크롤바 포함)가 안정된 후 B 캔버스를 동기화합니다."""
            if self.compare_mode_active:
                self._sync_viewports()
            # 미니맵은 항상 마지막에 업데이트합니다.
            if self.minimap_toggle.isChecked():
                self.toggle_minimap(True)

        # QTimer.singleShot(0, ...)은 현재 모든 이벤트 처리가 끝나고 UI가 완전히
        # 안정된 후에 finalize_sync 함수를 호출하도록 보장합니다.
        # 이것이 줌 값이 작아질 때 발생하는 스크롤바 업데이트 지연 문제를 해결합니다.
        QTimer.singleShot(0, finalize_sync)




    def rotate_image(self, canvas_id, direction):
        """지정된 캔버스의 이미지를 회전시키고 즉시 뷰와 썸네일을 업데이트합니다."""
        image_path = None
        current_index_in_list = -1 # 회전된 이미지의 전역 인덱스 저장용

        if canvas_id == 'A':
            # Grid Off 모드와 Grid 모드 모두에서 현재 활성화된 이미지 경로를 가져옴
            if self.grid_mode == "Off":
                image_path = self.get_current_image_path()
                current_index_in_list = self.current_image_index
            else: # Grid 모드
                primary_index = self.primary_selected_index
                if 0 <= primary_index < len(self.image_files):
                    image_path = str(self.image_files[primary_index])
                    current_index_in_list = primary_index
        elif canvas_id == 'B':
            image_path = str(self.image_B_path) if self.image_B_path else None
            if image_path:
                try:
                    current_index_in_list = self.image_files.index(Path(image_path))
                except ValueError:
                    current_index_in_list = -1 # B 캔버스 이미지는 목록에 없을 수도 있음

        if not image_path:
            return

        current_angle = self.image_rotations.get(image_path, 0)

        if direction == 'ccw':
            new_angle = (current_angle - 90) % 360
        else:
            new_angle = (current_angle + 90) % 360
        
        if new_angle == -270: new_angle = 90
        if new_angle == -180: new_angle = 180
        if new_angle == -90: new_angle = 270

        self.image_rotations[image_path] = new_angle
        logging.info(f"이미지 회전: {Path(image_path).name} -> {new_angle}°")

        self.fit_pixmap_cache.clear()

        # 회전된 썸네일을 즉시 다시 생성하도록 요청
        thumbnail_size = UIScaleManager.get("thumbnail_image_size")
        future = self.resource_manager.submit_imaging_task_with_priority(
            'high',
            self._generate_thumbnail_task,
            image_path,
            thumbnail_size,
            new_angle
        )
        if future:
            future.add_done_callback(
                lambda f, path=image_path: self._on_thumbnail_generated(f, path)
            )
        
        if self.grid_mode != "Off" and canvas_id == 'A' and 0 <= current_index_in_list < len(self.image_files):
            # 회전된 이미지가 현재 그리드 페이지에 있는지 확인
            if self.grid_page_start_index <= current_index_in_list < self.grid_page_start_index + len(self.grid_labels):
                grid_cell_index = current_index_in_list - self.grid_page_start_index
                cell_widget = self.grid_labels[grid_cell_index]
                
                # 원본 참조가 있는지 확인하고 회전 적용
                original_pixmap_ref = cell_widget.property("original_pixmap_ref")
                if original_pixmap_ref and isinstance(original_pixmap_ref, QPixmap):
                    transform = QTransform().rotate(new_angle)
                    rotated_pixmap = original_pixmap_ref.transformed(transform, Qt.SmoothTransformation)
                    cell_widget.setPixmap(rotated_pixmap) # 즉시 갱신
        
        # 메인 뷰 업데이트 (Grid Off 또는 Compare 모드일 때만 의미 있음)
        self.apply_zoom_to_image()

    def high_quality_resize_to_fit(self, pixmap, target_widget):
            """고품질 이미지 리사이징 (Fit 모드용) - 메모리 최적화"""
            if not pixmap or not target_widget:
                return pixmap
                
            # 이미지 패널 크기 가져오기
            panel_width = target_widget.width()
            panel_height = target_widget.height()

            if panel_width <= 0 or panel_height <= 0:
                return pixmap
                
            # 크기가 같다면 캐시 확인 (캐시 키는 이제 튜플 (너비, 높이) 사용)
            current_size = (panel_width, panel_height)
            # Fit 캐시는 A 패널 전용으로 유지하는 것이 간단합니다. B는 A의 결과를 따르기 때문입니다.
            if target_widget is self.scroll_area and self.last_fit_size == current_size and current_size in self.fit_pixmap_cache:
                return self.fit_pixmap_cache[current_size]
                
            # 이미지 크기
            img_width = pixmap.width()
            img_height = pixmap.height()
            
            # 이미지가 패널보다 크면 Qt의 네이티브 하드웨어 가속 렌더링을 사용한 리사이징
            if img_width > panel_width or img_height > panel_height:
                # 비율 계산
                ratio_w = panel_width / img_width
                ratio_h = panel_height / img_height
                ratio = min(ratio_w, ratio_h)
                # 새 크기 계산
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                
                # 메모리 사용량 확인 (가능한 경우)
                large_image_threshold = 20000000  # 약 20MB (원본 크기가 큰 이미지)
                estimated_size = new_width * new_height * 4  # 4 바이트/픽셀 (RGBA)
                
                if img_width * img_height > large_image_threshold:
                    # 대형 이미지는 메모리 최적화를 위해 단계적 축소
                    try:
                        # 단계적으로 줄이는 방법 (품질 유지하면서 메모리 사용량 감소)
                        if ratio < 0.3:  # 크게 축소해야 하는 경우
                            # 중간 크기로 먼저 축소
                            temp_ratio = ratio * 2 if ratio * 2 < 0.8 else 0.8
                            temp_width = int(img_width * temp_ratio)
                            temp_height = int(img_height * temp_ratio)
                            # 중간 크기로 먼저 변환
                            temp_pixmap = pixmap.scaled(
                                temp_width, 
                                temp_height,
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation
                            )
                            # 최종 크기로 변환
                            result_pixmap = temp_pixmap.scaled(
                                new_width,
                                new_height,
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation
                            )
                            # 중간 결과 명시적 해제
                            temp_pixmap = None
                        else:
                            # 한 번에 최종 크기로 변환
                            result_pixmap = pixmap.scaled(
                                new_width,
                                new_height,
                                Qt.KeepAspectRatio, 
                                Qt.SmoothTransformation
                            )
                    except:
                        # 오류 발생 시 기본 방식으로 축소
                        result_pixmap = pixmap.scaled(
                            new_width,
                            new_height,
                            Qt.KeepAspectRatio, 
                            Qt.FastTransformation  # 메모리 부족 시 빠른 변환 사용
                        )
                else:
                    # 일반 크기 이미지는 고품질 변환 사용
                    result_pixmap = pixmap.scaled(
                        new_width, 
                        new_height, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                # 캐시 업데이트 (A 패널에 대해서만)
                if target_widget is self.scroll_area:
                    self.fit_pixmap_cache[current_size] = result_pixmap
                    self.last_fit_size = current_size
                return result_pixmap
                
            # 이미지가 패널보다 작으면 원본 사용
            return pixmap
    
    def image_mouse_press_event(self, event):
        """이미지 영역 마우스 클릭 이벤트 처리"""
        # === 우클릭 컨텍스트 메뉴 처리 ===
        if event.button() == Qt.RightButton and self.image_files:
            # 이미지가 로드된 상태에서 우클릭 시 컨텍스트 메뉴 표시
            context_menu = self.create_context_menu(event.position().toPoint())
            if context_menu:
                context_menu.exec(self.image_container.mapToGlobal(event.position().toPoint()))
            return
        
        # === 빈 캔버스 클릭 시 폴더 선택 기능 ===
        if event.button() == Qt.LeftButton and not self.image_files:
            # 아무 이미지도 로드되지 않은 상태에서 캔버스 클릭 시 폴더 선택
            self.open_folder_dialog_for_canvas()
            return
        
        # === Fit 모드에서 드래그 앤 드롭 시작 준비 ===
        if (event.button() == Qt.LeftButton and 
            self.zoom_mode == "Fit" and 
            self.image_files and 
            0 <= self.current_image_index < len(self.image_files)):
            
            # 드래그 시작 준비
            self.drag_start_pos = event.position().toPoint()
            self.is_potential_drag = True
            logging.debug(f"드래그 시작 준비: {self.drag_start_pos}")
            return
        
        # === 기존 패닝 기능 ===
        # 100% 또는 Spin 모드에서만 패닝 활성화
        if self.zoom_mode in ["100%", "Spin"]:
            if event.button() == Qt.LeftButton:
                # 패닝 상태 활성화
                self.panning = True
                self.pan_last_mouse_pos = event.position()
                self.image_start_pos = self.image_label.pos()
                self.setCursor(Qt.ClosedHandCursor)
    
    def open_folder_dialog_for_canvas(self):
        """캔버스 클릭 시 폴더 선택 다이얼로그 열기"""
        try:
            folder_path = QFileDialog.getExistingDirectory(
                self, 
                LanguageManager.translate("이미지 파일이 있는 폴더 선택"), 
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if folder_path:
                # 선택된 폴더에 대해 캔버스 폴더 드롭 로직 적용
                success = self._handle_canvas_folder_drop(folder_path)
                if success:
                    logging.info(f"캔버스 클릭으로 폴더 로드 성공: {folder_path}")
                else:
                    logging.warning(f"캔버스 클릭으로 폴더 로드 실패: {folder_path}")
            else:
                logging.debug("캔버스 클릭 폴더 선택 취소됨")
                
        except Exception as e:
            logging.error(f"캔버스 클릭 폴더 선택 오류: {e}")
            self.show_themed_message_box(
                QMessageBox.Critical,
                LanguageManager.translate("오류"),
                LanguageManager.translate("폴더 선택 중 오류가 발생했습니다.")
            )
    
    def start_image_drag(self, dragged_grid_index=None, canvas=None):
        """이미지 드래그 시작 (A, B 캔버스 및 그리드 지원)"""
        try:
            if not self.image_files:
                logging.warning("드래그 시작 실패: 유효한 이미지가 없음")
                return

            drag_image_path = None
            mime_text_payload = ""
            drag_pixmap_source = None

            if self.grid_mode != "Off":
                # Grid 모드에서 드래그 시작
                drag_image_index = -1
                if dragged_grid_index is not None:
                    drag_image_index = self.grid_page_start_index + dragged_grid_index
                else: # Fallback
                    drag_image_index = self.grid_page_start_index + self.current_grid_index
                
                if not (0 <= drag_image_index < len(self.image_files)):
                    logging.warning("드래그 시작 실패: 유효하지 않은 그리드 인덱스")
                    return
                
                drag_image_path = self.image_files[drag_image_index]
                drag_pixmap_source = self.image_loader.cache.get(str(drag_image_path))

                # 다중 선택 여부 확인
                if (hasattr(self, 'selected_grid_indices') and self.selected_grid_indices and 
                    len(self.selected_grid_indices) > 1 and 
                    (dragged_grid_index in self.selected_grid_indices)):
                    # 다중 선택된 이미지를 드래그하는 경우
                    selected_global_indices = sorted([self.grid_page_start_index + i for i in self.selected_grid_indices])
                    indices_str = ",".join(map(str, selected_global_indices))
                    mime_text_payload = f"image_drag:grid:{indices_str}"
                    logging.info(f"다중 이미지 드래그 시작: {len(selected_global_indices)}개 이미지")
                else:
                    # 단일 이미지 드래그
                    mime_text_payload = f"image_drag:grid:{drag_image_index}"

            else: # Grid Off 모드 (Canvas A)
                if not (0 <= self.current_image_index < len(self.image_files)):
                    return
                drag_image_path = self.image_files[self.current_image_index]
                drag_pixmap_source = self.original_pixmap

                mode_context = "compareA" if self.compare_mode_active else "gridOff"
                mime_text_payload = f"image_drag:{mode_context}:{self.current_image_index}"

            if not drag_image_path or not mime_text_payload:
                logging.warning("드래그할 이미지를 결정할 수 없습니다.")
                return

            # 2. QDrag 객체 생성 및 데이터 설정
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(mime_text_payload)
            drag.setMimeData(mime_data)
            
            # 3. 드래그 커서 이미지 설정
            if drag_pixmap_source and not drag_pixmap_source.isNull():
                thumbnail = drag_pixmap_source.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                drag.setPixmap(thumbnail)
                drag.setHotSpot(QPoint(32, 32))

            logging.info(f"이미지 드래그 시작: {drag_image_path.name} (from: {mime_text_payload})")
            
            # 4. 드래그 실행
            drag.exec(Qt.MoveAction)
            
        except Exception as e:
            logging.error(f"이미지 드래그 시작 오류: {e}")

    def image_mouse_move_event(self, event):
        """이미지 영역 마우스 이동 이벤트 처리 (상대 위치 방식으로 개선)"""
        # === Fit 모드에서 드래그 시작 감지 (기존 코드 유지) ===
        if (self.is_potential_drag and 
            self.zoom_mode == "Fit" and 
            self.image_files and 
            0 <= self.current_image_index < len(self.image_files)):
            current_pos = event.position().toPoint()
            move_distance = (current_pos - self.drag_start_pos).manhattanLength()
            if move_distance > self.drag_threshold:
                self.start_image_drag()
                self.is_potential_drag = False
                return

        # === 부드러운 패닝 로직 (상대 위치 방식) ===
        if not self.panning or not self.original_pixmap:
            return

        # 1. 이벤트 스로틀링 (기존과 동일)
        current_time = int(time.time() * 1000)
        if current_time - self.last_event_time < 8:  # ~125fps 제한
            return
        self.last_event_time = current_time

        # 2. 이전 마우스 위치로부터의 변화량(delta) 계산
        current_mouse_pos = event.position() # QPointF
        delta = current_mouse_pos - self.pan_last_mouse_pos

        scaled_delta = delta * self.mouse_pan_sensitivity

        # 3. 이미지의 현재 위치에 변화량을 더해 새 위치 계산
        current_image_pos = self.image_label.pos()
        new_pos = QPointF(current_image_pos) + scaled_delta

        # 4. 패닝 범위 제한 (기존 로직 재사용)
        if self.zoom_mode == "100%":
            zoom_factor = 1.0
        else: # Spin 모드
            zoom_factor = self.zoom_spin_value
        
        img_width = self.original_pixmap.width() * zoom_factor
        img_height = self.original_pixmap.height() * zoom_factor
        view_width = self.scroll_area.width()
        view_height = self.scroll_area.height()

        x_min = min(0, view_width - img_width) if img_width > view_width else (view_width - img_width) / 2
        x_max = 0 if img_width > view_width else x_min
        y_min = min(0, view_height - img_height) if img_height > view_height else (view_height - img_height) / 2
        y_max = 0 if img_height > view_height else y_min
        
        final_x = max(x_min, min(x_max, new_pos.x()))
        final_y = max(y_min, min(y_max, new_pos.y()))

        # 5. 이미지 위치 업데이트
        self.image_label.move(int(final_x), int(final_y))
        self._sync_viewports()

        # 6. 다음 이벤트를 위해 현재 마우스 위치를 '마지막 위치'로 업데이트
        self.pan_last_mouse_pos = current_mouse_pos
        
        # 7. 미니맵 업데이트 (기존과 동일)
        if current_time - getattr(self, 'last_minimap_update_time', 0) > 50:
            self.last_minimap_update_time = current_time
            if self.minimap_visible and self.minimap_widget.isVisible():
                self.update_minimap()
    
    def image_mouse_release_event(self, event: QMouseEvent): # QMouseEvent 타입 명시
        # === 드래그 상태 초기화 ===
        if self.is_potential_drag:
            self.is_potential_drag = False
            logging.debug("드래그 시작 준비 상태 해제")
        
        # === 기존 패닝 기능 ===
        if event.button() == Qt.LeftButton and self.panning:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            
            if self.grid_mode == "Off" and self.zoom_mode in ["100%", "Spin"] and \
               self.original_pixmap and 0 <= self.current_image_index < len(self.image_files):
                current_rel_center = self._get_current_view_relative_center() # 현재 뷰 중심 계산
                current_zoom_level = self.zoom_mode
                
                # 현재 활성 포커스도 업데이트
                self.current_active_rel_center = current_rel_center
                self.current_active_zoom_level = current_zoom_level
                
                # 방향별 포커스 저장 (파일 경로가 아닌 orientation 전달)
                self._save_orientation_viewport_focus(self.current_image_orientation, current_rel_center, current_zoom_level)
            
            if self.minimap_visible and self.minimap_widget.isVisible():
                self.update_minimap()

        self.activateWindow()
        self.setFocus()
    
    def create_context_menu(self, mouse_pos):
        """컨텍스트 메뉴 생성 - folder_count에 따라 동적 생성"""
        # 이미지가 없거나 폴더가 없으면 메뉴 표시 안 함
        if not self.image_files or not self.target_folders:
            return None
            
        # 컨텍스트 메뉴 생성
        context_menu = QMenu(self)
        
        # 테마 스타일 적용
        context_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')};
                padding: 2px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: {ThemeManager.get_color('accent')};
                color: {ThemeManager.get_color('text')};
            }}
        """)
        
        # folder_count에 따라 메뉴 항목 생성
        for i in range(self.folder_count):
            # 폴더가 설정되지 않았으면 비활성화
            folder_path = self.target_folders[i] if i < len(self.target_folders) else ""
            
            # 메뉴 항목 텍스트 생성 - 실제 폴더 이름 포함
            if folder_path and os.path.isdir(folder_path):
                folder_name = Path(folder_path).name
                menu_text = LanguageManager.translate("이동 - 폴더 {0} [{1}]").format(i + 1, folder_name)
            else:
                # 폴더가 설정되지 않았거나 유효하지 않은 경우 기존 형식 사용
                menu_text = LanguageManager.translate("이동 - 폴더 {0}").format(i + 1)
            
            # 메뉴 액션 생성
            action = QAction(menu_text, self)
            action.triggered.connect(lambda checked, idx=i: self.move_to_folder_from_context(idx))
            
            # 폴더가 설정되지 않았거나 유효하지 않으면 비활성화
            if not folder_path or not os.path.isdir(folder_path):
                action.setEnabled(False)
            
            context_menu.addAction(action)
        
        context_menu.addSeparator()

        rotate_ccw_action = QAction(LanguageManager.translate("반시계 방향으로 회전"), self)
        rotate_ccw_action.triggered.connect(lambda: self.rotate_image('A', 'ccw'))
        context_menu.addAction(rotate_ccw_action)

        rotate_cw_action = QAction(LanguageManager.translate("시계 방향으로 회전"), self)
        rotate_cw_action.triggered.connect(lambda: self.rotate_image('A', 'cw'))
        context_menu.addAction(rotate_cw_action)

        return context_menu

    
    def move_to_folder_from_context(self, folder_index):
        """컨텍스트 메뉴에서 폴더 이동 처리"""
        if self.grid_mode == "Off":
            # Grid Off 모드: 현재 이미지 이동
            if 0 <= self.current_image_index < len(self.image_files):
                logging.info(f"컨텍스트 메뉴에서 이미지 이동 (Grid Off): 폴더 {folder_index + 1}")
                context = "CompareA" if self.compare_mode_active else "Off"
                self.move_current_image_to_folder(folder_index, context_mode=context)
        else:
            # Grid On 모드: 선택된 이미지들 이동
            logging.info(f"컨텍스트 메뉴에서 이미지 이동 (Grid On): 폴더 {folder_index + 1}")
            self.move_grid_image(folder_index)

        self.activateWindow()
        self.setFocus()
    
    def open_folder_in_explorer(self, folder_path):
        """폴더 경로를 윈도우 탐색기에서 열기"""
        if not folder_path or folder_path == LanguageManager.translate("폴더를 선택하세요"):
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
    
    def load_raw_folder(self):
        """RAW 파일이 있는 폴더 선택 및 매칭 (JPG 로드 상태에서만 호출됨)"""
        # JPG 파일이 로드되었는지 확인 (이 함수는 JPG 로드 상태에서만 호출되어야 함)
        if not self.image_files or self.is_raw_only_mode:
             # is_raw_only_mode 체크 추가
            self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("경고"), LanguageManager.translate("먼저 JPG 파일을 불러와야 합니다."))
            return

        folder_path = QFileDialog.getExistingDirectory(
            self, LanguageManager.translate("RAW 파일이 있는 폴더 선택"), "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if folder_path:
            if self.match_raw_files(folder_path):
                self.save_state()

    def load_raw_only_folder(self):
        """ RAW 파일만 로드하는 기능, 첫 파일 분석 및 사용자 선택 요청 """
        folder_path = QFileDialog.getExistingDirectory(
            self, LanguageManager.translate("RAW 파일이 있는 폴더 선택"), "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if folder_path:
            target_path = Path(folder_path)
            temp_raw_file_list = []

            # RAW 파일 검색
            for ext in self.raw_extensions:
                temp_raw_file_list.extend(target_path.glob(f'*{ext}'))
                temp_raw_file_list.extend(target_path.glob(f'*{ext.upper()}')) # 대문자 확장자도 고려

            # 중복 제거 및 정렬
            unique_raw_files = sorted(list(set(temp_raw_file_list)))

            if not unique_raw_files:
                self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("경고"), LanguageManager.translate("선택한 폴더에 RAW 파일이 없습니다."))
                # UI 초기화 (기존 JPG 로드 실패와 유사하게)
                self.image_files = []
                self.current_image_index = -1
                self.image_label.clear()
                self.image_label.setStyleSheet("background-color: black;")
                self.setWindowTitle("VibeCulling")
                self.update_counters()
                self.update_file_info_display(None)
                # RAW 관련 UI 업데이트
                self.raw_folder = ""
                self.is_raw_only_mode = False # 실패 시 모드 해제
                self.update_raw_folder_ui_state() # raw_folder_path_label 포함
                self.update_match_raw_button_state() # 버튼 텍스트 원복
                # JPG 버튼 활성화
                self.load_button.setEnabled(True)
                if self.session_management_popup and self.session_management_popup.isVisible():
                    self.session_management_popup.update_all_button_states()                
                return
            
            # --- 1. 첫 번째 RAW 파일 분석 ---
            first_raw_file_path_obj = unique_raw_files[0]
            first_raw_file_path_str = str(first_raw_file_path_obj)
            logging.info(f"첫 번째 RAW 파일 분석 시작: {first_raw_file_path_obj.name}")

            is_raw_compatible = False
            camera_model_name = LanguageManager.translate("알 수 없는 카메라") # 기본값
            original_resolution_str = "-"
            preview_resolution_str = "-"
            
            # exiftool을 사용해야 할 수도 있으므로 미리 경로 확보
            exiftool_path = self.get_exiftool_path() # 기존 get_exiftool_path() 사용
            exiftool_available = Path(exiftool_path).exists() and Path(exiftool_path).is_file()


            # 1.1. {RAW 호환 여부} 및 {원본 해상도 (rawpy 시도)}, {카메라 모델명 (rawpy 시도)}
            rawpy_exif_data = {} # rawpy에서 얻은 부분적 EXIF 저장용
            try:
                with rawpy.imread(first_raw_file_path_str) as raw:
                    is_raw_compatible = True
                    original_width = raw.sizes.width # postprocess 후 크기 (raw_width는 센서 크기)
                    original_height = raw.sizes.height
                    if original_width > 0 and original_height > 0 :
                        original_resolution_str = f"{original_width}x{original_height}"
                    
                    if hasattr(raw, 'camera_manufacturer') and raw.camera_manufacturer and \
                    hasattr(raw, 'model') and raw.model:
                        camera_model_name = f"{raw.camera_manufacturer.strip()} {raw.model.strip()}"
                    elif hasattr(raw, 'model') and raw.model: # 모델명만 있는 경우
                        camera_model_name = raw.model.strip()
                    
                    # 임시로 rawpy에서 일부 EXIF 정보 추출 (카메라 모델 등)
                    rawpy_exif_data["exif_make"] = raw.camera_manufacturer.strip() if hasattr(raw, 'camera_manufacturer') and raw.camera_manufacturer else ""
                    rawpy_exif_data["exif_model"] = raw.model.strip() if hasattr(raw, 'model') and raw.model else ""

            except Exception as e_rawpy:
                is_raw_compatible = False # rawpy로 기본 정보 읽기 실패 시 호환 안됨으로 간주
                logging.warning(f"rawpy로 첫 파일({first_raw_file_path_obj.name}) 분석 중 오류 (호환 안됨 가능성): {e_rawpy}")

            # 1.2. {카메라 모델명 (ExifTool 시도 - rawpy 실패 시 또는 보강)} 및 {원본 해상도 (ExifTool 시도 - rawpy 실패 시)}
            if (not camera_model_name or camera_model_name == LanguageManager.translate("알 수 없는 카메라") or \
            not original_resolution_str or original_resolution_str == "-") and exiftool_available:
                logging.info(f"Exiftool로 추가 정보 추출 시도: {first_raw_file_path_obj.name}")
                try:
                    cmd = [exiftool_path, "-json", "-Model", "-ImageWidth", "-ImageHeight", "-Make", first_raw_file_path_str]
                    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, creationflags=creationflags)
                    if process.returncode == 0 and process.stdout:
                        exif_data_list = json.loads(process.stdout)
                        if exif_data_list and isinstance(exif_data_list, list):
                            exif_data = exif_data_list[0]
                            model = exif_data.get("Model")
                            make = exif_data.get("Make")
                            
                            if make and model and (not camera_model_name or camera_model_name == LanguageManager.translate("알 수 없는 카메라")):
                                camera_model_name = f"{make.strip()} {model.strip()}"
                            elif model and (not camera_model_name or camera_model_name == LanguageManager.translate("알 수 없는 카메라")):
                                camera_model_name = model.strip()
                            
                            # rawpy_exif_data 보강
                            if not rawpy_exif_data.get("exif_make") and make: rawpy_exif_data["exif_make"] = make.strip()
                            if not rawpy_exif_data.get("exif_model") and model: rawpy_exif_data["exif_model"] = model.strip()


                            if (not original_resolution_str or original_resolution_str == "-"): # is_raw_compatible이 False인 경우 등
                                width = exif_data.get("ImageWidth")
                                height = exif_data.get("ImageHeight")
                                if width and height and int(width) > 0 and int(height) > 0:
                                    original_resolution_str = f"{width}x{height}"
                except Exception as e_exiftool:
                    logging.error(f"Exiftool로 정보 추출 중 오류: {e_exiftool}")
            
            # 최종 카메라 모델명 결정 (rawpy_exif_data 우선, 없으면 camera_model_name 변수 사용)
            final_camera_model_display = ""
            if rawpy_exif_data.get("exif_make") and rawpy_exif_data.get("exif_model"):
                final_camera_model_display = format_camera_name(rawpy_exif_data["exif_make"], rawpy_exif_data["exif_model"])
            elif rawpy_exif_data.get("exif_model"):
                final_camera_model_display = rawpy_exif_data["exif_model"]
            elif camera_model_name and camera_model_name != LanguageManager.translate("알 수 없는 카메라"):
                final_camera_model_display = camera_model_name
            else:
                final_camera_model_display = LanguageManager.translate("알 수 없는 카메라")


            # 1.3. {미리보기 해상도} 추출
            # ImageLoader의 _load_raw_preview_with_orientation을 임시로 호출하여 미리보기 정보 얻기
            # (ImageLoader 인스턴스가 필요)
            preview_pixmap, preview_width, preview_height = self.image_loader._load_raw_preview_with_orientation(first_raw_file_path_str)
            if preview_pixmap and not preview_pixmap.isNull() and preview_width and preview_height:
                preview_resolution_str = f"{preview_width}x{preview_height}"
            else: # 미리보기 추출 실패 또는 정보 없음
