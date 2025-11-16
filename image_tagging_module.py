"""
이미지 태깅 섹션 모듈
중앙 하단 패널의 태깅 기능을 담당
"""

from PySide6.QtWidgets import (QLabel, QVBoxLayout, QHBoxLayout, QWidget, 
                               QScrollArea, QProgressBar, QSizePolicy, QLineEdit, QPushButton, QLayout, QFrame, QCompleter, QApplication, QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
                               QStyledItemDelegate, QStyleOptionViewItem, QListView)

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
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRect, QMimeData, QStringListModel, QModelIndex, QTimer
from PySide6.QtGui import QDrag, QPainter, QFont
from PySide6.QtWidgets import QStyle
import csv
from pathlib import Path

# Danbooru 모듈 import (선택적)
try:
    from danbooru_module import get_danbooru_category_short, DANBOORU_AVAILABLE
except ImportError:
    DANBOORU_AVAILABLE = False
    def get_danbooru_category_short(tag):
        return ""


# load_tag_list 함수는 tag_autocomplete_plugin으로 이동됨


# 🎯 태그 호버 오버레이 (우클릭 메뉴와 동일한 디자인)
class TagHoverOverlay(QWidget):
    """태그에 마우스를 올렸을 때 표시되는 정보 오버레이"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        
        self.label = QLabel()
        self.label.setTextFormat(Qt.RichText)
        
        # 우클릭 메뉴의 item 스타일과 동일
        self.label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #E5E7EB;
                padding: 8px 12px;
                border-radius: 2px;
                font-size: 11px;
            }
        """)
        
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        # 우클릭 메뉴의 QMenu 배경 스타일과 동일
        self.setStyleSheet("""
            QWidget {
                background: #1A1B26;
                border: none;
                border-radius: 4px;
            }
        """)
        
        self.setMaximumWidth(400)
        self.hide()
    
    def show_for_tag(self, tag_name: str, position: QPoint):
        """태그 정보 표시 (자동완성과 동일한 방식)"""
        # 현재 호버 중인 위젯이 있는지 확인
        if _current_hover_widget is None:
            return
            
        try:
            from kr_danbooru_loader import kr_danbooru_loader
            
            if kr_danbooru_loader.is_available:
                tag_info = kr_danbooru_loader.get_tag_display_info(tag_name)
                
                # 자동완성과 동일한 방식으로 HTML 생성
                title = tag_info.get('title', tag_name)
                count = tag_info.get('count', '0')
                description = tag_info.get('description', '')
                keywords = tag_info.get('keywords', '')
                
                # 첫 번째 줄: 태그명 [카테고리] (굵게) + 사용 횟수 (오른쪽)
                html_parts = [f"<b>{title}</b>"]
                if count and count != '0':
                    html_parts[0] += f" <span style='color: #9CA3AF;'>({count})</span>"
                
                # 두 번째 줄: 설명 (자동완성과 동일한 길이 제한)
                if description:
                    description_text = f"설명: {description}"
                    if len(description_text) > 80:
                        description_text = description_text[:77] + "..."
                    html_parts.append(f"<span style='color: #D1D5DB; font-size: 10px;'>{description_text}</span>")
                
                # 세 번째 줄: 키워드 (자동완성과 동일한 방식)
                if keywords:
                    print(f"[툴팁 디버그] 키워드 발견: '{keywords}'")
                    # HTML에서 < > 괄호가 태그로 인식되지 않도록 HTML 엔티티로 변환
                    import html
                    escaped_keywords = html.escape(keywords)
                    keywords_text = f"키워드: {escaped_keywords}"
                    if len(keywords_text) > 80:
                        keywords_text = keywords_text[:77] + "..."
                    html_parts.append(f"<span style='color: #D1D5DB; font-size: 10px;'>{keywords_text}</span>")
                else:
                    print(f"[툴팁 디버그] 키워드 없음: '{tag_name}'")
                
                html = "<br>".join(html_parts)
            else:
                # Danbooru 로더가 없으면 기본 정보만 표시
                html = f"<b>{tag_name}</b>"
        except Exception as e:
            # 오류 시 기본 정보만 표시
            html = f"<b>{tag_name}</b>"
        
        self.label.setText(html)
        self.adjustSize()
        
        # 위치 조정
        final_position = QPoint(
            position.x() + 10,
            position.y() + 12
        )
        
        self.move(final_position)
        self.show()
        self.raise_()


# 전역 오버레이 인스턴스
_tag_hover_overlay = None
_current_hover_widget = None  # 현재 호버 중인 위젯 추적

def get_tag_hover_overlay():
    """전역 태그 호버 오버레이 인스턴스 반환"""
    global _tag_hover_overlay
    if _tag_hover_overlay is None:
        _tag_hover_overlay = TagHoverOverlay()
    return _tag_hover_overlay

def set_hover_widget(widget):
    """현재 호버 중인 위젯 설정"""
    global _current_hover_widget
    _current_hover_widget = widget

def clear_hover_widget():
    """호버 위젯 초기화"""
    global _current_hover_widget
    _current_hover_widget = None

def is_widget_hovering(widget):
    """특정 위젯이 현재 호버 중인지 확인"""
    return _current_hover_widget == widget


# KRDanbooruCompleterDelegate 클래스는 tag_autocomplete_plugin으로 이동됨


class TagButton(QPushButton):
    def __init__(self, tag_text, count=0):
        super().__init__()
        self.tag_text = tag_text
        self.count = count
        self.setCheckable(True)
        
        # 드래그 관련 속성
        self.drag_start_position = None
        self.is_dragging = False
        
        self.setup_ui()
    
    def setup_ui(self):
        self.setText(f"{self.tag_text}")
        self.setCursor(Qt.PointingHandCursor)
        self.update_style()
    
        self._base_text = self.text()
        self._last_wrap_width = -1
        self._apply_wrapped_text()
    def update_style(self):
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 #3B82F6, stop:1 #1D4ED8);
                    color: white;
                    border: none;
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 rgba(31,41,55,0.8), stop:1 rgba(17,24,39,0.6));
                    color: #9CA3AF;
                    border: 1px solid rgba(75,85,99,0.3);
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 rgba(55,65,81,0.8), stop:1 rgba(31,41,55,0.6));
                    color: #E5E7EB;
                    border-color: rgba(107,114,128,0.5);
                }
            """)
    
    def mousePressEvent(self, event):
        """마우스 누름 이벤트 - 드래그 시작 위치 저장"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트 - 드래그 시작"""
        if not (event.buttons() & Qt.LeftButton):
            return
        
        if self.drag_start_position is None:
            return
        
        # 드래그 거리 확인 (5픽셀 이상 이동 시 드래그 시작)
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 5):
            return
        
        if not self.is_dragging:
            self.is_dragging = True
            print(f"드래그 시작: {self.tag_text}")
            
            # 드래그 시작
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.tag_text)
            drag.setMimeData(mime_data)
            
            # 드래그 이미지 생성
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())
            
            # 드래그 실행
            drop_action = drag.exec(Qt.MoveAction)
            print(f"드래그 완료: action={drop_action}")
            
            # 드래그 완료 후 상태 초기화
            self.is_dragging = False
            self.drag_start_position = None
    
    def mouseReleaseEvent(self, event):
        """마우스 놓기 이벤트 - 드래그 상태 초기화"""
        if not self.is_dragging:
            # 드래그가 아닌 경우에만 클릭 이벤트 처리
            super().mouseReleaseEvent(event)
        self.is_dragging = False
        self.drag_start_position = None
    
    def enterEvent(self, event):
        """호버 시 - 태그 정보 오버레이 표시"""
        # 현재 호버 위젯 설정
        set_hover_widget(self)
        overlay = get_tag_hover_overlay()
        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        overlay.show_for_tag(self.tag_text, global_pos)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """호버 벗어남 - 오버레이 숨김"""
        # 호버 위젯 초기화
        clear_hover_widget()
        overlay = get_tag_hover_overlay()
        overlay.hide()
        super().leaveEvent(event)


    def _wrap_text_to_width(self, text: str, max_width: int) -> str:
        """Insert line breaks so QPushButton can display multi‑line text.
        Keeps everything else intact. Breaks anywhere if there is no space.
        """
        if not text:
            return ""
        fm = self.fontMetrics()
        lines = []
        current = ""
        for ch in text:
            if ch == "\n":
                lines.append(current)
                current = ""
                continue
            w = fm.horizontalAdvance(current + ch)
            if max_width > 0 and w > max_width and current:
                lines.append(current)
                current = ch
            else:
                current += ch
        if current:
            lines.append(current)
        return "\n".join(lines)

    def _apply_wrapped_text(self):
        # base text is what we want to show without inserted newlines
        base = getattr(self, "_base_text", self.text())
        # leave some horizontal padding
        available = max(120, (self.width() - 24) if self.width() > 0 else ((self.parent().width() - 24) if self.parent() else 220))
        wrapped = self._wrap_text_to_width(base, available)
        if self.text() != wrapped:
            super().setText(wrapped)
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reflow only when width meaningfully changes
        w = self.width()
        last = getattr(self, "_last_wrap_width", None)
        if last != w:
            self._last_wrap_width = w
            self._apply_wrapped_text()

