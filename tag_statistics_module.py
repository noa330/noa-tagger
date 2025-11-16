#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QFrame, QPushButton
from PySide6.QtCore import Qt, Signal, QSize


# ---- soft-wrapping helper (adds zero‑width spaces to allow wrapping of long unbroken tokens) ----
def insert_wrap_opportunities(s: str) -> str:
    try:
        # Only modify when there are no natural breakpoints and length is long
        if s and (" " not in s) and (len(s) > 18):
            # insert zero-width space between characters
            return "\u200b".join(list(s))
        return s
    except Exception:
        return s
# ---- end helper ----

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
            self.title_lbl = QLabel(title.upper())
            self.title_lbl.setStyleSheet("""
                font-size: 11px; 
                font-weight: 700;
                color: #9CA3AF; 
                letter-spacing: 1px;
                margin-bottom: 8px;
            """)
            self.title_lbl.setTextFormat(Qt.RichText)  # HTML 지원
            self._root.addWidget(self.title_lbl)
        
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(4)
        self._root.addLayout(self.body)
    
    def update_title(self, new_title: str):
        """헤더 제목 업데이트"""
        if hasattr(self, 'title_lbl'):
            self.title_lbl.setText(new_title.upper())

class TagListItem(QFrame):
    """태그 리스트 아이템"""
    removed = Signal(str)
    
    def __init__(self, text: str, category: str = "auto", confidence: float = None, app_instance=None, parent=None, count: int = 0):
        super().__init__(parent)
        self.tag_text = text
        self.app_instance = app_instance
        self.count = count
        self.setObjectName("TagListItem")
        self.setStyleSheet("""
            QFrame#TagListItem {
                background: rgba(255,255,255,0.035);
                border: none;
                border-radius: 8px;
                margin: 2px 0px;
            }
            QFrame#TagListItem:hover {
                background: rgba(255,255,255,0.055);
            }
        """)
        
        
        # 프레임 자체가 세로로 충분히 늘어날 수 있도록 허용
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # Tag info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # LLaVA 태그인지 확인 (llava_tag_info 딕셔너리에 있는 경우)
        is_llava_tag = False
        if app_instance and hasattr(app_instance, 'llava_tag_info'):
            is_llava_tag = text in app_instance.llava_tag_info
        
        # 태그 이름 표시 (카운트 번호 제거)
        self.name_label = QLabel(insert_wrap_opportunities(text))
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # LLaVA 태그는 은색으로 표시
        if is_llava_tag:
            self.name_label.setStyleSheet("""
                font-size: 12px;
                font-weight: 600;
                color: #9CA3AF;
                background: transparent;
            """)
        else:
            self.name_label.setStyleSheet("""
                font-size: 12px;
                font-weight: 600;
                color: #FFFFFF;
                background: transparent;
            """)
        
        # 이미지 개수와 카테고리 정보 표시
        image_count = 0
        if self.app_instance and hasattr(self.app_instance, 'global_tag_stats'):
            tag_stat = self.app_instance.global_tag_stats.get(text, 0)
            if isinstance(tag_stat, dict):
                image_count = tag_stat.get('image_count', 0)
            else:
                image_count = tag_stat
        
        # 카테고리 일관 분류 (중앙 집중 로직 사용)
        resolved_category = None
        try:
            if hasattr(self.app_instance, 'tag_statistics_module') and hasattr(self.app_instance.tag_statistics_module, 'resolve_category'):
                resolved_category = self.app_instance.tag_statistics_module.resolve_category(text)
        except Exception:
            resolved_category = None
        display_category = resolved_category or category or "unknown"
        meta_text = f"{count}. {display_category} • {image_count} images" if count > 0 else f"{display_category} • {image_count} images"
        
        # WD 태그인 경우 신뢰도 표시
        if confidence is not None and confidence > 0.0:
            meta_text += f" • {int(confidence*100)}%"
        
        self.meta_label = QLabel(meta_text)
        self.meta_label.setWordWrap(True)
        self.meta_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.meta_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.meta_label.setStyleSheet("""
            font-size: 10px;
            color: #D1D5DB;
            background: transparent;
        """)
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.meta_label)
        
        layout.addLayout(info_layout)
        
        # Edit button (펜 모양) - 반투명 하얀색 라운드 사각형
        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setFixedSize(30, 30)
        self.edit_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.3);
                color: #374151;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.5);
                color: #1F2937;
            }
        """)
        
        # Remove button - 반투명 빨간색 라운드 사각형
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(30, 30)
        self.remove_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.3);
                color: #E5E7EB;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 700;
                text-align: center;
                padding-top: -4px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        self.remove_btn.clicked.connect(self.on_remove_clicked)
        
        # 편집 버튼 이벤트 연결
        self.edit_btn.clicked.connect(lambda: self.on_edit_clicked())
        
        layout.addWidget(self.edit_btn)

        # 초기 렌더 직후 한 번 보정 (부분 줄 잘림 방지)
        try:
            self._recalc_full_layout_heights()
        except Exception:
            pass
        layout.addWidget(self.remove_btn)
    
    def on_remove_clicked(self):
        """태그 삭제 버튼 클릭 시 호출 - 에디터 동기화"""
        print(f"태그 삭제 클릭: {self.tag_text}")
        
        # 에디터가 열려있다면 해당 태그 제거
        if (self.app_instance and 
            hasattr(self.app_instance, 'tag_stylesheet_editor') and 
            self.app_instance.tag_stylesheet_editor):
            
            # 에디터에서 해당 태그 제거
            if self.tag_text in self.app_instance.tag_stylesheet_editor.selected_tags:
                print(f"에디터에서 태그 제거: {self.tag_text}")
                self.app_instance.tag_stylesheet_editor.remove_tag(self.tag_text)
        
        # 기존 삭제 이벤트 발생
        self.removed.emit(self.tag_text)
    
    def on_edit_clicked(self):
        """태그 편집 버튼 클릭 시 호출 - 태그 편집 모듈 사용"""
        print(f"태그 편집 클릭: {self.tag_text}")
        
        if self.app_instance:
            # 태그 스타일시트 에디터 가져오기 (없으면 생성)
            if not hasattr(self.app_instance, 'tag_stylesheet_editor'):
                from tag_stylesheet_editor_module import create_tag_stylesheet_editor
                self.app_instance.tag_stylesheet_editor = create_tag_stylesheet_editor(self.app_instance)
                
                # 리모컨도 함께 생성
                if not hasattr(self.app_instance, 'tag_stylesheet_editor_remote') or not self.app_instance.tag_stylesheet_editor_remote:
                    from tag_stylesheet_editor_remote_module import create_tag_stylesheet_editor_remote
                    self.app_instance.tag_stylesheet_editor_remote = create_tag_stylesheet_editor_remote(self.app_instance)
            
            # 태그를 에디터에 추가
            print(f"태그 스타일시트 에디터에 {self.tag_text} 추가합니다.")
            self.app_instance.tag_stylesheet_editor.create_or_update_tag_edit_card(self.tag_text)
            
            # 리모컨 표시
            if hasattr(self.app_instance, 'tag_stylesheet_editor_remote') and self.app_instance.tag_stylesheet_editor_remote:
                self.app_instance.tag_stylesheet_editor_remote.show_remote()
            
            # 기존 패널들 숨김 처리 제거 - 오버레이 플러그인이 처리
        else:
            print("app_instance가 None입니다!")
    
    def update_count(self, new_count: int):
        """카운트 번호 업데이트 (캐시 재사용을 위해)"""
        self.count = new_count
        self.update_meta_info()
    
    def update_meta_info(self):
        """메타 정보 업데이트 (카테고리, 이미지 수 등)"""
        if not hasattr(self, 'meta_label'):
            return
        
        # 실시간으로 이미지 개수 계산 (global_tag_stats 대신 all_tags에서 직접 계산)
        image_count = 0
        if self.app_instance and hasattr(self.app_instance, 'all_tags'):
            for image_path, tags in self.app_instance.all_tags.items():
                if self.tag_text in tags:
                    image_count += 1
        
        # 카테고리 정보 가져오기 (중앙 집중 로직 사용)
        category = "unknown"
        try:
            if hasattr(self.app_instance, 'tag_statistics_module') and hasattr(self.app_instance.tag_statistics_module, 'resolve_category'):
                category = self.app_instance.tag_statistics_module.resolve_category(self.tag_text)
        except Exception:
            category = "unknown"
        
        # 메타 텍스트 업데이트
        meta_text = f"{self.count}. {category} • {image_count} images" if self.count > 0 else f"{category} • {image_count} images"
        self.meta_label.setText(meta_text)
        print(f"태그 카드 메타 정보 업데이트: {self.tag_text} -> {category} • {image_count} images")
    
    def _recalc_full_layout_heights(self):
        """name_label/메타 라벨이 3줄 이상일 때도 '부분 줄'이 잘리지 않도록 실제 필요한 높이를 강제로 확보"""
        try:
            if not hasattr(self, 'name_label') or not hasattr(self, 'meta_label'):
                return
            # 가용 폭 = 프레임 전체 폭 - 좌우 마진(12*2) - HBox 간격(8) - 버튼 영역(편집 30 + 제거 30 + 버튼 사이 간격 8)
            total_w = self.width()
            button_block = 30 + 30 + 8  # edit, remove, spacing between buttons
            avail = max(0, total_w - (12*2) - 8 - button_block)
            if avail <= 0:
                return
            fm = self.name_label.fontMetrics()
            rect = fm.boundingRect(0, 0, avail, 10**9, Qt.TextWordWrap, self.name_label.text())
            # 라벨 자체가 필요한 정확한 높이를 최소 높이로 보장
            self.name_label.setMinimumHeight(rect.height())
            # 프레임(카드) 최소 높이도 라벨 + 메타 + 내부 상하 여백(8*2) + 라벨간 간격(2) 만큼 확보
            min_card_h = rect.height() + self.meta_label.sizeHint().height() + (8*2) + 2
            if min_card_h > self.minimumHeight():
                self.setMinimumHeight(min_card_h)
        except Exception:
            pass

    def sizeHint(self):
        try:
            # Use the current effective width if available, but do NOT *hint* a width.
            total_w = self.width()
            if total_w <= 0 and self.parentWidget():
                total_w = self.parentWidget().width()
            if total_w <= 0 and hasattr(self, 'name_label'):
                total_w = self.name_label.width() if self.name_label.width() > 0 else super().sizeHint().width()

            # Compute required height for wrapped text using available content width
            button_block = 30 + 30 + 8  # edit, remove, spacing between buttons
            avail = max(1, total_w - (12*2) - 8 - button_block)
            fm = self.name_label.fontMetrics()
            rect = fm.boundingRect(0, 0, avail, 10**9, Qt.TextWordWrap, self.name_label.text())

            # meta height + top/bottom padding (8*2) + spacing between labels (2)
            meta_h = self.meta_label.sizeHint().height()
            needed_h = rect.height() + meta_h + (8*2) + 2

            # IMPORTANT: do not suggest any width here; let the parent layout/viewport decide.
            # Using 0 tells Qt there's no specific width preference.
            return QSize(0, max(needed_h, super().sizeHint().height()))
        except Exception:
            return super().sizeHint()
        except Exception:
            return super().sizeHint()

    def minimumSizeHint(self):
        try:
            sh = self.sizeHint()
            # Do not enforce minimum width; height only.
            return QSize(0, sh.height())
        except Exception:
            return super().minimumSizeHint()
        except Exception:
            return super().minimumSizeHint()
    
    def resizeEvent(self, event):
        # 리사이즈 시마다 다시 계산해서 'N줄+반줄'에서도 잘림 없게.
        try:
            self._recalc_full_layout_heights()
        except Exception:
            pass
        super().resizeEvent(event)


class TagStatisticsModule:
    """태그 통계 모듈"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        # 태그 카드 캐시 - {tag: TagListItem} 형태로 저장
        self.tag_card_cache = {}
        # 마지막으로 표시된 태그 목록 (순서 포함)
        self.last_displayed_tags = []
        # 카테고리 캐시 - {tag: category} 형태로 저장
        self._cached_categories = {}

    def resolve_category(self, tag_text: str) -> str:
        """태그 카테고리 통합 분류: DB -> LLaVA -> manual -> WD -> Danbooru -> unknown
        - 키 정규화(소문자/trim/공백→언더스코어)를 적용하여 manual/llava 인포 조회 안정화
        """
        try:
            # 0) 캐시 (단, 'unknown'이면 계속 진행하여 상위 신뢰도 규칙로 재평가)
            cached = self._cached_categories.get(tag_text)
            if cached and cached != 'unknown':
                return cached

            # 정규화 키 준비 (원본/정규화 모두 조회)
            tag_norm = (tag_text or "").strip().lower().replace(' ', '_')

            # 1) DB 저장 카테고리
            if self.app_instance and hasattr(self.app_instance, 'global_tag_stats'):
                gs = (self.app_instance.global_tag_stats.get(tag_text)
                      or self.app_instance.global_tag_stats.get(tag_norm))
                if isinstance(gs, dict):
                    db_cat = gs.get('category')
                    if db_cat and db_cat != 'unknown':
                        self._cached_categories[tag_text] = db_cat
                        return db_cat

            # 2) LLaVA 여부
            if self.app_instance and hasattr(self.app_instance, 'llava_tag_info'):
                llava_info = self.app_instance.llava_tag_info
                if tag_text in llava_info or tag_norm in llava_info:
                    self._cached_categories[tag_text] = 'caption'
                    return 'caption'

            # 3) 수동(manual)
            if self.app_instance and hasattr(self.app_instance, 'manual_tag_info'):
                manual = self.app_instance.manual_tag_info
                if tag_text in manual or tag_norm in manual:
                    is_trigger = manual.get(tag_text, manual.get(tag_norm, False))
                    cat = 'trigger' if is_trigger else 'used'
                    self._cached_categories[tag_text] = cat
                    return cat

            # 4) WD
            try:
                from wd_tagger import get_tag_category as _wd_get_cat
                wd_cat = _wd_get_cat(tag_text) or _wd_get_cat(tag_norm)
                if wd_cat:
                    self._cached_categories[tag_text] = wd_cat
                    return wd_cat
            except Exception:
                pass

            # 5) Danbooru
            try:
                from danbooru_module import get_danbooru_category_short as _booru_get_cat
                booru_cat = _booru_get_cat(tag_text) or _booru_get_cat(tag_norm)
                if booru_cat:
                    self._cached_categories[tag_text] = booru_cat
                    return booru_cat
            except Exception:
                pass

            # 6) unknown
            self._cached_categories[tag_text] = 'unknown'
            return 'unknown'
        except Exception:
            return 'unknown'
        
    def create_tag_statistics_section(self):
        """태그 통계 섹션 생성"""
        # Global tag statistics and tags list - 하나의 컨테이너로 통합
        tags_card = SectionCard("TAG STYLESHEET")
        self.tags_card = tags_card  # 참조 저장
        
        # 통계 라벨들 제거 (제목에 통합됨)
        
        # 카테고리 필터 버튼들 (2행으로 나누기)
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(4)  # 위아래 간격을 4px로 줄임
        
        # 첫 번째 행
        filter_row1 = QHBoxLayout()
        filter_row1.setSpacing(8)  # 좌우 간격 8px
        
        # 두 번째 행
        filter_row2 = QHBoxLayout()
        filter_row2.setSpacing(8)  # 좌우 간격 8px
        
        # 필터 버튼 스타일 (호버 시에만 라운드 배경, 기본/온오프는 투명)
        filter_button_style = """
            QPushButton {
                background: transparent;
                color: #6B7280;
                border: none;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.055);
                color: #9CA3AF;
            }
            QPushButton:checked {
                background: transparent;
                color: #D1D5DB;
            }
        """
        
        # 카테고리별 필터 버튼들 (다중 선택 가능, 기본적으로 모두 선택)
        self.app_instance.filter_used_btn = QPushButton("Used")
        self.app_instance.filter_used_btn.setCheckable(True)
        self.app_instance.filter_used_btn.setChecked(True)
        self.app_instance.filter_used_btn.setStyleSheet(filter_button_style)
        self.app_instance.filter_used_btn.clicked.connect(self.update_filtered_tags)
        self.app_instance.filter_used_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.app_instance.filter_trigger_btn = QPushButton("Trigger")
        self.app_instance.filter_trigger_btn.setCheckable(True)
        self.app_instance.filter_trigger_btn.setChecked(True)
        self.app_instance.filter_trigger_btn.setStyleSheet(filter_button_style)
        self.app_instance.filter_trigger_btn.clicked.connect(self.update_filtered_tags)
        self.app_instance.filter_trigger_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.app_instance.filter_general_btn = QPushButton("General")
        self.app_instance.filter_general_btn.setCheckable(True)
        self.app_instance.filter_general_btn.setChecked(True)
        self.app_instance.filter_general_btn.setStyleSheet(filter_button_style)
        self.app_instance.filter_general_btn.clicked.connect(self.update_filtered_tags)
        self.app_instance.filter_general_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.app_instance.filter_character_btn = QPushButton("Character")
        self.app_instance.filter_character_btn.setCheckable(True)
        self.app_instance.filter_character_btn.setChecked(True)
        self.app_instance.filter_character_btn.setStyleSheet(filter_button_style)
        self.app_instance.filter_character_btn.clicked.connect(self.update_filtered_tags)
        self.app_instance.filter_character_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.app_instance.filter_rating_btn = QPushButton("Rating")
        self.app_instance.filter_rating_btn.setCheckable(True)
        self.app_instance.filter_rating_btn.setChecked(True)
        self.app_instance.filter_rating_btn.setStyleSheet(filter_button_style)
        self.app_instance.filter_rating_btn.clicked.connect(self.update_filtered_tags)
        self.app_instance.filter_rating_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.app_instance.filter_caption_btn = QPushButton("Caption")
        self.app_instance.filter_caption_btn.setCheckable(True)
        self.app_instance.filter_caption_btn.setChecked(True)
        self.app_instance.filter_caption_btn.setStyleSheet(filter_button_style)
        self.app_instance.filter_caption_btn.clicked.connect(self.update_filtered_tags)
        self.app_instance.filter_caption_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.app_instance.filter_unknown_btn = QPushButton("Unknown")
        self.app_instance.filter_unknown_btn.setCheckable(True)
        self.app_instance.filter_unknown_btn.setChecked(True)
        self.app_instance.filter_unknown_btn.setStyleSheet(filter_button_style)
        self.app_instance.filter_unknown_btn.clicked.connect(self.update_filtered_tags)
        self.app_instance.filter_unknown_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # 첫 번째 행에 버튼들 추가
        filter_row1.addWidget(self.app_instance.filter_used_btn)
        filter_row1.addWidget(self.app_instance.filter_trigger_btn)
        filter_row1.addWidget(self.app_instance.filter_general_btn)
        filter_row1.addWidget(self.app_instance.filter_character_btn)
        
        # 두 번째 행에 버튼들 추가
        filter_row2.addWidget(self.app_instance.filter_rating_btn)
        filter_row2.addWidget(self.app_instance.filter_caption_btn)
        filter_row2.addWidget(self.app_instance.filter_unknown_btn)
        
        # 행들을 메인 필터 레이아웃에 추가
        filter_layout.addLayout(filter_row1)
        filter_layout.addLayout(filter_row2)
        
        tags_card.body.addLayout(filter_layout)
        
        # 통계 라벨들을 필터 버튼 아래에 추가
        # 통계 정보 레이아웃 제거 (제목에 통합됨)
        
        # Global tags list
        self.app_instance.tags_scroll = QScrollArea()
        self.app_instance.tags_scroll.setWidgetResizable(True)
        self.app_instance.tags_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.app_instance.tags_scroll.setMinimumHeight(400)  # 최소 높이 설정
        self.app_instance.tags_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
                border-radius: 8px;
            }
        """)
        
        self.app_instance.tags_container = QWidget()
        self.app_instance.tags_container.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        self.app_instance.global_tags_layout = QVBoxLayout(self.app_instance.tags_container)
        self.app_instance.global_tags_layout.setContentsMargins(0, 8, 0, 0)  # 상단 패딩 8px
        self.app_instance.global_tags_layout.setSpacing(4)
        self.app_instance.global_tags_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 위쪽 정렬
        
        # 초기에는 빈 상태로 시작
        self.app_instance.tags_scroll.setWidget(self.app_instance.tags_container)
        
        tags_card.body.addWidget(self.app_instance.tags_scroll, 1)
        
        # 페이지네이션 초기화
        if not hasattr(self.app_instance, 'tag_current_page'):
            self.app_instance.tag_current_page = 1
        self.app_instance.tag_items_per_page = 50
        
        # 페이지네이션 UI 생성
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 8, 0, 0)
        pagination_layout.setSpacing(4)
        
        # 이전 페이지 버튼
        self.app_instance.tag_prev_page_btn = QPushButton("❮")
        self.app_instance.tag_prev_page_btn.setStyleSheet("""
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
        """)
        self.app_instance.tag_prev_page_btn.clicked.connect(lambda: self.change_tag_page(-1))
        
        # 페이지 번호 라벨
        self.app_instance.tag_page_label = QLabel("0 / 0")
        self.app_instance.tag_page_label.setStyleSheet("""
            QLabel {
                color: #F0F2F5;
                font-size: 12px;
                padding: 0px 8px;
            }
        """)
        self.app_instance.tag_page_label.setAlignment(Qt.AlignCenter)
        
        # 다음 페이지 버튼
        self.app_instance.tag_next_page_btn = QPushButton("❯")
        self.app_instance.tag_next_page_btn.setStyleSheet("""
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
        """)
        self.app_instance.tag_next_page_btn.clicked.connect(lambda: self.change_tag_page(1))
        
        # 페이지네이션 레이아웃 구성
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.app_instance.tag_prev_page_btn)
        pagination_layout.addWidget(self.app_instance.tag_page_label)
        pagination_layout.addWidget(self.app_instance.tag_next_page_btn)
        pagination_layout.addStretch()
        
        tags_card.body.addLayout(pagination_layout)
        
        return tags_card
    
    def update_header_stats(self, image_count: int, tag_count: int):
        """헤더에 이미지 수와 태그 수 표시"""
        if hasattr(self, 'tags_card'):
            header_text = f"TAG STYLESHEET <span style='font-size: 9px; color: #6B7280;'>({image_count} images, {tag_count} tags)</span>"
            self.tags_card.title_lbl.setText(header_text)
    
    def update_global_tags_list(self):
        """전체 태그 통계 리스트 업데이트"""
        # 다중 선택 필터로 업데이트
        self.update_filtered_tags()
    
    def update_filtered_tags(self):
        """다중 선택 필터로 태그 업데이트"""
        # 필터 변경 플래그 설정
        self.app_instance._tag_filter_changing = True
        
        # 선택된 카테고리들 수집
        selected_categories = []
        if hasattr(self.app_instance, 'filter_used_btn') and self.app_instance.filter_used_btn.isChecked():
            selected_categories.append("used")
        if hasattr(self.app_instance, 'filter_trigger_btn') and self.app_instance.filter_trigger_btn.isChecked():
            selected_categories.append("trigger")
        if hasattr(self.app_instance, 'filter_general_btn') and self.app_instance.filter_general_btn.isChecked():
            selected_categories.append("general")
        if hasattr(self.app_instance, 'filter_character_btn') and self.app_instance.filter_character_btn.isChecked():
            selected_categories.append("character")
        if hasattr(self.app_instance, 'filter_rating_btn') and self.app_instance.filter_rating_btn.isChecked():
            selected_categories.append("rating")
        if hasattr(self.app_instance, 'filter_caption_btn') and self.app_instance.filter_caption_btn.isChecked():
            selected_categories.append("caption")
        if hasattr(self.app_instance, 'filter_unknown_btn') and self.app_instance.filter_unknown_btn.isChecked():
            selected_categories.append("unknown")
        
        # 필터링된 태그 리스트 업데이트
        self.update_filtered_tags_list(selected_categories)
    
    def update_filtered_tags_list(self, selected_categories: list):
        """필터링된 태그 리스트 업데이트 (다중 선택 지원, 최적화된 버전, 페이지네이션 적용)"""
        # 태그를 빈도순으로 정렬 (딕셔너리와 정수 형태 모두 지원)
        def get_count(item):
            count = item[1]
            if isinstance(count, dict):
                return count.get('image_count', 0)
            return count
        sorted_tags = sorted(self.app_instance.global_tag_stats.items(), key=get_count, reverse=True)
        
        # 중앙 분류 로직 사용 (wd_tagger 직접 참조 제거)
        
        # 필터링된 태그 목록 생성 (전체)
        all_filtered_tags = []
        filtered_count = 0
        
        for idx, (tag, count) in enumerate(sorted_tags, 1):
            # 중앙 분류 로직으로 단일 결정
            try:
                tag_category = self.resolve_category(tag)
            except Exception:
                tag_category = "unknown"
            
            # 다중 카테고리 필터링
            if tag_category in selected_categories:
                filtered_count += 1
                all_filtered_tags.append((tag, tag_category, filtered_count))
        
        # 필터 변경 시 첫 페이지로 리셋
        if not hasattr(self.app_instance, '_tag_filter_changing'):
            self.app_instance._tag_filter_changing = False
        
        if self.app_instance._tag_filter_changing:
            self.app_instance.tag_current_page = 1
            self.app_instance._tag_filter_changing = False
        
        # 페이지네이션 적용: 현재 페이지의 태그만 표시
        items_per_page = getattr(self.app_instance, 'tag_items_per_page', 50)
        current_page = getattr(self.app_instance, 'tag_current_page', 1)
        total_pages = max(1, (filtered_count + items_per_page - 1) // items_per_page)
        
        # 현재 페이지 범위 계산
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_tags_to_show = all_filtered_tags[start_idx:end_idx]
        
        # 페이지 범위 보정
        if current_page > total_pages:
            self.app_instance.tag_current_page = total_pages
            current_page = total_pages
            start_idx = (current_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            current_tags_to_show = all_filtered_tags[start_idx:end_idx]
        
        # 기존 레이아웃에서 위젯들을 제거하되 삭제하지는 않음 (캐시 보존)
        while self.app_instance.global_tags_layout.count():
            child = self.app_instance.global_tags_layout.takeAt(0)
            # 위젯은 삭제하지 않고 레이아웃에서만 제거
        
        # 현재 페이지의 태그들만 레이아웃에 추가 (캐시된 카드 재사용)
        for tag, tag_category, display_count in current_tags_to_show:
            if tag in self.tag_card_cache:
                # 기존 카드 재사용
                tag_item = self.tag_card_cache[tag]
                # 카운트와 실시간 이미지 수 업데이트
                tag_item.update_count(display_count)
                tag_item.show()  # 다시 표시
            else:
                # 새 카드 생성 및 캐시에 저장
                tag_item = TagListItem(tag, tag_category, None, self.app_instance, count=display_count)
                tag_item.removed.connect(lambda t: self.remove_tag(t))
                self.tag_card_cache[tag] = tag_item
            
            self.app_instance.global_tags_layout.addWidget(tag_item)
        
        # 더 이상 표시되지 않는 태그들의 카드는 숨김 처리
        current_tag_names = [tag for tag, _, _ in current_tags_to_show]
        for cached_tag, cached_item in self.tag_card_cache.items():
            if cached_tag not in current_tag_names:
                cached_item.hide()
        
        # 마지막 표시된 태그 목록 업데이트
        self.last_displayed_tags = current_tag_names
        
        # 페이지네이션 UI 업데이트
        self.update_tag_pagination_ui(filtered_count)
        
        print(f"선택된 카테고리 {selected_categories} 필터링: {filtered_count}개 태그 중 페이지 {current_page}/{total_pages} ({len(current_tags_to_show)}개 표시)")
        
        # 필터링된 기준으로 통계 업데이트
        self.update_filtered_statistics(selected_categories, filtered_count)
    
    def change_tag_page(self, direction: int):
        """태그 페이지 변경"""
        if not hasattr(self.app_instance, 'tag_current_page'):
            self.app_instance.tag_current_page = 1
        
        # 필터링된 태그 목록 재계산
        selected_categories = []
        if hasattr(self.app_instance, 'filter_used_btn') and self.app_instance.filter_used_btn.isChecked():
            selected_categories.append("used")
        if hasattr(self.app_instance, 'filter_trigger_btn') and self.app_instance.filter_trigger_btn.isChecked():
            selected_categories.append("trigger")
        if hasattr(self.app_instance, 'filter_general_btn') and self.app_instance.filter_general_btn.isChecked():
            selected_categories.append("general")
        if hasattr(self.app_instance, 'filter_character_btn') and self.app_instance.filter_character_btn.isChecked():
            selected_categories.append("character")
        if hasattr(self.app_instance, 'filter_rating_btn') and self.app_instance.filter_rating_btn.isChecked():
            selected_categories.append("rating")
        if hasattr(self.app_instance, 'filter_caption_btn') and self.app_instance.filter_caption_btn.isChecked():
            selected_categories.append("caption")
        if hasattr(self.app_instance, 'filter_unknown_btn') and self.app_instance.filter_unknown_btn.isChecked():
            selected_categories.append("unknown")
        
        # 필터링된 태그 수 계산
        def get_count(item):
            count = item[1]
            if isinstance(count, dict):
                return count.get('image_count', 0)
            return count
        sorted_tags = sorted(self.app_instance.global_tag_stats.items(), key=get_count, reverse=True)
        
        filtered_count = 0
        for tag, count in sorted_tags:
            try:
                tag_category = self.resolve_category(tag)
            except Exception:
                tag_category = "unknown"
            if tag_category in selected_categories:
                filtered_count += 1
        
        items_per_page = getattr(self.app_instance, 'tag_items_per_page', 50)
        total_pages = max(1, (filtered_count + items_per_page - 1) // items_per_page)
        
        current_page = getattr(self.app_instance, 'tag_current_page', 1)
        new_page = current_page + direction
        
        if new_page < 1:
            new_page = 1
        elif new_page > total_pages:
            new_page = total_pages
        
        if new_page != current_page:
            self.app_instance.tag_current_page = new_page
            # 필터 변경 플래그 해제 (페이지 변경만)
            self.app_instance._tag_filter_changing = False
            # 태그 리스트 업데이트
            self.update_filtered_tags_list(selected_categories)
    
    def update_tag_pagination_ui(self, total_items: int):
        """태그 페이지네이션 UI 업데이트"""
        if not hasattr(self.app_instance, 'tag_page_label'):
            return
        
        items_per_page = getattr(self.app_instance, 'tag_items_per_page', 50)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        current_page = getattr(self.app_instance, 'tag_current_page', 1)
        
        # 페이지 범위 보정
        if current_page > total_pages:
            self.app_instance.tag_current_page = total_pages
            current_page = total_pages
        
        # UI 업데이트
        if total_items == 0:
            self.app_instance.tag_page_label.setText("0 / 0")
            self.app_instance.tag_prev_page_btn.setEnabled(False)
            self.app_instance.tag_next_page_btn.setEnabled(False)
        else:
            self.app_instance.tag_page_label.setText(f"{current_page} / {total_pages}")
            self.app_instance.tag_prev_page_btn.setEnabled(current_page > 1)
            self.app_instance.tag_next_page_btn.setEnabled(current_page < total_pages)

    def update_filtered_statistics(self, selected_categories: list, filtered_tag_count: int):
        """필터링된 기준으로 통계 업데이트"""
        # 현재 필터링된 태그들로 이미지 수 계산
        filtered_images = set()
        
        # 중앙 분류 로직 사용 (wd_tagger 직접 참조 제거)
        
        # 각 이미지의 태그들을 확인하여 필터링된 카테고리에 해당하는 태그가 있는지 확인
        for image_path in self.app_instance.image_files:
            if str(image_path) in self.app_instance.all_tags:
                image_tags = self.app_instance.all_tags[str(image_path)]
                for tag in image_tags:
                    try:
                        tag_category = self.resolve_category(tag)
                    except Exception:
                        tag_category = "unknown"
                    
                    if tag_category in selected_categories:
                        filtered_images.add(image_path)
                        break
        
        # 헤더 업데이트 (통계 정보를 제목에 표시)
        self.update_header_stats(len(filtered_images), filtered_tag_count)
        
        print(f"필터링된 통계 업데이트: {len(filtered_images)}개 이미지, {filtered_tag_count}개 고유 태그")

    def update_global_tag_statistics(self):
        """전체 태그 통계 업데이트 (이미지 수, 태그 수) - 활성 카테고리 기준으로 필터링"""
        # 단체 태깅 중이면 업데이트 건너뛰기
        if hasattr(self.app_instance, 'is_ai_tagging') and self.app_instance.is_ai_tagging:
            print("단체 태깅 중 - 태그 통계 업데이트 건너뛰기")
            return
        
        # all_tags 기반으로 global_tag_stats 재계산
        self.recalculate_global_tag_stats_from_all_tags()
        
        # 카운터 0인 태그들 제거
        self.remove_zero_count_tags()
            
        # 캐시된 모든 태그 카드의 실시간 이미지 수 업데이트
        self.update_all_cached_cards()
        
        # 현재 선택된 카테고리 기준으로 통계 업데이트
        self.update_filtered_tags()
    
    def recalculate_global_tag_stats_from_all_tags(self):
        """all_tags 기반으로 global_tag_stats 재계산"""
        if not hasattr(self.app_instance, 'all_tags'):
            return
        
        print("📊 all_tags 기반으로 global_tag_stats 재계산 시작")
        
        # 기존 통계를 보존해서 DB에서 복원된 카테고리를 이어받기
        old_stats = {}
        try:
            if hasattr(self.app_instance, 'global_tag_stats') and isinstance(self.app_instance.global_tag_stats, dict):
                old_stats = self.app_instance.global_tag_stats.copy()
        except Exception:
            old_stats = {}

        # global_tag_stats 초기화
        self.app_instance.global_tag_stats = {}
        
        # all_tags를 순회하며 각 태그의 이미지 수 계산
        for image_path, tags in self.app_instance.all_tags.items():
            for tag in tags:
                if tag not in self.app_instance.global_tag_stats:
                    # 중앙 분류 로직 사용: DB 보존값 → LLaVA → manual → WD → Danbooru → unknown
                    try:
                        # 과거 DB 보존값이 있으면 우선 사용 (unknown은 무시)
                        prev = old_stats.get(tag, {}) if isinstance(old_stats, dict) else {}
                        category = prev.get('category') if isinstance(prev, dict) else None
                        if not category or category == 'unknown':
                            category = self.resolve_category(tag)
                    except Exception:
                        category = 'unknown'
                    
                    self.app_instance.global_tag_stats[tag] = {
                        'image_count': 1,
                        'category': category
                    }
                else:
                    self.app_instance.global_tag_stats[tag]['image_count'] += 1
        
        print(f"📊 global_tag_stats 재계산 완료: {len(self.app_instance.global_tag_stats)}개 태그")
    
    def remove_zero_count_tags(self):
        """카운터가 0인 태그들을 제거"""
        if not hasattr(self.app_instance, 'global_tag_stats'):
            return
        
        tags_to_remove = []
        
        # 카운터가 0인 태그들 찾기
        for tag, stats in list(self.app_instance.global_tag_stats.items()):
            if isinstance(stats, dict):
                if stats.get('image_count', 0) <= 0:
                    tags_to_remove.append(tag)
            else:
                if stats <= 0:
                    tags_to_remove.append(tag)
        
        # 카운터가 0인 태그들 제거
        for tag in tags_to_remove:
            del self.app_instance.global_tag_stats[tag]
            print(f"🗑️ 카운터 0인 태그 제거: {tag}")
        
        if tags_to_remove:
            print(f"✅ 카운터 0인 태그 정리 완료: {len(tags_to_remove)}개 태그 제거")
    
    def update_all_cached_cards(self):
        """캐시된 모든 태그 카드의 실시간 이미지 수 업데이트"""
        for tag, cached_item in self.tag_card_cache.items():
            if hasattr(cached_item, 'update_meta_info'):
                # 메타 정보 업데이트 (카테고리, 이미지 수 등)
                cached_item.update_meta_info()
                print(f"캐시된 태그 카드 메타 정보 업데이트: {tag}")
            elif hasattr(cached_item, 'update_count'):
                # 폴백: 기존 방식으로 카운트 업데이트
                current_count = getattr(cached_item, 'count', 0)
                cached_item.update_count(current_count)
                print(f"캐시된 태그 카드 실시간 업데이트: {tag}")
    
    def remove_tag(self, tag):
        """태그 전역 삭제"""
        print(f"전역 태그 삭제 시작: {tag}")
        
        # 타임머신 로깅을 위한 변경 전 상태 저장
        from timemachine_log import TM
        before_all_tags = {k: v.copy() for k, v in self.app_instance.all_tags.items()}
        before_current_tags = self.app_instance.current_tags.copy()
        before_removed_tags = self.app_instance.removed_tags.copy()
        before_global_tag_stats = self.app_instance.global_tag_stats.copy()
        
        # 1. all_tags에서 모든 이미지의 해당 태그 제거
        removed_count = 0
        print(f"all_tags 크기: {len(self.app_instance.all_tags)}")
        for image_path in list(self.app_instance.all_tags.keys()):
            print(f"이미지 {image_path}: {self.app_instance.all_tags[image_path]}")
            if tag in self.app_instance.all_tags[image_path]:
                print(f"태그 {tag} 발견, 제거 중...")
                self.app_instance.all_tags[image_path].remove(tag)
                removed_count += 1
                print(f"제거 후: {self.app_instance.all_tags[image_path]}")
                # 빈 리스트가 되면 해당 이미지 키도 제거
                if not self.app_instance.all_tags[image_path]:
                    print(f"빈 리스트, 이미지 키 제거: {image_path}")
                    del self.app_instance.all_tags[image_path]
        
        # 2. current_tags/removed_tags에서 해당 태그 제거 (current_image와 관계없이)
        # 안전하게 태그 제거 (존재할 때만)
        while tag in self.app_instance.current_tags:
            self.app_instance.current_tags.remove(tag)
            print(f"current_tags에서 태그 제거: {tag}")
        while tag in self.app_instance.removed_tags:
            self.app_instance.removed_tags.remove(tag)
            print(f"removed_tags에서 태그 제거: {tag}")
        
        # 3. global_tag_stats에서 제거
        if tag in self.app_instance.global_tag_stats:
            del self.app_instance.global_tag_stats[tag]
        
        # 4. tag_confidence에서도 제거
        for image_path in list(self.app_instance.tag_confidence.keys()):
            self.app_instance.tag_confidence[image_path] = [
                (t, score) for t, score in self.app_instance.tag_confidence[image_path] 
                if t != tag
            ]
            # 빈 리스트가 되면 해당 이미지 키도 제거
            if not self.app_instance.tag_confidence[image_path]:
                del self.app_instance.tag_confidence[image_path]
        
        # 5. manual_tag_info에서도 제거
        if hasattr(self.app_instance, 'manual_tag_info') and tag in self.app_instance.manual_tag_info:
            del self.app_instance.manual_tag_info[tag]
        
        # 6. 태그 카드 캐시에서 제거
        if tag in self.tag_card_cache:
            cached_item = self.tag_card_cache[tag]
            cached_item.deleteLater()  # 위젯 삭제
            del self.tag_card_cache[tag]
            print(f"태그 카드 캐시에서 제거: {tag}")
        
        # 7. 전체 UI 업데이트 (중앙 패널/트리/통계 UI 동시 갱신)
        from image_tagging_module import update_tag_stats
        update_tag_stats(self.app_instance)
        
        # 7. 태그 스타일시트 에디터 강제 업데이트
        if hasattr(self.app_instance, 'tag_stylesheet_editor') and self.app_instance.tag_stylesheet_editor:
            # 선택된 태그에서 삭제된 태그 제거 (안전하게)
            while tag in self.app_instance.tag_stylesheet_editor.selected_tags:
                self.app_instance.tag_stylesheet_editor.selected_tags.remove(tag)
                print(f"에디터에서 선택된 태그 제거: {tag}")
            
            # 에디터 강제 업데이트
            self.app_instance.tag_stylesheet_editor.schedule_update()
            # 즉시 이미지 그리드도 업데이트
            self.app_instance.tag_stylesheet_editor.update_image_grid()
        
        print(f"전역 태그 삭제 완료: {tag} ({removed_count}개 이미지에서 제거)")
        
        # 타임머신에 전역 태그 삭제 기록
        try:
            print(f"[DEBUG] 타임머신 로그 기록 시도: global_tag_remove - {tag}")
            TM.log_change({
                "type": "global_tag_remove",
                "tag": tag,
                "removed_count": removed_count,
                "before_all_tags": before_all_tags,
                "after_all_tags": {k: v.copy() for k, v in self.app_instance.all_tags.items()},
                "before_current_tags": before_current_tags,
                "after_current_tags": self.app_instance.current_tags.copy(),
                "before_removed_tags": before_removed_tags,
                "after_removed_tags": self.app_instance.removed_tags.copy(),
                "before_global_tag_stats": before_global_tag_stats,
                "after_global_tag_stats": self.app_instance.global_tag_stats.copy()
            })
            print(f"[DEBUG] 타임머신 로그 기록 완료")
        except Exception as e:
            print(f"[ERROR] 타임머신 로그 기록 실패: {e}")
            import traceback
            traceback.print_exc()

# 단독 실행을 위한 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    class TestApp:
        def __init__(self):
            self.tags_scroll = None
            self.tags_container = None
            self.global_tags_layout = None
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Tag Statistics Module Test")
            self.setGeometry(100, 100, 400, 600)
            
            # 중앙 위젯
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 레이아웃
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(10)
            
            # 테스트 앱 인스턴스
            test_app = TestApp()
            
            # 태그 통계 모듈 생성
            tag_stats_module = TagStatisticsModule(test_app)
            tags_card = tag_stats_module.create_tag_statistics_section()
            
            # 테스트 데이터 설정 (제목에 통합됨)
            tag_stats_module.update_header_stats(93, 10)
            
            # 테스트 태그 추가 (원래 디자인 그대로)
            test_tags = [
                "solo (1)", "simple background (1)", "no humans (1)", 
                "pokemon (creature) (1)", "white background (1)", 
                "sketch (1)", "animal focus (1)", "multicolored hair (1)",
                "from side (1)", "1boy (1)"
            ]
            
            for tag in test_tags:
                item = QLabel(tag)
                item.setStyleSheet("""
                    color: #E5E7EB;
                    font-size: 11px;
                    padding: 4px 8px;
                    background: rgba(31,41,55,0.3);
                    border-radius: 4px;
                    margin: 2px;
                """)
                # 태그 라벨이 세로로 늘어나지 않도록 고정
                item.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
                item.setWordWrap(True)
                item.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
                test_app.global_tags_layout.addWidget(item)
            
            layout.addWidget(tags_card)
            
            # 스타일시트 적용
            self.setStyleSheet("""
                QMainWindow {
                    background: #1F2937;
                    color: #E5E7EB;
                }
            """)
    
    # 애플리케이션 실행
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())