        import gc
        gc.collect()
        logging.info("리소스 정리 완료.")        

    def closeEvent(self, event):
        """창 닫기 이벤트 처리 시 상태 저장 및 리소스 정리"""
        logging.info("앱 종료 요청됨.")

        if not self._is_resetting:
            self.save_state()

        if hasattr(self, 'copy_thread') and self.copy_thread.isRunning():
            self.copy_worker.stop()
            self.copy_queue.put(None) # 대기 중인 get()을 깨우기 위해 None 삽입
            self.copy_thread.quit()
            if not self.copy_thread.wait(1000): # 1초 대기
                self.copy_thread.terminate()
                logging.warning("복사 스레드를 강제 종료했습니다.")

        self._cleanup_resources()
        
        # 로그 핸들러 정리
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)

        super().closeEvent(event)

    def changeEvent(self, event):
        """창의 상태 변경 이벤트를 처리합니다 (활성화 시 포커스 설정)."""
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange:
            if self.isActiveWindow():
                # 창이 활성화될 때, 메인 윈도우 자체에 포커스를 설정합니다.
                # 이를 통해 키보드 이벤트를 즉시 받을 수 있습니다.
                self.setFocus()
                logging.debug("창 활성화됨: 메인 윈도우로 포커스 설정 완료.")


    def set_current_image_from_dialog(self, index):
        """FileListDialog에서 호출되어 특정 인덱스의 이미지 표시"""
        if not (0 <= index < len(self.image_files)):
            logging.error(f"오류: 잘못된 인덱스({index})로 이미지 설정 시도")
            return

        # 이미지 변경 전 강제 새로고침 플래그 설정
        self.force_refresh = True
        
        if self.grid_mode != "Off":
            # Grid 모드: 해당 인덱스가 포함된 페이지로 이동하고 셀 선택
            rows, cols = self._get_grid_dimensions()
            num_cells = rows * cols
            self.grid_page_start_index = (index // num_cells) * num_cells
            self.current_grid_index = index % num_cells

            # Grid 뷰 업데이트 (Grid 모드 유지 시)
            self.update_grid_view() 
        else:
            # Grid Off 모드: 해당 인덱스로 바로 이동
            self.current_image_index = index
            
            # Fit 모드인 경우 기존 캐시 무효화
            if self.zoom_mode == "Fit":
                self.last_fit_size = (0, 0)
                self.fit_pixmap_cache.clear()
            
            # 이미지 표시
            self.display_current_image()
            
            # 이미지 로더의 캐시 확인하여 이미 메모리에 있으면 즉시 적용을 시도
            image_path = str(self.image_files[index])
            if image_path in self.image_loader.cache:
                cached_pixmap = self.image_loader.cache[image_path]
                if cached_pixmap and not cached_pixmap.isNull():
                    # 캐시된 이미지가 있으면 즉시 적용 시도
                    self.original_pixmap = cached_pixmap
                    if self.zoom_mode == "Fit":
                        self.apply_zoom_to_image()

        # 메인 윈도우 활성화 및 포커스 설정
        self.activateWindow()
        self.setFocus()

    def highlight_folder_label(self, folder_index, highlight):
        """분류 폴더 레이블에 숫자 키 누름 하이라이트를 적용합니다."""
        if folder_index < 0 or folder_index >= len(self.folder_path_labels):
            return
        try:
            label = self.folder_path_labels[folder_index]
            # EditableFolderPathLabel에 새로 추가한 메서드 호출
            label.apply_keypress_highlight(highlight)
        except Exception as e:
            logging.error(f"highlight_folder_label 오류: {e}")

    def center_viewport(self):
        """뷰포트를 이미지 중앙으로 이동 (Zoom 100% 또는 Spin 모드에서만)"""
        try:
            # 전제 조건 확인
            if (self.grid_mode != "Off" or 
                self.zoom_mode not in ["100%", "Spin"] or 
                not self.original_pixmap):
                logging.debug("center_viewport: 조건 불만족 (Grid Off, Zoom 100%/Spin, 이미지 필요)")
                return False
            
            # 뷰포트 크기 가져오기
            view_width = self.scroll_area.width()
            view_height = self.scroll_area.height()
            
            # 이미지 크기 계산
            if self.zoom_mode == "100%":
                img_width = self.original_pixmap.width()
                img_height = self.original_pixmap.height()
            else:  # Spin 모드
                img_width = self.original_pixmap.width() * self.zoom_spin_value
                img_height = self.original_pixmap.height() * self.zoom_spin_value
            
            # 중앙 정렬 위치 계산
            if img_width <= view_width:
                # 이미지가 뷰포트보다 작으면 중앙 정렬
                new_x = (view_width - img_width) // 2
            else:
                # 이미지가 뷰포트보다 크면 이미지 중앙이 뷰포트 중앙에 오도록
                new_x = (view_width - img_width) // 2
            
            if img_height <= view_height:
                # 이미지가 뷰포트보다 작으면 중앙 정렬
                new_y = (view_height - img_height) // 2
            else:
                # 이미지가 뷰포트보다 크면 이미지 중앙이 뷰포트 중앙에 오도록
                new_y = (view_height - img_height) // 2
            
            # 위치 제한 (패닝 범위 계산과 동일한 로직)
            if img_width <= view_width:
                x_min = x_max = (view_width - img_width) // 2
            else:
                x_min = min(0, view_width - img_width)
                x_max = 0
            
            if img_height <= view_height:
                y_min = y_max = (view_height - img_height) // 2
            else:
                y_min = min(0, view_height - img_height)
                y_max = 0
            
            # 범위 내로 제한
            new_x = max(x_min, min(x_max, new_x))
            new_y = max(y_min, min(y_max, new_y))
            
            # 이미지 위치 업데이트
            self.image_label.move(int(new_x), int(new_y))
            
            # 뷰포트 포커스 정보 업데이트
            if self.current_image_orientation:
                current_rel_center = self._get_current_view_relative_center()
                self.current_active_rel_center = current_rel_center
                self.current_active_zoom_level = self.zoom_mode
                
                # 방향별 뷰포트 포커스 저장
                self._save_orientation_viewport_focus(
                    self.current_image_orientation, 
                    current_rel_center, 
                    self.zoom_mode
                )
            
            # 미니맵 업데이트
            if self.minimap_visible and self.minimap_widget.isVisible():
                self.update_minimap()

            if self.compare_mode_active:
                self._sync_viewports()
            
            logging.info(f"뷰포트 중앙 이동 완료: {self.zoom_mode} 모드, 위치: ({new_x}, {new_y})")
            return True
            
        except Exception as e:
            logging.error(f"center_viewport 오류: {e}")
            return False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            focused_widget = QApplication.focusWidget()
            if isinstance(focused_widget, (QLineEdit, QSpinBox, QTextBrowser)):
                return super().eventFilter(obj, event)
            if self.is_input_dialog_active:
                return super().eventFilter(obj, event)
            key = event.key()
            modifiers = event.modifiers()

            # (Q/E, 숫자키, Ctrl 단축키, 기능키 등은 변경 없음)
            if key in (Qt.Key_Q, Qt.Key_E):
                if not event.isAutoRepeat() and key not in self.key_press_start_time:
                    self.key_press_start_time[key] = time.time()
                return True
            
            base_number_key = None
            
            # 1. 눌린 키가 숫자키(1-9)인지 직접 확인
            if Qt.Key_1 <= key <= (Qt.Key_1 + self.folder_count - 1):
                base_number_key = key
            # 2. 또는 Shift+숫자 조합으로 나온 특수문자인지 확인
            elif key in self.KEY_MAP_SHIFT_NUMBER:
                mapped_key = self.KEY_MAP_SHIFT_NUMBER[key]
                # 매핑된 키가 현재 설정된 폴더 개수 범위 내에 있는지 추가 확인
                if Qt.Key_1 <= mapped_key <= (Qt.Key_1 + self.folder_count - 1):
                    base_number_key = mapped_key

            # 3. 유효한 숫자 키 입력이 감지된 경우
            if base_number_key is not None:
                if not event.isAutoRepeat():
                    folder_index = base_number_key - Qt.Key_1
                    
                    # 4. Shift 키가 눌렸는지 확인하여 복사/이동 분기
                    if (modifiers & Qt.ShiftModifier) and not (modifiers & Qt.ControlModifier):
                        # Shift + 숫자 = 복사
                        self._trigger_copy_operation(folder_index)
                    elif not (modifiers & Qt.ShiftModifier) and not (modifiers & Qt.ControlModifier):
                        # 숫자만 = 이동 준비 (하이라이트)
                        self.highlight_folder_label(folder_index, True)
                        # 중요: pressed_number_keys에는 매핑된 기본 숫자 키를 저장해야 합니다.
                        self.pressed_number_keys.add(base_number_key)
                        
                return True # 숫자 키 관련 이벤트는 여기서 모두 처리

            is_mac = sys.platform == 'darwin'
            ctrl_modifier = Qt.MetaModifier if is_mac else Qt.ControlModifier
            if modifiers == ctrl_modifier and key == Qt.Key_Z: self.undo_move(); return True
            elif modifiers == ctrl_modifier and key == Qt.Key_Y: self.redo_move(); return True
            elif (modifiers & ctrl_modifier) and (modifiers & Qt.ShiftModifier) and key == Qt.Key_Z: self.redo_move(); return True
            if key == Qt.Key_Return or key == Qt.Key_Enter:
                if self.file_list_dialog is None or not self.file_list_dialog.isVisible():
                    if self.image_files:
                        current_selected_index = -1
                        if self.grid_mode == "Off": current_selected_index = self.current_image_index
                        else:
                            potential_index = self.grid_page_start_index + self.current_grid_index
                            if 0 <= potential_index < len(self.image_files): current_selected_index = potential_index
                        if current_selected_index != -1:
                            self.file_list_dialog = FileListDialog(self.image_files, current_selected_index, self.image_loader, self)
                            self.file_list_dialog.finished.connect(self.on_file_list_dialog_closed)
                            self.file_list_dialog.show()
                else: self.file_list_dialog.activateWindow(); self.file_list_dialog.raise_()
                return True
            if key == Qt.Key_G:
                if self.grid_mode == "Off": self.grid_on_radio.setChecked(True); self._on_grid_mode_toggled(self.grid_on_radio)
                else: self.grid_off_radio.setChecked(True); self._on_grid_mode_toggled(self.grid_off_radio)
                return True
            elif key == Qt.Key_C:
                if self.compare_mode_active: self.grid_off_radio.setChecked(True); self._on_grid_mode_toggled(self.grid_off_radio)
                else: self.compare_radio.setChecked(True); self._on_grid_mode_toggled(self.compare_radio)
                return True
            if key == Qt.Key_F1: self.fit_radio.setChecked(True); self.on_zoom_changed(self.fit_radio); return True
            elif key == Qt.Key_F2:
                if self.zoom_100_radio.isEnabled(): self.zoom_100_radio.setChecked(True); self.on_zoom_changed(self.zoom_100_radio)
                return True
            elif key == Qt.Key_F3:
                if self.zoom_spin_btn.isEnabled(): self.zoom_spin_btn.setChecked(True); self.on_zoom_changed(self.zoom_spin_btn)
                return True
            elif key == Qt.Key_F5: self.refresh_folder_contents(); return True
            elif key == Qt.Key_Delete: self.reset_program_state(); return True
            if key == Qt.Key_Escape:
                if self.file_list_dialog and self.file_list_dialog.isVisible(): self.file_list_dialog.reject(); return True
                if self.zoom_mode != "Fit":
                    self.last_active_zoom_mode = self.zoom_mode
                    self.fit_radio.setChecked(True); self.on_zoom_changed(self.fit_radio)
                    return True
                elif self.grid_mode == "Off" and self.previous_grid_mode and self.previous_grid_mode != "Off":
                    self.grid_on_radio.setChecked(True)
                    idx = self.grid_size_combo.findText(self.previous_grid_mode.replace("x", " x "))
                    if idx != -1: self.grid_size_combo.setCurrentIndex(idx)
                    self._on_grid_mode_toggled(self.grid_on_radio)
                    return True
            if key == Qt.Key_R:
                if (self.grid_mode == "Off" and self.zoom_mode in ["100%", "Spin"] and self.original_pixmap): self.center_viewport(); return True
            if key == Qt.Key_Space:
                if self.grid_mode == "Off":
                    if self.original_pixmap:
                        if self.zoom_mode == "Fit":
                            target_zoom_mode = self.last_active_zoom_mode
                            current_orientation = self.current_image_orientation
                            if current_orientation:
                                saved_rel_center, _ = self._get_orientation_viewport_focus(current_orientation, target_zoom_mode)
                                self.current_active_rel_center = saved_rel_center
                            else: self.current_active_rel_center = QPointF(0.5, 0.5)
                            self.current_active_zoom_level = target_zoom_mode
                            self.zoom_change_trigger = "space_key_to_zoom"
                            self.zoom_mode = target_zoom_mode
                            if target_zoom_mode == "100%": self.zoom_100_radio.setChecked(True)
                            elif target_zoom_mode == "Spin": self.zoom_spin_btn.setChecked(True)
                            self.apply_zoom_to_image()
                            self.toggle_minimap(self.minimap_toggle.isChecked())
                        else:
                            self.last_active_zoom_mode = self.zoom_mode
                            self.zoom_mode = "Fit"
                            self.fit_radio.setChecked(True)
                            self.apply_zoom_to_image()
                    return True
                else:
                    current_selected_grid_index = self.grid_page_start_index + self.current_grid_index
                    if 0 <= current_selected_grid_index < len(self.image_files):
                        self.current_image_index = current_selected_grid_index
                        self.force_refresh = True
                        self.previous_grid_mode = self.grid_mode
                        self.grid_mode = "Off"
                        self.space_pressed = True
                        self.grid_off_radio.setChecked(True)
                        self.update_thumbnail_panel_style()
                        self.update_grid_view()
                        self.update_zoom_radio_buttons_state()
                        self.update_counter_layout()
                        QTimer.singleShot(0, self.display_current_image)
                    return True
            if self.zoom_mode == "Spin" and (key == Qt.Key_Z or key == Qt.Key_X):
                if hasattr(self, 'zoom_spin'):
                    current_zoom = self.zoom_spin.value()
                    if key == Qt.Key_X: new_zoom = min(500, current_zoom + 20)
                    else: new_zoom = max(10, current_zoom - 20)
                    if new_zoom != current_zoom: self.zoom_spin.setValue(new_zoom)
                return True

            # 1. Ctrl + A (전체 선택) - 가장 구체적인 조건이므로 가장 먼저 확인합니다.
            if key == Qt.Key_A and (modifiers & ctrl_modifier):
                if self.grid_mode != "Off" and self.image_files:
                    self.toggle_select_all_in_page()
                return True

            # 2. 뷰포트 패닝 처리 (이전과 동일)
            is_panning_mode = (self.grid_mode == "Off" and self.zoom_mode in ["100%", "Spin"] and self.original_pixmap)
            is_shift_wasd = (modifiers & Qt.ShiftModifier) and key in (Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D)
            is_arrow_keys_for_panning = not (modifiers & Qt.ShiftModifier) and key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right)
            
            if is_panning_mode and (is_shift_wasd or is_arrow_keys_for_panning):
                key_to_add_for_viewport = None
                if key in (Qt.Key_A, Qt.Key_Left): key_to_add_for_viewport = Qt.Key_Left
                elif key in (Qt.Key_D, Qt.Key_Right): key_to_add_for_viewport = Qt.Key_Right
                elif key in (Qt.Key_W, Qt.Key_Up): key_to_add_for_viewport = Qt.Key_Up
                elif key in (Qt.Key_S, Qt.Key_Down): key_to_add_for_viewport = Qt.Key_Down
                
                if key_to_add_for_viewport:
                    if not event.isAutoRepeat():
                        if key_to_add_for_viewport not in self.pressed_keys_for_viewport:
                            self.pressed_keys_for_viewport.add(key_to_add_for_viewport)
                        if not self.viewport_move_timer.isActive():
                            self.viewport_move_timer.start()
                    return True

            # 3. 사진/그리드 탐색 처리 (이전과 동일)
            if self.grid_mode != "Off":
                rows, cols = self._get_grid_dimensions()
                if (modifiers & Qt.ShiftModifier):
                    if key in (Qt.Key_A, Qt.Key_Left): self.navigate_to_adjacent_page(-1); return True
                    elif key in (Qt.Key_D, Qt.Key_Right): self.navigate_to_adjacent_page(1); return True
                else:
                    if key in (Qt.Key_A, Qt.Key_Left): self.navigate_grid(-1); return True
                    elif key in (Qt.Key_D, Qt.Key_Right): self.navigate_grid(1); return True
                    elif key in (Qt.Key_W, Qt.Key_Up): self.navigate_grid(-cols); return True
                    elif key in (Qt.Key_S, Qt.Key_Down): self.navigate_grid(cols); return True
            else: # Grid Off 모드
                is_no_shift_wasd = not (modifiers & Qt.ShiftModifier) and key in (Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D)
                is_fit_arrow_keys = self.zoom_mode == "Fit" and key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right)
                
                if is_no_shift_wasd or is_fit_arrow_keys:
                    if key in (Qt.Key_A, Qt.Key_W, Qt.Key_Left, Qt.Key_Up):
                        self.show_previous_image(); return True
                    elif key in (Qt.Key_D, Qt.Key_S, Qt.Key_Right, Qt.Key_Down):
                        self.show_next_image(); return True

            return False
        elif event.type() == QEvent.KeyRelease:
            key = event.key()
            if self.is_input_dialog_active or event.isAutoRepeat():
                return super().eventFilter(obj, event)
            
            if key in (Qt.Key_Q, Qt.Key_E):
                if key in self.key_press_start_time:
                    press_duration = time.time() - self.key_press_start_time.pop(key)
                    if press_duration > 0.25:
                        direction = 'ccw' if key == Qt.Key_Q else 'cw'
                        self.rotate_image('A', direction)
                return True

            if key in self.pressed_number_keys:
                folder_index = key - Qt.Key_1
                self.highlight_folder_label(folder_index, False)
                self.pressed_number_keys.remove(key)
                if not self.image_processing:
                    self.image_processing = True
                    if self.grid_mode != "Off": self.move_grid_image(folder_index)
                    else:
                        context = "CompareA" if self.compare_mode_active else "Off"
                        self.move_current_image_to_folder(folder_index, context_mode=context)
                    self.image_processing = False
                return True
            
            key_to_remove = None
            # 어떤 키가 눌렸는지에 관계없이, 눌렸던 방향키/WASD에 해당하는 표준 방향키 값을 찾습니다.
            if key in (Qt.Key_A, Qt.Key_Left): key_to_remove = Qt.Key_Left
            elif key in (Qt.Key_D, Qt.Key_Right): key_to_remove = Qt.Key_Right
            elif key in (Qt.Key_W, Qt.Key_Up): key_to_remove = Qt.Key_Up
            elif key in (Qt.Key_S, Qt.Key_Down): key_to_remove = Qt.Key_Down
            
            # Shift 키가 떨어지면 모든 패닝 키를 제거합니다.
            elif key == Qt.Key_Shift:
                self.pressed_keys_for_viewport.clear()
            
            if key_to_remove and key_to_remove in self.pressed_keys_for_viewport:
                self.pressed_keys_for_viewport.remove(key_to_remove)
            
            # 패닝 키가 하나도 남지 않았으면 타이머를 멈추고 상태를 최종 저장합니다.
            if not self.pressed_keys_for_viewport and self.viewport_move_timer.isActive():
                self.viewport_move_timer.stop()
                if self.grid_mode == "Off" and self.zoom_mode in ["100%", "Spin"] and self.original_pixmap:
                    final_rel_center = self._get_current_view_relative_center()
                    self.current_active_rel_center = final_rel_center
                    self.current_active_zoom_level = self.zoom_mode
                    self._save_orientation_viewport_focus(self.current_image_orientation, final_rel_center, self.zoom_mode)
            
            # 이벤트가 처리되었으면 True 반환
            if key_to_remove or key == Qt.Key_Shift:
                return True
            return False
        return super().eventFilter(obj, event)


    def on_file_list_dialog_closed(self, result):
        """FileListDialog가 닫혔을 때 호출되는 슬롯"""
        # finished 시그널은 인자(result)를 받으므로 맞춰줌
        self.file_list_dialog = None # 다이얼로그 참조 제거
        print("File list dialog closed.") # 확인용 로그

    def update_raw_toggle_state(self):
        """RAW 폴더 유효성 및 RAW 전용 모드에 따라 'RAW 이동' 체크박스 상태 업데이트"""
        self.raw_toggle_button.blockSignals(True)
        try:
            if self.is_raw_only_mode:
                # RAW 전용 모드일 때는 항상 체크되고 비활성화되어야 함
                self.raw_toggle_button.setChecked(True)
                self.raw_toggle_button.setEnabled(False)
                self.move_raw_files = True # 내부 상태도 강제로 동기화
            else:
                # JPG 모드일 때
                is_raw_folder_valid = bool(self.raw_folder and Path(self.raw_folder).is_dir())
                self.raw_toggle_button.setEnabled(is_raw_folder_valid)
                if is_raw_folder_valid:
                    # 유효한 RAW 폴더가 연결되면, 저장된 내부 상태를 UI에 반영
                    self.raw_toggle_button.setChecked(self.move_raw_files)
                else:
                    # 유효한 RAW 폴더가 없으면 체크박스는 비활성화되고 체크 해제됨
                    # 이때 내부 상태(self.move_raw_files)는 변경하지 않아야 함
                    self.raw_toggle_button.setChecked(False)
        finally:
            # try...finally 구문을 사용하여 어떤 경우에도 시그널 차단이 해제되도록 보장
            self.raw_toggle_button.blockSignals(False)

    def update_match_raw_button_state(self):
        """ JPG 로드 상태에 따라 RAW 관련 버튼의 텍스트/상태 업데이트 """
        if self.is_raw_only_mode:
            # RAW 전용 모드일 때: 버튼 비활성화
            self.match_raw_button.setText(LanguageManager.translate("RAW 불러오기"))
            self.match_raw_button.setEnabled(False)
            self.load_button.setEnabled(False) # JPG 버튼도 함께 비활성화
        elif self.image_files:
            # JPG 로드됨: "JPG - RAW 연결" 버튼으로 변경
            self.match_raw_button.setText(LanguageManager.translate("JPG - RAW 연결"))
            # RAW 폴더가 이미 로드된 상태인지 확인
            is_raw_loaded = bool(self.raw_folder and Path(self.raw_folder).is_dir())
            # RAW 폴더가 로드된 상태이면 버튼 비활성화, 아니면 활성화
            self.match_raw_button.setEnabled(not is_raw_loaded)
            # JPG가 이미 로드된 상태면 JPG 버튼 비활성화
            self.load_button.setEnabled(False)
        else:
            # JPG 로드 안됨: "RAW 불러오기" 버튼으로 변경
            self.match_raw_button.setText(LanguageManager.translate("RAW 불러오기"))
            self.match_raw_button.setEnabled(True)
            self.load_button.setEnabled(True)  # 둘 다 로드 안됨: JPG 버튼 활성화

    def update_info_folder_label_style(self, label: InfoFolderPathLabel, folder_path: str):
        """InfoFolderPathLabel의 스타일을 경로 유효성에 따라 업데이트합니다."""
        is_valid = bool(folder_path and Path(folder_path).is_dir())
        label.set_style(is_valid=is_valid)


    def update_jpg_folder_ui_state(self):
        is_valid = bool(self.current_folder and Path(self.current_folder).is_dir())
        
        if is_valid:
            self.folder_path_label.setText(self.current_folder)
        else:
            self.folder_path_label.setText(LanguageManager.translate("폴더 경로"))
            
        self.update_info_folder_label_style(self.folder_path_label, self.current_folder)
        
        if hasattr(self, 'jpg_clear_button'):
            self.jpg_clear_button.setEnabled(is_valid)
        if hasattr(self, 'load_button'):
            self.load_button.setEnabled(not is_valid and not self.is_raw_only_mode)

    def update_raw_folder_ui_state(self):
        is_valid = bool(self.raw_folder and Path(self.raw_folder).is_dir())
        
        if is_valid:
            self.raw_folder_path_label.setText(self.raw_folder)
        else:
            self.raw_folder_path_label.setText(LanguageManager.translate("폴더 경로"))
            
        self.update_info_folder_label_style(self.raw_folder_path_label, self.raw_folder)
        
        if hasattr(self, 'raw_clear_button'):
            self.raw_clear_button.setEnabled(is_valid)
        self.update_raw_toggle_state()

    def clear_jpg_folder(self):
        """JPG 폴더 지정 해제 및 관련 상태 초기화"""
        # 확인 대화상자 추가
        reply = self.show_themed_message_box(
            QMessageBox.Question,
            LanguageManager.translate("작업 초기화 확인"),
            LanguageManager.translate("현재 작업을 종료하고 이미지 폴더를 닫으시겠습니까?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            logging.info("JPG 폴더 닫기 작업이 사용자에 의해 취소되었습니다.")
            return # 사용자가 '아니오'를 선택하면 함수 종료
        
        self._reset_workspace()

        self.grid_off_radio.setChecked(True) # 라디오 버튼 상태 동기화
        self._update_view_for_grid_change()

        self.update_all_folder_labels_state()

        # UI 컨트롤 상태 복원
        self.load_button.setEnabled(True)
        self.update_match_raw_button_state()

        if self.session_management_popup and self.session_management_popup.isVisible():
            self.session_management_popup.update_all_button_states()
        
        self.save_state()
        logging.info("JPG 폴더 지정 해제 및 작업 공간 초기화 완료.")


    def clear_raw_folder(self):
        """RAW 폴더 지정 해제 및 관련 상태 초기화 (RAW 전용 모드 처리 추가)"""
        if self.is_raw_only_mode:
            # --- RAW 전용 모드 해제 및 전체 초기화 ---
            # RAW 전용 모드일 때의 확인 대화상자
            reply = self.show_themed_message_box(
                QMessageBox.Question,
                LanguageManager.translate("작업 초기화 확인"),
                LanguageManager.translate("현재 작업을 종료하고 이미지 폴더를 닫으시겠습니까?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                logging.info("RAW 전용 모드 닫기 작업이 사용자에 의해 취소되었습니다.")
                return
            
            logging.info("RAW 전용 모드 해제 및 초기화...")
            self._reset_workspace()

            self.grid_off_radio.setChecked(True)
            self._update_view_for_grid_change()
            
            # RAW 전용 모드 해제 후 추가 UI 상태 조정
            self.load_button.setEnabled(True)
            self.update_match_raw_button_state()
            
            if self.session_management_popup and self.session_management_popup.isVisible():
                self.session_management_popup.update_all_button_states()
        else:
            # JPG 모드일 때의 확인 대화상자
            reply = self.show_themed_message_box(
                QMessageBox.Question,
                LanguageManager.translate("RAW 연결 해제"),
                LanguageManager.translate("현재 JPG 폴더와의 RAW 파일 연결을 해제하시겠습니까?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                logging.info("RAW 연결 해제 작업이 사용자에 의해 취소되었습니다.")
                return

            self.raw_folder = ""
            self.raw_files = {}
            # UI 업데이트
            self.raw_folder_path_label.setText(LanguageManager.translate("폴더 경로"))
            self.update_raw_folder_ui_state() # 레이블 스타일, X 버튼, 토글 상태 업데이트
            self.update_match_raw_button_state() # RAW 버튼 상태 업데이트 ("JPG - RAW 연결"로)

            current_displaying_image_path = self.get_current_image_path()
            if current_displaying_image_path:
                logging.debug(f"clear_raw_folder (else): RAW 연결 해제 후 파일 정보 업데이트 시도 - {current_displaying_image_path}")
                self.update_file_info_display(current_displaying_image_path)
            else:
                # 현재 표시 중인 이미지가 없는 경우 (예: JPG 폴더도 비어있거나 로드 전)
                # 파일 정보 UI를 기본값으로 설정
                self.update_file_info_display(None)

            self.update_all_folder_labels_state()

            if self.session_management_popup and self.session_management_popup.isVisible():
                self.session_management_popup.update_all_button_states()

            self.save_state()
            logging.info("RAW 폴더 지정 해제 완료.")



    def on_language_radio_changed(self, button):
        """언어 라디오 버튼 변경 시 호출되는 함수"""
        if button == self.english_radio:
            LanguageManager.set_language("en")
        elif button == self.korean_radio:
            LanguageManager.set_language("ko")

        if hasattr(self, 'settings_popup') and self.settings_popup and self.settings_popup.isVisible():
            self.update_settings_labels_texts(self.settings_popup)

    def on_date_format_changed(self, index):
        """날짜 형식 변경 시 호출되는 함수"""
        if index < 0:
            return
        format_code = self.date_format_combo.itemData(index)
        DateFormatManager.set_date_format(format_code)

    def update_ui_texts(self):
        """UI의 모든 텍스트를 현재 언어로 업데이트"""
        # --- 메인 윈도우 UI 텍스트 업데이트 ---
        self.load_button.setText(LanguageManager.translate("이미지 불러오기"))
        self.update_match_raw_button_state()
        self.raw_toggle_button.setText(LanguageManager.translate("JPG + RAW 이동"))
        self.minimap_toggle.setText(LanguageManager.translate("미니맵"))
        if hasattr(self, 'image_label_B') and not self.image_B_path:
            self.image_label_B.setText(LanguageManager.translate("비교할 이미지를 썸네일 패널에서 이곳으로 드래그하세요.\n\n* 이곳의 이미지는 우클릭 메뉴를 통해서만 분류 폴더로 이동할 수 있습니다."))
        if hasattr(self, 'filename_toggle_grid'):
            self.filename_toggle_grid.setText(LanguageManager.translate("파일명"))
        if not self.current_folder:
            self.folder_path_label.setText(LanguageManager.translate("폴더 경로"))
        if not self.raw_folder:
            self.raw_folder_path_label.setText(LanguageManager.translate("폴더 경로"))
        self.update_all_folder_labels_state()
        self.update_window_title_with_selection()
        
        if hasattr(self, 'settings_popup') and self.settings_popup:
            self.settings_popup.setWindowTitle(LanguageManager.translate("설정 및 정보"))

        # --- 설정 창 관련 모든 컨트롤의 텍스트 업데이트 ---
        # [변경] 분리된 함수를 호출합니다.
        if hasattr(self, 'settings_popup') and self.settings_popup:
            self.update_settings_labels_texts(self.settings_popup)
        
        # [변경] 후원 섹션 가시성 및 텍스트 업데이트
        if hasattr(self, 'korean_donation_widget') and hasattr(self, 'english_donation_widget'):
            current_language = LanguageManager.get_current_language()
            self.korean_donation_widget.setVisible(current_language == "ko")
            self.english_donation_widget.setVisible(current_language == "en")
            
            # 객체 이름으로 위젯을 찾아 텍스트 업데이트
            if self.settings_popup:
                kakaopay_label = self.settings_popup.findChild(QRLinkLabel, "kakaopay_label")
                if kakaopay_label:
                    kakaopay_label.setText(LanguageManager.translate("카카오페이"))
                
                naverpay_label = self.settings_popup.findChild(QRLinkLabel, "naverpay_label")
                if naverpay_label:
                    naverpay_label.setText(LanguageManager.translate("네이버페이"))
        
        # --- 현재 파일 정보 다시 표시 (날짜 형식 등이 바뀌었을 수 있으므로) ---
        self.update_file_info_display(self.get_current_image_path())

    def update_settings_labels_texts(self, parent_widget):
        """설정 UI의 모든 텍스트를 현재 언어로 업데이트합니다."""
        if not parent_widget:
            return
        # --- 그룹 제목 업데이트 ---
        group_title_keys = {
            "group_title_UI_설정": "UI 설정",
            "group_title_작업_설정": "작업 설정",
            "group_title_도구_및_고급_설정": "도구 및 고급 설정"
        }
        for name, key in group_title_keys.items():
            label = parent_widget.findChild(QLabel, name)
            if label:
                label.setText(f"[ {LanguageManager.translate(key)} ]")
        # --- 개별 설정 항목 라벨 업데이트 ---
        setting_row_keys = {
            "언어_label": "언어",
            "테마_label": "테마",
            "컨트롤_패널_label": "컨트롤 패널",
            "날짜_형식_label": "날짜 형식",
            "불러올_이미지_형식_label": "불러올 이미지 형식",
            "분류_폴더_개수_label": "분류 폴더 개수",
            "뷰포트_이동_속도_ⓘ_label": "뷰포트 이동 속도 ⓘ",
            "마우스_휠_동작_label": "마우스 휠 동작",
            "마우스_휠_민감도_label": "마우스 휠 민감도",
            "마우스_패닝_감도_label": "마우스 패닝 감도",
            "성능_설정_ⓘ_label": "성능 설정 ⓘ",
        }
        for object_name, translation_key in setting_row_keys.items():
            label = parent_widget.findChild(QLabel, object_name)
            if label:
                label.setText(LanguageManager.translate(translation_key))
                if translation_key == "성능 설정 ⓘ":
                    tooltip_key = "프로그램을 처음 실행하면 시스템 사양에 맞춰 자동으로 설정됩니다.\n높은 옵션일수록 더 많은 메모리와 CPU 자원을 사용함으로써 더 많은 사진을 백그라운드에서 미리 로드하여 작업 속도를 높입니다.\n프로그램이 시스템을 느리게 하거나 메모리를 너무 많이 차지하는 경우 낮은 옵션으로 변경해주세요.\n특히 고용량 사진을 다루는 경우 높은 옵션은 시스템에 큰 부하를 줄 수 있습니다."
                    tooltip_text = LanguageManager.translate(tooltip_key)
                    label.setToolTip(tooltip_text)
                elif translation_key == "뷰포트 이동 속도 ⓘ":
                    tooltip_key = "사진 확대 중 Shift + WASD 또는 방향키로 뷰포트(확대 부분)를 이동할 때의 속도입니다."
                    tooltip_text = LanguageManager.translate(tooltip_key)
                    label.setToolTip(tooltip_text)
        # --- 라디오 버튼 텍스트 업데이트 (이전과 동일) ---
        if hasattr(self, 'panel_pos_left_radio'):
            self.panel_pos_left_radio.setText(LanguageManager.translate("좌측"))
        if hasattr(self, 'panel_pos_right_radio'):
            self.panel_pos_right_radio.setText(LanguageManager.translate("우측"))
        if hasattr(self, 'mouse_wheel_photo_radio'):
            self.mouse_wheel_photo_radio.setText(LanguageManager.translate("사진 넘기기"))
        if hasattr(self, 'mouse_wheel_none_radio'):
            self.mouse_wheel_none_radio.setText(LanguageManager.translate("없음"))
        # --- 버튼 텍스트 업데이트 (이전과 동일) ---
        if hasattr(self, 'reset_camera_settings_button'):
            self.reset_camera_settings_button.setText(LanguageManager.translate("RAW 처리 방식 초기화"))
        if hasattr(self, 'session_management_button'):
            self.session_management_button.setText(LanguageManager.translate("세션 관리"))
        if hasattr(self, 'reset_app_settings_button'):
            self.reset_app_settings_button.setText(LanguageManager.translate("프로그램 설정 초기화"))
        if hasattr(self, 'shortcuts_button'):
            self.shortcuts_button.setText(LanguageManager.translate("단축키 확인"))
        # --- 정보 및 후원 섹션 텍스트 업데이트 (이전과 동일) ---
        info_label = parent_widget.findChild(QLabel, "vibeculling_info_label")
        if info_label:
            info_label.setText(self.create_translated_info_text())

    def update_date_formats(self):
        """날짜 형식이 변경되었을 때 UI 업데이트"""
        # 현재 표시 중인 파일 정보 업데이트
        self.update_file_info_display(self.get_current_image_path())

    def get_current_image_path(self):
        """현재 선택된 이미지 경로 반환"""
        if not self.image_files:
            return None
            
        if self.grid_mode == "Off":
            if 0 <= self.current_image_index < len(self.image_files):
                return str(self.image_files[self.current_image_index])
        else:
            # 그리드 모드에서 선택된 이미지
            index = self.grid_page_start_index + self.current_grid_index
            if 0 <= index < len(self.image_files):
                return str(self.image_files[index])
                
        return None

    def _on_panel_position_changed(self, button):
        """컨트롤 패널 위치 라디오 버튼 클릭 시 호출"""
        button_id = self.panel_position_group.id(button) # 클릭된 버튼의 ID 가져오기 (0: 좌측, 1: 우측)
        new_state_on_right = (button_id == 1) # ID가 1이면 오른쪽

        # 현재 상태와 비교하여 변경되었을 때만 처리
        current_state = getattr(self, 'control_panel_on_right', False)
        if new_state_on_right != current_state:
            print(f"패널 위치 변경 감지: {'오른쪽' if new_state_on_right else '왼쪽'}")
            self.control_panel_on_right = new_state_on_right # 상태 업데이트
            self._apply_panel_position() # 레이아웃 즉시 적용
            self.update_counter_layout()
        else:
            print("패널 위치 변경 없음")

    def _apply_panel_position(self):
        """현재 self.control_panel_on_right 상태에 따라 패널 위치 및 크기 적용"""
        logging.info(f"_apply_panel_position 호출됨: 오른쪽 배치 = {self.control_panel_on_right}")

        if not hasattr(self, 'splitter') or not self.splitter:
            logging.warning("Warning: Splitter가 아직 준비되지 않았습니다.")
            return
        if not hasattr(self, 'control_panel') or not hasattr(self, 'image_panel'):
            logging.warning("Warning: 컨트롤 또는 이미지 패널이 아직 준비되지 않았습니다.")
            return

        try:
            self._is_reorganizing_layout = True

            # 스플리터 재구성 (이제 썸네일 패널은 항상 존재)
            self._reorganize_splitter_widgets(self.control_panel_on_right)
            
            # 카운터 레이아웃을 스플리터 재구성 *후*, adjust_layout *전*에 업데이트합니다.
            self.update_counter_layout()

            def finalize_layout_change():
                # adjust_layout을 타이머 콜백 안으로 이동시켜
                # 스플리터 구조가 완전히 적용된 후 크기를 계산하도록 합니다.
                self.adjust_layout()
                self._is_reorganizing_layout = False
                
                if self.grid_mode == "Off":
                    self.apply_zoom_to_image()
                else:
                    self.update_grid_view()
                logging.info("_apply_panel_position 완료 및 뷰 업데이트")

            QTimer.singleShot(0, finalize_layout_change)

        except Exception as e:
            logging.error(f"_apply_panel_position 오류: {e}", exc_info=True)
            self._is_reorganizing_layout = False # 오류 발생 시 플래그 해제