class ConfidenceTagButton(QPushButton):
    """신뢰도가 표시되는 태그 버튼 (AI 태깅)"""
    tag_edited = Signal(str, str)  # old_tag, new_tag
    
    def __init__(self, text: str, confidence: float, parent=None):
        # LLaVA 태그인지 확인 (confidence == -1.0)
        if confidence == -1.0:
            # LLaVA 태그는 신뢰도 표시하지 않음, (Caption) 표시
            display_text = f"{text} (Caption)"
        else:
            # WD 태그는 신뢰도 표시
            if DANBOORU_AVAILABLE:
                category = get_danbooru_category_short(text)
                display_text = f"{text} ({confidence:.1%}) [{category}]"
            else:
                display_text = f"{text} ({confidence:.1%})"
        super().__init__(display_text, parent)
        self.tag_text = text
        self.confidence = confidence
        self.setCheckable(True)
        self.setMinimumHeight(28)
        self._base_text = display_text
        self._last_wrap_width = -1
        self._apply_wrapped_text()
        
        # 드래그 관련 속성
        self.drag_start_position = None
        self.is_dragging = False
        
        # 편집 모드 관련 속성
        self.is_editing = False
        self.edit_widget = None
        
        # 신뢰도에 따른 색상 설정 (필터 버튼과 비슷한 차분한 톤)
        if confidence == -1.0:
            # LLaVA 태그 - 은색
            color_scheme = {
                'normal': 'rgba(156,163,175,0.15)',
                'hover': 'rgba(156,163,175,0.25)',
                'checked': 'rgba(156,163,175,0.4)',
                'border': 'rgba(156,163,175,0.3)'
            }
        elif confidence >= 0.8:
            # 높은 신뢰도 (80% 이상) - 차분한 녹색
            color_scheme = {
                'normal': 'rgba(16,185,129,0.15)',
                'hover': 'rgba(16,185,129,0.25)',
                'checked': 'rgba(16,185,129,0.4)',
                'border': 'rgba(16,185,129,0.3)'
            }
        elif confidence >= 0.6:
            # 중간 신뢰도 (60-80%) - 차분한 노란색
            color_scheme = {
                'normal': 'rgba(245,158,11,0.15)',
                'hover': 'rgba(245,158,11,0.25)',
                'checked': 'rgba(245,158,11,0.4)',
                'border': 'rgba(245,158,11,0.3)'
            }
        else:
            # 낮은 신뢰도 (60% 미만) - 차분한 주황색
            color_scheme = {
                'normal': 'rgba(239,68,68,0.15)',
                'hover': 'rgba(239,68,68,0.25)',
                'checked': 'rgba(239,68,68,0.4)',
                'border': 'rgba(239,68,68,0.3)'
            }
        
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {color_scheme['normal']}, stop:1 {color_scheme['normal']});
                color: #E5E7EB;
                border: 1px solid {color_scheme['border']};
                border-radius: 0px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {color_scheme['hover']}, stop:1 {color_scheme['hover']});
                border: 1px solid {color_scheme['border']};
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {color_scheme['checked']}, stop:1 {color_scheme['checked']});
                color: white;
                border: 1px solid {color_scheme['checked']};
            }}
        """)
    
    def mousePressEvent(self, event):
        """마우스 누름 이벤트 - 드래그 시작 위치 저장"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트 - 드래그 시작"""
        if not (event.buttons() & Qt.LeftButton):
            return
        
        if self.drag_start_position is None:
            return
        
        # 드래그 거리 확인 (5픽셀 이상 이동 시 드래그 시작)
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 5):
            return
        
        if not self.is_dragging:
            self.is_dragging = True
            print(f"ConfidenceTagButton 드래그 시작: {self.tag_text}")
            
            # 드래그 시작
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.tag_text)  # 원본 태그 텍스트 사용
            drag.setMimeData(mime_data)
            
            # 드래그 이미지 생성
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())
            
            # 드래그 실행
            drop_action = drag.exec(Qt.MoveAction)
            print(f"ConfidenceTagButton 드래그 완료: action={drop_action}")
            
            # 드래그 완료 후 상태 초기화
            self.is_dragging = False
            self.drag_start_position = None
    
    def mouseReleaseEvent(self, event):
        """마우스 놓기 이벤트 - 드래그 상태 초기화"""
        if not self.is_dragging:
            # 드래그가 아닌 경우에만 클릭 이벤트 처리
            super().mouseReleaseEvent(event)
        self.is_dragging = False
        self.drag_start_position = None
    
    def enterEvent(self, event):
        """호버 시 - 태그 정보 오버레이 표시"""
        # 현재 호버 위젯 설정
        set_hover_widget(self)
        overlay = get_tag_hover_overlay()
        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        overlay.show_for_tag(self.tag_text, global_pos)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """호버 벗어남 - 오버레이 숨김"""
        # 호버 위젯 초기화
        clear_hover_widget()
        overlay = get_tag_hover_overlay()
        overlay.hide()
        super().leaveEvent(event)
    
    def contextMenuEvent(self, event):
        """우클릭 컨텍스트 메뉴 이벤트"""
        if self.is_editing:
            return
        
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        # 메뉴 스타일 설정 - 테두리 투명
        menu.setStyleSheet("""
            QMenu {
                background: #1A1B26;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                background: transparent;
                color: #E5E7EB;
                padding: 8px 12px;
                border-radius: 2px;
                font-size: 11px;
            }
            QMenu::item:selected {
                background: transparent;
                color: #60A5FA;
            }
        """)
        
        edit_action = menu.addAction("태그 편집")
        edit_action.triggered.connect(self.start_edit_mode)
        
        menu.exec(event.globalPos())
    
    def start_edit_mode(self):
        """편집 모드 시작"""
        if self.is_editing:
            return
        
        self.is_editing = True
        
        # 편집 위젯 생성
        self.edit_widget = QLineEdit(self.tag_text, self)
        self.edit_widget.setStyleSheet("""
            QLineEdit {
                background: rgba(31,41,55,0.9);
                color: #E5E7EB;
                border: 1px solid #3B82F6;
                font-size: 11px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border-color: #60A5FA;
            }
        """)
        
        # 편집 위젯을 버튼과 같은 크기로 설정
        self.edit_widget.setGeometry(self.rect())
        self.edit_widget.show()
        self.edit_widget.setFocus()
        self.edit_widget.selectAll()
        
        # 편집 완료/취소 이벤트 연결
        self.edit_widget.returnPressed.connect(self.finish_edit)
        self.edit_widget.editingFinished.connect(self.finish_edit)
        self.edit_widget.focusOutEvent = self.edit_focus_out
    
    def edit_focus_out(self, event):
        """편집 위젯 포커스 아웃 이벤트"""
        if self.is_editing:
            self.finish_edit()
        super().focusOutEvent(event)
    
    def finish_edit(self):
        """편집 완료"""
        print(f"🔧 [DEBUG] ConfidenceTagButton.finish_edit 호출됨")
        if not self.is_editing or not self.edit_widget:
            print(f"⚠️ [DEBUG] 편집 모드가 아니거나 편집 위젯이 없음")
            return
        
        new_tag = self.edit_widget.text().strip()
        print(f"🔧 [DEBUG] 새 태그: '{new_tag}', 기존 태그: '{self.tag_text}'")
        
        if new_tag and new_tag != self.tag_text:
            # 태그가 변경된 경우
            old_tag = self.tag_text
            self.tag_text = new_tag
            
            # 신뢰도 텍스트 업데이트
            if DANBOORU_AVAILABLE:
                category = get_danbooru_category_short(new_tag)
                confidence_text = f"{new_tag} ({self.confidence:.1%}) [{category}]"
            else:
                confidence_text = f"{new_tag} ({self.confidence:.1%})"
            
            self.setText(confidence_text)
            
            self._base_text = confidence_text
            self._apply_wrapped_text()
            # 편집 완료 신호 발생
            print(f"📡 [DEBUG] tag_edited 신호 발생: '{old_tag}' -> '{new_tag}'")
            self.tag_edited.emit(old_tag, new_tag)
            print(f"✅ [DEBUG] ConfidenceTagButton 태그 편집 완료: '{old_tag}' -> '{new_tag}'")
        else:
            print(f"⚠️ [DEBUG] 태그 변경 없음 또는 빈 태그")
        
        # 편집 모드 종료
        self.is_editing = False
        if self.edit_widget:
            self.edit_widget.deleteLater()
            self.edit_widget = None


    def _wrap_text_to_width(self, text: str, max_width: int) -> str:
        """Insert line breaks so QPushButton can display multi‑line text.
        Keeps everything else intact. Breaks anywhere if there is no space.
        """
        if not text:
            return ""
        fm = self.fontMetrics()
        lines = []
        current = ""
        for ch in text:
            if ch == "\n":
                lines.append(current)
                current = ""
                continue
            w = fm.horizontalAdvance(current + ch)
            if max_width > 0 and w > max_width and current:
                lines.append(current)
                current = ch
            else:
                current += ch
        if current:
            lines.append(current)
        return "\n".join(lines)

    def _apply_wrapped_text(self):
        # base text is what we want to show without inserted newlines
        base = getattr(self, "_base_text", self.text())
        # leave some horizontal padding
        available = max(120, (self.width() - 24) if self.width() > 0 else ((self.parent().width() - 24) if self.parent() else 220))
        wrapped = self._wrap_text_to_width(base, available)
        if self.text() != wrapped:
            super().setText(wrapped)
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reflow only when width meaningfully changes
        w = self.width()
        last = getattr(self, "_last_wrap_width", None)
        if last != w:
            self._last_wrap_width = w
            self._apply_wrapped_text()

class ManualTagButton(QPushButton):
    """수동 입력 태그 버튼"""
    tag_edited = Signal(str, str)  # old_tag, new_tag
    
    def __init__(self, text: str, is_trigger: bool = False, parent=None):
        # 태그 타입에 따른 표시 텍스트
        if is_trigger:
            display_text = f"{text} (trigger)"
            color_scheme = {
                'normal': 'rgba(139,92,246,0.15)',  # 보라색
                'hover': 'rgba(139,92,246,0.25)',
                'checked': 'rgba(139,92,246,0.4)',
                'border': 'rgba(139,92,246,0.3)'
            }
        else:
            display_text = f"{text} (used)"
            color_scheme = {
                'normal': 'rgba(59,130,246,0.15)',  # 파란색
                'hover': 'rgba(59,130,246,0.25)',
                'checked': 'rgba(59,130,246,0.4)',
                'border': 'rgba(59,130,246,0.3)'
            }
        
        super().__init__(display_text, parent)
        self.tag_text = text
        self.is_trigger = is_trigger
        self.setCheckable(True)
        self.setMinimumHeight(28)
        self._base_text = display_text
        self._last_wrap_width = -1
        self._apply_wrapped_text()
        
        # 드래그 관련 속성
        self.drag_start_position = None
        self.is_dragging = False
        
        # 편집 모드 관련 속성
        self.is_editing = False
        self.edit_widget = None
        
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {color_scheme['normal']}, stop:1 {color_scheme['normal']});
                color: #E5E7EB;
                border: 1px solid {color_scheme['border']};
                border-radius: 0px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {color_scheme['hover']}, stop:1 {color_scheme['hover']});
                border: 1px solid {color_scheme['border']};
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {color_scheme['checked']}, stop:1 {color_scheme['checked']});
                color: white;
                border: 1px solid {color_scheme['checked']};
            }}
        """)
    
    def mousePressEvent(self, event):
        """마우스 누름 이벤트 - 드래그 시작 위치 저장"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트 - 드래그 시작"""
        if not (event.buttons() & Qt.LeftButton):
            return
        
        if self.drag_start_position is None:
            return
        
        # 드래그 거리 확인 (5픽셀 이상 이동 시 드래그 시작)
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 5):
            return
        
        if not self.is_dragging:
            self.is_dragging = True
            print(f"ManualTagButton 드래그 시작: {self.tag_text}")
            
            # 드래그 시작
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.tag_text)  # 원본 태그 텍스트 사용
            drag.setMimeData(mime_data)
            
            # 드래그 이미지 생성
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())
            
            # 드래그 실행
            drop_action = drag.exec(Qt.MoveAction)
            print(f"ManualTagButton 드래그 완료: action={drop_action}")
            
            # 드래그 완료 후 상태 초기화
            self.is_dragging = False
            self.drag_start_position = None
    
    def mouseReleaseEvent(self, event):
        """마우스 놓기 이벤트 - 드래그 상태 초기화"""
        if not self.is_dragging:
            # 드래그가 아닌 경우에만 클릭 이벤트 처리
            super().mouseReleaseEvent(event)
        self.is_dragging = False
        self.drag_start_position = None
    
    def enterEvent(self, event):
        """호버 시 - 태그 정보 오버레이 표시"""
        # 현재 호버 위젯 설정
        set_hover_widget(self)
        overlay = get_tag_hover_overlay()
        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        overlay.show_for_tag(self.tag_text, global_pos)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """호버 벗어남 - 오버레이 숨김"""
        # 호버 위젯 초기화
        clear_hover_widget()
        overlay = get_tag_hover_overlay()
        overlay.hide()
        super().leaveEvent(event)
    
    def contextMenuEvent(self, event):
        """우클릭 컨텍스트 메뉴 이벤트"""
        if self.is_editing:
            return
        
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        # 메뉴 스타일 설정 - 테두리 투명
        menu.setStyleSheet("""
            QMenu {
                background: #1A1B26;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                background: transparent;
                color: #E5E7EB;
                padding: 8px 12px;
                border-radius: 2px;
                font-size: 11px;
            }
            QMenu::item:selected {
                background: transparent;
                color: #60A5FA;
            }
        """)
        
        edit_action = menu.addAction("태그 편집")
        edit_action.triggered.connect(self.start_edit_mode)
        
        menu.exec(event.globalPos())
    
    def start_edit_mode(self):
        """편집 모드 시작"""
        if self.is_editing:
            return
        
        self.is_editing = True
        
        # 편집 위젯 생성
        self.edit_widget = QLineEdit(self.tag_text, self)
        self.edit_widget.setStyleSheet("""
            QLineEdit {
                background: rgba(31,41,55,0.9);
                color: #E5E7EB;
                border: 1px solid #3B82F6;
                font-size: 11px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border-color: #60A5FA;
            }
        """)
        
        # 편집 위젯을 버튼과 같은 크기로 설정
        self.edit_widget.setGeometry(self.rect())
        self.edit_widget.show()
        self.edit_widget.setFocus()
        self.edit_widget.selectAll()
        
        # 편집 완료/취소 이벤트 연결
        self.edit_widget.returnPressed.connect(self.finish_edit)
        self.edit_widget.editingFinished.connect(self.finish_edit)
        self.edit_widget.focusOutEvent = self.edit_focus_out
    
    def edit_focus_out(self, event):
        """편집 위젯 포커스 아웃 이벤트"""
        if self.is_editing:
            self.finish_edit()
        super().focusOutEvent(event)
    
    def finish_edit(self):
        """편집 완료"""
        print(f"🔧 [DEBUG] ManualTagButton.finish_edit 호출됨")
        if not self.is_editing or not self.edit_widget:
            print(f"⚠️ [DEBUG] 편집 모드가 아니거나 편집 위젯이 없음")
            return
        
        new_tag = self.edit_widget.text().strip()
        print(f"🔧 [DEBUG] 새 태그: '{new_tag}', 기존 태그: '{self.tag_text}'")
        
        if new_tag and new_tag != self.tag_text:
            # 태그가 변경된 경우
            old_tag = self.tag_text
            self.tag_text = new_tag
            
            # 표시 텍스트 업데이트
            if self.is_trigger:
                display_text = f"{new_tag} (trigger)"
            else:
                display_text = f"{new_tag} (used)"
            
            self.setText(display_text)
            
            self._base_text = display_text
            self._apply_wrapped_text()
            # 편집 완료 신호 발생
            print(f"📡 [DEBUG] tag_edited 신호 발생: '{old_tag}' -> '{new_tag}'")
            self.tag_edited.emit(old_tag, new_tag)
            print(f"✅ [DEBUG] ManualTagButton 태그 편집 완료: '{old_tag}' -> '{new_tag}'")
        else:
            print(f"⚠️ [DEBUG] 태그 변경 없음 또는 빈 태그")
        
        # 편집 모드 종료
        self.is_editing = False
        if self.edit_widget:
            self.edit_widget.deleteLater()
            self.edit_widget = None


    def _wrap_text_to_width(self, text: str, max_width: int) -> str:
        """Insert line breaks so QPushButton can display multi‑line text.
        Keeps everything else intact. Breaks anywhere if there is no space.
        """
        if not text:
            return ""
        fm = self.fontMetrics()
        lines = []
        current = ""
        for ch in text:
            if ch == "\n":
                lines.append(current)
                current = ""
                continue
            w = fm.horizontalAdvance(current + ch)
            if max_width > 0 and w > max_width and current:
                lines.append(current)
                current = ch
            else:
                current += ch
        if current:
            lines.append(current)
        return "\n".join(lines)

    def _apply_wrapped_text(self):
        # base text is what we want to show without inserted newlines
        base = getattr(self, "_base_text", self.text())
        # leave some horizontal padding
        available = max(120, (self.width() - 24) if self.width() > 0 else ((self.parent().width() - 24) if self.parent() else 220))
        wrapped = self._wrap_text_to_width(base, available)
        if self.text() != wrapped:
            super().setText(wrapped)
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reflow only when width meaningfully changes
        w = self.width()
        last = getattr(self, "_last_wrap_width", None)
        if last != w:
            self._last_wrap_width = w
            self._apply_wrapped_text()

