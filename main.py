
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI Image Tagger - Ultra Modern Dark Theme UI
PySide6 기반 이미지 태깅 도구 (Enhanced Design)
"""

import os
import sys
import traceback
from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# 전역 커스텀 UI 클래스들
class CustomSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QSpinBox.UpDownArrows)
        # 모든 스핀박스 높이 통일 (15px)
        self.setFixedHeight(15)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 올바른 스타일 옵션 생성
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        
        # 위쪽 화살표
        up_rect = self.style().subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_SpinBoxUp, self)
        if up_rect.isValid():
            # 화살표 텍스트 그리기
            painter.setPen(QPen(QColor("#E2E8F0")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(up_rect, Qt.AlignCenter, "▲")
        
        # 아래쪽 화살표
        down_rect = self.style().subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_SpinBoxDown, self)
        if down_rect.isValid():
            # 화살표 텍스트 그리기
            painter.setPen(QPen(QColor("#E2E8F0")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(down_rect, Qt.AlignCenter, "▼")

class CustomDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        # 모든 더블 스핀박스 높이 통일 (15px)
        self.setFixedHeight(15)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 올바른 스타일 옵션 생성
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        
        # 위쪽 화살표
        up_rect = self.style().subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_SpinBoxUp, self)
        if up_rect.isValid():
            # 화살표 텍스트 그리기
            painter.setPen(QPen(QColor("#E2E8F0")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(up_rect, Qt.AlignCenter, "▲")
        
        # 아래쪽 화살표
        down_rect = self.style().subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_SpinBoxDown, self)
        if down_rect.isValid():
            # 화살표 텍스트 그리기
            painter.setPen(QPen(QColor("#E2E8F0")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(down_rect, Qt.AlignCenter, "▼")

class CustomComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 모든 드롭다운 높이 통일 (15px)
        self.setFixedHeight(15)
        # 기본 화살표 완전히 제거
        self.setStyleSheet("""
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
        """)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 올바른 스타일 옵션 생성
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        
        # 드롭다운 화살표 영역 계산 (수동으로)
        rect = self.rect()
        arrow_width = 20
        arrow_rect = QRect(rect.width() - arrow_width, 0, arrow_width, rect.height())
        
        # 화살표 텍스트 그리기
        painter.setPen(QPen(QColor("#E2E8F0")))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(arrow_rect, Qt.AlignCenter, "▼")
from wd_tagger import WdTaggerThread, get_global_tagger, check_gpu_availability
from llava_captioner_module import LLaVATaggerThread

# Danbooru 모듈 임포트 (선택적)
try:
    from danbooru_module import get_danbooru_category_short, is_danbooru_available
    DANBOORU_AVAILABLE = is_danbooru_available()
except ImportError:
    DANBOORU_AVAILABLE = False
    def get_danbooru_category_short(tag):
        return "?"

# 태그 트리 모듈 임포트 (선택적)
try:
    from tag_tree_module import get_tag_tree_structure, is_tag_tree_available, get_category_color, create_tag_tree_item, TagTreeItem, create_tag_tree_section, update_tag_tree
    TAG_TREE_AVAILABLE = is_tag_tree_available()
except ImportError:
    TAG_TREE_AVAILABLE = False
    def get_tag_tree_structure(tags):
        return []
    def get_category_color(category_name):
        return "#10B981"  # 기본 녹색
    def create_tag_tree_item(text, item_type="category", tag_count=0, parent=None):
        return None
    def create_tag_tree_section(parent_widget):
        return None, None, None
    def update_tag_tree(tag_tree_layout, current_tags, category_expanded_state=None, on_tag_clicked=None, on_category_toggled=None):
        pass
    TagTreeItem = None

# 고급 검색 모듈 임포트
try:
    from advanced_search_module import create_advanced_search_widget, setup_search_focus_events
    ADVANCED_SEARCH_AVAILABLE = True
except ImportError:
    ADVANCED_SEARCH_AVAILABLE = False
    # advanced_search_module에서 import 실패 시 대체 함수들
    def create_advanced_search_widget(app_instance):
        return None
    def setup_search_focus_events(app_instance, search_input, advanced_search_card, preview_card, tag_tree_card):
        pass


class SectionCard(QFrame):
    """섹션별 카드 컨테이너"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SectionCard")
        self.setStyleSheet("""
            QFrame#SectionCard {
                background: rgba(17,17,27,0.9);
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 6px;
                margin: 4px;
            }
        """)
        
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(16, 16, 16, 16)
        self._root.setSpacing(6)
        
        if title:
            title_lbl = QLabel(title.upper())
            title_lbl.setStyleSheet("""
                font-size: 11px; 
                font-weight: 700;
                color: #9CA3AF; 
                letter-spacing: 1px;
                margin-bottom: 8px;
            """)
            self._root.addWidget(title_lbl)
        
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        self._root.addLayout(self.body)

# ImageThumbnail 클래스는 search_filter_grid_module.py로 이동됨

