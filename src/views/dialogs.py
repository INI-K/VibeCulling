"""
다이얼로그 모듈
파일 리스트 다이얼로그, 세션 관리 다이얼로그 등
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QColor, QPalette
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QLabel, QLineEdit, QComboBox,
    QCheckBox, QInputDialog, QSizePolicy, QScrollArea, QTextBrowser,
    QWidget
)

# 필요한 모듈들 import
from ..config import LanguageManager, ThemeManager, UIScaleManager


# 플랫폼별 기능 (필요시)
def apply_dark_title_bar(widget):
    """다크 타이틀 바 적용 (macOS/Windows 호환)"""
    try:
        if hasattr(widget, 'winId'):
            # 플랫폼별 다크 타이틀 바 구현
            pass
    except Exception as e:
        logging.warning(f"다크 타이틀 바 적용 실패: {e}")


class FileListDialog(QDialog):
    """사진 목록과 미리보기를 보여주는 팝업 대화상자"""
    def __init__(self, image_files, current_index, image_loader, parent=None):
        super().__init__(parent)
        self.image_files = image_files
        self.image_loader = image_loader
        self.preview_size = 750 # --- 미리보기 크기 750으로 변경 ---

        self.setWindowTitle(LanguageManager.translate("사진 목록"))
        # 창 크기 조정 (미리보기 증가 고려)
        self.setMinimumSize(1200, 850)

        # 제목표시줄 다크 테마
        apply_dark_title_bar(self)

        # --- 다크 테마 배경 설정 (이전 코드 유지) ---
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # --- 메인 레이아웃 (이전 코드 유지) ---
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # --- 좌측: 파일 목록 (이전 코드 유지, 스타일 포함) ---
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')};
                border-radius: 4px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 2px 0px;
            }}
            QListWidget::item:selected {{
                background-color: {ThemeManager.get_color('accent')};
                color: {ThemeManager.get_color('bg_primary')};
            }}
        """)
        list_font = parent.default_font if parent and hasattr(parent, 'default_font') else QFont("Arial", UIScaleManager.get("font_size", 10))
        list_font.setPointSize(UIScaleManager.get("font_size") -1)
        self.list_widget.setFont(list_font)

        # 파일 목록 채우기 (이전 코드 유지)
        for i, file_path in enumerate(self.image_files):
            item = QListWidgetItem(file_path.name)
            item.setData(Qt.UserRole, str(file_path))
            self.list_widget.addItem(item)

        # 현재 항목 선택 및 스크롤 (이전 코드 유지)
        if 0 <= current_index < self.list_widget.count():
            self.list_widget.setCurrentRow(current_index)
            self.list_widget.scrollToItem(self.list_widget.item(current_index), QListWidget.PositionAtCenter)

        # --- 우측: 미리보기 레이블 ---
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(self.preview_size, self.preview_size) # --- 크기 750 적용 ---
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(f"background-color: black; border-radius: 4px;")

        # --- 레이아웃에 위젯 추가 (이전 코드 유지) ---
        self.main_layout.addWidget(self.list_widget, 1)
        self.main_layout.addWidget(self.preview_label, 0)

        # --- 미리보기 업데이트 지연 로딩을 위한 타이머 설정 ---
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True) # 한 번만 실행
        self.preview_timer.setInterval(200)  # 200ms 지연
        self.preview_timer.timeout.connect(self.load_preview) # 타이머 만료 시 load_preview 호출

        self.list_widget.currentItemChanged.connect(self.on_selection_changed)
        # --- 더블클릭 시그널 연결 추가 ---
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        # 초기 미리보기 로드 (즉시 로드)
        self.update_preview(self.list_widget.currentItem())

    def on_selection_changed(self, current, previous):
        """목록 선택 변경 시 호출되는 슬롯, 미리보기 타이머 시작/재시작"""
        # 현재 선택된 항목이 유효할 때만 타이머 시작
        if current:
            self.preview_timer.start() # 타이머 시작 (이미 실행 중이면 재시작)
        else:
            # 선택된 항목이 없으면 미리보기 즉시 초기화하고 타이머 중지
            self.preview_timer.stop()
            self.preview_label.clear()
            self.preview_label.setText(LanguageManager.translate("선택된 파일 없음"))
            self.preview_label.setStyleSheet(f"background-color: black; color: white; border-radius: 4px;")


    def load_preview(self):
        """타이머 만료 시 실제 미리보기 로딩 수행"""
        current_item = self.list_widget.currentItem()
        self.update_preview(current_item)


    def update_preview(self, current_item): # current_item 인자 유지
        """선택된 항목의 미리보기 업데이트 (실제 로직)"""
        if not current_item:
            # load_preview 에서 currentItem()을 가져오므로, 여기서 다시 체크할 필요는 적지만 안전하게 둠
            self.preview_label.clear()
            self.preview_label.setText(LanguageManager.translate("선택된 파일 없음"))
            self.preview_label.setStyleSheet(f"background-color: black; color: white; border-radius: 4px;")
            return

        file_path = current_item.data(Qt.UserRole)
        if not file_path:
            self.preview_label.clear()
            self.preview_label.setText(LanguageManager.translate("파일 경로 없음"))
            self.preview_label.setStyleSheet(f"background-color: black; color: white; border-radius: 4px;")
            return

        # 이미지 로더를 통해 이미지 로드 (캐시 활용)
        pixmap = self.image_loader.load_image_with_orientation(file_path)

        if pixmap.isNull():
            self.preview_label.clear()
            self.preview_label.setText(LanguageManager.translate("미리보기 로드 실패"))
            self.preview_label.setStyleSheet(f"background-color: black; color: red; border-radius: 4px;")
        else:
            # 스케일링 속도 개선 (FastTransformation 유지)
            scaled_pixmap = pixmap.scaled(self.preview_size, self.preview_size, Qt.KeepAspectRatio, Qt.FastTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            # 텍스트 제거를 위해 스타일 초기화
            self.preview_label.setStyleSheet(f"background-color: black; border-radius: 4px;")

    # --- 더블클릭 처리 메서드 추가 ---
    def on_item_double_clicked(self, item):
        """리스트 항목 더블클릭 시 호출되는 슬롯"""
        file_path_str = item.data(Qt.UserRole)
        if not file_path_str:
            return

        file_path = Path(file_path_str)
        parent_app = self.parent() # VibeCullingApp 인스턴스 가져오기

        # 부모가 VibeCullingApp 인스턴스이고 필요한 속성/메서드가 있는지 확인
        if parent_app and hasattr(parent_app, 'image_files') and hasattr(parent_app, 'set_current_image_from_dialog'):
            try:
                # VibeCullingApp의 image_files 리스트에서 해당 Path 객체의 인덱스 찾기
                index = parent_app.image_files.index(file_path)
                parent_app.set_current_image_from_dialog(index) # 부모 앱의 메서드 호출
                self.accept() # 다이얼로그 닫기 (성공적으로 처리되면)
            except ValueError:
                logging.error(f"오류: 더블클릭된 파일을 메인 목록에서 찾을 수 없습니다: {file_path}")
                # 사용자를 위한 메시지 박스 표시 등 추가 가능
                QMessageBox.warning(self, 
                                    LanguageManager.translate("오류"), 
                                    LanguageManager.translate("선택한 파일을 현재 목록에서 찾을 수 없습니다.\n목록이 변경되었을 수 있습니다."))
            except Exception as e:
                logging.error(f"더블클릭 처리 중 오류 발생: {e}")
                QMessageBox.critical(self, 
                                     LanguageManager.translate("오류"), 
                                     f"{LanguageManager.translate('이미지 이동 중 오류가 발생했습니다')}:\n{e}")
        else:
            logging.error("오류: 부모 위젯 또는 필요한 속성/메서드를 찾을 수 없습니다.")
            QMessageBox.critical(self, 
                                 LanguageManager.translate("오류"), 
                                 LanguageManager.translate("내부 오류로 인해 이미지로 이동할 수 없습니다."))

class SessionManagementDialog(QDialog):
    def __init__(self, parent_widget: QWidget, main_app_logic: 'VibeCullingApp'): # 부모 위젯과 로직 객체를 분리
        super().__init__(parent_widget) # QDialog의 부모 설정
        self.parent_app = main_app_logic # VibeCullingApp의 메서드 호출을 위해 저장

        self.setWindowTitle(LanguageManager.translate("세션 관리"))
        self.setMinimumSize(500, 400) # 팝업창 최소 크기

        # 다크 테마 적용
        apply_dark_title_bar(self)
        palette = QPalette(); palette.setColor(QPalette.Window, QColor(ThemeManager.get_color('bg_primary')))
        self.setPalette(palette); self.setAutoFillBackground(True)

        # --- 메인 레이아웃 ---
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        button_style = f"""
            QPushButton {{
                background-color: {ThemeManager.get_color('bg_secondary')}; color: {ThemeManager.get_color('text')};
                border: none; padding: 8px 12px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {ThemeManager.get_color('bg_hover')}; }}
            QPushButton:pressed {{ background-color: {ThemeManager.get_color('bg_pressed')}; }}
            QPushButton:disabled {{
                background-color: {ThemeManager.get_color('bg_disabled')};
                color: {ThemeManager.get_color('text_disabled')};
            }}
        """

        # --- 1. 현재 세션 저장 버튼 ---
        self.save_current_button = QPushButton(LanguageManager.translate("현재 세션 저장"))
        self.save_current_button.setStyleSheet(button_style)
        self.save_current_button.clicked.connect(self.prompt_and_save_session)
        main_layout.addWidget(self.save_current_button)

        # --- 2. 저장된 세션 목록 ---
        list_label = QLabel(LanguageManager.translate("저장된 세션 목록 (최대 20개):"))
        list_label.setStyleSheet(f"color: {ThemeManager.get_color('text')}; margin-top: 10px;")
        main_layout.addWidget(list_label)

        self.session_list_widget = QListWidget()
        self.session_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {ThemeManager.get_color('bg_secondary')};
                color: {ThemeManager.get_color('text')};
                border: 1px solid {ThemeManager.get_color('border')};
                border-radius: 3px; padding: 5px;
            }}
            QListWidget::item {{ padding: 3px 2px; }}
            QListWidget::item:selected {{
                background-color: {ThemeManager.get_color('accent')};
                color: white; /* 선택 시 텍스트 색상 */
            }}
        """)
        self.session_list_widget.currentItemChanged.connect(self.update_all_button_states)
        main_layout.addWidget(self.session_list_widget, 1)

        # --- 3. 불러오기 및 삭제 버튼 ---
        buttons_layout = QHBoxLayout()
        self.load_button = QPushButton(LanguageManager.translate("선택 세션 불러오기"))
        self.load_button.setStyleSheet(button_style)
        self.load_button.clicked.connect(self.load_selected_session)
        self.load_button.setEnabled(False)

        self.delete_button = QPushButton(LanguageManager.translate("선택 세션 삭제"))
        self.delete_button.setStyleSheet(button_style)
        self.delete_button.clicked.connect(self.delete_selected_session)
        self.delete_button.setEnabled(False)

        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.load_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch(1)
        main_layout.addLayout(buttons_layout)
        
        self.populate_session_list()
        self.update_all_button_states()

    def populate_session_list(self):
        """VibeCullingApp의 saved_sessions를 가져와 목록 위젯을 채웁니다."""
        self.session_list_widget.clear()
        
        # 타임스탬프를 기준으로 세션을 정렬합니다 (오래된 것이 위로).
        session_items = self.parent_app.saved_sessions.items()
        # 타임스탬프가 없는 경우를 대비하여 기본값("")을 사용하고, 문자열로 정렬합니다.
        sorted_session_items = sorted(
            session_items, 
            key=lambda item: item[1].get("timestamp", "")
        )
        
        for session_name, session_data in sorted_session_items:
            timestamp = session_data.get("timestamp", "")
            display_text = session_name
            if timestamp:
                try: 
                    dt_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    formatted_ts = dt_obj.strftime("%y/%m/%d %H:%M")
                    display_text = f"{session_name} ({formatted_ts})"
                except ValueError:
                    pass 
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, session_name)
            self.session_list_widget.addItem(item)
            
        self.update_all_button_states()


    def update_all_button_states(self): # 새로운 메서드 또는 기존 update_button_states 확장
        """세션 목록 선택 상태 및 이미지 로드 상태에 따라 모든 버튼의 활성화 상태를 업데이트합니다."""
        # 1. 불러오기/삭제 버튼 상태 업데이트 (기존 로직)
        selected_item = self.session_list_widget.currentItem()
        is_item_selected = selected_item is not None
        self.load_button.setEnabled(is_item_selected)
        self.delete_button.setEnabled(is_item_selected)
        logging.debug(f"SessionManagementDialog.update_all_button_states: Item selected={is_item_selected}")

        # 2. "현재 세션 저장" 버튼 상태 업데이트
        # VibeCullingApp의 image_files 목록이 비어있지 않을 때만 활성화
        can_save_session = bool(self.parent_app.image_files) # 이미지 파일 목록이 있는지 확인
        self.save_current_button.setEnabled(can_save_session)
        logging.debug(f"SessionManagementDialog.update_all_button_states: Can save session={can_save_session}")



    def prompt_and_save_session(self):
        default_name = self.parent_app._generate_default_session_name()

        self.parent_app.is_input_dialog_active = True # 메인 앱의 플래그 설정
        try:
            text, ok = QInputDialog.getText(self,
                                             LanguageManager.translate("세션 이름"),
                                             LanguageManager.translate("저장할 세션 이름을 입력하세요:"),
                                             QLineEdit.Normal,
                                             default_name)
        finally:
            self.parent_app.is_input_dialog_active = False # 메인 앱의 플래그 해제

        if ok and text:
            if self.parent_app.save_current_session(text): # 성공 시
                self.populate_session_list() # 목록 새로고침
        elif ok and not text:
            self.parent_app.show_themed_message_box(QMessageBox.Warning, LanguageManager.translate("저장 오류"), LanguageManager.translate("세션 이름을 입력해야 합니다."))


    def load_selected_session(self):
        selected_items = self.session_list_widget.selectedItems()
        if selected_items:
            session_name_to_load = selected_items[0].data(Qt.UserRole) # 저장된 실제 이름 가져오기
            
            success = self.parent_app.load_session(session_name_to_load)
            
            if success:
                self.accept() # SessionManagementDialog 닫기
                
                # 부모가 settings_popup인지 확인하고 닫습니다.
                parent_popup = self.parent()
                if parent_popup and hasattr(self.parent_app, 'settings_popup') and parent_popup is self.parent_app.settings_popup:
                    parent_popup.accept()


    def delete_selected_session(self):
        selected_items = self.session_list_widget.selectedItems()
        if selected_items:
            session_name_to_delete = selected_items[0].data(Qt.UserRole)
            reply = self.parent_app.show_themed_message_box(
                QMessageBox.Question,
                LanguageManager.translate("삭제 확인"),
                LanguageManager.translate("'{session_name}' 세션을 정말 삭제하시겠습니까?").format(session_name=session_name_to_delete),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.parent_app.delete_session(session_name_to_delete)
                # self.populate_session_list() # delete_session 내부에서 호출될 것임

def format_camera_name(make, model):
    make_str = (make or "").strip()
    model_str = (model or "").strip()
    # 1. OLYMPUS IMAGING CORP. → OLYMPUS로 치환
    if make_str.upper() == "OLYMPUS IMAGING CORP.":
        make_str = "OLYMPUS"
    # 2. RICOH가 make에 있으면 make 생략
    if "RICOH" in make_str.upper():
        make_str = ""
    if make_str.upper().find("NIKON") != -1 and model_str.upper().startswith("NIKON"):
        return model_str
    if make_str.upper().find("CANON") != -1 and model_str.upper().startswith("CANON"):
        return model_str
    return f"{make_str} {model_str}".strip()

