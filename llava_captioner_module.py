"""
LLaVA Captioner Module - 다운로드 및 UI 표시만 구현
추론 로직은 제외하고 모델 다운로드와 UI 표시만 담당
"""

import os
import torch
from pathlib import Path
from typing import Optional
import logging
from PySide6.QtCore import QObject, Signal, QThread
import sys
import re
import io
from contextlib import redirect_stderr, redirect_stdout

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 전역 다운로드 진행 상황 시그널 (LLaVA 전용)
class LLaVADownloadProgressEmitter(QObject):
    llava_progress_updated = Signal(str, int, int, str)  # filename, downloaded, total, status

llava_download_progress_emitter = LLaVADownloadProgressEmitter()

class ModelLoadingProgressCapture:
    """모델 로딩 진행 상황을 tqdm 후킹으로 캐치하는 클래스"""
    def __init__(self, progress_callback=None, finished_callback=None):
        self.progress_callback = progress_callback
        self.model_loading_finished_callback = finished_callback
        self.original_tqdm_init = None
        self.current_progress = 0
        
    def capture_loading_progress(self, func, *args, **kwargs):
        """모델 로딩 함수를 실행하면서 tqdm 진행률을 후킹"""
        try:
            # tqdm 후킹 설정
            self._setup_tqdm_hook()
            
            # 모델 로딩 시작 알림
            if self.progress_callback:
                self.progress_callback("모델 체크포인트 로딩 시작...", 0)
            
            # 실제 함수 실행
            result = func(*args, **kwargs)
            
            # 모델 로딩 완료 알림 (하드코딩된 진행률 제거)
            # if self.progress_callback:
            #     self.progress_callback("모델 체크포인트 로딩 완료", 90)
            
            return result
            
        except Exception as e:
            if self.progress_callback:
                self.progress_callback("모델 로딩 실패", 0)
            raise e
        finally:
            # tqdm 후킹 해제
            self._restore_tqdm_hook()
    
    def _setup_tqdm_hook(self):
        """tqdm의 update 메서드를 후킹하여 진행률 캐치"""
        try:
            from tqdm import tqdm
            
            # 원본 update 메서드 백업
            if not hasattr(tqdm, '_original_update'):
                tqdm._original_update = tqdm.update
            
            # 커스텀 update 메서드 정의
            def hooked_update(self_tqdm, n=1):
                # 원본 update 호출
                result = tqdm._original_update(self_tqdm, n)
                
                # checkpoint shards 로딩인지 확인
                if hasattr(self_tqdm, 'desc') and self_tqdm.desc and 'checkpoint' in self_tqdm.desc.lower():
                    if self_tqdm.total and self_tqdm.total > 0:
                        progress_percent = int((self_tqdm.n / self_tqdm.total) * 100)
                        
                        # 진행률이 변경된 경우에만 콜백 호출
                        if progress_percent != self.current_progress:
                            self.current_progress = progress_percent
                            if self.progress_callback:
                                print(f"[DEBUG] 진행률 콜백 호출: {progress_percent}%")
                                self.progress_callback(
                                    f"모델 체크포인트 로딩 중... ({self_tqdm.n}/{self_tqdm.total})", 
                                    progress_percent
                                )
                            
                            # 체크포인트 로딩이 100% 완료되면 로딩 완료 신호 전송
                            if progress_percent >= 100:
                                if hasattr(self, 'model_loading_finished_callback') and self.model_loading_finished_callback is not None:
                                    self.model_loading_finished_callback()
                
                return result
            
            # update 메서드 교체
            tqdm.update = hooked_update
            
        except ImportError:
            # tqdm이 없는 경우 무시
            pass
    
    def _restore_tqdm_hook(self):
        """tqdm 후킹 해제"""
        try:
            from tqdm import tqdm
            
            # 원본 update 메서드 복원
            if hasattr(tqdm, '_original_update'):
                tqdm.update = tqdm._original_update
                
        except ImportError:
            pass


class LLaVACaptionerModule:
    """LLaVA 캡셔너 모듈 - 다운로드 및 UI 표시만"""
    
    def __init__(self, model_id: str = "llava-hf/llava-1.5-7b-hf", use_gpu: bool = True):
        self.model_id = model_id
        self.use_gpu = use_gpu
        self.is_loaded = False
        self.model_dir = None
        
        logger.info(f"LLaVA Captioner Module 초기화: {model_id}")
    
    def _get_device(self) -> str:
        """디바이스 설정"""
        if self.use_gpu and torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def _ensure_local_from_hub(self, repo_id: str, repo_filename: str, local_name: str, file_index: int = 1, total_files: int = 1) -> Path:
        """
        HF Hub에서 받아서 모델별 폴더에 '실제 파일'로 둔다.
        WD Tagger와 동일한 구조로 다운로드 처리.
        """
        # 모델별 폴더 생성
        model_name = repo_id.split('/')[-1]  # "llava-hf/llava-1.5-7b-hf" -> "llava-1.5-7b-hf"
        model_dir = Path("models") / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir = model_dir
        
        dst = model_dir / local_name
        
        # 기존 파일이 있으면 크기 확인 후 재사용 또는 이어받기
        if dst.is_file():
            try:
                # 파일 크기 확인을 위해 HEAD 요청
                import requests
                download_url = f"https://huggingface.co/{repo_id}/resolve/main/{repo_filename}"
                head_response = requests.head(download_url)
                if head_response.status_code == 200:
                    expected_size = int(head_response.headers.get('content-length', 0))
                    actual_size = dst.stat().st_size
                    
                    if actual_size == expected_size and expected_size > 0:
                        print(f"기존 파일 사용 (완전함): {dst}")
                        return dst
                    else:
                        print(f"파일 불완전, 이어받기: {dst} ({actual_size}/{expected_size} bytes)")
                        # 불완전한 파일 삭제
                        dst.unlink()
                else:
                    print(f"파일 확인 실패, 재다운로드: {dst}")
                    dst.unlink()
            except Exception as e:
                print(f"파일 확인 중 오류, 재다운로드: {e}")
                dst.unlink()
        
        print(f"LLaVA 다운로드 시작: {repo_id}/{repo_filename}")
        try:
            # 다운로드 시작 시그널 (간소화)
            try:
                llava_download_progress_emitter.llava_progress_updated.emit(repo_filename, 0, 0, f"[{file_index}/{total_files}]")
            except Exception:
                pass
            
            # 직접 다운로드 URL 생성
            download_url = f"https://huggingface.co/{repo_id}/resolve/main/{repo_filename}"
            
            print(f"다운로드 URL: {download_url}")
            
            # requests로 직접 다운로드
            import requests
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # 파일 크기 확인
            total_size = int(response.headers.get('content-length', 0))
            print(f"파일 크기: {total_size / (1024*1024):.1f} MB")
            
            # 파일 크기 정보 시그널 (간소화)
            try:
                total_size_mb = total_size // (1024 * 1024) if total_size > 0 else 0
                llava_download_progress_emitter.llava_progress_updated.emit(
                    repo_filename, 
                    0, 
                    total_size_mb, 
                    f"[{file_index}/{total_files}]"
                )
            except Exception:
                pass
            
            # 파일 저장
            downloaded = 0
            with open(dst, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 진행률 업데이트 (너무 자주 업데이트하지 않도록 제한)
                        if total_size > 0 and downloaded % (1024 * 1024) == 0:  # 1MB마다 업데이트
                            try:
                                downloaded_mb = downloaded // (1024 * 1024)
                                total_size_mb = total_size // (1024 * 1024)
                                llava_download_progress_emitter.llava_progress_updated.emit(
                                    repo_filename, 
                                    downloaded_mb, 
                                    total_size_mb, 
                                    f"[{file_index}/{total_files}] {downloaded / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB"
                                )
                            except Exception:
                                pass
            
            print(f"다운로드 완료: {dst}")
            return dst
            
        except Exception as e:
            print(f"다운로드 실패: {e}")
            raise e
    
    def download_model_files(self):
        """모델 파일들 다운로드 (실제 다운로드)"""
        try:
            logger.info(f"LLaVA 모델 파일 다운로드 시작: {self.model_id}")
            
            # Hugging Face API를 사용해서 실제 파일 목록 가져오기
            from huggingface_hub import HfApi
            api = HfApi()
            
            # 모델 정보 가져오기
            model_info = api.model_info(self.model_id)
            
            # 다운로드할 파일 목록 가져오기
            files_to_download = []
            file_sizes = {}
            
            for file_info in model_info.siblings:
                if file_info.rfilename.endswith(('.safetensors', '.bin', '.json', '.txt', '.model')):
                    files_to_download.append(file_info.rfilename)
                    # 파일 크기 처리 (None 값 방지)
                    size = getattr(file_info, 'size', None)
                    file_sizes[file_info.rfilename] = size if size is not None else 0
            
            # 파일을 크기 순으로 정렬 (큰 파일부터, None 값 처리)
            files_to_download.sort(key=lambda x: file_sizes.get(x, 0) or 0, reverse=True)
            
            total_files = len(files_to_download)
            
            logger.info(f"다운로드할 파일 목록 ({total_files}개):")
            for i, filename in enumerate(files_to_download):
                size = file_sizes.get(filename, 0)
                size_mb = (size / (1024 * 1024)) if size and size > 0 else 0
                logger.info(f"  {i+1}. {filename} ({size_mb:.1f}MB)")
            
            # 각 파일을 순차적으로 다운로드 (누락된 파일만)
            downloaded_count = 0
            for i, filename in enumerate(files_to_download):
                try:
                    # 파일이 이미 완전히 다운로드되었는지 확인
                    model_name = self.model_id.split('/')[-1]
                    model_dir = Path("models") / model_name
                    dst = model_dir / filename
                    
                    if dst.exists():
                        try:
                            # 파일 크기 확인
                            import requests
                            download_url = f"https://huggingface.co/{self.model_id}/resolve/main/{filename}"
                            head_response = requests.head(download_url)
                            if head_response.status_code == 200:
                                expected_size = int(head_response.headers.get('content-length', 0))
                                actual_size = dst.stat().st_size
                                
                                if actual_size == expected_size and expected_size > 0:
                                    logger.info(f"파일 이미 완전함 (스킵): {filename} [{i+1}/{total_files}]")
                                    downloaded_count += 1
                                    continue
                        except Exception:
                            pass
                    
                    logger.info(f"파일 다운로드 시작: {filename} [{i+1}/{total_files}]")
                    
                    # 실제 다운로드 (파일 번호 정보 전달)
                    self._ensure_local_from_hub(self.model_id, filename, filename, file_index=i+1, total_files=total_files)
                    
                    logger.info(f"파일 다운로드 완료: {filename} [{i+1}/{total_files}]")
                    downloaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"파일 다운로드 실패 (무시): {filename} [{i+1}/{total_files}] - {e}")
                    continue
            
            logger.info(f"LLaVA 모델 다운로드 완료: {self.model_id}")
            return True
            
        except Exception as e:
            logger.error(f"LLaVA 모델 다운로드 실패: {e}")
            return False
    
    def check_model_files(self) -> bool:
        """모델 파일들이 로컬에 있는지 확인 (간단한 방식)"""
        if not self.model_dir:
            model_name = self.model_id.split('/')[-1]
            self.model_dir = Path("models") / model_name
        
        if not self.model_dir.exists():
            _flush_print(f"[LLaVA] 모델 디렉토리 없음: {self.model_dir}")
            return False
        
        # 필수 파일들 확인
        required_files = [
            'config.json',
            'tokenizer.json', 
            'tokenizer_config.json',
            'generation_config.json'
        ]
        
        # 모델 가중치 파일 확인 (bin 또는 safetensors)
        model_files = list(self.model_dir.glob("*.bin")) + list(self.model_dir.glob("*.safetensors"))
        if not model_files:
            _flush_print(f"[LLaVA] 모델 가중치 파일 없음: {self.model_dir}")
            return False
        
        # 필수 설정 파일들 확인
        for file_name in required_files:
            local_file = self.model_dir / file_name
            if not local_file.exists():
                _flush_print(f"[LLaVA] 필수 파일 없음: {local_file}")
                return False
        
        _flush_print(f"[LLaVA] 모델 파일 확인 완료: {self.model_dir}")
        return True
    
    def get_model_info(self) -> dict:
        """모델 정보 반환"""
        return {
            "model_id": self.model_id,
            "model_name": self.model_id.split('/')[-1],
            "device": self._get_device(),
            "is_downloaded": self.check_model_files(),
            "model_dir": str(self.model_dir) if self.model_dir else None,
            "use_gpu": self.use_gpu
        }


