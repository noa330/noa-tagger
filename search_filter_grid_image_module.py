# -*- coding: utf-8 -*-
"""
이미지 그리드 전용 모듈
- 이미지 썸네일 생성 및 관리
- 이미지 그리드 UI 로직
- 이미지 자동 정렬 등 이미지 관련 기능
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pathlib import Path
import os
from tokenizer_plugin import count_clip_tokens_for_tags

def clear_image_grid(app_instance):
    """이미지 플로우 레이아웃 초기화"""
    from search_filter_grid_module import clear_media_grid
    clear_media_grid(app_instance, 'image')


def create_image_thumbnails(app_instance):
    """이미지 썸네일들 생성"""
    # 패널 초기화 완료 후 썸네일 생성 (지연 실행)
    QTimer.singleShot(120, lambda: create_thumbnails_with_delay(app_instance))


def create_thumbnails_with_delay(app_instance):
    """지연된 썸네일 생성 (패널 초기화 완료 후) - 페이지네이션 적용"""
    # 기존 썸네일 제거 (중복 방지)
    if hasattr(app_instance, 'image_flow_layout') and app_instance.image_flow_layout:
        try:
            while app_instance.image_flow_layout.count():
                child = app_instance.image_flow_layout.takeAt(0)
                if child and child.widget():
                    child.widget().deleteLater()
        except RuntimeError as e:
            print(f"이미지 레이아웃 정리 중 오류 (무시): {e}")
    
    # 스크롤 영역의 실제 폭 계산
    from search_filter_grid_module import get_available_width, get_columns_and_spacing
    available_width = get_available_width(app_instance)
    print(f"썸네일 생성 - 사용 가능한 폭: {available_width}")
    columns, spacing = get_columns_and_spacing(app_instance, available_width)
    
    if hasattr(app_instance, 'image_list'):
        app_instance.image_list = [str(p) for p in app_instance.image_files]  # 초기 로드 시
    
    # 페이지네이션 초기화
    if not hasattr(app_instance, 'image_current_page'):
        app_instance.image_current_page = 1
    
    # 전체 이미지 목록 저장
    all_images = list(app_instance.image_files)
    app_instance.image_filtered_list = all_images
    
    # 페이지네이션 UI 업데이트
    update_image_pagination_ui(app_instance)
    
    # 첫 페이지의 이미지만 로딩 (50개)
    items_per_page = getattr(app_instance, 'image_items_per_page', 50)
    current_page = app_instance.image_current_page
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_images = all_images[start_idx:end_idx]
    
    print(f"초기 로딩: 페이지 {current_page}, {len(page_images)}개 이미지 (인덱스 {start_idx}~{end_idx-1})")
    
    for image_path in page_images:
        thumb = ImageThumbnail(str(image_path), image_path.name)
        thumb.clicked.connect(lambda path=str(image_path): handle_thumbnail_click(app_instance, path))
        
        # 패널 폭/열수에 맞춰 썸네일 로드 (초기: 매끄럽게)
        thumb.load_thumbnail(available_width, smooth=True, force=True, columns=columns, spacing=spacing)
        
        # 플로우 레이아웃에 추가 (자동 배치)
        if hasattr(app_instance, 'image_flow_layout') and app_instance.image_flow_layout:
            app_instance.image_flow_layout.addWidget(thumb)
        # 토큰 경고 상태 초기화
        try:
            thumb._token_warning = _is_token_over_limit(app_instance, str(image_path))
            thumb.update_selection()
        except Exception:
            pass

    # 첫 번째 이미지 자동 선택 (전체 목록의 첫 번째)
    if app_instance.image_files:
        first_image_path = str(app_instance.image_files[0])
        print(f"첫 번째 이미지 자동 선택: {first_image_path}")
        from image_preview_module import load_image
        load_image(app_instance, first_image_path)
        
        # 첫 번째 이미지 선택 후 선택 상태 강제 업데이트
        _refresh_image_grid_selection_visuals(app_instance)


def update_image_selection(app_instance, selected_path):
    """이미지 선택 상태 업데이트"""
    app_instance.current_image = selected_path
    _refresh_image_grid_selection_visuals(app_instance)


def create_image_grid_section(app_instance, SectionCard):
    """이미지 그리드 섹션 생성"""
    
    # Image list
    list_card = SectionCard("")
    list_card._root.setContentsMargins(4, 4, 0, 10)  # 그리드 영역 패딩 대폭 줄임
    
    # 이미지/비디오 필터 버튼들 추가
    media_filter_layout = QHBoxLayout()
    media_filter_layout.setSpacing(8)
    media_filter_layout.setContentsMargins(0, 0, 0, 8)
    
    # 이미지 필터 버튼
    app_instance.image_filter_btn = QPushButton("이미지")
    app_instance.image_filter_btn.setCheckable(True)
    app_instance.image_filter_btn.setChecked(True)  # 기본 선택
    app_instance.image_filter_btn.setCursor(Qt.PointingHandCursor)
    app_instance.image_filter_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    app_instance.image_filter_btn.setMinimumWidth(100)
    app_instance.image_filter_btn.setStyleSheet("""
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
    """)
    app_instance.image_filter_btn.toggled.connect(lambda checked: on_media_filter_changed(app_instance, "image", checked))
    
    # 비디오 필터 버튼
    app_instance.video_filter_btn = QPushButton("비디오")
    app_instance.video_filter_btn.setCheckable(True)
    app_instance.video_filter_btn.setChecked(False)
    app_instance.video_filter_btn.setCursor(Qt.PointingHandCursor)
    app_instance.video_filter_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    app_instance.video_filter_btn.setMinimumWidth(100)
    app_instance.video_filter_btn.setStyleSheet("""
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
    """)
    app_instance.video_filter_btn.toggled.connect(lambda checked: on_media_filter_changed(app_instance, "video", checked))
    
    media_filter_layout.addWidget(app_instance.image_filter_btn)
    media_filter_layout.addWidget(app_instance.video_filter_btn)
    
    list_card.body.addLayout(media_filter_layout)
    
    from search_filter_grid_module import create_common_scroll_area, create_common_container, create_common_flow_layout
    
    scroll = create_common_scroll_area()
    
    app_instance.image_container = create_common_container()
    # FlowLayout으로 변경 - 이미지들이 자동으로 배치됨
    app_instance.image_flow_layout = create_common_flow_layout(app_instance.image_container)
    
    # 컨테이너에 레이아웃 설정
    app_instance.image_container.setLayout(app_instance.image_flow_layout)
    
    scroll.setWidget(app_instance.image_container)
    
    # 페이지네이션 초기화
    if not hasattr(app_instance, 'image_current_page'):
        app_instance.image_current_page = 1
    app_instance.image_items_per_page = 50
    
    # 페이지네이션 UI 생성
    pagination_layout = QHBoxLayout()
    pagination_layout.setContentsMargins(0, 8, 0, 0)
    pagination_layout.setSpacing(4)
    
    # 이전 페이지 버튼
    app_instance.image_prev_page_btn = QPushButton("❮")
    app_instance.image_prev_page_btn.setStyleSheet("""
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
    app_instance.image_prev_page_btn.clicked.connect(lambda: change_image_page(app_instance, -1))
    
    # 페이지 정보 라벨
    app_instance.image_page_label = QLabel("0 / 0")
    app_instance.image_page_label.setStyleSheet("""
        color: #9CA3AF;
        font-size: 11px;
        padding: 4px 8px;
    """)
    app_instance.image_page_label.setAlignment(Qt.AlignCenter)
    app_instance.image_page_label.setMinimumWidth(60)
    
    # 다음 페이지 버튼
    app_instance.image_next_page_btn = QPushButton("❯")
    app_instance.image_next_page_btn.setStyleSheet("""
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
    app_instance.image_next_page_btn.clicked.connect(lambda: change_image_page(app_instance, 1))
    
    # Add 버튼 (이미지 추가용) - 파란색 배경 버튼
    app_instance.add_image_button = QPushButton("Add")
    app_instance.add_image_button.setCursor(Qt.PointingHandCursor)
    app_instance.add_image_button.setStyleSheet("""
        QPushButton {
            background: #3B82F6;
            color: #FFFFFF;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #60A5FA;
        }
        QPushButton:pressed {
            background: #1D4ED8;
        }
    """)
    app_instance.add_image_button.clicked.connect(lambda: add_images_to_current(app_instance))
    
    # 페이지네이션을 중앙 정렬하고 Add 버튼 추가
    pagination_layout.addStretch()
    pagination_layout.addWidget(app_instance.image_prev_page_btn)
    pagination_layout.addWidget(app_instance.image_page_label)
    pagination_layout.addWidget(app_instance.image_next_page_btn)
    pagination_layout.addSpacing(6)  # Add 버튼과 오른쪽 화살표 사이 여백 10px (기존 4px spacing + 6px)
    pagination_layout.addWidget(app_instance.add_image_button)
    pagination_layout.addStretch()
    
    # 페이지네이션 레이아웃 저장 (비디오 페이지네이션 추가 시 사용)
    app_instance.pagination_layout = pagination_layout
    
    # 초기 상태: 항목이 없으므로 버튼 비활성화
    app_instance.image_prev_page_btn.setEnabled(False)
    app_instance.image_next_page_btn.setEnabled(False)
    
    # 스크롤, 페이지네이션을 세로로 배치
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    main_layout.addWidget(scroll)
    main_layout.addLayout(pagination_layout)
    
    list_card.body.addLayout(main_layout)

    # 스크롤/뷰포트 레퍼런스 저장 (폭 계산에 사용)
    app_instance.image_scroll = scroll

    # 다중 선택 상태 초기화
    if not hasattr(app_instance, 'image_multi_selected'):
        app_instance.image_multi_selected = set()

    # === 패널(뷰포트) 리사이즈 감지: 미리보기(빠른) + 최종(부드러운) 재스케일 ===
    # [추가] 상태 플래그
    app_instance._last_image_viewport_width = -1
    app_instance._image_rescale_busy = False

    def _safe_on_image_panel_resized(preview=True):
        # 재진입 방지
        if getattr(app_instance, "_image_rescale_busy", False):
            return
        # 폭이 실제 변한 경우에만 동작 (preview 패스에서만 적용)
        from search_filter_grid_module import get_available_width
        vw = get_available_width(app_instance)
        if preview and vw == getattr(app_instance, "_last_image_viewport_width", -1):
            return

        app_instance._last_image_viewport_width = vw
        app_instance._image_rescale_busy = True
        try:
            from search_filter_grid_module import on_panel_resized
            on_panel_resized(app_instance, preview=preview)
        finally:
            app_instance._image_rescale_busy = False

    app_instance._image_resize_watcher = ResizeWatcher(_safe_on_image_panel_resized)
    
    # 즉시 설치 대신 한 틱 뒤에 설치 (초기 레이아웃 완료 후)
    QTimer.singleShot(0, lambda: scroll.viewport().installEventFilter(app_instance._image_resize_watcher))
    # ===========================================================
    
    # Counter container (이미지/비디오 공용)
    counter_container = QWidget()
    counter_layout = QVBoxLayout(counter_container)
    counter_layout.setContentsMargins(0, 0, 0, 0)
    counter_layout.setSpacing(0)
    
    # 이미지 카운터 라벨
    app_instance.image_counter = QLabel("No images loaded")
    app_instance.image_counter.setStyleSheet("""
        color: #6B7280;
        font-size: 11px;
        padding: 8px;
    """)
    app_instance.image_counter.setAlignment(Qt.AlignCenter)
    counter_layout.addWidget(app_instance.image_counter)
    
    # 비디오 카운터 라벨 (초기에는 숨김)
    if not hasattr(app_instance, 'video_counter') or not app_instance.video_counter:
        app_instance.video_counter = QLabel("No videos loaded")
        app_instance.video_counter.setStyleSheet("""
            color: #6B7280;
            font-size: 11px;
            padding: 8px;
        """)
        app_instance.video_counter.setAlignment(Qt.AlignCenter)
    app_instance.video_counter.setParent(counter_container)
    app_instance.video_counter.setVisible(False)
    counter_layout.addWidget(app_instance.video_counter)
    
    _register_timemachine_auto_refresh(app_instance)
    
    return list_card, counter_container


def on_media_filter_changed(app_instance, media_type, checked):
    """미디어 필터 버튼 변경 처리"""
    print(f"미디어 필터 변경: {media_type} = {checked}")
    
    # 상호 배타적 선택 (하나만 선택 가능)
    if checked:
        if media_type == "image":
            if hasattr(app_instance, 'video_filter_btn') and app_instance.video_filter_btn:
                app_instance.video_filter_btn.setChecked(False)
            # 이미지 그리드로 전환
            switch_to_image_grid(app_instance)
            # 비디오 프레임 숨김
            try:
                from video_preview_module import on_video_mode_deactivated
                on_video_mode_deactivated(app_instance)
            except ImportError:
                pass
        elif media_type == "video":
            if hasattr(app_instance, 'image_filter_btn') and app_instance.image_filter_btn:
                app_instance.image_filter_btn.setChecked(False)
            # 비디오 그리드로 전환 (비디오 모듈에서 처리)
            from search_filter_grid_video_module import switch_to_video_grid
            switch_to_video_grid(app_instance)
            # 비디오 프레임 표시
            try:
                from video_preview_module import on_video_mode_activated
                on_video_mode_activated(app_instance)
            except ImportError:
                pass
        
        # 검색 UI 업데이트 (모드에 따라 placeholder, 드롭다운 옵션 변경)
        try:
            from search_module import update_search_ui_for_mode
            update_search_ui_for_mode(app_instance)
        except ImportError:
            pass
        
        # 필터 드롭다운 업데이트 (모드에 따라 옵션 변경)
        try:
            from search_filter_grid_module import update_filter_dropdown_for_mode
            update_filter_dropdown_for_mode(app_instance)
        except ImportError:
            pass
    
    # 즉시 UI 업데이트 (안전성 검사 추가)
    try:
        refresh_image_thumbnails_immediate(app_instance)
    except RuntimeError as e:
        print(f"미디어 필터 업데이트 중 오류 (무시): {e}")
        # 위젯이 이미 삭제된 경우 무시


def switch_to_image_grid(app_instance):
    """이미지 그리드로 전환"""
    print("이미지 그리드로 전환")
    
    # 모드 전환 시 페이지를 1로 초기화
    if hasattr(app_instance, 'image_current_page'):
        app_instance.image_current_page = 1
        print("이미지 페이지를 1로 초기화")
    
    # 현재 스크롤 위치 저장 (비디오에서 이미지로 전환 시)
    if hasattr(app_instance, 'video_scroll') and app_instance.video_scroll:
        saved_scroll_position = app_instance.video_scroll.verticalScrollBar().value()
        print(f"비디오 스크롤 위치 저장: {saved_scroll_position}")
    else:
        saved_scroll_position = 0
    
    # 🔧 중요: 이미지 컨테이너를 스크롤 영역에 다시 연결
    if hasattr(app_instance, 'image_scroll') and app_instance.image_scroll:
        if hasattr(app_instance, 'image_container') and app_instance.image_container:
            # 현재 위젯(비디오 컨테이너)을 제거하고 이미지 컨테이너를 다시 설정
            app_instance.image_scroll.takeWidget()
            app_instance.image_scroll.setWidget(app_instance.image_container)
            print("이미지 컨테이너를 스크롤 영역에 다시 연결")
    
    # 이미지 컨테이너 보이기, 비디오 컨테이너 숨기기
    if hasattr(app_instance, 'image_container') and app_instance.image_container:
        app_instance.image_container.setVisible(True)
        print("이미지 컨테이너 표시")
    
    if hasattr(app_instance, 'video_container') and app_instance.video_container:
        app_instance.video_container.setVisible(False)
        print("비디오 컨테이너 숨김")
    
    # 이미지 페이지네이션 UI 보이기, 비디오 페이지네이션 UI 숨기기
    if hasattr(app_instance, 'image_prev_page_btn'):
        app_instance.image_prev_page_btn.setVisible(True)
    if hasattr(app_instance, 'image_page_label'):
        app_instance.image_page_label.setVisible(True)
    if hasattr(app_instance, 'image_next_page_btn'):
        app_instance.image_next_page_btn.setVisible(True)
    if hasattr(app_instance, 'add_image_button'):
        app_instance.add_image_button.setVisible(True)
    
    if hasattr(app_instance, 'video_prev_page_btn'):
        app_instance.video_prev_page_btn.setVisible(False)
    if hasattr(app_instance, 'video_page_label'):
        app_instance.video_page_label.setVisible(False)
    if hasattr(app_instance, 'video_next_page_btn'):
        app_instance.video_next_page_btn.setVisible(False)
    if hasattr(app_instance, 'add_video_button'):
        app_instance.add_video_button.setVisible(False)
    
    # 카운터 표시 전환
    if hasattr(app_instance, 'image_counter') and app_instance.image_counter:
        app_instance.image_counter.setVisible(True)
    if hasattr(app_instance, 'video_counter') and app_instance.video_counter:
        app_instance.video_counter.setVisible(False)
    
    print("이미지 페이지네이션 UI 표시, 비디오 페이지네이션 UI 숨김")
    
    # 이미지 썸네일 새로고침 (이미지 레이아웃이 존재할 때만)
    if hasattr(app_instance, 'image_flow_layout') and app_instance.image_flow_layout:
        # 모드 전환 플래그 설정 (페이지 리셋 방지용)
        app_instance._is_mode_switching = True
        refresh_image_thumbnails_immediate(app_instance)
        app_instance._is_mode_switching = False
        
        # 스크롤 위치 복원 (이미지 그리드로 전환 시)
        if hasattr(app_instance, 'image_scroll') and app_instance.image_scroll:
            QTimer.singleShot(100, lambda: app_instance.image_scroll.verticalScrollBar().setValue(saved_scroll_position))
            print(f"이미지 스크롤 위치 복원: {saved_scroll_position}")
        
        # 이미지 선택 표시 업데이트
        from search_filter_grid_image_module import _refresh_image_grid_selection_visuals
        QTimer.singleShot(200, lambda: _refresh_image_grid_selection_visuals(app_instance))
    else:
        print("이미지 레이아웃이 없음 - 썸네일 새로고침 건너뜀")


def change_image_page(app_instance, direction):
    """이미지 페이지 변경 (direction: -1 이전, 1 다음)"""
    if not hasattr(app_instance, 'image_filtered_list'):
        return
    
    total_items = len(app_instance.image_filtered_list)
    if total_items == 0:
        return
    
    items_per_page = getattr(app_instance, 'image_items_per_page', 50)
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
    
    # 현재 페이지 업데이트
    current_page = getattr(app_instance, 'image_current_page', 1)
    new_page = current_page + direction
    
    # 페이지 범위 제한
    if new_page < 1 or new_page > total_pages:
        return
    
    app_instance.image_current_page = new_page
    
    # 페이지 변경 중임을 표시 (필터 리셋 방지)
    app_instance._is_page_changing = True
    
    # 스크롤 위치 초기화
    if hasattr(app_instance, 'image_scroll') and app_instance.image_scroll:
        app_instance.image_scroll.verticalScrollBar().setValue(0)
    
    # 썸네일 재생성
    refresh_image_thumbnails_immediate(app_instance)
    
    # 페이지 변경 완료
    app_instance._is_page_changing = False
    
    print(f"이미지 페이지 변경: {new_page} / {total_pages}")


def update_image_pagination_ui(app_instance):
    """이미지 페이지네이션 UI 업데이트"""
    if not hasattr(app_instance, 'image_page_label'):
        return
    
    total_items = len(getattr(app_instance, 'image_filtered_list', []))
    if total_items == 0:
        app_instance.image_page_label.setText("0 / 0")
        app_instance.image_prev_page_btn.setEnabled(False)
        app_instance.image_next_page_btn.setEnabled(False)
        return
    
    items_per_page = getattr(app_instance, 'image_items_per_page', 50)
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
    current_page = getattr(app_instance, 'image_current_page', 1)
    
    # 페이지 범위 조정 (필터 변경 시 현재 페이지가 범위를 벗어날 수 있음)
    if current_page > total_pages:
        app_instance.image_current_page = total_pages
        current_page = total_pages
    
    app_instance.image_page_label.setText(f"{current_page} / {total_pages}")
    app_instance.image_prev_page_btn.setEnabled(current_page > 1)
    app_instance.image_next_page_btn.setEnabled(current_page < total_pages)


def refresh_image_thumbnails_immediate(app_instance):
    """즉시 필터 반영 (딜레이 없음)"""
    filter_text = app_instance.filter_dropdown.currentText()
    print(f"즉시 필터 반영: {filter_text}")
    
    # 필터 변경 시 첫 페이지로 초기화 (단, 페이지 변경 중이거나 모드 전환 중이 아닐 때만)
    is_page_changing = getattr(app_instance, '_is_page_changing', False)
    is_mode_switching = getattr(app_instance, '_is_mode_switching', False)
    
    if not is_page_changing and not is_mode_switching:
        if not hasattr(app_instance, '_filter_initialization_done'):
            app_instance._filter_initialization_done = True
        else:
            # 초기화가 아닌 경우에만 페이지 리셋
            if hasattr(app_instance, 'image_current_page'):
                app_instance.image_current_page = 1
    
    # 미디어 필터 상태 확인
    if hasattr(app_instance, 'image_filter_btn') and hasattr(app_instance, 'video_filter_btn'):
        image_checked = app_instance.image_filter_btn.isChecked()
        video_checked = app_instance.video_filter_btn.isChecked()
        
        if video_checked and not image_checked:
            # 비디오 모드: 비디오 그리드 업데이트 (비디오 모듈에서 처리)
            print("비디오 모드 - 비디오 그리드 업데이트")
            from search_filter_grid_video_module import refresh_video_thumbnails
            if hasattr(app_instance, 'video_files') and app_instance.video_files:
                refresh_video_thumbnails(app_instance)
            return
        elif image_checked and not video_checked:
            # 이미지 모드: 이미지 그리드 업데이트
            print("이미지 모드 - 이미지 그리드 업데이트")
        else:
            # 기본값: 이미지 모드
            print("기본값 - 이미지 모드로 설정")
            app_instance.image_filter_btn.setChecked(True)
            app_instance.video_filter_btn.setChecked(False)
    
    # 기존 썸네일 즉시 제거 (안전성 검사 추가) - 레이아웃은 삭제하지 않음
    if hasattr(app_instance, 'image_flow_layout') and app_instance.image_flow_layout:
        try:
            # 썸네일 위젯들만 제거 (레이아웃은 유지)
            while app_instance.image_flow_layout.count():
                child = app_instance.image_flow_layout.takeAt(0)
                if child and child.widget():
                    child.widget().deleteLater()
        except RuntimeError as e:
            print(f"이미지 레이아웃 정리 중 오류 (무시): {e}")
            # 레이아웃이 이미 삭제된 경우 무시
    
    # 이미지만 표시 (비디오는 절대 안들어가게)
    show_images = True
    show_videos = False
    
    # search_module의 통합 필터 로직 호출 (중복 방지)
    from search_module import update_image_grid_unified
    app_instance.active_grid_token += 1
    update_image_grid_unified(app_instance, expected_token=app_instance.active_grid_token)
    return
    
    print(f"즉시 필터링 완료: {len(filtered_images)}개 미디어")
    
    # 필터링된 전체 목록 저장 (페이지네이션에서 사용)
    app_instance.image_filtered_list = filtered_images
    app_instance.image_list = [str(p) for p in filtered_images]  # 드롭다운 바뀔 때 즉시 반영
    
    # 페이지네이션 UI 업데이트
    update_image_pagination_ui(app_instance)
    
    # 카운터 업데이트
    try:
        from search_module import update_image_counter
        # 전체 이미지 수는 원본 목록에서 가져오기 (로드된 이미지 수)
        total_images = len(getattr(app_instance, 'original_image_files', getattr(app_instance, 'image_files', [])))
        # 필터링된 이미지 수는 Search 숫자에 사용
        update_image_counter(app_instance, len(filtered_images), total_images)
    except Exception as e:
        print(f"이미지 카운터 업데이트 실패: {e}")
    
    # 스타일시트 에디터가 검색 결과 연동이 켜져있을 때 업데이트
    if hasattr(app_instance, 'tag_stylesheet_editor') and app_instance.tag_stylesheet_editor:
        if hasattr(app_instance.tag_stylesheet_editor, 'grid_filter_enabled') and app_instance.tag_stylesheet_editor.grid_filter_enabled:
            print("이미지 그리드 즉시 갱신 - 스타일시트 에디터 검색 결과 연동 업데이트")
            app_instance.tag_stylesheet_editor.update_image_grid()
    
    # 현재 페이지의 이미지만 필터링
    items_per_page = getattr(app_instance, 'image_items_per_page', 50)
    current_page = getattr(app_instance, 'image_current_page', 1)
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_images = filtered_images[start_idx:end_idx]
    
    print(f"페이지 {current_page}: {len(page_images)}개 이미지 로딩 (인덱스 {start_idx}~{end_idx-1})")
    
    # 썸네일을 백그라운드에서 생성 (현재 페이지만)
    create_thumbnails_async(app_instance, page_images)


def create_thumbnails_async(app_instance, filtered_images, update_token=None):
    """이미지 썸네일을 비동기로 생성"""
    app_instance.image_list = [str(p) for p in filtered_images]  # 검색 모듈이 이 경로로 들어올 때도 커버
    
    # ✅ 이전 작업 타이머가 있으면 정지 (섞임 방지)
    try:
        if hasattr(app_instance, 'thumbnail_creation_timer') and app_instance.thumbnail_creation_timer:
            app_instance.thumbnail_creation_timer.stop()
    except Exception:
        pass

    # ✅ 토큰: 호출 시 전달되면 사용, 아니면 내부 토큰 증가
    if update_token is None:
        current = getattr(app_instance, '_thumb_job_token', 0) + 1
        setattr(app_instance, '_thumb_job_token', current)
        token = current
    else:
        token = int(update_token)

    # 활성 토큰 기록 (오래된 배치 차단용)
    app_instance._thumb_active_token = token

    # 배치 시작 인덱스 초기화
    app_instance.thumbnail_batch_start = 0

    # QTimer를 사용하여 백그라운드에서 썸네일 생성
    app_instance.thumbnail_creation_timer = QTimer()
    app_instance.thumbnail_creation_timer.setSingleShot(True)
    # ✅ 토큰을 함께 전달
    app_instance.thumbnail_creation_timer.timeout.connect(lambda: create_thumbnail_batch(app_instance, filtered_images, token))
    app_instance.thumbnail_creation_timer.start(0)  # 즉시 시작


def create_thumbnail_batch(app_instance, filtered_images, job_token=None):
    """배치 썸네일 생성 (UI 블로킹 방지)"""
    # ✅ 오래된 작업이면 즉시 중단
    if job_token is not None and job_token != getattr(app_instance, '_thumb_active_token', None):
        print(f"⏭️ 오래된 배치 무시: {job_token} != {getattr(app_instance, '_thumb_active_token', None)}")
        return
    
    # 레이아웃이 존재하는지 확인
    if not hasattr(app_instance, 'image_flow_layout') or not app_instance.image_flow_layout:
        print("이미지 레이아웃이 없음 - 썸네일 생성 중단")
        return

    # 스크롤 영역의 실제 폭 계산
    from search_filter_grid_module import get_available_width, get_columns_and_spacing
    available_width = get_available_width(app_instance)
    print(f"배치 썸네일 생성 - 사용 가능한 폭: {available_width}")
    columns, spacing = get_columns_and_spacing(app_instance, available_width)
    
    # 한 번에 처리할 썸네일 수 (UI 반응성 유지)
    batch_size = 10
    start_idx = getattr(app_instance, 'thumbnail_batch_start', 0)
    end_idx = min(start_idx + batch_size, len(filtered_images))
    
    # 현재 배치의 썸네일 생성
    for i in range(start_idx, end_idx):
        # ✅ 진행 중 토큰 재확인 (중간에 무효화될 수 있음)
        if job_token is not None and job_token != getattr(app_instance, '_thumb_active_token', None):
            print(f"⏭️ 배치 중단(토큰 변경): {job_token} != {getattr(app_instance, '_thumb_active_token', None)}")
            return

        image_path = filtered_images[i]
        thumb = ImageThumbnail(str(image_path), image_path.name)
        thumb.clicked.connect(lambda path=str(image_path): handle_thumbnail_click(app_instance, path))
        
        # 패널 폭/열수에 맞춰 썸네일 로드 (배치: 매끄럽게)
        thumb.load_thumbnail(available_width, smooth=True, force=True, columns=columns, spacing=spacing)
        
        # 플로우 레이아웃에 추가 (자동 배치) - 안전성 검사 추가
        if hasattr(app_instance, 'image_flow_layout') and app_instance.image_flow_layout:
            try:
                app_instance.image_flow_layout.addWidget(thumb)
            except RuntimeError as e:
                print(f"썸네일 추가 중 오류 (무시): {e}")
                # 레이아웃이 이미 삭제된 경우 썸네일도 삭제
                thumb.deleteLater()
                return
        
        # 선택 상태 복원 (썸네일 재생성 시 선택 상태 유지)
        image_key = str(image_path)
        current_image = getattr(app_instance, 'current_image', None)
        multi_selected = getattr(app_instance, 'image_multi_selected', set())
        thumb.is_current = (image_key == current_image)
        thumb.is_multi = (image_key in multi_selected) and (image_key != current_image)
        
        # 토큰 경고 상태 초기화
        try:
            thumb._token_warning = _is_token_over_limit(app_instance, image_key)
            thumb.update_selection()
        except Exception:
            pass
    
    # 다음 배치가 있으면 계속 처리
    if end_idx < len(filtered_images):
        app_instance.thumbnail_batch_start = end_idx
        # ✅ 다음 배치에도 동일 토큰 전달
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1, lambda: create_thumbnail_batch(app_instance, filtered_images, job_token))
    else:
        # 모든 썸네일 생성 완료
        app_instance.thumbnail_batch_start = 0
        print("이미지 썸네일 새로고침 완료")
        
        # 썸네일 생성 완료 후 현재 선택 상태 강제 업데이트
        _refresh_image_grid_selection_visuals(app_instance)


def _is_token_over_limit(app_instance, image_key: str) -> bool:
    try:
        # 이미지별 활성 태그 리스트 가져오기
        from all_tags_manager import get_tags_for_image
        tags = get_tags_for_image(app_instance, image_key) or []
        # 토큰 수 계산
        tokens = count_clip_tokens_for_tags(tags)
        if tokens is None:
            return False
        # 한도 값: ModernTagInput의 스핀박스가 있으면 우선 사용, 없으면 77
        limit = 77
        try:
            if hasattr(app_instance, 'tag_input_widget') and hasattr(app_instance.tag_input_widget, 'token_limit_spin'):
                limit = int(app_instance.tag_input_widget.token_limit_spin.value())
        except Exception:
            limit = 77
        return tokens > limit
    except Exception as e:
        print(f"토큰 한도 체크 오류: {e}")
        return False


# get_image_available_width 함수는 메인 모듈의 get_available_width로 통합됨


# on_image_panel_resized 함수는 메인 모듈의 on_panel_resized로 통합됨


def add_images_to_current(app_instance):
    """현재 이미지 목록에 추가 이미지 로드"""
    from search_filter_grid_module import add_media_files_to_current
    add_media_files_to_current(app_instance, 'image', 
                              "미디어 파일 (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v)", 
                              "추가할 파일 선택")


def handle_thumbnail_click(app_instance, image_path):
    """썸네일 클릭 처리: Shift+Ctrl 동시 시 다중선택 토글, 아니면 단일 선택"""
    from search_filter_grid_module import handle_common_thumbnail_click
    handle_common_thumbnail_click(app_instance, image_path, 'image')


def _choose_replacement_current_from_multi(app_instance, reference_path):
    """현재 선택 해제 시 다중선택 내에서 아래 우선, 없으면 위에서 선택"""
    from search_filter_grid_module import choose_replacement_current_from_multi
    return choose_replacement_current_from_multi(app_instance, reference_path, 'image')


def _refresh_image_grid_selection_visuals(app_instance):
    """이미지 그리드의 현재/다중 선택 테두리 일괄 갱신"""
    from search_filter_grid_module import refresh_grid_selection_visuals
    refresh_grid_selection_visuals(app_instance, 'image')


def _register_timemachine_auto_refresh(app_instance):
    """타임머신 로그 발생 시 검색/필터를 자동 재적용하도록 구독"""
    if getattr(app_instance, '_tm_auto_refresh_registered', False):
        return
    try:
        from timemachine_log import TM
    except Exception:
        return

    def _handle_tm_log(_record):
        def _refresh():
            try:
                search_text = ""
                if hasattr(app_instance, 'filter_input') and app_instance.filter_input:
                    try:
                        search_text = app_instance.filter_input.text()
                    except Exception:
                        search_text = ""
                try:
                    from search_module import on_search_text_changed
                    on_search_text_changed(app_instance, search_text or "")
                except Exception:
                    pass

                try:
                    if hasattr(app_instance, 'advanced_search_results') and app_instance.advanced_search_results is not None:
                        widget = _get_advanced_search_widget(app_instance)
                        if widget and hasattr(widget, 'execute_search'):
                            widget.execute_search()
                except Exception:
                    pass

                try:
                    if hasattr(app_instance, 'active_grid_token'):
                        app_instance.active_grid_token += 1
                    else:
                        app_instance.active_grid_token = 1
                    from search_module import update_image_grid_unified
                    update_image_grid_unified(app_instance, expected_token=getattr(app_instance, 'active_grid_token', None))
                except Exception:
                    pass
            except Exception:
                pass

        try:
            QTimer.singleShot(0, _refresh)
        except Exception:
            _refresh()

    try:
        TM.subscribe(_handle_tm_log)
        app_instance._tm_auto_refresh_registered = True
        app_instance._tm_auto_refresh_handler = _handle_tm_log
    except Exception:
        pass


def _get_advanced_search_widget(app_instance):
    """app_instance에서 AdvancedSearchWidget 인스턴스를 안전하게 가져오기"""
    try:
        card = getattr(app_instance, 'advanced_search_card', None)
        if not card or not hasattr(card, 'body'):
            return None
        layout = card.body
        for idx in range(layout.count()):
            item = layout.itemAt(idx)
            if item and item.widget():
                return item.widget()
    except Exception:
        pass
    return None


# get_columns_and_spacing 함수는 메인 모듈로 통합됨


# 필요한 클래스들 import
try:
    from search_filter_grid_module import ImageThumbnail, QFlowLayout, ResizeWatcher
except ImportError:
    # 기본 클래스들 정의 (필요시)
    pass
