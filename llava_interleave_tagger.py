# llava_interleave_tagger.py
# LLaVA-Interleave 전용 확장 추론 모듈 (멀티이미지/시퀀스 입력 강화)
# - 로딩: LlavaNextForConditionalGeneration + LlavaNextProcessor (인터리브 체크포인트는 NeXT 타입)
# - 멀티이미지 전용 predict_tags_multi 제공

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
    LlavaNextForConditionalGeneration,
    LlavaNextProcessor,
    BitsAndBytesConfig,
)

class LLaVAInterleaveTagger(LLaVATaggerModel):
    def __init__(self, model_id: str = "llava-hf/llava-interleave-qwen-7b-hf", use_gpu: bool = True):
        super().__init__(model_id=model_id, use_gpu=use_gpu)
        # model_dir 초기화
        if not self.model_dir:
            model_name = self.model_id.split('/')[-1]
            self.model_dir = Path("models") / model_name
    
    def _contains_non_english(self, text):
        """텍스트에 영어가 아닌 문자가 포함되어 있는지 확인"""
        import re
        # 영어, 숫자, 공백, 언더스코어, 하이픈만 허용
        english_pattern = re.compile(r'^[a-zA-Z0-9\s_-]+$')
        
        # 영어가 아닌 문자가 있으면 제거
        if not english_pattern.match(text):
            return True
        
        # 숫자만 있는 경우 제거 (1, 2, 3 등)
        if re.match(r'^\d+$', text.strip()):
            return True
        
        # 공백만 있는 경우 제거
        if not text.strip():
            return True
            
        return False
    
    def _load_llava_config(self):
        """LLaVA-Interleave 전용 설정 (독립적)"""
        import json
        from pathlib import Path
        
        config_path = Path("models/llava_interleave_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                _flush_print(f"[LLaVA-Interleave] 설정 로드 실패: {e}")
        
        # 기본 설정 (Interleave에 최적화)
        return {
            "max_tokens": 600,  # 멀티이미지 처리로 더 긴 토큰 필요
            "temperature": 0.15,
            "top_p": 0.9,
            "num_beams": 1,
            "quantization_type": "4bit",
            "use_flash_attention": True,
            "prompt_style": "sentence_caption",
            "prompt_persona": "neutral",
            "custom_prompt": "",
            "custom_persona": ""
        }

    def load_model(self):
        import torch  # torch import 명시적 추가
        # 모델 캐싱 체크: 같은 모델이 이미 로드되어 있으면 재사용
        if (self._is_loaded and 
            self.model is not None and 
            self.processor is not None and 
            hasattr(self, '_cached_model_id') and 
            self._cached_model_id == self.model_id):
            _flush_print(f"[LLaVA-Interleave] 모델 캐시 재사용: {self.model_id}")
            return

        # 메모리 정리: 항상 기존 모델을 완전히 정리 (RAM 크래시 방지)
        if self._is_loaded or self.model is not None or self.processor is not None:
            _flush_print(f"[LLaVA-Interleave] 메모리 정리: {getattr(self, '_cached_model_id', 'None')} → {self.model_id}")
            self._cleanup_model_memory()
            # 모든 LLaVA 모델 타입을 한번에 언로드하여 메모리 누적 방지
            try:
                from llava_captioner_module import unload_all_llava_models
                unload_all_llava_models()
            except Exception as e:
                _flush_print(f"[LLaVA-Interleave] 통합 언로드 실패, 개별 언로드 시도: {e}")
                unload_global_llava_interleave_tagger_model()
            _flush_print("[LLaVA-Interleave] 기존 모델 완전 정리 완료")
        
        _flush_print(f"[LLaVA-Interleave] 새 모델 로딩 시작: {self.model_id}")

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
                _flush_print(f"[LLaVA-Interleave] ✅ {quant} 양자화 설정 적용됨")
            except Exception as e:
                _flush_print(f"[LLaVA-Interleave] bitsandbytes 설정 실패, CPU 모드로 전환: {e}")
                load_kwargs.pop("quantization_config", None)
                load_kwargs["device_map"] = None
        elif quant in ["FP16", "16bit"] and self.use_gpu:
            # FP16 precision
            torch_dtype = torch.float16
            load_kwargs["torch_dtype"] = torch_dtype
            load_kwargs["device_map"] = "auto"
            _flush_print("[LLaVA-Interleave] ✅ FP16 설정 적용됨")
        elif quant in ["BF16"] and self.use_gpu:
            # BF16 precision
            torch_dtype = torch.bfloat16
            load_kwargs["torch_dtype"] = torch_dtype
            load_kwargs["device_map"] = "auto"
            _flush_print("[LLaVA-Interleave] ✅ BF16 설정 적용됨")
        elif quant in ["FP32", "32bit"] and self.use_gpu:
            # FP32 precision
            torch_dtype = torch.float32
            load_kwargs["torch_dtype"] = torch_dtype
            load_kwargs["device_map"] = "auto"
            _flush_print("[LLaVA-Interleave] ✅ FP32 설정 적용됨")
        else:
            if self.use_gpu:
                load_kwargs["device_map"] = "auto"
            else:
                load_kwargs["device_map"] = None
            if quant != "none":
                _flush_print(f"[LLaVA-Interleave] ⚠️ 지원하지 않는 양자화 타입: {quant}")

        if self.config.get("use_flash_attention", True) and self.use_gpu:
            load_kwargs["attn_implementation"] = "flash_attention_2"

        progress_capture = ModelLoadingProgressCapture(
            progress_callback=lambda msg, p: self.model_loading_progress.emit(msg, p),
            finished_callback=lambda: self.model_loading_finished.emit()
        )
        print(f"[DEBUG] LLaVA-Interleave 진행률 콜백 설정 완료: {hasattr(self, 'model_loading_progress')}")
        self.model = progress_capture.capture_loading_progress(
            LlavaNextForConditionalGeneration.from_pretrained,
            str(local_model_path),
            **load_kwargs
        )
        self.processor = LlavaNextProcessor.from_pretrained(str(local_model_path), local_files_only=True)

        try:
            self.processor.tokenizer.padding_side = "left"
            self.processor.patch_size = getattr(self.model.config.vision_config, "patch_size", None)
            self.processor.vision_feature_select_strategy = getattr(self.model.config, "vision_feature_select_strategy", None)
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
                _flush_print(f"[LLaVA-Interleave] VRAM 상태 - 할당: {gpu_mem_allocated:.2f}GB, 예약: {gpu_mem_reserved:.2f}GB")
                
                # device_map 상태 확인
                device_map = getattr(self.model, "hf_device_map", None)
                if device_map:
                    _flush_print(f"[LLaVA-Interleave] device_map: {device_map}")
                    # CPU 오프로딩 감지
                    cpu_layers = [k for k, v in device_map.items() if "cpu" in str(v)]
                    if cpu_layers:
                        _flush_print(f"⚠️ [LLaVA-Interleave] CPU 오프로딩 감지! 레이어: {cpu_layers[:3]}... (총 {len(cpu_layers)}개)")
                    else:
                        _flush_print(f"✅ [LLaVA-Interleave] 모든 레이어가 GPU에 로드됨")
                else:
                    _flush_print(f"[LLaVA-Interleave] device_map 정보 없음")
        except Exception as e:
            _flush_print(f"[LLaVA-Interleave] VRAM 진단 실패: {e}")
        
        self.model_loading_finished.emit()  # 모델 로딩 완료 신호
        _flush_print(f"[LLaVA-Interleave] 로드 완료: {self.model_id}")

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
            
            _flush_print("[LLaVA-Interleave] 메모리 정리 완료")
        except Exception as e:
            _flush_print(f"[LLaVA-Interleave] 메모리 정리 중 오류: {e}")

    # 단일 이미지 predict_tags는 공통 그대로 사용

    def predict_tags_multi(self, image_paths: List[str], max_tags: int = 40) -> List[Tuple[str, float]]:
        import time, re
        if not image_paths:
            return []

        self.config = self._load_llava_config()
        if not self._is_loaded or self.model is None or self.processor is None:
            self.load_model()

        # multi_image_max 설정 적용
        max_images = self.config.get("multi_image_max", 4)
        if len(image_paths) > max_images:
            _flush_print(f"[LLaVA-Interleave] 이미지 수 제한: {len(image_paths)} → {max_images}")
            image_paths = image_paths[:max_images]
        
        images = [Image.open(p).convert("RGB") for p in image_paths]
        
        # 새로운 프롬프트 템플릿 사용
        prompt_style = self.config.get("prompt_style", "sentence_caption")
        prompt_persona = self.config.get("prompt_persona", "neutral")
        custom_prompt = self.config.get("custom_prompt", "")
        custom_persona = self.config.get("custom_persona", "")
        
        # 커스텀 프롬프트 우선순위 처리
        if prompt_style == "custom" and custom_prompt and custom_prompt.strip():
            base_prompt = custom_prompt.strip()
            _flush_print(f"[LLaVA-Interleave] 커스텀 프롬프트 사용: '{base_prompt}'")
        else:
            # 기본 템플릿 사용
            prompt_templates = {
                "booru": "Based on the provided images, generate Booru tags. Use only English words with underscores. Separate each tag with commas. Only describe what is actually visible in the images. Do not provide explanations, only tags.",
                "sentence_caption": "Describe these images.",
                "midjourney": "Based on the provided images, write MidJourney prompts. Use creative English phrases. Only describe what is actually visible in the images. Only prompt text. Do not write incomplete sentences.",
                "art_critic": "Based on the provided images, analyze like an art critic. Use descriptive English phrases. Only analyze what is actually visible in the images. Only analysis. Do not write incomplete sentences.",
                "detailed": "Based on the provided images, describe in detail. Use descriptive English sentences. Only describe what is actually visible in the images. Only description. Do not write incomplete sentences.",
                "brief": "Based on the provided images, describe briefly. Use short English phrases. Only describe what is actually visible in the images. Only description. Do not write incomplete sentences."
            }
            base_prompt = prompt_templates.get(prompt_style)
        
        # 페르소나 톤 설정
        if prompt_persona == "custom" and custom_persona and custom_persona.strip():
            persona_tone = f" {custom_persona.strip()}"
            _flush_print(f"[LLaVA-Interleave] 커스텀 페르소나 사용: '{persona_tone}'")
        else:
            persona_tones = {
                "neutral": "",
                "professional": " Use a professional and objective tone.",
                "friendly": " Use a warm and friendly tone.",
                "creative": " Use a creative and artistic tone.",
                "analytical": " Use an analytical and systematic tone.",
                "casual": " Use a casual and conversational tone."
            }
            persona_tone = persona_tones.get(prompt_persona, "")
        
        # 프롬프트 + 페르소나 조합
        prompt_text = base_prompt + persona_tone
        
        # 디버깅: 프롬프트 조합 과정 로그 출력
        _flush_print(f"[LLaVA-Interleave] 프롬프트 조합 디버깅:")
        _flush_print(f"  - 선택된 스타일: {prompt_style}")
        _flush_print(f"  - 선택된 페르소나: {prompt_persona}")
        _flush_print(f"  - 기본 프롬프트: '{base_prompt}'")
        _flush_print(f"  - 페르소나 톤: '{persona_tone}'")
        _flush_print(f"  - 최종 조합: '{prompt_text}'")
        
        # 공식 멀티이미지 형식
        conversation = [
            {
                "role": "user",
                "content": ([{"type": "image"} for _ in images] + [
                    {"type": "text", "text": prompt_text}
                ])
            }
        ]
        prompt = self.processor.apply_chat_template(conversation, add_generation_prompt=True)
        inputs = self.processor(images, prompt, return_tensors="pt")

        # 양자화 설정에 따른 dtype 결정 (설정 우선)
        quantization_type = self.config.get("quantization_type", "none")
        if quantization_type == "BF16":
            dtype = torch.bfloat16
        elif quantization_type in ["FP16", "16bit"]:
            dtype = torch.float16
        elif quantization_type in ["FP32", "32bit"]:
            dtype = torch.float32
        elif quantization_type in ["4bit", "8bit"]:
            # 4bit/8bit 양자화는 계산 시 float16 사용
            dtype = torch.float16
        else:
            # 설정이 없거나 "none"인 경우 모델의 실제 dtype 사용
            if hasattr(self.model, "dtype"):
                dtype = self.model.dtype
            else:
                dtype = torch.float16 if self.use_gpu else torch.float32

        # 양자화 설정에 따른 명확한 로그 출력
        if quantization_type == "BF16":
            _flush_print(f"[LLaVA-Interleave] 사용할 dtype: {dtype} (BF16 정밀도 - 16비트 Brain Float)")
        elif quantization_type in ["FP16", "16bit"]:
            _flush_print(f"[LLaVA-Interleave] 사용할 dtype: {dtype} (FP16 정밀도 - 16비트 Float)")
        elif quantization_type in ["FP32", "32bit"]:
            _flush_print(f"[LLaVA-Interleave] 사용할 dtype: {dtype} (FP32 정밀도 - 32비트 Float)")
        elif quantization_type in ["4bit", "8bit"]:
            _flush_print(f"[LLaVA-Interleave] 사용할 dtype: {dtype} (계산용 - {quantization_type} 양자화 모델)")
        else:
            _flush_print(f"[LLaVA-Interleave] 사용할 dtype: {dtype} (기본 설정 - 모델과 일관성 유지)")

        if self.config.get("quantization_type", "none") in ["4bit", "8bit"]:
            device = next(self.model.parameters()).device
        else:
            device = 0 if self.use_gpu else "cpu"

        for k, v in inputs.items():
            if hasattr(v, "to"):
                if "pixel" in k.lower():
                    inputs[k] = v.to(device, dtype=dtype)
                else:
                    inputs[k] = v.to(device)

        gen_ids, _ = self._generate_with_model(inputs)
        input_len = inputs["input_ids"].shape[1]
        new_tokens = gen_ids[0][input_len:]
        caption = self.processor.tokenizer.decode(new_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)

        # 모든 스타일에서 콤마 제거 후 구둣점 기준으로 분리
        caption_no_comma = re.sub(r',', '', caption or "")
        tags = re.split(r'[.\n\r]+', caption_no_comma)
        
        cleaned = []
        for t in tags:
            t = t.strip()
            t = re.sub(r"^[,\n\r.]+|[,\n\r.]+$", "", t)
            
            # 특수기호 제거: [,],',",&,$
            t = re.sub(r'[\[\]\'\"&$]', '', t)
            t = t.strip()
            
            # 타국어 태그 필터링 (한글, 일본어, 중국어 등)
            if self._contains_non_english(t):
                continue  # 타국어 태그는 건너뛰기
            
            if t:
                cleaned.append(t)
        
        # 완전 동일한 중복 제거 (대소문자 구분)
        cleaned = list(dict.fromkeys(cleaned))  # 순서 유지하면서 중복 제거

        return [(t, -1.0) for t in cleaned[:max_tags]]
    
    def check_model_files(self) -> bool:
        """LLaVA-Interleave 모델 파일들이 로컬에 있는지 확인"""
        if not self.model_dir:
            model_name = self.model_id.split('/')[-1]
            self.model_dir = Path("models") / model_name
        
        if not self.model_dir.exists():
            _flush_print(f"[LLaVA-Interleave] 모델 디렉토리 없음: {self.model_dir}")
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
            _flush_print(f"[LLaVA-Interleave] 모델 가중치 파일 없음: {self.model_dir}")
            return False
        
        # 필수 설정 파일들 확인
        for file_name in required_files:
            local_file = self.model_dir / file_name
            if not local_file.exists():
                _flush_print(f"[LLaVA-Interleave] 필수 파일 없음: {local_file}")
                return False
        
        _flush_print(f"[LLaVA-Interleave] 모델 파일 확인 완료: {self.model_dir}")
        return True
    
    def download_model(self):
        """LLaVA-Interleave 모델 다운로드"""
        try:
            _flush_print(f"[LLaVA-Interleave] 모델 다운로드 시작: {self.model_id}")
            
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
            
            _flush_print(f"[LLaVA-Interleave] 모델 다운로드 완료: {self.model_dir}")
            return True
            
        except Exception as e:
            _flush_print(f"[LLaVA-Interleave] 모델 다운로드 실패: {e}")
            return False


# 전역 모델 인스턴스 관리
_global_llava_interleave_tagger_model = None

def get_global_llava_interleave_tagger_model(model_id: str = "llava-hf/llava-interleave-qwen-7b-hf", use_gpu: bool = True):
    """전역 LLaVA-Interleave 모델 인스턴스 반환 (통합 매니저 사용)"""
    # 통합 매니저를 통해 모델 반환
    from llava_captioner_module import get_unified_llava_model
    return get_unified_llava_model(model_id, use_gpu)

def unload_global_llava_interleave_tagger_model():
    """전역 LLaVA-Interleave 모델 인스턴스 해제 및 메모리 정리"""
    global _global_llava_interleave_tagger_model
    
    if _global_llava_interleave_tagger_model is not None:
        try:
            # 모델과 프로세서 메모리에서 제거
            if hasattr(_global_llava_interleave_tagger_model, 'model') and _global_llava_interleave_tagger_model.model is not None:
                del _global_llava_interleave_tagger_model.model
                _global_llava_interleave_tagger_model.model = None
                _flush_print("[LLaVA-Interleave] 모델 메모리에서 제거")
            
            if hasattr(_global_llava_interleave_tagger_model, 'processor') and _global_llava_interleave_tagger_model.processor is not None:
                del _global_llava_interleave_tagger_model.processor
                _global_llava_interleave_tagger_model.processor = None
                _flush_print("[LLaVA-Interleave] 프로세서 메모리에서 제거")
            
            # 전역 변수 해제
            _global_llava_interleave_tagger_model = None
            
            # GPU 메모리 캐시 정리
            import gc
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                _flush_print("[LLaVA-Interleave] GPU 메모리 캐시 정리 완료")
            
            _flush_print("[LLaVA-Interleave] 전역 모델 인스턴스 해제 및 메모리 정리 완료")
        except Exception as e:
            _flush_print(f"[LLaVA-Interleave] 모델 언로딩 중 오류: {e}")
            _global_llava_interleave_tagger_model = None


from PySide6.QtCore import QThread, Signal

class LLaVAInterleaveDownloadThread(QThread):
    """LLaVA-Interleave 모델 다운로드 전용 스레드"""
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
            self.error_occurred.emit(f"LLaVA-Interleave 다운로드 실패: {e}")
            self.download_finished.emit(False)

class LLaVAInterleaveTaggerThread(QThread):
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
            self._tagger = get_global_llava_interleave_tagger_model(model_id=self.model_id, use_gpu=self.use_gpu)
            
            # 시그널 포워딩 (체크포인트 로딩 진행률만 유지)
            self._tagger.progress_updated.connect(self.progress_updated)
            self._tagger.model_loading_progress.connect(self.model_loading_progress)
            self._tagger.model_loading_finished.connect(self.model_loading_finished)
            self._tagger.tag_generated.connect(self.tag_generated)
            self._tagger.finished.connect(self.finished)
            self._tagger.error_occurred.connect(self.error_occurred)
            
            # 멀티이미지 한 번에 처리 예시: 필요에 따라 묶음 전략 조정
            tags = self._tagger.predict_tags_multi(self.image_paths)
            for i, p in enumerate(self.image_paths, 1):
                self.tag_generated.emit(p, tags)  # 동일 태그 브로드캐스트(원하면 분리 처리 가능)
                self.progress_updated.emit(i, len(self.image_paths))
            self.finished.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit()
