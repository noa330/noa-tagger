# -*- coding: utf-8 -*-
"""
Miracle Manager Batch Module - 배치 작업 로직 전용 모듈
"""

from PySide6.QtCore import QObject, Signal
from pathlib import Path
import re
import time



class BatchWorker(QObject):
    """배치 워커 (해석 전용 - QThread에서 실행)"""
    progress = Signal(dict)   # {"chunk": [...], "ai_resp": str, "tag_renames": list}
    finished = Signal()

    def __init__(self, command, target_images, batch_size, parent_mi):
        super().__init__()
        self.command = command
        self.target_images = list(target_images)
        self.batch_size = max(2, int(batch_size))
        self.mi = parent_mi  # MiracleTagInput 인스턴스 (interpret 호출용)

    def run(self):
        total = len(self.target_images)
        start = 0
        batch_num = 0
        
        while start < total:
            batch_num += 1
            end = min(start + self.batch_size, total)
            chunk = self.target_images[start:end]
            
            print(f"✨ BatchWorker: 배치 {batch_num} 처리 중 ({start+1}~{end}/{total}) - {len(chunk)}개 이미지")
            
            try:
                # API 키 순환은 call_google_ai_api_with_multiple_images에서 처리됨
                ai_resp = self.mi.interpret_natural_language_with_ai(self.command, True, chunk)
                err_msg = None
                
                if ai_resp and ai_resp.startswith("⚠️"):
                    # 오류 메시지가 반환된 경우
                    err_msg = ai_resp
                    ai_resp = None
                    print(f"⚠️ BatchWorker: 배치 {batch_num} API 오류 - {err_msg[:100]}")
                elif ai_resp:
                    print(f"✅ BatchWorker: 배치 {batch_num} 성공")
                else:
                    err_msg = "AI 응답이 비어있습니다"
                    print(f"⚠️ BatchWorker: 배치 {batch_num} 응답 없음")
                    
            except Exception as e:
                ai_resp = None
                err_msg = str(e)
                print(f"❌ BatchWorker: 배치 {batch_num} 예외 발생 - {e}")
            
            tag_renames = []
            self.progress.emit({
                "chunk": chunk,
                "ai_resp": ai_resp,
                "tag_renames": tag_renames,
                "error": err_msg,
                "batch_num": batch_num
            })
            start = end
        
        print(f"✅ BatchWorker: 모든 배치 완료 ({batch_num}개 배치)")
        self.finished.emit()


def on_batch_progress(miracle_input_widget, data: dict):
    """배치 프로그레스 수신 슬롯 (메인 스레드 UI 반영)"""
    try:
        chunk = data.get("chunk") or []
        ai_resp = data.get("ai_resp")
        tag_renames = data.get("tag_renames") or []
        error_msg = data.get("error")
        batch_num = data.get("batch_num", 0)
        
        # 이전 배치 응답이 다음 매핑에 섞이지 않도록 반드시 초기화
        miracle_input_widget.ai_response_message = ""

        # 에러가 발생한 경우, miracle_manager에 실패 정보 추적
        if error_msg:
            try:
                mm = getattr(miracle_input_widget.app_instance, 'miracle_manager', None)
                if mm:
                    # _failed_batch_info 초기화 (첫 배치 시작 시)
                    if not hasattr(mm, '_failed_batch_info') or mm._failed_batch_info is None:
                        mm._failed_batch_info = {
                            'command': '',
                            'batch_size': getattr(miracle_input_widget, 'get_batch_size', lambda: 10)(),
                            'failed_images': []
                        }
                    
                    # 실패한 청크 정보 저장
                    mm._failed_batch_info['failed_images'].append({
                        'chunk': list(chunk),
                        'error': error_msg,
                        'batch_num': batch_num
                    })
                    print(f"⚠️ Miracle Manager: 배치 {batch_num} 실패 추적 - {len(chunk)}개 이미지")
            except Exception as e:
                print(f"실패 정보 추적 중 오류: {e}")

        tm_pending = False
        pending_change = None

        if ai_resp:
            miracle_input_widget.ai_response_message = ai_resp
            try:
                miracle_input_widget.ai_response_message_display = postprocess_ai_response_for_batch_display(miracle_input_widget, ai_resp, chunk)
            except Exception:
                miracle_input_widget.ai_response_message_display = ai_resp
            try:
                # 현재 배치 응답만 즉시 표시 (누적/세션 파싱 없이)
                display_entry = getattr(miracle_input_widget, 'ai_response_message_display', ai_resp)
                if hasattr(miracle_input_widget.app_instance, 'miracle_manager'):
                    mm = miracle_input_widget.app_instance.miracle_manager
                    # 배치 응답 카드: 초록색 윤곽선
                    try:
                        mm._current_response_border = "#22c55e"  # green-500
                    except Exception:
                        pass

                    try:
                        apply_tags_to_multiple_images(miracle_input_widget, chunk, [], [], tag_renames)
                        tm_pending = getattr(miracle_input_widget, '_tm_pending_miracle_tx', False)
                        pending_change = getattr(miracle_input_widget, '_tm_pending_miracle_change', None)
                    except Exception as apply_err:
                        print(f"✨ Miracle Manager Batch: 태그 적용 중 오류 - {apply_err}")
                        tm_pending = getattr(miracle_input_widget, '_tm_pending_miracle_tx', False)
                        pending_change = getattr(miracle_input_widget, '_tm_pending_miracle_change', None)

                    if hasattr(mm, 'update_right_response'):
                        card_id = mm.update_right_response(str(display_entry), defer_tm_commit=tm_pending)
                        if card_id:
                            setattr(miracle_input_widget, "_last_response_card_id", card_id)
                            if pending_change is not None:
                                pending_change["card_id"] = card_id
                        if pending_change is not None:
                            pending_change.setdefault("card_text", str(display_entry))

                    if tm_pending:
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
            except Exception:
                pass
        else:
            # 응답이 없으면 에러 카드 표시 (현재 청크 파일명 포함)
            error_msg = data.get("error")
            try:
                if error_msg and hasattr(miracle_input_widget.app_instance, 'miracle_manager'):
                    import os as _os
                    names = [str(_os.path.basename(str(p))) for p in (chunk or [])]
                    preview = ", ".join(names[:5])
                    more = f" (+{len(names)-5} more)" if len(names) > 5 else ""
                    display_entry = f"[ERROR] {error_msg}\nTargets: {preview}{more}"
                    mm = miracle_input_widget.app_instance.miracle_manager
                    # 배치 에러 카드도 초록 윤곽선 유지
                    try:
                        mm._current_response_border = "#22c55e"
                    except Exception:
                        pass
                    if hasattr(mm, 'update_right_response'):
                        # update_right_response에서 카드 ID 생성 및 타임머신 로그 기록
                        card_id = mm.update_right_response(display_entry)
                        if card_id:
                            setattr(miracle_input_widget, "_last_response_card_id", card_id)
                # 이전 트랜잭션 잔여물이 있다면 정리
                for attr in ('_tm_pending_miracle_tx', '_tm_pending_miracle_change', '_tm_pending_miracle_mode'):
                    if hasattr(miracle_input_widget, attr):
                        delattr(miracle_input_widget, attr)
            except Exception:
                pass
            # 응답이 없는 배치는 태그 적용 스킵
            try:
                if hasattr(miracle_input_widget, 'increment_miracle_progress'):
                    miracle_input_widget.increment_miracle_progress(len(chunk or []))
            except Exception as prog_err:
                print(f"[MiracleProgress] 에러 진행 갱신 실패: {prog_err}")
            return

        # ⭐ 현재 이미지가 처리된 청크에 포함되어 있으면 태그 트리 업데이트
        current_image = getattr(miracle_input_widget.app_instance, 'current_image', None)
        if current_image and current_image in chunk:
            if hasattr(miracle_input_widget.app_instance, 'update_tag_tree'):
                miracle_input_widget.app_instance.update_tag_tree()
                print(f"✨ Miracle Manager Batch: 현재 이미지 태그 트리 업데이트")

        # 한 박자 쉬어 주기 (리페인트)
        try:
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
        except Exception:
            pass
    except Exception as e:
        print(f"✨ on_batch_progress 오류 - {e}")


