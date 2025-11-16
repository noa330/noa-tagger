"""
CLIP ViT-B/32 토크나이저 플러그인
- 토크나이저를 지연 로딩하고, 태그 목록의 전체 토큰 수를 계산
"""

from typing import List, Optional
from pathlib import Path

_tokenizer = None
_tokenizer_dir: Optional[str] = None  # 로컬 토크나이저 디렉터리 (설정 가능)


def configure_clip_tokenizer_dir(directory: Optional[str]) -> None:
    """로컬 토크나이저 디렉터리를 지정한다. None이면 기본 경로(모듈 옆 'tokenizer') 사용.
    지정된 경로가 비어있으면 자동 다운로드 후 저장한다.
    """
    global _tokenizer_dir, _tokenizer
    _tokenizer_dir = directory
    _tokenizer = None  # 경로 변경 시 재로딩


def _expected_dir() -> Path:
    base = Path(__file__).parent
    return base / "tokenizer" / "openai-clip-vit-base-patch32"


def _get_clip_tokenizer():
    """openai/clip-vit-base-patch32 토크나이저를 로드.
    - 우선 모듈 경로 하위 'tokenizer/openai-clip-vit-base-patch32'에서 로드
    - 없으면 네트워크로 다운로드 후 해당 경로에 저장
    - 사용자가 configure_clip_tokenizer_dir 로 경로 지정 시 그 경로 우선
    transformers 미설치/로드 실패 시 None 반환.
    """
    global _tokenizer
    if _tokenizer is not None:
        return _tokenizer
    try:
        from transformers import AutoTokenizer
    except Exception:
        return None

    # 1) 우선 경로 결정
    target_dir = Path(_tokenizer_dir) if _tokenizer_dir else _expected_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # 2) 우선 로컬 시도
    try:
        _tokenizer = AutoTokenizer.from_pretrained(str(target_dir), local_files_only=True)
        return _tokenizer
    except Exception:
        _tokenizer = None

    # 3) 로컬에 없으면 다운로드 후 저장
    try:
        tmp = AutoTokenizer.from_pretrained("openai/clip-vit-base-patch32")
        # 지정 디렉터리에 저장 (다음 로드부터는 로컬 사용)
        try:
            tmp.save_pretrained(str(target_dir))
        except Exception:
            pass
        _tokenizer = tmp
        return _tokenizer
    except Exception:
        return None


def count_clip_tokens_for_tags(tags: List[str]) -> Optional[int]:
    """태그 리스트를 ", " 로 이어 CLIP 토큰 수를 계산하여 반환.
    transformers 가 없거나 로드 실패 시 None.
    """
    if not tags:
        return 0
    tok = _get_clip_tokenizer()
    if tok is None:
        return None
    text = ", ".join(tags)
    try:
        encoded = tok(text, add_special_tokens=True, return_attention_mask=False, return_token_type_ids=False)
        ids = encoded.get("input_ids", [])
        return len(ids)
    except Exception:
        return None


