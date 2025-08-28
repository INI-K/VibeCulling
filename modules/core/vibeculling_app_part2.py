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



        self.is_raw_only_mode = False
        self.image_label.clear()
        self.image_label.setStyleSheet("background-color: black;")
        self.setWindowTitle("VibeCulling")
        self.update_counters()
        self.update_file_info_display(None)
        self.update_jpg_folder_ui_state()
        self.update_raw_folder_ui_state()
        self.update_match_raw_button_state()
        self.update_all_folder_labels_state()

    def reset_application_settings(self):
        """사용자에게 확인을 받은 후, 설정 파일을 삭제하고 앱을 종료합니다."""
        title = LanguageManager.translate("초기화 확인")
        message = LanguageManager.translate("모든 설정을 초기화하고 프로그램을 종료하시겠습니까?\n이 작업은 되돌릴 수 없습니다.")
        
        reply = self.show_themed_message_box(
            QMessageBox.Question,
            title,
            message,
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel
        )

        if reply == QMessageBox.Yes:
            logging.info("사용자가 프로그램 설정 초기화를 승인했습니다.")
            
            state_file_path = self.get_script_dir() / self.STATE_FILE
            
            try:
                if state_file_path.exists():
                    state_file_path.unlink()
                    logging.info(f"설정 파일 삭제 성공: {state_file_path}")
            except Exception as e:
                logging.error(f"설정 파일 삭제 실패: {e}")
                self.show_themed_message_box(
                    QMessageBox.Critical, LanguageManager.translate("오류"),
                    f"설정 파일 삭제에 실패했습니다:\n{e}"
                )
                return

            logging.info("설정 초기화 완료. 앱을 종료합니다.")
            self._is_resetting = True
            self.close()


    def start_idle_preloading(self):
        """사용자가 유휴 상태일 때 백그라운드에서 이미지를 미리 로드합니다."""
        # 앱 상태 확인
        if not self.image_files or self.grid_mode != "Off" or self.is_idle_preloading_active:
            return

        # 현재 캐시된 파일들의 set과 로딩 중인 파일들의 set을 만듭니다.
        cached_paths = set(self.image_loader.cache.keys())
        # ResourceManager를 통해 현재 활성/대기 중인 작업 경로를 가져오는 기능이 필요할 수 있으나,
        # 여기서는 간단하게 캐시된 경로만 확인합니다.

        # 미리 로드할 파일 목록을 결정합니다.
        # 현재 이미지 위치에서부터 양방향으로 순차적으로 찾는 것이 효과적입니다.
        files_to_preload = []
        total_files = len(self.image_files)
        
        # 캐시가 꽉 찼는지 먼저 확인
        if len(cached_paths) >= self.image_loader.cache_limit:
            logging.info("유휴 프리로더: 캐시가 이미 가득 차서 실행하지 않습니다.")
            return

        # 현재 인덱스에서 시작하여 양방향으로 탐색
        for i in range(1, total_files):
            # 앞으로 탐색
            forward_index = (self.current_image_index + i) % total_files
            forward_path = str(self.image_files[forward_index])
            if forward_path not in cached_paths:
                files_to_preload.append(forward_path)

            # 뒤로 탐색 (중복 방지)
            backward_index = (self.current_image_index - i + total_files) % total_files
            if backward_index != forward_index:
                backward_path = str(self.image_files[backward_index])
                if backward_path not in cached_paths:
                    files_to_preload.append(backward_path)
        
        if not files_to_preload:
            logging.info("유휴 프리로더: 모든 이미지가 이미 캐시되었습니다.")
            return

        logging.info(f"유휴 프리로더: {len(files_to_preload)}개의 이미지를 낮은 우선순위로 로딩 시작합니다.")
        self.is_idle_preloading_active = True

        # ResourceManager를 통해 'low' 우선순위로 작업을 제출합니다.
        for path in files_to_preload:
            # 매번 루프를 돌 때마다 중단 플래그와 캐시 상태를 확인합니다.
            if not self.is_idle_preloading_active:
                logging.info("유휴 프리로더: 사용자 입력으로 인해 로딩이 중단되었습니다.")
                break
            
            if len(self.image_loader.cache) >= self.image_loader.cache_limit:
                logging.info("유휴 프리로더: 캐시가 가득 차서 로딩을 중단합니다.")
                break
            
            # 이미 캐시되었거나 다른 작업에서 로딩 중일 수 있으므로 다시 확인
            if path in self.image_loader.cache:
                continue
            
            # _preload_image_for_grid 함수는 내부적으로 ImageLoader 캐시를 채우므로 재사용합니다.
            # 이 함수는 RAW 파일의 경우 preview만 로드하므로, 유휴 로딩 시에도 시스템 부하가 적습니다.
            self.resource_manager.submit_imaging_task_with_priority(
                'low',
                self._preload_image_for_grid,
                path
            )

        # 모든 작업 제출이 끝나면 플래그를 리셋합니다.
        # 실제 작업은 백그라운드에서 계속됩니다.
        self.is_idle_preloading_active = False
        logging.info("유휴 프리로더: 모든 로딩 작업 제출 완료.")

    def deactivate_compare_mode(self):
        """비교 모드 X 버튼 클릭 시 동작 처리"""
        if not self.compare_mode_active:
            return

        # B 캔버스에 이미지가 로드되어 있으면, 이미지만 언로드
        if self.image_B_path:
            logging.info("비교 이미지 언로드")
            self.image_B_path = None
            self.original_pixmap_B = None
            self.image_label_B.clear()
            self.image_label_B.setText(LanguageManager.translate("비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다."))
        else:
            # B 캔버스가 비어있으면, 비교 모드 종료 (Grid Off로 전환)
            logging.info("비교 모드 종료")
            self.grid_off_radio.setChecked(True)
            self._on_grid_mode_toggled(self.grid_off_radio)

        self.activateWindow()
        self.setFocus()

    def image_B_mouse_press_event(self, event):
        """B 패널 마우스 클릭 이벤트 처리 (패닝 시작 및 우클릭 메뉴)"""
        if event.button() == Qt.RightButton and self.image_B_path:
            self.show_context_menu_for_B(event.position().toPoint())
            return
            
        # 100% 또는 Spin 모드에서만 패닝 활성화
        if self.zoom_mode in ["100%", "Spin"]:
            if event.button() == Qt.LeftButton:
                self.panning = True
                self.pan_start_pos = event.position().toPoint()
                self.image_start_pos = self.image_label.pos() # A 캔버스 위치 기준
                self.setCursor(Qt.ClosedHandCursor)

    def image_B_mouse_move_event(self, event):
        """B 패널 마우스 이동 이벤트 처리 (A와 동일한 패닝 로직)"""
        if not self.panning:
            return
        
        # A 캔버스의 패닝 로직을 그대로 사용합니다.
        # A 캔버스의 image_label 위치를 변경하고, _sync_viewports를 호출합니다.
        self.image_mouse_move_event(event)

    def image_B_mouse_release_event(self, event):
        """B 패널 마우스 릴리스 이벤트 처리 (A와 동일한 패닝 종료 로직)"""
        if event.button() == Qt.LeftButton and self.panning:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            # A 캔버스와 동일하게 뷰포트 포커스 저장
            if self.grid_mode == "Off" and self.zoom_mode in ["100%", "Spin"] and \
               self.original_pixmap and 0 <= self.current_image_index < len(self.image_files):
                current_rel_center = self._get_current_view_relative_center()
                self.current_active_rel_center = current_rel_center
                self.current_active_zoom_level = self.zoom_mode
                self._save_orientation_viewport_focus(self.current_image_orientation, current_rel_center, self.zoom_mode)
            
            if self.minimap_visible and self.minimap_widget.isVisible():
                self.update_minimap()

    def move_image_B_to_folder(self, folder_index, specific_index=None):
        """B 패널의 이미지를 이동합니다. specific_index가 주어지면 해당 인덱스의 파일을 이동합니다."""
        image_to_move_path = None
        image_to_move_index = -1

        if specific_index is not None and 0 <= specific_index < len(self.image_files):
                image_to_move_path = self.image_files[specific_index]
                image_to_move_index = specific_index
        elif self.image_B_path:
                image_to_move_path = self.image_B_path
                try:
                    image_to_move_index = self.image_files.index(image_to_move_path)
                except ValueError:
                    image_to_move_index = -1
        
        if not image_to_move_path:
            return
        
        current_A_path = self.get_current_image_path()

        if self.compare_mode_active and current_A_path and image_to_move_path == Path(current_A_path):
            logging.info("B->Move: A와 B가 동일하여 A의 이동 로직을 대신 실행합니다.")
            # A의 이동 로직을 호출하되, 히스토리에 Compare 모드였음을 기록하도록 수정
            self.move_current_image_to_folder(folder_index, index_to_move=image_to_move_index, context_mode="CompareA")
            return # 여기서 함수 종료

        # --- 아래는 A와 B가 다른 이미지일 경우의 기존 로직 ---
        target_folder = self.target_folders[folder_index]
        if not target_folder or not os.path.isdir(target_folder):
            self.show_themed_message_box(QMessageBox.Warning, "경고", "유효하지 않은 폴더입니다.")
            return

        moved_jpg_path = None
        moved_raw_path = None
        raw_path_before_move = None
        
        try:
            moved_jpg_path = self.move_file(image_to_move_path, target_folder)
            if moved_jpg_path is None:
                self.show_themed_message_box(QMessageBox.Critical, "에러", f"파일 이동 중 오류 발생: {image_to_move_path.name}")
                return

            raw_moved_successfully = True
            if self.move_raw_files:
                base_name = image_to_move_path.stem
                if base_name in self.raw_files:
                    raw_path_before_move = self.raw_files[base_name]
                    moved_raw_path = self.move_file(raw_path_before_move, target_folder)
                    if moved_raw_path:
                        del self.raw_files[base_name]
                    else:
                        raw_moved_successfully = False
                        self.show_themed_message_box(QMessageBox.Warning, "경고", f"RAW 파일 이동 실패: {raw_path_before_move.name}")

            if moved_jpg_path and image_to_move_index != -1:
                history_entry = {
                    "jpg_source": str(image_to_move_path),
                    "jpg_target": str(moved_jpg_path),
                    "raw_source": str(raw_path_before_move) if raw_path_before_move else None,
                    "raw_target": str(moved_raw_path) if moved_raw_path and raw_moved_successfully else None,
                    "index_before_move": image_to_move_index,
                    "a_index_before_move": self.current_image_index, # B 이동 시 A의 인덱스도 기록
                    "mode": "CompareB"
                }
                self.add_move_history(history_entry)

            self.image_B_path = None
            self.original_pixmap_B = None
            self.image_label_B.clear()
            self.image_label_B.setText(LanguageManager.translate("비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다."))
            
            if image_to_move_index != -1:
                self.image_files.pop(image_to_move_index)
                
                # A 캔버스의 인덱스가 밀렸는지 확인하고 조정
                if image_to_move_index < self.current_image_index:
                    self.current_image_index -= 1
            
            # 썸네일 패널과 UI 업데이트
            self.thumbnail_panel.set_image_files(self.image_files)
            self.update_thumbnail_current_index()
            self.update_counters()
            self.update_compare_filenames() # B 캔버스 파일명 업데이트

        except Exception as e:
            logging.error(f"B 패널 이미지 이동 중 예외 발생: {e}")
            self.show_themed_message_box(QMessageBox.Critical, "에러", f"파일 이동 중 오류 발생: {str(e)}")


    def show_context_menu_for_B(self, pos):
        if not self.image_B_path:
            return

        context_menu = QMenu(self)
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
        
        for i in range(self.folder_count):
            folder_path = self.target_folders[i] if i < len(self.target_folders) else ""
            
            if folder_path and os.path.isdir(folder_path):
                folder_name = Path(folder_path).name
                menu_text = LanguageManager.translate("이동 - 폴더 {0} [{1}]").format(i + 1, folder_name)
            else:
                menu_text = LanguageManager.translate("이동 - 폴더 {0}").format(i + 1)
                
            action = QAction(menu_text, self)
            action.triggered.connect(lambda checked, idx=i: self.move_image_B_to_folder(idx))
            
            # 폴더가 지정되지 않았거나 유효하지 않으면 비활성화
            if not folder_path or not os.path.isdir(folder_path):
                action.setEnabled(False)
                
            context_menu.addAction(action)

        context_menu.addSeparator()

        rotate_ccw_action = QAction(LanguageManager.translate("반시계 방향으로 회전"), self)
        rotate_ccw_action.triggered.connect(lambda: self.rotate_image('B', 'ccw'))
        context_menu.addAction(rotate_ccw_action)

        rotate_cw_action = QAction(LanguageManager.translate("시계 방향으로 회전"), self)
        rotate_cw_action.triggered.connect(lambda: self.rotate_image('B', 'cw'))
        context_menu.addAction(rotate_cw_action)
        
        context_menu.exec(self.image_container_B.mapToGlobal(pos))


    def _sync_viewports(self):
            """A와 B 캔버스의 스크롤 위치 및 이미지 위치를 동기화합니다."""
            # 줌 모드가 Fit일 때는 동기화가 불필요하고 오히려 레이아웃 문제를 일으키므로 즉시 반환합니다.
            if self.zoom_mode == "Fit":
                return

            if getattr(self, '_is_zooming', False):
                return

            if not self.compare_mode_active or not self.original_pixmap_B:
                return

            # 1. 스크롤바 위치 동기화 (스크롤바가 있는 경우)
            v_scroll_A = self.scroll_area.verticalScrollBar()
            h_scroll_A = self.scroll_area.horizontalScrollBar()
            v_scroll_B = self.scroll_area_B.verticalScrollBar()
            h_scroll_B = self.scroll_area_B.horizontalScrollBar()
            
            # A의 스크롤바 값을 B에 그대로 설정
            if v_scroll_A.value() != v_scroll_B.value():
                v_scroll_B.setValue(v_scroll_A.value())
            if h_scroll_A.value() != h_scroll_B.value():
                h_scroll_B.setValue(h_scroll_A.value())
                
            # 2. 이미지 라벨 위치 동기화 (패닝 시)
            pos_A = self.image_label.pos()
            pos_B = self.image_label_B.pos()
            
            if pos_A != pos_B:
                self.image_label_B.move(pos_A)


    def canvas_B_dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("thumbnail_drag:"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def canvas_B_dropEvent(self, event):
        mime_text = event.mimeData().text()
        
        if mime_text.startswith("thumbnail_drag:") or mime_text.startswith("image_drag:off:"):
            try:
                # mime 데이터에서 드롭된 이미지의 인덱스를 추출
                dropped_index = int(mime_text.split(":")[-1])
                current_A_index = self.current_image_index

                # 드롭된 이미지가 A 캔버스의 이미지와 동일한지 확인
                if dropped_index == current_A_index:
                    self.show_canvas_B_warning() # 경고 메시지 표시 함수 호출
                    event.acceptProposedAction()
                    return # 여기서 함수 종료

                # 이미지가 다를 경우, 기존 로직 실행
                if 0 <= dropped_index < len(self.image_files):
                    self.image_B_path = self.image_files[dropped_index]
                    self.original_pixmap_B = self.image_loader.load_image_with_orientation(str(self.image_B_path))
                    if self.original_pixmap_B and not self.original_pixmap_B.isNull():
                        self.image_label_B.setText("") # 안내 문구 제거
                        self._apply_zoom_to_canvas('B') # B 캔버스에 줌/뷰포트 적용
                        self._sync_viewports()
                        self.update_compare_filenames()
                    else:
                        self.image_B_path = None
                        self.original_pixmap_B = None
                        self.image_label_B.setText(LanguageManager.translate("이미지 로드 실패"))
                    
                    event.acceptProposedAction()

            except (ValueError, IndexError) as e:
                logging.error(f"B 패널 드롭 오류: {e}")
                event.ignore()
            finally:
                self.activateWindow()
                self.setFocus()
        else:
            event.ignore()


    
    def show_canvas_B_warning(self):
        """Canvas B에 경고 메시지를 표시하고 3초 후 되돌리는 타이머를 시작합니다."""
        warning_text = LanguageManager.translate("좌측 이미지와 다른 이미지를 드래그해주세요.")
        self.image_label_B.setText(warning_text)

        # 타이머가 없으면 생성
        if not hasattr(self, 'canvas_B_warning_timer'):
            self.canvas_B_warning_timer = QTimer(self)
            self.canvas_B_warning_timer.setSingleShot(True)
            self.canvas_B_warning_timer.timeout.connect(self._revert_canvas_B_text)
        
        # 3초 타이머 시작
        self.canvas_B_warning_timer.start(3000)

    def _revert_canvas_B_text(self):
        """Canvas B의 텍스트를 원래 안내 문구로 되돌립니다."""
        # B 캔버스에 다른 이미지가 로드되지 않았을 경우에만 텍스트를 되돌립니다.
        if not self.image_B_path:
            original_text = LanguageManager.translate("비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다.")
            self.image_label_B.setText(original_text)


    def _show_first_raw_decode_progress(self):
        """첫 RAW 파일 디코딩 시 진행률 대화상자를 표시합니다."""
        if self.first_raw_load_progress is None:
            line1 = LanguageManager.translate("쾌적한 작업을 위해 RAW 파일을 준비하고 있습니다.")
            line2 = LanguageManager.translate("잠시만 기다려주세요.")
            progress_text = f"<p style='margin-bottom: 10px;'>{line1}</p><p>{line2}</p>"
            progress_title = LanguageManager.translate("파일 준비 중")
            
            self.first_raw_load_progress = QProgressDialog(
                progress_text,
                "", 0, 0, self
            )
            self.first_raw_load_progress.setWindowTitle(progress_title)
            self.first_raw_load_progress.setCancelButton(None)
            self.first_raw_load_progress.setWindowModality(Qt.WindowModal)
            self.first_raw_load_progress.setMinimumDuration(0)
            apply_dark_title_bar(self.first_raw_load_progress)
            
            self.first_raw_load_progress.setStyleSheet(f"""
                QProgressDialog {{
                    background-color: {ThemeManager.get_color('bg_primary')};
                    color: {ThemeManager.get_color('text')};
                }}
                QProgressDialog > QLabel {{
                    padding-top: 20px;
                    padding-bottom: 30px;
                }}
                QProgressBar {{
                    text-align: center;
                }}
            """)
            
        # 대화상자를 메인 윈도우 중앙에 위치시키는 로직
        parent_geometry = self.geometry()
        self.first_raw_load_progress.adjustSize()
        dialog_size = self.first_raw_load_progress.size()
        new_x = parent_geometry.x() + (parent_geometry.width() - dialog_size.width()) // 2
        new_y = parent_geometry.y() + (parent_geometry.height() - dialog_size.height()) // 2
        self.first_raw_load_progress.move(new_x, new_y)
        self.first_raw_load_progress.show()
        QApplication.processEvents()

    def _close_first_raw_decode_progress(self):
        """진행률 대화상자를 닫습니다."""
        if self.first_raw_load_progress is not None and self.first_raw_load_progress.isVisible():
            self.first_raw_load_progress.close()
            self.first_raw_load_progress = None

    def refresh_folder_contents(self):
        """F5 키를 눌렀을 때 현재 로드된 폴더의 내용을 새로고침합니다."""
        if not self.current_folder and not self.is_raw_only_mode:
            logging.debug("새로고침 건너뛰기: 로드된 폴더가 없습니다.")
            return

        logging.info("폴더 내용 새로고침을 시작합니다...")

        # 1. 새로고침 전 현재 상태를 정확히 저장합니다.
        path_before_refresh = self.get_current_image_path()
        index_before_refresh = self.current_image_index if self.grid_mode == "Off" else (self.grid_page_start_index + self.current_grid_index)
        
        # 2. 파일 목록을 다시 스캔하고 정렬합니다.
        new_image_files = []
        folder_to_scan = self.raw_folder if self.is_raw_only_mode else self.current_folder
        
        if folder_to_scan and Path(folder_to_scan).is_dir():
            target_path = Path(folder_to_scan)
            extensions_to_scan = self.raw_extensions if self.is_raw_only_mode else self.supported_image_extensions
            
            scanned_files = []
            for file_path in target_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in extensions_to_scan:
                    scanned_files.append(file_path)
            new_image_files = sorted(scanned_files, key=self.get_datetime_from_file_fast)
        
        if not new_image_files:
            logging.warning("새로고침 결과: 폴더에 파일이 더 이상 없습니다. 초기화합니다.")
            if self.is_raw_only_mode: self.clear_raw_folder()
            else: self.clear_jpg_folder()
            return

        # 3. 새 목록에서 이전 위치를 찾습니다.
        self.image_files = new_image_files
        new_index = -1
        
        if path_before_refresh:
            try:
                new_index = self.image_files.index(Path(path_before_refresh))
                logging.info(f"이전 이미지 '{Path(path_before_refresh).name}'를 새 목록에서 찾았습니다. 인덱스: {new_index}")
            except ValueError:
                logging.info("이전에 보던 파일이 삭제되었습니다. 인덱스를 조정합니다.")
                new_index = min(index_before_refresh, len(self.image_files) - 1)
        
        if new_index < 0 and self.image_files:
            new_index = 0

        if not self.is_raw_only_mode and self.raw_folder and Path(self.raw_folder).is_dir():
            logging.info(f"새로고침 중 RAW 파일 동기 매칭 시작: {self.raw_folder}")
            self.raw_files.clear() # 기존 매칭 정보 초기화
            jpg_filenames = {f.stem: f for f in self.image_files}
            for file_path in Path(self.raw_folder).iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.raw_extensions:
                    if file_path.stem in jpg_filenames:
                        self.raw_files[file_path.stem] = file_path
            logging.info(f"동기 매칭 완료: {len(self.raw_files)}개 RAW 파일 매칭됨.")

        # 5. 계산된 최종 인덱스를 사용하여 모든 UI를 일관되게 업데이트합니다.
        self.force_refresh = True
        
        if self.grid_mode == "Off":
            self.current_image_index = new_index
            self.thumbnail_panel.set_image_files(self.image_files)
            self.display_current_image()
            self.update_thumbnail_current_index()
        else: # Grid 모드
            rows, cols = self._get_grid_dimensions()
            num_cells = rows * cols
            if new_index != -1:
                self.grid_page_start_index = (new_index // num_cells) * num_cells
                self.current_grid_index = new_index % num_cells
            else:
                self.grid_page_start_index = 0
                self.current_grid_index = 0
            
            self.thumbnail_panel.set_image_files(self.image_files)
            self.update_grid_view()

        self.update_counters()
        logging.info("UI 새로고침이 완료되었습니다.")



    def request_thumbnail_load(self, file_path, index):
        """ThumbnailModel로부터 썸네일 로딩 요청을 받아 처리"""
        # 이제 ResourceManager가 아닌 전용 스레드 풀을 사용합니다.
        if not hasattr(self, 'grid_thumbnail_executor') or self.grid_thumbnail_executor._shutdown:
            return

        thumbnail_size = UIScaleManager.get("thumbnail_image_size")
        angle = self.image_rotations.get(file_path, 0)

        # 전용 스레드 풀에 작업을 제출합니다. 우선순위 개념이 필요 없습니다.
        future = self.grid_thumbnail_executor.submit(
            self._generate_thumbnail_task,
            file_path,
            thumbnail_size,
            angle
        )
        
        if future:
            future.add_done_callback(
                lambda f, path=file_path: self._on_thumbnail_generated(f, path)
            )
        else:
            logging.warning(f"썸네일 로딩 작업 제출 실패 (future is None): {Path(file_path).name}")


    def _on_thumbnail_generated(self, future, file_path):
        """
        [Main Thread] 썸네일 생성이 완료되면 호출되는 콜백.
        """
        try:
            qimage = future.result()
            if qimage and not qimage.isNull():
                pixmap = QPixmap.fromImage(qimage)
                # 생성된 썸네일을 모델에 전달하여 UI 업데이트
                self.thumbnail_panel.model.set_thumbnail(file_path, pixmap)
        except Exception as e:
            logging.error(f"썸네일 결과 처리 중 오류 ({Path(file_path).name}): {e}")

    def on_thumbnail_clicked(self, index):
        """썸네일 클릭 시 해당 이미지로 이동"""
        # 이제 index는 QModelIndex가 아닌 정수입니다.
        if 0 <= index < len(self.image_files):
            self.current_image_index = index
            
            # Fit 모드인 경우 기존 캐시 무효화
            if self.zoom_mode == "Fit":
                self.last_fit_size = (0, 0)
                self.fit_pixmap_cache.clear()
            
            # 이미지 표시
            self.display_current_image()
            
            # 썸네일 패널 현재 인덱스 업데이트 (이 함수는 내부적으로 selectionModel도 처리합니다)
            self.thumbnail_panel.set_current_index(index)

            # 포커스를 메인 윈도우로 되돌림
            self.setFocus()


    def _generate_thumbnail_task(self, file_path, size, angle=0):
        """
        [Worker Thread] QImageReader를 사용하여 썸네일용 QImage를 생성하고, 주어진 각도로 회전시킵니다.
        """
        try:
            qimage = None
            is_raw = Path(file_path).suffix.lower() in self.raw_extensions
            if is_raw:
                preview_pixmap, _, _ = self.image_loader._load_raw_preview_with_orientation(file_path)
                if preview_pixmap and not preview_pixmap.isNull():
                    qimage = preview_pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation).toImage()
                else:
                    logging.warning(f"썸네일 패널용 프리뷰 없음: {file_path}")
                    qimage = QImage()
            else:
                reader = QImageReader(str(file_path))
                if not reader.canRead():
                    logging.warning(f"썸네일 생성을 위해 파일을 읽을 수 없음: {file_path}")
                    if Path(file_path).suffix.lower() in ['.heic', '.heif']:
                        try:
                            from PIL import Image
                            pil_image = Image.open(file_path)
                            pil_image.thumbnail((size, size), Image.Resampling.LANCZOS)
                            if pil_image.mode != 'RGB':
                                pil_image = pil_image.convert('RGB')
                            width, height = pil_image.size
                            rgb_data = pil_image.tobytes('raw', 'RGB')
                            qimage = QImage(rgb_data, width, height, QImage.Format_RGB888)
                            logging.info(f"PIL로 HEIC 썸네일 생성 성공: {file_path}")
                        except Exception as e:
                            logging.error(f"PIL로 HEIC 썸네일 생성 실패: {e}")
                else:
                    reader.setAutoTransform(True)
                    original_size = reader.size()
                    scaled_size = original_size.scaled(size, size, Qt.KeepAspectRatio)
                    reader.setScaledSize(scaled_size)
                    qimage = reader.read()
            
            if qimage is None or qimage.isNull():
                return None

            if angle != 0:
                transform = QTransform().rotate(angle)
                qimage = qimage.transformed(transform, Qt.SmoothTransformation)
            
            return qimage
        except Exception as e:
            logging.error(f"썸네일 생성 작업 중 오류 ({Path(file_path).name}): {e}")
            return None


    def on_thumbnail_double_clicked(self, index):
        """썸네일 더블클릭 시 처리 (단일 클릭과 동일하게 처리)"""
        self.on_thumbnail_clicked(index)

    def toggle_thumbnail_panel(self):
        """썸네일 패널 표시/숨김 토글 (Grid Off 모드에서만)"""
        if self.grid_mode == "Off":
            if self.thumbnail_panel.isVisible():
                self.thumbnail_panel.hide()
            else:
                self.thumbnail_panel.show()
                # 썸네일 패널이 표시될 때 현재 이미지 파일 목록 설정
                self.thumbnail_panel.set_image_files(self.image_files)
                if self.current_image_index >= 0:
                    self.thumbnail_panel.set_current_index(self.current_image_index)
            
            # 레이아웃 재조정
            self.adjust_layout()

    def update_thumbnail_panel_style(self):
        """Grid 모드에 따라 썸네일 패널의 내부 스타일(배경색, 리스트뷰 가시성)을 업데이트합니다."""
        if not hasattr(self, 'thumbnail_panel'):
            return

        panel = self.thumbnail_panel
        list_view = self.thumbnail_panel.list_view

        # QPalette를 직접 제어하여 배경색을 설정합니다.
        palette = panel.palette()

        if self.grid_mode == "Off":
            # Grid Off (일반) 모드: 리스트뷰를 표시하고 테마 기본 배경색으로 설정
            list_view.show()
            bg_color = QColor(ThemeManager.get_color('bg_primary'))
            palette.setColor(QPalette.Window, bg_color)
        else:
            # Grid On 또는 Compare 모드: 리스트뷰를 숨기고 #222222 배경색으로 설정
            list_view.hide()
            bg_color = QColor("#222222")
            palette.setColor(QPalette.Window, bg_color)

        # setAutoFillBackground(True)를 호출하여 팔레트 변경 사항을 위젯에 그리도록 지시합니다.
        panel.setAutoFillBackground(True)
        panel.setPalette(palette)
        
    def update_thumbnail_current_index(self):
        """현재 이미지 인덱스가 변경될 때 썸네일 패널 업데이트"""
        if self.thumbnail_panel.isVisible() and self.current_image_index >= 0:
            self.thumbnail_panel.set_current_index(self.current_image_index)


    def set_window_icon(self):
        """크로스 플랫폼 윈도우 아이콘을 설정합니다."""
        try:
            from PySide6.QtGui import QIcon
            
            # 플랫폼별 아이콘 파일 결정
            if sys.platform == "darwin":  # macOS
                icon_filename = "app_icon.icns"
            else:  # Windows, Linux
                icon_filename = "app_icon.ico"
            
            # 아이콘 파일 경로 결정
            if getattr(sys, 'frozen', False):
                # PyInstaller로 패키징된 경우
                if hasattr(sys, '_MEIPASS'):
                    # PyInstaller의 임시 폴더에서 찾기
                    icon_path = Path(sys._MEIPASS) / icon_filename
                else:
                    # Nuitka나 다른 패키징 도구의 경우
                    icon_path = Path(sys.executable).parent / icon_filename
            else:
                # 일반 스크립트로 실행된 경우
                icon_path = Path(__file__).parent / icon_filename
            
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                self.setWindowIcon(icon)
                
                # 애플리케이션 레벨에서도 아이콘 설정 (macOS Dock용)
                QApplication.instance().setWindowIcon(icon)
                
                logging.info(f"윈도우 아이콘 설정 완료: {icon_path}")
            else:
                logging.warning(f"아이콘 파일을 찾을 수 없습니다: {icon_path}")
                
        except Exception as e:
            logging.error(f"윈도우 아이콘 설정 실패: {e}")

    def _rebuild_folder_selection_ui(self):
        """기존 분류 폴더 UI를 제거하고 새로 생성하여 교체합니다."""
        if hasattr(self, 'category_folder_container') and self.category_folder_container:
            self.category_folder_container.setParent(None)
            self.control_layout.removeWidget(self.category_folder_container)
            
            self.category_folder_container.deleteLater()
            self.category_folder_container = None

        self.category_folder_container = self.setup_folder_selection_ui()

        try:
            # 구분선의 인덱스를 찾아서 그 바로 아래(+2, 구분선과 그 아래 spacing)에 삽입
            insertion_index = self.control_layout.indexOf(self.line_before_folders) + 2
            self.control_layout.insertWidget(insertion_index, self.category_folder_container)
        except Exception as e:
            # 예외 발생 시 (예: 구분선을 찾지 못함) 레이아웃의 끝에 추가 (안전 장치)
            logging.error(f"_rebuild_folder_selection_ui에서 삽입 위치 찾기 실패: {e}. 레이아웃 끝에 추가합니다.")
            self.control_layout.addWidget(self.category_folder_container)

        self.update_all_folder_labels_state()


    def on_folder_count_changed(self, index):
        """분류 폴더 개수 콤보박스 변경 시 호출되는 슬롯"""
        if index < 0: return
        
        new_count = self.folder_count_combo.itemData(index)
        if new_count is None or new_count == self.folder_count:
            return

        logging.info(f"분류 폴더 개수 변경: {self.folder_count} -> {new_count}")
        self.folder_count = new_count

        # self.target_folders 리스트 크기 조정
        current_len = len(self.target_folders)
        if new_count > current_len:
            # 늘어난 만큼 빈 문자열 추가
            self.target_folders.extend([""] * (new_count - current_len))
        elif new_count < current_len:
            # 줄어든 만큼 뒤에서부터 잘라냄
            self.target_folders = self.target_folders[:new_count]
            
        # UI 재구축
        self._rebuild_folder_selection_ui()
        
        # 변경된 상태 저장
        self.save_state()

    # === 폴더 경로 레이블 드래그 앤 드랍 관련 코드 시작 === #
    def dragEnterEvent(self, event):
        """드래그 진입 시 호출"""
        try:
            # 폴더만 허용
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if len(urls) == 1:  # 하나의 항목만 허용
                    file_path = urls[0].toLocalFile()
                    if file_path and Path(file_path).is_dir():
                        event.acceptProposedAction()
                        logging.debug(f"드래그 진입: 폴더 감지됨 - {file_path}")
                        return
            
            # 조건에 맞지 않으면 거부
            event.ignore()
            logging.debug("드래그 진입: 폴더가 아니거나 여러 항목 감지됨")
        except Exception as e:
            logging.error(f"dragEnterEvent 오류: {e}")
            event.ignore()

    def dragMoveEvent(self, event):
        """드래그 이동 시 호출"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if len(urls) == 1:
                    file_path = urls[0].toLocalFile()
                    if file_path and Path(file_path).is_dir():
                        # 현재 마우스 위치에서 타겟 레이블 찾기
                        pos = event.position().toPoint() if hasattr(event.position(), 'toPoint') else event.pos()
                        target_label, target_type = self._find_target_label_at_position(pos)
                        
                        # 폴더 유효성 검사
                        is_valid = self._validate_folder_for_target(file_path, target_type)
                        
                        # 이전 타겟과 다르면 스타일 복원
                        if self.drag_target_label and self.drag_target_label != target_label:
                            self._restore_original_style(self.drag_target_label)
                            self.drag_target_label = None
                        
                        # 새 타겟에 스타일 적용
                        if target_label and target_label != self.drag_target_label:
                            self._save_original_style(target_label)
                            if is_valid:
                                self._set_drag_accept_style(target_label)
                            else:
                                self._set_drag_reject_style(target_label)
                            self.drag_target_label = target_label
                        
                        event.acceptProposedAction()
                        return
            
            # 조건에 맞지 않으면 스타일 복원 후 거부
            if self.drag_target_label:
                self._restore_original_style(self.drag_target_label)
                self.drag_target_label = None
            event.ignore()
        except Exception as e:
            logging.error(f"dragMoveEvent 오류: {e}")
            event.ignore()

    def dragLeaveEvent(self, event):
        """드래그 벗어날 때 호출"""
        try:
            # 모든 스타일 복원
            if self.drag_target_label:
                self._restore_original_style(self.drag_target_label)
                self.drag_target_label = None
            logging.debug("드래그 벗어남: 스타일 복원됨")
        except Exception as e:
            logging.error(f"dragLeaveEvent 오류: {e}")

    def dropEvent(self, event):
        """드랍 시 호출"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if len(urls) == 1:
                    file_path = urls[0].toLocalFile()
                    if file_path and Path(file_path).is_dir():
                        # 현재 마우스 위치에서 타겟 레이블 찾기
                        pos = event.position().toPoint() if hasattr(event.position(), 'toPoint') else event.pos()
                        target_label, target_type = self._find_target_label_at_position(pos)
                        
                        # 스타일 복원
                        if self.drag_target_label:
                            self._restore_original_style(self.drag_target_label)
                            self.drag_target_label = None
                        
                        # 타겟에 따른 처리
                        success = self._handle_folder_drop(file_path, target_type)
                        
                        if success:
                            event.acceptProposedAction()
                            logging.info(f"폴더 드랍 성공: {file_path} -> {target_type}")
                        else:
                            event.ignore()
                            logging.warning(f"폴더 드랍 실패: {file_path} -> {target_type}")
                        return
            
            # 조건에 맞지 않으면 거부
            event.ignore()
            logging.debug("dropEvent: 유효하지 않은 드랍")
        except Exception as e:
            logging.error(f"dropEvent 오류: {e}")
            event.ignore()

    def _find_target_label_at_position(self, pos):
        """좌표에서 타겟 레이블과 타입을 찾기"""
        try:
            # 컨트롤 패널 내의 위젯에서 좌표 확인
            widget_at_pos = self.childAt(pos)
            if not widget_at_pos:
                return None, None
            
            # 부모 위젯들을 따라가며 타겟 레이블 찾기
            current_widget = widget_at_pos
            for _ in range(10):  # 최대 10단계까지 부모 탐색
                if current_widget is None:
                    break
                
                # JPG 폴더 레이블 확인
                if hasattr(self, 'folder_path_label') and current_widget == self.folder_path_label:
                    return self.folder_path_label, "image_folder"
                
                # RAW 폴더 레이블 확인
                if hasattr(self, 'raw_folder_path_label') and current_widget == self.raw_folder_path_label:
                    return self.raw_folder_path_label, "raw_folder"
                
                # 분류 폴더 레이블들 확인
                if hasattr(self, 'folder_path_labels'):
                    for i, label in enumerate(self.folder_path_labels):
                        if current_widget == label:
                            return label, f"category_folder_{i}"
                
                # 부모로 이동
                current_widget = current_widget.parent()
            
            return None, None
        except Exception as e:
            logging.error(f"_find_target_label_at_position 오류: {e}")
            return None, None

    def _validate_folder_for_target(self, folder_path, target_type):
        """타겟별 폴더 유효성 검사"""
        try:
            if not folder_path or not target_type:
                return False
            
            folder_path_obj = Path(folder_path)
            if not folder_path_obj.is_dir():
                return False
            
            if target_type == "image_folder":
                # 이미지 폴더: 지원하는 이미지 파일이 있는지 확인
                return self._has_supported_image_files(folder_path_obj)
            
            elif target_type == "raw_folder":
                # RAW 폴더: RAW 파일이 있는지 확인
                return self._has_raw_files(folder_path_obj)
            
            elif target_type.startswith("category_folder_"):
                # 분류 폴더: 모든 디렉토리 허용
                return True
            
            return False
        except Exception as e:
            logging.error(f"_validate_folder_for_target 오류: {e}")
            return False

    def _has_supported_image_files(self, folder_path):
        """폴더에 지원하는 이미지 파일이 있는지 확인"""
        try:
            for file_path in folder_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.supported_image_extensions:
                    return True
            return False
        except Exception as e:
            logging.debug(f"이미지 파일 확인 오류: {e}")
            return False

    def _has_raw_files(self, folder_path):
        """폴더에 RAW 파일이 있는지 확인"""
        try:
            for file_path in folder_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.raw_extensions:
                    return True
            return False
        except Exception as e:
            logging.debug(f"RAW 파일 확인 오류: {e}")
            return False

    def _save_original_style(self, widget):
        """원래 스타일 저장"""
        try:
            if widget:
                self.original_label_styles[widget] = widget.styleSheet()
        except Exception as e:
            logging.error(f"_save_original_style 오류: {e}")
