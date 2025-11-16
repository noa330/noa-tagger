# -*- coding: utf-8 -*-
"""
Miracle Manager Single Module - 단일 작업 로직 전용 모듈
"""

from PySide6.QtWidgets import (QPushButton, QLineEdit, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QFrame, QSpinBox, QStyleOptionSpinBox, QStyle, QSizePolicy)
from PySide6.QtCore import Signal, Qt, QTimer, QEvent, QThread, QObject
from PySide6.QtGui import QFont, QPainter, QPen, QColor

import os
import traceback
from pathlib import Path


# 커스텀 스핀박스
class CustomSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QSpinBox.UpDownArrows)
    def paintEvent(self, event):
        super().paintEvent(event)
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            option = QStyleOptionSpinBox()
            self.initStyleOption(option)
            up_rect = self.style().subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_SpinBoxUp, self)
            if up_rect.isValid():
                painter.setPen(QPen(QColor("#E2E8F0")))
                painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                painter.drawText(up_rect, Qt.AlignCenter, "▲")
            down_rect = self.style().subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_SpinBoxDown, self)
            if down_rect.isValid():
                painter.setPen(QPen(QColor("#E2E8F0")))
                painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                painter.drawText(down_rect, Qt.AlignCenter, "▼")
        except Exception:
            pass


class MiracleWorker(QObject):
    """단일 작업 워커 - 백그라운드에서 명령어 처리"""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, command, miracle_manager):
        super().__init__()
        self.command = command
        self.miracle_manager = miracle_manager
    
    def run(self):
        try:
            # 백그라운드에서 명령어 처리
            result = self.miracle_manager.process_miracle_command(self.command)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# 단일 작업 로직 함수들
def process_miracle_command_async(miracle_input_widget, user_input):
    """비동기로 명령어 처리 (진짜 백그라운드 스레드)"""
    try:
        # 기존 스레드가 실행 중이면 정리 (안전)
        try:
            if hasattr(miracle_input_widget, 'worker_thread') and getattr(miracle_input_widget, 'worker_thread') is not None:
                try:
                    if miracle_input_widget.worker_thread.isRunning():
                        print("✨ Miracle Manager: 기존 스레드 정리 중...")
                        miracle_input_widget.worker_thread.quit()
                        miracle_input_widget.worker_thread.wait(3000)
                        if miracle_input_widget.worker_thread.isRunning():
                            miracle_input_widget.worker_thread.terminate()
                            miracle_input_widget.worker_thread.wait(1000)
                except RuntimeError:
                    pass
                except Exception:
                    pass
                finally:
                    try:
                        miracle_input_widget.worker_thread.deleteLater()
                    except Exception:
                        pass
                    try:
                        delattr(miracle_input_widget, 'worker_thread')
                    except Exception:
                        pass
        except Exception:
            pass
        
        # 워커 스레드 생성
        miracle_input_widget.worker_thread = QThread()
        try:
            if hasattr(miracle_input_widget, 'start_miracle_progress'):
                miracle_input_widget.start_miracle_progress(1)
        except Exception as prog_err:
            print(f"[MiracleProgress] 초기화 실패: {prog_err}")
        miracle_input_widget.worker = MiracleWorker(user_input, miracle_input_widget)
        miracle_input_widget.worker.moveToThread(miracle_input_widget.worker_thread)
        
        # 시그널 연결
        miracle_input_widget.worker_thread.started.connect(miracle_input_widget.worker.run)
        miracle_input_widget.worker.finished.connect(miracle_input_widget.on_miracle_finished)
        miracle_input_widget.worker.error.connect(miracle_input_widget.on_miracle_error)
        miracle_input_widget.worker.finished.connect(lambda _res: miracle_input_widget.worker_thread.quit())
        miracle_input_widget.worker.error.connect(lambda _err: miracle_input_widget.worker_thread.quit())
        miracle_input_widget.worker.finished.connect(lambda _res: miracle_input_widget.worker.deleteLater())
        miracle_input_widget.worker.error.connect(lambda _err: miracle_input_widget.worker.deleteLater())
        miracle_input_widget.worker_thread.finished.connect(miracle_input_widget.worker_thread.deleteLater)
        
        # 스레드 시작
        miracle_input_widget.worker_thread.start()
        
    except Exception as e:
        print(f"✨ Miracle Manager: 백그라운드 처리 시작 중 오류 - {e}")
        miracle_input_widget.hide_loading_indicator()


