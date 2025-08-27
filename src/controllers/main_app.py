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