class ModernButton(QPushButton):
    """그라데이션 모던 버튼"""
    def __init__(self, text, color1="#10B981", color2="#059669", parent=None):
        super().__init__(text, parent)
        self.color1 = color1
        self.color2 = color2
        self.apply_style()
    
    def apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, 
                    stop:0 {self.color1}, stop:1 {self.color2});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 12px;
                min-height: 16px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, 
                    stop:0 {self.color1}DD, stop:1 {self.color2}DD);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, 
                    stop:0 {self.color2}, stop:1 {self.color1});
            }}
        """)




class AIImageTagger(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_image = None
        self.current_tags = []
        self.removed_tags = []  # 현재 이미지에서 취소된 태그들
        self.all_tags = {}  # {image_path: [tags]}
        self.image_removed_tags = {}  # {image_path: [removed_tags]} - 각 이미지별 취소된 태그
        self.image_files = []
        self.current_folder = None
        self.wd_tagger_thread = None
        self.global_tag_stats = {}  # {tag: count} - 전체 태그 통계
        self.tag_confidence = {}  # {image_path: [(tag, score), ...]} - 신뢰도 정보
        self.manual_tag_info = {}  # {tag: is_trigger} - 수동 입력 태그의 트리거 여부
        self.llava_tag_info = {}  # {tag: True} - LLaVA 태그 정보
        self.batch_tagging_in_progress = False  # 일괄 태깅 진행 중 플래그
        self.tag_tree_available = TAG_TREE_AVAILABLE  # 태그 트리 모듈 사용 가능 여부
        self.advanced_search_available = ADVANCED_SEARCH_AVAILABLE  # 고급 검색 모듈 사용 가능 여부
        
        # 태그 스타일시트 에디터 리모컨 초기화
        self.tag_stylesheet_editor_remote = None
        
        # 설정 모듈 초기화
        self.settings_module = None
        
        self.setup_ui()
        self.apply_theme()
        
        # 액션 버튼 모듈에서 다운로드 진행 상황 시그널 연결
        if hasattr(self, 'action_buttons_module'):
            self.action_buttons_module.setup_download_progress_connection()
        
        # 모델 미리 로드 비활성화 (버튼 클릭 시에만 로드)
        # self.preload_model()
    
    def setup_ui(self):
        self.setWindowTitle("AI Image Tagger — Modern Interface")
        self.setGeometry(100, 100, 1600, 960)
        
        # 창 헤더 숨기기 (제목 표시줄, 최소화/최대화/닫기 버튼 제거)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Central widget
        central_widget = QWidget()
        central_widget.setObjectName("CentralRoot")
        self.setCentralWidget(central_widget)
        
        # Main layout (horizontal - vertical nav + content)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left vertical navigation bar
        from left_navigation_module import LeftNavigationModule
        self.left_nav_module = LeftNavigationModule(self)
        vertical_nav = self.left_nav_module.create_vertical_navigation_bar()
        main_layout.addWidget(vertical_nav)
        
        # Right content area (top nav + panels)
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Top navigation bar
        from top_navigation_module import TopNavigationModule
        self.top_nav_module = TopNavigationModule(self)
        nav_bar = self.top_nav_module.create_navigation_bar()
        right_layout.addWidget(nav_bar)
        
        # Main horizontal splitter for all panels
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName("MainSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(0)
        
        # Left sidebar
        left_panel = self.create_left_panel()
        self.main_splitter.addWidget(left_panel)
        
        # Center panel with vertical splitter
        self.center_splitter = QSplitter(Qt.Vertical)
        self.center_splitter.setHandleWidth(0)
        
        # Top panel (image preview)
        top_panel = self.create_top_panel()
        self.center_splitter.addWidget(top_panel)
        
        # Bottom panel (tagging)
        bottom_panel = self.create_bottom_panel()
        self.center_splitter.addWidget(bottom_panel)
        
        # Set splitter proportions (60% top, 40% bottom)
        self.center_splitter.setSizes([600, 400])
        
        # Connect splitter resize event
        self.center_splitter.splitterMoved.connect(self.on_splitter_resized)
        
        self.main_splitter.addWidget(self.center_splitter)
        
        # Right panel
        right_panel = self.create_right_panel()
        self.main_splitter.addWidget(right_panel)
        
        # Set main splitter proportions (350px left, flexible center, 300px right)
        self.main_splitter.setSizes([350, 1200, 350])
        
        # Connect main splitter resize event (비디오 프리뷰 리사이즈용)
        self.main_splitter.splitterMoved.connect(self.on_main_splitter_resized)
        
        # Add to right content layout
        right_layout.addWidget(self.main_splitter)
        main_layout.addWidget(right_content)
        
        # Status bar
        self.create_statusbar()
    
    def on_splitter_resized(self, pos, index):
        """스플리터 크기 변경 시 이미지 프리뷰 리사이즈"""
        if self.current_image and hasattr(self, 'image_preview'):
            # 현재 이미지가 로드되어 있으면 프리뷰 영역에 맞춰 리사이즈
            self.resize_image_preview()
    
    def on_main_splitter_resized(self, pos, index):
        """메인 스플리터 크기 변경 시 비디오 프리뷰 리사이즈"""
        # 비디오 프리뷰 리사이즈
        if hasattr(self, 'video_frame_module') and self.video_frame_module:
            if hasattr(self.video_frame_module, 'video_preview_card'):
                video_preview = self.video_frame_module.video_preview_card
                if video_preview and hasattr(video_preview, 'update_video_widget_size'):
                    # 약간의 지연을 두어 레이아웃 완료 후 리사이즈
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(10, video_preview.update_video_widget_size)
    
    def resize_image_preview(self):
        """이미지 프리뷰를 현재 프리뷰 영역 크기에 맞춰 리사이즈"""
        if not self.current_image or not hasattr(self, 'image_preview'):
            return
            
        try:
            pixmap = QPixmap(self.current_image)
            if not pixmap.isNull():
                current_size = self.image_preview.size()
                if current_size.width() > 0 and current_size.height() > 0:
                    # 현재 프리뷰 영역에 맞춰 비율 유지하며 스케일링
                    scaled_pixmap = pixmap.scaled(
                        current_size, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.image_preview.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error resizing image preview: {e}")
    
    def create_left_panel(self):
        """좌측 사이드바 - 이미지 목록"""
        panel = QFrame()
        panel.setMinimumWidth(250)  # 최소 너비 250px로 설정
        panel.setMaximumWidth(700)
        panel.setObjectName("SidebarPanel")
        panel.setStyleSheet("""
            QFrame#SidebarPanel {
                background: rgba(17,17,27,0.9);
                border-right: 1px solid rgba(75,85,99,0.2);
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        
        # Search and Filter section (통합 섹션)
        from search_module import create_search_widget, create_search_dropdown_widget
        from search_filter_grid_module import create_filter_widget
        from search_filter_grid_image_module import create_image_grid_section
        
        # 통합된 Search & Filter 섹션 생성
        search_filter_card = SectionCard("SEARCH & FILTER")
        
        # 검색 위젯 추가 (검색창만)
        search_widget = create_search_widget(self)
        search_filter_card.body.addWidget(search_widget)
        
        # 고급 검색 포커스 이벤트는 create_top_panel에서 연결됨
        
        # 드롭다운들을 2열 1행으로 배치
        dropdown_layout = QHBoxLayout()
        dropdown_layout.setSpacing(8)  # 간격을 두 배로 증가 (4 → 8)
        dropdown_layout.setContentsMargins(0, 0, 0, 0)  # 패딩 0으로 설정
        
        # 검색 드롭다운 추가
        search_dropdown = create_search_dropdown_widget(self)
        dropdown_layout.addWidget(search_dropdown)
        
        # 필터 드롭다운 추가
        filter_dropdown = create_filter_widget(self)
        dropdown_layout.addWidget(filter_dropdown)
        
        # 드롭다운 레이아웃을 카드에 추가
        dropdown_widget = QWidget()
        dropdown_widget.setLayout(dropdown_layout)
        search_filter_card.body.addWidget(dropdown_widget)
        
        # 고급 검색 체크박스 추가 (드롭다운 밑에)
        from advanced_search_module import add_advanced_search_checkbox
        add_advanced_search_checkbox(self, filter_dropdown)
        
        # 이미지 그리드 섹션 생성
        list_card, image_counter = create_image_grid_section(self, SectionCard)
        
        layout.addWidget(search_filter_card)
        layout.addWidget(list_card, 1)
        layout.addWidget(image_counter)
        
        return panel
    
    def create_top_panel(self):
        """상단 패널 - 이미지 프리뷰와 태그 트리 배치"""
        panel = QWidget()
        panel.setObjectName("TopPanel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        # 상단 레이아웃
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(10)
        
        # 섹션 생성 및 저장
        from image_preview_module import create_image_preview_section
        from tag_tree_module import create_tag_tree_section
        
        self.preview_card = create_image_preview_section(self, SectionCard)
        if self.tag_tree_available:
            self.tag_tree_card = create_tag_tree_section(self, SectionCard)
        
        # 고급 검색 섹션 추가 (초기에는 숨김)
        if self.advanced_search_available:
            advanced_search_widget = create_advanced_search_widget(self)
            self.advanced_search_card = SectionCard("ADVANCED SEARCH")
            self.advanced_search_card.body.addWidget(advanced_search_widget)
            
            # 카드 외부 마진(14px) 적용 - tag_stylesheet_editor_module과 동일
            self.advanced_search_card.setStyleSheet("""
                QFrame#SectionCard {
                    background: rgba(17,17,27,0.9);
                    border: 1px solid rgba(75,85,99,0.2);
                    border-radius: 6px;
                    margin: 14px;
                }
            """)
            
            self.advanced_search_card.hide()  # 초기에는 숨김
            layout.addWidget(self.advanced_search_card)
            
            # 검색 위젯 찾아서 이벤트 연결
            if hasattr(self, 'filter_input') and self.filter_input:
                setup_search_focus_events(self, self.filter_input, self.advanced_search_card, 
                                        self.preview_card, self.tag_tree_card if self.tag_tree_available else None)
                print("고급 검색 포커스 이벤트 연결 완료")
            else:
                print("검색 위젯(filter_input)을 찾을 수 없습니다")
        
        # 기본 배치: 왼쪽 이미지 프리뷰, 오른쪽 태그 트리
        self.top_layout.addWidget(self.preview_card, 2)
        if self.tag_tree_available:
            self.top_layout.addWidget(self.tag_tree_card, 1)
        
        layout.addLayout(self.top_layout)
        
        return panel
    
    def update_image_grid(self, image_paths):
        """이미지 그리드 업데이트 (고급 검색 결과 표시용)"""
        try:
            if not image_paths:
                print("검색 결과가 없습니다.")
                return
            
            # 통합된 그리드 업데이트 함수 호출
            from search_module import update_image_grid_unified
            update_image_grid_unified(self)
            
        except Exception as e:
            print(f"이미지 그리드 업데이트 중 오류: {e}")
    
    def reset_to_original_images(self):
        """원본 이미지 목록으로 복원 (고급 검색 초기화용)"""
        try:
            # 통합된 검색 초기화 함수 호출
            from search_module import reset_all_searches
            reset_all_searches(self)
                
        except Exception as e:
            print(f"원본 이미지 복원 중 오류: {e}")
    
    def get_image_tags(self, image_path):
        """이미지의 태그 가져오기 (중앙 하단 태그 관리 모듈에서)"""
        try:
            # all_tags 딕셔너리에서 가져오기 (중앙 하단 태그 관리 모듈에서 저장된 태그)
            image_key = str(image_path)
            if image_key in self.all_tags:
                return self.all_tags[image_key]
            
            # 태그가 없으면 빈 리스트 반환
            return []
            
        except Exception as e:
            print(f"이미지 태그 로드 중 오류: {e}")
            return []
    
    def create_bottom_panel(self):
        """하단 패널 - 태깅"""
        panel = QWidget()
        panel.setObjectName("BottomPanel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 0, 10, 10)
        layout.setSpacing(6)
        
        # bottom_layout을 저장하여 다른 곳에서 접근 가능하도록 함
        self.bottom_layout = layout
        
        # Tagging section (모듈에서 처리)
        from image_tagging_module import create_tagging_section
        self.tagging_card = create_tagging_section(self, SectionCard)
        
        # 시그널 연결 (is_trigger 파라미터 추가)
        if hasattr(self, 'tag_input_widget') and self.tag_input_widget:
            self.tag_input_widget.tagAdded.connect(self.add_tag_with_trigger)
            self.tag_input_widget.tagAddedToAll.connect(self.add_tag_to_all_images_with_trigger)
        
        layout.addWidget(self.tagging_card, 1)
        
        return panel
    
    def create_right_panel(self):
        """우측 패널 - 태그 관리"""
        panel = QWidget()
        panel.setObjectName("RightPanel") 
        panel.setStyleSheet("""
            QWidget#RightPanel {
                background: rgba(17,17,27,0.9);
                border-left: 1px solid rgba(75,85,99,0.2);
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        # 태그 통계 모듈 사용
        from tag_statistics_module import TagStatisticsModule
        self.tag_statistics_module = TagStatisticsModule(self)
        tags_card = self.tag_statistics_module.create_tag_statistics_section()
        layout.addWidget(tags_card, 1)
        
        # Action buttons
        from action_buttons_module import ActionButtonsModule
        self.action_buttons_module = ActionButtonsModule(self)
        action_card = self.action_buttons_module.create_action_buttons_section()
        layout.addWidget(action_card)
        
        return panel
    
    def create_statusbar(self):
        """상태바 생성"""
        sb = QStatusBar()
        sb.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(17,24,39,0.9), stop:1 rgba(31,41,55,0.7));
                color: #9CA3AF;
                border-top: 1px solid rgba(75,85,99,0.3);
                padding: 8px 16px;
                font-size: 11px;
            }
        """)
        self.setStatusBar(sb)
        sb.showMessage("Ready — No folder loaded")
        
        # 모듈 초기화
        self.initialize_modules()
    
    def initialize_modules(self):
        """모듈들 초기화"""
        try:
            # 설정 모듈 초기화
            from settings_module import SettingsModule
            self.settings_module = SettingsModule(self)
            print("✅ 설정 모듈 초기화 완료")
        except ImportError as e:
            print(f"❌ 설정 모듈 초기화 실패: {e}")
            self.settings_module = None
    
    def apply_theme(self):
        """전체 테마 적용"""
        self.setStyleSheet("""
            /* Global */
            QMainWindow {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #0A0A0F, stop:1 #0D0D14);
            }
            
            QWidget {
                font-family: "Segoe UI", "SF Pro Display", -apple-system, sans-serif;
                color: #F0F2F5;
            }
            
            /* Scrollbars */
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
            
            QScrollBar:horizontal {
                background: rgba(26,27,38,0.8);
                height: 8px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:horizontal {
                background: rgba(75,85,99,0.6);
                border-radius: 4px;
                min-width: 20px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background: rgba(75,85,99,0.8);
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: rgba(26,27,38,1.0);
            }
            
            /* Inputs - 모든 입력 위젯 높이 통일 (15px) */
            QLineEdit {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(17,24,39,0.8), stop:1 rgba(31,41,55,0.6));
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                padding: 10px 10px;
                font-size: 12px;
                min-height: 15px;
                max-height: 15px;
            }
            
            QLineEdit:focus {
                border: 2px solid #3B82F6;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(30,58,138,0.2), stop:1 rgba(37,99,235,0.1));
            }
            
            QSpinBox {
                border-radius: 4px;
                padding: 10px 10px;
                min-height: 15px;
                max-height: 15px;
            }
            
            QDoubleSpinBox {
                border-radius: 4px;
                padding: 10px 10px;
                min-height: 15px;
                max-height: 15px;
            }
            
            QComboBox {
                border-radius: 4px;
                padding: 10px 10px;
                min-height: 15px;
                max-height: 15px;
            }
            
            
            /* Splitter */
            QSplitter::handle {
                background: rgba(75,85,99,0.2);
                width: 1px;
            }
            
            /* ScrollArea */
            QScrollArea {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                border: none;
            }
        """)
    
    # Event handlers - 폴더 관련 함수들은 left_navigation_module.py로 이동됨
    
    def refresh_image_thumbnails(self):
        """필터에 따라 이미지 썸네일 새로고침 (통합 모듈에서 처리)"""
        from search_module import update_image_grid_unified
        update_image_grid_unified(self)
    
    def create_thumbnails_async(self, filtered_images):
        """썸네일을 비동기로 생성 (모듈에서 처리)"""
        from search_filter_grid_image_module import create_thumbnails_async
        create_thumbnails_async(self, filtered_images)
    
    def create_thumbnail_batch(self, filtered_images):
        """배치로 썸네일 생성 (모듈에서 처리)"""
        from search_filter_grid_image_module import create_thumbnail_batch
        create_thumbnail_batch(self, filtered_images)
    
    # 이미지 프리뷰 관련 메서드들은 image_preview_module.py로 이동됨
    
    def clear_current_tags(self):
        """현재 태그들 초기화"""
        # 태그 리스트 초기화
        self.current_tags.clear()
        
        # 통계 업데이트
        self.update_tag_stats()
    
    # update_thumbnail_selection은 image_preview_module.py로 이동됨
    
    def add_tag(self, tag):
        """태그 추가 (모듈에서 처리)"""
        from image_tagging_module import add_tag
        add_tag(self, tag)
    
    def add_tag_with_trigger(self, tag, is_trigger=False):
        """태그 추가 (트리거 정보 포함)"""
        from image_tagging_module import add_tag
        add_tag(self, tag, is_trigger)
    
    def add_tag_to_all_images(self, tag):
        """검색된 모든 이미지에 태그 추가"""
        from image_tagging_module import add_tag_to_all_images
        add_tag_to_all_images(self, tag)
    
    def add_tag_to_all_images_with_trigger(self, tag, is_trigger=False):
        """검색된 모든 이미지에 태그 추가 (트리거 정보 포함)"""
        from image_tagging_module import add_tag_to_all_images
        add_tag_to_all_images(self, tag, is_trigger)
    
    def remove_tag(self, tag):
        """태그 제거 (모듈에서 처리)"""
        from image_tagging_module import remove_tag
        remove_tag(self, tag)
    
    def toggle_current_tag(self, tag, checked):
        """현재 이미지의 태그 활성화/비활성화 (모듈에서 처리)"""
        from image_tagging_module import toggle_current_tag
        toggle_current_tag(self, tag, checked)
    
    def update_tag_stats(self):
        """태그 통계 업데이트 (모듈에서 처리)"""
        from image_tagging_module import update_tag_stats
        update_tag_stats(self)
    
    def update_current_tags_display(self):
        """현재 이미지의 태그들을 중앙 패널에 표시 (모듈에서 처리)"""
        from image_tagging_module import update_current_tags_display
        update_current_tags_display(self)
    
    def update_global_tag_stats(self):
        """전체 태그 통계 업데이트 (모듈에서 처리)"""
        from image_tagging_module import update_global_tag_stats
        update_global_tag_stats(self)
        
        # 태그 통계 모듈에서도 업데이트
        if hasattr(self, 'tag_statistics_module'):
            self.tag_statistics_module.update_global_tag_statistics()
    
    def update_tag_tree(self):
        """태그 트리 업데이트 (모듈에서 처리)"""
        if not self.tag_tree_available or not hasattr(self, 'tag_tree_layout'):
            return
        
        # 카테고리 확장 상태 초기화
        if not hasattr(self, 'category_expanded_state'):
            self.category_expanded_state = {}
        
        # 모듈의 update_tag_tree 함수 호출
        update_tag_tree(
            self.tag_tree_layout, 
            self.current_tags, 
            self.category_expanded_state,
            self.on_tag_tree_item_clicked,
            self.on_category_toggled,
            self.removed_tags,
            self.on_removed_tag_clicked,
            self  # app_instance 전달
        )
        
        # 컨테이너 크기 동적 조정 (비활성화 - 스크롤 사라짐 방지)
        # self.adjust_tag_tree_container_size()
    
    def adjust_tag_tree_container_size(self):
        """태그 트리 컨테이너 크기를 동적으로 조정 (모듈에서 처리)"""
        from tag_tree_module import adjust_container_size
        adjust_container_size(self)
    
    def on_tag_tree_item_clicked(self, tag_text):
        """태그 트리에서 태그 클릭 시 처리 (모듈에서 처리)"""
        from tag_tree_module import handle_tag_click
        handle_tag_click(self, tag_text)
    
    def on_category_toggled(self, category_name, is_expanded):
        """카테고리 확장/축소 토글 처리 (모듈에서 처리)"""
        from tag_tree_module import handle_category_toggle
        handle_category_toggle(self, category_name, is_expanded)
    
    def on_removed_tag_clicked(self, tag_text):
        """removed 태그 클릭 시 액티브로 복원 (모듈에서 처리)"""
        from tag_tree_module import handle_removed_tag_click
        handle_removed_tag_click(self, tag_text)
    
    def update_global_tags_list(self):
        """전체 태그 통계 리스트 업데이트 (모듈에서 처리)"""
        if hasattr(self, 'tag_statistics_module'):
            self.tag_statistics_module.update_global_tags_list()
    
    # 모델 다운로드 관련 메서드들은 action_buttons_module.py로 이동됨
    
    # 다운로드 진행 상황 관련 메서드들은 action_buttons_module.py로 이동됨
    
    # 다운로드 진행 상황 관련 메서드들은 action_buttons_module.py로 이동됨
    
    def on_ai_progress_updated(self, current, total):
        """AI 태깅 진행률 업데이트"""
        self.ai_progress_label.setText(f"AI 태깅 중... ({current}/{total})")
        self.ai_progress_bar.setMaximum(total)  # 태깅 시에는 total 개수로 설정
        self.ai_progress_bar.setValue(current)
    
    def on_ai_tag_generated(self, image_path, tags_with_scores):
        """AI 태그 생성 완료 (신뢰도 포함)"""
        # tags_with_scores는 [(tag, score), (tag, score), ...] 형태
        print(f"AI 태그 생성 완료: {Path(image_path).name}, 태그 수: {len(tags_with_scores)}")
        
        # 태그와 신뢰도 정보 저장 - all_tags 관리 플러그인 사용
        tags = [tag for tag, score in tags_with_scores]
        from all_tags_manager import set_tags_for_image
        set_tags_for_image(self, image_path, tags)
        self.tag_confidence[image_path] = tags_with_scores
        
        # LLaVA 태그 정보 저장
        for tag in tags:
            self.llava_tag_info[tag] = True
        
        # 현재 이미지인 경우 UI 업데이트
        if image_path == self.current_image:
            self.current_tags = tags.copy()
            self.update_current_tags_display()
            self.update_tag_stats()
        
        # 태그 트리 업데이트
        self.update_tag_tree()
    
    def on_ai_finished(self):
        """AI 태깅 완료"""
        self.ai_progress_label.hide()
        self.ai_progress_bar.hide()
        
        # LLaVA 태거 스레드 정리
        if hasattr(self, 'llava_tagger_thread') and self.llava_tagger_thread:
            self.llava_tagger_thread.deleteLater()
            self.llava_tagger_thread = None
        
        # WD 태거 스레드 정리
        if hasattr(self, 'wd_tagger_thread') and self.wd_tagger_thread:
            self.wd_tagger_thread.deleteLater()
            self.wd_tagger_thread = None
        
        # 썸네일 새로고침
        if hasattr(self, 'refresh_image_thumbnails'):
            self.refresh_image_thumbnails()
            self.batch_tagging_in_progress = False
            
        # 태깅 완료 후 스타일시트 에디터 업데이트
        self.is_ai_tagging = False
        if hasattr(self, 'tag_stylesheet_editor') and self.tag_stylesheet_editor:
            self.tag_stylesheet_editor.schedule_update()
        
        # 태그 통계 모듈 강제 업데이트 (단체 태깅 완료 후)
        if hasattr(self, 'tag_statistics_module') and self.tag_statistics_module:
            print("단체 태깅 완료 - 태그 통계 모듈 강제 업데이트")
            self.tag_statistics_module.update_global_tag_statistics()
        
        # 버튼 활성화
        if hasattr(self, 'btn_auto_tag'):
            self.btn_auto_tag.setEnabled(True)
        if hasattr(self, 'btn_batch_auto_tag'):
            self.btn_batch_auto_tag.setEnabled(True)
        
        self.statusBar().showMessage("AI 태깅 완료!")
    
    def on_ai_error(self, error_message):
        """AI 태깅 오류"""
        self.ai_progress_label.hide()
        self.ai_progress_bar.hide()
        
        # 버튼 활성화
        if hasattr(self, 'btn_auto_tag'):
            self.btn_auto_tag.setEnabled(True)
        if hasattr(self, 'btn_batch_auto_tag'):
            self.btn_batch_auto_tag.setEnabled(True)
        
        if hasattr(self, 'action_buttons_module'):
            self.action_buttons_module.show_custom_message("AI 태깅 오류", error_message, "error")
        self.statusBar().showMessage("AI 태깅 실패")
        
        # 스레드 정리
        if hasattr(self, 'wd_tagger_thread') and self.wd_tagger_thread:
            self.wd_tagger_thread.deleteLater()
            self.wd_tagger_thread = None
        if hasattr(self, 'llava_tagger_thread') and self.llava_tagger_thread:
            self.llava_tagger_thread.deleteLater()
            self.llava_tagger_thread = None
    
    def on_llava_model_loading_started(self, message):
        """LLaVA 모델 로딩 시작"""
        print(f"[UI] {message}")
        self.ai_progress_label.setText(message)
        self.ai_progress_bar.setValue(0)
        self.ai_progress_bar.setMaximum(100)  # 진행률 0-100%
    
    # 중복된 메서드 제거됨
    
    def auto_tag_current_image(self):
        """현재 이미지에 AI 태깅 적용"""
        if not self.current_image:
            if hasattr(self, 'action_buttons_module'):
                self.action_buttons_module.show_custom_message("경고", "먼저 이미지를 선택해주세요.", "warning")
            return
        
        self.batch_auto_tag_images([self.current_image])
    
    def batch_auto_tag_images(self, image_paths=None):
        """여러 이미지에 일괄 AI 태깅 적용"""
        print("배치 오토 태그 시작!")
        print(f"image_paths: {image_paths}")
        print(f"self.image_files: {self.image_files}")
        print(f"self.current_folder: {self.current_folder}")
        
        # image_paths가 None이 아니고 유효한 리스트가 아닌 경우 None으로 설정
        if image_paths is not None and not isinstance(image_paths, list):
            print(f"image_paths가 유효하지 않음: {image_paths}, None으로 설정")
            image_paths = None
        
        if image_paths is None:
            # 1) 다중선택이 있으면 그것만 태깅
            from search_filter_grid_module import get_multi_selected_images
            multi_selected_images = get_multi_selected_images(self)
            if multi_selected_images:
                image_paths = multi_selected_images
                print(f"다중선택된 이미지 기반으로 태깅: {len(image_paths)}개")
            else:
                # 2) 다중선택이 없으면 '현재 그리드에 표시되는 전체 결과(모든 페이지)' 기준으로 태깅
                is_video_mode = False
                if hasattr(self, 'image_filter_btn') and hasattr(self, 'video_filter_btn'):
                    is_video_mode = self.video_filter_btn.isChecked() and not self.image_filter_btn.isChecked()
                
                if is_video_mode:
                    # 비디오 모드: 현재 그리드(필터/검색 AND 반영) 전체
                    source_list = getattr(self, 'video_filtered_list', getattr(self, 'video_files', []))
                else:
                    # 이미지 모드: 현재 그리드(필터/검색 AND 반영) 전체
                    source_list = getattr(self, 'image_filtered_list', getattr(self, 'image_files', []))
                
                if not source_list:
                    print("태깅할 항목이 없음 (현재 그리드 비어 있음)")
                    if hasattr(self, 'action_buttons_module'):
                        self.action_buttons_module.show_custom_message("알림", "현재 그리드에 태깅할 항목이 없습니다.", "info")
                    return
                
                image_paths = [str(path) for path in source_list]
                print(f"현재 그리드 전체 기준으로 태깅: {len(image_paths)}개")
        
        if not image_paths:
            print("태깅할 이미지가 없음")
            if hasattr(self, 'action_buttons_module'):
                self.action_buttons_module.show_custom_message("경고", "태깅할 이미지가 없습니다.", "warning")
            return
        
        print(f"처리할 이미지 수: {len(image_paths)}")
        print(f"처리할 이미지 목록: {image_paths[:3]}...")  # 처음 3개만 출력
        
        # 기존 스레드가 실행 중이면 중단
        if self.wd_tagger_thread and self.wd_tagger_thread.isRunning():
            if hasattr(self, 'action_buttons_module'):
                self.action_buttons_module.show_custom_message("정보", "이미 AI 태깅이 진행 중입니다.", "info")
            return
        
        # 모델 정보 표시
        print(f"모델 ID: {self.current_model_id}")
        
        # 진행률 표시 시작
        self.ai_progress_label.setText(f"AI 태깅 중... (0/{len(image_paths)})")
        self.ai_progress_label.show()
        self.ai_progress_bar.setMaximum(len(image_paths))
        self.ai_progress_bar.setValue(0)
        self.ai_progress_bar.show()
        
        # 버튼 비활성화
        self.btn_auto_tag.setEnabled(False)
        self.btn_batch_auto_tag.setEnabled(False)
        
        # 일괄 태깅 시작 플래그 설정
        self.batch_tagging_in_progress = True
        self.is_ai_tagging = True  # 태깅 중 플래그 설정
        print("일괄 태깅 시작 - 필터 업데이트 비활성화")
        
        # 모델 타입에 따른 처리 (모듈에서 확인)
        
        if self.model_selector.is_llava_model():
            # LLaVA 모델로 태깅 시작
            print("LLaVA 모델로 태깅 시작")
            self.statusBar().showMessage("LLaVA 모델 로드 중.")
            try:
                # 모델 타입에 따라 적절한 스레드 사용
                if "llava-1.5" in self.current_model_id.lower():
                    from llava_captioner_module import LLaVATaggerThread
                    self.llava_tagger_thread = LLaVATaggerThread(
                        image_paths=image_paths,
                        model_id=self.current_model_id,
                        use_gpu=self.use_gpu
                    )
                elif "llava-v1.6" in self.current_model_id.lower() or "llava-next" in self.current_model_id.lower():
                    from llava_next_tagger import LLaVANextTaggerThread
                    self.llava_tagger_thread = LLaVANextTaggerThread(
                        image_paths=image_paths,
                        model_id=self.current_model_id,
                        use_gpu=self.use_gpu
                    )
                elif "llava-interleave" in self.current_model_id.lower():
                    from llava_interleave_tagger import LLaVAInterleaveTaggerThread
                    self.llava_tagger_thread = LLaVAInterleaveTaggerThread(
                        image_paths=image_paths,
                        model_id=self.current_model_id,
                        use_gpu=self.use_gpu
                    )
                elif "vip-llava" in self.current_model_id.lower():
                    from llava_vip_tagger import VipLlavaTaggerThread
                    self.llava_tagger_thread = VipLlavaTaggerThread(
                        image_paths=image_paths,
                        model_id=self.current_model_id,
                        use_gpu=self.use_gpu
                    )
                elif "llava-llama-3" in self.current_model_id.lower():
                    from llava_llama3_tagger import LLaVALlama3TaggerThread
                    self.llava_tagger_thread = LLaVALlama3TaggerThread(
                        image_paths=image_paths,
                        model_id=self.current_model_id,
                        use_gpu=self.use_gpu
                    )
                else:
                    # 기본 LLaVA 1.5 스레드 사용
                    from llava_captioner_module import LLaVATaggerThread
                    self.llava_tagger_thread = LLaVATaggerThread(
                        image_paths=image_paths,
                        model_id=self.current_model_id,
                        use_gpu=self.use_gpu
                    )
                
                # 신호 연결 (WD와 동일 핸들러 재사용 + 모델 로딩 진행 시그널 추가)
                self.llava_tagger_thread.progress_updated.connect(self.on_ai_progress_updated)
                self.llava_tagger_thread.model_loading_started.connect(self.on_llava_model_loading_started)
                self.llava_tagger_thread.model_loading_progress.connect(self.on_llava_model_loading_progress)
                self.llava_tagger_thread.model_loading_finished.connect(self.on_llava_model_loading_finished)
                self.llava_tagger_thread.tag_generated.connect(self.on_ai_tag_generated)
                self.llava_tagger_thread.finished.connect(self.on_ai_finished)
                self.llava_tagger_thread.error_occurred.connect(self.on_ai_error)
                self.llava_tagger_thread.start()
            except Exception as e:
                print(f"LLaVA 태깅 시작 오류: {e}")
                self.on_ai_error(str(e))
        else:
# WD Tagger 모델인 경우
            print("WD Tagger 모델로 태깅 시작")
            self.statusBar().showMessage("WD Tagger 모델 로드 중...")
            self.wd_tagger_thread = WdTaggerThread(
                image_paths=image_paths,
                model_id=self.current_model_id,
                exclude_tags=["rating:general", "rating:sensitive", "rating:questionable", "rating:explicit"],
                use_gpu=self.use_gpu
            )
            
            # 신호 연결
            self.wd_tagger_thread.progress_updated.connect(self.on_ai_progress_updated)
            self.wd_tagger_thread.tag_generated.connect(self.on_ai_tag_generated)
            self.wd_tagger_thread.finished.connect(self.on_ai_finished)
            self.wd_tagger_thread.error_occurred.connect(self.on_ai_error)
            
            self.wd_tagger_thread.start()
    
    def on_llava_model_loading_started(self, message):
        """LLaVA 모델 로딩 시작"""
        print(f"[UI] {message}")
        self.ai_progress_label.setText(message)
        self.ai_progress_bar.setValue(0)
        self.ai_progress_bar.setMaximum(100)  # 진행률 0-100%
    
    def on_llava_model_loading_progress(self, status, progress):
        """LLaVA 모델 로딩 진행 상태 업데이트"""
        try:
            print(f"[UI] 모델 로딩 진행: {status} ({progress}%)")
            print(f"[DEBUG] 진행바 업데이트: {progress}%")
            print(f"[DEBUG] 진행바 설정 전 - maximum: {self.ai_progress_bar.maximum()}, value: {self.ai_progress_bar.value()}")
            
            # 진행바 maximum이 100이 아닌 경우 100으로 설정
            if self.ai_progress_bar.maximum() != 100:
                self.ai_progress_bar.setMaximum(100)
                print(f"[DEBUG] 진행바 maximum을 100으로 설정")
            
            # UI 업데이트를 안전하게 처리
            self.ai_progress_label.setText(f"{status} ({progress}%)")
            self.ai_progress_label.show()  # 라벨 표시
            self.ai_progress_bar.setValue(progress)
            self.ai_progress_bar.show()  # 진행바 표시
            
            # UI 즉시 갱신
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            
            print(f"[DEBUG] 진행바 값 설정 후: {self.ai_progress_bar.value()}% (maximum: {self.ai_progress_bar.maximum()})")
            
        except Exception as e:
            print(f"[DEBUG] UI 업데이트 오류: {e}")
            # 오류가 발생해도 기본적인 업데이트는 시도
            try:
                self.ai_progress_bar.setValue(progress)
                self.ai_progress_label.setText(f"모델 로딩 중... ({progress}%)")
            except:
                pass
    
    def on_llava_model_loading_finished(self):
        """LLaVA 모델 로딩 완료"""
        print("[UI] 모델 로딩 완료")
        # 태깅 진행바는 on_ai_progress_updated에서 처리
    
    def on_ai_progress_updated(self, current, total):
        """AI 태깅 진행률 업데이트"""
        self.ai_progress_label.setText(f"AI 태깅 중... ({current}/{total})")
        self.ai_progress_bar.setMaximum(total)  # 태깅 시에는 total 개수로 설정
        self.ai_progress_bar.setValue(current)
    
    def on_ai_tag_generated(self, image_path, tags_with_scores):
        """AI 태그 생성 완료 (신뢰도 포함)"""
        # tags_with_scores는 [(tag, score), (tag, score), ...] 형태
        print(f"AI 태그 생성 완료: {Path(image_path).name}, 태그 수: {len(tags_with_scores)}")
        
        # 디버깅: 함수 시작 시 기존 태그 상태 확인
        print("[DBG] BEFORE", len(self.all_tags.get(image_path, [])), self.all_tags.get(image_path, []))
        
        # 태그만 추출 (신뢰도 제외)
        tags = [tag for tag, score in tags_with_scores]
        
        # 기존 태그들 유지하고 AI 태그 추가 - all_tags 관리 플러그인 사용
        from all_tags_manager import get_tags_for_image, set_tags_for_image
        existing_tags = get_tags_for_image(self, image_path)
        
        # AI 태그들을 기존 태그에 추가 (중복 제거)
        for tag in tags:
            if tag not in existing_tags:
                existing_tags.append(tag)
        
        # 업데이트된 태그 리스트 저장
        set_tags_for_image(self, image_path, existing_tags)
        
        # 신뢰도 정보 저장 (UI 표시용)
        if not hasattr(self, 'tag_confidence'):
            self.tag_confidence = {}
        
        # LLaVA 태그인지 확인 (score == -1.0인 태그가 있는지)
        is_llava_tagging = any(score == -1.0 for _, score in tags_with_scores)
        
        if is_llava_tagging:
            # LLaVA 태깅: 기존 신뢰도 정보에 추가
            if image_path in self.tag_confidence:
                # 기존 WD 태그들과 새로운 LLaVA 태그들 합치기
                existing_scores = self.tag_confidence[image_path]
                combined_scores = existing_scores + tags_with_scores
                self.tag_confidence[image_path] = combined_scores
            else:
                self.tag_confidence[image_path] = tags_with_scores.copy()
            
            # LLaVA 태그 딕셔너리에 저장
            if not hasattr(self, 'llava_tag_info'):
                self.llava_tag_info = {}
            for tag, score in tags_with_scores:
                if score == -1.0:  # LLaVA 태그
                    self.llava_tag_info[tag] = True
        else:
            # WD 태깅: 기존 LLaVA 태그는 보존하고 WD 태그만 업데이트
            if image_path in self.tag_confidence:
                # 기존 신뢰도 정보에서 LLaVA 태그들 추출
                existing_scores = self.tag_confidence[image_path]
                llava_tags = [(tag, score) for tag, score in existing_scores if score == -1.0]
                # LLaVA 태그 + 새로운 WD 태그들
                combined_scores = llava_tags + tags_with_scores
                self.tag_confidence[image_path] = combined_scores
            else:
                self.tag_confidence[image_path] = tags_with_scores.copy()
        
        # 새로 추가된 AI 태그들만 통계에 추가 - 글로벌 태그 관리 플러그인 사용
        from all_tags_manager import get_tags_for_image
        from global_tag_manager import add_global_tag
        original_tags = get_tags_for_image(self, image_path)
        for tag in tags:
            if tag not in original_tags:
                add_global_tag(self, tag, False)
        
        # 현재 이미지가 태깅된 이미지라면 태그 리스트 업데이트
        if self.current_image == image_path:
            print(f"현재 이미지 태그 업데이트: {Path(image_path).name}")
            self.current_tags = existing_tags.copy()  # 기존 태그 + AI 태그
            self.removed_tags.clear()  # AI 태깅 시 취소된 태그 초기화
            self.update_tag_stats()
            self.update_tag_tree()  # 태그 트리 실시간 업데이트
        
        # 전체 태그 통계 UI 업데이트 (실시간)
        self.update_global_tag_stats()
        
        # 디버깅: 함수 끝에서 최종 태그 상태 확인
        print("[DBG] AFTER ", len(self.all_tags.get(image_path, [])), self.all_tags.get(image_path, []))
        
        # 태그 스타일시트 에디터 업데이트 (실시간)
        if hasattr(self, 'tag_stylesheet_editor') and self.tag_stylesheet_editor:
            self.tag_stylesheet_editor.schedule_update()
        
        # 필터 업데이트 (일괄 태깅 중이 아닐 때만)
        if not self.batch_tagging_in_progress:
            self.refresh_image_thumbnails()
        
        # 상태바 업데이트
        image_name = Path(image_path).name
        self.statusBar().showMessage(f"AI 태깅 완료: {image_name} ({len(tags)}개 태그)")
    
    def on_ai_finished(self):
        """AI 태깅 완료"""
        self.ai_progress_label.hide()
        self.ai_progress_bar.hide()
        
        # 일괄 태깅이 완료되면 필터를 한 번만 업데이트
        if self.batch_tagging_in_progress:
            print("일괄 태깅 완료, 필터 업데이트")
            self.refresh_image_thumbnails()
            self.batch_tagging_in_progress = False
            
        # 태깅 완료 후 스타일시트 에디터 업데이트
        self.is_ai_tagging = False
        if hasattr(self, 'tag_stylesheet_editor') and self.tag_stylesheet_editor:
            self.tag_stylesheet_editor.schedule_update()
        
        # 태그 통계 모듈 강제 업데이트 (단체 태깅 완료 후)
        if hasattr(self, 'tag_statistics_module') and self.tag_statistics_module:
            print("단체 태깅 완료 - 태그 통계 모듈 강제 업데이트")
            self.tag_statistics_module.update_global_tag_statistics()
        
        # 버튼 활성화
        self.btn_auto_tag.setEnabled(True)
        self.btn_batch_auto_tag.setEnabled(True)
        
        self.statusBar().showMessage("AI 태깅 완료!")
        
        # 스레드 정리
        if self.wd_tagger_thread:
            self.wd_tagger_thread.deleteLater()
            self.wd_tagger_thread = None
    
    def on_ai_error(self, error_message):
        """AI 태깅 오류"""
        self.ai_progress_label.hide()
        self.ai_progress_bar.hide()
        
        # 버튼 활성화
        self.btn_auto_tag.setEnabled(True)
        self.btn_batch_auto_tag.setEnabled(True)
        
        if hasattr(self, 'action_buttons_module'):
            self.action_buttons_module.show_custom_message("AI 태깅 오류", error_message, "error")
        self.statusBar().showMessage("AI 태깅 실패")
        
        # 스레드 정리
        if self.wd_tagger_thread:
            self.wd_tagger_thread.deleteLater()
            self.wd_tagger_thread = None
    
    def preload_model(self):
        """모델 미리 로드 (백그라운드)"""
        def load_model_async():
            try:
                print("모델 미리 로드 시작...")
                get_global_tagger(self.current_model_id, use_gpu=self.use_gpu)
                print("모델 미리 로드 완료!")
                self.statusBar().showMessage("AI 모델 로드 완료 - 태깅 준비됨")
            except Exception as e:
                print(f"모델 미리 로드 실패: {e}")
                self.statusBar().showMessage("AI 모델 로드 실패")
        
        # 백그라운드에서 모델 로드
        QTimer.singleShot(1000, load_model_async)  # 1초 후 시작
    
    
    
    # show_custom_message 메서드는 action_buttons_module.py로 이동됨
    
    def open_settings(self):
        """설정 창 열기"""
        if hasattr(self, 'settings_module'):
            self.settings_module.open_settings()
        else:
            print("설정 모듈이 초기화되지 않았습니다.")
    
    def closeEvent(self, event):
        """프로그램 종료 시 호출되는 이벤트"""
        # plugins/ffmpeg/images 폴더 비우기
        try:
            if hasattr(self, 'video_frame_module') and self.video_frame_module:
                if hasattr(self.video_frame_module, 'frame_extraction_options'):
                    frame_extraction = self.video_frame_module.frame_extraction_options
                    if frame_extraction:
                        frame_extraction.clear_extracted_images_folder()
        except Exception as e:
            print(f"⚠️ 프로그램 종료 시 이미지 폴더 정리 실패: {e}")
        
        # 기본 종료 처리
        event.accept()

# Flow layout for tags


def main():
    app = QApplication(sys.argv)
    app.setStyle("Windows")
    
    # Set application font
    font = app.font()
    font.setFamily("Segoe UI")
    app.setFont(font)
    
    window = AIImageTagger()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()