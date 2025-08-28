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



class ImageLoader(QObject):
    """이미지 로딩 및 캐싱을 관리하는 클래스"""

    imageLoaded = Signal(int, QPixmap, str)  # 인덱스, 픽스맵, 이미지 경로
    loadCompleted = Signal(QPixmap, str, int)  # pixmap, image_path, requested_index
    loadFailed = Signal(str, str, int)  # error_message, image_path, requested_index
    decodingFailedForFile = Signal(str) # 디코딩 실패 시 VibeCullingApp에 알리기 위한 새 시그널(실패한 파일 경로 전달)

     # 클래스 변수로 전역 전략 설정 (스레드 간 공유)
    _global_raw_strategy = "undetermined"
    _strategy_initialized = False  # 전략 초기화 여부 플래그 추가

    def __init__(self, parent=None, raw_extensions=None):
        super().__init__(parent)
        self.raw_extensions = raw_extensions or set()
        
        # 시스템 메모리 기반 캐시 크기 조정
        self.system_memory_gb = self.get_system_memory_gb()
        self.cache_limit = self.calculate_adaptive_cache_size()
        self.cache = self.create_lru_cache(self.cache_limit)

        # 디코딩 이력 추적 (중복 디코딩 방지용)
        self.recently_decoded = {}  # 파일명 -> 마지막 디코딩 시간
        self.decoding_cooldown = 30  # 초 단위 (이 시간 내 중복 디코딩 방지)

        # 주기적 캐시 건전성 확인 타이머 추가
        self.cache_health_timer = QTimer()
        self.cache_health_timer.setInterval(30000)  # 30초마다 캐시 건전성 확인
        self.cache_health_timer.timeout.connect(self.check_cache_health)
        self.cache_health_timer.start()
        
        # 마지막 캐시 동적 조정 시간 저장
        self.last_cache_adjustment = time.time()

        self.resource_manager = ResourceManager.instance()
        self.active_futures = []  # 현재 활성화된 로딩 작업 추적
        self.last_requested_page = -1  # 마지막으로 요청된 페이지
        self._raw_load_strategy = "preview" # VibeCullingApp에서 명시적으로 설정하기 전까지의 기본값
        self.load_executor = self.resource_manager.imaging_thread_pool
        
        # RAW 디코딩 보류 중인 파일 추적 
        self.pending_raw_decoding = set()

        # 전략 결정을 위한 락 추가
        self._strategy_lock = threading.Lock()

    def cancel_loading(self):
        """진행 중인 모든 이미지 로딩 작업을 취소합니다."""
        for future in self.active_futures:
            future.cancel()
        self.active_futures.clear()
        logging.info("ImageLoader: 활성 로딩 작업이 취소되었습니다.")

    def get_system_memory_gb(self):
        """시스템 메모리 크기 확인 (GB)"""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 * 1024 * 1024)
        except:
            return 8.0  # 기본값 8GB
        
        
    def calculate_adaptive_cache_size(self):
        """시스템 프로필에 맞는 캐시 크기를 가져옵니다."""
        # HardwareProfileManager가 이미 초기화되었다고 가정
        size = HardwareProfileManager.get("cache_size_images")
        logging.info(f"ImageLoader: 캐시 크기 설정 -> {size}개 이미지 ({HardwareProfileManager.get_current_profile_name()} 프로필)")
        return size
    
    def create_lru_cache(self, max_size): # 이 함수는 OrderedDict를 반환하며, 실제 크기 제한은 _add_to_cache에서 self.cache_limit을 사용하여 관리됩니다.
        """LRU 캐시 생성 (OrderedDict 기반)"""
        from collections import OrderedDict
        return OrderedDict()
    
    def check_cache_health(self):
        """캐시 상태 확인 및 시스템 프로필에 따라 동적으로 축소"""
        try:
            memory_percent = psutil.virtual_memory().percent
            current_time = time.time()

            # HardwareProfileManager에서 현재 프로필의 임계값과 비율 가져오기
            thresholds = HardwareProfileManager.get("memory_thresholds")
            ratios = HardwareProfileManager.get("cache_clear_ratios")
            
            # 임시 쿨다운 (향후 프로필에 추가 가능)
            cooldowns = {"danger": 5, "warning": 10, "caution": 30}

            level = None
            if memory_percent > thresholds["danger"]: level = "danger"
            elif memory_percent > thresholds["warning"]: level = "warning"
            elif memory_percent > thresholds["caution"]: level = "caution"

            if level and (current_time - self.last_cache_adjustment > cooldowns[level]):
                reduction_count = max(1, int(len(self.cache) * ratios[level]))
                removed_count = self._remove_oldest_items_from_cache(reduction_count)
                
                log_level_map = {"danger": logging.CRITICAL, "warning": logging.WARNING, "caution": logging.INFO}
                logging.log(
                    log_level_map[level],
                    f"메모리 사용량 {level.upper()} 수준 ({memory_percent}%): 캐시 {ratios[level]*100:.0f}% 정리 ({removed_count}개 항목 제거)"
                )
                
                self.last_cache_adjustment = current_time
                gc.collect()

        except Exception as e:
            if "psutil" not in str(e):
                logging.warning(f"check_cache_health에서 예외 발생: {e}")

    def _remove_oldest_items_from_cache(self, count):
        """캐시에서 가장 오래된 항목 제거하되, 현재 이미지와 인접 이미지는 보존"""
        if not self.cache or count <= 0:
            return 0
            
        # 현재 이미지 경로 및 인접 이미지 경로 확인 (보존 대상)
        preserved_paths = set()
        
        # 1. 현재 표시 중인 이미지나 그리드에 표시 중인 이미지 보존
        if hasattr(self, 'current_image_index') and self.current_image_index >= 0:
            if hasattr(self, 'image_files') and 0 <= self.current_image_index < len(self.image_files):
                current_path = str(self.image_files[self.current_image_index])
                preserved_paths.add(current_path)
                
                # 현재 이미지 주변 이미지도 보존 (앞뒤 3개씩)
                for offset in range(-3, 4):
                    if offset == 0:
                        continue
                    idx = self.current_image_index + offset
                    if 0 <= idx < len(self.image_files):
                        preserved_paths.add(str(self.image_files[idx]))
        
        # 2. 가장 오래된 항목부터 제거하되, 보존 대상은 제외
        items_to_remove = []
        items_removed = 0
        
        for key in list(self.cache.keys()):
            if items_removed >= count:
                break
                
            if key not in preserved_paths:
                items_to_remove.append(key)
                items_removed += 1
        
        # 3. 실제 캐시에서 제거
        for key in items_to_remove:
            del self.cache[key]
            
        return items_removed  # 실제 제거된 항목 수 반환


    def cancel_all_raw_decoding(self):
        """진행 중인 모든 RAW 디코딩 작업 취소"""
        # 보류 중인 RAW 디코딩 작업 목록 초기화
        self.pending_raw_decoding.clear()
        
        # 캐시와 전략 초기화
        self._raw_load_strategy = "preview"
        logging.info("모든 RAW 디코딩 작업 취소됨, 인스턴스 전략 초기화됨")

    def check_decoder_results(self):
        """멀티프로세스 RAW 디코더의 결과를 주기적으로 확인"""
        # 리소스 매니저를 통한 접근으로 변경
        self.resource_manager.process_raw_results(10)

    def _add_to_cache(self, file_path, pixmap):
        """PixMap을 LRU 방식으로 캐시에 추가"""
        if pixmap and not pixmap.isNull():
            # 캐시 크기 제한 확인
            while len(self.cache) >= self.cache_limit:
                # 가장 오래전에 사용된 항목 제거 (OrderedDict의 첫 번째 항목)
                try:
                    self.cache.popitem(last=False)
                except:
                    break  # 캐시가 비어있는 경우 예외 처리
                    
            # 새 항목 추가 또는 기존 항목 갱신 (최근 사용됨으로 표시)
            self.cache[file_path] = pixmap
            # 항목을 맨 뒤로 이동 (최근 사용)
            self.cache.move_to_end(file_path)
      
    def _load_raw_preview_with_orientation(self, file_path):
        try:
            with rawpy.imread(file_path) as raw:
                try:
                    thumb = raw.extract_thumb()
                    thumb_image = None
                    preview_width, preview_height = None, None
                    orientation = 1  # 기본 방향

                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        # JPEG 썸네일 처리
                        thumb_data = thumb.data
                        thumb_image = Image.open(io.BytesIO(thumb_data))
                        preview_width, preview_height = thumb_image.size

                        # EXIF 방향 정보 추출 시도
                        try:
                            exif_data = thumb_image._getexif()
                            if exif_data and 274 in exif_data:  # 274는 Orientation 태그
                                orientation = exif_data[274]
                        except:
                            orientation = 1  # 실패 시 기본값

                    elif thumb.format == rawpy.ThumbFormat.BITMAP:
                        # 비트맵 썸네일 처리
                        thumb_image = Image.fromarray(thumb.data)
                        preview_width, preview_height = thumb_image.size
                    
                    if thumb_image:
                        # 방향에 따라 이미지 회전
                        if orientation > 1:
                            rotation_methods = {
                                2: Image.FLIP_LEFT_RIGHT,
                                3: Image.ROTATE_180,
                                4: Image.FLIP_TOP_BOTTOM,
                                5: Image.TRANSPOSE,
                                6: Image.ROTATE_270,
                                7: Image.TRANSVERSE,
                                8: Image.ROTATE_90
                            }
                            if orientation in rotation_methods:
                                thumb_image = thumb_image.transpose(rotation_methods[orientation])
                        
                        # PIL Image를 QImage로 수동 변환 (ImageQt 사용하지 않음)
                        if thumb_image.mode == 'P' or thumb_image.mode == 'RGBA':
                            thumb_image = thumb_image.convert('RGBA')
                            img_format = QImage.Format_RGBA8888
                            bytes_per_pixel = 4
                        elif thumb_image.mode != 'RGB':
                            thumb_image = thumb_image.convert('RGB')
                            img_format = QImage.Format_RGB888
                            bytes_per_pixel = 3
                        else:
                            img_format = QImage.Format_RGB888
                            bytes_per_pixel = 3
                        
                        data = thumb_image.tobytes('raw', thumb_image.mode)
                        qimage = QImage(
                            data,
                            thumb_image.width,
                            thumb_image.height,
                            thumb_image.width * bytes_per_pixel,
                            img_format
                        )
                        
                        pixmap = QPixmap.fromImage(qimage)
                        
                        if pixmap and not pixmap.isNull():
                            logging.info(f"내장 미리보기 로드 성공 ({Path(file_path).name})")
                            return pixmap, preview_width, preview_height  # Return pixmap and dimensions
                        else:
                            raise ValueError("미리보기 QPixmap 변환 실패")
                    else:
                        raise rawpy.LibRawUnsupportedThumbnailError(f"지원하지 않는 미리보기 형식: {thumb.format}")

                except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError) as e_thumb:
                    logging.error(f"내장 미리보기 없음/지원안함 ({Path(file_path).name}): {e_thumb}")
                    return None, None, None  # Return None for all on failure
                except Exception as e_inner:
                    logging.error(f"미리보기 처리 중 오류 ({Path(file_path).name}): {e_inner}")
                    return None, None, None  # Return None for all on failure

        except (rawpy.LibRawIOError, rawpy.LibRawFileUnsupportedError, Exception) as e:
            logging.error(f"RAW 파일 읽기 오류 (미리보기 시도 중) ({Path(file_path).name}): {e}")
            return None, None, None  # Return None for all on failure

        # Should not be reached, but as fallback
        return None, None, None
    
    def load_image_with_orientation(self, file_path, strategy_override=None):
        """EXIF 방향 및 ICC 색상 프로파일을 고려하여 이미지를 올바른 방향과 색상으로 로드합니다."""
        logging.debug(f"ImageLoader ({id(self)}): load_image_with_orientation 호출됨. 파일: {Path(file_path).name}, 내부 전략: {self._raw_load_strategy}, 오버라이드: {strategy_override}")
        if not ResourceManager.instance()._running:
            logging.info(f"ImageLoader.load_image_with_orientation: ResourceManager 종료 중, 로드 중단 ({Path(file_path).name})")
            return QPixmap()
        
        if strategy_override is None and file_path in self.cache:
            self.cache.move_to_end(file_path)
            return self.cache[file_path]

        file_path_obj = Path(file_path)
        is_raw = file_path_obj.suffix.lower() in self.raw_extensions
        pixmap = QPixmap()

        if is_raw:
            # RAW 파일 처리는 _load_image_task -> _on_raw_decoded_for_display에서 처리됩니다.
            # 이 함수에서는 기존 로직을 유지합니다.
            current_processing_method = strategy_override if strategy_override else self._raw_load_strategy
            if current_processing_method == "preview":
                preview_pixmap_result, _, _ = self._load_raw_preview_with_orientation(file_path)
                pixmap = preview_pixmap_result if preview_pixmap_result and not preview_pixmap_result.isNull() else QPixmap()
            elif current_processing_method == "decode":
                # 실제 디코딩은 비동기로 처리되므로 여기서는 플레이스홀더나 빈 QPixmap을 반환할 수 있습니다.
                # 이 경로는 주로 썸네일 생성 등 동기적 호출에서 사용될 수 있습니다.
                try:
                    with rawpy.imread(file_path) as raw:
                        rgb = raw.postprocess(use_camera_wb=True, output_bps=8)
                        height, width, _ = rgb.shape
                        qimage = QImage(rgb.data, width, height, width * 3, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimage)
                except Exception as e:
                    logging.error(f"RAW 직접 디코딩 실패 (동기 호출): {e}")
                    pixmap = QPixmap()
            if pixmap and not pixmap.isNull() and strategy_override is None:
                self._add_to_cache(file_path, pixmap)
            return pixmap
        else:
            # --- 일반 이미지 (JPG, HEIC 등) 색상 관리 로직 ---
            try:
                if not ResourceManager.instance()._running: return QPixmap()
                
                with open(file_path, 'rb') as f:
                    image = Image.open(f)
                    image.load()

                # 1. 이미지의 ICC 프로파일 추출
                icc_profile = image.info.get('icc_profile')
                source_color_space = None
                if icc_profile:
                    try:
                        source_color_space = QColorSpace.fromIccProfile(icc_profile)
                        if not source_color_space.isValid():
                            logging.warning(f"이미지의 ICC 프로파일이 유효하지 않습니다: {file_path_obj.name}. sRGB로 간주합니다.")
                            source_color_space = QColorSpace(QColorSpace.SRgb)
                    except Exception as e:
                        logging.warning(f"ICC 프로파일로 QColorSpace 생성 실패: {e}. sRGB로 간주합니다.")
                        source_color_space = QColorSpace(QColorSpace.SRgb)
                else:
                    # 프로파일이 없으면 sRGB로 간주 (웹 표준)
                    source_color_space = QColorSpace(QColorSpace.SRgb)
                
                # 2. EXIF 방향 정보에 따라 이미지 회전
                orientation = 1
                if hasattr(image, 'getexif'):
                    exif = image.getexif()
                    if exif and 0x0112 in exif: orientation = exif[0x0112]
                if orientation > 1:
                    # (회전 로직은 기존과 동일)
                    if orientation == 2: image = image.transpose(Image.FLIP_LEFT_RIGHT)
                    elif orientation == 3: image = image.transpose(Image.ROTATE_180)
                    elif orientation == 4: image = image.transpose(Image.FLIP_TOP_BOTTOM)
                    elif orientation == 5: image = image.transpose(Image.TRANSPOSE)
                    elif orientation == 6: image = image.transpose(Image.ROTATE_270)
                    elif orientation == 7: image = image.transpose(Image.TRANSVERSE)
                    elif orientation == 8: image = image.transpose(Image.ROTATE_90)
                
                # 3. QImage로 변환
                if image.mode == 'P' or image.mode == 'RGBA': image = image.convert('RGBA')
                elif image.mode != 'RGB': image = image.convert('RGB')
                img_format = QImage.Format_RGBA8888 if image.mode == 'RGBA' else QImage.Format_RGB888
                bytes_per_pixel = 4 if image.mode == 'RGBA' else 3
                data = image.tobytes('raw', image.mode)
                qimage = QImage(data, image.width, image.height, image.width * bytes_per_pixel, img_format)

                # 4. QImage에 소스 색상 공간(ICC 프로파일) 설정
                if qimage and not qimage.isNull() and source_color_space:
                    qimage.setColorSpace(source_color_space)

                pixmap = QPixmap.fromImage(qimage)
                if pixmap and not pixmap.isNull():
                    self._add_to_cache(file_path, pixmap)
                    return pixmap
                else:
                    return QPixmap()
            except Exception as e_img:
                logging.error(f"일반 이미지 처리 오류 ({file_path_obj.name}): {e_img}")
                return QPixmap()

    def set_raw_load_strategy(self, strategy: str):
        """이 ImageLoader 인스턴스의 RAW 처리 방식을 설정합니다 ('preview' 또는 'decode')."""
        if strategy in ["preview", "decode"]:
            old_strategy = self._raw_load_strategy
            self._raw_load_strategy = strategy
            logging.info(f"ImageLoader ({id(self)}): RAW 처리 방식 변경됨: {old_strategy} -> {self._raw_load_strategy}")
        else:
            logging.warning(f"ImageLoader ({id(self)}): 알 수 없는 RAW 처리 방식 '{strategy}'. 변경 안 함. 현재: {self._raw_load_strategy}")
    
    def _clean_old_decoding_history(self, current_time, max_entries=50):
        """오래된 디코딩 이력 정리 (메모리 관리)"""
        if len(self.recently_decoded) <= max_entries:
            return
            
        # 현재 시간으로부터 일정 시간이 지난 항목 제거
        old_threshold = current_time - (self.decoding_cooldown * 2)
        keys_to_remove = []
        
        for file_name, decode_time in self.recently_decoded.items():
            if decode_time < old_threshold:
                keys_to_remove.append(file_name)
        
        # 실제 항목 제거
        for key in keys_to_remove:
            del self.recently_decoded[key]
            
        # 여전히 너무 많은 항목이 있으면 가장 오래된 것부터 제거
        if len(self.recently_decoded) > max_entries:
            items = sorted(self.recently_decoded.items(), key=lambda x: x[1])
            to_remove = items[:len(items) - max_entries]
            for file_name, _ in to_remove:
                del self.recently_decoded[file_name]

    def preload_page(self, image_files, page_start_index, cells_per_page, strategy_override=None):
        """특정 페이지의 이미지를 미리 로딩"""
        self.last_requested_page = page_start_index // cells_per_page
        for future in self.active_futures:
            future.cancel()
        self.active_futures.clear()
        end_idx = min(page_start_index + cells_per_page, len(image_files))
        futures = []
        for i in range(page_start_index, end_idx):
            if i < 0 or i >= len(image_files):
                continue
            img_path = str(image_files[i])
            if img_path in self.cache:
                pixmap = self.cache[img_path]
                self.imageLoaded.emit(i - page_start_index, pixmap, img_path)
            else:
                future = self.load_executor.submit(self._load_and_signal, i - page_start_index, img_path, strategy_override)
                futures.append(future)
        self.active_futures = futures
        next_page_start = page_start_index + cells_per_page
        if next_page_start < len(image_files):
            next_end = min(next_page_start + cells_per_page, len(image_files))
            for i in range(next_page_start, next_end):
                if i >= len(image_files):
                    break
                img_path = str(image_files[i])
                if img_path not in self.cache:
                    future = self.load_executor.submit(self._preload_image, img_path, strategy_override)
                    self.active_futures.append(future)
    
    def _load_and_signal(self, cell_index, img_path, strategy_override=None):
        """이미지 로드 후 시그널 발생"""
        try:
            pixmap = self.load_image_with_orientation(img_path, strategy_override=strategy_override)
            self.imageLoaded.emit(cell_index, pixmap, img_path)
            return True
        except Exception as e:
            logging.error(f"이미지 로드 오류 (인덱스 {cell_index}): {e}")
            return False
    
    def _preload_image(self, img_path, strategy_override=None):
        """이미지 미리 로드 (시그널 없음)"""
        try:
            self.load_image_with_orientation(img_path, strategy_override=strategy_override)
            return True
        except:
            return False
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        logging.info(f"ImageLoader ({id(self)}): Cache cleared. RAW load strategy '{self._raw_load_strategy}' is preserved.")
        
        # 활성 로딩 작업도 취소
        for future in self.active_futures:
            future.cancel()
        self.active_futures.clear()
        logging.info(f"ImageLoader ({id(self)}): Active loading futures cleared.")

    def set_raw_load_strategy(self, strategy: str):
        """이 ImageLoader 인스턴스의 RAW 처리 방식을 설정합니다 ('preview' 또는 'decode')."""
        if strategy in ["preview", "decode"]:
            self._raw_load_strategy = strategy
            logging.info(f"ImageLoader: RAW 처리 방식 설정됨: {strategy}")
        else:
            logging.warning(f"ImageLoader: 알 수 없는 RAW 처리 방식 '{strategy}'. 변경 안 함.")

