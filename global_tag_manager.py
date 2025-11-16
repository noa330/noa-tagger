# -*- coding: utf-8 -*-
"""
글로벌 태그 관리 플러그인
모든 모듈에서 공통으로 사용하는 글로벌 태그 추가/삭제/편집 로직을 담당
"""

def add_global_tag(app_instance, tag, is_trigger=False, **kwargs):
    """글로벌 태그 추가 (메타 보존 중심)
    - WD/LLaVA 등 AI 메타(tag_confidence/llava_tag_info)가 이미 있는 태그는 manual_tag_info를 건드리지 않는다.
    - 수동 입력(트리거/used)로 보이는 경우에만 manual_tag_info를 세팅한다.
    """
    if not tag:
        return
    
    # 전체 태그 통계에 추가 (정수/딕셔너리 형태 모두 지원)
    if tag in app_instance.global_tag_stats:
        current_value = app_instance.global_tag_stats[tag]
        if isinstance(current_value, dict):
            # 딕셔너리 형태: {'image_count': count, 'category': 'unknown'}
            app_instance.global_tag_stats[tag]['image_count'] += 1
        else:
            # 정수 형태: count
            app_instance.global_tag_stats[tag] += 1
    else:
        # 새로운 태그 추가 시 기존 구조 확인
        if app_instance.global_tag_stats and isinstance(next(iter(app_instance.global_tag_stats.values())), dict):
            # 딕셔너리 형태로 초기화
            app_instance.global_tag_stats[tag] = {'image_count': 1, 'category': 'unknown'}
        else:
            # 정수 형태로 초기화
            app_instance.global_tag_stats[tag] = 1

    # ── 메타 보존 로직 ─────────────────────────────────────────────────────────
    # 현재 이미지 기준으로 해당 태그가 AI 메타를 보유하는지 확인
    has_ai_meta = False
    try:
        current_image = getattr(app_instance, 'current_image', None)
        tc = getattr(app_instance, 'tag_confidence', None)
        if current_image and isinstance(tc, dict):
            pairs = tc.get(current_image, [])
            # pairs: list[(tag, score)] with score == -1.0 for LLaVA, >0 for WD
            for t, s in pairs:
                if t == tag:
                    has_ai_meta = True
                    break
    except Exception:
        has_ai_meta = False

    # manual_tag_info 준비
    if not hasattr(app_instance, 'manual_tag_info'):
        app_instance.manual_tag_info = {}

    if has_ai_meta:
        # AI 메타가 이미 있는 태그: 수동 표기를 덮어쓰지 않음
        # 단, 과거에 (used=False)로 잘못 찍혀 있던 흔적은 제거
        try:
            if tag in app_instance.manual_tag_info and app_instance.manual_tag_info[tag] is False:
                del app_instance.manual_tag_info[tag]
        except Exception:
            pass
    else:
        # AI 메타가 없는 태그: 이번 추가를 '수동'으로 간주하여 is_trigger 값 기록
        app_instance.manual_tag_info[tag] = bool(is_trigger)



def remove_global_tag(app_instance, tag):
    """글로벌 태그 제거 (카운터만 감소, 삭제는 하지 않음)"""
    if not tag:
        return
    
    # 전체 태그 통계에서 제거 (정수/딕셔너리 형태 모두 지원)
    if tag in app_instance.global_tag_stats:
        current_value = app_instance.global_tag_stats[tag]
        if isinstance(current_value, dict):
            app_instance.global_tag_stats[tag]['image_count'] -= 1
        else:
            app_instance.global_tag_stats[tag] -= 1


def edit_global_tag(app_instance, old_tag, new_tag):
    """글로벌 태그 편집 (기존 태그 삭제 후 새 태그 추가)"""
    if not old_tag or not new_tag or old_tag == new_tag:
        return
    
    # 기존 태그 정보 백업
    old_value = None
    if old_tag in app_instance.global_tag_stats:
        old_value = app_instance.global_tag_stats[old_tag]
        del app_instance.global_tag_stats[old_tag]
    
    # 새 태그로 추가
    if old_value:
        # 정수 형태인지 딕셔너리 형태인지 확인
        if isinstance(old_value, dict):
            # 딕셔너리 형태: {'image_count': count, 'category': 'unknown'}
            app_instance.global_tag_stats[new_tag] = old_value.copy()
        else:
            # 정수 형태: count
            app_instance.global_tag_stats[new_tag] = old_value
    
    # manual_tag_info 업데이트 (수동 입력 태그인 경우)
    if hasattr(app_instance, 'manual_tag_info') and old_tag in app_instance.manual_tag_info:
        is_trigger = app_instance.manual_tag_info[old_tag]
        del app_instance.manual_tag_info[old_tag]
        app_instance.manual_tag_info[new_tag] = is_trigger
    
    # llava_tag_info 업데이트 (LLaVA 태그인 경우)
    if hasattr(app_instance, 'llava_tag_info') and old_tag in app_instance.llava_tag_info:
        del app_instance.llava_tag_info[old_tag]
        app_instance.llava_tag_info[new_tag] = True


# all_tags 관리는 all_tags_manager.py에서 담당