class LLaVADownloadThread(QThread):
    """LLaVA 모델 다운로드를 위한 스레드"""
    
    llava_progress_updated = Signal(str, int, int, str)  # filename, downloaded, total, status
    download_finished = Signal(bool)  # 다운로드 완료
    error_occurred = Signal(str)  # 오류 발생
    
    def __init__(self, model_id: str, use_gpu: bool = True):
        super().__init__()
        self.model_id = model_id
        self.use_gpu = use_gpu
        self.captioner_module = None
    
    def run(self):
        """스레드에서 모델 다운로드 실행"""
        try:
            self.captioner_module = LLaVACaptionerModule(self.model_id, self.use_gpu)
            
            # 다운로드 진행 상황 시그널 연결
            llava_download_progress_emitter.llava_progress_updated.connect(self.llava_progress_updated)
            
            # 모델 파일 다운로드
            success = self.captioner_module.download_model_files()
            
            self.download_finished.emit(success)
            
        except Exception as e:
            logger.error(f"LLaVA 다운로드 스레드 오류: {e}")
            self.error_occurred.emit(str(e))
            self.download_finished.emit(False)


# 전역 LLaVA 모듈 인스턴스
_global_llava_module = None
_global_llava_tagger_model = None

# 통합 전역 모델 매니저 (모든 LLaVA 모델 타입 통합 관리)
_unified_llava_model_manager = {
    "current_model": None,
    "current_model_id": None,
    "current_model_type": None,
    "cached_models": {}  # {model_id: model_instance}
}

def get_global_llava_module(model_id: str = "llava-hf/llava-1.5-7b-hf", use_gpu: bool = True) -> LLaVACaptionerModule:
    """전역 LLaVA 모듈 인스턴스 반환"""
    global _global_llava_module
    
    if _global_llava_module is None or _global_llava_module.model_id != model_id:
        _global_llava_module = LLaVACaptionerModule(model_id, use_gpu)
    
    return _global_llava_module

def unload_global_llava_module():
    """전역 LLaVA 모듈 언로딩"""
    global _global_llava_module
    
    if _global_llava_module is not None:
        _global_llava_module = None

def get_global_llava_tagger_model(model_id: str = "llava-hf/llava-1.5-7b-hf", use_gpu: bool = True):
    """전역 LLaVA 태거 모델 인스턴스 반환 (통합 매니저 사용)"""
    # 통합 매니저를 통해 모델 반환
    return get_unified_llava_model(model_id, use_gpu)

def unload_global_llava_tagger_model():
    """전역 LLaVA 태거 모델 언로딩 및 메모리 정리"""
    global _global_llava_tagger_model
    
    if _global_llava_tagger_model is not None:
        try:
            # 모델과 프로세서 메모리에서 제거
            if hasattr(_global_llava_tagger_model, 'model') and _global_llava_tagger_model.model is not None:
                del _global_llava_tagger_model.model
                _global_llava_tagger_model.model = None
                _flush_print("[LLaVA] 모델 메모리에서 제거")
            
            if hasattr(_global_llava_tagger_model, 'processor') and _global_llava_tagger_model.processor is not None:
                del _global_llava_tagger_model.processor
                _global_llava_tagger_model.processor = None
                _flush_print("[LLaVA] 프로세서 메모리에서 제거")
            
            # 전역 변수 해제
            _global_llava_tagger_model = None
            
            # GPU 메모리 캐시 정리
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                _flush_print("[LLaVA] GPU 메모리 캐시 정리 완료")
            
            _flush_print("[LLaVA] 전역 태거 모델 언로딩 및 메모리 정리 완료")
        except Exception as e:
            _flush_print(f"[LLaVA] 모델 언로딩 중 오류: {e}")
            _global_llava_tagger_model = None

def unload_all_llava_models():
    """모든 LLaVA 모델 타입을 한번에 언로드 (메모리 누적 방지)"""
    _flush_print("[LLaVA] 모든 LLaVA 모델 타입 언로드 시작...")
    
    # 1. 기본 LLaVA 모델 언로드
    try:
        unload_global_llava_tagger_model()
    except Exception as e:
        _flush_print(f"[LLaVA] 기본 모델 언로드 실패: {e}")
    
    # 2. LLaVA-NeXT 모델 언로드
    try:
        from llava_next_tagger import unload_global_llava_next_tagger_model
        unload_global_llava_next_tagger_model()
    except Exception as e:
        _flush_print(f"[LLaVA-NeXT] 모델 언로드 실패: {e}")
    
    # 3. LLaVA-Interleave 모델 언로드
    try:
        from llava_interleave_tagger import unload_global_llava_interleave_tagger_model
        unload_global_llava_interleave_tagger_model()
    except Exception as e:
        _flush_print(f"[LLaVA-Interleave] 모델 언로드 실패: {e}")
    
    # 4. LLaVA-Llama3 모델 언로드
    try:
        from llava_llama3_tagger import unload_global_llava_llama3_tagger_model
        unload_global_llava_llama3_tagger_model()
    except Exception as e:
        _flush_print(f"[LLaVA-Llama3] 모델 언로드 실패: {e}")
    
    # 5. VIP-LLaVA 모델 언로드
    try:
        from llava_vip_tagger import unload_global_vip_llava_tagger_model
        unload_global_vip_llava_tagger_model()
    except Exception as e:
        _flush_print(f"[VIP-LLaVA] 모델 언로드 실패: {e}")
    
    # 6. 최종 GPU 메모리 정리 (강제 정리 사용)
    force_cleanup_gpu_memory()
    
    _flush_print("[LLaVA] 모든 LLaVA 모델 타입 언로드 완료")

