#!/usr/bin/env python3
"""
태그 트리 정리 기능을 담당하는 모듈
ai-image-tagger.py에서 임포트해서 사용
"""

from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QScrollArea, QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Signal, Qt, QPoint

# ---- robust multi-line QLabel to avoid clipping ----
from PySide6.QtCore import QRect, QSize

class WrappingLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setMargin(1)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        if w <= 0:
            return super().heightForWidth(w)
        m = self.contentsMargins()
        inner_w = max(0, w - (m.left() + m.right()) - 6)
        rect = QRect(0, 0, inner_w, 10**7)  # effectively "infinite" height
        flags = Qt.TextWordWrap
        br = self.fontMetrics().boundingRect(rect, flags, self.text())
        # 최소 높이 보장 및 여유 공간 추가
        min_height = self.fontMetrics().height() + 4
        calculated_height = br.height() + m.top() + m.bottom()
        return max(min_height, calculated_height)

    def sizeHint(self) -> QSize:
        w = max(1, self.width())
        return QSize(w, self.heightForWidth(w))
# ---- end robust label ----



# ---- soft-wrapping helper (allow wrapping of long unbroken tokens) ----
def insert_wrap_opportunities(s: str) -> str:
    try:
        if s and (" " not in s) and (len(s) > 18):
            return "\u200b".join(list(s))
        return s
    except Exception:
        return s
# ---- end helper ----

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

def get_tag_hover_overlay():
    """전역 태그 호버 오버레이 인스턴스 반환"""
    global _tag_hover_overlay
    if _tag_hover_overlay is None:
        _tag_hover_overlay = TagHoverOverlay()
    return _tag_hover_overlay

# Danbooru 모듈 임포트 (선택적)
try:
    from danbooru_module import get_danbooru_category_short, is_danbooru_available
    DANBOORU_AVAILABLE = is_danbooru_available()
except ImportError:
    DANBOORU_AVAILABLE = False
    def get_danbooru_category_short(tag: str) -> str:
        return "?"

