"""
간단한 와일드카드 매칭 유틸리티 (선택적 플러그인)

지원 문법:
- *  : 0개 이상의 아무 문자 (greedy)
- ?  : 정확히 1개의 문자
- [ ]: 지정 문자 중 하나 (문자 클래스)
- { }: 여러 단어 패턴 중 하나 (쉼표로 구분)
- ^/$: 문자열 시작/끝 앵커 (정규식과 동일 의미)

대소문자 구분 없이 매칭합니다.
"""

from __future__ import annotations

import re
from typing import Iterable, List


_WILDCARD_SIGNS = set(["*", "?", "[", "]", "{", "}", "^", "$"])


def is_wildcard(pattern: str) -> bool:
    """패턴에 와일드카드 기호가 포함되어 있는지 여부"""
    if not pattern:
        return False
    return any(ch in pattern for ch in _WILDCARD_SIGNS)


def _compile_wildcard_to_regex(pattern: str) -> re.Pattern:
    """와일드카드 패턴을 정규식으로 컴파일 (대소문자 무시).

    규칙:
    - '*' -> '.*'
    - '?' -> '.'
    - '[...]' -> 문자 클래스 그대로 사용 (내부는 사용자가 책임)
    - '{a,b,c}' -> '(?:a|b|c)'
    - '^', '$' -> 그대로 앵커 처리
    - 그 외 문자는 re.escape로 이스케이프
    """
    i = 0
    n = len(pattern)
    regex_parts: List[str] = []

    while i < n:
        ch = pattern[i]
        if ch == '*':
            regex_parts.append('.*')
            i += 1
        elif ch == '?':
            regex_parts.append('.')
            i += 1
        elif ch == '[':
            # 문자 클래스 끝 ']'까지 그대로 복사 (간단 처리)
            end = pattern.find(']', i + 1)
            if end == -1:
                # 잘못된 경우는 리터럴로 처리
                regex_parts.append(re.escape(ch))
                i += 1
            else:
                regex_parts.append(pattern[i:end+1])
                i = end + 1
        elif ch == '{':
            # {a,b,c} -> (?:a|b|c)
            end = pattern.find('}', i + 1)
            if end == -1:
                regex_parts.append(re.escape(ch))
                i += 1
            else:
                inner = pattern[i+1:end]
                alts = [re.escape(p.strip()) for p in inner.split(',') if p.strip()]
                if alts:
                    regex_parts.append('(?:' + '|'.join(alts) + ')')
                else:
                    regex_parts.append(re.escape(pattern[i:end+1]))
                i = end + 1
        elif ch in ('^', '$'):
            # 앵커는 그대로 사용
            regex_parts.append(ch)
            i += 1
        else:
            regex_parts.append(re.escape(ch))
            i += 1

    regex_str = ''.join(regex_parts)
    return re.compile(regex_str, flags=re.IGNORECASE)


def matches(text: str, pattern: str) -> bool:
    """텍스트가 와일드카드 패턴과 매칭되는지 여부"""
    if text is None or pattern is None:
        return False
    rx = _compile_wildcard_to_regex(pattern)
    return rx.search(text) is not None


def filter_list(items: Iterable[str], pattern: str) -> List[str]:
    """리스트에서 와일드카드 패턴에 매칭되는 항목만 반환"""
    rx = _compile_wildcard_to_regex(pattern)
    return [it for it in items if rx.search(it or '')]


