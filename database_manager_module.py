# -*- coding: utf-8 -*-
"""
데이터베이스 관리 모듈
프로젝트별 이미지 복사 및 태그 정보 저장/불러오기 기능
폴더 관리 기능 추가
"""

import json
import shutil
import os
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class FolderManagerButton(QPushButton):
    """폴더 관리 버튼"""
    folder_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__("📁", parent)
        self.setFixedSize(60, 50)
        self.setToolTip("프로젝트 불러오기 / 폴더 선택")
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
        self.clicked.connect(self.folder_clicked.emit)


class FolderManager:
    """폴더 관리 클래스"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.db_manager = DatabaseManager(app_instance)
    
    def load_tags_from_txt(self, image_path):
        """이미지와 동일한 이름의 txt 파일에서 태그를 읽어옴 (엔터/콤마로 분리)"""
        try:
            image_path_obj = Path(image_path)
            # txt 파일 경로 생성 (이미지와 동일한 이름, 확장자만 .txt)
            txt_path = image_path_obj.with_suffix('.txt')
            
            # txt 파일이 존재하는지 확인
            if not txt_path.exists():
                return []
            
            # txt 파일 읽기
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return []
            
            # 엔터와 콤마로 태그 분리
            tags = []
            # 먼저 엔터로 분리
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 각 줄을 콤마로도 분리
                comma_tags = [tag.strip() for tag in line.split(',')]
                tags.extend([tag for tag in comma_tags if tag])
            
            # 중복 제거 및 빈 태그 제거
            tags = list(dict.fromkeys(tags))  # 순서 유지하면서 중복 제거
            
            return tags
        except Exception as e:
            print(f"txt 파일에서 태그 읽기 오류 ({image_path}): {e}")
            return []
    
    def apply_txt_tags_to_image(self, image_path, tags):
        """이미지에 태그를 추가"""
        try:
            if not tags:
                return
            
            from image_tagging_module import add_tag
            from all_tags_manager import add_tag_to_all_tags
            
            # 이미지 경로를 문자열로 변환
            image_key = str(image_path)
            
            # all_tags 초기화
            if not hasattr(self.app_instance, 'all_tags'):
                self.app_instance.all_tags = {}
            if image_key not in self.app_instance.all_tags:
                self.app_instance.all_tags[image_key] = []
            
            # 각 태그 추가
            for tag in tags:
                if tag and tag not in self.app_instance.all_tags[image_key]:
                    # all_tags에 추가
                    self.app_instance.all_tags[image_key].append(tag)
                    
                    # 글로벌 태그 관리
                    from global_tag_manager import add_global_tag
                    add_global_tag(self.app_instance, tag, False)
                    
                    # all_tags_manager에도 추가
                    add_tag_to_all_tags(self.app_instance, image_key, tag, False)
            
            print(f"txt 태그 적용 완료 ({image_path}): {len(tags)}개 태그")
        except Exception as e:
            print(f"태그 적용 오류 ({image_path}): {e}")
    
    def open_folder(self):
        """프로젝트 불러오기 또는 폴더 선택"""
        try:
            projects = self.db_manager.get_available_projects()
            
            if projects:
                # 저장된 프로젝트가 있으면 선택 대화상자 표시
                dialog = ProjectSelectionDialog(projects, self.app_instance)
                result = dialog.exec()
                
                if result == QDialog.Accepted:
                    # 프로젝트가 선택된 경우
                    selected = dialog.get_selected_project()
                    if selected:
                        self.db_manager.load_project_database(selected["folder"])
                        return
                    
                    # 폴더가 선택된 경우
                    selected_folder = getattr(dialog, 'selected_folder', None)
                    if selected_folder:
                        self.app_instance.current_folder = selected_folder
                        # txt 태그 불러오기 체크박스 상태 확인
                        load_txt_tags = getattr(dialog, 'txt_tag_checkbox', None) and dialog.txt_tag_checkbox.isChecked()
                        self.load_images_from_folder(selected_folder, load_txt_tags=load_txt_tags)
                        return
                    
                    # 파일이 선택된 경우
                    selected_files = getattr(dialog, 'selected_images', None)
                    if selected_files:
                        # txt 태그 불러오기 체크박스 상태 확인
                        load_txt_tags = getattr(dialog, 'txt_tag_checkbox', None) and dialog.txt_tag_checkbox.isChecked()
                        self.db_manager.load_files_from_files(selected_files, load_txt_tags=load_txt_tags)
                        return
                
                # QDialog.Rejected (취소/X버튼)인 경우 아무것도 하지 않음
                return
            
            # 프로젝트가 없는 경우에만 폴더 선택
            folder = QFileDialog.getExistingDirectory(self.app_instance, "Select Image Folder")
            if folder:
                self.app_instance.current_folder = folder
                self.load_images_from_folder(folder)
                
        except Exception as e:
            print(f"프로젝트/폴더 불러오기 오류: {e}")
            # 오류 발생 시 기존 폴더 선택 방식으로 폴백
            folder = QFileDialog.getExistingDirectory(self.app_instance, "Select Image Folder")
            if folder:
                self.app_instance.current_folder = folder
                self.load_images_from_folder(folder)
    
    def load_images_from_folder(self, folder_path, load_txt_tags=False):
        """폴더에서 이미지 파일들을 로드"""
        print(f"폴더 로드 시작: {folder_path}")
        
        # 지원하는 미디어 확장자
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        
        # 기존 이미지들 제거 (이미지 모듈에서 처리)
        from search_filter_grid_image_module import clear_image_grid
        clear_image_grid(self.app_instance)
        
        # 기존 비디오들 제거 (비디오 모듈에서 처리)
        from search_filter_grid_video_module import clear_video_grid
        clear_video_grid(self.app_instance)
        
        # 전체 상태 초기화 (태그, 응답 카드, 타임머신 등)
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.clear_existing_data()
            else:
                self.clear_existing_data()
        except AttributeError:
            self.clear_existing_data()
        
        # 프로젝트 명 초기화 (폴더/파일 불러오기는 프로젝트 명 없음)
        self.app_instance.current_project_name = None
        
        # 타임머신 로그 완전 초기화 🔥
        try:
            from timemachine_log import TM
            TM.clear_logs()
            print("[TM LOG] 타임머신 로그 완전 초기화")
            
            # 타임머신 모듈도 초기화
            if hasattr(self.app_instance, 'timemachine_manager'):
                tm_module = self.app_instance.timemachine_manager
                # 브랜치 구조 완전 초기화
                tm_module._branches = [{
                    "records": [],
                    "current_index": -1,
                    "name": "main",
                    "forked_from": None
                }]
                tm_module._active_branch = 0
                tm_module._viewing_branch = 0
                tm_module._timeline = []
                tm_module._current_index = -1
                print("[TM LOG] 타임머신 모듈 브랜치 구조 초기화")
                
                # UI 패널도 완전 초기화
                if hasattr(tm_module, 'timeline_panel') and tm_module.timeline_panel:
                    tm_module.timeline_panel.clear_cards()
                    # 타임라인과 타임스탬프도 초기화
                    tm_module.timeline_panel.timeline.set_entries([])
                    tm_module.timeline_panel.time_labels.set_entries([])
                    print("[TM LOG] 타임머신 UI 패널 완전 초기화")
        except Exception as e:
            print(f"[TM LOG] 타임머신 초기화 실패: {e}")
        
        # 태그 스타일시트 에디터 초기화
        if hasattr(self.app_instance, 'tag_stylesheet_editor') and self.app_instance.tag_stylesheet_editor:
            self.app_instance.tag_stylesheet_editor.reset_editor()
        
        # 태깅 패널 초기화
        from image_tagging_module import clear_tagging_panel
        clear_tagging_panel(self.app_instance)
        
        # 폴더에서 이미지/비디오 파일들을 분리해서 찾기
        self.app_instance.image_files = []
        self.app_instance.video_files = []
        try:
            folder_path_obj = Path(folder_path)
            print(f"폴더 경로 객체: {folder_path_obj}")
            print(f"폴더 존재 여부: {folder_path_obj.exists()}")
            
            for file_path in folder_path_obj.iterdir():
                print(f"파일 발견: {file_path}, 확장자: {file_path.suffix.lower()}")
                if file_path.is_file():
                    if file_path.suffix.lower() in image_extensions:
                        self.app_instance.image_files.append(file_path)
                        print(f"이미지 파일 추가: {file_path}")
                    elif file_path.suffix.lower() in video_extensions:
                        self.app_instance.video_files.append(file_path)
                        print(f"비디오 파일 추가: {file_path}")
            
            # 원본 이미지/비디오 목록 저장 (검색/필터 초기화용)
            self.app_instance.original_image_files = self.app_instance.image_files.copy()
            self.app_instance.original_video_files = self.app_instance.video_files.copy()
            print(f"원본 이미지 목록 저장: {len(self.app_instance.original_image_files)}개")
            print(f"원본 비디오 목록 저장: {len(self.app_instance.original_video_files)}개")
            
            print(f"총 로드된 이미지 수: {len(self.app_instance.image_files)}")
            print(f"총 로드된 비디오 수: {len(self.app_instance.video_files)}")
            
            # txt 태그 불러오기 (이미지만 해당, 동영상은 제외)
            if load_txt_tags and self.app_instance.image_files:
                print("txt 태그 불러오기 시작...")
                txt_tag_count = 0
                for image_path in self.app_instance.image_files:
                    tags = self.load_tags_from_txt(image_path)
                    if tags:
                        self.apply_txt_tags_to_image(image_path, tags)
                        txt_tag_count += len(tags)
                print(f"txt 태그 불러오기 완료: {txt_tag_count}개 태그 적용")
            
            # 이미지와 비디오가 모두 0장인 경우 조기 종료 (무한 로딩 방지)
            if len(self.app_instance.image_files) == 0 and len(self.app_instance.video_files) == 0:
                print("이미지/비디오 0장 - 로딩 중단")
                try:
                    if hasattr(self.app_instance, 'action_buttons_module') and self.app_instance.action_buttons_module:
                        self.app_instance.action_buttons_module.show_custom_message("알림", "선택한 폴더에 이미지나 비디오가 없습니다.", "warning")
                    else:
                        QMessageBox.information(self.app_instance, "알림", "선택한 폴더에 이미지나 비디오가 없습니다.")
                except Exception:
                    pass
                return
            
        except Exception as e:
            print(f"이미지 로드 오류: {e}")
            if hasattr(self.app_instance, 'action_buttons_module'):
                self.app_instance.action_buttons_module.show_custom_message("Error", f"Failed to load images: {str(e)}", "error")
            return
        
        # 이미지 그리드 업데이트 (통합 함수 사용 - 중복 방지)
        from search_module import update_image_grid_unified
        self.app_instance.active_grid_token += 1
        update_image_grid_unified(self.app_instance, expected_token=self.app_instance.active_grid_token)
        
        # 첫 번째 이미지 자동 선택 (파란색 테두리 표시)
        if hasattr(self.app_instance, 'image_files') and self.app_instance.image_files:
            from PySide6.QtCore import QTimer
            def select_first_image():
                first_image_path = str(self.app_instance.image_files[0])
                print(f"첫 번째 이미지 자동 선택: {first_image_path}")
                from image_preview_module import load_image
                load_image(self.app_instance, first_image_path)
                # 선택 상태 강제 업데이트
                from search_filter_grid_image_module import _refresh_image_grid_selection_visuals
                _refresh_image_grid_selection_visuals(self.app_instance)
            # 썸네일 생성 완료 후 선택 (약간의 딜레이)
            QTimer.singleShot(300, select_first_image)
        
        # 비디오가 있으면 비디오 그리드도 초기화
        if hasattr(self.app_instance, 'video_files') and self.app_instance.video_files:
            print(f"비디오 {len(self.app_instance.video_files)}개 발견 - 비디오 그리드 초기화")
            from search_filter_grid_video_module import create_video_grid_in_place, refresh_video_thumbnails
            create_video_grid_in_place(self.app_instance)
            # 동영상 썸네일 생성 (페이지네이션 적용)
            refresh_video_thumbnails(self.app_instance)
        
        # 카운터 업데이트
        from search_module import update_image_counter
        update_image_counter(self.app_instance, len(self.app_instance.image_files), len(self.app_instance.image_files))
        self.app_instance.statusBar().showMessage(f"Loaded {len(self.app_instance.image_files)} images from {folder_path}")
        
        # 전체 태그 통계 초기화 및 업데이트
        if hasattr(self.app_instance, 'global_tag_stats'):
            self.app_instance.global_tag_stats.clear()
        if hasattr(self.app_instance, 'update_global_tag_stats'):
            self.app_instance.update_global_tag_stats()
        
        # 태그 트리 업데이트 (폴더 로드 시)
        if hasattr(self.app_instance, 'update_tag_tree'):
            self.app_instance.update_tag_tree()
        
        # 고급 검색이 활성화된 상태라면 상태 복구
        if (hasattr(self.app_instance, 'advanced_search_card') and 
            self.app_instance.advanced_search_card and 
            self.app_instance.advanced_search_card.isVisible()):
            print("고급 검색이 활성화된 상태에서 폴더 로드 - 상태 복구")
            # center_splitter 사이즈를 고급 검색 모드로 복구
            if hasattr(self.app_instance, 'center_splitter'):
                # 고급 검색 카드가 center_splitter에 추가되어 있는지 확인
                if self.app_instance.advanced_search_card.parent() == self.app_instance.center_splitter:
                    # 고급 검색 모드로 사이즈 설정
                    current_count = self.app_instance.center_splitter.count()
                    if hasattr(self.app_instance, 'advanced_search_original_sizes'):
                        total_size = sum(self.app_instance.advanced_search_original_sizes)
                    else:
                        # 고급 검색 사이즈가 없으면 현재 사이즈 사용
                        total_size = sum(self.app_instance.center_splitter.sizes())
                    
                    # 현재 패널 개수에 맞춰 사이즈 배열 생성
                    if current_count == 3:
                        self.app_instance.center_splitter.setSizes([0, 0, total_size])
                        print(f"고급 검색 모드로 사이즈 복구 완료 (3패널): [0, 0, {total_size}]")
                    elif current_count == 4:
                        self.app_instance.center_splitter.setSizes([0, 0, total_size, 0])
                        print(f"고급 검색 모드로 사이즈 복구 완료 (4패널): [0, 0, {total_size}, 0]")
                    else:
                        print(f"예상치 못한 패널 개수: {current_count}")
                        self.app_instance.center_splitter.setSizes([0, 0, total_size])
        
        print(f"이미지 로드 완료: {len(self.app_instance.image_files)}개")


class DatabaseManager:
    """데이터베이스 관리 클래스"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.script_folder = Path(__file__).parent  # 스크립트 폴더 경로
        self.projects_folder = self.script_folder / "projects"
        self.projects_folder.mkdir(exist_ok=True)
    
    def load_tags_from_txt(self, image_path):
        """이미지와 동일한 이름의 txt 파일에서 태그를 읽어옴 (엔터/콤마로 분리)"""
        try:
            image_path_obj = Path(image_path)
            # txt 파일 경로 생성 (이미지와 동일한 이름, 확장자만 .txt)
            txt_path = image_path_obj.with_suffix('.txt')
            
            # txt 파일이 존재하는지 확인
            if not txt_path.exists():
                return []
            
            # txt 파일 읽기
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return []
            
            # 엔터와 콤마로 태그 분리
            tags = []
            # 먼저 엔터로 분리
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 각 줄을 콤마로도 분리
                comma_tags = [tag.strip() for tag in line.split(',')]
                tags.extend([tag for tag in comma_tags if tag])
            
            # 중복 제거 및 빈 태그 제거
            tags = list(dict.fromkeys(tags))  # 순서 유지하면서 중복 제거
            
            return tags
        except Exception as e:
            print(f"txt 파일에서 태그 읽기 오류 ({image_path}): {e}")
            return []
    
    def apply_txt_tags_to_image(self, image_path, tags):
        """이미지에 태그를 추가"""
        try:
            if not tags:
                return
            
            from image_tagging_module import add_tag
            from all_tags_manager import add_tag_to_all_tags
            
            # 이미지 경로를 문자열로 변환
            image_key = str(image_path)
            
            # all_tags 초기화
            if not hasattr(self.app_instance, 'all_tags'):
                self.app_instance.all_tags = {}
            if image_key not in self.app_instance.all_tags:
                self.app_instance.all_tags[image_key] = []
            
            # 각 태그 추가
            for tag in tags:
                if tag and tag not in self.app_instance.all_tags[image_key]:
                    # all_tags에 추가
                    self.app_instance.all_tags[image_key].append(tag)
                    
                    # 글로벌 태그 관리
                    from global_tag_manager import add_global_tag
                    add_global_tag(self.app_instance, tag, False)
                    
                    # all_tags_manager에도 추가
                    add_tag_to_all_tags(self.app_instance, image_key, tag, False)
            
            print(f"txt 태그 적용 완료 ({image_path}): {len(tags)}개 태그")
        except Exception as e:
            print(f"태그 적용 오류 ({image_path}): {e}")
    
    def get_next_project_number(self):
        """다음 프로젝트 번호 계산"""
        existing_projects = []
        for item in self.projects_folder.iterdir():
            if item.is_dir() and item.name.startswith("project"):
                try:
                    num = int(item.name.replace("project", ""))
                    existing_projects.append(num)
                except ValueError:
                    continue
        
        if not existing_projects:
            return 1
        return max(existing_projects) + 1
    
    def save_project_database(self, overwrite=False, project_name=None):
        """프로젝트 데이터베이스 저장"""
        if not hasattr(self.app_instance, 'current_image') or not self.app_instance.current_image:
            self.show_message("경고", "저장할 이미지가 선택되지 않았습니다.", "warning")
            return False
        
        try:
            # 덮어쓰기 모드 확인
            current_project_name = getattr(self.app_instance, 'current_project_name', None)
            
            if overwrite:
                # 덮어쓰기 모드: 같은 이름이 있으면 덮어쓰기, 없으면 새로 생성
                if project_name:
                    # 편집된 프로젝트명 사용
                    project_folder = self.projects_folder / project_name
                    if not project_folder.exists():
                        # 같은 이름의 프로젝트가 없으면 새로 생성
                        project_folder.mkdir(exist_ok=True)
                elif current_project_name:
                    # 프로젝트명이 없으면 현재 프로젝트에 덮어쓰기
                    project_folder = self.projects_folder / current_project_name
                    if not project_folder.exists():
                        self.show_message("오류", f"기존 프로젝트 폴더를 찾을 수 없습니다: {current_project_name}", "error")
                        return False
                else:
                    # 프로젝트명도 없고 현재 프로젝트도 없으면 자동 번호로 새로 생성
                    project_num = self.get_next_project_number()
                    project_folder = self.projects_folder / f"project{project_num}"
                    project_folder.mkdir(exist_ok=True)
            else:
                # 새 프로젝트 저장
                if project_name:
                    # 사용자가 입력한 프로젝트명 사용
                    project_folder = self.projects_folder / project_name
                    if project_folder.exists():
                        self.show_message("오류", f"이미 존재하는 프로젝트명입니다: {project_name}", "error")
                        return False
                    project_folder.mkdir(exist_ok=True)
                else:
                    # 프로젝트 번호로 자동 생성 (기존 호환성)
                    project_num = self.get_next_project_number()
                    project_folder = self.projects_folder / f"project{project_num}"
                    project_folder.mkdir(exist_ok=True)
            
            # images 하위 폴더 생성
            images_folder = project_folder / "images"
            images_folder.mkdir(exist_ok=True)
            
            # 현재 폴더의 모든 이미지 복사
            image_files = getattr(self.app_instance, 'image_files', [])
            video_files = getattr(self.app_instance, 'video_files', [])
            
            if not image_files and not video_files:
                self.show_message("오류", "저장할 미디어 파일이 없습니다.", "error")
                return False
            
            # 덮어쓰기 모드인 경우 기존 파일 목록 저장
            # 실제로 기존 프로젝트 폴더가 존재하는 경우에만 덮어쓰기 모드로 처리
            old_image_files = set()
            old_txt_files = set()
            is_overwrite_mode = overwrite and project_folder.exists() and (project_folder / "database.json").exists()
            if is_overwrite_mode:
                # 기존 이미지 파일 목록 수집
                for old_file in images_folder.iterdir():
                    if old_file.is_file():
                        if old_file.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}:
                            old_image_files.add(old_file.name)
                        elif old_file.suffix.lower() == '.txt':
                            old_txt_files.add(old_file.name)
            
            # 데이터베이스 정보 먼저 수집 (덮어쓰기 전에)
            database_info = self.collect_database_info_for_project(images_folder)
            
            # 데이터베이스 파일 먼저 저장 (덮어쓰기)
            database_file = project_folder / "database.json"
            try:
                with open(database_file, 'w', encoding='utf-8') as f:
                    json.dump(database_info, f, ensure_ascii=False, indent=2)
            except Exception as json_error:
                print(f"JSON 저장 오류: {json_error}")
                print(f"데이터베이스 정보 타입: {type(database_info)}")
                print(f"데이터베이스 정보 키들: {list(database_info.keys()) if isinstance(database_info, dict) else 'Not a dict'}")
                
                # 문제가 되는 데이터 찾기
                for key, value in database_info.items():
                    try:
                        json.dumps(value)
                    except Exception as e:
                        print(f"문제가 되는 키 '{key}': {e}")
                        print(f"값 타입: {type(value)}")
                        if isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                try:
                                    json.dumps(sub_value)
                                except Exception as sub_e:
                                    print(f"  하위 키 '{sub_key}': {sub_e}")
                                    print(f"  하위 값 타입: {type(sub_value)}")
                
                raise json_error
            
            copied_count = 0
            txt_saved_count = 0
            new_image_files = set()
            new_txt_files = set()
            
            # 이미지 파일 복사
            for image_path in image_files:
                try:
                    image_path_obj = Path(image_path)
                    if image_path_obj.exists():
                        copied_image_path = images_folder / image_path_obj.name
                        # 덮어쓰기 모드가 아니거나 파일이 없을 때만 복사
                        if not is_overwrite_mode or not copied_image_path.exists():
                            shutil.copy2(image_path_obj, copied_image_path)
                            copied_count += 1
                        new_image_files.add(image_path_obj.name)
                        
                        # 해당 이미지의 TXT 파일이 있으면 복사
                        txt_path = image_path_obj.with_suffix('.txt')
                        if txt_path.exists():
                            copied_txt_path = images_folder / txt_path.name
                            if not is_overwrite_mode or not copied_txt_path.exists():
                                shutil.copy2(txt_path, copied_txt_path)
                        
                        # all_tags에서 태그를 가져와서 txt 파일로 저장
                        image_key = str(image_path)
                        all_tags = getattr(self.app_instance, 'all_tags', {})
                        if image_key in all_tags:
                            tags = all_tags[image_key]
                            if tags:  # 태그가 있는 경우만 저장
                                try:
                                    # 복사된 이미지와 동일한 이름의 txt 파일 경로 생성
                                    copied_txt_path = images_folder / image_path_obj.with_suffix('.txt').name
                                    
                                    # 태그를 콤마로 구분하여 저장
                                    tag_text = ', '.join(tags)
                                    
                                    # UTF-8 인코딩으로 저장 (덮어쓰기)
                                    with open(copied_txt_path, 'w', encoding='utf-8') as f:
                                        f.write(tag_text)
                                    
                                    new_txt_files.add(copied_txt_path.name)
                                    txt_saved_count += 1
                                    print(f"태그 txt 파일 저장: {copied_txt_path.name} ({len(tags)}개 태그)")
                                except Exception as txt_error:
                                    print(f"태그 txt 파일 저장 실패 {image_path}: {txt_error}")
                        else:
                            # 태그가 없는 경우 txt 파일명도 기록 (삭제 대상 확인용)
                            txt_filename = image_path_obj.with_suffix('.txt').name
                            # 실제 txt 파일이 있는지 확인
                            txt_path_check = images_folder / txt_filename
                            if txt_path_check.exists():
                                new_txt_files.add(txt_filename)
                            
                except Exception as e:
                    print(f"이미지 복사 실패 {image_path}: {e}")
                    continue
            
            # 동영상은 원본 경로만 기록 (복사하지 않음)
            video_paths_recorded = 0
            for video_path in video_files:
                try:
                    video_path_obj = Path(video_path)
                    if video_path_obj.exists():
                        video_paths_recorded += 1
                except Exception as e:
                    print(f"동영상 경로 확인 실패 {video_path}: {e}")
                    continue
            
            if copied_count == 0 and video_paths_recorded == 0 and not is_overwrite_mode:
                self.show_message("오류", "미디어 파일 처리에 실패했습니다.", "error")
                return False
            
            # 덮어쓰기 모드인 경우: 구버전에 있지만 새 버전에 없는 파일 삭제
            deleted_count = 0
            if is_overwrite_mode:
                # 구버전에 있지만 새 버전에 없는 이미지 파일 삭제
                files_to_delete = old_image_files - new_image_files
                for filename in files_to_delete:
                    try:
                        file_path = images_folder / filename
                        if file_path.exists():
                            file_path.unlink()
                            deleted_count += 1
                            print(f"삭제된 이미지: {filename}")
                    except Exception as e:
                        print(f"이미지 삭제 실패 {filename}: {e}")
                
                # 구버전에 있지만 새 버전에 없는 txt 파일 삭제
                txt_files_to_delete = old_txt_files - new_txt_files
                for filename in txt_files_to_delete:
                    try:
                        file_path = images_folder / filename
                        if file_path.exists():
                            file_path.unlink()
                            print(f"삭제된 txt 파일: {filename}")
                    except Exception as e:
                        print(f"txt 파일 삭제 실패 {filename}: {e}")
            
            # 메시지 구성
            project_name = project_folder.name
            if is_overwrite_mode:
                message = f"프로젝트 '{project_name}'이 덮어쓰기되었습니다.\n"
                if copied_count > 0:
                    message += f"추가된 이미지: {copied_count}개\n"
                if deleted_count > 0:
                    message += f"삭제된 이미지: {deleted_count}개\n"
                message += f"태그 txt 파일: {txt_saved_count}개\n"
                message += f"경로: {project_folder}"
            else:
                message = f"프로젝트 '{project_name}'이 저장되었습니다.\n복사된 이미지: {copied_count}개\n태그 txt 파일: {txt_saved_count}개\n경로: {project_folder}"
            
            self.show_message("성공", message, "info")
            
            # 저장된 프로젝트명 업데이트
            if not is_overwrite_mode:
                self.app_instance.current_project_name = project_folder.name
            
            return True
            
        except Exception as e:
            self.show_message("오류", f"프로젝트 저장 중 오류가 발생했습니다:\n{str(e)}", "error")
            return False
    
    def collect_database_info_for_project(self, images_folder):
        """프로젝트용 데이터베이스 정보 수집 (이미지 경로를 파일명으로 변환)"""
        # Path 객체를 문자열로 변환하는 헬퍼 함수
        def convert_paths_to_strings(data):
            if isinstance(data, Path):
                return str(data)
            elif isinstance(data, list):
                return [convert_paths_to_strings(item) for item in data]
            elif isinstance(data, dict):
                return {str(key): convert_paths_to_strings(value) for key, value in data.items()}
            elif isinstance(data, set):
                return list(data)  # set을 list로 변환
            else:
                return data
        
        # 이미지 경로를 파일명으로 변환하는 함수
        def convert_image_paths_to_filenames(data):
            if isinstance(data, dict):
                result = {}
                for key, value in data.items():
                    key_str = str(key)
                    key_lower = key_str.lower()
                    if isinstance(key, (str, Path)) and key_lower.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')):
                        # 이미지 경로를 파일명으로 변환 (대소문자 무관 확장자 처리)
                        filename = Path(key_str).name
                        result[filename] = convert_image_paths_to_filenames(value)
                    else:
                        result[key_str] = convert_image_paths_to_filenames(value)
                return result
            elif isinstance(data, list):
                return [convert_image_paths_to_filenames(item) for item in data]
            else:
                return data
        
        # 안전하게 데이터 수집
        try:
            all_tags = getattr(self.app_instance, 'all_tags', {})
            current_tags = getattr(self.app_instance, 'current_tags', [])
            removed_tags = getattr(self.app_instance, 'removed_tags', [])
            global_tag_stats = getattr(self.app_instance, 'global_tag_stats', {})
            image_removed_tags = getattr(self.app_instance, 'image_removed_tags', {})
            tag_confidence = getattr(self.app_instance, 'tag_confidence', {})
            manual_tag_info = getattr(self.app_instance, 'manual_tag_info', {})
            llava_tag_info = getattr(self.app_instance, 'llava_tag_info', {})
            image_files = getattr(self.app_instance, 'image_files', [])
            original_image_files = getattr(self.app_instance, 'original_image_files', [])
            video_files = getattr(self.app_instance, 'video_files', [])
            original_video_files = getattr(self.app_instance, 'original_video_files', [])
            
            # 현재 이미지 파일명
            current_image_filename = Path(getattr(self.app_instance, 'current_image', '')).name
            
            database_info = {
                "project_info": {
                    "created_at": datetime.now().isoformat(),
                    "script_version": "2.41",
                    "current_image": current_image_filename,
                    "images_folder": "images"
                },
                "tag_data": {
                    # 클리어올에서 삭제하는 모든 태그 정보들 (이미지 경로를 파일명으로 변환)
                    "all_tags": convert_image_paths_to_filenames(convert_paths_to_strings(all_tags)),
                    "current_tags": convert_paths_to_strings(current_tags),
                    "removed_tags": convert_paths_to_strings(removed_tags),
                    "global_tag_stats": convert_paths_to_strings(global_tag_stats),
                    "image_removed_tags": convert_image_paths_to_filenames(convert_paths_to_strings(image_removed_tags)),
                    "tag_confidence": convert_image_paths_to_filenames(convert_paths_to_strings(tag_confidence)),
                    "manual_tag_info": convert_paths_to_strings(manual_tag_info),
                    "llava_tag_info": convert_paths_to_strings(llava_tag_info)
                },
                "timemachine_logs": self.collect_timemachine_logs_for_project(images_folder),
                "image_files": [Path(path).name for path in image_files],
                "original_image_files": [Path(path).name for path in original_image_files],
                "video_files": [str(path) for path in video_files],  # 동영상은 원본 경로 그대로 저장
                "original_video_files": [str(path) for path in original_video_files]  # 동영상은 원본 경로 그대로 저장
            }
            
            return database_info
            
        except Exception as e:
            print(f"데이터베이스 정보 수집 중 오류: {e}")
            # 최소한의 정보라도 저장
            return {
                "project_info": {
                    "created_at": datetime.now().isoformat(),
                    "script_version": "2.41",
                    "current_image": Path(getattr(self.app_instance, 'current_image', '')).name,
                    "images_folder": "images"
                },
                "tag_data": {
                    "all_tags": {},
                    "current_tags": [],
                    "removed_tags": [],
                    "global_tag_stats": {},
                    "image_removed_tags": {},
                    "tag_confidence": {},
                    "manual_tag_info": {},
                    "llava_tag_info": {}
                },
                "timemachine_logs": [],
                "image_files": [],
                "original_image_files": []
            }
    
    def collect_database_info(self):
        """데이터베이스에 저장할 정보 수집"""
        # Path 객체를 문자열로 변환하는 헬퍼 함수
        def convert_paths_to_strings(data):
            if isinstance(data, Path):
                return str(data)
            elif isinstance(data, list):
                return [convert_paths_to_strings(item) for item in data]
            elif isinstance(data, dict):
                return {str(key): convert_paths_to_strings(value) for key, value in data.items()}
            elif isinstance(data, set):
                return list(data)  # set을 list로 변환
            else:
                return data
        
        # 안전하게 데이터 수집
        try:
            all_tags = getattr(self.app_instance, 'all_tags', {})
            current_tags = getattr(self.app_instance, 'current_tags', [])
            removed_tags = getattr(self.app_instance, 'removed_tags', [])
            global_tag_stats = getattr(self.app_instance, 'global_tag_stats', {})
            image_removed_tags = getattr(self.app_instance, 'image_removed_tags', {})
            tag_confidence = getattr(self.app_instance, 'tag_confidence', {})
            manual_tag_info = getattr(self.app_instance, 'manual_tag_info', {})
            llava_tag_info = getattr(self.app_instance, 'llava_tag_info', {})
            image_files = getattr(self.app_instance, 'image_files', [])
            original_image_files = getattr(self.app_instance, 'original_image_files', [])
            
            database_info = {
                "project_info": {
                    "created_at": datetime.now().isoformat(),
                    "script_version": "2.41",
                    "current_image": str(getattr(self.app_instance, 'current_image', '')),
                    "current_folder": str(getattr(self.app_instance, 'current_folder', ''))
                },
                "tag_data": {
                    # 클리어올에서 삭제하는 모든 태그 정보들
                    "all_tags": convert_paths_to_strings(all_tags),
                    "current_tags": convert_paths_to_strings(current_tags),
                    "removed_tags": convert_paths_to_strings(removed_tags),
                    "global_tag_stats": convert_paths_to_strings(global_tag_stats),
                    "image_removed_tags": convert_paths_to_strings(image_removed_tags),
                    "tag_confidence": convert_paths_to_strings(tag_confidence),
                    "manual_tag_info": convert_paths_to_strings(manual_tag_info),
                    "llava_tag_info": convert_paths_to_strings(llava_tag_info)
                },
                "timemachine_logs": self.collect_timemachine_logs(),
                "image_files": convert_paths_to_strings(image_files),
                "original_image_files": convert_paths_to_strings(original_image_files)
            }
            
            return database_info
            
        except Exception as e:
            print(f"데이터베이스 정보 수집 중 오류: {e}")
            # 최소한의 정보라도 저장
            return {
                "project_info": {
                    "created_at": datetime.now().isoformat(),
                    "script_version": "2.41",
                    "current_image": str(getattr(self.app_instance, 'current_image', '')),
                    "current_folder": str(getattr(self.app_instance, 'current_folder', ''))
                },
                "tag_data": {
                    "all_tags": {},
                    "current_tags": [],
                    "removed_tags": [],
                    "global_tag_stats": {},
                    "image_removed_tags": {},
                    "tag_confidence": {},
                    "manual_tag_info": {},
                    "llava_tag_info": {}
                },
                "timemachine_logs": [],
                "image_files": [],
                "original_image_files": []
            }
    
    def collect_timemachine_logs(self):
        """타임머신 로그 수집"""
        try:
            from timemachine_log import TM
            logs = TM.get_all_logs()
            
            # JSON 직렬화 가능하도록 로그 데이터 정리
            def clean_log_data(data):
                if isinstance(data, dict):
                    return {str(key): clean_log_data(value) for key, value in data.items()}
                elif isinstance(data, list):
                    return [clean_log_data(item) for item in data]
                elif isinstance(data, Path):
                    return str(data)
                elif hasattr(data, '__dict__'):
                    # 객체인 경우 딕셔너리로 변환
                    try:
                        return clean_log_data(data.__dict__)
                    except:
                        return str(data)
                else:
                    return data
            
            return clean_log_data(logs)
            
        except Exception as e:
            print(f"타임머신 로그 수집 실패: {e}")
            return []
    
    def collect_timemachine_logs_for_project(self, images_folder):
        """프로젝트용 타임머신 로그 수집 (브랜치 구조 포함)"""
        try:
            # 타임머신 모듈에서 직접 브랜치 정보 가져오기
            if hasattr(self.app_instance, 'timemachine_manager'):
                tm_module = self.app_instance.timemachine_manager
                
                # 브랜치 구조 전체 저장
                branches_data = {
                    "branches": [],
                    "active_branch": getattr(tm_module, '_active_branch', 0),
                    "viewing_branch": getattr(tm_module, '_viewing_branch', 0)
                }
                
                # 각 브랜치 저장
                for branch in tm_module._branches:
                    branch_data = {
                        "records": self.clean_log_data_for_project(branch["records"], images_folder),
                        "current_index": branch["current_index"],
                        "name": branch["name"],
                        "forked_from": branch.get("forked_from")  # (parent_idx, fork_point)
                    }
                    branches_data["branches"].append(branch_data)
                
                print(f"[TM LOG] 브랜치 구조 저장: {len(branches_data['branches'])}개 브랜치")
                return branches_data
            else:
                print("[TM LOG] 타임머신 모듈을 찾을 수 없음")
                return {"branches": [], "active_branch": 0, "viewing_branch": 0}
                
        except Exception as e:
            print(f"타임머신 로그 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"branches": [], "active_branch": 0, "viewing_branch": 0}
    
    def clean_log_data_for_project(self, data, images_folder, depth=0):
        """로그 데이터 정리 (경로를 파일명으로 변환)"""
        if depth > 10:
            return str(data)
            
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(key, str) and key.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')):
                    filename = Path(key).name
                    result[filename] = self.clean_log_data_for_project(value, images_folder, depth + 1)
                else:
                    result[str(key)] = self.clean_log_data_for_project(value, images_folder, depth + 1)
            return result
        elif isinstance(data, list):
            return [self.clean_log_data_for_project(item, images_folder, depth + 1) for item in data]
        elif isinstance(data, Path):
            if str(data).lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')):
                return Path(data).name
            return str(data)
        elif isinstance(data, str) and data.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')):
            return Path(data).name
        elif hasattr(data, '__dict__'):
            try:
                return self.clean_log_data_for_project(data.__dict__, images_folder, depth + 1)
            except:
                return str(data)
        else:
            return data
    
    def convert_filenames_to_paths_in_logs(self, data, images_folder):
        """로그의 파일명을 실제 경로로 변환"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(key, str) and key.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')):
                    actual_path = str(images_folder / key)
                    result[actual_path] = self.convert_filenames_to_paths_in_logs(value, images_folder)
                else:
                    result[str(key)] = self.convert_filenames_to_paths_in_logs(value, images_folder)
            return result
        elif isinstance(data, list):
            return [self.convert_filenames_to_paths_in_logs(item, images_folder) for item in data]
        elif isinstance(data, str) and data.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')):
            return str(images_folder / data)
        else:
            return data
    
    def load_project_database(self, project_folder):
        """프로젝트 데이터베이스 불러오기"""
        try:
            database_file = project_folder / "database.json"
            if not database_file.exists():
                self.show_message("오류", "데이터베이스 파일을 찾을 수 없습니다.", "error")
                return False
            
            # 데이터베이스 파일 읽기
            with open(database_file, 'r', encoding='utf-8') as f:
                database_info = json.load(f)
            
            # images 폴더 경로
            images_folder = project_folder / "images"
            if not images_folder.exists():
                self.show_message("오류", "images 폴더를 찾을 수 없습니다.", "error")
                return False
            
            # 기존 데이터 초기화
            self.clear_existing_data()
            
            # 태그 데이터 복원 (파일명을 실제 경로로 변환)
            tag_data = database_info.get("tag_data", {})
            self.restore_tag_data_for_project(tag_data, images_folder)
            
            # 이미지 파일 목록 복원 (파일명을 실제 경로로 변환)
            image_files = database_info.get("image_files", [])
            original_image_files = database_info.get("original_image_files", [])
            self.restore_image_files_for_project(image_files, original_image_files, images_folder)
            
            # 동영상 파일 목록 복원 (원본 경로 그대로 사용)
            video_files = database_info.get("video_files", [])
            original_video_files = database_info.get("original_video_files", [])
            self.restore_video_files_for_project(video_files, original_video_files)
            
            # 타임머신 로그 복원
            timemachine_logs = database_info.get("timemachine_logs", [])
            self.restore_timemachine_logs(timemachine_logs, images_folder)
            
            # 현재 이미지 설정
            project_info = database_info.get("project_info", {})
            current_image_filename = project_info.get("current_image", "")
            if current_image_filename:
                current_image_path = images_folder / current_image_filename
                if current_image_path.exists():
                    self.app_instance.current_image = str(current_image_path)
            
            # UI 업데이트
            self.update_ui_after_load()
            
            # 프로젝트 명 저장
            project_name = project_folder.name
            self.app_instance.current_project_name = project_name
            
            self.show_message("성공", f"프로젝트 {project_name}이 불러와졌습니다.", "info")
            return True
            
        except Exception as e:
            self.show_message("오류", f"프로젝트 불러오기 중 오류가 발생했습니다:\n{str(e)}", "error")
            return False
    
    def clear_existing_data(self):
        """기존 데이터 초기화 (클리어올과 동일한 로직)"""
        # 클리어올에서 삭제하는 모든 항목들 초기화
        self.app_instance.all_tags.clear()
        self.app_instance.current_tags.clear()
        self.app_instance.removed_tags.clear()
        self.app_instance.image_removed_tags.clear()
        self.app_instance.tag_confidence.clear()
        self.app_instance.manual_tag_info.clear()
        self.app_instance.llava_tag_info.clear()
        self.app_instance.global_tag_stats.clear()
        
        # 타임머신 로그 완전 초기화 🔥
        try:
            from timemachine_log import TM
            TM.clear_logs()
            print("[TM LOG] 타임머신 로그 완전 초기화 (데이터베이스 불러오기)")
            
            # 타임머신 모듈도 초기화
            if hasattr(self.app_instance, 'timemachine_manager'):
                tm_module = self.app_instance.timemachine_manager
                # 브랜치 구조 완전 초기화
                tm_module._branches = [{
                    "records": [],
                    "current_index": -1,
                    "name": "main",
                    "forked_from": None
                }]
                tm_module._active_branch = 0
                tm_module._viewing_branch = 0
                tm_module._timeline = []
                tm_module._current_index = -1
                print("[TM LOG] 타임머신 모듈 브랜치 구조 초기화")
                
                # UI 패널도 완전 초기화
                if hasattr(tm_module, 'timeline_panel') and tm_module.timeline_panel:
                    tm_module.timeline_panel.clear_cards()
                    # 타임라인과 타임스탬프도 초기화
                    tm_module.timeline_panel.timeline.set_entries([])
                    tm_module.timeline_panel.time_labels.set_entries([])
                    print("[TM LOG] 타임머신 UI 패널 완전 초기화")
        except Exception as e:
            print(f"[TM LOG] 타임머신 초기화 실패: {e}")
        
        # 태그 카드 캐시도 정리
        if hasattr(self.app_instance, 'tag_statistics_module'):
            for w in list(self.app_instance.tag_statistics_module.tag_card_cache.values()):
                w.deleteLater()
            self.app_instance.tag_statistics_module.tag_card_cache.clear()
        
        if hasattr(self.app_instance, 'miracle_manager') and self.app_instance.miracle_manager:
            try:
                self.app_instance.miracle_manager.clear_response_cards()
            except Exception as e:
                print(f"[TM LOG] 미라클 응답 카드 초기화 실패: {e}")

        # 동영상 데이터 초기화
        self.app_instance.video_files = []
        self.app_instance.original_video_files = []
    
    def restore_tag_data(self, tag_data):
        """태그 데이터 복원"""
        # all_tags 복원
        all_tags = tag_data.get("all_tags", {})
        for image_path, tags in all_tags.items():
            self.app_instance.all_tags[image_path] = list(tags)
        
        # current_tags 복원
        self.app_instance.current_tags = list(tag_data.get("current_tags", []))
        
        # removed_tags 복원
        self.app_instance.removed_tags = list(tag_data.get("removed_tags", []))
        
        # global_tag_stats 복원
        global_tag_stats = tag_data.get("global_tag_stats", {})
        for tag, stats in global_tag_stats.items():
            if isinstance(stats, dict):
                # 딕셔너리 형태: {'image_count': count, 'category': 'unknown', 'images': [...]}
                self.app_instance.global_tag_stats[tag] = {
                    'image_count': stats.get('image_count', 0),
                    'category': stats.get('category', 'unknown'),
                    'images': list(stats.get('images', []))
                }
            else:
                # 정수 형태: count
                self.app_instance.global_tag_stats[tag] = stats
        
        # image_removed_tags 복원
        image_removed_tags = tag_data.get("image_removed_tags", {})
        for image_path, tags in image_removed_tags.items():
            self.app_instance.image_removed_tags[image_path] = list(tags)
        
        # tag_confidence 복원
        tag_confidence = tag_data.get("tag_confidence", {})
        for image_path, pairs in tag_confidence.items():
            self.app_instance.tag_confidence[image_path] = list(pairs)
        
        # manual_tag_info 복원
        manual_tag_info = tag_data.get("manual_tag_info", {})
        for tag, is_trigger in manual_tag_info.items():
            self.app_instance.manual_tag_info[tag] = is_trigger
        
        # llava_tag_info 복원
        llava_tag_info = tag_data.get("llava_tag_info", {})
        for tag, value in llava_tag_info.items():
            self.app_instance.llava_tag_info[tag] = value
    
    def restore_tag_data_for_project(self, tag_data, images_folder):
        """프로젝트용 태그 데이터 복원 (파일명을 실제 경로로 변환)"""
        # 파일명을 실제 경로로 변환하는 함수
        def convert_filenames_to_paths(data):
            if isinstance(data, dict):
                result = {}
                for key, value in data.items():
                    key_str = str(key)
                    if isinstance(key, str) and key_str.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')):
                        # 파일명을 실제 경로로 변환
                        actual_path = str(images_folder / key_str)
                        result[actual_path] = convert_filenames_to_paths(value)
                    else:
                        result[key_str] = convert_filenames_to_paths(value)
                return result
            elif isinstance(data, list):
                return [convert_filenames_to_paths(item) for item in data]
            else:
                return data
        
        # all_tags 복원
        all_tags = tag_data.get("all_tags", {})
        converted_all_tags = convert_filenames_to_paths(all_tags)
        for image_path, tags in converted_all_tags.items():
            self.app_instance.all_tags[image_path] = list(tags)
        
        # current_tags 복원
        self.app_instance.current_tags = list(tag_data.get("current_tags", []))
        
        # removed_tags 복원
        self.app_instance.removed_tags = list(tag_data.get("removed_tags", []))
        
        # global_tag_stats 복원
        global_tag_stats = tag_data.get("global_tag_stats", {})
        for tag, stats in global_tag_stats.items():
            if isinstance(stats, dict):
                # 딕셔너리 형태: {'image_count': count, 'category': 'unknown', 'images': [...]}
                self.app_instance.global_tag_stats[tag] = {
                    'image_count': stats.get('image_count', 0),
                    'category': stats.get('category', 'unknown'),
                    'images': list(stats.get('images', []))
                }
            else:
                # 정수 형태: count
                self.app_instance.global_tag_stats[tag] = stats
        
        # image_removed_tags 복원
        image_removed_tags = tag_data.get("image_removed_tags", {})
        converted_image_removed_tags = convert_filenames_to_paths(image_removed_tags)
        for image_path, tags in converted_image_removed_tags.items():
            self.app_instance.image_removed_tags[image_path] = list(tags)
        
        # tag_confidence 복원 (WD 태그 신뢰도 정보)
        tag_confidence = tag_data.get("tag_confidence", {})
        converted_tag_confidence = convert_filenames_to_paths(tag_confidence)
        print(f"[DB LOG] tag_confidence 복원: {len(converted_tag_confidence)}개 이미지")
        for image_path, pairs in converted_tag_confidence.items():
            self.app_instance.tag_confidence[image_path] = list(pairs)
            # 신뢰도 정보 디버깅 (처음 3개 이미지만)
            if len(converted_tag_confidence) <= 3 or image_path == list(converted_tag_confidence.keys())[0]:
                print(f"  {Path(image_path).name}: {len(pairs)}개 태그 신뢰도")
                for tag, score in pairs[:3]:  # 처음 3개만 표시
                    print(f"    {tag}: {score}")
                if len(pairs) > 3:
                    print(f"    ... 외 {len(pairs)-3}개")
        
        # manual_tag_info 복원
        manual_tag_info = tag_data.get("manual_tag_info", {})
        print(f"[DB LOG] manual_tag_info 복원: {len(manual_tag_info)}개 태그")
        for tag, is_trigger in manual_tag_info.items():
            self.app_instance.manual_tag_info[tag] = is_trigger
        
        # llava_tag_info 복원 (LLaVA 태그 캡셔너 분류)
        llava_tag_info = tag_data.get("llava_tag_info", {})
        print(f"[DB LOG] llava_tag_info 복원: {len(llava_tag_info)}개 LLaVA 태그")
        for tag, value in llava_tag_info.items():
            self.app_instance.llava_tag_info[tag] = value
            print(f"  LLaVA 태그: {tag} -> {value}")
    
    def restore_image_files_for_project(self, image_files, original_image_files, images_folder):
        """프로젝트용 이미지 파일 목록 복원 (파일명을 실제 경로로 변환)"""
        # 파일명을 실제 경로로 변환
        self.app_instance.image_files = [images_folder / filename for filename in image_files]
        self.app_instance.original_image_files = [images_folder / filename for filename in original_image_files]
    
    def restore_video_files_for_project(self, video_files, original_video_files):
        """프로젝트용 동영상 파일 목록 복원 (원본 경로 그대로 사용)"""
        # 동영상은 원본 경로 그대로 사용 (복사하지 않았으므로)
        self.app_instance.video_files = [Path(path) for path in video_files]
        self.app_instance.original_video_files = [Path(path) for path in original_video_files]
    
    def restore_image_files(self, image_files, original_image_files):
        """이미지 파일 목록 복원"""
        # 문자열 경로를 Path 객체로 변환
        self.app_instance.image_files = [Path(path) for path in image_files]
        self.app_instance.original_image_files = [Path(path) for path in original_image_files]
    
    def restore_timemachine_logs(self, timemachine_logs, images_folder):
        """타임머신 로그 복원 (브랜치 구조 포함)"""
        try:
            if not hasattr(self.app_instance, 'timemachine_manager'):
                print("[TM LOG] 타임머신 모듈을 찾을 수 없습니다.")
                return
            
            tm_module = self.app_instance.timemachine_manager
            
            # 브랜치 구조 복원
            if isinstance(timemachine_logs, dict) and "branches" in timemachine_logs:
                print(f"[TM LOG] 브랜치 구조 복원: {len(timemachine_logs['branches'])}개 브랜치")
                
                # 브랜치 리스트 초기화
                tm_module._branches = []
                
                # 각 브랜치 복원
                for branch_data in timemachine_logs["branches"]:
                    records = self.convert_filenames_to_paths_in_logs(branch_data["records"], images_folder)
                    restored_branch = {
                        "records": records,
                        "current_index": branch_data["current_index"],
                        "name": branch_data["name"],
                        "forked_from": branch_data.get("forked_from")
                    }
                    tm_module._branches.append(restored_branch)
                    print(f"[TM LOG] 브랜치 '{branch_data['name']}' 복원: {len(records)}개 레코드")
                
                # active/viewing 브랜치 복원
                tm_module._active_branch = timemachine_logs.get("active_branch", 0)
                tm_module._viewing_branch = timemachine_logs.get("viewing_branch", 0)
                
                # 현재 타임라인 설정
                tm_module._timeline = tm_module._branches[tm_module._viewing_branch]["records"]
                tm_module._current_index = tm_module._branches[tm_module._viewing_branch]["current_index"]
                
                print(f"[TM LOG] Active branch: {tm_module._active_branch}, Viewing branch: {tm_module._viewing_branch}")
                
                # UI 업데이트
                if hasattr(tm_module, 'timeline_panel') and tm_module.timeline_panel:
                    tm_module._rebuild_panel()
                    print(f"[TM LOG] 타임머신 UI 패널 재구성 완료")
            else:
                # 기존 방식 (평탄화된 로그) - 호환성을 위해 유지
                print(f"[TM LOG] 기존 방식으로 로그 복원: {len(timemachine_logs)}개")
                converted_logs = self.convert_filenames_to_paths_in_logs(timemachine_logs, images_folder)
                from timemachine_log import TM
                TM.restore_logs(converted_logs)
            
            # 타임머신 모듈의 내부 상태 업데이트 (기존 방식에서만)
            if not (isinstance(timemachine_logs, dict) and "branches" in timemachine_logs):
                # 기존 방식(평탄화된 로그)인 경우에만 추가 처리
                try:
                    if hasattr(self.app_instance, 'timemachine_manager') and self.app_instance.timemachine_manager:
                        tm_module = self.app_instance.timemachine_manager
                        print(f"[TM LOG] 타임머신 모듈 발견: {type(tm_module)}")
                        
                        # 타임머신 모듈의 브랜치 구조 업데이트
                        if hasattr(tm_module, '_branches'):
                            print(f"[TM LOG] _branches 속성 발견: {len(tm_module._branches)}개 브랜치")
                            
                            # 메인 브랜치에 복원된 로그 설정
                            tm_module._branches[0]["records"] = converted_logs.copy()
                            tm_module._branches[0]["current_index"] = len(converted_logs) - 1 if converted_logs else -1
                            
                            # 현재 보기 브랜치 업데이트
                            tm_module._timeline = tm_module._branches[0]["records"]
                            tm_module._current_index = tm_module._branches[0]["current_index"]
                            
                            print(f"[TM LOG] 타임머신 모듈 내부 상태가 업데이트되었습니다.")
                            print(f"[TM LOG] _timeline 길이: {len(tm_module._timeline)}")
                            print(f"[TM LOG] _current_index: {tm_module._current_index}")
                            
                            # timeline_panel이 존재하는지 확인
                            if hasattr(tm_module, 'timeline_panel') and tm_module.timeline_panel:
                                print(f"[TM LOG] timeline_panel 발견: {type(tm_module.timeline_panel)}")
                                
                                # UI 패널 재구성
                                if hasattr(tm_module, '_rebuild_panel'):
                                    tm_module._rebuild_panel()
                                    print(f"[TM LOG] 타임머신 UI 패널이 재구성되었습니다. ({len(converted_logs)}개 로그)")
                                else:
                                    print("[TM LOG] _rebuild_panel 메서드를 찾을 수 없습니다.")
                            else:
                                print("[TM LOG] timeline_panel이 없습니다. 타임머신 카드가 초기화되지 않았을 수 있습니다.")
                                
                                # 타임머신 카드 강제 초기화 시도
                                if hasattr(tm_module, 'create_timemachine_card'):
                                    print("[TM LOG] 타임머신 카드 초기화 시도...")
                                    tm_module.create_timemachine_card()
                                    if hasattr(tm_module, 'timeline_panel') and tm_module.timeline_panel:
                                        tm_module._rebuild_panel()
                                        print("[TM LOG] 타임머신 카드 초기화 후 UI 패널 재구성 완료")
                        else:
                            print("[TM LOG] _branches 속성을 찾을 수 없습니다.")
                            print(f"[TM LOG] 타임머신 모듈 속성들: {[attr for attr in dir(tm_module) if not attr.startswith('__')]}")
                    else:
                        print("[TM LOG] 타임머신 모듈을 찾을 수 없습니다.")
                        print(f"[TM LOG] app_instance 속성들: {[attr for attr in dir(self.app_instance) if 'time' in attr.lower()]}")
                            
                except Exception as ui_error:
                    print(f"[TM LOG] 타임머신 UI 업데이트 실패: {ui_error}")
                    import traceback
                    traceback.print_exc()

            mm = getattr(self.app_instance, 'miracle_manager', None)
            if mm:
                try:
                    if hasattr(mm, 'clear_response_cards'):
                        mm.clear_response_cards()
                except Exception as clr_err:
                    print(f"[TM LOG] 미라클 응답 카드 초기화 실패: {clr_err}")
                timeline = getattr(tm_module, '_timeline', None)
                current_index = getattr(tm_module, '_current_index', -1)
                if timeline and current_index is not None:
                    try:
                        if hasattr(mm, '_response_card_meta'):
                            mm._response_card_meta = {}
                        if hasattr(mm, '_pending_response_card_order'):
                            mm._pending_response_card_order = []
                        active_ids = []
                        limit = max(-1, min(current_index, len(timeline) - 1))
                        if limit >= 0:
                            for idx, record in enumerate(timeline):
                                if idx > limit:
                                    break
                                for change in record.get("changes", []):
                                    if change.get("type") != "miracle_response_card":
                                        continue
                                    card_id = change.get("card_id")
                                    if not card_id or card_id in active_ids:
                                        continue
                                    text = change.get("text", "") or ""
                                    mode = change.get("mode", "single")
                                    border = change.get("border")
                                    if not border:
                                        border = "#22c55e" if mode == "batch" else "#3B82F6"
                                    extra_payload = {
                                        k: v for k, v in change.items()
                                        if k not in ("type", "card_id", "text", "mode", "border")
                                    }
                                    meta = {
                                        "text": text,
                                        "mode": mode,
                                        "border": border,
                                    }
                                    if extra_payload:
                                        meta["payload"] = extra_payload
                                    if hasattr(mm, '_response_card_meta'):
                                        mm._response_card_meta[card_id] = meta
                                    active_ids.append(card_id)
                        if hasattr(mm, '_pending_response_card_order'):
                            mm._pending_response_card_order = active_ids
                        if getattr(mm, 'is_miracle_mode', False):
                            if hasattr(mm, 'render_cached_response_cards'):
                                mm.render_cached_response_cards()
                    except Exception as rebuild_err:
                        print(f"[TM LOG] 미라클 응답 카드 메타 복원 실패: {rebuild_err}")
                else:
                    if hasattr(mm, '_response_card_meta'):
                        mm._response_card_meta = {}
                    if hasattr(mm, '_pending_response_card_order'):
                        mm._pending_response_card_order = []
                
        except Exception as e:
            print(f"타임머신 로그 복원 실패: {e}")
    
    def load_files_from_files(self, file_paths, load_txt_tags=False):
        """선택된 파일들을 로드 (이미지/동영상 자동 분리)"""
        print(f"파일 로드 시작: {len(file_paths)}개 파일")
        
        try:
            # 기존 그리드 초기화
            from search_filter_grid_image_module import clear_image_grid
            clear_image_grid(self.app_instance)
            from search_filter_grid_video_module import clear_video_grid
            clear_video_grid(self.app_instance)
            
            # 기존 데이터 초기화
            self.clear_existing_data()
            
            # 프로젝트 명 초기화 (파일 불러오기는 프로젝트 명 없음)
            self.app_instance.current_project_name = None
            
            # 지원하는 미디어 확장자
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            
            # Path 객체로 변환
            from pathlib import Path
            file_paths = [Path(file_path) for file_path in file_paths]
            
            # 이미지와 동영상 파일 분리
            image_files = []
            video_files = []
            
            for file_path in file_paths:
                if file_path.suffix.lower() in image_extensions:
                    image_files.append(file_path)
                elif file_path.suffix.lower() in video_extensions:
                    video_files.append(file_path)
            
            # 파일들을 앱 인스턴스에 저장
            self.app_instance.image_files = image_files
            self.app_instance.original_image_files = image_files.copy()
            self.app_instance.video_files = video_files
            self.app_instance.original_video_files = video_files.copy()
            
            # txt 태그 불러오기 (이미지만 해당, 동영상은 제외)
            if load_txt_tags and image_files:
                print("txt 태그 불러오기 시작...")
                txt_tag_count = 0
                for image_path in image_files:
                    tags = self.load_tags_from_txt(image_path)
                    if tags:
                        self.apply_txt_tags_to_image(image_path, tags)
                        txt_tag_count += len(tags)
                print(f"txt 태그 불러오기 완료: {txt_tag_count}개 태그 적용")
            
            # UI 업데이트
            self.update_ui_after_load()
            
            # 첫 번째 이미지 자동 선택 (파란색 테두리 표시)
            if image_files:
                from PySide6.QtCore import QTimer
                def select_first_image():
                    first_image_path = str(image_files[0])
                    print(f"첫 번째 이미지 자동 선택: {first_image_path}")
                    from image_preview_module import load_image
                    load_image(self.app_instance, first_image_path)
                    # 선택 상태 강제 업데이트
                    from search_filter_grid_image_module import _refresh_image_grid_selection_visuals
                    _refresh_image_grid_selection_visuals(self.app_instance)
                # 썸네일 생성 완료 후 선택 (약간의 딜레이)
                QTimer.singleShot(300, select_first_image)
            
            # 동영상이 있는 경우 즉시 썸네일 생성 (그리드 모드와 관계없이)
            if video_files:
                from search_filter_grid_video_module import create_video_grid_in_place, refresh_video_thumbnails
                create_video_grid_in_place(self.app_instance)
                # 동영상 썸네일 생성 (페이지네이션 적용)
                refresh_video_thumbnails(self.app_instance)
            
            # 상태바 메시지 업데이트
            total_media = len(image_files) + len(video_files)
            message = f"미디어 {total_media}개가 로드되었습니다"
            if image_files:
                message += f" (이미지 {len(image_files)}개"
            if video_files:
                message += f", 동영상 {len(video_files)}개"
            if image_files and video_files:
                message += ")"
            elif image_files or video_files:
                message += ")"
            self.app_instance.statusBar().showMessage(message)
            
        except Exception as e:
            print(f"파일 로드 오류: {e}")
            self.app_instance.statusBar().showMessage(f"파일 로드 오류: {e}")
    
    def update_ui_after_load(self):
        """데이터 로드 후 UI 업데이트"""
        # 현재 태그 표시 업데이트
        if hasattr(self.app_instance, 'update_current_tags_display'):
            self.app_instance.update_current_tags_display()
        
        # 태그 통계 업데이트
        if hasattr(self.app_instance, 'update_tag_stats'):
            self.app_instance.update_tag_stats()
        
        # 태그 트리 업데이트
        if hasattr(self.app_instance, 'update_tag_tree'):
            self.app_instance.update_tag_tree()
        
        # 이미지 그리드 업데이트 (통합 함수 사용 - 중복 방지)
        if hasattr(self.app_instance, 'image_files') and self.app_instance.image_files:
            from search_module import update_image_grid_unified
            self.app_instance.active_grid_token += 1
            update_image_grid_unified(self.app_instance, expected_token=self.app_instance.active_grid_token)
        
        # 동영상 썸네일 생성 - 현재 그리드 모드에 따라 처리
        if hasattr(self.app_instance, 'video_files') and self.app_instance.video_files:
            # 현재 활성화된 그리드 모드 확인
            video_mode_active = False
            if (hasattr(self.app_instance, 'video_filter_btn') and 
                hasattr(self.app_instance, 'image_filter_btn')):
                video_mode_active = (self.app_instance.video_filter_btn.isChecked() and 
                                   not self.app_instance.image_filter_btn.isChecked())
            
            if video_mode_active:
                # 동영상 그리드가 활성화된 경우 - 썸네일 생성 (페이지네이션 적용)
                from search_filter_grid_video_module import refresh_video_thumbnails
                refresh_video_thumbnails(self.app_instance)
            else:
                # 이미지 그리드가 활성화된 경우 - 동영상 그리드 생성 후 썸네일 생성
                from search_filter_grid_video_module import create_video_grid_in_place, refresh_video_thumbnails
                create_video_grid_in_place(self.app_instance)
                # 동영상 썸네일 생성 (페이지네이션 적용)
                refresh_video_thumbnails(self.app_instance)
        
        # 카운터 업데이트
        if hasattr(self.app_instance, 'image_files'):
            from search_module import update_image_counter
            update_image_counter(self.app_instance, len(self.app_instance.image_files), len(self.app_instance.image_files))
        
        # 동영상 카운터 업데이트
        if hasattr(self.app_instance, 'video_files'):
            from search_filter_grid_video_module import update_video_counter
            update_video_counter(self.app_instance, len(self.app_instance.video_files), len(self.app_instance.video_files))
        
        # 프로젝트 로드 시 이미지 프리뷰와 썸네일 선택 강제 업데이트
        if (hasattr(self.app_instance, 'image_files') and 
            self.app_instance.image_files):
            
            from image_preview_module import load_image
            
            if not self.app_instance.current_image:
                # current_image가 없으면 첫 번째 이미지 선택
                first_image_path = str(self.app_instance.image_files[0])
                load_image(self.app_instance, first_image_path)
            else:
                # current_image가 있으면 강제로 이미지 프리뷰와 썸네일 업데이트
                # 강제 업데이트를 위해 임시로 current_image를 None으로 설정
                temp_current = self.app_instance.current_image
                self.app_instance.current_image = None
                load_image(self.app_instance, temp_current)
            
            # 썸네일 그리드의 선택 상태 강제 업데이트
            from search_filter_grid_image_module import _refresh_image_grid_selection_visuals
            _refresh_image_grid_selection_visuals(self.app_instance)
        
        # 타임머신 UI는 restore_timemachine_logs에서 이미 업데이트됨
    
    def get_available_projects(self):
        """사용 가능한 프로젝트 목록 반환 (database.json이 있는 모든 폴더 인식)"""
        projects = []
        for item in self.projects_folder.iterdir():
            if item.is_dir():
                database_file = item / "database.json"
                if database_file.exists():
                    try:
                        with open(database_file, 'r', encoding='utf-8') as f:
                            database_info = json.load(f)
                        
                        project_info = database_info.get("project_info", {})
                        created_at = project_info.get("created_at", "")
                        current_image = project_info.get("current_image", "")
                        
                        projects.append({
                            "folder": item,
                            "name": item.name,
                            "created_at": created_at,
                            "current_image": current_image
                        })
                    except Exception as e:
                        print(f"프로젝트 {item.name} 정보 읽기 실패: {e}")
        
        # 생성일 기준으로 정렬 (최신순)
        projects.sort(key=lambda x: x["created_at"], reverse=True)
        return projects
    
    def show_message(self, title, message, msg_type="info"):
        """메시지 박스 표시"""
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


class ProjectItem(QFrame):
    """프로젝트 아이템 위젯"""
    load_clicked = Signal(dict)  # project_data
    delete_clicked = Signal(dict)  # project_data
    
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setObjectName("ProjectItem")
        self.setStyleSheet("""
            QFrame#ProjectItem {
                background: transparent;
                border: none;
                margin: 1px 0px;
            }
            QFrame#ProjectItem:hover {
                background: rgba(255,255,255,0.05);
            }
        """)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(46)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # 프로젝트 정보 표시
        project_text = f"{project['name']} - {project['current_image']}"
        if project['created_at']:
            try:
                created_date = datetime.fromisoformat(project['created_at']).strftime("%Y-%m-%d %H:%M")
                project_text += f" ({created_date})"
            except:
                pass
        
        self.project_label = QLabel(project_text)
        self.project_label.setWordWrap(False)
        self.project_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.project_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.project_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #FFFFFF;
            background: transparent;
        """)
        
        layout.addWidget(self.project_label)
        
        # 불러오기 버튼 (미라클 설정과 동일한 스타일)
        self.load_btn = QPushButton("📂")
        self.load_btn.setFixedSize(30, 30)
        self.load_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.load_btn.setCursor(Qt.PointingHandCursor)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.3);
                color: #E5E7EB;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 700;
                text-align: center;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.5);
                color: white;
            }
        """)
        self.load_btn.clicked.connect(self.on_load_clicked)
        
        # 삭제 버튼 (미라클 설정과 동일한 스타일)
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(30, 30)
        self.delete_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.3);
                color: #E5E7EB;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 700;
                text-align: center;
                padding: 0px;
                padding-top: -4px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        
        layout.addWidget(self.load_btn)
        layout.addWidget(self.delete_btn)
    
    def on_load_clicked(self):
        """불러오기 버튼 클릭"""
        self.load_clicked.emit(self.project)
    
    def on_delete_clicked(self):
        """삭제 버튼 클릭"""
        self.delete_clicked.emit(self.project)


class ProjectSelectionDialog(QDialog):
    """프로젝트 선택 대화상자"""
    
    def __init__(self, projects, parent=None):
        super().__init__(parent)
        self.projects = projects
        self.selected_project = None
        self.selected_folder = None
        self.selected_images = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("File Selector")
        self.setModal(True)
        self.resize(700, 500)
        
        # 메인 대화상자 스타일 적용
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title_label = QLabel("File Selector")
        title_label.setStyleSheet("""
            font-size: 25px;
            font-weight: 700;
            color: #E2E8F0;
            margin-bottom: 8px;
            font-family: 'Segoe UI';
        """)
        layout.addWidget(title_label)
        
        # 설명
        desc_label = QLabel("저장된 프로젝트를 불러오거나, 미디어 폴더를 선택하거나, 개별 파일들을 선택하세요.")
        desc_label.setStyleSheet("color: #9CA3AF; font-size: 11px; margin-top: 8px;")
        layout.addWidget(desc_label)
        
        # 프로젝트 목록 섹션
        list_label = QLabel("저장된 프로젝트:")
        list_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 6px;
            padding: 6px 0px;
            border-bottom: 1px solid rgba(75,85,99,0.3);
        """)
        layout.addWidget(list_label)
        
        # 프로젝트 목록 스크롤 영역
        project_scroll = QScrollArea()
        project_scroll.setWidgetResizable(True)
        project_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                background: rgba(26,27,38,0.8);
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        # 프로젝트 목록 위젯
        project_widget = QWidget()
        project_layout = QVBoxLayout(project_widget)
        project_layout.setContentsMargins(8, 8, 8, 8)
        project_layout.setSpacing(4)
        project_layout.setAlignment(Qt.AlignTop)
        
        # 프로젝트 아이템들 추가
        self.project_items = []
        for project in self.projects:
            project_item = ProjectItem(project, self)
            project_item.load_clicked.connect(self.load_project)
            project_item.delete_clicked.connect(self.delete_project)
            project_layout.addWidget(project_item)
            self.project_items.append(project_item)
        
        project_scroll.setWidget(project_widget)
        layout.addWidget(project_scroll)
        
        # txt 태그 불러오기 체크박스 (버튼 위에 배치)
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setContentsMargins(0, 8, 0, 8)
        
        # 커스텀 체크박스 클래스 정의 (GPU/CPU 토글과 동일 디자인)
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
        
        self.txt_tag_checkbox = CustomCheckBox("txt태그 불러오기")
        self.txt_tag_checkbox.setChecked(False)  # 기본값: 체크 안됨
        checkbox_layout.addWidget(self.txt_tag_checkbox)
        checkbox_layout.addStretch()
        
        layout.addLayout(checkbox_layout)
        
        # 하단 버튼들
        button_layout = QHBoxLayout()
        
        # 폴더 불러오기 버튼
        self.folder_btn = QPushButton("폴더 불러오기")
        self.folder_btn.setStyleSheet("""
            QPushButton {
                background: #10B981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #059669;
            }
            QPushButton:pressed {
                background: #047857;
            }
        """)
        self.folder_btn.clicked.connect(self.select_folder)
        
        # 이미지 불러오기 버튼
        self.image_btn = QPushButton("파일 불러오기")
        self.image_btn.setStyleSheet("""
            QPushButton {
                background: #8B5CF6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background: #7C3AED;
            }
            QPushButton:pressed {
                background: #6D28D9;
            }
        """)
        self.image_btn.clicked.connect(self.select_files)
        
        button_layout.addWidget(self.folder_btn)
        button_layout.addWidget(self.image_btn)
        button_layout.addStretch()
        
        # 취소 버튼
        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_project(self, project):
        """프로젝트 불러오기"""
        self.selected_project = project
        self.accept()
    
    def delete_project(self, project):
        """프로젝트 삭제"""
        # 삭제 확인 다이얼로그
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, 
            "프로젝트 삭제", 
            f"'{project['name']}' 프로젝트를 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 프로젝트 삭제 로직 (실제 구현 필요)
            print(f"프로젝트 삭제: {project['name']}")
            # 여기에 실제 삭제 로직을 추가해야 합니다
    
    def get_selected_project(self):
        """선택된 프로젝트 반환"""
        return self.selected_project
    
    def select_folder(self):
        """폴더 선택 모드로 전환"""
        # 폴더 선택 대화상자 스타일 적용
        folder_dialog = QFileDialog(self)
        folder_dialog.setFileMode(QFileDialog.Directory)
        folder_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        folder_dialog.setWindowTitle("이미지 폴더 선택")
        
        # 스타일 적용
        folder_dialog.setStyleSheet("""
            QFileDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
            }
            QPushButton {
                background: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2563EB;
            }
            QPushButton:pressed {
                background: #1D4ED8;
            }
        """)
        
        if folder_dialog.exec() == QDialog.Accepted:
            folders = folder_dialog.selectedFiles()
            if folders:
                folder = folders[0]
                # 폴더 선택 결과를 저장하고 대화상자 종료
                self.selected_folder = folder
                self.selected_project = None  # 프로젝트 선택 초기화 (폴더 선택 우선)
                # accept() 호출하지 않고 직접 결과 반환
                self.done(QDialog.Accepted)
            else:
                self.selected_folder = None
        else:
            # 폴더 선택을 취소한 경우
            self.selected_folder = None

    def select_files(self):
        """파일 선택 모드로 전환 (이미지/동영상 자동 분리)"""
        # 파일 선택 대화상자
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("미디어 파일 (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v)")
        file_dialog.setWindowTitle("파일 선택")
        
        # 스타일 적용
        file_dialog.setStyleSheet("""
            QFileDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F0;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
            }
            QPushButton {
                background: #8B5CF6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #7C3AED;
            }
            QPushButton:pressed {
                background: #6D28D9;
            }
        """)
        
        if file_dialog.exec() == QDialog.Accepted:
            files = file_dialog.selectedFiles()
            if files:
                # 파일 선택 결과를 저장하고 대화상자 종료
                self.selected_images = files  # 변수명은 기존과 호환성을 위해 유지
                self.selected_folder = None
                self.selected_project = None  # 프로젝트 선택 초기화 (파일 선택 우선)
                # accept() 호출하지 않고 직접 결과 반환
                self.done(QDialog.Accepted)
            else:
                self.selected_images = None
        else:
            # 파일 선택을 취소한 경우
            self.selected_images = None


