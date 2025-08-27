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
            if hasattr(self, 'language_group'):
                lang_button_id = 0 if language == "en" else 1
                button_to_check = self.language_group.button(lang_button_id)
                if button_to_check: button_to_check.setChecked(True)
            if hasattr(self, 'date_format_combo'):
                idx = self.date_format_combo.findData(date_format)
                if idx >= 0: self.date_format_combo.setCurrentIndex(idx)
            if hasattr(self, 'theme_combo'):
                index = self.theme_combo.findData(theme)
                if index >= 0: self.theme_combo.setCurrentIndex(index)
            if hasattr(self, 'panel_position_group'):
                panel_button_id = 1 if self.control_panel_on_right else 0
                panel_button_to_check = self.panel_position_group.button(panel_button_id)
                if panel_button_to_check: panel_button_to_check.setChecked(True)
            if hasattr(self, 'filename_toggle_grid'):
                self.filename_toggle_grid.setChecked(self.show_grid_filenames)
            if hasattr(self, 'viewport_speed_combo'):
                idx = self.viewport_speed_combo.findData(self.viewport_move_speed)
                if idx >= 0: self.viewport_speed_combo.setCurrentIndex(idx)
            if hasattr(self, 'mouse_wheel_photo_radio') and hasattr(self, 'mouse_wheel_none_radio'):
                if self.mouse_wheel_action == 'photo_navigation': self.mouse_wheel_photo_radio.setChecked(True)
                else: self.mouse_wheel_none_radio.setChecked(True)
            if hasattr(self, 'mouse_wheel_sensitivity_combo'):
                index = self.mouse_wheel_sensitivity_combo.findData(self.mouse_wheel_sensitivity)
                if index >= 0: self.mouse_wheel_sensitivity_combo.setCurrentIndex(index)
            if hasattr(self, 'mouse_pan_sensitivity_combo'):
                import math
                for i in range(self.mouse_pan_sensitivity_combo.count()):
                    if math.isclose(self.mouse_pan_sensitivity_combo.itemData(i), self.mouse_pan_sensitivity):
                        self.mouse_pan_sensitivity_combo.setCurrentIndex(i)
                        break
            if hasattr(self, 'folder_count_combo'):
                index = self.folder_count_combo.findData(self.folder_count)
                if index >= 0: self.folder_count_combo.setCurrentIndex(index)
            self.minimap_toggle.setChecked(loaded_data.get("minimap_visible", True))

            self._update_settings_styles()
            
            # 3. 폴더 및 파일 관련 상태 변수 설정
            self.current_folder = loaded_data.get("current_folder", "")
            self.raw_folder = loaded_data.get("raw_folder", "")
            raw_files_str = loaded_data.get("raw_files", {})
            self.raw_files = {k: Path(v) for k, v in raw_files_str.items() if v and Path(v).exists()}
            self.is_raw_only_mode = loaded_data.get("is_raw_only_mode", False)
            self.last_loaded_raw_method_from_state = loaded_data.get("last_used_raw_method", "preview")

            self.current_image_index = loaded_data.get("current_image_index", -1)
            self.current_grid_index = loaded_data.get("current_grid_index", 0)
            self.grid_page_start_index = loaded_data.get("grid_page_start_index", 0)
            saved_grid_mode = loaded_data.get("grid_mode", "Off")
            saved_compare_mode = loaded_data.get("compare_mode_active", False)
            
            image_B_path_str = loaded_data.get("image_B_path", "")
            if saved_compare_mode and image_B_path_str and Path(image_B_path_str).exists():
                self.compare_mode_active = True
                self.image_B_path = Path(image_B_path_str)
            else:
                self.compare_mode_active = False
                self.image_B_path = None
            
            if self.is_raw_only_mode and self.last_loaded_raw_method_from_state == "decode":
                self.grid_mode = "Off"
                self.compare_mode_active = False
                logging.info("RAW+Decode 모드이므로 Grid/Compare 모드를 강제로 해제합니다.")
            else:
                # grid_mode가 None인 경우를 방지
                self.grid_mode = saved_grid_mode if saved_grid_mode is not None else "Off"

            if hasattr(self, 'grid_mode_group'):
                self.grid_mode_group.blockSignals(True)

                if self.compare_mode_active:
                    if hasattr(self, 'compare_radio'):
                        self.compare_radio.setChecked(True)
                elif self.grid_mode == "Off":
                    if hasattr(self, 'grid_off_radio'):
                        self.grid_off_radio.setChecked(True)
                else:
                    if hasattr(self, 'grid_on_radio'):
                        self.grid_on_radio.setChecked(True)
                    if hasattr(self, 'grid_size_combo'):
                        # grid_mode가 None이 아니라고 확신할 수 있음
                        combo_text = self.grid_mode.replace("x", " x ")
                        index = self.grid_size_combo.findText(combo_text)
                        if index != -1:
                            self.grid_size_combo.setCurrentIndex(index)
                
                self.grid_mode_group.blockSignals(False)
            
            if self.is_raw_only_mode and self.last_loaded_raw_method_from_state == "decode":
                raw_folder_path = loaded_data.get("raw_folder", "")
                if raw_folder_path and Path(raw_folder_path).is_dir():
                    self._show_first_raw_decode_progress()
            
            # 5. UI 컨트롤 업데이트 (폴더 경로 등)
            if self.current_folder and Path(self.current_folder).is_dir(): self.folder_path_label.setText(self.current_folder)
            else: self.current_folder = ""; self.folder_path_label.setText(LanguageManager.translate("폴더 경로"))
            if self.raw_folder and Path(self.raw_folder).is_dir(): self.raw_folder_path_label.setText(self.raw_folder)
            else: self.raw_folder = ""; self.raw_folder_path_label.setText(LanguageManager.translate("폴더 경로"))
            
            self._rebuild_folder_selection_ui()
            self.update_all_folder_labels_state()
            
            # 6. 이미지 목록 로드 시작
            if self.is_raw_only_mode:
                if self.raw_folder and Path(self.raw_folder).is_dir():
                    raw_files_to_load = self.reload_raw_files_from_state(self.raw_folder)
                    if raw_files_to_load:
                        self.start_background_loading(
                            mode='raw_only',
                            jpg_folder_path=self.raw_folder,
                            raw_folder_path=None,
                            raw_file_list=raw_files_to_load
                        )
                    else:
                        self._is_silent_load = False
                        self.update_all_ui_after_load_failure_or_first_run()
                else:
                    self._is_silent_load = False
                    self.update_all_ui_after_load_failure_or_first_run()
            elif self.current_folder and Path(self.current_folder).is_dir():
                mode_on_load = 'jpg_with_raw' if self.raw_folder and Path(self.raw_folder).is_dir() else 'jpg_only'
                self.start_background_loading(
                    mode=mode_on_load,
                    jpg_folder_path=self.current_folder,
                    raw_folder_path=self.raw_folder,
                    raw_file_list=None
                )
            else:
                self._is_silent_load = False
                self.update_all_ui_after_load_failure_or_first_run()

            # 7. 성능 프로필 UI 동기화
            saved_profile = loaded_data.get("performance_profile")
            if saved_profile: HardwareProfileManager.set_profile_manually(saved_profile)
            self._sync_performance_profile_ui()
            self.update_all_settings_controls_text()
            self._apply_panel_position()
            return True
        except Exception as e:
            logging.error(f"VibeCullingApp.load_state: 상태 불러오는 중 예외 발생: {e}", exc_info=True)
            self.show_themed_message_box(QMessageBox.Critical, 
                                         LanguageManager.translate("상태 로드 오류"), 
                                         f"{LanguageManager.translate('저장된 상태 파일을 불러오는 데 실패했습니다. 기본 설정으로 시작합니다.')}\n\nError: {e}")
            self.initialize_to_default_state()
            self.update_all_ui_after_load_failure_or_first_run()
            QTimer.singleShot(0, self._apply_panel_position)
            self.setFocus()
            self.update_all_settings_controls_text()
            self.update_thumbnail_panel_style()
            self._apply_panel_position()
            return True

    def _force_update_all_styles_after_load(self):
        """
        상태 로드 후 모든 UI 스타일을 현재 테마에 맞게 강제로 다시 적용합니다.
        이는 setChecked 등으로 인해 스타일이 초기화되는 문제를 해결합니다.
        """
        logging.info("상태 로드 완료 후 모든 UI 스타일 강제 업데이트 시작...")
        self.update_ui_colors()  # 메인 창 UI 스타일 업데이트
        self._update_settings_styles() # 설정 창 컨트롤 스타일 업데이트
        logging.info("모든 UI 스타일 강제 업데이트 완료.")

    def load_session(self, session_name: str):
        """저장된 작업 세션을 불러옵니다."""
        if session_name not in self.saved_sessions:
            logging.error(f"세션 '{session_name}'을(를) 찾을 수 없습니다.")
            self.show_themed_message_box(QMessageBox.Critical, LanguageManager.translate("불러오기 오류"), LanguageManager.translate("선택한 세션을 찾을 수 없습니다."))
            return False

        self._show_session_load_success_popup = True
        logging.info(f"세션 불러오기 시작: {session_name}")
        session_data = self.saved_sessions[session_name]

        # 0. 리소스 정리
        self.resource_manager.cancel_all_tasks()
        if hasattr(self, 'image_loader'): self.image_loader.clear_cache()
        self.fit_pixmap_cache.clear()
        if hasattr(self, 'grid_thumbnail_cache'):
            for key in self.grid_thumbnail_cache: self.grid_thumbnail_cache[key].clear()
        self.original_pixmap = None

        # 1. 상태 변수 설정 (뷰와 직접 관련 없는 것들)
        self.image_rotations = session_data.get("image_rotations", {})
        loaded_folder_count = session_data.get("folder_count", 3)
        if loaded_folder_count != self.folder_count:
            self.folder_count = loaded_folder_count
            if hasattr(self, 'folder_count_combo'):
                idx = self.folder_count_combo.findData(self.folder_count)
                if idx >= 0: self.folder_count_combo.setCurrentIndex(idx)
        
        self.current_folder = session_data.get("current_folder", "")
        self.raw_folder = session_data.get("raw_folder", "")
        raw_files_str_dict = session_data.get("raw_files", {})
        self.raw_files = {k: Path(v) for k, v in raw_files_str_dict.items() if v}
        self.move_raw_files = session_data.get("move_raw_files", True)
        loaded_folders = session_data.get("target_folders", [])
        self.target_folders = (loaded_folders + [""] * self.folder_count)[:self.folder_count]
        self.is_raw_only_mode = session_data.get("is_raw_only_mode", False)
        self.last_loaded_raw_method_from_state = session_data.get("last_used_raw_method", "preview")

        # 2. UI 재구성 및 경로 표시
        self._rebuild_folder_selection_ui()
        if self.current_folder and Path(self.current_folder).is_dir(): self.folder_path_label.setText(self.current_folder)
        else: self.current_folder = ""; self.folder_path_label.setText(LanguageManager.translate("폴더 경로"))
        if self.raw_folder and Path(self.raw_folder).is_dir(): self.raw_folder_path_label.setText(self.raw_folder)
        else: self.raw_folder = ""; self.raw_folder_path_label.setText(LanguageManager.translate("폴더 경로"))
        self.update_all_folder_labels_state()

        # 3. 뷰 상태를 임시 변수에 저장
        self._pending_view_state = {
            "zoom_mode": session_data.get("zoom_mode", "Fit"),
            "grid_mode": session_data.get("grid_mode", "Off"),
            "compare_mode_active": session_data.get("compare_mode_active", False),
            "current_image_index": session_data.get("current_image_index", -1),
            "current_grid_index": session_data.get("current_grid_index", 0),
            "grid_page_start_index": session_data.get("grid_page_start_index", 0),
            "image_B_path": session_data.get("image_B_path", ""),
        }

        # 4. 비동기 로딩 시작
        self._is_silent_load = True
        images_loaded_successfully = False
        
        if self.is_raw_only_mode:
            if self.raw_folder and Path(self.raw_folder).is_dir():
                raw_files_to_load = self.reload_raw_files_from_state(self.raw_folder)
                if raw_files_to_load:
                    if self.last_loaded_raw_method_from_state == "decode": self._show_first_raw_decode_progress()
                    self.start_background_loading('raw_only', self.raw_folder, None, raw_files_to_load)
                    images_loaded_successfully = True
        elif self.current_folder and Path(self.current_folder).is_dir():
            mode_on_load = 'jpg_with_raw' if self.raw_folder and Path(self.raw_folder).is_dir() else 'jpg_only'
            self.start_background_loading(mode_on_load, self.current_folder, self.raw_folder, None)
            images_loaded_successfully = True

        if not images_loaded_successfully:
            self._is_silent_load = False
            self._pending_view_state = None
            self.update_all_ui_after_load_failure_or_first_run()
            return False
            
        if self.session_management_popup and self.session_management_popup.isVisible():
            self.session_management_popup.accept()

        logging.info(f"세션 '{session_name}' 불러오기 시작됨.")
        return True

    def _apply_view_state_after_load(self, state_data):
        """
        세션 로드 완료 후, 저장된 상태 데이터에 기반하여 UI와 뷰를 최종적으로 설정합니다.
        """
        logging.info("세션 뷰 상태 적용 시작...")
        
        # 1. 상태 변수 설정
        self.zoom_mode = state_data.get("zoom_mode", "Fit")
        # grid_mode와 compare_mode_active는 load_state에서 이미 설정됨
        self.current_image_index = state_data.get("current_image_index", -1)
        self.current_grid_index = state_data.get("current_grid_index", 0)
        self.grid_page_start_index = state_data.get("grid_page_start_index", 0)
        
        image_B_path_str = state_data.get("image_B_path", "")
        if self.compare_mode_active and image_B_path_str and Path(image_B_path_str).exists():
            self.image_B_path = Path(image_B_path_str)
        else:
            self.image_B_path = None
            # B 경로가 유효하지 않으면 compare_mode_active를 다시 False로 설정
            if self.compare_mode_active:
                self.compare_mode_active = False
                self.grid_mode = state_data.get("grid_mode", "Off") # Compare가 취소됐으니 원래 grid 모드로

        # 2. UI 컨트롤 동기화 (load_state에서 이미 처리됨)
        # 라디오 버튼 상태는 load_state에서 명시적으로 설정해주었으므로 여기서는 생략 가능

        # 3. 마지막으로 보던 이미지 인덱스 유효성 검사 및 설정
        loaded_index = self.current_image_index
        if not (0 <= loaded_index < len(self.image_files)):
            loaded_index = 0 if self.image_files else -1
            logging.warning(f"복원된 인덱스({self.current_image_index})가 유효하지 않아 0으로 재설정합니다.")

        if self.grid_mode != "Off":
            rows, cols = self._get_grid_dimensions()
            num_cells = rows * cols if rows > 0 else 1
            self.grid_page_start_index = (loaded_index // num_cells) * num_cells
            self.current_grid_index = loaded_index % num_cells
        else:
            self.current_image_index = loaded_index

        # 4. 최종 뷰 업데이트 (수정된 함수 호출)
        self._update_view_for_grid_change()
        
        def display_content_after_layout():
            if self.grid_mode == "Off": # 이제 compare 모드도 여기에 포함됨
                self.display_current_image()
                if self.compare_mode_active and self.image_B_path:
                    self.original_pixmap_B = self.image_loader.load_image_with_orientation(str(self.image_B_path))
                    self._apply_zoom_to_canvas('B')
                    self._sync_viewports()
                self.update_compare_filenames()

        QTimer.singleShot(50, display_content_after_layout)

        final_index_to_show = self.current_image_index if self.grid_mode == "Off" else self.grid_page_start_index + self.current_grid_index
        if final_index_to_show >= 0:
            self.thumbnail_panel.set_current_index(final_index_to_show)

        logging.info("세션 뷰 상태 적용 완료.")



    def _sync_performance_profile_ui(self):
        """현재 활성화된 HardwareProfileManager 프로필을 UI 콤보박스와 동기화합니다."""
        # 저장된 프로필이 있다면 수동으로 설정 (load_state에서 호출 시)
        # 이 부분은 load_state에서만 처리하도록 분리하는 것이 더 명확할 수 있습니다.
        # 여기서는 현재 활성화된 프로필을 UI에 반영하는 데 집중합니다.
        
        current_profile_key = HardwareProfileManager.get_current_profile_key()
        if hasattr(self, 'performance_profile_combo'):
            index = self.performance_profile_combo.findData(current_profile_key)
            if index != -1:
                # 시그널 발생을 막기 위해 blockSignals 사용
                self.performance_profile_combo.blockSignals(True)
                self.performance_profile_combo.setCurrentIndex(index)
                self.performance_profile_combo.blockSignals(False)
                logging.debug(f"성능 프로필 UI 동기화 완료: '{current_profile_key}'")

    def initialize_to_default_state(self):
        """애플리케이션 상태를 안전한 기본값으로 초기화합니다 (파일 로드 실패 시 등)."""
        logging.info("VibeCullingApp.initialize_to_default_state: 앱 상태를 기본값으로 초기화합니다.")

        # --- 1. 모든 백그라운드 작업 및 타이머 중지 ---
        logging.debug("  -> 활성 타이머 및 백그라운드 작업 중지...")
        
        # 리소스 매니저를 통해 모든 스레드/프로세스 풀의 작업을 취소합니다.
        if hasattr(self, 'resource_manager'):
            self.resource_manager.cancel_all_tasks()
        
        # 그리드 썸네일 전용 스레드 풀의 작업도 취소합니다.
        if hasattr(self, 'active_thumbnail_futures'):
            for future in self.active_thumbnail_futures:
                future.cancel()
            self.active_thumbnail_futures.clear()

        # 모든 활성 타이머를 중지합니다.
        if hasattr(self, 'loading_indicator_timer') and self.loading_indicator_timer.isActive():
            self.loading_indicator_timer.stop()
        if hasattr(self, 'state_save_timer') and self.state_save_timer.isActive():
            self.state_save_timer.stop()
        if hasattr(self, 'viewport_move_timer') and self.viewport_move_timer.isActive():
            self.viewport_move_timer.stop()
        if hasattr(self, 'idle_preload_timer') and self.idle_preload_timer.isActive():
            self.idle_preload_timer.stop()
        if hasattr(self, 'wheel_reset_timer') and self.wheel_reset_timer.isActive():
            self.wheel_reset_timer.stop()
        # raw_result_processor_timer와 memory_monitor_timer는 앱 전역에서 계속 실행되어야 하므로 중지하지 않습니다.

        # --- 2. 상태 변수 초기화 ---
        logging.debug("  -> 상태 변수 초기화...")

        # 폴더 및 파일 관련 상태
        self.current_folder = ""
        self.raw_folder = ""
        self.image_files = []
        self.raw_files = {}
        self.is_raw_only_mode = False
        self.move_raw_files = True
        self.folder_count = 3
        self.target_folders = [""] * self.folder_count
        
        # 뷰 관련 상태
        self.zoom_mode = "Fit"
        self.zoom_spin_value = 2.0
        self.grid_mode = "Off"
        self.current_image_index = -1
        self.current_grid_index = 0
        self.grid_page_start_index = 0
        self.previous_grid_mode = None
        self.original_pixmap = None
        self.compare_mode_active = False
        self.image_B_path = None
        self.original_pixmap_B = None

        # 캐시 초기화
        if hasattr(self, 'image_loader'):
            self.image_loader.clear_cache()
            self.image_loader.set_raw_load_strategy("preview")
        self.fit_pixmap_cache.clear()
        self.last_fit_size = (0,0)

        # 기타 UI 및 상호작용 관련 상태
        self.last_processed_camera_model = None
        self.viewport_move_speed = 5
        self.show_grid_filenames = True
        self.mouse_wheel_sensitivity = 1
        self.mouse_wheel_accumulator = 0
        self.last_wheel_direction = 0
        self.control_panel_on_right = False
        self.pressed_keys_for_viewport.clear()
        self.pressed_number_keys.clear()
        self.is_potential_drag = False
        self.is_idle_preloading_active = False

        # Undo/Redo 히스토리 초기화
        self.move_history = []
        self.history_pointer = -1
        
        logging.info("  -> 상태 초기화 완료.")

    def update_all_ui_after_load_failure_or_first_run(self):
        """load_state 실패 또는 첫 실행 시 UI를 기본 상태로 설정하는 헬퍼"""
        self.folder_path_label.setText(LanguageManager.translate("폴더 경로"))
        self.raw_folder_path_label.setText(LanguageManager.translate("폴더 경로"))
        for label in self.folder_path_labels:
            label.setText(LanguageManager.translate("폴더 경로"))
        self.update_jpg_folder_ui_state()
        self.update_raw_folder_ui_state()
        self.update_all_folder_labels_state()
        self.update_match_raw_button_state()
        self.grid_mode = "Off"; self.grid_off_radio.setChecked(True)
        self.zoom_mode = "Fit"; self.fit_radio.setChecked(True)
        self.zoom_spin_value = 2.0
        # SpinBox UI 업데이트 추가
        if hasattr(self, 'zoom_spin'):
            self.zoom_spin.setValue(int(self.zoom_spin_value * 100))
        self.update_zoom_radio_buttons_state()
        self.display_current_image() # 빈 화면 표시
        self.update_counter_layout()
        self.toggle_minimap(False)
        QTimer.singleShot(0, self._apply_panel_position)
        self.setFocus()

    def reload_raw_files_from_state(self, folder_path):
        """ 저장된 RAW 폴더 경로에서 파일 목록을 다시 로드하고 리스트를 반환 """
        target_path = Path(folder_path)
        temp_raw_file_list = []
        try:
            # RAW 파일 검색
            for ext in self.raw_extensions:
                temp_raw_file_list.extend(target_path.glob(f'*{ext}'))
                temp_raw_file_list.extend(target_path.glob(f'*{ext.upper()}'))

            # 중복 제거 및 정렬
            unique_raw_files = sorted(list(set(temp_raw_file_list)))

            if unique_raw_files:
                logging.info(f"RAW 파일 목록 복원됨: {len(unique_raw_files)}개")
                return unique_raw_files # 성공 시 파일 목록 반환
            else:
                logging.warning(f"경고: RAW 폴더({folder_path})에서 파일을 찾지 못했습니다.")
                return None # 실패 시 None 반환
        except Exception as e:
            logging.error(f"RAW 파일 목록 리로드 중 오류 발생: {e}")
            return None # 실패 시 None 반환

    def add_move_history(self, move_info):
        """ 파일 이동 기록을 히스토리에 추가하고 포인터 업데이트 (배치 작업 지원) """
        logging.debug(f"Adding to history: {move_info}") # 디버깅 로그

        # 현재 포인터 이후의 기록(Redo 가능한 기록)은 삭제
        if self.history_pointer < len(self.move_history) - 1:
            self.move_history = self.move_history[:self.history_pointer + 1]

        # 새 기록 추가
        self.move_history.append(move_info)

        # 히스토리 최대 개수 제한
        if len(self.move_history) > self.max_history:
            self.move_history.pop(0) # 가장 오래된 기록 제거

        # 포인터를 마지막 기록으로 이동
        self.history_pointer = len(self.move_history) - 1
        logging.debug(f"History pointer updated to: {self.history_pointer}") # 디버깅 로그
        logging.debug(f"Current history length: {len(self.move_history)}") # 디버깅 로그

    def add_batch_move_history(self, move_entries):
        """ 배치 파일 이동 기록을 히스토리에 추가 """
        if not move_entries:
            return
            
        # 배치 작업을 하나의 히스토리 엔트리로 묶음
        batch_entry = {
            "type": "batch",
            "entries": move_entries,
            "timestamp": datetime.now().isoformat()
        }
        
        logging.debug(f"Adding batch to history: {len(move_entries)} entries")
        self.add_move_history(batch_entry)

    def undo_move(self):
        """ 마지막 파일 이동 작업을 취소 (Undo) - 배치 작업 지원 """
        if self.history_pointer < 0:
            logging.warning("Undo: 히스토리 없음")
            return # 실행 취소할 작업 없음

        # 현재 포인터에 해당하는 기록 가져오기
        move_info = self.move_history[self.history_pointer]
        logging.debug(f"Undoing: {move_info}") # 디버깅 로그

        # 배치 작업인지 확인
        if isinstance(move_info, dict) and move_info.get("type") == "batch":
            # 배치 작업 Undo
            self.undo_batch_move(move_info["entries"])
        else:
            # 단일 작업 Undo (기존 로직)
            self.undo_single_move(move_info)

        # 히스토리 포인터 이동
        self.history_pointer -= 1
        logging.debug(f"Undo complete. History pointer: {self.history_pointer}")

    def undo_batch_move(self, batch_entries):
        """ 배치 이동 작업을 취소 """
        try:
            # 배치 엔트리들을 역순으로 처리하여 데이터 모델을 먼저 복원합니다.
            for move_info in reversed(batch_entries):
                # 1. 파일 시스템 복원
                jpg_source_path = Path(move_info["jpg_source"])
                jpg_target_path = Path(move_info["jpg_target"])
                raw_source_path = Path(move_info["raw_source"]) if move_info["raw_source"] else None
                raw_target_path = Path(move_info["raw_target"]) if move_info["raw_target"] else None
                
                if jpg_target_path.exists():
                    shutil.move(str(jpg_target_path), str(jpg_source_path))
                if raw_source_path and raw_target_path and raw_target_path.exists():
                    shutil.move(str(raw_target_path), str(raw_source_path))

                # 2. VibeCullingApp의 image_files 리스트 직접 복원 (핵심)
                index_before_move = move_info["index_before_move"]
                if jpg_source_path not in self.image_files:
                    if 0 <= index_before_move <= len(self.image_files):
                        self.image_files.insert(index_before_move, jpg_source_path)
                    else:
                        self.image_files.append(jpg_source_path)

                # 3. RAW 딕셔너리 복원
                if raw_source_path:
                    if jpg_source_path.stem not in self.raw_files:
                        self.raw_files[jpg_source_path.stem] = raw_source_path
            
            # 모든 데이터 복원 후, UI 업데이트 함수 호출
            self.update_ui_after_undo_batch(batch_entries)
            
        except Exception as e:
            logging.error(f"배치 Undo 중 오류 발생: {e}")
            self.show_themed_message_box(
                QMessageBox.Critical, 
                LanguageManager.translate("에러"), 
                f"{LanguageManager.translate('실행 취소 중 오류 발생')}: {str(e)}"
            )


    def undo_single_move_internal(self, move_info):
        """ 단일 이동 작업을 취소 (UI 업데이트 없음) """
        jpg_source_path = Path(move_info["jpg_source"])
        jpg_target_path = Path(move_info["jpg_target"])
        raw_source_path = Path(move_info["raw_source"]) if move_info["raw_source"] else None
        raw_target_path = Path(move_info["raw_target"]) if move_info["raw_target"] else None

        # 1. JPG 파일 원래 위치로 이동
        if jpg_target_path.exists():
            shutil.move(str(jpg_target_path), str(jpg_source_path))
            logging.debug(f"Undo: Moved {jpg_target_path} -> {jpg_source_path}")

        # 2. RAW 파일 원래 위치로 이동
        if raw_source_path and raw_target_path and raw_target_path.exists():
            shutil.move(str(raw_target_path), str(raw_source_path))
            logging.debug(f"Undo: Moved RAW {raw_target_path} -> {raw_source_path}")

        # 4. RAW 파일 딕셔너리 복원 (중복 검사 추가)
        if raw_source_path:
            if jpg_source_path.stem not in self.raw_files:
                self.raw_files[jpg_source_path.stem] = raw_source_path
                logging.debug(f"Undo: Restored RAW file mapping for {jpg_source_path.stem}")
            else:
                logging.warning(f"Undo: Skipped duplicate RAW file mapping for {jpg_source_path.stem}")

        if move_info.get("mode") == "CompareB":
            jpg_source_path = Path(move_info["jpg_source"])
            self.image_B_path = jpg_source_path
            # B 캔버스용 pixmap도 다시 로드
            self.original_pixmap_B = self.image_loader.load_image_with_orientation(str(self.image_B_path))
            self.update_compare_filenames()
            logging.debug(f"Undo: Restored image to Canvas B: {self.image_B_path.name}")

    def undo_single_move(self, move_info):
        """ 단일 이동 작업을 취소하고 UI를 업데이트합니다. """
        try:
            # 1. 파일 시스템 복원
            self.undo_single_move_internal(move_info)
            
            jpg_source_path = Path(move_info["jpg_source"])
            index_before_move = move_info["index_before_move"]
            
            # 2. 데이터 모델 복원
            self.thumbnail_panel.model.addItem(index_before_move, jpg_source_path)
            self.image_files = self.thumbnail_panel.model._image_files
            
            mode_before_move = move_info.get("mode", "Off")
            self.force_refresh = True
            
            # 3. 뷰 상태 복원
            if mode_before_move in ["CompareA", "CompareB"]:
                a_index = move_info.get("a_index_before_move", index_before_move) 
                if a_index >= len(self.image_files): a_index = len(self.image_files) - 1
                self.current_image_index = a_index
                self.compare_mode_active = True
                self.grid_mode = "Off" 
                self.compare_radio.setChecked(True)
                self._update_view_for_grid_change()
                
                def restore_compare_view():
                    self.display_current_image()
                    if self.image_B_path: 
                        self.original_pixmap_B = self.image_loader.load_image_with_orientation(str(self.image_B_path))
                        self._apply_zoom_to_canvas('B')
                    self._sync_viewports()
                    self.update_compare_filenames()
                QTimer.singleShot(50, restore_compare_view)
                
            elif mode_before_move == "Off":
                self.current_image_index = index_before_move
                if self.grid_mode != "Off" or self.compare_mode_active:
                    self.compare_mode_active = False
                    self.grid_mode = "Off"
                    self.grid_off_radio.setChecked(True)
                self._update_view_for_grid_change()
                self.display_current_image()
            else: # Grid 모드
                self.grid_mode = mode_before_move
                
                # UI 컨트롤을 업데이트하는 동안 신호 발생을 막아 _on_grid_mode_toggled의 자동 실행을 방지합니다.
                self.grid_mode_group.blockSignals(True)
                self.grid_on_radio.setChecked(True)
                self.grid_mode_group.blockSignals(False)

                self.grid_size_combo.blockSignals(True)
                combo_text = self.grid_mode.replace("x", " x ")
                index = self.grid_size_combo.findText(combo_text)
                if index != -1:
                    self.grid_size_combo.setCurrentIndex(index)
                self.grid_size_combo.blockSignals(False)
                
                self.update_grid_view() 
            
            self.update_counters()
            self.update_thumbnail_current_index()

        except Exception as e:
            logging.error(f"단일 Undo 작업 중 오류 발생: {e}", exc_info=True)
            self.show_themed_message_box(QMessageBox.Critical, "에러", f"실행 취소 중 오류 발생: {str(e)}")



    def update_ui_after_undo_batch(self, batch_entries):
        """ 배치 Undo 후 UI 업데이트 """
        if not batch_entries:
            return

        # 첫 번째 엔트리의 모드와 인덱스를 기준으로 UI 상태 복원
        first_entry = batch_entries[0]
        mode_before_move = first_entry.get("mode", "Off")
        first_index = first_entry["index_before_move"]
        
        self.force_refresh = True
        
        # 모델 구조가 변경되었으므로 썸네일 패널을 리셋합니다.
        self.thumbnail_panel.set_image_files(self.image_files)

        # Grid 모드 복원
        self.grid_mode = mode_before_move
        
        # 복원할 이미지들의 페이지 내 인덱스 계산
        restored_grid_indices = set()
        rows, cols = self._get_grid_dimensions()
        num_cells = rows * cols if rows > 0 else 1
        target_page_start_index = (first_index // num_cells) * num_cells
        
        for entry in batch_entries:
            idx = entry["index_before_move"]
            if target_page_start_index <= idx < target_page_start_index + num_cells:
                restored_grid_indices.add(idx - target_page_start_index)

        # UI 상태 설정
        self.grid_page_start_index = target_page_start_index
        self.current_grid_index = first_index - target_page_start_index
        self.selected_grid_indices = restored_grid_indices
        self.primary_selected_index = first_index

        # 라디오 버튼과 콤보박스 UI를 수동으로 동기화합니다.
        self.grid_on_radio.setChecked(True)
        combo_text = self.grid_mode.replace("x", " x ")
        index = self.grid_size_combo.findText(combo_text)
        if index != -1:
            self.grid_size_combo.setCurrentIndex(index)
        
        # 모든 상태 설정 후, 그리드 뷰를 완전히 새로고침합니다.
        self.update_grid_view()
        
        self.update_counters()
        self.update_thumbnail_current_index()






    def redo_move(self):
        """ 취소된 파일 이동 작업을 다시 실행 (Redo) - 배치 작업 지원 """
        if self.history_pointer >= len(self.move_history) - 1:
            logging.warning("Redo: 히스토리 없음")
            return # 다시 실행할 작업 없음

        # 다음 포인터로 이동하고 해당 기록 가져오기
        self.history_pointer += 1
        move_info = self.move_history[self.history_pointer]
        logging.debug(f"Redoing: {move_info}")

        # 배치 작업인지 확인
        if isinstance(move_info, dict) and move_info.get("type") == "batch":
            # 배치 작업 Redo
            self.redo_batch_move(move_info["entries"])
        else:
            # 단일 작업 Redo (기존 로직)
            self.redo_single_move(move_info)

        logging.debug(f"Redo complete. History pointer: {self.history_pointer}")

    def redo_batch_move(self, batch_entries):
        """ 배치 이동 작업을 다시 실행 """
        try:
            # 배치 엔트리들을 순서대로 처리하여 데이터 모델을 먼저 수정합니다.
            for move_info in batch_entries:
                # 1. 파일 시스템 이동
                jpg_source_path = Path(move_info["jpg_source"])
                jpg_target_path = Path(move_info["jpg_target"])
                raw_source_path = Path(move_info["raw_source"]) if move_info["raw_source"] else None
                raw_target_path = Path(move_info["raw_target"]) if move_info["raw_target"] else None

                if jpg_target_path.exists():
                    logging.warning(f"경고: Redo 대상 위치에 이미 파일 존재: {jpg_target_path}")
                if jpg_source_path.exists():
                    shutil.move(str(jpg_source_path), str(jpg_target_path))
                
                if raw_source_path and raw_target_path and raw_source_path.exists():
                    shutil.move(str(raw_source_path), str(raw_target_path))

                # 2. VibeCullingApp의 image_files 리스트에서 직접 제거 (핵심)
                try:
                    self.image_files.remove(jpg_source_path)
                except ValueError:
                    logging.warning(f"경고: Redo 시 파일 목록에서 경로를 찾지 못함: {jpg_source_path}")

                # 3. RAW 딕셔너리 업데이트
                if raw_source_path and jpg_source_path.stem in self.raw_files:
                    del self.raw_files[jpg_source_path.stem]
            
            # 모든 데이터 수정 후, UI 업데이트 함수 호출
            self.update_ui_after_redo_batch(batch_entries)
            
        except Exception as e:
            logging.error(f"배치 Redo 중 오류 발생: {e}")
            self.show_themed_message_box(
                QMessageBox.Critical, 
                LanguageManager.translate("에러"), 
                f"{LanguageManager.translate('다시 실행 중 오류 발생')}: {str(e)}"
            )


    def redo_single_move_internal(self, move_info):
        """ 단일 이동 작업을 다시 실행 (UI 업데이트 없음) """
        jpg_source_path = Path(move_info["jpg_source"])
        jpg_target_path = Path(move_info["jpg_target"])
        raw_source_path = Path(move_info["raw_source"]) if move_info["raw_source"] else None
        raw_target_path = Path(move_info["raw_target"]) if move_info["raw_target"] else None

        # 1. JPG 파일 다시 대상 위치로 이동
        if jpg_target_path.exists():
            logging.warning(f"경고: Redo 대상 위치에 이미 파일 존재: {jpg_target_path}")

        if jpg_source_path.exists():
            shutil.move(str(jpg_source_path), str(jpg_target_path))
            logging.debug(f"Redo: Moved {jpg_source_path} -> {jpg_target_path}")

        # 2. RAW 파일 다시 대상 위치로 이동
        if raw_source_path and raw_target_path:
            if raw_target_path.exists():
                logging.warning(f"경고: Redo 대상 RAW 위치에 이미 파일 존재: {raw_target_path}")
            if raw_source_path.exists():
                shutil.move(str(raw_source_path), str(raw_target_path))
                logging.debug(f"Redo: Moved RAW {raw_source_path} -> {raw_target_path}")

        # 4. RAW 파일 딕셔너리 업데이트
        if raw_source_path and jpg_source_path.stem in self.raw_files:
            del self.raw_files[jpg_source_path.stem]

    def update_ui_after_redo_batch(self, batch_entries):
        """ 배치 Redo 후 UI 업데이트 """
        if not batch_entries:
            return
            
        first_entry = batch_entries[0]
        mode_at_move = first_entry.get("mode", "Off")
        
        self.force_refresh = True
        
        if self.image_files:
            first_removed_index = first_entry["index_before_move"]
            new_index = min(first_removed_index, len(self.image_files) - 1)
            if new_index < 0: new_index = 0
            
            if mode_at_move == "Off":
                self.current_image_index = new_index
                if self.grid_mode != "Off":
                    self.grid_mode = "Off"
                    self.grid_off_radio.setChecked(True)
                    self.update_zoom_radio_buttons_state()
                    self.update_counter_layout()
                if self.zoom_mode == "Fit":
                    self.last_fit_size = (0, 0)
                    self.fit_pixmap_cache.clear()
                self.display_current_image()
            else:
                # Grid 모드
                if self.grid_mode != mode_at_move:
                    self.grid_mode = mode_at_move
                    # 새로운 UI 상태로 업데이트
                    self.grid_on_radio.setChecked(True)
                    self.grid_size_combo.setEnabled(True)
                    combo_text = self.grid_mode.replace("x", " x ")
                    index = self.grid_size_combo.findText(combo_text)
                    if index != -1: self.grid_size_combo.setCurrentIndex(index)
                    self.update_zoom_radio_buttons_state()
                    self.update_counter_layout()

                rows, cols = self._get_grid_dimensions()
                num_cells = rows * cols
                self.grid_page_start_index = (new_index // num_cells) * num_cells
                self.current_grid_index = new_index % num_cells
                self.update_grid_view()
        else:
            # 모든 파일이 이동된 경우
            self.current_image_index = -1
            if self.grid_mode != "Off":
                self.grid_mode = "Off"
                self.grid_off_radio.setChecked(True)
                self.update_zoom_radio_buttons_state()
            self.display_current_image()
        
        self.update_counters()

    def redo_single_move(self, move_info):
        """ 단일 이동 작업을 다시 실행 (기존 로직) """
        try:
            # 1. 파일 시스템 이동
            self.redo_single_move_internal(move_info)

            # 2. 데이터 모델 변경
            index_to_remove = move_info["index_before_move"]
            self.thumbnail_panel.model.removeItem(index_to_remove)
            self.image_files = self.thumbnail_panel.model._image_files
            
            mode_at_move = move_info.get("mode", "Off")
            
            if self.image_files:
                redo_removed_index = move_info["index_before_move"]
                new_index = min(redo_removed_index, len(self.image_files) - 1)
                if new_index < 0: new_index = 0
                
                self.force_refresh = True

                if mode_at_move == "Off":
                    self.current_image_index = new_index
                    if self.grid_mode != "Off":
                        self.grid_mode = "Off"
                        self.grid_off_radio.setChecked(True)
                        self.update_zoom_radio_buttons_state()
                    if self.zoom_mode == "Fit":
                        self.last_fit_size = (0, 0)
                        self.fit_pixmap_cache.clear()
                    self.display_current_image()
                else:
                    # 페이지를 재계산하지 않고, 현재 페이지의 그리드 뷰만 새로고침합니다.
                    # Redo 후 현재 인덱스가 현재 페이지 범위를 벗어날 수 있으므로 안전하게 조정합니다.
                    rows, cols = self._get_grid_dimensions()
                    num_cells = rows * cols if rows > 0 else 1
                    current_page_image_count = min(num_cells, len(self.image_files) - self.grid_page_start_index)

                    if self.current_grid_index >= current_page_image_count and current_page_image_count > 0:
                        self.current_grid_index = current_page_image_count - 1
                    
                    self.grid_mode = mode_at_move
                    self.update_grid_view()
            else:
                # 모든 파일이 이동된 경우
                self.current_image_index = -1
                if self.grid_mode != "Off":
                    self.grid_mode = "Off"
                    self.grid_off_radio.setChecked(True)
                    self.update_zoom_radio_buttons_state()
                self.display_current_image()

            self.update_counters()
            self.update_thumbnail_current_index()
        except Exception as e:
            logging.error(f"단일 Redo 작업 중 오류 발생: {e}", exc_info=True)
            self.show_themed_message_box(QMessageBox.Critical, "에러", f"다시 실행 중 오류 발생: {str(e)}")



    def _cleanup_resources(self):
        """앱 종료 또는 재시작 시 호출되는 리소스 정리 함수"""
        logging.info("리소스 정리 시작...")
        
        # 타이머 중지
        if hasattr(self, 'memory_monitor_timer') and self.memory_monitor_timer.isActive(): self.memory_monitor_timer.stop()
        if hasattr(self, 'raw_result_processor_timer') and self.raw_result_processor_timer.isActive(): self.raw_result_processor_timer.stop()
        if hasattr(self, 'state_save_timer') and self.state_save_timer.isActive(): self.state_save_timer.stop()
        
        # 열려있는 다이얼로그 닫기
        if hasattr(self, 'file_list_dialog') and self.file_list_dialog and self.file_list_dialog.isVisible():
            self.file_list_dialog.close()

        # 메모리 집약적 객체 해제
        if hasattr(self, 'image_loader'): self.image_loader.cache.clear()
        self.fit_pixmap_cache.clear()
        if hasattr(self, 'grid_thumbnail_cache'):
            for key in self.grid_thumbnail_cache: self.grid_thumbnail_cache[key].clear()
        self.original_pixmap = None
        
        # 백그라운드 작업 취소 및 스레드 풀 종료
        if hasattr(self, 'resource_manager'): self.resource_manager.shutdown()
        if hasattr(self, 'folder_loader_thread') and self.folder_loader_thread.isRunning():
            if hasattr(self, 'folder_loader_worker'): self.folder_loader_worker.stop()
            self.folder_loader_thread.quit()
            if not self.folder_loader_thread.wait(500): self.folder_loader_thread.terminate()
        if hasattr(self, 'exif_thread') and self.exif_thread.isRunning():
            if hasattr(self, 'exif_worker'): self.exif_worker.stop()
            self.exif_thread.quit()
            if not self.exif_thread.wait(500): self.exif_thread.terminate()
        if hasattr(self, 'grid_thumbnail_executor'):
            self.grid_thumbnail_executor.shutdown(wait=False, cancel_futures=True)
        
        # 가비지 컬렉션
