#!/usr/bin/env python3
"""
KR_danbooru_tags.csv 파일을 로드하고 관리하는 모듈
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

class KRDanbooruTag:
    """한국어 Danbooru 태그 정보를 담는 클래스"""
    
    def __init__(self, name: str, count: int, category: str, description: str, keywords: List[str]):
        self.name = name
        self.count = count
        self.category = category
        self.description = description
        self.keywords = keywords
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"KRDanbooruTag(name='{self.name}', count={self.count}, category='{self.category}')"

class KRDanbooruLoader:
    """KR_danbooru_tags.csv 파일을 로드하고 관리하는 클래스"""
    
    def __init__(self, csv_path: str = "KR_danbooru_tags.csv"):
        self.csv_path = Path(csv_path)
        self.tags: Dict[str, KRDanbooruTag] = {}
        self.category_to_tags: Dict[str, List[str]] = defaultdict(list)
        self.is_available = False
        
        if self.csv_path.exists():
            self._load_tags()
    
    def _load_tags(self):
        """CSV 파일에서 태그 정보 로드 (실제 형식: name,0,count,description)"""
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                line_count = 0
                for row in reader:
                    line_count += 1
                    if len(row) < 4:
                        continue
                    
                    name = row[0].strip()
                    if not name:
                        continue
                    
                    # 카운트 파싱 (세 번째 컬럼이 실제 카운트)
                    try:
                        count = int(row[2].replace(',', ''))
                    except (ValueError, IndexError):
                        count = 0
                    
                    # 설명 (네 번째 컬럼)
                    description = row[3].strip()
                    category = self._parse_category_from_description(description)
                    
                    # 키워드 파싱
                    keywords = self._parse_keywords(description)
                    
                    # 태그 객체 생성
                    tag_obj = KRDanbooruTag(name, count, category, description, keywords)
                    self.tags[name] = tag_obj
                    self.category_to_tags[category].append(name)
                
                self.is_available = True
                print(f"KR_danbooru_tags.csv 로드 완료: {len(self.tags)}개 태그 (총 {line_count}줄 처리)")
                
        except Exception as e:
            print(f"KR_danbooru_tags.csv 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            self.is_available = False
    
    def _parse_category_from_description(self, description: str) -> str:
        """설명에서 [패션 > 헤어컬러] 형식의 카테고리 추출 (전체 카테고리 사용)"""
        if not description:
            return "UNKNOWN"
        
        # [패션 > 헤어컬러] 형식 찾기
        import re
        match = re.search(r'\[([^\]]+)\]', description)
        if match:
            category_full = match.group(1).strip()
            # 전체 카테고리 사용 (패션 > 헤어컬러 -> 패션 > 헤어컬러)
            return category_full
        
        return "UNKNOWN"
    
    def _parse_keywords(self, description: str) -> List[str]:
        """설명 문자열에서 키워드를 파싱하여 리스트로 변환"""
        if not description:
            return []
        
        keywords = []
        
        # "키워드: <키워드1>, <키워드2>" 형식에서 키워드 추출
        import re
        keyword_matches = re.findall(r'<([^>]+)>', description)
        keywords.extend(keyword_matches)
        
        # "키워드:" 뒤의 쉼표로 구분된 키워드들도 추가
        if '키워드:' in description:
            keywords_part = description.split('키워드:')[1].strip()
            comma_keywords = [kw.strip() for kw in keywords_part.split(',') if kw.strip() and not kw.strip().startswith('<')]
            keywords.extend(comma_keywords)
        
        return keywords
    
    def get_tag(self, name: str) -> Optional[KRDanbooruTag]:
        """태그명으로 태그 객체 반환"""
        return self.tags.get(name)
    
    def get_tag_category(self, name: str) -> str:
        """태그의 카테고리 반환"""
        tag = self.get_tag(name)
        return tag.category if tag else "UNKNOWN"
    
    def get_tags_in_category(self, category: str) -> List[str]:
        """특정 카테고리에 속하는 모든 태그 반환"""
        return self.category_to_tags.get(category, [])
    
    def search_tags(self, query: str, limit: int = None) -> List[Tuple[str, int, str]]:
        """
        검색 쿼리에 맞는 태그들을 우선순위별로 반환
        반환: [(태그명, 우선순위, 매칭타입), ...]
        우선순위: 0=태그명일치, 1=키워드일치, 2=카테고리일치, 3=설명일치
        limit: 최대 반환 개수 (None이면 전체 반환)
        """
        if not query.strip():
            return []
        
        query_lower = query.lower()
        results = []
        
        for name, tag in self.tags.items():
            priority = None
            match_type = ""
            
            # 1. 태그명 일치 (가장 높은 우선순위)
            if query_lower in name.lower():
                if name.lower().startswith(query_lower):
                    priority = 0  # 시작 일치
                    match_type = "tag_start"
                else:
                    priority = 0  # 포함 일치
                    match_type = "tag_contains"
            
            # 2. 키워드 일치
            if priority is None and any(query_lower in kw.lower() for kw in tag.keywords):
                priority = 1
                match_type = "keyword"
            
            # 3. 카테고리 일치
            if priority is None and query_lower in tag.category.lower():
                priority = 2
                match_type = "category"
            
            # 4. 설명 일치
            if priority is None and query_lower in tag.description.lower():
                priority = 3
                match_type = "description"
            
            if priority is not None:
                # 카운트도 함께 저장 (우선순위, 카운트, 태그명)
                count = tag.count
                results.append((name, priority, match_type, count))
        
        # 우선순위별로 정렬, 같은 우선순위면 카운트 높은 순
        results.sort(key=lambda x: (x[1], -x[3], x[0]))
        
        # limit이 설정되어 있으면 상위 limit개만 반환
        if limit is not None:
            results = results[:limit]
        
        # 카운트 제거하고 반환
        return [(name, priority, match_type) for name, priority, match_type, _ in results]
    
    def get_autocomplete_list(self, query: str = "", limit: int = None) -> List[str]:
        """
        자동완성용 태그 목록 반환 (카운트 높은 순)
        limit: 최대 반환 개수 (None이면 전체 반환)
        """
        if not query.strip():
            # 쿼리가 없으면 모든 태그를 카운트 순으로 정렬 (높은 순)
            all_tags = [(name, tag.count) for name, tag in self.tags.items()]
            all_tags.sort(key=lambda x: x[1], reverse=True)  # 카운트 높은 순
            # limit이 설정되어 있으면 상위 limit개만 반환
            if limit is not None:
                return [name for name, _ in all_tags[:limit]]
            return [name for name, _ in all_tags]
        
        # 검색 결과를 태그명만 반환 (검색 결과는 이미 우선순위로 정렬됨)
        search_results = self.search_tags(query, limit=limit)
        return [name for name, _, _ in search_results]
    
    def get_tag_display_info(self, name: str) -> Dict[str, str]:
        """
        태그의 표시 정보 반환 (자동완성용)
        카테고리는 태그 옆에 표시하고, 키워드는 줄바꿈하여 표시
        """
        tag = self.get_tag(name)
        if not tag:
            return {
                "name": name,
                "title": name,
                "description": "",
                "keywords": ""
            }
        
        # description에서 "키워드:" 이후 부분 추출
        keywords_text = ""
        clean_description = tag.description
        
        if '키워드:' in tag.description:
            parts = tag.description.split('키워드:', 1)
            clean_description = parts[0].strip()
            keywords_text = parts[1].strip()
        
        # clean_description에서 [카테고리] 부분 제거
        import re
        clean_description = re.sub(r'^\[([^\]]+)\]\s*', '', clean_description)
        
        return {
            "name": name,
            "title": f"{name} [{tag.category}]",  # 태그명과 카테고리를 한 줄에
            "description": clean_description,  # 카테고리 제거된 설명
            "keywords": keywords_text,  # "키워드:" 뒤 원본 문자열 그대로
            "count": str(tag.count)
        }

# 전역 인스턴스
kr_danbooru_loader = KRDanbooruLoader()
