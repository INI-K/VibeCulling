"""
UI 컴포넌트 모듈
QR 링크 라벨, 폴더 패스 라벨, 파일명 라벨 등 커스텀 UI 컴포넌트들
"""

import webbrowser
from PySide6.QtCore import Qt, Signal, QEvent, QUrl
from PySide6.QtGui import QPixmap, QFont, QMouseEvent, QKeyEvent, QFocusEvent, QDesktopServices
from PySide6.QtWidgets import QLabel, QLineEdit, QToolTip, QSizePolicy


class QRLinkLabel(QLabel):
    """
    마우스 오버 시 QR 코드를 보여주고 (macOS에서는 HTML 툴팁, 그 외 OS에서는 팝업),
    클릭 시 URL을 여는 범용 라벨 클래스.
    """
    def __init__(self, text, url, qr_path=None, parent=None, color="#D8D8D8", qr_display_size=400): # size -> qr_display_size로 변경
        super().__init__(text, parent)
        self.url = url
        self._qr_path = qr_path  # macOS HTML 툴팁과 다른 OS 팝업에서 공통으로 사용
        self._qr_display_size = qr_display_size # QR 코드 표시 크기 (툴팁/팝업 공통)

        self.normal_color = color
        self.hover_color = "#FFFFFF" # 또는 ThemeManager 사용

        # --- 스타일 및 커서 설정 ---
        self.setStyleSheet(f"""
            color: {self.normal_color};
            text-decoration: none; /* 링크 밑줄 제거 원하면 */
            font-weight: normal;
        """)
        self.setCursor(Qt.PointingHandCursor)

        # --- macOS가 아닌 경우에만 사용할 QR 팝업 멤버 ---
        self.qr_popup_widget = None # 실제 팝업 QLabel 위젯 (macOS에서는 사용 안 함)

        # --- macOS가 아닌 경우, 팝업 생성 (필요하다면) ---
        if platform.system() != "Darwin" and self._qr_path:
            self._create_non_mac_qr_popup()

    def _create_non_mac_qr_popup(self):
        """macOS가 아닌 환경에서 사용할 QR 코드 팝업 QLabel을 생성합니다."""
        if not self._qr_path or not Path(self._qr_path).exists():
            return

        self.qr_popup_widget = QLabel(self.window()) # 부모를 메인 윈도우로 설정하여 다른 위젯 위에 뜨도록
        self.qr_popup_widget.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.qr_popup_widget.setAttribute(Qt.WA_TranslucentBackground)
        # 흰색 배경, 둥근 모서리, 약간의 패딩을 가진 깔끔한 팝업 스타일
        self.qr_popup_widget.setStyleSheet(
            "background-color: white; border-radius: 5px; padding: 5px; border: 1px solid #CCCCCC;"
        )

        qr_pixmap = QPixmap(self._qr_path)
        if not qr_pixmap.isNull():
            scaled_pixmap = qr_pixmap.scaled(self._qr_display_size, self._qr_display_size,
                                             Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_popup_widget.setPixmap(scaled_pixmap)
            self.qr_popup_widget.adjustSize() # 콘텐츠 크기에 맞게 조절
        else:
            self.qr_popup_widget = None # Pixmap 로드 실패 시 팝업 사용 안 함

    def enterEvent(self, event):
        """마우스가 위젯에 들어왔을 때 스타일 변경 및 QR 코드/툴팁 표시"""
        self.setStyleSheet(f"""
            color: {self.hover_color};
            text-decoration: none;
            font-weight: bold;
        """)

        if platform.system() == "Darwin":
            if self._qr_path and Path(self._qr_path).exists():
                # macOS: HTML 툴팁 표시
                # QUrl.fromLocalFile을 사용하여 로컬 파일 경로를 올바른 URL 형식으로 변환
                local_file_url = QUrl.fromLocalFile(Path(self._qr_path).resolve()).toString()
                html = f'<img src="{local_file_url}" width="{self._qr_display_size}">'
                QToolTip.showText(self.mapToGlobal(event.position().toPoint()), html, self) # 세 번째 인자로 위젯 전달
            # else: macOS이지만 qr_path가 없으면 아무것도 안 함 (또는 기본 툴팁)
        else:
            # 다른 OS: 생성된 팝업 위젯 표시
            if self.qr_popup_widget and self.qr_popup_widget.pixmap() and not self.qr_popup_widget.pixmap().isNull():
                # 팝업 위치 계산 (마우스 커서 근처 또는 라벨 위 등)
                global_pos = self.mapToGlobal(QPoint(0, self.height())) # 라벨 하단 중앙 기준
                
                # 화면 경계 고려하여 팝업 위치 조정 (간단한 예시)
                screen_geo = QApplication.primaryScreen().availableGeometry()
                popup_width = self.qr_popup_widget.width()
                popup_height = self.qr_popup_widget.height()

                popup_x = global_pos.x() + (self.width() - popup_width) // 2
                popup_y = global_pos.y() + 5 # 라벨 아래에 약간의 간격

                # 화면 오른쪽 경계 초과 방지
                if popup_x + popup_width > screen_geo.right():
                    popup_x = screen_geo.right() - popup_width
                # 화면 왼쪽 경계 초과 방지
                if popup_x < screen_geo.left():
                    popup_x = screen_geo.left()
                # 화면 아래쪽 경계 초과 방지 (위로 올림)
                if popup_y + popup_height > screen_geo.bottom():
                    popup_y = global_pos.y() - popup_height - self.height() - 5 # 라벨 위로 이동
                # 화면 위쪽 경계 초과 방지 (아래로 내림 - 드문 경우)
                if popup_y < screen_geo.top():
                    popup_y = screen_geo.top()

                self.qr_popup_widget.move(popup_x, popup_y)
                self.qr_popup_widget.show()
                self.qr_popup_widget.raise_() # 다른 위젯 위로 올림

        super().enterEvent(event) # 부모 클래스의 enterEvent도 호출 (필요시)

    def leaveEvent(self, event):
        """마우스가 위젯을 벗어났을 때 스타일 복원 및 QR 코드/툴팁 숨김"""
        self.setStyleSheet(f"""
            color: {self.normal_color};
            text-decoration: none;
            font-weight: normal;
        """)

        if platform.system() == "Darwin":
            QToolTip.hideText() # macOS HTML 툴팁 숨김
        else:
            # 다른 OS: 팝업 위젯 숨김
            if self.qr_popup_widget:
                self.qr_popup_widget.hide()

        super().leaveEvent(event) # 부모 클래스의 leaveEvent도 호출

    def mouseReleaseEvent(self, event):
        """마우스 클릭 시 URL 열기"""
        if event.button() == Qt.LeftButton and self.url: # url이 있을 때만
            QDesktopServices.openUrl(QUrl(self.url))
        super().mouseReleaseEvent(event)

    # QR 팝업 위젯의 내용(QR 이미지)을 업데이트해야 할 경우를 위한 메서드 (선택 사항)
    def setQrPath(self, qr_path: str):
        self._qr_path = qr_path
        if platform.system() != "Darwin":
            # 기존 팝업이 있다면 숨기고, 새로 만들거나 업데이트
            if self.qr_popup_widget:
                self.qr_popup_widget.hide()
                # self.qr_popup_widget.deleteLater() # 필요시 이전 팝업 삭제
                self.qr_popup_widget = None
            if self._qr_path:
                self._create_non_mac_qr_popup()
        # macOS에서는 enterEvent에서 바로 처리하므로 별도 업데이트 불필요

class InfoFolderPathLabel(QLabel):
    """
    JPG/RAW 폴더 경로를 표시하기 위한 QLabel 기반 레이블. (기존 FolderPathLabel)
    2줄 높이, 줄 바꿈, 폴더 드래그 호버 효과를 지원합니다.
    """
    doubleClicked = Signal(str)
    folderDropped = Signal(str) # 폴더 경로만 전달

    def __init__(self, text="", parent=None):
        super().__init__(parent=parent)
        self.full_path = ""
        self.original_style = ""
        self.folder_index = -1 # 기본값 설정
        
        fixed_height_padding = UIScaleManager.get("folder_label_padding")
        
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(LanguageManager.translate("더블클릭하면 해당 폴더가 열립니다 (전체 경로 표시)"))
        font = QFont("Arial", UIScaleManager.get("font_size"))
        self.setFont(font)
        fm = QFontMetrics(font)
        line_height = fm.height()
        default_height = (line_height * 2) + fixed_height_padding
        self.setFixedHeight(default_height)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setAcceptDrops(True)
        
        self.set_style(is_valid=False)
        self.original_style = self.styleSheet()
        self.setText(text)

    def set_folder_index(self, index):
        """폴더 인덱스를 저장합니다."""
        self.folder_index = index

    def set_style(self, is_valid):
        """경로 유효성에 따라 스타일을 설정합니다."""
        if is_valid:
            style = f"""
                QLabel {{
                    color: #AAAAAA;
                    padding: 5px;
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border-radius: 1px;
                }}
            """
        else:
            style = f"""
                QLabel {{
                    color: {ThemeManager.get_color('text_disabled')};
                    padding: 5px;
                    background-color: {ThemeManager.get_color('bg_disabled')};
                    border-radius: 1px;
                }}
            """
        self.setStyleSheet(style)
        self.original_style = style

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and Path(urls[0].toLocalFile()).is_dir():
                event.acceptProposedAction()
                self.setStyleSheet(f"""
                    QLabel {{
                        color: #AAAAAA;
                        padding: 5px;
                        background-color: {ThemeManager.get_color('bg_primary')};
                        border: 2px solid {ThemeManager.get_color('accent')};
                        border-radius: 1px;
                    }}
                """)
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.original_style)

    def dropEvent(self, event):
        self.setStyleSheet(self.original_style)
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            if Path(file_path).is_dir():
                self.folderDropped.emit(file_path)
                event.acceptProposedAction()
                return
        event.ignore()

    def setText(self, text: str):
        self.full_path = text
        self.setToolTip(text)
        
        # 긴 경로 생략 로직
        max_length = 40
        prefix_length = 13
        suffix_length = 24
        # QGuiApplication.primaryScreen()을 사용하여 현재 화면의 비율을 얻는 것이 더 안정적입니다.
        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            aspect_ratio = geometry.width() / geometry.height() if geometry.height() else 0
            if abs(aspect_ratio - 1.6) < 0.1: # 대략 16:10 비율
                max_length=30; prefix_length=11; suffix_length=11

        if len(text) > max_length:
            display_text = text[:prefix_length] + "..." + text[-suffix_length:]
        else:
            display_text = text
        super().setText(display_text)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.full_path and self.full_path != LanguageManager.translate("폴더 경로"):
            self.doubleClicked.emit(self.full_path)

