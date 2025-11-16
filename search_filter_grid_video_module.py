# -*- coding: utf-8 -*-
"""
비디오 그리드 전용 모듈
- 비디오 썸네일 생성 및 관리
- 비디오 그리드 UI 로직
- 비디오 자동 정렬 등 비디오 관련 기능
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pathlib import Path
import os

def create_video_grid_section(app_instance, SectionCard):
    """비디오 전용 그리드 섹션 생성"""
    
    # Video list
    list_card = SectionCard("")
    list_card._root.setContentsMargins(4, 4, 0, 10)  # 그리드 영역 패딩 대폭 줄임
    
    scroll = QScrollArea()
    # viewport 리사이즈를 컨텐츠에 반영되게
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    # 스크롤바 무한 반복 방지: 적절한 여백 추가
    scroll.setViewportMargins(0, 0, 3, 0)
    scroll.setStyleSheet("""
        QScrollArea {
            background: transparent;
            border: none;
            border-radius: 8px;
        }
    """)
    
    app_instance.video_container = QWidget()
    # 스크롤바 무한 반복 방지: SizePolicy 설정
    app_instance.video_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    app_instance.video_container.setStyleSheet("""
        QWidget {
            background: transparent;
        }
    """)
    # FlowLayout으로 변경 - 비디오들이 자동으로 배치됨
    app_instance.video_flow_layout = QFlowLayout(app_instance.video_container)
    app_instance.video_flow_layout.setSpacing(4)  # 비디오 간격
    app_instance.video_flow_layout.setContentsMargins(0, 0, 0, 0)  # 좌우 마진 0으로 설정
    
    # 컨테이너에 레이아웃 설정
    app_instance.video_container.setLayout(app_instance.video_flow_layout)
    
    scroll.setWidget(app_instance.video_container)
    
    # 페이지네이션 초기화
    if not hasattr(app_instance, 'video_current_page'):
        app_instance.video_current_page = 1
    app_instance.video_items_per_page = 50
    
    # 페이지네이션 UI 생성
    pagination_layout = QHBoxLayout()
    pagination_layout.setContentsMargins(0, 8, 0, 0)
    pagination_layout.setSpacing(4)
    
    # 이전 페이지 버튼
    app_instance.video_prev_page_btn = QPushButton("❮")
    app_instance.video_prev_page_btn.setStyleSheet("""
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
    app_instance.video_prev_page_btn.clicked.connect(lambda: change_video_page(app_instance, -1))
    
    # 페이지 정보 라벨
    app_instance.video_page_label = QLabel("0 / 0")
    app_instance.video_page_label.setStyleSheet("""
        color: #9CA3AF;
        font-size: 11px;
        padding: 4px 8px;
    """)
    app_instance.video_page_label.setAlignment(Qt.AlignCenter)
    app_instance.video_page_label.setMinimumWidth(60)
    
    # 다음 페이지 버튼
    app_instance.video_next_page_btn = QPushButton("❯")
    app_instance.video_next_page_btn.setStyleSheet("""
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
    app_instance.video_next_page_btn.clicked.connect(lambda: change_video_page(app_instance, 1))
    
    # Add 버튼 (비디오 추가용) - 파란색 배경 버튼
    app_instance.add_video_button = QPushButton("Add")
    app_instance.add_video_button.setCursor(Qt.PointingHandCursor)
    app_instance.add_video_button.setStyleSheet("""
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
    app_instance.add_video_button.clicked.connect(lambda: add_videos_to_current(app_instance))
    
    # 페이지네이션을 중앙 정렬하고 Add 버튼 추가
    pagination_layout.addStretch()
    pagination_layout.addWidget(app_instance.video_prev_page_btn)
    pagination_layout.addWidget(app_instance.video_page_label)
    pagination_layout.addWidget(app_instance.video_next_page_btn)
    pagination_layout.addSpacing(6)  # Add 버튼과 오른쪽 화살표 사이 여백 10px (기존 4px spacing + 6px)
    pagination_layout.addWidget(app_instance.add_video_button)
    pagination_layout.addStretch()
    
    # 스크롤, 페이지네이션을 세로로 배치
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    main_layout.addWidget(scroll)
    main_layout.addLayout(pagination_layout)
    
    list_card.body.addLayout(main_layout)

    # 스크롤/뷰포트 레퍼런스 저장 (폭 계산에 사용)
    app_instance.video_scroll = scroll

    # 다중 선택 상태 초기화
    if not hasattr(app_instance, 'video_multi_selected'):
        app_instance.video_multi_selected = set()

    # === 패널(뷰포트) 리사이즈 감지: 미리보기(빠른) + 최종(부드러운) 재스케일 ===
    # [추가] 상태 플래그
    app_instance._last_video_viewport_width = -1
    app_instance._video_rescale_busy = False

    def _safe_on_video_panel_resized(preview=True):
        # 재진입 방지
        if getattr(app_instance, "_video_rescale_busy", False):
            return
        # 폭이 실제 변한 경우에만 동작 (preview 패스에서만 적용)
        from search_filter_grid_module import get_available_width
        vw = get_available_width(app_instance)
        if preview and vw == getattr(app_instance, "_last_video_viewport_width", -1):
            return

        app_instance._last_video_viewport_width = vw
        app_instance._video_rescale_busy = True
        try:
            from search_filter_grid_module import on_panel_resized
            on_panel_resized(app_instance, preview=preview)
        finally:
            app_instance._video_rescale_busy = False

    app_instance._video_resize_watcher = ResizeWatcher(_safe_on_video_panel_resized)
    
    # 즉시 설치 대신 한 틱 뒤에 설치 (초기 레이아웃 완료 후)
    QTimer.singleShot(0, lambda: scroll.viewport().installEventFilter(app_instance._video_resize_watcher))
    # ===========================================================
    
    # Video counter (이미지 섹션에서 생성된 경우 재사용)
    if not hasattr(app_instance, 'video_counter') or not app_instance.video_counter:
        app_instance.video_counter = QLabel("No videos loaded")
        app_instance.video_counter.setStyleSheet("""
            color: #6B7280;
            font-size: 11px;
            padding: 8px;
        """)
        app_instance.video_counter.setAlignment(Qt.AlignCenter)
    app_instance.video_counter.setVisible(False)
    
    # 초기 상태: 항목이 없으므로 버튼 비활성화
    app_instance.video_prev_page_btn.setEnabled(False)
    app_instance.video_next_page_btn.setEnabled(False)
    
    return list_card, app_instance.video_counter


def clear_video_grid(app_instance):
    """비디오 플로우 레이아웃 초기화"""
    if hasattr(app_instance, 'video_flow_layout') and app_instance.video_flow_layout:
        while app_instance.video_flow_layout.count():
            child = app_instance.video_flow_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    if hasattr(app_instance, 'video_list'):
        app_instance.video_list = []  # 그리드 비우면 목록도 비움


def update_video_counter(app_instance, filtered_count, total_count):
    """동영상 카운터 업데이트
    
    ✅ filtered_count: AND 필터링 후 최종 결과 개수 (그리드에 표시되는 실제 개수)
    ✅ total_count: 원본 비디오 총 개수
    """
    try:
        if not hasattr(app_instance, 'video_counter') or not app_instance.video_counter:
            return

        if total_count == 0:
            counter_text = "No videos loaded\nSearch: 0 videos"
        else:
            # ✅ Search 라인은 항상 최종 필터링 결과 개수를 표시 (AND 적용된 결과)
            counter_text = f"{total_count} videos loaded\nSearch: {filtered_count} videos"

        app_instance.video_counter.setText(counter_text)

    except Exception as e:
        print(f"비디오 카운터 업데이트 중 오류: {e}")


def switch_to_video_grid(app_instance):
    """비디오 그리드로 전환"""
    print("비디오 그리드로 전환")
    
    # 모드 전환 시 페이지를 1로 초기화
    if hasattr(app_instance, 'video_current_page'):
        app_instance.video_current_page = 1
        print("비디오 페이지를 1로 초기화")
    
    # 현재 스크롤 위치 저장 (이미지에서 비디오로 전환 시)
    if hasattr(app_instance, 'image_scroll') and app_instance.image_scroll:
        saved_scroll_position = app_instance.image_scroll.verticalScrollBar().value()
        print(f"이미지 스크롤 위치 저장: {saved_scroll_position}")
    else:
        saved_scroll_position = 0
    
    # 비디오 그리드가 없으면 생성
    if not hasattr(app_instance, 'video_container') or not app_instance.video_container:
        print("비디오 그리드 생성 중...")
        create_video_grid_in_place(app_instance)
    
    # 🔧 중요: 비디오 컨테이너를 스크롤 영역에 연결
    if hasattr(app_instance, 'image_scroll') and app_instance.image_scroll:
        if hasattr(app_instance, 'video_container') and app_instance.video_container:
            # 현재 위젯(이미지 컨테이너)을 제거하고 비디오 컨테이너를 설정
            app_instance.image_scroll.takeWidget()
            app_instance.image_scroll.setWidget(app_instance.video_container)
            # 🔧 video_scroll 참조 설정 (리사이즈 이벤트 처리를 위해)
            app_instance.video_scroll = app_instance.image_scroll
            print("비디오 컨테이너를 스크롤 영역에 연결")
    
    # 비디오 컨테이너 보이기, 이미지 컨테이너 숨기기
    if hasattr(app_instance, 'video_container') and app_instance.video_container:
        app_instance.video_container.setVisible(True)
        print("비디오 컨테이너 표시")
    
    if hasattr(app_instance, 'image_container') and app_instance.image_container:
        app_instance.image_container.setVisible(False)
        print("이미지 컨테이너 숨김")
    
    # 비디오 페이지네이션 UI가 없으면 생성
    if not hasattr(app_instance, 'video_prev_page_btn') or not hasattr(app_instance, 'video_page_label'):
        print("비디오 페이지네이션 UI 생성 중...")
        create_video_pagination_ui(app_instance)
    
    # 비디오 페이지네이션 UI 보이기, 이미지 페이지네이션 UI 숨기기
    if hasattr(app_instance, 'video_prev_page_btn'):
        app_instance.video_prev_page_btn.setVisible(True)
    if hasattr(app_instance, 'video_page_label'):
        app_instance.video_page_label.setVisible(True)
    if hasattr(app_instance, 'video_next_page_btn'):
        app_instance.video_next_page_btn.setVisible(True)
    if hasattr(app_instance, 'add_video_button'):
        app_instance.add_video_button.setVisible(True)
    
    if hasattr(app_instance, 'image_prev_page_btn'):
        app_instance.image_prev_page_btn.setVisible(False)
    if hasattr(app_instance, 'image_page_label'):
        app_instance.image_page_label.setVisible(False)
    if hasattr(app_instance, 'image_next_page_btn'):
        app_instance.image_next_page_btn.setVisible(False)
    if hasattr(app_instance, 'add_image_button'):
        app_instance.add_image_button.setVisible(False)
    
    # 카운터 표시 전환
    if hasattr(app_instance, 'video_counter') and app_instance.video_counter:
        app_instance.video_counter.setVisible(True)
    if hasattr(app_instance, 'image_counter') and app_instance.image_counter:
        app_instance.image_counter.setVisible(False)
    
    print("비디오 페이지네이션 UI 표시, 이미지 페이지네이션 UI 숨김")
    
    # 비디오 썸네일 새로고침 (비디오 레이아웃이 존재할 때만)
    if hasattr(app_instance, 'video_flow_layout') and app_instance.video_flow_layout:
        if hasattr(app_instance, 'video_files') and app_instance.video_files:
            # 모드 전환 플래그 설정 (페이지 리셋 방지용)
            app_instance._is_video_mode_switching = True
            refresh_video_thumbnails(app_instance)
            app_instance._is_video_mode_switching = False
            
            # 스크롤 위치 복원 (비디오 그리드로 전환 시)
            if hasattr(app_instance, 'video_scroll') and app_instance.video_scroll:
                QTimer.singleShot(100, lambda: app_instance.video_scroll.verticalScrollBar().setValue(saved_scroll_position))
                print(f"비디오 스크롤 위치 복원: {saved_scroll_position}")
        else:
            print("비디오 파일이 없습니다.")
    else:
        print("비디오 레이아웃이 없음 - 썸네일 새로고침 건너뜀")


def create_video_grid_in_place(app_instance):
    """기존 이미지 그리드와 동일한 스크롤 영역에 비디오 그리드 생성"""
    try:
        # 기존 이미지 스크롤 영역이 있는지 확인
        if hasattr(app_instance, 'image_scroll') and app_instance.image_scroll:
            # 비디오 컨테이너가 없으면 생성
            if not hasattr(app_instance, 'video_container') or not app_instance.video_container:
                # 비디오 컨테이너 생성
                app_instance.video_container = QWidget()
                # 스크롤바 무한 반복 방지: SizePolicy 설정
                app_instance.video_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                app_instance.video_container.setStyleSheet("""
                    QWidget {
                        background: transparent;
                    }
                """)
                
                # 비디오 플로우 레이아웃 생성
                app_instance.video_flow_layout = QFlowLayout(app_instance.video_container)
                app_instance.video_flow_layout.setSpacing(4)
                app_instance.video_flow_layout.setContentsMargins(0, 0, 0, 0)
                
                # 컨테이너에 레이아웃 설정
                app_instance.video_container.setLayout(app_instance.video_flow_layout)
                
                print("비디오 그리드 생성 완료")
            else:
                print("비디오 그리드가 이미 존재함")
            
            # 비디오 스크롤 영역 설정 (이미지와 동일한 스크롤 사용)
            app_instance.video_scroll = app_instance.image_scroll
            
            # 🔧 중요: 비디오 컨테이너를 스크롤 영역에 연결 (이미 존재하는 경우에도)
            # 현재 활성화된 그리드 모드 확인
            video_mode_active = False
            if (hasattr(app_instance, 'video_filter_btn') and 
                hasattr(app_instance, 'image_filter_btn')):
                video_mode_active = (app_instance.video_filter_btn.isChecked() and 
                                   not app_instance.image_filter_btn.isChecked())
            
            if video_mode_active:
                # 비디오 모드인 경우 스크롤 영역에 비디오 컨테이너 연결
                current_widget = app_instance.image_scroll.widget()
                if current_widget != app_instance.video_container:
                    app_instance.image_scroll.takeWidget()
                    app_instance.image_scroll.setWidget(app_instance.video_container)
                    app_instance.video_container.setVisible(True)
                    print("비디오 컨테이너를 스크롤 영역에 연결 (비디오 모드)")
            else:
                # 이미지 모드인 경우 초기에는 숨김 상태로 설정
                app_instance.video_container.setVisible(False)
                print("비디오 그리드 생성 완료 (이미지 스크롤 영역 재사용, 숨김 상태)")
        else:
            print("이미지 스크롤 영역을 찾을 수 없습니다.")
    except Exception as e:
        print(f"비디오 그리드 생성 오류: {e}")


def create_video_pagination_ui(app_instance):
    """비디오 페이지네이션 UI를 동적으로 생성"""
    try:
        # 페이지네이션 초기화
        if not hasattr(app_instance, 'video_current_page'):
            app_instance.video_current_page = 1
        if not hasattr(app_instance, 'video_items_per_page'):
            app_instance.video_items_per_page = 50
        
        # 이전 페이지 버튼
        app_instance.video_prev_page_btn = QPushButton("❮")
        app_instance.video_prev_page_btn.setStyleSheet("""
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
        app_instance.video_prev_page_btn.clicked.connect(lambda: change_video_page(app_instance, -1))
        
        # 페이지 정보 라벨
        app_instance.video_page_label = QLabel("0 / 0")
        app_instance.video_page_label.setStyleSheet("""
            color: #9CA3AF;
            font-size: 11px;
            padding: 4px 8px;
        """)
        app_instance.video_page_label.setAlignment(Qt.AlignCenter)
        app_instance.video_page_label.setMinimumWidth(60)
        
        # 다음 페이지 버튼
        app_instance.video_next_page_btn = QPushButton("❯")
        app_instance.video_next_page_btn.setStyleSheet("""
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
        app_instance.video_next_page_btn.clicked.connect(lambda: change_video_page(app_instance, 1))
        
        # Add 버튼 (비디오 추가용) - 파란색 배경 버튼
        app_instance.add_video_button = QPushButton("Add")
        app_instance.add_video_button.setCursor(Qt.PointingHandCursor)
        app_instance.add_video_button.setStyleSheet("""
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
        app_instance.add_video_button.clicked.connect(lambda: add_videos_to_current(app_instance))
        
        # 페이지네이션 레이아웃에 비디오 버튼 추가
        if hasattr(app_instance, 'pagination_layout') and app_instance.pagination_layout:
            # 레이아웃 구조: [stretch(0), image_prev(1), image_label(2), image_next(3), spacing(4), add_image_button(5), stretch(6)]
            # 비디오 버튼들을 이미지 버튼 바로 앞에 insert하여 정확히 같은 위치에 배치
            # insert 후: [stretch(0), video_prev(1), video_label(2), video_next(3), spacing(4), add_video_button(5), image_prev(6), image_label(7), image_next(8), spacing(9), add_image_button(10), stretch(11)]
            # show/hide로 전환 시 숨겨진 위젯은 레이아웃에서 공간을 차지하지 않으므로 위치가 동일해짐
            
            app_instance.pagination_layout.insertWidget(1, app_instance.video_prev_page_btn)
            app_instance.pagination_layout.insertWidget(2, app_instance.video_page_label)
            app_instance.pagination_layout.insertWidget(3, app_instance.video_next_page_btn)
            app_instance.pagination_layout.insertSpacing(4, 6)  # Add 버튼과 오른쪽 화살표 사이 여백 10px (기존 4px spacing + 6px)
            app_instance.pagination_layout.insertWidget(5, app_instance.add_video_button)
            
            # 초기에는 숨김
            app_instance.video_prev_page_btn.setVisible(False)
            app_instance.video_page_label.setVisible(False)
            app_instance.video_next_page_btn.setVisible(False)
            app_instance.add_video_button.setVisible(False)
            
            # 초기 상태: 비활성화
            app_instance.video_prev_page_btn.setEnabled(False)
            app_instance.video_next_page_btn.setEnabled(False)
            
            print("비디오 페이지네이션 UI가 이미지 버튼과 같은 위치에 추가됨 (숨김 상태)")
        else:
            # 레이아웃이 없더라도 초기 상태는 비활성화
            app_instance.video_prev_page_btn.setEnabled(False)
            app_instance.video_next_page_btn.setEnabled(False)
        
    except Exception as e:
        print(f"비디오 페이지네이션 UI 생성 오류: {e}")


def change_video_page(app_instance, direction):
    """비디오 페이지 변경 (direction: -1 이전, 1 다음)"""
    if not hasattr(app_instance, 'video_filtered_list'):
        return
    
    total_items = len(app_instance.video_filtered_list)
    if total_items == 0:
        return
    
    items_per_page = getattr(app_instance, 'video_items_per_page', 50)
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
    
    # 현재 페이지 업데이트
    current_page = getattr(app_instance, 'video_current_page', 1)
    new_page = current_page + direction
    
    # 페이지 범위 제한
    if new_page < 1 or new_page > total_pages:
        return
    
    app_instance.video_current_page = new_page
    
    # 페이지 변경 중임을 표시 (필터 리셋 방지)
    app_instance._is_video_page_changing = True
    
    # 스크롤 위치 초기화
    if hasattr(app_instance, 'video_scroll') and app_instance.video_scroll:
        app_instance.video_scroll.verticalScrollBar().setValue(0)
    
    # 썸네일 재생성
    refresh_video_thumbnails(app_instance)
    
    # 페이지 변경 완료
    app_instance._is_video_page_changing = False
    
    print(f"비디오 페이지 변경: {new_page} / {total_pages}")


def update_video_pagination_ui(app_instance):
    """비디오 페이지네이션 UI 업데이트"""
    if not hasattr(app_instance, 'video_page_label'):
        return
    
    total_items = len(getattr(app_instance, 'video_filtered_list', []))
    if total_items == 0:
        app_instance.video_page_label.setText("0 / 0")
        app_instance.video_prev_page_btn.setEnabled(False)
        app_instance.video_next_page_btn.setEnabled(False)
        return
    
    items_per_page = getattr(app_instance, 'video_items_per_page', 50)
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
    current_page = getattr(app_instance, 'video_current_page', 1)
    
    # 페이지 범위 조정 (필터 변경 시 현재 페이지가 범위를 벗어날 수 있음)
    if current_page > total_pages:
        app_instance.video_current_page = total_pages
        current_page = total_pages
    
    app_instance.video_page_label.setText(f"{current_page} / {total_pages}")
    app_instance.video_prev_page_btn.setEnabled(current_page > 1)
    app_instance.video_next_page_btn.setEnabled(current_page < total_pages)


def refresh_video_thumbnails(app_instance):
    """비디오 썸네일 새로고침 (검색 결과 반영)"""
    print(f"비디오 썸네일 새로고침 시작: 총 비디오 {len(app_instance.video_files)}개")
    
    # 검색/필터 변경 시 첫 페이지로 초기화 (단, 페이지 변경 중이거나 모드 전환 중이 아닐 때만)
    is_page_changing = getattr(app_instance, '_is_video_page_changing', False)
    is_mode_switching = getattr(app_instance, '_is_video_mode_switching', False)
    
    if not is_page_changing and not is_mode_switching:
        if not hasattr(app_instance, '_video_filter_initialization_done'):
            app_instance._video_filter_initialization_done = True
        else:
            # 초기화가 아닌 경우에만 페이지 리셋
            if hasattr(app_instance, 'video_current_page'):
                app_instance.video_current_page = 1
    
    # search_module의 통합 필터 로직 호출 (중복 방지)
    print("🔄 비디오 그리드 갱신 요청 - 통합 필터로 라우팅")
    from search_module import update_image_grid_unified
    app_instance.active_grid_token += 1
    update_image_grid_unified(app_instance, expected_token=app_instance.active_grid_token)


def _render_video_grid_direct(app_instance, filtered_videos):
    """비디오 그리드 직접 렌더링 (이미 필터링된 목록 전달받음)"""
    print(f"🔄 비디오 그리드 직접 렌더링: {len(filtered_videos)}개")
    
    # 즉시 기존 썸네일들 제거
    if hasattr(app_instance, 'video_flow_layout') and app_instance.video_flow_layout:
        try:
            while app_instance.video_flow_layout.count():
                child = app_instance.video_flow_layout.takeAt(0)
                if child and child.widget():
                    child.widget().deleteLater()
        except RuntimeError as e:
            print(f"비디오 레이아웃 정리 중 오류 (무시): {e}")
    
    # 비디오 카운터 업데이트
    try:
        search_target = getattr(app_instance, 'original_video_files', getattr(app_instance, 'video_files', []))
        update_video_counter(app_instance, len(filtered_videos), len(search_target))
    except Exception as e:
        print(f"비디오 카운터 업데이트 실패: {e}")
    
    # 페이지네이션 UI 업데이트
    update_video_pagination_ui(app_instance)
    
    # 현재 페이지의 비디오만 필터링
    items_per_page = getattr(app_instance, 'video_items_per_page', 50)
    current_page = getattr(app_instance, 'video_current_page', 1)
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_videos = filtered_videos[start_idx:end_idx]
    
    print(f"페이지 {current_page}: {len(page_videos)}개 비디오 로딩 (인덱스 {start_idx}~{end_idx-1})")
    
    # 비디오 썸네일을 백그라운드에서 생성 (현재 페이지만)
    create_video_thumbnails_async(app_instance, page_videos)

def create_video_thumbnails_async(app_instance, filtered_videos, update_token=None):
    """비디오 썸네일을 비동기로 생성"""
    app_instance.video_list = [str(p) for p in filtered_videos]  # 검색 모듈이 이 경로로 들어올 때도 커버
    
    # ✅ 이전 작업 타이머가 있으면 정지 (섞임 방지)
    try:
        if hasattr(app_instance, 'video_thumbnail_creation_timer') and app_instance.video_thumbnail_creation_timer:
            app_instance.video_thumbnail_creation_timer.stop()
    except Exception:
        pass

    # ✅ 토큰: 호출 시 전달되면 사용, 아니면 내부 토큰 증가
    if update_token is None:
        current = getattr(app_instance, '_video_thumb_job_token', 0) + 1
        setattr(app_instance, '_video_thumb_job_token', current)
        token = current
    else:
        token = int(update_token)

    # 활성 토큰 기록 (오래된 배치 차단용)
    app_instance._video_thumb_active_token = token

    # 배치 시작 인덱스 초기화
    app_instance.video_thumbnail_batch_start = 0

    # QTimer를 사용하여 백그라운드에서 썸네일 생성
    app_instance.video_thumbnail_creation_timer = QTimer()
    app_instance.video_thumbnail_creation_timer.setSingleShot(True)
    # ✅ 토큰을 함께 전달
    app_instance.video_thumbnail_creation_timer.timeout.connect(lambda: create_video_thumbnail_batch(app_instance, filtered_videos, token))
    app_instance.video_thumbnail_creation_timer.start(0)  # 즉시 시작


def create_video_thumbnail_batch(app_instance, filtered_videos, job_token=None):
    """배치 비디오 썸네일 생성 (UI 블로킹 방지)"""
    # ✅ 오래된 작업이면 즉시 중단
    if job_token is not None and job_token != getattr(app_instance, '_video_thumb_active_token', None):
        print(f"⏭️ 오래된 비디오 배치 무시: {job_token} != {getattr(app_instance, '_video_thumb_active_token', None)}")
        return
    
    # 레이아웃이 존재하는지 확인
    if not hasattr(app_instance, 'video_flow_layout') or not app_instance.video_flow_layout:
        print("비디오 레이아웃이 없음 - 썸네일 생성 중단")
        return

    # 스크롤 영역의 실제 폭 계산
    from search_filter_grid_module import get_available_width, get_columns_and_spacing
    available_width = get_available_width(app_instance)
    print(f"배치 비디오 썸네일 생성 - 사용 가능한 폭: {available_width}")
    columns, spacing = get_columns_and_spacing(app_instance, available_width)
    
    # 한 번에 처리할 썸네일 수 (UI 반응성 유지)
    batch_size = 10
    start_idx = getattr(app_instance, 'video_thumbnail_batch_start', 0)
    end_idx = min(start_idx + batch_size, len(filtered_videos))
    
    # 현재 배치의 썸네일 생성
    for i in range(start_idx, end_idx):
        # ✅ 진행 중 토큰 재확인 (중간에 무효화될 수 있음)
        if job_token is not None and job_token != getattr(app_instance, '_video_thumb_active_token', None):
            print(f"⏭️ 비디오 배치 중단(토큰 변경): {job_token} != {getattr(app_instance, '_video_thumb_active_token', None)}")
            return

        video_path = filtered_videos[i]
        thumb = ImageThumbnail(str(video_path), video_path.name)
        thumb.clicked.connect(lambda path=str(video_path): handle_video_thumbnail_click(app_instance, path))
        
        # 패널 폭/열수에 맞춰 썸네일 로드 (배치: 매끄럽게)
        thumb.load_thumbnail(available_width, smooth=True, force=True, columns=columns, spacing=spacing)
        
        # 플로우 레이아웃에 추가 (자동 배치) - 안전성 검사 추가
        if hasattr(app_instance, 'video_flow_layout') and app_instance.video_flow_layout:
            try:
                app_instance.video_flow_layout.addWidget(thumb)
            except RuntimeError as e:
                print(f"비디오 썸네일 추가 중 오류 (무시): {e}")
                # 레이아웃이 이미 삭제된 경우 썸네일도 삭제
                thumb.deleteLater()
                return
    
    # 다음 배치가 있으면 계속 처리
    if end_idx < len(filtered_videos):
        app_instance.video_thumbnail_batch_start = end_idx
        # ✅ 다음 배치에도 동일 토큰 전달
        QTimer.singleShot(1, lambda: create_video_thumbnail_batch(app_instance, filtered_videos, job_token))
    else:
        # 모든 썸네일 생성 완료
        app_instance.video_thumbnail_batch_start = 0
        print("비디오 썸네일 새로고침 완료")
        
        # 현재 선택된 비디오가 필터링된 목록에 있으면 그것을 선택, 없으면 첫 번째 비디오 선택
        if filtered_videos:
            current_video = getattr(app_instance, 'current_video', None)
            video_to_load = None
            
            # 현재 선택된 비디오가 필터링된 목록에 있는지 확인
            if current_video:
                current_video_str = str(current_video)
                for video_path in filtered_videos:
                    if str(video_path) == current_video_str:
                        video_to_load = current_video_str
                        print(f"현재 선택된 동영상 유지: {video_to_load}")
                        break
            
            # 현재 선택된 비디오가 없거나 필터링된 목록에 없으면 첫 번째 비디오 선택
            if not video_to_load:
                video_to_load = str(filtered_videos[0])
                print(f"첫 번째 동영상 자동 선택: {video_to_load}")
            
            # 동영상 프리뷰 로드
            from video_preview_module import load_video_from_module
            load_video_from_module(app_instance, video_to_load)
        
        # 썸네일 생성 완료 후 현재 선택 상태 강제 업데이트
        _refresh_video_grid_selection_visuals(app_instance)


# get_video_available_width 함수는 메인 모듈의 get_available_width로 통합됨


# on_video_panel_resized 함수는 메인 모듈의 on_panel_resized로 통합됨


def add_videos_to_current(app_instance):
    """현재 비디오 목록에 추가 비디오 로드"""
    from PySide6.QtWidgets import QFileDialog
    from pathlib import Path
    
    # 파일 선택 대화상자
    file_dialog = QFileDialog(app_instance)
    file_dialog.setFileMode(QFileDialog.ExistingFiles)
    file_dialog.setNameFilter("비디오 파일 (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v)")
    file_dialog.setWindowTitle("추가할 비디오 선택")
    
    # 스타일 적용
    file_dialog.setStyleSheet("""
        QFileDialog {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
            color: #F0F2F5;
            border: 1px solid rgba(75,85,99,0.3);
            border-radius: 8px;
        }
        QPushButton {
            background: #3B82F6;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #2563EB;
        }
        QPushButton:pressed {
            background: #1D4ED8;
        }
    """)
    
    if file_dialog.exec() == QFileDialog.Accepted:
        selected_files = file_dialog.selectedFiles()
        if selected_files:
            # 지원하는 비디오 확장자
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            
            # 새로 추가할 비디오들 필터링
            new_videos = []
            for file_path in selected_files:
                path_obj = Path(file_path)
                if path_obj.suffix.lower() in video_extensions:
                    new_videos.append(path_obj)
            
            if new_videos:
                # 기존 비디오 목록에 추가
                if not hasattr(app_instance, 'video_files'):
                    app_instance.video_files = []
                if not hasattr(app_instance, 'original_video_files'):
                    app_instance.original_video_files = []
                
                # 중복 제거하면서 추가
                existing_paths = {str(path) for path in app_instance.video_files}
                for new_video in new_videos:
                    if str(new_video) not in existing_paths:
                        app_instance.video_files.append(new_video)
                        app_instance.original_video_files.append(new_video)
                
                # 비디오 썸네일 새로고침
                refresh_video_thumbnails(app_instance)
                
                # 카운터 업데이트
                update_video_counter(app_instance, len(app_instance.video_files), len(app_instance.video_files))
                
                app_instance.statusBar().showMessage(f"비디오 {len(new_videos)}개가 추가되었습니다.")
            else:
                app_instance.statusBar().showMessage("선택된 비디오가 없습니다.")


def handle_video_thumbnail_click(app_instance, video_path):
    """비디오 썸네일 클릭 처리: Shift+Ctrl 동시 시 다중선택 토글, 아니면 단일 선택"""
    from search_filter_grid_module import handle_common_thumbnail_click
    handle_common_thumbnail_click(app_instance, video_path, 'video')


def _choose_replacement_current_from_multi_video(app_instance, reference_path):
    """현재 선택 해제 시 다중선택 내에서 아래 우선, 없으면 위에서 선택"""
    try:
        grid_order = getattr(app_instance, 'video_list', [])
        if not grid_order:
            return None
        idx_map = {p: i for i, p in enumerate(grid_order)}
        ref_idx = idx_map.get(reference_path, -1)
        if ref_idx == -1:
            return None

        # 다중선택 후보를 그리드 순서로 정렬
        candidates = [p for p in app_instance.video_multi_selected if p in idx_map]
        if not candidates:
            return None
        candidates.sort(key=lambda p: idx_map[p])

        # 아래(인덱스 큰 것) 우선
        below = [p for p in candidates if idx_map[p] > ref_idx]
        if below:
            return below[0]
        # 없으면 위(인덱스 작은 것)에서 마지막
        above = [p for p in candidates if idx_map[p] < ref_idx]
        if above:
            return above[-1]
        return None
    except Exception:
        return None


def _refresh_video_grid_selection_visuals(app_instance):
    """비디오 그리드의 현재/다중 선택 테두리 일괄 갱신"""
    try:
        current = getattr(app_instance, 'current_video', None)
        multi = getattr(app_instance, 'video_multi_selected', set())
        
        for i in range(app_instance.video_flow_layout.count()):
            item = app_instance.video_flow_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ImageThumbnail):
                    # 현재 선택된 비디오는 항상 파란색 테두리 유지
                    widget.is_current = (widget.image_path == current)
                    # 다중선택된 비디오들은 초록색 테두리 (현재 선택 비디오 제외)
                    widget.is_multi = (widget.image_path in multi) and (widget.image_path != current)
                    widget.update_selection()
    except Exception:
        pass


# get_columns_and_spacing 함수는 메인 모듈로 통합됨


# 필요한 클래스들 import
try:
    from search_filter_grid_module import ImageThumbnail, QFlowLayout, ResizeWatcher
except ImportError:
    # 기본 클래스들 정의 (필요시)
    pass
