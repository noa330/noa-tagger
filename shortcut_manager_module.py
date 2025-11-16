# -*- coding: utf-8 -*-
"""
Shortcut Manager Module - 단축키 관리 모듈
실제 단축키 기능 연결 포함
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class ShortcutManagerButton(QPushButton):
    """단축키 매니저 버튼 클래스"""
    
    shortcut_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_button()
    
    def setup_button(self):
        """버튼 설정"""
        self.setText("⌨️")
        self.setFixedSize(60, 50)
        self.setToolTip("Keyboard Shortcuts")
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #CFD8DC;
                border: none;
                font-size: 18px;
                text-decoration: none;
                outline: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        
        # 클릭 시그널 연결
        self.clicked.connect(self.shortcut_clicked.emit)


class ShortcutManager:
    """단축키 매니저 - 단축키 관리 및 실제 기능 연결"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.shortcut_dialog = None
        self.shortcuts = {}  # 단축키 객체 저장
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """모든 단축키 등록 및 기능 연결"""
        print("[단축키 매니저] 단축키 등록 시작...")
        # 파일 관리
        self.register_shortcut("Ctrl+S", self.save_project, "프로젝트 저장")
        self.register_shortcut("Ctrl+O", self.open_file_selector, "프로젝트 불러오기")
        self.register_shortcut("Ctrl+E", self.export_all_tags, "모든 태그 내보내기")
        self.register_shortcut("Ctrl+Shift+Delete", self.clear_all_tags, "모든 태그 지우기")
        
        # 이미지 네비게이션
        self.register_shortcut("Right", self.next_image, "다음 이미지/비디오")
        self.register_shortcut("Left", self.previous_image, "이전 이미지/비디오")
        self.register_shortcut("Home", self.first_image, "첫 번째 이미지/비디오")
        self.register_shortcut("End", self.last_image, "마지막 이미지/비디오")
        self.register_shortcut("PgDown", self.next_image_page, "이미지/비디오 그리드 다음 페이지")
        self.register_shortcut("PgUp", self.previous_image_page, "이미지/비디오 그리드 이전 페이지")
        
        # 비디오 제어
        self.register_shortcut("Ctrl+Space", self.toggle_video_play_pause, "비디오 재생/일시정지")
        self.register_shortcut("Ctrl+S", self.stop_video, "비디오 정지", context="video")
        self.register_shortcut("Ctrl+F", self.extract_video_frames, "비디오 프레임 추출")
        self.register_shortcut("Ctrl+Shift+F", self.goto_extracted_frames, "추출한 프레임으로 이동")
        
        # 검색 및 필터링
        self.register_shortcut("Ctrl+F", self.focus_search, "검색창 포커스")
        self.register_shortcut("F3", self.focus_search, "검색창 포커스 (F3)")
        self.register_shortcut("Ctrl+Shift+F", self.open_advanced_search, "고급 검색 열기")
        self.register_shortcut("Ctrl+I", self.switch_to_image_grid, "이미지 그리드 모드")
        self.register_shortcut("Ctrl+V", self.switch_to_video_grid, "비디오 그리드 모드")
        
        # AI 태깅
        self.register_shortcut("Ctrl+T", self.auto_tag_current, "현재 이미지 AI 태깅")
        self.register_shortcut("Ctrl+Shift+T", self.batch_auto_tag, "일괄 AI 태깅")
        self.register_shortcut("Ctrl+M", self.toggle_miracle_mode, "미라클 모드 토글")
        self.register_shortcut("Ctrl+Shift+M", self.open_miracle_settings, "미라클 설정 열기")
        self.register_shortcut("T", self.focus_tag_autocomplete, "태그 입력창 포커스")
        
        # 모드 전환
        self.register_shortcut("Ctrl+Shift+T", self.toggle_timemachine_mode, "타임머신 모드 토글")
        self.register_shortcut("Ctrl+G", self.toggle_gpu_mode, "GPU 모드 전환")
        self.register_shortcut("Ctrl+Shift+G", self.toggle_cpu_mode, "CPU 모드 전환")
        
        # 네비게이션
        self.register_shortcut("Ctrl+O", self.open_folder, "폴더 열기")
        self.register_shortcut("Ctrl+,", self.open_settings, "설정 열기")
        self.register_shortcut("Ctrl+/", self.open_shortcuts_dialog, "단축키 도움말")
        self.register_shortcut("F1", self.open_shortcuts_dialog, "단축키 도움말 (F1)")
        self.register_shortcut("Alt+Home", self.go_home, "홈으로")
        
        # 창 제어
        self.register_shortcut("Alt+-", self.minimize_window, "창 최소화")
        self.register_shortcut("Alt+=", self.toggle_maximize, "창 최대화/복원")
        
        # 타임머신
        self.register_shortcut("Ctrl+Z", self.timemachine_undo, "Undo")
        self.register_shortcut("Ctrl+Shift+Z", self.timemachine_redo, "Redo")
        self.register_shortcut("Ctrl+[", self.timemachine_prev_branch, "이전 브랜치")
        self.register_shortcut("Ctrl+]", self.timemachine_next_branch, "다음 브랜치")
        
        # 태그 스타일시트 에디터
        self.register_shortcut("Ctrl+Shift+S", self.open_stylesheet_editor, "태그 스타일시트 에디터")
        
        # 모델 관리
        self.register_shortcut("Ctrl+Shift+M", self.open_model_selector, "모델 선택")
        print(f"[단축키 매니저] 단축키 등록 완료 (총 {len(self.shortcuts)}개)")
    
    def register_shortcut(self, key_sequence, handler, description, context=None):
        """단축키 등록"""
        try:
            shortcut = QShortcut(QKeySequence(key_sequence), self.app)
            shortcut.activated.connect(handler)
            shortcut.setContext(Qt.WidgetShortcut if context else Qt.ApplicationShortcut)
            self.shortcuts[key_sequence] = {
                'shortcut': shortcut,
                'handler': handler,
                'description': description,
                'context': context
            }
            print(f"[단축키 등록 성공] {key_sequence} -> {description}")
        except Exception as e:
            print(f"[단축키 등록 실패] {key_sequence}: {e}")
    
    def open_shortcuts(self):
        """단축키 관리 창 열기"""
        if self.shortcut_dialog is None:
            self.shortcut_dialog = ShortcutDialog(self.app, self)
        self.shortcut_dialog.show()
        self.shortcut_dialog.raise_()
        self.shortcut_dialog.activateWindow()
    
    # === 실제 기능 연결 함수들 ===
    
    def save_project(self):
        """프로젝트 저장"""
        print("[단축키 호출] Ctrl+S - 프로젝트 저장")
        try:
            from save_project_module import show_save_project_dialog
            show_save_project_dialog(self.app)
        except Exception as e:
            print(f"[오류] 프로젝트 저장: {e}")
    
    def open_file_selector(self):
        """파일 셀렉터 열기"""
        print("[단축키 호출] Ctrl+O - 파일 셀렉터 열기")
        try:
            if hasattr(self.app, 'folder_manager'):
                self.app.folder_manager.open_folder()
            else:
                print("[경고] folder_manager 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 파일 셀렉터 열기: {e}")
    
    def export_all_tags(self):
        """모든 태그 내보내기"""
        print("[단축키 호출] Ctrl+E - 모든 태그 내보내기")
        try:
            if hasattr(self.app, 'btn_export'):
                self.app.btn_export.click()
            else:
                print("[경고] btn_export 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 태그 내보내기: {e}")
    
    def clear_all_tags(self):
        """모든 태그 지우기"""
        print("[단축키 호출] Ctrl+Shift+Delete - 모든 태그 지우기")
        try:
            if hasattr(self.app, 'btn_clear'):
                self.app.btn_clear.click()
            else:
                print("[경고] btn_clear 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 태그 지우기: {e}")
    
    def _is_video_mode(self):
        """현재 비디오 모드인지 확인"""
        if hasattr(self.app, 'image_filter_btn') and hasattr(self.app, 'video_filter_btn'):
            return self.app.video_filter_btn.isChecked() and not self.app.image_filter_btn.isChecked()
        return False
    
    def next_image(self):
        """다음 이미지/비디오"""
        print("[단축키 호출] Right - 다음 이미지/비디오")
        try:
            if self._is_video_mode():
                # 비디오 모드: 다음 비디오로 이동
                if hasattr(self.app, 'video_frame_module') and self.app.video_frame_module:
                    if hasattr(self.app.video_frame_module, 'video_preview_card'):
                        card = self.app.video_frame_module.video_preview_card
                        if card:
                            card.next_video()
                            print("[정보] 다음 비디오로 이동")
                        else:
                            print("[경고] video_preview_card가 None입니다")
                    else:
                        print("[경고] video_preview_card 속성이 없습니다")
                else:
                    print("[경고] video_frame_module이 없습니다")
            else:
                # 이미지 모드: 다음 이미지로 이동
                from image_preview_module import next_image
                next_image(self.app)
        except Exception as e:
            print(f"[오류] 다음 이미지/비디오: {e}")
            import traceback
            traceback.print_exc()
    
    def previous_image(self):
        """이전 이미지/비디오"""
        print("[단축키 호출] Left - 이전 이미지/비디오")
        try:
            if self._is_video_mode():
                # 비디오 모드: 이전 비디오로 이동
                if hasattr(self.app, 'video_frame_module') and self.app.video_frame_module:
                    if hasattr(self.app.video_frame_module, 'video_preview_card'):
                        card = self.app.video_frame_module.video_preview_card
                        if card:
                            card.previous_video()
                            print("[정보] 이전 비디오로 이동")
                        else:
                            print("[경고] video_preview_card가 None입니다")
                    else:
                        print("[경고] video_preview_card 속성이 없습니다")
                else:
                    print("[경고] video_frame_module이 없습니다")
            else:
                # 이미지 모드: 이전 이미지로 이동
                from image_preview_module import previous_image
                previous_image(self.app)
        except Exception as e:
            print(f"[오류] 이전 이미지/비디오: {e}")
            import traceback
            traceback.print_exc()
    
    def first_image(self):
        """첫 번째 이미지/비디오"""
        print("[단축키 호출] Home - 첫 번째 이미지/비디오")
        try:
            if self._is_video_mode():
                # 비디오 모드: 첫 번째 비디오로 이동
                video_list = None
                if hasattr(self.app, 'video_list') and self.app.video_list:
                    video_list = self.app.video_list
                elif hasattr(self.app, 'video_files') and self.app.video_files:
                    video_list = [str(v) for v in self.app.video_files]
                
                if video_list and len(video_list) > 0:
                    from video_preview_module import load_video_from_module
                    load_video_from_module(self.app, video_list[0])
                    print("[정보] 첫 번째 비디오로 이동")
                else:
                    print("[경고] video_list 또는 video_files가 없거나 비어있습니다")
            else:
                # 이미지 모드: 첫 번째 이미지로 이동
                if hasattr(self.app, 'image_files') and self.app.image_files:
                    from image_preview_module import load_image
                    load_image(self.app, str(self.app.image_files[0]))
                else:
                    print("[경고] image_files가 없거나 비어있습니다")
        except Exception as e:
            print(f"[오류] 첫 번째 이미지/비디오: {e}")
            import traceback
            traceback.print_exc()
    
    def last_image(self):
        """마지막 이미지/비디오"""
        print("[단축키 호출] End - 마지막 이미지/비디오")
        try:
            if self._is_video_mode():
                # 비디오 모드: 마지막 비디오로 이동
                video_list = None
                if hasattr(self.app, 'video_list') and self.app.video_list:
                    video_list = self.app.video_list
                elif hasattr(self.app, 'video_files') and self.app.video_files:
                    video_list = [str(v) for v in self.app.video_files]
                
                if video_list and len(video_list) > 0:
                    from video_preview_module import load_video_from_module
                    load_video_from_module(self.app, video_list[-1])
                    print("[정보] 마지막 비디오로 이동")
                else:
                    print("[경고] video_list 또는 video_files가 없거나 비어있습니다")
            else:
                # 이미지 모드: 마지막 이미지로 이동
                if hasattr(self.app, 'image_files') and self.app.image_files:
                    from image_preview_module import load_image
                    load_image(self.app, str(self.app.image_files[-1]))
                else:
                    print("[경고] image_files가 없거나 비어있습니다")
        except Exception as e:
            print(f"[오류] 마지막 이미지/비디오: {e}")
            import traceback
            traceback.print_exc()
    
    def next_image_page(self):
        """이미지/비디오 그리드 다음 페이지"""
        print("[단축키 호출] Page Down - 이미지/비디오 그리드 다음 페이지")
        try:
            if self._is_video_mode():
                # 비디오 모드: 비디오 그리드 다음 페이지
                from search_filter_grid_video_module import change_video_page
                change_video_page(self.app, 1)
                print("[정보] 비디오 그리드 다음 페이지로 이동")
            else:
                # 이미지 모드: 이미지 그리드 다음 페이지
                from search_filter_grid_image_module import change_image_page
                change_image_page(self.app, 1)
        except Exception as e:
            print(f"[오류] 다음 페이지: {e}")
            import traceback
            traceback.print_exc()
    
    def previous_image_page(self):
        """이미지/비디오 그리드 이전 페이지"""
        print("[단축키 호출] Page Up - 이미지/비디오 그리드 이전 페이지")
        try:
            if self._is_video_mode():
                # 비디오 모드: 비디오 그리드 이전 페이지
                from search_filter_grid_video_module import change_video_page
                change_video_page(self.app, -1)
                print("[정보] 비디오 그리드 이전 페이지로 이동")
            else:
                # 이미지 모드: 이미지 그리드 이전 페이지
                from search_filter_grid_image_module import change_image_page
                change_image_page(self.app, -1)
        except Exception as e:
            print(f"[오류] 이전 페이지: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_video_play_pause(self):
        """비디오 재생/일시정지"""
        print("[단축키 호출] Ctrl+Space - 비디오 재생/일시정지")
        try:
            if hasattr(self.app, 'video_frame_module') and self.app.video_frame_module:
                if hasattr(self.app.video_frame_module, 'video_preview_card'):
                    card = self.app.video_frame_module.video_preview_card
                    if card:
                        card.toggle_play_pause()
                    else:
                        print("[경고] video_preview_card가 None입니다")
                else:
                    print("[경고] video_preview_card 속성이 없습니다")
            else:
                print("[경고] video_frame_module이 없습니다")
        except Exception as e:
            print(f"[오류] 비디오 재생/일시정지: {e}")
    
    def stop_video(self):
        """비디오 정지"""
        print("[단축키 호출] Ctrl+S (비디오 모드) - 비디오 정지")
        try:
            if hasattr(self.app, 'video_frame_module') and self.app.video_frame_module:
                if hasattr(self.app.video_frame_module, 'video_preview_card'):
                    card = self.app.video_frame_module.video_preview_card
                    if card:
                        card.stop_video()
                    else:
                        print("[경고] video_preview_card가 None입니다")
                else:
                    print("[경고] video_preview_card 속성이 없습니다")
            else:
                print("[경고] video_frame_module이 없습니다")
        except Exception as e:
            print(f"[오류] 비디오 정지: {e}")
    
    def extract_video_frames(self):
        """비디오 프레임 추출"""
        print("[단축키 호출] Ctrl+F (비디오 모드) - 비디오 프레임 추출")
        try:
            if hasattr(self.app, 'video_frame_module') and self.app.video_frame_module:
                if hasattr(self.app.video_frame_module, 'frame_extraction_options'):
                    options = self.app.video_frame_module.frame_extraction_options
                    if options:
                        options.on_extract_clicked()
                        print("[정보] 프레임 추출 시작")
                    else:
                        print("[경고] frame_extraction_options가 None입니다")
                else:
                    print("[경고] frame_extraction_options 속성이 없습니다")
            else:
                print("[경고] video_frame_module이 없습니다")
        except Exception as e:
            print(f"[오류] 프레임 추출: {e}")
            import traceback
            traceback.print_exc()
    
    def goto_extracted_frames(self):
        """추출한 프레임으로 이동"""
        print("[단축키 호출] Ctrl+Shift+F - 추출한 프레임으로 이동")
        try:
            if hasattr(self.app, 'video_frame_module') and self.app.video_frame_module:
                if hasattr(self.app.video_frame_module, 'frame_extraction_options'):
                    options = self.app.video_frame_module.frame_extraction_options
                    if options:
                        options.on_goto_frames_clicked()
                        print("[정보] 추출한 프레임으로 이동")
                    else:
                        print("[경고] frame_extraction_options가 None입니다")
                else:
                    print("[경고] frame_extraction_options 속성이 없습니다")
            else:
                print("[경고] video_frame_module이 없습니다")
        except Exception as e:
            print(f"[오류] 프레임 이동: {e}")
            import traceback
            traceback.print_exc()
    
    def focus_search(self):
        """검색창 포커스"""
        print("[단축키 호출] Ctrl+F 또는 F3 - 검색창 포커스")
        try:
            if hasattr(self.app, 'filter_input'):
                # 위젯이 보이도록 보장
                self.app.filter_input.setVisible(True)
                self.app.filter_input.setEnabled(True)
                # 부모 위젯들도 표시 및 활성화
                parent = self.app.filter_input.parent()
                while parent:
                    if hasattr(parent, 'setVisible'):
                        parent.setVisible(True)
                    if hasattr(parent, 'setEnabled'):
                        parent.setEnabled(True)
                    if hasattr(parent, 'show'):
                        parent.show()
                    parent = parent.parent()
                
                # 창 활성화
                if hasattr(self.app, 'activateWindow'):
                    self.app.activateWindow()
                if hasattr(self.app, 'raise'):
                    getattr(self.app, 'raise')()
                
                # 이벤트 처리
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()
                
                # 포커스 설정
                self.app.filter_input.setFocus()
                QApplication.processEvents()
                
                # focusInEvent를 수동으로 트리거하여 고급 검색 표시
                from PySide6.QtGui import QFocusEvent
                from PySide6.QtCore import Qt
                focus_event = QFocusEvent(QFocusEvent.FocusIn, Qt.OtherFocusReason)
                self.app.filter_input.focusInEvent(focus_event)
                QApplication.processEvents()
            else:
                print("[경고] filter_input 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 검색창 포커스: {e}")
            import traceback
            traceback.print_exc()
    
    def open_advanced_search(self):
        """고급 검색 열기"""
        print("[단축키 호출] Ctrl+Shift+F - 고급 검색 열기")
        try:
            if hasattr(self.app, 'filter_input'):
                self.app.filter_input.setFocus()
                # 고급 검색은 검색창 포커스 시 자동으로 열림
            else:
                print("[경고] filter_input 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 고급 검색 열기: {e}")
    
    def switch_to_image_grid(self):
        """이미지 그리드 모드로 전환"""
        print("[단축키 호출] Ctrl+I - 이미지 그리드 모드로 전환")
        try:
            if hasattr(self.app, 'image_filter_btn'):
                self.app.image_filter_btn.setChecked(True)
            if hasattr(self.app, 'video_filter_btn'):
                self.app.video_filter_btn.setChecked(False)
            from search_filter_grid_image_module import switch_to_image_grid
            switch_to_image_grid(self.app)
        except Exception as e:
            print(f"[오류] 이미지 그리드 전환: {e}")
    
    def switch_to_video_grid(self):
        """비디오 그리드 모드로 전환"""
        print("[단축키 호출] Ctrl+V - 비디오 그리드 모드로 전환")
        try:
            if hasattr(self.app, 'video_filter_btn'):
                self.app.video_filter_btn.setChecked(True)
            if hasattr(self.app, 'image_filter_btn'):
                self.app.image_filter_btn.setChecked(False)
            from search_filter_grid_video_module import switch_to_video_grid
            switch_to_video_grid(self.app)
        except Exception as e:
            print(f"[오류] 비디오 그리드 전환: {e}")
    
    def focus_tag_autocomplete(self):
        """태그 입력창 포커스"""
        print("[단축키 호출] T - 태그 입력창 포커스")
        try:
            # 태깅 카드가 숨겨져 있으면 표시
            if hasattr(self.app, 'tagging_card') and self.app.tagging_card:
                self.app.tagging_card.setVisible(True)
                self.app.tagging_card.setEnabled(True)
                self.app.tagging_card.show()
            
            if hasattr(self.app, 'tag_input_widget') and self.app.tag_input_widget:
                # 태그 입력 위젯 표시 및 활성화
                self.app.tag_input_widget.setVisible(True)
                self.app.tag_input_widget.setEnabled(True)
                self.app.tag_input_widget.show()
                
                if hasattr(self.app.tag_input_widget, 'tag_input'):
                    tag_input = self.app.tag_input_widget.tag_input
                    # 태그 입력창 표시 및 활성화
                    tag_input.setVisible(True)
                    tag_input.setEnabled(True)
                    tag_input.show()
                    
                    # 창 활성화
                    if hasattr(self.app, 'activateWindow'):
                        self.app.activateWindow()
                    if hasattr(self.app, 'raise'):
                        getattr(self.app, 'raise')()
                    
                    # 이벤트 처리
                    from PySide6.QtWidgets import QApplication
                    QApplication.processEvents()
                    
                    # 태그 입력창에 포커스
                    tag_input.setFocus()
                    QApplication.processEvents()
                    print("[정보] 태그 입력창 포커스 완료")
                else:
                    print("[경고] tag_input_widget.tag_input 속성이 없습니다")
            else:
                print("[경고] tag_input_widget 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 태그 입력창 포커스: {e}")
            import traceback
            traceback.print_exc()
    
    def auto_tag_current(self):
        """현재 이미지 AI 태깅"""
        print("[단축키 호출] Ctrl+T - 현재 이미지 AI 태깅")
        try:
            if hasattr(self.app, 'btn_auto_tag'):
                self.app.btn_auto_tag.click()
            else:
                print("[경고] btn_auto_tag 속성이 없습니다")
        except Exception as e:
            print(f"[오류] AI 태깅: {e}")
    
    def batch_auto_tag(self):
        """일괄 AI 태깅"""
        print("[단축키 호출] Ctrl+Shift+T - 일괄 AI 태깅")
        try:
            if hasattr(self.app, 'btn_batch_auto_tag'):
                self.app.btn_batch_auto_tag.click()
            else:
                print("[경고] btn_batch_auto_tag 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 일괄 AI 태깅: {e}")
    
    def toggle_miracle_mode(self):
        """미라클 모드 토글"""
        print("[단축키 호출] Ctrl+M - 미라클 모드 토글")
        try:
            if hasattr(self.app, 'miracle_manager'):
                self.app.miracle_manager.toggle_miracle_mode()
            else:
                print("[경고] miracle_manager 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 미라클 모드 토글: {e}")
    
    def open_miracle_settings(self):
        """미라클 설정 열기"""
        print("[단축키 호출] Ctrl+Shift+M - 미라클 설정 열기")
        try:
            if hasattr(self.app, 'miracle_manager'):
                if hasattr(self.app.miracle_manager, 'miracle_tag_input'):
                    if hasattr(self.app.miracle_manager.miracle_tag_input, 'open_miracle_settings'):
                        self.app.miracle_manager.miracle_tag_input.open_miracle_settings()
                    else:
                        print("[경고] open_miracle_settings 메서드가 없습니다")
                else:
                    print("[경고] miracle_tag_input 속성이 없습니다")
            else:
                print("[경고] miracle_manager 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 미라클 설정 열기: {e}")
    
    def toggle_timemachine_mode(self):
        """타임머신 모드 토글"""
        print("[단축키 호출] Ctrl+Shift+T - 타임머신 모드 토글")
        try:
            if hasattr(self.app, 'timemachine_manager'):
                self.app.timemachine_manager.toggle_timemachine_mode()
            else:
                print("[경고] timemachine_manager 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 타임머신 모드 토글: {e}")
    
    def toggle_gpu_mode(self):
        """GPU 모드 전환"""
        print("[단축키 호출] Ctrl+G - GPU 모드 전환")
        try:
            if hasattr(self.app, 'gpu_checkbox'):
                self.app.gpu_checkbox.setChecked(True)
            else:
                print("[경고] gpu_checkbox 속성이 없습니다")
        except Exception as e:
            print(f"[오류] GPU 모드 전환: {e}")
    
    def toggle_cpu_mode(self):
        """CPU 모드 전환"""
        print("[단축키 호출] Ctrl+Shift+G - CPU 모드 전환")
        try:
            if hasattr(self.app, 'cpu_checkbox'):
                self.app.cpu_checkbox.setChecked(True)
            else:
                print("[경고] cpu_checkbox 속성이 없습니다")
        except Exception as e:
            print(f"[오류] CPU 모드 전환: {e}")
    
    def open_folder(self):
        """폴더 열기"""
        print("[단축키 호출] Ctrl+O - 폴더 열기")
        try:
            if hasattr(self.app, 'folder_manager'):
                self.app.folder_manager.open_folder()
            else:
                print("[경고] folder_manager 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 폴더 열기: {e}")
    
    def open_settings(self):
        """설정 열기"""
        print("[단축키 호출] Ctrl+, - 설정 열기")
        try:
            if hasattr(self.app, 'open_settings'):
                self.app.open_settings()
            else:
                print("[경고] open_settings 메서드가 없습니다")
        except Exception as e:
            print(f"[오류] 설정 열기: {e}")
    
    def open_shortcuts_dialog(self):
        """단축키 도움말 열기"""
        print("[단축키 호출] Ctrl+/ 또는 F1 - 단축키 도움말 열기")
        self.open_shortcuts()
    
    def go_home(self):
        """홈으로"""
        print("[단축키 호출] Alt+Home - 홈으로")
        try:
            if hasattr(self.app, 'btn_home'):
                self.app.btn_home.click()
            else:
                print("[경고] btn_home 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 홈 이동: {e}")
    
    def minimize_window(self):
        """창 최소화"""
        print("[단축키 호출] Alt+- - 창 최소화")
        try:
            self.app.showMinimized()
        except Exception as e:
            print(f"[오류] 창 최소화: {e}")
    
    def toggle_maximize(self):
        """창 최대화/복원"""
        print("[단축키 호출] Alt+= - 창 최대화/복원")
        try:
            if self.app.isMaximized():
                self.app.showNormal()
            else:
                self.app.showMaximized()
        except Exception as e:
            print(f"[오류] 창 최대화/복원: {e}")
    
    def timemachine_undo(self):
        """타임머신 Undo - 한 개씩만 실행"""
        print("[단축키 호출] Ctrl+Z - Undo")
        try:
            if hasattr(self.app, 'timemachine_manager') and self.app.timemachine_manager:
                tm = self.app.timemachine_manager
                # 현재 인덱스 확인
                current = tm._current_index
                timeline_len = len(tm._timeline)
                
                if current >= 0 and timeline_len > 0:
                    # Undo: 한 개씩만 실행
                    # 현재 인덱스의 레코드를 Undo
                    record = tm._timeline[current]
                    tm._apply(record, False)  # is_redo=False
                    
                    # 인덱스 업데이트
                    new_index = current - 1
                    tm._current_index = new_index
                    tm._branches[tm._viewing_branch]["current_index"] = new_index
                    
                    # 브랜치 상태 저장
                    tm._persist_branch_state()
                    
                    # UI 업데이트
                    if hasattr(tm, "timeline_panel"):
                        tm.timeline_panel.update_states(new_index)
                    if hasattr(self.app, 'update_current_tags_display'):
                        self.app.update_current_tags_display()
                    if hasattr(self.app, 'update_tag_stats'):
                        self.app.update_tag_stats()
                    
                    print(f"[정보] Undo: {current} -> {new_index} (한 개만 실행)")
                else:
                    print("[정보] Undo할 항목이 없습니다")
            else:
                print("[경고] timemachine_manager가 없습니다")
        except Exception as e:
            print(f"[오류] Undo: {e}")
            import traceback
            traceback.print_exc()
    
    def timemachine_redo(self):
        """타임머신 Redo - 한 개씩만 실행"""
        print("[단축키 호출] Ctrl+Shift+Z - Redo")
        try:
            if hasattr(self.app, 'timemachine_manager') and self.app.timemachine_manager:
                tm = self.app.timemachine_manager
                # 현재 인덱스 확인
                current = tm._current_index
                timeline_len = len(tm._timeline)
                
                if current < timeline_len - 1:
                    # Redo: 한 개씩만 실행
                    # 다음 인덱스의 레코드를 Redo
                    next_index = current + 1
                    record = tm._timeline[next_index]
                    tm._apply(record, True)  # is_redo=True
                    
                    # 인덱스 업데이트
                    tm._current_index = next_index
                    tm._branches[tm._viewing_branch]["current_index"] = next_index
                    
                    # 브랜치 상태 저장
                    tm._persist_branch_state()
                    
                    # UI 업데이트
                    if hasattr(tm, "timeline_panel"):
                        tm.timeline_panel.update_states(next_index)
                    if hasattr(self.app, 'update_current_tags_display'):
                        self.app.update_current_tags_display()
                    if hasattr(self.app, 'update_tag_stats'):
                        self.app.update_tag_stats()
                    
                    print(f"[정보] Redo: {current} -> {next_index} (한 개만 실행)")
                else:
                    print("[정보] Redo할 항목이 없습니다")
            else:
                print("[경고] timemachine_manager가 없습니다")
        except Exception as e:
            print(f"[오류] Redo: {e}")
            import traceback
            traceback.print_exc()
    
    def timemachine_prev_branch(self):
        """타임머신 이전 브랜치"""
        print("[단축키 호출] Ctrl+[ - 타임머신 이전 브랜치")
        try:
            if hasattr(self.app, 'timemachine_manager') and self.app.timemachine_manager:
                tm = self.app.timemachine_manager
                current_branch = tm._viewing_branch
                total_branches = len(tm._branches)
                
                if total_branches <= 1:
                    print("[정보] 전환할 브랜치가 없습니다")
                    return
                
                # 현재 위치에서 사용 가능한 브랜치들 찾기
                current_index = tm._current_index
                available_branches = tm._get_branches_at_position(current_index)
                
                if len(available_branches) <= 1:
                    # 현재 위치에 분기가 없으면, 단순히 이전 브랜치 인덱스로 이동
                    prev_branch = (current_branch - 1) % total_branches
                    if prev_branch != current_branch:
                        # 현재 인덱스를 record_index로 사용
                        tm.switch_to_branch_at_position(current_index, prev_branch)
                        print(f"[정보] 이전 브랜치로 전환: {current_branch} -> {prev_branch}")
                    else:
                        print("[정보] 전환할 이전 브랜치가 없습니다")
                else:
                    # 현재 위치에 분기가 있으면, 사용 가능한 브랜치 중에서 이전 브랜치 찾기
                    branch_indices = [b[0] for b in available_branches]
                    current_pos = branch_indices.index(current_branch) if current_branch in branch_indices else -1
                    
                    if current_pos > 0:
                        prev_branch_idx = branch_indices[current_pos - 1]
                        tm.switch_to_branch_at_position(current_index, prev_branch_idx)
                        print(f"[정보] 분기점에서 이전 브랜치로 전환: {current_branch} -> {prev_branch_idx}")
                    else:
                        print("[정보] 분기점에서 전환할 이전 브랜치가 없습니다")
            else:
                print("[경고] timemachine_manager가 없습니다")
        except Exception as e:
            print(f"[오류] 이전 브랜치: {e}")
            import traceback
            traceback.print_exc()
    
    def timemachine_next_branch(self):
        """타임머신 다음 브랜치"""
        print("[단축키 호출] Ctrl+] - 타임머신 다음 브랜치")
        try:
            if hasattr(self.app, 'timemachine_manager') and self.app.timemachine_manager:
                tm = self.app.timemachine_manager
                current_branch = tm._viewing_branch
                total_branches = len(tm._branches)
                
                if total_branches <= 1:
                    print("[정보] 전환할 브랜치가 없습니다")
                    return
                
                # 현재 위치에서 사용 가능한 브랜치들 찾기
                current_index = tm._current_index
                available_branches = tm._get_branches_at_position(current_index)
                
                if len(available_branches) <= 1:
                    # 현재 위치에 분기가 없으면, 단순히 다음 브랜치 인덱스로 이동
                    next_branch = (current_branch + 1) % total_branches
                    if next_branch != current_branch:
                        # 현재 인덱스를 record_index로 사용
                        tm.switch_to_branch_at_position(current_index, next_branch)
                        print(f"[정보] 다음 브랜치로 전환: {current_branch} -> {next_branch}")
                    else:
                        print("[정보] 전환할 다음 브랜치가 없습니다")
                else:
                    # 현재 위치에 분기가 있으면, 사용 가능한 브랜치 중에서 다음 브랜치 찾기
                    branch_indices = [b[0] for b in available_branches]
                    current_pos = branch_indices.index(current_branch) if current_branch in branch_indices else -1
                    
                    if current_pos >= 0 and current_pos < len(branch_indices) - 1:
                        next_branch_idx = branch_indices[current_pos + 1]
                        tm.switch_to_branch_at_position(current_index, next_branch_idx)
                        print(f"[정보] 분기점에서 다음 브랜치로 전환: {current_branch} -> {next_branch_idx}")
                    else:
                        print("[정보] 분기점에서 전환할 다음 브랜치가 없습니다")
            else:
                print("[경고] timemachine_manager가 없습니다")
        except Exception as e:
            print(f"[오류] 다음 브랜치: {e}")
            import traceback
            traceback.print_exc()
    
    def open_stylesheet_editor(self):
        """태그 스타일시트 에디터 열기"""
        print("[단축키 호출] Ctrl+Shift+S - 태그 스타일시트 에디터 열기")
        try:
            # 태그 스타일시트 에디터 가져오기 (없으면 생성)
            if not hasattr(self.app, 'tag_stylesheet_editor'):
                from tag_stylesheet_editor_module import create_tag_stylesheet_editor
                self.app.tag_stylesheet_editor = create_tag_stylesheet_editor(self.app)
                print("[정보] tag_stylesheet_editor 생성 완료")
            
            # 리모컨도 함께 생성
            if not hasattr(self.app, 'tag_stylesheet_editor_remote') or not self.app.tag_stylesheet_editor_remote:
                from tag_stylesheet_editor_remote_module import create_tag_stylesheet_editor_remote
                self.app.tag_stylesheet_editor_remote = create_tag_stylesheet_editor_remote(self.app)
                print("[정보] tag_stylesheet_editor_remote 생성 완료")
            
            # 에디터 카드 열기 - 현재 이미지의 태그가 있으면 첫 번째 태그 사용
            if hasattr(self.app, 'current_tags') and self.app.current_tags:
                first_tag = self.app.current_tags[0]
                print(f"[정보] 현재 이미지의 첫 번째 태그로 에디터 열기: {first_tag}")
                self.app.tag_stylesheet_editor.create_or_update_tag_edit_card(first_tag)
            else:
                # 태그가 없으면 빈 카드 생성
                print("[정보] 현재 이미지에 태그가 없어 빈 카드 생성")
                if not hasattr(self.app, 'tag_edit_card') or not self.app.tag_edit_card:
                    self.app.tag_stylesheet_editor.create_initial_card()
                else:
                    # 기존 카드가 있으면 오버레이로 표시
                    from center_panel_overlay_plugin import CenterPanelOverlayPlugin
                    overlay_plugin = CenterPanelOverlayPlugin(self.app)
                    overlay_plugin.show_overlay_card(self.app.tag_edit_card, "tag_editor")
            
            # 리모컨 표시
            if hasattr(self.app, 'tag_stylesheet_editor_remote') and self.app.tag_stylesheet_editor_remote:
                self.app.tag_stylesheet_editor_remote.show_remote()
                print("[정보] 태그 스타일시트 에디터 리모컨 표시 완료")
            else:
                print("[경고] tag_stylesheet_editor_remote를 표시할 수 없습니다")
        except Exception as e:
            print(f"[오류] 스타일시트 에디터 열기: {e}")
            import traceback
            traceback.print_exc()
    
    def open_model_selector(self):
        """모델 선택"""
        print("[단축키 호출] Ctrl+Shift+M - 모델 선택")
        try:
            if hasattr(self.app, 'model_combo'):
                self.app.model_combo.showPopup()
            else:
                print("[경고] model_combo 속성이 없습니다")
        except Exception as e:
            print(f"[오류] 모델 선택: {e}")
    
class ShortcutDialog(QDialog):
    """단축키 관리 대화상자"""
    
    def __init__(self, app_instance, shortcut_manager, parent=None):
        super().__init__(parent)
        self.app_instance = app_instance
        self.shortcut_manager = shortcut_manager
        
        # 디버그 매니저 초기화
        from shortcut_manager_debug_module import ShortcutDebugManager
        self.debug_manager = ShortcutDebugManager(app_instance)
        # shortcut_manager 참조 저장 (디버그 창에서 사용)
        self.debug_manager.shortcut_manager = shortcut_manager
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("Keyboard Shortcuts")
        self.setModal(False)
        # 최소 크기 설정 (컨텐츠가 잘리지 않도록)
        self.setMinimumSize(1200, 700)
        self.resize(1200, 700)
        
        # 메인 대화상자 스타일 적용 (설정 모듈과 동일한 그라데이션 네이비 배경)
        # QDialog는 전역 스타일을 상속받지 않으므로 스크롤바 스타일도 명시적으로 추가
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
            }
            
            /* Scrollbars - 메인 모듈 전역 스타일과 동일 */
            QScrollBar:vertical {
                background: rgba(26,27,38,0.8);
                width: 8px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical {
                background: rgba(75,85,99,0.6);
                border-radius: 4px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: rgba(75,85,99,0.8);
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: rgba(26,27,38,1.0);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목 (파일 셀렉터와 동일한 스타일)
        title_label = QLabel("Keyboard Shortcuts")
        title_label.setStyleSheet("""
            font-size: 25px;
            font-weight: 700;
            color: #E2E8F0;
            margin-bottom: 8px;
            font-family: 'Segoe UI';
        """)
        layout.addWidget(title_label)
        
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # 스크롤바는 메인 모듈의 전역 스타일 사용 (별도 스타일 지정 안 함)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        # 스크롤 영역 내부 위젯
        scroll_content = QWidget()
        scroll_content.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        scroll_layout = QHBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(10, 0, 10, 0)  # 좌우 여백 추가
        
        # 단축키 데이터 정의 (명확한 키 표시)
        shortcuts_data = [
            # Column 1 (4개)
            [
                {
                    "category": "File Management",
                    "items": [
                        ("Save Project", ["Ctrl", "S"]),
                        ("Open Project", ["Ctrl", "O"]),
                        ("Export All Tags", ["Ctrl", "E"]),
                        ("Clear All Tags", ["Ctrl", "Shift", "Delete"])
                    ]
                },
                {
                    "category": "Image/Video Navigation",
                    "items": [
                        ("Next Image/Video", ["Right"]),
                        ("Previous Image/Video", ["Left"]),
                        ("First Image/Video", ["Home"]),
                        ("Last Image/Video", ["End"]),
                        ("Next Page", ["Page Down"]),
                        ("Previous Page", ["Page Up"])
                    ]
                },
                {
                    "category": "Video Controls",
                    "items": [
                        ("Play/Pause", ["Ctrl", "Space"]),
                        ("Stop Video", ["Ctrl", "S"]),
                        ("Extract Frames", ["Ctrl", "F"]),
                        ("Go to Frames", ["Ctrl", "Shift", "F"])
                    ]
                },
                {
                    "category": "Search & Filtering",
                    "items": [
                        ("Focus Search", ["Ctrl", "F"]),
                        ("Focus Search (F3)", ["F3"]),
                        ("Advanced Search", ["Ctrl", "Shift", "F"]),
                        ("Image Grid Mode", ["Ctrl", "I"]),
                        ("Video Grid Mode", ["Ctrl", "V"])
                    ]
                }
            ],
            # Column 2 (4개)
            [
                {
                    "category": "AI Tagging",
                    "items": [
                        ("Auto-Tag Current", ["Ctrl", "T"]),
                        ("Batch Auto-Tag", ["Ctrl", "Shift", "T"]),
                        ("Toggle Miracle Mode", ["Ctrl", "M"]),
                        ("Miracle Settings", ["Ctrl", "Shift", "M"]),
                        ("Focus Tag Input", ["T"])
                    ]
                },
                {
                    "category": "Mode Switching",
                    "items": [
                        ("Toggle Time Machine", ["Ctrl", "Shift", "T"]),
                        ("GPU Mode", ["Ctrl", "G"]),
                        ("CPU Mode", ["Ctrl", "Shift", "G"])
                    ]
                },
                {
                    "category": "Navigation",
                    "items": [
                        ("Open Folder", ["Ctrl", "O"]),
                        ("Open Settings", ["Ctrl", ","]),
                        ("Keyboard Shortcuts", ["Ctrl", "/"]),
                        ("Keyboard Shortcuts (F1)", ["F1"]),
                        ("Go Home", ["Alt", "Home"])
                    ]
                }
            ],
            # Column 3 (3개)
            [
                {
                    "category": "Window Controls",
                    "items": [
                        ("Minimize", ["Alt", "-"]),
                        ("Maximize/Restore", ["Alt", "="])
                    ]
                },
                {
                    "category": "Time Machine",
                    "items": [
                        ("Undo", ["Ctrl", "Z"]),
                        ("Redo", ["Ctrl", "Shift", "Z"]),
                        ("Previous Branch", ["Ctrl", "["]),
                        ("Next Branch", ["Ctrl", "]"])
                    ]
                },
                {
                    "category": "Other",
                    "items": [
                        ("Stylesheet Editor", ["Ctrl", "Shift", "S"]),
                        ("Model Selector", ["Ctrl", "Shift", "M"])
                    ]
                }
            ]
        ]
        
        # 각 컬럼 생성
        for column_data in shortcuts_data:
            column_widget = self.create_column(column_data)
            scroll_layout.addWidget(column_widget)
        
        scroll_layout.addStretch()
        
        # 스크롤 영역에 컨텐츠 설정
        scroll_area.setWidget(scroll_content)
        
        # 레이아웃에 스크롤 영역 추가
        layout.addWidget(scroll_area)
        
        # 닫기 버튼 (파일 셀렉터와 동일한 스타일)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("닫기")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #6B7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #4B5563;
            }
            QPushButton:pressed {
                background: #374151;
            }
        """)
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_column(self, categories):
        """단일 컬럼 위젯 생성"""
        column_widget = QWidget()
        # 컬럼 최소 너비 설정 (내용이 잘리지 않도록)
        column_widget.setMinimumWidth(300)
        column_layout = QVBoxLayout(column_widget)
        column_layout.setSpacing(20)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setAlignment(Qt.AlignTop)
        
        for category_data in categories:
            category_widget = self.create_category(category_data)
            column_layout.addWidget(category_widget)
        
        column_layout.addStretch()
        
        return column_widget
    
    def create_category(self, category_data):
        """카테고리 위젯 생성"""
        category_name = category_data["category"]
        items = category_data["items"]
        
        # 카테고리 컨테이너
        category_widget = QWidget()
        category_layout = QVBoxLayout(category_widget)
        category_layout.setSpacing(8)
        category_layout.setContentsMargins(0, 0, 0, 0)
        
        # 카테고리 제목
        title_label = QLabel(category_name)
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 8px;
            }
        """)
        category_layout.addWidget(title_label)
        
        # 구분선 추가 (고급 검색 모듈과 동일한 스타일)
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("""
            QFrame {
                background-color: rgba(75,85,99,0.3);
                border: none;
                margin: 10px 20px;
            }
        """)
        category_layout.addWidget(separator)
        
        # 단축키 아이템들
        for action_name, keys in items:
            item_widget = self.create_shortcut_item(action_name, keys)
            category_layout.addWidget(item_widget)
        
        return category_widget
    
    def create_shortcut_item(self, action_name, keys):
        """단축키 아이템 위젯 생성"""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setSpacing(12)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setAlignment(Qt.AlignLeft)
        
        # 액션 이름
        action_label = QLabel(action_name)
        action_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                min-width: 200px;
            }
        """)
        item_layout.addWidget(action_label)
        
        # 키 조합
        keys_layout = QHBoxLayout()
        keys_layout.setSpacing(4)
        keys_layout.setContentsMargins(0, 0, 0, 0)
        
        for key in keys:
            key_button = QPushButton(key)
            key_button.setEnabled(True)  # 클릭 가능하도록 활성화
            key_button.setFixedHeight(24)
            key_button.setStyleSheet("""
                QPushButton {
                    background: rgba(60, 60, 70, 0.8);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                    font-weight: 500;
                    min-width: 30px;
                }
                QPushButton:pressed {
                    background: rgba(80, 80, 90, 1.0);
                }
            """)
            # 클릭 이벤트 연결 (10번 연속 클릭 감지용)
            key_button.clicked.connect(lambda checked=False, btn=key_button: self.on_key_button_clicked(btn))
            keys_layout.addWidget(key_button)
        
        keys_layout.addStretch()
        item_layout.addLayout(keys_layout)
        item_layout.addStretch()
        
        return item_widget
    
    def on_key_button_clicked(self, key_button):
        """키버튼 클릭 이벤트 핸들러"""
        # 디버그 매니저에 클릭 이벤트 전달
        if hasattr(self, 'debug_manager'):
            self.debug_manager.on_key_button_clicked(key_button)
