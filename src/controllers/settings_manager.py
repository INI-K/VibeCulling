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

    def _create_panel_position_radios(self):
        """패널 위치 선택 라디오 버튼 그룹 위젯 생성"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        layout.addWidget(self.panel_pos_left_radio)
        layout.addWidget(self.panel_pos_right_radio)
        layout.addStretch(1)
        return container

    def _create_mouse_wheel_radios(self):
        """마우스 휠 동작 선택 라디오 버튼 그룹 위젯 생성"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        layout.addWidget(self.mouse_wheel_photo_radio)
        layout.addWidget(self.mouse_wheel_none_radio)
        layout.addStretch(1)
        return container

    def _create_extension_checkboxes(self):
        """이미지 형식 체크박스 그룹 위젯 생성 (2줄 구조)"""
        # 전체 체크박스들을 담을 메인 컨테이너와 수직 레이아웃
        main_container = QWidget()
        vertical_layout = QVBoxLayout(main_container)
        vertical_layout.setContentsMargins(0, 0, 0, 0)
        vertical_layout.setSpacing(10)  # 줄 사이의 수직 간격

        # 첫 번째 줄 체크박스 키 목록
        keys_row1 = ["JPG", "HEIC", "WebP"]
        # 두 번째 줄 체크박스 키 목록
        keys_row2 = ["PNG", "BMP", "TIFF"]

        # --- 첫 번째 줄 생성 ---
        row1_container = QWidget()
        row1_layout = QHBoxLayout(row1_container)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(20) # 체크박스 사이의 수평 간격

        for name in keys_row1:
            if name in self.ext_checkboxes:
                row1_layout.addWidget(self.ext_checkboxes[name])
        row1_layout.addStretch(1) # 오른쪽에 남는 공간을 채움

        # --- 두 번째 줄 생성 ---
        row2_container = QWidget()
        row2_layout = QHBoxLayout(row2_container)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(20) # 체크박스 사이의 수평 간격

        for name in keys_row2:
            if name in self.ext_checkboxes:
                row2_layout.addWidget(self.ext_checkboxes[name])
        row2_layout.addStretch(1) # 오른쪽에 남는 공간을 채움

        # --- 메인 레이아웃에 각 줄 추가 ---
        vertical_layout.addWidget(row1_container)
        vertical_layout.addWidget(row2_container)

        return main_container

    def on_viewport_speed_changed(self, index):
        """뷰포트 이동 속도 콤보박스 변경 시 호출"""
        if index < 0: return
        selected_speed = self.viewport_speed_combo.itemData(index)
        if selected_speed is not None:
            self.viewport_move_speed = int(selected_speed)
            logging.info(f"뷰포트 이동 속도 변경됨: {self.viewport_move_speed}")
            # self.save_state() # 즉시 저장하려면 호출 (set_camera_raw_setting처럼)

    @Slot()
    def _reset_wheel_accumulator(self):
        """비활성 상태가 1초간 지속되면 마우스 휠 누적 카운터를 초기화합니다."""
        logging.debug("마우스 휠 비활성으로 누적 카운터 초기화됨.")
        self.mouse_wheel_accumulator = 0
        self.last_wheel_direction = 0

    def on_mouse_wheel_sensitivity_changed(self, index):
        """마우스 휠 민감도 설정 변경 시 호출"""
        if index < 0: return
        new_sensitivity = self.mouse_wheel_sensitivity_combo.itemData(index)
        if new_sensitivity is not None:
            self.mouse_wheel_sensitivity = new_sensitivity
            # 민감도 변경 시 누적 카운터와 방향, 타이머 초기화
            self.mouse_wheel_accumulator = 0
            self.last_wheel_direction = 0
            self.wheel_reset_timer.stop() # 타이머도 중지
            logging.info(f"마우스 휠 민감도 변경됨: {self.mouse_wheel_sensitivity}")

    def on_theme_changed(self, index):
        """테마 변경 시 호출되는 함수 (인덱스 기반)"""
        if index < 0:
            return
            
        theme_key = self.theme_combo.itemData(index)
        if theme_key:
            # 현재 테마와 다를 경우에만 변경 (무한 루프 방지)
            if ThemeManager.get_current_theme_name() != theme_key:
                ThemeManager.set_theme(theme_key)

    def update_scrollbar_style(self):
        """컨트롤 패널의 스크롤바 스타일을 현재 테마에 맞게 업데이트합니다."""
        if hasattr(self, 'control_panel') and isinstance(self.control_panel, QScrollArea):
            self.control_panel.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: none;
                }}
                QScrollBar:vertical {{
                    border: none;
                    background: {ThemeManager.get_color('bg_primary')};
                    width: 6px;
                    margin: 0px 0px 0px 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: {ThemeManager.get_color('border')};
                    min-height: 20px;
                    border-radius: 5px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {ThemeManager.get_color('accent_hover')};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    border: none;
                    background: none;
                    height: 0px;
                }}
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                    background: none;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: none;
                }}
            """)

    def update_ui_colors(self):
        """테마 변경 시 모든 UI 요소의 색상을 업데이트"""
        # 모든 UI 요소의 스타일시트를 다시 설정
        self.update_button_styles()
        self.update_label_styles()
        self.update_folder_styles()
        self.update_scrollbar_style()
        self.update_thumbnail_panel_style()
        
        # 설정 버튼 스타일 업데이트
        self.settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: none;
                border-radius: 3px;
                font-size: 20px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {ThemeManager.get_color('accent_hover')};
            }}
            QPushButton:pressed {{
                background-color: {ThemeManager.get_color('accent_pressed')};
            }}
        """)
        
        # 메시지 표시
        print(f"테마가 변경되었습니다: {ThemeManager.get_current_theme_name()}")

    def update_button_styles(self):
        """버튼 스타일을 현재 테마에 맞게 업데이트"""
        # 기본 버튼 스타일
        button_style = ThemeManager.generate_main_button_style()
        # 동적 높이 버튼을 위한 새 스타일
        dynamic_button_style = ThemeManager.generate_dynamic_height_button_style()
        # 삭제 버튼 스타일
        delete_button_style = ThemeManager.generate_action_button_style()
        # 라디오 버튼 스타일
        radio_style = ThemeManager.generate_radio_button_style()

        if hasattr(self, 'load_button') and hasattr(self, 'folder_path_label'):
            # 1. 수직 패딩이 없는 스타일 적용
            self.load_button.setStyleSheet(dynamic_button_style)
            # 2. 전체 높이를 강제 설정 (이제 패딩과 충돌하지 않음)
            button_height = int(self.folder_path_label.height() * 0.72) # 레이블 높이의 0.x배로 버튼 높이를 고정
            self.load_button.setFixedHeight(button_height)

        if hasattr(self, 'match_raw_button') and hasattr(self, 'raw_folder_path_label'):
            # 1. 수직 패딩이 없는 스타일 적용
            self.match_raw_button.setStyleSheet(dynamic_button_style)
            # 2. 전체 높이를 강제 설정
            button_height = int(self.raw_folder_path_label.height() * 0.72) # 레이블 높이의 0.x배로 버튼 높이를 고정
            self.match_raw_button.setFixedHeight(button_height)
            
        # 삭제 버튼 스타일 적용
        if hasattr(self, 'jpg_clear_button'):
            self.jpg_clear_button.setStyleSheet(delete_button_style)
        if hasattr(self, 'raw_clear_button'):
            self.raw_clear_button.setStyleSheet(delete_button_style)
            
        # 폴더 버튼과 삭제 버튼 스타일 적용 (이 버튼들은 고정 높이가 아니므로 기존 스타일 사용)
        if hasattr(self, 'folder_buttons'):
            for button in self.folder_buttons:
                button.setStyleSheet(button_style)
        if hasattr(self, 'folder_action_buttons'):
            for button in self.folder_action_buttons:
                button.setStyleSheet(delete_button_style)
                
        # 줌 라디오 버튼 스타일 적용
        if hasattr(self, 'zoom_group'):
            for button in self.zoom_group.buttons():
                button.setStyleSheet(radio_style)
                
        if hasattr(self, 'grid_mode_group'):
            for button in self.grid_mode_group.buttons():
                button.setStyleSheet(radio_style)
                
    def resource_path(self, relative_path: str) -> str:
        """개발 환경과 PyInstaller 번들 환경 모두에서 리소스 경로 반환"""
        try:
            base = Path(sys._MEIPASS)
        except Exception:
            base = Path(__file__).parent
        return str(base / relative_path)

    def update_label_styles(self):
        """라벨 스타일을 현재 테마에 맞게 업데이트"""
        # 기본 라벨 스타일
        label_style = f"color: {ThemeManager.get_color('text')};"
        
        # 카운트 라벨 스타일 적용
        if hasattr(self, 'image_count_label'):
            self.image_count_label.setStyleSheet(label_style)
            
        # 파일 정보 라벨들 스타일 적용
        if hasattr(self, 'file_info_labels'):
            for label in self.file_info_labels:
                label.setStyleSheet(label_style)

        # 미니맵 토글 및 RAW 토글 체크박스 스타일 업데이트
        if hasattr(self, 'minimap_toggle'):
            self.minimap_toggle.setStyleSheet(ThemeManager.generate_checkbox_style())
        if hasattr(self, 'raw_toggle_button'):
            self.raw_toggle_button.setStyleSheet(ThemeManager.generate_checkbox_style())
        if hasattr(self, 'filename_toggle_grid'):
            self.filename_toggle_grid.setStyleSheet(ThemeManager.generate_checkbox_style())
        
    
    def update_folder_styles(self):
        """폴더 관련 UI 요소의 스타일을 업데이트 (테마 변경 시 호출됨)"""
        # 1. JPG/RAW 폴더 UI 상태 업데이트 (내부적으로 InfoFolderPathLabel의 스타일 재설정)
        if hasattr(self, 'folder_path_label'):
            self.update_jpg_folder_ui_state()
        if hasattr(self, 'raw_folder_path_label'):
            self.update_raw_folder_ui_state()

        # 2. 분류 폴더 UI 상태 업데이트 (내부적으로 EditableFolderPathLabel의 스타일 재설정)
        if hasattr(self, 'folder_path_labels'):
            self.update_all_folder_labels_state()
    
    def _create_settings_popup(self):
        """설정 팝업창을 최초 한 번만 생성하고 레이아웃을 구성합니다."""
        self.settings_popup = QDialog(self)
        self.settings_popup.setWindowTitle(LanguageManager.translate("설정 및 정보"))
        popup_width = UIScaleManager.get("settings_popup_width", 785)
        popup_height = UIScaleManager.get("settings_popup_height", 910)
        self.settings_popup.setMinimumSize(popup_width, popup_height)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        self.settings_popup.setPalette(palette)
        self.settings_popup.setAutoFillBackground(True)

        # --- 메인 레이아웃 (수평 2컬럼) ---
        main_layout = QHBoxLayout(self.settings_popup)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(30)

        # --- 왼쪽 컬럼 (설정 항목들) ---
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        settings_ui_widget = self.setup_settings_ui()
        left_layout.addWidget(settings_ui_widget)

        # --- 중앙 구분선 ---
        separator_vertical = QFrame()
        separator_vertical.setFrameShape(QFrame.VLine)
        separator_vertical.setFrameShadow(QFrame.Sunken)
        separator_vertical.setStyleSheet(f"background-color: {ThemeManager.get_color('border')}; max-width: 1px;")

        # --- 오른쪽 컬럼 (정보 및 후원) ---
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(UIScaleManager.get("info_donation_spacing", 40))
        info_section = self._build_info_section()
        right_layout.addStretch(1)
        separator_top = QFrame()
        separator_top.setFrameShape(QFrame.HLine)
        separator_top.setFrameShadow(QFrame.Sunken)
        separator_top.setStyleSheet(f"background-color: {ThemeManager.get_color('border')}; max-height: 1px;")
        right_layout.addWidget(separator_top)
        right_layout.addWidget(info_section)
        separator_middle = QFrame()
        separator_middle.setFrameShape(QFrame.HLine)
        separator_middle.setFrameShadow(QFrame.Sunken)
        separator_middle.setStyleSheet(f"background-color: {ThemeManager.get_color('border')}; max-height: 1px;")
        right_layout.addWidget(separator_middle)
        donation_section = self._build_donation_section()
        right_layout.addWidget(donation_section)
        right_layout.addStretch(1)

        # --- 메인 레이아웃에 컬럼 추가 ---
        main_layout.addWidget(left_column, 6)
        main_layout.addWidget(separator_vertical)
        main_layout.addWidget(right_column, 4)

    def _update_settings_styles(self):
        """
        설정창의 모든 UI 요소 스타일을 현재 테마에 맞게 업데이트하고,
        Qt 스타일 엔진에 즉시 적용하도록 강제합니다.
        """
        # settings_popup이 아직 생성되지 않았을 수도 있으므로 self의 멤버 변수를 직접 참조합니다.
        # 이 함수는 앱 시작 시점부터 호출될 수 있습니다.
        logging.debug("_update_settings_styles 호출됨.")

        # --- 스타일 문자열 생성 (기존 로직 유지) ---
        radio_style = f"""
            QRadioButton {{ color: {ThemeManager.get_color('text')}; padding: 5px 10px; }}
            QRadioButton::indicator {{ width: {UIScaleManager.get("radiobutton_size")}px; height: {UIScaleManager.get("radiobutton_size")}px; }}
            QRadioButton::indicator:checked {{ background-color: {ThemeManager.get_color('accent')}; border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('accent')}; border-radius: {UIScaleManager.get("radiobutton_border_radius")}px; }}
            QRadioButton::indicator:unchecked {{ background-color: {ThemeManager.get_color('bg_primary')}; border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('border')}; border-radius: {UIScaleManager.get("radiobutton_border_radius")}px; }}
            QRadioButton::indicator:unchecked:hover {{ border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('text_disabled')}; }}
        """
        checkbox_style = f"""
            QCheckBox {{ color: {ThemeManager.get_color('text')}; padding: 3px 5px; }}
            QCheckBox::indicator {{ width: {UIScaleManager.get("checkbox_size")}px; height: {UIScaleManager.get("checkbox_size")}px; }}
            QCheckBox::indicator:checked {{ background-color: {ThemeManager.get_color('accent')}; border: {UIScaleManager.get("checkbox_border")}px solid {ThemeManager.get_color('accent')}; border-radius: {UIScaleManager.get("checkbox_border_radius")}px; }}
            QCheckBox::indicator:unchecked {{ background-color: {ThemeManager.get_color('bg_primary')}; border: {UIScaleManager.get("checkbox_border")}px solid {ThemeManager.get_color('border')}; border-radius: {UIScaleManager.get("checkbox_border_radius")}px; }}
            QCheckBox::indicator:unchecked:hover {{ border: {UIScaleManager.get("checkbox_border")}px solid {ThemeManager.get_color('text_disabled')}; }}
        """
        combobox_style = self.generate_combobox_style()
        
        def apply_style_and_polish(widget):
            if hasattr(widget, 'setStyleSheet'):
                # 위젯의 타입을 확인하여 적절한 스타일을 적용합니다.
                if isinstance(widget, QRadioButton):
                    widget.setStyleSheet(radio_style)
                elif isinstance(widget, QCheckBox):
                    widget.setStyleSheet(checkbox_style)
                elif isinstance(widget, QComboBox):
                    widget.setStyleSheet(combobox_style)
                
                # 스타일을 즉시 다시 계산하고 적용하도록 강제합니다.
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update() # 위젯을 다시 그리도록 명시적으로 요청 (추가적인 안전장치)

        # --- 모든 설정 컨트롤에 대해 헬퍼 함수 호출 ---
        # 라디오 버튼
        if hasattr(self, 'english_radio'): apply_style_and_polish(self.english_radio)
        if hasattr(self, 'korean_radio'): apply_style_and_polish(self.korean_radio)
        if hasattr(self, 'panel_pos_left_radio'): apply_style_and_polish(self.panel_pos_left_radio)
        if hasattr(self, 'panel_pos_right_radio'): apply_style_and_polish(self.panel_pos_right_radio)
        if hasattr(self, 'mouse_wheel_photo_radio'): apply_style_and_polish(self.mouse_wheel_photo_radio)
        if hasattr(self, 'mouse_wheel_none_radio'): apply_style_and_polish(self.mouse_wheel_none_radio)
        
        # 체크박스
        if hasattr(self, 'ext_checkboxes'):
            for checkbox in self.ext_checkboxes.values():
                apply_style_and_polish(checkbox)
        
        # 콤보박스
        if hasattr(self, 'theme_combo'): apply_style_and_polish(self.theme_combo)
        if hasattr(self, 'date_format_combo'): apply_style_and_polish(self.date_format_combo)
        if hasattr(self, 'folder_count_combo'): apply_style_and_polish(self.folder_count_combo)
        if hasattr(self, 'viewport_speed_combo'): apply_style_and_polish(self.viewport_speed_combo)
        if hasattr(self, 'mouse_wheel_sensitivity_combo'): apply_style_and_polish(self.mouse_wheel_sensitivity_combo)
        if hasattr(self, 'mouse_pan_sensitivity_combo'): apply_style_and_polish(self.mouse_pan_sensitivity_combo)
        if hasattr(self, 'performance_profile_combo'): apply_style_and_polish(self.performance_profile_combo)


    def _update_first_run_settings_styles(self):
        """초기 설정 창의 라디오 버튼 스타일을 현재 테마에 맞게 업데이트"""
        if not hasattr(self, 'settings_popup') or self.settings_popup is None:
            return
        
        # 초기 설정 창인지 확인
        if not self.settings_popup.property("is_first_run_popup"):
            return
        
        # _create_settings_controls에서 정의된 radio_style과 동일하게 생성
        radio_style = f"""
            QRadioButton {{ color: {ThemeManager.get_color('text')}; padding: 5px 10px; }}
            QRadioButton::indicator {{ width: {UIScaleManager.get("radiobutton_size")}px; height: {UIScaleManager.get("radiobutton_size")}px; }}
            QRadioButton::indicator:checked {{ background-color: {ThemeManager.get_color('accent')}; border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('accent')}; border-radius: {UIScaleManager.get("radiobutton_border_radius")}px; }}
            QRadioButton::indicator:unchecked {{ background-color: {ThemeManager.get_color('bg_primary')}; border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('border')}; border-radius: {UIScaleManager.get("radiobutton_border_radius")}px; }}
            QRadioButton::indicator:unchecked:hover {{ border: {UIScaleManager.get("radiobutton_border")}px solid {ThemeManager.get_color('text_disabled')}; }}
        """
        
        # 초기 설정 창의 라디오 버튼들에 스타일 적용
        if hasattr(self, 'english_radio'):
            self.english_radio.setStyleSheet(radio_style)
        if hasattr(self, 'korean_radio'):
            self.korean_radio.setStyleSheet(radio_style)
        if hasattr(self, 'panel_pos_left_radio'):
            self.panel_pos_left_radio.setStyleSheet(radio_style)
        if hasattr(self, 'panel_pos_right_radio'):
            self.panel_pos_right_radio.setStyleSheet(radio_style)

    def show_settings_popup(self):
        """설정 버튼 클릭 시 호출, 팝업을 생성하거나 기존 팝업을 보여줍니다."""
        if not hasattr(self, 'settings_popup') or self.settings_popup is None:
            self._create_settings_popup()

        # 팝업을 보여주기 전에 현재 상태를 UI 컨트롤에 반영
        current_theme_name = ThemeManager.get_current_theme_name()
        
        # findText 대신 findData를 사용하여 정확한 아이템을 찾음
        index = self.theme_combo.findData(current_theme_name)
        
        if index >= 0:
            # setCurrentIndex가 on_theme_changed를 호출할 수 있으므로,
            # 시그널을 잠시 막아 불필요한 재실행을 방지합니다.
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(index)
            self.theme_combo.blockSignals(False)
        
        # 현재 언어 설정 반영
        current_lang = LanguageManager.get_current_language()
        if current_lang == "en":
            self.english_radio.setChecked(True)
        else:
            self.korean_radio.setChecked(True)

        # 컨트롤 패널 위치 동기화
        if hasattr(self, 'panel_position_group'):
            panel_button_id = 1 if self.control_panel_on_right else 0
            panel_button_to_check = self.panel_position_group.button(panel_button_id)
            if panel_button_to_check: 
                panel_button_to_check.setChecked(True)
        
        # 이미지 형식 체크박스 동기화
        if hasattr(self, 'ext_checkboxes'):
            extension_groups = {
                "JPG": ['.jpg', '.jpeg'], 
                "PNG": ['.png'], 
                "WebP": ['.webp'], 
                "HEIC": ['.heic', '.heif'], 
                "BMP": ['.bmp'], 
                "TIFF": ['.tif', '.tiff']
            }
            for name, checkbox in self.ext_checkboxes.items():
                is_checked = any(ext in self.supported_image_extensions for ext in extension_groups[name])
                checkbox.blockSignals(True)
                checkbox.setChecked(is_checked)
                checkbox.blockSignals(False)
        
        # 분류 폴더 개수 콤보박스 동기화
        if hasattr(self, 'folder_count_combo'):
            index = self.folder_count_combo.findData(self.folder_count)
            if index >= 0: 
                self.folder_count_combo.setCurrentIndex(index)
        
        # 뷰포트 이동 속도 콤보박스 동기화
        if hasattr(self, 'viewport_speed_combo'):
            index = self.viewport_speed_combo.findData(self.viewport_move_speed)
            if index >= 0: 
                self.viewport_speed_combo.setCurrentIndex(index)
        
        # 마우스 휠 동작 라디오 버튼 동기화
        if hasattr(self, 'mouse_wheel_photo_radio') and hasattr(self, 'mouse_wheel_none_radio'):
            if self.mouse_wheel_action == 'photo_navigation': 
                self.mouse_wheel_photo_radio.setChecked(True)
            else: 
                self.mouse_wheel_none_radio.setChecked(True)
        
        # 마우스 휠 감도 콤보박스 동기화
        if hasattr(self, 'mouse_wheel_sensitivity_combo'):
            index = self.mouse_wheel_sensitivity_combo.findData(self.mouse_wheel_sensitivity)
            if index >= 0: 
                self.mouse_wheel_sensitivity_combo.setCurrentIndex(index)
        
        # 성능 설정 동기화
        self._sync_performance_profile_ui()
        
        # 날짜 형식 동기화
        if hasattr(self, 'date_format_combo'):
            current_date_format = DateFormatManager.get_current_format()
            idx = self.date_format_combo.findData(current_date_format)
            if idx >= 0: 
                self.date_format_combo.setCurrentIndex(idx)

        # 팝업의 모든 텍스트를 현재 언어에 맞게 업데이트
        self.update_settings_labels_texts(self.settings_popup)

        apply_dark_title_bar(self.settings_popup)
        self.settings_popup.exec()
        
        all_controls = [
            self.theme_combo, self.date_format_combo, self.folder_count_combo,
            self.viewport_speed_combo, self.mouse_wheel_sensitivity_combo,
            self.mouse_pan_sensitivity_combo, self.reset_camera_settings_button,
            self.reset_app_settings_button, self.session_management_button,
            self.shortcuts_button, self.performance_profile_combo
        ]
        for widget in self.language_group.buttons(): all_controls.append(widget)
        for widget in self.panel_position_group.buttons(): all_controls.append(widget)
        for widget in self.mouse_wheel_group.buttons(): all_controls.append(widget)
        for widget in self.ext_checkboxes.values(): all_controls.append(widget)

    def _build_info_section(self):
        """'정보' 섹션 UI를 생성합니다."""
        info_section = QWidget()
        info_layout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)

        info_text = self.create_translated_info_text()
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet(f"color: {ThemeManager.get_color('text')};")
        info_label.setObjectName("vibeculling_info_label")
        info_label.setOpenExternalLinks(True)
        info_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_layout.addWidget(info_label)
        info_layout.addSpacing(UIScaleManager.get("infotext_licensebutton", 40))

        license_button_container = QWidget()
        license_button_layout = QHBoxLayout(license_button_container)
        license_button_layout.setContentsMargins(0, 0, 0, 0)
        licenses_button = QPushButton("Open Source Licenses")
        licenses_button.setStyleSheet(f"""
            QPushButton {{ background-color: {ThemeManager.get_color('bg_secondary')}; color: {ThemeManager.get_color('text')}; border: none; padding: 8px 16px; border-radius: 4px; min-width: 180px; }}
            QPushButton:hover {{ background-color: {ThemeManager.get_color('bg_hover')}; }}
            QPushButton:pressed {{ background-color: {ThemeManager.get_color('bg_pressed')}; }}
        """)
        licenses_button.setCursor(Qt.PointingHandCursor)
        licenses_button.clicked.connect(self.show_licenses_popup)
        license_button_layout.addStretch(1)
        license_button_layout.addWidget(licenses_button)
        license_button_layout.addStretch(1)
        info_layout.addWidget(license_button_container)
        
        return info_section

    def _build_donation_section(self):
        """'후원' 섹션 UI를 생성합니다."""
        donation_section = QWidget()
        donation_layout = QVBoxLayout(donation_section)
        donation_layout.setContentsMargins(0, 0, 0, 0)

        # 공통 아이콘 생성
        coffee_icon_path = self.resource_path("resources/coffee_icon.png")
        coffee_icon = QPixmap(coffee_icon_path)
        coffee_emoji = QLabel()
        if not coffee_icon.isNull():
            coffee_icon = coffee_icon.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            coffee_emoji.setPixmap(coffee_icon)
        else:
            coffee_emoji.setText("☕")
        coffee_emoji.setFixedWidth(60)
        coffee_emoji.setStyleSheet("padding-left: 10px;")
        coffee_emoji.setAlignment(Qt.AlignCenter)

        # 언어별 위젯을 담을 컨테이너
        links_container = QWidget()
        links_layout = QVBoxLayout(links_container)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(0)

        # --- 한국어용 위젯 생성 ---
        self.korean_donation_widget = QWidget()
        ko_links_layout = QVBoxLayout(self.korean_donation_widget)
        ko_links_layout.setContentsMargins(0, 0, 0, 0)
        ko_links_layout.setSpacing(UIScaleManager.get("donation_between_tworows", 30))
        
        ko_row1_container = QHBoxLayout()
        qr_path_kakaopay_ko = self.resource_path("resources/kakaopay_qr.png")
        kakaopay_label = QRLinkLabel(LanguageManager.translate("카카오페이"), "", qr_path=qr_path_kakaopay_ko, qr_display_size=400, parent=self.settings_popup)
        kakaopay_label.setAlignment(Qt.AlignCenter)
        kakaopay_label.setObjectName("kakaopay_label")
        qr_path_naverpay_ko = self.resource_path("resources/naverpay_qr.png")
        naverpay_label = QRLinkLabel(LanguageManager.translate("네이버페이"), "", qr_path=qr_path_naverpay_ko, qr_display_size=250, parent=self.settings_popup)
        naverpay_label.setAlignment(Qt.AlignCenter)
        naverpay_label.setObjectName("naverpay_label")
        ko_row1_container.addWidget(kakaopay_label)
        ko_row1_container.addWidget(naverpay_label)
        ko_links_layout.addLayout(ko_row1_container)
        links_layout.addWidget(self.korean_donation_widget)

        # --- 영어용 위젯 생성 ---
        self.english_donation_widget = QWidget()
        en_links_layout = QVBoxLayout(self.english_donation_widget)
        en_links_layout.setContentsMargins(0, 0, 0, 0)
        en_links_layout.setSpacing(UIScaleManager.get("donation_between_tworows", 30))
        
        en_row1_container = QHBoxLayout()
        bmc_url = "https://buymeacoffee.com/ffamilist"
        qr_path_bmc = self.resource_path("resources/bmc_qr.png")
        bmc_label = QRLinkLabel("Buy Me a Coffee", bmc_url, qr_path=qr_path_bmc, qr_display_size=250, parent=self.settings_popup)
        bmc_label.setAlignment(Qt.AlignCenter)
        paypal_url = "https://paypal.me/ffamilist"
        paypal_label = QRLinkLabel("PayPal", paypal_url, qr_path="", qr_display_size=250, parent=self.settings_popup)
        paypal_label.setAlignment(Qt.AlignCenter)
        paypal_label.setToolTip("Click to go to PayPal")
        en_row1_container.addWidget(bmc_label)
        en_row1_container.addWidget(paypal_label)
        en_links_layout.addLayout(en_row1_container)
        links_layout.addWidget(self.english_donation_widget)
        
        # 최종 레이아웃 조립
        content_container = QHBoxLayout()
        content_container.setContentsMargins(0, 0, 0, 0)
        content_container.addWidget(coffee_emoji, 0, Qt.AlignVCenter)
        content_container.addWidget(links_container, 1)
        donation_layout.addLayout(content_container)

        # 초기 가시성 설정
        current_language = LanguageManager.get_current_language()
        self.korean_donation_widget.setVisible(current_language == "ko")
        self.english_donation_widget.setVisible(current_language == "en")

        return donation_section

    def show_shortcuts_popup(self):
        """단축키 안내 팝업창을 표시합니다."""
        if hasattr(self, 'shortcuts_info_popup') and self.shortcuts_info_popup.isVisible():
            self.shortcuts_info_popup.activateWindow()
            return

        self.shortcuts_info_popup = QDialog(self)
        self.shortcuts_info_popup.setWindowTitle(LanguageManager.translate("단축키")) # 새 번역 키
        
        # 다크 테마 적용 (기존 show_themed_message_box 또는 settings_popup 참조)
        apply_dark_title_bar(self.shortcuts_info_popup)
        palette = QPalette(); palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        self.shortcuts_info_popup.setPalette(palette); self.shortcuts_info_popup.setAutoFillBackground(True)

        layout = QVBoxLayout(self.shortcuts_info_popup)
        layout.setContentsMargins(20, 20, 20, 20)

        # 스크롤 가능한 텍스트 영역으로 변경 (내용이 길어지므로)
        text_browser = QTextBrowser() # QLabel 대신 QTextBrowser 사용
        text_browser.setReadOnly(True)
        text_browser.setOpenExternalLinks(False) # 이 팝업에는 링크가 없을 것이므로
        text_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent; /* 부모 위젯 배경색 사용 */
                color: {ThemeManager.get_color('text')};
                border: none; /* 테두리 없음 */
            }}
        """)
        html_content = self._build_shortcut_html() # 위에서 만든 함수 호출
        text_browser.setHtml(html_content)
        
        # 텍스트 브라우저의 최소/권장 크기 설정 (내용에 따라 조절)
        text_browser.setMinimumHeight(UIScaleManager.get("shortcuts_popup_height", 930))
        text_browser.setMinimumWidth(700)

        layout.addWidget(text_browser)

        close_button = QPushButton(LanguageManager.translate("닫기"))
        # 닫기 버튼 스타일 설정
        button_style = f"""
            QPushButton {{
                background-color: {ThemeManager.get_color('bg_secondary')}; color: {ThemeManager.get_color('text')};
                border: none; padding: 8px 16px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{ background-color: {ThemeManager.get_color('accent_hover')}; }}
            QPushButton:pressed {{ background-color: {ThemeManager.get_color('accent_pressed')}; }}
        """
        close_button.setStyleSheet(button_style)
        close_button.clicked.connect(self.shortcuts_info_popup.accept)
        
        button_layout = QHBoxLayout() # 버튼 중앙 정렬용
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        self.shortcuts_info_popup.exec()



    def create_translated_info_text(self):
        """현재 언어에 맞게 번역된 정보 텍스트를 생성하여 반환"""
        version_margin = UIScaleManager.get("info_version_margin", 40)
        paragraph_margin = UIScaleManager.get("info_paragraph_margin", 30) 
        bottom_margin = UIScaleManager.get("info_bottom_margin", 30)
        accent_color = "#01CA47"

        info_text = f"""
        <h2 style="color: {accent_color};">VibeCulling</h2>
        <p style="margin-bottom: {version_margin}px;">Version: 25.08.06</p>
        <p>{LanguageManager.translate("자유롭게 사용, 수정, 배포할 수 있는 오픈소스 소프트웨어입니다.")}</p>
        <p>{LanguageManager.translate("AGPL-3.0 라이선스 조건에 따라 소스 코드 공개 의무가 있습니다.")}</p>
        <p style="margin-bottom: {paragraph_margin}px;">{LanguageManager.translate("이 프로그램이 마음에 드신다면, 커피 한 잔으로 응원해 주세요.")}</p>
        <p style="margin-bottom: {bottom_margin}px;">Copyright © 2025 newboon</p>
        <p>
            {LanguageManager.translate("피드백 및 업데이트 확인:")}
            <a href="https://medium.com/@ffamilist/VibeCulling-simple-sorting-for-busy-dads-e9a4f45b03dc" style="color: {accent_color}; text-decoration: none;">[EN]</a>&nbsp;
            <a href="https://blog.naver.com/ffamilist/223844618813" style="color: {accent_color}; text-decoration: none;">[KR]</a>&nbsp;
            <a href="https://github.com/newboon/VibeCulling/releases" style="color: {accent_color}; text-decoration: none;">[GitHub]</a>
        </p>
        """
        return info_text

    def show_licenses_popup(self):
        """오픈소스 라이선스 정보를 표시하는 팝업"""
        # 다이얼로그 생성
        licenses_popup = QDialog(self)
        licenses_popup.setWindowTitle("Open Source Licenses Info")
        licenses_popup.setMinimumSize(950, 950)
        
        # Windows용 다크 테마 제목 표시줄 설정
        apply_dark_title_bar(licenses_popup)
        
        # 다크 테마 배경 설정
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        licenses_popup.setPalette(palette)
        licenses_popup.setAutoFillBackground(True)
        
        # 메인 레이아웃 설정
        main_layout = QVBoxLayout(licenses_popup)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # QTextBrowser로 변경 - 마크다운 지원 및 텍스트 선택 가능
        scroll_content = QTextBrowser()
        scroll_content.setOpenExternalLinks(True)  # 외부 링크 열기 허용
        scroll_content.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {ThemeManager.get_color('bg_primary')};
                color: {ThemeManager.get_color('text')};
                border: none;
                selection-background-color: #505050;
                selection-color: white;
            }}
        """)
        
        # HTML 스타일 추가 (마크다운 스타일 에뮬레이션)
        html_style = """
        <style>
            body { color: #D8D8D8; font-family: Arial, sans-serif; }
            h1 { font-size: 18px; margin-top: 20px; margin-bottom: 15px; color: #FFFFFF; }
            h2 { font-size: 16px; margin-top: 15px; margin-bottom: 10px; color: #FFFFFF; }
            p { margin: 8px 0; }
            ul { margin-left: 20px; }
            li { margin: 5px 0; }
            a { color: #42A5F5; text-decoration: none; }
            a:hover { text-decoration: underline; }
            hr { border: 0; height: 1px; background-color: #555555; margin: 20px 0; }
        </style>
        """
        
        # 라이선스 정보 HTML 변환
        licenses_html = f"""
        {html_style}
        <h1>Open Source Libraries and Licenses</h1>
        <p>This application uses the following open source libraries:</p>

        <h2>PySide6 (Qt for Python)</h2>
        <ul>
        <li><strong>License</strong>: LGPL-3.0</li>
        <li><strong>Website</strong>: <a href="https://www.qt.io/qt-for-python">https://www.qt.io/qt-for-python</a></li>
        <li>Qt for Python is the official Python bindings for Qt, providing access to the complete Qt framework.</li>
        </ul>

        <h2>Pillow (PIL Fork)</h2>
        <ul>
        <li><strong>License</strong>: HPND License (Historical Permission Notice and Disclaimer)</li>
        <li><strong>Website</strong>: <a href="https://pypi.org/project/pillow/">https://pypi.org/project/pillow/</a></li>
        <li>Pillow is the friendly PIL fork. PIL is the Python Imaging Library that adds image processing capabilities to your Python interpreter.</li>
        </ul>

        <h2>pillow-heif</h2>
        <ul>
        <li><strong>License</strong>: Apache-2.0 (Python wrapper), LGPL-3.0 (libheif core)</li>
        <li><strong>Website</strong>: <a href="https://github.com/bigcat88/pillow_heif">https://github.com/bigcat88/pillow_heif</a></li>
        <li>A Pillow-plugin for HEIF/HEIC support, powered by libheif.</li>
        </ul>

        <h2>piexif</h2>
        <ul>
        <li><strong>License</strong>: MIT License</li>
        <li><strong>Website</strong>: <a href="https://github.com/hMatoba/Piexif">https://github.com/hMatoba/Piexif</a></li>
        <li>Piexif is a pure Python library for reading and writing EXIF data in JPEG and TIFF files.</li>
        </ul>

        <h2>rawpy</h2>
        <ul>
        <li><strong>License</strong>: MIT License</li>
        <li><strong>Website</strong>: <a href="https://github.com/letmaik/rawpy">https://github.com/letmaik/rawpy</a></li>
        <li>Rawpy provides Python bindings to LibRaw, allowing you to read and process camera RAW files.</li>
        </ul>

        <h2>LibRaw (used by rawpy)</h2>
        <ul>
        <li><strong>License</strong>: LGPL-2.1 or CDDL-1.0</li>
        <li><strong>Website</strong>: <a href="https://www.libraw.org/">https://www.libraw.org/</a></li>
        <li>LibRaw is a library for reading RAW files obtained from digital photo cameras.</li>
        </ul>

        <h2>ExifTool</h2>
        <ul>
        <li><strong>License</strong>: Perl's Artistic License / GNU GPL</li>
        <li><strong>Website</strong>: <a href="https://exiftool.org/">https://exiftool.org/</a></li>
        <li>ExifTool is a platform-independent Perl library and command-line application for reading, writing and editing meta information in a wide variety of files.</li>
        </ul>

        <h2>UIW Icon Kit</h2>
        <ul>
        <li><strong>License</strong>: MIT License</li>
        <li><strong>Website</strong>: <a href="https://iconduck.com/sets/uiw-icon-kit">https://iconduck.com/sets/uiw-icon-kit</a></li>
        <li>UIW Icon Kit is an Icon Set of 214 solid icons that can be used for both personal and commercial purposes.</li>
        </ul>

        <hr>

        <p>Each of these libraries is subject to its own license terms. Full license texts are available at the respective project websites. This software is not affiliated with or endorsed by any of these projects or their authors.</p>
        """
        
        # HTML 형식으로 내용 설정
        scroll_content.setHtml(licenses_html)
        
        # 확인 버튼 생성
        close_button = QPushButton(LanguageManager.translate("닫기"))
        close_button.setStyleSheet(f"""
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
        close_button.clicked.connect(licenses_popup.accept)
        
        # 버튼 컨테이너 (가운데 정렬)
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        button_layout.addStretch(1)
        
        # 메인 레이아웃에 위젯 추가
        main_layout.addWidget(scroll_content, 1)  # 스크롤 영역에 확장성 부여
        main_layout.addWidget(button_container)
        
        # 팝업 표시
        licenses_popup.exec()

    def generate_combobox_style(self):
        """현재 테마에 맞는 콤보박스 스타일 생성"""
        return f"""
            QComboBox {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: none;
                padding: {UIScaleManager.get("combobox_padding")}px;
                border-radius: 1px;
            }}
            QComboBox:hover {{
                background-color: #555555;
            }}
            QComboBox QAbstractItemView {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                selection-background-color: #505050;
                selection-color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')};
                padding: 0px; /* 메뉴 자체의 내부 여백 */
            }}
            /* 드롭다운 메뉴의 각 항목(item)에 대한 스타일 */
            QComboBox QAbstractItemView::item {{
                padding: 6px 10px; /* 상하, 좌우 여백 */
                min-height: 25px; /* 최소 높이를 지정하여 너무 좁아지지 않게 함 (선택 사항) */
            }}
        """

    def setup_dark_theme(self):
        """다크 테마 설정"""
        app = QApplication.instance()
        
        # 다크 팔레트 생성
        dark_palette = QPalette()
        
        # 다크 테마 색상 설정
        dark_palette.setColor(QPalette.Window, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # 어두운 비활성화 색상
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
        
        # 팔레트 적용
        app.setPalette(dark_palette)
        
        # 스타일시트 추가 설정
        app.setStyleSheet(f"""
            QToolTip {{
                color: {ThemeManager.get_color('text')};
                background-color: {ThemeManager.get_color('bg_secondary')};
                border: 1px solid {ThemeManager.get_color('border')};
            }}
            QSplitter::handle {{
                background-color: {ThemeManager.get_color('bg_primary')};
            }}
            QSplitter::handle:horizontal {{
                width: 1px;
            }}
        """)
    
    def adjust_layout(self):
        """
        UIScaleManager가 제공하는 min/max 너비 범위 내에서 
        스플리터의 초기 레이아웃을 설정합니다.
        """
        window_width = self.width()

        # 1. UIScaleManager로부터 이상적인(min) 너비와 최대(max) 너비를 가져옵니다.
        control_min_width = UIScaleManager.get("control_panel_min_width")