class TagTreeModule:
    """태그를 카테고리별로 트리 구조로 정리하는 모듈"""
    
    def __init__(self):
        self.is_available = DANBOORU_AVAILABLE
    
    @staticmethod
    def get_category_color(category_name):
        """카테고리명을 기반으로 일관된 랜덤 색상 반환"""
        import hashlib
        import random
        
        # 카테고리명을 시드로 사용하여 일관된 랜덤 색상 생성
        hash_value = int(hashlib.md5(category_name.encode()).hexdigest(), 16)
        random.seed(hash_value)
        
        # 밝고 대비가 좋은 색상 범위에서 랜덤 생성
        # 너무 어두운 색상은 피하고, 가독성을 위해 밝은 색상 위주로 생성
        hue = random.randint(0, 360)  # 0-360도 색상환
        saturation = random.randint(60, 100)  # 채도 60-100%
        lightness = random.randint(45, 70)  # 명도 45-70% (너무 어둡지 않게)
        
        # HSL을 RGB로 변환
        def hsl_to_rgb(h, s, l):
            h = h / 360.0
            s = s / 100.0
            l = l / 100.0
            
            def hue_to_rgb(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1/6: return p + (q - p) * 6 * t
                if t < 1/2: return q
                if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                return p
            
            if s == 0:
                r = g = b = l
            else:
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                r = hue_to_rgb(p, q, h + 1/3)
                g = hue_to_rgb(p, q, h)
                b = hue_to_rgb(p, q, h - 1/3)
            
            return (int(r * 255), int(g * 255), int(b * 255))
        
        r, g, b = hsl_to_rgb(hue, saturation, lightness)
        return f"#{r:02x}{g:02x}{b:02x}"


class TagTreeItem(QFrame):
    """태그 트리 아이템 (카테고리 또는 태그)"""
    tagClicked = Signal(str)  # 태그 클릭 시그널
    removedTagClicked = Signal(str)  # removed 태그 클릭 시그널
    categoryToggled = Signal(str, bool)  # 카테고리 토글 시그널
    
    def __init__(self, text: str, item_type: str = "category", tag_count: int = 0, parent=None):
        super().__init__(parent)
        self.item_type = item_type
        self.tag_text = text
        self.is_expanded = True  # 카테고리 확장 상태
        self.is_removed = False  # removed 상태 추적
        self.setMinimumHeight(24)  # 최소 높이 설정
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # 태그 아이템인 경우 클릭 가능하도록 스타일 설정
        if item_type == "tag":
            self.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                    padding-right: 2px;
                    padding-bottom: 1px;
                }
                QFrame:hover {
                    background: transparent;
                    border: none;
                }
            """)
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                }
            """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)  # 상하 마진 추가
        layout.setSpacing(0)  # 내부 요소들 사이 간격 제거
        
        # 확장/축소 버튼 및 들여쓰기 처리
        if item_type == "category":
            # 상위 카테고리: 들여쓰기 없음
            self.expand_btn = QPushButton()
            self.expand_btn.setFixedSize(16, 16)
            category_color = TagTreeModule.get_category_color(text)
            self.expand_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {category_color};
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 2px;
                }}
            """)
            self.expand_btn.setText("▼" if self.is_expanded else "▶")
            self.expand_btn.clicked.connect(self.toggle_expand)
            layout.addWidget(self.expand_btn)
        elif item_type == "subcategory":
            # 하위 카테고리: 들여쓰기만 추가
            indent_label = QLabel("  ")  # 하위 카테고리용 들여쓰기 (기호 없이)
            indent_label.setFixedSize(10, 24)
            indent_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            indent_label.setStyleSheet("""
                color: transparent;
                font-size: 10px;
                background: transparent;
            """)
            layout.addWidget(indent_label)
            
            self.expand_btn = QPushButton()
            self.expand_btn.setFixedSize(16, 16)
            category_color = TagTreeModule.get_category_color(text)
            self.expand_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {category_color};
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 2px;
                }}
            """)
            self.expand_btn.setText("▼" if self.is_expanded else "▶")
            self.expand_btn.clicked.connect(self.toggle_expand)
            layout.addWidget(self.expand_btn)
        else:
            # 태그 아이템인 경우 더 깊은 들여쓰기 추가
            indent_label = QLabel("      └─")  # 태그용 들여쓰기 (6칸으로 조정)
            indent_label.setTextFormat(Qt.PlainText)  # HTML 포맷 비활성화
            indent_label.setFixedSize(50, 24)  # 높이를 TagTreeItem과 맞춤 (6칸 + └─ 기호에 맞게 조정)
            indent_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            indent_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 오른쪽 정렬
            indent_label.setStyleSheet("""
                color: #6B7280;
                font-size: 12px;
                background: transparent;
                padding: 1px 6px 2px 0px;
            """)
            layout.addWidget(indent_label)
        
        # 텍스트 (구버전처럼 서브 카테고리 없이)
        self.text_label = WrappingLabel(insert_wrap_opportunities(text))
        if item_type == "category":
            category_color = TagTreeModule.get_category_color(text)
            self.text_label.setStyleSheet(f"""
                color: {category_color};
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                padding: 1px 6px 2px 0px;
            """)
        elif item_type == "subcategory":
            # 하위 카테고리는 상위 카테고리와 비슷한 색상이지만 조금 더 연하게
            category_color = TagTreeModule.get_category_color(text)
            self.text_label.setStyleSheet(f"""
                color: {category_color};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                padding: 1px 6px 2px 0px;
            """)
        else:
            self.text_label.setStyleSheet("""
                color: #E5E7EB;
                font-size: 12px;
                background: transparent;
                padding: 1px 6px 2px 0px;
            """)
            # 태그 텍스트에 호버 효과 추가
            if item_type == "tag":
                self.text_label.mousePressEvent = lambda event: self.mousePressEvent(event)
                self.text_label.enterEvent = lambda event: self._on_text_hover_enter(self.text_label)
                self.text_label.leaveEvent = lambda event: self._on_text_hover_leave(self.text_label)
        
        self.text_label.setWordWrap(True)
        self.text_label.setMargin(1)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)  # patched: give label 1px internal padding
        layout.addWidget(self.text_label)
        self.text_label.updateGeometry()
        self.text_label.setMinimumHeight(self.text_label.heightForWidth(self.text_label.width()))
        self.updateGeometry()
        
        # 카테고리인 경우 태그 개수 표시
        if item_type == "category" and tag_count > 0:
            count_label = QLabel(f"({tag_count})")
            count_label.setStyleSheet("""
                color: #6B7280;
                font-size: 11px;
                background: transparent;
            """)
            layout.addWidget(count_label)
        
        
        # 좌상단 정렬을 위해 stretch 제거
    
    def toggle_expand(self):
        """카테고리 확장/축소 토글"""
        self.is_expanded = not self.is_expanded
        self.expand_btn.setText("▼" if self.is_expanded else "▶")
        self.categoryToggled.emit(self.tag_text, self.is_expanded)
    
    def _on_text_hover_enter(self, text_label):
        """텍스트 호버 진입 시 글씨 크기 증가 및 오버레이 표시"""
        if self.item_type == "tag":
            if self.is_removed:
                # removed 태그는 빨간색 유지하면서 크기만 증가
                text_label.setStyleSheet("""
                    color: #EF4444;
                    font-size: 13px;
                    font-weight: bold;
                    background: transparent;
                """)
            else:
                # 일반 태그는 회색으로 크기 증가
                text_label.setStyleSheet("""
                    color: #E5E7EB;
                    font-size: 13px;
                    font-weight: bold;
                    background: transparent;
                """)
            
            # 태그 호버 오버레이 표시
            overlay = get_tag_hover_overlay()
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            overlay.show_for_tag(self.tag_text, global_pos)
    
    def _on_text_hover_leave(self, text_label):
        """텍스트 호버 벗어날 시 글씨 크기 원복 및 오버레이 숨김"""
        if self.item_type == "tag":
            if self.is_removed:
                # removed 태그는 빨간색 유지하면서 크기 원복
                text_label.setStyleSheet("""
                    color: #EF4444;
                    font-size: 12px;
                    background: transparent;
                """)
            else:
                # 일반 태그는 회색으로 크기 원복
                text_label.setStyleSheet("""
                    color: #E5E7EB;
                    font-size: 12px;
                    background: transparent;
                """)
            
            # 태그 호버 오버레이 숨김
            overlay = get_tag_hover_overlay()
            overlay.hide()
    
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            # reflow label when width changes so more lines fit and nothing is clipped
            if hasattr(self, 'text_label') and self.text_label is not None:
                self.text_label.updateGeometry()
                # 텍스트가 잘리지 않도록 높이 재계산
                self.text_label.setMinimumHeight(self.text_label.heightForWidth(self.text_label.width()))
            self.updateGeometry()
        except Exception:
            pass

    def mousePressEvent(self, event):
        """마우스 클릭 이벤트 처리"""
        if event.button() == Qt.LeftButton and self.item_type == "tag":
            if self.is_removed:
                self.removedTagClicked.emit(self.tag_text)
            else:
                self.tagClicked.emit(self.tag_text)
        super().mousePressEvent(event)
    
    def set_removed_style(self):
        """removed 태그 스타일 적용"""
        if self.item_type == "tag":
            self.is_removed = True
            # 내부 text_label 찾기
            for child in self.findChildren(QLabel):
                if child.text().replace('\u200b','') == self.tag_text:
                    child.setStyleSheet("""
                        color: #EF4444;
                        font-size: 12px;
                        background: transparent;
                    """)
                    break