def on_batch_finished(miracle_input_widget):
    """배치 종료 슬롯 (최종 스냅샷/트리 재갱신)"""
    try:
        # 현재 이미지의 태그를 all_tags에서 강제로 갱신 (배치 처리 후 동기화)
        try:
            current_image = getattr(miracle_input_widget.app_instance, 'current_image', None)
            if current_image and current_image in miracle_input_widget.app_instance.all_tags:
                miracle_input_widget.app_instance.current_tags = list(miracle_input_widget.app_instance.all_tags[current_image])
                print(f"✨ Miracle Manager Batch: 배치 종료 후 현재 이미지 태그 동기화 완료 - {len(miracle_input_widget.app_instance.current_tags)}개 태그")
        except Exception as e:
            print(f"✨ Miracle Manager Batch: 현재 이미지 태그 동기화 실패 - {e}")
        
        if hasattr(miracle_input_widget.app_instance, 'update_tag_stats'):
            miracle_input_widget.app_instance.update_tag_stats()
        if hasattr(miracle_input_widget.app_instance, 'update_tag_tree'):
            miracle_input_widget.app_instance.update_tag_tree()
        if hasattr(miracle_input_widget.app_instance, 'update_current_tags_display'):
            miracle_input_widget.app_instance.update_current_tags_display()
        miracle_input_widget.miracle_tag_input.clear()
        miracle_input_widget.miracle_tag_input.setEnabled(True)
        miracle_input_widget.miracle_tag_input.setPlaceholderText("미라클 명령어를 입력하세요...")
        try:
            miracle_input_widget.apply_outline_styles()
        except Exception:
            pass
        miracle_input_widget.hide_loading_indicator()
        if hasattr(miracle_input_widget, 'batch_thread'):
            miracle_input_widget.batch_thread.quit()
            miracle_input_widget.batch_thread.wait(3000)
            if miracle_input_widget.batch_thread.isRunning():
                miracle_input_widget.batch_thread.terminate()
                miracle_input_widget.batch_thread.wait(1000)
        if hasattr(miracle_input_widget, '_miracle_busy'):
            miracle_input_widget._miracle_busy = False
        
        # 실패한 이미지가 있으면 재시도 버튼 추가
        try:
            mm = getattr(miracle_input_widget.app_instance, 'miracle_manager', None)
            if mm and hasattr(mm, '_failed_batch_info') and mm._failed_batch_info:
                failed_images_list = mm._failed_batch_info.get('failed_images', [])
                if failed_images_list:
                    # command 정보 설정 (배치 워커에서 사용한 명령어)
                    if hasattr(miracle_input_widget, 'batch_worker') and miracle_input_widget.batch_worker:
                        mm._failed_batch_info['command'] = miracle_input_widget.batch_worker.command
                    
                    # 재시도 버튼 추가
                    mm.add_retry_button_if_needed()
                    print(f"✨ Miracle Manager: 재시도 버튼 추가 요청 - {len(failed_images_list)}개 배치 실패")
        except Exception as e:
            print(f"재시도 버튼 추가 중 오류: {e}")
        
        print("✨ Miracle Manager: 일괄 모드 완료 (배치별 표시)")
        try:
            if hasattr(miracle_input_widget, 'complete_miracle_progress'):
                miracle_input_widget.complete_miracle_progress()
        except Exception as prog_err:
            print(f"[MiracleProgress] 완료 처리 실패: {prog_err}")
    except Exception as e:
        print(f"✨ on_batch_finished 오류 - {e}")
        try:
            if hasattr(miracle_input_widget, 'complete_miracle_progress'):
                miracle_input_widget.complete_miracle_progress()
        except Exception as prog_err:
            print(f"[MiracleProgress] 완료 처리(예외) 실패: {prog_err}")


