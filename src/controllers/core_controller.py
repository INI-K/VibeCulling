"""
코어 컨트롤러 모듈
VibeCulling 애플리케이션의 핵심 클래스 정의와 초기화
"""

# Standard library imports
import os
import gc
import json
import shutil
import subprocess
import sys
import threading
import time
import logging
from datetime import datetime
from functools import partial
from pathlib import Path
import platform

# Third-party imports  
import numpy as np
import psutil
from PIL import Image

# PySide6 imports
from PySide6.QtCore import (
    Qt, QEvent, QObject, QPoint, Slot, QTimer, QThread, QUrl,
    Signal, QItemSelectionModel, QRect, QPointF, QMimeData, QSize
)
from PySide6.QtGui import (
    QAction, QColor, QFont, QGuiApplication, QImage, QImageReader,
    QKeyEvent, QMouseEvent, QPainter, QPalette, QIcon, QPen, QPixmap,
    QTransform, QWheelEvent, QFontMetrics, QKeySequence, QDrag,
    QDesktopServices
)
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSplitter,
    QTextBrowser, QVBoxLayout, QWidget, QToolTip, QInputDialog,
    QLineEdit, QSpinBox, QProgressDialog, QLayout
)

# 모듈 imports
from ..config import (
    UIScaleManager, ThemeManager, HardwareProfileManager,
    LanguageManager, DateFormatManager
)
from ..models import ResourceManager, ThumbnailModel, ImageLoader
from ..views import *
from ..workers import ExifWorker, FolderLoaderWorker, CopyWorker
from ..utils import get_app_data_dir, format_camera_name


