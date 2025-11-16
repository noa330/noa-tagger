# -*- coding: utf-8 -*-
"""
All Tags 관리 공용 모듈
모든 모듈에서 공통으로 사용하는 all_tags 추가/삭제/편집 로직을 담당
"""

def add_tag_to_all_tags(app_instance, image_path: str, tag: str, is_trigger: bool = False):
    """all_tags에 태그 추가"""
    if not image_path or not tag:
        return
    
    # all_tags 초기화
    if not hasattr(app_instance, 'all_tags'):
        app_instance.all_tags = {}
    
    # 이미지 경로가 없으면 빈 리스트로 초기화
    if image_path not in app_instance.all_tags:
        app_instance.all_tags[image_path] = []
    
    # 태그가 이미 있으면 추가하지 않음
    if tag not in app_instance.all_tags[image_path]:
        app_instance.all_tags[image_path].append(tag)
        print(f"✅ All Tags Manager: 태그 추가 - {tag} (이미지: {image_path})")


def remove_tag_from_all_tags(app_instance, image_path: str, tag: str):
    """all_tags에서 태그 제거"""
    if not image_path or not tag:
        return
    
    # all_tags가 없으면 아무것도 하지 않음
    if not hasattr(app_instance, 'all_tags') or not app_instance.all_tags:
        return
    
    # 이미지 경로가 없으면 아무것도 하지 않음
    if image_path not in app_instance.all_tags:
        return
    
    # 태그 제거
    if tag in app_instance.all_tags[image_path]:
        app_instance.all_tags[image_path].remove(tag)
        print(f"✅ All Tags Manager: 태그 제거 - {tag} (이미지: {image_path})")


def edit_tag_in_all_tags(app_instance, image_path: str, old_tag: str, new_tag: str):
    """all_tags에서 태그 편집"""
    if not image_path or not old_tag or not new_tag or old_tag == new_tag:
        return
    
    # all_tags가 없으면 아무것도 하지 않음
    if not hasattr(app_instance, 'all_tags') or not app_instance.all_tags:
        return
    
    # 이미지 경로가 없으면 아무것도 하지 않음
    if image_path not in app_instance.all_tags:
        return
    
    # 태그 편집
    if old_tag in app_instance.all_tags[image_path]:
        index = app_instance.all_tags[image_path].index(old_tag)
        app_instance.all_tags[image_path][index] = new_tag
        print(f"✅ All Tags Manager: 태그 편집 - {old_tag} → {new_tag} (이미지: {image_path})")


def set_tags_for_image(app_instance, image_path: str, tags: list):
    """특정 이미지의 모든 태그를 설정"""
    if not image_path:
        return
    
    # all_tags 초기화
    if not hasattr(app_instance, 'all_tags'):
        app_instance.all_tags = {}
    
    # 태그 리스트 설정
    app_instance.all_tags[image_path] = list(tags) if tags else []
    print(f"✅ All Tags Manager: 이미지 태그 설정 - {len(tags)}개 태그 (이미지: {image_path})")


def get_tags_for_image(app_instance, image_path: str) -> list:
    """특정 이미지의 태그 리스트 반환"""
    if not image_path or not hasattr(app_instance, 'all_tags') or not app_instance.all_tags:
        return []
    
    return app_instance.all_tags.get(image_path, [])


def remove_image_from_all_tags(app_instance, image_path: str):
    """all_tags에서 특정 이미지 제거"""
    if not image_path or not hasattr(app_instance, 'all_tags') or not app_instance.all_tags:
        return
    
    if image_path in app_instance.all_tags:
        del app_instance.all_tags[image_path]
        print(f"✅ All Tags Manager: 이미지 제거 - {image_path}")


def get_all_unique_tags(app_instance) -> set:
    """모든 고유 태그 반환"""
    if not hasattr(app_instance, 'all_tags') or not app_instance.all_tags:
        return set()
    
    unique_tags = set()
    for tags in app_instance.all_tags.values():
        unique_tags.update(tags)
    
    return unique_tags


def get_image_count_for_tag(app_instance, tag: str) -> int:
    """특정 태그를 사용하는 이미지 수 반환"""
    if not tag or not hasattr(app_instance, 'all_tags') or not app_instance.all_tags:
        return 0
    
    count = 0
    for tags in app_instance.all_tags.values():
        if tag in tags:
            count += 1
    
    return count


def sync_current_tags_with_all_tags(app_instance):
    """current_tags를 all_tags와 동기화"""
    if not hasattr(app_instance, 'current_image') or not app_instance.current_image:
        return
    
    current_tags = get_tags_for_image(app_instance, app_instance.current_image)
    if hasattr(app_instance, 'current_tags'):
        app_instance.current_tags = current_tags
        print(f"✅ All Tags Manager: current_tags 동기화 완료 - {len(current_tags)}개 태그")


def update_current_tags_from_all_tags(app_instance):
    """all_tags에서 current_tags 업데이트"""
    if not hasattr(app_instance, 'current_image') or not app_instance.current_image:
        return
    
    current_tags = get_tags_for_image(app_instance, app_instance.current_image)
    if hasattr(app_instance, 'current_tags'):
        app_instance.current_tags = current_tags
        print(f"✅ All Tags Manager: current_tags 업데이트 완료 - {len(current_tags)}개 태그")


def update_all_tags_from_current_tags(app_instance):
    """current_tags에서 all_tags 업데이트"""
    if not hasattr(app_instance, 'current_image') or not app_instance.current_image:
        return
    
    if hasattr(app_instance, 'current_tags'):
        set_tags_for_image(app_instance, app_instance.current_image, app_instance.current_tags)
        print(f"✅ All Tags Manager: all_tags 업데이트 완료 - {len(app_instance.current_tags)}개 태그")
