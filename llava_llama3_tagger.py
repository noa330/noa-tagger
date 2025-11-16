# llava_llama3_tagger.py
# LLaVA-Llama-3 전용 확장 추론 모듈
# - 로딩: LlavaForConditionalGeneration + LlavaProcessor (Llama-3 기반)
# - Llama-3 특화: 향상된 추론 능력과 다국어 지원

from typing import List, Tuple
from PIL import Image
import torch
from pathlib import Path

from llava_captioner_module import (
    LLaVATaggerModel,
    ModelLoadingProgressCapture,
    _flush_print,
    LLaVACaptionerModule,
    llava_download_progress_emitter,
)

from transformers import (
    LlavaForConditionalGeneration,
    LlavaProcessor,
    BitsAndBytesConfig,
)

class LLaVALlama3Tagger(LLaVATaggerModel):
    def __init__(self, model_id: str = "llava-hf/llava-llama-3-8b-v1_1-transformers", use_gpu: bool = True):
        super().__init__(model_id=model_id, use_gpu=use_gpu)
        # model_dir 초기화
        if not self.model_dir:
            model_name = self.model_id.split('/')[-1]
            self.model_dir = Path("models") / model_name
    
    def _load_llava_config(self):
        """LLaVA-Llama-3 전용 설정 (독립적)"""
        import json
        from pathlib import Path
        
        config_path = Path("models/llava_llama3_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                _flush_print(f"[LLaVA-Llama-3] 설정 로드 실패: {e}")
        
        # 기본 설정 (Llama-3에 최적화)
        return {
            "max_tokens": 480,  # Llama-3의 향상된 추론 능력 활용
            "temperature": 0.12,  # Llama-3에 적합한 온도
            "top_p": 0.92,
            "num_beams": 1,
            "quantization_type": "4bit",
            "use_flash_attention": True,
            "prompt_style": "booru",
            "prompt_persona": "neutral",
            "custom_prompt": "",
            "custom_persona": ""
        }

    def load_model(self):
        """LLaVA-Llama-3 전용 로더"""
        import torch  # torch import 명시적 추가
        # 모델 캐싱 체크: 같은 모델이 이미 로드되어 있으면 재사용
        if (self._is_loaded and 
            self.model is not None and 
            self.processor is not None and 
            hasattr(self, '_cached_model_id') and 
            self._cached_model_id == self.model_id):
            _flush_print(f"[LLaVA-Llama-3] 모델 캐시 재사용: {self.model_id}")
            return

        # 메모리 정리: 항상 기존 모델을 완전히 정리 (RAM 크래시 방지)
        if self._is_loaded or self.model is not None or self.processor is not None:
            _flush_print(f"[LLaVA-Llama-3] 메모리 정리: {getattr(self, '_cached_model_id', 'None')} → {self.model_id}")
            self._cleanup_model_memory()
            # 모든 LLaVA 모델 타입을 한번에 언로드하여 메모리 누적 방지
            try:
                from llava_captioner_module import unload_all_llava_models
                unload_all_llava_models()
            except Exception as e:
                _flush_print(f"[LLaVA-Llama-3] 통합 언로드 실패, 개별 언로드 시도: {e}")
                unload_global_llava_llama3_tagger_model()
            _flush_print("[LLaVA-Llama-3] 기존 모델 완전 정리 완료")
        
        _flush_print(f"[LLaVA-Llama-3] 새 모델 로딩 시작: {self.model_id}")

        torch_dtype = torch.float16 if self.use_gpu else torch.float32
        from pathlib import Path
        model_name = self.model_id.split('/')[-1]
        local_model_path = Path("models") / model_name
        if not local_model_path.exists():
            raise RuntimeError(f"로컬 모델 경로 없음: {local_model_path}")

        load_kwargs = {
            "torch_dtype": torch_dtype,
            "low_cpu_mem_usage": True,
            "local_files_only": True,
        }
        quant = self.config.get("quantization_type", "4bit")
        if quant in ["4bit", "8bit"] and self.use_gpu:
            try:
                bnb = BitsAndBytesConfig(
                    load_in_4bit=(quant == "4bit"),
                    load_in_8bit=(quant == "8bit"),
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                load_kwargs["quantization_config"] = bnb
                load_kwargs["device_map"] = "auto"
                _flush_print(f"[LLaVA-Llama-3] ✅ {quant} 양자화 설정 적용됨")
            except Exception as e:
                _flush_print(f"[LLaVA-Llama-3] bitsandbytes 설정 실패, CPU 모드로 전환: {e}")
                load_kwargs.pop("quantization_config", None)
                load_kwargs["device_map"] = None
        elif quant in ["FP16", "16bit"] and self.use_gpu:
            # FP16 precision
            torch_dtype = torch.float16
            load_kwargs["torch_dtype"] = torch_dtype
            load_kwargs["device_map"] = "auto"
            _flush_print("[LLaVA-Llama-3] ✅ FP16 설정 적용됨")
        elif quant in ["BF16"] and self.use_gpu:
            # BF16 precision
            torch_dtype = torch.bfloat16
            load_kwargs["torch_dtype"] = torch_dtype
            load_kwargs["device_map"] = "auto"
            _flush_print("[LLaVA-Llama-3] ✅ BF16 설정 적용됨")
        elif quant in ["FP32", "32bit"] and self.use_gpu:
            # FP32 precision
            torch_dtype = torch.float32
            load_kwargs["torch_dtype"] = torch_dtype
            load_kwargs["device_map"] = "auto"
            _flush_print("[LLaVA-Llama-3] ✅ FP32 설정 적용됨")
        else:
            if self.use_gpu:
                load_kwargs["device_map"] = "auto"
            else:
                load_kwargs["device_map"] = None
            if quant != "none":
                _flush_print(f"[LLaVA-Llama-3] ⚠️ 지원하지 않는 양자화 타입: {quant}")

        if self.config.get("use_flash_attention", True) and self.use_gpu:
            load_kwargs["attn_implementation"] = "flash_attention_2"

        progress_capture = ModelLoadingProgressCapture(
            progress_callback=lambda msg, p: self.model_loading_progress.emit(msg, p),
            finished_callback=lambda: self.model_loading_finished.emit()
        )
        print(f"[DEBUG] LLaVA-Llama-3 진행률 콜백 설정 완료: {hasattr(self, 'model_loading_progress')}")
        self.model = progress_capture.capture_loading_progress(
            LlavaForConditionalGeneration.from_pretrained,
            str(local_model_path),
            **load_kwargs
        )
        self.processor = LlavaProcessor.from_pretrained(str(local_model_path), local_files_only=True)

        try:
            self.processor.tokenizer.padding_side = "left"
        except Exception:
            pass

        self.model.eval()
        self._is_loaded = True
        self._cached_model_id = self.model_id  # 캐시된 모델 ID 저장
        
        # VRAM 상태 및 device_map 진단 로깅
        try:
            if torch.cuda.is_available():
                gpu_mem_allocated = torch.cuda.memory_allocated(0) / 1024**3
                gpu_mem_reserved = torch.cuda.memory_reserved(0) / 1024**3
                _flush_print(f"[LLaVA-Llama-3] VRAM 상태 - 할당: {gpu_mem_allocated:.2f}GB, 예약: {gpu_mem_reserved:.2f}GB")
                
                # device_map 상태 확인
                device_map = getattr(self.model, "hf_device_map", None)
                if device_map:
                    _flush_print(f"[LLaVA-Llama-3] device_map: {device_map}")
                    # CPU 오프로딩 감지
                    cpu_layers = [k for k, v in device_map.items() if "cpu" in str(v)]
                    if cpu_layers:
                        _flush_print(f"⚠️ [LLaVA-Llama-3] CPU 오프로딩 감지! 레이어: {cpu_layers[:3]}... (총 {len(cpu_layers)}개)")
                    else:
                        _flush_print(f"✅ [LLaVA-Llama-3] 모든 레이어가 GPU에 로드됨")
                else:
                    _flush_print(f"[LLaVA-Llama-3] device_map 정보 없음")
        except Exception as e:
            _flush_print(f"[LLaVA-Llama-3] VRAM 진단 실패: {e}")
        
        self.model_loading_finished.emit()  # 모델 로딩 완료 신호
        _flush_print(f"[LLaVA-Llama-3] 로드 완료: {self.model_id}")

    def _cleanup_model_memory(self):
        """모델 메모리 완전 정리 (RAM 크래시 방지)"""
        try:
            # 모델과 프로세서 정리
            if hasattr(self, 'model') and self.model is not None:
                del self.model
                self.model = None
            if hasattr(self, 'processor') and self.processor is not None:
                del self.processor
                self.processor = None
            
            # 상태 플래그 리셋
            self._is_loaded = False
            if hasattr(self, '_cached_model_id'):
                delattr(self, '_cached_model_id')
            
            # Python 가비지 컬렉션 강제 실행
            import gc
            gc.collect()
            
            # CUDA 메모리 정리 (성능 최적화)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                # torch.cuda.synchronize() 제거 - 성능 저하 방지
            
            _flush_print("[LLaVA-Llama-3] 메모리 정리 완료")
        except Exception as e:
            _flush_print(f"[LLaVA-Llama-3] 메모리 정리 중 오류: {e}")

    def check_model_files(self) -> bool:
        """LLaVA-Llama-3 모델 파일들이 로컬에 있는지 확인"""
        if not self.model_dir:
            model_name = self.model_id.split('/')[-1]
            self.model_dir = Path("models") / model_name
        
        if not self.model_dir.exists():
            _flush_print(f"[LLaVA-Llama-3] 모델 디렉토리 없음: {self.model_dir}")
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
            _flush_print(f"[LLaVA-Llama-3] 모델 가중치 파일 없음: {self.model_dir}")
            return False
        
        # 필수 설정 파일들 확인
        for file_name in required_files:
            local_file = self.model_dir / file_name
            if not local_file.exists():
                _flush_print(f"[LLaVA-Llama-3] 필수 파일 없음: {local_file}")
                return False
        
        _flush_print(f"[LLaVA-Llama-3] 모델 파일 확인 완료: {self.model_dir}")
        return True
    
    def download_model(self):
        """LLaVA-Llama-3 모델 다운로드"""
        try:
            _flush_print(f"[LLaVA-Llama-3] 모델 다운로드 시작: {self.model_id}")
            
            # Hugging Face Hub를 사용한 모델 다운로드
            from huggingface_hub import snapshot_download
            
            # 모델 디렉토리 생성
            self.model_dir.mkdir(parents=True, exist_ok=True)
            
            # 모델 다운로드
            snapshot_download(
                repo_id=self.model_id,
                local_dir=str(self.model_dir),
                local_dir_use_symlinks=False
            )
            
            _flush_print(f"[LLaVA-Llama-3] 모델 다운로드 완료: {self.model_dir}")
            return True
            
        except Exception as e:
            _flush_print(f"[LLaVA-Llama-3] 모델 다운로드 실패: {e}")
            return False

    # 단일 이미지 predict_tags는 부모 구현 사용 (Llama-3 특화 기능 자동 적용)


# 전역 모델 인스턴스 관리
_global_llava_llama3_tagger_model = None

def get_global_llava_llama3_tagger_model(model_id: str = "llava-hf/llava-llama-3-8b-v1_1-transformers", use_gpu: bool = True):
    """전역 LLaVA-Llama-3 모델 인스턴스 반환 (통합 매니저 사용)"""
    # 통합 매니저를 통해 모델 반환
    from llava_captioner_module import get_unified_llava_model
    return get_unified_llava_model(model_id, use_gpu)

def unload_global_llava_llama3_tagger_model():
    """전역 LLaVA-Llama-3 모델 인스턴스 해제 및 메모리 정리"""
    global _global_llava_llama3_tagger_model
    
    if _global_llava_llama3_tagger_model is not None:
        try:
            # 모델과 프로세서 메모리에서 제거
            if hasattr(_global_llava_llama3_tagger_model, 'model') and _global_llava_llama3_tagger_model.model is not None:
                del _global_llava_llama3_tagger_model.model
                _global_llava_llama3_tagger_model.model = None
                _flush_print("[LLaVA-Llama-3] 모델 메모리에서 제거")
            
            if hasattr(_global_llava_llama3_tagger_model, 'processor') and _global_llava_llama3_tagger_model.processor is not None:
                del _global_llava_llama3_tagger_model.processor
                _global_llava_llama3_tagger_model.processor = None
                _flush_print("[LLaVA-Llama-3] 프로세서 메모리에서 제거")
            
            # 전역 변수 해제
            _global_llava_llama3_tagger_model = None
            
            # GPU 메모리 캐시 정리
            import gc
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                _flush_print("[LLaVA-Llama-3] GPU 메모리 캐시 정리 완료")
            
            _flush_print("[LLaVA-Llama-3] 전역 모델 인스턴스 해제 및 메모리 정리 완료")
        except Exception as e:
            _flush_print(f"[LLaVA-Llama-3] 모델 언로딩 중 오류: {e}")
            _global_llava_llama3_tagger_model = None


from PySide6.QtCore import QThread, Signal

class LLaVALlama3DownloadThread(QThread):
    """LLaVA-Llama-3 모델 다운로드 전용 스레드"""
    llava_progress_updated = Signal(str, int, int, str)  # filename, downloaded, total, status
    download_finished = Signal(bool)
    error_occurred = Signal(str)
    
    def __init__(self, model_id: str, use_gpu: bool = True):
        super().__init__()
        self.model_id = model_id
        self.use_gpu = use_gpu
    
    def run(self):
        try:
            llava_download_progress_emitter.llava_progress_updated.connect(self.llava_progress_updated)
            ok = LLaVACaptionerModule(self.model_id, self.use_gpu).download_model_files()
            self.download_finished.emit(bool(ok))
        except Exception as e:
            self.error_occurred.emit(f"LLaVA-Llama-3 다운로드 실패: {e}")
            self.download_finished.emit(False)

class LLaVALlama3TaggerThread(QThread):
    progress_updated = Signal(int, int)
    model_loading_started = Signal(str)
    model_loading_progress = Signal(str, int)
    model_loading_finished = Signal()
    tag_generated = Signal(str, list)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, image_paths: List[str], model_id: str, use_gpu: bool = True):
        super().__init__()
        self.image_paths = image_paths
        self.model_id = model_id
        self.use_gpu = use_gpu

    def run(self):
        try:
            # 전역 모델 인스턴스 사용
            self._tagger = get_global_llava_llama3_tagger_model(model_id=self.model_id, use_gpu=self.use_gpu)
            
            # 시그널 포워딩 (체크포인트 로딩 진행률만 유지)
            self._tagger.progress_updated.connect(self.progress_updated)
            self._tagger.model_loading_progress.connect(self.model_loading_progress)
            self._tagger.model_loading_finished.connect(self.model_loading_finished)
            self._tagger.tag_generated.connect(self.tag_generated)
            self._tagger.finished.connect(self.finished)
            self._tagger.error_occurred.connect(self.error_occurred)
            
            total = len(self.image_paths)
            
            # 태그 결과 수집
            tag_results = []
            
            for i, p in enumerate(self.image_paths, 1):
                tags = self._tagger.predict_tags(p)
                tag_results.append(tags)
                self.tag_generated.emit(p, tags)
                self.progress_updated.emit(i, total)
            
            # 타임머신 로그 기록 (공통 함수 사용)
            try:
                from timemachine_log import log_ai_batch_tagging
                log_ai_batch_tagging("LLaVA-Llama-3", self.model_id, self.image_paths, tag_results)
            except Exception:
                pass
            
            self.finished.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit()