def apply_tags_to_multiple_images(miracle_input_widget, image_paths, add_tags, dilet_tags, tag_renames=None):
    """다중 이미지에 태그 적용 - 각 이미지별로 다른 태그 적용"""
    try:
        print(f"✨ Miracle Manager Batch: 일괄 모드 시작 - {len(image_paths)}개 이미지 처리")
        # ── 타임머신: 일괄 작업을 1개의 트랜잭션으로 묶기 ──
        TM = None
        try:
            from timemachine_log import TM as _TM
            TM = _TM
        except Exception:
            TM = None
        if TM is not None:
            TM.begin("batch apply", context={
                "source": "miracle_batch",
                "num_images": len(image_paths),
            })
            # 배치 작업 시작을 로그로 기록
            TM.log_change({
                "type": "miracle_batch_apply",
                "num_images": len(image_paths),
                "batch_size": miracle_input_widget.get_batch_size() if hasattr(miracle_input_widget, 'get_batch_size') else 10,
            })
            try:
                pending_change = TM._local._tm_tx_stack[-1]["changes"][-1]
            except Exception:
                pending_change = None
            setattr(miracle_input_widget, '_tm_pending_miracle_tx', True)
            setattr(miracle_input_widget, '_tm_pending_miracle_mode', 'batch')
            if pending_change is not None:
                setattr(miracle_input_widget, '_tm_pending_miracle_change', pending_change)
        
        # AI 응답에서 각 이미지별 태그 매핑 생성
        image_tag_mapping = create_image_tag_mapping(miracle_input_widget, image_paths, add_tags, dilet_tags)
        
        for i, image_path in enumerate(image_paths, 1):
            print(f"✨ Miracle Manager Batch: 이미지 {i}/{len(image_paths)} 처리 중 - {image_path}")
            
            # 이 이미지 전용 태그 가져오기
            image_add_tags = image_tag_mapping.get(f"{i}.png", {}).get("add", [])
            image_dilet_tags = image_tag_mapping.get(f"{i}.png", {}).get("dilet", [])
            image_toggle_tags = image_tag_mapping.get(f"{i}.png", {}).get("toggle", [])
            
            print(f"✨ Miracle Manager Batch: 이미지 {i} - add: {len(image_add_tags)}개, dilet: {len(image_dilet_tags)}개, toggle: {len(image_toggle_tags)}개")
            
            # 각 이미지에 직접 태그 적용 (all_tags에 직접 저장)
            try:
                # all_tags 딕셔너리에 이미지 키가 없으면 생성 - all_tags 관리 플러그인 사용
                from all_tags_manager import get_tags_for_image
                if not get_tags_for_image(miracle_input_widget.app_instance, image_path):
                    from all_tags_manager import set_tags_for_image
                    set_tags_for_image(miracle_input_widget.app_instance, image_path, [])
                
                # 기존 태그 가져오기 (순서 보존)
                existing_list = list(miracle_input_widget.app_instance.all_tags.get(image_path, []))
                new_list = existing_list[:]
                
                # 리무버 리스트 미리 정의 (모든 처리에서 공통 사용)
                removed = miracle_input_widget.app_instance.image_removed_tags.setdefault(image_path, [])

                # 토글 처리 (dilet/add 처리 전에 먼저 실행)
                for t in image_toggle_tags:
                    if t in new_list:
                        # 액티브에 있으면 → 리무버로 이동
                        # 타임머신 로그 기록
                        try:
                            from timemachine_log import TM
                            TM.log_change({
                                "type": "tag_toggle_off",
                                "image": image_path,
                                "tag": t,
                            })
                        except Exception:
                            pass
                        
                        # 1. 액티브에서 제거
                        new_list.remove(t)
                        # 2. 리무버에 추가
                        miracle_input_widget.app_instance.image_removed_tags.setdefault(image_path, [])
                        if t not in miracle_input_widget.app_instance.image_removed_tags[image_path]:
                            miracle_input_widget.app_instance.image_removed_tags[image_path].append(t)
                        # 3. UI 동기화 (현재 표시 이미지일 때만)
                        if miracle_input_widget.app_instance.current_image == image_path:
                            if t not in miracle_input_widget.app_instance.removed_tags:
                                miracle_input_widget.app_instance.removed_tags.append(t)
                        print(f"✨ Miracle Manager Batch: 토글 (액티브→리무버) - {t}")
                    elif t in miracle_input_widget.app_instance.image_removed_tags.get(image_path, []):
                        # 리무버에 있으면 → 액티브로 이동
                        # 타임머신 로그 기록
                        try:
                            from timemachine_log import TM
                            TM.log_change({
                                "type": "tag_toggle_on",
                                "image": image_path,
                                "tag": t,
                            })
                        except Exception:
                            pass
                        
                        # 1. 리무버에서 제거
                        miracle_input_widget.app_instance.image_removed_tags[image_path].remove(t)
                        # 2. 액티브에 추가
                        new_list.append(t)
                        # 3. UI 동기화 (현재 표시 이미지일 때만)
                        if miracle_input_widget.app_instance.current_image == image_path:
                            if t in miracle_input_widget.app_instance.removed_tags:
                                miracle_input_widget.app_instance.removed_tags.remove(t)
                        print(f"✨ Miracle Manager Batch: 토글 (리무버→액티브) - {t}")
                    else:
                        print(f"✨ Miracle Manager Batch: 토글 대상 태그 없음 - {t}")

                # 삭제 (완전 삭제) - 원래 위치 정보 수집
                delete_from = {}  # 원래 위치 정보 저장
                for t in image_dilet_tags:
                    if t in new_list:
                        # 액티브에서 완전 삭제
                        delete_from[t] = "active"  # 원래 위치 기록
                        new_list.remove(t)
                        # 개별 로깅 추가 (타임머신 복원용)
                        if TM is not None:
                            try:
                                TM.log_change({
                                    "type": "batch_tag_delete",
                                    "image": image_path,
                                    "tag": t,
                                    "target_type": "active",
                                })
                            except Exception:
                                pass
                        print(f"✨ Miracle Manager Batch: 액티브에서 완전 삭제 - {t}")
                    elif t in removed:
                        # 리무버에서 완전 삭제
                        delete_from[t] = "removed"  # 원래 위치 기록
                        removed.remove(t)
                        # 개별 로깅 추가 (타임머신 복원용)
                        if TM is not None:
                            try:
                                TM.log_change({
                                    "type": "batch_tag_delete",
                                    "image": image_path,
                                    "tag": t,
                                    "target_type": "removed",
                                })
                            except Exception:
                                pass
                        # 현재 표시 이미지라면 app.removed_tags에서도 제거
                        if miracle_input_widget.app_instance.current_image == image_path:
                            if t in miracle_input_widget.app_instance.removed_tags:
                                miracle_input_widget.app_instance.removed_tags.remove(t)
                        print(f"✨ Miracle Manager Batch: 리무버에서 완전 삭제 - {t}")

                # 추가 (뒤에 append, 이미 있으면 패스)
                for t in image_add_tags:
                    if t not in new_list:
                        new_list.append(t)
                        # ✅ 개별 로깅 추가 (타임머신 복원용)
                        if TM is not None:
                            try:
                                TM.log_change({
                                    "type": "batch_tag_add",
                                    "image": image_path,
                                    "tag": t,
                                })
                            except Exception:
                                pass

                # 리네임(이미지별 → old 자리 유지)
                try:
                    image_map = image_tag_mapping.get(f"{i}.png", {}) if 'image_tag_mapping' in locals() else {}
                    per_image_renames = (image_map.get("renames") or []) if image_map else []
                    _renames = per_image_renames or (tag_renames or [])
                    
                    for r in _renames:
                        old = str(r.get('from','')).strip().strip('\'"[](){}')
                        new = str(r.get('to','')).strip().strip('\'"[](){}')
                        if not old or not new or old == new:
                            continue
                        
                        # 대상 리스트 결정
                        if old in new_list:
                            target_list = new_list
                            target_type = 'active'
                        elif old in removed:
                            target_list = removed
                            target_type = 'removed'
                        else:
                            continue
                        
                        old_idx = target_list.index(old)
                        
                        # 중복 처리: 새 이름이 반대 필드에 있으면 반대 필드에서 제거
                        if target_type == 'active' and new in removed:
                            removed.remove(new)
                            print(f"✨ Miracle Manager Batch: 리무버에서 중복 제거 - {new}")
                        elif target_type == 'removed' and new in new_list:
                            new_list.remove(new)
                            print(f"✨ Miracle Manager Batch: 액티브에서 중복 제거 - {new}")
                        
                        # 같은 리스트 내 중복 처리
                        if new in target_list:
                            new_idx = target_list.index(new)
                            target_list.pop(new_idx)
                            if new_idx < old_idx:
                                old_idx -= 1
                        
                        target_list[old_idx] = new
                        
                        # 개별 로깅 추가 (타임머신 복원용)
                        if TM is not None:
                            try:
                                TM.log_change({
                                    "type": "batch_tag_rename",
                                    "image": image_path,
                                    "old_tag": old,
                                    "new_tag": new,
                                    "target_type": target_type,
                                })
                            except Exception:
                                pass
                        
                        # manual_tag_info 옮기기 (old 태그의 used/trigger 정보를 new 태그로 이전)
                        if hasattr(miracle_input_widget.app_instance, 'manual_tag_info'):
                            if old in miracle_input_widget.app_instance.manual_tag_info:
                                is_trigger = miracle_input_widget.app_instance.manual_tag_info[old]
                                miracle_input_widget.app_instance.manual_tag_info[new] = is_trigger
                                del miracle_input_widget.app_instance.manual_tag_info[old]
                                print(f"✨ Miracle Manager Batch: manual_tag_info 이전 - {old} → {new} ({'trigger' if is_trigger else 'used'})")
                                
                                # 태그 통계 모듈의 캐시도 업데이트
                                if hasattr(miracle_input_widget.app_instance, 'tag_statistics_module'):
                                    if hasattr(miracle_input_widget.app_instance.tag_statistics_module, '_cached_categories'):
                                            cache = miracle_input_widget.app_instance.tag_statistics_module._cached_categories
                                            if old in cache:
                                                cache[new] = cache[old]
                                                del cache[old]
                                            else:
                                                cache[new] = 'trigger' if is_trigger else 'used'
                                            print(f"✨ Miracle Manager Batch: 태그 캐시 업데이트 - {old} → {new}")
                            
                            # 통계 반영 및 카테고리 정보 유지
                            # 글로벌 태그 관리 플러그인 사용
                            from global_tag_manager import edit_global_tag
                            edit_global_tag(miracle_input_widget.app_instance, old, new)
                except Exception as _e:
                    print(f"✨ Miracle Manager Batch: (일괄) rename 적용 실패 - {_e}")

                # per-image moves from mapping
                try:
                    image_map = image_tag_mapping.get(f"{i}.png", {}) if 'image_tag_mapping' in locals() else {}
                    per_image_moves = (image_map.get("moves") or []) if image_map else []
                    if per_image_moves:
                        print(f"✨ Miracle Manager Batch: 이미지 {i} - moves {len(per_image_moves)}개 적용")
                    for mv in per_image_moves:
                        tag_name = mv.get('tag')
                        direction = mv.get('direction')
                        steps = int(mv.get('steps') or 1)
                        
                        # 대상 리스트 결정
                        if tag_name in new_list:
                            target_list = new_list
                            target_type = 'active'
                        elif tag_name in removed:
                            target_list = removed
                            target_type = 'removed'
                        else:
                            print(f"✨ Miracle Manager Batch: move 대상 '{tag_name}' 없음 - skip")
                            continue
                        
                        cur_idx = target_list.index(tag_name)
                        new_idx = cur_idx
                        if direction == 'up':
                            new_idx = max(0, cur_idx - steps)
                        elif direction == 'down':
                            new_idx = min(len(target_list) - 1, cur_idx + steps)
                        if new_idx != cur_idx:
                            tag_val = target_list.pop(cur_idx)
                            target_list.insert(new_idx, tag_val)
                            print(f"✨ Miracle Manager Batch: '{tag_name}' {direction} {steps}칸 이동 - {cur_idx} → {new_idx} ({target_type})")
                            
                            # 개별 로깅 추가 (타임머신 복원용)
                            if TM is not None:
                                try:
                                    TM.log_change({
                                        "type": "batch_tag_move",
                                        "image": image_path,
                                        "tag": tag_name,
                                        "direction": direction,
                                        "steps": steps,
                                        "from_index": cur_idx,
                                        "to_index": new_idx,
                                        "target_type": target_type,
                                    })
                                except Exception:
                                    pass
                            
                            # 리무버 태그 이동시 UI 동기화
                            if target_type == 'removed' and miracle_input_widget.app_instance.current_image == image_path:
                                if hasattr(miracle_input_widget.app_instance, 'removed_tags'):
                                    miracle_input_widget.app_instance.removed_tags = removed[:]
                        else:
                            print(f"✨ Miracle Manager Batch: '{tag_name}' 이동 불가 - 경계 초과")
                except Exception as __e:
                    print(f"✨ Miracle Manager Batch: (일괄) moves 적용 실패 - {__e}")

                # all_tags 업데이트 - all_tags 관리 플러그인 사용
                from all_tags_manager import set_tags_for_image
                set_tags_for_image(miracle_input_widget.app_instance, image_path, new_list)
                
                # 리무버 리스트 저장 (rename 처리 후 변경사항 반영)
                miracle_input_widget.app_instance.image_removed_tags[image_path] = removed
                
                # UI 동기화 (현재 표시 이미지인 경우)
                if miracle_input_widget.app_instance.current_image == image_path:
                    miracle_input_widget.app_instance.removed_tags = list(removed)
                    if hasattr(miracle_input_widget.app_instance, 'update_current_tags_display'):
                        miracle_input_widget.app_instance.update_current_tags_display()
                
                # ── 타임머신: 이미지별 변경 기록 ──
                # ❌ 스냅샷 로깅 제거: 개별 로깅(batch_tag_add/remove/rename/move)과 충돌하므로 주석 처리
                # 각 작업은 이미 개별적으로 로깅되었으므로 중복 불필요
                # if TM is not None:
                #     try:
                #         TM.log_change({
                #             "type": "batch_apply_per_image",
                #             "image": image_path,
                #             "before": existing_list,
                #             "after": new_list,
                #             "add": list(image_add_tags),
                #             "delete": list(image_dilet_tags),
                #             "renames": list(tag_renames or []),
                #         })
                #     except Exception:
                #         pass
                
                # global_tag_stats 업데이트 (추가된 태그만)
                for tag in image_add_tags:
                    if tag in miracle_input_widget.app_instance.global_tag_stats:
                        current_value = miracle_input_widget.app_instance.global_tag_stats[tag]
                        if isinstance(current_value, dict):
                            miracle_input_widget.app_instance.global_tag_stats[tag]['image_count'] += 1
                        else:
                            miracle_input_widget.app_instance.global_tag_stats[tag] += 1
                    else:
                        # 새로운 태그 추가 시 카테고리 정보 가져오기
                        if miracle_input_widget.app_instance.global_tag_stats and isinstance(next(iter(miracle_input_widget.app_instance.global_tag_stats.values())), dict):
                            try:
                                from danbooru_module import get_danbooru_category
                                category = get_danbooru_category(tag)
                                if category:
                                    miracle_input_widget.app_instance.global_tag_stats[tag] = {'image_count': 1, 'category': category}
                                    print(f"✨ Miracle Manager Batch: 태그 카테고리 설정 - {tag} → {category} (danbooru)")
                                else:
                                    miracle_input_widget.app_instance.global_tag_stats[tag] = {'image_count': 1, 'category': 'unknown'}
                                    print(f"✨ Miracle Manager Batch: 태그 카테고리 설정 - {tag} → unknown")
                            except ImportError:
                                miracle_input_widget.app_instance.global_tag_stats[tag] = {'image_count': 1, 'category': 'unknown'}
                        else:
                            miracle_input_widget.app_instance.global_tag_stats[tag] = 1
                    
                    # manual_tag_info에 추가 (미라클로 추가된 태그는 used로 표시)
                    if not hasattr(miracle_input_widget.app_instance, 'manual_tag_info'):
                        miracle_input_widget.app_instance.manual_tag_info = {}
                    miracle_input_widget.app_instance.manual_tag_info[tag] = False  # False = used (not trigger)
                    
                    # 태그 통계 모듈의 캐시 업데이트 (기존 캐시가 없는 경우에만 used로 설정)
                    if hasattr(miracle_input_widget.app_instance, 'tag_statistics_module'):
                        if hasattr(miracle_input_widget.app_instance.tag_statistics_module, '_cached_categories'):
                            cache = miracle_input_widget.app_instance.tag_statistics_module._cached_categories
                            # 기존 캐시가 없는 경우에만 used로 설정 (WD/LLaVA 태그는 유지)
                            if tag not in cache:
                                cache[tag] = 'used'
                                print(f"✨ Miracle Manager Batch: 태그 캐시 업데이트 - {tag} → used")
                            else:
                                print(f"✨ Miracle Manager Batch: 태그 캐시 유지 - {tag} → {cache[tag]}")
                    
                    print(f"✨ Miracle Manager Batch: 태그 추가 - {tag} (이미지 {i})")
                
                # global_tag_stats 업데이트 (삭제된 태그만)
                for tag in image_dilet_tags:
                    if tag in miracle_input_widget.app_instance.global_tag_stats:
                        current_value = miracle_input_widget.app_instance.global_tag_stats[tag]
                        if isinstance(current_value, dict):
                            # 글로벌 태그 관리 플러그인 사용
                            from global_tag_manager import remove_global_tag
                            remove_global_tag(miracle_input_widget.app_instance, tag)
                    print(f"✨ Miracle Manager Batch: 태그 삭제 - {tag} (이미지 {i})")
                
                print(f"✨ Miracle Manager Batch: 이미지 {i} 태그 적용 완료 - add: {len(image_add_tags)}개, dilet: {len(image_dilet_tags)}개")
                
                # 현재 선택된 이미지가 처리된 이미지라면 current_tags 업데이트
                current_image = getattr(miracle_input_widget.app_instance, 'current_image', None)
                if current_image == image_path:
                    print(f"✨ Miracle Manager Batch: 현재 이미지 태그 동기화 - {image_path}")
                    miracle_input_widget.app_instance.current_tags = list(new_list)
                    # removed_tags에서 추가된 태그들 제거 (다시 활성화)
                    for tag in image_add_tags:
                        if tag in miracle_input_widget.app_instance.removed_tags:
                            miracle_input_widget.app_instance.removed_tags.remove(tag)
                    # 삭제된 태그들은 removed_tags에 추가하지 않음 (all_tags에서만 제거)
                
            except Exception as e:
                print(f"✨ Miracle Manager Batch: 태그 적용 실패 - {e}")
            
            # 각 이미지 처리 후 즉시 UI 갱신
            print(f"✨ Miracle Manager Batch: 이미지 {i} 처리 완료 - UI 갱신 중...")
            miracle_input_widget.app_instance.update_tag_stats()
            if hasattr(miracle_input_widget.app_instance, "tag_stylesheet_editor") and miracle_input_widget.app_instance.tag_stylesheet_editor:
                miracle_input_widget.app_instance.tag_stylesheet_editor.schedule_update()
            if hasattr(miracle_input_widget.app_instance, "update_tag_tree"):
                miracle_input_widget.app_instance.update_tag_tree()
            
            try:
                if hasattr(miracle_input_widget, 'increment_miracle_progress'):
                    miracle_input_widget.increment_miracle_progress(1)
            except Exception as prog_err:
                print(f"[MiracleProgress] 배치 진행 갱신 실패: {prog_err}")

        # 타임머신 커밋은 카드 생성 시점에서 수행

    except Exception as e:
        print(f"✨ on_batch_finished 오류 - {e}")
        # ── 타임머신: 오류 시 롤백 ──
        if TM is not None:
            try:
                TM.abort()
            except Exception:
                pass


