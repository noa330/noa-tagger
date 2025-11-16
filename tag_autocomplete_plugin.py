"""
태그 자동완성 플러그인
이미지 태깅 모듈과 태그 스타일시트 에디터에서 공통으로 사용하는 자동완성 기능
"""

from PySide6.QtWidgets import QCompleter, QStyledItemDelegate
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QStyle

# 전역 캐시
_cached_tag_list = None
_cache_loaded = False


def load_tag_list():
    """자동완성용 태그 목록을 로드 (KR_danbooru_tags.csv 사용) - 캐싱 적용"""
    global _cached_tag_list, _cache_loaded
    
    # 캐시가 있으면 즉시 반환
    if _cache_loaded and _cached_tag_list is not None:
        return _cached_tag_list
    
    try:
        from kr_danbooru_loader import kr_danbooru_loader
        
        print(f"로더 상태: is_available={kr_danbooru_loader.is_available}, 태그 수={len(kr_danbooru_loader.tags)}")
        
        if kr_danbooru_loader.is_available:
            # 최적화: 처음에는 상위 1000개만 로드 (빠른 초기 로딩)
            tag_list = kr_danbooru_loader.get_autocomplete_list(limit=1000)
            print(f"KR_danbooru_tags.csv 로드 완료: {len(tag_list)}개 태그 (상위 1000개)")
            
            # 캐시에 저장
            _cached_tag_list = tag_list
            _cache_loaded = True
            
            return tag_list
        else:
            print("KR_danbooru_tags.csv 파일을 찾을 수 없거나 로드 실패")
            return []
    except Exception as e:
        print(f"load_tag_list 오류: {e}")
        import traceback
        traceback.print_exc()
        return []


def load_full_tag_list():
    """전체 태그 목록을 로드 (검색 시 사용) - 필요할 때만 호출"""
    global _cached_tag_list, _cache_loaded
    
    try:
        from kr_danbooru_loader import kr_danbooru_loader
        
        if kr_danbooru_loader.is_available:
            # 전체 태그 목록 로드
            full_tag_list = kr_danbooru_loader.get_autocomplete_list()
            print(f"전체 태그 목록 로드 완료: {len(full_tag_list)}개 태그")
            return full_tag_list
        else:
            return []
    except Exception as e:
        print(f"load_full_tag_list 오류: {e}")
        return []


def clear_tag_cache():
    """태그 캐시 초기화 (메모리 절약용)"""
    global _cached_tag_list, _cache_loaded
    _cached_tag_list = None
    _cache_loaded = False


