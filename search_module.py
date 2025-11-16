"""
검색 모듈
검색 기능만 담당하는 모듈
"""

from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Qt, QTimer  # QTimer 추가 (디바운스용)

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


def _search_by_tag_position(tags, search_text):
    """태그 순서 기반 검색"""
    if not tags or not search_text:
        return False
    
    # "1:solo" 형태의 검색 (N번째 태그)
    if ':' in search_text:
        try:
            position_str, tag_name = search_text.split(':', 1)
            position = int(position_str.strip()) - 1  # 1-based to 0-based
            tag_name = tag_name.strip().lower()
            
            if 0 <= position < len(tags):
                return tag_name in tags[position].lower()
        except (ValueError, IndexError):
            pass
    
    # "solo:pokemon" 형태의 검색 (태그 A가 태그 B보다 앞에 있는지)
    if ':' in search_text:
        try:
            tag_a, tag_b = search_text.split(':', 1)
            tag_a = tag_a.strip().lower()
            tag_b = tag_b.strip().lower()
            
            # 두 태그 모두 존재하는지 확인
            if tag_a in [tag.lower() for tag in tags] and tag_b in [tag.lower() for tag in tags]:
                # 태그 A의 위치가 태그 B보다 앞에 있는지 확인
                pos_a = next(i for i, tag in enumerate(tags) if tag.lower() == tag_a)
                pos_b = next(i for i, tag in enumerate(tags) if tag.lower() == tag_b)
                return pos_a < pos_b
        except (ValueError, StopIteration):
            pass
    
    return False

def create_search_widget(app_instance):
    """검색 위젯 생성 (검색창만)"""
    from PySide6.QtWidgets import QVBoxLayout, QWidget, QComboBox
    
    # 디바운스 타이머 & 토큰 초기화 ------------------------------
    if not hasattr(app_instance, 'grid_update_timer'):
        app_instance.grid_update_timer = QTimer()
        app_instance.grid_update_timer.setSingleShot(True)
        app_instance.grid_update_timer.setInterval(120)  # 입력 안정화 대기 120ms
    if not hasattr(app_instance, 'active_grid_token'):
        app_instance.active_grid_token = 0  # 갱신 토큰(버전)
    # -----------------------------------------------------------

    # 컨테이너 위젯 생성
    search_container = QWidget()
    search_layout = QVBoxLayout(search_container)
    search_layout.setContentsMargins(0, 0, 0, 0)
    search_layout.setSpacing(4)
    
    # 검색 타입 드롭다운 (이미지 모드 기본 옵션)
    app_instance.search_type_dropdown = CustomComboBox()
    app_instance.search_type_dropdown.addItems([
        "전체", "파일명", "전체 태그", "활성 태그", "리무버 태그",
        "첫 번째 태그", "마지막 태그", "태그 순서"
    ])
    app_instance.search_type_dropdown.setCurrentText("전체")
    
    # 드롭다운 스타일
    app_instance.search_type_dropdown.setStyleSheet("""
        QComboBox {
            background: rgba(26,27,38,0.8);
            border: 1px solid rgba(75,85,99,0.3);
            color: white;
            font-family: 'Segoe UI';
            font-size: 12px;
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
            color: white;
            selection-background-color: #3B82F6;
        }
    """)
    
    # 검색 입력창 (기본값: 이미지 모드)
    app_instance.filter_input = QLineEdit()
    app_instance.filter_input.setPlaceholderText("Search images...")
    app_instance.filter_input.setMinimumWidth(0)  # 최소 너비 0으로 설정
    
    # 검색 입력창 스타일
    app_instance.filter_input.setStyleSheet("""
        QLineEdit {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            font-family: 'Segoe UI';
            font-size: 12px;
        }
        QLineEdit:focus {
            border: 2px solid #3B82F6;
        }
        QLineEdit:hover {
            border: 1px solid rgba(75,85,99,0.5);
        }
    """)
    
    # 레이아웃에 추가 (검색창만)
    search_layout.addWidget(app_instance.filter_input)
    
    # 이벤트 연결 ------------------------------------------------
    app_instance.filter_input.textChanged.connect(
        lambda text: on_search_text_changed(app_instance, text)
    )
    app_instance.search_type_dropdown.currentTextChanged.connect(
        lambda _: on_search_text_changed(app_instance, app_instance.filter_input.text())
    )
    # -----------------------------------------------------------

    # 검색 결과 초기화 (None으로 설정하여 필터링에서 제외되지 않도록)
    app_instance.search_results = None
    
    # 고급 검색 이벤트는 메인 애플리케이션에서 연결됨
    
    return search_container