# 단독 실행을 위한 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
    
    class TestApp:
        def __init__(self):
            self.current_image = "test_image.jpg"
            self.current_folder = "test_folder"
            self.all_tags = {"test_image.jpg": ["tag1", "tag2"]}
            self.current_tags = ["tag1", "tag2"]
            self.removed_tags = []
            self.global_tag_stats = {"tag1": 1, "tag2": 1}
            self.image_removed_tags = {}
            self.tag_confidence = {}
            self.manual_tag_info = {}
            self.llava_tag_info = {}
            self.image_files = []
            self.original_image_files = []
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Database Manager Module Test")
            self.setGeometry(100, 100, 400, 300)
            
            # 중앙 위젯
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 레이아웃
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(10)
            
            # 테스트 앱 인스턴스
            self.test_app = TestApp()
            
            # 데이터베이스 매니저 생성
            self.db_manager = DatabaseManager(self.test_app)
            
            # 테스트 버튼들
            save_btn = QPushButton("프로젝트 저장 테스트")
            save_btn.clicked.connect(self.test_save)
            layout.addWidget(save_btn)
            
            load_btn = QPushButton("프로젝트 불러오기 테스트")
            load_btn.clicked.connect(self.test_load)
            layout.addWidget(load_btn)
            
            # 스타일시트 적용
            self.setStyleSheet("""
                QMainWindow {
                    background: #1F2937;
                    color: #E5E7EB;
                }
            """)
        
        def test_save(self):
            self.db_manager.save_project_database()
        
        def test_load(self):
            projects = self.db_manager.get_available_projects()
            if projects:
                dialog = ProjectSelectionDialog(projects, self)
                if dialog.exec() == QDialog.Accepted:
                    selected = dialog.get_selected_project()
                    if selected:
                        self.db_manager.load_project_database(selected["folder"])
            else:
                self.db_manager.show_message("정보", "저장된 프로젝트가 없습니다.", "info")
    
    # 애플리케이션 실행
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