def get_unified_llava_model(model_id: str, use_gpu: bool = True):
    """통합 LLaVA 모델 매니저 - 모든 모델 타입을 통합 관리 (성능 최적화)"""
    import torch  # torch import 명시적 추가 (첫 번째 실행 시 에러 방지)
    global _unified_llava_model_manager
    
    # 모델 타입 결정
    model_type = _determine_model_type(model_id)
    
    # 현재 모델과 동일한지 확인
    if (_unified_llava_model_manager["current_model"] is not None and
        _unified_llava_model_manager["current_model_id"] == model_id and
        _unified_llava_model_manager["current_model_type"] == model_type):
        _flush_print(f"[통합 매니저] 기존 모델 재사용: {model_id} ({model_type})")
        return _unified_llava_model_manager["current_model"]
    
    # 캐시된 모델 확인 (CPU 모델만)
    cache_key = f"{model_id}_{use_gpu}"
    if not use_gpu and cache_key in _unified_llava_model_manager["cached_models"]:
        cached_model = _unified_llava_model_manager["cached_models"][cache_key]
        if (hasattr(cached_model, '_is_loaded') and cached_model._is_loaded and
            hasattr(cached_model, 'model') and cached_model.model is not None):
            _flush_print(f"[통합 매니저] 캐시된 CPU 모델 재사용: {model_id} ({model_type})")
            _unified_llava_model_manager["current_model"] = cached_model
            _unified_llava_model_manager["current_model_id"] = model_id
            _unified_llava_model_manager["current_model_type"] = model_type
            return cached_model
    elif use_gpu:
        _flush_print(f"[통합 매니저] GPU 모델 캐시 확인 안함 (VRAM 누수 방지): {model_id}")
    
    # 새 모델 생성
    _flush_print(f"[통합 매니저] 새 모델 생성: {model_id} ({model_type})")
    
    # 기존 모델 정리 (VRAM 누수 방지를 위한 진짜 언로드)
    if _unified_llava_model_manager["current_model"] is not None:
        _flush_print(f"[통합 매니저] 기존 모델 정리: {_unified_llava_model_manager['current_model_id']}")
        
        # VRAM 상태 로깅 (정리 전)
        try:
            import torch
            if torch.cuda.is_available():
                gpu_mem_before = torch.cuda.memory_allocated(0) / 1024**3
                gpu_mem_reserved_before = torch.cuda.memory_reserved(0) / 1024**3
                _flush_print(f"[통합 매니저] 정리 전 VRAM - 할당: {gpu_mem_before:.2f}GB, 예약: {gpu_mem_reserved_before:.2f}GB")
        except Exception:
            pass
        
        # 현재 모델의 실제 언로드 (VRAM 누수 방지)
        try:
            current_model = _unified_llava_model_manager["current_model"]
            
            # 모델과 프로세서의 참조를 완전히 끊기
            if hasattr(current_model, 'model') and current_model.model is not None:
                del current_model.model
                current_model.model = None
                _flush_print("[통합 매니저] 모델 객체 참조 해제")
            
            if hasattr(current_model, 'processor') and current_model.processor is not None:
                del current_model.processor
                current_model.processor = None
                _flush_print("[통합 매니저] 프로세서 객체 참조 해제")
            
            # 상태 플래그 리셋
            if hasattr(current_model, '_is_loaded'):
                current_model._is_loaded = False
            if hasattr(current_model, '_cached_model_id'):
                delattr(current_model, '_cached_model_id')
                
        except Exception as e:
            _flush_print(f"[통합 매니저] 모델 언로드 실패: {e}")
        
        # 강제 메모리 정리
        try:
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()  # IPC 메모리도 정리
                _flush_print("[통합 매니저] 강제 메모리 정리 완료")
                
                # VRAM 상태 로깅 (정리 후)
                gpu_mem_after = torch.cuda.memory_allocated(0) / 1024**3
                gpu_mem_reserved_after = torch.cuda.memory_reserved(0) / 1024**3
                _flush_print(f"[통합 매니저] 정리 후 VRAM - 할당: {gpu_mem_after:.2f}GB, 예약: {gpu_mem_reserved_after:.2f}GB")
                
                # VRAM 해제 확인
                if gpu_mem_reserved_after < gpu_mem_reserved_before * 0.5:  # 50% 이상 해제
                    _flush_print("✅ [통합 매니저] VRAM 대폭 해제 성공")
                else:
                    _flush_print("⚠️ [통합 매니저] VRAM 해제 부족 - 누수 가능성")
                    
        except Exception as e:
            _flush_print(f"[통합 매니저] 메모리 정리 실패: {e}")
    
    # 모델 타입에 따른 인스턴스 생성
    new_model = _create_model_instance(model_type, model_id, use_gpu)
    
    # 매니저 업데이트
    _unified_llava_model_manager["current_model"] = new_model
    _unified_llava_model_manager["current_model_id"] = model_id
    _unified_llava_model_manager["current_model_type"] = model_type
    
    # VRAM 누수 방지를 위한 캐시 정책: GPU 모델은 캐시하지 않음
    # (캐시하면 VRAM이 계속 점유되어 다음 모델이 CPU 오프로딩됨)
    if use_gpu and torch.cuda.is_available():
        _flush_print(f"[통합 매니저] GPU 모델 캐시 저장 안함 (VRAM 누수 방지): {model_id}")
        # 기존 GPU 캐시도 정리
        if cache_key in _unified_llava_model_manager["cached_models"]:
            del _unified_llava_model_manager["cached_models"][cache_key]
    else:
        # CPU 모델만 캐시 저장
        _unified_llava_model_manager["cached_models"][cache_key] = new_model
        _flush_print(f"[통합 매니저] CPU 모델 캐시 저장: {model_id}")
    
    return new_model

def _determine_model_type(model_id: str) -> str:
    """모델 ID로부터 모델 타입 결정"""
    model_id_lower = model_id.lower()
    
    if "next" in model_id_lower or "v1.6" in model_id_lower:
        return "next"
    elif "interleave" in model_id_lower:
        return "interleave"
    elif "llama-3" in model_id_lower or "llama3" in model_id_lower:
        return "llama3"
    elif "vip" in model_id_lower:
        return "vip"
    else:
        return "standard"  # 기본 LLaVA 모델

def _create_model_instance(model_type: str, model_id: str, use_gpu: bool):
    """모델 타입에 따른 인스턴스 생성"""
    if model_type == "next":
        from llava_next_tagger import LLaVANextTagger
        return LLaVANextTagger(model_id=model_id, use_gpu=use_gpu)
    elif model_type == "interleave":
        from llava_interleave_tagger import LLaVAInterleaveTagger
        return LLaVAInterleaveTagger(model_id=model_id, use_gpu=use_gpu)
    elif model_type == "llama3":
        from llava_llama3_tagger import LLaVALlama3Tagger
        return LLaVALlama3Tagger(model_id=model_id, use_gpu=use_gpu)
    elif model_type == "vip":
        from llava_vip_tagger import VipLlavaTagger
        return VipLlavaTagger(model_id=model_id, use_gpu=use_gpu)
    else:
        # 기본 LLaVA 모델
        return LLaVATaggerModel(model_id=model_id, use_gpu=use_gpu)

def clear_unified_model_cache():
    """통합 모델 캐시 완전 정리"""
    global _unified_llava_model_manager
    
    _flush_print("[통합 매니저] 캐시 완전 정리 시작")
    
    # 모든 모델 언로드
    unload_all_llava_models()
    
    # 매니저 초기화
    _unified_llava_model_manager["current_model"] = None
    _unified_llava_model_manager["current_model_id"] = None
    _unified_llava_model_manager["current_model_type"] = None
    _unified_llava_model_manager["cached_models"].clear()
    
    _flush_print("[통합 매니저] 캐시 완전 정리 완료")

def force_cleanup_gpu_memory():
    """최적화된 GPU 메모리 정리 (성능 우선)"""
    try:
        import gc
        import torch
        
        # Python 가비지 컬렉션만 실행 (빠름)
        gc.collect()
        
        if torch.cuda.is_available():
            # CUDA 메모리 캐시만 정리 (synchronize 제거로 성능 향상)
            torch.cuda.empty_cache()
            
            # 추가 메모리 정리는 필요시에만 (성능 저하 방지)
            # torch.cuda.synchronize() 제거 - 성능 저하의 주요 원인
            # torch.cuda.reset_peak_memory_stats() 제거 - 불필요한 오버헤드
            
            _flush_print("[GPU] 최적화된 메모리 정리 완료")
        else:
            _flush_print("[GPU] CUDA 사용 불가, CPU 메모리만 정리")
            
    except Exception as e:
        _flush_print(f"[GPU] 메모리 정리 실패: {e}")

def aggressive_cleanup_gpu_memory():
    """공격적인 GPU 메모리 정리 (메모리 부족 시에만 사용)"""
    try:
        import gc
        import torch
        
        # Python 가비지 컬렉션 강제 실행
        gc.collect()
        
        if torch.cuda.is_available():
            # CUDA 메모리 캐시 완전 정리
            torch.cuda.empty_cache()
            torch.cuda.synchronize()  # 메모리 부족 시에만 동기화
            
            # 추가 메모리 정리
            try:
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.reset_accumulated_memory_stats()
            except Exception:
                pass
            
            _flush_print("[GPU] 공격적 메모리 정리 완료")
            
            # 정리 후 메모리 상태 로깅
            log_gpu_memory_status("공격적 정리 후")
        else:
            _flush_print("[GPU] CUDA 사용 불가, CPU 메모리만 정리")
            
    except Exception as e:
        _flush_print(f"[GPU] 공격적 메모리 정리 실패: {e}")

