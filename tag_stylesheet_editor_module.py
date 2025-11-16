"""
태그 스타일시트 에디터 모듈 - 다중 태그 선택 및 OR 방식 이미지 표시
"""

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit, 
                               QSizePolicy, QScrollArea, QGridLayout, QFrame, QWidget, QLayout, QComboBox, QLayoutItem, QWidgetItem, QApplication, QCheckBox, QSpinBox, QDoubleSpinBox)

# 전역 커스텀 클래스 import
try:
    import sys
    main_module = sys.modules.get('__main__')
    if main_module and hasattr(main_module, 'CustomSpinBox'):
        CustomSpinBox = main_module.CustomSpinBox
        CustomDoubleSpinBox = main_module.CustomDoubleSpinBox
        CustomComboBox = main_module.CustomComboBox
    else:
        # 직접 정의 (fallback)
        CustomSpinBox = QSpinBox
        CustomDoubleSpinBox = QDoubleSpinBox
        CustomComboBox = QComboBox
except:
    # 실패 시 기본 클래스 사용
    CustomSpinBox = QSpinBox
    CustomDoubleSpinBox = QDoubleSpinBox
    CustomComboBox = QComboBox
from PySide6.QtCore import Signal, QTimer, Qt, QSize, QRect, QPoint, QObject
from PySide6.QtGui import QPixmap, QPainter, QPen, QFont, QColor, QImageReader
from pathlib import Path
import math


class FlowLayout(QLayout):
    """커스텀 FlowLayout - 태그 버튼들을 자연스럽게 배치"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item_list = []
        self.spacing = 8
    
    def expandingDirections(self):
        """가로 확장 방지 - 세로로만 확장"""
        return Qt.Orientation.Vertical
    
    def addItem(self, item):
        self.item_list.append(item)
        self.update()
    
    def count(self):
        return len(self.item_list)
    
    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None
    
    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None
    
    def setSpacing(self, spacing):
        self.spacing = spacing
        self.update()
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        return size
    
    def heightForWidth(self, width):
        """주어진 너비에 대해 필요한 높이 계산"""
        if not self.item_list:
            return 0
        
        x = 0
        y = 0
        line_height = 0
        
        for item in self.item_list:
            widget = item.widget()
            if widget is None:
                continue
                
            space_x = self.spacing
            space_y = self.spacing
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > width and line_height > 0:
                x = 0
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        
        return y + line_height
    
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)
    
    def doLayout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        
        for item in self.item_list:
            widget = item.widget()
            if widget is None:
                continue
                
            space_x = self.spacing
            space_y = self.spacing
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
    
    def get_drop_index(self, position):
        """주어진 위치에서 드롭할 인덱스를 계산"""
        print(f"get_drop_index 호출: position=({position.x()}, {position.y()})")
        print(f"item_list 개수: {len(self.item_list)}")
        
        # 컨테이너의 실제 크기 사용 (geometry가 0x0인 경우)
        container_width = self.parent().width() if self.parent() else 200
        print(f"컨테이너 폭: {container_width}")
        
        if not self.item_list:
            print("item_list가 비어있음, 인덱스 0 반환")
            return 0
        
        # 실제 아이템들의 위치를 정확하게 계산
        visible_items = []
        for i, item in enumerate(self.item_list):
            # 드래그 중인 아이템(플레이스홀더)은 건너뛰기
            if hasattr(item.widget(), 'is_placeholder') and item.widget().is_placeholder:
                print(f"아이템 {i}는 플레이스홀더, 건너뜀")
                continue
            visible_items.append((i, item))
        
        # 실제 레이아웃 계산
        x, y = 0, 0
        line_height = 0
        item_positions = []
        
        for original_index, item in visible_items:
            size_hint = item.sizeHint()
            next_x = x + size_hint.width() + self.spacing
            
            # 다음 줄로 넘어가야 하는지 확인 (실제 컨테이너 폭 사용)
            if next_x - self.spacing > container_width and len(item_positions) > 0:
                x = 0
                y += line_height + self.spacing
                line_height = 0
                next_x = x + size_hint.width() + self.spacing
            
            # 아이템의 경계 계산
            item_left = x
            item_right = x + size_hint.width()
            item_top = y
            item_bottom = y + size_hint.height()
            
            item_positions.append({
                'original_index': original_index,
                'left': item_left,
                'right': item_right,
                'top': item_top,
                'bottom': item_bottom,
                'center_x': x + size_hint.width() // 2
            })
            
            print(f"아이템 {original_index}: pos=({x}, {y}), size=({size_hint.width()}, {size_hint.height()})")
            print(f"  경계: left={item_left}, right={item_right}, top={item_top}, bottom={item_bottom}")
            
            x = next_x
            line_height = max(line_height, size_hint.height())
        
        # 드롭 위치와 가장 가까운 아이템 찾기
        for item_info in item_positions:
            # 드롭 위치가 이 아이템 영역 내에 있는지 확인
            if (item_info['left'] <= position.x() <= item_info['right'] and 
                item_info['top'] <= position.y() <= item_info['bottom']):
                
                print(f"  드롭 위치가 아이템 {item_info['original_index']} 영역 내에 있음")
                print(f"  중심점: {item_info['center_x']}, 드롭 X: {position.x()}")
                
                # 드롭 위치가 아이템의 왼쪽 절반이면 앞에 삽입
                if position.x() < item_info['center_x']:
                    print(f"  왼쪽 절반 -> 인덱스 {item_info['original_index']} 반환")
                    return item_info['original_index']
                # 드롭 위치가 아이템의 오른쪽 절반이면 뒤에 삽입
                else:
                    print(f"  오른쪽 절반 -> 인덱스 {item_info['original_index']+1} 반환")
                    return item_info['original_index'] + 1
        
        # 마지막 아이템 뒤에 드롭
        print(f"모든 아이템 영역 밖 -> 마지막 인덱스 {len(self.item_list)} 반환")
        return len(self.item_list)
    
    def move_widget(self, widget, new_index):
        """위젯을 새로운 인덱스로 이동"""
        # 현재 인덱스 찾기
        current_index = -1
        for i, item in enumerate(self.item_list):
            if item.widget() == widget:
                current_index = i
                break
        
        if current_index == -1:
            return False
        
        # 인덱스가 같으면 이동하지 않음
        if current_index == new_index:
            return False
        
        # 위젯을 레이아웃에서 제거
        self.removeWidget(widget)
        
        # 새로운 위치에 삽입
        if new_index >= len(self.item_list):
            self.addWidget(widget)
        else:
            self.insertWidget(new_index, widget)
        
        return True
    
    def insertWidget(self, index, widget):
        """위젯을 지정된 인덱스에 삽입"""
        if index < 0 or index > len(self.item_list):
            index = len(self.item_list)
        
        # QWidgetItem 생성 (QLayoutItem의 구체적인 구현체)
        item = QWidgetItem(widget)
        
        # 인덱스 위치에 삽입
        self.item_list.insert(index, item)
        
        # 레이아웃 갱신
        self.invalidate()


class PlaceholderWidget(QWidget):
    """드래그 앤 드롭 시 표시되는 플레이스홀더 위젯"""
    
    def __init__(self, size_hint, parent=None):
        super().__init__(parent)
        self.setFixedSize(size_hint)
        self.is_placeholder = True  # 플레이스홀더 식별용 속성
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(59, 130, 246, 0.1);
                border: 2px dashed rgba(59, 130, 246, 0.5);
                border-radius: 16px;
            }
        """)