def create_image_tag_mapping(miracle_input_widget, image_paths, add_tags, dilet_tags):
    """AI 응답에서 각 이미지별 태그 매핑 생성"""
    try:
        # AI 응답 메시지에서 각 이미지별 태그 추출
        ai_response = getattr(miracle_input_widget, 'ai_response_message', '')
        print(f"✨ Miracle Manager Batch: AI 응답 메시지 확인 - 길이: {len(ai_response) if ai_response else 0}")
        if ai_response:
            preview = ai_response.replace("\n", "\\n")
            print(f"✨ Miracle Manager Batch: AI 응답 메시지 전체 - {preview}")
        
        if not ai_response:
            print("✨ Miracle Manager Batch: AI 응답 메시지가 없음 - 모든 태그를 첫 번째 이미지에 적용")
            return {f"{i}.png": {"add": add_tags, "dilet": dilet_tags} for i in range(1, len(image_paths) + 1)}
        
        mapping = {}
        
        # 대괄호로 구분된 각 이미지 응답 파싱
        pattern = r'\[([^&]+)&([^\]]+)\]'
        matches = re.findall(pattern, ai_response, re.DOTALL)
        
        print(f"✨ Miracle Manager Batch: 정규식 매칭 결과 - {len(matches)}개 매칭")
        if matches:
            for i, (filename, content) in enumerate(matches, 1):
                print(f"✨ Miracle Manager Batch: 정규식 매칭 {i} - {filename}: {content}")
        
        # 대괄호가 제대로 매칭되지 않은 경우 수동으로 파싱
        if not matches:
            print("✨ Miracle Manager Batch: 정규식 매칭 실패 - 수동 파싱 시도")
            # 여는 대괄호와 닫는 대괄호를 찾아서 수동으로 파싱
            start_pos = 0
            while True:
                open_pos = ai_response.find('[', start_pos)
                if open_pos == -1:
                    break
                
                # 닫는 대괄호 찾기 (여는 대괄호 이후부터)
                close_pos = ai_response.find(']', open_pos + 1)
                if close_pos == -1:
                    # 닫는 대괄호가 없으면 문자열 끝까지 사용
                    close_pos = len(ai_response)
                    print(f"✨ Miracle Manager Batch: 닫는 대괄호 없음 - 문자열 끝까지 사용")
                
                # 대괄호 안의 내용 추출
                content = ai_response[open_pos + 1:close_pos]
                
                # & 구분자로 파일명과 내용 분리
                if '&' in content:
                    filename, content = content.split('&', 1)
                    filename = filename.strip()
                    content = content.strip()
                    matches.append((filename, content))
                    print(f"✨ Miracle Manager Batch: 수동 파싱 성공 - {filename}")
                    print(f"✨ Miracle Manager Batch: 파싱된 내용 - {content}")
                
                start_pos = close_pos + 1
            
            # 대괄호가 전혀 없는 경우 - 파일명 패턴으로 분리
            if not matches:
                print("✨ Miracle Manager Batch: 대괄호 없음 - 파일명 패턴으로 분리 시도")
                # 1.png, 2.png 등의 패턴으로 분리
                import re as re_module
                # 파일명 패턴: 숫자.확장자 또는 숫자.png 등
                file_pattern = r'(\d+\.(?:png|jpg|jpeg|webp|gif))'
                parts = re_module.split(ai_response, file_pattern)
                
                current_filename = None
                current_content = ""
                for part in parts:
                    if re_module.match(file_pattern, part):
                        # 이전 내용 저장
                        if current_filename and current_content.strip():
                            matches.append((current_filename, current_content.strip()))
                            print(f"✨ Miracle Manager Batch: 파일명 패턴 파싱 성공 - {current_filename}")
                        current_filename = part
                        current_content = ""
                    else:
                        current_content += part
                
                # 마지막 내용 저장
                if current_filename and current_content.strip():
                    matches.append((current_filename, current_content.strip()))
                    print(f"✨ Miracle Manager Batch: 파일명 패턴 파싱 성공 - {current_filename}")
        
        print(f"✨ Miracle Manager Batch: AI 응답에서 {len(matches)}개 이미지 응답 발견")
        
        # AI 응답 순서대로 매핑 (AI가 1.png, 2.png, 3.png, 4.png 순서로 응답)
        for i, (filename, content) in enumerate(matches, 1):
            filename = filename.strip()
            
            print(f"✨ Miracle Manager Batch: 이미지 {filename} 태그 매핑 생성 중...")
            
            # 각 이미지 응답에서 add::, dilet::, tags::, toggle:: 패턴 추출
            add_pattern = r'add::\s*([^:]+?)(?=\s+dilet::|\s+tags::|\s+toggle::|$)'
            dilet_pattern = r'dilet::\s*([^:]+?)(?=\s+add::|\s+tags::|\s+toggle::|$)'
            tags_pattern = r'tags::\s*([^:]+?)(?=\s+add::|\s+dilet::|\s+toggle::|\s+tags::|$)'
            toggle_pattern = r'toggle::\s*([^:]+?)(?=\s+add::|\s+dilet::|\s+tags::|\s+toggle::|$)'
            
            add_matches_local = re.findall(add_pattern, content, re.IGNORECASE | re.DOTALL)
            dilet_matches_local = re.findall(dilet_pattern, content, re.IGNORECASE | re.DOTALL)
            tags_matches_local = re.findall(tags_pattern, content, re.IGNORECASE | re.DOTALL)
            toggle_matches_local = re.findall(toggle_pattern, content, re.IGNORECASE | re.DOTALL)
            
            # tags::는 add::로 취급
            image_add_tags = []
            for match in add_matches_local + tags_matches_local:
                tags = [tag.strip() for tag in match.split(',') if tag.strip()]
                image_add_tags.extend(tags)
            
            image_dilet_tags = []
            for match in dilet_matches_local:
                tags = [tag.strip() for tag in match.split(',') if tag.strip()]
                image_dilet_tags.extend(tags)
            
            image_toggle_tags = []
            for match in toggle_matches_local:
                tags = [tag.strip() for tag in match.split(',') if tag.strip()]
                image_toggle_tags.extend(tags)
            
            # rename 패턴 추출
            renames_for_image = []
            rn_matches = re.findall(r'(?mi)^\s*"?(.+?)"?\s*::\s*change\s+"?(.+?)"?\s*$', content)
            for _o, _n in rn_matches:
                _o = _o.strip().strip('\'"[](){}')
                _n = _n.strip().strip('\'"[](){}')
                renames_for_image.append({'from': _o, 'to': _n})
            
            # move 패턴 추출
            moves_for_image = []
            mv_matches = re.findall(r'(?mi)\b(up|down)(\d*)::\s*(.+)', content)
            for _dir, _steps, _tag in mv_matches:
                moves_for_image.append({
                    'tag': _tag.strip().strip('\'"[](){}'),
                    'direction': _dir.lower(),
                    'steps': int(_steps) if _steps else 1
                })
            
            # AI 응답 순서대로 매핑 (1.png = 첫 번째 이미지, 2.png = 두 번째 이미지...)
            mapping[f"{i}.png"] = {
                "add": image_add_tags,
                "dilet": image_dilet_tags,
                "toggle": image_toggle_tags,
                "renames": renames_for_image,
                "moves": moves_for_image
            }
            
            print(f"✨ Miracle Manager Batch: {i}.png (AI 응답 순서) - add: {len(image_add_tags)}개, dilet: {len(image_dilet_tags)}개")
        
        return mapping
        
    except Exception as e:
        print(f"✨ Miracle Manager Batch: 이미지 태그 매핑 생성 중 오류 - {e}")
        return {f"{i}.png": {"add": add_tags, "dilet": dilet_tags} for i in range(1, len(image_paths) + 1)}