class TagTreeModule:
    """태그를 카테고리별로 트리 구조로 정리하는 모듈"""
    
    def __init__(self):
        self.is_available = DANBOORU_AVAILABLE
    
    @staticmethod
    def get_category_color(category_name):
        """카테고리명을 기반으로 일관된 랜덤 색상 반환"""
        import hashlib
        import random
        
        # 카테고리명을 시드로 사용하여 일관된 랜덤 색상 생성
        hash_value = int(hashlib.md5(category_name.encode()).hexdigest(), 16)
        random.seed(hash_value)
        
        # 밝고 대비가 좋은 색상 범위에서 랜덤 생성
        # 너무 어두운 색상은 피하고, 가독성을 위해 밝은 색상 위주로 생성
        hue = random.randint(0, 360)  # 0-360도 색상환
        saturation = random.randint(60, 100)  # 채도 60-100%
        lightness = random.randint(45, 70)  # 명도 45-70% (너무 어둡지 않게)
        
        # HSL을 RGB로 변환
        def hsl_to_rgb(h, s, l):
            h = h / 360.0
            s = s / 100.0
            l = l / 100.0
            
            def hue_to_rgb(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1/6: return p + (q - p) * 6 * t
                if t < 1/2: return q
                if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                return p
            
            if s == 0:
                r = g = b = l
            else:
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                r = hue_to_rgb(p, q, h + 1/3)
                g = hue_to_rgb(p, q, h)
                b = hue_to_rgb(p, q, h - 1/3)
            
            return (int(r * 255), int(g * 255), int(b * 255))
        
        r, g, b = hsl_to_rgb(hue, saturation, lightness)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def organize_tags_by_category(self, tags: List[str], app_instance=None) -> Dict[str, Dict[str, List[str]]]:
        """태그들을 계층적 카테고리별로 정리 (KR_danbooru_tags.csv 기준)"""
        if not tags:
            return {}
        
        try:
            from kr_danbooru_loader import kr_danbooru_loader
            
            print(f"태그 트리 로더 상태: is_available={kr_danbooru_loader.is_available}, 태그 수={len(kr_danbooru_loader.tags)}")
            
            # 계층적 구조: {상위카테고리: {하위카테고리: [태그들]}}
            category_hierarchy = defaultdict(lambda: defaultdict(list))
            
            for tag in tags:
                if kr_danbooru_loader.is_available:
                    full_category = kr_danbooru_loader.get_tag_category(tag)
                    
                    # 카테고리 분리 (패션 > 헤어컬러 -> 패션, 헤어컬러)
                    if ' > ' in full_category:
                        main_category, sub_category = full_category.split(' > ', 1)
                        main_category = main_category.strip()
                        sub_category = sub_category.strip()
                    else:
                        main_category = full_category
                        sub_category = "기타"
                else:
                    main_category = "UNKNOWN"
                    sub_category = "기타"
                
                category_hierarchy[main_category][sub_category].append(tag)
            
            # 각 카테고리별로 태그 정렬
            for main_cat in category_hierarchy:
                for sub_cat in category_hierarchy[main_cat]:
                    category_hierarchy[main_cat][sub_cat].sort()
            
            return dict(category_hierarchy)
        except Exception as e:
            print(f"organize_tags_by_category 오류: {e}")
            import traceback
            traceback.print_exc()
            return {"UNKNOWN": {"기타": tags}}
    
    
    def get_tree_structure(self, tags: List[str], app_instance=None) -> List[Tuple[str, Dict[str, List[str]]]]:
        """트리 구조로 정리된 태그 반환 (상위카테고리, {하위카테고리: 태그리스트})"""
        organized = self.organize_tags_by_category(tags, app_instance)
        
        # 상위 카테고리별 총 태그 수로 정렬 (내림차순: 많은 순서대로)
        def get_total_tags(category_data):
            return sum(len(tags) for tags in category_data.values())
        
        sorted_categories = sorted(organized.items(), key=lambda x: get_total_tags(x[1]), reverse=True)
        
        return sorted_categories
    
    def get_category_stats(self, tags: List[str]) -> Dict[str, int]:
        """카테고리별 태그 개수 통계 (계층 구조)"""
        organized = self.organize_tags_by_category(tags)
        stats = {}
        for main_category, sub_categories in organized.items():
            total_tags = sum(len(tag_list) for tag_list in sub_categories.values())
            stats[main_category] = total_tags
        return stats

# 전역 인스턴스
tag_tree_module = TagTreeModule()

def organize_tags_by_category(tags: List[str], app_instance=None) -> Dict[str, List[str]]:
    """태그들을 카테고리별로 정리 (편의 함수)"""
    return tag_tree_module.organize_tags_by_category(tags, app_instance)

def get_tag_tree_structure(tags: List[str], app_instance=None) -> List[Tuple[str, List[str]]]:
    """트리 구조로 정리된 태그 반환 (편의 함수)"""
    return tag_tree_module.get_tree_structure(tags, app_instance)

def get_category_stats(tags: List[str]) -> Dict[str, int]:
    """카테고리별 태그 개수 통계 (편의 함수)"""
    return tag_tree_module.get_category_stats(tags)

def is_tag_tree_available() -> bool:
    """태그 트리 모듈이 사용 가능한지 확인"""
    return tag_tree_module.is_available

def get_category_color(category_name: str) -> str:
    """카테고리명을 기반으로 일관된 랜덤 색상 반환 (편의 함수)"""
    return tag_tree_module.get_category_color(category_name)

def create_tag_tree_item(text: str, item_type: str = "category", tag_count: int = 0, parent=None):
    """TagTreeItem 생성 편의 함수"""
    return TagTreeItem(text, item_type, tag_count, parent)

def handle_tag_click(app_instance, tag_text):
    """태그 클릭 시 removed로 이동 처리"""
    print(f"태그 트리에서 태그 클릭: {tag_text}")
    
    # 이미지 태깅 모듈의 toggle_current_tag 함수 사용 (데이터 동기화 보장)
    from image_tagging_module import toggle_current_tag
    
    # 태그가 현재 활성화되어 있으면 비활성화 (removed로 이동)
    if tag_text in app_instance.current_tags:
        toggle_current_tag(app_instance, tag_text, False)
        print(f"태그 '{tag_text}'가 removed로 이동되었습니다.")
    else:
        print(f"태그 '{tag_text}'가 현재 태그 목록에 없습니다.")

def handle_removed_tag_click(app_instance, tag_text):
    """removed 태그 클릭 시 액티브로 복원 처리"""
    print(f"removed 태그 클릭: {tag_text}")
    
    # 이미지 태깅 모듈의 toggle_current_tag 함수 사용 (데이터 동기화 보장)
    from image_tagging_module import toggle_current_tag
    
    # 태그가 removed 상태에 있으면 활성화 (current로 복원)
    if tag_text in app_instance.removed_tags:
        toggle_current_tag(app_instance, tag_text, True)
        print(f"태그 '{tag_text}'가 액티브로 복원되었습니다.")
    else:
        print(f"태그 '{tag_text}'가 removed 목록에 없습니다.")

def handle_category_toggle(app_instance, category_name, is_expanded):
    """카테고리 확장/축소 토글 처리"""
    print(f"카테고리 토글: {category_name} -> {'확장' if is_expanded else '축소'}")
    
    # 카테고리 확장 상태 저장
    if not hasattr(app_instance, 'category_expanded_state'):
        app_instance.category_expanded_state = {}
    app_instance.category_expanded_state[category_name] = is_expanded
    
    # 태그 트리 다시 그리기
    app_instance.update_tag_tree()

def adjust_container_size(app_instance):
    """태그 트리 컨테이너 크기를 동적으로 조정"""
    if not hasattr(app_instance, 'tag_tree_container') or not hasattr(app_instance, 'tag_tree_layout'):
        return
    
    # 레이아웃의 크기 힌트 계산
    size_hint = app_instance.tag_tree_layout.sizeHint()
    
    # 최소 높이와 계산된 높이 중 더 큰 값 사용 (스크롤 여백 제거)
    min_height = 200  # 최소 높이 보장
    calculated_height = max(min_height, size_hint.height() + 20)  # 여유 공간 추가
    
    # 컨테이너 크기 조정 (스크롤 여백 제거)
    vw = app_instance.tag_tree_scroll.viewport().width() if hasattr(app_instance, 'tag_tree_scroll') else 280
    app_instance.tag_tree_container.setMinimumSize(vw, calculated_height)
    app_instance.tag_tree_container.resize(vw, calculated_height)
    
    print(f"태그 트리 컨테이너 크기 조정: {calculated_height}px (스크롤 여백 제거)")

def create_tag_tree_section(app_instance, SectionCard):
    """태그 트리 섹션 UI 생성 함수 (카드 포함)"""
    # 태그 트리 카드 생성 (원본 PY에서 이식)
    tag_tree_card = SectionCard("TAG TREE")
    tag_tree_card.setFixedWidth(300)  # 고정 너비 설정
    
    # 태그 트리 스크롤 영역
    tag_tree_scroll = QScrollArea()
    tag_tree_scroll.setWidgetResizable(True)
    tag_tree_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tag_tree_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    # reserve space for the vertical scrollbar so labels don't get clipped
    try:
        _sbw = tag_tree_scroll.verticalScrollBar().sizeHint().width()
    except Exception:
        _sbw = 8
    tag_tree_scroll.setViewportMargins(6, 6, int((_sbw or 8) + 10), 6)  # 여백 증가
    tag_tree_scroll.setMinimumHeight(200)  # 최소 높이 설정
    tag_tree_scroll.setMaximumHeight(2000)  # 최대 높이 설정 (800 → 2000)
    tag_tree_scroll.setStyleSheet("""
        QScrollArea {
            background: transparent;
            border: none;
            border-radius: 4px;
        }
        QScrollArea > QWidget > QWidget {
            background: transparent;
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
    
    # 태그 트리 컨테이너
    tag_tree_container = QWidget()
    tag_tree_container.setMinimumSize(0, 0)  # patched: allow to shrink/expand to viewport width
    tag_tree_container.setMaximumSize(16777215, 2000)  # patched: no fixed width limit
    tag_tree_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    tag_tree_layout = QVBoxLayout(tag_tree_container)
    tag_tree_layout.setContentsMargins(6, 6, 16, 6)  # 여백 증가
    tag_tree_layout.setSpacing(2)  # 간격 약간 증가
    tag_tree_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 위/왼 정렬 (avoid centering)
    
    tag_tree_scroll.setWidget(tag_tree_container)
    
    # 카드에 스크롤 영역 추가 (원본 PY에서 이식)
    tag_tree_card.body.addWidget(tag_tree_scroll)
    
    # app_instance에 참조 저장 (원본 PY에서 이식)
    app_instance.tag_tree_scroll = tag_tree_scroll
    app_instance.tag_tree_container = tag_tree_container
    app_instance.tag_tree_layout = tag_tree_layout
    
    return tag_tree_card

def update_tag_tree(tag_tree_layout, current_tags, category_expanded_state=None, on_tag_clicked=None, on_category_toggled=None, removed_tags=None, on_removed_tag_clicked=None, app_instance=None):
    """태그 트리 업데이트 함수"""
    if not tag_tree_layout:
        return
    
    # 기존 태그 트리 아이템들 제거
    while tag_tree_layout.count():
        child = tag_tree_layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()
    
    # current_tags와 removed_tags를 합쳐서 모든 태그 표시
    all_tags = current_tags.copy() if current_tags else []
    if removed_tags:
        all_tags.extend(removed_tags)
    
    # 태그가 없으면 안내 메시지 표시
    if not all_tags:
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt
        empty_label = QLabel("No tags to display")
        empty_label.setStyleSheet("""
            color: #6B7280;
            font-size: 12px;
            padding: 20px;
        """)
        empty_label.setAlignment(Qt.AlignCenter)
        tag_tree_layout.addWidget(empty_label)
        return
    
    # 태그 트리 구조 생성
    try:
        tree_structure = get_tag_tree_structure(all_tags, app_instance)
        
        # 카테고리 확장 상태 저장 (초기화)
        if category_expanded_state is None:
            category_expanded_state = {}
        
        for main_category, sub_categories in tree_structure:
            # 상위 카테고리 확장 상태 확인 (기본값: True)
            main_expanded = category_expanded_state.get(main_category, True)
            
            # 상위 카테고리 아이템 추가
            total_tags = sum(len(tags) for tags in sub_categories.values())
            main_category_item = TagTreeItem(main_category, "category", total_tags)
            main_category_item.is_expanded = main_expanded
            if hasattr(main_category_item, 'expand_btn'):
                main_category_item.expand_btn.setText("▼" if main_expanded else "▶")
            if on_category_toggled:
                main_category_item.categoryToggled.connect(on_category_toggled)
            tag_tree_layout.addWidget(main_category_item)
            
            # 상위 카테고리가 확장된 경우 하위 카테고리들 추가
            if main_expanded:
                for sub_category, tags in sub_categories.items():
                    # 하위 카테고리 확장 상태 확인 (기본값: True)
                    sub_expanded = category_expanded_state.get(f"{main_category}_{sub_category}", True)
                    
                    # 하위 카테고리 아이템 추가
                    sub_category_item = TagTreeItem(sub_category, "subcategory", len(tags))
                    sub_category_item.is_expanded = sub_expanded
                    if hasattr(sub_category_item, 'expand_btn'):
                        sub_category_item.expand_btn.setText("▼" if sub_expanded else "▶")
                    if on_category_toggled:
                        # 하위 카테고리용 별도 핸들러 (클로저 문제 해결)
                        def make_subcategory_handler(main_cat, sub_cat):
                            def handler(category_name, is_expanded):
                                full_key = f"{main_cat}_{sub_cat}"
                                on_category_toggled(full_key, is_expanded)
                            return handler
                        sub_category_item.categoryToggled.connect(make_subcategory_handler(main_category, sub_category))
                    tag_tree_layout.addWidget(sub_category_item)
                    
                    # 하위 카테고리가 확장된 경우 태그들 추가
                    if sub_expanded:
                        for tag in tags:
                            tag_item = TagTreeItem(tag, "tag")
                            if on_tag_clicked:
                                tag_item.tagClicked.connect(on_tag_clicked)
                            if on_removed_tag_clicked:
                                tag_item.removedTagClicked.connect(on_removed_tag_clicked)
                            
                            # removed된 태그인지 확인하여 빨간색으로 표시
                            if removed_tags and tag in removed_tags:
                                tag_item.set_removed_style()
                            
                            tag_tree_layout.addWidget(tag_item)
            
            # 카테고리 간 간격 추가
            from PySide6.QtWidgets import QWidget
            spacer = QWidget()
            spacer.setFixedHeight(4)
            tag_tree_layout.addWidget(spacer)
        
        print(f"태그 트리 업데이트: {len(tree_structure)}개 카테고리, {len(current_tags)}개 태그")
        
    except Exception as e:
        print(f"태그 트리 업데이트 오류: {e}")
        # 오류 발생 시 기본 메시지 표시
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt
        error_label = QLabel("Error loading tag tree")
        error_label.setStyleSheet("""
            color: #EF4444;
            font-size: 12px;
            padding: 20px;
        """)
        error_label.setAlignment(Qt.AlignCenter)
        tag_tree_layout.addWidget(error_label)


def clear_tag_tree(app_instance):
    """태그 트리 초기화 - 새로운 폴더 로딩 시 호출"""
    print("태그 트리 초기화")
    
    # 태그 트리 위젯 초기화
    if hasattr(app_instance, 'tag_tree_widget') and app_instance.tag_tree_widget:
        # 모든 자식 위젯 제거
        while app_instance.tag_tree_widget.count():
            child = app_instance.tag_tree_widget.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 빈 상태 메시지 표시
        empty_label = QLabel("No tags available")
        empty_label.setStyleSheet("""
            color: #9CA3AF;
            font-size: 14px;
            padding: 40px;
        """)
        empty_label.setAlignment(Qt.AlignCenter)
        app_instance.tag_tree_widget.addWidget(empty_label)