class KRDanbooruCompleterDelegate(QStyledItemDelegate):
    """KR_danbooru_tags.csv 기반 자동완성용 커스텀 델리게이트"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        from kr_danbooru_loader import kr_danbooru_loader
        self.kr_loader = kr_danbooru_loader
    
    def paint(self, painter, option, index):
        """커스텀 그리기"""
        # 태그명 가져오기
        tag_name = index.data(Qt.DisplayRole)
        if not tag_name:
            super().paint(painter, option, index)
            return
        
        # "더 보기" 항목은 특별하게 처리
        if tag_name.startswith("---"):
            # 배경 그리기
            from PySide6.QtGui import QColor
            bg_color = QColor(50, 50, 70, 100)
            painter.fillRect(option.rect, bg_color)
            
            # 텍스트 그리기 (중앙 정렬, 회색)
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(option.font)
            painter.drawText(option.rect, Qt.AlignCenter, tag_name)
            return
        
        if not self.kr_loader.is_available:
            super().paint(painter, option, index)
            return
        
        # 태그 정보 가져오기
        tag_info = self.kr_loader.get_tag_display_info(tag_name)
        
        # 배경 그리기 (선택됨 또는 호버)
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        elif option.state & QStyle.State_MouseOver:
            # 마우스 오버 시 하얀빛 효과
            from PySide6.QtGui import QColor
            hover_color = QColor(255, 255, 255, 30)  # 반투명 흰색
            painter.fillRect(option.rect, hover_color)
            painter.setPen(option.palette.text().color())
        else:
            painter.setPen(option.palette.text().color())
        
        # 텍스트 그리기
        painter.setFont(option.font)
        
        # 태그명 [카테고리] (굵게)
        bold_font = QFont(option.font)
        bold_font.setBold(True)
        painter.setFont(bold_font)
        
        tag_rect = option.rect.adjusted(8, 4, -8, -4)
        title = tag_info.get('title', tag_name)
        painter.drawText(tag_rect, Qt.AlignLeft | Qt.AlignTop, title)
        
        # count 숫자 (오른쪽 정렬, 괄호 안에)
        count = tag_info.get('count', '0')
        count_text = f"({count})"
        painter.drawText(tag_rect, Qt.AlignRight | Qt.AlignTop, count_text)
        
        # 설명 (작은 글씨)
        small_font = QFont(option.font)
        current_size = small_font.pointSize()
        if current_size > 1:
            small_font.setPointSize(max(1, current_size - 1))
        painter.setFont(small_font)
        
        # 설명 텍스트 준비 (자동 줄바꿈)
        description = tag_info.get('description', '')
        current_y = 18  # 태그명 다음부터 시작
        
        if description:
            description_text = f"설명: {description}"
            # 줄바꿈 없이 그리기 (boundingRect로 필요한 높이 계산)
            desc_rect = tag_rect.adjusted(0, current_y, 0, 0)
            from PySide6.QtGui import QFontMetrics
            fm = QFontMetrics(small_font)
            # 사용 가능한 폭 계산 (패딩 제외)
            available_width = tag_rect.width()
            # 텍스트를 여러 줄로 그리기
            bounding_rect = fm.boundingRect(desc_rect.x(), desc_rect.y(), 
                                          available_width, 1000,  # 충분한 높이
                                          Qt.AlignLeft | Qt.TextWordWrap, 
                                          description_text)
            painter.drawText(desc_rect.x(), desc_rect.y(), 
                           available_width, bounding_rect.height(),
                           Qt.AlignLeft | Qt.TextWordWrap, 
                           description_text)
            current_y += bounding_rect.height() + 2  # 다음 항목을 위해 간격 추가
        
        # 키워드 그리기 (자동 줄바꿈)
        keywords = tag_info.get('keywords', '')
        if keywords:
            keywords_text = f"키워드: {keywords}"
            keyword_rect = tag_rect.adjusted(0, current_y, 0, 0)
            from PySide6.QtGui import QFontMetrics
            fm = QFontMetrics(small_font)
            available_width = tag_rect.width()
            bounding_rect = fm.boundingRect(keyword_rect.x(), keyword_rect.y(), 
                                          available_width, 1000,
                                          Qt.AlignLeft | Qt.TextWordWrap, 
                                          keywords_text)
            painter.drawText(keyword_rect.x(), keyword_rect.y(), 
                           available_width, bounding_rect.height(),
                           Qt.AlignLeft | Qt.TextWordWrap, 
                           keywords_text)
    
    def sizeHint(self, option, index):
        """아이템 크기 조정 (텍스트 길이에 따라 동적으로 높이 계산)"""
        tag_name = index.data(Qt.DisplayRole)
        
        # "더 보기" 항목은 높이를 작게
        if tag_name and tag_name.startswith("---"):
            return QSize(option.rect.width(), 30)
        
        if not self.kr_loader.is_available:
            return QSize(option.rect.width(), 60)
        
        # 태그 정보 가져오기
        tag_info = self.kr_loader.get_tag_display_info(tag_name)
        
        # 폰트 설정
        small_font = QFont(option.font)
        current_size = small_font.pointSize()
        if current_size > 1:
            small_font.setPointSize(max(1, current_size - 1))
        
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(small_font)
        
        # 사용 가능한 폭 (패딩 제외: 좌우 8px씩)
        # 실제 아이템 폭에서 패딩 제외 (고정 폭이 아닌 동적 계산)
        available_width = max(option.rect.width() - 16, 300)  # 최소 300px 보장
        
        # 기본 높이 (태그명 줄 + 상하 패딩)
        total_height = 18 + 8  # 태그명 18px + 상단 패딩 4px + 하단 여백
        
        # 설명 높이 계산
        description = tag_info.get('description', '')
        if description:
            description_text = f"설명: {description}"
            desc_rect = fm.boundingRect(0, 0, available_width, 1000,
                                       Qt.AlignLeft | Qt.TextWordWrap,
                                       description_text)
            total_height += desc_rect.height() + 2
        
        # 키워드 높이 계산
        keywords = tag_info.get('keywords', '')
        if keywords:
            keywords_text = f"키워드: {keywords}"
            keyword_rect = fm.boundingRect(0, 0, available_width, 1000,
                                          Qt.AlignLeft | Qt.TextWordWrap,
                                          keywords_text)
            total_height += keyword_rect.height() + 2
        
        # 최소 높이 보장
        total_height = max(total_height, 60)
        
        return QSize(option.rect.width(), total_height)