class VibeCullingApp(QMainWindow):
    STATE_FILE = "vibeculling_data.json" # 상태 저장 파일 이름 정의
    
    # 단축키 정의 (두 함수에서 공통으로 사용)
    SHORTCUT_DEFINITIONS = [
        ("group", "탐색"),
        ("key", "WASD / 방향키", "사진 넘기기"),
        ("key", "Shift + WASD/방향키", "뷰포트 이동 (확대 중에)"),
        ("key", "Shift + A/D", "이전/다음 페이지 (그리드 모드)"),
        ("key", "Enter", "사진 목록 보기"),
        ("key", "F5", "폴더 새로고침"),
        
        ("group", "보기 설정"),
        ("key", "F1 / F2 / F3", "줌 모드 변경 (Fit / 100% / 가변)"),
        ("key", "Space", "줌 전환 (Fit/100%) 또는 그리드에서 확대"),
        ("key", "ESC", "줌 아웃 또는 그리드 복귀"),
        ("key", "Z [Zoom-out]", "줌 아웃 (가변 모드)"),
        ("key", "X [eXpand]", "줌 인 (가변 모드)"),
        ("key", "R [Reset]", "뷰포트 중앙 정렬"),
        ("key", "G [Grid]", "그리드 모드 켜기/끄기"),
        ("key", "C [Compare]", "A | B 비교 모드 켜기/끄기"),
        ("key", "Q / E (* 꾹 누르기)", "이미지 회전 (반시계/시계)"),

        ("group", "파일 작업"),
        ("key", "1 ~ 9", "지정한 폴더로 사진 이동"),
        ("key", "Shift + 1 ~ 9", "지정한 폴더로 사진 복사"),
        ("key", "Ctrl + Z", "파일 이동 취소 (Undo)"),
        ("key", "Ctrl + Y / Ctrl + Shift + Z", "파일 이동 다시 실행 (Redo)"),
        ("key", "Ctrl + A", "페이지 전체 선택 (그리드 모드)"),
        ("key", "Delete", "작업 상태 초기화"),
    ]

    # macOS용 단축키 정의
    SHORTCUT_DEFINITIONS_MAC = [
        ("group", "탐색"),
        ("key", "WASD / 방향키", "사진 넘기기"),
        ("key", "Shift + WASD/방향키", "뷰포트 이동 (확대 중에)"),
        ("key", "Shift + A/D", "이전/다음 페이지 (그리드 모드)"),
        ("key", "Enter", "사진 목록 보기"),
        ("key", "F5", "폴더 새로고침"),
        
        ("group", "보기 설정"),
        ("key", "F1 / F2 / F3", "줌 모드 변경 (Fit / 100% / 가변)"),
        ("key", "Space", "줌 전환 (Fit/100%) 또는 그리드에서 확대"),
        ("key", "ESC", "줌 아웃 또는 그리드 복귀"),
        ("key", "Z [Zoom-out]", "줌 아웃 (가변 모드)"),
        ("key", "X [eXpand]", "줌 인 (가변 모드)"),
        ("key", "R [Reset]", "뷰포트 중앙 정렬"),
        ("key", "G [Grid]", "그리드 모드 켜기/끄기"),
        ("key", "C [Compare]", "A | B 비교 모드 켜기/끄기"),
        ("key", "Q / E (* 꾹 누르기)", "이미지 회전 (반시계/시계)"),

        ("group", "파일 작업"),
        ("key", "1 ~ 9", "지정한 폴더로 사진 이동"),
        ("key", "Shift + 1~9", "지정한 폴더로 사진 복사"),
        ("key", "Cmd + Z", "파일 이동 취소 (Undo)"),
        ("key", "Cmd + Y / Cmd + Shift + Z", "파일 이동 다시 실행 (Redo)"),
        ("key", "Cmd + A", "페이지 전체 선택 (그리드 모드)"),
        ("key", "Delete", "작업 상태 초기화"),
    ]

    KEY_MAP_SHIFT_NUMBER = {
        Qt.Key_Exclam: Qt.Key_1,      # ! -> 1
        Qt.Key_At: Qt.Key_2,          # @ -> 2
        Qt.Key_NumberSign: Qt.Key_3,  # # -> 3
        Qt.Key_Dollar: Qt.Key_4,      # $ -> 4
        Qt.Key_Percent: Qt.Key_5,     # % -> 5
        Qt.Key_AsciiCircum: Qt.Key_6, # ^ -> 6
        Qt.Key_Ampersand: Qt.Key_7,   # & -> 7
        Qt.Key_Asterisk: Qt.Key_8,    # * -> 8
        Qt.Key_ParenLeft: Qt.Key_9,   # ( -> 9
    }

    def __init__(self):
        super().__init__()
        
        # 앱 제목 설정
        self.setWindowTitle("VibeCulling")

        # 크로스 플랫폼 윈도우 아이콘 설정
        self.set_window_icon()

        self.copy_queue = queue.Queue() # 복사 작업을 위한 FIFO 큐
        self._setup_copy_worker()       # 백그라운드 복사 워커 스레드 설정
        
        # 내부 변수 초기화
        self.current_folder = ""
        self.raw_folder = ""
        self.image_files = []
        self.supported_image_extensions = {
            '.jpg', '.jpeg'
        }
        self.raw_files = {}  # 키: 기본 파일명, 값: RAW 파일 경로
        self.is_raw_only_mode = False # RAW 단독 로드 모드인지 나타내는 플래그
        self.raw_extensions = {'.arw', '.crw', '.dng', '.cr2', '.cr3', '.nef', 
                             '.nrw', '.raf', '.srw', '.srf', '.sr2', '.rw2', 
                             '.rwl', '.x3f', '.gpr', '.orf', '.pef', '.ptx', 
                             '.3fr', '.fff', '.mef', '.iiq', '.braw', '.ari', '.r3d'}
        self.current_image_index = -1
        self.move_raw_files = True  # RAW 파일 이동 여부 (기본값: True)
        self.folder_count = 3  # 기본 폴더 개수 (load_state에서 덮어쓸 값)
        self.target_folders = [""] * self.folder_count  # folder_count에 따라 동적으로 리스트 생성
        self.zoom_mode = "Fit"  # 기본 확대 모드: "Fit", "100%", "Spin"
        self.last_active_zoom_mode = "100%" # 기본 확대 모드는 100%
        self.zoom_spin_value = 2.0  # 기본 200% (2.0 배율)
        self.original_pixmap = None  # 원본 이미지 pixmap
        self.panning = False  # 패닝 모드 여부
        self.pan_last_mouse_pos = QPointF(0, 0)  # 패닝 중 마우스의 마지막 위치 (QPointF로 정밀도 향상)
        self.scroll_pos = QPoint(0, 0)  # 스크롤 위치 

        self.control_panel_on_right = False # 기본값: 왼쪽 (False)

        self.viewport_move_speed = 5 # 뷰포트 이동 속도 (1~10), 기본값 5
        self.mouse_wheel_action = "photo_navigation"  # 마우스 휠 동작: "photo_navigation" 또는 "none"

        self.mouse_wheel_sensitivity = 1 # 휠 민감도 (1, 2, 3)
        self.mouse_wheel_accumulator = 0 # 휠 틱 누적 카운터
        self.last_wheel_direction = 0    # 마지막 휠 방향 (1: 위, -1: 아래)
        self.wheel_reset_timer = QTimer(self)
        self.wheel_reset_timer.setSingleShot(True)  # 한 번만 실행
        self.wheel_reset_timer.setInterval(1000)    # 1초 (1000ms)
        self.wheel_reset_timer.timeout.connect(self._reset_wheel_accumulator)

        self.mouse_pan_sensitivity = 1.5  # 마우스 패닝 감도 (1.0, 1.5, 2.0 등)

        self.last_processed_camera_model = None
        self.show_grid_filenames = True  # 그리드 모드에서 파일명 표시 여부 (기본값: True)

        self.image_processing = False  # 이미지 처리 중 여부

        # --- 회전 기능 변수 추가 ---
        self.image_rotations = {}  # {image_path: angle} 형식의 딕셔너리
        self.key_press_start_time = {} # Q/E 키 누름 시작 시간 기록용
        self.rotation_B = 0 # B 캔버스 전용 회전 각도

        # --- 세션 저장을 위한 딕셔너리 ---
        # 형식: {"세션이름": {상태정보 딕셔너리}}
        self.saved_sessions = {} # 이전 self.saved_workspaces 에서 이름 변경
        # load_state에서 로드되므로 여기서 _load_saved_sessions 호출 불필요
        
        # 세션 관리 팝업 인스턴스 (중복 생성 방지용)
        self.session_management_popup = None

        # --- 뷰포트 부드러운 이동을 위한 변수 ---
        self.viewport_move_timer = QTimer(self)
        self.viewport_move_timer.setInterval(16) # 약 60 FPS (1000ms / 60 ~= 16ms)
        self.viewport_move_timer.timeout.connect(self.smooth_viewport_move)
        self.pressed_keys_for_viewport = set() # 현재 뷰포트 이동을 위해 눌린 키 저장

        # 뷰포트 저장 및 복구를 위한 변수
        self.viewport_focus_by_orientation = {
            # "landscape": {"rel_center": QPointF(0.5, 0.5), "zoom_level": "100%"},
            # "portrait": {"rel_center": QPointF(0.5, 0.5), "zoom_level": "100%"}
        } # 초기에는 비어있거나 기본값으로 채울 수 있음

        self.current_active_rel_center = QPointF(0.5, 0.5)
        self.current_active_zoom_level = "Fit"
        self.zoom_change_trigger = None        
        # self.zoom_triggered_by_double_click = False # 이전 플래그 -> self.zoom_change_trigger로 대체
        # 현재 활성화된(보여지고 있는) 뷰포트의 상대 중심과 줌 레벨
        # 이 정보는 사진 변경 시 다음 사진으로 "이어질" 수 있음
        self.current_active_rel_center = QPointF(0.5, 0.5)
        self.current_active_zoom_level = "Fit" # 초기값은 Fit
        self.zoom_change_trigger = None # "double_click", "space_key_to_zoom", "radio_button", "photo_change_same_orientation", "photo_change_diff_orientation"

        # 메모리 모니터링 및 자동 조정을 위한 타이머
        self.memory_monitor_timer = QTimer(self)
        self.memory_monitor_timer.setInterval(10000)  # 10초마다 확인
        self.memory_monitor_timer.timeout.connect(self.check_memory_usage)
        self.memory_monitor_timer.start()

        # current_image_index 주기적 자동동저장을 위한
        self.state_save_timer = QTimer(self)
        self.state_save_timer.setSingleShot(True) # 한 번만 실행되도록 설정
        self.state_save_timer.setInterval(5000)  # 5초 (5000ms)
        self.state_save_timer.timeout.connect(self._trigger_state_save_for_index) # 새 슬롯 연결

        # 시스템 사양 검사
        self.system_memory_gb = self.get_system_memory_gb()
        self.system_cores = cpu_count()

        # 파일 이동 기록 (Undo/Redo 용)
        self.move_history = [] # 이동 기록을 저장할 리스트
        self.history_pointer = -1 # 현재 히스토리 위치 (-1은 기록 없음)
        self.max_history = 10 # 최대 저장할 히스토리 개수

        # Grid 관련 변수 추가
        self.grid_mode = "Off" # 'Off', '2x2', '3x3'
        self.last_active_grid_mode = "2x2"  # 마지막으로 활성화된 그리드 모드 저장 (기본값 "2x2")
        self.current_grid_index = 0 # 현재 선택된 그리드 셀 인덱스 (0부터 시작)
        self.grid_page_start_index = 0 # 현재 그리드 페이지의 시작 이미지 인덱스
        self.previous_grid_mode = None # 이전 그리드 모드 저장 변수
        self.grid_layout = None # 그리드 레이아웃 객체
        self.grid_labels = []   # 그리드 셀 QLabel 목록

        # 다중 선택 관리 변수 추가
        self.selected_grid_indices = set()  # 선택된 그리드 셀 인덱스들 (페이지 내 상대 인덱스)
        self.primary_selected_index = -1  # 첫 번째로 선택된 이미지의 인덱스 (파일 정보 표시용)
        self.last_single_click_index = -1  # Shift+클릭 범위 선택을 위한 마지막 단일 클릭 인덱스

        # 리소스 매니저 초기화
        self.resource_manager = ResourceManager.instance()

        # === 유휴 프리로더(Idle Preloader) 타이머 추가 ===
        self.idle_preload_timer = QTimer(self)
        self.idle_preload_timer.setSingleShot(True)
        # HardwareProfileManager에서 유휴 로딩 관련 설정 가져오기
        self.idle_preload_enabled = HardwareProfileManager.get("idle_preload_enabled")
        if self.idle_preload_enabled:
            idle_interval = HardwareProfileManager.get("idle_interval_ms")
            self.idle_preload_timer.setInterval(idle_interval)
            self.idle_preload_timer.timeout.connect(self.start_idle_preloading)
            self.is_idle_preloading_active = False # 진행 중 작업 추적 플래그
            logging.info(f"유휴 프리로더 활성화 (유휴 시간: {idle_interval}ms)")
        else:
            logging.info("유휴 프리로더 비활성화 (Conservative 프로필)")

        # RAW 디코더 결과 처리 타이머 
        if not hasattr(self, 'raw_result_processor_timer'): # 중복 생성 방지
            self.raw_result_processor_timer = QTimer(self)
            self.raw_result_processor_timer.setInterval(100)  # 0.1초마다 결과 확인 (조정 가능)
            self.raw_result_processor_timer.timeout.connect(self.process_pending_raw_results)
            self.raw_result_processor_timer.start()

        # --- 그리드 썸네일 사전 생성을 위한 변수 추가 ---
        self.grid_thumbnail_cache = {"2x2": {}, "3x3": {}, "4x4": {}}
        self.active_thumbnail_futures = [] # 현재 실행 중인 백그라운드 썸네일 작업 추적
        self.grid_thumbnail_executor = ThreadPoolExecutor(
        max_workers=2, 
        thread_name_prefix="GridThumbnail")

        # 이미지 방향 추적을 위한 변수 추가
        self.current_image_orientation = None  # "landscape" 또는 "portrait"
        self.previous_image_orientation = None
        

        # 미니맵 관련 변수
        self.minimap_visible = False  # 미니맵 표시 여부
        self.minimap_base_size = 230  # 미니맵 기본 크기 (배율 적용 전)
        self.minimap_max_size = self.get_scaled_size(self.minimap_base_size)  # UI 배율 적용한 최대 크기
        self.minimap_width = self.minimap_max_size
        self.minimap_height = int(self.minimap_max_size / 1.5)  # 3:2 비율 기준
        self.minimap_pixmap = None     # 미니맵용 축소 이미지
        self.minimap_viewbox = None    # 미니맵 뷰박스 정보
        self.minimap_dragging = False  # 미니맵 드래그 중 여부
        self.minimap_viewbox_dragging = False  # 미니맵 뷰박스 드래그 중 여부
        self.minimap_drag_start = QPoint(0, 0)  # 미니맵 드래그 시작 위치
        self.last_event_time = 0  # 이벤트 스로틀링을 위한 타임스탬프
        
        # 미니맵 뷰박스 캐싱 변수
        self.cached_viewbox_params = {
            "zoom": None, 
            "img_pos": None, 
            "canvas_size": None
        }
        
        # 이미지 캐싱 관련 변수 추가
        self.fit_pixmap_cache = {}  # 크기별로 Fit 이미지 캐싱
        self.last_fit_size = (0, 0)
        
        # 이미지 로더/캐시 추가
        self.image_loader = ImageLoader(raw_extensions=self.raw_extensions)
        self.image_loader.imageLoaded.connect(self.on_image_loaded)
        self.image_loader.loadCompleted.connect(self._on_image_loaded_for_display)  # 새 시그널 연결
        self.image_loader.loadFailed.connect(self._on_image_load_failed)  # 새 시그널 연결
        self.image_loader.decodingFailedForFile.connect(self.handle_raw_decoding_failure) # 새 시그널 연결

        self.is_input_dialog_active = False # 플래그 초기화 (세션창 QInputDialog가 떠 있는지 여부)
        
        # 그리드 로딩 시 빠른 표시를 위한 플레이스홀더 이미지
        self.placeholder_pixmap = QPixmap(100, 100)
        self.placeholder_pixmap.fill(QColor("#222222"))

        # === 이미지→폴더 드래그 앤 드롭 관련 변수 ===
        self.drag_start_pos = QPoint(0, 0)  # 드래그 시작 위치
        self.is_potential_drag = False  # 드래그 시작 가능 상태
        self.drag_threshold = 10  # 드래그 시작을 위한 최소 이동 거리 (픽셀)
        
        # 드래그 앤 드롭 관련 변수
        self.drag_target_label = None  # 현재 드래그 타겟 레이블
        self.original_label_styles = {}
        
        logging.info("이미지→폴더 드래그 앤 드롭 기능 초기화됨")
        # === 이미지→폴더 드래그 앤 드롭 설정 끝 ===

        self.pressed_number_keys = set()  # 현재 눌린 숫자키 추적

        # --- 첫 RAW 파일 디코딩 진행률 대화상자 ---
        self.first_raw_load_progress = None

        # --- 카메라별 RAW 처리 설정을 위한 딕셔너리 ---
        # 형식: {"카메라모델명": {"method": "preview" or "decode", "dont_ask": True or False}}
        self.camera_raw_settings = {} 

        # === 비교 모드 관련 변수 ===
        self.compare_mode_active = False  # 비교 모드 활성화 여부
        self.image_B_path = None          # B 패널에 표시될 이미지 경로
        self.original_pixmap_B = None     # B 패널의 원본 QPixmap

        self._is_reorganizing_layout = False

        self._is_resetting = False
        
        # ==================== 여기서부터 UI 관련 코드 ====================

        # 다크 테마 적용
        self.setup_dark_theme()
        
        # 제목 표시줄 다크 테마 적용
        apply_dark_title_bar(self)
        
        # 중앙 위젯 설정
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 메인 레이아웃 설정
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 수평 분할기 생성
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(0)  # 분할기 핸들 너비를 0픽셀로 설정
        self.main_layout.addWidget(self.splitter)

        # === 썸네일 패널 생성 ===
        self.thumbnail_panel = ThumbnailPanel(self)
        self.thumbnail_panel.hide()  # 초기에는 숨김 (Grid Off 모드에서만 표시)

        # 썸네일 패널 시그널 연결
        self.thumbnail_panel.thumbnailClicked.connect(self.on_thumbnail_clicked)
        self.thumbnail_panel.thumbnailDoubleClicked.connect(self.on_thumbnail_double_clicked)
        self.thumbnail_panel.model.thumbnailRequested.connect(self.request_thumbnail_load)
        
        # 1. 스크롤 가능한 컨트롤 패널을 위한 QScrollArea 생성
        self.control_panel = QScrollArea() # 기존 self.control_panel을 QScrollArea로 변경
        self.control_panel.setWidgetResizable(True) # 내용물이 스크롤 영역에 꽉 차도록 설정
        self.control_panel.setFrameShape(QFrame.NoFrame) # 테두리 제거
        self.control_panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # 가로 스크롤바는 항상 끔

        ## 추가: 컨트롤 패널 최소/최대 너비 설정 ##
        self.control_panel.setMinimumWidth(UIScaleManager.get("control_panel_min_width"))
        self.control_panel.setMaximumWidth(UIScaleManager.get("control_panel_max_width"))

        # 2. 스크롤 영역에 들어갈 실제 콘텐츠를 담을 위젯 생성
        scroll_content_widget = QWidget()

        # 3. 기존 control_layout을 이 새로운 위젯에 설정
        self.control_layout = QVBoxLayout(scroll_content_widget)
        self.control_layout.setContentsMargins(*UIScaleManager.get_margins())
        self.control_layout.setSpacing(UIScaleManager.get("control_layout_spacing"))

        # 4. QScrollArea(self.control_panel)에 콘텐츠 위젯을 설정
        self.control_panel.setWidget(scroll_content_widget)

        # --- 이미지 뷰 영역: 분할 가능한 구조로 변경 ---
        # 1. 전체 이미지 뷰를 담을 메인 패널 (기존 image_panel 역할)
        self.image_panel = QFrame()
        self.image_panel.setFrameShape(QFrame.NoFrame)
        self.image_panel.setAutoFillBackground(True)
        image_palette = self.image_panel.palette()
        image_palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.image_panel.setPalette(image_palette)
        # 캔버스 전체 영역에 대한 드래그 앤 드롭 활성화
        self.image_panel.setAcceptDrops(True)
        self.image_panel.dragEnterEvent = self.canvas_dragEnterEvent
        self.image_panel.dropEvent = self.canvas_dropEvent
        
        # 2. 메인 패널 내부에 레이아웃과 스플리터 배치
        self.view_splitter_layout = QHBoxLayout(self.image_panel)
        self.view_splitter_layout.setContentsMargins(0, 0, 0, 0)
        self.view_splitter_layout.setSpacing(0)
        self.view_splitter = QSplitter(Qt.Horizontal)
        self.view_splitter.setStyleSheet("QSplitter::handle { background-color: #222222; } QSplitter::handle:hover { background-color: #444444; }")
        self.view_splitter.setHandleWidth(4) # 분할자 핸들 너비
        self.view_splitter_layout.addWidget(self.view_splitter)

        # 3. 패널 A (기존 메인 뷰) 위젯 설정
        self.image_container = QWidget()
        self.image_container.setStyleSheet("background-color: black;")
        self.image_label = QLabel(self.image_container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: transparent;")
        self.scroll_area = ZoomScrollArea(self)
        self.scroll_area.setWidget(self.image_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("background-color: black; border: none;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 패널 A 마우스 이벤트 연결 (기존과 동일)
        self.image_container.setMouseTracking(True)
        self.image_container.mousePressEvent = self.image_mouse_press_event
        self.image_container.mouseMoveEvent = self.image_mouse_move_event
        self.image_container.mouseReleaseEvent = self.image_mouse_release_event
        self.image_container.mouseDoubleClickEvent = self.image_mouse_double_click_event

        # 4. 패널 B (비교 뷰) 위젯 설정
        self.image_container_B = QWidget()
        self.image_container_B.setStyleSheet("background-color: black;")
        self.image_label_B = QLabel(self.image_container_B)
        self.image_label_B.setAlignment(Qt.AlignCenter)
        self.image_label_B.setStyleSheet("background-color: transparent; color: #888888;")
        self.image_label_B.setText(LanguageManager.translate("비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다."))
        self.scroll_area_B = ZoomScrollArea(self)
        self.scroll_area_B.setWidget(self.image_container_B)
        self.scroll_area_B.setWidgetResizable(True)
        self.scroll_area_B.setAlignment(Qt.AlignCenter)
        self.scroll_area_B.setStyleSheet("background-color: black; border: none;")
        self.scroll_area_B.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area_B.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 패널 B 드래그 앤 드롭, 마우스 이벤트, 우클릭 메뉴 연결
        self.scroll_area_B.setAcceptDrops(True)
        self.scroll_area_B.dragEnterEvent = self.canvas_B_dragEnterEvent
        self.scroll_area_B.dropEvent = self.canvas_B_dropEvent
        
        self.image_container_B.setMouseTracking(True)
        self.image_container_B.mousePressEvent = self.image_B_mouse_press_event
        self.image_container_B.mouseMoveEvent = self.image_B_mouse_move_event
        self.image_container_B.mouseReleaseEvent = self.image_B_mouse_release_event

        # 5. 스플리터에 패널 A, B 추가
        self.view_splitter.addWidget(self.scroll_area)   # 패널 A
        self.view_splitter.addWidget(self.scroll_area_B) # 패널 B
        self.scroll_area_B.hide() # 비교 모드가 아니면 숨김

        # B 패널 내에 레이아웃 설정
        self.image_container_B_layout = QVBoxLayout(self.image_container_B)
        self.image_container_B_layout.setContentsMargins(0, 0, 0, 0)
        self.image_container_B_layout.addWidget(self.image_label_B)

        # B 패널 닫기 버튼 추가
        self.close_compare_button = QPushButton("✕", self.scroll_area_B)
        self.close_compare_button.setFixedSize(40, 40)
        self.close_compare_button.setCursor(Qt.PointingHandCursor)
        self.close_compare_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(40, 40, 40, 180);
                color: #AAAAAA;
                border: 1px solid #555555;
                border-radius: 20px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: rgba(60, 60, 60, 220);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: rgba(20, 20, 20, 220);
            }
        """)
        self.close_compare_button.clicked.connect(self.deactivate_compare_mode)
        self.close_compare_button.hide() # 평소에는 숨김

        # 6. 미니맵 위젯 생성 (부모를 self.image_panel로 유지)
        self.minimap_widget = QWidget(self.scroll_area)
        self.minimap_widget.setStyleSheet("background-color: rgba(20, 20, 20, 200); border: 1px solid #666666;")
        self.minimap_widget.setFixedSize(self.minimap_width, self.minimap_height)
        self.minimap_widget.hide()
        self.minimap_label = QLabel(self.minimap_widget)
        self.minimap_label.setAlignment(Qt.AlignCenter)
        self.minimap_layout = QVBoxLayout(self.minimap_widget)
        self.minimap_layout.setContentsMargins(0, 0, 0, 0)
        self.minimap_layout.addWidget(self.minimap_label)
        self.minimap_widget.setMouseTracking(True)
        self.minimap_widget.mousePressEvent = self.minimap_mouse_press_event
        self.minimap_widget.mouseMoveEvent = self.minimap_mouse_move_event
        self.minimap_widget.mouseReleaseEvent = self.minimap_mouse_release_event

        # Compare 모드 파일명 라벨
        self.filename_label_A = QLabel(self.scroll_area)
        self.filename_label_B = QLabel(self.scroll_area_B)
        
        filename_label_style = """
            QLabel {
                background-color: rgba(0, 0, 0, 0.6);
                color: white;
                padding: 4px 4px;
                border-radius: 3px;
                font-size: 10pt;
            }
        """
        self.filename_label_A.setStyleSheet(filename_label_style)
        self.filename_label_B.setStyleSheet(filename_label_style)
        
        self.filename_label_A.hide()
        self.filename_label_B.hide()
        
        # 세로 가운데 정렬을 위한 상단 Stretch
        self.control_layout.addStretch(1)

        # --- JPG 폴더 섹션 ---
        # JPG 폴더 경로/클리어 컨테이너
        jpg_folder_container = QWidget()
        jpg_folder_layout = QHBoxLayout(jpg_folder_container)
        jpg_folder_layout.setContentsMargins(0, 0, 0, 0)
        jpg_folder_layout.setSpacing(UIScaleManager.get("folder_container_spacing", 5))

        # JPG 폴더 경로 표시 레이블 추가
        self.folder_path_label = InfoFolderPathLabel(LanguageManager.translate("폴더 경로"))
        self.folder_path_label.set_folder_index(-2)
        self.folder_path_label.doubleClicked.connect(self.open_folder_in_explorer)
        self.folder_path_label.folderDropped.connect(self._handle_canvas_folder_drop)

        # JPG 폴더 클리어 버튼 (X) 추가 (레이블 높이에 맞춰짐)
        self.jpg_clear_button = QPushButton("✕")
        self.jpg_clear_button.setStyleSheet(ThemeManager.generate_action_button_style())
        # InfoFolderPathLabel은 내부적으로 이미 높이가 고정되었으므로, 그 값을 바로 사용합니다.
        label_fixed_height = self.folder_path_label.height()
        self.jpg_clear_button.setFixedHeight(label_fixed_height)
        self.jpg_clear_button.setFixedWidth(UIScaleManager.get("delete_button_width"))
        self.jpg_clear_button.setEnabled(False)
        self.jpg_clear_button.clicked.connect(self.clear_jpg_folder)

        # JPG 폴더 레이아웃에 레이블과 버튼 추가
        jpg_folder_layout.addWidget(self.folder_path_label, 1)
        jpg_folder_layout.addWidget(self.jpg_clear_button)
        
        self.load_button = QPushButton(LanguageManager.translate("이미지 불러오기"))
        self.load_button.setStyleSheet(ThemeManager.generate_main_button_style())
        
        # 레이블 높이의 0.x배로 버튼 높이를 고정합니다.
        button_height = int(self.folder_path_label.height() * 0.72)
        self.load_button.setFixedHeight(button_height)
        
        self.load_button.clicked.connect(self.load_jpg_folder)
        
        self.control_layout.addWidget(self.load_button)
        self.control_layout.addWidget(jpg_folder_container)

        self.control_layout.addSpacing(UIScaleManager.get("JPG_RAW_spacing", 15))

        # --- RAW 폴더 섹션 ---
        # RAW 폴더 경로/클리어 컨테이너
        raw_folder_container = QWidget()
        raw_folder_layout = QHBoxLayout(raw_folder_container)
        raw_folder_layout.setContentsMargins(0, 0, 0, 0)
        raw_folder_layout.setSpacing(UIScaleManager.get("folder_container_spacing", 5))

        # RAW 폴더 경로 표시 레이블 추가
        self.raw_folder_path_label = InfoFolderPathLabel(LanguageManager.translate("폴더 경로"))
        self.raw_folder_path_label.set_folder_index(-1)
        self.raw_folder_path_label.doubleClicked.connect(self.open_raw_folder_in_explorer)
        self.raw_folder_path_label.folderDropped.connect(lambda path: self._handle_raw_folder_drop(path))

        # RAW 폴더 클리어 버튼 (X) 추가
        self.raw_clear_button = QPushButton("✕")
        self.raw_clear_button.setStyleSheet(ThemeManager.generate_action_button_style())
        raw_label_fixed_height = self.raw_folder_path_label.height()
        self.raw_clear_button.setFixedHeight(raw_label_fixed_height)
        self.raw_clear_button.setFixedWidth(UIScaleManager.get("delete_button_width"))
        self.raw_clear_button.setEnabled(False)
        self.raw_clear_button.clicked.connect(self.clear_raw_folder)

        # RAW 폴더 레이아웃에 레이블과 버튼 추가
        raw_folder_layout.addWidget(self.raw_folder_path_label, 1)
        raw_folder_layout.addWidget(self.raw_clear_button)
        
        self.match_raw_button = QPushButton(LanguageManager.translate("JPG - RAW 연결"))
        self.match_raw_button.setStyleSheet(ThemeManager.generate_main_button_style())
        
        # raw_folder_path_label 높이의 0.x배로 버튼 높이를 고정합니다.
        match_button_height = int(self.raw_folder_path_label.height() * 0.72)
        self.match_raw_button.setFixedHeight(match_button_height)
        
        self.match_raw_button.clicked.connect(self.on_match_raw_button_clicked)
        
        self.control_layout.addWidget(self.match_raw_button)
        self.control_layout.addWidget(raw_folder_container)

        # RAW 이동 토글 버튼을 위한 컨테이너 위젯 및 레이아웃
        self.toggle_container = QWidget()
        self.toggle_layout = QHBoxLayout(self.toggle_container)
        self.toggle_layout.setContentsMargins(0, 10, 0, 0)
        
        # RAW 이동 토글 버튼
        self.raw_toggle_button = QCheckBox(LanguageManager.translate("JPG + RAW 이동"))
        self.raw_toggle_button.setChecked(True)  # 기본적으로 활성화 상태로 시작
        self.raw_toggle_button.toggled.connect(self.on_raw_toggle_changed) # 자동 상태 관리로 변경
        self.raw_toggle_button.setStyleSheet(ThemeManager.generate_checkbox_style())
        
        # 토글 버튼을 레이아웃에 가운데 정렬로 추가
        self.toggle_layout.addStretch()
        self.toggle_layout.addWidget(self.raw_toggle_button)
        self.toggle_layout.addStretch()
        
        # 컨트롤 패널에 토글 컨테이너 추가
        self.control_layout.addWidget(self.toggle_container)
        
        # 구분선 추가
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))
        self.line_before_folders = HorizontalLine()
        self.control_layout.addWidget(self.line_before_folders)
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))

        # 분류 폴더 설정 영역
        self._rebuild_folder_selection_ui() # 이 시점에는 self.folder_count = 3
        
        # 구분선 추가
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))
        self.control_layout.addWidget(HorizontalLine())
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))
        
        # 이미지 줌 설정 UI 구성
        self.setup_zoom_ui()

        # 구분선 추가
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))
        self.control_layout.addWidget(HorizontalLine())
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))
        
        # Grid 설정 UI 구성 (Zoom UI 아래 추가)
        self.setup_grid_ui()

        # 구분선 추가
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))
        self.control_layout.addWidget(HorizontalLine())
        
        # 파일 정보 UI 구성 (Grid UI 아래 추가)
        self.setup_file_info_ui()

        # 구분선 추가 (파일 정보 아래)
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))
        self.control_layout.addWidget(HorizontalLine())
        self.control_layout.addSpacing(UIScaleManager.get("section_spacing", 20))

        # 이미지 카운터와 설정 버튼을 담을 컨테이너
        self.counter_settings_container = QWidget() # 컨테이너 생성만 하고 레이아웃은 별도 메서드에서 설정

        # 설정 버튼 초기화
        self.settings_button = QPushButton("⚙")
        settings_button_size = UIScaleManager.get("settings_button_size")
        self.settings_button.setFixedSize(settings_button_size, settings_button_size)
        self.settings_button.setCursor(Qt.PointingHandCursor)
        settings_font_size_style = settings_button_size - 15 # 폰트 크기는 UIScaleManager에 별도 정의하거나 버튼 크기에 비례하여 조정 가능
        self.settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: none;
                border-radius: 3px;
                font-size: {settings_font_size_style}px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {ThemeManager.get_color('accent_hover')};
            }}
            QPushButton:pressed {{
                background-color: {ThemeManager.get_color('accent_pressed')};
            }}
        """)
        self.settings_button.clicked.connect(self.show_settings_popup)

        # 이미지/페이지 카운트 레이블 추가
        self.image_count_label = QLabel("- / -")
        self.image_count_label.setStyleSheet(f"color: {ThemeManager.get_color('text')};")

        # 초기 레이아웃 설정 (현재 grid_mode에 맞게)
        self.update_counter_layout()

        # 컨트롤 레이아웃에 컨테이너 추가
        self.control_layout.addWidget(self.counter_settings_container)

        # 세로 가운데 정렬을 위한 하단 Stretch
        self.control_layout.addStretch(1)

        logging.info(f"__init__: 컨트롤 패널 오른쪽 배치 = {getattr(self, 'control_panel_on_right', False)}")

        # 초기에는 2패널 구조로 시작 (썸네일 패널은 숨김)
        self.thumbnail_panel.hide()
        
        # 화면 크기가 변경되면 레이아웃 다시 조정
        QGuiApplication.instance().primaryScreen().geometryChanged.connect(self.adjust_layout)

        # --- 초기 UI 상태 설정 추가 ---
        self.update_raw_toggle_state() # RAW 토글 초기 상태 설정
        self.update_info_folder_label_style(self.folder_path_label, self.current_folder) # JPG 폴더 레이블 초기 스타일
        self.update_info_folder_label_style(self.raw_folder_path_label, self.raw_folder) # RAW 폴더 레이블 초기 스타일
        self.update_match_raw_button_state() # <--- 추가: RAW 관련 버튼 초기 상태 업데이트      
        
        # 화면 해상도 기반 면적 75% 크기로 중앙 배치
        screen = QGuiApplication.primaryScreen()
        if screen:
            available_geometry = screen.availableGeometry()
            screen_width = available_geometry.width()
            screen_height = available_geometry.height()
            
            # 면적 기준 75%를 위한 스케일 팩터 계산
            scale_factor = 0.75 ** 0.5  # √0.75 ≈ 0.866
            
            # 75% 면적 크기 계산
            window_width = int(screen_width * scale_factor)
            window_height = int(screen_height * scale_factor)
            
            # 중앙 위치 계산
            center_x = (screen_width - window_width) // 2
            center_y = (screen_height - window_height) // 2
            
            # 윈도우 크기 및 위치 설정
            self.setGeometry(center_x, center_y, window_width, window_height)
        else:
            # 화면 정보를 가져올 수 없는 경우 기본 크기로 설정
            self.resize(1200, 800)

        # 초기 레이아웃 설정
        QApplication.processEvents()
        self.adjust_layout()
        
        # 키보드 포커스 설정
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        
        # 더블클릭 줌 관련 변수 추가
        self.center_image = False  # 이미지를 가운데로 이동할지 여부 플래그
        self.center_on_click = False  # 클릭한 지점을 중심으로 줌할지 여부 플래그
        self.double_click_pos = QPoint(0, 0)  # 더블클릭 위치 저장

        # 스페이스바 처리를 위한 플래그 추가
        self.space_pressed = False

        # 애플리케이션 레벨 이벤트 필터 설치
        self.installEventFilter(self)

        # --- 프로그램 시작 시 상태 불러오기 (UI 로드 후 실행) ---
        # QTimer.singleShot(100, self.load_state)

        # --- 파일 목록 다이얼로그 인스턴스 변수 추가 ---
        self.file_list_dialog = None

        # 테마 관리자 초기화 및 콜백 등록
        ThemeManager.register_theme_change_callback(self.update_ui_colors)
        
        # 언어 및 날짜 형식 관련 콜백 등록
        LanguageManager.register_language_change_callback(self.update_ui_texts)
        LanguageManager.register_language_change_callback(self.update_performance_profile_combo_text)
        LanguageManager.register_language_change_callback(self.update_mouse_wheel_sensitivity_combo_text)
        LanguageManager.register_language_change_callback(self.update_mouse_pan_sensitivity_combo_text)
        DateFormatManager.register_format_change_callback(self.update_date_formats)

        # ExifTool 가용성 확인
        self.exiftool_available = False
        #self.exiftool_path = self.get_bundled_exiftool_path()  # 인스턴스 변수로 저장 
        self.exiftool_path = self.get_exiftool_path() 
        try:
            if Path(self.exiftool_path).exists():
                result = subprocess.run([self.exiftool_path, "-ver"], capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    logging.info(f"ExifTool 버전 {version} 사용 가능")
                    self.exiftool_available = True
                else:
                    logging.warning("ExifTool을 찾았지만 실행할 수 없습니다. 제한된 메타데이터 추출만 사용됩니다.")
            else:
                logging.warning(f"ExifTool을 찾을 수 없습니다: {self.exiftool_path}")
        except Exception as e:
            logging.error(f"ExifTool 확인 중 오류: {e}")

        # === EXIF 병렬 처리를 위한 스레드 및 워커 설정 ===
        self.exif_thread = QThread(self)
        self.exif_worker = ExifWorker(self.raw_extensions, self.exiftool_path, self.exiftool_available)
        self.exif_worker.moveToThread(self.exif_thread)

        # 시그널-슬롯 연결
        self.exif_worker.finished.connect(self.on_exif_info_ready)
        self.exif_worker.error.connect(self.on_exif_info_error)

        # 스레드 시작
        self.exif_thread.start()

        # EXIF 캐시
        self.exif_cache = {}  # 파일 경로 -> EXIF 데이터 딕셔너리
        self.current_exif_path = None  # 현재 처리 중인 EXIF 경로
        # === 병렬 처리 설정 끝 ===

        # 드래그 앤 드랍 관련 변수
        self.drag_target_label = None  # 현재 드래그 타겟 레이블
        self.original_label_styles = {}  # 원래 레이블 스타일 저장
        
        logging.info("드래그 앤 드랍 기능 활성화됨")
        # === 드래그 앤 드랍 설정 끝 ===

        self.update_scrollbar_style()

        # 설정 창에 사용될 UI 컨트롤들을 미리 생성합니다.
        self._create_settings_controls()
        ThemeManager.register_theme_change_callback(self._update_settings_styles)

        self.update_all_folder_labels_state()

        self._is_silent_load = False

        # --- 백그라운드 폴더 로더 설정 ---
        self.folder_loader_thread = QThread()
        self.folder_loader_worker = FolderLoaderWorker(
            self.raw_extensions, self.get_datetime_from_file_fast
        )
        self.folder_loader_worker.moveToThread(self.folder_loader_thread)

        # 시그널 연결
        self.folder_loader_worker.finished.connect(self.on_loading_finished)
        self.folder_loader_worker.progress.connect(self.on_loading_progress)
        self.folder_loader_worker.error.connect(self.on_loading_error)
        
        self.folder_loader_thread.start()
        self.loading_progress_dialog = None
        # --- 백그라운드 폴더 로더 설정 끝 ---

        self.scroll_area.verticalScrollBar().valueChanged.connect(self._sync_viewports)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._sync_viewports)

        self.ui_refresh_timer = QTimer(self)
        self.ui_refresh_timer.setInterval(500)  # 0.5초 간격
        self.ui_refresh_timer.timeout.connect(self._periodic_ui_refresh)

    def _setup_copy_worker(self):
        """백그라운드 복사 작업을 위한 워커와 스레드를 설정합니다."""
        self.copy_thread = QThread(self)
        self.copy_worker = CopyWorker(self.copy_queue, self) # 부모 앱 참조 전달
        self.copy_worker.moveToThread(self.copy_thread)

        # 성공 신호 연결 (중복 제거)
        self.copy_worker.copyFinished.connect(self.show_feedback_message)
        
        # 실패 신호를 받으면 메시지 박스를 띄우는 람다 함수 연결
        self.copy_worker.copyFailed.connect(
            lambda msg: self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("복사 오류"), msg)
        )

        # 스레드가 시작될 때 워커의 처리 루프를 시작하도록 연결
        self.copy_thread.started.connect(self.copy_worker.process_queue)
        
        # 스레드 시작
        self.copy_thread.start()


    @Slot(str)
    def show_feedback_message(self, message):
        """캔버스 중앙에 피드백 메시지를 잠시 표시합니다."""
        # 피드백 라벨이 없으면 생성
        if not hasattr(self, 'feedback_label'):
            self.feedback_label = QLabel(self.image_panel) # image_panel을 부모로 설정
            self.feedback_label.setAlignment(Qt.AlignCenter)
            self.feedback_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(30, 30, 30, 0.7);
                    color: #AAAAAA;
                    font-size: 15pt;
                    padding: 10px 20px;
                    border-radius: 8px;
                }
            """)
            self.feedback_label.hide()
            
            # 피드백 메시지를 숨기기 위한 타이머
            self.feedback_timer = QTimer(self)
            self.feedback_timer.setSingleShot(True)
            self.feedback_timer.timeout.connect(self.feedback_label.hide)

        self.feedback_label.setText(message)
        self.feedback_label.adjustSize() # 텍스트 크기에 맞게 라벨 크기 조절

        # image_panel 중앙에 위치
        panel_rect = self.image_panel.rect()
        label_size = self.feedback_label.size()
        self.feedback_label.move(
            (panel_rect.width() - label_size.width()) // 2,
            (panel_rect.height() - label_size.height()) // 2
        )

        self.feedback_label.show()
        self.feedback_label.raise_()
        self.feedback_timer.start(500) # 0.5초 후에 숨김

    def _trigger_copy_operation(self, folder_index):
        """현재 선택된 이미지(들)에 대한 복사 작업을 큐에 추가합니다."""
        if not self.image_files: return

        target_folder = self.target_folders[folder_index]
        if not target_folder or not os.path.isdir(target_folder):
            return

        files_to_copy = []
        if self.grid_mode == "Off":
            if 0 <= self.current_image_index < len(self.image_files):
                files_to_copy.append(self.image_files[self.current_image_index])
        else: # Grid 모드
            if self.selected_grid_indices:
                for grid_idx in self.selected_grid_indices:
                    global_idx = self.grid_page_start_index + grid_idx
                    if 0 <= global_idx < len(self.image_files):
                        files_to_copy.append(self.image_files[global_idx])
            elif 0 <= self.current_grid_index < len(self.image_files) - self.grid_page_start_index:
                 global_idx = self.grid_page_start_index + self.current_grid_index
                 files_to_copy.append(self.image_files[global_idx])

        if files_to_copy:
            # (복사할 파일 목록, 대상 폴더, RAW 파일 정보, RAW 복사 여부) 튜플을 큐에 추가
            task = (files_to_copy, target_folder, self.raw_files, self.move_raw_files)
            self.copy_queue.put(task)


    def on_loading_progress(self, message):
        """로딩 진행 상황을 로딩창에 업데이트합니다."""
        if self.loading_progress_dialog:
            self.loading_progress_dialog.setLabelText(message)
            QApplication.processEvents() # UI 업데이트 강제

    def on_loading_error(self, message, title):
        """로딩 중 오류 발생 시 처리합니다."""
        if self.loading_progress_dialog:
            self.loading_progress_dialog.close()
            self.loading_progress_dialog = None
        
        self.show_themed_message_box(QMessageBox.Warning, title, message)
        self._reset_workspace_after_load_fail()

    def on_loading_finished(self, image_files, raw_files, jpg_folder, raw_folder, final_mode):
        """백그라운드 로딩 완료 시 UI를 업데이트합니다."""
        if self.loading_progress_dialog:
            self.loading_progress_dialog.close()
            self.loading_progress_dialog = None

        if not image_files:
            logging.warning("백그라운드 로더가 빈 이미지 목록을 반환했습니다.")
            self._reset_workspace_after_load_fail()
            self._is_silent_load = False
            return
            
        # 1. 파일 목록과 폴더 경로를 앱의 상태 변수에 먼저 업데이트합니다.
        self.image_files = image_files
        self.raw_files = raw_files
        
        if final_mode == 'raw_only':
            self.is_raw_only_mode = True
            self.raw_folder = jpg_folder # RAW Only 모드에서는 jpg_folder 인자에 raw 폴더 경로가 담겨 옴
            self.current_folder = ""
        else: # 'jpg_only' 또는 'jpg_with_raw'
            self.is_raw_only_mode = False
            self.current_folder = jpg_folder
            self.raw_folder = raw_folder

        logging.info(f"백그라운드 로딩 완료 (모드: {final_mode}): {len(self.image_files)}개 이미지, {len(self.raw_files)}개 RAW 매칭")
