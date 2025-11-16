"""
액션 버튼 모듈 - 오른쪽 하단 태그 스타일시트 섹션
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class SectionCard(QFrame):
    """섹션 카드 위젯"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("SectionCard")
        self.setStyleSheet("""
            QFrame#SectionCard {
                background: rgba(17,17,27,0.9);
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 6px;
                margin: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        
        # 헤더
        if title:
            header = QLabel(title.upper())
            header.setStyleSheet("""
                font-size: 11px; 
                font-weight: 700;
                color: #9CA3AF; 
                letter-spacing: 1px;
                margin-bottom: 8px;
            """)
            header.setTextFormat(Qt.RichText)  # HTML 지원
            layout.addWidget(header)
        
        # 바디
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(4)
        layout.addLayout(self.body)


class ModernButton(QPushButton):
    """모던 스타일 버튼"""
    
    def __init__(self, text, color1, color2, parent=None):
        super().__init__(text, parent)
        self.color1 = color1
        self.color2 = color2
        self.apply_style()
    
    def apply_style(self):
        self.setStyleSheet(f"""
            /* 태그 스타일시트 에디터 카드 선택 버튼 스타일 */
            QPushButton {{
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 12px;
                min-height: 16px;
            }}
            QPushButton:hover {{
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
            }}
            QPushButton:pressed {{
                background: #2D3748;
                border-color: #2D3748;
                color: #CBD5E0;
            }}
        """)


class ActionButtonsModule:
    """액션 버튼 관리 모듈"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.setup_model_connections()
        
    def create_action_buttons_section(self):
        """액션 버튼 섹션 생성"""
        # Action buttons
        action_card = SectionCard("ACTIONS")
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        
        # CPU/GPU 모드 선택 (좌우 배치)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(12)
        
        # GPU 모드 체크박스
        self.app_instance.gpu_checkbox = QCheckBox("GPU")
        self.app_instance.gpu_checkbox.setChecked(True)  # 기본값: GPU 모드
        # 커스텀 체크박스 클래스 정의
        class CustomCheckBox(QCheckBox):
            def __init__(self, text, parent=None):
                super().__init__(text, parent)
                self.setStyleSheet("""
                    QCheckBox {
                        color: #FFFFFF;
                        font-size: 12px;
                        font-weight: 600;
                        spacing: 6px;
                    }
                    QCheckBox::indicator {
                        width: 14px;
                        height: 14px;
                        border-radius: 2px;
                        border: 1px solid rgba(255, 255, 255, 0.8);
                        background: rgba(17, 17, 27, 0.9);
                    }
                    QCheckBox::indicator:checked {
                        background: rgba(17, 17, 27, 0.9);
                        border: 1px solid rgba(255, 255, 255, 0.8);
                        image: none;
                    }
                    QCheckBox::indicator:hover {
                        border: 1px solid rgba(255, 255, 255, 1.0);
                    }
                """)
            
            def paintEvent(self, event):
                super().paintEvent(event)
                
                if self.isChecked():
                    painter = QPainter(self)
                    painter.setRenderHint(QPainter.Antialiasing)
                    
                    # 체크 표시 그리기
                    painter.setPen(QPen(QColor("#FFFFFF"), 2))
                    painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
                    
                    # 체크박스 영역 계산
                    rect = self.rect()
                    indicator_rect = QRect(1, (rect.height() - 14) // 2, 14, 14)
                    
                    # 체크 표시 (🗸) 그리기
                    painter.drawText(indicator_rect, Qt.AlignCenter, "🗸")
        
        # 기존 체크박스를 커스텀 체크박스로 교체
        gpu_text = self.app_instance.gpu_checkbox.text()
        gpu_checked = self.app_instance.gpu_checkbox.isChecked()
        self.app_instance.gpu_checkbox = CustomCheckBox(gpu_text)
        self.app_instance.gpu_checkbox.setChecked(gpu_checked)
        self.app_instance.gpu_checkbox.toggled.connect(self.on_gpu_toggled)
        mode_layout.addWidget(self.app_instance.gpu_checkbox)
        
        # CPU 모드 체크박스
        self.app_instance.cpu_checkbox = QCheckBox("CPU")
        self.app_instance.cpu_checkbox.setChecked(False)
        # CPU 체크박스도 커스텀 체크박스로 교체
        cpu_text = self.app_instance.cpu_checkbox.text()
        cpu_checked = self.app_instance.cpu_checkbox.isChecked()
        self.app_instance.cpu_checkbox = CustomCheckBox(cpu_text)
        self.app_instance.cpu_checkbox.setChecked(cpu_checked)
        self.app_instance.cpu_checkbox.toggled.connect(self.on_cpu_toggled)
        mode_layout.addWidget(self.app_instance.cpu_checkbox)
        
        # 좌우 정렬을 위한 스트레치 추가
        mode_layout.addStretch()
        
        btn_layout.addLayout(mode_layout)
        
        # 모델 선택 모듈 초기화
        from model_selector_module import ModelSelectorModule
        self.app_instance.model_selector = ModelSelectorModule(self.app_instance)
        self.app_instance.model_combo = self.app_instance.model_selector.create_model_selector()
        
        # 현재 모델 ID 설정
        self.app_instance.current_model_id = self.app_instance.model_selector.get_current_model_id()
        
        # 모듈 임포트 경로 확인 (디버깅용)
        print("액션 버튼 모듈 초기화 완료")
        
        # GPU 사용 가능 여부 확인
        gpu_available = self.check_gpu_availability()
        self.app_instance.use_gpu = gpu_available  # GPU 사용 가능하면 GPU, 아니면 CPU
        
        # GPU 사용 불가능하면 CPU 모드로 설정
        if not gpu_available:
            self.app_instance.gpu_checkbox.setChecked(False)
            self.app_instance.cpu_checkbox.setChecked(True)
            print("GPU 사용 불가능하여 CPU 모드로 설정")
        
        # 모델 변경 시그널 연결
        self.app_instance.model_combo.currentTextChanged.connect(self.on_model_changed)
        
        btn_layout.addWidget(self.app_instance.model_combo)
        
        # 모델 다운로드 진행바
        self.app_instance.download_progress_label = QLabel("")
        self.app_instance.download_progress_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                padding: 4px 8px;
                background: rgba(17,17,27,0.5);
                border-radius: 6px;
                border: 1px solid rgba(75,85,99,0.3);
            }
        """)
        self.app_instance.download_progress_label.hide()  # 초기에는 숨김
        
        self.app_instance.download_progress_bar = QProgressBar()
        self.app_instance.download_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 6px;
                text-align: center;
                background: rgba(17,17,27,0.9);
                color: #F9FAFB;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #1D4ED8);
                border-radius: 5px;
            }
        """)
        self.app_instance.download_progress_bar.hide()  # 초기에는 숨김
        self.app_instance.download_progress_bar.setRange(0, 100)
        
        btn_layout.addWidget(self.app_instance.download_progress_label)
        btn_layout.addWidget(self.app_instance.download_progress_bar)
        
        # AI 버튼들 (중앙 하단에서 이동) - 미라클 회색 버튼 톤과 동일 (이모지 제거)
        self.app_instance.btn_auto_tag = ModernButton("Auto-Tag with AI", "#6B7280", "#4B5563")
        self.app_instance.btn_batch_auto_tag = ModernButton("Batch Auto-Tag", "#6B7280", "#4B5563")
        # Generate Caption 버튼 제거 (미사용)
        
        # 기존 액션 버튼들 - 미라클 회색 버튼 톤과 동일 (이모지 제거)
        self.app_instance.btn_save = ModernButton("Save Project", "#6B7280", "#4B5563")
        self.app_instance.btn_export = ModernButton("Export All", "#6B7280", "#4B5563")
        self.app_instance.btn_clear = ModernButton("Clear All", "#6B7280", "#4B5563")
        
        # 버튼 연결
        self.app_instance.btn_auto_tag.clicked.connect(self.auto_tag_current_image)
        self.app_instance.btn_batch_auto_tag.clicked.connect(self.batch_auto_tag_images)
        self.app_instance.btn_save.clicked.connect(self.save_project_database)
        self.app_instance.btn_export.clicked.connect(self.export_all_tags)
        self.app_instance.btn_clear.clicked.connect(self.clear_all_tags)
        
        # 모든 버튼들 추가 (AI + 기존 액션)
        all_buttons = [self.app_instance.btn_auto_tag, self.app_instance.btn_batch_auto_tag,
                      self.app_instance.btn_save, self.app_instance.btn_export, self.app_instance.btn_clear]
        
        for btn in all_buttons:
            btn.setFixedHeight(36)
            btn_layout.addWidget(btn)
        
        action_card.body.addLayout(btn_layout)
        
        return action_card
    
    def check_gpu_availability(self):
        """GPU 사용 가능 여부 확인"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def setup_model_connections(self):
        """모델 관련 연결 설정"""
        # 모델 변경 시그널 연결은 모델 선택 모듈에서 처리됨
        pass
    
    def on_model_changed(self, display_name):
        """모델 선택 변경 시 호출 (모듈에서 처리됨)"""
        # 모델 선택 모듈을 통해 현재 모델 ID 업데이트
        self.app_instance.current_model_id = self.app_instance.model_selector.get_current_model_id()
        
        print(f"모델 변경됨: {display_name} -> {self.app_instance.current_model_id}")
        
        # 모델 타입에 따른 처리
        if "llava" in self.app_instance.current_model_id.lower():
            print("LLaVA 캡셔너 모델 선택됨")
            self.update_button_texts_for_captioner()
            # LLaVA 모델 다운로드 확인 (안전하게 처리)
            try:
                self.check_llava_model_download()
            except Exception as e:
                print(f"LLaVA 모델 확인 중 오류: {e}")
                self.app_instance.download_progress_label.setText("LLaVA 모델 확인 실패")
        else:
            print("WD Tagger 모델 선택됨")
            self.update_button_texts_for_tagger()
            # WD 모델도 다운로드 확인 및 준비 상태 표시 (라바와 통일)
            try:
                self.check_wd_model_download()
            except Exception as e:
                print(f"WD 모델 확인 중 오류: {e}")
                self.app_instance.download_progress_label.setText("WD 모델 확인 실패")
    
    def update_button_texts_for_tagger(self):
        """WD Tagger 모델용 버튼 텍스트 업데이트"""
        if hasattr(self.app_instance, 'btn_auto_tag'):
            self.app_instance.btn_auto_tag.setText("🤖 Auto-Tag with AI")
        if hasattr(self.app_instance, 'btn_batch_auto_tag'):
            self.app_instance.btn_batch_auto_tag.setText("📦 Batch Auto-Tag")
    
    def update_button_texts_for_captioner(self):
        """LLaVA 캡셔너 모델용 버튼 텍스트 업데이트"""
        if hasattr(self.app_instance, 'btn_auto_tag'):
            self.app_instance.btn_auto_tag.setText("🤖 Auto-Tag with AI")
        if hasattr(self.app_instance, 'btn_batch_auto_tag'):
            self.app_instance.btn_batch_auto_tag.setText("📦 Batch Auto-Tag")
    
    def check_llava_model_download(self):
        """LLaVA 모델 다운로드 상태 확인 (모든 LLaVA 변형 지원)"""
        try:
            # 모델 타입에 따라 적절한 모듈 가져오기
            if "llava-1.5" in self.app_instance.current_model_id.lower():
                from llava_captioner_module import get_global_llava_module
                llava_module = get_global_llava_module(self.app_instance.current_model_id, self.app_instance.use_gpu)
            elif "llava-v1.6" in self.app_instance.current_model_id.lower() or "llava-next" in self.app_instance.current_model_id.lower():
                import importlib
                import llava_next_tagger
                importlib.reload(llava_next_tagger)
                from llava_next_tagger import LLaVANextTagger
                llava_module = LLaVANextTagger(self.app_instance.current_model_id, self.app_instance.use_gpu)
            elif "llava-interleave" in self.app_instance.current_model_id.lower():
                import importlib
                import llava_interleave_tagger
                importlib.reload(llava_interleave_tagger)
                from llava_interleave_tagger import LLaVAInterleaveTagger
                llava_module = LLaVAInterleaveTagger(self.app_instance.current_model_id, self.app_instance.use_gpu)
            elif "vip-llava" in self.app_instance.current_model_id.lower():
                import importlib
                import llava_vip_tagger
                importlib.reload(llava_vip_tagger)
                from llava_vip_tagger import VipLlavaTagger
                llava_module = VipLlavaTagger(self.app_instance.current_model_id, self.app_instance.use_gpu)
            elif "llava-llama-3" in self.app_instance.current_model_id.lower():
                import importlib
                import llava_llama3_tagger
                importlib.reload(llava_llama3_tagger)
                from llava_llama3_tagger import LLaVALlama3Tagger
                llava_module = LLaVALlama3Tagger(self.app_instance.current_model_id, self.app_instance.use_gpu)
            else:
                # 기본 LLaVA 1.5 모듈 사용
                from llava_captioner_module import get_global_llava_module
                llava_module = get_global_llava_module(self.app_instance.current_model_id, self.app_instance.use_gpu)
            
            # 모델 파일 확인 (공통 인터페이스 사용)
            if llava_module.check_model_files():
                print(f"LLaVA 모델 파일이 이미 다운로드됨: {self.app_instance.current_model_id}")
                self.app_instance.download_progress_label.setText("모델 준비 완료")
                self.app_instance.download_progress_label.show()
            else:
                print(f"LLaVA 모델 파일이 없음, 다운로드 시작: {self.app_instance.current_model_id}")
                self.start_llava_download()
                
        except Exception as e:
            print(f"LLaVA 모델 확인 중 오류: {e}")
    
    def start_llava_download(self):
        """LLaVA 모델 다운로드 시작 (모든 변형 지원)"""
        try:
            # 모델 타입에 따라 적절한 다운로드 스레드 사용
            if "llava-1.5" in self.app_instance.current_model_id.lower():
                from llava_captioner_module import LLaVADownloadThread
                self.app_instance.llava_download_thread = LLaVADownloadThread(self.app_instance.current_model_id, self.app_instance.use_gpu)
            elif "llava-v1.6" in self.app_instance.current_model_id.lower() or "llava-next" in self.app_instance.current_model_id.lower():
                import importlib
                import llava_next_tagger
                importlib.reload(llava_next_tagger)
                print("LOADED FROM:", llava_next_tagger.__file__)
                from llava_next_tagger import LLaVANextDownloadThread
                self.app_instance.llava_download_thread = LLaVANextDownloadThread(self.app_instance.current_model_id, self.app_instance.use_gpu)
            elif "llava-interleave" in self.app_instance.current_model_id.lower():
                import importlib
                import llava_interleave_tagger
                importlib.reload(llava_interleave_tagger)
                from llava_interleave_tagger import LLaVAInterleaveDownloadThread
                self.app_instance.llava_download_thread = LLaVAInterleaveDownloadThread(self.app_instance.current_model_id, self.app_instance.use_gpu)
            elif "vip-llava" in self.app_instance.current_model_id.lower():
                import importlib
                import llava_vip_tagger
                importlib.reload(llava_vip_tagger)
                from llava_vip_tagger import VipLlavaDownloadThread
                self.app_instance.llava_download_thread = VipLlavaDownloadThread(self.app_instance.current_model_id, self.app_instance.use_gpu)
            elif "llava-llama-3" in self.app_instance.current_model_id.lower():
                import importlib
                import llava_llama3_tagger
                importlib.reload(llava_llama3_tagger)
                from llava_llama3_tagger import LLaVALlama3DownloadThread
                self.app_instance.llava_download_thread = LLaVALlama3DownloadThread(self.app_instance.current_model_id, self.app_instance.use_gpu)
            else:
                # 기본 LLaVA 1.5 다운로드 스레드 사용
                from llava_captioner_module import LLaVADownloadThread
                self.app_instance.llava_download_thread = LLaVADownloadThread(self.app_instance.current_model_id, self.app_instance.use_gpu)
            
            # 시그널 연결
            self.app_instance.llava_download_thread.llava_progress_updated.connect(self.on_llava_download_progress)
            self.app_instance.llava_download_thread.download_finished.connect(self.on_llava_download_finished)
            self.app_instance.llava_download_thread.error_occurred.connect(self.on_llava_download_error)
            
            # 다운로드 시작
            self.app_instance.llava_download_thread.start()
            
            print(f"LLaVA 모델 다운로드 시작: {self.app_instance.current_model_id}")
            
        except Exception as e:
            print(f"LLaVA 다운로드 시작 중 오류: {e}")
    
    def check_wd_model_download(self):
        """WD 모델 다운로드 상태 확인 (라바와 통일된 고급 방식)"""
        try:
            from wd_tagger import WdTaggerModel
            from pathlib import Path
            
            # WD 모델 인스턴스 생성하여 파일 확인
            wd_model = WdTaggerModel(self.app_instance.current_model_id, self.app_instance.use_gpu)
            
            # 모델 파일들이 로컬에 있는지 확인 (고급 검증)
            model_name = self.app_instance.current_model_id.split('/')[-1]
            model_dir = Path("models") / model_name
            
            # 필수 파일들 확인
            required_files = ['model.onnx', 'selected_tags.csv', 'config.json']
            all_files_exist = True
            missing_files = []
            
            for filename in required_files:
                file_path = model_dir / filename
                if not file_path.exists():
                    all_files_exist = False
                    missing_files.append(filename)
                else:
                    # 파일 크기 검증 (누락된 파일 검증)
                    try:
                        import requests
                        download_url = f"https://huggingface.co/{self.app_instance.current_model_id}/resolve/main/{filename}"
                        head_response = requests.head(download_url)
                        if head_response.status_code == 200:
                            expected_size = int(head_response.headers.get('content-length', 0))
                            actual_size = file_path.stat().st_size
                            
                            if actual_size != expected_size or expected_size == 0:
                                all_files_exist = False
                                missing_files.append(f"{filename} (불완전)")
                    except Exception:
                        # 검증 실패시 재다운로드
                        all_files_exist = False
                        missing_files.append(f"{filename} (검증실패)")
            
            if all_files_exist:
                print(f"WD 모델 파일이 이미 완전히 다운로드됨: {self.app_instance.current_model_id}")
                self.app_instance.download_progress_label.setText("WD 모델 준비 완료")
                self.app_instance.download_progress_label.show()
            else:
                print(f"WD 모델 파일 누락/불완전, 다운로드 시작: {self.app_instance.current_model_id}")
                print(f"누락된 파일: {missing_files}")
                self.start_wd_download_advanced()
                
        except Exception as e:
            print(f"WD 모델 확인 중 오류: {e}")
    
    def start_wd_download_advanced(self):
        """WD 모델 고급 다운로드 시작 (라바와 통일된 방식)"""
        try:
            from wd_tagger import WdDownloadThread
            from PySide6.QtCore import QTimer
            
            # WD 다운로드 스레드 생성 (LLaVA와 통일)
            self.app_instance.wd_download_thread = WdDownloadThread(self.app_instance.current_model_id, self.app_instance.use_gpu)
            
            # 시그널 연결 (중복 방지)
            try:
                self.app_instance.wd_download_thread.progress_updated.disconnect()
            except:
                pass
            try:
                self.app_instance.wd_download_thread.download_finished.disconnect()
            except:
                pass
            try:
                self.app_instance.wd_download_thread.error_occurred.disconnect()
            except:
                pass
            
            self.app_instance.wd_download_thread.progress_updated.connect(self.on_wd_download_progress)
            self.app_instance.wd_download_thread.download_finished.connect(self.on_wd_download_finished)
            self.app_instance.wd_download_thread.error_occurred.connect(self.on_wd_download_error)
            
            # 다운로드 시작
            self.app_instance.wd_download_thread.start()
            
            print(f"WD 모델 다운로드 스레드 시작: {self.app_instance.current_model_id}")
            self.app_instance.download_progress_label.setText("WD 모델 다운로드 중...")
            self.app_instance.download_progress_label.show()
            self.app_instance.download_progress_bar.show()
            
        except Exception as e:
            print(f"WD 다운로드 시작 중 오류: {e}")
            self.app_instance.download_progress_label.setText(f"WD 모델 다운로드 실패: {e}")
            QTimer.singleShot(2000, self.hide_download_progress)
    
    def hide_download_progress(self):
        """다운로드 진행바 숨김"""
        self.app_instance.download_progress_label.hide()
        self.app_instance.download_progress_bar.hide()
    
    def setup_download_progress_connection(self):
        """다운로드 진행 상황 시그널 연결"""
        from wd_tagger import download_progress_emitter
        download_progress_emitter.progress_updated.connect(self.on_download_progress)
    
    def on_download_progress(self, filename, downloaded, total, status):
        """다운로드 진행 상황 업데이트"""
        if total > 0:
            # 진행바 표시
            progress = int((downloaded / total) * 100)
            self.app_instance.download_progress_bar.setValue(progress)
            self.app_instance.download_progress_bar.show()
            
            # 상태 라벨 업데이트
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.app_instance.download_progress_label.setText(
                f"{filename}: {downloaded_mb:.1f}MB / {total_mb:.1f}MB ({progress}%)"
            )
            self.app_instance.download_progress_label.show()
            
            # 100% 완료 시 1초 후 숨김
            if progress >= 100:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, self.hide_download_progress)
        else:
            # 파일 크기 정보가 없는 경우 (시작/완료)
            self.app_instance.download_progress_label.setText(f"{filename}: {status}")
            self.app_instance.download_progress_label.show()
            if "완료" in status:
                # 완료 시 1초 후 숨김
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, self.hide_download_progress)
    
    def on_wd_download_progress(self, filename, downloaded, total, status):
        """WD 다운로드 진행 상황 업데이트 (바이트 단위 지원)"""
        if total > 0:
            # 진행바 표시
            progress = int((downloaded / total) * 100)
            self.app_instance.download_progress_bar.setValue(progress)
            self.app_instance.download_progress_bar.show()
            
            # status에서 [i/n] 부분만 추출 (진행률 표시 시에는 중복 방지)
            import re
            file_count_match = re.search(r'\[(\d+)/(\d+)\]', status)
            file_count_info = file_count_match.group(0) if file_count_match else ""
            
            # 상태 텍스트 업데이트
            if total >= 1024 * 1024:  # 1MB 이상
                downloaded_mb = downloaded / (1024 * 1024) if downloaded > 0 else 0
                total_mb = total / (1024 * 1024) if total > 0 else 0
                self.app_instance.download_progress_label.setText(
                    f"WD {file_count_info} {filename}: {downloaded_mb:.1f}MB / {total_mb:.1f}MB ({progress}%)"
                )
            else:  # 1MB 미만
                downloaded_kb = downloaded / 1024 if downloaded > 0 else 0
                total_kb = total / 1024 if total > 0 else 0
                self.app_instance.download_progress_label.setText(
                    f"WD {file_count_info} {filename}: {downloaded_kb:.1f}KB / {total_kb:.1f}KB ({progress}%)"
                )
            self.app_instance.download_progress_label.show()
        else:
            # 파일 크기 정보가 없는 경우 (시작/완료) - status 그대로 사용
            self.app_instance.download_progress_label.setText(f"WD {filename}: {status}")
            self.app_instance.download_progress_label.show()
            if "완료" in status:
                # 완료 시 1초 후 숨김
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, self.hide_download_progress)
    
    def on_wd_download_finished(self, success):
        """WD 모델 다운로드 완료"""
        if success:
            print("WD 모델 다운로드 완료")
            self.app_instance.download_progress_label.setText("WD 모델 준비 완료")
        else:
            print("WD 모델 다운로드 실패")
            self.app_instance.download_progress_label.setText("WD 모델 다운로드 실패")
        # 1초 후 숨김
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1000, self.hide_download_progress)
    
    def on_wd_download_error(self, error_message):
        """WD 다운로드 오류"""
        print(f"WD 다운로드 오류: {error_message}")
        self.app_instance.download_progress_label.setText(f"WD 다운로드 오류: {error_message}")
        self.app_instance.download_progress_bar.hide()
    
    def on_llava_download_progress(self, *args):
        """LLaVA 다운로드 진행 상황 업데이트 (방탄 + 명시 렌더링)"""
        # 어떤 시그널이 오든 4필드로 정규화
        filename = ""; downloaded = 0; total = 0; status = ""
        if len(args) >= 1: filename = args[0] or ""
        if len(args) >= 2: downloaded = int(args[1] or 0)
        if len(args) >= 3: total = int(args[2] or 0)
        if len(args) >= 4: status = str(args[3] or "")

        if total > 0:
            pct = int((downloaded / total) * 100)
            self.app_instance.download_progress_bar.setValue(pct)
            self.app_instance.download_progress_bar.show()
            # status는 [i/n] 프리픽스를 포함하므로 그대로 살리고, MB/퍼센트는 명시로 붙임
            self.app_instance.download_progress_label.setText(f"{status} • {filename} — {downloaded}MB / {total}MB ({pct}%)")
            self.app_instance.download_progress_label.show()
        else:
            # 총 용량 미상(HEAD 없음 등)인 경우에도 최소 [i/n]·파일명은 보이도록
            self.app_instance.download_progress_label.setText(f"{status} • {filename}".strip(" •"))
            self.app_instance.download_progress_label.show()

        # UI 즉시 갱신(슬롯 연쇄 시 갱신이 늦는 현상 방지)
        try:
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
        except Exception:
            pass
    
    def on_llava_download_finished(self, success):
        """LLaVA 다운로드 완료"""
        if success:
            print("LLaVA 모델 다운로드 완료")
            self.app_instance.download_progress_label.setText("LLaVA 모델 다운로드 완료")
            self.app_instance.download_progress_bar.hide()
        else:
            print("LLaVA 모델 다운로드 실패")
            self.app_instance.download_progress_label.setText("LLaVA 모델 다운로드 실패")
            self.app_instance.download_progress_bar.hide()
    
    def on_llava_download_error(self, error_message):
        """LLaVA 다운로드 오류"""
        print(f"LLaVA 다운로드 오류: {error_message}")
        self.app_instance.download_progress_label.setText(f"다운로드 오류: {error_message}")
        self.app_instance.download_progress_bar.hide()
    
    def on_gpu_toggled(self, checked):
        """GPU 체크박스 토글 시 호출"""
        if checked:
            # GPU 선택 시 CPU 체크 해제
            self.app_instance.cpu_checkbox.setChecked(False)
            self.app_instance.use_gpu = True
            print("GPU 모드 활성화")
        else:
            # GPU 체크 해제 시 CPU 자동 선택
            self.app_instance.cpu_checkbox.setChecked(True)
            self.app_instance.use_gpu = False
            print("CPU 모드 활성화")
    
    def on_cpu_toggled(self, checked):
        """CPU 체크박스 토글 시 호출"""
        if checked:
            # CPU 선택 시 GPU 체크 해제
            self.app_instance.gpu_checkbox.setChecked(False)
            self.app_instance.use_gpu = False
            print("CPU 모드 활성화")
        else:
            # CPU 체크 해제 시 GPU 자동 선택
            self.app_instance.gpu_checkbox.setChecked(True)
            self.app_instance.use_gpu = True
            print("GPU 모드 활성화")
    
    def auto_tag_current_image(self):
        """현재 이미지 자동 태깅"""
        if hasattr(self.app_instance, 'auto_tag_current_image'):
            self.app_instance.auto_tag_current_image()
    
    def batch_auto_tag_images(self):
        """일괄 자동 태깅"""
        if hasattr(self.app_instance, 'batch_auto_tag_images'):
            self.app_instance.batch_auto_tag_images()
    
    def save_project_database(self):
        """프로젝트 데이터베이스 저장 팝업 표시"""
        try:
            from save_project_module import show_save_project_dialog
            show_save_project_dialog(self.app_instance)
        except Exception as e:
            self.show_custom_message("오류", f"프로젝트 저장 팝업 표시 중 오류가 발생했습니다:\n{str(e)}", "error")
    
    def export_all_tags(self):
        """모든 이미지의 태그를 TXT 파일로 일괄 저장"""
        if not self.app_instance.all_tags:
            self.show_custom_message("경고", "저장할 태그가 없습니다.", "warning")
            return
        
        try:
            from pathlib import Path
            saved_count = 0
            error_count = 0
            
            for image_path, tags in self.app_instance.all_tags.items():
                if tags:  # 태그가 있는 경우만 저장
                    try:
                        # 이미지 파일명에서 확장자를 제거하고 .txt로 변경
                        image_path_obj = Path(image_path)
                        txt_path = image_path_obj.with_suffix('.txt')
                        
                        # 태그들을 공백으로 구분하여 저장
                        tag_text = ', '.join(tags)
                        
                        # UTF-8 인코딩으로 저장
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(tag_text)
                        
                        saved_count += 1
                        
                    except Exception as e:
                        print(f"태그 저장 실패 {image_path}: {e}")
                        error_count += 1
            
            # 결과 메시지
            if error_count == 0:
                self.show_custom_message("성공", f"모든 태그가 저장되었습니다.\n저장된 파일: {saved_count}개", "info")
            else:
                self.show_custom_message("부분 성공", f"태그 저장 완료: {saved_count}개\n실패: {error_count}개", "warning")
            
            if hasattr(self.app_instance, 'statusBar'):
                self.app_instance.statusBar().showMessage(f"태그 일괄 저장 완료: {saved_count}개")
            
        except Exception as e:
            self.show_custom_message("오류", f"태그 일괄 저장 중 오류가 발생했습니다:\n{str(e)}", "error")
    
    def clear_all_tags(self):
        """모든 태그 지우기"""
        if not self.app_instance.all_tags:
            self.show_custom_message("경고", "지울 태그가 없습니다.", "warning")
            return
        
        # 확인 대화상자 (커스텀 스타일 적용)
        from PySide6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self.app_instance)
        msg_box.setWindowTitle("태그 삭제 확인")
        msg_box.setText("모든 이미지의 태그를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        # 다크 테마 스타일 적용
        msg_box.setStyleSheet("""
            QMessageBox {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
                font-family: 'Segoe UI';
            }
            
            QMessageBox QLabel {
                color: #F0F2F5;
                font-size: 12px;
                padding: 10px;
                background: transparent;
                font-family: 'Segoe UI';
            }
            
            QMessageBox QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #EF4444, stop:1 #EF4444);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 600;
                min-width: 80px;
                font-family: 'Segoe UI';
            }
            
            QMessageBox QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #F87171, stop:1 #EF4444);
            }
            
            QMessageBox QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #EF4444, stop:1 #EF4444);
            }
        """)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.Yes:
            # 타임머신 로그를 위한 백업 데이터 수집
            try:
                from timemachine_log import TM
                
                # 삭제 전 상태 백업
                before_all_tags = dict(self.app_instance.all_tags)
                before_current_tags = list(self.app_instance.current_tags)
                before_removed_tags = list(self.app_instance.removed_tags)
                before_global_tag_stats = dict(self.app_instance.global_tag_stats)
                before_manual_tag_info = dict(getattr(self.app_instance, 'manual_tag_info', {}))
                before_tag_confidence = dict(getattr(self.app_instance, 'tag_confidence', {}))
                before_llava_tag_info = dict(getattr(self.app_instance, 'llava_tag_info', {}))
                
                # 클리어올 작업을 타임머신에 기록
                with TM.transaction("Clear All Tags", context={"source": "action_buttons", "user": "System"}):
                    # 각 이미지별로 태그 삭제 기록
                    for image_path, tags in before_all_tags.items():
                        if tags:  # 태그가 있는 이미지만 기록
                            before_removed = []
                            try:
                                before_removed = list(self.app_instance.image_removed_tags.get(image_path, []))
                            except Exception:
                                before_removed = []
                            TM.log_change({
                                "type": "clear_all_tags",
                                "image": image_path,
                                "before": list(tags),
                                "before_image_removed_tags": before_removed,
                                "after": [],
                                "removed_count": len(tags)
                            })
                    
                    # 전역 태그 통계 삭제 기록
                    if before_global_tag_stats:
                        TM.log_change({
                            "type": "global_tag_stats_cleared",
                            "before": dict(before_global_tag_stats),
                            "after": {},
                            "cleared_tags_count": len(before_global_tag_stats)
                        })
                    
                    # 메타데이터 삭제 기록
                    if before_manual_tag_info or before_tag_confidence or before_llava_tag_info:
                        TM.log_change({
                            "type": "clear_all_metadata",
                            "before_manual_tag_info": dict(before_manual_tag_info),
                            "before_tag_confidence": dict(before_tag_confidence),
                            "before_llava_tag_info": dict(before_llava_tag_info),
                            "after_manual_tag_info": {},
                            "after_tag_confidence": {},
                            "after_llava_tag_info": {}
                        })
                
            except Exception as e:
                print(f"[TM ERROR] 클리어올 타임머신 로그 실패: {e}")
                # 타임머신 로그 실패해도 클리어올 작업은 계속 진행
            
            # 모든 태그 삭제
            self.app_instance.all_tags.clear()
            self.app_instance.current_tags.clear()
            self.app_instance.removed_tags.clear()
            self.app_instance.image_removed_tags.clear()
            self.app_instance.tag_confidence.clear()
            self.app_instance.manual_tag_info.clear()
            self.app_instance.llava_tag_info.clear()
            
            # global_tag_stats도 비워서 태그 카드들이 완전히 사라지도록 함
            self.app_instance.global_tag_stats.clear()
            
            # 태그 카드 캐시도 정리 (선택사항 - 메모리 정리)
            if hasattr(self.app_instance, 'tag_statistics_module'):
                for w in list(self.app_instance.tag_statistics_module.tag_card_cache.values()):
                    w.deleteLater()
                self.app_instance.tag_statistics_module.tag_card_cache.clear()
            
            # UI 업데이트
            if hasattr(self.app_instance, 'update_current_tags_display'):
                self.app_instance.update_current_tags_display()
            if hasattr(self.app_instance, 'update_tag_stats'):
                self.app_instance.update_tag_stats()
            if hasattr(self.app_instance, 'update_tag_tree'):
                self.app_instance.update_tag_tree()
            
            self.show_custom_message("완료", "모든 태그가 삭제되었습니다.", "info")
            if hasattr(self.app_instance, 'statusBar'):
                self.app_instance.statusBar().showMessage("모든 태그 삭제 완료")
    
    def show_custom_message(self, title, message, msg_type="info"):
        """커스텀 메시지 박스 표시 (스타일 적용)"""
        from PySide6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self.app_instance)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        # 메시지 타입에 따른 아이콘 설정
        if msg_type == "error":
            msg_box.setIcon(QMessageBox.Critical)
            button_color = "#EF4444"
            button_hover = "#F87171"
        elif msg_type == "warning":
            msg_box.setIcon(QMessageBox.Warning)
            button_color = "#F59E0B"
            button_hover = "#FBBF24"
        else:  # info
            msg_box.setIcon(QMessageBox.Information)
            button_color = "#3B82F6"
            button_hover = "#60A5FA"
        
        # 다크 테마 스타일 적용
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
                font-family: 'Segoe UI';
            }}
            
            QMessageBox QLabel {{
                color: #F0F2F5;
                font-size: 12px;
                padding: 10px;
                background: transparent;
                font-family: 'Segoe UI';
            }}
            
            QMessageBox QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {button_color}, stop:1 {button_color});
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 600;
                min-width: 80px;
                font-family: 'Segoe UI';
            }}
            
            QMessageBox QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {button_hover}, stop:1 {button_color});
            }}
            
            QMessageBox QPushButton:pressed {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {button_color}, stop:1 {button_color});
            }}
        """)
        
        msg_box.exec()