class ModernTagInput(QWidget):
    tagAdded = Signal(str, bool)  # tag, is_trigger
    tagAddedToAll = Signal(str, bool)  # tag, is_trigger
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_autocomplete()
    
    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.tag_input = SmartTagInput()
        self.tag_input.returnPressed.connect(self.add_tag)
        self.tag_input.tagsAdded.connect(self.add_multiple_tags)
        
        # 트리거 태그 토글 버튼
        self.trigger_btn = QPushButton("Trigger")
        self.trigger_btn.setFlat(True)
        self.trigger_btn.setFixedSize(60, 36)
        self.trigger_btn.setCursor(Qt.PointingHandCursor)
        self.trigger_btn.setToolTip("트리거 태그 모드 토글")
        self.trigger_btn.setCheckable(True)
        self.trigger_btn.setChecked(False)  # 기본값: 일반 태그
        self.trigger_btn.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 18px;
                font-size: 11px;
                font-weight: 500;
                padding: 0px 12px;
            }
            QPushButton:hover {
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:checked {
                background: #2D3748;
                border-color: #2D3748;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:checked:hover {
                background: #1A202C;
                border-color: #1A202C;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:pressed {
                padding: 0px 12px;
            }
        """)

        # 개별/일괄 입력 모드 토글 버튼
        self.mode_btn = QPushButton("개별")
        self.mode_btn.setFlat(True)
        self.mode_btn.setFixedSize(50, 36)
        self.mode_btn.setCursor(Qt.PointingHandCursor)
        self.mode_btn.setToolTip("개별/일괄 입력 모드 토글")
        self.mode_btn.setCheckable(True)
        self.mode_btn.setChecked(False)  # 기본값: 개별 모드
        self.mode_btn.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 18px;
                font-size: 12px;
                font-weight: 700;
                padding: 0px 12px;
            }
            QPushButton:hover {
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:checked {
                background: #2D3748;
                border-color: #2D3748;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:checked:hover {
                background: #1A202C;
                border-color: #1A202C;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:pressed {
                padding: 0px 12px;
            }
        """)
        self.mode_btn.toggled.connect(self.toggle_input_mode)
        
        # 입력 모드 상태 변수
        self.is_batch_mode = False

        top_row.addWidget(self.tag_input)
        top_row.addWidget(self.trigger_btn)
        top_row.addWidget(self.mode_btn)

        # 아래 행: 토큰 한도 스핀박스 (기본 77)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(6)
        bottom_row.addStretch()
        self.token_limit_spin = CustomSpinBox()
        self.token_limit_spin.setRange(1, 1000)
        self.token_limit_spin.setValue(77)
        # 텍스트 입력 높이에 맞춰 높이 통일
        try:
            target_h = int(self.tag_input.sizeHint().height())
            self.token_limit_spin.setFixedHeight(target_h)
        except Exception:
            pass
        self.token_limit_spin.setFixedWidth(72)
        self.token_limit_spin.setToolTip("Token limit for Active Tags")
        # 이미지 태깅 텍스트박스와 동일한 윤곽선 스타일 적용 (기본 그레이, 포커스만 블루)
        try:
            self.token_limit_spin.setStyleSheet(
                """
                QSpinBox {
                    background: rgba(26,27,38,0.8);
                    color: #F9FAFB;
                    border: 1px solid rgba(75,85,99,0.3);
                    font-size: 12px;
                    min-width: 60px;
                }
                QSpinBox:hover {
                    border: 1px solid rgba(75,85,99,0.5);
                    background: rgba(26,27,38,0.85);
                }
                QSpinBox:focus {
                    border: 2px solid #3B82F6;
                    background: rgba(26,27,38,0.9);
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    width: 20px; border: none; background: transparent; margin: 0; padding: 0;
                }
                QSpinBox::up-arrow, QSpinBox::down-arrow {
                    image: none; width: 0px; height: 0px; border: none; background: transparent; margin: 0; padding: 0;
                }
                """
            )
        except Exception:
            pass
        bottom_row.addWidget(self.token_limit_spin)
        # 토큰 한도 변경 시 썸네일 경고 전면 재계산
        def _on_limit_changed(_):
            try:
                from search_filter_grid_image_module import _is_token_over_limit
                if hasattr(self.parent(), 'image_flow_layout') and self.parent().image_flow_layout:
                    flow = self.parent().image_flow_layout
                    for i in range(flow.count()):
                        item = flow.itemAt(i)
                        if item and item.widget():
                            thumb = item.widget()
                            if hasattr(thumb, 'image_path'):
                                thumb._token_warning = _is_token_over_limit(self.parent(), thumb.image_path)
                                thumb.update_selection()
            except Exception:
                pass
        self.token_limit_spin.valueChanged.connect(_on_limit_changed)

        root.addLayout(top_row)
        root.addLayout(bottom_row)

    def setup_autocomplete(self):
        """자동완성 기능 설정 - 지연 로딩 적용"""
        # 초기에는 빈 모델로 설정 (빠른 초기화)
        self.original_tag_list = []
        self.tag_model = QStringListModel([])
        
        # QCompleter 생성 및 설정
        self.completer = QCompleter()
        self.completer.setModel(self.tag_model)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setMaxVisibleItems(4)  # 표시 개수 4개로 제한
        self.completer.setFilterMode(Qt.MatchContains)  # 중간부터 일치하는 것도 포함
        
        # QCompleter의 필터 모델을 커스텀으로 설정
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        
        # 한글 입력 지원을 위한 타이머 설정 (디바운싱)
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(500)  # 500ms 딜레이 (한글 조합 대기 - 증가)
        self.filter_timer.timeout.connect(self.do_filter_completions)
        
        # 페이징 관련 변수
        self.current_search_results = []  # 전체 검색 결과
        self.current_page_size = 50  # 한 번에 표시할 개수 (렉 방지를 위해 50으로 조정)
        self.current_displayed_count = 0  # 현재 표시된 개수
        self.is_loading_more = False  # 추가 로딩 중 플래그
        self.full_tag_list_loaded = False  # 전체 태그 목록 로드 여부
        
        # 커스텀 필터링을 위한 이벤트 연결 (타이머 사용)
        self.tag_input.textChanged.connect(self.schedule_filter)
        
        # 커스텀 델리게이트 설정
        from tag_autocomplete_plugin import KRDanbooruCompleterDelegate
        custom_delegate = KRDanbooruCompleterDelegate()
        self.completer.popup().setItemDelegate(custom_delegate)
        
        # 스크롤 이벤트 연결 (무한 스크롤)
        popup = self.completer.popup()
        scrollbar = popup.verticalScrollBar()
        scrollbar.valueChanged.connect(self.on_completer_scroll)
        
        # 지연 로딩: 1초 후에 태그 목록 로드
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.load_initial_tags)
        self.load_timer.start(1000)  # 1초 후 로드
        
        # popup 설정 - 설명/키워드는 자동 줄바꿈 (폭은 입력 필드에 맞춤)
        from PySide6.QtWidgets import QAbstractItemView
        popup.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        popup.setMaximumHeight(400)  # 높이를 늘려서 여러 줄 표시 가능하도록
        
        # 자동완성 팝업 스타일 설정 (전역 스크롤바 스타일 포함)
        self.completer.popup().setStyleSheet("""
                QListView {
                    background: rgba(17,17,27,0.95);
                    border: 1px solid rgba(75,85,99,0.3);
                    border-radius: 6px;
                    color: #F9FAFB;
                    font-size: 12px;
                    padding: 4px;
                }
                QListView::item {
                    padding: 6px 8px;
                    border-radius: 4px;
                    margin: 1px;
                }
                QListView::item:selected {
                    background: rgba(59,130,246,0.3);
                    color: #FFFFFF;
                }
                QListView::item:hover {
                    background: rgba(75,85,99,0.2);
                }
                QScrollBar:vertical {
                    background: rgba(26,27,38,0.8);
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(75,85,99,0.6);
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(75,85,99,0.8);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: rgba(26,27,38,1.0);
                }
            """)
            
            
        # LineEdit에 자동완성 연결
        self.tag_input.setCompleter(self.completer)
        
        print("자동완성 설정 완료 (지연 로딩 적용)")

    def load_initial_tags(self):
        """초기 태그 목록 로드 (지연 로딩)"""
        try:
            from tag_autocomplete_plugin import load_tag_list
            tag_list = load_tag_list()
            
            if tag_list:
                # 원본 태그 목록 저장 (필터링용)
                self.original_tag_list = tag_list.copy()
                
                # 모델 업데이트
                self.tag_model.setStringList(tag_list)
                
                print(f"초기 태그 목록 로드 완료: {len(tag_list)}개 태그")
            else:
                print("태그 목록 로드 실패")
        except Exception as e:
            print(f"초기 태그 로드 오류: {e}")

    def load_full_tags_if_needed(self):
        """필요시 전체 태그 목록 로드"""
        if not self.full_tag_list_loaded:
            try:
                from tag_autocomplete_plugin import load_full_tag_list
                full_tag_list = load_full_tag_list()
                
                if full_tag_list:
                    self.original_tag_list = full_tag_list.copy()
                    self.tag_model.setStringList(full_tag_list)
                    self.full_tag_list_loaded = True
                    print(f"전체 태그 목록 로드 완료: {len(full_tag_list)}개 태그")
            except Exception as e:
                print(f"전체 태그 로드 오류: {e}")

    def schedule_filter(self, text):
        """타이머를 사용한 필터링 예약 (한글 입력 지원)"""
        self.pending_filter_text = text
        self.filter_timer.stop()
        self.filter_timer.start()
    
    def on_completer_scroll(self, value):
        """자동완성 팝업 스크롤 이벤트 - 무한 스크롤"""
        try:
            scrollbar = self.completer.popup().verticalScrollBar()
            
            # 스크롤이 맨 아래에 도달했는지 확인
            if value >= scrollbar.maximum() - 10:  # 여유를 두고 10픽셀 전에 로드
                # 더 표시할 결과가 있는지 확인
                if self.current_displayed_count < len(self.current_search_results):
                    print(f"스크롤 끝 도달 - 다음 페이지 로드")
                    self.load_more_results()
        except Exception as e:
            print(f"스크롤 이벤트 오류: {e}")
    
    def load_more_results(self):
        """다음 페이지 결과 로드"""
        try:
            if self.is_loading_more:
                print("이미 로딩 중")
                return
            
            self.is_loading_more = True
            
            # 다음 페이지의 시작과 끝 인덱스 계산
            start_idx = self.current_displayed_count
            end_idx = min(start_idx + self.current_page_size, len(self.current_search_results))
            
            if start_idx >= len(self.current_search_results):
                print("더 이상 로드할 결과 없음")
                self.is_loading_more = False
                return
            
            # 새로운 결과를 기존 결과에 추가
            current_tags = self.tag_model.stringList()
            
            # 마지막 "더 보기" 항목 제거
            if current_tags and current_tags[-1].startswith("---"):
                current_tags = current_tags[:-1]
            
            new_tags = self.current_search_results[start_idx:end_idx]
            all_tags = current_tags + new_tags
            
            # 더 표시할 결과가 있으면 "더 보기" 항목 추가
            remaining = len(self.current_search_results) - end_idx
            if remaining > 0:
                all_tags.append(f"--- 더 보기 ({remaining}개 더) ---")
            
            # 모델 업데이트
            self.tag_model.setStringList(all_tags)
            self.current_displayed_count = end_idx
            
            print(f"추가 로드: {len(new_tags)}개 (총 {self.current_displayed_count}/{len(self.current_search_results)})")
            
            self.is_loading_more = False
            
        except Exception as e:
            print(f"추가 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            self.is_loading_more = False
    
    def do_filter_completions(self):
        """실제 필터링 수행"""
        if hasattr(self, 'pending_filter_text'):
            self.filter_completions(self.pending_filter_text)
    
    def filter_completions(self, text):
        """커스텀 필터링으로 우선순위 정렬 (KR_danbooru_tags.csv 기반) - 페이징 지원"""
        try:
            # 검색할 때만 전체 태그 목록 로드
            if not self.full_tag_list_loaded:
                self.load_full_tags_if_needed()
            
            from kr_danbooru_loader import kr_danbooru_loader
            
            print(f"필터링 검색: '{text}'")
            print(f"로더 상태: is_available={kr_danbooru_loader.is_available}, 태그 수={len(kr_danbooru_loader.tags)}")
            
            if not kr_danbooru_loader.is_available:
                print("로더가 사용 불가능합니다.")
                return
            
            if not text.strip():
                # 텍스트가 비어있으면 모든 태그를 카운트 순으로 표시
                all_tags = kr_danbooru_loader.get_autocomplete_list()
                print(f"빈 검색 - 전체 태그: {len(all_tags)}개")
                
                # 전체 결과 저장 및 첫 페이지만 표시
                self.current_search_results = all_tags
                self.current_displayed_count = min(self.current_page_size, len(all_tags))
                displayed_tags = all_tags[:self.current_displayed_count]
                
                # 더 표시할 결과가 있으면 "더 보기" 항목 추가
                if self.current_displayed_count < len(all_tags):
                    displayed_tags.append(f"--- 더 보기 ({len(all_tags) - self.current_displayed_count}개 더) ---")
                
                self.tag_model.setStringList(displayed_tags)
                print(f"표시: {self.current_displayed_count}/{len(all_tags)}개")
                return
            
            # KR_danbooru_loader의 검색 기능 사용
            search_results = kr_danbooru_loader.search_tags(text)
            print(f"검색 결과: {len(search_results)}개")
            
            # 검색 결과를 태그명만 추출
            filtered_tags = [name for name, _, _ in search_results]
            
            # 전체 결과 저장 및 첫 페이지만 표시
            self.current_search_results = filtered_tags
            self.current_displayed_count = min(self.current_page_size, len(filtered_tags))
            displayed_tags = filtered_tags[:self.current_displayed_count]
            
            # 더 표시할 결과가 있으면 "더 보기" 항목 추가
            if self.current_displayed_count < len(filtered_tags):
                displayed_tags.append(f"--- 더 보기 ({len(filtered_tags) - self.current_displayed_count}개 더) ---")
            
            # 모델 업데이트
            self.tag_model.setStringList(displayed_tags)
            
            # QCompleter 강제 새로고침
            self.completer.setModel(self.tag_model)
            self.completer.complete()  # 자동완성 팝업 강제 표시
            
            print(f"표시: {self.current_displayed_count}/{len(filtered_tags)}개")
            
        except Exception as e:
            print(f"필터링 오류: {e}")
            import traceback
            traceback.print_exc()

    def add_tag(self):
        """태그 추가 - 모드에 따라 개별/일괄 처리"""
        tag = self.tag_input.text().strip()
        
        # "더 보기" 항목은 무시
        if tag.startswith("---"):
            self.tag_input.clear()
            return
        
        if tag:
            is_trigger = self.trigger_btn.isChecked()
            if self.is_batch_mode:
                self.tagAddedToAll.emit(tag, is_trigger)
            else:
                self.tagAdded.emit(tag, is_trigger)
            self.tag_input.clear()
    
    def toggle_input_mode(self, checked):
        """입력 모드 토글"""
        self.is_batch_mode = checked
        if checked:
            self.mode_btn.setText("일괄")
            self.mode_btn.setToolTip("일괄 입력 모드 - 모든 검색된 이미지에 태그 추가")
        else:
            self.mode_btn.setText("개별")
            self.mode_btn.setToolTip("개별 입력 모드 - 선택된 이미지에만 태그 추가")
        print(f"입력 모드 변경: {'일괄' if checked else '개별'}")
    
    def add_multiple_tags(self, tags):
        """여러 태그를 한 번에 추가 - 모드에 따라 개별/일괄 처리"""
        print(f"여러 태그 추가: {tags} (모드: {'일괄' if self.is_batch_mode else '개별'})")
        is_trigger = self.trigger_btn.isChecked()
        for tag in tags:
            if tag.strip():
                if self.is_batch_mode:
                    self.tagAddedToAll.emit(tag.strip(), is_trigger)
                else:
                    self.tagAdded.emit(tag.strip(), is_trigger)
    
    def parse_tags_from_text(self, text):
        """텍스트에서 태그들을 분리하여 리스트로 반환"""
        import re
        
        # 줄바꿈, 콤마, 세미콜론으로 분리
        # 정규표현식으로 여러 구분자 동시 처리
        tags = re.split(r'[\n\r,;]+', text)
        
        # 빈 문자열 제거 및 공백 제거
        tags = [tag.strip() for tag in tags if tag.strip()]
        
        return tags


class SmartTagInput(QLineEdit):
    """스마트 태그 입력 필드 - 붙여넣기 시 태그 자동 분리"""
    tagsAdded = Signal(list)  # 여러 태그 추가 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.last_text = ""  # 이전 텍스트 저장
        self.preedit_text = ""  # 한글 조합 중인 텍스트
        self.textChanged.connect(self.on_text_changed)
    
    def setup_ui(self):
        self.setPlaceholderText("Add custom tag...")
        # 스핀박스와 동일한 배경/윤곽선/패딩으로 통일
        self.setStyleSheet("""
            QLineEdit {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
            }
            QLineEdit:hover {
                border: 1px solid rgba(75,85,99,0.5);
                background: rgba(26,27,38,0.85);
            }
            QLineEdit:focus {
                border: 2px solid #3B82F6;
                background: rgba(26,27,38,0.9);
            }
        """)
    
    def keyPressEvent(self, event):
        """키 입력 처리 - 엔터 키 시 자동완성 동작 완전 차단"""
        from PySide6.QtCore import Qt
        
        # 엔터 키를 눌렀을 때
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 자동완성 팝업이 열려있으면 닫기
            completer = self.completer()
            if completer and completer.popup() and completer.popup().isVisible():
                completer.popup().hide()
            
            # 이벤트를 소비하여 QCompleter가 자동완성을 수행하지 못하도록 함
            event.accept()
            
            # returnPressed 시그널을 직접 발생시켜서 현재 입력된 텍스트만 사용
            # 이렇게 하면 자동완성 없이 현재 텍스트만 태그로 추가됨
            self.returnPressed.emit()
            return
        
        # 기본 동작 수행
        super().keyPressEvent(event)
    
    def inputMethodEvent(self, event):
        """한글 입력 처리 - 조합 중인 텍스트도 감지"""
        super().inputMethodEvent(event)
        # preedit string (조합 중인 텍스트) 저장
        self.preedit_text = event.preeditString()
        # 부모 위젯의 필터링 트리거 (조합 중인 텍스트 포함)
        if hasattr(self.parent(), 'schedule_filter'):
            full_text = self.text() + self.preedit_text
            self.parent().schedule_filter(full_text)
    
    def get_full_text(self):
        """완성된 텍스트 + 조합 중인 텍스트 반환"""
        return self.text() + self.preedit_text
    
    def on_text_changed(self, text):
        """텍스트 변경 감지 - 구분자 입력 시 태그 자동 분리"""
        # 한글 조합이 완료되면 preedit_text 초기화
        self.preedit_text = ""
        # 줄바꿈, 콤마, 세미콜론이 포함되어 있는지 확인
        if any(sep in text for sep in ['\n', '\r', ',', ';']):
            print(f"구분자 감지: '{text}'")
            tags = self.parse_tags_from_text(text)
            if len(tags) > 0:  # 빈 태그가 아닌 경우에만 처리
                print(f"  {len(tags)}개 태그로 분리: {tags}")
                self.tagsAdded.emit(tags)
                self.clear()
                self.last_text = ""
                return
        
        self.last_text = text
    
    def parse_tags_from_text(self, text):
        """텍스트에서 태그들을 분리하여 리스트로 반환"""
        import re
        
        # 줄바꿈, 콤마, 세미콜론으로 분리
        # 정규표현식으로 여러 구분자 동시 처리
        tags = re.split(r'[\n\r,;]+', text)
        
        # 빈 문자열 제거 및 공백 제거
        tags = [tag.strip() for tag in tags if tag.strip()]
        
        return tags


class QFlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
    
    def addItem(self, item):
        self._items.append(item)
    
    def count(self):
        return len(self._items)
    
    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        # patched: avoid large minimum width, so horizontal scrollbar never appears
        margins = self.contentsMargins()
        return QSize(margins.left() + margins.right(), margins.top() + margins.bottom() + 1)
    
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect)
    
    def doLayout(self, rect):
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        line_height = 0
        spacing = 6
        
        for item in self._items:
            widget = item.widget()
            if widget:
                space_x = spacing + widget.sizeHint().width()
                space_y = spacing + widget.sizeHint().height()
                
                next_x = x + space_x
                if next_x > rect.right() - margins.right() and line_height > 0:
                    x = rect.x() + margins.left()
                    y = y + line_height + spacing
                    next_x = x + space_x
                    line_height = 0
                
                item.setGeometry(QRect(QPoint(x, y), QSize(min(widget.sizeHint().width(), rect.right() - margins.right() - x), widget.sizeHint().height())))
                x = next_x
                line_height = max(line_height, space_y)