class EditableFolderPathLabel(QLineEdit):
    """
    분류 폴더 경로를 위한 QLineEdit 기반 위젯.
    상태에 따라 편집 가능/읽기 전용 모드를 전환하며 하위 폴더 생성을 지원합니다.
    """
    STATE_DISABLED = 0
    STATE_EDITABLE = 1
    STATE_SET = 2

    doubleClicked = Signal(str)
    imageDropped = Signal(int, str)
    folderDropped = Signal(int, str)
    stateChanged = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.full_path = ""
        self.folder_index = -1
        self._current_state = self.STATE_DISABLED
        self.original_style = ""
        
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        self.set_state(self.STATE_DISABLED)

    def set_folder_index(self, index):
        self.folder_index = index
        fm = QFontMetrics(self.font())
        line_height = fm.height()
        padding = UIScaleManager.get("sort_folder_label_padding")
        single_line_height = line_height + padding
        self.setFixedHeight(single_line_height)

    def set_state(self, state, path=None):
        self._current_state = state
        
        if self._current_state == self.STATE_DISABLED:
            self.setReadOnly(True)
            self.setCursor(Qt.ArrowCursor)
            style = f"""
                QLineEdit {{
                    color: {ThemeManager.get_color('text_disabled')};
                    background-color: {ThemeManager.get_color('bg_disabled')};
                    border: 1px solid {ThemeManager.get_color('bg_disabled')};
                    padding: 5px; border-radius: 1px;
                }}
            """
            self.setPlaceholderText("")
            self.setText(LanguageManager.translate("폴더 경로"))
            self.setToolTip(LanguageManager.translate("폴더를 드래그하여 지정하세요."))
        elif self._current_state == self.STATE_EDITABLE:
            self.setReadOnly(False)
            self.setCursor(Qt.IBeamCursor)
            style = f"""
                QLineEdit {{
                    color: {ThemeManager.get_color('text')};
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: 1px solid {ThemeManager.get_color('bg_primary')};
                    padding: 5px; border-radius: 1px;
                }}
                QLineEdit:focus {{ border: 1px solid {ThemeManager.get_color('accent')}; }}
            """
            self.setText("")
            self.setPlaceholderText(LanguageManager.translate("폴더 경로"))
            self.setToolTip(LanguageManager.translate("새 폴더명을 입력하거나 폴더를 드래그하여 지정하세요."))
        elif self._current_state == self.STATE_SET:
            self.setReadOnly(True)
            self.setCursor(Qt.PointingHandCursor)
            style = f"""
                QLineEdit {{
                    color: #AAAAAA;
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: 1px solid {ThemeManager.get_color('bg_primary')};
                    padding: 5px; border-radius: 1px;
                }}
            """
            self.setPlaceholderText("")
            if path:
                self.set_path_text(path)
            self.setToolTip(f"{self.full_path}\n{LanguageManager.translate('더블클릭하면 해당 폴더가 열립니다.')}")
        
        self.setStyleSheet(style)
        self.original_style = style
        self.stateChanged.emit(self.folder_index, self._current_state)

    def set_path_text(self, text: str):
        self.full_path = text
        self.setToolTip(text)
        
        max_len = 20  # 기본 최대 길이
        suf_len = 15  # 기본 뒷부분 길이

        screen = QGuiApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            aspect_ratio = geometry.width() / geometry.height() if geometry.height() > 0 else 0
            # 1.6 (16:10)에 가까운 비율인지 확인 (오차 범위 0.1)
            if abs(aspect_ratio - 1.6) < 0.1:
                logging.debug("16:10 비율 디스플레이 감지됨. EditableFolderPathLabel 텍스트 길이 조정.")
                max_len = 15
                suf_len = 12

        display_text = text
        if len(text) > max_len:
            display_text = "..." + text[-suf_len:]
            
        super().setText(display_text)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self._current_state == self.STATE_SET and self.full_path:
            self.doubleClicked.emit(self.full_path)
        else:
            super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event):
        if self._can_accept_drop(event):
            event.acceptProposedAction()
            self.apply_drag_hover_style()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._can_accept_drop(event):
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.restore_original_style()

    def dropEvent(self, event):
        self.restore_original_style()
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            if Path(file_path).is_dir():
                self.folderDropped.emit(self.folder_index, file_path)
                event.acceptProposedAction()
                return
        elif event.mimeData().hasText():
            drag_data = event.mimeData().text()
            if drag_data.startswith("image_drag:"):
                if self.folder_index >= 0 and self._current_state == self.STATE_SET:
                    self.imageDropped.emit(self.folder_index, drag_data)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def _can_accept_drop(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            return len(urls) == 1 and Path(urls[0].toLocalFile()).is_dir()
        
        can_accept_image = (self.folder_index >= 0 and self._current_state == self.STATE_SET)
        if event.mimeData().hasText() and event.mimeData().text().startswith("image_drag:") and can_accept_image:
            return True
            
        return False

    def apply_drag_hover_style(self):
        """드래그 호버 시 테두리만 강조하는 스타일을 적용합니다."""
        hover_style = ""
        if self._current_state == self.STATE_DISABLED:
            hover_style = f"""
                QLineEdit {{
                    color: {ThemeManager.get_color('text_disabled')};
                    background-color: {ThemeManager.get_color('bg_disabled')};
                    border: 2px solid {ThemeManager.get_color('accent')};
                    padding: 4px; border-radius: 1px;
                }}
            """
        elif self._current_state == self.STATE_EDITABLE:
            hover_style = f"""
                QLineEdit {{
                    color: {ThemeManager.get_color('text')};
                    background-color: {ThemeManager.get_color('bg_secondary')};
                    border: 2px solid {ThemeManager.get_color('accent')};
                    padding: 4px; border-radius: 1px;
                }}
                QLineEdit:focus {{ border: 2px solid {ThemeManager.get_color('accent')}; }}
            """
        elif self._current_state == self.STATE_SET:
            hover_style = f"""
                QLineEdit {{
                    color: #AAAAAA;
                    background-color: {ThemeManager.get_color('bg_primary')};
                    border: 2px solid {ThemeManager.get_color('accent')};
                    padding: 4px; border-radius: 1px;
                }}
            """
        if hover_style:
            self.setStyleSheet(hover_style)

    def apply_keypress_highlight(self, highlight: bool):
        if self._current_state != self.STATE_SET:
            return

        if highlight:
            style = f"""
                QLineEdit {{
                    color: #FFFFFF;
                    background-color: {ThemeManager.get_color('accent')};
                    border: 1px solid {ThemeManager.get_color('accent')};
                    padding: 5px; border-radius: 1px;
                }}
            """
            self.setStyleSheet(style)
        else:
            self.restore_original_style()

    def restore_original_style(self):
        self.setStyleSheet(self.original_style)

class FilenameLabel(QLabel):
    """파일명을 표시하는 레이블 클래스, 더블클릭 시 파일 열기"""
    doubleClicked = Signal(str) # 시그널에 파일명(str) 전달

    def __init__(self, text="", fixed_height_padding=40, parent=None):
        super().__init__(parent=parent)
        self._raw_display_text = "" # 아이콘 포함될 수 있는, 화면 표시용 전체 텍스트
        self._actual_filename_for_opening = "" # 더블클릭 시 열어야 할 실제 파일명 (아이콘X)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)

        font = QFont("Arial", UIScaleManager.get("filename_font_size"))
        font.setBold(True)
        self.setFont(font)

        fm = QFontMetrics(font)
        line_height = fm.height()
        fixed_height = line_height + fixed_height_padding
        self.setFixedHeight(fixed_height)

        self.setWordWrap(True)
        self.setStyleSheet(f"color: {ThemeManager.get_color('text')};")
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        
        # 초기 텍스트 설정 (만약 text에 아이콘이 있다면 분리 필요)
        self.set_display_and_actual_filename(text, text.replace("🔗", "")) # 아이콘 제거 시도

    def set_display_and_actual_filename(self, display_text: str, actual_filename: str):
        """표시용 텍스트와 실제 열릴 파일명을 별도로 설정"""
        self._raw_display_text = display_text # 아이콘 포함 가능성 있는 전체 표시 텍스트
        self._actual_filename_for_opening = actual_filename # 아이콘 없는 순수 파일명

        self.setToolTip(self._raw_display_text) # 툴팁에는 전체 표시 텍스트

        # 화면 표시용 텍스트 생략 처리 (아이콘 포함된 _raw_display_text 기준)
        if len(self._raw_display_text) > 17: # 아이콘 길이를 고려하여 숫자 조정 필요 가능성
            # 아이콘이 있다면 아이콘은 유지하면서 앞부분만 생략
            if "🔗" in self._raw_display_text:
                name_part = self._raw_display_text.replace("🔗", "")
                if len(name_part) > 15: # 아이콘 제외하고 15자 초과 시
                    display_text_for_label = name_part[:6] + "..." + name_part[-7:] + "🔗"
                else:
                    display_text_for_label = self._raw_display_text
            else: # 아이콘 없을 때
                display_text_for_label = self._raw_display_text[:6] + "..." + self._raw_display_text[-10:]
        else:
            display_text_for_label = self._raw_display_text

        super().setText(display_text_for_label)

    # setText는 이제 set_display_and_actual_filename을 사용하도록 유도하거나,
    # 이전 setText의 역할을 유지하되 내부적으로 _actual_filename_for_opening을 관리해야 함.
    # 여기서는 set_display_and_actual_filename을 주 사용 메서드로 가정.
    def setText(self, text: str): # 이 메서드는 VibeCullingApp에서 직접 호출 시 주의
        # 아이콘 유무에 따라 실제 열릴 파일명 결정
        actual_name = text.replace("🔗", "")
        self.set_display_and_actual_filename(text, actual_name)

    def text(self) -> str: # 화면에 표시되는 텍스트 반환 (생략된 텍스트)
        return super().text()

    def raw_display_text(self) -> str: # 아이콘 포함된 전체 표시 텍스트 반환
        return self._raw_display_text

    def actual_filename_for_opening(self) -> str: # 실제 열릴 파일명 반환
        return self._actual_filename_for_opening

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """더블클릭 시 _actual_filename_for_opening으로 시그널 발생"""
        if self._actual_filename_for_opening:
            self.doubleClicked.emit(self._actual_filename_for_opening) # 아이콘 없는 파일명 전달