def _build_simple_to_actual_name_map(image_paths):
    """일괄 모드에서 사용한 임시 파일명(1.png 등) → 실제 파일명 매핑 생성"""
    try:
        mapping = {}
        if not image_paths:
            return mapping
        for i, p in enumerate(image_paths, 1):
            actual = Path(p).name  # 실제 파일명 (확장자 포함)
            for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                mapping[f"{i}{ext}"] = actual
            # 숫자만 온 경우도 대비
            mapping[str(i)] = actual
        return mapping
    except Exception as e:
        print(f"✨ Miracle Manager Batch: 파일명 매핑 생성 실패 - {e}")
        return {}


def postprocess_ai_response_for_batch_display(miracle_input_widget, text, image_paths):
    """
    UI 카드 '표시' 전용 후처리:
    - [1.png& ...] → [원본파일명]\n...  (본문/뒷내용 그대로)
    - 두 번째 이미지 헤더부터는 앞에 줄바꿈 2개 추가
    - 섹션 헤더의 임시 파일명은 실제 원본 파일명(확장자 제거)으로 치환
    """
    try:
        if not text:
            return text
        name_map = _build_simple_to_actual_name_map(image_paths)

        def _clean_name(fname: str) -> str:
            # 매핑 우선, 없으면 자체 확장자만 제거
            actual = name_map.get(fname.strip())
            if actual:
                return Path(actual).stem
            return Path(fname.strip()).stem

        # '[' 다음부터 첫 '&' 전까지 = 파일명 헤더만 매칭
        pattern = r'\[([^\]\uFF06&]+)(?:&|\uFF06)'

        counter = {'i': 0}
        def repl(m):
            counter['i'] += 1
            left = m.group(1)
            safe_left = _clean_name(left)

            if counter['i'] == 1:
                # 첫 번째 헤더
                before = text[:m.start()]
                has_non_ws_before = any((not ch.isspace()) for ch in before)
                if has_non_ws_before:
                    if before.endswith("\n"):
                        prefix = "\u200B\n\u200B\n"
                    else:
                        prefix = "\n\u200B\n\u200B\n"
                else:
                    prefix = ""
            else:
                # 두 번째 헤더부터
                prefix = "\n\u200B\n"

            return f"{prefix}[{safe_left}]\n"

        return re.sub(pattern, repl, text)
    except Exception as e:
        print(f"✨ Miracle Manager Batch: AI 응답 표시 후처리 오류 - {e}")
        return text