def create_tagging_section(app_instance, SectionCard):
    """태깅 섹션 생성"""
    # 태깅 카드 생성
    tagging_card = SectionCard("TAGGING")
    
    # AI 태깅 진행률 표시
    app_instance.ai_progress_layout = QVBoxLayout()
    app_instance.ai_progress_layout.setContentsMargins(0, 0, 0, 0)
    app_instance.ai_progress_layout.setSpacing(4)
    
    app_instance.ai_progress_label = QLabel("")
    app_instance.ai_progress_label.setStyleSheet("""
        color: #9CA3AF;
        font-size: 11px;
        font-weight: 500;
    """)
    app_instance.ai_progress_label.hide()
    
    app_instance.ai_progress_bar = QProgressBar()
    app_instance.ai_progress_bar.setStyleSheet("""
        QProgressBar {
            border: 1px solid rgba(75,85,99,0.3);
            border-radius: 6px;
            text-align: center;
            background: rgba(17,17,27,0.9);
            color: #F9FAFB;
            font-size: 11px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3B82F6, stop:1 #1D4ED8);
            border-radius: 5px;
        }
    """)
    app_instance.ai_progress_bar.hide()
    
    app_instance.ai_progress_layout.addWidget(app_instance.ai_progress_label)
    app_instance.ai_progress_layout.addWidget(app_instance.ai_progress_bar)
    
    tagging_card.body.addLayout(app_instance.ai_progress_layout)
    
    # Tag input
    app_instance.tag_input_widget = ModernTagInput()
    # 시그널 연결은 메인 파일에서 처리
    tagging_card.body.addWidget(app_instance.tag_input_widget)
    # 토큰 한도 변경 시 썸네일 경고 즉시 재계산
    try:
        if hasattr(app_instance.tag_input_widget, 'token_limit_spin') and app_instance.tag_input_widget.token_limit_spin:
            app_instance.tag_input_widget.token_limit_spin.valueChanged.connect(lambda _: _update_thumbnail_token_warnings(app_instance))
    except Exception:
        pass
    
    # Current image tags section
    current_tags_label = QLabel("Current Image Tags")
    current_tags_label.setStyleSheet("""
        color: #9CA3AF;
        font-size: 11px;
        font-weight: 600;
        margin-top: 8px;
    """)
    tagging_card.body.addWidget(current_tags_label)
    
    # 태그 패널을 반반으로 나누기
    tags_split_layout = QHBoxLayout()
    tags_split_layout.setSpacing(8)
    
    # 왼쪽: 현재 활성 태그
    active_tags_widget = QWidget()
    active_tags_widget.setStyleSheet("""
        QWidget {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(20,25,35,0.3), stop:1 rgba(25,30,40,0.2));
            border: 1px solid rgba(75,85,99,0.2);
            border-radius: 6px;
        }
    """)
    active_tags_layout = QVBoxLayout(active_tags_widget)
    active_tags_layout.setContentsMargins(8, 8, 8, 8)
    active_tags_layout.setSpacing(4)
    
    active_label = QLabel("✓ Active Tags")
    active_label.setStyleSheet("""
        color: #10B981;
        font-size: 10px;
        font-weight: 600;
    """)
    active_tags_layout.addWidget(active_label)
    # CLIP 토큰 수 실시간 표시용 업데이트 함수 바인딩
    def _update_active_label_with_tokens():
        try:
            from tokenizer_plugin import count_clip_tokens_for_tags
            tokens = count_clip_tokens_for_tags(getattr(app_instance, 'current_tags', []))
            if tokens is None:
                active_label.setText("✓ Active Tags")
            else:
                active_label.setText(f"✓ Active Tags (Tokens: {tokens})")
        except Exception:
            active_label.setText("✓ Active Tags")
    app_instance.update_active_tokens = _update_active_label_with_tokens
    # 초기 1회 호출
    _update_active_label_with_tokens()
    
    # Create scroll area for active tags
    app_instance.active_tags_scroll = QScrollArea()
    app_instance.active_tags_scroll.setWidgetResizable(True)  # True로 설정하여 상대사이즈
    app_instance.active_tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    app_instance.active_tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # 무조건 스크롤바 표시
    app_instance.active_tags_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 상대사이즈로 크기 조정 가능
    app_instance.active_tags_scroll.setMinimumHeight(150)  # 최소 높이 설정
    app_instance.active_tags_scroll.setMaximumHeight(800)  # 최대 높이 설정 (2배)
    app_instance.active_tags_scroll.setStyleSheet("""
        QScrollArea {
            background: transparent;
            border: none;
            border-radius: 4px;
        }
        QScrollArea > QWidget > QWidget {
            background: transparent;
            border: none;
        }
    """)
    
    app_instance.active_tags_container = QWidget()
    app_instance.active_tags_container.setAcceptDrops(True)
    app_instance.active_tags_container.setMinimumSize(0, 800)  # 컨테이너 최소 크기 설정 (폭 감소)
    app_instance.active_tags_layout = QFlowLayout(app_instance.active_tags_container)
    
    app_instance.active_tags_layout.setContentsMargins(8, 8, 16, 8)
    # Set the container as the scroll area's widget
    app_instance.active_tags_scroll.setWidget(app_instance.active_tags_container)
    active_tags_layout.addWidget(app_instance.active_tags_scroll)
    
    # 드롭 이벤트 연결
    app_instance.active_tags_container.dragEnterEvent = lambda event: drag_enter_event(app_instance, event)
    app_instance.active_tags_container.dragMoveEvent = lambda event: drag_move_event(app_instance, event)
    app_instance.active_tags_container.dropEvent = lambda event: drop_event(app_instance, event)
    
    # 오른쪽: 취소된 태그
    removed_tags_widget = QWidget()
    removed_tags_widget.setStyleSheet("""
        QWidget {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(20,25,35,0.3), stop:1 rgba(25,30,40,0.2));
            border: 1px solid rgba(75,85,99,0.2);
            border-radius: 6px;
        }
    """)
    removed_tags_layout = QVBoxLayout(removed_tags_widget)
    removed_tags_layout.setContentsMargins(8, 8, 8, 8)
    removed_tags_layout.setSpacing(4)
    
    removed_label = QLabel("✗ Removed Tags")
    removed_label.setStyleSheet("""
        color: #EF4444;
        font-size: 10px;
        font-weight: 600;
    """)
    removed_tags_layout.addWidget(removed_label)
    # Active/Removed 토큰 라벨 동시 갱신 함수
    def _update_token_labels():
        try:
            from tokenizer_plugin import count_clip_tokens_for_tags
            active_tokens = count_clip_tokens_for_tags(getattr(app_instance, 'current_tags', []))
            removed_tokens = count_clip_tokens_for_tags(getattr(app_instance, 'removed_tags', []))
            if active_tokens is None:
                active_label.setText("✓ Active Tags")
            else:
                active_label.setText(f"✓ Active Tags (Tokens: {active_tokens})")
            if removed_tokens is None:
                removed_label.setText("✗ Removed Tags")
            else:
                removed_label.setText(f"✗ Removed Tags (Tokens: {removed_tokens})")
        except Exception:
            active_label.setText("✓ Active Tags")
            removed_label.setText("✗ Removed Tags")
    app_instance.update_token_labels = _update_token_labels
    _update_token_labels()
    
    # Create scroll area for removed tags
    app_instance.removed_tags_scroll = QScrollArea()
    app_instance.removed_tags_scroll.setWidgetResizable(True)  # True로 설정하여 상대사이즈
    app_instance.removed_tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    app_instance.removed_tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # 무조건 스크롤바 표시
    app_instance.removed_tags_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 상대사이즈로 크기 조정 가능
    app_instance.removed_tags_scroll.setMinimumHeight(150)  # 최소 높이 설정
    app_instance.removed_tags_scroll.setMaximumHeight(800)  # 최대 높이 설정 (2배)
    app_instance.removed_tags_scroll.setStyleSheet("""
        QScrollArea {
            background: transparent;
            border: none;
            border-radius: 4px;
        }
        QScrollArea > QWidget > QWidget {
            background: transparent;
            border: none;
        }
    """)
    
    app_instance.removed_tags_container = QWidget()
    app_instance.removed_tags_container.setMinimumSize(0, 800)  # 컨테이너 최소 크기 설정 (폭 감소)
    app_instance.removed_tags_layout = QFlowLayout(app_instance.removed_tags_container)
    
    app_instance.removed_tags_layout.setContentsMargins(8, 8, 16, 8)
    # Set the container as the scroll area's widget
    app_instance.removed_tags_scroll.setWidget(app_instance.removed_tags_container)
    removed_tags_layout.addWidget(app_instance.removed_tags_scroll)
    
    # 반반으로 나누기
    tags_split_layout.addWidget(active_tags_widget, 1)
    tags_split_layout.addWidget(removed_tags_widget, 1)
    
    tagging_card.body.addLayout(tags_split_layout)
    
    return tagging_card


