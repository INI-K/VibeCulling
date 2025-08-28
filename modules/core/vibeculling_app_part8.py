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



                    print(f"[{attempt+1}] PermissionError: {e}")
                    return None # 권한 오류 발생 시 None 반환
            except Exception as e:
                logging.error(f"파일 이동 실패: {source_path} -> {target_path}, 오류: {e}")
                return None # 이동 실패 시 None 반환

        # 대상 경로 생성
        target_path = target_dir / source_path.name

        # 이미 같은 이름의 파일이 있는지 확인
        if target_path.exists():
            # 파일명 중복 처리
            counter = 1
            while target_path.exists():
                # 새 파일명 형식: 원본파일명_1.확장자
                new_name = f"{source_path.stem}_{counter}{source_path.suffix}"
                target_path = target_dir / new_name
                counter += 1
            logging.info(f"파일명 중복 처리: {source_path.name} -> {target_path.name}")

        # 파일 이동
        try: #  파일 이동 시 오류 처리 추가
            shutil.move(str(source_path), str(target_path))
            logging.info(f"파일 이동: {source_path} -> {target_path}")
            return target_path # 이동 성공 시 최종 target_path 반환
        except Exception as e:
            logging.error(f"파일 이동 실패: {source_path} -> {target_path}, 오류: {e}")
            return None #  이동 실패 시 None 반환
    
    def setup_zoom_ui(self):
        """줌 UI 설정"""
        # 확대/축소 섹션 제목
        zoom_label = QLabel("Zoom")
        zoom_label.setAlignment(Qt.AlignCenter) # --- 가운데 정렬 추가 ---
        zoom_label.setStyleSheet(f"color: {ThemeManager.get_color('text')};")
        font = QFont(self.font()) # 현재 위젯(VibeCullingApp)의 폰트를 가져와서 복사
        # font.setBold(True) # 이 새 폰트 객체에만 볼드 적용
        font.setPointSize(UIScaleManager.get("zoom_grid_font_size")) # 이 새 폰트 객체에만 크기 적용
        zoom_label.setFont(font) # 수정된 새 폰트를 레이블에 적용
        self.control_layout.addWidget(zoom_label)
        self.control_layout.addSpacing(UIScaleManager.get("title_spacing"))

        # 확대 옵션 컨테이너 (가로 배치)
        zoom_container = QWidget()
        zoom_layout = QHBoxLayout(zoom_container)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(UIScaleManager.get("group_box_spacing"))
        
        # 라디오 버튼 생성
        self.fit_radio = QRadioButton("Fit")
        self.zoom_100_radio = QRadioButton("100%")
        self.zoom_spin_btn = QRadioButton()
        
        # 버튼 그룹에 추가
        self.zoom_group = QButtonGroup(self)
        self.zoom_group.addButton(self.fit_radio, 0)
        self.zoom_group.addButton(self.zoom_100_radio, 1)
        self.zoom_group.addButton(self.zoom_spin_btn, 2) # ID: 2 (기존 200 자리)

        # 동적 줌 SpinBox 설정
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(10, 500)
        self.zoom_spin.setValue(int(self.zoom_spin_value * 100)) # 2.0 -> 200
        self.zoom_spin.setSuffix("%")
        self.zoom_spin.setSingleStep(10)

        # 폰트 크기를 기반으로 너비를 동적으로 계산
        # 1. QSpinBox의 폰트 메트릭스 가져오기
        font_metrics = self.zoom_spin.fontMetrics()
        
        # 2. 표시될 가장 긴 텍스트("500%")의 너비 계산
        #    최대값(500)과 접미사("%")를 합친 문자열로 계산합니다.
        max_text = f"{self.zoom_spin.maximum()}{self.zoom_spin.suffix()}"
        text_width = font_metrics.horizontalAdvance(max_text)
        
        # 3. 화살표 버튼, 내부 여백(padding), 테두리 등을 위한 추가 공간 확보
        #    이 값은 OS나 스타일에 따라 다르므로 약간의 여유를 줍니다.
        extra_space = 40
        
        # 4. 최종 너비를 계산하여 고정 너비로 설정
        calculated_width = text_width + extra_space
        self.zoom_spin.setFixedWidth(calculated_width)

        self.zoom_spin.lineEdit().setReadOnly(True)
        self.zoom_spin.setContextMenuPolicy(Qt.NoContextMenu)
        self.zoom_spin.valueChanged.connect(self.on_zoom_spinbox_value_changed)
        self.zoom_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {ThemeManager.get_color('bg_primary')};
                color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')};
                border-radius: 1px;
                padding: {UIScaleManager.get("spinbox_padding")}px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {ThemeManager.get_color('bg_primary')};
                border: 1px solid {ThemeManager.get_color('border')};
                width: 16px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {ThemeManager.get_color('bg_secondary')};
            }}
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
        """)
        # 기본값: Fit
        self.fit_radio.setChecked(True)
        
        # 버튼 스타일 설정 (기존 코드 재사용)
        radio_style = ThemeManager.generate_radio_button_style()

        self.fit_radio.setStyleSheet(radio_style)
        self.zoom_100_radio.setStyleSheet(radio_style)
        self.zoom_spin_btn.setStyleSheet(radio_style)
        
        # 이벤트 연결
        self.zoom_group.buttonClicked.connect(self.on_zoom_changed)
        
        # 레이아웃에 위젯 추가 (가운데 정렬)
        zoom_layout.addStretch()
        zoom_layout.addWidget(self.fit_radio)
        zoom_layout.addWidget(self.zoom_100_radio)
        spin_widget_container = QWidget()
        spin_layout = QHBoxLayout(spin_widget_container)
        spin_layout.setContentsMargins(0,0,0,0)
        spin_layout.setSpacing(0) # 라디오 버튼과 스핀박스 사이 간격
        spin_layout.addWidget(self.zoom_spin_btn)
        spin_layout.addWidget(self.zoom_spin)

        zoom_layout.addWidget(spin_widget_container) # 묶인 위젯을 한 번에 추가
        zoom_layout.addStretch()
        
        self.control_layout.addWidget(zoom_container)
        
        # 미니맵 토글 체크박스 추가
        self.minimap_toggle = QCheckBox(LanguageManager.translate("미니맵"))
        self.minimap_toggle.setChecked(True)  # 기본값 체크(ON)
        self.minimap_toggle.toggled.connect(self.toggle_minimap)
        self.minimap_toggle.setStyleSheet(ThemeManager.generate_checkbox_style())
        
        # 미니맵 토글을 중앙에 배치
        minimap_container = QWidget()
        minimap_layout = QHBoxLayout(minimap_container)
        minimap_layout.setContentsMargins(0, 10, 0, 0)
        minimap_layout.addStretch()
        minimap_layout.addWidget(self.minimap_toggle)
        minimap_layout.addStretch()
        
        self.control_layout.addWidget(minimap_container)


    def on_zoom_changed(self, button):
        old_zoom_mode = self.zoom_mode
        new_zoom_mode = ""
        if button == self.fit_radio:
            new_zoom_mode = "Fit"
            self.update_thumbnail_panel_style()
        elif button == self.zoom_100_radio:
            new_zoom_mode = "100%"
        elif button == self.zoom_spin_btn:
            new_zoom_mode = "Spin"
        else:
            return

        if old_zoom_mode == new_zoom_mode:
            return

        if new_zoom_mode != "Fit":
            self.last_active_zoom_mode = new_zoom_mode
            logging.debug(f"Last active zoom mode updated to: {self.last_active_zoom_mode}")

        current_orientation = self.current_image_orientation
        
        # 디버깅: 현재 상태 로그
        logging.debug(f"줌 모드 변경: {old_zoom_mode} -> {new_zoom_mode}, 방향: {current_orientation}")

        # 현재 뷰포트 포커스 저장 (100%/Spin -> Fit 전환 시)
        if old_zoom_mode in ["100%", "Spin"] and current_orientation:
            # 중요: zoom_mode를 변경하기 전에 현재 뷰포트 위치를 계산해야 함
            current_rel_center = self._get_current_view_relative_center()
            logging.debug(f"뷰포트 위치 저장: {current_orientation} -> {current_rel_center} (줌: {old_zoom_mode})")
            
            # 현재 활성 포커스 업데이트
            self.current_active_rel_center = current_rel_center
            self.current_active_zoom_level = old_zoom_mode
            
            # 방향별 포커스 저장
            self._save_orientation_viewport_focus(
                current_orientation,
                current_rel_center,
                old_zoom_mode
            )

        # 줌 모드 변경
        self.zoom_mode = new_zoom_mode

        if self.zoom_mode == "Fit":
            self.current_active_rel_center = QPointF(0.5, 0.5)
            self.current_active_zoom_level = "Fit"
            logging.debug("Fit 모드로 전환: 중앙 포커스 설정")
        else:
            # 저장된 뷰포트 포커스 복구 (Fit -> 100%/Spin 전환 시)
            if current_orientation:
                saved_rel_center, saved_zoom_level = self._get_orientation_viewport_focus(current_orientation, self.zoom_mode)
                self.current_active_rel_center = saved_rel_center
                self.current_active_zoom_level = self.zoom_mode
                logging.debug(f"뷰포트 포커스 복구: {current_orientation} -> 중심={saved_rel_center}, 줌={self.zoom_mode}")
            else:
                # orientation 정보가 없으면 중앙 사용
                self.current_active_rel_center = QPointF(0.5, 0.5)
                self.current_active_zoom_level = self.zoom_mode
                logging.debug(f"orientation 정보 없음: 중앙 사용")

        self.zoom_change_trigger = "radio_button"

        # 그리드 모드 관련 처리
        if self.zoom_mode != "Fit" and self.grid_mode != "Off":
            if self.image_files and 0 <= self.grid_page_start_index + self.current_grid_index < len(self.image_files):
                self.current_image_index = self.grid_page_start_index + self.current_grid_index
            else:
                self.current_image_index = 0 if self.image_files else -1
            
            self.grid_mode = "Off"
            self.grid_off_radio.setChecked(True)
            self.update_grid_view()
            self.update_zoom_radio_buttons_state()
            self.update_counter_layout()
            
            if self.original_pixmap is None and self.current_image_index != -1:
                logging.debug("on_zoom_changed: Grid에서 Off로 전환, original_pixmap 로드 위해 display_current_image 호출")
                self.display_current_image()
                return
        
        # 이미지 적용
        if self.original_pixmap:
            logging.debug(f"on_zoom_changed: apply_zoom_to_image 호출 (줌: {self.zoom_mode}, 활성중심: {self.current_active_rel_center})")
            self.apply_zoom_to_image()

        self.toggle_minimap(self.minimap_toggle.isChecked())
        self.activateWindow()
        self.setFocus()

    def on_zoom_spinbox_value_changed(self, value):
        """줌 스핀박스 값 변경 시 호출"""
        self.zoom_spin_value = value / 100.0  # 300 -> 3.0
        if self.zoom_mode == "Spin":
            # 현재 모드가 Spin일 때만 즉시 이미지에 반영
            self.image_processing = True
            self.apply_zoom_to_image()
            self.image_processing = False
        self.activateWindow()
        self.setFocus()

    def toggle_minimap(self, show=None):
        """미니맵 표시 여부 토글"""
        # 파라미터가 없으면 현재 상태에서 토글
        if show is None:
            show = not self.minimap_visible
        
        self.minimap_visible = show and self.minimap_toggle.isChecked()
        
        # Fit 모드이거나 이미지가 없는 경우 미니맵 숨김
        if self.zoom_mode == "Fit" or not self.image_files or self.current_image_index < 0:
            self.minimap_widget.hide()
            return
        
        if self.minimap_visible:
            # 미니맵 크기 계산
            self.calculate_minimap_size()
            
            # 미니맵 위치 업데이트
            self.update_minimap_position()
            
            # 미니맵 이미지 업데이트
            self.update_minimap()
            
            # 미니맵 표시
            self.minimap_widget.show()
            self.minimap_widget.raise_()  # 위젯을 다른 위젯들 위로 올림
        else:
            self.minimap_widget.hide()
    
    def calculate_minimap_size(self):
        """현재 이미지 비율에 맞게 미니맵 크기 계산"""
        if not self.original_pixmap:
            # 기본 3:2 비율 사용
            self.minimap_width = self.minimap_max_size
            self.minimap_height = int(self.minimap_max_size / 1.5)
            return
        
        try:
            # 원본 이미지의 비율 확인
            img_width = self.original_pixmap.width()
            img_height = self.original_pixmap.height()
            img_ratio = img_width / img_height if img_height > 0 else 1.5  # 안전 처리
            
            # 이미지 비율에 맞게 미니맵 크기 설정 (최대 크기 제한)
            if img_ratio > 1:  # 가로가 더 긴 이미지
                self.minimap_width = self.minimap_max_size
                self.minimap_height = int(self.minimap_max_size / img_ratio)
            else:  # 세로가 더 길거나 정사각형 이미지
                self.minimap_height = self.minimap_max_size
                self.minimap_width = int(self.minimap_max_size * img_ratio)
            
            # 미니맵 위젯 크기 업데이트
            self.minimap_widget.setFixedSize(self.minimap_width, self.minimap_height)
            
        except Exception as e:
            # 오류 발생 시 기본 크기 사용
            self.minimap_width = self.minimap_max_size
            self.minimap_height = int(self.minimap_max_size / 1.5)
            logging.error(f"미니맵 크기 계산 오류: {e}")
    
    def update_minimap_position(self):
        """미니맵 위치 업데이트 (A 캔버스 기준)"""
        if not self.minimap_visible:
            return
        padding = 10
        # 기준을 self.image_panel에서 self.scroll_area로 변경
        panel_width = self.scroll_area.width()
        panel_height = self.scroll_area.height()
        minimap_x = panel_width - self.minimap_width - padding
        minimap_y = panel_height - self.minimap_height - padding
        self.minimap_widget.move(minimap_x, minimap_y)
    
    def update_minimap(self):
        """미니맵 이미지 및 뷰박스 업데이트"""
        if not self.minimap_visible or not self.original_pixmap:
            return
        
        try:
            # 미니맵 이미지 생성 (원본 이미지 축소)
            scaled_pixmap = self.original_pixmap.scaled(
                self.minimap_width, 
                self.minimap_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 미니맵 크기에 맞게 배경 이미지 조정
            background_pixmap = QPixmap(self.minimap_width, self.minimap_height)
            background_pixmap.fill(Qt.black)
            
            # 배경에 이미지 그리기
            painter = QPainter(background_pixmap)
            # 이미지 중앙 정렬
            x = (self.minimap_width - scaled_pixmap.width()) // 2
            y = (self.minimap_height - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
            
            # 뷰박스 그리기
            if self.zoom_mode != "Fit":
                self.draw_minimap_viewbox(painter, scaled_pixmap, x, y)
            
            painter.end()
            
            # 미니맵 이미지 설정
            self.minimap_pixmap = background_pixmap
            self.minimap_label.setPixmap(background_pixmap)
            
        except Exception as e:
            logging.error(f"미니맵 업데이트 오류: {e}")
    
    def draw_minimap_viewbox(self, painter, scaled_pixmap, offset_x, offset_y):
        """미니맵에 현재 보이는 영역을 표시하는 뷰박스 그리기"""
        try:
            # 현재 상태 정보
            zoom_level = self.zoom_mode
            
            # 캔버스 크기
            view_width = self.scroll_area.width()
            view_height = self.scroll_area.height()
            
            # 원본 이미지 크기
            img_width = self.original_pixmap.width()
            img_height = self.original_pixmap.height()
            
            # 스케일 계산
            minimap_img_width = scaled_pixmap.width()
            minimap_img_height = scaled_pixmap.height()
            
            # 확대 비율
            if zoom_level == "100%":
                zoom_percent = 1.0
            elif zoom_level == "Spin":
                zoom_percent = self.zoom_spin_value
            else:
                return
            
            # 확대된 이미지 크기
            zoomed_width = img_width * zoom_percent
            zoomed_height = img_height * zoom_percent
            
            # 현재 이미지 위치
            img_pos = self.image_label.pos()
            
            # 뷰포트가 보이는 이미지 영역의 비율 계산 (0~1 사이 값)
            if zoomed_width <= view_width:
                # 이미지가 더 작으면 전체가 보임
                view_x_ratio = 0
                view_width_ratio = 1.0
            else:
                # 이미지가 더 크면 일부만 보임
                view_x_ratio = -img_pos.x() / zoomed_width if img_pos.x() < 0 else 0
                view_width_ratio = min(1.0, view_width / zoomed_width)
            
            if zoomed_height <= view_height:
                y_min = (view_height - img_height) // 2
                y_max = y_min
            else:
                y_min = min(0, view_height - img_height)
                y_max = 0
            
            if img_height <= view_height:
                view_y_ratio = 0
                view_height_ratio = 1.0
            else:
                view_y_ratio = -img_pos.y() / zoomed_height if img_pos.y() < 0 else 0
                view_height_ratio = min(1.0, view_height / zoomed_height)
            
            # 범위 제한
            view_x_ratio = min(1.0 - view_width_ratio, max(0, view_x_ratio))
            view_y_ratio = min(1.0 - view_height_ratio, max(0, view_y_ratio))
            
            # 뷰박스 좌표 계산
            box_x1 = offset_x + (view_x_ratio * minimap_img_width)
            box_y1 = offset_y + (view_y_ratio * minimap_img_height)
            box_x2 = box_x1 + (view_width_ratio * minimap_img_width)
            box_y2 = box_y1 + (view_height_ratio * minimap_img_height)
            
            # 뷰박스 그리기
            painter.setPen(QPen(QColor(255, 255, 0), 2))  # 노란색, 2px 두께
            painter.drawRect(int(box_x1), int(box_y1), int(box_x2 - box_x1), int(box_y2 - box_y1))
            
            # 뷰박스 정보 저장
            self.minimap_viewbox = {
                "x1": box_x1,
                "y1": box_y1,
                "x2": box_x2,
                "y2": box_y2,
                "offset_x": offset_x,
                "offset_y": offset_y,
                "width": minimap_img_width,
                "height": minimap_img_height
            }
            
        except Exception as e:
            logging.error(f"뷰박스 그리기 오류: {e}")
    
    def minimap_mouse_press_event(self, event):
        """미니맵 마우스 클릭 이벤트 처리"""
        if not self.minimap_visible or self.zoom_mode == "Fit":
            return
        
        # 패닝 진행 중이면 중단
        if self.panning:
            self.panning = False
            
        # 이벤트 발생 위치
        pos = event.position().toPoint()
        
        # 뷰박스 클릭 체크
        if self.minimap_viewbox and self.is_point_in_viewbox(pos):
            # 뷰박스 내부 클릭 - 드래그 시작
            self.minimap_viewbox_dragging = True
            self.minimap_drag_start = pos
        else:
            # 뷰박스 외부 클릭 - 위치 이동
            self.move_view_to_minimap_point(pos)
    
    def minimap_mouse_move_event(self, event):
        """미니맵 마우스 이동 이벤트 처리"""
        if not self.minimap_visible or self.zoom_mode == "Fit":
            return
            
        # 패닝 중이라면 중단
        if self.panning:
            self.panning = False
            
        pos = event.position().toPoint()
        
        # 뷰박스 드래그 처리
        if self.minimap_viewbox_dragging:
            self.drag_minimap_viewbox(pos)
        
        # 뷰박스 위에 있을 때 커서 모양 변경
        if self.is_point_in_viewbox(pos):
            self.minimap_widget.setCursor(Qt.PointingHandCursor)
        else:
            self.minimap_widget.setCursor(Qt.ArrowCursor)
    
    def minimap_mouse_release_event(self, event):
        """미니맵 마우스 릴리스 이벤트 처리"""
        if event.button() == Qt.LeftButton:
            # 드래그 상태 해제
            self.minimap_viewbox_dragging = False
            self.minimap_widget.setCursor(Qt.ArrowCursor)
    
    def is_point_in_viewbox(self, point):
        """포인트가 뷰박스 내에 있는지 확인"""
        if not self.minimap_viewbox:
            return False
        
        vb = self.minimap_viewbox
        return (vb["x1"] <= point.x() <= vb["x2"] and
                vb["y1"] <= point.y() <= vb["y2"])
    
    def move_view_to_minimap_point(self, point):
        """미니맵의 특정 지점으로 뷰 이동"""
        if not self.minimap_viewbox or not self.original_pixmap:
            return
        
        # 이벤트 스로틀링
        current_time = int(time.time() * 1000)
        if current_time - self.last_event_time < 50:  # 50ms 지연
            return
        
        self.last_event_time = current_time
        
        vb = self.minimap_viewbox
        
        # 미니맵 이미지 내 클릭 위치의 상대적 비율 계산
        x_ratio = (point.x() - vb["offset_x"]) / vb["width"]
        y_ratio = (point.y() - vb["offset_y"]) / vb["height"]
        
        # 비율 제한
        x_ratio = max(0, min(1, x_ratio))
        y_ratio = max(0, min(1, y_ratio))
        
        # 원본 이미지 크기
        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()
        
        # 확대 비율
        zoom_percent = 1.0 if self.zoom_mode == "100%" else 2.0
        
        # 확대된 이미지 크기
        zoomed_width = img_width * zoom_percent
        zoomed_height = img_height * zoom_percent
        
        # 뷰포트 크기
        view_width = self.scroll_area.width()
        view_height = self.scroll_area.height()
        
        # 새 이미지 위치 계산
        new_x = -x_ratio * (zoomed_width - view_width) if zoomed_width > view_width else (view_width - zoomed_width) / 2
        new_y = -y_ratio * (zoomed_height - view_height) if zoomed_height > view_height else (view_height - zoomed_height) / 2
        
        # 이미지 위치 업데이트
        self.image_label.move(int(new_x), int(new_y))
        
        # 미니맵 업데이트
        self.update_minimap()
    
    def drag_minimap_viewbox(self, point):
        """미니맵 뷰박스 드래그 처리 - 부드럽게 개선"""
        if not self.minimap_viewbox or not self.minimap_viewbox_dragging:
            return
        
        # 스로틀링 시간 감소하여 부드러움 향상 
        current_time = int(time.time() * 1000)
        if current_time - self.last_event_time < 16:  # 약 60fps를 목표로 (~16ms)
            return
        
        self.last_event_time = current_time
        
        # 마우스 이동 거리 계산
        dx = point.x() - self.minimap_drag_start.x()
        dy = point.y() - self.minimap_drag_start.y()
        
        # 현재 위치 업데이트
        self.minimap_drag_start = point
        
        # 미니맵 내에서의 이동 비율
        vb = self.minimap_viewbox
        x_ratio = dx / vb["width"] if vb["width"] > 0 else 0
        y_ratio = dy / vb["height"] if vb["height"] > 0 else 0
        
        # 원본 이미지 크기
        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()
        
        # 확대 비율
        zoom_percent = 1.0 if self.zoom_mode == "100%" else 2.0
        
        # 확대된 이미지 크기
        zoomed_width = img_width * zoom_percent
        zoomed_height = img_height * zoom_percent
        
        # 현재 이미지 위치
        img_pos = self.image_label.pos()
        
        # 이미지가 이동할 거리 계산
        img_dx = x_ratio * zoomed_width
        img_dy = y_ratio * zoomed_height
        
        # 뷰포트 크기
        view_width = self.scroll_area.width()
        view_height = self.scroll_area.height()
        
        # 새 위치 계산
        new_x = img_pos.x() - img_dx
        new_y = img_pos.y() - img_dy
        
        # 위치 제한
        if zoomed_width > view_width:
            new_x = min(0, max(view_width - zoomed_width, new_x))
        else:
            new_x = (view_width - zoomed_width) / 2
            
        if zoomed_height > view_height:
            new_y = min(0, max(view_height - zoomed_height, new_y))
        else:
            new_y = (view_height - zoomed_height) / 2
        
        # 이미지 위치 업데이트
        self.image_label.move(int(new_x), int(new_y))
        
        # 미니맵 업데이트
        self.update_minimap()
    
    def get_scaled_size(self, base_size):
        """UI 배율을 고려한 크기 계산"""
        # 화면의 물리적 DPI와 논리적 DPI를 사용하여 스케일 계산
        screen = QGuiApplication.primaryScreen()
        if screen:
            dpi_ratio = screen.devicePixelRatio()
            # Qt의 devicePixelRatio를 사용하여 실제 UI 배율 계산
            # Windows에서 150% 배율일 경우 dpi_ratio는 1.5가 됨
            return int(base_size / dpi_ratio)  # 배율을 고려하여 크기 조정
        return base_size  # 스케일 정보를 얻을 수 없으면 기본값 사용

    def setup_grid_ui(self):
        """Grid 설정 UI 구성 (라디오 버튼 + 콤보박스)"""
        # ... (함수 상단은 이전과 동일) ...
        grid_title = QLabel("Grid")
        grid_title.setAlignment(Qt.AlignCenter)
        grid_title.setStyleSheet(f"color: {ThemeManager.get_color('text')};")
        font = QFont(self.font())
        font.setPointSize(UIScaleManager.get("zoom_grid_font_size"))
        grid_title.setFont(font)
        self.control_layout.addWidget(grid_title)
        self.control_layout.addSpacing(UIScaleManager.get("title_spacing"))

        grid_container = QWidget()
        grid_layout_grid = QGridLayout(grid_container)
        grid_layout_grid.setContentsMargins(0, 0, 0, 0)
        
        self.grid_off_radio = QRadioButton("Off")
        self.grid_on_radio = QRadioButton()

        self.grid_size_combo = QComboBox()
        self.grid_size_combo.addItems(["2 x 2", "3 x 3", "4 x 4"])

        # (콤보박스 너비 및 스타일 설정은 이전과 동일)
        font_metrics = self.grid_size_combo.fontMetrics()
        max_text_width = 0
        for i in range(self.grid_size_combo.count()):
            width = font_metrics.horizontalAdvance(self.grid_size_combo.itemText(i))
            if width > max_text_width:
                max_text_width = width
        extra_space = 30
        self.grid_size_combo.setFixedWidth(max_text_width + extra_space)
        self.grid_size_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {ThemeManager.get_color('bg_primary')}; color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')}; border-radius: 1px;
                padding: {UIScaleManager.get("combobox_padding")}px;
            }}
            QComboBox:hover {{ background-color: #555555; }}
            QComboBox QAbstractItemView {{
                background-color: {ThemeManager.get_color('bg_secondary')}; color: {ThemeManager.get_color('text')};
                selection-background-color: #505050; selection-color: {ThemeManager.get_color('text')};
            }}
        """)
        
        self.grid_mode_group = QButtonGroup(self)
        self.grid_mode_group.addButton(self.grid_off_radio, 0)
        self.grid_mode_group.addButton(self.grid_on_radio, 1)
        
        radio_style = ThemeManager.generate_radio_button_style()
        self.grid_off_radio.setStyleSheet(radio_style)
        self.grid_on_radio.setStyleSheet(radio_style)
        
        self.grid_mode_group.buttonClicked.connect(self._on_grid_mode_toggled)
        self.grid_size_combo.currentTextChanged.connect(self._on_grid_size_changed)

        # (이하 레이아웃 구성은 이전과 동일)
        grid_on_widget_container = QWidget()
        grid_on_container_layout = QHBoxLayout(grid_on_widget_container)
        grid_on_container_layout.setContentsMargins(0, 0, 0, 0)
        grid_on_container_layout.setSpacing(5)
        grid_on_container_layout.addWidget(self.grid_on_radio)
        grid_on_container_layout.addWidget(self.grid_size_combo)
        
        self.compare_radio = QRadioButton("A | B")
        self.compare_radio.setStyleSheet(radio_style)
        self.grid_mode_group.addButton(self.compare_radio, 2)

        grid_layout_grid.addWidget(self.grid_off_radio, 0, 1)
        grid_layout_grid.addWidget(grid_on_widget_container, 0, 2)
        grid_layout_grid.addWidget(self.compare_radio, 0, 3)

        grid_layout_grid.setColumnStretch(0, 1)
        grid_layout_grid.setColumnStretch(4, 1)

        self.control_layout.addWidget(grid_container)

        self.filename_toggle_grid = QCheckBox(LanguageManager.translate("파일명"))
        self.filename_toggle_grid.setChecked(self.show_grid_filenames)
        self.filename_toggle_grid.toggled.connect(self.on_filename_toggle_changed)
        self.filename_toggle_grid.setStyleSheet(ThemeManager.generate_checkbox_style())
        filename_toggle_container = QWidget()
        filename_toggle_layout = QHBoxLayout(filename_toggle_container)
        filename_toggle_layout.setContentsMargins(0, 10, 0, 0)
        filename_toggle_layout.addStretch()
        filename_toggle_layout.addWidget(self.filename_toggle_grid)
        filename_toggle_layout.addStretch()
        self.control_layout.addWidget(filename_toggle_container)


    def _on_grid_mode_toggled(self, button):
        """Grid On/Off/Compare 라디오 버튼 클릭 시 호출 """
        button_id = self.grid_mode_group.id(button)
        new_compare_active = (button_id == 2)
        is_grid_on = (button_id == 1)
        
        new_grid_mode = "Off"
        if is_grid_on:
            new_grid_mode = self.last_active_grid_mode
        
        is_transitioning_from_grid_to_compare = (self.grid_mode != "Off" and new_compare_active)

        if is_transitioning_from_grid_to_compare:
            target_index = self.primary_selected_index if self.primary_selected_index != -1 else (self.grid_page_start_index + self.current_grid_index)
            if 0 <= target_index < len(self.image_files):
                self.current_image_index = target_index
        
        if self.compare_mode_active != new_compare_active or self.grid_mode != new_grid_mode:
            is_transitioning_to_off = (self.grid_mode != "Off" and new_grid_mode == "Off" and not new_compare_active)
            
            self.compare_mode_active = new_compare_active
            self.grid_mode = new_grid_mode

            if is_transitioning_to_off:
                target_index = self.primary_selected_index if self.primary_selected_index != -1 else (self.grid_page_start_index + self.current_grid_index)
                if 0 <= target_index < len(self.image_files):
                    self.current_image_index = target_index
                self.force_refresh = True
            
            self._update_view_for_grid_change()
            
            if self.grid_mode == "Off":
                QTimer.singleShot(0, self.display_current_image)

                if self.compare_mode_active and self.current_image_index >= 0:
                    # 짧은 지연 후 썸네일 패널의 인덱스를 설정하여 스크롤 위치를 맞춥니다.
                    # 지연을 주는 이유는 썸네일 패널이 완전히 표시되고 레이아웃이 계산될 시간을 확보하기 위함입니다.
                    QTimer.singleShot(50, lambda: self.thumbnail_panel.set_current_index(self.current_image_index))

        self.activateWindow()
        self.setFocus()



    
    def _on_grid_size_changed(self, text):
        """Grid 크기 콤보박스 변경 시 호출"""
        new_mode = text.replace(" ", "")
        self.last_active_grid_mode = new_mode
        logging.debug(f"_on_grid_size_changed: last_active_grid_mode updated to '{new_mode}'")

        # 이미 Grid On 상태에서 콤보박스를 변경하면, 즉시 뷰를 업데이트합니다.
        if self.grid_on_radio.isChecked() and self.grid_mode != new_mode:
            self.grid_mode = new_mode
            # _update_view_for_grid_change() 대신 직접 update_grid_view()를 호출하여
            # 레이아웃 문제를 피합니다.
            self.update_grid_view()
            
        self.activateWindow()
        self.setFocus()

    def _update_view_for_grid_change(self):
        """Grid/Compare 모드 변경에 따른 공통 UI 업데이트 로직 (최종 수정)"""
        logging.debug(f"View change triggered. Target Grid mode: {self.grid_mode}, Compare mode: {self.compare_mode_active}")
        
        def update_ui_after_resize():
            if self.compare_mode_active:
                splitter_width = self.view_splitter.width()
                self.view_splitter.setSizes([splitter_width // 2, splitter_width // 2])
                padding = 10
                btn_size = self.close_compare_button.width()
                new_x = self.scroll_area_B.width() - btn_size - padding
                new_y = padding
                self.close_compare_button.move(new_x, new_y)
                self.close_compare_button.raise_()
            else:
                self.view_splitter.setSizes([self.view_splitter.width(), 0])
            self.apply_zoom_to_image()

        if self.compare_mode_active:
            self.scroll_area_B.show()
            self.close_compare_button.show()
            if not self.image_B_path:
                self.image_label_B.setText(LanguageManager.translate("비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다."))
            self.grid_mode = "Off" # Compare 모드일 땐 내부적으로 항상 Grid Off

            # 비교 모드일 때는 update_grid_view()를 호출하지 않고,
            # A 패널이 단일 이미지 뷰(image_container)를 유지하도록 보장합니다.
            current_view_widget = self.scroll_area.takeWidget()
            if current_view_widget and current_view_widget is not self.image_container:
                current_view_widget.deleteLater()
            self.scroll_area.setWidget(self.image_container)
        else:
            self.scroll_area_B.hide()
            self.close_compare_button.hide()
            self.image_B_path = None
            self.original_pixmap_B = None
            self.image_label_B.clear()
            # 비교 모드가 아닐 때만 update_grid_view()를 호출하여 그리드 또는 단일 뷰를 설정합니다.
            self.update_grid_view()

        QTimer.singleShot(10, update_ui_after_resize)
        self.update_thumbnail_panel_style()
        
        if self.grid_mode != "Off":
            if self.zoom_mode != "Fit":
                self.zoom_mode = "Fit"
                self.fit_radio.setChecked(True)
            if self.current_image_index != -1:
                rows, cols = self._get_grid_dimensions()
                if rows > 0:
                    num_cells = rows * cols
                    self.grid_page_start_index = (self.current_image_index // num_cells) * num_cells
                    self.current_grid_index = self.current_image_index % num_cells
            self.selected_grid_indices.clear()
            self.selected_grid_indices.add(self.current_grid_index)
            self.primary_selected_index = self.grid_page_start_index + self.current_grid_index
            self.last_single_click_index = self.current_grid_index
        
        self.update_zoom_radio_buttons_state()
        self.update_counter_layout()
        self.update_compare_filenames()
        self.activateWindow()
        self.setFocus()

        

    def update_compare_filenames(self):
        """Compare 모드에서 A, B 캔버스의 파일명 라벨을 업데이트합니다."""
        # 1. Compare 모드가 아니거나, 파일명 표시 옵션이 꺼져있으면 라벨을 숨기고 종료합니다.
        if not self.compare_mode_active or not self.show_grid_filenames:
            self.filename_label_A.hide()
            self.filename_label_B.hide()
            return

        padding = UIScaleManager.get("compare_filename_padding", 10)

        # 2. A 캔버스 파일명 라벨 업데이트
        # A 캔버스에 유효한 이미지가 표시되고 있는지 확인합니다.
        if self.original_pixmap and 0 <= self.current_image_index < len(self.image_files):
            # 파일명을 라벨에 설정하고, 내용에 맞게 크기를 조절합니다.
            self.filename_label_A.setText(self.image_files[self.current_image_index].name)
            self.filename_label_A.adjustSize()
            # 좌측 상단에 위치시킵니다.
            self.filename_label_A.move(padding, padding)
            # 라벨을 보이게 하고, 다른 위젯 위에 오도록 합니다.
            self.filename_label_A.show()
            self.filename_label_A.raise_()
        else:
            # 이미지가 없으면 숨깁니다.
            self.filename_label_A.hide()

        # 3. B 캔버스 파일명 라벨 업데이트
        # B 캔버스에 이미지가 로드되었는지 확인합니다.
        if self.image_B_path:
            self.filename_label_B.setText(self.image_B_path.name)
            self.filename_label_B.adjustSize()
            self.filename_label_B.move(padding, padding)
            self.filename_label_B.show()
            self.filename_label_B.raise_()
        else:
            self.filename_label_B.hide()

    def _get_grid_dimensions(self):
        """현재 grid_mode에 맞는 (행, 열)을 반환합니다."""
        if self.grid_mode == '2x2':
            return 2, 2
        if self.grid_mode == '3x3':
            return 3, 3
        if self.grid_mode == '4x4':
            return 4, 4
        return 0, 0 # Grid Off 또는 예외 상황

    def update_zoom_radio_buttons_state(self):
        """그리드 모드에 따라 줌 라디오 버튼 활성화/비활성화"""
        if self.grid_mode != "Off":
            # 그리드 모드에서 100%, spin 비활성화
            self.zoom_100_radio.setEnabled(False)
            self.zoom_spin_btn.setEnabled(False)
            # 비활성화 스타일 적용
            disabled_radio_style = f"""
                QRadioButton {{
                    color: {ThemeManager.get_color('text_disabled')};
                    padding: {UIScaleManager.get("radiobutton_padding")}px;
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
            """
            self.zoom_100_radio.setStyleSheet(disabled_radio_style)
            self.zoom_spin_btn.setStyleSheet(disabled_radio_style)
            
            # SpinBox 비활성화 스타일 적용
            disabled_spinbox_style = f"""
                QSpinBox {{
                    background-color: {ThemeManager.get_color('bg_primary')};
                    color: {ThemeManager.get_color('text_disabled')};
                    border: 1px solid {ThemeManager.get_color('border')};
                    border-radius: 1px;
                    padding: {UIScaleManager.get("spinbox_padding")}px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: 1px solid {ThemeManager.get_color('border')};
                    width: 16px;
                }}
                QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                    background-color: {ThemeManager.get_color('bg_primary')};
                }}
                QSpinBox::up-arrow, QSpinBox::down-arrow {{
                    image: none;
                    width: 0px;
                    height: 0px;
                }}
            """
            self.zoom_spin.setStyleSheet(disabled_spinbox_style)
            
        else:
            # 그리드 모드가 아닐 때 모든 버튼 활성화
            self.zoom_100_radio.setEnabled(True)
            self.zoom_spin_btn.setEnabled(True)
            # 활성화 스타일 복원
            radio_style = ThemeManager.generate_radio_button_style()
            self.zoom_100_radio.setStyleSheet(radio_style)
            self.zoom_spin_btn.setStyleSheet(radio_style)
            
            # SpinBox 활성화 스타일 복원
            active_spinbox_style = f"""
                QSpinBox {{
                    background-color: {ThemeManager.get_color('bg_primary')};
                    color: {ThemeManager.get_color('text')};
                    border: 1px solid {ThemeManager.get_color('border')};
                    border-radius: 1px;
                    padding: {UIScaleManager.get("spinbox_padding")}px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: 1px solid {ThemeManager.get_color('border')};
                    width: 16px;
                }}
                QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                    background-color: {ThemeManager.get_color('bg_secondary')};
                }}
                QSpinBox::up-arrow, QSpinBox::down-arrow {{
                    image: none;
                    width: 0px;
                    height: 0px;
                }}
            """
            self.zoom_spin.setStyleSheet(active_spinbox_style)


    def grid_cell_mouse_press_event(self, event, widget, index):
        """Grid 셀 마우스 프레스 이벤트 - 드래그와 클릭을 함께 처리"""
        try:
            # === 우클릭 컨텍스트 메뉴 처리 ===
            if event.button() == Qt.RightButton and self.image_files:
                # 해당 셀에 이미지가 있는지 확인
                global_index = self.grid_page_start_index + index
                if 0 <= global_index < len(self.image_files):
                    # 우클릭한 셀이 이미 선택된 셀들 중 하나인지 확인
                    if index not in self.selected_grid_indices:
                        # 선택되지 않은 셀을 우클릭한 경우: 해당 셀만 선택
                        self.selected_grid_indices.clear()
                        self.selected_grid_indices.add(index)