# ---------- High-level helpers (for minimal hooks) ----------
def match_or_contains(text: str, query: str) -> bool:
    """코어 모듈에서 한 줄로 쓰기 위한 매칭 헬퍼.
    - query에 와일드카드 문자가 있으면 와일드카드 매칭
    - 없으면 단순 부분 문자열 포함(in)
    모두 대소문자 무시
    """
    if text is None or query is None:
        return False
    t = text.lower()
    q = query.strip()
    if not q:
        return False

    # 앵커 감지 (외곽의 ^, $만 처리)
    anchor_start = q.startswith('^')
    anchor_end = q.endswith('$')
    if anchor_start:
        q = q[1:]
    if anchor_end and len(q) > 0:
        q = q[:-1]

    # 따옴표로 감싸인 경우는 리터럴로 처리
    is_quoted = len(q) >= 2 and q[0] == '"' and q[-1] == '"'
    if is_quoted:
        inner = q[1:-1]
        # 리터럴은 정규식 이스케이프 후 앵커 적용
        pat = re.escape(inner)
        if anchor_start:
            pat = '^' + pat
        if anchor_end:
            pat = pat + '$'
        rx = re.compile(pat, flags=re.IGNORECASE)
        return rx.search(t) is not None

    # 비인용: 와일드카드/문자클래스/중괄호/앵커 지원
    q_low = q.lower()
    # 와일드카드가 포함되면 변환, 없으면 단순 포함
    if is_wildcard(q_low) or anchor_start or anchor_end:
        # 내부를 와일드카드 규칙으로 컴파일한 뒤 앵커 추가
        # _compile_wildcard_to_regex는 앵커를 그대로 두므로, q에 남은 ^/$도 포함 가능
        # 이미 여기서 외곽 앵커는 제거했으므로 직접 붙인다
        # 내부를 정규식 문자열로 만들기 위해 동일 로직 재사용
        # 구현 단순화를 위해: 내부를 변환하여 패턴 문자열을 얻기 위해 임시 컴파일 후 pattern 추출 대신 직접 변환 함수를 사용
        # 아래는 내부 변환을 다시 구현하지 않고 search에 맡김: '^'/'$'는 이미 제거했으므로 직접 붙여줌
        rx_inner = _compile_wildcard_to_regex(q_low)
        pat = rx_inner.pattern
        if anchor_start:
            pat = '^' + pat
        if anchor_end:
            pat = pat + '$'
        rx = re.compile(pat, flags=re.IGNORECASE)
        return rx.search(t) is not None
    else:
        return q_low in t


def expand_tag_patterns(patterns: Iterable[str], all_known_tags: Iterable[str]) -> List[str]:
    """쉼표 분리된 패턴 리스트를 실제 태그 목록으로 확장.
    - 각 패턴에 와일드카드가 있으면 all_known_tags에서 필터링
    - 없으면 리터럴로 사용
    - 출력은 중복 제거 + 원래 순서 보존
    """
    all_list = list(all_known_tags)
    result: List[str] = []
    seen = set()
    for pat in patterns:
        if not pat:
            continue
        if is_wildcard(pat):
            for hit in filter_list(all_list, pat):
                if hit not in seen:
                    seen.add(hit)
                    result.append(hit)
        else:
            if pat not in seen:
                seen.add(pat)
                result.append(pat)
    return result


def expand_tag_patterns_advanced(patterns: Iterable[str], all_known_tags: Iterable[str]) -> List[str]:
    """따옴표와 앵커(^/$)를 지원하는 확장 버전.
    - 토큰 외곽의 ^, $는 시작/끝을 의미
    - 토큰이 "로 감싸인 경우 내부는 리터럴(특수기호 무시)
    - 그 외는 기존 와일드카드 규칙
    """
    result: List[str] = []
    seen = set()
    tag_list = list(all_known_tags)
    for raw in patterns:
        if not raw:
            continue
        token = raw.strip()
        if not token:
            continue
        anchor_start = token.startswith('^')
        anchor_end = token.endswith('$')
        if anchor_start:
            token = token[1:]
        if anchor_end and len(token) > 0:
            token = token[:-1]

        # 인용 리터럴?
        is_quoted = len(token) >= 2 and token[0] == '"' and token[-1] == '"'
        if is_quoted:
            inner = token[1:-1]
            pat = re.escape(inner)
            if anchor_start:
                pat = '^' + pat
            if anchor_end:
                pat = pat + '$'
            rx = re.compile(pat, flags=re.IGNORECASE)
        else:
            # 비인용: 와일드카드/문자클래스/중괄호 처리 후 앵커 적용
            rx_inner = _compile_wildcard_to_regex(token)
            pat = rx_inner.pattern
            if anchor_start:
                pat = '^' + pat
            if anchor_end:
                pat = pat + '$'
            rx = re.compile(pat, flags=re.IGNORECASE)

        for tag in tag_list:
            if rx.search(tag or '') and tag not in seen:
                seen.add(tag)
                result.append(tag)
    return result