def update_current_tags_display(app_instance):
    """현재 이미지의 태그들을 중앙 패널에 표시 (신뢰도 포함)"""
    print(f"🔄 [DEBUG] update_current_tags_display 호출: current_tags={app_instance.current_tags}")
    print(f"🔄 [DEBUG] removed_tags={app_instance.removed_tags}")
    
    # 기존 활성 태그들 제거 (호버 상태 정리 포함)
    while app_instance.active_tags_layout.count():
        child = app_instance.active_tags_layout.takeAt(0)
        if child.widget():
            # 호버 상태 정리
            if is_widget_hovering(child.widget()):
                clear_hover_widget()
                overlay = get_tag_hover_overlay()
                overlay.hide()
            child.widget().deleteLater()
    
    # 기존 취소된 태그들 제거 (호버 상태 정리 포함)
    while app_instance.removed_tags_layout.count():
        child = app_instance.removed_tags_layout.takeAt(0)
        if child.widget():
            # 호버 상태 정리
            if is_widget_hovering(child.widget()):
                clear_hover_widget()
                overlay = get_tag_hover_overlay()
                overlay.hide()
            child.widget().deleteLater()
    
    # 현재 이미지의 태그들을 표시
    if app_instance.current_image:
        # 신뢰도 정보가 있으면 사용, 없으면 기본 표시
        if app_instance.current_image in app_instance.tag_confidence:
            tags_with_scores = app_instance.tag_confidence[app_instance.current_image]
            
            # current_tags 순서대로 활성 태그들 표시
            for tag in app_instance.current_tags:
                # 수동 입력 태그인지 확인
                is_manual = hasattr(app_instance, 'manual_tag_info') and tag in app_instance.manual_tag_info
                # LLaVA 태그인지 확인
                is_llava = hasattr(app_instance, 'llava_tag_info') and tag in app_instance.llava_tag_info
                
                if is_manual:
                    # 수동 입력 태그 - ManualTagButton 사용
                    is_trigger = app_instance.manual_tag_info[tag]
                    manual_btn = ManualTagButton(tag, is_trigger)
                    manual_btn.setChecked(True)
                    manual_btn.clicked.connect(lambda checked, b=manual_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    manual_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.active_tags_layout.addWidget(manual_btn)
                    print(f"수동 입력 활성 태그 추가: {tag} (trigger: {is_trigger})")
                elif is_llava:
                    # LLaVA 태그 - ConfidenceTagButton 사용 (score = -1.0)
                    confidence_btn = ConfidenceTagButton(tag, -1.0)
                    confidence_btn.setChecked(True)
                    confidence_btn.clicked.connect(lambda checked, b=confidence_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    confidence_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.active_tags_layout.addWidget(confidence_btn)
                    print(f"LLaVA 활성 태그 추가: {tag}")
                else:
                    # WD AI 태깅 태그 - ConfidenceTagButton 사용
                    score = 1.0  # 기본값
                    for t, s in tags_with_scores:
                        if t == tag:
                            score = s
                            break
                    
                    confidence_btn = ConfidenceTagButton(tag, score)
                    confidence_btn.setChecked(True)
                    confidence_btn.clicked.connect(lambda checked, b=confidence_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    confidence_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.active_tags_layout.addWidget(confidence_btn)
                    print(f"WD AI 태깅 활성 태그 추가: {tag}")
            
            # 취소된 태그들 표시
            for tag in app_instance.removed_tags:
                # 수동 입력 태그인지 확인
                is_manual = hasattr(app_instance, 'manual_tag_info') and tag in app_instance.manual_tag_info
                # LLaVA 태그인지 확인
                is_llava = hasattr(app_instance, 'llava_tag_info') and tag in app_instance.llava_tag_info
                
                if is_manual:
                    # 수동 입력 태그 - ManualTagButton 사용 (비활성화 상태)
                    is_trigger = app_instance.manual_tag_info[tag]
                    manual_btn = ManualTagButton(tag, is_trigger)
                    manual_btn.setChecked(False)
                    manual_btn.clicked.connect(lambda checked, b=manual_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    manual_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.removed_tags_layout.addWidget(manual_btn)
                    print(f"수동 입력 취소된 태그 추가: {tag} (trigger: {is_trigger})")
                elif is_llava:
                    # LLaVA 태그 - ConfidenceTagButton 사용 (비활성화 상태, score = -1.0)
                    confidence_btn = ConfidenceTagButton(tag, -1.0)
                    confidence_btn.setChecked(False)  # 리무버 상태로 설정
                    confidence_btn.clicked.connect(lambda checked, b=confidence_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    confidence_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.removed_tags_layout.addWidget(confidence_btn)
                    print(f"LLaVA 취소된 태그 추가: {tag}")
                else:
                    # WD AI 태깅 태그 - ConfidenceTagButton 사용 (리무버 상태)
                    score = 1.0  # 기본값
                    for t, s in tags_with_scores:
                        if t == tag:
                            score = s
                            break
                    
                    confidence_btn = ConfidenceTagButton(tag, score)
                    confidence_btn.setChecked(False)  # 리무버 상태로 설정
                    confidence_btn.clicked.connect(lambda checked, b=confidence_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    confidence_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.removed_tags_layout.addWidget(confidence_btn)
                    print(f"WD AI 태깅 취소된 태그 추가: {tag}")
        else:
            # 신뢰도 정보가 없는 경우 기본 표시
            for tag in app_instance.current_tags:
                # 수동 입력 태그인지 확인
                is_manual = hasattr(app_instance, 'manual_tag_info') and tag in app_instance.manual_tag_info
                
                if is_manual:
                    # 수동 입력 태그 - ManualTagButton 사용
                    is_trigger = app_instance.manual_tag_info[tag]
                    manual_btn = ManualTagButton(tag, is_trigger)
                    manual_btn.setChecked(True)
                    manual_btn.clicked.connect(lambda checked, b=manual_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    manual_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.active_tags_layout.addWidget(manual_btn)
                    print(f"수동 입력 기본 활성 태그 추가: {tag} (trigger: {is_trigger})")
                else:
                    # AI 태깅 태그 - TagButton 사용
                    btn = TagButton(tag)
                    btn.setChecked(True)
                    btn.clicked.connect(lambda checked, b=btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    app_instance.active_tags_layout.addWidget(btn)
                    print(f"AI 태깅 기본 활성 태그 추가: {tag}")
            
            for tag in app_instance.removed_tags:
                # 수동 입력 태그인지 확인
                is_manual = hasattr(app_instance, 'manual_tag_info') and tag in app_instance.manual_tag_info
                # LLaVA 태그인지 확인
                is_llava = hasattr(app_instance, 'llava_tag_info') and tag in app_instance.llava_tag_info
                
                if is_manual:
                    # 수동 입력 태그 - ManualTagButton 사용 (비활성화 상태)
                    is_trigger = app_instance.manual_tag_info[tag]
                    manual_btn = ManualTagButton(tag, is_trigger)
                    manual_btn.setChecked(False)
                    manual_btn.clicked.connect(lambda checked, b=manual_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    manual_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.removed_tags_layout.addWidget(manual_btn)
                    print(f"수동 입력 기본 취소된 태그 추가: {tag} (trigger: {is_trigger})")
                elif is_llava:
                    # LLaVA 태그 - ConfidenceTagButton 사용 (비활성화 상태, score = -1.0)
                    confidence_btn = ConfidenceTagButton(tag, -1.0)
                    confidence_btn.setChecked(False)  # 리무버 상태로 설정
                    confidence_btn.clicked.connect(lambda checked, b=confidence_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    confidence_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.removed_tags_layout.addWidget(confidence_btn)
                    print(f"LLaVA 기본 취소된 태그 추가: {tag}")
                else:
                    # AI 태깅 태그 - ConfidenceTagButton 사용 (리무버 상태)
                    confidence_btn = ConfidenceTagButton(tag, 0.0)
                    confidence_btn.setChecked(False)  # 리무버 상태로 설정
                    confidence_btn.clicked.connect(lambda checked, b=confidence_btn: toggle_current_tag(app_instance, b.tag_text, checked))
                    confidence_btn.tag_edited.connect(lambda old_tag, new_tag: handle_tag_edit(app_instance, old_tag, new_tag))
                    app_instance.removed_tags_layout.addWidget(confidence_btn)
                    print(f"AI 태깅 기본 취소된 태그 추가: {tag}")
    
    # 레이아웃 강제 업데이트
    app_instance.active_tags_layout.update()
    app_instance.removed_tags_layout.update()
    app_instance.active_tags_container.update()
    app_instance.removed_tags_container.update()
    
    print("레이아웃 업데이트 완료")
    # 토큰 수 라벨 갱신
    if hasattr(app_instance, 'update_token_labels'):
        try:
            app_instance.update_token_labels()
        except Exception:
            pass
    # 썸네일 토큰 경고 상태 즉시 갱신
    try:
        _update_thumbnail_token_warnings(app_instance)
    except Exception:
        pass

def _update_thumbnail_token_warnings(app_instance):
    """모든 이미지 썸네일에 대해 토큰 한도 초과 경고를 즉시 재계산/반영"""
    try:
        flow = getattr(app_instance, 'image_flow_layout', None)
        if not flow:
            return
        # 한도는 search_filter_grid_image_module._is_token_over_limit 내부에서 스핀박스값 참조
        from search_filter_grid_image_module import _is_token_over_limit
        for i in range(flow.count()):
            item = flow.itemAt(i)
            if item and item.widget():
                thumb = item.widget()
                if hasattr(thumb, 'image_path'):
                    thumb._token_warning = _is_token_over_limit(app_instance, thumb.image_path)
                    thumb.update_selection()
    except Exception as e:
        print(f"⚠️ 썸네일 토큰 경고 업데이트 실패: {e}")


def toggle_current_tag(app_instance, tag, checked, image_path=None):
    """현재 이미지의 태그 활성화/비활성화"""
    # 질문 시점 이미지 고정을 위한 image_path 파라미터 추가
    image = image_path or app_instance.current_image
    if not image:
        return
        
    # 이미지별 리무버 태그 저장소 초기화
    if not hasattr(app_instance, 'image_removed_tags'):
        app_instance.image_removed_tags = {}
    if image not in app_instance.image_removed_tags:
        app_instance.image_removed_tags[image] = []
    
    if checked:
        # 태그 활성화
        # 타임머신: 단일 토글도 1 작업으로 기록(암묵 트랜잭션)
        try:
            from timemachine_log import TM
            TM.log_change({
                "type": "tag_toggle_on",
                "image": image,
                "tag": tag,
            })
        except Exception:
            pass
        
        # 상호 배타 보장: 이미지별 리무버 태그에서 제거
        if tag in app_instance.image_removed_tags[image]:
            app_instance.image_removed_tags[image].remove(tag)
        
        # 현재 표시 이미지일 때만 UI 동기화
        if image == app_instance.current_image:
            # 현재 이미지의 리무버 태그에서도 제거 (UI 동기화용)
            if tag in getattr(app_instance, 'removed_tags', []):
                try:
                    app_instance.removed_tags.remove(tag)
                except Exception:
                    pass
                    
            if tag not in app_instance.current_tags:
                app_instance.current_tags.append(tag)
        # 글로벌 태그 관리 플러그인 사용
        from global_tag_manager import add_global_tag
        from all_tags_manager import add_tag_to_all_tags
        
        # is_trigger 정보 가져오기
        is_trigger = hasattr(app_instance, 'manual_tag_info') and app_instance.manual_tag_info.get(tag, False)
        add_global_tag(app_instance, tag, is_trigger)
        add_tag_to_all_tags(app_instance, image, tag, is_trigger)
    else:
        # 태그 비활성화
        try:
            from timemachine_log import TM
            TM.log_change({
                "type": "tag_toggle_off",
                "image": image,
                "tag": tag,
            })
        except Exception:
            pass
        # 현재 표시 이미지일 때만 UI 동기화
        if image == app_instance.current_image:
            if tag in app_instance.current_tags:
                app_instance.current_tags.remove(tag)
        
        # 글로벌 태그 관리 플러그인 사용
        from global_tag_manager import remove_global_tag
        from all_tags_manager import remove_tag_from_all_tags
        
        remove_global_tag(app_instance, tag)
        remove_tag_from_all_tags(app_instance, image, tag)
        
        # 상호 배타 보장: 이미지별 리무버 태그에 추가
        if tag not in app_instance.image_removed_tags[image]:
            app_instance.image_removed_tags[image].append(tag)
        
        # 현재 표시 이미지일 때만 UI 동기화
        if image == app_instance.current_image:
            if tag not in app_instance.removed_tags:
                app_instance.removed_tags.append(tag)
    
    # 현재 이미지의 태그 상태 저장
    if app_instance.current_image:
        from image_preview_module import save_current_image_tags
        save_current_image_tags(app_instance)
    
    # UI 업데이트 (태그 트리 업데이트 포함)
    update_tag_stats(app_instance)
    print(f"✅ 태그 토글 후 UI 업데이트: {tag} ({'활성화' if checked else '비활성화'})")
    
    # 태그 스타일시트 에디터 업데이트 (태깅 중이 아닐 때만)
    if (hasattr(app_instance, 'tag_stylesheet_editor') and app_instance.tag_stylesheet_editor and 
        not getattr(app_instance, 'is_ai_tagging', False)):
        app_instance.tag_stylesheet_editor.schedule_update()


def update_tag_stats(app_instance):
    """태그 통계 업데이트"""
    # 현재 이미지 태그 표시 업데이트
    update_current_tags_display(app_instance)
    
    # 전체 태그 통계 업데이트 (앱 메서드 사용으로 위젯까지 완전 갱신)
    app_instance.update_global_tag_stats()
    
    # 태그 트리 업데이트 (색상 동기화를 위해)
    if hasattr(app_instance, 'update_tag_tree'):
        app_instance.update_tag_tree()
    


def update_global_tag_stats(app_instance):
    """전체 태그 통계 업데이트"""
    # 단체 태깅 중이면 업데이트 건너뛰기
    if hasattr(app_instance, 'is_ai_tagging') and app_instance.is_ai_tagging:
        print("단체 태깅 중 - 전체 태그 통계 업데이트 건너뛰기")
        return
        
    # 태그 통계 모듈 업데이트 (제목에 통계 정보 포함)
    if hasattr(app_instance, 'tag_statistics_module') and app_instance.tag_statistics_module:
        app_instance.tag_statistics_module.update_global_tag_statistics()
    else:
        # 태그 통계 리스트 업데이트 (fallback)
        update_global_tags_list(app_instance)
    
    print(f"전체 태그 통계 업데이트 완료")


def update_global_tags_list(app_instance):
    """전체 태그 통계 리스트 업데이트"""
    # TagStatisticsModule의 다중 선택 필터링 사용
    if hasattr(app_instance, 'tag_statistics_module'):
        app_instance.tag_statistics_module.update_filtered_tags()
    else:
        # 폴백: 모든 태그 표시 (딕셔너리와 정수 형태 모두 지원)
        def get_count(item):
            count = item[1]
            if isinstance(count, dict):
                return count.get('image_count', 0)
            return count
        sorted_tags = sorted(app_instance.global_tag_stats.items(), key=get_count, reverse=True)
        
        # 기존 태그들 제거
        while app_instance.global_tags_layout.count():
            child = app_instance.global_tags_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # WD Tagger에서 카테고리 정보 가져오기
        try:
            from wd_tagger import get_tag_category
        except ImportError:
            get_tag_category = lambda x: "unknown"
        
        # 모든 태그 표시 (제한 없음)
        for idx, (tag, count) in enumerate(sorted_tags, 1):
            from tag_statistics_module import TagListItem
            # 수동 입력 태그인지 확인
            if hasattr(app_instance, 'manual_tag_info') and tag in app_instance.manual_tag_info:
                # 수동 입력 태그: trigger 또는 used로 표시
                is_trigger = app_instance.manual_tag_info[tag]
                category = "trigger" if is_trigger else "used"
            else:
                # AI 태깅 태그: 실제 카테고리 정보 가져오기
                category = get_tag_category(tag)
            
            tag_item = TagListItem(tag, category, None, app_instance, count=idx)
            tag_item.removed.connect(lambda t: remove_tag(app_instance, t))
            app_instance.global_tags_layout.addWidget(tag_item)
        
        print(f"태그 통계 리스트 업데이트: {len(sorted_tags)}개 태그")


def add_tag(app_instance, tag, is_trigger=False):
    """태그 추가"""
    if not app_instance.current_image:
        return
        
    if tag not in app_instance.current_tags:
        # 타임머신: 단일 추가 기록(암묵 트랜잭션)
        try:
            from timemachine_log import TM
            TM.log_change({
                "type": "tag_add",
                "image": getattr(app_instance, 'current_image', None),
                "tag": tag,
                "is_trigger": bool(is_trigger),
            })
        except Exception:
            pass
        
        # 이미지별 리무버 태그 저장소 초기화
        if not hasattr(app_instance, 'image_removed_tags'):
            app_instance.image_removed_tags = {}
        if app_instance.current_image not in app_instance.image_removed_tags:
            app_instance.image_removed_tags[app_instance.current_image] = []
        
        # 상호 배타 보장: 이미지별 리무버 태그에서 제거
        if tag in app_instance.image_removed_tags[app_instance.current_image]:
            app_instance.image_removed_tags[app_instance.current_image].remove(tag)
        
        # 현재 이미지의 리무버 태그에서도 제거 (UI 동기화용)
        if tag in getattr(app_instance, 'removed_tags', []):
            try:
                app_instance.removed_tags.remove(tag)
            except Exception:
                pass
                
        if is_trigger:
            # 트리거 태그는 맨 앞에 추가
            app_instance.current_tags.insert(0, tag)
        else:
            # 일반 태그는 맨 뒤에 추가
            app_instance.current_tags.append(tag)
        
        # 글로벌 태그 관리 플러그인 사용
        from global_tag_manager import add_global_tag
        from all_tags_manager import add_tag_to_all_tags
        
        add_global_tag(app_instance, tag, is_trigger)
        add_tag_to_all_tags(app_instance, app_instance.current_image, tag, is_trigger)
        
        update_tag_stats(app_instance)
        
        # 태그 스타일시트 에디터 업데이트
        if hasattr(app_instance, 'tag_stylesheet_editor') and app_instance.tag_stylesheet_editor:
            app_instance.tag_stylesheet_editor.schedule_update()


def add_tag_to_all_images(app_instance, tag, is_trigger=False):
    """검색된 모든 이미지에 태그 추가 (다중 선택이 있으면 선택된 이미지에만 적용)"""
    # 타임머신: 일괄 추가를 1개의 트랜잭션으로 묶기
    TM = None
    try:
        from timemachine_log import TM as _TM
        TM = _TM
    except Exception:
        TM = None
    if TM is not None:
        TM.begin("bulk: add tag to images", context={
            "source": "ui_bulk_add",
            "tag": tag,
            "is_trigger": bool(is_trigger),
        })
    # 다중 선택된 이미지가 있으면 우선 처리 (배치 오토태깅과 동일한 로직)
    target_images = []
    from search_filter_grid_module import get_multi_selected_images
    multi_selected_images = get_multi_selected_images(app_instance)
    if multi_selected_images:
        target_images = multi_selected_images
        print(f"다중 선택된 {len(target_images)}개 이미지에 태그 추가")
    else:
        # 다중선택이 없으면 현재 그리드에 표시 중인 전체 결과(모든 페이지)를 기준으로 태깅
        source_list = getattr(app_instance, 'image_filtered_list', None)
        if not source_list:
            # 필터 리스트가 없으면 현재 로드된 이미지 목록 사용 (이미 통합 필터링 적용됨)
            source_list = getattr(app_instance, 'image_files', [])
        
        if not source_list:
            print("추가할 이미지가 없습니다. (현재 그리드 비어 있음)")
            return
        
        target_images = source_list
        print(f"현재 그리드 전체 기준으로 태그 추가: {len(target_images)}개")
    
    added_count = 0
    current_image_updated = False
    
    for image_path in target_images:
        # 키 타입 통일: 항상 문자열로 변환
        img_key = str(image_path)
        
        if img_key not in app_instance.all_tags:
            app_instance.all_tags[img_key] = []
        
        # 태그가 이미 있으면 건너뛰기
        if tag not in app_instance.all_tags[img_key]:
            if is_trigger:
                # 트리거 태그는 맨 앞에 추가
                app_instance.all_tags[img_key].insert(0, tag)
            else:
                # 일반 태그는 맨 뒤에 추가
                app_instance.all_tags[img_key].append(tag)
            added_count += 1
            # 타임머신: per-image change 축적
            if TM is not None:
                try:
                    TM.log_change({
                        "type": "bulk_add_per_image",
                        "image": img_key,
                        "tag": tag,
                        "is_trigger": bool(is_trigger),
                    })
                except Exception:
                    pass
            
            # 글로벌 태그 관리 플러그인 사용
            from global_tag_manager import add_global_tag
            
            add_global_tag(app_instance, tag, is_trigger)
            
            # 현재 이미지가 대상에 포함되어 있으면 current_tags도 업데이트 (문자열 키로 비교)
            if app_instance.current_image == img_key:
                if tag not in app_instance.current_tags:
                    # 상호 배타 보장: 활성에 추가하기 전에 리무버에서 제거
                    if tag in getattr(app_instance, 'removed_tags', []):
                        try:
                            app_instance.removed_tags.remove(tag)
                        except Exception:
                            pass
                    if is_trigger:
                        # 트리거 태그는 맨 앞에 추가
                        app_instance.current_tags.insert(0, tag)
                    else:
                        # 일반 태그는 맨 뒤에 추가
                        app_instance.current_tags.append(tag)
                    current_image_updated = True
                
                # removed_tags에 있었다면 제거 (중복 안전)
                if tag in app_instance.removed_tags:
                    try:
                        app_instance.removed_tags.remove(tag)
                        current_image_updated = True
                    except Exception:
                        pass
                
                # 수동 입력 태그 정보는 add_global_tag에서 처리됨
    
    print(f"'{tag}' 태그를 {added_count}개 이미지에 추가했습니다.")
    # 타임머신: 커밋/롤백
    if TM is not None:
        try:
            TM.commit()
        except Exception:
            try:
                TM.abort()
            except Exception:
                pass
    
    # UI 갱신 - 무조건 전체 UI 갱신 (조건부 제거)
    update_tag_stats(app_instance)
    
    # 태그 스타일시트 에디터가 열려있으면 업데이트
    if hasattr(app_instance, 'tag_stylesheet_editor') and app_instance.tag_stylesheet_editor:
        app_instance.tag_stylesheet_editor.schedule_update()


def remove_tag(app_instance, tag):
    """태그 제거"""
    if not app_instance.current_image:
        return
        
    # 타임머신: 단일 제거 기록(암묵 트랜잭션)
    try:
        from timemachine_log import TM
        TM.log_change({
            "type": "tag_remove",
            "image": getattr(app_instance, 'current_image', None),
            "tag": tag,
        })
    except Exception:
        pass
    if tag in app_instance.current_tags:
        app_instance.current_tags.remove(tag)
        
        # 이미지별 리무버 태그 저장소 초기화
        if not hasattr(app_instance, 'image_removed_tags'):
            app_instance.image_removed_tags = {}
        if app_instance.current_image not in app_instance.image_removed_tags:
            app_instance.image_removed_tags[app_instance.current_image] = []
        
        # 글로벌 태그 관리 플러그인 사용
        from global_tag_manager import remove_global_tag
        from all_tags_manager import remove_tag_from_all_tags
        
        remove_global_tag(app_instance, tag)
        remove_tag_from_all_tags(app_instance, app_instance.current_image, tag)
        
        # 상호 배타 보장: 이미지별 리무버 태그에 추가
        if tag not in app_instance.image_removed_tags[app_instance.current_image]:
            app_instance.image_removed_tags[app_instance.current_image].append(tag)
        
        # 현재 이미지의 리무버 태그에도 추가 (UI 동기화용)
        if tag not in app_instance.removed_tags:
            app_instance.removed_tags.append(tag)
        
        update_tag_stats(app_instance)
        
        # 태그 스타일시트 에디터 업데이트
        if hasattr(app_instance, 'tag_stylesheet_editor') and app_instance.tag_stylesheet_editor:
            app_instance.tag_stylesheet_editor.schedule_update()


def clear_tagging_panel(app_instance):
    """태깅 패널 초기화 - 새로운 폴더 로딩 시 호출"""
    print("태깅 패널 초기화")
    
    # 현재 이미지 초기화
    app_instance.current_image = None
    app_instance.current_tags = []
    app_instance.removed_tags = []
    
    # 태그 관련 데이터 초기화
    # 데이터 초기화 - 공용 모듈 사용
    from all_tags_manager import set_tags_for_image
    from global_tag_manager import add_global_tag
    
    app_instance.all_tags = {}
    app_instance.image_removed_tags = {}
    app_instance.global_tag_stats = {}
    app_instance.tag_confidence = {}
    app_instance.manual_tag_info = {}
    app_instance.llava_tag_info = {}
    
    # UI 초기화 - 태그 칩들을 강제로 제거
    if hasattr(app_instance, 'current_tags_display'):
        # 모든 자식 위젯 제거
        while app_instance.current_tags_display.count():
            child = app_instance.current_tags_display.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        app_instance.current_tags_display.clear()
    
    if hasattr(app_instance, 'tag_input'):
        app_instance.tag_input.clear()
    
    # 이미지 프리뷰 초기화
    if hasattr(app_instance, 'preview_label'):
        app_instance.preview_label.clear()
        app_instance.preview_label.setText("No image selected")
    
    # 태그 트리 초기화
    from tag_tree_module import clear_tag_tree
    clear_tag_tree(app_instance)
    
    # 태그 표시 업데이트 (빈 상태로)
    update_current_tags_display(app_instance)
    
    print("태깅 패널 초기화 완료")


def handle_tag_edit(app_instance, old_tag, new_tag):
    """태그 편집 처리"""
    print(f"🔧 [DEBUG] handle_tag_edit 호출됨: '{old_tag}' -> '{new_tag}'")
    print(f"🔧 [DEBUG] 현재 이미지: {app_instance.current_image}")
    print(f"🔧 [DEBUG] current_tags: {app_instance.current_tags}")
    print(f"🔧 [DEBUG] removed_tags: {app_instance.removed_tags}")
    
    # 현재 이미지가 없으면 무시
    if not app_instance.current_image:
        print("❌ [DEBUG] 현재 이미지가 없어서 태그 편집 무시")
        return
    
    # 타임머신: 단일 편집 기록(암묵 트랜잭션)
    try:
        from timemachine_log import TM
        TM.log_change({
            "type": "tag_edit",
            "image": getattr(app_instance, 'current_image', None),
            "old": old_tag,
            "new": new_tag,
        })
    except Exception:
        pass

    # 1. current_tags에서 태그 이름 변경
    if old_tag in app_instance.current_tags:
        index = app_instance.current_tags.index(old_tag)
        app_instance.current_tags[index] = new_tag
        print(f"✅ [DEBUG] current_tags 업데이트: index {index}, '{old_tag}' -> '{new_tag}'")
    else:
        print(f"⚠️ [DEBUG] current_tags에 '{old_tag}' 없음")
    
    # 2. removed_tags에서도 태그 이름 변경
    if old_tag in app_instance.removed_tags:
        index = app_instance.removed_tags.index(old_tag)
        app_instance.removed_tags[index] = new_tag
        print(f"✅ [DEBUG] removed_tags 업데이트: index {index}, '{old_tag}' -> '{new_tag}'")
    else:
        print(f"⚠️ [DEBUG] removed_tags에 '{old_tag}' 없음")
    
    # 3. all_tags에서 태그 이름 변경
    if app_instance.current_image in app_instance.all_tags:
        if old_tag in app_instance.all_tags[app_instance.current_image]:
            index = app_instance.all_tags[app_instance.current_image].index(old_tag)
            app_instance.all_tags[app_instance.current_image][index] = new_tag
            print(f"✅ [DEBUG] all_tags 업데이트: index {index}, '{old_tag}' -> '{new_tag}'")
        else:
            print(f"⚠️ [DEBUG] all_tags[{app_instance.current_image}]에 '{old_tag}' 없음")
    else:
        print(f"⚠️ [DEBUG] all_tags에 현재 이미지 없음")
    
    # 4. 글로벌 태그 관리 플러그인 사용
    from global_tag_manager import edit_global_tag
    from all_tags_manager import edit_tag_in_all_tags
    
    edit_global_tag(app_instance, old_tag, new_tag)
    edit_tag_in_all_tags(app_instance, app_instance.current_image, old_tag, new_tag)
    
    # tag_confidence 동기화
    if hasattr(app_instance, 'tag_confidence') and app_instance.current_image in app_instance.tag_confidence:
        for i, (tag, score) in enumerate(app_instance.tag_confidence[app_instance.current_image]):
            if tag == old_tag:
                app_instance.tag_confidence[app_instance.current_image][i] = (new_tag, score)
    
    # 8. UI 업데이트
    print(f"🔄 [DEBUG] UI 업데이트 시작")
    update_current_tags_display(app_instance)
    print(f"✅ [DEBUG] update_current_tags_display 완료")
    update_tag_stats(app_instance)
    print(f"✅ [DEBUG] update_tag_stats 완료")
    
    # 9. 태그 스타일시트 에디터 업데이트
    if hasattr(app_instance, 'tag_stylesheet_editor') and app_instance.tag_stylesheet_editor:
        app_instance.tag_stylesheet_editor.schedule_update()
        print(f"✅ [DEBUG] 태그 스타일시트 에디터 업데이트 완료")
    else:
        print(f"⚠️ [DEBUG] 태그 스타일시트 에디터 없음")
    
    print(f"🎉 [DEBUG] 태그 편집 완료: '{old_tag}' -> '{new_tag}'")


def drag_enter_event(app_instance, event):
    """드래그 진입 이벤트"""
    print(f"drag_enter_event: {event.mimeData().text() if event.mimeData().hasText() else 'no text'}")
    if event.mimeData().hasText():
        event.acceptProposedAction()
    else:
        event.ignore()


def drag_move_event(app_instance, event):
    """드래그 이동 이벤트"""
    if event.mimeData().hasText():
        event.acceptProposedAction()
    else:
        event.ignore()


def drop_event(app_instance, event):
    """드롭 이벤트 - 태그 순서 변경"""
    if event.mimeData().hasText():
        tag_text = event.mimeData().text()
        
        # 드롭 위치 찾기
        drop_position = event.position().toPoint()
        target_index = find_drop_position(app_instance, drop_position)
        
        print(f"드롭 이벤트: {tag_text}, 위치: {drop_position}, 타겟 인덱스: {target_index}")
        print(f"현재 태그들: {app_instance.current_tags}")
        
        # 태그 순서 변경
        if tag_text in app_instance.current_tags:
            # ── 타임머신: 트랜잭션 단위로 묶기(한 번의 드래그를 1 작업으로 기록) ──
            try:
                from timemachine_log import TM
            except Exception:
                TM = None

            before_order = app_instance.current_tags.copy()
            old_index = app_instance.current_tags.index(tag_text)
            print(f"기존 인덱스: {old_index}, 새 인덱스: {target_index}")
            
            # 같은 위치로 드롭하는 경우 무시
            if old_index == target_index:
                print("같은 위치로 드롭, 무시")
                event.acceptProposedAction()
                return
            
            if TM is not None:
                ctx = {
                    "source": "drag_reorder",
                    "image": getattr(app_instance, 'current_image', None),
                }
                TM.begin("tag reorder", context=ctx)
            app_instance.current_tags.pop(old_index)
            # target_index가 old_index보다 큰 경우 조정
            if target_index > old_index:
                target_index -= 1
            app_instance.current_tags.insert(target_index, tag_text)
            
            print(f"변경된 태그들: {app_instance.current_tags}")
            
            # all_tags에도 반영
            if app_instance.current_image in app_instance.all_tags:
                app_instance.all_tags[app_instance.current_image] = app_instance.current_tags.copy()
            
            # UI 업데이트
            update_current_tags_display(app_instance)

            # ── 타임머신: 변경 사항 커밋 ──
            if TM is not None:
                try:
                    TM.log_change({
                        "type": "tag_reorder",
                        "image": getattr(app_instance, 'current_image', None),
                        "before": before_order,
                        "after": app_instance.current_tags.copy(),
                        "moved_tag": tag_text,
                        "from_index": old_index,
                        "to_index": target_index,
                    })
                    TM.commit()
                except Exception:
                    try:
                        TM.abort()
                    except Exception:
                        pass
            
        event.acceptProposedAction()
    else:
        event.ignore()


def find_drop_position(app_instance, position):
    """드롭 위치에 따른 인덱스 찾기"""
    print(f"find_drop_position 호출: position={position}")
    print(f"active_tags_layout.count()={app_instance.active_tags_layout.count()}")
    
    # 모든 위젯의 정보를 수집
    widgets_info = []
    for i in range(app_instance.active_tags_layout.count()):
        item = app_instance.active_tags_layout.itemAt(i)
        if item and item.widget():
            widget = item.widget()
            widget_rect = widget.geometry()
            center_x = widget_rect.center().x()
            center_y = widget_rect.center().y()
            widget_text = widget.text() if hasattr(widget, 'text') else 'unknown'
            widgets_info.append({
                'index': i,
                'widget': widget,
                'rect': widget_rect,
                'center_x': center_x,
                'center_y': center_y,
                'text': widget_text
            })
            print(f"위젯 {i}: {widget_text}, rect={widget_rect}, center=({center_x}, {center_y})")
    
    # Y 좌표로 먼저 정렬 (행별로), 그 다음 X 좌표로 정렬 (열별로)
    widgets_info.sort(key=lambda x: (x['center_y'], x['center_x']))
    
    # 드롭 위치와 가장 가까운 위젯 찾기
    drop_x = position.x()
    drop_y = position.y()
    
    print(f"드롭 위치: ({drop_x}, {drop_y})")
    
    for i, widget_info in enumerate(widgets_info):
        center_x = widget_info['center_x']
        center_y = widget_info['center_y']
        widget_text = widget_info['text']
        
        # 같은 행에 있는지 확인 (Y 좌표 차이가 작은 경우)
        if abs(drop_y - center_y) < 20:  # 같은 행으로 간주하는 임계값을 20px로 줄임
            if drop_x < center_x:
                print(f"같은 행에서 위치 {drop_x} < 위젯 '{widget_text}' 중앙 {center_x}, 인덱스 {i} 반환")
                return i
        # 다른 행인 경우, Y 좌표로 판단
        elif drop_y < center_y:
            print(f"다른 행에서 위치 {drop_y} < 위젯 '{widget_text}' 중앙 {center_y}, 인덱스 {i} 반환")
            return i
    
    print(f"모든 위젯을 지나침, 마지막 인덱스 {len(app_instance.current_tags)} 반환")
    return len(app_instance.current_tags)