# 단독 실행을 위한 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    class TestApp:
        def __init__(self):
            self.gpu_checkbox = None
            self.cpu_checkbox = None
            self.model_selector = None
            self.model_combo = None
            self.current_model_id = None
            self.use_gpu = None
            self.download_progress_label = None
            self.download_progress_bar = None
            self.btn_auto_tag = None
            self.btn_batch_auto_tag = None
            # 제거됨: self.btn_caption
            self.btn_save = None
            self.btn_export = None
            self.btn_clear = None
        
        def on_gpu_toggled(self, checked):
            print(f"GPU 체크박스: {checked}")
        
        def on_cpu_toggled(self, checked):
            print(f"CPU 체크박스: {checked}")
        
        def auto_tag_current_image(self):
            print("Auto-Tag with AI 클릭")
        
        def batch_auto_tag_images(self):
            print("Batch Auto-Tag 클릭")
        
        def save_tags_to_txt(self):
            print("Save Tags 클릭 - 실제 구현은 ActionButtonsModule에 있음")
        
        def export_all_tags(self):
            print("Export All 클릭 - 실제 구현은 ActionButtonsModule에 있음")
        
        def clear_all_tags(self):
            print("Clear All 클릭 - 실제 구현은 ActionButtonsModule에 있음")
        
        def on_model_changed(self, display_name):
            print(f"모델 변경: {display_name}")
        
        def check_model_download(self):
            print("모델 다운로드 상태 확인")
        
        def start_model_download(self):
            print("모델 다운로드 시작")
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Action Buttons Module Test")
            self.setGeometry(100, 100, 400, 600)
            
            # 중앙 위젯
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 레이아웃
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(10)
            
            # 테스트 앱 인스턴스
            test_app = TestApp()
            
            # 액션 버튼 모듈 생성
            action_buttons_module = ActionButtonsModule(test_app)
            action_card = action_buttons_module.create_action_buttons_section()
            
            layout.addWidget(action_card)
            
            # 스타일시트 적용
            self.setStyleSheet("""
                QMainWindow {
                    background: #1F2937;
                    color: #E5E7EB;
                }
            """)
    
    # 애플리케이션 실행
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
