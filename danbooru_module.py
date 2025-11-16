#!/usr/bin/env python3
"""
Danbooru 태그 카테고리 기능을 담당하는 모듈
ai-image-tagger.py에서 임포트해서 사용
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional

class DanbooruModule:
    """Danbooru 태그 카테고리 관리 모듈"""
    
    def __init__(self, danbooru_root: str = "danbooru"):
        self.danbooru_root = Path(danbooru_root)
        self.tag_to_category: Dict[str, str] = {}
        self.category_to_tags: Dict[str, List[str]] = {}
        self.mapping_file = "groups_tag_danbooru.json"
        self.is_available = False
        
        # Danbooru 폴더나 매핑 파일이 있으면 로드 시도
        if self.danbooru_root.exists() or Path(self.mapping_file).exists():
            self._load_mapping()
    
    def _load_mapping(self):
        """매핑 파일에서 태그 카테고리 로드"""
        try:
            if Path(self.mapping_file).exists():
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # groups_tag_danbooru.json 구조에 맞게 매핑 데이터 구성
                for category_name, category_data in data.items():
                    tags = category_data.get("tags", [])
                    self.category_to_tags[category_name] = tags
                    
                    for tag in tags:
                        # 태그가 여러 카테고리에 있을 경우, 먼저 로드된 카테고리를 유지
                        if tag not in self.tag_to_category:
                            self.tag_to_category[tag] = category_name
                
                self.is_available = True
                print(f"Danbooru 모듈 로드 완료: {len(self.tag_to_category)}개 태그, {len(self.category_to_tags)}개 카테고리")
                
            elif self.danbooru_root.exists():
                # 매핑 파일이 없으면 danbooru 폴더에서 직접 로드
                self._load_from_danbooru_folder()
                self.is_available = True
                
        except Exception as e:
            print(f"Danbooru 모듈 로드 오류: {e}")
            self.is_available = False
    
    def _load_from_danbooru_folder(self):
        """danbooru 폴더에서 직접 태그 카테고리 로드"""
        print("Danbooru 폴더에서 직접 로드 중...")
        
        for txt_file in self.danbooru_root.rglob("*.txt"):
            category_name = txt_file.stem
            
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    tags = [line.strip() for line in f if line.strip()]
                
                self.category_to_tags[category_name] = tags
                for tag in tags:
                    if tag not in self.tag_to_category:
                        self.tag_to_category[tag] = category_name
                        
            except Exception as e:
                print(f"파일 로드 오류 {txt_file}: {e}")
    
    def get_tag_category(self, tag: str) -> Optional[str]:
        """태그의 카테고리 반환"""
        if not self.is_available:
            return None
        
        # 먼저 원본 태그로 검색
        if tag in self.tag_to_category:
            return self.tag_to_category[tag]
        
        # 띄어쓰기를 언더바로 변환해서 검색 (기존 danbooru 폴더 형식용)
        normalized_tag = tag.replace(' ', '_')
        return self.tag_to_category.get(normalized_tag)
    
    def get_tags_in_category(self, category: str) -> List[str]:
        """특정 카테고리에 속하는 모든 태그 반환"""
        if not self.is_available:
            return []
        return self.category_to_tags.get(category, [])
    
    def get_category_short_name(self, category: str) -> str:
        """카테고리명을 짧게 줄여서 반환"""
        if not category:
            return "?"
        
        # :: 구분자로 나누어서 마지막 부분만 사용
        if "::" in category:
            short_name = category.split("::")[-1]
        else:
            short_name = category
        
        # 여전히 길면 앞의 몇 글자만 사용
        if len(short_name) > 8:
            return short_name[:8]
        return short_name
    
    def is_tag_available(self, tag: str) -> bool:
        """태그가 Danbooru 데이터베이스에 있는지 확인"""
        if not self.is_available:
            return False
        
        # 먼저 원본 태그로 검색
        if tag in self.tag_to_category:
            return True
        
        # 띄어쓰기를 언더바로 변환해서 검색 (기존 danbooru 폴더 형식용)
        normalized_tag = tag.replace(' ', '_')
        return normalized_tag in self.tag_to_category

# 전역 인스턴스
danbooru_module = DanbooruModule()

def get_danbooru_category(tag: str) -> Optional[str]:
    """태그의 Danbooru 카테고리 반환 (편의 함수)"""
    return danbooru_module.get_tag_category(tag)

def get_danbooru_category_short(tag: str) -> str:
    """태그의 Danbooru 카테고리 짧은 이름 반환 (편의 함수)"""
    category = danbooru_module.get_tag_category(tag)
    return danbooru_module.get_category_short_name(category)

def is_danbooru_available() -> bool:
    """Danbooru 모듈이 사용 가능한지 확인"""
    return danbooru_module.is_available