def create_search_dropdown_widget(app_instance):
    """검색 드롭다운 위젯 생성"""
    from PySide6.QtWidgets import QComboBox
    
    # 검색 타입 드롭다운
    app_instance.search_type_dropdown = CustomComboBox()
    app_instance.search_type_dropdown.addItems([
        "전체", "파일명", "전체 태그", "활성 태그", "리무버 태그",
        "첫 번째 태그", "마지막 태그", "태그 순서"
    ])
    app_instance.search_type_dropdown.setCurrentText("전체")
    
    # 드롭다운 스타일
    app_instance.search_type_dropdown.setStyleSheet("""
        QComboBox {
            background: rgba(26,27,38,0.8);
            border: 1px solid rgba(75,85,99,0.3);
            color: white;
            font-family: 'Segoe UI';
            font-size: 12px;
            min-width: 0px;
        }
        QComboBox:hover {
            background: rgba(26,27,38,0.85);
            border: 1px solid rgba(75,85,99,0.5);
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
            color: white;
            selection-background-color: #3B82F6;
        }
        QComboBox:focus {
            border: 2px solid #3B82F6;
        }
    """)
    
    # 이벤트 연결
    app_instance.search_type_dropdown.currentTextChanged.connect(
        lambda _: on_search_text_changed(app_instance, app_instance.filter_input.text())
    )
    
    return app_instance.search_type_dropdown

def update_search_ui_for_mode(app_instance):
    """미디어 모드에 따라 검색 UI 업데이트 (placeholder, 드롭다운 옵션)"""
    # 미디어 필터 상태 확인
    is_video_mode = False
    if hasattr(app_instance, 'image_filter_btn') and hasattr(app_instance, 'video_filter_btn'):
        is_video_mode = app_instance.video_filter_btn.isChecked() and not app_instance.image_filter_btn.isChecked()
    
    # 검색창 placeholder 업데이트
    if hasattr(app_instance, 'filter_input') and app_instance.filter_input:
        if is_video_mode:
            app_instance.filter_input.setPlaceholderText("Search videos...")
        else:
            app_instance.filter_input.setPlaceholderText("Search images...")
    
    # 검색 대상 드롭다운 옵션 업데이트
    if hasattr(app_instance, 'search_type_dropdown') and app_instance.search_type_dropdown:
        current_text = app_instance.search_type_dropdown.currentText()
        
        if is_video_mode:
            # 비디오 모드: "전체", "파일명"만 표시 (태깅 기능 없음)
            video_options = ["전체", "파일명"]
            app_instance.search_type_dropdown.clear()
            app_instance.search_type_dropdown.addItems(video_options)
            
            # 현재 선택된 옵션이 비디오 모드에 없으면 "전체"로 설정
            if current_text not in video_options:
                app_instance.search_type_dropdown.setCurrentText("전체")
            else:
                app_instance.search_type_dropdown.setCurrentText(current_text)
        else:
            # 이미지 모드: 모든 옵션 표시
            image_options = [
                "전체", "파일명", "전체 태그", "활성 태그", "리무버 태그",
                "첫 번째 태그", "마지막 태그", "태그 순서"
            ]
            app_instance.search_type_dropdown.clear()
            app_instance.search_type_dropdown.addItems(image_options)
            
            # 현재 선택된 옵션이 이미지 모드에 없으면 "전체"로 설정
            if current_text not in image_options:
                app_instance.search_type_dropdown.setCurrentText("전체")
            else:
                app_instance.search_type_dropdown.setCurrentText(current_text)
        
        print(f"검색 UI 업데이트: {'비디오' if is_video_mode else '이미지'} 모드")