def on_miracle_finished(miracle_input_widget, result):
    """미라클 처리 완료 시 호출 (메인 스레드에서 실행) - 단일 작업만"""
    try:
        import json
        print(f"✨ Miracle Manager Single: 단일 작업 처리 결과 - {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 배치 모드는 제외 (단일 작업만 처리)
        is_batch_mode = False
        try:
            is_batch_mode = bool(miracle_input_widget.miracle_mode_btn.isChecked()) and len(get_current_grid_images(miracle_input_widget)) > 1
        except Exception:
            is_batch_mode = False

        if not is_batch_mode:
            # 단일 작업만 처리
            # 새 단일 응답 전에 기존 윤곽선 제거
            try:
                if hasattr(miracle_input_widget.app_instance, 'miracle_manager') and hasattr(miracle_input_widget.app_instance.miracle_manager, 'clear_right_response_borders'):
                    miracle_input_widget.app_instance.miracle_manager.clear_right_response_borders()
            except Exception:
                pass

            display_msg = getattr(miracle_input_widget, 'ai_response_message_display', getattr(miracle_input_widget, 'ai_response_message', ''))

            # 태그를 실제 UI에 반영 (단일 작업만)
            has_changes = any([
                result.get("add"), result.get("dilet"),
                result.get("tag_renames"), result.get("tag_moves"),
                result.get("toggle")   # ✅ 토글 추가
            ])

            pending_tx = False
            pending_change = None

            if result.get("ok") and has_changes:
                apply_miracle_tags_to_ui(miracle_input_widget, result)
                pending_tx = getattr(miracle_input_widget, '_tm_pending_miracle_tx', False)
                pending_change = getattr(miracle_input_widget, '_tm_pending_miracle_change', None)
            else:
                # 이전 작업에서 남은 보류 상태 정리
                for attr in ('_tm_pending_miracle_tx', '_tm_pending_miracle_change', '_tm_pending_miracle_mode'):
                    if hasattr(miracle_input_widget, attr):
                        delattr(miracle_input_widget, attr)

            # 우측 섹션 미러링 업데이트 (카드 ID 생성 및 타임머신 로그는 update_right_response에서 처리)
            try:
                if hasattr(miracle_input_widget.app_instance, 'miracle_manager'):
                    mm = miracle_input_widget.app_instance.miracle_manager
                    if hasattr(mm, 'update_right_response'):
                        card_id = mm.update_right_response(display_msg, defer_tm_commit=pending_tx)
                        # 카드 ID 저장 (필요시 사용)
                        if card_id:
                            setattr(miracle_input_widget, '_tm_last_response_card_id', card_id)
                            setattr(miracle_input_widget, '_tm_last_response_text', display_msg)
                            if pending_change is not None:
                                pending_change["card_id"] = card_id
                        if pending_change is not None and display_msg:
                            pending_change.setdefault("card_text", display_msg)
            except Exception:
                pass

            if pending_tx:
                _TM_commit = None
                try:
                    from timemachine_log import TM as _TM_commit
                    if _TM_commit is not None:
                        _TM_commit.commit()
                except Exception:
                    try:
                        if _TM_commit is not None:
                            _TM_commit.abort()
                    except Exception:
                        pass
                finally:
                    for attr in ('_tm_pending_miracle_tx', '_tm_pending_miracle_change', '_tm_pending_miracle_mode'):
                        if hasattr(miracle_input_widget, attr):
                            delattr(miracle_input_widget, attr)
        
        # 입력 필드 초기화
        miracle_input_widget.miracle_tag_input.clear()
        
        # UI 다시 활성화
        miracle_input_widget.miracle_tag_input.setEnabled(True)
        miracle_input_widget.miracle_tag_input.setPlaceholderText("미라클 명령어를 입력하세요...")
        try:
            miracle_input_widget.apply_outline_styles()
        except Exception:
            pass
        
        # 로딩 인디케이터 숨김
        miracle_input_widget.hide_loading_indicator()
        try:
            if hasattr(miracle_input_widget, 'increment_miracle_progress'):
                miracle_input_widget.increment_miracle_progress(1)
            if hasattr(miracle_input_widget, 'complete_miracle_progress'):
                miracle_input_widget.complete_miracle_progress()
        except Exception as prog_err:
            print(f"[MiracleProgress] 단일 완료 처리 실패: {prog_err}")
        
        # ⭐ 태그 트리 업데이트 추가
        if hasattr(miracle_input_widget.app_instance, 'update_tag_tree'):
            miracle_input_widget.app_instance.update_tag_tree()
            print("✨ Miracle Manager Single: 태그 트리 업데이트 완료")
        
        # 스레드 정리
        if hasattr(miracle_input_widget, 'worker_thread'):
            miracle_input_widget.worker_thread.quit()
            miracle_input_widget.worker_thread.wait(3000)
            if miracle_input_widget.worker_thread.isRunning():
                miracle_input_widget.worker_thread.terminate()
                miracle_input_widget.worker_thread.wait(1000)
            delattr(miracle_input_widget, 'worker_thread')
        if hasattr(miracle_input_widget, '_miracle_busy'):
            miracle_input_widget._miracle_busy = False
        
        # 단일 모드 실패 재시도 버튼 처리
        try:
            mm = getattr(miracle_input_widget.app_instance, 'miracle_manager', None)
            if mm and getattr(mm, '_failed_single_info', None):
                mm.add_retry_button_if_needed()
        except Exception as e:
            print(f"✨ Miracle Manager Single: 재시도 버튼 추가 중 오류 - {e}")
        
        # 질문 시점 이미지 경로 정리
        if hasattr(miracle_input_widget, '_question_time_image_path'):
            delattr(miracle_input_widget, '_question_time_image_path')
            print(f"✨ Miracle Manager Single: 질문 시점 이미지 경로 정리 완료")
            
    except Exception as e:
        print(f"✨ Miracle Manager Single: 처리 완료 후 오류 - {e}")
        miracle_input_widget.miracle_tag_input.setEnabled(True)
        miracle_input_widget.miracle_tag_input.setPlaceholderText("미라클 명령어를 입력하세요...")
        try:
            miracle_input_widget.apply_outline_styles()
        except Exception:
            pass
        miracle_input_widget.hide_loading_indicator()
        if hasattr(miracle_input_widget, '_miracle_busy'):
            miracle_input_widget._miracle_busy = False
        try:
            if hasattr(miracle_input_widget, 'complete_miracle_progress'):
                miracle_input_widget.complete_miracle_progress()
        except Exception as prog_err:
            print(f"[MiracleProgress] 단일 오류 처리(예외) 종료 실패: {prog_err}")


def on_miracle_error(miracle_input_widget, error_msg):
    """미라클 처리 오류 시 호출 - 단일 작업만"""
    try:
        print(f"✨ Miracle Manager Single: 단일 작업 처리 중 오류 - {error_msg}")
        miracle_input_widget.miracle_tag_input.setEnabled(True)
        miracle_input_widget.miracle_tag_input.setPlaceholderText("미라클 명령어를 입력하세요...")
        try:
            miracle_input_widget.apply_outline_styles()
        except Exception:
            pass
        miracle_input_widget.hide_loading_indicator()
        try:
            if hasattr(miracle_input_widget, 'complete_miracle_progress'):
                miracle_input_widget.complete_miracle_progress()
        except Exception as prog_err:
            print(f"[MiracleProgress] 단일 오류 진행 종료 실패: {prog_err}")
        
        # 스레드 정리
        if hasattr(miracle_input_widget, 'worker_thread'):
            miracle_input_widget.worker_thread.quit()
            miracle_input_widget.worker_thread.wait(3000)
            if miracle_input_widget.worker_thread.isRunning():
                miracle_input_widget.worker_thread.terminate()
                miracle_input_widget.worker_thread.wait(1000)
            delattr(miracle_input_widget, 'worker_thread')
        if hasattr(miracle_input_widget, '_miracle_busy'):
            miracle_input_widget._miracle_busy = False
        
        # 질문 시점 이미지 경로 정리
        if hasattr(miracle_input_widget, '_question_time_image_path'):
            delattr(miracle_input_widget, '_question_time_image_path')
            print(f"✨ Miracle Manager Single: 질문 시점 이미지 경로 정리 완료 (에러)")
            
    except Exception as e:
        print(f"✨ Miracle Manager Single: 오류 처리 중 오류 - {e}")
        miracle_input_widget.miracle_tag_input.setEnabled(True)
        miracle_input_widget.miracle_tag_input.setPlaceholderText("미라클 명령어를 입력하세요...")
        miracle_input_widget.hide_loading_indicator()
        if hasattr(miracle_input_widget, '_miracle_busy'):
            miracle_input_widget._miracle_busy = False
        
        # 질문 시점 이미지 경로 정리
        if hasattr(miracle_input_widget, '_question_time_image_path'):
            delattr(miracle_input_widget, '_question_time_image_path')


def process_miracle_command(miracle_input_widget, command):
    """미라클 명령어 파싱 및 처리 - 단일 작업만"""
    import re
    import json
    
    # 현재 선택된 단일 이미지 경로 가져오기 (질문 시점에 고정)
    current_image_path = get_current_image_path(miracle_input_widget)
    if current_image_path:
        miracle_input_widget._question_time_image_path = current_image_path
        print(f"✨ Miracle Manager Single: 질문 시점 이미지 저장 - {current_image_path}")
    
    # 현재 선택된 이미지 목록 가져오기
    target_images = get_current_grid_images(miracle_input_widget)
    targets_count = len(target_images)
    
    mm = getattr(miracle_input_widget.app_instance, 'miracle_manager', None)
    if mm and hasattr(mm, '_failed_single_info'):
        mm._failed_single_info = None
    
    # 미라클 일괄 모드 확인
    is_batch_mode = miracle_input_widget.miracle_mode_btn.isChecked()
    btn_text = miracle_input_widget.miracle_mode_btn.text()
    print(f"✨ Miracle Manager Single: process_miracle_command - 버튼={btn_text}, is_batch_mode={is_batch_mode}, 이미지 수={targets_count}")
    
    # 명령어 파싱
    add_pattern = r'add::\s*([^:]+?)(?=\s+dilet::|\s+tags::|\s+toggle::|$)'
    dilet_pattern = r'dilet::\s*([^:]+?)(?=\s+add::|\s+tags::|\s+toggle::|$)'
    tags_pattern = r'tags::\s*([^:]+?)(?=\s+add::|\s+dilet::|\s+toggle::|\s+tags::|$)'
    toggle_pattern = r'toggle::\s*([^:]+?)(?=\s+add::|\s+dilet::|\s+tags::|\s+toggle::|$)'
    
    add_matches = re.findall(add_pattern, command, re.IGNORECASE)
    dilet_matches = re.findall(dilet_pattern, command, re.IGNORECASE)
    tags_matches = re.findall(tags_pattern, command, re.IGNORECASE)
    toggle_matches = re.findall(toggle_pattern, command, re.IGNORECASE)
    
    add_tags = []
    dilet_tags = []
    toggle_tags = []
    
    if add_matches:
        add_text = add_matches[0].strip()
        add_tags = [tag.strip() for tag in re.split(r'[,\n\r]+', add_text) if tag.strip()]
        print(f"✨ Miracle Manager Single: add 태그 파싱 - {add_tags}")
    
    if dilet_matches:
        dilet_text = dilet_matches[0].strip()
        dilet_tags = [tag.strip() for tag in re.split(r'[,\n\r]+', dilet_text) if tag.strip()]
        print(f"✨ Miracle Manager Single: dilet 태그 파싱 - {dilet_tags}")
    
    if toggle_matches:
        toggle_text = toggle_matches[0].strip()
        toggle_tags = [tag.strip() for tag in re.split(r'[,\n\r]+', toggle_text) if tag.strip()]
        print(f"✨ Miracle Manager Single: toggle 태그 파싱 - {toggle_tags}")
    
    api_error_message = None
    
    # 태그 위치 조작 파싱
    tag_moves = []
    tag_renames = []
    if tags_matches:
        tags_text = tags_matches[0].strip()
        tags_tags = [tag.strip() for tag in re.split(r'[,\n\r]+', tags_text) if tag.strip()]
        print(f"✨ Miracle Manager Single: tags 태그 파싱 - {tags_tags}")
        
        for tag_move in tags_tags:
            move_pattern = r'^(.+?)::(up|down)(\d*)$'
            match = re.match(move_pattern, tag_move, re.IGNORECASE)
            if match:
                tag_name = match.group(1).strip()
                direction = match.group(2).lower()
                steps = int(match.group(3)) if match.group(3) else 1
                tag_moves.append({
                    'tag': tag_name,
                    'direction': direction,
                    'steps': steps
                })
                print(f"✨ Miracle Manager Single: 태그 위치 조작 - {tag_name} {direction} {steps}칸")
            else:
                add_tags.append(tag_move)
                print(f"✨ Miracle Manager Single: 태그 추가로 처리 - {tag_move}")
    
    if not add_matches and not dilet_matches:
        # 배치 모드는 처리하지 않음 (단일 작업만)
        if is_batch_mode and len(target_images) > 1:
            print("✨ Miracle Manager Single: 배치 모드는 단일 모듈에서 처리하지 않음")
            ai_response = None
        else:
            print("✨ Miracle Manager Single: 자연어 명령어 감지 - AI 모델로 해석")
            ai_response = interpret_natural_language_with_ai(miracle_input_widget, command, is_batch_mode, target_images)
        
        if ai_response:
            print(f"✨ Miracle Manager Single: AI 응답 - {ai_response}")
            # 단일 이미지 모드: 기존 파싱 로직
            add_matches = re.findall(add_pattern, ai_response, re.IGNORECASE)
            dilet_matches = re.findall(dilet_pattern, ai_response, re.IGNORECASE)
            tags_matches = re.findall(tags_pattern, ai_response, re.IGNORECASE)
            toggle_matches = re.findall(toggle_pattern, ai_response, re.IGNORECASE)
            
            if add_matches:
                add_text = add_matches[0].strip()
                add_tags = [tag.strip() for tag in re.split(r'[,\n\r]+', add_text) if tag.strip()]
                print(f"✨ Miracle Manager Single: AI 응답에서 add 태그 추출 - {add_tags}")
            
            if dilet_matches:
                dilet_text = dilet_matches[0].strip()
                dilet_tags = [tag.strip() for tag in re.split(r'[,\n\r]+', dilet_text) if tag.strip()]
                print(f"✨ Miracle Manager Single: AI 응답에서 dilet 태그 추출 - {dilet_tags}")
            
            if toggle_matches:
                toggle_text = toggle_matches[0].strip()
                toggle_tags = [tag.strip() for tag in re.split(r'[,\n\r]+', toggle_text) if tag.strip()]
                print(f"✨ Miracle Manager Single: AI 응답에서 toggle 태그 추출 - {toggle_tags}")
            
            if tags_matches:
                tags_text = tags_matches[0].strip()
                tags_tags = [tag.strip() for tag in re.split(r'[,\n\r]+', tags_text) if tag.strip()]
                print(f"✨ Miracle Manager Single: AI 응답에서 tags 태그 추출 - {tags_tags}")
                
                for tag_move in tags_tags:
                    move_pattern = r'^(up|down)(\d*)::(.+?)$'
                    match = re.match(move_pattern, tag_move, re.IGNORECASE)
                    if match:
                        direction = match.group(1).lower()
                        steps = int(match.group(2)) if match.group(2) else 1
                        tag_name = match.group(3).strip()
                        tag_moves.append({
                            'tag': tag_name,
                            'direction': direction,
                            'steps': steps
                        })
                        print(f"✨ Miracle Manager Single: AI 응답에서 태그 위치 조작 추출 - {tag_name} {direction} {steps}칸")
            
            if not tag_moves:
                move_pattern = r'(up|down)(\d*)::(.+?)(?=\n|$)'
                matches = re.findall(move_pattern, ai_response, re.IGNORECASE | re.DOTALL)
                
                rn_matches = re.findall(r'(?mi)^\s*"?(.+?)"?\s*::\s*change\s+"?(.+?)"?\s*$', ai_response)
                for _o, _n in rn_matches:
                    _o = _o.strip().strip('\'"[](){}')
                    _n = _n.strip().strip('\'"[](){}')
                    tag_renames.append({'from': _o, 'to': _n})
                    print(f"✨ Miracle Manager Single: AI 응답에서 rename 추출 - {_o} → {_n}")
                
                for match in matches:
                    direction = match[0].lower()
                    steps = int(match[1]) if match[1] else 1
                    tag_name = match[2].strip()
                    tag_moves.append({
                        'tag': tag_name,
                        'direction': direction,
                        'steps': steps
                    })
                    print(f"✨ Miracle Manager Single: AI 응답에서 태그 위치 조작 추출 (직접) - {tag_name} {direction} {steps}칸")
            
            miracle_input_widget.ai_response_message = ai_response
            try:
                miracle_input_widget.ai_response_message_display = postprocess_ai_response_for_batch_display(miracle_input_widget, ai_response, target_images)
            except Exception as __e:
                print(f"✨ Miracle Manager Single: display 후처리 실패 - {__e}")
                miracle_input_widget.ai_response_message_display = miracle_input_widget.ai_response_message
            
            stripped_ai_resp = ai_response.strip() if isinstance(ai_response, str) else ""
            if stripped_ai_resp.startswith("⚠️"):
                api_error_message = stripped_ai_resp
        else:
            api_error_message = "⚠️ AI 응답이 없습니다."
            miracle_input_widget.ai_response_message = api_error_message
            miracle_input_widget.ai_response_message_display = api_error_message
    
    if api_error_message and mm:
        failure_info = {
            "command": command,
            "error": api_error_message
        }
        question_image_path = getattr(miracle_input_widget, '_question_time_image_path', None) or current_image_path
        if question_image_path:
            try:
                failure_info["image_path"] = str(question_image_path)
            except Exception:
                failure_info["image_path"] = question_image_path
        mm._failed_single_info = failure_info

    # 태그 검증
    validated_result = validate_tags(miracle_input_widget, add_tags, dilet_tags)
    
    # 현재 이미지의 태그들 가져오기
    current_image_tags = get_current_image_tags(miracle_input_widget)
    
    # 현재 이미지 이름 가져오기
    current_image_name = get_current_image_name(miracle_input_widget)
    
    # ok/reason 결정
    if api_error_message:
        reason = "api-error"
        ok = False
    elif (not validated_result["add"] and not validated_result["dilet"]
          and not tag_moves and not tag_renames
          and not toggle_tags):   # ✅ 토글 반영
        if validated_result["rejected"]:
            reason = "no-valid-tags"
            ok = False
        else:
            reason = "noop"
            ok = True
    else:
        reason = "ok"
        ok = True
    
    # 자연어 메시지 생성
    if hasattr(miracle_input_widget, 'ai_response_message') and miracle_input_widget.ai_response_message:
        message = miracle_input_widget.ai_response_message
    else:
        message = compose_message(reason, validated_result["add"], validated_result["dilet"], 
                                targets_count, validated_result["rejected"])
    
    # 태그 위치 조작 및 이름 변경 수행 (단일 모드만)
    if tag_renames and not (miracle_input_widget.miracle_mode_btn.isChecked() and len(target_images) > 1):
        apply_tag_renames(miracle_input_widget, tag_renames)
    if tag_moves:
        apply_tag_moves(miracle_input_widget, tag_moves)
    
    # 결과 구성
    result = {
        "version": "v1",
        "ok": ok,
        "reason": reason,
        "command": command,
        "targets_count": targets_count,
        "targets": None,
        "add": validated_result["add"],
        "dilet": validated_result["dilet"],
        "toggle": toggle_tags,
        "tag_moves": tag_moves,
        "tag_renames": tag_renames,
        "rejected": validated_result["rejected"],
        "notes": validated_result["notes"],
        "current_image_name": current_image_name,
        "message": message,
        "current_tags": current_image_tags
    }
    
    return result


# 헬퍼 함수들
def apply_tag_moves(miracle_input_widget, tag_moves):
    """태그 위치 조작 수행 (타임머신 로그 없음)"""
    try:
        # 질문 시점에 저장된 이미지 경로 사용
        if hasattr(miracle_input_widget, '_question_time_image_path') and miracle_input_widget._question_time_image_path:
            actual_image_path = miracle_input_widget._question_time_image_path
            print(f"✨ Miracle Manager Single: 질문 시점 이미지 사용 (태그 이동) - {actual_image_path}")
        else:
            actual_image_path = get_current_image_path(miracle_input_widget)
            print(f"✨ Miracle Manager Single: 현재 이미지 사용 (태그 이동) - {actual_image_path}")
        
        if not actual_image_path:
            print("✨ Miracle Manager Single: 이미지 경로 없어서 위치 조작 불가")
            return
        
        # all_tags에서 직접 가져오기 (배치 모드와 동일)
        if not hasattr(miracle_input_widget.app_instance, 'all_tags'):
            miracle_input_widget.app_instance.all_tags = {}
        
        if actual_image_path not in miracle_input_widget.app_instance.all_tags:
            print("✨ Miracle Manager Single: 이미지에 태그가 없어서 위치 조작 불가")
            return
        
        current_tags = list(miracle_input_widget.app_instance.all_tags[actual_image_path])
        print(f"✨ Miracle Manager Single: 태그 위치 조작 시작 - 현재 순서: {current_tags}")

        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨
        
        for move in tag_moves:
            tag_name = move['tag']
            direction = move['direction']
            steps = move['steps']
            
            if tag_name not in current_tags:
                print(f"✨ Miracle Manager Single: 태그 '{tag_name}'를 찾을 수 없음")
                continue
            
            current_index = current_tags.index(tag_name)
            new_index = current_index
            
            if direction == 'up':
                new_index = max(0, current_index - steps)
            elif direction == 'down':
                new_index = min(len(current_tags) - 1, current_index + steps)
            
            if new_index != current_index:
                tag = current_tags.pop(current_index)
                current_tags.insert(new_index, tag)
                print(f"✨ Miracle Manager Single: '{tag_name}' {direction} {steps}칸 이동 - {current_index} → {new_index}")
            else:
                print(f"✨ Miracle Manager Single: '{tag_name}' 이동 불가 - 경계 초과")
        
        # all_tags에 저장 (배치 모드와 동일)
        miracle_input_widget.app_instance.all_tags[actual_image_path] = current_tags
        print(f"✨ Miracle Manager Single: 태그 위치 조작 완료 - 새로운 순서: {current_tags}")

        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨
        
        # 현재 표시 중인 이미지와 같으면 UI 업데이트
        current_display_image = getattr(miracle_input_widget.app_instance, 'current_image', None)
        if current_display_image == actual_image_path:
            miracle_input_widget.app_instance.current_tags = current_tags
            if hasattr(miracle_input_widget.app_instance, 'update_current_tags_display'):
                miracle_input_widget.app_instance.update_current_tags_display()
        
    except Exception as e:
        print(f"✨ Miracle Manager Single: 태그 위치 조작 중 오류 - {e}")
        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨


def apply_tag_renames(miracle_input_widget, renames):
    """태그 이름 변경 수행 (타임머신 로그 없음)"""
    try:
        if not renames:
            return
        
        # 질문 시점에 저장된 이미지 경로 사용
        if hasattr(miracle_input_widget, '_question_time_image_path') and miracle_input_widget._question_time_image_path:
            actual_image_path = miracle_input_widget._question_time_image_path
            print(f"✨ Miracle Manager Single: 질문 시점 이미지 사용 (태그 리네임) - {actual_image_path}")
        else:
            actual_image_path = get_current_image_path(miracle_input_widget)
            print(f"✨ Miracle Manager Single: 현재 이미지 사용 (태그 리네임) - {actual_image_path}")
        
        if not actual_image_path:
            print("✨ Miracle Manager Single: 이미지 경로 없어서 리네임 불가")
            return
        
        # all_tags에서 직접 가져오기 (배치 모드와 동일)
        if not hasattr(miracle_input_widget.app_instance, 'all_tags'):
            miracle_input_widget.app_instance.all_tags = {}
        
        if actual_image_path not in miracle_input_widget.app_instance.all_tags:
            print("✨ Miracle Manager Single: 이미지에 태그가 없어서 리네임 불가")
            return
        
        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨
        
        active_list = list(miracle_input_widget.app_instance.all_tags[actual_image_path])
        removed_list = list(miracle_input_widget.app_instance.image_removed_tags.get(actual_image_path, []))
        print(f"✨ Miracle Manager Single: rename 시작 - {renames}")
        
        for r in renames:
            old = str(r.get('from','')).strip().strip('\'"[](){}')
            new = str(r.get('to','')).strip().strip('\'"[](){}')
            if not old or not new or old == new:
                continue
            
            # 대상 리스트 결정
            if old in active_list:
                target_list = active_list
                target_type = 'active'
            elif old in removed_list:
                target_list = removed_list
                target_type = 'removed'
            else:
                continue
            
            old_idx = target_list.index(old)
            
            # 중복 처리: 새 이름이 반대 필드에 있으면 반대 필드에서 제거
            if target_type == 'active' and new in removed_list:
                removed_list.remove(new)
                print(f"✨ Miracle Manager Single: 리무버에서 중복 제거 - {new}")
            elif target_type == 'removed' and new in active_list:
                active_list.remove(new)
                print(f"✨ Miracle Manager Single: 액티브에서 중복 제거 - {new}")
            
            # 같은 리스트 내 중복 처리
            if new in target_list:
                new_idx = target_list.index(new)
                target_list.pop(new_idx)
                if new_idx < old_idx:
                    old_idx -= 1
            
            target_list[old_idx] = new
            
            # manual_tag_info 옮기기 (old 태그의 used/trigger 정보를 new 태그로 이전)
            if hasattr(miracle_input_widget.app_instance, 'manual_tag_info'):
                if old in miracle_input_widget.app_instance.manual_tag_info:
                    is_trigger = miracle_input_widget.app_instance.manual_tag_info[old]
                    miracle_input_widget.app_instance.manual_tag_info[new] = is_trigger
                    del miracle_input_widget.app_instance.manual_tag_info[old]
                    print(f"✨ Miracle Manager Single: manual_tag_info 이전 - {old} → {new} ({'trigger' if is_trigger else 'used'})")
                    
                    # 태그 통계 모듈의 캐시도 업데이트
                    if hasattr(miracle_input_widget.app_instance, 'tag_statistics_module'):
                        if hasattr(miracle_input_widget.app_instance.tag_statistics_module, '_cached_categories'):
                                cache = miracle_input_widget.app_instance.tag_statistics_module._cached_categories
                                if old in cache:
                                    cache[new] = cache[old]
                                    del cache[old]
                                else:
                                    cache[new] = 'trigger' if is_trigger else 'used'
                                print(f"✨ Miracle Manager Single: 태그 캐시 업데이트 - {old} → {new}")
                
                # 글로벌 태그 관리 플러그인 사용
                from global_tag_manager import edit_global_tag
                edit_global_tag(miracle_input_widget.app_instance, old, new)
        
        # 결과 반영 - all_tags 관리 플러그인 사용
        from all_tags_manager import set_tags_for_image
        set_tags_for_image(miracle_input_widget.app_instance, actual_image_path, active_list)
        
        # 리무버 리스트 저장
        miracle_input_widget.app_instance.image_removed_tags[actual_image_path] = removed_list
        
        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨
        
        print(f"✨ Miracle Manager Single: rename 완료 - {actual_image_path}")
        
        # UI 동기화
        if hasattr(miracle_input_widget.app_instance, 'current_image') and miracle_input_widget.app_instance.current_image == actual_image_path:
            miracle_input_widget.app_instance.current_tags = list(active_list)
            miracle_input_widget.app_instance.removed_tags = list(removed_list)
            if hasattr(miracle_input_widget.app_instance, 'update_current_tags_display'):
                miracle_input_widget.app_instance.update_current_tags_display()
        
    except Exception as e:
        print(f"✨ Miracle Manager Single: 태그 이름 변경 수행 중 오류 - {e}")
        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨


def validate_tags(miracle_input_widget, add_tags, dilet_tags):
    """태그 검증"""
    allowed_tags = get_allowed_tags(miracle_input_widget)
    categories = get_tag_categories(miracle_input_widget)
    
    validated_add = []
    validated_dilet = []
    rejected = {}
    notes = []
    
    for tag in add_tags:
        validation_result = validate_single_tag(tag, allowed_tags, categories)
        if validation_result["valid"]:
            validated_add.append(tag)
        else:
            rejected[tag] = validation_result["reason"]
    
    for tag in dilet_tags:
        validation_result = validate_single_tag(tag, allowed_tags, categories)
        if validation_result["valid"]:
            validated_dilet.append(tag)
        else:
            rejected[tag] = validation_result["reason"]
    
    validated_add = [tag for tag in validated_add if tag not in validated_dilet]
    validated_add = list(dict.fromkeys(validated_add))
    validated_dilet = list(dict.fromkeys(validated_dilet))
    
    if rejected:
        notes.append("일부 태그가 검증 규칙에 맞지 않아 제외되었습니다.")
    if not validated_add and not validated_dilet:
        notes.append("유효한 태그가 없습니다.")
    
    return {
        "add": validated_add,
        "dilet": validated_dilet,
        "rejected": rejected,
        "notes": notes
    }


def get_allowed_tags(miracle_input_widget):
    """태그 트리에서 허용 가능한 태그들 가져오기"""
    allowed_tags = set()
    try:
        if hasattr(miracle_input_widget.app_instance, 'current_tags') and miracle_input_widget.app_instance.current_tags:
            allowed_tags.update(miracle_input_widget.app_instance.current_tags)
        if hasattr(miracle_input_widget.app_instance, 'removed_tags') and miracle_input_widget.app_instance.removed_tags:
            allowed_tags.update(miracle_input_widget.app_instance.removed_tags)
        if hasattr(miracle_input_widget.app_instance, 'global_tag_stats') and miracle_input_widget.app_instance.global_tag_stats:
            allowed_tags.update(miracle_input_widget.app_instance.global_tag_stats.keys())
    except Exception as e:
        print(f"태그 수집 중 오류: {e}")
    return allowed_tags


def get_tag_categories(miracle_input_widget):
    """태그 카테고리들 가져오기"""
    categories = set()
    try:
        if hasattr(miracle_input_widget.app_instance, 'tag_tree_module'):
            all_tags = get_allowed_tags(miracle_input_widget)
            if all_tags:
                tree_structure = miracle_input_widget.app_instance.tag_tree_module.get_tag_tree_structure(list(all_tags), miracle_input_widget.app_instance)
                if tree_structure:
                    for category, tags in tree_structure:
                        categories.add(str(category))
    except Exception as e:
        print(f"카테고리 수집 중 오류: {e}")
    return categories


def validate_single_tag(tag, allowed_tags, categories):
    """단일 태그 유효성 검사"""
    if tag in categories:
        return {"valid": False, "reason": "category-name-not-allowed"}
    
    forbidden_chars = {':', '/', '>', '\\'}
    if any(char in tag for char in forbidden_chars):
        return {"valid": False, "reason": "category-path-like-string-not-allowed"}
    
    import re
    if re.search(r'[가-힣]', tag):
        return {"valid": False, "reason": "korean-tags-not-allowed"}
    
    return {"valid": True, "reason": "ok"}


def compose_message(reason, add_final, dilet_ok, targets_count, rejected):
    """자연어 메시지 생성"""
    if reason == "miracle-mode-off":
        return "미라클 모드가 비활성화되어 있습니다."
    if reason == "noop":
        return "처리 완료"
    if reason == "no-valid-tags":
        return "유효한 태그가 없습니다."
    if add_final or dilet_ok:
        return f"{targets_count}개 이미지 처리 완료"
    return "처리 완료"


def get_current_grid_images(miracle_input_widget):
    """현재 선택된 이미지 목록 가져오기"""
    try:
        is_batch_mode = miracle_input_widget.miracle_mode_btn.isChecked()
        
        if is_batch_mode:
            # 배치 모드: 현재 그리드 전체(모든 페이지) 기준
            # 우선순위: image_filtered_list (경로 객체 리스트) → image_list (문자열 경로 리스트)
            if hasattr(miracle_input_widget.app_instance, 'image_filtered_list') and miracle_input_widget.app_instance.image_filtered_list:
                selected_images = [str(p) for p in miracle_input_widget.app_instance.image_filtered_list]
                return selected_images
            if hasattr(miracle_input_widget.app_instance, 'image_list') and miracle_input_widget.app_instance.image_list:
                selected_images = list(miracle_input_widget.app_instance.image_list)
                return selected_images
        
        selected_images = []
        
        if hasattr(miracle_input_widget.app_instance, 'search_filter_grid_module'):
            grid_module = miracle_input_widget.app_instance.search_filter_grid_module
            if hasattr(grid_module, 'selected_images') and grid_module.selected_images:
                selected_images = list(grid_module.selected_images)
            elif hasattr(grid_module, 'get_selected_images'):
                selected_images = grid_module.get_selected_images()
        
        if not selected_images:
            if hasattr(miracle_input_widget.app_instance, 'current_image_path') and miracle_input_widget.app_instance.current_image_path:
                selected_images = [miracle_input_widget.app_instance.current_image_path]
            elif hasattr(miracle_input_widget.app_instance, 'image_list') and miracle_input_widget.app_instance.image_list:
                selected_images = [miracle_input_widget.app_instance.image_list[0]] if miracle_input_widget.app_instance.image_list else []
        
        return selected_images
        
    except Exception as e:
        print(f"이미지 목록 가져오기 중 오류: {e}")
    return []


def apply_miracle_tags_to_ui(miracle_input_widget, result):
    """미라클 결과를 실제 UI에 반영 - 단일 작업만 (통합 트랜잭션)"""
    try:
        add_tags = result.get("add", [])
        dilet_tags = result.get("dilet", [])
        tag_renames = result.get("tag_renames", [])
        tag_moves = result.get("tag_moves", [])
        toggle_tags = result.get("toggle", [])   # ✅ 위로 당김
        
        print(f"✨ Miracle Manager Single: 단일 작업 UI 반영 시작 - add: {len(add_tags)}개, dilet: {len(dilet_tags)}개, renames: {len(tag_renames)}개, moves: {len(tag_moves)}개, toggle: {len(toggle_tags)}개")
        
        # 변경사항이 없으면 로그 기록하지 않음
        if not add_tags and not dilet_tags and not tag_renames and not tag_moves and not toggle_tags:
            print(f"✨ Miracle Manager Single: 변경사항 없음 - 로그 기록하지 않음")
            return
        
        # 질문 시점에 저장된 이미지 경로 사용
        if hasattr(miracle_input_widget, '_question_time_image_path') and miracle_input_widget._question_time_image_path:
            actual_image_path = miracle_input_widget._question_time_image_path
            print(f"✨ Miracle Manager Single: 질문 시점 이미지 사용 - {actual_image_path}")
        else:
            actual_image_path = get_current_image_path(miracle_input_widget)
            print(f"✨ Miracle Manager Single: 현재 이미지 사용 - {actual_image_path}")
        
        if not actual_image_path:
            print("✨ Miracle Manager Single: 이미지 경로 없어서 처리 불가")
            return
        
        # ── 타임머신: 모든 미라클 작업을 하나의 트랜잭션으로 묶기 ──
        TM = None
        try:
            from timemachine_log import TM as _TM
            TM = _TM
        except Exception:
            TM = None
        
        if TM is not None:
            TM.begin("single comprehensive", context={
                "source": "miracle_single",
                "image": actual_image_path,
                "add_count": len(add_tags),
                "delete_count": len(dilet_tags),
                "rename_count": len(tag_renames),
                "moves_count": len(tag_moves),
            })
        
        # all_tags에서 직접 태그를 처리
        if not hasattr(miracle_input_widget.app_instance, 'all_tags'):
            miracle_input_widget.app_instance.all_tags = {}
        
        if actual_image_path not in miracle_input_widget.app_instance.all_tags:
            miracle_input_widget.app_instance.all_tags[actual_image_path] = []
        
        current_tags = list(miracle_input_widget.app_instance.all_tags[actual_image_path])
        before_tags_snapshot = list(current_tags)
        print(f"✨ Miracle Manager Single: 현재 태그 - {current_tags}")

        # 1. 태그 이름 변경 먼저 처리 (다른 작업에 영향)
        if tag_renames:
            print(f"✨ Miracle Manager Single: 태그 이름 변경 처리 - {tag_renames}")
            for rename in tag_renames:
                old_tag = rename.get('from', '').strip().strip('\'"[](){}')
                new_tag = rename.get('to', '').strip().strip('\'"[](){}')
                if old_tag and new_tag and old_tag != new_tag and old_tag in current_tags:
                    old_idx = current_tags.index(old_tag)
                    if new_tag in current_tags:
                        new_idx = current_tags.index(new_tag)
                        current_tags.pop(new_idx)
                        if new_idx < old_idx:
                            old_idx -= 1
                    current_tags[old_idx] = new_tag
                    
                    # manual_tag_info 옮기기
                    if hasattr(miracle_input_widget.app_instance, 'manual_tag_info'):
                        if old_tag in miracle_input_widget.app_instance.manual_tag_info:
                            is_trigger = miracle_input_widget.app_instance.manual_tag_info[old_tag]
                            miracle_input_widget.app_instance.manual_tag_info[new_tag] = is_trigger
                            del miracle_input_widget.app_instance.manual_tag_info[old_tag]
                    
                    # 글로벌 태그 관리 플러그인 사용
                    from global_tag_manager import edit_global_tag
                    edit_global_tag(miracle_input_widget.app_instance, old_tag, new_tag)
                    print(f"✨ Miracle Manager Single: 태그 이름 변경 - {old_tag} → {new_tag}")

        # 2. 토글 처리 (dilet/add 처리 전에 먼저 실행)
        if toggle_tags:
            print(f"✨ Miracle Manager Single: 토글 처리 - {toggle_tags}")
            from image_tagging_module import toggle_current_tag
            for tag in toggle_tags:
                # 현재 이미지의 액티브/리무버 상태 확인
                if tag in current_tags:
                    # 액티브에 있으면 → 리무버로 이동
                    # 타임머신 로그 기록
                    try:
                        from timemachine_log import TM
                        TM.log_change({
                            "type": "tag_toggle_off",
                            "image": actual_image_path,
                            "tag": tag,
                        })
                    except Exception:
                        pass
                    
                    # 1. 액티브에서 제거
                    current_tags.remove(tag)
                    # 2. 리무버에 추가
                    miracle_input_widget.app_instance.image_removed_tags.setdefault(actual_image_path, [])
                    if tag not in miracle_input_widget.app_instance.image_removed_tags[actual_image_path]:
                        miracle_input_widget.app_instance.image_removed_tags[actual_image_path].append(tag)
                    # 3. UI 동기화 (현재 표시 이미지일 때만)
                    if actual_image_path == miracle_input_widget.app_instance.current_image:
                        if tag not in miracle_input_widget.app_instance.removed_tags:
                            miracle_input_widget.app_instance.removed_tags.append(tag)
                    print(f"✨ Miracle Manager Single: 토글 (액티브→리무버) - {tag}")
                elif tag in miracle_input_widget.app_instance.image_removed_tags.get(actual_image_path, []):
                    # 리무버에 있으면 → 액티브로 이동
                    # 타임머신 로그 기록
                    try:
                        from timemachine_log import TM
                        TM.log_change({
                            "type": "tag_toggle_on",
                            "image": actual_image_path,
                            "tag": tag,
                        })
                    except Exception:
                        pass
                    
                    # 1. 리무버에서 제거
                    miracle_input_widget.app_instance.image_removed_tags[actual_image_path].remove(tag)
                    # 2. 액티브에 추가
                    current_tags.append(tag)
                    # 3. UI 동기화 (현재 표시 이미지일 때만)
                    if actual_image_path == miracle_input_widget.app_instance.current_image:
                        if tag in miracle_input_widget.app_instance.removed_tags:
                            miracle_input_widget.app_instance.removed_tags.remove(tag)
                    print(f"✨ Miracle Manager Single: 토글 (리무버→액티브) - {tag}")
                else:
                    print(f"✨ Miracle Manager Single: 토글 대상 태그 없음 - {tag}")

        # 3. 태그 삭제 처리 (완전 삭제)
        delete_from = {}  # 원래 위치 정보 저장
        if dilet_tags:
            print(f"✨ Miracle Manager Single: 태그 완전 삭제 처리 - {dilet_tags}")
            for tag in dilet_tags:
                # 액티브에서 완전 삭제
                if tag in current_tags:
                    delete_from[tag] = "active"  # 원래 위치 기록
                    current_tags.remove(tag)
                    # 글로벌 태그에서도 제거
                    try:
                        from timemachine_log import TM
                        TM.log_change({
                            "type": "tag_remove",
                            "image": actual_image_path,
                            "tag": tag,
                        })
                    except Exception:
                        pass
                    print(f"✨ Miracle Manager Single: 액티브에서 완전 삭제 - {tag}")
                
                # 리무버에서 완전 삭제
                elif tag in miracle_input_widget.app_instance.image_removed_tags.get(actual_image_path, []):
                    delete_from[tag] = "removed"  # 원래 위치 기록
                    miracle_input_widget.app_instance.image_removed_tags[actual_image_path].remove(tag)
                    # UI 동기화 (현재 표시 이미지일 때만)
                    if actual_image_path == miracle_input_widget.app_instance.current_image:
                        if tag in miracle_input_widget.app_instance.removed_tags:
                            miracle_input_widget.app_instance.removed_tags.remove(tag)
                    print(f"✨ Miracle Manager Single: 리무버에서 완전 삭제 - {tag}")

        # 4. 태그 추가 처리
        if add_tags:
            print(f"✨ Miracle Manager Single: 태그 추가 처리 - {add_tags}")
            for tag in add_tags:
                if tag not in current_tags:
                    current_tags.append(tag)
                    print(f"✨ Miracle Manager Single: 태그 추가 - {tag}")
                    
                    # global_tag_stats 업데이트
                    if tag not in miracle_input_widget.app_instance.global_tag_stats:
                        try:
                            from danbooru_module import get_danbooru_category
                            category = get_danbooru_category(tag)
                            if category:
                                miracle_input_widget.app_instance.global_tag_stats[tag] = {
                                    'image_count': 0,
                                    'category': category
                                }
                            else:
                                miracle_input_widget.app_instance.global_tag_stats[tag] = {
                                    'image_count': 0,
                                    'category': 'unknown'
                                }
                        except ImportError:
                            miracle_input_widget.app_instance.global_tag_stats[tag] = {
                                'image_count': 0,
                                'category': 'unknown'
                            }
                    
                    # global_tag_stats 카운트 증가
                    if isinstance(miracle_input_widget.app_instance.global_tag_stats.get(tag), dict):
                        miracle_input_widget.app_instance.global_tag_stats[tag]['image_count'] += 1
                    elif tag in miracle_input_widget.app_instance.global_tag_stats:
                        miracle_input_widget.app_instance.global_tag_stats[tag] += 1
                    else:
                        miracle_input_widget.app_instance.global_tag_stats[tag] = 1
                    
                    # manual_tag_info 업데이트
                    if hasattr(miracle_input_widget.app_instance, 'manual_tag_info'):
                        if tag not in miracle_input_widget.app_instance.manual_tag_info:
                            miracle_input_widget.app_instance.manual_tag_info[tag] = False

        # 5. 태그 위치 조작 처리
        if tag_moves:
            print(f"✨ Miracle Manager Single: 태그 위치 조작 처리 - {tag_moves}")
            removed_list = list(miracle_input_widget.app_instance.image_removed_tags.get(actual_image_path, []))
            
            for move in tag_moves:
                tag_name = move.get('tag')
                direction = move.get('direction')
                steps = move.get('steps', 1)
                
                # 대상 리스트 결정
                if tag_name in current_tags:
                    target = 'active'
                    work_list = current_tags
                elif tag_name in removed_list:
                    target = 'removed'
                    work_list = removed_list
                else:
                    print(f"✨ Miracle Manager Single: 위치 조작 대상 태그 없음 - {tag_name}")
                    continue
                
                current_index = work_list.index(tag_name)
                new_index = current_index
                
                if direction == 'up':
                    new_index = max(0, current_index - steps)
                elif direction == 'down':
                    new_index = min(len(work_list) - 1, current_index + steps)
                
                if new_index != current_index:
                    tag = work_list.pop(current_index)
                    work_list.insert(new_index, tag)
                    print(f"✨ Miracle Manager Single: '{tag_name}' {direction} {steps}칸 이동 - {current_index} → {new_index} ({target})")
            
            # 변경된 태그 순서 저장
            if target == 'active':
                # 현재 표시 이미지면 UI 반영
                if actual_image_path == miracle_input_widget.app_instance.current_image:
                    miracle_input_widget.app_instance.current_tags = current_tags
            else:
                miracle_input_widget.app_instance.image_removed_tags[actual_image_path] = removed_list
                # 현재 표시 이미지면 UI 반영
                if actual_image_path == miracle_input_widget.app_instance.current_image:
                    miracle_input_widget.app_instance.removed_tags = removed_list

        # all_tags 업데이트 - all_tags 관리 플러그인 사용
        from all_tags_manager import set_tags_for_image
        set_tags_for_image(miracle_input_widget.app_instance, actual_image_path, current_tags)
        print(f"✨ Miracle Manager Single: 최종 태그 - {current_tags}")

        # ── 타임머신: 통합 변경 기록 (커밋은 카드 생성 시점에 수행) ──
        if TM is not None:
            try:
                TM.log_change({
                    "type": "miracle_single_comprehensive",
                    "image": actual_image_path,
                    "before": before_tags_snapshot,
                    "after": list(current_tags),
                    "add": list(add_tags),
                    "delete": list(dilet_tags),
                    "delete_from": delete_from,  # 원래 위치 정보 추가
                    "renames": list(tag_renames),
                    "moves": list(tag_moves),
                    "add_count": len(add_tags),
                    "delete_count": len(dilet_tags),
                    "rename_count": len(tag_renames),
                    "moves_count": len(tag_moves),
                })
                try:
                    pending_change = TM._local._tm_tx_stack[-1]["changes"][-1]
                except Exception:
                    pending_change = None
                setattr(miracle_input_widget, '_tm_pending_miracle_tx', True)
                setattr(miracle_input_widget, '_tm_pending_miracle_mode', 'single')
                if pending_change is not None:
                    setattr(miracle_input_widget, '_tm_pending_miracle_change', pending_change)
            except Exception:
                try:
                    TM.abort()
                except Exception:
                    pass

        # UI 업데이트
        miracle_input_widget.app_instance.update_tag_stats()
        if hasattr(miracle_input_widget.app_instance, "tag_stylesheet_editor") and miracle_input_widget.app_instance.tag_stylesheet_editor:
            miracle_input_widget.app_instance.tag_stylesheet_editor.schedule_update()
        if hasattr(miracle_input_widget.app_instance, "update_tag_tree"):
            miracle_input_widget.app_instance.update_tag_tree()
        
        # 현재 표시 중인 이미지와 같으면 UI 업데이트
        current_display_image = getattr(miracle_input_widget.app_instance, 'current_image', None)
        if current_display_image == actual_image_path:
            miracle_input_widget.app_instance.current_tags = current_tags
            if hasattr(miracle_input_widget.app_instance, 'update_current_tags_display'):
                miracle_input_widget.app_instance.update_current_tags_display()
                print(f"✨ Miracle Manager Single: 현재 표시 이미지 UI 업데이트")
        
        print(f"✨ Miracle Manager Single: 단일 작업 UI 반영 완료")
        
    except Exception as e:
        print(f"✨ Miracle Manager Single: UI 반영 중 오류 - {e}")
        import traceback
        traceback.print_exc()
        # ── 타임머신: 오류 시 롤백 ──
        try:
            from timemachine_log import TM as _TM2
            _TM2.abort()
        except Exception:
            pass


def apply_tags_to_single_image(miracle_input_widget, image_path, add_tags, dilet_tags):
    """단일 이미지에 태그 적용 - 질문 시점의 이미지 경로 사용 (타임머신 로그 없음)"""
    try:
        # 질문 시점에 저장된 이미지 경로가 있으면 그것을 사용
        if hasattr(miracle_input_widget, '_question_time_image_path') and miracle_input_widget._question_time_image_path:
            actual_image_path = miracle_input_widget._question_time_image_path
            print(f"✨ Miracle Manager Single: 질문 시점 이미지 사용 - {actual_image_path}")
        else:
            actual_image_path = image_path
            print(f"✨ Miracle Manager Single: 전달받은 이미지 사용 - {actual_image_path}")
        
        # all_tags에서 직접 태그를 추가/삭제 (배치 로직과 동일)
        if not hasattr(miracle_input_widget.app_instance, 'all_tags'):
            miracle_input_widget.app_instance.all_tags = {}
        
        if actual_image_path not in miracle_input_widget.app_instance.all_tags:
            miracle_input_widget.app_instance.all_tags[actual_image_path] = []
        
        current_tags = list(miracle_input_widget.app_instance.all_tags[actual_image_path])
        print(f"✨ Miracle Manager Single: 현재 태그 - {current_tags}")

        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨

        for tag in add_tags:
            # 태그 추가 전에 global_tag_stats에 카테고리 정보 설정
            if tag not in miracle_input_widget.app_instance.global_tag_stats:
                try:
                    from danbooru_module import get_danbooru_category
                    category = get_danbooru_category(tag)
                    if category:
                        # 카테고리 정보가 있으면 딕셔너리 형태로 저장 (danbooru 카테고리)
                        miracle_input_widget.app_instance.global_tag_stats[tag] = {
                            'image_count': 0,
                            'category': category
                        }
                        print(f"✨ Miracle Manager Single: 태그 카테고리 설정 - {tag} → {category} (danbooru)")
                    else:
                        # 카테고리 정보가 없으면 unknown으로 설정
                        miracle_input_widget.app_instance.global_tag_stats[tag] = {
                            'image_count': 0,
                            'category': 'unknown'
                        }
                        print(f"✨ Miracle Manager Single: 태그 카테고리 설정 - {tag} → unknown")
                except ImportError:
                    # danbooru_module을 임포트할 수 없으면 unknown으로 설정
                    miracle_input_widget.app_instance.global_tag_stats[tag] = {
                        'image_count': 0,
                        'category': 'unknown'
                    }
            
            # all_tags에 직접 추가 (배치 로직과 동일)
            if tag not in current_tags:
                current_tags.append(tag)
                print(f"✨ Miracle Manager Single: 태그 추가 - {tag}")
                
                # global_tag_stats 업데이트
                if isinstance(miracle_input_widget.app_instance.global_tag_stats.get(tag), dict):
                    miracle_input_widget.app_instance.global_tag_stats[tag]['image_count'] += 1
                elif tag in miracle_input_widget.app_instance.global_tag_stats:
                    miracle_input_widget.app_instance.global_tag_stats[tag] += 1
                else:
                    miracle_input_widget.app_instance.global_tag_stats[tag] = 1
            
            # 태그 통계 모듈의 캐시 업데이트 (기존 캐시가 없는 경우에만 used로 설정)
            if hasattr(miracle_input_widget.app_instance, 'tag_statistics_module'):
                if hasattr(miracle_input_widget.app_instance.tag_statistics_module, '_cached_categories'):
                    cache = miracle_input_widget.app_instance.tag_statistics_module._cached_categories
                    # 기존 캐시가 없는 경우에만 used로 설정 (WD/LLaVA 태그는 유지)
                    if tag not in cache:
                        cache[tag] = 'used'
                        print(f"✨ Miracle Manager Single: 태그 캐시 업데이트 - {tag} → used")
                    else:
                        print(f"✨ Miracle Manager Single: 태그 캐시 유지 - {tag} → {cache[tag]}")
            
            # manual_tag_info 업데이트
            if hasattr(miracle_input_widget.app_instance, 'manual_tag_info'):
                if tag not in miracle_input_widget.app_instance.manual_tag_info:
                    miracle_input_widget.app_instance.manual_tag_info[tag] = False

        for tag in dilet_tags:
            if tag in current_tags:
                current_tags.remove(tag)
                print(f"✨ Miracle Manager Single: 태그 삭제 - {tag}")
                
                # 글로벌 태그 관리 플러그인 사용
                from global_tag_manager import remove_global_tag
                remove_global_tag(miracle_input_widget.app_instance, tag)
        
        # all_tags 업데이트 - all_tags 관리 플러그인 사용
        from all_tags_manager import set_tags_for_image
        set_tags_for_image(miracle_input_widget.app_instance, actual_image_path, current_tags)
        print(f"✨ Miracle Manager Single: 최종 태그 - {current_tags}")

        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨

        miracle_input_widget.app_instance.update_tag_stats()
        if hasattr(miracle_input_widget.app_instance, "tag_stylesheet_editor") and miracle_input_widget.app_instance.tag_stylesheet_editor:
            miracle_input_widget.app_instance.tag_stylesheet_editor.schedule_update()
        if hasattr(miracle_input_widget.app_instance, "update_tag_tree"):
            miracle_input_widget.app_instance.update_tag_tree()
        
        # 배치 모드처럼 현재 표시 이미지와 상관없이 태그 파일에 저장 (이미 all_tags에 반영됨)
        # 만약 현재 표시 중인 이미지가 처리한 이미지와 같다면 UI도 업데이트
        current_display_image = getattr(miracle_input_widget.app_instance, 'current_image', None)
        if current_display_image == actual_image_path:
            miracle_input_widget.app_instance.current_tags = current_tags
            if hasattr(miracle_input_widget.app_instance, 'update_current_tags_display'):
                miracle_input_widget.app_instance.update_current_tags_display()
                print(f"✨ Miracle Manager Single: 현재 표시 이미지 UI 업데이트")
            
            # ⭐ 태그 트리도 즉시 업데이트
            if hasattr(miracle_input_widget.app_instance, 'update_tag_tree'):
                miracle_input_widget.app_instance.update_tag_tree()
                print(f"✨ Miracle Manager Single: 태그 트리 즉시 업데이트")

    except Exception as e:
        print(f"✨ Miracle Manager Single: 단일 이미지 태그 적용 중 오류 - {e}")
        import traceback
        traceback.print_exc()
        # 타임머신 로그는 apply_miracle_tags_to_ui에서 통합 처리됨


def get_current_image_path(miracle_input_widget):
    """현재 이미지 경로 가져오기"""
    try:
        if hasattr(miracle_input_widget.app_instance, 'current_image_path'):
            return miracle_input_widget.app_instance.current_image_path
        
        if hasattr(miracle_input_widget.app_instance, 'current_image'):
            return miracle_input_widget.app_instance.current_image
        
        if hasattr(miracle_input_widget.app_instance, 'image_tagging_module'):
            tagging_module = miracle_input_widget.app_instance.image_tagging_module
            if hasattr(tagging_module, 'current_image_path'):
                return tagging_module.current_image_path
        
        target_images = get_current_grid_images(miracle_input_widget)
        if target_images:
            return target_images[0]
        
        return None
        
    except Exception as e:
        print(f"✨ Miracle Manager Single: 현재 이미지 경로 가져오기 중 오류 - {e}")
        return None


def get_current_image_name(miracle_input_widget):
    """현재 이미지의 파일명 가져오기"""
    try:
        current_image_path = get_current_image_path(miracle_input_widget)
        if current_image_path:
            from pathlib import Path
            image_name = Path(current_image_path).name
            return image_name
        
        target_images = get_current_grid_images(miracle_input_widget)
        if target_images and len(target_images) > 0:
            from pathlib import Path
            image_name = Path(target_images[0]).name
            return image_name
        
        return "unknown_image"
        
    except Exception as e:
        print(f"이미지 이름 가져오기 중 오류: {e}")
        return "unknown_image"


def interpret_natural_language_with_ai(miracle_input_widget, command, is_batch_mode=False, target_images=None):
    """자연어 명령어를 AI 모델로 해석 - 단일 작업만"""
    try:
        # 현재 선택된 단일 이미지 경로 가져오기 (질문 시점에 고정)
        current_image_path = get_current_image_path(miracle_input_widget)
        if current_image_path:
            miracle_input_widget._question_time_image_path = current_image_path
            print(f"✨ Miracle Manager Single: AI 질문 시점 이미지 저장 - {current_image_path}")
        
        current_tags = get_current_image_tags(miracle_input_widget)
        if target_images is None:
            target_images = get_current_grid_images(miracle_input_widget)
        
        # 현재 이미지의 액티브/리무버 태그 분리
        current_image_path = get_current_image_path(miracle_input_widget)
        active_tags = current_tags
        removed_tags = miracle_input_widget.app_instance.image_removed_tags.get(current_image_path, []) if hasattr(miracle_input_widget.app_instance, 'image_removed_tags') and current_image_path else []
        
        mode_info = "개별 처리 모드"
        prompt = f"""
사용자 명령어: "{command}"

현재 이미지의 액티브 태그: {active_tags}
현재 이미지의 리무버 태그: {removed_tags}
타겟 이미지 수: {len(target_images)}
처리 모드: {mode_info}

태그 구성 방식 설명:
- 각 태그는 "태그명{{위치,카테고리}}" 형식으로 표시됩니다
- 위치: 태그의 현재 순서 (1부터 시작)
- 카테고리: 태그의 분류 (text_typ, other_su, backgrou, framing 등)
- 예시: "english text{{1,text_typ}}" = 1번째 위치의 text_typ 카테고리 태그

중요: 명령어를 작성할 때는 괄호 안의 위치와 카테고리 정보를 포함하지 마세요.
- 올바른 예시: "english text::up", "no humans::down2"
- 잘못된 예시: "english text{{1,text_typ}}::up", "no humans{{2,other_su}}::down2"

위 정보를 바탕으로 사용자의 명령어에 대해 자연스럽고 자유롭게 답변해주세요. 사용자가 명령어로 지시하면 되묻지 말고 최선의 작업을 수행하세요.

중요한 규칙:
1. 자연어 답변은 순수하게 자연어로만 작성하세요 (add::, dilet::, tags:: 형식 포함하지 말 것)
2. 태그 조작이 필요한 경우에만 답변과 별도로 다음 형식을 추가하세요:
   - 태그 삭제: dilet::tag1,tag2 (완전 삭제 - 명확한 삭제 요청시에만 사용)
   - 새 태그 추가: add::tag1,tag2,tag3
   - 태그 토글: toggle::tag1,tag2 (액티브 ↔ 리무버 필드 전환)
   - 태그 위치 조작: up1::tag1, down1::tag2, up3::tag3, down2::tag4
   - 태그 이름 변경: old_name::change new_name
3. 태그는 반드시 영어로만 작성하세요
4. 자연어 답변과 태그 형식은 분리해서 작성하세요
4-1. 응답 구조: 자연어 설명 → 빈 줄 → 명령어 (순서 고정)
5. 사용자가 지시가 없다면 커맨드 명령을 사용하지 마세요
6. 자연어 답변은 자연스럽게 작성하세요 (현재형, 미래형, 과거형 모두 적절히 사용)
7. 사용자가 지시한 행동 이외에 다른 작업을 수행하지 마세요
8. 다만, 실제로 태그를 편집/추가/삭제한 경우에만 그 부분에 대해서는 과거형으로 설명하세요 (예: "태그를 추가했습니다", "순서를 조정했습니다")
9. 태그 조작을 수행한 경우, 이미지 설명과 별개로 반드시 수행한 태그 작업을 빠짐없이 명시하세요:
   - 추가: "다음 태그들을 추가했습니다: beautiful landscape, nature, sunset"
   - 삭제: "다음 태그들을 삭제했습니다: old_tag, unnecessary_tag"
   - 이동: "beautiful을 2칸 앞으로 이동하고, nature를 1칸 뒤로 이동했습니다"
   - 수정: "old_tag를 new_tag로 변경했습니다"
   - 복합 작업: "beautiful, nature를 추가하고, old_tag를 삭제하며, sunset을 1칸 앞으로 이동했습니다"
   - 중요: 커맨드 문(add::, dilet:: 등)은 사용자에게 보이지 않으므로, 자연어 답변에서 정확히 어떤 태그를 어떻게 조작했는지 구체적으로 설명하세요

태그 위치 조작 가이드:
- up1::태그명 = 태그를 1칸 앞으로 이동
- up3::태그명 = 태그를 3칸 앞으로 이동  
- down1::태그명 = 태그를 1칸 뒤로 이동
- down2::태그명 = 태그를 2칸 뒤로 이동
- 숫자는 원하는 만큼 지정 가능 (up5, down10 등)

태그 이름 변경 가이드:
- old_name::change new_name = 태그 이름을 old_name에서 new_name으로 변경

태그 필드 설명:
- 액티브 필드: 실제 사용될 태그들 (이미지에 적용됨)
- 리무버 필드: 사용 보류된 태그들 (이미지에 적용되지 않음)

태그 토글 가이드:
- toggle::tag1,tag2 = 액티브 태그를 리무버로 이동하거나 리무버 태그를 액티브로 이동
- 사용자가 "태그를 지워달라"고 할 때는 가급적 toggle 명령어로 필드만 전환
- 액티브 → 리무버: 태그를 사용 보류 상태로 변경
- 리무버 → 액티브: 태그를 다시 사용 가능 상태로 변경

태그 삭제 가이드:
- dilet::tag1,tag2 = 태그를 완전히 삭제 (되돌릴 수 없음)
- 사용 조건:
  - 사용자가 명확하게 "액티브 필드나 리무버 필드의 태그를 지워달라"고 요청한 경우
  - 또는 삭제를 요청하는 태그가 이미 리무버 필드에 있는 경우
- 일반적인 "지워달라" 요청은 toggle 명령어 사용 권장

예시 (올바른 순서):
- 태그 추가 적용 예시 → "이 이미지는 ~해서 이런 태그를 적용했습니다.\\n\\nadd::tag1,tag2,tag3"
- 태그 삭제 적용 예시 → "이 태그는 ~한 이유로 정리했습니다.\\n\\ndilet::tag1,tag2"
- 태그 토글 적용 예시 → "이 태그들을 토글했습니다.\\n\\ntoggle::tag1,tag2"
- 태그 순서 조정 적용 예시 → "태그 순서를 ~한 근거로 이렇게 조정했습니다.\\n\\nup1::tag1, down2::tag2"
- 태그 이름 변경 적용 예시 → "명확성을 위해 이름을 이렇게 바꿨습니다.\\n\\nold_tag::change new_tag"

잘못된 예시 (파싱 실패):
- "add::tag1,tag2\\n\\n이 이미지는 ~해서 이런 태그를 적용했습니다." ❌

추가 규칙:
- 엔터 사용시 가독성을 위해 두 번씩 사용할 것
- 빈 명령어 사용 금지: 실제 이동이나 변경이 없는 명령어(add::, dilet::, up, down 등)는 사용하지 말 것. 사용자는 명령어가 제거된 답변을 받기 때문에 명령어를 직접 설명하지 말 것
"""
        
        # 단일 이미지 처리
        ai_response = call_google_ai_api_with_image(miracle_input_widget, prompt, target_images)
        return ai_response
        
    except Exception as e:
        print(f"AI 해석 중 오류: {e}")
        return None


def postprocess_ai_response_for_batch_display(miracle_input_widget, text, image_paths):
    """UI 표시용 후처리"""
    try:
        if not text:
            return text
        return text
    except Exception as e:
        print(f"✨ Miracle Manager Single: AI 응답 표시 후처리 오류 - {e}")
        return text


def call_google_ai_api_with_image(miracle_input_widget, prompt, image_paths):
    """이미지를 포함한 Google AI API 호출"""
    try:
        import requests
        import json
        import base64
        from pathlib import Path
        
        # Google API 키는 설정에서 가져오기 (매번 새로 로드)
        api_key = None
        try:
            if hasattr(miracle_input_widget, 'miracle_settings') and miracle_input_widget.miracle_settings:
                # get_active_api_key()가 내부에서 load_config()를 호출하여 매번 새로 읽음
                api_key = miracle_input_widget.miracle_settings.get_active_api_key()
                print(f"✨ Miracle Manager Single: 설정 파일에서 API 키 로드 완료")
        except Exception as e:
            print(f"✨ Miracle Manager Single: 설정 로드 오류 - {e}")
        
        if not api_key:
            print("✨ Miracle Manager Single: API 키 없음 - 설정에서 API 키를 추가하세요")
            return "⚠️ Google AI API 키가 설정되지 않았습니다.\n\n미라클 설정 (⚙️ 버튼)에서 API 키를 추가해주세요."
        
        print(f"✨ Miracle Manager Single: API 키 사용 - {api_key[:10]}...")
        
        # 모델명을 설정에서 가져오기
        model_name = "gemini-2.5-flash"  # 기본값
        try:
            if hasattr(miracle_input_widget, 'miracle_settings') and miracle_input_widget.miracle_settings:
                model_name = miracle_input_widget.miracle_settings.get_selected_model()
                print(f"✨ Miracle Manager Single: 선택된 모델 - {model_name}")
        except Exception as e:
            print(f"✨ Miracle Manager Single: 모델 설정 로드 오류 - {e}")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        headers = {"Content-Type": "application/json"}
        
        # 질문 시점에 저장된 이미지 경로가 있으면 그것을 사용
        if hasattr(miracle_input_widget, '_question_time_image_path') and miracle_input_widget._question_time_image_path:
            image_path = miracle_input_widget._question_time_image_path
            print(f"✨ Miracle Manager Single: 질문 시점 이미지 사용 (API 전송) - {image_path}")
        elif image_paths and len(image_paths) > 0:
            image_path = image_paths[0]
            print(f"✨ Miracle Manager Single: 전달받은 이미지 사용 (API 전송) - {image_path}")
        else:
            image_path = None
        
        if image_path:
            print(f"✨ Miracle Manager Single: 이미지 로드 시도 - {image_path}")
            
            try:
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                
                image_ext = Path(image_path).suffix.lower()
                if image_ext in ['.jpg', '.jpeg']:
                    mime_type = "image/jpeg"
                elif image_ext == '.png':
                    mime_type = "image/png"
                elif image_ext == '.gif':
                    mime_type = "image/gif"
                elif image_ext == '.webp':
                    mime_type = "image/webp"
                else:
                    mime_type = "image/jpeg"
                
                data = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": image_data
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95,
                    }
                }
                
            except Exception as e:
                print(f"✨ Miracle Manager Single: 이미지 로드 실패 - {e}")
                data = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95,
                    }
                }
        else:
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                }
            }
        
        # 503 에러 재시도 로직 (최대 API 키 개수만큼 시도, 무한 루프 방지)
        max_retries = len(miracle_input_widget.miracle_settings.api_keys) if hasattr(miracle_input_widget, 'miracle_settings') and miracle_input_widget.miracle_settings else 1
        tried_keys = set()  # 이미 시도한 키 추적 (무한 루프 방지)
        
        for retry_count in range(max_retries):
            # 이미 시도한 키면 건너뛰기
            if api_key in tried_keys:
                print(f"⚠️ Miracle Manager Single: 이미 시도한 키, 종료")
                break
            
            tried_keys.add(api_key)
            api_url = f"{url}?key={api_key}"
            
            print(f"✨ Miracle Manager Single: API 요청 시도 {retry_count + 1}/{max_retries} - {api_key[:10]}...")
            
            try:
                response = requests.post(api_url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        ai_text = result['candidates'][0]['content']['parts'][0]['text']
                        print(f"✅ Miracle Manager Single: Google AI 응답 성공")
                        return ai_text
                    else:
                        print("⚠️ Miracle Manager Single: Google AI 응답이 비어있음")
                        return None
                
                elif response.status_code == 503:
                    # 503 에러: 과부하 - 다음 API 키로 재시도
                    error_detail = ""
                    try:
                        error_json = response.json()
                        error_detail = f" - {error_json.get('error', {}).get('message', '')}"
                    except:
                        pass
                    
                    print(f"⚠️ Miracle Manager Single: 503 과부하 에러{error_detail}")
                    
                    # 마지막 시도가 아니면 다음 키로 재시도
                    if retry_count < max_retries - 1:
                        if hasattr(miracle_input_widget, 'miracle_settings') and miracle_input_widget.miracle_settings:
                            next_key = miracle_input_widget.miracle_settings.get_next_api_key(api_key)
                            if not next_key or next_key == api_key:
                                print("⚠️ Miracle Manager Single: 사용 가능한 다른 API 키 없음")
                                return f"⚠️ API 과부하 에러 (503)\n\n모든 API 키가 과부하 상태입니다.\n잠시 후 다시 시도해주세요.{error_detail}"
                            api_key = next_key
                            print(f"🔄 Miracle Manager Single: 다음 API 키로 재시도 - {api_key[:10]}...")
                            import time
                            time.sleep(1)  # 1초 대기 후 재시도
                        else:
                            break
                    else:
                        print("❌ Miracle Manager Single: 모든 API 키 시도 실패 (503 에러)")
                        return f"⚠️ API 과부하 에러 (503)\n\n모든 API 키({max_retries}개)가 과부하 상태입니다.\n잠시 후 다시 시도해주세요."
                
                else:
                    # 다른 에러는 즉시 반환
                    error_msg = f"Google AI API 오류 ({response.status_code})"
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('error', {}).get('message', response.text[:200])
                        error_msg += f"\n\n{error_detail}"
                    except:
                        error_msg += f"\n\n{response.text[:200]}"
                    
                    print(f"❌ Miracle Manager Single: {error_msg}")
                    return f"⚠️ {error_msg}"
            
            except requests.exceptions.Timeout:
                print(f"⚠️ Miracle Manager Single: 요청 타임아웃 (30초)")
                return "⚠️ API 요청 타임아웃\n\n30초 내에 응답이 없습니다."
            
            except Exception as e:
                print(f"❌ Miracle Manager Single: 요청 중 예외 발생 - {e}")
                return f"⚠️ 요청 중 오류 발생\n\n{str(e)}"
        
        # 모든 재시도 실패
        return f"⚠️ 모든 API 키 시도 실패\n\n{max_retries}개 키 모두 실패했습니다."
            
    except Exception as e:
        import traceback
        print(f"✨ Miracle Manager Single: Google AI API 호출 중 오류 - {e}")
        print(f"✨ Miracle Manager Single: 오류 상세 정보: {traceback.format_exc()}")
        return None


def get_current_image_tags(miracle_input_widget):
    """현재 이미지의 태그들 가져오기"""
    try:
        current_tags = []
        
        if hasattr(miracle_input_widget.app_instance, 'current_tags'):
            if miracle_input_widget.app_instance.current_tags:
                for idx, tag in enumerate(miracle_input_widget.app_instance.current_tags, 1):
                    category = "unknown"
                    
                    try:
                        from kr_danbooru_loader import KRDanbooruLoader
                        kr_loader = KRDanbooruLoader()
                        kr_category = kr_loader.get_tag_category(tag)
                        if kr_category:
                            category = kr_category
                            print(f"✨ Miracle Manager Single: 태그 '{tag}' KR danbooru 카테고리 = {category}")
                        else:
                            print(f"✨ Miracle Manager Single: 태그 '{tag}' KR danbooru 카테고리 없음 → unknown")
                    except ImportError as e:
                        print(f"✨ Miracle Manager Single: kr_danbooru_loader 임포트 실패 - {e}")
                    except Exception as e:
                        print(f"✨ Miracle Manager Single: 태그 '{tag}' 카테고리 조회 오류 - {e}")
                    
                    current_tags.append(f"{tag}{{{idx},{category}}}")
        
        if hasattr(miracle_input_widget.app_instance, 'current_image_path') and miracle_input_widget.app_instance.current_image_path:
            image_path = miracle_input_widget.app_instance.current_image_path
            
            if hasattr(miracle_input_widget.app_instance, 'image_tagging_module'):
                img_module = miracle_input_widget.app_instance.image_tagging_module
                if hasattr(img_module, 'get_image_tags'):
                    image_specific_tags = img_module.get_image_tags(image_path)
                    if image_specific_tags:
                        current_tags.extend(image_specific_tags)
        
        current_tags = list(dict.fromkeys(current_tags))
        return current_tags
        
    except Exception as e:
        print(f"현재 이미지 태그 수집 중 오류: {e}")
    return []