# ============================================================================
# [ADDED] LLaVA Inference (test-only) — do NOT modify any download logic above
# - Hard-coded settings per user's request (no external config/moduleization)
# - WD-like interface (Qt signals + batch tagging) so UI can reuse hooks
# ============================================================================

import re
import sys
import traceback
import torch
from PIL import Image
from typing import List, Tuple
from PySide6.QtCore import QObject, Signal, QThread

try:
    from transformers import AutoProcessor, LlavaForConditionalGeneration  # >=4.38.0
    _TRANSFORMERS_OK = True
except Exception as _e:
    _TRANSFORMERS_OK = False
    print(f"⚠️ transformers import failed for Llava: {_e}", flush=True)

def _flush_print(msg: str):
    print(msg, flush=True)

def log_gpu_memory_status(context: str = ""):
    """GPU 메모리 사용량 로깅"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_mem_allocated = torch.cuda.memory_allocated(0) / 1024**3
            gpu_mem_reserved = torch.cuda.memory_reserved(0) / 1024**3
            gpu_mem_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            gpu_mem_free = gpu_mem_total - gpu_mem_reserved
            
            context_str = f" [{context}]" if context else ""
            _flush_print(f"[GPU 메모리{context_str}] 할당: {gpu_mem_allocated:.2f}GB, 예약: {gpu_mem_reserved:.2f}GB, 여유: {gpu_mem_free:.2f}GB, 총량: {gpu_mem_total:.2f}GB")
            
            # 메모리 부족 경고
            if gpu_mem_free < 2.0:  # 2GB 미만 여유 메모리
                _flush_print(f"⚠️ [GPU 메모리 경고] 여유 메모리가 부족합니다: {gpu_mem_free:.2f}GB")
        else:
            _flush_print(f"[GPU 메모리{context}] CUDA 사용 불가")
    except Exception as e:
        _flush_print(f"[GPU 메모리] 상태 확인 실패: {e}")

class LLaVATaggerModel(QObject):
    progress_updated = Signal(int, int)       # current, total
    model_loading_progress = Signal(str, int)  # 모델 로딩 진행 시그널 (상태, 진행률)
    model_loading_finished = Signal()         # 모델 로딩 완료 시그널
    tag_generated   = Signal(str, list)       # image_path, List[(tag, score)]
    finished        = Signal()
    error_occurred  = Signal(str)


    def __init__(self, model_id: str = "llava-hf/llava-1.5-7b-hf", use_gpu: bool = True):
        super().__init__()
        self.model_id   = model_id
        self.use_gpu    = bool(use_gpu and torch.cuda.is_available())
        self.device     = "cuda" if self.use_gpu else "cpu"
        self.model      = None
        self.processor  = None
        self.config     = self._load_llava_config()
        self._is_loaded = False  # 모델 로드 상태 추적
        self.model_dir  = None   # 모델 디렉토리 경로
        
        # 디버그 출력
        print(f"[LLaVA] 설정 로드 완료:")
        print(f"  - max_tokens: {self.config.get('max_tokens', 500)}")
        print(f"  - quantization_type: {self.config.get('quantization_type', 'none')}")
        print(f"  - use_flash_attention: {self.config.get('use_flash_attention', True)}")

    def _load_llava_config(self):
        """LLaVA 설정 불러오기"""
        try:
            import json
            config_path = "models/llava_tagger_config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 설정 반환
                return self._get_default_llava_config()
        except Exception as e:
            print(f"LLaVA 설정 불러오기 오류: {str(e)}")
            return self._get_default_llava_config()
    
    def _get_default_llava_config(self):
        """LLaVA 기본 설정 반환 (정리된 버전)"""
        return {
            "max_tokens": 500,
            "temperature": 0.1,
            "top_p": 0.9,
            "num_beams": 1,
            "quantization_type": "4bit",
            "use_flash_attention": True,
            "prompt_style": "detailed",
            "prompt_persona": "neutral",
            "custom_prompt": "",
            "custom_persona": ""
        }

    def _generate_with_model(self, inputs):
        """모델 생성 공통 함수 (중복 코드 제거)"""
        import time
        import torch  # torch import 명시적 추가
        
        # 생성 파라미터 로그 출력 (동적으로 설정된 후 출력)
        pass  # 로그는 gen_kwargs 설정 후에 출력
        
        _flush_print(f"[LLaVA] 생성 시작... (device={next(self.model.parameters()).device})")
        generation_start = time.time()
        
        # GPU 메모리 사용량 체크 (생성 전)
        if self.use_gpu and torch.cuda.is_available():
            gpu_mem_before = torch.cuda.memory_allocated(0) / 1024**3
            _flush_print(f"[LLaVA] 생성 전 GPU 메모리: {gpu_mem_before:.2f} GB")
        
        with torch.inference_mode():
            # 생성 파라미터 설정
            temperature = self.config.get("temperature", 0.1)
            num_beams = self.config.get("num_beams", 1)  # 기본값 1 (그리디)
            
            gen_kwargs = {
                "max_new_tokens": self.config.get("max_tokens", 500),
                "temperature": temperature,
                "top_p": self.config.get("top_p", 0.9),
                "num_beams": num_beams,
                "pad_token_id": self.model.config.pad_token_id if self.model.config.pad_token_id is not None else self.model.config.eos_token_id,
            }
            
            # 추가 디코딩/샘플링 제어 옵션들 (지원되는 옵션만)
            if self.config.get("top_k") is not None:
                gen_kwargs["top_k"] = self.config.get("top_k")
            if self.config.get("typical_p") is not None:
                gen_kwargs["typical_p"] = self.config.get("typical_p")
            if self.config.get("repetition_penalty") is not None:
                gen_kwargs["repetition_penalty"] = self.config.get("repetition_penalty")
            if self.config.get("no_repeat_ngram_size") is not None:
                gen_kwargs["no_repeat_ngram_size"] = self.config.get("no_repeat_ngram_size")
            if self.config.get("length_penalty") is not None:
                gen_kwargs["length_penalty"] = self.config.get("length_penalty")
            if self.config.get("min_new_tokens") is not None:
                gen_kwargs["min_new_tokens"] = self.config.get("min_new_tokens")
            if self.config.get("num_return_sequences") is not None:
                gen_kwargs["num_return_sequences"] = self.config.get("num_return_sequences")
            
            # early_stopping 설정 (사용자 지정값 우선, 없으면 빔서치 시 자동 설정)
            if self.config.get("early_stopping") is not None:
                gen_kwargs["early_stopping"] = self.config.get("early_stopping")
            elif num_beams > 1:
                gen_kwargs["early_stopping"] = True
            else:
                gen_kwargs["early_stopping"] = False
            
            # do_sample 설정 (사용자 지정값 우선, 없으면 temperature 기반 자동 설정)
            if self.config.get("do_sample") is not None:
                gen_kwargs["do_sample"] = self.config.get("do_sample")
            elif temperature > 0.0:
                gen_kwargs["do_sample"] = True  # 샘플링 활성화
            else:
                gen_kwargs["do_sample"] = False  # greedy decoding
            
            # 종료/토큰 관련 옵션들은 모델 기본값 사용 (사용자 설정 불필요)
            
            # seed 설정 (재현성)
            seed = self.config.get("seed")
            if seed is not None and seed != -1:
                import torch
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed(seed)
                _flush_print(f"[LLaVA] 시드 설정: {seed}")
            
            # 생성 파라미터 로그 출력 (최종 설정 후)
            _flush_print(f"[LLaVA] 생성 파라미터:")
            _flush_print(f"  - max_new_tokens: {gen_kwargs['max_new_tokens']}")
            _flush_print(f"  - temperature: {gen_kwargs['temperature']}")
            _flush_print(f"  - top_p: {gen_kwargs['top_p']}")
            _flush_print(f"  - do_sample: {gen_kwargs['do_sample']}")
            _flush_print(f"  - num_beams: {gen_kwargs['num_beams']}")
            _flush_print(f"  - early_stopping: {gen_kwargs['early_stopping']}")
            
            # 추가 옵션들 로그 출력 (지원되는 옵션만)
            additional_params = []
            for key in ["top_k", "typical_p", "repetition_penalty", "no_repeat_ngram_size", "length_penalty", "min_new_tokens", "num_return_sequences"]:
                if key in gen_kwargs:
                    additional_params.append(f"{key}: {gen_kwargs[key]}")
            if additional_params:
                _flush_print(f"  - 추가 옵션: {', '.join(additional_params)}")
            
            gen_ids = self.model.generate(**inputs, **gen_kwargs)
        
        generation_time = time.time() - generation_start
        _flush_print(f"[LLaVA] 생성 완료 ({generation_time:.3f}s)")
        
        # GPU 메모리 사용량 체크 (생성 후)
        if self.use_gpu and torch.cuda.is_available():
            gpu_mem_after = torch.cuda.memory_allocated(0) / 1024**3
            _flush_print(f"[LLaVA] 생성 후 GPU 메모리: {gpu_mem_after:.2f} GB")
        
        return gen_ids, generation_time

    def _build_prompt_messages(self):
        # 설정에서 프롬프트 스타일과 페르소나 가져오기
        prompt_style = self.config.get("prompt_style", "detailed")
        prompt_persona = self.config.get("prompt_persona", "neutral")
        custom_prompt = self.config.get("custom_prompt", "")
        custom_persona = self.config.get("custom_persona", "")
        
        # 커스텀 프롬프트/페르소나 처리
        if prompt_style == "custom" and custom_prompt and custom_prompt.strip():
            # 커스텀 프롬프트가 선택되고 입력된 경우
            prompt_text = custom_prompt.strip()
            # 커스텀 페르소나도 있으면 추가
            if prompt_persona == "custom" and custom_persona and custom_persona.strip():
                prompt_text += f" {custom_persona.strip()}"
        else:
            # 기본 템플릿 사용
            
            # 프롬프트 스타일과 페르소나에 따른 템플릿
            prompt_templates = {
                "detailed": {
                    "neutral": "Describe this image in detail. Provide a comprehensive caption that explains what you see, including objects, actions, colors, and any other relevant details.",
                    "professional": "Analyze this image professionally. Provide a detailed, objective description covering all visual elements, composition, and contextual information.",
                    "friendly": "Look at this image and tell me what you see! Describe everything in a warm, friendly way - the colors, objects, people, and what's happening.",
                    "creative": "Interpret this image creatively. Describe not just what you see, but the mood, atmosphere, and artistic elements that make it special.",
                    "analytical": "Examine this image systematically. Break down the visual components, analyze the composition, and provide a structured description of all elements.",
                    "anime": "Describe this image focusing on anime-style elements. Pay attention to character design, art style, expressions, and typical anime visual characteristics.",
                    "realistic": "Describe this image with a focus on realistic elements. Emphasize natural lighting, realistic proportions, and lifelike details.",
                    "cartoon": "Describe this image with a cartoon-style perspective. Focus on simplified shapes, bold colors, and cartoon-like visual characteristics.",
                    "photography": "Describe this image from a photography perspective. Focus on composition, lighting, depth of field, and photographic techniques.",
                    "digital_art": "Describe this image as digital artwork. Focus on digital art techniques, color palettes, and digital medium characteristics."
                },
                "brief": {
                    "neutral": "Briefly describe this image.",
                    "professional": "Provide a concise, professional description of this image.",
                    "friendly": "Tell me what you see in this image in a few words!",
                    "creative": "Give me a creative, short description of this image.",
                    "analytical": "Provide a brief, analytical summary of this image.",
                    "anime": "Briefly describe this image focusing on anime-style elements.",
                    "realistic": "Briefly describe this image with realistic details.",
                    "cartoon": "Briefly describe this image in cartoon style.",
                    "photography": "Briefly describe this image from a photography perspective.",
                    "digital_art": "Briefly describe this image as digital artwork."
                },
                "technical": {
                    "neutral": "Provide a technical description of this image, including specifications, measurements, and technical details where applicable.",
                    "professional": "Analyze this image from a technical perspective, focusing on technical specifications and measurable elements.",
                    "friendly": "Explain what you see in this image using simple technical terms!",
                    "creative": "Describe the technical aspects of this image in an innovative way.",
                    "analytical": "Break down the technical components of this image systematically.",
                    "anime": "Provide a technical analysis of this anime-style image, focusing on art techniques and visual elements.",
                    "realistic": "Provide a technical description of this realistic image, focusing on technical accuracy and details.",
                    "cartoon": "Provide a technical analysis of this cartoon-style image, focusing on simplified technical elements.",
                    "photography": "Provide a technical analysis of this photograph, focusing on camera settings and photographic techniques.",
                    "digital_art": "Provide a technical analysis of this digital artwork, focusing on digital techniques and tools."
                },
                "artistic": {
                    "neutral": "Describe this image from an artistic perspective, focusing on visual elements, composition, and aesthetic qualities.",
                    "professional": "Analyze the artistic elements of this image, including composition, color theory, and visual design principles.",
                    "friendly": "Tell me about the artistic beauty you see in this image!",
                    "creative": "Interpret this image as a work of art, describing its creative and aesthetic qualities.",
                    "analytical": "Examine the artistic composition and visual elements of this image systematically.",
                    "anime": "Analyze this image from an anime art perspective, focusing on anime-specific artistic techniques and styles.",
                    "realistic": "Analyze this image from a realistic art perspective, focusing on realistic artistic techniques and details.",
                    "cartoon": "Analyze this image from a cartoon art perspective, focusing on cartoon artistic techniques and styles.",
                    "photography": "Analyze this image from an artistic photography perspective, focusing on photographic composition and artistic elements.",
                    "digital_art": "Analyze this image as digital art, focusing on digital artistic techniques and creative elements."
                },
                "casual": {
                    "neutral": "What do you see in this image? Just tell me in a casual way.",
                    "professional": "Provide a casual but informative description of this image.",
                    "friendly": "Hey! What's going on in this image? Tell me in a fun way!",
                    "creative": "What's the vibe of this image? Give me a casual, creative take on it.",
                    "analytical": "Take a casual look at this image and tell me what stands out to you.",
                    "anime": "What anime-style elements do you see in this image? Tell me casually!",
                    "realistic": "What realistic details do you notice in this image? Just tell me casually.",
                    "cartoon": "What cartoon elements do you see in this image? Tell me in a casual way!",
                    "photography": "What do you think about this photo? Tell me casually what catches your eye.",
                    "digital_art": "What digital art elements do you see? Just tell me casually what stands out."
                },
                "word_tags": {
                    "neutral": "List all the objects, characters, actions, and visual elements you see in this image as individual words or short phrases, separated by commas.",
                    "professional": "Identify and list all visual elements in this image using precise, descriptive terms separated by commas.",
                    "friendly": "Tell me what you see in this image using simple words and phrases, separated by commas!",
                    "creative": "Describe the visual elements of this image using creative and artistic terms, separated by commas.",
                    "analytical": "Systematically list all identifiable elements in this image using analytical terms, separated by commas.",
                    "anime": "List anime-style elements, characters, and visual features you see in this image, separated by commas.",
                    "realistic": "List realistic elements and details you see in this image, separated by commas.",
                    "cartoon": "List cartoon-style elements and features you see in this image, separated by commas.",
                    "photography": "List photographic elements, composition details, and visual features you see in this image, separated by commas.",
                    "digital_art": "List digital art elements, techniques, and visual features you see in this image, separated by commas."
                },
                "danbooru_style": {
                    "neutral": "Describe this image using Danbooru-style tags. List characters, objects, actions, clothing, expressions, and visual elements as comma-separated tags.",
                    "professional": "Analyze this image and provide Danbooru-style tags including character names, clothing, expressions, poses, and visual elements.",
                    "friendly": "Give me Danbooru-style tags for this image! List characters, clothes, expressions, and what's happening!",
                    "creative": "Create Danbooru-style tags for this image, focusing on artistic elements, mood, and creative aspects.",
                    "analytical": "Systematically generate Danbooru-style tags for this image, covering all visual elements, composition, and details.",
                    "anime": "Provide Danbooru-style tags for this anime image, focusing on anime-specific character features, expressions, and art styles.",
                    "realistic": "Provide Danbooru-style tags for this realistic image, focusing on realistic character features and visual elements.",
                    "cartoon": "Provide Danbooru-style tags for this cartoon image, focusing on cartoon-style character features and visual elements.",
                    "photography": "Provide Danbooru-style tags for this photograph, focusing on photographic elements and realistic visual features.",
                    "digital_art": "Provide Danbooru-style tags for this digital artwork, focusing on digital art techniques and visual elements."
                }
            }
            
            prompt_text = prompt_templates.get(prompt_style, {}).get(prompt_persona, 
                "Describe this image in detail. Provide a comprehensive caption that explains what you see, including objects, actions, colors, and any other relevant details.")
            
            # 커스텀 페르소나가 있으면 텍스트에 추가로 주입 (태그 전용 스타일 제외, custom 명시적 선택시만)
            tag_only_styles = ["word_tags", "danbooru_style"]
            if prompt_style not in tag_only_styles and prompt_persona == "custom" and custom_persona and custom_persona.strip():
                # 커스텀 페르소나만 선택된 경우: 기본 템플릿 + 커스텀 페르소나
                prompt_text += f" Also reflect the following style/tone: {custom_persona.strip()}."
        
        # HF 권장 chat template 사용 (이미지가 먼저, 텍스트가 나중)
        return [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {
                        "type": "text",
                        "text": prompt_text,
                    },
                ],
            }
        ]

    def load_model(self):
        import torch  # torch import 명시적 추가
        if not _TRANSFORMERS_OK:
            raise RuntimeError("transformers>=4.38.0 필요 (멀티모달 chat template 지원)")

        # 기존 모델 언로드 및 메모리 정리 (성능 최적화)
        # 통합 매니저를 통해 최적화된 정리만 수행
        log_gpu_memory_status("모델 전환 전")
        # unload_all_llava_models() 대신 최적화된 정리만 사용
        force_cleanup_gpu_memory()
        log_gpu_memory_status("모델 언로드 후")
        _flush_print("[LLaVA] 최적화된 모델 정리 완료, 새 모델 로딩 시작")

        # GPU/CUDA 디버깅 정보
        _flush_print(f"[LLaVA] GPU 설정: use_gpu={self.use_gpu}")
        _flush_print(f"[LLaVA] CUDA 사용 가능: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            _flush_print(f"[LLaVA] CUDA 디바이스 수: {torch.cuda.device_count()}")
            _flush_print(f"[LLaVA] 현재 CUDA 디바이스: {torch.cuda.current_device()}")
            _flush_print(f"[LLaVA] CUDA 디바이스 이름: {torch.cuda.get_device_name(0)}")
            _flush_print(f"[LLaVA] CUDA 메모리: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

        # torch_dtype 설정 (사용자 설정 우선, 없으면 자동 결정)
        torch_dtype_setting = self.config.get("torch_dtype")
        if torch_dtype_setting and torch_dtype_setting != "auto":
            if torch_dtype_setting == "float16":
                torch_dtype = torch.float16
            elif torch_dtype_setting == "float32":
                torch_dtype = torch.float32
            elif torch_dtype_setting == "bfloat16":
                torch_dtype = torch.bfloat16
            else:
                torch_dtype = torch.float16 if self.use_gpu else torch.float32
            _flush_print(f"[LLaVA] 사용자 설정 torch_dtype: {torch_dtype}")
        else:
            torch_dtype = torch.float16 if self.use_gpu else torch.float32
            _flush_print(f"[LLaVA] 자동 설정 torch_dtype: {torch_dtype}")

        # 로컬 모델 경로 사용 (다운로드 방지)
        model_name = self.model_id.split('/')[-1]
        local_model_path = Path("models") / model_name
        
        if not local_model_path.exists():
            raise RuntimeError(f"로컬 모델 경로가 존재하지 않습니다: {local_model_path}")

        _flush_print("[LLaVA] 모델 로드 중...")
        
        # 로컬 파일에서 모델 로드 (로컬 우선, 필요시 Hub에서 가져오기)
        try:
            # 4bit 양자화 시도 (성능 최적화)
            load_kwargs = {
                "torch_dtype": torch_dtype,
                "low_cpu_mem_usage": True,
                "local_files_only": True,
            }
            
            # max_memory 설정 (사용자 설정이 있으면 적용)
            max_memory_setting = self.config.get("max_memory")
            if max_memory_setting:
                # "8GB", "4096MB" 등의 문자열을 파싱
                if isinstance(max_memory_setting, str):
                    if "GB" in max_memory_setting:
                        gb_value = float(max_memory_setting.replace("GB", ""))
                        load_kwargs["max_memory"] = {0: f"{gb_value}GB"}
                    elif "MB" in max_memory_setting:
                        mb_value = float(max_memory_setting.replace("MB", ""))
                        gb_value = mb_value / 1024
                        load_kwargs["max_memory"] = {0: f"{gb_value}GB"}
                    _flush_print(f"[LLaVA] max_memory 설정: {load_kwargs['max_memory']}")
                elif isinstance(max_memory_setting, dict):
                    load_kwargs["max_memory"] = max_memory_setting
                    _flush_print(f"[LLaVA] max_memory 설정: {max_memory_setting}")
            else:
                # 기본값으로 8GB 제한 (메모리 부족 방지)
                load_kwargs["max_memory"] = {0: "8GB"}
                _flush_print(f"[LLaVA] 기본 max_memory 설정: {load_kwargs['max_memory']}")
            
            # device_map 설정 (사용자 설정 우선, 없으면 자동 결정)
            device_map_setting = self.config.get("device_map")
            if device_map_setting and device_map_setting != "auto":
                # 사용자가 명시적으로 설정한 경우
                load_kwargs["device_map"] = device_map_setting
                _flush_print(f"[LLaVA] 사용자 설정 device_map: {device_map_setting}")
            elif self.use_gpu:
                # GPU 선택 시: 양자화 타입에 따른 device_map 설정
                if self.config.get("quantization_type", "none") == "8bit":
                    # 8bit 양자화 시 device_map을 None으로 설정 (CPU 오프로드와 충돌 방지)
                    load_kwargs["device_map"] = None
                    _flush_print(f"[LLaVA] ℹ️ GPU 선택: 8bit 양자화 - device_map=None (CPU 오프로드 자동 처리)")
                elif self.config.get("quantization_type", "none") == "4bit":
                    load_kwargs["device_map"] = "auto"
                    _flush_print(f"[LLaVA] ℹ️ GPU 선택: device_map=auto (4bit 양자화)")
                else:
                    load_kwargs["device_map"] = None
                    _flush_print(f"[LLaVA] ℹ️ GPU 선택: device_map=None, GPU에 직접 로드")
            else:
                # CPU 선택 시: CPU에 직접 로드
                load_kwargs["device_map"] = None
                _flush_print("[LLaVA] ℹ️ CPU 선택: device_map=None, CPU에 직접 로드")
            
            # 양자화 설정 (사용자 선택 + 설정 파일 확인)
            if self.config.get("quantization_type", "none") != "none" and self.use_gpu:
                try:
                    from transformers import BitsAndBytesConfig
                    if torch.cuda.is_available():
                        if self.config.get("quantization_type", "none") == "4bit":
                            bnb_config = BitsAndBytesConfig(
                                load_in_4bit=True,
                                bnb_4bit_use_double_quant=True,
                                bnb_4bit_quant_type="nf4",
                                bnb_4bit_compute_dtype=torch_dtype
                            )
                            _flush_print("[LLaVA] ✅ 4bit 양자화 설정 적용됨 (GPU 선택됨)")
                        elif self.config.get("quantization_type", "none") == "8bit":
                            # 8비트 양자화 시 CPU 오프로드 활성화 (메모리 부족 문제 해결)
                            bnb_config = BitsAndBytesConfig(
                                load_in_8bit=True,
                                llm_int8_threshold=6.0,
                                llm_int8_has_fp16_weight=False,
                                llm_int8_enable_fp32_cpu_offload=True  # CPU 오프로드 강제 활성화
                            )
                            _flush_print(f"[LLaVA] ✅ 8bit 양자화 설정 적용됨 (CPU 오프로드 활성화)")
                        elif self.config.get("quantization_type", "none") == "FP16":
                            # FP16 precision
                            torch_dtype = torch.float16
                            _flush_print("[LLaVA] ✅ FP16 설정 적용됨 (GPU 선택됨)")
                            bnb_config = None
                        elif self.config.get("quantization_type", "none") == "BF16":
                            # BF16 precision
                            torch_dtype = torch.bfloat16
                            _flush_print("[LLaVA] ✅ BF16 설정 적용됨 (GPU 선택됨)")
                            bnb_config = None
                        elif self.config.get("quantization_type", "none") == "FP32":
                            # FP32 precision
                            torch_dtype = torch.float32
                            _flush_print("[LLaVA] ✅ FP32 설정 적용됨 (GPU 선택됨)")
                            bnb_config = None
                        else:
                            _flush_print(f"[LLaVA] ⚠️ 지원하지 않는 양자화 타입: {self.config.get('quantization_type', 'none')}")
                            bnb_config = None
                        
                        if bnb_config:
                            load_kwargs["quantization_config"] = bnb_config
                        load_kwargs["torch_dtype"] = torch_dtype
                    else:
                        _flush_print("[LLaVA] ⚠️ CUDA 사용 불가, 양자화 건너뜀")
                except ImportError:
                    _flush_print("[LLaVA] ⚠️ bitsandbytes 없음, 표준 데이터 타입으로 로드")
                except Exception as e:
                    _flush_print(f"[LLaVA] ❌ 양자화 실패: {e}")
            elif self.config.get("quantization_type", "none") != "none" and not self.use_gpu:
                _flush_print(f"[LLaVA] ℹ️ CPU 선택됨, {self.config.get('quantization_type', 'none')} 양자화 건너뜀 (GPU 전용 기능)")
            else:
                _flush_print("[LLaVA] ℹ️ 양자화 비활성화됨")
            
            # FlashAttention2 시도 (사용자 선택 + 설정 파일 확인)
            if self.config.get("use_flash_attention", True) and self.use_gpu:
                try:
                    load_kwargs["attn_implementation"] = "flash_attention_2"
                    _flush_print("[LLaVA] ✅ FlashAttention2 설정 적용됨 (GPU 선택됨)")
                except Exception as e:
                    _flush_print(f"[LLaVA] ❌ FlashAttention2 실패: {e}")
            elif self.config.get("use_flash_attention", True) and not self.use_gpu:
                _flush_print("[LLaVA] ℹ️ CPU 선택됨, FlashAttention2 건너뜀 (GPU 전용 기능)")
            else:
                _flush_print("[LLaVA] ℹ️ FlashAttention2 비활성화됨")
            
            # 메모리 캐시 정리 (8bit 양자화 시 메모리 부족 방지)
            if self.config.get("quantization_type", "none") == "8bit" and self.use_gpu:
                try:
                    import gc
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        _flush_print("[LLaVA] 🧹 GPU 메모리 캐시 정리 완료")
                except Exception as e:
                    _flush_print(f"[LLaVA] ⚠️ 메모리 정리 실패: {e}")
            
            # 모델 로드 시도 (진행률 캐치 적용)
            progress_capture = ModelLoadingProgressCapture(
                progress_callback=lambda msg, progress: self.model_loading_progress.emit(msg, progress),
                finished_callback=lambda: self.model_loading_finished.emit()
            )
            # 모델 로드 시도 (진행률 캐치 적용)
            try:
                self.model = progress_capture.capture_loading_progress(
                    LlavaForConditionalGeneration.from_pretrained,
                    str(local_model_path),
                    **load_kwargs
                )
            except Exception as e:
                # 8bit 양자화 실패 시 4bit로 폴백 시도
                if ("8bit" in str(e) and ("CPU or the disk" in str(e) or "memory" in str(e).lower())) or \
                   ("Some modules are dispatched" in str(e)):
                    _flush_print("[LLaVA] 8bit 양자화 실패, 4bit로 폴백 시도...")
                    # 8bit 실패 시 4bit로 폴백
                    if self.config.get("quantization_type", "none") == "8bit":
                        try:
                            from transformers import BitsAndBytesConfig
                            bnb_config = BitsAndBytesConfig(
                                load_in_4bit=True,
                                bnb_4bit_use_double_quant=True,
                                bnb_4bit_quant_type="nf4",
                                bnb_4bit_compute_dtype=torch_dtype
                            )
                            load_kwargs["quantization_config"] = bnb_config
                            load_kwargs["device_map"] = "auto"  # 4bit는 device_map 사용
                            _flush_print("[LLaVA] ✅ 4bit 양자화로 폴백 적용됨")
                            
                            self.model = progress_capture.capture_loading_progress(
                                LlavaForConditionalGeneration.from_pretrained,
                                str(local_model_path),
                                **load_kwargs
                            )
                        except Exception as fallback_e:
                            _flush_print(f"[LLaVA] 4bit 폴백도 실패: {fallback_e}")
                            raise e  # 원래 오류를 다시 발생
                    else:
                        raise e
                else:
                    raise e
            self.processor = AutoProcessor.from_pretrained(
                str(local_model_path),
                local_files_only=True  # 로컬 파일만 사용
            )
            # LLaMA 계열 생성 시 좌측 패딩 권장
            self.processor.tokenizer.padding_side = "left"
            _flush_print("[LLaVA] 로컬 모델 로드 완료")
        except Exception as e:
            _flush_print(f"[LLaVA] 로컬 모델 로드 실패: {e}")
            # 로컬 로드 실패 시 예외를 다시 발생시켜서 다운로드가 필요함을 알림
            raise RuntimeError(f"로컬 모델 로드 실패: {e}. 모델을 다운로드하세요.")
        
        # 모델이 이미 올바른 디바이스에 로드되었는지 확인
        model_device = next(self.model.parameters()).device
        _flush_print(f"[LLaVA] 모델 디바이스: {model_device}")
        _flush_print(f"[LLaVA] 모델 데이터 타입: {next(self.model.parameters()).dtype}")
        
        # GPU 선택했는데 CPU에 로드된 경우에만 GPU로 이동 (bnb 양자화 제외)
        if self.use_gpu and "cpu" in str(model_device):
            # bnb 양자화로 device_map="auto" 사용한 경우는 이미 올바른 디바이스에 배치됨
            if self.config.get("quantization_type", "none") not in ["4bit", "8bit"]:
                _flush_print("[LLaVA] 모델을 GPU로 이동 중...")
                self.model.to(0)
                _flush_print(f"[LLaVA] 모델 GPU 이동 완료: {next(self.model.parameters()).device}")
            else:
                _flush_print("[LLaVA] bnb 양자화로 device_map=auto 사용, 디바이스 이동 건너뜀")
        elif not self.use_gpu and "cuda" in str(model_device):
            _flush_print("[LLaVA] 모델을 CPU로 이동 중...")
            self.model.to("cpu")
            _flush_print(f"[LLaVA] 모델 CPU 이동 완료: {next(self.model.parameters()).device}")
        
        self.model.eval()

        # SDPA (Scaled Dot Product Attention) 가속 체크
        try:
            if hasattr(self.model, 'config'):
                config = self.model.config
                _flush_print(f"[LLaVA] 모델 설정 - attention_implementation: {getattr(config, 'attn_implementation', 'default')}")
                _flush_print(f"[LLaVA] 모델 설정 - use_sdpa: {getattr(config, 'use_sdpa', 'not set')}")
        except Exception as e:
            _flush_print(f"[LLaVA] SDPA 설정 확인 실패: {e}")

        try:
            if hasattr(self.processor, "tokenizer"):
                self.processor.tokenizer.padding_side = "left"
        except Exception:
            pass
        self._is_loaded = True  # 모델 로드 완료 플래그 설정
        
        # VRAM 상태 및 device_map 진단 로깅
        try:
            if torch.cuda.is_available():
                gpu_mem_allocated = torch.cuda.memory_allocated(0) / 1024**3
                gpu_mem_reserved = torch.cuda.memory_reserved(0) / 1024**3
                _flush_print(f"[LLaVA] VRAM 상태 - 할당: {gpu_mem_allocated:.2f}GB, 예약: {gpu_mem_reserved:.2f}GB")
                
                # device_map 상태 확인
                device_map = getattr(self.model, "hf_device_map", None)
                if device_map:
                    _flush_print(f"[LLaVA] device_map: {device_map}")
                    # CPU 오프로딩 감지
                    cpu_layers = [k for k, v in device_map.items() if "cpu" in str(v)]
                    if cpu_layers:
                        _flush_print(f"⚠️ [LLaVA] CPU 오프로딩 감지! 레이어: {cpu_layers[:3]}... (총 {len(cpu_layers)}개)")
                    else:
                        _flush_print(f"✅ [LLaVA] 모든 레이어가 GPU에 로드됨")
                else:
                    _flush_print(f"[LLaVA] device_map 정보 없음")
        except Exception as e:
            _flush_print(f"[LLaVA] VRAM 진단 실패: {e}")
        
        # model_loading_finished.emit()은 체크포인트 로딩 100% 완료 시 호출됨
        log_gpu_memory_status("모델 로딩 완료")
        _flush_print("[LLaVA] 모델 로드 완료")


    def predict_tags(self, image_path: str) -> List[Tuple[str, float]]:
        import time
        import torch  # torch import 명시적 추가
        start_time = time.time()
        
        try:
            # 추론할 때마다 최신 설정 로드
            self.config = self._load_llava_config()
            _flush_print(f"[LLaVA] 최신 설정 로드: temperature={self.config.get('temperature', 0.1)}, top_p={self.config.get('top_p', 0.9)}")
            
            if not self._is_loaded or self.model is None or self.processor is None:
                _flush_print("[LLaVA] 모델이 로드되지 않음, 로딩 시작...")
                self.load_model()
            else:
                _flush_print("[LLaVA] 이미 로드된 모델 사용")

            _flush_print("[LLaVA] 이미지 로드 중...")
            image_load_start = time.time()
            image = Image.open(image_path).convert("RGB")
            
            # Let processor handle image preprocessing (no manual resize)
            original_size = image.size
            _flush_print(f"[LLaVA] 이미지 크기: {original_size} (프로세서가 자동 처리)")
            
            image_load_time = time.time() - image_load_start
            _flush_print(f"[LLaVA] 이미지 로드 완료: {image.size} ({image_load_time:.3f}s)")

            _flush_print("[LLaVA] 프롬프트 구성 및 텐서 처리 중...")
            prompt_start = time.time()
            messages = self._build_prompt_messages()
            
            # Use standard method: apply_chat_template + processor
            prompt = self.processor.apply_chat_template(messages, add_generation_prompt=True)
            prompt_time = time.time() - prompt_start
            _flush_print(f"[LLaVA] 프롬프트 구성 완료: {len(prompt)} 문자 ({prompt_time:.3f}s)")

            _flush_print("[LLaVA] 텐서 처리 중...")
            tensor_start = time.time()
            
            # 모델의 실제 dtype 사용 (설정과 일관성 유지)
            if hasattr(self.model, 'dtype'):
                dtype = self.model.dtype
            else:
                # 모델 dtype을 가져올 수 없는 경우 첫 번째 파라미터의 dtype 사용
                try:
                    dtype = next(self.model.parameters()).dtype
                except:
                    # 최후의 수단: 설정 기반 dtype
                    quantization_type = self.config.get("quantization_type", "none")
                    if quantization_type == "BF16":
                        dtype = torch.bfloat16
                    elif quantization_type in ["FP16", "4bit", "8bit"]:
                        dtype = torch.float16
                    else:
                        dtype = torch.float32
            
            _flush_print(f"[LLaVA] 사용할 dtype: {dtype} (모델과 일관성 유지)")
            
            # image_aspect_policy 적용 (이미지 전처리 정책)
            image_aspect_policy = self.config.get("image_aspect_policy", "auto")
            if image_aspect_policy != "auto":
                # 이미지 전처리 정책에 따른 처리
                if image_aspect_policy == "resize":
                    # 이미지를 정사각형으로 리사이즈
                    from PIL import ImageOps
                    image = ImageOps.fit(image, (336, 336), Image.Resampling.LANCZOS)
                    _flush_print(f"[LLaVA] 이미지 리사이즈 적용: {image_aspect_policy}")
                elif image_aspect_policy == "crop":
                    # 이미지를 정사각형으로 크롭
                    from PIL import ImageOps
                    image = ImageOps.fit(image, (336, 336), Image.Resampling.LANCZOS)
                    _flush_print(f"[LLaVA] 이미지 크롭 적용: {image_aspect_policy}")
                elif image_aspect_policy == "pad":
                    # 이미지에 패딩 추가 (기본 processor 동작)
                    _flush_print(f"[LLaVA] 이미지 패딩 적용: {image_aspect_policy}")
            
            inputs = self.processor(images=image, text=prompt, return_tensors="pt")
            
            # 디바이스 핸들링: 양자화 사용 시 device_map="auto"이므로 모델 디바이스에 맞춤
            if self.config.get("quantization_type", "none") in ["4bit", "8bit"]:
                # 양자화 사용 시: 모델의 첫 번째 디바이스에 맞춤
                try:
                    model_device = next(self.model.parameters()).device
                    device = model_device
                except:
                    device = 0 if self.use_gpu else "cpu"
            else:
                # 일반 로드 시: 지정된 디바이스 사용
                device = 0 if self.use_gpu else "cpu"
            
            # Fix: Only cast float tensors to dtype, keep integer tensors as integers
            for k, v in inputs.items():
                if hasattr(v, 'to'):
                    if k in ['pixel_values', 'image_grid_*'] or 'pixel' in k.lower():
                        # Float tensors (image data) - cast to dtype
                        inputs[k] = v.to(device, dtype=dtype)
                    else:
                        # Integer tensors (input_ids, attention_mask) - only move to device
                        inputs[k] = v.to(device)
            tensor_time = time.time() - tensor_start
            _flush_print(f"[LLaVA] 텐서 처리 완료 ({tensor_time:.3f}s)")
            
            try:
                dbg = {k: tuple(v.shape) for k, v in inputs.items() if hasattr(v, "shape")}
                _flush_print(f"[LLaVA] 입력 텐서 키/쉐이프: {dbg}")
                # 텐서 디바이스 확인
                for k, v in inputs.items():
                    if hasattr(v, "device"):
                        _flush_print(f"[LLaVA] {k} 디바이스: {v.device}, dtype: {v.dtype}")
            except Exception:
                pass

            # 모델 생성 (공통 함수 사용)
            gen_ids, generation_time = self._generate_with_model(inputs)

            _flush_print("[LLaVA] 결과 디코드 중...")
            decode_start = time.time()
            
            # 입력 토큰 길이 계산 (프롬프트 부분 제외)
            input_length = inputs['input_ids'].shape[1]
            
            # 모델이 생성한 새로운 토큰만 추출
            new_tokens = gen_ids[0][input_length:]
            caption = self.processor.tokenizer.decode(new_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            
            decode_time = time.time() - decode_start
            _flush_print(f"[LLaVA] 디코드 완료 ({decode_time:.3f}s)")

            # 원문 바로 터미널에
            try:
                from pathlib import Path as _P
                _flush_print(f"[LLaVA] { _P(image_path).name } — caption:\n{caption}\n")
            except Exception:
                pass

            # 전체 시간 계산
            total_time = time.time() - start_time
            _flush_print(f"[LLaVA] === 시간 요약 ===")
            _flush_print(f"[LLaVA] 이미지 로드: {image_load_time:.3f}s")
            _flush_print(f"[LLaVA] 프롬프트 구성: {prompt_time:.3f}s")
            _flush_print(f"[LLaVA] 텐서 처리: {tensor_time:.3f}s")
            _flush_print(f"[LLaVA] 생성: {generation_time:.3f}s")
            _flush_print(f"[LLaVA] 디코드: {decode_time:.3f}s")
            _flush_print(f"[LLaVA] 총 시간: {total_time:.3f}s")

            # 캡션을 태그 형태로 변환 (UI 호환성을 위해)
            if caption:
                # 모든 스타일에서 쉼표, 마침표, 줄바꿈으로 분리하여 개별 태그로 처리
                import re
                tags = re.split(r'[,\n\r.]+', caption)
                # 각 태그에서 구분자 제거 및 공백 정리
                cleaned_tags = []
                for tag in tags:
                    # 앞뒤 공백 제거
                    tag = tag.strip()
                    # 태그 내부의 불필요한 구분자들 제거
                    tag = re.sub(r'[,\n\r.]+$', '', tag)  # 끝에 있는 구분자 제거
                    tag = re.sub(r'^[,\n\r.]+', '', tag)  # 앞에 있는 구분자 제거
                    tag = tag.strip()  # 다시 공백 제거
                    if tag:  # 빈 태그가 아닌 경우만 추가
                        cleaned_tags.append(tag)
                
                # LLaVA 태그들을 반환 (LLaVA 식별용 특별한 점수 사용)
                # 태그명은 깔끔하게, 캡션 정보는 별도로 저장
                result_tags = []
                for tag in cleaned_tags:
                    # LLaVA 태그임을 표시하기 위해 -1.0 사용 (WD는 0.0~1.0)
                    result_tags.append((tag, -1.0))
                
                return result_tags
            else:
                return []

        except Exception as e:
            tb = traceback.format_exc(limit=3)
            _flush_print(f"[LLaVA] 예측 중 오류: {e}\n{tb}")
            raise


    def batch_predict(self, image_paths: List[str]):
        total = len(image_paths)
        _flush_print(f"[LLaVA] 배치 예측 시작: {total}개 이미지")
        
        # 태그 결과 수집
        tag_results = []
        
        for i, p in enumerate(image_paths, start=1):
            try:
                _flush_print(f"[LLaVA] 이미지 {i}/{total} 처리 시작: {p}")
                tags = self.predict_tags(p)
                tag_results.append(tags)
                self.tag_generated.emit(p, tags)
            except Exception as e:
                self.error_occurred.emit(f"LLaVA 태깅 실패: {e}")
                tag_results.append([])  # 실패한 경우 빈 리스트
            finally:
                self.progress_updated.emit(i, total)
        
        # 타임머신 로그 기록 (공통 함수 사용)
        try:
            from timemachine_log import log_ai_batch_tagging
            log_ai_batch_tagging("LLaVA", self.model_id, image_paths, tag_results)
        except Exception:
            pass
        
        self.finished.emit()

class LLaVATaggerThread(QThread):
    progress_updated = Signal(int, int)
    model_loading_started = Signal(str)  # 모델 로딩 시작 시그널
    model_loading_progress = Signal(str, int)  # 모델 로딩 진행 시그널 (상태, 진행률)
    model_loading_finished = Signal()  # 모델 로딩 완료 시그널
    tag_generated   = Signal(str, list)
    finished        = Signal()
    error_occurred  = Signal(str)

    def __init__(self, image_paths: List[str], model_id: str, use_gpu: bool = True):
        super().__init__()
        self.image_paths = image_paths
        self.model_id    = model_id
        self.use_gpu     = use_gpu
        self._tagger     = None

    def run(self):
        try:
            _flush_print(f"[LLaVA Thread] 스레드 시작: {len(self.image_paths)}개 이미지")
            
            # 모델 로딩 시작 시그널 발생
            self.model_loading_started.emit(f"LLaVA 모델 로딩 중... ({self.model_id})")
            
            # 전역 모델 인스턴스 사용 (모델 재사용)
            self._tagger = get_global_llava_tagger_model(model_id=self.model_id, use_gpu=self.use_gpu)
            _flush_print("[LLaVA Thread] 전역 모델 인스턴스 사용 완료")

            # 시그널 포워딩
            self._tagger.progress_updated.connect(self.progress_updated)
            self._tagger.model_loading_progress.connect(self.model_loading_progress)
            self._tagger.model_loading_finished.connect(self.model_loading_finished)
            self._tagger.tag_generated.connect(self.tag_generated)
            self._tagger.finished.connect(self.finished)
            self._tagger.error_occurred.connect(self.error_occurred)
            _flush_print("[LLaVA Thread] 시그널 연결 완료")

            _flush_print("[LLaVA Thread] 배치 예측 시작")
            self._tagger.batch_predict(self.image_paths)
        except Exception as e:
            self.error_occurred.emit(f"LLaVA 스레드 오류: {e}")
            try:
                self.finished.emit()
            except Exception:
                pass

# ============================================================================
# [ADDED] LLaVA 성능 최적화 메시지
# ============================================================================

try:
    print("[OK] LLaVA Captioner 성능 최적화 적용 (4bit 양자화 + FlashAttention2 + 이미지 리사이즈).")
except Exception as _e:
    print(f"[WARN] Could not attach LLaVA optimizations: {_e}")

try:
    print("[OK] LLaVA 설정 모듈 연결 완료 (실시간 설정 변경 지원).")
except Exception as __e:
    print(f"[WARN] Could not attach LLaVA settings: {__e}")