def _schedule_grid_update(app_instance):
    """디바운스로 그리드 갱신 1회만 스케줄"""
    # 토큰 증가: 이 호출 이전의 모든 작업은 무효화
    app_instance.active_grid_token += 1
    this_token = app_instance.active_grid_token

    # 타이머 리셋 후 최신 토큰으로만 실행
    app_instance.grid_update_timer.stop()
    # ✅ 기존 연결 전부 해제 (receivers() 쓰지 말고 안전하게 disconnect만)
    try:
        app_instance.grid_update_timer.timeout.disconnect()
    except (TypeError, RuntimeError):
        pass
    app_instance.grid_update_timer.timeout.connect(
        lambda: update_image_grid_unified(app_instance, expected_token=this_token)
    )
    app_instance.grid_update_timer.start()


def _guard_video_frame_focus_during_search_input(app_instance, duration_ms=600):
    """고급 검색 오버레이 상태에서 검색입력을 할 때 비디오 프레임 자동 표시를 잠시 막아 포커스 튐 방지"""
    try:
        if getattr(app_instance, '_overlay_active_type', None) != 'advanced_search':
            return
        
        setattr(app_instance, '_skip_video_frame_auto_show', True)
        
        timer = getattr(app_instance, '_advanced_search_focus_guard_timer', None)
        if timer is None:
            timer = QTimer(app_instance)
            timer.setSingleShot(True)

            def release_guard():
                setattr(app_instance, '_skip_video_frame_auto_show', False)
                print("고급 검색 입력 포커스 가드 해제")

            timer.timeout.connect(release_guard)
            app_instance._advanced_search_focus_guard_timer = timer
        
        timer.stop()
        timer.start(max(200, duration_ms))
        print("고급 검색 입력 중 - 비디오 프레임 자동 표시 차단")
    except Exception as e:
        print(f"고급 검색 입력 포커스 가드 설정 오류: {e}")