class TagButton(QPushButton):
    """X 버튼이 있는 타원형 태그 버튼 - 드래그 앤 드롭 지원"""
    removed = Signal(str)
    drag_started = Signal(object)  # 드래그 시작 신호
    drag_ended = Signal(object, int)  # 드래그 종료 신호 (버튼, 새 인덱스)
    
    def __init__(self, tag_text, parent=None):
        super().__init__(parent)
        self.tag_text = tag_text
        # Display-only ellipsis for long tags (20+ chars)
        display_tag = (tag_text[:20] + "...") if isinstance(tag_text, str) and len(tag_text) > 20 else tag_text
        self.setText(f"{display_tag} ✕")
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.adjustSize()
        
        # 드래그 앤 드롭 관련 변수
        self.drag_start_position = None
        self.is_dragging = False
        self.drag_copy = None  # 드래그 중 마우스를 따라 움직이는 복사본
        
        # 타원형 디자인 스타일
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 16px;
                color: #93C5FD;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.25);
                border: 1px solid rgba(59, 130, 246, 0.5);
                color: #BFDBFE;
            }
            QPushButton:pressed {
                background-color: rgba(59, 130, 246, 0.35);
            }
        """)
        
        self.clicked.connect(lambda: self.removed.emit(self.tag_text))
    
    def mousePressEvent(self, event):
        """마우스 누름 이벤트 - 드래그 시작점 기록"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
            self.is_dragging = False
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트 - 드래그 시작 판단"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if self.drag_start_position is None:
            return
        
        # 드래그 시작 가드 강화: 마우스가 버튼 위에 있지 않으면 드래그 시작하지 않음
        if not self.underMouse():
            return
        
        # 드래그 거리 확인 (더 엄격한 조건)
        distance = (event.position().toPoint() - self.drag_start_position).manhattanLength()
        # 기본 드래그 거리의 3배 + 최소 20픽셀 이상 움직여야 드래그 시작
        min_drag_distance = max(QApplication.startDragDistance() * 3, 20)
        if distance >= min_drag_distance:
            if not self.is_dragging:
                self.start_drag()
            self.is_dragging = True
        
        # 드래그 중 복사본이 마우스를 따라 움직임
        if self.is_dragging and self.drag_copy:
            from PySide6.QtGui import QCursor
            global_mouse_pos = QCursor.pos()
            # 부모 윈도우 기준으로 위치 계산
            parent = self.drag_copy.parent()
            if parent:
                local_pos = parent.mapFromGlobal(global_mouse_pos)
                # 오프셋을 고려하여 복사본 위치 계산
                offset = self.drag_start_position
                new_pos = local_pos - offset
                self.drag_copy.move(new_pos)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """마우스 놓기 이벤트 - 드래그 종료"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging:
                self.end_drag()
                # 드래그가 있었다면 클릭 이벤트 무시
                event.ignore()
                return
            self.drag_start_position = None
            self.is_dragging = False
        super().mouseReleaseEvent(event)
    
    def start_drag(self):
        """드래그 시작 - 앱 내부 오버레이 방식"""
        # 원본 버튼을 반투명하게 만들기
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 16px;
                color: #93C5FD;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 16px;
            }
        """)
        
        # 부모 윈도우 찾기
        parent = self.window()
        if not parent:
            parent = self.parent()
        
        # 드래그용 복사본 생성 (앱 내부 오버레이)
        self.drag_copy = QPushButton(self.text(), parent)
        self.drag_copy.setFixedSize(self.size())
        self.drag_copy.setStyleSheet("""
            QPushButton {
                background-color: rgba(59, 130, 246, 0.3);
                border: 2px solid rgba(59, 130, 246, 0.8);
                border-radius: 16px;
                color: #93C5FD;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 16px;
            }
        """)
        
        # 마우스 이벤트를 투명하게 처리 (클릭 방지)
        self.drag_copy.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # 복사본을 반투명하게 설정
        self.drag_copy.setWindowOpacity(0.7)
        
        # 부모 윈도우 기준으로 위치 계산
        global_pos = self.mapToGlobal(QPoint(0, 0))
        local_pos = parent.mapFromGlobal(global_pos)
        self.drag_copy.move(local_pos)
        self.drag_copy.show()
        
        # 드래그 복사본이 생성되었음을 로그로 확인
        print(f"드래그 복사본 생성 (오버레이): {self.tag_text}")
        
        self.drag_started.emit(self)
    
    def end_drag(self):
        """드래그 종료"""
        # 복사본 제거 (더 안전한 방식)
        if self.drag_copy:
            print(f"드래그 복사본 제거: {self.tag_text}")
            try:
                self.drag_copy.hide()  # 먼저 숨기기
                self.drag_copy.deleteLater()
            except RuntimeError:
                # 이미 삭제된 경우 무시
                pass
            self.drag_copy = None
        
        # 원래 스타일로 복원
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 16px;
                color: #93C5FD;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.25);
                border: 1px solid rgba(59, 130, 246, 0.5);
                color: #BFDBFE;
            }
            QPushButton:pressed {
                background-color: rgba(59, 130, 246, 0.35);
            }
        """)
        
        # 새 인덱스는 FlowLayout에서 계산하여 전달
        self.drag_ended.emit(self, -1)  # -1은 아직 계산되지 않음을 의미


class TagStyleSheetEditor(QObject):
    """태그 스타일시트 에디터 관리자"""
    
    # 태그 변경 시그널
    tags_changed = Signal(list)  # 선택된 태그 목록이 변경될 때
    
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.selected_tags = []  # 선택된 태그들 (순서 보존)을 저장
        self.tag_buttons = {}  # 태그 버튼들을 저장
        self.image_grid_widget = None
        self.flow_layout = None
        self.tags_scroll_area = None
        self.tags_container = None
        self.search_mode = "OR"  # "OR" 또는 "AND" 모드
        self.grid_filter_enabled = False  # 이미지 그리드 필터링 활성화 여부
        
        # 카드 선택 관련 변수들
        self.card_selection_mode = False  # 카드 선택 모드 활성화 여부
        self.selected_cards = set()  # 선택된 카드들의 이미지 경로 저장
        self.image_frames = {}  # 이미지 경로 -> 프레임 위젯 매핑
        
        # 실시간 동기화를 위한 타이머
        self._grid_sync_timer = QTimer()
        self._grid_sync_timer.setInterval(400)  # 0.4초 간격(가볍고 충분)
        self._grid_sync_timer.timeout.connect(self._check_grid_sync)
        self._last_image_list_snapshot = tuple(getattr(self.app_instance, 'image_list', []) or [])
        
        # 실시간 업데이트를 위한 타이머
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.refresh_editor_content)
        
        # 드래그 앤 드롭 관련 변수
        self.dragged_button = None
        self.placeholder_widget = None
        self.original_button_index = -1
        
        # 썸네일 캐싱 시스템
        self.thumbnail_cache = {}  # Dict[path, QPixmap]
        self.thumbnail_mtime_cache = {}  # Dict[path, float] - 파일 수정 시간 캐시
        
        # 성능 최적화 설정 (제한 제거)
        # self.max_images_display = 30  # 제한 제거
        # self.thumbnail_size = 80  # 제한 제거
        
        # 세션 토큰 (닫았다 다시 열 때 이전 타이머 콜백 무효화용)
        self._session_token = 0
        self._loader_session_token = -1
        
        # 페이지네이션 상태
        self.items_per_page = 50
        self.current_page = 1
        self.total_pages = 0
        self.max_page_buttons = 10
        self._all_filtered_images = []
        self._pagination_initialized = False
        self.pagination_widget = None
        self.page_prev_btn = None
        self.page_next_btn = None
        self.page_buttons_layout = None
        self._page_number_buttons = []
        self.page_buttons_container = None
    
    def _normalize_image_path(self, image_path):
        """경로 값을 문자열로 정규화"""
        if isinstance(image_path, Path):
            return str(image_path)
        if isinstance(image_path, str):
            return image_path
        try:
            return str(image_path)
        except Exception:
            return ""
    
    def create_or_update_tag_edit_card(self, tag_text):
        """태그 편집 카드 생성 또는 업데이트 - 태그를 추가하는 방식"""
        print(f"create_or_update_tag_edit_card 호출: {tag_text}")
        print(f"현재 selected_tags: {self.selected_tags}")
        print(f"현재 tag_buttons: {list(self.tag_buttons.keys())}")
        
        # 이미 선택된 태그라면 무시
        if tag_text in self.selected_tags:
            print(f"태그 {tag_text}는 이미 선택됨")
            # 중복이어도 카드가 항상 맨앞으로 오도록 오버레이 호출
            if not hasattr(self.app_instance, 'tag_edit_card') or not self.app_instance.tag_edit_card:
                self.create_initial_card()
            else:
                from center_panel_overlay_plugin import CenterPanelOverlayPlugin
                overlay_plugin = CenterPanelOverlayPlugin(self.app_instance)
                overlay_plugin.show_overlay_card(self.app_instance.tag_edit_card, "tag_editor")
            return
        
        # 선택된 태그 추가 (중복 방지)
        if tag_text not in self.selected_tags:
            self.selected_tags.append(tag_text)
            print(f"선택된 태그에 추가: {tag_text}, 총 개수: {len(self.selected_tags)}")
        else:
            print(f"태그 {tag_text}는 이미 selected_tags에 존재함")
        
        # 카드가 없다면 새로 생성
        if not hasattr(self.app_instance, 'tag_edit_card') or not self.app_instance.tag_edit_card:
            print("카드가 없어서 새로 생성합니다")
            self.create_initial_card()
        else:
            print("기존 카드가 존재합니다")
            # 기존 카드가 있으면 오버레이 플러그인으로 사이즈만 조정
            from center_panel_overlay_plugin import CenterPanelOverlayPlugin
            overlay_plugin = CenterPanelOverlayPlugin(self.app_instance)
            overlay_plugin.show_overlay_card(self.app_instance.tag_edit_card, "tag_editor")
        
        # 태그 버튼 추가
        self.add_tag_button(tag_text)
        
        # 이미지 그리드 업데이트 (스로틀링 적용)
        self.schedule_update()
    
    def _restore_card_state(self):
        """기존 카드의 상태 복원"""
        print("🔄 기존 카드 상태 복원 시작")
        
        # 카드가 보이도록 설정
        if hasattr(self.app_instance, 'tag_edit_card') and self.app_instance.tag_edit_card:
            self.app_instance.tag_edit_card.show()
            print("✅ 카드 표시 완료")
        else:
            print("❌ 카드가 존재하지 않음")
            return
        
        # 현재 상태 확인
        print(f"🔍 현재 상태 확인:")
        print(f"  - selected_tags: {len(self.selected_tags)}개 - {self.selected_tags}")
        print(f"  - grid_filter_enabled: {self.grid_filter_enabled}")
        print(f"  - image_frames: {len(self.image_frames)}개")
        print(f"  - image_grid_widget 존재: {hasattr(self, 'image_grid_widget') and self.image_grid_widget is not None}")
        
        # 검색 결과 연동 상태 복원
        if hasattr(self, 'grid_filter_checkbox'):
            current_sync_state = self.grid_filter_checkbox.isChecked()
            print(f"  - UI 체크박스 상태: {current_sync_state}")
            if current_sync_state != self.grid_filter_enabled:
                print(f"🔄 검색 결과 연동 상태 복원: {current_sync_state}")
                self.grid_filter_enabled = current_sync_state
                if current_sync_state:
                    self._grid_sync_timer.start()
                    self._last_image_list_snapshot = tuple(getattr(self.app_instance, 'image_list', []) or [])
                    print("✅ 검색 결과 연동 타이머 시작")
                else:
                    self._grid_sync_timer.stop()
                    print("✅ 검색 결과 연동 타이머 중지")
        
        # 이미지 그리드 상태 복원
        if self.selected_tags:
            print(f"🔄 선택된 태그로 이미지 그리드 복원: {len(self.selected_tags)}개")
            
            # image_grid_widget이 없으면 새로 생성
            if not hasattr(self, 'image_grid_widget') or not self.image_grid_widget:
                print("⚠️ image_grid_widget이 없음 - 새로 생성")
                # 빈 그리드 위젯 생성
                grid_widget = QWidget()
                grid_widget.setStyleSheet("background-color: transparent;")
                grid_layout = QGridLayout(grid_widget)
                grid_layout.setSpacing(6)
                grid_layout.setContentsMargins(6, 6, 6, 6)
                grid_layout.setAlignment(Qt.AlignTop)
                
                try:
                    self.image_scroll_area.setWidget(grid_widget)
                    self.image_grid_widget = grid_widget
                    print("✅ 새로운 image_grid_widget 생성 완료")
                except RuntimeError as e:
                    print(f"❌ RuntimeError 발생 (위젯 삭제됨) in _restore_card_state: {e}")
                    return
            
            # 즉시 업데이트 (스로틀링 없이)
            self.update_image_grid()
        else:
            print("⚠️ 선택된 태그가 없음 - 빈 그리드 표시")
            try:
                if hasattr(self, 'grid_header_label'):
                    self.grid_header_label.setText("Select tags to view images")
                if hasattr(self, 'image_scroll_area'):
                    empty_widget = QWidget()
                    empty_widget.setStyleSheet("background-color: transparent;")
                    self.image_scroll_area.setWidget(empty_widget)
                self.image_frames.clear()
                print("✅ 빈 그리드 설정 완료")
            except RuntimeError as e:
                print(f"❌ RuntimeError 발생 (위젯 삭제됨) in _restore_card_state: {e}")
        
        print("✅ 기존 카드 상태 복원 완료")
    
    def create_initial_card(self):
        """초기 카드 생성"""
        print("create_initial_card 시작")
        
        # 기존 태그 편집 카드가 있다면 재생성하지 않고 상태만 복원
        if hasattr(self.app_instance, 'tag_edit_card') and self.app_instance.tag_edit_card:
            print("기존 카드가 존재함 - 재생성하지 않고 상태만 복원")
            # 기존 카드의 상태 복원
            self._restore_card_state()
            return
        
        # 새로운 태그 스타일시트 에디터 카드 생성
        from tag_statistics_module import SectionCard
        self.app_instance.tag_edit_card = SectionCard("TAG STYLESHEET EDITOR")
        print("새 카드 생성 완료")
        
        # 카드가 전체 영역을 덮도록 설정 (높이 제약 완화)
        self.app_instance.tag_edit_card.setMinimumHeight(0)  # 최소 높이 제거
        self.app_instance.tag_edit_card.setMaximumHeight(16777215)
        self.app_instance.tag_edit_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 카드 외부 마진(14px) 적용 및 고급 검색과 동일한 버튼 스타일
        self.app_instance.tag_edit_card.setStyleSheet("""
            QFrame#SectionCard {
                background: rgba(17,17,27,0.9);
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 6px;
                margin: 14px;
            }
            QPushButton {
                background: rgba(17,17,27,1);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                color: #F0F2F5;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(17,17,27,1);
                border-color: rgba(75,85,99,0.5);
            }
            QPushButton#searchBtn {
                background: white;
                color: black;
                border: none;
                padding: 8px 24px;
            }
            QPushButton#searchBtn:hover {
                background: white;
            }
        """)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 고급 검색과 동일한 여백
        
        # 상단 설명 라벨
        desc_label = QLabel("Select tags to edit their styles. Images with any of the selected tags will be displayed.")
        desc_label.setStyleSheet("color: #9CA3AF; font-size: 13px; margin-bottom: 10px;")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # 선택된 태그들을 표시할 Flow Layout 영역
        self.tags_container = QWidget()
        self.tags_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.tags_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
        """)
        
        # Flow Layout 생성
        self.flow_layout = FlowLayout()
        self.flow_layout.setSpacing(8)
        self.flow_layout.setContentsMargins(8, 8, 8, 8)
        self.tags_container.setLayout(self.flow_layout)
        # 선택 태그 없음 안내 라벨
        self.no_tags_hint_label = QLabel("선택된 태그가 없으므로 검색된 이미지를 불러옵니다")
        self.no_tags_hint_label.setStyleSheet("color: #9CA3AF; font-size: 12px; margin: 4px 12px;")
        self.no_tags_hint_label.setAlignment(Qt.AlignCenter)
        self.no_tags_hint_label.setVisible(False)
        # FlowLayout 위에 오버레이처럼 보이도록 컨테이너 상단에 추가
        # 간단히 수직 레이아웃을 감싸지 않고, 스크롤 위젯 상단에 별도 라벨을 두기 위해 아래에서 tags_scroll_area 위에 배치
        print(f"FlowLayout 생성 완료: {self.flow_layout}")
        
        # 태그 컨테이너를 스크롤 가능하게 만들기
        self.tags_scroll_area = QScrollArea()
        self.tags_scroll_area.setWidget(self.tags_container)
        self.tags_scroll_area.setWidgetResizable(True)  # 내용 위젯이 뷰포트 폭을 받게
        self.tags_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 가로 스크롤 항상 끄기
        self.tags_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # 세로 스크롤 필요시만
        self.tags_scroll_area.setMinimumHeight(0)  # 최소 높이 제거
        # self.tags_scroll_area.setMaximumHeight(200)  # 최대 높이 제한 제거
        self.tags_scroll_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)  # 가로는 Preferred, 세로는 Fixed
        self.tags_scroll_area.setSizeAdjustPolicy(QScrollArea.SizeAdjustPolicy.AdjustIgnored)  # 내용 폭에 맞춰 스크롤 영역 자체가 커지지 않게
        self.tags_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
        """)
        
        # 컨테이너와 스크롤 뷰포트 크기 변화 감지
        self.tags_container.installEventFilter(self)
        self.tags_scroll_area.viewport().installEventFilter(self)
        
        # 태그 스크롤 + 안내 라벨 컨테이너
        tags_block = QVBoxLayout()
        tags_block.setContentsMargins(0, 0, 0, 0)
        tags_block.setSpacing(0)
        tags_block.addWidget(self.no_tags_hint_label)
        container_for_tags = QWidget()
        container_for_tags.setLayout(tags_block)
        # 스크롤 영역을 라벨 아래에 추가
        tags_block.addWidget(self.tags_scroll_area)
        main_layout.addWidget(container_for_tags)
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); margin: 10px 0;")
        separator.setFixedHeight(1)
        main_layout.addWidget(separator)
        
        # 이미지 그리드 헤더 (AND/OR 모드 선택 포함)
        header_layout = QHBoxLayout()
        
        self.grid_header_label = QLabel("Select tags to view images")
        self.grid_header_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; margin: 10px 0;")
        self.grid_header_label.setWordWrap(True)  # 줄바꿈 허용
        self.grid_header_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)  # 가로 확장 방지
        
        # 이미지 검색 결과 연동 체크박스 (커스텀 체크박스 적용)
        class CustomCheckBox(QCheckBox):
            def __init__(self, text="", parent=None):
                super().__init__(text, parent)
                self.setStyleSheet("""
                    QCheckBox {
                        color: #FFFFFF;
                        font-size: 12px;
                        spacing: 6px;
                    }
                    /* locked 상태(무태그 시 클릭만 비활성) - 비활성 색상 적용 */
                    QCheckBox[locked="true"] {
                        color: #6B7280;
                    }
                    QCheckBox::indicator {
                        width: 14px;
                        height: 14px;
                        border-radius: 2px;
                        border: 1px solid rgba(255, 255, 255, 0.8);
                        background: rgba(17, 17, 27, 0.9);
                    }
                    QCheckBox::indicator[locked="true"] {
                        border: 1px solid rgba(75,85,99,0.2);
                        background: rgba(26,27,38,0.4);
                    }
                    QCheckBox::indicator:checked {
                        background: rgba(17, 17, 27, 0.9);
                        border: 1px solid rgba(255, 255, 255, 0.8);
                        image: none;
                    }
                    QCheckBox::indicator:checked[locked="true"] {
                        border: 1px solid rgba(75,85,99,0.2);
                        background: rgba(26,27,38,0.4);
                    }
                    QCheckBox::indicator:hover {
                        border: 1px solid rgba(255, 255, 255, 1.0);
                    }
                    QCheckBox::indicator:hover[locked="true"] {
                        border: 1px solid rgba(75,85,99,0.2);
                    }
                    QCheckBox:disabled {
                        color: #6B7280;
                    }
                    QCheckBox::indicator:disabled {
                        border: 1px solid rgba(75,85,99,0.2);
                        background: rgba(26,27,38,0.4);
                    }
                """)
            
            def paintEvent(self, event):
                super().paintEvent(event)
                if self.isChecked():
                    painter = QPainter(self)
                    painter.setRenderHint(QPainter.Antialiasing)
                    # locked 또는 disabled일 때 체크표시는 비활성 색으로
                    is_locked = bool(self.property("locked"))
                    check_color = QColor("#FFFFFF") if (self.isEnabled() and not is_locked) else QColor("#6B7280")
                    painter.setPen(QPen(check_color, 2))
                    painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
                    rect = self.rect()
                    indicator_rect = QRect(1, (rect.height() - 14) // 2, 14, 14)
                    painter.drawText(indicator_rect, Qt.AlignCenter, "🗸")

        self.grid_filter_checkbox = CustomCheckBox("이미지 검색 결과 연동")
        self.grid_filter_checkbox.setChecked(False)
        # 기본은 잠금 해제 상태
        try:
            self.grid_filter_checkbox.setProperty("locked", False)
        except Exception:
            pass
        self.grid_filter_checkbox.toggled.connect(self.on_search_result_sync_toggled)
        
        # AND/OR 모드 선택 드롭다운
        self.mode_combo = CustomComboBox()
        self.mode_combo.addItems(["OR", "AND"])
        self.mode_combo.setCurrentText("OR")
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                color: white;
                font-family: 'Segoe UI';
                font-size: 12px;
                min-width: 80px;
            }
            QComboBox:hover {
                background: rgba(26,27,38,0.85);
                border: 1px solid rgba(75,85,99,0.5);
            }
            QComboBox:disabled {
                background: rgba(26,27,38,0.4);
                border: 1px solid rgba(75,85,99,0.2);
                color: #6B7280;
            }
            QComboBox::drop-down {
                border: none;
                width: 0px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background: rgba(26,27,38,0.95);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                color: white;
                selection-background-color: #3B82F6;
            }
            QComboBox:focus {
                border: 2px solid #3B82F6;
            }
        """)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        # 첫 번째 행: 체크박스와 모드 드롭다운
        header_layout.addWidget(self.grid_filter_checkbox)
        header_layout.addStretch()
        header_layout.addWidget(self.mode_combo)
        
        main_layout.addLayout(header_layout)
        
        # 두 번째 행: 헤더 라벨 (별도 행)
        header_label_layout = QHBoxLayout()
        header_label_layout.addWidget(self.grid_header_label)
        header_label_layout.addStretch()
        main_layout.addLayout(header_label_layout)
        
        # 이미지 그리드를 위한 스크롤 영역
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setWidgetResizable(True)
        self.image_scroll_area.setMinimumHeight(0)  # 최소 높이 제거
        self.image_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
        """)
        
        # 초기 빈 위젯
        empty_widget = QWidget()
        empty_widget.setStyleSheet("background-color: transparent;")
        self.image_scroll_area.setWidget(empty_widget)
        
        main_layout.addWidget(self.image_scroll_area)
        
        # 페이지네이션 바 추가
        self._build_pagination_bar(main_layout)
        
        # 버튼 영역 (이미지 그리드 아래로 이동)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 닫기 버튼 (맨 왼쪽) - 고급 검색과 동일한 스타일
        close_btn = QPushButton("Close Editor")
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(17,17,27,1);
                border: 1px solid rgba(75,85,99,0.3);
                color: #F0F2F5;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(17,17,27,1);
                border-color: rgba(75,85,99,0.5);
                color: #F9FAFB;
            }
            QPushButton:pressed {
                background: rgba(17,17,27,1);
                border-color: rgba(75,85,99,0.7);
            }
        """)
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.cancel_tag_edit)
        button_layout.addWidget(close_btn)
        
        button_layout.addStretch()
        
        # 모두 선택 해제 버튼 - 고급 검색과 동일한 스타일
        clear_all_btn = QPushButton("Clear All Tags")
        clear_all_btn.setMinimumWidth(100)
        clear_all_btn.setCursor(Qt.PointingHandCursor)
        clear_all_btn.clicked.connect(self.clear_all_tags)
        button_layout.addWidget(clear_all_btn)
        
        # 카드 선택 모드 토글 버튼 (기존 Apply Style 버튼 대체)
        self.card_selection_btn = QPushButton("카드 선택 모드")
        self.card_selection_btn.setObjectName("cardSelectionBtn")
        self.card_selection_btn.setCheckable(True)
        self.card_selection_btn.setChecked(False)
        self.card_selection_btn.setMinimumWidth(100)
        self.card_selection_btn.setCursor(Qt.PointingHandCursor)
        self.card_selection_btn.toggled.connect(self.on_card_selection_mode_toggled)
        
        # 버튼 스타일 적용
        self.card_selection_btn.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
            }
            QPushButton:pressed {
                background: #2D3748;
                border-color: #2D3748;
                color: #CBD5E0;
            }
            QPushButton:checked {
                background: #2D3748;
                border-color: #2D3748;
                color: #CBD5E0;
            }
        """)
        
        button_layout.addWidget(self.card_selection_btn)
        
        main_layout.addLayout(button_layout)
        
        # 카드에 내용 추가
        self.app_instance.tag_edit_card.body.addLayout(main_layout)
        
        # 오버레이 플러그인 사용
        from center_panel_overlay_plugin import CenterPanelOverlayPlugin
        overlay_plugin = CenterPanelOverlayPlugin(self.app_instance)
        overlay_plugin.show_overlay_card(self.app_instance.tag_edit_card, "tag_editor")
    
        # 초기 높이 조정 - 카드가 화면에 붙은 다음 프레임에 실행
        QTimer.singleShot(0, self.update_tags_container_height)
    
    def _build_pagination_bar(self, parent_layout):
        """번호형 페이지네이션 UI 구성"""
        if self.pagination_widget:
            parent_layout.addWidget(self.pagination_widget)
            return
        
        self.pagination_widget = QWidget()
        self.pagination_widget.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QPushButton {
                background: transparent;
                border: 1px solid rgba(75,85,99,0.3);
                color: #F0F2F5;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: rgba(75,85,99,0.5);
            }
            QPushButton:disabled {
                background: transparent;
                border-color: rgba(75,85,99,0.3);
                color: #F0F2F5;
            }
            QPushButton[current='true'] {
                background: #3B82F6;
                border: 1px solid #3B82F6;
                color: #F9FAFB;
            }
        """)
        pagination_layout = QHBoxLayout(self.pagination_widget)
        pagination_layout.setContentsMargins(0, 8, 0, 8)
        pagination_layout.setSpacing(10)  # 화살표와 숫자 사이 간격 10px
        
        pagination_layout.addStretch()
        
        self.page_prev_btn = QPushButton("❮")
        self.page_prev_btn.setCursor(Qt.PointingHandCursor)
        self.page_prev_btn.clicked.connect(self._on_prev_page_clicked)
        pagination_layout.addWidget(self.page_prev_btn)
        
        self.page_buttons_container = QWidget()
        self.page_buttons_layout = QHBoxLayout(self.page_buttons_container)
        self.page_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.page_buttons_layout.setSpacing(10)  # 숫자와 숫자 사이 간격 10px
        self.page_buttons_layout.addStretch()
        pagination_layout.addWidget(self.page_buttons_container)
        
        self.page_next_btn = QPushButton("❯")
        self.page_next_btn.setCursor(Qt.PointingHandCursor)
        self.page_next_btn.clicked.connect(self._on_next_page_clicked)
        pagination_layout.addWidget(self.page_next_btn)
        
        pagination_layout.addStretch()
        
        self.pagination_widget.setVisible(False)
        parent_layout.addWidget(self.pagination_widget)

    def _update_pagination_ui(self, total_items):
        """페이지네이션 UI 갱신"""
        if not self.pagination_widget or not self.page_prev_btn or not self.page_next_btn:
            return
        
        if total_items == 0 or self.total_pages <= 1:
            self.pagination_widget.setVisible(False)
            self.page_prev_btn.setEnabled(False)
            self.page_next_btn.setEnabled(False)
            self._refresh_page_number_buttons([])
            return
        
        self.pagination_widget.setVisible(True)
        self.page_prev_btn.setEnabled(self.current_page > 1)
        self.page_next_btn.setEnabled(self.current_page < self.total_pages)
        
        window_size = self.max_page_buttons
        start_page = max(1, self.current_page - window_size // 2)
        end_page = start_page + window_size - 1
        if end_page > self.total_pages:
            end_page = self.total_pages
            start_page = max(1, end_page - window_size + 1)
        
        page_range = list(range(start_page, end_page + 1))
        self._refresh_page_number_buttons(page_range)

    def _refresh_page_number_buttons(self, page_range):
        if not self.page_buttons_layout:
            return
        
        while self.page_buttons_layout.count():
            item = self.page_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        self._page_number_buttons = []
        self.page_buttons_layout.addStretch()
        
        for page in page_range:
            btn = QPushButton(str(page))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, p=page: self._on_page_button_clicked(p))
            btn.setProperty("current", "true" if page == self.current_page else "false")
            style = btn.style()
            style.unpolish(btn)
            style.polish(btn)
            btn.update()
            self.page_buttons_layout.addWidget(btn)
            self._page_number_buttons.append(btn)
        
        self.page_buttons_layout.addStretch()

    def _on_prev_page_clicked(self):
        self._set_page(self.current_page - 1)

    def _on_next_page_clicked(self):
        self._set_page(self.current_page + 1)

    def _on_page_button_clicked(self, page):
        self._set_page(page)

    def _set_page(self, page):
        if not self._all_filtered_images or self.total_pages == 0:
            return
        page = max(1, min(page, self.total_pages))
        if page == self.current_page:
            return
        
        # 페이지 전환 시 진행 중인 비동기 로딩 작업 모두 중단
        self._cancel_all_loading_tasks()
        
        self.current_page = page
        self._render_current_page()
    
    def _cancel_all_loading_tasks(self):
        """진행 중인 모든 비동기 로딩 작업 중단"""
        # 세션 토큰 증가로 이전 콜백들이 무시되도록 함
        self._session_token += 1
        print(f"🛑 페이지 전환: 모든 로딩 작업 중단 (세션 토큰: {self._session_token})")
        
        # 진행 중인 로딩 인덱스 초기화
        for attr in [
            '_current_loading_index',
            '_additional_loading_index',
            '_checkbox_loading_index',
            '_selected_loading_index'
        ]:
            if hasattr(self, attr):
                delattr(self, attr)
        
        # 로딩 경로 및 레이아웃 참조 정리
        for attr in [
            '_image_paths_to_load',
            '_additional_image_paths',
            '_checkbox_image_paths',
            '_selected_image_paths',
            '_grid_layout',
            '_checkbox_grid_layout',
            '_additional_grid_layout',
            '_selected_grid_layout',
            '_additional_start_count'
        ]:
            if hasattr(self, attr):
                delattr(self, attr)
        
        # 로더 세션 토큰도 무효화
        self._loader_session_token = -1
        
        # 기존 이미지 프레임들 정리 (팝업 방지)
        # 주의: _render_current_page에서도 정리하지만, 여기서 먼저 정리하여 
        # 이전 페이지의 프레임들이 새 페이지 로딩 중에 팝업되는 것을 방지
        for image_path, frame in list(self.image_frames.items()):
            try:
                if frame and hasattr(frame, 'deleteLater'):
                    frame.hide()
                    frame.deleteLater()
            except RuntimeError:
                pass
        self.image_frames.clear()

    def _prepare_paginated_images(self, tagged_images=None, reset_page=False):
        """필터된 전체 목록을 저장하고 현재 페이지 이미지를 반환"""
        if tagged_images is not None:
            normalized = {self._normalize_image_path(p) for p in tagged_images if self._normalize_image_path(p)}
            self._all_filtered_images = sorted(normalized)
            if reset_page or not self._pagination_initialized:
                self.current_page = 1
            self._pagination_initialized = True
        
        images_list = self._all_filtered_images or []
        total_items = len(images_list)
        
        if total_items == 0:
            self.total_pages = 0
            self.current_page = 1
            self._update_pagination_ui(total_items)
            return [], total_items
        
        self.total_pages = math.ceil(total_items / self.items_per_page)
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        if self.current_page < 1:
            self.current_page = 1
        
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_list = images_list[start_idx:end_idx]
        
        self._update_pagination_ui(total_items)
        return page_list, total_items
    
    def _update_header_label(self, total_items):
        if not hasattr(self, 'grid_header_label') or not self.grid_header_label:
            return
        
        if total_items == 0:
            text = "No images found with selected tags" if self.selected_tags else "Select tags to view images"
        else:
            if self.total_pages > 1:
                text = f"Found {total_items} images (Page {self.current_page}/{self.total_pages})"
            else:
                text = f"Found {total_items} images"
        try:
            self.grid_header_label.setText(text)
            self.grid_header_label.setWordWrap(True)
        except RuntimeError:
            pass
    
    def _render_current_page(self):
        # 페이지 렌더링 전에 기존 이미지 프레임들 정리 (팝업 방지)
        self._cleanup_existing_image_frames()
        
        if self.card_selection_mode:
            self.show_tagged_images_with_checkboxes(reset_page=False)
            return
        
        page_images, total_items = self._prepare_paginated_images(None, reset_page=False)
        self._update_header_label(total_items)
        self._render_standard_page(page_images)
    
    def _render_standard_page(self, page_images):
        target_set = set(page_images)
        try:
            self._update_grid_with_diff(target_set)
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _render_standard_page: {e}")
    
    def add_tag_button(self, tag_text):
        """태그 버튼 추가"""
        print(f"add_tag_button 호출: {tag_text}")
        print(f"flow_layout 존재: {self.flow_layout is not None}")
        
        if tag_text in self.tag_buttons:
            print(f"태그 {tag_text}는 이미 존재함")
            return
        
        # 타원형 태그 버튼 생성
        tag_btn = TagButton(tag_text)
        tag_btn.removed.connect(self.remove_tag)
        tag_btn.drag_started.connect(self.on_drag_started)
        tag_btn.drag_ended.connect(self.on_drag_ended)
        print(f"TagButton 생성 완료: {tag_text}")
        
        # FlowLayout에 추가
        if self.flow_layout:
            self.flow_layout.addWidget(tag_btn)
            print(f"FlowLayout에 태그 버튼 추가 완료: {tag_text}")
            
            # 레이아웃 강제 갱신
            self.flow_layout.invalidate()
            self.tags_container.updateGeometry()
            
        else:
            print("ERROR: flow_layout이 None입니다!")
            return
        
        self.tag_buttons[tag_text] = tag_btn
        # selected_tags에 추가 (중복 방지)
        if tag_text not in self.selected_tags:
            self.selected_tags.append(tag_text)
        print(f"tag_buttons에 추가: {tag_text}, 총 개수: {len(self.tag_buttons)}")
        
        # 높이 자동 조정 (두 번 호출로 확실히)
        self.update_tags_container_height()
        QTimer.singleShot(0, self.update_tags_container_height)
        
        # 태그 변경 시그널 발생
        self.tags_changed.emit(self.selected_tags.copy())
    
    def remove_tag(self, tag_text):
        """태그 제거"""
        print(f"remove_tag 호출: {tag_text}")
        print(f"삭제 전 selected_tags: {self.selected_tags}")
        
        if tag_text in self.selected_tags:
            # 모든 인스턴스 제거 (중복이 있을 수 있으므로)
            while tag_text in self.selected_tags:
                self.selected_tags.remove(tag_text)
            print(f"selected_tags에서 제거됨: {tag_text}")
        else:
            print(f"selected_tags에 {tag_text}가 없음")
        
        if tag_text in self.tag_buttons:
            btn = self.tag_buttons[tag_text]
            btn.deleteLater()
            del self.tag_buttons[tag_text]
            print(f"tag_buttons에서 제거됨: {tag_text}")
        else:
            print(f"tag_buttons에 {tag_text}가 없음")
        
        print(f"삭제 후 selected_tags: {self.selected_tags}")
        
        # 드래그 앤 드롭 상태 초기화 (삭제된 태그가 드래그 중이었다면)
        if self.dragged_button and self.dragged_button.tag_text == tag_text:
            self.dragged_button = None
            self.original_button_index = -1
            if self.placeholder_widget:
                self.placeholder_widget.deleteLater()
                self.placeholder_widget = None
        
        # 이미지 그리드 업데이트 (스로틀링 적용)
        self.schedule_update()
        
        # 높이 자동 조정
        self.update_tags_container_height()
        
        # 태그 변경 시그널 발생
        self.tags_changed.emit(self.selected_tags.copy())
    
    def on_mode_changed(self, mode):
        """AND/OR 모드 변경 시 호출"""
        self.search_mode = mode
        print(f"검색 모드 변경: {mode}")
        # 이미지 그리드 업데이트 (스로틀링 적용)
        self.schedule_update()
    
    def _check_grid_sync(self):
        """이미지 그리드(왼쪽)의 현재 목록 변화를 감지해서 에디터를 동기화"""
        if not self.grid_filter_enabled:
            return
        current = tuple(getattr(self.app_instance, 'image_list', []) or [])
        if current != self._last_image_list_snapshot:
            self._last_image_list_snapshot = current
            print(f"이미지 그리드 변화 감지 - 에디터 동기화: {len(current)}개 이미지")
            # 그리드 대상이 바뀌었으니 에디터도 재계산 (스로틀링 적용)
            self.schedule_update()
    
    def on_search_result_sync_toggled(self, checked):
        """이미지 검색 결과 연동 체크박스 토글"""
        self.grid_filter_enabled = checked
        print(f"이미지 검색 결과 연동: {'활성화' if checked else '비활성화'}")
        
        # 스냅샷 초기화 + 타이머 제어
        self._last_image_list_snapshot = tuple(getattr(self.app_instance, 'image_list', []) or [])
        if checked:
            self._grid_sync_timer.start()
            print("실시간 동기화 타이머 시작")
        else:
            self._grid_sync_timer.stop()
            print("실시간 동기화 타이머 중지")
        
        # 즉시 1회 반영 (스로틀링 적용)
        self.schedule_update()
    
    def on_card_selection_mode_toggled(self, checked):
        """카드 선택 모드 토글"""
        # 선택 모드 전환 로그
        print(f"카드 선택 모드: {'활성화' if checked else '비활성화'}")

        if checked:
            # 선택 모드 활성화
            self.card_selection_mode = True
            self.card_selection_btn.setText("선택 모드 종료")
            # 태그 기준으로 필터링된 이미지들을 체크박스와 함께 표시
            self.show_tagged_images_with_checkboxes(reset_page=True)
        else:
            # 선택 모드 종료
            self.card_selection_mode = False
            self.card_selection_btn.setText("카드 선택 모드")
            
            # 선택 모드 종료 시 selected_cards를 새로운 태그 기준으로 필터링
            if hasattr(self, 'selected_cards') and self.selected_cards:
                print(f"선택 모드 종료 전 selected_cards: {len(self.selected_cards)}개")
                
                # 현재 선택된 태그들로 필터링된 이미지 집합 계산
                filtered_images = self._get_current_filtered_images()
                
                # selected_cards에서 새로운 태그 기준으로 매칭되지 않는 이미지들 제거
                original_selected_count = len(self.selected_cards)
                self.selected_cards = self.selected_cards.intersection(filtered_images)
                
                print(f"선택 모드 종료 후 selected_cards: {original_selected_count}개 -> {len(self.selected_cards)}개")
                
                # 매칭 결과가 0이면 selected_cards 완전 정리
                if not filtered_images:
                    print("⚠️ 선택 모드 종료 시 매칭 결과가 0개이므로 selected_cards 정리")
                    self.selected_cards.clear()
            
            # 선택된 카드만 새 그리드로 재배치(빈 칸 없이)
            self.display_selected_cards_only()

        # 모든 이미지 프레임의 체크박스 표시/숨김 업데이트
        self.update_card_checkboxes_visibility()

    
    def update_card_checkboxes_visibility(self):
        """모든 이미지 프레임의 체크박스 표시/숨김 업데이트"""
        # 삭제된 프레임들을 정리하기 위한 리스트
        frames_to_remove = []
        
        for image_path, frame in self.image_frames.items():
            try:
                if hasattr(frame, 'card_checkbox') and frame.card_checkbox is not None:
                    frame.card_checkbox.setVisible(self.card_selection_mode)
            except RuntimeError:
                # C++ 객체가 이미 삭제된 경우
                print(f"삭제된 프레임 발견: {image_path}")
                frames_to_remove.append(image_path)
        
        # 삭제된 프레임들을 image_frames에서 제거
        for image_path in frames_to_remove:
            self.image_frames.pop(image_path, None)
    
    def filter_to_selected_cards(self):
        """선택된 카드들만 표시하도록 필터링"""
        if not self.selected_cards:
            print("선택된 카드가 없음")
            return
        
        print(f"선택된 카드들만 표시: {len(self.selected_cards)}개")
        
        # 현재 그리드 위젯에서 선택된 카드들만 표시
        if self.image_grid_widget:
            grid_layout = self.image_grid_widget.layout()
            if grid_layout:
                # 모든 위젯 숨기기
                for i in range(grid_layout.count()):
                    item = grid_layout.itemAt(i)
                    if item and item.widget():
                        item.widget().hide()
                
                # 선택된 카드들만 표시하고 나머지는 숨기기
                for image_path, frame in self.image_frames.items():
                    if image_path in self.selected_cards:
                        frame.show()
                    else:
                        frame.hide()
                
                # 그리드 재정렬 (구멍 제거)
                self._rearrange_grid_layout()
                
                # 헤더 업데이트
                self.grid_header_label.setText(f"Selected {len(self.selected_cards)} cards")
    
    def show_all_images(self):
        """모든 이미지를 다시 표시 (카드 선택 모드 활성화 시)"""
        print("모든 이미지 다시 표시")
        
        # 현재 그리드 위젯에서 모든 위젯 표시
        if self.image_grid_widget:
            grid_layout = self.image_grid_widget.layout()
            if grid_layout:
                # 모든 위젯 표시
                for i in range(grid_layout.count()):
                    item = grid_layout.itemAt(i)
                    if item and item.widget():
                        item.widget().show()
                
                # 그리드 재정렬 (구멍 제거)
                self._rearrange_grid_layout()
                
                # 헤더 업데이트 (원래 태그 기반 필터링 결과로 복원)
                if self.selected_tags:
                    # 태그 기반 필터링 결과 개수 계산
                    tagged_images = set()
                    if hasattr(self.app_instance, 'all_tags'):
                        search_target_images = None
                        if self.grid_filter_enabled and hasattr(self.app_instance, 'image_list') and self.app_instance.image_list:
                            search_target_images = set(self.app_instance.image_list)
                        
                        for image_path, tags in self.app_instance.all_tags.items():
                            if search_target_images and image_path not in search_target_images:
                                continue
                                
                            if self.search_mode == "OR":
                                if any(tag in tags for tag in self.selected_tags):
                                    tagged_images.add(image_path)
                            else:  # AND 모드
                                if all(tag in tags for tag in self.selected_tags):
                                    tagged_images.add(image_path)
                    
                    self.grid_header_label.setText(f"Found {len(tagged_images)} images")
                else:
                    self.grid_header_label.setText("Select tags to view images")
    
    def on_card_checkbox_toggled(self, image_path, checked):
        """카드 체크박스 토글 처리"""
        if checked:
            self.selected_cards.add(image_path)
        else:
            self.selected_cards.discard(image_path)
        
        print(f"카드 선택 상태 변경: {image_path} -> {'선택' if checked else '해제'}, 총 선택: {len(self.selected_cards)}개")
    
    def clear_all_tags(self):
        """모든 태그 선택 해제"""
        # 모든 태그 버튼 제거
        for tag_text in list(self.tag_buttons.keys()):
            self.remove_tag(tag_text)
        
        self.selected_tags.clear()
        self.schedule_update()
        
        # 높이 자동 조정
        self.update_tags_container_height()

    def _get_current_filtered_images(self):
        """현재 UI 상태(선택된 태그, AND/OR, 검색 결과 연동)에 맞는 이미지 집합을 계산한다.
        선택된 태그가 없으면 전체 집합을 반환한다(연동 시에는 현재 검색 결과 집합, 비연동 시에는 전체 이미지).
        """
        # 선택된 태그가 없으면 전체 집합 반환 (연동 여부에 따라 대상 결정)
        if not self.selected_tags:
            # 연동 켜짐: 현재 검색 결과(image_list)를 그대로 사용 (비어있으면 0 유지)
            if self.grid_filter_enabled and hasattr(self.app_instance, 'image_list'):
                return set(self.app_instance.image_list or [])
            # 연동 꺼짐: 전체 이미지
            if hasattr(self.app_instance, 'all_tags') and isinstance(self.app_instance.all_tags, dict):
                return set(self.app_instance.all_tags.keys())
            if hasattr(self.app_instance, 'image_files'):
                return set(self.app_instance.image_files or [])
            return set()
        
        tagged_images = set()
        if hasattr(self.app_instance, 'all_tags'):
            # 검색 결과 연동이 켜져 있으면 해당 그리드의 전체 필터 목록을 우선 사용
            search_target_images = None
            if self.grid_filter_enabled:
                if hasattr(self.app_instance, 'image_filtered_list') and self.app_instance.image_filtered_list:
                    search_target_images = {
                        self._normalize_image_path(p) for p in self.app_instance.image_filtered_list
                    }
                    print(f"🔍 검색 결과 연동 활성화(image_filtered_list): {len(search_target_images)}개 이미지 대상으로 필터링")
                elif hasattr(self.app_instance, 'image_list') and self.app_instance.image_list:
                    search_target_images = {
                        self._normalize_image_path(p) for p in self.app_instance.image_list
                    }
                    print(f"🔍 검색 결과 연동 활성화(image_list): {len(search_target_images)}개 이미지 대상으로 필터링")
                else:
                    search_target_images = set()
                    print("🔍 검색 결과 연동 활성화: 대상 이미지가 없음")
            else:
                print("🔍 검색 결과 연동 비활성화: 모든 이미지 대상으로 필터링")
            
            filtered_count = 0
            for image_path, tags in self.app_instance.all_tags.items():
                normalized_path = self._normalize_image_path(image_path)
                if search_target_images is not None and normalized_path not in search_target_images:
                    filtered_count += 1
                    continue
                
                if self.search_mode == "OR":
                    if any(tag in tags for tag in self.selected_tags):
                        tagged_images.add(normalized_path)
                else:  # AND
                    if all(tag in tags for tag in self.selected_tags):
                        tagged_images.add(normalized_path)
            
            if self.grid_filter_enabled:
                print(f"🔍 검색 결과 연동으로 제외된 이미지: {filtered_count}개")
        return tagged_images

    def show_tagged_images_with_checkboxes(self, tagged_images=None, reset_page=False):
        """태그 기준으로 필터링된 이미지들을 체크박스와 함께 표시 (선택 모드용) - 순차적 로딩"""
        # 카드 선택 모드 진입 시 모든 드래그 복사본 정리
        self._cleanup_all_drag_copies()
        self._cleanup_existing_image_frames()
        
        # 태그가 선택되지 않은 경우
        if not self.selected_tags:
            print("선택된 태그가 없음")
            try:
                self.grid_header_label.setText("Select tags to view images")
                empty_widget = QWidget()
                empty_widget.setStyleSheet("background-color: transparent;")
                self.image_scroll_area.setWidget(empty_widget)
                self._update_pagination_ui(0)
            except RuntimeError as e:
                print(f"RuntimeError 발생 (위젯 삭제됨) in show_tagged_images_with_checkboxes: {e}")
            return
        
        # 태그 기준으로 필터링된 이미지들 계산
        if tagged_images is None:
            tagged_images = self._get_current_filtered_images()
        else:
            tagged_images = {self._normalize_image_path(p) for p in tagged_images if self._normalize_image_path(p)}
        
        page_images, total_items = self._prepare_paginated_images(tagged_images, reset_page=reset_page)
        self._update_header_label(total_items)
        
        # 그리드 위젯 생성
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(6, 6, 6, 6)
        grid_layout.setAlignment(Qt.AlignTop)
        
        try:
            self.image_scroll_area.setWidget(grid_widget)
            self.image_grid_widget = grid_widget
            print("카드 선택 모드 그리드 위젯 생성 완료")
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in show_tagged_images_with_checkboxes: {e}")
            grid_widget.deleteLater()
            return
        
        if total_items == 0 or not page_images:
            print("이미지가 없음, 'No images found' 메시지 표시")
            no_images_label = QLabel("No images found with selected tags")
            no_images_label.setStyleSheet("color: #9CA3AF; font-size: 12px; margin: 20px;")
            no_images_label.setAlignment(Qt.AlignCenter)
            grid_layout.addWidget(no_images_label, 0, 0)
        else:
            print(f"카드 선택 모드 순차적 이미지 로딩 시작: {len(page_images)}개 (전체 {total_items}개 중)")
            # 순차적으로 이미지들을 하나씩 추가 (체크박스와 함께)
            self._load_checkbox_images_sequentially(page_images, grid_layout)
    
    def _load_checkbox_images_sequentially(self, image_paths, grid_layout):
        # 이 로딩 세션의 토큰을 고정
        self._loader_session_token = self._session_token
        """체크박스가 있는 이미지들을 순차적으로 로딩"""
        if not image_paths:
            return
        
        # 첫 번째 이미지부터 시작
        self._checkbox_loading_index = 0
        self._checkbox_image_paths = image_paths
        self._checkbox_grid_layout = grid_layout
        
        # 첫 번째 이미지 즉시 로딩
        self._load_next_checkbox_image()
    
    def _load_next_checkbox_image(self):
        """다음 체크박스 이미지를 로딩"""
        # 세션이 바뀌었으면 (이전 singleShot 콜백) 즉시 중단
        if hasattr(self, '_loader_session_token') and self._loader_session_token != self._session_token:
            print('⏹️ _load_next_checkbox_image: 세션 불일치로 중단')
            return
        if (not hasattr(self, '_checkbox_loading_index') or 
            not hasattr(self, '_checkbox_image_paths') or
            not hasattr(self, '_checkbox_grid_layout')):
            return
        
        if self._checkbox_loading_index >= len(self._checkbox_image_paths):
            print("모든 체크박스 이미지 로딩 완료")
            # 로딩 완료 후 레이아웃 재정렬
            QTimer.singleShot(50, self._rearrange_grid_layout)
            return
        
        try:
            image_path = self._checkbox_image_paths[self._checkbox_loading_index]
            print(f"체크박스 이미지 프레임 생성: {image_path} ({self._checkbox_loading_index + 1}/{len(self._checkbox_image_paths)})")
            
            # 이미지 프레임 생성 (체크박스 포함)
            img_frame = self.create_image_frame(image_path)
            
            if not img_frame:
                # 프레임 생성 실패 (세션 토큰 불일치 등) - 다음 이미지로 진행
                self._checkbox_loading_index += 1
                QTimer.singleShot(10, self._load_next_checkbox_image)
                return
            
            # 그리드에 추가
            cols = 3
            row = self._checkbox_loading_index // cols
            col = self._checkbox_loading_index % cols
            self._checkbox_grid_layout.addWidget(img_frame, row, col)
            
            # 다음 이미지 로딩을 위해 타이머 설정
            self._checkbox_loading_index += 1
            QTimer.singleShot(10, self._load_next_checkbox_image)  # 10ms 후 다음 이미지 로딩
            
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _load_next_checkbox_image: {e}")
            return

    def _cleanup_existing_image_frames(self):
        """기존 이미지 프레임들을 완전히 정리 (겹침 현상 방지)"""
        print(f"🧹 기존 이미지 프레임 정리 시작: {len(self.image_frames)}개")
        
        # 기존 이미지 프레임들 완전 삭제
        for image_path, frame in list(self.image_frames.items()):
            try:
                if frame and hasattr(frame, 'deleteLater'):
                    frame.hide()
                    frame.deleteLater()
            except RuntimeError:
                # 이미 삭제된 경우 무시
                pass
        self.image_frames.clear()
        
        # 기존 그리드 위젯도 완전 삭제
        if hasattr(self, 'image_grid_widget') and self.image_grid_widget:
            try:
                self.image_grid_widget.hide()
                self.image_grid_widget.deleteLater()
            except RuntimeError:
                pass
            self.image_grid_widget = None
        
        print(f"🧹 기존 이미지 프레임 정리 완료")

    def update_image_grid(self):
        """선택된 태그들을 OR 조건으로 이미지 그리드 업데이트 - diff 기반 최적화"""
        # 세션 토큰 증가 (이전 로딩 작업 무효화)
        self._session_token += 1
        print(f"🔄 update_image_grid 시작: selected_tags={self.selected_tags}")
        print(f"🔍 현재 상태:")
        print(f"  - card_selection_mode: {self.card_selection_mode}")
        print(f"  - grid_filter_enabled: {self.grid_filter_enabled}")
        print(f"  - image_frames 개수: {len(self.image_frames)}")
        
        # 기존 이미지 프레임들 완전 정리 (겹침 현상 방지)
        self._cleanup_existing_image_frames()
        print(f"  - 세션 토큰: {self._session_token}")
        
        # 카드 선택 모드가 활성화되어 있으면 태그 기준 이미지들을 체크박스와 함께 표시
        if self.card_selection_mode:
            print("🔄 카드 선택 모드 활성화: 태그 기준 이미지들을 체크박스와 함께 표시")
            self.show_tagged_images_with_checkboxes(reset_page=True)
            return
        
        if not self.selected_tags:
            # 태그가 선택되지 않은 경우: 연동을 자동 활성화하고(일관성),
            # 연동이면 현재 검색 결과 전체, 비연동이면 전체 이미지 표시
            print("선택된 태그가 없음 - 대상 전체 표시")
            try:
                if hasattr(self, 'grid_filter_checkbox') and not self.grid_filter_checkbox.isChecked():
                    # 자동으로 연동 ON (사용자 의도: 선택 태그 없으면 검색결과 연동 상태로 보기)
                    self.grid_filter_checkbox.setChecked(True)
            except Exception:
                pass
            try:
                target_set = self._get_current_filtered_images()
                page_images, total_items = self._prepare_paginated_images(target_set, reset_page=True)
                self._update_header_label(total_items)
                # 새 그리드 생성 및 표시
                self._render_standard_page(page_images)
                # 안내 라벨 및 AND/OR 드롭다운 상태
                try:
                    if hasattr(self, 'no_tags_hint_label') and self.no_tags_hint_label:
                        self.no_tags_hint_label.setVisible(True)
                except Exception:
                    pass
                try:
                    if hasattr(self, 'mode_combo') and self.mode_combo:
                        self.mode_combo.setEnabled(False)
                except Exception:
                    pass
            except RuntimeError as e:
                print(f"RuntimeError 발생 (위젯 삭제됨) in update_image_grid: {e}")
            return
        
        # 현재 UI 상태에 맞는 이미지 집합 계산 (검색 결과 연동 포함)
        print(f"🔍 검색 결과 연동 상태: {self.grid_filter_enabled}")
        if self.grid_filter_enabled and hasattr(self.app_instance, 'image_list'):
            print(f"🔍 현재 image_list: {len(self.app_instance.image_list) if self.app_instance.image_list else 0}개")
        print(f"🔍 all_tags 존재: {hasattr(self.app_instance, 'all_tags')}")
        if hasattr(self.app_instance, 'all_tags'):
            print(f"🔍 all_tags 개수: {len(self.app_instance.all_tags)}개")
        tagged_images = self._get_current_filtered_images()
        print(f"✅ 필터링된 이미지: {len(tagged_images)}개")
        if len(tagged_images) > 0:
            print(f"🔍 필터링된 이미지 샘플: {list(tagged_images)[:3]}")
        
        # 매칭 결과가 0이면 selected_cards 정리
        if not tagged_images and hasattr(self, 'selected_cards') and self.selected_cards:
            print("⚠️ 매칭 결과가 0개이므로 selected_cards 정리")
            self.selected_cards.clear()
        
        page_images, total_items = self._prepare_paginated_images(tagged_images, reset_page=True)
        self._update_header_label(total_items)
        
        # 헤더/안내/드롭다운 업데이트
        try:
            # 태그가 있는 상태: 안내 숨김, AND/OR 활성화
            try:
                if hasattr(self, 'no_tags_hint_label') and self.no_tags_hint_label:
                    self.no_tags_hint_label.setVisible(False)
                if hasattr(self, 'tags_scroll_area') and self.tags_scroll_area:
                    self.tags_scroll_area.setVisible(True)
                # 태그가 있으면 체크박스 클릭 가능하게 복원 (강제 체크 제거)
                try:
                    if hasattr(self, 'grid_filter_checkbox') and self.grid_filter_checkbox:
                        self.grid_filter_checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
                        self.grid_filter_checkbox.setProperty("locked", False)
                        self.grid_filter_checkbox.style().unpolish(self.grid_filter_checkbox)
                        self.grid_filter_checkbox.style().polish(self.grid_filter_checkbox)
                        self.grid_filter_checkbox.update()
                        # 강제 체크 제거 - 사용자가 선택한 상태 유지
                        self.grid_filter_checkbox.setToolTip("")
                except Exception:
                    pass
                # 모드 드롭다운도 다시 활성화
                try:
                    if hasattr(self, 'mode_combo') and self.mode_combo:
                        self.mode_combo.setEnabled(True)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                if hasattr(self, 'mode_combo') and self.mode_combo:
                    self.mode_combo.setEnabled(True)
            except Exception:
                pass
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in 헤더 업데이트: {e}")
            return
        
        # diff 기반 그리드 업데이트
        print(f"diff 기반 그리드 업데이트 시작: {len(page_images)}개 이미지 (전체 {total_items}개 중)")
        try:
            self._render_standard_page(page_images)
            print(f"diff 기반 그리드 업데이트 완료")
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _update_grid_with_diff: {e}")
            return
    
    def _cleanup_all_drag_copies(self):
        """모든 태그 버튼의 드래그 복사본들을 정리"""
        print("모든 드래그 복사본 정리 시작")
        cleanup_count = 0
        
        for tag_text, tag_button in self.tag_buttons.items():
            if hasattr(tag_button, 'drag_copy') and tag_button.drag_copy:
                try:
                    print(f"드래그 복사본 정리: {tag_text}")
                    tag_button.drag_copy.hide()
                    tag_button.drag_copy.deleteLater()
                    tag_button.drag_copy = None
                    cleanup_count += 1
                except RuntimeError:
                    # 이미 삭제된 경우 무시
                    pass
        
        if cleanup_count > 0:
            print(f"드래그 복사본 {cleanup_count}개 정리 완료")
    
    def _update_grid_with_diff(self, new_tagged_images):
        """diff 기반으로 그리드를 효율적으로 업데이트"""
        # 그리드 업데이트 전에 모든 드래그 복사본 정리
        self._cleanup_all_drag_copies()
        
        # 현재 표시된 이미지들
        current_images = set(self.image_frames.keys())
        new_images = set(new_tagged_images)
        
        # 추가할 이미지들
        images_to_add = new_images - current_images
        # 제거할 이미지들
        images_to_remove = current_images - new_images
        
        print(f"그리드 diff: 추가={len(images_to_add)}, 제거={len(images_to_remove)}, 유지={len(current_images & new_images)}")
        
        # 기존 그리드가 없거나 삭제된 경우 새로 생성
        grid_exists = False
        if hasattr(self, 'image_grid_widget') and self.image_grid_widget:
            try:
                # 위젯이 실제로 유효한지 확인
                _ = self.image_grid_widget.size()
                grid_exists = True
                print(f"✅ 기존 그리드 존재: {self.image_grid_widget}")
            except RuntimeError:
                print("⚠️ 기존 그리드가 삭제됨 - 새로 생성")
                self.image_grid_widget = None
                grid_exists = False
        
        if not grid_exists:
            print("🔄 기존 그리드가 없음, 새로 생성")
            self._create_new_grid(new_images)
            return
        
        # 제거할 이미지들의 프레임을 숨기고 정리
        for image_path in images_to_remove:
            if image_path in self.image_frames:
                frame = self.image_frames[image_path]
                try:
                    frame.hide()
                    frame.deleteLater()
                except RuntimeError:
                    # 이미 삭제된 위젯은 무시
                    pass
                del self.image_frames[image_path]
        
        # 제거 후 즉시 그리드 재정렬 (구멍 제거)
        if images_to_remove:
            self._rearrange_grid_layout()
        
        # 추가할 이미지들의 프레임을 순차적으로 생성
        if images_to_add:
            print(f"추가할 이미지들을 순차적으로 로딩: {len(images_to_add)}개")
            self._load_additional_images_sequentially(list(images_to_add))
        
        # 그리드 레이아웃 재정렬 (빈 공간 제거) - 순차적 로딩이 완료된 후에만
        if (not hasattr(self, '_current_loading_index') and 
            not hasattr(self, '_additional_loading_index') and
            not hasattr(self, '_checkbox_loading_index') and
            not hasattr(self, '_selected_loading_index')):
            self._rearrange_grid_layout()
    
    def _load_additional_images_sequentially(self, image_paths):
        # 이 로딩 세션의 토큰을 고정
        self._loader_session_token = self._session_token
        """추가할 이미지들을 순차적으로 로딩"""
        if not image_paths:
            return
        
        # 현재 그리드의 아이템 수 계산
        if not hasattr(self, 'image_grid_widget') or not self.image_grid_widget:
            return
        
        try:
            # 위젯이 실제로 유효한지 확인
            _ = self.image_grid_widget.size()
            grid_layout = self.image_grid_widget.layout()
            if not grid_layout:
                return
        except RuntimeError:
            print("⚠️ _load_additional_images_sequentially: 위젯이 삭제됨")
            return
        
        try:
            
            current_count = 0
            for i in range(grid_layout.count()):
                item = grid_layout.itemAt(i)
                if item and item.widget() and item.widget().isVisible():
                    current_count += 1
            
            # 추가할 이미지들의 시작 인덱스
            self._additional_loading_index = 0
            self._additional_image_paths = image_paths
            self._additional_start_count = current_count
            self._additional_grid_layout = grid_layout
            
            # 첫 번째 추가 이미지 즉시 로딩
            self._load_next_additional_image()
            
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _load_additional_images_sequentially: {e}")
            return
    
    def _load_next_additional_image(self):
        # 세션이 바뀌었으면 (이전 singleShot 콜백) 즉시 중단
        if hasattr(self, '_loader_session_token') and self._loader_session_token != self._session_token:
            print('⏹️ _load_next_additional_image: 세션 불일치로 중단')
            return
        """다음 추가 이미지를 로딩"""
        if (not hasattr(self, '_additional_loading_index') or 
            not hasattr(self, '_additional_image_paths') or
            not hasattr(self, '_additional_grid_layout')):
            return
        
        if self._additional_loading_index >= len(self._additional_image_paths):
            print("모든 추가 이미지 로딩 완료")
            # 로딩 완료 후 레이아웃 재정렬
            QTimer.singleShot(50, self._rearrange_grid_layout)
            return
        
        try:
            image_path = self._additional_image_paths[self._additional_loading_index]
            print(f"추가 이미지 프레임 생성: {image_path} ({self._additional_loading_index + 1}/{len(self._additional_image_paths)})")
            
            # 이미지 프레임 생성
            img_frame = self.create_image_frame(image_path)
            
            if not img_frame:
                # 프레임 생성 실패 (세션 토큰 불일치 등) - 다음 이미지로 진행
                self._additional_loading_index += 1
                QTimer.singleShot(10, self._load_next_additional_image)
                return
            
            # 그리드에 추가 (기존 아이템 수 + 현재 인덱스)
            cols = 3
            total_index = self._additional_start_count + self._additional_loading_index
            row = total_index // cols
            col = total_index % cols
            self._additional_grid_layout.addWidget(img_frame, row, col)
            
            # 다음 이미지 로딩을 위해 타이머 설정
            self._additional_loading_index += 1
            QTimer.singleShot(10, self._load_next_additional_image)  # 10ms 후 다음 이미지 로딩
            
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _load_next_additional_image: {e}")
            return
    
    def _create_new_grid(self, tagged_images):
        # 이 로딩 세션의 토큰을 고정
        self._loader_session_token = self._session_token
        """새 그리드 생성 - 순차적 로딩"""
        print(f"_create_new_grid 시작: {len(tagged_images)}개 이미지")
        
        # 그리드 위젯 생성
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(6, 6, 6, 6)
        grid_layout.setAlignment(Qt.AlignTop)
        
        try:
            self.image_scroll_area.setWidget(grid_widget)
            self.image_grid_widget = grid_widget
            print("그리드 위젯 생성 완료")
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _create_new_grid: {e}")
            grid_widget.deleteLater()
            return
        
        # 레이아웃 시스템이 완전히 초기화될 때까지 지연
        def delayed_image_loading():
            if not tagged_images:
                print("이미지가 없음, 'No images found' 메시지 표시")
                no_images_label = QLabel("No images found with selected tags")
                no_images_label.setStyleSheet("color: #9CA3AF; font-size: 12px; margin: 20px;")
                no_images_label.setAlignment(Qt.AlignCenter)
                grid_layout.addWidget(no_images_label, 0, 0)
            else:
                print(f"순차적 이미지 로딩 시작: {len(tagged_images)}개")
                # 순차적으로 이미지들을 하나씩 추가
                self._load_images_sequentially(sorted(tagged_images), grid_layout)
        
        # 레이아웃 초기화 완료 후 이미지 로딩 시작 (100ms 지연)
        QTimer.singleShot(100, delayed_image_loading)
    
    def _load_images_sequentially(self, image_paths, grid_layout):
        # 이 로딩 세션의 토큰을 고정
        self._loader_session_token = self._session_token
        """이미지들을 순차적으로 하나씩 로딩하여 즉시 표시"""
        if not image_paths:
            return
        
        # 첫 번째 이미지부터 시작
        self._current_loading_index = 0
        self._image_paths_to_load = image_paths
        self._grid_layout = grid_layout
        
        # 첫 번째 이미지 즉시 로딩
        self._load_next_image()
    
    def _load_next_image(self):
        """다음 이미지를 로딩"""
        # 세션이 바뀌었으면 (이전 singleShot 콜백) 즉시 중단
        if hasattr(self, '_loader_session_token') and self._loader_session_token != self._session_token:
            print('⏹️ _load_next_image: 세션 불일치로 중단')
            return
        if (not hasattr(self, '_current_loading_index') or 
            not hasattr(self, '_image_paths_to_load') or
            not hasattr(self, '_grid_layout')):
            return
        
        if self._current_loading_index >= len(self._image_paths_to_load):
            print("모든 이미지 로딩 완료")
            # 로딩 완료 후 레이아웃 재정렬
            QTimer.singleShot(50, self._rearrange_grid_layout)
            return
        
        try:
            image_path = self._image_paths_to_load[self._current_loading_index]
            print(f"이미지 프레임 생성: {image_path} ({self._current_loading_index + 1}/{len(self._image_paths_to_load)})")
            
            # 이미지 프레임 생성
            img_frame = self.create_image_frame(image_path)
            
            if not img_frame:
                # 프레임 생성 실패 (세션 토큰 불일치 등) - 다음 이미지로 진행
                self._current_loading_index += 1
                QTimer.singleShot(10, self._load_next_image)
                return
            
            # 그리드에 추가
            cols = 3
            row = self._current_loading_index // cols
            col = self._current_loading_index % cols
            self._grid_layout.addWidget(img_frame, row, col)
            
            # 다음 이미지 로딩을 위해 타이머 설정 (즉시 반응성을 위해 매우 짧은 간격)
            self._current_loading_index += 1
            QTimer.singleShot(10, self._load_next_image)  # 10ms 후 다음 이미지 로딩
            
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _load_next_image: {e}")
            return
    
    def _add_frame_to_grid(self, frame, image_path):
        """프레임을 그리드에 추가"""
        if not hasattr(self, 'image_grid_widget') or not self.image_grid_widget:
            print(f"image_grid_widget이 없음: {image_path}")
            return
        
        try:
            grid_layout = self.image_grid_widget.layout()
            if not grid_layout:
                print(f"grid_layout이 없음: {image_path}")
                return
            
            # 프레임이 톱레벨 창인 경우 그리드 위젯을 부모로 재설정
            if frame.isWindow():
                print(f"WARNING: Frame is top-level window, fixing parent for {image_path}")
                frame.setParent(self.image_grid_widget)
                frame.setWindowFlags(Qt.Widget)  # 윈도우 플래그 제거
            
            # 현재 그리드의 아이템 수 계산
            current_count = 0
            for i in range(grid_layout.count()):
                item = grid_layout.itemAt(i)
                if item and item.widget() and item.widget().isVisible():
                    current_count += 1
            
            # 새 위치 계산
            cols = 3
            row = current_count // cols
            col = current_count % cols
            
            grid_layout.addWidget(frame, row, col)
            print(f"프레임 그리드에 추가 완료: {image_path} at ({row}, {col}), isWindow={frame.isWindow()}")
            
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨): {image_path}, 오류: {e}")
            # 위젯이 삭제된 경우 프레임도 정리
            if frame:
                frame.deleteLater()
            return
    
    def _rearrange_grid_layout(self):
        """그리드 레이아웃 재정렬 (빈 공간 제거)"""
        if not hasattr(self, 'image_grid_widget') or not self.image_grid_widget:
            return
        
        try:
            # 위젯이 실제로 유효한지 확인
            _ = self.image_grid_widget.size()
            grid_layout = self.image_grid_widget.layout()
            if not grid_layout:
                return
        except RuntimeError:
            print("⚠️ _rearrange_grid_layout: 위젯이 삭제됨")
            return
        
        try:
            
            # 모든 위젯을 임시 리스트에 수집
            visible_widgets = []
            for i in range(grid_layout.count()):
                item = grid_layout.itemAt(i)
                if item and item.widget() and item.widget().isVisible():
                    visible_widgets.append(item.widget())
            
            # 레이아웃 초기화 (위젯 완전 삭제)
            while grid_layout.count():
                child = grid_layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
            
            # 위젯들을 다시 배치
            cols = 3
            for i, widget in enumerate(visible_widgets):
                row = i // cols
                col = i % cols
                grid_layout.addWidget(widget, row, col)
                
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _rearrange_grid_layout: {e}")
            return
    
    def display_selected_cards_only(self):
        """선택된 카드들만 표시 - 순차적 로딩"""
        # 선택된 카드만 표시 시 모든 드래그 복사본 정리
        self._cleanup_all_drag_copies()
        
        # 그리드 위젯 생성
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(6, 6, 6, 6)
        grid_layout.setAlignment(Qt.AlignTop)
        
        try:
            self.image_scroll_area.setWidget(grid_widget)
            self.image_grid_widget = grid_widget
            print("선택된 카드만 표시 그리드 위젯 생성 완료")
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in display_selected_cards_only: {e}")
            grid_widget.deleteLater()
            return
        
        if not self.selected_cards:
            # 선택된 카드가 없는 경우 메시지 표시
            print("선택된 카드가 없음, 'No cards selected' 메시지 표시")
            no_cards_label = QLabel("No cards selected")
            no_cards_label.setStyleSheet("color: #9CA3AF; font-size: 12px; margin: 20px;")
            no_cards_label.setAlignment(Qt.AlignCenter)
            grid_layout.addWidget(no_cards_label, 0, 0)
            try:
                self.grid_header_label.setText("No cards selected")
            except RuntimeError as e:
                print(f"RuntimeError 발생 (위젯 삭제됨) in 헤더 업데이트: {e}")
        else:
            print(f"선택된 카드들 순차적 로딩 시작: {len(self.selected_cards)}개")
            # 순차적으로 선택된 카드들을 하나씩 추가
            self._load_selected_cards_sequentially(sorted(self.selected_cards), grid_layout)
            try:
                self.grid_header_label.setText(f"Selected {len(self.selected_cards)} cards")
            except RuntimeError as e:
                print(f"RuntimeError 발생 (위젯 삭제됨) in 헤더 업데이트: {e}")
    
    def _load_selected_cards_sequentially(self, image_paths, grid_layout):
        # 이 로딩 세션의 토큰을 고정
        self._loader_session_token = self._session_token
        """선택된 카드들을 순차적으로 로딩"""
        if not image_paths:
            return
        
        # 첫 번째 이미지부터 시작
        self._selected_loading_index = 0
        self._selected_image_paths = image_paths
        self._selected_grid_layout = grid_layout
        
        # 첫 번째 이미지 즉시 로딩
        self._load_next_selected_card()
    
    def _load_next_selected_card(self):
        # 세션이 바뀌었으면 (이전 singleShot 콜백) 즉시 중단
        if hasattr(self, '_loader_session_token') and self._loader_session_token != self._session_token:
            print('⏹️ _load_next_selected_card: 세션 불일치로 중단')
            return
        """다음 선택된 카드를 로딩"""
        if (not hasattr(self, '_selected_loading_index') or 
            not hasattr(self, '_selected_image_paths') or
            not hasattr(self, '_selected_grid_layout')):
            return
        
        if self._selected_loading_index >= len(self._selected_image_paths):
            print("모든 선택된 카드 로딩 완료")
            # 로딩 완료 후 레이아웃 재정렬
            QTimer.singleShot(50, self._rearrange_grid_layout)
            return
        
        try:
            image_path = self._selected_image_paths[self._selected_loading_index]
            print(f"선택된 카드 프레임 생성: {image_path} ({self._selected_loading_index + 1}/{len(self._selected_image_paths)})")
            
            # 이미지 프레임 생성
            img_frame = self.create_image_frame(image_path)
            
            if not img_frame:
                # 프레임 생성 실패 (세션 토큰 불일치 등) - 다음 이미지로 진행
                self._selected_loading_index += 1
                QTimer.singleShot(10, self._load_next_selected_card)
                return
            
            # 그리드에 추가
            cols = 3
            row = self._selected_loading_index // cols
            col = self._selected_loading_index % cols
            self._selected_grid_layout.addWidget(img_frame, row, col)
            
            # 다음 이미지 로딩을 위해 타이머 설정
            self._selected_loading_index += 1
            QTimer.singleShot(10, self._load_next_selected_card)  # 10ms 후 다음 이미지 로딩
            
        except RuntimeError as e:
            print(f"RuntimeError 발생 (위젯 삭제됨) in _load_next_selected_card: {e}")
            return
    
    def refresh_editor_content(self):
        """에디터 내용 실시간 새로고침"""
        print("에디터 내용 새로고침 시작")
        
        # 에디터가 열려있는지 확인
        if not (hasattr(self.app_instance, 'tag_edit_card') and self.app_instance.tag_edit_card):
            print("에디터가 열려있지 않음")
            return
        
        # 중복 새로고침 방지 (이미 새로고침 중이면 스킵)
        if hasattr(self, '_refreshing') and self._refreshing:
            print("이미 새로고침 중 - 스킵")
            return
        
        self._refreshing = True
        
        # 검색 결과 연동 상태 확인 및 복원
        if hasattr(self, 'grid_filter_checkbox'):
            current_sync_state = self.grid_filter_checkbox.isChecked()
            if current_sync_state != self.grid_filter_enabled:
                print(f"검색 결과 연동 상태 불일치 감지: UI={current_sync_state}, 내부={self.grid_filter_enabled}")
                self.grid_filter_enabled = current_sync_state
                if current_sync_state:
                    # 검색 결과 연동 활성화 시 타이머 시작
                    self._grid_sync_timer.start()
                    self._last_image_list_snapshot = tuple(getattr(self.app_instance, 'image_list', []) or [])
                    print("검색 결과 연동 상태 복원: 타이머 시작")
                else:
                    # 검색 결과 연동 비활성화 시 타이머 중지
                    self._grid_sync_timer.stop()
                    print("검색 결과 연동 상태 복원: 타이머 중지")
        
        # image_list 상태 확인 및 로그
        if hasattr(self.app_instance, 'image_list'):
            image_list_count = len(self.app_instance.image_list) if self.app_instance.image_list else 0
            print(f"🔍 현재 image_list 상태: {image_list_count}개 이미지")
            if self.grid_filter_enabled and image_list_count == 0:
                print("⚠️ 검색 결과 연동이 활성화되었지만 image_list가 비어있음 - 모든 이미지로 폴백")
        
        # 무효한 태그들 정리 (비활성화 - selected_tags 유지를 위해)
        # self.cleanup_invalid_tags()
        
        # 태그 버튼들 업데이트 (존재하지 않는 태그 버튼 제거)
        valid_buttons = {}
        for tag_text in list(self.tag_buttons.keys()):
            if tag_text in self.selected_tags:
                # 태그가 여전히 유효한지 확인
                if hasattr(self.app_instance, 'all_tags'):
                    all_existing_tags = set()
                    for image_path, tags in self.app_instance.all_tags.items():
                        all_existing_tags.update(tags)
                    if tag_text in all_existing_tags:
                        valid_buttons[tag_text] = self.tag_buttons[tag_text]
                    else:
                        # 무효한 태그 버튼 제거
                        btn = self.tag_buttons[tag_text]
                        btn.deleteLater()
                        if tag_text in self.selected_tags:
                            self.selected_tags.remove(tag_text)
                else:
                    # all_tags가 없으면 모든 버튼 제거
                    btn = self.tag_buttons[tag_text]
                    btn.deleteLater()
                    if tag_text in self.selected_tags:
                        self.selected_tags.remove(tag_text)
            else:
                # 선택되지 않은 태그 버튼 제거
                btn = self.tag_buttons[tag_text]
                btn.deleteLater()
        
        self.tag_buttons = valid_buttons
        
        # 이미지 그리드 업데이트 (즉시 실행 - 새로고침에서는 스로틀링 불필요)
        self.update_image_grid()
        
        # 높이 조정
        self.update_tags_container_height()
        
        # 다른 UI 요소들도 업데이트
        self.update_other_ui_elements()
        
        # 안전망: 선택 모드가 켜져 있으면 체크박스 가시성 한 번 더 확인
        if self.card_selection_mode:
            self.update_card_checkboxes_visibility()
        
        # 태그 변경 시그널 발생 (태그 제거 감지를 위해)
        self.tags_changed.emit(self.selected_tags.copy())
        
        # 새로고침 완료 플래그 해제
        self._refreshing = False
        
        print(f"에디터 새로고침 완료 - 선택된 태그: {len(self.selected_tags)}개")
    
    def update_other_ui_elements(self):
        """다른 UI 요소들 업데이트 (태그 트리, 태그 통계 등)"""
        print("🔄 다른 UI 요소들 업데이트 시작")
        
        # 현재 이미지의 removed_tags 업데이트 (색상 업데이트를 위해)
        if (hasattr(self.app_instance, 'current_image') and self.app_instance.current_image and
            hasattr(self.app_instance, 'removed_tags')):
            current_image_path = self.app_instance.current_image
            if current_image_path in self.app_instance.all_tags:
                updated_tags = self.app_instance.all_tags[current_image_path]
                original_removed_count = len(self.app_instance.removed_tags)
                self.app_instance.removed_tags = [
                    tag for tag in self.app_instance.removed_tags 
                    if tag not in updated_tags
                ]
                if len(self.app_instance.removed_tags) != original_removed_count:
                    print(f"removed_tags 업데이트: {original_removed_count}개 -> {len(self.app_instance.removed_tags)}개")
        
        # 에디터의 selected_tags는 태그 교체/이동 후에도 그대로 유지
        # (검색 조건을 유지하기 위해)
        print(f"에디터 selected_tags 유지: {self.selected_tags}")
        
        # 태그 통계 재계산은 tag_statistics_module.py에서 담당
        
        # 2. 메인 애플리케이션의 올바른 업데이트 메서드 호출
        if hasattr(self.app_instance, 'update_global_tag_stats'):
            self.app_instance.update_global_tag_stats()
        
        # 3. 태그 트리 업데이트 (올바른 경로 사용)
        if hasattr(self.app_instance, 'update_tag_tree'):
            self.app_instance.update_tag_tree()
        
        print("✅ 다른 UI 요소들 업데이트 완료")
    
    # 전역 태그 통계 재계산은 tag_statistics_module.py에서 담당
    
    def schedule_update(self):
        """에디터 업데이트 예약 (디바운싱)"""
        self.update_timer.stop()
        self.update_timer.start(200)  # 200ms 후 업데이트 (렉 방지, 더 빠른 반응)
    
    def cleanup_invalid_tags(self):
        """실제로 존재하지 않는 태그들을 선택 목록에서 제거"""
        if not hasattr(self.app_instance, 'all_tags'):
            return
        
        # 현재 존재하는 모든 태그 수집
        existing_tags = set()
        for image_path, tags in self.app_instance.all_tags.items():
            existing_tags.update(tags)
        
        # 선택된 태그 중 존재하지 않는 것들 제거
        invalid_tags = []
        for tag in self.selected_tags:
            if tag not in existing_tags:
                invalid_tags.append(tag)
        
        # 무효한 태그들 제거
        for tag in invalid_tags:
            print(f"존재하지 않는 태그 제거: {tag}")
            if tag in self.tag_buttons:
                btn = self.tag_buttons[tag]
                btn.deleteLater()
                del self.tag_buttons[tag]
            if tag in self.selected_tags:
                self.selected_tags.remove(tag)  # list에서 제거
    
    def update_tags_container_height(self):
        """태그 컨테이너의 높이를 동적으로 조정"""
        if not self.tags_scroll_area or not self.flow_layout:
            return
        
        # 현재 스크롤 영역의 너비
        viewport_width = self.tags_scroll_area.viewport().width()
        if viewport_width <= 0:
            print(f"뷰포트 너비가 0입니다: {viewport_width}")
            return
        
        # FlowLayout에서 필요한 높이 계산
        required_height = self.flow_layout.heightForWidth(viewport_width - 16)  # 패딩 고려
        print(f"뷰포트 너비: {viewport_width}, 필요한 높이: {required_height}")
        
        # 최소/최대 높이 제한
        min_height = 40
        max_height = 200
        
        # 높이 조정
        actual_height = max(min_height, min(required_height + 16, max_height))  # 패딩 추가
        
        # 컨테이너와 스크롤 영역 높이 설정 (고정 높이 제거)
        # self.tags_container.setFixedHeight(required_height + 16)
        # self.tags_scroll_area.setFixedHeight(actual_height)
        print(f"높이 계산 완료: 컨테이너={required_height + 16}, 스크롤={actual_height}")
    
    def eventFilter(self, obj, event):
        """이벤트 필터 - 컨테이너와 뷰포트 크기 변화 감지"""
        try:
            # 객체가 삭제되었는지 확인
            if hasattr(self, 'tags_container') and hasattr(self, 'tags_scroll_area'):
                if (obj == self.tags_container or 
                    (self.tags_scroll_area and obj == self.tags_scroll_area.viewport())) and event.type() == event.Type.Resize:
                    # 컨테이너나 뷰포트 크기가 변경되면 높이 재조정
                    QTimer.singleShot(0, self.update_tags_container_height)
        except RuntimeError:
            # 객체가 삭제된 경우 무시
            pass
        return super().eventFilter(obj, event)
    
    def create_image_frame(self, image_path):
        """이미지 프레임 생성"""
        # 세션 토큰 확인: 페이지 전환으로 인해 무효화된 경우 프레임 생성 중단
        if hasattr(self, '_loader_session_token') and self._loader_session_token != self._session_token:
            print(f'⏹️ create_image_frame: 세션 불일치로 중단 (토큰: {self._loader_session_token} != {self._session_token})')
            return None
        
        # 그리드 위젯이 유효한지 확인
        if not hasattr(self, 'image_grid_widget') or not self.image_grid_widget:
            print(f"⏹️ create_image_frame: image_grid_widget이 없음 - 중단")
            return None
        
        try:
            # 위젯이 실제로 유효한지 확인
            _ = self.image_grid_widget.size()
        except RuntimeError:
            print(f"⏹️ create_image_frame: image_grid_widget이 삭제됨 - 중단")
            return None
        
        # 부모 위젯을 명시적으로 설정하여 윈도우로 인식되지 않도록 함
        parent_widget = self.image_grid_widget
        if not isinstance(parent_widget, QWidget):
            print(f"⏹️ create_image_frame: 유효하지 않은 부모 위젯 - 중단")
            return None
        
        img_frame = QFrame(parent_widget)
        
        # 만약 예외적으로 최상위 윈도우로 만들어졌다면(부모 누락), 즉시 안전한 부모로 재설정
        if img_frame.isWindow():
            print("WARNING: QFrame became top-level window! Attempting to fix...")
            if isinstance(parent_widget, QWidget):
                img_frame.setParent(parent_widget)
                print(f"Fixed: setParent to {type(parent_widget)}")
            else:
                print("ERROR: Could not find valid parent widget!")
                img_frame.deleteLater()
                return None
        img_frame.setMinimumSize(200, 0)  # 최소 높이 제거, 너비 축소
        img_frame.setMaximumSize(500, 16777215)  # 최대 높이 제거, 너비 확장
        img_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
            }
            QFrame:hover {
                border: 1px solid rgba(59, 130, 246, 0.5);
                background-color: rgba(59, 130, 246, 0.1);
            }
        """)
        
        # 이미지 프레임을 매핑에 저장
        self.image_frames[image_path] = img_frame
        
        img_layout = QHBoxLayout(img_frame)  # 가로 레이아웃으로 변경
        img_layout.setContentsMargins(4, 4, 4, 4)
        img_layout.setSpacing(8)
        img_layout.setAlignment(Qt.AlignVCenter)  # 수직 중앙 정렬로 변경
        
        # 카드 선택용 체크박스 (왼쪽에 배치) - 이미지 검색 결과 연동과 동일한 디자인
        class CardCheckBox(QCheckBox):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setStyleSheet("""
                    QCheckBox {
                        color: #FFFFFF;
                        font-size: 12px;
                        spacing: 6px;
                    }
                    QCheckBox::indicator {
                        width: 14px;
                        height: 14px;
                        border-radius: 2px;
                        border: 1px solid rgba(255, 255, 255, 0.8);
                        background: rgba(17, 17, 27, 0.9);
                    }
                    QCheckBox::indicator:checked {
                        background: rgba(17, 17, 27, 0.9);
                        border: 1px solid rgba(255, 255, 255, 0.8);
                        image: none;
                    }
                    QCheckBox::indicator:hover {
                        border: 1px solid rgba(255, 255, 255, 1.0);
                    }
                    QCheckBox:disabled {
                        color: #6B7280;
                    }
                    QCheckBox::indicator:disabled {
                        border: 1px solid #374151;
                        background: #1F2937;
                    }
                """)
            
            def paintEvent(self, event):
                super().paintEvent(event)
                if self.isChecked():
                    painter = QPainter(self)
                    painter.setRenderHint(QPainter.Antialiasing)
                    check_color = QColor("#FFFFFF") if self.isEnabled() else QColor("#6B7280")
                    painter.setPen(QPen(check_color, 2))
                    painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
                    rect = self.rect()
                    indicator_rect = QRect(1, (rect.height() - 14) // 2, 14, 14)
                    painter.drawText(indicator_rect, Qt.AlignCenter, "🗸")

        card_checkbox = CardCheckBox(img_frame)  # 부모를 img_frame으로 명시적 설정
        card_checkbox.setVisible(self.card_selection_mode)  # 선택 모드일 때만 표시
        card_checkbox.toggled.connect(lambda checked: self.on_card_checkbox_toggled(image_path, checked))
        img_frame.card_checkbox = card_checkbox  # 프레임에 체크박스 참조 저장
        # 이전 선택 상태 복원
        try:
            card_checkbox.setChecked(image_path in self.selected_cards)
        except Exception:
            pass

        img_layout.addWidget(card_checkbox)
        
        # 왼쪽: 이미지 영역
        left_widget = QWidget(img_frame)  # 부모를 img_frame으로 명시적 설정
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        left_layout.setAlignment(Qt.AlignTop)
        
        # 이미지 라벨
        img_label = QLabel(left_widget)  # 부모를 left_widget으로 명시적 설정
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setMinimumSize(100, 100)
        img_label.setMaximumSize(120, 120)
        img_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        img_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        
        left_layout.addWidget(img_label)
        
        # 오른쪽: 태그 정보 영역
        right_widget = QWidget(img_frame)  # 부모를 img_frame으로 명시적 설정
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        right_layout.setAlignment(Qt.AlignTop)  # 위쪽 정렬로 변경 (좌우 칼럼 통일)
        
        # 파일명을 맨 위에 추가
        filename = Path(image_path).name
        filename_label = QLabel(filename[:25] + "..." if len(filename) > 25 else filename, right_widget)  # 부모를 right_widget으로 명시적 설정
        filename_label.setAlignment(Qt.AlignLeft)  # 왼쪽 정렬로 변경
        filename_label.setStyleSheet("color: #9CA3AF; font-size: 10px; background-color: transparent; border: none;")
        filename_label.setWordWrap(False)
        filename_label.setFixedHeight(20)
        filename_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(filename_label)
        
        # 해당 이미지의 전체 태그 표시 (키는 문자열 사용)
        all_image_tags = []
        if hasattr(self.app_instance, 'all_tags'):
            all_image_tags = self.app_instance.all_tags.get(str(image_path), [])
        
        # 태그 표시 영역을 스크롤 가능하게 만들기
        tags_scroll = QScrollArea(right_widget)
        tags_scroll.setWidgetResizable(True)
        tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 가로 스크롤바 숨김
        tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 세로 스크롤바 필요시 표시
        tags_scroll.setMaximumHeight(80)  # 최대 높이 제한으로 카드가 너무 커지지 않도록
        tags_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tags_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(26,27,38,0.8);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(75,85,99,0.6);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(75,85,99,0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 태그 표시 라벨(항상 생성, 이후 갱신 시 교체 없이 텍스트만 변경)
        all_tags_label = QLabel("")
        all_tags_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        all_tags_label.setStyleSheet("color: #9CA3AF; font-size: 10px; background-color: transparent; border: none;")
        all_tags_label.setWordWrap(True)
        all_tags_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # 스크롤 영역에 라벨 추가
        tags_scroll.setWidget(all_tags_label)
        right_layout.addWidget(tags_scroll)
        
        # 프레임에 참조 저장 (태그만 갱신용)
        img_frame.all_tags_label = all_tags_label
        
        if all_image_tags:
            # 태그 전체 표시 (중략 없이)
            all_tags_text = ", ".join([str(t) for t in all_image_tags])
            all_tags_label.setText(all_tags_text)
        else:
            all_tags_label.setText("No tags")
        
        # 메인 레이아웃에 추가
        img_layout.addWidget(left_widget)
        img_layout.addWidget(right_widget)
        
        # 이미지 로딩 (비동기)
        self.load_image_thumbnail(img_label, str(image_path))
        
        return img_frame

    def refresh_card_tags(self, image_paths=None):
        """이미지는 유지하고 카드 우측 태그 라벨만 갱신한다."""
        try:
            targets = []
            if image_paths:
                for p in image_paths:
                    if p in self.image_frames:
                        targets.append(p)
            else:
                targets = list(self.image_frames.keys())
            for image_path in targets:
                frame = self.image_frames.get(image_path)
                if not frame or not hasattr(frame, 'all_tags_label'):
                    continue
                tags = []
                if hasattr(self.app_instance, 'all_tags'):
                    tags = self.app_instance.all_tags.get(str(image_path), [])
                if tags:
                    display_tags = [(t[:20] + "...") if isinstance(t, str) and len(t) > 20 else t for t in tags]
                    text = ", ".join(display_tags)
                else:
                    text = "No tags"
                frame.all_tags_label.setText(text)
        except Exception:
            pass
    
    def load_image_thumbnail(self, label, image_path):
        """이미지 썸네일 로딩 - 캐싱 시스템 및 Qt 최적화 적용"""
        print(f"이미지 로딩 시도: {image_path}")
        
        # 파일 존재 확인
        if not Path(image_path).exists():
            print(f"파일이 존재하지 않음: {image_path}")
            label.setText("File\nNot Found")
            label.setStyleSheet(label.styleSheet() + "color: #EF4444; font-size: 10px;")
            return
        
        # 파일 수정 시간 확인
        current_mtime = Path(image_path).stat().st_mtime
        
        # 캐시에서 확인
        if (image_path in self.thumbnail_cache and 
            image_path in self.thumbnail_mtime_cache and
            self.thumbnail_mtime_cache[image_path] == current_mtime):
            print(f"썸네일 캐시 히트: {image_path}")
            label.setPixmap(self.thumbnail_cache[image_path])
            return
        
        # 캐시 미스 - Qt QImageReader로 최적화된 로딩 시도
        print(f"썸네일 캐시 미스, 새로 생성: {image_path}")
        pixmap = self._load_thumbnail_with_qt(image_path)
        
        if pixmap and not pixmap.isNull():
            # 캐시에 저장
            self.thumbnail_cache[image_path] = pixmap
            self.thumbnail_mtime_cache[image_path] = current_mtime
            
            label.setPixmap(pixmap)
            print("Qt 최적화 이미지 로딩 및 캐시 저장 완료")
        else:
            # Qt 로딩 실패 시 Pillow로 폴백
            print("Qt 로딩 실패, Pillow로 폴백")
            pixmap = self._load_thumbnail_with_pillow(image_path)
            
            if pixmap and not pixmap.isNull():
                # 캐시에 저장
                self.thumbnail_cache[image_path] = pixmap
                self.thumbnail_mtime_cache[image_path] = current_mtime
                
                label.setPixmap(pixmap)
                print("Pillow 폴백 이미지 로딩 및 캐시 저장 완료")
            else:
                print("모든 이미지 로딩 방법 실패")
                label.setText("Load\nFailed")
                label.setStyleSheet(label.styleSheet() + "color: #EF4444; font-size: 10px;")
    
    def _load_thumbnail_with_qt(self, image_path):
        """Qt QImageReader를 사용한 최적화된 썸네일 로딩"""
        try:
            reader = QImageReader(image_path)
            
            # 이미지 크기 정보만 읽기 (실제 이미지 데이터는 로딩하지 않음)
            size = reader.size()
            if not size.isValid():
                print(f"Qt: 이미지 크기 정보 읽기 실패: {image_path}")
                return None
            
            # 썸네일 크기 계산 (100x100에 맞춰 비율 유지)
            target_size = QSize(100, 100)
            scaled_size = size.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio)
            
            # 스케일된 크기로 이미지 로딩
            reader.setScaledSize(scaled_size)
            image = reader.read()
            
            if image.isNull():
                print(f"Qt: 이미지 로딩 실패: {image_path}")
                return None
            
            # QPixmap으로 변환
            pixmap = QPixmap.fromImage(image)
            print(f"Qt 최적화 로딩 성공: {image_path}, 원본: {size}, 썸네일: {scaled_size}")
            return pixmap
            
        except Exception as e:
            print(f"Qt 이미지 로딩 실패: {image_path}, 오류: {e}")
            return None
    
    def _load_thumbnail_with_pillow(self, image_path):
        """Pillow를 사용한 썸네일 로딩 (폴백)"""
        try:
            from PIL import Image
            import io
            
            # 이미지 로딩 및 리사이즈
            with Image.open(image_path) as img:
                print(f"Pillow: 이미지 열기 성공: {img.size}, 모드: {img.mode}")
                
                # 팔레트 모드나 RGBA를 RGB로 변환 (JPEG 저장을 위해)
                if img.mode in ['P', 'RGBA', 'LA', 'PA']:
                    if img.mode == 'P':
                        # 팔레트 모드를 RGB로 변환
                        img = img.convert('RGB')
                        print("Pillow: 팔레트 모드 -> RGB 변환 완료")
                    elif img.mode == 'RGBA':
                        img = img.convert('RGB')
                        print("Pillow: RGBA -> RGB 변환 완료")
                    elif img.mode in ['LA', 'PA']:
                        img = img.convert('RGB')
                        print(f"Pillow: {img.mode} -> RGB 변환 완료")
                
                # 썸네일 생성 (BILINEAR로 변경하여 성능 향상)
                img.thumbnail((100, 100), Image.Resampling.BILINEAR)
                print(f"Pillow: 썸네일 생성 완료: {img.size}")
                
                # QPixmap으로 변환 (optimize=False로 변경하여 성능 향상)
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='JPEG', quality=85, optimize=False)
                img_bytes.seek(0)
                print(f"Pillow: JPEG 압축 완료: {len(img_bytes.getvalue())} bytes")
                
                pixmap = QPixmap()
                success = pixmap.loadFromData(img_bytes.getvalue())
                print(f"Pillow: QPixmap 로딩: {'성공' if success else '실패'}")
                
                if success:
                    return pixmap
                else:
                    return None
                
        except Exception as e:
            print(f"Pillow 이미지 로딩 실패: {image_path}, 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
        
    def clear_thumbnail_cache(self):
        """썸네일 캐시 정리"""
        print(f"썸네일 캐시 정리: {len(self.thumbnail_cache)}개 항목")
        self.thumbnail_cache.clear()
        self.thumbnail_mtime_cache.clear()
    
    def reset_editor(self):
        """에디터 초기화 - 새로운 이미지 폴더 로딩 시 호출"""
        print("태그 스타일시트 에디터 초기화")
        
        # 실시간 동기화 타이머 정리
        try:
            self._grid_sync_timer.stop()
        except Exception:
            pass
        
        # 이벤트 필터 제거 (안전하게)
        try:
            if hasattr(self, 'tags_container') and self.tags_container:
                self.tags_container.removeEventFilter(self)
            if hasattr(self, 'tags_scroll_area') and self.tags_scroll_area:
                self.tags_scroll_area.viewport().removeEventFilter(self)
        except RuntimeError:
            # 객체가 이미 삭제된 경우 무시
            pass
        
        # 선택된 태그들 초기화
        self.selected_tags.clear()
        
        # 모든 태그 버튼 제거
        for tag_text in list(self.tag_buttons.keys()):
            btn = self.tag_buttons[tag_text]
            btn.deleteLater()
        self.tag_buttons.clear()
        
        # 카드 선택 관련 변수들 초기화
        self.card_selection_mode = False
        self.selected_cards.clear()
        self.image_frames.clear()
        
        # 썸네일 캐시 정리
        self.clear_thumbnail_cache()
        
        # 이미지 그리드 초기화 (안전하게)
        try:
            if hasattr(self, 'image_scroll_area') and self.image_scroll_area:
                empty_widget = QWidget()
                empty_widget.setStyleSheet("background-color: transparent;")
                self.image_scroll_area.setWidget(empty_widget)
        except RuntimeError:
            # 객체가 이미 삭제된 경우 무시
            pass
        
        # 헤더 초기화 (안전하게)
        try:
            if hasattr(self, 'grid_header_label') and self.grid_header_label:
                self.grid_header_label.setText("Select tags to view images")
        except RuntimeError:
            # 객체가 이미 삭제된 경우 무시
            pass
        
        # 높이 조정 (안전하게)
        try:
            self.update_tags_container_height()
        except RuntimeError:
            # 객체가 이미 삭제된 경우 무시
            pass
    
    def cancel_tag_edit(self):
        """에디터 닫기"""
        print("태그 스타일시트 에디터 닫기")
        
        # 이벤트 필터 제거 (안전하게)
        try:
            if hasattr(self, 'tags_container') and self.tags_container:
                self.tags_container.removeEventFilter(self)
            if hasattr(self, 'tags_scroll_area') and self.tags_scroll_area:
                self.tags_scroll_area.viewport().removeEventFilter(self)
        except RuntimeError:
            # 객체가 이미 삭제된 경우 무시
            pass
        
        # 선택된 태그들 초기화
        self.selected_tags.clear()
        
        # 실제 UI 위젯들 제거
        for tag_text, tag_button in list(self.tag_buttons.items()):
            try:
                if tag_button and hasattr(tag_button, 'deleteLater'):
                    tag_button.deleteLater()
            except RuntimeError:
                pass
        self.tag_buttons.clear()
        
        # 카드 선택 관련 변수들 초기화
        self.card_selection_mode = False
        self.selected_cards.clear()
        
        # 이미지 프레임들 제거
        for image_path, frame in list(self.image_frames.items()):
            try:
                if frame and hasattr(frame, 'deleteLater'):
                    frame.deleteLater()
            except RuntimeError:
                pass
        self.image_frames.clear()
        
        # 오버레이 플러그인 사용
        from center_panel_overlay_plugin import CenterPanelOverlayPlugin
        overlay_plugin = CenterPanelOverlayPlugin(self.app_instance)
        overlay_plugin.hide_overlay_card("tag_editor")
    
        # 리모컨 숨기기
        if hasattr(self.app_instance, 'tag_stylesheet_editor_remote') and self.app_instance.tag_stylesheet_editor_remote:
            self.app_instance.tag_stylesheet_editor_remote.hide_remote()


    def on_drag_started(self, button):
        """드래그 시작 처리"""
        self.dragged_button = button
        
        # 원본 버튼의 인덱스 찾기
        self.original_button_index = self.selected_tags.index(button.tag_text)
        
        # 플레이스홀더 생성
        placeholder_size = button.size()
        self.placeholder_widget = PlaceholderWidget(placeholder_size)
        
        # FlowLayout에서 원본 버튼을 플레이스홀더로 교체
        if self.flow_layout:
            self.flow_layout.removeWidget(button)
            self.flow_layout.insertWidget(self.original_button_index, self.placeholder_widget)
        
        print(f"드래그 시작: {button.tag_text}, 인덱스: {self.original_button_index}")
    
    def on_drag_ended(self, button, new_index):
        """드래그 종료 처리"""
        print(f"on_drag_ended 호출: {button.tag_text}")
        print(f"dragged_button: {self.dragged_button is not None}")
        print(f"placeholder_widget: {self.placeholder_widget is not None}")
        
        if not self.dragged_button or not self.placeholder_widget:
            print("드래그 상태가 올바르지 않음, 종료")
            return
        
        # 마우스 위치에서 드롭 인덱스 계산
        if hasattr(self, 'tags_container') and self.tags_container:
            from PySide6.QtGui import QCursor
            global_pos = self.tags_container.mapFromGlobal(QCursor.pos())
            print(f"마우스 전역 위치: {QCursor.pos()}")
            print(f"컨테이너 내 상대 위치: {global_pos}")
            drop_index = self.flow_layout.get_drop_index(global_pos)
            print(f"계산된 드롭 인덱스: {drop_index}")
        else:
            drop_index = self.original_button_index
            print(f"컨테이너 없음, 원래 인덱스 사용: {drop_index}")
        
        # 드롭 인덱스가 유효한지 확인
        if drop_index < 0 or drop_index > len(self.selected_tags):
            print(f"드롭 인덱스 {drop_index}가 유효하지 않음, 원래 인덱스 {self.original_button_index}로 수정")
            drop_index = self.original_button_index
        
        # 드래그한 버튼이 원래 위치보다 뒤로 이동하는 경우 인덱스 조정
        if drop_index > self.original_button_index:
            drop_index -= 1
            print(f"뒤로 이동, 인덱스 조정: {drop_index}")
        
        print(f"최종 드롭 인덱스: {drop_index}, 원래 인덱스: {self.original_button_index}")
        
        # 플레이스홀더 제거
        if self.placeholder_widget and self.flow_layout:
            self.flow_layout.removeWidget(self.placeholder_widget)
            self.placeholder_widget.deleteLater()
            self.placeholder_widget = None
            print("플레이스홀더 제거 완료")
        
        # selected_tags 리스트 재정렬 (레이아웃 변경 전에)
        if drop_index != self.original_button_index:
            tag_text = button.tag_text
            
            # 타임머신 로깅을 위한 변경 전 상태 저장
            from timemachine_log import TM
            before_tags = self.selected_tags.copy()
            
            self.selected_tags.remove(tag_text)
            self.selected_tags.insert(drop_index, tag_text)
            
            print(f"태그 순서 변경: {tag_text}, {self.original_button_index} -> {drop_index}")
            print(f"새로운 selected_tags: {self.selected_tags}")
            
            # 타임머신에 태그 순서 변경 기록
            TM.log_change({
                "type": "tag_stylesheet_reorder",
                "tag": tag_text,
                "from_index": self.original_button_index,
                "to_index": drop_index,
                "before": before_tags,
                "after": self.selected_tags.copy()
            })
            
            # FlowLayout을 selected_tags 순서대로 재구성
            self.rebuild_flow_layout()
            
            # 이미지 그리드 업데이트 (순서 변경으로 인한 영향, 스로틀링 적용)
            self.schedule_update()
        else:
            # 원래 위치에 그대로 두기
            if self.flow_layout:
                self.flow_layout.insertWidget(self.original_button_index, button)
            print("원래 위치에 그대로 배치")
        
        # 드래그 상태 초기화
        self.dragged_button = None
        self.original_button_index = -1
        print("드래그 상태 초기화 완료")
    
    def rebuild_flow_layout(self):
        """FlowLayout을 selected_tags 순서대로 재구성"""
        if not self.flow_layout:
            return
        
        # 모든 위젯을 레이아웃에서 제거
        while self.flow_layout.count():
            child = self.flow_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        # selected_tags 순서대로 위젯을 다시 추가
        for tag_text in self.selected_tags:
            if tag_text in self.tag_buttons:
                self.flow_layout.addWidget(self.tag_buttons[tag_text])
        
        # 레이아웃 갱신
        self.flow_layout.invalidate()
        self.tags_container.updateGeometry()
        self.update_tags_container_height()
        
        # 태그 변경 시그널 발생
        self.tags_changed.emit(self.selected_tags.copy())


def create_tag_stylesheet_editor(app_instance):
    """태그 스타일시트 에디터 관리자 생성"""
    return TagStyleSheetEditor(app_instance)


# 커스텀 FlowLayout 사용


# 단독 실행을 위한 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
    from PySide6.QtCore import Qt
    
    class MockApp:
        """테스트용 Mock 앱 클래스"""
        def __init__(self):
            self.tag_edit_card = None
            self.original_splitter_sizes = None
            self.preview_card = None
            self.tag_tree_card = None
            self.advanced_search_card = None
            self.tagging_card = None
            self.center_splitter = None
            # 테스트용 태그 데이터
            self.all_tags = {
                "image1.jpg": ["tag1", "tag2", "tag3"],
                "image2.jpg": ["tag2", "tag4"],
                "image3.jpg": ["tag1", "tag5"],
                "image4.jpg": ["tag3", "tag4", "tag5"],
                "image5.jpg": ["tag1", "tag2", "tag3", "tag4", "tag5"],
            }
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Tag Stylesheet Editor Test")
            self.setGeometry(100, 100, 1000, 700)
            
            # Mock 앱 인스턴스
            self.mock_app = MockApp()
            
            # 중앙 위젯
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 레이아웃
            layout = QVBoxLayout(central_widget)
            
            # 테스트 버튼들
            test_buttons_layout = QHBoxLayout()
            
            for i in range(1, 6):
                tag_name = f"tag{i}"
                test_btn = QPushButton(f"Add {tag_name}")
                test_btn.clicked.connect(lambda checked=False, tag=tag_name: self.add_tag(tag))
                test_buttons_layout.addWidget(test_btn)
            
            layout.addLayout(test_buttons_layout)
            
            # 태그 스타일시트 에디터 생성
            self.tag_stylesheet_editor = create_tag_stylesheet_editor(self.mock_app)
            
            # Mock splitter 생성
            from PySide6.QtWidgets import QSplitter
            self.mock_app.center_splitter = QSplitter(Qt.Orientation.Vertical)
            layout.addWidget(self.mock_app.center_splitter)
            
            # Mock 카드들 생성
            self.mock_app.preview_card = QLabel("Preview Card")
            self.mock_app.preview_card.setStyleSheet("background-color: #333; color: white; padding: 20px;")
            self.mock_app.tag_tree_card = QLabel("Tag Tree Card")
            self.mock_app.tag_tree_card.setStyleSheet("background-color: #444; color: white; padding: 20px;")
            
            self.mock_app.center_splitter.addWidget(self.mock_app.preview_card)
            self.mock_app.center_splitter.addWidget(self.mock_app.tag_tree_card)
        
        def add_tag(self, tag_text):
            """태그 추가 테스트"""
            self.tag_stylesheet_editor.create_or_update_tag_edit_card(tag_text)
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())