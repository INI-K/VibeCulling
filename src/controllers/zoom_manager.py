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
                        self.primary_selected_index = global_index
                        self.current_grid_index = index
                        self.update_grid_selection_border()
                    # 이미 선택된 셀을 우클릭한 경우: 기존 선택 유지 (아무것도 하지 않음)
                    
                    # 컨텍스트 메뉴 표시
                    context_menu = self.create_context_menu(event.position().toPoint())
                    if context_menu:
                        context_menu.exec(widget.mapToGlobal(event.position().toPoint()))
                return
            
            # === Fit 모드에서 드래그 앤 드롭 시작 준비 ===
            if (event.button() == Qt.LeftButton and 
                self.zoom_mode == "Fit" and 
                self.image_files and 
                0 <= self.current_image_index < len(self.image_files)):
                
                # 드래그 시작 준비
                widget.drag_start_pos = event.position().toPoint()
                widget.is_potential_drag = True
                logging.debug(f"Grid 셀에서 드래그 시작 준비: index {index}")
            
            # 기존 클릭 처리는 드래그가 시작되지 않으면 mouseReleaseEvent에서 처리
            widget._click_widget = widget
            widget._click_index = index
            widget._click_event = event
            
        except Exception as e:
            logging.error(f"grid_cell_mouse_press_event 오류: {e}")

    def grid_cell_mouse_move_event(self, event, widget, index):
        """Grid 셀 마우스 이동 이벤트 - 드래그 시작 감지"""
        try:
            # === Fit 모드에서 드래그 시작 감지 ===
            if (hasattr(widget, 'is_potential_drag') and 
                widget.is_potential_drag and 
                self.zoom_mode == "Fit" and 
                self.image_files and 
                0 <= self.current_image_index < len(self.image_files)):
                
                current_pos = event.position().toPoint()
                move_distance = (current_pos - widget.drag_start_pos).manhattanLength()
                
                if move_distance > getattr(widget, 'drag_threshold', 10):
                    # 드래그 시작 - 드래그된 셀의 인덱스 전달
                    self.start_image_drag(dragged_grid_index=index)
                    widget.is_potential_drag = False
                    logging.debug(f"Grid 셀에서 드래그 시작됨: index {index}")
                    return
            
        except Exception as e:
            logging.error(f"grid_cell_mouse_move_event 오류: {e}")

    def grid_cell_mouse_release_event(self, event, widget, index):
        """Grid 셀 마우스 릴리스 이벤트 - 드래그 상태 초기화 및 클릭 처리"""
        try:
            # 드래그 상태 초기화
            if hasattr(widget, 'is_potential_drag') and widget.is_potential_drag:
                widget.is_potential_drag = False
                
                # 드래그가 시작되지 않았으면 클릭으로 처리
                if (hasattr(widget, '_click_widget') and 
                    hasattr(widget, '_click_index') and 
                    hasattr(widget, '_click_event')):
                    
                    # 기존 클릭 처리 로직 호출
                    self.on_grid_cell_clicked(widget._click_widget, widget._click_index)
                    
                    # 임시 변수 정리
                    delattr(widget, '_click_widget')
                    delattr(widget, '_click_index')
                    delattr(widget, '_click_event')
                
                logging.debug(f"Grid 셀에서 드래그 시작 준비 상태 해제: index {index}")
            
        except Exception as e:
            logging.error(f"grid_cell_mouse_release_event 오류: {e}")

    def update_grid_view(self):
        """Grid 모드에 따라 이미지 뷰를 동기적으로 재구성합니다. (최종 안정화 버전)"""
        # 레이아웃 변경으로 인한 이벤트 문제를 피하기 위해 QTimer.singleShot을 사용합니다.
        def build_and_display_grid():
            current_view_widget = self.scroll_area.takeWidget()
            
            if self.grid_mode == "Off":
                # (이 부분은 기존과 동일)
                if current_view_widget and current_view_widget is not self.image_container:
                    current_view_widget.deleteLater()
                self.image_label.clear()
                self.image_label.setStyleSheet("background-color: transparent;")
                self.scroll_area.setWidget(self.image_container)
                return

            if current_view_widget and current_view_widget is self.image_container:
                current_view_widget.setParent(None)
            
            self.grid_labels.clear()
            self.grid_layout = None

            rows, cols = self._get_grid_dimensions()
            if rows == 0: return

            self.grid_layout = QGridLayout()
            self.grid_layout.setSpacing(0)
            self.grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_container_widget = QWidget()
            grid_container_widget.setLayout(self.grid_layout)
            grid_container_widget.setStyleSheet("background-color: black;")
            self.scroll_area.setWidget(grid_container_widget)
            self.scroll_area.setWidgetResizable(True)

            num_cells = rows * cols
            start_idx = self.grid_page_start_index
            end_idx = min(start_idx + num_cells, len(self.image_files))
            images_to_display = self.image_files[start_idx:end_idx]

            if self.current_grid_index >= len(images_to_display) and len(images_to_display) > 0:
                 self.current_grid_index = len(images_to_display) - 1
            elif len(images_to_display) == 0:
                 self.current_grid_index = 0

            for i in range(num_cells):
                row, col = divmod(i, cols)
                cell_widget = GridCellWidget(parent=grid_container_widget)
                from functools import partial
                cell_widget.mousePressEvent = partial(self.grid_cell_mouse_press_event, widget=cell_widget, index=i)
                cell_widget.mouseMoveEvent = partial(self.grid_cell_mouse_move_event, widget=cell_widget, index=i)
                cell_widget.mouseReleaseEvent = partial(self.grid_cell_mouse_release_event, widget=cell_widget, index=i)
                cell_widget.mouseDoubleClickEvent = partial(self.on_grid_cell_double_clicked, clicked_widget=cell_widget, clicked_index=i)
                
                if i < len(images_to_display):
                    current_image_path_obj = images_to_display[i]
                    current_image_path = str(current_image_path_obj)
                    cell_widget.setProperty("image_path", current_image_path)
                    cell_widget.setPixmap(self.placeholder_pixmap)
                
                self.grid_layout.addWidget(cell_widget, row, col)
                self.grid_labels.append(cell_widget)

            # 이 함수는 다중 선택 상태를 초기화하지 않으므로, Undo 시 복원된 상태가 유지됩니다.
            self.update_grid_selection_border()
            self.update_window_title_with_selection()
            
            self.image_loader.preload_page(self.image_files, self.grid_page_start_index, num_cells, strategy_override="preview")
            
            # resize_grid_images도 타이머 콜백 안에서 호출되도록 이동
            self.resize_grid_images()

            selected_image_list_index_gw = self.grid_page_start_index + self.current_grid_index
            if 0 <= selected_image_list_index_gw < len(self.image_files):
                self.update_file_info_display(str(self.image_files[selected_image_list_index_gw]))
            else:
                self.update_file_info_display(None)
            
            self.update_counters()
            if self.grid_mode != "Off" and self.image_files:
                self.state_save_timer.start()

        self.image_loader.cancel_loading()
        if hasattr(self, 'loading_indicator_timer') and self.loading_indicator_timer.isActive():
            self.loading_indicator_timer.stop()
        
        # QTimer.singleShot으로 그리드 빌드 및 표시 로직을 감싸서 실행합니다.
        QTimer.singleShot(0, build_and_display_grid)


    def on_filename_toggle_changed(self, checked):
        """그리드 파일명 표시 토글 상태 변경 시 호출"""
        self.show_grid_filenames = checked
        logging.debug(f"Grid Filename Toggle: {'On' if checked else 'Off'}")

        # Grid 모드이고, 그리드 라벨(이제 GridCellWidget)들이 존재할 때만 업데이트
        if self.grid_mode != "Off" and self.grid_labels:
            for cell_widget in self.grid_labels:
                # 1. 각 GridCellWidget에 파일명 표시 상태를 설정합니다.
                cell_widget.setShowFilename(checked)
                
                # 2. (중요) 파일명 텍스트를 다시 설정합니다.
                #    show_grid_filenames 상태가 변경되었으므로,
                #    표시될 텍스트 내용 자체가 바뀔 수 있습니다 (보이거나 안 보이거나).
                #    이 로직은 resize_grid_images나 update_grid_view에서 가져올 수 있습니다.
                image_path = cell_widget.property("image_path")
                filename_text = ""
                if image_path and checked: # checked (self.show_grid_filenames) 상태를 사용
                    filename = Path(image_path).name
                    # 파일명 축약 로직 (GridCellWidget의 paintEvent에서 하는 것이 더 정확할 수 있으나, 여기서도 처리)
                    # font_metrics를 여기서 가져오기 어려우므로, 간단한 길이 기반 축약 사용
                    if len(filename) > 20: # 예시 길이
                        filename = filename[:7] + "..." + filename[-10:]
                    filename_text = filename
                cell_widget.setText(filename_text) # 파일명 텍스트 업데이트

                # 3. 각 GridCellWidget의 update()를 호출하여 즉시 다시 그리도록 합니다.
                #    setShowFilename 내부에서 update()를 호출했다면 이 줄은 필요 없을 수 있지만,
                #    명시적으로 호출하여 확실하게 합니다.
                #    (GridCellWidget의 setShowFilename, setText 메서드에서 이미 update()를 호출한다면 중복될 수 있으니 확인 필요)
                cell_widget.update() # paintEvent를 다시 호출하게 함
        elif self.compare_mode_active:
            self.update_compare_filenames()

        # Grid Off 모드에서는 이 설정이 현재 뷰에 직접적인 영향을 주지 않으므로
        # 별도의 즉각적인 뷰 업데이트는 필요하지 않습니다.
        # (다음에 Grid On으로 전환될 때 self.show_grid_filenames 상태가 반영됩니다.)

    def on_image_loaded(self, cell_index, pixmap, img_path):
        """비동기 이미지 로딩 완료 시 호출되는 슬롯"""
        if self.grid_mode == "Off" or not self.grid_labels:
            return
            
        if 0 <= cell_index < len(self.grid_labels):
            cell_widget = self.grid_labels[cell_index] # 이제 GridCellWidget
            # GridCellWidget의 경로와 일치하는지 확인
            if cell_widget.property("image_path") == img_path:
                cell_widget.setProperty("original_pixmap_ref", pixmap) # 원본 참조 저장

                pixmap_to_display = pixmap
                angle = self.image_rotations.get(img_path, 0)
                if angle != 0:
                    transform = QTransform().rotate(angle)
                    pixmap_to_display = pixmap.transformed(transform, Qt.SmoothTransformation)
                
                cell_widget.setPixmap(pixmap_to_display) # 회전된 픽스맵을 셀에 설정
                cell_widget.setProperty("loaded", True)

                # 파일명도 여기서 다시 설정해줄 수 있음 (선택적)
                if self.show_grid_filenames:
                    filename = Path(img_path).name
                    if len(filename) > 20:
                        filename = filename[:7] + "..." + filename[-10:]
                    cell_widget.setText(filename)
                cell_widget.setShowFilename(self.show_grid_filenames) # 파일명 표시 상태 업데이트


    def resize_grid_images(self):
        """그리드 셀 크기에 맞춰 이미지 리사이징 (고품질) 및 파일명 업데이트"""
        if not self.grid_labels or self.grid_mode == "Off":
            return

        for cell_widget in self.grid_labels: # 이제 GridCellWidget
            image_path = cell_widget.property("image_path")
            original_pixmap_ref = cell_widget.property("original_pixmap_ref") # 저장된 원본 참조 가져오기

            if image_path and original_pixmap_ref and isinstance(original_pixmap_ref, QPixmap) and not original_pixmap_ref.isNull():
                # GridCellWidget의 setPixmap은 내부적으로 update()를 호출하므로,
                # 여기서 setPixmap을 다시 호출하면 paintEvent가 실행되어 스케일링된 이미지가 그려짐.
                # paintEvent에서 rect.size()를 사용하므로 별도의 스케일링 호출은 불필요.
                # cell_widget.setPixmap(original_pixmap_ref) # 이렇게만 해도 paintEvent에서 처리
                cell_widget.update() # 강제 리페인트 요청으로도 충분할 수 있음
            elif image_path:
                # 플레이스홀더가 이미 설정되어 있거나, 다시 설정
                # cell_widget.setPixmap(self.placeholder_pixmap)
                cell_widget.update()
            else:
                # cell_widget.setPixmap(QPixmap())
                cell_widget.update()

            # 파일명 업데이트 (필요시) - GridCellWidget의 paintEvent에서 처리하므로 여기서 직접 할 필요는 없을 수도 있음
            if self.show_grid_filenames and image_path:
                filename = Path(image_path).name
                # 파일명 축약은 GridCellWidget.paintEvent 내에서 하는 것이 더 정확함
                # (현재 위젯 크기를 알 수 있으므로)
                # 여기서는 setShowFilename 상태만 전달
                if len(filename) > 20:
                    filename = filename[:7] + "..." + filename[-10:]
                cell_widget.setText(filename) # 텍스트 설정
            else:
                cell_widget.setText("")
            cell_widget.setShowFilename(self.show_grid_filenames) # 상태 전달
            # cell_widget.update() # setShowFilename 후에도 업데이트

        self.update_grid_selection_border() # 테두리 업데이트는 별도

    def update_grid_selection_border(self):
        """선택된 그리드 셀들의 테두리 업데이트 (다중 선택 지원)"""
        if not self.grid_labels or self.grid_mode == "Off":
            return

        for i, cell_widget in enumerate(self.grid_labels): # 이제 GridCellWidget
            if i in self.selected_grid_indices:
                cell_widget.setSelected(True)
            else:
                cell_widget.setSelected(False)

    def get_primary_grid_cell_index(self):
        """primary 선택의 페이지 내 인덱스를 반환 (기존 current_grid_index 호환성용)"""
        if self.primary_selected_index != -1:
            return self.primary_selected_index - self.grid_page_start_index
        return 0

    def clear_grid_selection(self, preserve_current_index=False):
        """그리드 선택 상태 초기화"""
        self.selected_grid_indices.clear()
        self.primary_selected_index = -1
        
        # preserve_current_index가 True이면 현재 인덱스 유지
        if not preserve_current_index:
            self.current_grid_index = 0
        
        # 현재 위치를 단일 선택으로 설정 (빈 폴더가 아닌 경우)
        if (self.grid_mode != "Off" and self.image_files and 
            0 <= self.grid_page_start_index + self.current_grid_index < len(self.image_files)):
            self.selected_grid_indices.add(self.current_grid_index)
            self.primary_selected_index = self.grid_page_start_index + self.current_grid_index
        
        self.update_grid_selection_border()
        self.update_window_title_with_selection()

    def toggle_select_all_in_page(self):
        """현재 페이지의 모든 이미지 선택/해제 토글"""
        if self.grid_mode == "Off" or not self.image_files:
            return
        
        rows, cols = self._get_grid_dimensions()
        if rows == 0: return

        num_cells = rows * cols
        
        # 현재 페이지에 실제로 있는 이미지 수 계산
        current_page_image_count = min(num_cells, len(self.image_files) - self.grid_page_start_index)
        
        if current_page_image_count <= 0:
            return
        
        # 현재 페이지의 모든 셀이 선택되어 있는지 확인
        all_selected = True
        for i in range(current_page_image_count):
            if i not in self.selected_grid_indices:
                all_selected = False
                break
        
        if all_selected:
            # 모두 선택되어 있으면 모두 해제
            self.selected_grid_indices.clear()
            self.primary_selected_index = -1
            logging.info("전체 선택 해제")
        else:
            # 일부만 선택되어 있거나 선택이 없으면 모두 선택
            self.selected_grid_indices.clear()
            for i in range(current_page_image_count):
                self.selected_grid_indices.add(i)
            
            # 첫 번째 이미지를 primary로 설정
            self.primary_selected_index = self.grid_page_start_index
            logging.info(f"전체 선택: {current_page_image_count}개 이미지")
        
        # UI 업데이트
        self.update_grid_selection_border()
        self.update_window_title_with_selection()
        
        # 파일 정보 업데이트
        if self.primary_selected_index != -1 and 0 <= self.primary_selected_index < len(self.image_files):
            selected_image_path = str(self.image_files[self.primary_selected_index])
            self.update_file_info_display(selected_image_path)
        else:
            self.update_file_info_display(None)

    def update_window_title_with_selection(self):
        """그리드 모드에서 창 제목 업데이트 (다중/단일 선택 모두 지원)"""
        if self.grid_mode == "Off":
             # Grid Off 모드에서는 display_current_image에서 처리
             return

        total_images = len(self.image_files)
        
        # 다중 선택 상태 확인
        if hasattr(self, 'selected_grid_indices') and self.selected_grid_indices:
            selected_count = len(self.selected_grid_indices)
            if selected_count > 1:
                # 다중 선택: 개수 표시
                if not hasattr(self, 'original_title'):
                    self.original_title = "VibeCulling"

                # 포맷팅이 가능한 번역 키 사용
                title_key = "{count}개 선택됨"
                translated_format = LanguageManager.translate(title_key)
                
                # 번역된 문자열에 실제 개수를 포맷팅
                selection_text = translated_format.format(count=selected_count)
                
                title = f"{self.original_title} - {selection_text}"
            else:
                # 단일 선택: 파일명 표시
                if self.primary_selected_index != -1 and 0 <= self.primary_selected_index < total_images:
                    selected_filename = self.image_files[self.primary_selected_index].name
                    title = f"VibeCulling - {selected_filename}"
                else:
                    title = "VibeCulling"
        else:
            # 기존 단일 선택 방식 (호환성)
            selected_image_list_index = self.grid_page_start_index + self.current_grid_index
            if 0 <= selected_image_list_index < total_images:
                selected_filename = self.image_files[selected_image_list_index].name
                title = f"VibeCulling - {selected_filename}"
            else:
                title = "VibeCulling"

        self.setWindowTitle(title)


    def navigate_grid(self, delta):
        """Grid 셀 간 이동 및 페이지 전환 처리 (다중 선택 시 단일 선택으로 변경)"""
        if not self.image_files or self.grid_mode == "Off":
            return

        total_images = len(self.image_files)
        if total_images <= 0: return # 이미지가 없으면 중단

        rows, cols = self._get_grid_dimensions()
        if rows == 0: return
        num_cells = rows * cols

        # 현재 페이지의 셀 개수 계산 (마지막 페이지는 다를 수 있음)
        current_page_first_image_index = self.grid_page_start_index
        current_page_last_possible_image_index = min(current_page_first_image_index + num_cells - 1, total_images - 1)
        current_page_cell_count = current_page_last_possible_image_index - current_page_first_image_index + 1

        # 현재 선택된 셀의 전체 목록에서의 인덱스
        current_global_index = self.grid_page_start_index + self.current_grid_index

        page_changed = False
        new_grid_index = self.current_grid_index # 페이지 내 이동 기본값

        # 1. 좌/우 이동 처리 (Left/A 또는 Right/D)
        if delta == -1: # 왼쪽
            if current_global_index == 0:
                self.grid_page_start_index = ((total_images - 1) // num_cells) * num_cells
                self.current_grid_index = (total_images - 1) % num_cells
                page_changed = True
                logging.debug("Navigating grid: Wrap around to last image") # 디버깅 로그
            elif self.current_grid_index == 0 and self.grid_page_start_index > 0: # 페이지 첫 셀에서 왼쪽: 이전 페이지 마지막 셀
                self.grid_page_start_index = max(0, self.grid_page_start_index - num_cells)
                # 이전 페이지의 셀 개수 계산
                prev_page_cell_count = min(num_cells, total_images - self.grid_page_start_index)
                self.current_grid_index = prev_page_cell_count - 1 # 이전 페이지의 마지막 유효 셀로 이동
                page_changed = True
                logging.debug(f"Navigating grid: To previous page, index {self.current_grid_index}") # 디버깅 로그
            elif self.current_grid_index > 0: # 페이지 내 왼쪽 이동
                new_grid_index = self.current_grid_index - 1
                logging.debug(f"Navigating grid: Move left within page to {new_grid_index}") # 디버깅 로그

        elif delta == 1: # 오른쪽
            if current_global_index == total_images - 1:
                self.grid_page_start_index = 0
                self.current_grid_index = 0
                page_changed = True
                logging.debug("Navigating grid: Wrap around to first image") # 디버깅 로그
            elif self.current_grid_index == current_page_cell_count - 1 and self.grid_page_start_index + num_cells < total_images: # 페이지 마지막 셀에서 오른쪽: 다음 페이지 첫 셀
                self.grid_page_start_index += num_cells
                self.current_grid_index = 0
                page_changed = True
                logging.debug("Navigating grid: To next page, index 0") # 디버깅 로그
            elif self.current_grid_index < current_page_cell_count - 1: # 페이지 내 오른쪽 이동
                new_grid_index = self.current_grid_index + 1
                logging.debug(f"Navigating grid: Move right within page to {new_grid_index}") # 디버깅 로그

        # 2. 상/하 이동 처리 (Up/W 또는 Down/S) - 페이지 이동 없음
        elif delta == -cols: # 위
            if self.current_grid_index >= cols: # 첫 줄이 아니면 위로 이동
                new_grid_index = self.current_grid_index - cols
                logging.debug(f"Navigating grid: Move up within page to {new_grid_index}") # 디버깅 로그
            # 첫 줄이면 이동 안 함

        elif delta == cols: # 아래
            potential_new_index = self.current_grid_index + cols
            # 이동하려는 위치가 현재 페이지의 유효한 셀 범위 내에 있는지 확인
            if potential_new_index < current_page_cell_count:
                new_grid_index = potential_new_index
                logging.debug(f"Navigating grid: Move down within page to {new_grid_index}") # 디버깅 로그
            # 마지막 줄이거나 다음 줄에 해당하는 셀이 현재 페이지에 없으면 이동 안 함

        # 3. 페이지 내 이동 결과 적용 (페이지 변경이나 순환이 아닐 경우)
        if not page_changed and new_grid_index != self.current_grid_index:
            self.current_grid_index = new_grid_index
            
            # 키보드 네비게이션 시 다중 선택을 단일 선택으로 변경
            if hasattr(self, 'selected_grid_indices'):
                self.selected_grid_indices.clear()
                self.selected_grid_indices.add(new_grid_index)
                self.primary_selected_index = self.grid_page_start_index + new_grid_index
                logging.debug(f"키보드 네비게이션: 단일 선택으로 변경 - index {new_grid_index}")
            
            # 페이지 내 이동 시 UI 업데이트
            self.update_grid_selection_border()
            self.update_window_title_with_selection()
            image_list_index_ng = self.grid_page_start_index + self.current_grid_index
            # 페이지 내 이동 시에도 전역 인덱스 유효성 검사 (안전 장치)
            if 0 <= image_list_index_ng < total_images:
                self.update_file_info_display(str(self.image_files[image_list_index_ng]))
            else:
                # 이 경우는 발생하면 안되지만, 방어적으로 처리
                self.update_file_info_display(None)
                logging.warning(f"Warning: Invalid global index {image_list_index_ng} after intra-page navigation.")
            self.update_counters()

        # 4. 페이지 변경 또는 순환 발생 시 UI 업데이트
        elif page_changed:
            # 페이지 변경 시에도 다중 선택을 단일 선택으로 변경
            if hasattr(self, 'selected_grid_indices'):
                self.selected_grid_indices.clear()
                self.selected_grid_indices.add(self.current_grid_index)
                self.primary_selected_index = self.grid_page_start_index + self.current_grid_index
                logging.debug(f"페이지 변경: 단일 선택으로 변경 - index {self.current_grid_index}")
            
            # 페이지 변경/순환 시에는 update_grid_view가 모든 UI 업데이트를 처리
            self.update_grid_view()
            logging.debug(f"Navigating grid: Page changed to start index {self.grid_page_start_index}, grid index {self.current_grid_index}") # 디버깅 로그

    def move_grid_image(self, folder_index):
        """Grid 모드에서 선택된 이미지(들)를 지정된 폴더로 이동 (다중 선택 지원)"""
        if self.grid_mode == "Off" or not self.grid_labels:
            return
        
        if hasattr(self, 'selected_grid_indices') and self.selected_grid_indices:
            selected_global_indices = []
            for grid_index in self.selected_grid_indices:
                global_index = self.grid_page_start_index + grid_index
                if 0 <= global_index < len(self.image_files):
                    selected_global_indices.append(global_index)
            if not selected_global_indices:
                logging.warning("선택된 이미지가 없습니다.")
                return
            logging.info(f"다중 이미지 이동 시작: {len(selected_global_indices)}개 파일")
        else:
            image_list_index = self.grid_page_start_index + self.current_grid_index
            if not (0 <= image_list_index < len(self.image_files)):
                logging.warning("선택된 셀에 이동할 이미지가 없습니다.")
                return
            selected_global_indices = [image_list_index]
            logging.info(f"단일 이미지 이동: index {image_list_index}")
            
        target_folder = self.target_folders[folder_index]
        if not target_folder or not os.path.isdir(target_folder):
            return
            
        selected_global_indices.sort(reverse=True)
        
        show_progress = len(selected_global_indices) >= 2
        progress_dialog = None
        if show_progress:
            progress_dialog = QProgressDialog(
                LanguageManager.translate("이미지 이동 중..."),
                "", 
                0, len(selected_global_indices), self
            )
            progress_dialog.setCancelButton(None)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.show()
            QApplication.processEvents()

        successful_moves = []
        failed_moves = []
        move_history_entries = []
        user_canceled = False
        try:
            for idx, global_index in enumerate(selected_global_indices):
                if show_progress and progress_dialog:
                    progress_dialog.setValue(idx)
                    if progress_dialog.wasCanceled():
                        logging.info("사용자가 이동 작업을 취소했습니다.")
                        user_canceled = True
                        break
                    QApplication.processEvents()
                
                if global_index >= len(self.image_files):
                    continue
                
                current_image_path = self.image_files[global_index]
                moved_jpg_path = None
                moved_raw_path = None
                raw_path_before_move = None
                
                try:
                    moved_jpg_path = self.move_file(current_image_path, target_folder)
                    if moved_jpg_path is None:
                        failed_moves.append(current_image_path.name)
                        logging.error(f"파일 이동 실패: {current_image_path.name}")
                        continue
                    
                    raw_moved_successfully = True
                    if self.move_raw_files:
                        base_name = current_image_path.stem
                        if base_name in self.raw_files:
                            raw_path_before_move = self.raw_files[base_name]
                            moved_raw_path = self.move_file(raw_path_before_move, target_folder)
                            if moved_raw_path is None:
                                logging.warning(f"RAW 파일 이동 실패: {raw_path_before_move.name}")
                                raw_moved_successfully = False
                            else:
                                del self.raw_files[base_name]
                    
                    self.image_files.pop(global_index)
                    successful_moves.append(moved_jpg_path.name)
                    
                    if moved_jpg_path:
                        history_entry = {
                            "jpg_source": str(current_image_path),
                            "jpg_target": str(moved_jpg_path),
                            "raw_source": str(raw_path_before_move) if raw_path_before_move else None,
                            "raw_target": str(moved_raw_path) if moved_raw_path and raw_moved_successfully else None,
                            "index_before_move": global_index,
                            "mode": self.grid_mode
                        }
                        move_history_entries.append(history_entry)
                except Exception as e:
                    failed_moves.append(current_image_path.name)
                    logging.error(f"이미지 이동 중 오류 발생 ({current_image_path.name}): {str(e)}")
            
            if show_progress and progress_dialog:
                progress_dialog.close()
                progress_dialog = None

            if user_canceled:
                if successful_moves:
                    msg_template = LanguageManager.translate("작업 취소됨.\n성공: {success_count}개, 실패: {fail_count}개")
                    message = msg_template.format(success_count=len(successful_moves), fail_count=len(failed_moves))
                    self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("경고"), message)
            elif successful_moves and failed_moves:
                msg_template = LanguageManager.translate("성공: {success_count}개\n실패: {fail_count}개")
                message = msg_template.format(success_count=len(successful_moves), fail_count=len(failed_moves))
                self.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("경고"), message)
            elif failed_moves:
                msg_template = LanguageManager.translate("모든 파일 이동 실패: {fail_count}개")
                message = msg_template.format(fail_count=len(failed_moves))
                self.show_themed_message_box(QMessageBox.Critical, LanguageManager.translate("에러"), message)
            
            rows, cols = self._get_grid_dimensions()
            num_cells = rows * cols
            
            if hasattr(self, 'selected_grid_indices'):
                self.clear_grid_selection(preserve_current_index=True)
                
            current_page_image_count = min(num_cells, len(self.image_files) - self.grid_page_start_index)
            if self.current_grid_index >= current_page_image_count and current_page_image_count > 0:
                self.current_grid_index = current_page_image_count - 1
            if current_page_image_count == 0 and len(self.image_files) > 0:
                self.grid_page_start_index = max(0, self.grid_page_start_index - num_cells)
                new_page_image_count = min(num_cells, len(self.image_files) - self.grid_page_start_index)
                self.current_grid_index = max(0, new_page_image_count - 1)
            
            self.update_grid_view()
            
            if not self.image_files:
                self.grid_mode = "Off"
                self.grid_off_radio.setChecked(True)
                self.update_grid_view()
                if self.minimap_visible:
                    self.minimap_widget.hide()
                    self.minimap_visible = False
                if self.session_management_popup and self.session_management_popup.isVisible():
                    self.session_management_popup.update_all_button_states()
                self.show_themed_message_box(QMessageBox.Information, LanguageManager.translate("완료"), LanguageManager.translate("모든 이미지가 분류되었습니다."))
            
            self.update_counters()
        except Exception as e:
            if show_progress and progress_dialog:
                progress_dialog.close()
            self.show_themed_message_box(QMessageBox.Critical, LanguageManager.translate("에러"), f"{LanguageManager.translate('파일 이동 중 오류 발생')}: {str(e)}")
        
        if move_history_entries:
            if len(move_history_entries) == 1:
                self.add_move_history(move_history_entries[0])
                logging.info(f"단일 이동 히스토리 추가: 1개 항목")
            else:
                self.add_batch_move_history(move_history_entries)
                logging.info(f"배치 이동 히스토리 추가: {len(move_history_entries)}개 항목")


    def on_grid_cell_double_clicked(self, event, clicked_widget, clicked_index): # 파라미터 이름을 clicked_widget으로
        """그리드 셀 더블클릭 시 Grid Off 모드로 전환"""
        if self.grid_mode == "Off" or not self.grid_labels:
            logging.debug("Grid Off 모드이거나 그리드 레이블이 없어 더블클릭 무시")
            return
        try:
            # 현재 페이지에 실제로 표시될 수 있는 이미지의 총 개수
            current_page_image_count = min(len(self.grid_labels), len(self.image_files) - self.grid_page_start_index)

            # 클릭된 인덱스가 유효한 범위 내에 있고, 해당 인덱스에 해당하는 이미지가 실제로 존재하는지 확인
            if 0 <= clicked_index < current_page_image_count:
                image_path_property = clicked_widget.property("image_path")
                if image_path_property: # 이미지 경로가 있다면 유효한 셀로 간주
                    # 1. 상태 변수 설정
                    self.current_image_index = self.grid_page_start_index + clicked_index
                    self.force_refresh = True
                    self.previous_grid_mode = self.grid_mode
                    self.grid_mode = "Off"
                    
                    # 2. UI 컨트롤 및 구조 변경
                    self.grid_off_radio.setChecked(True)
                    self.update_thumbnail_panel_style()
                    self.update_grid_view()
                    self.update_zoom_radio_buttons_state()
                    self.update_counter_layout()

                    # 3. 이미지 표시 예약
                    QTimer.singleShot(0, self.display_current_image)
                    self.update_thumbnail_current_index()
                else:
                    logging.debug(f"빈 셀 더블클릭됨 (이미지 경로 없음): index {clicked_index}")
            else:
                 logging.debug(f"유효하지 않은 셀 더블클릭됨 (인덱스 범위 초과): index {clicked_index}, page_img_count {current_page_image_count}")
        except Exception as e:
            logging.error(f"그리드 셀 더블클릭 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc() # 상세 오류 로깅
        finally:
            pass


    def image_mouse_double_click_event(self, event: QMouseEvent):
        if self.grid_mode == "Off" and self.original_pixmap:
            current_image_path_str = str(self.image_files[self.current_image_index]) if 0 <= self.current_image_index < len(self.image_files) else None
            current_orientation = self.current_image_orientation
            if self.zoom_mode == "Fit":
                self.double_click_pos = event.position().toPoint()
                scaled_fit_pixmap = self.high_quality_resize_to_fit(self.original_pixmap, self.scroll_area)
                view_width = self.scroll_area.width()
                view_height = self.scroll_area.height()
                fit_img_width = scaled_fit_pixmap.width()
                fit_img_height = scaled_fit_pixmap.height()
                fit_img_rect_in_view = QRect(
                    (view_width - fit_img_width) // 2, (view_height - fit_img_height) // 2,
                    fit_img_width, fit_img_height
                )
                click_x_vp = self.double_click_pos.x()
                click_y_vp = self.double_click_pos.y()
                if fit_img_rect_in_view.contains(int(click_x_vp), int(click_y_vp)):
                    target_zoom_mode = self.last_active_zoom_mode
                    logging.debug(f"더블클릭: Fit -> {target_zoom_mode} 요청")
                    current_orientation = self.current_image_orientation
                    if current_orientation:
                        saved_rel_center, _ = self._get_orientation_viewport_focus(current_orientation, target_zoom_mode)
                        self.current_active_rel_center = saved_rel_center
                    else:
                        self.current_active_rel_center = QPointF(0.5, 0.5)
                    self.current_active_zoom_level = target_zoom_mode
                    self.zoom_change_trigger = "double_click"
                    self.zoom_mode = target_zoom_mode
                    if target_zoom_mode == "100%":
                        self.zoom_100_radio.setChecked(True)
                    elif target_zoom_mode == "Spin":
                        self.zoom_spin_btn.setChecked(True)
                    self.apply_zoom_to_image() 
                    self.toggle_minimap(self.minimap_toggle.isChecked())
                else:
                    logging.debug("더블클릭 위치가 이미지 바깥입니다 (Fit 모드).")
            elif self.zoom_mode in ["100%", "Spin"]:
                logging.debug(f"더블클릭: {self.zoom_mode} -> Fit 요청")
                current_orientation = self.current_image_orientation
                if current_orientation:
                    current_rel_center = self._get_current_view_relative_center()
                    logging.debug(f"더블클릭 뷰포트 위치 저장: {current_orientation} -> {current_rel_center}")
                    self.current_active_rel_center = current_rel_center
                    self.current_active_zoom_level = self.zoom_mode
                    self._save_orientation_viewport_focus(
                        current_orientation,
                        current_rel_center,
                        self.zoom_mode
                    )
                self.last_active_zoom_mode = self.zoom_mode
                logging.debug(f"Last active zoom mode updated to: {self.last_active_zoom_mode}")
                self.zoom_mode = "Fit"
                self.current_active_rel_center = QPointF(0.5, 0.5)
                self.current_active_zoom_level = "Fit"
                self.fit_radio.setChecked(True)
                self.apply_zoom_to_image()


    def reset_program_state(self):
        """프로그램 상태를 초기화 (Delete 키)"""
        reply = self.show_themed_message_box(QMessageBox.Question, 
                                    LanguageManager.translate("프로그램 초기화"),
                                    LanguageManager.translate("로드된 파일과 현재 작업 상태를 초기화하시겠습니까?"),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.target_folders = [""] * self.folder_count
            # 핵심 초기화 로직을 헬퍼 메서드로 이동
            self._reset_workspace()

            self.grid_mode = "Off" # grid_mode를 명시적으로 Off로 설정
            self.grid_off_radio.setChecked(True)
            self._update_view_for_grid_change() # 뷰를 강제로 업데이트
            
            # 추가적으로 UI 컨트롤 상태를 기본값으로 설정
            self.zoom_mode = "Fit"
            self.fit_radio.setChecked(True)
            self.zoom_spin_value = 2.0
            if hasattr(self, 'zoom_spin'):
                self.zoom_spin.setValue(int(self.zoom_spin_value * 100))
            
            self.grid_mode = "Off"
            self.grid_off_radio.setChecked(True)

            self.update_zoom_radio_buttons_state()
            self.update_counter_layout()
            self.toggle_minimap(self.minimap_toggle.isChecked())

            self.save_state() 
            if self.session_management_popup and self.session_management_popup.isVisible():
                self.session_management_popup.update_all_button_states()
            logging.info("프로그램 상태 초기화 완료 (카메라별 RAW 설정은 유지됨).")
        else:
            logging.info("프로그램 초기화 취소됨")

    def _reset_workspace(self):
        """로드된 파일과 현재 작업 상태를 초기화하는 핵심 로직."""
        logging.info("작업 공간 초기화 시작...")
        self.setWindowTitle("VibeCulling") # 제목표시줄 초기화

        # 대기 중인 모든 복사 작업을 취소합니다.
        if hasattr(self, 'copy_queue'):
            logging.debug("  -> 대기 중인 복사 작업 큐를 비웁니다...")
            while not self.copy_queue.empty():
                try:
                    # 큐에서 항목을 꺼내 버립니다.
                    self.copy_queue.get_nowait()
                except queue.Empty:
                    # 다른 스레드와의 경쟁 조건으로 인해 큐가 비었을 경우를 대비
                    break

        # 0. 모든 백그라운드 작업을 가장 먼저, 확실하게 중단시킵니다.
        if hasattr(self, 'resource_manager'):
            self.resource_manager.cancel_all_tasks()

        # 1. 백그라운드 작업 취소
        self.resource_manager.cancel_all_tasks()
        for future in self.image_loader.active_futures:
            future.cancel()
        self.image_loader.active_futures.clear()
        for future in self.active_thumbnail_futures:
            future.cancel()
        self.active_thumbnail_futures.clear()
        # 2. Undo/Redo 히스토리 초기화
        self.move_history = []
        self.history_pointer = -1
        self.image_rotations.clear()
        # 3. 상태 변수 초기화 (이미지 목록을 먼저 비웁니다)
        self.image_files = [] # UI 업데이트 전에 데이터부터 비웁니다.
        self.current_folder = ""
        self.raw_folder = ""
        self.raw_files = {}
        self.current_image_index = -1
        self.is_raw_only_mode = False
        self.compare_mode_active = False
        # 4. 캐시 및 원본 이미지 초기화
        self.original_pixmap = None
        self.image_loader.clear_cache()
        self.fit_pixmap_cache.clear()
        if hasattr(self, 'thumbnail_panel'):
            self.thumbnail_panel.model.set_image_files([])
        if hasattr(self, 'grid_thumbnail_cache'):
            for key in self.grid_thumbnail_cache:
                self.grid_thumbnail_cache[key].clear()
        # 5. 뷰 및 UI 상태 초기화 (grid_mode를 먼저 Off로 설정)
        self.grid_mode = "Off" # update_grid_view가 참조할 상태를 먼저 설정합니다.
        self.grid_page_start_index = 0
        self.current_grid_index = 0
        self.previous_grid_mode = None
        self.viewport_focus_by_orientation.clear()
        self.current_active_rel_center = QPointF(0.5, 0.5)
        self.current_active_zoom_level = "Fit"
        
        # 6. UI 업데이트 (상태 변수 설정 후)
        self.folder_path_label.setText(LanguageManager.translate("폴더 경로"))
        self.raw_folder_path_label.setText(LanguageManager.translate("폴더 경로"))
        self.update_jpg_folder_ui_state()
        self.update_raw_folder_ui_state()
        self.update_match_raw_button_state()
        self.update_all_folder_labels_state()
        self.update_file_info_display(None)

        self.update_grid_view()

        if hasattr(self, 'grid_off_radio'):
            self.grid_off_radio.setChecked(True)
        self.update_zoom_radio_buttons_state()
        self.update_thumbnail_panel_style()
        
        logging.info("작업 공간 초기화 완료.")

    def setup_file_info_ui(self):
        """이미지 파일 정보 표시 UI 구성"""
        # 파일명 레이블 (커스텀 클래스 사용)
        # ========== UIScaleManager 적용 ==========
        filename_padding = UIScaleManager.get("filename_label_padding")
        self.info_filename_label = FilenameLabel("-", fixed_height_padding=filename_padding)
        self.info_filename_label.doubleClicked.connect(self.open_current_file_in_explorer)
        self.control_layout.addWidget(self.info_filename_label)

        # 정보 레이블들을 담을 하나의 컨테이너
        info_container = QWidget()
        info_container.setFixedWidth(UIScaleManager.get("info_container_width"))  # 고정 너비 설정으로 가운데 정렬 효과
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(UIScaleManager.get("control_layout_spacing"))

        # 정보 표시를 위한 레이블들 (왼쪽 정렬)
        # ========== UIScaleManager 적용 ==========
        info_padding = UIScaleManager.get("info_label_padding")
        info_label_style = f"color: #A8A8A8; padding-left: {info_padding}px;"
        info_font = QFont("Arial", UIScaleManager.get("font_size"))

        # 정보 레이블 공통 설정 함수
        def configure_info_label(label):
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setStyleSheet(info_label_style)
            label.setFont(info_font)
            label.setWordWrap(False)  # 줄바꿈 방지
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 텍스트 선택 가능
            # 가로 방향으로 고정된 크기 정책 설정 (확장 방지)
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            # 말줄임표 설정 (오른쪽에 ... 표시)
            label.setTextFormat(Qt.PlainText)  # 일반 텍스트 형식 사용
            try:
                # Qt 6에서는 setElideMode가 없을 수 있음
                if hasattr(label, "setElideMode"):
                    label.setElideMode(Qt.ElideRight)
            except:
                pass

        # 정보 레이블 생성 및 설정 적용
        self.info_datetime_label = QLabel("-")
        configure_info_label(self.info_datetime_label)
        info_layout.addWidget(self.info_datetime_label)

        self.info_resolution_label = QLabel("-")
        configure_info_label(self.info_resolution_label)
        info_layout.addWidget(self.info_resolution_label)

        self.info_camera_label = QLabel("-")
        configure_info_label(self.info_camera_label)
        info_layout.addWidget(self.info_camera_label)

        self.info_exposure_label = QLabel("-")
        configure_info_label(self.info_exposure_label)
        info_layout.addWidget(self.info_exposure_label)

        self.info_focal_label = QLabel("-")
        configure_info_label(self.info_focal_label)
        info_layout.addWidget(self.info_focal_label)

        self.info_aperture_label = QLabel("-")
        configure_info_label(self.info_aperture_label)
        info_layout.addWidget(self.info_aperture_label)