def on_search_text_changed(app_instance, text):
    """검색 텍스트 변경 처리 (검색 타입에 따라 다르게 동작)"""
    print(f"검색 텍스트 변경: {text}")
    
    # 미디어 모드 확인
    is_video_mode = False
    if hasattr(app_instance, 'image_filter_btn') and hasattr(app_instance, 'video_filter_btn'):
        is_video_mode = app_instance.video_filter_btn.isChecked() and not app_instance.image_filter_btn.isChecked()
    
    # 고급 검색 오버레이 상태에서는 검색 입력 중 비디오 프레임 자동 표시를 잠시 막아 포커스 튐을 방지
    if is_video_mode:
        _guard_video_frame_focus_during_search_input(app_instance)
    
    # 검색 타입 가져오기
    search_type = "전체"  # 기본값
    if hasattr(app_instance, 'search_type_dropdown') and app_instance.search_type_dropdown:
        search_type = app_instance.search_type_dropdown.currentText()
    
    print(f"검색 타입: {search_type}, 모드: {'비디오' if is_video_mode else '이미지'}")
    
    # 검색 결과 업데이트
    if not text.strip():
        app_instance.search_results = None  # 검색창이 비어있음을 표시
    else:
        search_lower = text.strip().lower()
        filtered_paths = []
        
        # 선택적 와일드카드 지원 (모듈이 존재하는 경우에만)
        try:
            import wildcard_plugin as _wc
        except Exception:
            _wc = None
        
        # 검색 대상 선택 (이미지 모드 또는 비디오 모드)
        if is_video_mode:
            # 비디오 모드: 비디오 파일 목록 사용
            search_target = getattr(app_instance, 'original_video_files', getattr(app_instance, 'video_files', []))
        else:
            # 이미지 모드: 이미지 파일 목록 사용
            search_target = getattr(app_instance, 'original_image_files', app_instance.image_files)
        
        for media_path in search_target:
            match_found = False
            
            if search_type == "전체":
                # 1. 파일명 검색
                media_name = media_path.name.lower()
                if (_wc and _wc.match_or_contains(media_name, search_lower)) or (not _wc and search_lower in media_name):
                    match_found = True
                
                # 2. 태그 검색 (이미지 모드에서만, 파일명에서 매칭되지 않은 경우에만)
                if not match_found and not is_video_mode:
                    try:
                        media_key = str(media_path)
                        from all_tags_manager import get_tags_for_image
                        media_tags = get_tags_for_image(app_instance, media_key)
                        if media_tags:
                            for tag in media_tags:
                                tag_l = tag.lower()
                                if (_wc and _wc.match_or_contains(tag_l, search_lower)) or (not _wc and search_lower in tag_l):
                                    match_found = True
                                    break
                    except Exception as e:
                        print(f"태그 검색 중 오류: {e}")
                        
            elif search_type == "파일명":
                # 파일명만 검색
                media_name = media_path.name.lower()
                if (_wc and _wc.match_or_contains(media_name, search_lower)) or (not _wc and search_lower in media_name):
                    match_found = True
                    
            elif search_type == "전체 태그" and not is_video_mode:
                # 해당 이미지의 모든 태그 검색 (활성 + 리무버 태그)
                try:
                    media_key = str(media_path)
                    all_media_tags = []
                    
                    # 활성 태그 추가 - all_tags 관리 플러그인 사용
                    from all_tags_manager import get_tags_for_image
                    media_tags = get_tags_for_image(app_instance, media_key)
                    if media_tags:
                        all_media_tags.extend(media_tags)
                    
                    # 리무버 태그 추가
                    if hasattr(app_instance, 'image_removed_tags') and media_key in app_instance.image_removed_tags:
                        all_media_tags.extend(app_instance.image_removed_tags[media_key])
                    
                    # 모든 태그에서 검색
                    for tag in all_media_tags:
                        tag_l = tag.lower()
                        if (_wc and _wc.match_or_contains(tag_l, search_lower)) or (not _wc and search_lower in tag_l):
                            match_found = True
                            break
                except Exception as e:
                    print(f"전체 태그 검색 중 오류: {e}")
                    
            elif search_type == "활성 태그" and not is_video_mode:
                # 해당 이미지의 활성화된 태그만 검색 (all_tags에서)
                try:
                    media_key = str(media_path)
                    from all_tags_manager import get_tags_for_image
                    media_tags = get_tags_for_image(app_instance, media_key)
                    if media_tags:
                        for tag in media_tags:
                            tag_l = tag.lower()
                            if (_wc and _wc.match_or_contains(tag_l, search_lower)) or (not _wc and search_lower in tag_l):
                                match_found = True
                                break
                except Exception as e:
                    print(f"활성 태그 검색 중 오류: {e}")
                    
            elif search_type == "리무버 태그" and not is_video_mode:
                # 해당 이미지의 비활성화된 태그만 검색 (image_removed_tags에서)
                try:
                    media_key = str(media_path)
                    if hasattr(app_instance, 'image_removed_tags') and media_key in app_instance.image_removed_tags:
                        removed_tags = app_instance.image_removed_tags[media_key]
                        for tag in removed_tags:
                            tag_l = tag.lower()
                            if (_wc and _wc.match_or_contains(tag_l, search_lower)) or (not _wc and search_lower in tag_l):
                                match_found = True
                                break
                except Exception as e:
                    print(f"리무버 태그 검색 중 오류: {e}")
                    
            elif search_type == "첫 번째 태그" and not is_video_mode:
                # 첫 번째 태그로 검색
                try:
                    media_key = str(media_path)
                    from all_tags_manager import get_tags_for_image
                    media_tags = get_tags_for_image(app_instance, media_key)
                    if media_tags:
                        first_tag = media_tags[0]
                        first_l = first_tag.lower()
                        if (_wc and _wc.match_or_contains(first_l, search_lower)) or (not _wc and search_lower in first_l):
                            match_found = True
                except Exception as e:
                    print(f"첫 번째 태그 검색 중 오류: {e}")
                    
            elif search_type == "마지막 태그" and not is_video_mode:
                # 마지막 태그로 검색
                try:
                    media_key = str(media_path)
                    from all_tags_manager import get_tags_for_image
                    media_tags = get_tags_for_image(app_instance, media_key)
                    if media_tags:
                        last_tag = media_tags[-1]
                        last_l = last_tag.lower()
                        if (_wc and _wc.match_or_contains(last_l, search_lower)) or (not _wc and search_lower in last_l):
                            match_found = True
                except Exception as e:
                    print(f"마지막 태그 검색 중 오류: {e}")
                    
            elif search_type == "태그 순서" and not is_video_mode:
                # 태그 순서 기반 검색 (예: "1:solo" 또는 "solo:pokemon")
                try:
                    media_key = str(media_path)
                    from all_tags_manager import get_tags_for_image
                    tags = get_tags_for_image(app_instance, media_key)
                    if tags:
                        match_found = _search_by_tag_position(tags, search_lower)
                except Exception as e:
                    print(f"태그 순서 검색 중 오류: {e}")
            
            if match_found:
                filtered_paths.append(media_path)
        
        app_instance.search_results = filtered_paths
        print(f"검색 결과: {len(filtered_paths)}개 ({search_type})")
        
        # 디버깅: 검색 결과 상태 확인
        if len(filtered_paths) == 0:
            print(f"⚠️ 검색 결과가 0개입니다. search_results = [] (빈 리스트)")
        else:
            print(f"✅ 검색 결과가 {len(filtered_paths)}개입니다.")
    
    # ✅ 디바운스된 단 한 번의 업데이트만 실행
    _schedule_grid_update(app_instance)

