"""
썸네일 뷰 모듈
썸네일 델리게이트, 드래그 가능한 썸네일 뷰, 썸네일 패널 등
"""

from PySide6.QtCore import Qt, Signal, QRect, QPoint, QTimer
from PySide6.QtGui import QPainter, QPixmap, QMouseEvent, QDrag, QFont, QColor, QPen
from PySide6.QtWidgets import (
    QStyledItemDelegate, QStyle, QListView, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QCheckBox, QSizePolicy
)


class ThumbnailDelegate(QStyledItemDelegate):
    """썸네일 아이템의 렌더링을 담당하는 델리게이트"""
    
    # 썸네일 클릭 시그널
    thumbnailClicked = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._placeholder_pixmap = self._create_placeholder()
    
    def _create_placeholder(self):
        """플레이스홀더 이미지 생성"""
        size = UIScaleManager.get("thumbnail_image_size")
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor("#222222"))
        return pixmap
    
    def paint(self, painter, option, index):
        """썸네일 아이템 렌더링 (테두리 보존 하이라이트)"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # --- 기본 변수 설정 ---
        rect = option.rect
        image_size = UIScaleManager.get("thumbnail_image_size")
        padding = UIScaleManager.get("thumbnail_padding")
        text_height = UIScaleManager.get("thumbnail_text_height")
        border_width = UIScaleManager.get("thumbnail_border_width")
        
        # --- 상태 확인 ---
        is_current = index.data(Qt.UserRole + 1)
        is_selected = option.state & QStyle.State_Selected
        
        # --- 1. 테두리 그리기 (모든 아이템에 동일한 테두리) ---
        # 테두리 색상으로 전체 아이템 영역을 먼저 칠합니다.
        border_color = QColor("#505050")
        painter.fillRect(rect, border_color)

        # --- 2. 배경 그리기 (테두리 안쪽으로) ---
        # 배경을 칠할 영역을 테두리 두께만큼 안쪽으로 축소합니다.
        # rect.adjusted(left, top, right, bottom) - right, bottom은 음수여야 축소됨
        inner_bg_rect = rect.adjusted(border_width, border_width, -border_width, -border_width)

        # 선택 상태에 따라 배경색 결정
        if is_current or is_selected:
            bg_color = QColor("#525252") # 선택 시 밝은 회색
        else:
            bg_color = QColor(ThemeManager.get_color('bg_primary'))   # 비선택 시 어두운 배경색
        
        # 축소된 영역에 배경색을 칠합니다.
        painter.fillRect(inner_bg_rect, bg_color)
            
        # --- 3. 이미지 그리기 ---
        image_path = index.data(Qt.UserRole)
        if image_path:
            pixmap = index.data(Qt.DecorationRole)
            target_pixmap = pixmap if pixmap and not pixmap.isNull() else self._placeholder_pixmap
            
            scaled_pixmap = target_pixmap.scaled(
                image_size, image_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            x_pos = rect.x() + (rect.width() - scaled_pixmap.width()) // 2
            image_area_height = rect.height() - text_height - (padding * 3)
            y_pos = rect.y() + padding + (image_area_height - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x_pos, y_pos, scaled_pixmap)

        # --- 4. 파일명 텍스트 그리기 ---
        filename = index.data(Qt.DisplayRole)
        if filename:
            text_rect = QRect(
                rect.x() + padding,
                rect.y() + padding + image_size + padding,
                rect.width() - (padding * 2),
                text_height
            )
            
            painter.setPen(QColor(ThemeManager.get_color('text')))
            font = QFont("Arial", UIScaleManager.get("font_size", 10))
            font.setPointSize(UIScaleManager.get("font_size"))
            painter.setFont(font)
            
            metrics = painter.fontMetrics()
            elided_text = metrics.elidedText(filename, Qt.ElideMiddle, text_rect.width())
            painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, elided_text)

        painter.restore()


    
    def sizeHint(self, option, index):
        """아이템 크기 힌트"""
        height = UIScaleManager.get("thumbnail_item_height")
        return QSize(0, height)

class DraggableThumbnailView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_start_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position().toPoint()
        # 기본 mousePressEvent를 호출하지 않아 즉시 선택되는 것을 방지
        # super().mousePressEvent(event) 

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.drag_start_position:
            return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # 드래그 시작
        drag = QDrag(self)
        mime_data = QMimeData()
        
        index = self.indexAt(self.drag_start_position)
        if not index.isValid():
            return
        
        # 드래그 데이터에 이미지 인덱스 저장
        mime_data.setText(f"thumbnail_drag:{index.row()}")
        drag.setMimeData(mime_data)

        # 드래그 시 보여줄 썸네일 이미지 설정
        pixmap = index.data(Qt.DecorationRole)
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            drag.setPixmap(scaled_pixmap)
            drag.setHotSpot(QPoint(32, 32))

        drag.exec(Qt.CopyAction)
        self.drag_start_position = None # 드래그 후 초기화

    def mouseReleaseEvent(self, event):
        # 드래그가 시작되지 않았다면, 일반 클릭으로 간주하여 선택 처리
        if self.drag_start_position is not None:
            # 마우스 누른 위치와 뗀 위치가 거의 같다면 클릭으로 처리
            if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                # 기본 QListView의 클릭 동작을 여기서 수행
                super().mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, event.position().toPoint(), event.globalPosition().toPoint(), event.button(), event.buttons(), event.modifiers()))
                super().mouseReleaseEvent(event)
        self.drag_start_position = None

class ThumbnailPanel(QWidget):
    """썸네일 패널 위젯 - 현재 이미지 주변의 썸네일들을 표시"""
    
    # 시그널 정의
    thumbnailClicked = Signal(int)           # 썸네일 클릭 시 인덱스 전달
    thumbnailDoubleClicked = Signal(int)     # 썸네일 더블클릭 시 인덱스 전달
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent  # VibeCullingApp 참조
        
        # 모델과 델리게이트 생성 (image_loader 전달)
        self.model = ThumbnailModel([], self.parent_app.image_loader if self.parent_app else None, self)
        self.delegate = ThumbnailDelegate(self)

        self.setup_ui()
        self.connect_signals()
        
        # 테마/언어 변경 콜백 등록
        ThemeManager.register_theme_change_callback(self.update_ui_colors)
        
    def setup_ui(self):
        """UI 구성 요소 초기화"""
        # 메인 레이아웃
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(UIScaleManager.get("control_layout_spacing"))
        
        # 썸네일 리스트 뷰
        self.list_view = DraggableThumbnailView()
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setDragEnabled(True)
        
        # 리스트 뷰 설정
        self.list_view.setSelectionMode(QListView.SingleSelection)
        self.list_view.setDragDropMode(QListView.DragOnly)           # 드래그 허용
        self.list_view.setDefaultDropAction(Qt.MoveAction)
        self.list_view.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_view.setSpacing(UIScaleManager.get("thumbnail_item_spacing"))

        # 썸네일 아이템 간격 설정
        item_spacing = UIScaleManager.get("thumbnail_item_spacing")
        
        # 스타일 설정
        self.list_view.setStyleSheet(f"""
            QListView {{
                background-color: {ThemeManager.get_color('bg_primary')};
                border: none;
                outline: none;
                padding: {item_spacing}px;
                spacing: {item_spacing}px;
            }}
            QListView::item {{
                border: none;
                padding: 0px;
                margin-bottom: {item_spacing}px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {ThemeManager.get_color('bg_primary')};
                width: 10px;
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
        
        # 레이아웃에 추가
        self.layout.addWidget(self.list_view, 1)  # 확장 가능
        
        # 패널 전체 스타일
        self.setStyleSheet(f"""
            ThumbnailPanel {{
                background-color: {ThemeManager.get_color('bg_primary')};
                border-right: 1px solid {ThemeManager.get_color('border')};
            }}
        """)
        
        # 최소 크기 설정
        min_width = UIScaleManager.get("thumbnail_panel_min_width")
        max_width = UIScaleManager.get("thumbnail_panel_max_width")
        self.setMinimumWidth(min_width)
        self.setMaximumWidth(max_width)
        
    def connect_signals(self):
        """시그널 연결"""
        # 모델 시그널 연결
        logging.info("ThumbnailPanel: 시그널 연결 시작")
        self.model.currentIndexChanged.connect(self.on_current_index_changed)
        
        # 리스트 뷰 시그널 연결
        self.list_view.clicked.connect(self.on_thumbnail_clicked)
        self.list_view.doubleClicked.connect(self.on_thumbnail_double_clicked)

        
        logging.info("ThumbnailPanel: 모든 시그널 연결 완료")
    
    def set_image_files(self, image_files):
        """이미지 파일 목록 설정"""
        logging.info(f"ThumbnailPanel.set_image_files: {len(image_files) if image_files else 0}개 파일 설정")
        self.model.set_image_files(image_files)
        
        # 모델 상태 확인
        logging.debug(f"ThumbnailPanel: 모델 rowCount={self.model.rowCount()}")
                
    def set_current_index(self, index):
        """현재 인덱스 설정 및 스크롤"""
        if not self.model._image_files or index < 0 or index >= len(self.model._image_files):
            return
        
        self.model.set_current_index(index)
        
        self.scroll_to_index(index)
        
        self.preload_surrounding_thumbnails(index)
    
    def scroll_to_index(self, index):
        """지정된 인덱스가 리스트 중앙에 오도록 스크롤 (타이머로 지연 실행)"""
        if index < 0 or index >= self.model.rowCount():
            return
        
        # 10ms의 짧은 지연을 추가하여 뷰가 업데이트될 시간을 확실히 보장합니다.
        QTimer.singleShot(10, lambda: self._perform_scroll(index))

    def _perform_scroll(self, index):
        """실제 스크롤을 수행하는 내부 메서드"""
        # 타이머 콜백 시점에 인덱스가 여전히 유효한지 다시 확인
        if 0 <= index < self.model.rowCount():
            model_index = self.model.createIndex(index, 0)
            
            # 1. 뷰에게 현재 인덱스가 무엇인지 명시적으로 알려줍니다.
            #    이렇게 하면 뷰가 스크롤 위치를 계산하기 전에 올바른 아이템에 집중하게 됩니다.
            self.list_view.setCurrentIndex(model_index)
            
            # 2. 스크롤을 수행합니다.
            self.list_view.scrollTo(model_index, QListView.PositionAtCenter)
    
    def preload_surrounding_thumbnails(self, center_index, radius=5):
        """중심 인덱스 주변의 썸네일 미리 로딩"""
        self.model.preload_thumbnails(center_index, radius)

    
    def on_current_index_changed(self, index):
        """모델의 현재 인덱스 변경 시 호출"""
        # 필요시 추가 처리
        pass
    
    def on_thumbnail_clicked(self, model_index):
        """썸네일 클릭 시 호출"""
        if model_index.isValid():
            index = model_index.row()
            self.thumbnailClicked.emit(index)

    def on_thumbnail_double_clicked(self, model_index):
        """썸네일 더블클릭 시 호출"""
        if model_index.isValid():
            index = model_index.row()
            self.thumbnailDoubleClicked.emit(index)
    
    def get_selected_indexes(self):
        """현재 선택된 인덱스들 반환"""
        selection_model = self.list_view.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        return [index.row() for index in selected_indexes]
    
    def clear_selection(self):
        """선택 해제"""
        self.list_view.clearSelection()
    
    
    def update_ui_colors(self):
        """테마 변경 시 UI 색상 업데이트"""
        self.list_view.setStyleSheet(f"""
            QListView {{
                background-color: {ThemeManager.get_color('bg_primary')};
                border: none;
                outline: none;
            }}
            QListView::item {{
                border: none;
                padding: 0px;
            }}
            QListView::item:selected {{
                background-color: {ThemeManager.get_color('accent')};
                background-color: rgba(255, 255, 255, 30);
            }}
            QScrollBar:vertical {{
                border: none;
                background: {ThemeManager.get_color('bg_primary')};
                width: 10px;
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
    



