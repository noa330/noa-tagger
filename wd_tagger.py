#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WD Tagger - Reference-style pipeline (config.json: size only, everything else same as reference)
- model.onnx / selected_tags.csv / config.json(있으면) 를 현재 스크립트 경로에 저장/사용
- 파이프라인:
  * RGBA → 흰색 합성
  * 비율 유지 패딩(정사각) → target_size로 리사이즈
  * RGB → BGR (채널 스왑)
  * 정규화/스케일링 없음 (0~255 float)
  * NHWC (1,H,W,3) 입력
  * 출력값(preds)을 그대로 confidence로 사용 (sigmoid 등 없음)
  * rating=카테고리9(사전 형식), general=0/character=4 임계값 컷
"""

import csv
import json
import os
import shutil
from pathlib import Path
from typing import List, Tuple, Optional, Dict

import numpy as np
from PIL import Image as PILImage
import onnxruntime as ort
import os
import huggingface_hub
import requests
from PySide6.QtCore import QObject, Signal, QThread

# ▼ 추가: pip 경로 정확 탐색 + DLL 검색 경로 주입용
import sys
import importlib.util


# 전역 다운로드 진행 상황 시그널 (QObject 인스턴스 필요)
class DownloadProgressEmitter(QObject):
    progress_updated = Signal(str, int, int, str)  # filename, downloaded, total, status

download_progress_emitter = DownloadProgressEmitter()


def check_gpu_availability():
    """GPU 사용 가능 여부 확인"""
    try:
        # ONNX Runtime에서 사용 가능한 providers 확인
        available_providers = ort.get_available_providers()
        print(f"사용 가능한 providers: {available_providers}")
        
        if 'CUDAExecutionProvider' in available_providers:
            print("✅ CUDA GPU 사용 가능")
            return True
        else:
            print("❌ CUDA GPU 사용 불가능")
            return False
    except Exception as e:
        print(f"GPU 확인 중 오류: {e}")
        return False


MODEL_FILENAME = "model.onnx"
LABEL_FILENAME = "selected_tags.csv"  # 모델 다운로드용
CONFIG_CANDIDATES = ["config.json", "preprocessor_config.json"]
TAGGER_CONFIG_FILE = "models/wd_tagger_config.json"  # WD 전용 설정 파일

# 카테고리 정의(레퍼런스와 동일)
RATING_CAT = 9
GENERAL_CAT = 0
CHAR_CAT = 4

# kaomojis(언더스코어 유지)
kaomojis = [
    "0_0","(o)_(o)","+_+","+_-","._.","<o>_<o>","<|>_<|>","=_=",
    ">_<","3_3","6_9",">_o","@_@","^_^","o_o","u_u","x_x","|_|","||_||",
]


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _migrate_old_models():
    """기존 스크립트 폴더에 저장된 모델 파일들을 모델별 폴더로 이동"""
    script_dir = _script_dir()
    
    # 기존 파일들 확인
    old_files = {
        "model.onnx": "wd-vit-large-tagger-v3",  # 기본 모델로 가정
        "selected_tags.csv": "wd-vit-large-tagger-v3",
        "config.json": "wd-vit-large-tagger-v3",
        "preprocessor_config.json": "wd-vit-large-tagger-v3"
    }
    
    for filename, default_model in old_files.items():
        old_path = script_dir / filename
        if old_path.exists():
            # 모델별 폴더 생성
            model_dir = script_dir / "models" / default_model
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # 새 경로
            new_path = model_dir / filename
            
            # 파일 이동
            if not new_path.exists():
                print(f"모델 파일 마이그레이션: {old_path} -> {new_path}")
                old_path.rename(new_path)
            else:
                print(f"모델 파일 이미 존재: {new_path}")
                old_path.unlink()  # 기존 파일 삭제


def _ensure_local_from_hub(repo_id: str, repo_filename: str, local_name: str, file_index: int = 1, total_files: int = 1) -> Path:
    """
    HF Hub에서 받아서 모델별 폴더에 '실제 파일'로 둔다(심링크 X).
    캐시를 완전히 우회하고 직접 다운로드.
    LLaVA와 통일된 고급 기능 포함: 파일 검증, 이어받기, 진행률 표시
    """
    # 모델별 폴더 생성 (repo_id에서 모델명 추출)
    model_name = repo_id.split('/')[-1]  # "SmilingWolf/wd-vit-large-tagger-v3" -> "wd-vit-large-tagger-v3"
    model_dir = _script_dir() / "models" / model_name
    model_dir.mkdir(parents=True, exist_ok=True)
    
    dst = model_dir / local_name
    
    # 기존 파일이 있으면 크기 확인 후 재사용 또는 이어받기 (LLaVA와 통일)
    if dst.is_file():
        try:
            # 파일 크기 확인을 위해 HEAD 요청 (리다이렉트 추적 추가)
            download_url = f"https://huggingface.co/{repo_id}/resolve/main/{repo_filename}"
            head_response = requests.head(download_url, allow_redirects=True, timeout=15)
            if head_response.status_code == 200:
                expected_size = int(head_response.headers.get('content-length', 0))
                actual_size = dst.stat().st_size
                
                if actual_size == expected_size and expected_size > 0:
                    print(f"기존 파일 사용 (완전함): {dst}")
                    return dst
                elif expected_size > 0 and actual_size < expected_size:
                    print(f"파일 불완전, 이어받기: {dst} ({actual_size}/{expected_size} bytes)")
                    # 불완전한 파일은 삭제하지 않고 이어받기용으로 유지
                elif expected_size == 0:
                    print(f"서버에서 크기 정보 없음, 기존 파일 유지: {dst}")
                    return dst
                elif actual_size > expected_size:
                    print(f"파일 크기 초과 (손상 가능성), 재다운로드: {dst}")
                    dst.unlink()
                else:
                    print(f"파일 크기 불일치, 재다운로드: {dst}")
                    dst.unlink()
            else:
                print(f"파일 확인 실패 (HTTP {head_response.status_code}), 재다운로드: {dst}")
                dst.unlink()
        except Exception as e:
            print(f"파일 확인 중 오류, 재다운로드: {e}")
            dst.unlink()
    
    print(f"WD 다운로드 시작: {repo_id}/{repo_filename}")
    try:
        # 다운로드 시작 시그널 (간소화)
        try:
            download_progress_emitter.progress_updated.emit(repo_filename, 0, 0, f"[{file_index}/{total_files}]")
        except Exception:
            pass
        
        # 직접 다운로드 URL 생성
        download_url = f"https://huggingface.co/{repo_id}/resolve/main/{repo_filename}"
        
        print(f"다운로드 URL: {download_url}")
        
        # 이어받기 지원을 위한 파일 크기 확인
        actual_size = 0
        if dst.is_file():
            actual_size = dst.stat().st_size
            print(f"기존 파일 크기: {actual_size / (1024*1024):.1f} MB")
        
        # HTTP Range 헤더로 이어받기 시도
        headers = {}
        if actual_size > 0:
            headers['Range'] = f'bytes={actual_size}-'
            print(f"이어받기 시도: {actual_size} bytes부터")
        
        # requests로 직접 다운로드 (Range 헤더 포함)
        response = requests.get(download_url, stream=True, headers=headers)
        response.raise_for_status()
        
        # 파일 크기 확인
        if response.status_code == 206:  # Partial Content (이어받기 성공)
            content_range = response.headers.get('content-range', '')
            if content_range:
                # Content-Range: bytes 200-1023/1024 형태에서 총 크기 추출
                total_size = int(content_range.split('/')[-1])
                print(f"이어받기 성공: {actual_size}/{total_size} bytes")
            else:
                # Content-Range가 없으면 Content-Length + 기존 크기
                total_size = actual_size + int(response.headers.get('content-length', 0))
                print(f"이어받기 성공 (추정): {actual_size}/{total_size} bytes")
        else:  # 200 OK (처음부터 다운로드)
            total_size = int(response.headers.get('content-length', 0))
            print(f"처음부터 다운로드: {total_size / (1024*1024):.1f} MB")
            actual_size = 0  # 처음부터 받으므로 0으로 리셋
        
        # 파일 크기 정보 시그널 (간소화)
        try:
            download_progress_emitter.progress_updated.emit(
                repo_filename, 
                actual_size, 
                total_size,  # 항상 바이트로 통일
                f"[{file_index}/{total_files}]"
            )
        except Exception:
            pass
        
        # 파일 저장 (이어받기 지원)
        downloaded = actual_size
        next_emit = actual_size
        emit_step = 1024*1024 if total_size >= 1024*1024 else 100*1024  # 1MB 또는 100KB
        
        # 파일 모드 결정 (이어받기면 'ab', 처음부터면 'wb')
        file_mode = 'ab' if actual_size > 0 else 'wb'
        
        with open(dst, file_mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 진행률 업데이트 (누적 임계치 방식)
                    if total_size > 0 and (downloaded >= next_emit or downloaded == total_size):
                        try:
                            download_progress_emitter.progress_updated.emit(
                                repo_filename, 
                                downloaded,  # 바이트로 통일
                                total_size,  # 바이트로 통일
                                f"[{file_index}/{total_files}] {downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB"
                            )
                            next_emit = downloaded + emit_step
                        except Exception:
                            pass
        
        print(f'\n다운로드 완료: {dst}')
        
        # 다운로드 완료 시그널
        try:
            download_progress_emitter.progress_updated.emit(
                repo_filename, 
                total_size, 
                total_size, 
                "다운로드 완료!"
            )
        except Exception:
            pass
        
        return dst
        
    except Exception as e:
        print(f"직접 다운로드 실패: {e}")
        print("Hugging Face Hub 캐시 방식으로 재시도...")
        
        # 실패하면 기존 방식으로 재시도
        try:
            cached = huggingface_hub.hf_hub_download(
                repo_id, filename=repo_filename, local_dir=str(_script_dir()), local_dir_use_symlinks=False
            )
            cached_path = Path(cached)
            if cached_path.resolve() != dst.resolve():
                shutil.copy2(cached_path, dst)
            print(f"캐시 방식 다운로드 완료: {dst}")
            return dst
        except Exception as e2:
            print(f"캐시 방식도 실패: {e2}")
            raise


def _maybe_local_config(repo_id: str) -> Optional[Path]:
    # 모델별 폴더 경로 생성
    model_name = repo_id.split('/')[-1]
    model_dir = _script_dir() / "models" / model_name
    
    # 1) 모델별 폴더에서 우선 검색
    for name in CONFIG_CANDIDATES:
        p = model_dir / name
        if p.is_file():
            return p
    
    # 2) 허브에서 시도 (모델별 폴더에 저장)
    for name in CONFIG_CANDIDATES:
        try:
            return _ensure_local_from_hub(repo_id, name, name)
        except Exception:
            continue
    return None


def _safe_int(x):
    try:
        return int(x)
    except Exception:
        return None


def load_tagger_config():
    """전 모델 공통 설정 파일 로드"""
    config_path = _script_dir() / TAGGER_CONFIG_FILE
    default_config = {
        "general_threshold": 0.35,
        "character_threshold": 0.85,
        "character_mcut_min": 0.15,
        "max_tags": 30,
        "general_mcut_enabled": False,
        "character_mcut_enabled": False,
        "general_mcut_min_enabled": False,
        "general_mcut_min": 0.15,
        "character_mcut_min_enabled": False,
        "apply_sigmoid": False,
        "tta_enabled": False,
        "tta_horizontal_flip": True,
        "tta_merge_mode": "mean"
    }
    
    try:
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
                # 기본값과 병합 (누락된 키가 있으면 기본값 사용)
                for key, default_value in default_config.items():
                    if key not in config:
                        config[key] = default_value
                return config
        else:
            # 설정 파일이 없으면 기본값으로 생성
            save_tagger_config(default_config)
            return default_config
    except Exception as e:
        print(f"설정 파일 로드 실패: {e}, 기본값 사용")
        return default_config


def save_tagger_config(config):
    """전 모델 공통 설정 파일 저장"""
    config_path = _script_dir() / TAGGER_CONFIG_FILE
    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ 설정 파일 저장 완료: {config_path}")
    except Exception as e:
        print(f"❌ 설정 파일 저장 실패: {e}")


def get_tagger_config_value(key, default_value=None):
    """설정 파일에서 특정 값 가져오기"""
    config = load_tagger_config()
    return config.get(key, default_value)


class WdTaggerModel(QObject):
    progress_updated = Signal(int, int)
    tag_generated = Signal(str, list)    # image_path, List[(tag, score)]
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        model_id: str = "SmilingWolf/wd-vit-large-tagger-v3",
        general_threshold: float = None,
        character_threshold: float = None,
        pad_rgb=(255, 255, 255),
        use_gpu: bool = True,
    ):
        super().__init__()
        self.model_id = model_id
        # 설정 파일에서 기본값 로드
        self.general_threshold = general_threshold if general_threshold is not None else get_tagger_config_value("general_threshold", 0.35)
        self.character_threshold = character_threshold if character_threshold is not None else get_tagger_config_value("character_threshold", 0.85)
        self.pad_rgb = pad_rgb
        self.use_gpu = use_gpu

        self.session: Optional[ort.InferenceSession] = None
        self.is_loaded = False

        # 태그/인덱스
        self.tag_names: List[str] = []
        self.rating_indexes: List[int] = []
        self.general_indexes: List[int] = []
        self.character_indexes: List[int] = []

        # config에서 읽을 값(크기만 반영)
        self.target_size = 448  # 기본값
        
        # LLaVA와 통일된 다운로드 기능을 위한 속성
        self.model_dir = None

        # ▼ 추가: Windows에서 add_dll_directory 핸들 유지
        self._dll_dir_handles: List[object] = []

    # ────────────── LLaVA와 통일된 고급 다운로드 기능 ──────────────
    
    def download_model_files(self):
        """WD 모델 파일들 다운로드 (LLaVA와 통일된 고급 방식)"""
        try:
            print(f"WD 모델 파일 다운로드 시작: {self.model_id}")
            
            # WD 모델의 필수 파일들 정의
            required_files = ['model.onnx', 'selected_tags.csv', 'config.json']
            total_files = len(required_files)
            
            print(f"다운로드할 파일 목록 ({total_files}개):")
            for i, filename in enumerate(required_files):
                print(f"  {i+1}. {filename}")
            
            # 전체 다운로드 시작 시그널 (LLaVA와 동일한 형태 - 간소화)
            try:
                download_progress_emitter.progress_updated.emit("WD 모델", 0, 0, f"[0/{total_files}]")
            except Exception:
                pass
            
            # 각 파일을 순차적으로 다운로드 (누락된 파일만)
            downloaded_count = 0
            for i, filename in enumerate(required_files):
                try:
                    # 파일이 이미 완전히 다운로드되었는지 확인
                    model_name = self.model_id.split('/')[-1]
                    model_dir = _script_dir() / "models" / model_name
                    self.model_dir = model_dir
                    dst = model_dir / filename
                    
                    if dst.exists():
                        try:
                            # 파일 크기 확인
                            download_url = f"https://huggingface.co/{self.model_id}/resolve/main/{filename}"
                            head_response = requests.head(download_url)
                            if head_response.status_code == 200:
                                expected_size = int(head_response.headers.get('content-length', 0))
                                actual_size = dst.stat().st_size
                                
                                if actual_size == expected_size and expected_size > 0:
                                    print(f"파일 이미 완전함 (스킵): {filename} [{i+1}/{total_files}]")
                                    downloaded_count += 1
                                    continue
                        except Exception:
                            pass
                    
                    print(f"파일 다운로드 시작: {filename} [{i+1}/{total_files}]")
                    
                    # 다운로드 시작 시그널 (LLaVA와 동일한 형태)
                    try:
                        download_progress_emitter.progress_updated.emit(filename, 0, 0, f"[{i+1}/{total_files}]")
                    except Exception:
                        pass
                    
                    # 실제 다운로드 (파일 번호 정보 전달)
                    _ensure_local_from_hub(self.model_id, filename, filename, file_index=i+1, total_files=total_files)
                    
                    print(f"파일 다운로드 완료: {filename} [{i+1}/{total_files}]")
                    downloaded_count += 1
                    
                except Exception as e:
                    print(f"파일 다운로드 실패 (무시): {filename} [{i+1}/{total_files}] - {e}")
                    continue
            
            print(f"WD 모델 다운로드 완료: {self.model_id}")
            
            # 전체 다운로드 완료 시그널 (LLaVA와 동일한 형태 - 간소화)
            try:
                download_progress_emitter.progress_updated.emit("WD 모델", 0, 0, f"[{total_files}/{total_files}]")
            except Exception:
                pass
            
            return True
            
        except Exception as e:
            print(f"WD 모델 다운로드 실패: {e}")
            return False
    
    def check_model_files(self) -> bool:
        """WD 모델 파일들이 로컬에 있는지 확인 (LLaVA와 통일)"""
        if not self.model_dir:
            model_name = self.model_id.split('/')[-1]
            self.model_dir = _script_dir() / "models" / model_name
        
        if not self.model_dir.exists():
            return False
        
        try:
            # 필수 파일들 확인
            required_files = ['model.onnx', 'selected_tags.csv', 'config.json']
            
            # 각 파일이 존재하는지 확인
            for filename in required_files:
                if not (self.model_dir / filename).exists():
                    print(f"필수 파일 누락: {filename}")
                    return False
            
            print(f"모든 필수 파일 존재 확인: {len(required_files)}개 파일")
            return True
            
        except Exception as e:
            print(f"파일 확인 중 오류: {e}")
            return False
    
    def get_model_info(self) -> dict:
        """WD 모델 정보 반환 (LLaVA와 통일)"""
        return {
            "model_id": self.model_id,
            "model_name": self.model_id.split('/')[-1],
            "is_downloaded": self.check_model_files(),
            "model_dir": str(self.model_dir) if self.model_dir else None,
            "use_gpu": self.use_gpu
        }

    # ────────────── 로딩 ──────────────
    def _load_tags(self, csv_path: Path):
        self.tag_names.clear()
        self.rating_indexes.clear()
        self.general_indexes.clear()
        self.character_indexes.clear()

        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                name = row["name"]
                # kaomojis는 언더스코어 유지, 그 외 언더스코어→스페이스
                if name not in kaomojis:
                    name = name.replace("_", " ")
                self.tag_names.append(name)

                try:
                    cat = int(row.get("category", "0"))
                except Exception:
                    cat = 0

                if cat == RATING_CAT:
                    self.rating_indexes.append(i)
                elif cat == CHAR_CAT:
                    self.character_indexes.append(i)
                elif cat == GENERAL_CAT:
                    self.general_indexes.append(i)
                else:
                    # 다른 카테고리는 general로 취급하지 않음 (레퍼런스와 동일 분류)
                    pass

    def _maybe_read_config_for_size(self, cfg_path: Optional[Path]):
        """
        config.json에서 input_size를 읽어 target_size만 반영.
        (전처리/정규화/레이아웃 등은 모두 레퍼런스대로 유지)
        """
        if not cfg_path or not cfg_path.is_file():
            return
        try:
            with cfg_path.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
            pcfg = cfg.get("pretrained_cfg", {})
            inp = pcfg.get("input_size", None)
            if isinstance(inp, list) and len(inp) == 3:
                # [3,H,W] or [H,W,3] → 정사각만 쓰므로 H 또는 W 사용
                if inp[0] == 3:
                    self.target_size = _safe_int(inp[1]) or self.target_size
                elif inp[-1] == 3:
                    self.target_size = _safe_int(inp[0]) or self.target_size
        except Exception:
            pass

    # ▼ 추가: DLL 검색 경로 주입 유틸
    def _add_dll_dir(self, p: str):
        try:
            if os.name == "nt":
                h = os.add_dll_directory(p)
                self._dll_dir_handles.append(h)
        except Exception:
            pass
        # PATH에도 prepend (보조)
        cur = os.environ.get("PATH", "")
        if p not in cur.split(";"):
            os.environ["PATH"] = p + ";" + cur

    def _inject_cuda_from_pip(self) -> List[str]:
        """
        pip로 설치된 nvidia-cu12 패키지들의 bin/lib 경로를 importlib로 찾은 뒤
        DLL 검색 경로에 주입한다.
        """
        found: List[str] = []
        modules = [
            "nvidia.cuda_runtime",
            "nvidia.cublas",
            "nvidia.cudnn",
            "nvidia.cufft",
            "nvidia.curand",
            "nvidia.cusolver",
            "nvidia.cusparse",
            "nvidia.nvjitlink",
        ]
        for m in modules:
            try:
                spec = importlib.util.find_spec(m)
                if not spec:
                    continue
                if spec.submodule_search_locations:
                    base = Path(list(spec.submodule_search_locations)[0])
                else:
                    base = Path(spec.origin).parent
                for sub in ("bin", "lib"):
                    cand = base / sub
                    if cand.is_dir():
                        p = str(cand.resolve())
                        self._add_dll_dir(p)
                        found.append(p)
                        break
            except Exception:
                continue
        return found

    def _inject_cuda_from_system(self) -> List[str]:
        """
        시스템 CUDA(툴킷) 경로를 DLL 검색 경로에 주입. 12.x 우선, 11.x 후순위.
        """
        added: List[str] = []
        candidates = []
        env_cuda = os.environ.get("CUDA_PATH")
        if env_cuda:
            candidates.append(env_cuda)
        candidates += [
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.5",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.2",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7",
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.6",
        ]
        for base in candidates:
            bin_dir = os.path.join(base, "bin")
            if os.path.isdir(bin_dir):
                self._add_dll_dir(bin_dir)
                added.append(bin_dir)
        return added

    def _verify_cu12_presence(self) -> bool:
        """
        cu12 핵심 DLL(cudart64_12.dll / cublasLt64_12.dll)이 PATH에서 보이는지 빠르게 점검.
        """
        targets = ("cudart64_12.dll", "cublasLt64_12.dll")
        for t in targets:
            for p in os.environ.get("PATH", "").split(";"):
                if p and os.path.isfile(os.path.join(p, t)):
                    return True
        return False

    def load_model(self):
        try:
            # 기존 모델 파일들 마이그레이션 (한 번만 실행)
            _migrate_old_models()
            
            # LLaVA와 통일된 고급 다운로드 기능 사용
            if not self.check_model_files():
                print(f"WD 모델 파일이 누락됨, 고급 다운로드 시작: {self.model_id}")
                self.download_model_files()
            
            # 모델별 폴더에 자산 확보 (기존 방식 유지)
            labels_path = _ensure_local_from_hub(self.model_id, LABEL_FILENAME, LABEL_FILENAME)
            model_path  = _ensure_local_from_hub(self.model_id, MODEL_FILENAME, MODEL_FILENAME)
            cfg_path    = _maybe_local_config(self.model_id)  # optional

            # 태그 로드
            self._load_tags(labels_path)

            # ONNX Runtime 상태 확인
            print(f"🔍 ONNX Runtime 상태 확인:")
            print(f"   - 사용 가능한 providers: {ort.get_available_providers()}")
            print(f"   - GPU 모드 설정: {self.use_gpu}")
            print(f"   - 모델 경로: {model_path}")

            # GPU 모드일 때 동적으로 NVIDIA 패키지 경로 찾기
            if self.use_gpu:
                print("🔧 NVIDIA DLL 경로 탐색 시작")
                # 1) pip에서 cu12 컴포넌트 경로 주입 (가장 신뢰)
                pip_paths = self._inject_cuda_from_pip()
                # 2) 시스템 CUDA 경로 주입 (12.x 우선)
                sys_paths = self._inject_cuda_from_system()

                # 출력 정리
                all_added: List[str] = []
                all_added.extend(pip_paths)
                for p in sys_paths:
                    if p not in all_added:
                        all_added.append(p)

                if all_added:
                    print(f"🔧 NVIDIA DLL 경로 추가: {len(all_added)}개 경로")
                    for p in all_added:
                        print(f"   - {p}")
                else:
                    print("⚠️ NVIDIA DLL 경로를 찾을 수 없음 (pip nvidia-cu12 패키지 또는 CUDA Toolkit 12.x 필요)")

                if not self._verify_cu12_presence():
                    print("❗ cu12 핵심 DLL(cudart64_12.dll 등)을 PATH에서 찾지 못했습니다. pip 또는 CUDA 12.x 설치/환경변수 설정을 확인하세요.")

            # ONNX 세션 (GPU/CPU 모드 선택)
            if self.use_gpu:
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                print(f"🚀 GPU 모드로 세션 생성 시도: {providers}")
                try:
                    self.session = ort.InferenceSession(str(model_path), providers=providers)
                    # 실제 사용된 provider 확인
                    actual_providers = self.session.get_providers()
                    print(f"GPU 모드로 모델 로드 완료 - 사용된 providers: {actual_providers}")
                    if 'CUDAExecutionProvider' in actual_providers:
                        print("✅ GPU (CUDA) 사용 중")
                    else:
                        print("⚠️ GPU 사용 실패, CPU로 실행 중")
                except Exception as e:
                    # GPU 사용 실패 시 CPU로 fallback
                    print(f"❌ GPU 사용 실패, CPU로 fallback: {e}")
                    self.session = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
                    actual_providers = self.session.get_providers()
                    print(f"CPU 모드로 모델 로드 완료 - 사용된 providers: {actual_providers}")
            else:
                print(f"🖥️ CPU 모드로 세션 생성")
                self.session = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
                actual_providers = self.session.get_providers()
                print(f"CPU 모드로 모델 로드 완료 - 사용된 providers: {actual_providers}")

            # config에서 target_size만 우선 반영
            self._maybe_read_config_for_size(cfg_path)

            # 그래도 target_size가 없으면, 입력 shape에서 NHWC로 가정해 높이 사용(레퍼런스와 동일 흐름)
            try:
                _, height, width, _ = self.session.get_inputs()[0].shape  # NHWC 가정
                if isinstance(height, int) and height:
                    self.target_size = height
            except Exception:
                pass

            self.is_loaded = True

        except Exception as e:
            self.error_occurred.emit(f"모델 로드 실패: {e}")
            raise

    # ────────────── 전처리(레퍼런스 동일) ──────────────
    def _alpha_composite_rgb(self, image: PILImage.Image, bg_rgb=(255, 255, 255)) -> PILImage.Image:
        if image.mode == "RGBA":
            bg = PILImage.new("RGBA", image.size, bg_rgb + (255,))
            return PILImage.alpha_composite(bg, image).convert("RGB")
        return image.convert("RGB")

    def _prepare_tensor_reference(self, pil_img: PILImage.Image) -> np.ndarray:
        """
        레퍼런스 파이프라인:
          - RGBA → 흰색 합성
          - 비율 유지 패딩(정사각) → target_size 리사이즈
          - RGB → BGR
          - float32 (0~255), 정규화/스케일링 없음
          - NHWC (1,H,W,3)
        """
        img = self._alpha_composite_rgb(pil_img, bg_rgb=self.pad_rgb)

        target = int(self.target_size) if self.target_size else 448
        w, h = img.size
        max_dim = max(w, h)
        pad_left = (max_dim - w) // 2
        pad_top = (max_dim - h) // 2

        padded = PILImage.new("RGB", (max_dim, max_dim), self.pad_rgb)
        padded.paste(img, (pad_left, pad_top))

        if max_dim != target:
            padded = padded.resize((target, target), PILImage.BICUBIC)

        arr = np.asarray(padded, dtype=np.float32)  # 0~255 float
        arr = arr[:, :, ::-1]  # RGB → BGR
        arr = np.expand_dims(arr, axis=0)  # NHWC
        return arr

    # ────────────── 추론/후처리(레퍼런스 동일) ──────────────
    def _mcut_threshold(self, probs: np.ndarray) -> float:
        """MCut (옵션)"""
        sorted_probs = probs[np.argsort(probs)[::-1]]
        difs = sorted_probs[:-1] - sorted_probs[1:]
        t = np.argmax(difs)
        return float((sorted_probs[t] + sorted_probs[t + 1]) / 2.0)

    def predict_tags(
        self,
        image_path: str,
        general_mcut_enabled: bool = None,
        character_mcut_enabled: bool = None,
        max_tags: int = None,
        exclude_tags: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """
        레퍼런스 로직으로 태그 선택 후 (general+character) 합쳐 점수순 반환.
        rating(카테고리9)은 내부에서 dict로 계산하지만 반환 목록에는 포함하지 않음(레퍼런스 UI 호환).
        """
        if not self.is_loaded:
            raise RuntimeError("모델이 로드되지 않았습니다")
        
        # 설정 파일에서 기본값 로드
        if max_tags is None:
            max_tags = get_tagger_config_value("max_tags", 30)
        if general_mcut_enabled is None:
            general_mcut_enabled = get_tagger_config_value("general_mcut_enabled", False)
        if character_mcut_enabled is None:
            character_mcut_enabled = get_tagger_config_value("character_mcut_enabled", False)
            
        try:
            import time
            start_time = time.time()
            
            pil = PILImage.open(image_path)
            tensor = self._prepare_tensor_reference(pil)

            input_name = self.session.get_inputs()[0].name
            out_name = self.session.get_outputs()[0].name
            
            # 추론 실행 및 시간 측정
            inference_start = time.time()
            preds = self.session.run([out_name], {input_name: tensor})[0]  # (1, num_tags)
            inference_time = time.time() - inference_start
            
            scores = preds[0].astype(np.float32)  # 그대로 confidence
            
            # 사용된 provider 확인
            actual_providers = self.session.get_providers()
            provider_info = "GPU" if 'CUDAExecutionProvider' in actual_providers else "CPU"
            print(f"🔍 추론 시간: {inference_time:.3f}초 ({provider_info} 모드)")

            # (이 부분은 레퍼런스의 grouping/threshold 절차와 동일)
            labels = list(zip(self.tag_names, scores))

            rating_names = [labels[i] for i in self.rating_indexes]  # dict로 쓰는 경우가 많음
            rating_dict: Dict[str, float] = dict(rating_names)       # 필요시 사용

            general_names = [labels[i] for i in self.general_indexes]
            if general_mcut_enabled and len(general_names) >= 2:
                general_probs = np.array([x[1] for x in general_names], dtype=np.float32)
                general_mcut_min_enabled = get_tagger_config_value("general_mcut_min_enabled", False)
                if general_mcut_min_enabled:
                    general_mcut_min = get_tagger_config_value("general_mcut_min", 0.15)
                    general_thresh = max(general_mcut_min, self._mcut_threshold(general_probs))
                else:
                    general_thresh = self._mcut_threshold(general_probs)
            else:
                general_thresh = self.general_threshold
            general_res = {t: float(s) for (t, s) in general_names if s > general_thresh}

            character_names = [labels[i] for i in self.character_indexes]
            if character_mcut_enabled and len(character_names) >= 2:
                character_probs = np.array([x[1] for x in character_names], dtype=np.float32)
                character_mcut_min_enabled = get_tagger_config_value("character_mcut_min_enabled", False)
                if character_mcut_min_enabled:
                    character_mcut_min = get_tagger_config_value("character_mcut_min", 0.15)
                    character_thresh = max(character_mcut_min, self._mcut_threshold(character_probs))
                else:
                    character_thresh = self._mcut_threshold(character_probs)
            else:
                character_thresh = self.character_threshold
            character_res = {t: float(s) for (t, s) in character_names if s > character_thresh}

            # 반환 형식: general+character를 합쳐 점수순 리스트 (기존 시그널 호환)
            ex = set(exclude_tags or [])
            picked = [(t, sc) for (t, sc) in {**general_res, **character_res}.items() if t not in ex]
            picked.sort(key=lambda x: x[1], reverse=True)
            if max_tags > 0:
                picked = picked[:max_tags]
            return picked

        except Exception as e:
            raise RuntimeError(f"태그 예측 실패: {e}")

    def batch_predict(
        self,
        image_paths: List[str],
        general_mcut_enabled: bool = None,
        character_mcut_enabled: bool = None,
        max_tags: int = None,
        exclude_tags: Optional[List[str]] = None,
    ):
        if not self.is_loaded:
            self.load_model()
        
        # 설정 파일에서 기본값 로드
        if max_tags is None:
            max_tags = get_tagger_config_value("max_tags", 30)
        if general_mcut_enabled is None:
            general_mcut_enabled = get_tagger_config_value("general_mcut_enabled", False)
        if character_mcut_enabled is None:
            character_mcut_enabled = get_tagger_config_value("character_mcut_enabled", False)
            
        total = len(image_paths)
        
        # 태그 결과 수집
        tag_results = []
        
        for i, p in enumerate(image_paths):
            try:
                tags = self.predict_tags(
                    p,
                    general_mcut_enabled=general_mcut_enabled,
                    character_mcut_enabled=character_mcut_enabled,
                    max_tags=max_tags,
                    exclude_tags=exclude_tags,
                )
                tag_results.append(tags)
                self.tag_generated.emit(p, tags)
            except Exception as e:
                self.error_occurred.emit(f"이미지 {p} 처리 실패: {e}")
                tag_results.append([])  # 실패한 경우 빈 리스트
            finally:
                self.progress_updated.emit(i + 1, total)
        
        # 타임머신 로그 기록 (공통 함수 사용)
        try:
            from timemachine_log import log_ai_batch_tagging
            log_ai_batch_tagging("WD Tagger", self.model_id, image_paths, tag_results)
        except Exception:
            pass
        
        self.finished.emit()

    def batch_predict_unified(
        self,
        image_paths: List[str],
        mode: str = "auto",  # "v0", "v1", "v2", "auto"
        general_mcut_enabled: bool = None,
        character_mcut_enabled: bool = None,
        max_tags: int = None,
        exclude_tags: Optional[List[str]] = None,
    ):
        """
        통합 배치 예측 엔트리포인트 (WdTaggerModel용)
        - mode="auto": 설정에 따라 자동으로 v0/v1/v2 선택
        - mode="v0": 기본 메서드 사용
        - mode="v1": Enhanced V1 사용 (Sigmoid + TTA)
        - mode="v2": Enhanced V2 사용 (V1 + 일반 MCut min)
        """
        if not self.is_loaded:
            self.load_model()
        
        # 설정 파일에서 기본값 로드
        if max_tags is None:
            max_tags = get_tagger_config_value("max_tags", 30)
        if general_mcut_enabled is None:
            general_mcut_enabled = get_tagger_config_value("general_mcut_enabled", False)
        if character_mcut_enabled is None:
            character_mcut_enabled = get_tagger_config_value("character_mcut_enabled", False)
        
        # 성능 가드레일: 대량 배치 시 TTA 비활성화
        perf_tier = get_tagger_config_value("perf_tier", "balanced")  # "speed", "balanced", "quality"
        if perf_tier == "speed" and len(image_paths) > 10:
            print("⚠️ 성능 우선 모드: 대량 배치로 인해 TTA 비활성화")
            # TTA 강제 비활성화를 위한 임시 설정 오버라이드
            tta_enabled = False
        else:
            tta_enabled = get_tagger_config_value("tta_enabled", False)
        
        # auto 모드에서 버전 자동 선택
        if mode == "auto":
            if tta_enabled and get_tagger_config_value("apply_sigmoid", False):
                mode = "v2"  # 가장 고급 기능
            elif tta_enabled or get_tagger_config_value("apply_sigmoid", False):
                mode = "v1"  # 중간 기능
            else:
                mode = "v0"  # 기본 기능
        
        # 로깅 정보
        log_info = {
            "mode": mode,
            "images": len(image_paths),
            "max_tags": max_tags,
            "general_mcut": general_mcut_enabled,
            "character_mcut": character_mcut_enabled,
            "perf_tier": perf_tier
        }
        
        # 로깅 정보 출력
        print(f"📊 배치 예측 시작: {log_info}")
        
        # 버전별 메서드 호출
        if mode == "v2" and hasattr(self, 'batch_predict_enhanced_v2'):
            print("✅ V2 Enhanced methods 사용")
            log_info["tta_applied"] = tta_enabled
            log_info["sigmoid_applied"] = get_tagger_config_value("apply_sigmoid", False)
            self.batch_predict_enhanced_v2(
                image_paths,
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                max_tags=max_tags,
                exclude_tags=exclude_tags,
            )
        elif mode == "v1" and hasattr(self, 'batch_predict_enhanced'):
            print("✅ V1 Enhanced methods 사용")
            log_info["tta_applied"] = tta_enabled
            log_info["sigmoid_applied"] = get_tagger_config_value("apply_sigmoid", False)
            self.batch_predict_enhanced(
                image_paths,
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                max_tags=max_tags,
                exclude_tags=exclude_tags,
            )
        else:
            print("✅ 기본 methods 사용")
            log_info["tta_applied"] = False
            log_info["sigmoid_applied"] = False
            self.batch_predict(
                image_paths,
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                max_tags=max_tags,
                exclude_tags=exclude_tags,
            )
        
        # 최종 로깅 정보 출력
        print(f"📊 배치 예측 완료: {log_info}")


# 전역 인스턴스
_global_tagger = None

def get_global_tagger(
    model_id: str = "SmilingWolf/wd-vit-large-tagger-v3",
    general_threshold: float = None,
    character_threshold: float = None,
    pad_rgb=(255, 255, 255),
    use_gpu: bool = True,
):
    global _global_tagger
    
    # 설정 파일에서 기본값 로드
    if general_threshold is None:
        general_threshold = get_tagger_config_value("general_threshold", 0.35)
    if character_threshold is None:
        character_threshold = get_tagger_config_value("character_threshold", 0.85)
    
    # 파라미터가 바뀌면 새로 생성
    if (_global_tagger is None or
        _global_tagger.model_id != model_id or
        _global_tagger.general_threshold != general_threshold or
        _global_tagger.character_threshold != character_threshold or
        _global_tagger.pad_rgb != pad_rgb or
        _global_tagger.use_gpu != use_gpu):
        print(f"🔄 모델 새로 로드: GPU={use_gpu}, Model={model_id}")
        _global_tagger = WdTaggerModel(
            model_id=model_id,
            general_threshold=general_threshold,
            character_threshold=character_threshold,
            pad_rgb=pad_rgb,
            use_gpu=use_gpu,
        )
        _global_tagger.load_model()
    else:
        print(f"♻️ 기존 모델 재사용: GPU={_global_tagger.use_gpu}, Model={_global_tagger.model_id}")
    return _global_tagger


def get_tag_category(tag_name: str) -> str:
    """태그의 카테고리 정보 반환 (general/character/rating)"""
    global _global_tagger
    if _global_tagger is None or not _global_tagger.is_loaded:
        return "unknown"
    
    try:
        # 태그 이름으로 인덱스 찾기
        if tag_name in _global_tagger.tag_names:
            tag_index = _global_tagger.tag_names.index(tag_name)
            
            # 카테고리 확인
            if tag_index in _global_tagger.general_indexes:
                return "general"
            elif tag_index in _global_tagger.character_indexes:
                return "character"
            elif tag_index in _global_tagger.rating_indexes:
                return "rating"
            else:
                return "unknown"
        else:
            return "unknown"
    except Exception as e:
        print(f"태그 카테고리 확인 오류: {e}")
        return "unknown"


class WdTaggerThread(QThread):
    progress_updated = Signal(int, int)
    tag_generated = Signal(str, list)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        image_paths: List[str],
        model_id: str = "SmilingWolf/wd-vit-large-tagger-v3",
        general_threshold: float = None,
        character_threshold: float = None,
        max_tags: int = None,
        pad_rgb=(255, 255, 255),
        exclude_tags: Optional[List[str]] = None,
        general_mcut_enabled: bool = None,
        character_mcut_enabled: bool = None,
        use_gpu: bool = True,
    ):
        super().__init__()
        self.image_paths = image_paths
        self.model_id = model_id
        self.general_threshold = general_threshold
        self.character_threshold = character_threshold
        self.max_tags = max_tags
        self.pad_rgb = pad_rgb
        self.exclude_tags = exclude_tags or []
        self.general_mcut_enabled = general_mcut_enabled
        self.character_mcut_enabled = character_mcut_enabled
        self.use_gpu = use_gpu
        self.tagger = None

    def run(self):
        try:
            # 설정 파일에서 기본값 로드
            general_threshold = self.general_threshold if self.general_threshold is not None else get_tagger_config_value("general_threshold", 0.35)
            character_threshold = self.character_threshold if self.character_threshold is not None else get_tagger_config_value("character_threshold", 0.85)
            max_tags = self.max_tags if self.max_tags is not None else get_tagger_config_value("max_tags", 30)
            general_mcut_enabled = self.general_mcut_enabled if self.general_mcut_enabled is not None else get_tagger_config_value("general_mcut_enabled", False)
            character_mcut_enabled = self.character_mcut_enabled if self.character_mcut_enabled is not None else get_tagger_config_value("character_mcut_enabled", False)
            
            self.tagger = get_global_tagger(
                model_id=self.model_id,
                general_threshold=general_threshold,
                character_threshold=character_threshold,
                pad_rgb=self.pad_rgb,
                use_gpu=self.use_gpu,
            )
            self.tagger.progress_updated.connect(self.progress_updated)
            self.tagger.tag_generated.connect(self.tag_generated)
            self.tagger.finished.connect(self.finished)
            self.tagger.error_occurred.connect(self.error_occurred)
            # 통합 엔트리포인트 사용 (auto 모드로 설정에 따라 자동 선택)
            self.tagger.batch_predict_unified(
                self.image_paths,
                mode="auto",  # 설정에 따라 v0/v1/v2 자동 선택
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                max_tags=max_tags,
                exclude_tags=self.exclude_tags,
            )
        except Exception as e:
            self.error_occurred.emit(f"WD Tagger 스레드 오류: {e}")
            self.finished.emit()

    def batch_predict_unified(
        self,
        image_paths: List[str],
        mode: str = "auto",  # "v0", "v1", "v2", "auto"
        general_mcut_enabled: bool = None,
        character_mcut_enabled: bool = None,
        max_tags: int = None,
        exclude_tags: Optional[List[str]] = None,
    ):
        """
        통합 배치 예측 엔트리포인트
        - mode="auto": 설정에 따라 자동으로 v0/v1/v2 선택
        - mode="v0": 기본 메서드 사용
        - mode="v1": Enhanced V1 사용 (Sigmoid + TTA)
        - mode="v2": Enhanced V2 사용 (V1 + 일반 MCut min)
        """
        if not self.is_loaded:
            self.load_model()
        
        # 설정 파일에서 기본값 로드
        if max_tags is None:
            max_tags = get_tagger_config_value("max_tags", 30)
        if general_mcut_enabled is None:
            general_mcut_enabled = get_tagger_config_value("general_mcut_enabled", False)
        if character_mcut_enabled is None:
            character_mcut_enabled = get_tagger_config_value("character_mcut_enabled", False)
        
        # 성능 가드레일: 대량 배치 시 TTA 비활성화
        perf_tier = get_tagger_config_value("perf_tier", "balanced")  # "speed", "balanced", "quality"
        if perf_tier == "speed" and len(image_paths) > 10:
            print("⚠️ 성능 우선 모드: 대량 배치로 인해 TTA 비활성화")
            # TTA 강제 비활성화를 위한 임시 설정 오버라이드
            tta_enabled = False
        else:
            tta_enabled = get_tagger_config_value("tta_enabled", False)
        
        # auto 모드에서 버전 자동 선택
        if mode == "auto":
            # V2 조건: 일반 MCut min이 활성화되어 있거나 필요
            general_mcut_min_enabled = get_tagger_config_value("general_mcut_min_enabled", False)
            if general_mcut_min_enabled:
                mode = "v2"
                print("✅ Auto mode: V2 선택 (일반 MCut min 활성화)")
            else:
                # V1 조건: Sigmoid 또는 TTA가 활성화
                apply_sigmoid = get_tagger_config_value("apply_sigmoid", False)
                if apply_sigmoid or tta_enabled:
                    mode = "v1"
                    print("✅ Auto mode: V1 선택 (Sigmoid/TTA 활성화)")
                else:
                    mode = "v0"
                    print("✅ Auto mode: V0 선택 (기본 설정)")
        
        # 로깅 정보 수집
        log_info = {
            "method_used": mode,
            "image_count": len(image_paths),
            "perf_tier": perf_tier,
            "general_mcut_enabled": general_mcut_enabled,
            "character_mcut_enabled": character_mcut_enabled,
            "max_tags": max_tags
        }
        
        # 로깅 정보 출력
        print(f"📊 배치 예측 시작: {log_info}")
        
        # 버전별 메서드 호출
        if mode == "v2" and hasattr(self, 'batch_predict_enhanced_v2'):
            print("✅ V2 Enhanced methods 사용")
            log_info["tta_applied"] = tta_enabled
            log_info["sigmoid_applied"] = get_tagger_config_value("apply_sigmoid", False)
            self.batch_predict_enhanced_v2(
                image_paths,
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                max_tags=max_tags,
                exclude_tags=exclude_tags,
            )
        elif mode == "v1" and hasattr(self, 'batch_predict_enhanced'):
            print("✅ V1 Enhanced methods 사용")
            log_info["tta_applied"] = tta_enabled
            log_info["sigmoid_applied"] = get_tagger_config_value("apply_sigmoid", False)
            self.batch_predict_enhanced(
                image_paths,
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                max_tags=max_tags,
                exclude_tags=exclude_tags,
            )
        else:
            print("✅ 기본 methods 사용")
            log_info["tta_applied"] = False
            log_info["sigmoid_applied"] = False
            self.batch_predict(
                image_paths,
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                max_tags=max_tags,
                exclude_tags=exclude_tags,
            )
        
        # 최종 로깅 정보 출력
        print(f"📊 배치 예측 완료: {log_info}")

# ============================================================================
# [ADDED] Enhancements: Sigmoid + TTA + JSON toggles (non-invasive additions)
# - No existing code above is modified; this block only adds new helpers/methods.
# - You can enable/disable via models/wd_tagger_config.json (keys documented below).
# ============================================================================

import numpy as _np
from PIL import Image as _PILImage

# ---- Config helpers (do NOT modify existing load/save; extend on top) ----

def _enh_default_config():
    return {
        "general_mcut_enabled": False,
        "character_mcut_enabled": False,
        "apply_sigmoid": False,
        "tta_enabled": False,
        "tta_horizontal_flip": True,
        "tta_merge_mode": "mean"  # "mean" or "max"
    }

def _load_enh_config_with_defaults():
    cfg = {}
    try:
        cfg = load_tagger_config()
    except Exception:
        cfg = {}
    # merge defaults without touching disk
    defaults = _enh_default_config()
    for k, v in defaults.items():
        cfg.setdefault(k, v)
    return cfg

def upgrade_tagger_config_for_enhancements():
    """
    Idempotent upgrade: ensure the new keys exist in models/wd_tagger_config.json.
    We do NOT touch existing values; only fill missing keys with defaults.
    """
    try:
        cfg = load_tagger_config()
        changed = False
        for k, v in _enh_default_config().items():
            if k not in cfg:
                cfg[k] = v
                changed = True
        if changed:
            save_tagger_config(cfg)
            print("🔧 wd_tagger_config.json upgraded with enhancement keys.")
    except Exception as e:
        print(f"⚠️ Could not upgrade wd_tagger_config.json: {e}")

# run upgrade at import-time (safe, only fills missing keys)
try:
    upgrade_tagger_config_for_enhancements()
except Exception:
    pass

# ---- Math helpers ----

def _safe_sigmoid(x: "_np.ndarray") -> "_np.ndarray":
    # stable sigmoid
    x = _np.clip(x, -60.0, 60.0)
    return 1.0 / (1.0 + _np.exp(-x))

def _merge_scores(arrs: "_np.ndarray", mode: str = "mean") -> "_np.ndarray":
    if mode == "max":
        return _np.max(arrs, axis=0)
    # default: mean
    return _np.mean(arrs, axis=0)

def _pil_horizontal_flip(img: "_PILImage") -> "_PILImage":
    try:
        return img.transpose(_PILImage.FLIP_LEFT_RIGHT)
    except Exception:
        arr = _np.array(img)
        return _PILImage.fromarray(arr[:, ::-1, ...])

# ---- WdTaggerModel: add NON-INTRUSIVE new methods (monkey-patched) ----

def _predict_scores_single_pass(self, pil_img, apply_sigmoid=False):
    """
    Internal single-pass inference that mirrors the reference pipeline,
    with optional sigmoid application.
    """
    tensor = self._prepare_tensor_reference(pil_img)
    input_name = self.session.get_inputs()[0].name
    out_name = self.session.get_outputs()[0].name
    preds = self.session.run([out_name], {input_name: tensor})[0]  # (1, num_tags)
    scores = preds[0].astype(_np.float32)  # baseline: as-is (reference behavior)
    if apply_sigmoid:
        scores = _safe_sigmoid(scores)
    return scores  # 1D (num_tags,)

def predict_tags_enhanced(
    self,
    image_path: str,
    use_config: bool = True,
    # Explicit overrides; if None, values come from JSON
    general_mcut_enabled: bool = None,
    character_mcut_enabled: bool = None,
    apply_sigmoid: bool = None,
    tta_enabled: bool = None,
    tta_horizontal_flip: bool = None,
    tta_merge_mode: str = None,
    max_tags: int = None,
    exclude_tags: list = None,
):
    """
    Enhanced prediction:
    - Optional sigmoid on raw outputs.
    - Optional TTA (currently: horizontal flip) with mean/max merge.
    - Thresholding identical to reference (including MCut when enabled).
    NOTE: This is an additive API; existing methods remain untouched.
    """
    if not self.is_loaded:
        self.load_model()

    # Resolve defaults
    cfg = _load_enh_config_with_defaults() if use_config else _enh_default_config()
    if general_mcut_enabled is None:
        general_mcut_enabled = bool(cfg.get("general_mcut_enabled", False))
    if character_mcut_enabled is None:
        character_mcut_enabled = bool(cfg.get("character_mcut_enabled", False))
    if apply_sigmoid is None:
        apply_sigmoid = bool(cfg.get("apply_sigmoid", False))
    if tta_enabled is None:
        tta_enabled = bool(cfg.get("tta_enabled", False))
    if tta_horizontal_flip is None:
        tta_horizontal_flip = bool(cfg.get("tta_horizontal_flip", True))
    if tta_merge_mode is None:
        tta_merge_mode = str(cfg.get("tta_merge_mode", "mean"))
    if max_tags is None:
        max_tags = get_tagger_config_value("max_tags", 30)

    # Load image
    pil = _PILImage.open(image_path)

    # Inference (single or TTA)
    if not tta_enabled:
        scores = _predict_scores_single_pass(self, pil, apply_sigmoid=apply_sigmoid)
    else:
        _scores = []
        # original
        _scores.append(_predict_scores_single_pass(self, pil, apply_sigmoid=apply_sigmoid))
        # horizontal flip (optional)
        if tta_horizontal_flip:
            pil_flip = _pil_horizontal_flip(pil)
            _scores.append(_predict_scores_single_pass(self, pil_flip, apply_sigmoid=apply_sigmoid))
        scores = _merge_scores(_np.stack(_scores, axis=0), mode=tta_merge_mode).astype(_np.float32)

    # Thresholding (exactly as in reference predict_tags)
    labels = list(zip(self.tag_names, scores))

    # rating kept for internal parity; not returned
    rating_names = [labels[i] for i in self.rating_indexes]
    _ = dict(rating_names)

    # general
    general_names = [labels[i] for i in self.general_indexes]
    if general_mcut_enabled and len(general_names) >= 2:
        general_probs = _np.array([x[1] for x in general_names], dtype=_np.float32)
        general_thresh = self._mcut_threshold(general_probs)
    else:
        general_thresh = self.general_threshold
    general_res = {t: float(s) for (t, s) in general_names if s > general_thresh}

    # character (with floor via character_mcut_min when MCut is used)
    character_names = [labels[i] for i in self.character_indexes]
    if character_mcut_enabled and len(character_names) >= 2:
        character_probs = _np.array([x[1] for x in character_names], dtype=_np.float32)
        character_mcut_min = get_tagger_config_value("character_mcut_min", 0.15)
        character_thresh = max(character_mcut_min, self._mcut_threshold(character_probs))
    else:
        character_thresh = self.character_threshold
    character_res = {t: float(s) for (t, s) in character_names if s > character_thresh}

    ex = set(exclude_tags or [])
    picked = [(t, sc) for (t, sc) in {**general_res, **character_res}.items() if t not in ex]
    picked.sort(key=lambda x: x[1], reverse=True)
    if max_tags > 0:
        picked = picked[:max_tags]
    return picked

def batch_predict_enhanced(
    self,
    image_paths,
    use_config: bool = True,
    general_mcut_enabled: bool = None,
    character_mcut_enabled: bool = None,
    apply_sigmoid: bool = None,
    tta_enabled: bool = None,
    tta_horizontal_flip: bool = None,
    tta_merge_mode: str = None,
    max_tags: int = None,
    exclude_tags=None,
):
    if not self.is_loaded:
        self.load_model()

    if max_tags is None:
        max_tags = get_tagger_config_value("max_tags", 30)

    total = len(image_paths)
    
    # 태그 결과 수집
    tag_results = []
    
    for i, p in enumerate(image_paths):
        try:
            tags = predict_tags_enhanced(
                self,
                p,
                use_config=use_config,
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                apply_sigmoid=apply_sigmoid,
                tta_enabled=tta_enabled,
                tta_horizontal_flip=tta_horizontal_flip,
                tta_merge_mode=tta_merge_mode,
                max_tags=max_tags,
                exclude_tags=exclude_tags,
            )
            tag_results.append(tags)
            self.tag_generated.emit(p, tags)
        except Exception as e:
            self.error_occurred.emit(f"태그 예측 실패: {e}")
            tag_results.append([])  # 실패한 경우 빈 리스트
        finally:
            self.progress_updated.emit(i + 1, total)
    
    # 타임머신 로그 기록 (공통 함수 사용)
    try:
        from timemachine_log import log_ai_batch_tagging
        log_ai_batch_tagging("WD Tagger Enhanced", self.model_id, image_paths, tag_results)
    except Exception:
        pass
    
    self.finished.emit()

# Attach as new methods; do NOT override existing ones
try:
    WdTaggerModel.predict_tags_enhanced = predict_tags_enhanced
    WdTaggerModel.batch_predict_enhanced = batch_predict_enhanced
    print("✅ WdTaggerModel enhanced methods attached (sigmoid + TTA + JSON toggles).")
except Exception as _e:
    print(f"⚠️ Could not attach enhanced methods: {_e}")
# ============================================================================
# End of added enhancement block
# ============================================================================

# ============================================================================
# [ADDED V2] General MCut minimum (floor) + JSON toggles
# - Adds *optional* minimum floor for general MCut.
# - Controlled via models/wd_tagger_config.json:
#     "general_mcut_min_enabled": false,
#     "general_mcut_min": 0.15
# - Non-invasive: no existing functions above are modified.
# - New methods: predict_tags_enhanced_v2 / batch_predict_enhanced_v2
# ============================================================================

import numpy as __np

def _enh_v2_default_config():
    return {
        "general_mcut_min_enabled": False,
        "general_mcut_min": 0.15
    }

def _load_enh_v2_config_with_defaults():
    cfg = {}
    try:
        cfg = load_tagger_config()
    except Exception:
        cfg = {}
    for k, v in _enh_v2_default_config().items():
        cfg.setdefault(k, v)
    return cfg

def upgrade_tagger_config_for_enhancements_v2():
    """
    Idempotently add general MCut floor keys to models/wd_tagger_config.json if missing.
    Preserves existing keys/values.
    """
    try:
        cfg = load_tagger_config()
        changed = False
        for k, v in _enh_v2_default_config().items():
            if k not in cfg:
                cfg[k] = v
                changed = True
        if changed:
            save_tagger_config(cfg)
            print("🔧 wd_tagger_config.json upgraded with V2 (general MCut min) keys.")
    except Exception as e:
        print(f"⚠️ Could not upgrade wd_tagger_config.json (V2): {e}")

try:
    upgrade_tagger_config_for_enhancements_v2()
except Exception:
    pass

def predict_tags_enhanced_v2(
    self,
    image_path: str,
    use_config: bool = True,
    # MCut toggles (if None → read from JSON)
    general_mcut_enabled: bool = None,
    character_mcut_enabled: bool = None,
    # NEW: general MCut minimum controls (if None → read from JSON)
    general_mcut_min_enabled: bool = None,
    general_mcut_min: float = None,
    # Existing enhancement toggles (if present from previous block)
    apply_sigmoid: bool = None,
    tta_enabled: bool = None,
    tta_horizontal_flip: bool = None,
    tta_merge_mode: str = None,
    max_tags: int = None,
    exclude_tags: list = None,
):
    """
    Enhanced V2 prediction:
    - Same as predict_tags_enhanced(...) with *additional* support for
      a minimum floor on the general MCut threshold.
    - If enabled, final general threshold = max(general_mcut_min, mcut_value).
    """
    if not self.is_loaded:
        self.load_model()

    # Load configs
    # Base enhancement config (if present)
    try:
        base_cfg = _load_enh_config_with_defaults() if use_config else _enh_default_config()
    except NameError:
        # If first enhancement block isn't present, fall back to sane defaults
        base_cfg = {
            "general_mcut_enabled": False,
            "character_mcut_enabled": False,
            "apply_sigmoid": False,
            "tta_enabled": False,
            "tta_horizontal_flip": True,
            "tta_merge_mode": "mean"
        }
    # V2 keys
    v2_cfg = _load_enh_v2_config_with_defaults() if use_config else _enh_v2_default_config()

    # Resolve toggles/values
    if general_mcut_enabled is None:
        general_mcut_enabled = bool(base_cfg.get("general_mcut_enabled", False))
    if character_mcut_enabled is None:
        character_mcut_enabled = bool(base_cfg.get("character_mcut_enabled", False))

    if general_mcut_min_enabled is None:
        general_mcut_min_enabled = bool(v2_cfg.get("general_mcut_min_enabled", False))
    if general_mcut_min is None:
        general_mcut_min = float(v2_cfg.get("general_mcut_min", 0.15))

    if apply_sigmoid is None:
        apply_sigmoid = bool(base_cfg.get("apply_sigmoid", False))
    if tta_enabled is None:
        tta_enabled = bool(base_cfg.get("tta_enabled", False))
    if tta_horizontal_flip is None:
        tta_horizontal_flip = bool(base_cfg.get("tta_horizontal_flip", True))
    if tta_merge_mode is None:
        tta_merge_mode = str(base_cfg.get("tta_merge_mode", "mean"))

    if max_tags is None:
        max_tags = get_tagger_config_value("max_tags", 30)

    # Load image
    pil = PILImage.open(image_path)

    # Inference (reuse helpers from first enhancement block if present)
    try:
        scores = _predict_scores_single_pass(self, pil, apply_sigmoid=apply_sigmoid)
        if tta_enabled:
            _scores = [scores]
            if tta_horizontal_flip:
                pil_flip = pil.transpose(PILImage.FLIP_LEFT_RIGHT)
                _scores.append(_predict_scores_single_pass(self, pil_flip, apply_sigmoid=apply_sigmoid))
            scores = __np.mean(__np.stack(_scores, axis=0), axis=0).astype(__np.float32) if tta_merge_mode != "max" else __np.max(__np.stack(_scores, axis=0), axis=0).astype(__np.float32)
    except NameError:
        # If helper not available, do single pass baseline
        tensor = self._prepare_tensor_reference(pil)
        input_name = self.session.get_inputs()[0].name
        out_name = self.session.get_outputs()[0].name
        preds = self.session.run([out_name], {input_name: tensor})[0]
        scores = preds[0].astype(__np.float32)

    labels = list(zip(self.tag_names, scores))

    # rating (not returned; parity only)
    rating_names = [labels[i] for i in self.rating_indexes]
    _ = dict(rating_names)

    # ---- general with MCut + optional floor ----
    general_names = [labels[i] for i in self.general_indexes]
    if general_mcut_enabled and len(general_names) >= 2:
        general_probs = __np.array([x[1] for x in general_names], dtype=__np.float32)
        mcut_val = self._mcut_threshold(general_probs)
        if general_mcut_min_enabled:
            general_thresh = max(float(general_mcut_min), mcut_val)
        else:
            general_thresh = mcut_val
    else:
        general_thresh = self.general_threshold
    general_res = {t: float(s) for (t, s) in general_names if s > general_thresh}

    # ---- character (unchanged from reference/enhanced) ----
    character_names = [labels[i] for i in self.character_indexes]
    if character_mcut_enabled and len(character_names) >= 2:
        character_probs = __np.array([x[1] for x in character_names], dtype=__np.float32)
        character_mcut_min = get_tagger_config_value("character_mcut_min", 0.15)
        character_thresh = max(character_mcut_min, self._mcut_threshold(character_probs))
    else:
        character_thresh = self.character_threshold
    character_res = {t: float(s) for (t, s) in character_names if s > character_thresh}

    ex = set(exclude_tags or [])
    picked = [(t, sc) for (t, sc) in {**general_res, **character_res}.items() if t not in ex]
    picked.sort(key=lambda x: x[1], reverse=True)
    if max_tags > 0:
        picked = picked[:max_tags]
    return picked

def batch_predict_enhanced_v2(
    self,
    image_paths,
    use_config: bool = True,
    general_mcut_enabled: bool = None,
    character_mcut_enabled: bool = None,
    general_mcut_min_enabled: bool = None,
    general_mcut_min: float = None,
    apply_sigmoid: bool = None,
    tta_enabled: bool = None,
    tta_horizontal_flip: bool = None,
    tta_merge_mode: str = None,
    max_tags: int = None,
    exclude_tags=None,
):
    if not self.is_loaded:
        self.load_model()

    if max_tags is None:
        max_tags = get_tagger_config_value("max_tags", 30)

    total = len(image_paths)
    
    # 태그 결과 수집
    tag_results = []
    
    for i, p in enumerate(image_paths):
        try:
            tags = predict_tags_enhanced_v2(
                self,
                p,
                use_config=use_config,
                general_mcut_enabled=general_mcut_enabled,
                character_mcut_enabled=character_mcut_enabled,
                general_mcut_min_enabled=general_mcut_min_enabled,
                general_mcut_min=general_mcut_min,
                apply_sigmoid=apply_sigmoid,
                tta_enabled=tta_enabled,
                tta_horizontal_flip=tta_horizontal_flip,
                tta_merge_mode=tta_merge_mode,
                max_tags=max_tags,
                exclude_tags=exclude_tags,
            )
            tag_results.append(tags)
            self.tag_generated.emit(p, tags)
        except Exception as e:
            self.error_occurred.emit(f"태그 예측 실패(v2): {e}")
            tag_results.append([])  # 실패한 경우 빈 리스트
        finally:
            self.progress_updated.emit(i + 1, total)
    
    # 타임머신 로그 기록 (공통 함수 사용)
    try:
        from timemachine_log import log_ai_batch_tagging
        log_ai_batch_tagging("WD Tagger Enhanced V2", self.model_id, image_paths, tag_results)
    except Exception:
        pass
    
    self.finished.emit()

# Attach V2 methods (without removing previous ones)
try:
    WdTaggerModel.predict_tags_enhanced_v2 = predict_tags_enhanced_v2
    WdTaggerModel.batch_predict_enhanced_v2 = batch_predict_enhanced_v2
    print("✅ WdTaggerModel V2 methods attached (general MCut min + JSON toggles).")
except Exception as __e:
    print(f"⚠️ Could not attach V2 enhanced methods: {__e}")
# ============================================================================
# End of V2 enhancement block
# ============================================================================

# ============================================================================
# WD Download Thread (LLaVA와 통일된 방식)
# ============================================================================

class WdDownloadThread(QThread):
    """WD 모델 다운로드를 위한 스레드 (LLaVA와 통일)"""
    
    progress_updated = Signal(str, int, int, str)  # filename, downloaded, total, status
    download_finished = Signal(bool)  # 다운로드 완료
    error_occurred = Signal(str)  # 오류 발생
    
    def __init__(self, model_id: str, use_gpu: bool = True):
        super().__init__()
        self.model_id = model_id
        self.use_gpu = use_gpu
        self.tagger = None
    
    def run(self):
        """스레드에서 모델 다운로드 실행"""
        try:
            print(f"[WD Download Thread] 스레드 시작: {self.model_id}")
            self.tagger = WdTaggerModel(self.model_id, self.use_gpu)
            
            # 다운로드 진행 상황 시그널 연결
            download_progress_emitter.progress_updated.connect(self.progress_updated)
            
            # 모델 파일 다운로드
            success = self.tagger.download_model_files()
            
            self.download_finished.emit(success)
            
        except Exception as e:
            print(f"[WD Download Thread] 오류: {e}")
            self.error_occurred.emit(str(e))
            self.download_finished.emit(False)