def update_image_grid_unified(app_instance, expected_token=None):
    """통합된 이미지/비디오 그리드 업데이트 함수 - 모든 검색 모듈에서 사용
    
    ✅ 이 함수가 이미지/비디오 그리드의 단일 진입점입니다.
    ✅ 검색 결과(search_results, advanced_search_results) + 필터(태깅/노태깅) 모두 AND 적용
    ✅ 이미지 모드: search_target → search_results AND → advanced_search_results AND → 필터(태깅/노태깅)
    ✅ 비디오 모드: search_target → search_results AND → advanced_search_results AND
    """
    try:
        print("🔄 통합 그리드 업데이트 시작")
        
        # 토큰 검증: 예약 당시 토큰과 현재 토큰이 다르면 실행 중단
        if expected_token is not None and expected_token != getattr(app_instance, 'active_grid_token', 0):
            print(f"⏭️ 오래된 업데이트 토큰 무시: {expected_token} != {app_instance.active_grid_token}")
            return
        
        # 미디어 모드 확인
        is_video_mode = False
        if hasattr(app_instance, 'image_filter_btn') and hasattr(app_instance, 'video_filter_btn'):
            is_video_mode = app_instance.video_filter_btn.isChecked() and not app_instance.image_filter_btn.isChecked()
        
        # 비디오 모드일 때는 비디오 필터링 후 그리드 업데이트
        if is_video_mode:
            print("🔄 비디오 모드 - 비디오 필터링 & 그리드 업데이트")
            _update_video_grid_with_filters(app_instance)
            return
        
        # 검색 상태 디버깅
        search_status = "None"
        if hasattr(app_instance, 'search_results'):
            if app_instance.search_results is None:
                search_status = "None (검색 안함)"
            elif app_instance.search_results:
                search_status = f"List[{len(app_instance.search_results)}] (검색 결과 있음)"
            else:
                search_status = "List[0] (검색 결과 없음)"
        
        advanced_status = "None"
        if hasattr(app_instance, 'advanced_search_results'):
            if app_instance.advanced_search_results is None:
                advanced_status = "None (고급검색 안함)"
            elif app_instance.advanced_search_results:
                advanced_status = f"List[{len(app_instance.advanced_search_results)}] (고급검색 결과 있음)"
            else:
                advanced_status = "List[0] (고급검색 결과 없음)"
        
        print(f"🔍 검색 상태 - 일반: {search_status}, 고급: {advanced_status}")
        
        # 기존 썸네일 즉시 제거
        if hasattr(app_instance, 'image_flow_layout'):
            while app_instance.image_flow_layout.count():
                child = app_instance.image_flow_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        
        # 검색 대상 이미지 목록 결정 (원본 이미지 사용)
        search_target = getattr(app_instance, 'original_image_files', app_instance.image_files)
        print(f"🔍 검색 대상 이미지 수: {len(search_target)}개")
        from all_tags_manager import get_all_unique_tags
        all_tags_count = len(get_all_unique_tags(app_instance))
        print(f"🔍 all_tags 딕셔너리 크기: {all_tags_count}개")
        
        # 필터링된 이미지 목록 생성
        filtered_images = []
        tagged_count = 0
        untagged_count = 0
        
        # 필터 텍스트 가져오기
        if hasattr(app_instance, 'filter_dropdown') and app_instance.filter_dropdown:
            filter_text = app_instance.filter_dropdown.currentText()
        else:
            filter_text = "전체 이미지"  # 기본값
            print("⚠️ filter_dropdown이 없어서 기본값 '전체 이미지' 사용")
        
        print(f"🔧 현재 필터: '{filter_text}'")
        
        for image_path in search_target:
            image_key = str(image_path)
            from all_tags_manager import get_tags_for_image
            image_tags = get_tags_for_image(app_instance, image_key)
            has_tags = len(image_tags) > 0
            
            # 일반 검색 결과 처리
            if hasattr(app_instance, 'search_results') and app_instance.search_results is not None:
                if app_instance.search_results:  # 검색 결과가 있는 경우
                    if image_path not in app_instance.search_results:
                        continue
                    else:
                        print(f"✅ 검색 결과에 포함된 이미지: {image_path.name}")
                else:  # 검색 결과가 빈 리스트인 경우 (매칭되는 파일이 없음)
                    print(f"❌ 검색 결과가 빈 리스트이므로 모든 이미지 제외")
                    continue
            
            # 고급 검색 결과 처리
            if hasattr(app_instance, 'advanced_search_results') and app_instance.advanced_search_results is not None:
                if app_instance.advanced_search_results:  # 고급 검색 결과가 있는 경우
                    if image_path not in app_instance.advanced_search_results:
                        continue
                else:  # 고급 검색 결과가 빈 리스트인 경우 (매칭되는 파일이 없음)
                    continue
            
            # 드롭박스 선택에 따른 필터링
            filter_match = False
            if filter_text == "전체 이미지":
                filter_match = True
            elif filter_text == "태깅 이미지" and has_tags:
                filter_match = True
            elif filter_text == "노태깅 이미지" and not has_tags:
                filter_match = True
            
            if filter_match:
                filtered_images.append(image_path)
                if has_tags:
                    tagged_count += 1
                else:
                    untagged_count += 1
        
        print(f"✅ 통합 필터링 완료: {len(filtered_images)}개 이미지 (태그된: {tagged_count}개, 태그 없는: {untagged_count}개)")
        
        # 이미지 카운터 업데이트
        update_image_counter(app_instance, len(filtered_images), len(search_target))
        
        # 이전 썸네일 생성 타이머 취소
        if hasattr(app_instance, 'thumbnail_creation_timer') and app_instance.thumbnail_creation_timer:
            app_instance.thumbnail_creation_timer.stop()
            print("🛑 이전 썸네일 생성 타이머 취소")
        
        # ▼▼▼ 단일 소스 고정 + 토큰 부여 ▼▼▼
        app_instance.image_files = filtered_images
        app_instance.current_grid_images = filtered_images
        current_token = getattr(app_instance, 'active_grid_token', 0)
        # ▲▲▲
        
        # 페이지네이션: 전체 목록 저장 및 현재 페이지 유지/초기화
        app_instance.image_filtered_list = filtered_images
        is_page_changing = getattr(app_instance, '_is_page_changing', False)
        if not hasattr(app_instance, 'image_current_page'):
            app_instance.image_current_page = 1
        else:
            # 페이지 이동 중이면 현재 페이지 유지, 아니면 첫 페이지로
            if not is_page_changing:
                app_instance.image_current_page = 1
        
        # 페이지네이션 UI 업데이트
        from search_filter_grid_image_module import update_image_pagination_ui
        update_image_pagination_ui(app_instance)
        
        # 현재 페이지의 이미지만 추출
        items_per_page = getattr(app_instance, 'image_items_per_page', 50)
        current_page = app_instance.image_current_page
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_images = filtered_images[start_idx:end_idx]
        
        print(f"📄 페이지 {current_page}: {len(page_images)}개 이미지 로딩 (인덱스 {start_idx}~{end_idx-1})")
        
        # 썸네일을 백그라운드에서 생성 (현재 페이지만, 토큰 전달)
        from search_filter_grid_image_module import create_thumbnails_async
        try:
            create_thumbnails_async(app_instance, page_images, update_token=current_token)
        except TypeError:
            # 기존 시그니처(토큰 미지원)인 경우도 안전하게 호출
            create_thumbnails_async(app_instance, page_images)
        
    except Exception as e:
        print(f"통합 그리드 업데이트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def update_image_counter(app_instance, filtered_count, total_count):
    """이미지 카운터 통합 업데이트 함수
    
    ✅ filtered_count: AND 필터링 후 최종 결과 개수 (그리드에 표시되는 실제 개수)
    ✅ total_count: 원본 이미지 총 개수
    """
    try:
        if not hasattr(app_instance, 'image_counter'):
            return
        
        # 카운터 텍스트 생성 (두 줄로 구분)
        if filtered_count == 0:
            counter_text = f"No images loaded\nSearch: 0 images"
        else:
            # ✅ Search 라인은 항상 최종 필터링 결과 개수를 표시 (AND 적용된 결과)
            counter_text = f"{total_count} images loaded\nSearch: {filtered_count} images"
        
        app_instance.image_counter.setText(counter_text)
        
    except Exception as e:
        print(f"이미지 카운터 업데이트 중 오류: {e}")

def reset_all_searches(app_instance):
    """모든 검색 결과 초기화"""
    try:
        print("🔄 검색 초기화 시작")
        
        # 검색 결과만 초기화 (None = 검색 안 함 상태)
        app_instance.search_results = None
        app_instance.advanced_search_results = None
        print("✅ 검색 결과 초기화 (None)")
        
        # 토큰 증가 후 통합 그리드 갱신 (현재 필터 상태 유지)
        app_instance.active_grid_token += 1
        update_image_grid_unified(app_instance, expected_token=app_instance.active_grid_token)
        
        print("✅ 검색 초기화 완료")
        
    except Exception as e:
        print(f"❌ 검색 초기화 중 오류: {e}")
        import traceback
        traceback.print_exc()

def _update_video_grid_with_filters(app_instance):
    """비디오 그리드 전용 AND 필터링 (search_results AND advanced_search_results)"""
    print("🔄 비디오 그리드 필터링 시작")
    
    # 원본 비디오 목록 가져오기
    search_target = getattr(app_instance, 'original_video_files', getattr(app_instance, 'video_files', []))
    print(f"🔍 원본 비디오: {len(search_target)}개")
    
    # 검색 상태 디버깅
    search_status = "None"
    if hasattr(app_instance, 'search_results'):
        if app_instance.search_results is None:
            search_status = "None (검색 안함)"
        elif app_instance.search_results:
            search_status = f"List[{len(app_instance.search_results)}] (검색 결과 있음)"
        else:
            search_status = "List[0] (검색 결과 없음)"
    
    advanced_status = "None"
    if hasattr(app_instance, 'advanced_search_results'):
        if app_instance.advanced_search_results is None:
            advanced_status = "None (고급검색 안함)"
        elif app_instance.advanced_search_results:
            advanced_status = f"List[{len(app_instance.advanced_search_results)}] (고급검색 결과 있음)"
        else:
            advanced_status = "List[0] (고급검색 결과 없음)"
    
    print(f"🔍 검색 상태 - 일반: {search_status}, 고급: {advanced_status}")
    
    # AND 필터링
    filtered_videos = []
    for video_path in search_target:
        # 일반 검색 결과 처리
        if hasattr(app_instance, 'search_results') and app_instance.search_results is not None:
            if app_instance.search_results:  # 검색 결과가 있는 경우
                if video_path not in app_instance.search_results:
                    continue
            else:  # 검색 결과가 빈 리스트인 경우 (매칭되는 파일이 없음)
                continue
        
        # 고급 검색 결과 처리
        if hasattr(app_instance, 'advanced_search_results') and app_instance.advanced_search_results is not None:
            if app_instance.advanced_search_results:  # 고급 검색 결과가 있는 경우
                if video_path not in app_instance.advanced_search_results:
                    continue
            else:  # 고급 검색 결과가 빈 리스트인 경우
                continue
        
        filtered_videos.append(video_path)
    
    print(f"✅ 비디오 필터링 완료: {len(filtered_videos)}개")
    
    # 필터링된 목록을 app_instance에 저장
    app_instance.video_files = filtered_videos
    app_instance.video_filtered_list = filtered_videos
    app_instance.video_list = [str(p) for p in filtered_videos]
    
    # 비디오 그리드 갱신 (search_filter_grid_video_module 직접 호출)
    from search_filter_grid_video_module import _render_video_grid_direct
    _render_video_grid_direct(app_instance, filtered_videos)