def call_google_ai_api_with_multiple_images(miracle_input_widget, prompt, image_paths):
    """다중 이미지를 포함한 Google AI API 호출"""
    try:
        import requests
        import json
        import base64
        
        # Google API 키는 설정에서 가져오기 (매번 새로 로드)
        api_key = None
        try:
            if hasattr(miracle_input_widget, 'miracle_settings') and miracle_input_widget.miracle_settings:
                # get_active_api_key()가 내부에서 load_config()를 호출하여 매번 새로 읽음
                api_key = miracle_input_widget.miracle_settings.get_active_api_key()
                print(f"✨ Miracle Manager Batch: 설정 파일에서 API 키 로드 완료")
        except Exception as e:
            print(f"✨ Miracle Manager Batch: 설정 로드 오류 - {e}")
        
        if not api_key:
            print("✨ Miracle Manager Batch: API 키 없음 - 설정에서 API 키를 추가하세요")
            return "⚠️ Google AI API 키가 설정되지 않았습니다.\n\n미라클 설정 (⚙️ 버튼)에서 API 키를 추가해주세요."
        
        print(f"✨ Miracle Manager Batch: API 키 사용 - {api_key[:10]}...")
        
        # Google AI API 엔드포인트
        # 모델명을 설정에서 가져오기
        model_name = "gemini-2.5-flash"  # 기본값
        try:
            if hasattr(miracle_input_widget, 'miracle_settings') and miracle_input_widget.miracle_settings:
                model_name = miracle_input_widget.miracle_settings.get_selected_model()
                print(f"✨ Miracle Manager Batch: 선택된 모델 - {model_name}")
        except Exception as e:
            print(f"✨ Miracle Manager Batch: 모델 설정 로드 오류 - {e}")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # 다중 이미지 처리용 프롬프트 수정
        file_mapping = {}
        simple_file_names = []
        for i, image_path in enumerate(image_paths, 1):
            actual_name = Path(image_path).name
            simple_name = f"{i}.png"
            file_mapping[simple_name] = actual_name
            simple_file_names.append(simple_name)
        
        file_list = ", ".join(simple_file_names[:5])
        if len(simple_file_names) > 5:
            file_list += f" 등 총 {len(simple_file_names)}개"
        
        # 투입된 PNG 리스트 생성
        png_list = "\n".join([f"{i}. {simple_name}" for i, simple_name in enumerate(simple_file_names, 1)])
        
        # 각 이미지의 현재 태그 정보 수집 (액티브/리무버 분리)
        current_tags_info = []
        for i, image_path in enumerate(image_paths, 1):
            try:
                existing_tags = []
                if hasattr(miracle_input_widget.app_instance, 'all_tags') and image_path in miracle_input_widget.app_instance.all_tags:
                    existing_tags = miracle_input_widget.app_instance.all_tags[image_path]
                
                # 리무버 태그 가져오기
                removed_tags = []
                if hasattr(miracle_input_widget.app_instance, 'image_removed_tags') and image_path in miracle_input_widget.app_instance.image_removed_tags:
                    removed_tags = miracle_input_widget.app_instance.image_removed_tags[image_path]
                
                if existing_tags:
                    # 액티브 태그를 순서와 카테고리 포함해서 표시
                    active_tags_with_info = []
                    for idx, tag in enumerate(existing_tags, 1):
                        category = 'unknown'
                        
                        # KR danbooru 카테고리 직접 조회
                        try:
                            from kr_danbooru_loader import KRDanbooruLoader
                            kr_loader = KRDanbooruLoader()
                            kr_category = kr_loader.get_tag_category(tag)
                            if kr_category:
                                category = kr_category
                                print(f"✨ Miracle Manager Batch: 태그 '{tag}' KR danbooru 카테고리 = {category}")
                            else:
                                print(f"✨ Miracle Manager Batch: 태그 '{tag}' KR danbooru 카테고리 없음 → unknown")
                        except ImportError as e:
                            print(f"✨ Miracle Manager Batch: kr_danbooru_loader 임포트 실패 - {e}")
                        except Exception as e:
                            print(f"✨ Miracle Manager Batch: 태그 '{tag}' 카테고리 조회 오류 - {e}")
                        
                        active_tags_with_info.append(f"{tag}{{{idx},{category}}}")
                    
                    active_tags_str = ", ".join(active_tags_with_info)
                    removed_tags_str = ", ".join(removed_tags) if removed_tags else "(없음)"
                    current_tags_info.append(f"{i}.png:\n액티브: {active_tags_str}\n리무버: {removed_tags_str}")
                    print(f"✨ Miracle Manager Batch: {i}.png 현재 태그 - 액티브: {len(existing_tags)}개, 리무버: {len(removed_tags)}개")
                else:
                    removed_tags_str = ", ".join(removed_tags) if removed_tags else "(없음)"
                    current_tags_info.append(f"{i}.png:\n액티브: (태그 없음)\n리무버: {removed_tags_str}")
                    print(f"✨ Miracle Manager Batch: {i}.png 현재 태그 - 액티브: 없음, 리무버: {len(removed_tags)}개")
            except Exception as e:
                current_tags_info.append(f"{i}.png: (태그 로드 실패: {e})")
                print(f"✨ Miracle Manager Batch: {i}.png 태그 로드 실패 - {e}")
        
        current_tags_text = "\n".join(current_tags_info)
        
        multi_prompt = f"""
{prompt}

투입된 PNG 리스트:
{png_list}

각 이미지의 현재 태그:
{current_tags_text}

태그 구성 방식 설명:
- 각 태그는 "태그명{{위치,카테고리}}" 형식으로 표시됩니다
- 위치: 태그의 현재 순서 (1부터 시작)
- 카테고리: 태그의 분류 (text_typ, other_su, backgrou, framing 등)
- 예시: "english text{{1,text_typ}}" = 1번째 위치의 text_typ 카테고리 태그

중요: 명령어를 작성할 때는 괄호 안의 위치와 카테고리 정보를 포함하지 마세요.
- 올바른 예시: "english text::up", "no humans::down2"
- 잘못된 예시: "english text{{1,text_typ}}::up", "no humans{{2,other_su}}::down2"

위 정보를 바탕으로 사용자의 명령어에 대해 각 이미지별로 자연스럽고 자유롭게 답변해주세요. 사용자가 명령어로 지시하면 다시 묻지 말고 최선의 작업을 수행하세요.

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

**배치 모드 응답 형식 (반드시 준수):**
[1.png&자연어답변

add::tag1,tag2,tag3
dilet::tag4,tag5]
[2.png&자연어답변

add::tag6,tag7
dilet::tag8,tag9]

**중요: 각 이미지마다 반드시 대괄호 [ ]로 감싸서 응답하세요!**
**대괄호 없이 응답하면 태그가 적용되지 않습니다!**
**응답 구조: 자연어 설명 → 빈 줄 → 명령어 (순서 고정)!**

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

예시:
- 태그 추가 적용 예시 → [1.png&이 이미지는 ~해서 이런 태그를 적용했습니다.

add::tag1,tag2,tag3]
- 태그 삭제 적용 예시 → [2.png&이 태그는 ~한 이유로 정리했습니다.

dilet::tag1,tag2]
- 태그 토글 적용 예시 → [3.png&이 태그들을 토글했습니다.

toggle::tag1,tag2]
- 태그 순서 조정 적용 예시 → [4.png&태그 순서를 ~한 근거로 이렇게 조정했습니다.

up1::tag1
down2::tag2]
- 태그 이름 변경 적용 예시 → [5.png&명확성을 위해 이름을 이렇게 바꿨습니다.

old_tag::change new_tag]

추가 규칙:
- 엔터 사용시 가독성을 위해 두 번씩 사용할 것
- 빈 명령어 사용 금지: 실제 이동이나 변경이 없는 명령어(add::, dilet::, up, down 등)는 사용하지 말 것. 사용자는 명령어가 제거된 답변을 받기 때문에 명령어를 직접 설명하지 말 것
"""
        
        # 이미지 데이터 준비
        max_images = len(image_paths)
        parts = [{"text": multi_prompt}]
        
        print(f"✨ Miracle Manager Batch: 다중 이미지 처리 - 총 {max_images}개 처리")
        
        for i, image_path in enumerate(image_paths[:max_images], 1):
            try:
                simple_name = f"{i}.png"
                print(f"✨ Miracle Manager Batch: 다중 이미지 로드 시도 - {image_path} → {simple_name}")
                
                # 이미지를 base64로 인코딩
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                
                # 이미지 MIME 타입 결정
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
                
                parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_data
                    }
                })
                
            except Exception as e:
                print(f"✨ Miracle Manager Batch: 이미지 로드 실패 - {image_path}: {e}")
                continue
        
        if len(parts) == 1:
            print("✨ Miracle Manager Batch: 로드된 이미지가 없음 - 텍스트만으로 요청")
        
        data = {
            "contents": [{"parts": parts}],
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
                print(f"⚠️ Miracle Manager Batch: 이미 시도한 키, 종료")
                break
            
            tried_keys.add(api_key)
            api_url = f"{url}?key={api_key}"
            
            print(f"✨ Miracle Manager Batch: API 요청 시도 {retry_count + 1}/{max_retries} - {api_key[:10]}... (배치: {len(image_paths)}개 이미지)")
            
            try:
                response = requests.post(api_url, headers=headers, json=data, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        ai_text = result['candidates'][0]['content']['parts'][0]['text']
                        print(f"✅ Miracle Manager Batch: Google AI 응답 성공 (다중 이미지)")
                        return ai_text
                    else:
                        print("⚠️ Miracle Manager Batch: Google AI 응답이 비어있음")
                        return None
                
                elif response.status_code == 503:
                    # 503 에러: 과부하 - 다음 API 키로 재시도
                    error_detail = ""
                    try:
                        error_json = response.json()
                        error_detail = f" - {error_json.get('error', {}).get('message', '')}"
                        print(f"⚠️ Miracle Manager Batch: 오류 상세 - {error_json}")
                    except:
                        pass
                    
                    print(f"⚠️ Miracle Manager Batch: 503 과부하 에러{error_detail}")
                    
                    # 마지막 시도가 아니면 다음 키로 재시도
                    if retry_count < max_retries - 1:
                        if hasattr(miracle_input_widget, 'miracle_settings') and miracle_input_widget.miracle_settings:
                            next_key = miracle_input_widget.miracle_settings.get_next_api_key(api_key)
                            if not next_key or next_key == api_key:
                                print("⚠️ Miracle Manager Batch: 사용 가능한 다른 API 키 없음")
                                return f"⚠️ API 과부하 에러 (503)\n\n모든 API 키가 과부하 상태입니다.\n잠시 후 다시 시도해주세요.{error_detail}"
                            api_key = next_key
                            print(f"🔄 Miracle Manager Batch: 다음 API 키로 재시도 - {api_key[:10]}...")
                            import time
                            time.sleep(1)  # 1초 대기 후 재시도
                        else:
                            break
                    else:
                        print("❌ Miracle Manager Batch: 모든 API 키 시도 실패 (503 에러)")
                        return f"⚠️ API 과부하 에러 (503)\n\n모든 API 키({max_retries}개)가 과부하 상태입니다.\n잠시 후 다시 시도해주세요."
                
                else:
                    # 다른 에러는 즉시 반환
                    error_msg = f"Google AI API 오류 ({response.status_code})"
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('error', {}).get('message', response.text[:200])
                        error_msg += f"\n\n{error_detail}"
                        print(f"❌ Miracle Manager Batch: 오류 상세 - {error_json}")
                    except:
                        error_msg += f"\n\n{response.text[:200]}"
                    
                    print(f"❌ Miracle Manager Batch: {error_msg}")
                    return f"⚠️ {error_msg}"
            
            except requests.exceptions.Timeout:
                print(f"⚠️ Miracle Manager Batch: 요청 타임아웃 (60초)")
                return "⚠️ API 요청 타임아웃\n\n60초 내에 응답이 없습니다."
            
            except Exception as e:
                print(f"❌ Miracle Manager Batch: 요청 중 예외 발생 - {e}")
                return f"⚠️ 요청 중 오류 발생\n\n{str(e)}"
        
        # 모든 재시도 실패
        return f"⚠️ 모든 API 키 시도 실패\n\n{max_retries}개 키 모두 실패했습니다."
            
    except Exception as e:
        import traceback
        print(f"✨ Miracle Manager Batch: Google AI API 호출 중 오류 - {e}")
        print(f"✨ Miracle Manager Batch: 오류 상세 정보: {traceback.format_exc()}")
        return None


def parse_multi_image_response(ai_response, target_images):
    """다중 이미지 응답을 파싱하여 각 이미지별 태그 추출"""
    try:
        all_add_tags = []
        all_dilet_tags = []
        
        # 대괄호로 구분된 각 이미지 응답 파싱
        pattern = r'\[([^&]+)&([^\]]+)\]'
        matches = re.findall(pattern, ai_response, re.DOTALL)
        
        print(f"✨ Miracle Manager Batch: 다중 이미지 응답에서 {len(matches)}개 이미지 응답 발견")
        
        # 간단한 파일명 목록 생성
        simple_file_names = [f"{i}.png" for i in range(1, len(target_images) + 1)]
        
        for filename, content in matches:
            filename = filename.strip()
            print(f"✨ Miracle Manager Batch: 이미지 {filename} 응답 파싱 중...")
            
            if filename in simple_file_names:
                print(f"✨ Miracle Manager Batch: 간단 파일명 매칭 성공 - {filename}")
            else:
                print(f"✨ Miracle Manager Batch: 파일명 매칭 실패 - {filename}")
            
            # 각 이미지 응답에서 add::, dilet:: 패턴 추출
            add_pattern = r'add::\s*([^:]+?)(?=\s+dilet::|\s+tags::|$)'
            dilet_pattern = r'dilet::\s*([^:]+?)(?=\s+add::|\s+tags::|$)'
            tags_pattern = r'tags::\s*([^:]+?)(?=\s+add::|\s+dilet::|\s+tags::|$)'
            
            add_matches = re.findall(add_pattern, content, re.IGNORECASE | re.DOTALL)
            dilet_matches = re.findall(dilet_pattern, content, re.IGNORECASE | re.DOTALL)
            tags_matches = re.findall(tags_pattern, content, re.IGNORECASE | re.DOTALL)
            
            # tags::는 add::로 취급
            for match in add_matches + tags_matches:
                tags = [tag.strip() for tag in match.split(',') if tag.strip()]
                all_add_tags.extend(tags)
            
            for match in dilet_matches:
                tags = [tag.strip() for tag in match.split(',') if tag.strip()]
                all_dilet_tags.extend(tags)
            
            print(f"✨ Miracle Manager Batch: {filename} - add: {len(add_matches + tags_matches)}개, dilet: {len(dilet_matches)}개")
        
        # 중복 제거
        all_add_tags = list(set(all_add_tags))
        all_dilet_tags = list(set(all_dilet_tags))
        
        print(f"✨ Miracle Manager Batch: 전체 파싱 결과 - add: {len(all_add_tags)}개, dilet: {len(all_dilet_tags)}개")
        
        return all_add_tags, all_dilet_tags
        
    except Exception as e:
        print(f"✨ Miracle Manager Batch: 다중 이미지 응답 파싱 오류 - {e}")
        return [], []
