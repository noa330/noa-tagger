# -*- coding: utf-8 -*-
"""
타임머신 공통 로그/트랜잭션 모듈

요구사항:
- 모든 모듈에서 매우 얇게 호출할 수 있어야 함
- 작업 단위를 트랜잭션으로 묶어(일괄/개별) 1개의 작업으로 인식되어야 함
- 타임머신 UI가 있을 경우만 기록(없어도 안전하게 no-op)

사용 예:
    from timemachine_log import TM
    with TM.transaction("miracle: batch rename", context={"source":"miracle_batch"}):
        TM.log_change({"type":"tag_rename", "image": path, "before": before, "after": after})

핵심 아이디어:
- 전역 싱글톤 TM
- begin/end/abort 트랜잭션 + context manager
- 내부 버퍼링 후 커밋할 때 1개의 작업으로 전달
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import threading
import time


class _TimeMachineLogger:
    """프로세스 전역 타임머신 로거(경량 API).

    - 다른 모듈에서는 이 클래스의 정적 인스턴스(TM)만 import하여 사용
    - 트랜잭션 경계 내에서 발생한 여러 변경을 하나의 작업으로 묶어 전달
    - 타임머신 수신기가 없으면 no-op
    """

    def __init__(self) -> None:
        self._local = threading.local()
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._all_logs: List[Dict[str, Any]] = []  # 모든 로그 저장

    # ── 구독 관리 ───────────────────────────────────────────────────────────
    def subscribe(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        if handler not in self._subscribers:
            self._subscribers.append(handler)

    def unsubscribe(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        try:
            self._subscribers.remove(handler)
        except ValueError:
            pass

    def _publish(self, record: Dict[str, Any]) -> None:
        # 모든 로그를 내부 저장소에 추가
        self._all_logs.append(record.copy())
        
        # 수신기가 없으면 조용히 종료(no-op)
        if not self._subscribers:
            print(f"[TM LOG] 구독자가 없음 - 로그 무시: {record.get('title', 'Unknown')}")
            return
        
        print(f"[TM LOG] {len(self._subscribers)}명의 구독자에게 로그 발행: {record.get('title', 'Unknown')}")
        for i, handler in enumerate(list(self._subscribers)):
            try:
                print(f"[TM LOG] 구독자 {i+1}에게 전달 중...")
                handler(record)
                print(f"[TM LOG] 구독자 {i+1} 전달 완료")
            except Exception as e:
                print(f"[TM LOG ERROR] 구독자 {i+1} 처리 실패: {e}")
                # 구독자 오류는 다른 구독자에게 전파하지 않음
                pass
    
    # ── 트랜잭션/로깅 API ──────────────────────────────────────────────────
    def transaction(self, title: str, context: Optional[Dict[str, Any]] = None):
        """컨텍스트 매니저: 트랜잭션 단위(한 작업)로 로그 묶기."""
        return _Transaction(self, title, context or {})

    def begin(self, title: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._ensure_tx_stack()
        tx = {
            "title": title,
            "context": dict(context or {}),
            "changes": [],
            "started_at": time.time(),
        }
        self._local._tm_tx_stack.append(tx)

    def log_change(self, change: Dict[str, Any]) -> None:
        """트랜잭션 내 변경 기록. 트랜잭션 없으면 암묵적으로 시작/즉시 커밋.

        change 예시:
            {"type": "tag_reorder", "image": path, "before": [...], "after": [...]} 
        """
        self._ensure_tx_stack()
        # 로그 표준화: 이미지 경로를 파일명으로 강제 변환
        try:
            change = self._sanitize_change(change)
        except Exception:
            pass
        if self._local._tm_tx_stack:
            self._local._tm_tx_stack[-1]["changes"].append(change)
            return

        # 암묵 트랜잭션: 단일 변경을 하나의 작업으로 래핑
        self.begin(title=change.get("type", "change"), context={"implicit": True})
        try:
            self._local._tm_tx_stack[-1]["changes"].append(change)
            self.commit()
        except Exception:
            self.abort()
            raise

    def commit(self) -> None:
        self._ensure_tx_stack()
        if not self._local._tm_tx_stack:
            return
        tx = self._local._tm_tx_stack.pop()
        record = {
            "title": tx["title"],
            "context": tx["context"],
            "changes": tx["changes"],
            "started_at": tx["started_at"],
            "ended_at": time.time(),
        }
        # 빈 변경이면 버림
        if record["changes"]:
            self._publish(record)

    def abort(self) -> None:
        self._ensure_tx_stack()
        if not self._local._tm_tx_stack:
            return
        self._local._tm_tx_stack.pop()

    def _ensure_tx_stack(self) -> None:
        if not hasattr(self._local, "_tm_tx_stack"):
            self._local._tm_tx_stack = []

    def _sanitize_change(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """변경 레코드 표준화.
        - image 키: 전체 경로 -> 파일명
        - images 리스트: 각 요소 파일명화
        """
        out = dict(change)
        try:
            if "image" in out and isinstance(out["image"], (str, Path)):
                out["image"] = Path(str(out["image"])) .name
        except Exception:
            pass
        try:
            if "images" in out and isinstance(out["images"], list):
                out["images"] = [Path(str(p)).name if isinstance(p, (str, Path)) else p for p in out["images"]]
        except Exception:
            pass
        return out
    
    # ── 데이터베이스 저장/복원 API ──────────────────────────────────────────────
    def get_all_logs(self) -> List[Dict[str, Any]]:
        """모든 로그 반환 (데이터베이스 저장용)"""
        return self._all_logs.copy()
    
    def restore_logs(self, logs: List[Dict[str, Any]]) -> None:
        """로그 복원 (데이터베이스 불러오기용)"""
        self._all_logs = logs.copy()
        print(f"[TM LOG] {len(logs)}개의 로그가 복원되었습니다.")
    
    def clear_logs(self) -> None:
        """모든 로그 삭제"""
        self._all_logs.clear()
        print("[TM LOG] 모든 로그가 삭제되었습니다.")


class _Transaction:
    """with TM.transaction(...) as tx: 지원용 컨텍스트 매니저"""

    def __init__(self, logger: _TimeMachineLogger, title: str, context: Dict[str, Any]):
        self._logger = logger
        self._title = title
        self._context = context

    def __enter__(self):
        self._logger.begin(self._title, self._context)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self._logger.commit()
            return False
        self._logger.abort()
        return False


# 전역 싱글톤 인스턴스
TM = _TimeMachineLogger()


# ── AI 배치 태깅 공통 함수 ──────────────────────────────────────────────────
def log_ai_batch_tagging(model_name: str, model_id: str, image_paths: list, tag_results: list):
    """AI 배치 태깅 결과를 타임머신에 기록하는 공통 함수
    
    Args:
        model_name: 모델명 (예: "WD Tagger", "LLaVA-NeXT")
        model_id: 모델 ID
        image_paths: 이미지 경로 리스트
        tag_results: 각 이미지별 태그 결과 리스트 [(tag, score), ...]
    """
    try:
        total = len(image_paths)
        if total > 1:
            # 배치 작업을 하나의 트랜잭션으로 묶기
            TM.begin("ai_batch_tagging", context={
                "model": model_name,
                "model_id": model_id,
                "num_images": total
            })
            
            # 각 이미지별 태그 결과 기록
            for i, (image_path, tags) in enumerate(zip(image_paths, tag_results)):
                TM.log_change({
                    "type": "ai_tag_generated",
                    "image": Path(str(image_path)).name,
                    "tags": [tag for tag, score in tags],
                    "model": model_name,
                    "model_id": model_id,
                    "scores": {tag: score for tag, score in tags}
                })
            
            # 트랜잭션 커밋
            TM.commit()
        else:
            # 단일 이미지 처리
            if image_paths and tag_results:
                TM.log_change({
                    "type": "ai_tag_generated",
                    "image": Path(str(image_paths[0])).name,
                    "tags": [tag for tag, score in tag_results[0]],
                    "model": model_name,
                    "model_id": model_id,
                    "scores": {tag: score for tag, score in tag_results[0]}
                })
    except Exception:
        # 타임머신 로그 실패해도 태깅 작업은 계속 진행
        pass


def log_ai_single_tagging(model_name: str, model_id: str, image_path: str, tags: list):
    """AI 단일 이미지 태깅 결과를 타임머신에 기록하는 공통 함수
    
    Args:
        model_name: 모델명
        model_id: 모델 ID
        image_path: 이미지 경로
        tags: 태그 결과 리스트 [(tag, score), ...]
    """
    try:
        TM.log_change({
            "type": "ai_tag_generated",
            "image": Path(str(image_path)).name,
            "tags": [tag for tag, score in tags],
            "model": model_name,
            "model_id": model_id,
            "scores": {tag: score for tag, score in tags}
        })
    except Exception:
        pass


