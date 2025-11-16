# -*- coding: utf-8 -*-
"""Time Machine Module - Per-Card Branch Navigation (LLM Chat Style)"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pathlib import Path

# TM log subscription
try:
    from timemachine_log import TM
except:
    TM = None


# ---- Bridge to ensure UI-thread updates --------------------------------------
class _TMBridge(QObject):
    # Emit log records; connected with Qt.QueuedConnection to marshal to UI thread
    record = Signal(dict)

# Design tokens
COLORS = {
    'link': "#0D6EFD",
    'card_bg': "#FBFCFD", 
    'card_bg_undone': "#F5F5F5",
    'card_border': "#E9EEF3",
    'text_dark': "#1A2833",
    'text_muted': "#6D7A88",
    'pill_red': "#F44336",
    'dot_blue': "#3BA5FF",
    'dot_gray': "#999999",
    'line_gray': "#E1E7EE",
    'btn_undo': "#4CAF50",
    'btn_redo': "#2196F3",
    'branch_bg': "rgba(17,17,27,0.5)",
    'tag_highlight': "#E8F4FD"
}

class TimeMachineButton(QPushButton):
    timemachine_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__("🕒", parent)
        self.setFixedSize(60, 50)
        self.setToolTip("Time Machine")
        self.setStyleSheet("""
            QPushButton {
                background: transparent; color: #CFD8DC; border: none;
                font-size: 18px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); color: #FFF; }
        """)
        self.clicked.connect(self.timemachine_clicked.emit)

# ──────────────────────────────────────────────────────────────────────────────
# Per-card branch navigator
# ──────────────────────────────────────────────────────────────────────────────
class CardBranchNavigator(QWidget):
    branch_changed = Signal(int, int)  # (record_index, branch_index)
    
    def __init__(self, record_index, branches_info, parent=None):
        super().__init__(parent)
        self.record_index = record_index
        self.branches_info = branches_info  # [(branch_idx, branch_name), ...]
        self.current_branch_index = 0
        
        if len(branches_info) <= 1:
            self.hide()
            return
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self.btn_prev = QPushButton("❮")
        self.btn_next = QPushButton("❯")
        for b in (self.btn_prev, self.btn_next):
            b.setFixedSize(20, 20)
            b.setStyleSheet("""
                QPushButton { 
                    background: transparent;
                    border: none;
                    color: #9CA3AF;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    color: #9CA3AF;
                }
                QPushButton:disabled {
                    color: #9CA3AF;
                }
            """)
        
        self.label = QLabel(f"1/{len(branches_info)}")
        self.label.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.label)
        layout.addWidget(self.btn_next)
        
        self.btn_prev.clicked.connect(self._go_prev)
        self.btn_next.clicked.connect(self._go_next)
        self._update_enabled()
    
    def set_current_branch(self, branch_idx):
        """Update which branch is currently shown"""
        for i, (bidx, _) in enumerate(self.branches_info):
            if bidx == branch_idx:
                self.current_branch_index = i
                self.label.setText(f"{i+1}/{len(self.branches_info)}")
                self._update_enabled()
                return
    
    def _go_prev(self):
        if self.current_branch_index > 0:
            self.current_branch_index -= 1
            self.label.setText(f"{self.current_branch_index+1}/{len(self.branches_info)}")
            self._update_enabled()
            branch_idx = self.branches_info[self.current_branch_index][0]
            self.branch_changed.emit(self.record_index, branch_idx)
    
    def _go_next(self):
        if self.current_branch_index < len(self.branches_info) - 1:
            self.current_branch_index += 1
            self.label.setText(f"{self.current_branch_index+1}/{len(self.branches_info)}")
            self._update_enabled()
            branch_idx = self.branches_info[self.current_branch_index][0]
            self.branch_changed.emit(self.record_index, branch_idx)
    
    def _update_enabled(self):
        self.btn_prev.setEnabled(self.current_branch_index > 0)
        self.btn_next.setEnabled(self.current_branch_index < len(self.branches_info) - 1)

class TimeMachine:
    def __init__(self, app_instance):
        self.app = app_instance
        self.is_timemachine_mode = False
        self.timemachine_card = None
        
        # ── Branch state ──────────────────────────────────────────────────────────────────
        self._branches = [{
            "records": [],
            "current_index": -1,
            "name": "main",
            "forked_from": None  # (parent_branch_idx, fork_point_record_idx)
        }]
        self._active_branch = 0  # Actually applied to data
        self._viewing_branch = 0  # Currently displayed in UI (can be different from active)
        
        # Back-compat aliases (point to VIEWING branch for UI display)
        self._timeline = self._branches[self._viewing_branch]["records"]
        self._current_index = self._branches[self._viewing_branch]["current_index"]
        # ──────────────────────────────────────────────────────────────────────────────────
        
                # Bridge TM -> UI thread
        self._bridge = _TMBridge()
        self._bridge.record.connect(self._on_tm_record, Qt.QueuedConnection)

        # Keep reference to bound method for unsubscribe safety
        self._tm_handler = self._ingest_from_tm

        if TM:
            try: 
                TM.subscribe(self._tm_handler)
                print(f"[TM DEBUG] 타임머신 구독 완료")
            except Exception as e:
                print(f"[TM ERROR] 타임머신 구독 실패: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[TM ERROR] TM 객체가 None입니다!")

    
    
    # Bridge ingest: called from TM publisher thread(s); forwards to UI thread safely.
    def _ingest_from_tm(self, record):
        try:
            print(f"[TM DEBUG] 로그 수신: {record.get('title', 'Unknown')} - {record.get('changes', [])}")
            # copy to decouple from any background mutations
            self._bridge.record.emit(dict(record))
        except Exception as e:
            print(f"[TM ERROR] 로그 수신 실패: {e}")
            import traceback
            traceback.print_exc()

# ── Branch helpers ────────────────────────────────────────────────────────────────────
    def _persist_branch_state(self):
        """Mirror alias vars back onto the VIEWING branch dict."""
        b = self._branches[self._viewing_branch]
        b["records"] = self._timeline
        b["current_index"] = self._current_index
    
    def _records_match(self, rec1, rec2):
        """Check if two records represent the same operation (same changes)"""
        changes1 = rec1.get("changes", [])
        changes2 = rec2.get("changes", [])
        
        if len(changes1) != len(changes2):
            print(f"[TM]     Length mismatch: {len(changes1)} vs {len(changes2)}")
            return False
        
        # Compare changes (simplified - you can make this more strict if needed)
        for i, (c1, c2) in enumerate(zip(changes1, changes2)):
            if c1.get("type") != c2.get("type"):
                print(f"[TM]     Change {i} type mismatch: {c1.get('type')} vs {c2.get('type')}")
                return False
            if c1.get("tag") != c2.get("tag"):
                print(f"[TM]     Change {i} tag mismatch: {c1.get('tag')} vs {c2.get('tag')}")
                return False
            if c1.get("image") != c2.get("image"):
                print(f"[TM]     Change {i} image mismatch: {c1.get('image')} vs {c2.get('image')}")
                return False
        
        print(f"[TM]     Records match!")
        return True
    
    def _get_branches_at_position(self, record_index):
        """
        Simple logic: Show branch navigator only at the exact fork point.
        When a branch was created, it was forked at a specific index.
        Only show navigator at that index.
        """
        result = []
        
        print(f"[TM] Checking fork points at position {record_index}")
        
        # Find all branches that forked at this exact position
        for bidx, branch in enumerate(self._branches):
            fork_info = branch.get("forked_from")
            if fork_info is None:
                # This is main branch
                if bidx == self._viewing_branch and record_index < len(branch["records"]):
                    result.append((bidx, branch["name"]))
                continue
            
            parent_idx, fork_point = fork_info
            
            # Check if this branch forked at current position
            if fork_point == record_index:
                # Include parent branch
                if parent_idx not in [r[0] for r in result]:
                    parent_branch = self._branches[parent_idx]
                    if record_index < len(parent_branch["records"]):
                        result.append((parent_idx, parent_branch["name"]))
                
                # Include this branch
                if record_index < len(branch["records"]):
                    result.append((bidx, branch["name"]))
                
                print(f"[TM]   Branch {bidx} ({branch['name']}) forked here from {parent_idx}")
        
        # Also check if current viewing branch is a parent of any forks at this position
        for bidx, branch in enumerate(self._branches):
            fork_info = branch.get("forked_from")
            if fork_info and fork_info[0] == self._viewing_branch and fork_info[1] == record_index:
                # Current branch is parent - include it
                if self._viewing_branch not in [r[0] for r in result]:
                    viewing_branch = self._branches[self._viewing_branch]
                    if record_index < len(viewing_branch["records"]):
                        result.append((self._viewing_branch, viewing_branch["name"]))
                # Include child
                if bidx not in [r[0] for r in result]:
                    if record_index < len(branch["records"]):
                        result.append((bidx, branch["name"]))
        
        print(f"[TM] Found {len(result)} branches at fork point {record_index}: {[b[1] for b in result]}")
        return result if len(result) > 1 else []
    
    def switch_to_branch_at_position(self, record_index, target_branch_idx):
        """
        Switch VIEWING branch only (read-only view).
        Does NOT change actual data - that happens only when user clicks Redo.
        """
        if target_branch_idx < 0 or target_branch_idx >= len(self._branches):
            return
        if target_branch_idx == self._viewing_branch:
            return
        
        print(f"[TM] Switching VIEW from branch {self._viewing_branch} to {target_branch_idx}")
        print(f"[TM] Active branch remains: {self._active_branch}")
        
        # Save current viewing state
        self._persist_branch_state()
        
        # Don't revert actual data - just switch viewing branch
        # The actual data should remain unchanged when switching branches
        
        # Switch viewing branch (UI only)
        self._viewing_branch = target_branch_idx
        self._timeline = self._branches[target_branch_idx]["records"]
        self._current_index = self._branches[target_branch_idx]["current_index"]
        
        # Rebuild entire UI to update all branch states
        if hasattr(self, "timeline_panel"):
            print(f"[TM] Rebuilding entire panel to update all branch states")
            self._rebuild_panel_with_branch_point(record_index)
        
        print(f"[TM] View switched. Viewing={self._viewing_branch}, Active={self._active_branch}")
    
    def _rebuild_panel_from_position(self, from_index):
        """Rebuild cards from a specific position downward (for branch switching)"""
        if not hasattr(self, "timeline_panel"):
            return
        
        # Remove cards from from_index onward
        self.timeline_panel.remove_cards_from(from_index)
        
        # Add cards from current branch starting at from_index
        for i in range(from_index, len(self._timeline)):
            self._add_to_panel(self._timeline[i], i)
        
        # Update all card states - 분기점 이전은 모두 활성화, 이후는 현재 분기 상태에 따라
        self.timeline_panel.update_states_with_branch_point(self._current_index, from_index)
    
    def _rebuild_panel(self):
        """Rebuild the entire panel for the VIEWING branch."""
        if not hasattr(self, "timeline_panel"):
            return
        self.timeline_panel.clear_cards()
        for i, rec in enumerate(self._timeline):
            self._add_to_panel(rec, i)
        
        # Use regular update_states for normal rebuild
        self.timeline_panel.update_states(self._current_index)
        print(f"[TM] Panel rebuilt for viewing branch {self._viewing_branch}")
    
    def _rebuild_panel_with_branch_point(self, branch_point):
        """Rebuild the entire panel considering branch point for correct state display."""
        if not hasattr(self, "timeline_panel"):
            return
        self.timeline_panel.clear_cards()
        for i, rec in enumerate(self._timeline):
            self._add_to_panel(rec, i)
        
        # Use update_states_with_branch_point for branch switching
        self.timeline_panel.update_states_with_branch_point(self._current_index, branch_point)
        print(f"[TM] Panel rebuilt with branch point {branch_point} for viewing branch {self._viewing_branch}")
    
    # ── UI toggling ───────────────────────────────────────────────────────────────────────
    def toggle_timemachine_mode(self):
        from center_panel_overlay_plugin import CenterPanelOverlayPlugin
        overlay = CenterPanelOverlayPlugin(self.app)
        
        if not self.timemachine_card:
            self.create_timemachine_card()
            self.app.timemachine_card = self.timemachine_card
        
        order_list = getattr(self.app, "_overlay_order", [])
        active = getattr(self.app, "_overlay_active_type", None)
        
        if "timemachine" not in order_list or active != "timemachine":
            # 타임머신 열 때 항상 현재 활성 분기로 뷰 전환
            if self._viewing_branch != self._active_branch:
                print(f"[TM] 타임머신 열기 - 현재 활성 분기로 뷰 전환: {self._active_branch}")
                self._viewing_branch = self._active_branch
                self._timeline = self._branches[self._active_branch]["records"]
                self._current_index = self._branches[self._active_branch]["current_index"]
                # 패널 재구성
                if hasattr(self, "timeline_panel"):
                    self._rebuild_panel()
            
            overlay.show_overlay_card(self.timemachine_card, "timemachine")
            self.is_timemachine_mode = True
        else:
            overlay.hide_overlay_card("timemachine")
            self.is_timemachine_mode = False
    
    def create_timemachine_card(self):
        from tag_statistics_module import SectionCard
        
        self.timemachine_card = SectionCard("TIME MACHINE")
        self.timemachine_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.timemachine_card.setStyleSheet("""
            QFrame#SectionCard {
                background: rgba(17,17,27,0.9);
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 6px; margin: 14px;
            }
        """)
        
        # Timeline panel
        self.timeline_panel = TimeMachinePanel(self)
        self.timemachine_card.body.addWidget(self.timeline_panel, 1)
        
        # Load existing timeline for VIEWING branch
        for i, rec in enumerate(self._timeline):
            self._add_to_panel(rec, i)
        self.timeline_panel.update_states(self._current_index)
        
        print(f"[TM] Panel initialized. Active={self._active_branch}, Viewing={self._viewing_branch}")
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()  # 왼쪽 여백
        close_btn = QPushButton("Close Time Machine")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
            }
        """)
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.toggle_timemachine_mode)
        btn_layout.addWidget(close_btn)
        self.timemachine_card.body.addLayout(btn_layout)
    
    # ── Extract tag info from record ──────────────────────────────────────────────────────
    def _extract_tag_info(self, record):
        """Extract tag information from record changes for display"""
        changes = record.get("changes", [])
        if not changes:
            return ""
        
        tag_info = []
        for ch in changes:
            ctype = ch.get("type")
            tag = ch.get("tag", "")
            old_tag = ch.get("old", "")
            new_tag = ch.get("new", "")
            
            if ctype in ("tag_add", "tag_toggle_on"):
                if tag:
                    tag_info.append(f"태그추가: '{tag}'")
            elif ctype in ("tag_remove", "tag_toggle_off"):
                if tag:
                    tag_info.append(f"태그삭제: '{tag}'")
            elif ctype == "tag_edit":
                if old_tag and new_tag:
                    tag_info.append(f"태그수정: '{old_tag}'→'{new_tag}'")
            elif ctype == "bulk_add_per_image":
                if tag:
                    tag_info.append(f"태그추가: '{tag}'")
            elif ctype in ("batch_apply_per_image", "single_rename"):
                # For batch operations, show count instead of all tags
                before = ch.get("before", [])
                after = ch.get("after", [])
                added = set(after) - set(before)
                removed = set(before) - set(after)
                if added:
                    tag_info.append(f"태그추가: {len(added)}개")
                if removed:
                    tag_info.append(f"태그삭제: {len(removed)}개")
            elif ctype == "ai_tag_generated":
                # For AI tag generation, show model and tag count
                model = ch.get("model", "AI")
                ai_tags = ch.get("tags", [])
                if ai_tags:
                    tag_info.append(f"AI생성: {len(ai_tags)}개 태그")
            elif ctype == "miracle_single_apply":
                # For miracle single apply, show add/delete counts
                add_count = ch.get("add_count", 0)
                delete_count = ch.get("delete_count", 0)
                if add_count > 0 or delete_count > 0:
                    if add_count > 0 and delete_count > 0:
                        tag_info.append(f"미라클: 추가{add_count}개, 삭제{delete_count}개")
                    elif add_count > 0:
                        tag_info.append(f"미라클: 추가{add_count}개")
                    elif delete_count > 0:
                        tag_info.append(f"미라클: 삭제{delete_count}개")
            elif ctype == "miracle_single_rename":
                # For miracle single rename, show rename count
                rename_count = ch.get("num_renames", 0)
                if rename_count > 0:
                    tag_info.append(f"미라클: 태그이름변경{rename_count}개")
            elif ctype == "miracle_single_moves":
                # For miracle single tag moves, show moves count
                moves_count = ch.get("moves_count", 0)
                if moves_count > 0:
                    tag_info.append(f"미라클: 태그위치조작{moves_count}개")
            elif ctype == "miracle_batch_apply":
                # For miracle batch apply, show image count and operation summary
                num_images = ch.get("num_images", 0)
                if num_images > 0:
                    tag_info.append(f"미라클배치: {num_images}개 이미지")
            elif ctype == "miracle_single_comprehensive":
                # For miracle single comprehensive, show all operations in one line
                add_count = ch.get("add_count", 0)
                delete_count = ch.get("delete_count", 0)
                rename_count = ch.get("rename_count", 0)
                moves_count = ch.get("moves_count", 0)
                
                operations = []
                if add_count > 0:
                    operations.append(f"추가{add_count}개")
                if delete_count > 0:
                    operations.append(f"삭제{delete_count}개")
                if rename_count > 0:
                    operations.append(f"이름변경{rename_count}개")
                if moves_count > 0:
                    operations.append(f"위치조작{moves_count}개")
                
                if operations:
                    tag_info.append(f"미라클: {', '.join(operations)}")
            elif ctype == "global_tag_remove":
                # For global tag removal, show tag name and count
                tag = ch.get("tag", "")
                removed_count = ch.get("removed_count", 0)
                if tag:
                    tag_info.append(f"전역삭제: '{tag}' ({removed_count}개 이미지)")
            elif ctype in ("tag_replace", "bulk_tag_replace"):
                # For tag replacement, show old and new tags
                old_tags = ch.get("old_tags", [])
                new_tag = ch.get("new_tag", "")
                modified_count = ch.get("modified_count", 0)
                if old_tags and new_tag:
                    old_tags_str = ", ".join(old_tags) if len(old_tags) <= 2 else f"{old_tags[0]}, ..."
                    tag_info.append(f"태그교체: '{old_tags_str}'→'{new_tag}' ({modified_count}개 이미지)")
            elif ctype == "tag_delete":
                # For tag deletion, show deleted tag and count
                old_tag = ch.get("old_tag", "")
                modified_count = ch.get("modified_count", 0)
                if old_tag:
                    tag_info.append(f"태그삭제: '{old_tag}' ({modified_count}개 이미지)")
            elif ctype == "tag_insert_relative":
                # For tag insertion, show inserted tag and count
                new_tag = ch.get("new_tag", "")
                modified_count = ch.get("modified_count", 0)
                if new_tag:
                    tag_info.append(f"태그삽입: '{new_tag}' ({modified_count}개 이미지)")
            elif ctype == "tag_append_edge":
                # For tag edge append, show appended tag, position and count
                new_tag = ch.get("new_tag", "")
                to_front = ch.get("to_front", False)
                modified_count = ch.get("modified_count", 0)
                if new_tag:
                    position = "맨앞으로" if to_front else "맨뒤로"
                    tag_info.append(f"새태그추가: '{new_tag}' {position} ({modified_count}개 이미지)")
            elif ctype in ("tag_position_change", "bulk_tag_position_change"):
                # For tag position change, show moved tags and position
                move_tags = ch.get("move_tags", [])
                position_type = ch.get("position_type", "")
                modified_count = ch.get("modified_count", 0)
                if move_tags and position_type:
                    move_tags_str = ", ".join(move_tags) if len(move_tags) <= 2 else f"{move_tags[0]}, ..."
                    tag_info.append(f"태그위치변경: '{move_tags_str}'→'{position_type}' ({modified_count}개 이미지)")
            elif ctype == "clear_all_tags_complete":
                # For complete clear all tags, show comprehensive info
                total_images = ch.get("total_images_cleared", 0)
                total_tags = ch.get("total_tags_cleared", 0)
                if total_images > 0 or total_tags > 0:
                    tag_info.append(f"전체클리어올: {total_images}개 이미지, {total_tags}개 태그")
            elif ctype == "clear_all_tags":
                # For clear all tags, show removed count
                removed_count = ch.get("removed_count", 0)
                if removed_count > 0:
                    tag_info.append(f"클리어올: {removed_count}개 태그")
            elif ctype == "global_tag_stats_cleared":
                # For global tag stats cleared, show cleared count
                cleared_count = ch.get("cleared_tags_count", 0)
                if cleared_count > 0:
                    tag_info.append(f"전역통계클리어: {cleared_count}개 태그")
        
        # 배치 작업의 경우 요약 표시
        if len(tag_info) > 3:  # 3개 이상의 태그 정보가 있으면 요약
            # 배치 작업인지 확인 (미라클 배치, AI 배치, 대량 작업 등)
            batch_types = [
                "miracle_batch_apply", "ai_tag_generated", "bulk_add_per_image",
                "batch_tag_add", "batch_tag_remove", "batch_tag_rename", "batch_tag_move", "batch_tag_delete",
                "bulk_tag_replace", "bulk_tag_position_change"
            ]
            is_batch = any(any(ch.get("type") == bt for ch in changes) for bt in batch_types)
            
            if is_batch:
                # 배치 작업의 경우 전체 요약
                total_added = sum(1 for info in tag_info if "추가" in info or "생성" in info)
                total_removed = sum(1 for info in tag_info if "삭제" in info)
                total_modified = sum(1 for info in tag_info if "교체" in info or "수정" in info)
                
                # 이미지 수 계산 (변경사항 수로 추정)
                image_count = len(changes)
                
                summary_parts = []
                if total_added > 0:
                    summary_parts.append(f"추가{total_added}개")
                if total_removed > 0:
                    summary_parts.append(f"삭제{total_removed}개")
                if total_modified > 0:
                    summary_parts.append(f"수정{total_modified}개")
                
                if summary_parts:
                    return f"배치작업: {', '.join(summary_parts)} ({image_count}장)"
                else:
                    return f"배치작업: {len(tag_info)}개 작업 ({image_count}장)"
        
        # 일반 작업의 경우 기존 방식
        result = " ".join(tag_info[:5])  # Show up to 5 operations
        if len(tag_info) > 5:
            result += f" +{len(tag_info)-5} more"
        return result
    
    # ── Ingestion of new log record ───────────────────────────────────────────────────────
    def _on_tm_record(self, record):
        """
        New record always goes to ACTIVE branch, not viewing branch.
        """
        # Work with ACTIVE branch
        active_records = self._branches[self._active_branch]["records"]
        active_current = self._branches[self._active_branch]["current_index"]
        
        print(f"[TM] New record received. Active branch: {self._active_branch}, current: {active_current}, length: {len(active_records)}")
        
        # If user is in "undone" state IN ACTIVE BRANCH, create a new branch
        branch_created = False
        view_switched = False
        if active_current < len(active_records) - 1:
            print(f"[TM] Creating new branch from active branch {self._active_branch}")
            
            # Fork: keep records up to current position
            kept_records = active_records[:active_current+1].copy()
            new_branch = {
                "records": kept_records[:],
                "current_index": len(kept_records) - 1,
                "name": f"branch {len(self._branches)}",
                "forked_from": (self._active_branch, active_current)
            }
            self._branches.append(new_branch)
            print(f"[TM] Created branch {len(self._branches)-1} with {len(kept_records)} records")
            
            # Switch BOTH active and viewing to new branch
            self._active_branch = len(self._branches) - 1
            self._viewing_branch = self._active_branch
            self._timeline = self._branches[self._active_branch]["records"]
            self._current_index = self._branches[self._active_branch]["current_index"]
            print(f"[TM] Switched to new branch {self._active_branch}")
            branch_created = True
        else:
            # If viewing a different branch, switch view back to active
            if self._viewing_branch != self._active_branch:
                print(f"[TM] Switching view from {self._viewing_branch} to active {self._active_branch}")
                self._viewing_branch = self._active_branch
                self._timeline = self._branches[self._active_branch]["records"]
                self._current_index = self._branches[self._active_branch]["current_index"]
                view_switched = True
        
        # Normal append to active branch
        self._timeline.append(record)
        self._current_index = len(self._timeline) - 1
        self._branches[self._active_branch]["records"] = self._timeline
        self._branches[self._active_branch]["current_index"] = self._current_index
        
        print(f"[TM] Appended record. New index: {self._current_index}, Timeline length: {len(self._timeline)}")

        # Attach both all_tags and global_tag_stats snapshots for logging/redo
        try:
            record.setdefault("_snapshots", {})
            # global_tag_stats deep copy (convert sets to lists)
            _gts = getattr(self.app, "global_tag_stats", {}) or {}
            _gts_copy = {}
            for _t, _rec in _gts.items():
                if isinstance(_rec, dict):
                    _images_obj = _rec.get('images', [])
                    _images_list = list(_images_obj) if isinstance(_images_obj, (set, list, tuple)) else []
                    _gts_copy[_t] = {
                        'image_count': int(_rec.get('image_count', len(_images_list))),
                        'category': _rec.get('category', 'unknown'),
                        'images': _images_list,
                    }
                else:
                    try:
                        _gts_copy[_t] = {'image_count': int(_rec), 'category': 'unknown', 'images': []}
                    except Exception:
                        _gts_copy[_t] = {'image_count': 0, 'category': 'unknown', 'images': []}
            record["_snapshots"]["global_tag_stats"] = _gts_copy

            # all_tags summary by image (avoid heavy payload)
            _ats = getattr(self.app, "all_tags", {}) or {}
            record["_snapshots"]["all_tags_counts"] = {k: len(v or []) for k, v in list(_ats.items())[:200]}
            record["_snapshots"]["all_tags_total"] = sum(len(v or []) for v in _ats.values())
        except Exception as _e:
            print(f"[TM] snapshot attach skipped: {_e}")

        
        # Reflect in UI
        if hasattr(self, "timeline_panel"):
            if branch_created or view_switched:
                # Rebuild entire panel
                print(f"[TM] Rebuilding panel (branch_created={branch_created}, view_switched={view_switched})")
                self._rebuild_panel()
            else:
                # Just add new card
                self._add_to_panel(record, len(self._timeline) - 1)
                self.timeline_panel.update_states(self._current_index)
            
            # Auto scroll to bottom - 개선된 스크롤
            self._auto_scroll_to_bottom()
        
        # Trim branch length
        if len(self._timeline) > 500:
            self._timeline.pop(0)
            if self._current_index > 0:
                self._current_index -= 1
    
    def _get_operation_type(self, record):
        """작업 유형을 분석하여 카테고리와 색상 반환"""
        title = record.get("title", "").lower()
        changes = record.get("changes", [])
        context = record.get("context", {})
        
        # 미라클 관련 작업 (제목이나 컨텍스트에서 확인)
        if ("miracle" in title or 
            context.get("source") == "miracle_batch" or
            any(ch.get("type") in ["miracle_batch_apply", "miracle_single_comprehensive", "miracle_response_card"] for ch in changes)):
            return "miracle", "Miracle", "#FFD93D"  # 노란색
        
        # 태그 스타일시트 관련 작업 (우선순위를 높여서 태깅보다 먼저 체크)
        if ("stylesheet" in title or 
            context.get("source") == "tag_stylesheet_editor" or
            any(ch.get("type") in [
                "stylesheet_change", "stylesheet_clear", "tag_stylesheet_reorder",
                "tag_replace", "bulk_tag_replace", "tag_position_change", "bulk_tag_position_change",
                "tag_delete", "tag_insert_relative", "tag_append_edge", "global_tag_remove"
            ] for ch in changes)):
            return "stylesheet", "Stylesheet", "#6BCF7F"  # 파란색
        
        # 클리어올 관련 작업
        if ("clear" in title or 
            context.get("source") == "action_buttons" or
            any(ch.get("type") in ["clear_all_tags", "clear_all_tags_complete", "clear_all_metadata", "global_tag_stats_cleared"] for ch in changes)):
            return "clearall", "ClearAll", "#FF6B6B"  # 빨간색
        
        # 태깅 관련 작업 (개별 태그 조작 - 스타일시트 작업 제외)
        if any(ch.get("type") in [
            "tag_add", "tag_remove", "tag_toggle", "tag_toggle_on", "tag_toggle_off",
            "tag_edit", "tag_reorder",
            "batch_tag_add", "batch_tag_remove", "batch_tag_rename", "batch_tag_move", "batch_tag_delete",
            "bulk_add_per_image", "ai_tag_generated"
        ] for ch in changes):
            return "tagging", "Tagging", "#9B59B6"  # 보라색
        
        # 기본 시스템 작업
        return "system", "System", "#95A5A6"  # 회색

    def _auto_scroll_to_bottom(self):
        """개선된 자동 스크롤 - 스크롤이 길어지면 맨 아래로"""
        if not hasattr(self, 'timeline_panel') or not hasattr(self.timeline_panel, 'scroll'):
            return
        
        scrollbar = self.timeline_panel.scroll.verticalScrollBar()
        
        # 현재 스크롤 위치가 맨 아래 근처에 있는지 확인 (50픽셀 이내)
        current_value = scrollbar.value()
        max_value = scrollbar.maximum()
        is_near_bottom = (max_value - current_value) <= 50
        
        # 맨 아래 근처에 있거나 새 카드가 추가된 경우에만 스크롤
        if is_near_bottom or len(self._timeline) <= 5:  # 처음 5개 카드는 항상 스크롤
            QTimer.singleShot(100, lambda: scrollbar.setValue(scrollbar.maximum()))

    def _add_to_panel(self, rec, index):
        if not hasattr(self, 'timeline_panel'):
            return
        
        import datetime
        ts = rec.get("ended_at") or rec.get("started_at")
        # 일관된 포맷: 년-월-일 시:분:초
        time_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
        
        # Get branches with same operation at this position
        branches = self._get_branches_at_position(index)
        
        # Extract tag info
        tag_info = self._extract_tag_info(rec)
        tag_display = f" {tag_info}" if tag_info else ""
        
        # 작업 유형 분석
        op_type, op_name, op_color = self._get_operation_type(rec)
        
        # 상태 표시 (한글 + 태그 정보)
        status_text = "(적용됨)" if index <= self._current_index else "(취소됨)"
        if tag_display:
            status_text += f" {tag_display}"
        
        self.timeline_panel.add_card({
            "time": time_str,
            "who": op_name,  # 작업 유형으로 표시
            "body": f"{rec.get('title', '')} ({len(rec.get('changes', []))}개 변경사항)",
            "status": status_text,
            "index": index,
            "record": rec,
            "branches": branches,
            "operation_type": op_type,
            "operation_color": op_color
        })
    
    def jump_to(self, card_index):
        """
        Undo/Redo around the clicked card.
        CRITICAL: If viewing a different branch and clicking Redo, switch ACTIVE branch.
        """
        if card_index < 0 or card_index >= len(self._timeline):
            return
        
        current = self._current_index
        is_applied_now = (card_index <= current)
        
        # Calculate target
        target = (card_index - 1) if is_applied_now else card_index
        if target < -1:
            target = -1
        if target >= len(self._timeline):
            target = len(self._timeline) - 1
        
        if target == current:
            if hasattr(self, "timeline_panel"):
                self.timeline_panel.update_states(self._current_index)
            return
        
        # Check if we're clicking Redo in a different branch than active
        if not is_applied_now and self._viewing_branch != self._active_branch:
            print(f"[TM] Redo clicked in viewing branch {self._viewing_branch} (active is {self._active_branch})")
            print(f"[TM] Switching ACTIVE branch to {self._viewing_branch}")
            
            # Find divergence point between active and viewing branches
            active_records = self._branches[self._active_branch]["records"]
            viewing_records = self._branches[self._viewing_branch]["records"]
            
            divergence_point = -1
            for i in range(min(len(active_records), len(viewing_records))):
                if not self._records_match(active_records[i], viewing_records[i]):
                    divergence_point = i - 1
                    break
            else:
                divergence_point = min(len(active_records), len(viewing_records)) - 1
            
            print(f"[TM] Divergence point: {divergence_point}")
            
            # Undo active branch from its current position down to divergence point
            active_current = self._branches[self._active_branch]["current_index"]
            if active_current > divergence_point:
                print(f"[TM] Undoing active branch from {active_current} to {divergence_point}")
                for i in range(active_current, divergence_point, -1):
                    self._apply(active_records[i], False)
                # Update active branch's current_index to divergence point
                self._branches[self._active_branch]["current_index"] = divergence_point
                print(f"[TM] Updated active branch {self._active_branch} current_index to {divergence_point}")
            
            # Switch active branch
            self._active_branch = self._viewing_branch
            self._viewing_branch = self._active_branch
            print(f"[TM] Active and viewing now both: {self._active_branch}")
        
        # Normal Undo/Redo
        if target < current:
            for i in range(current, target, -1):
                self._apply(self._timeline[i], False)
        else:
            for i in range(current + 1, target + 1):
                self._apply(self._timeline[i], True)
        
        self._current_index = target
        self._persist_branch_state()
        
        # Also update active branch's current_index
        if self._active_branch == self._viewing_branch:
            self._branches[self._active_branch]["current_index"] = target
        
        if hasattr(self, "timeline_panel"):
            self.timeline_panel.update_states(self._current_index)
        
        if hasattr(self.app, 'update_current_tags_display'):
            self.app.update_current_tags_display()
        if hasattr(self.app, 'update_tag_stats'):
            self.app.update_tag_stats()
        
        # 태그/검색 재적용 (그리드 자동 새로고침)
        handler = getattr(self.app, '_tm_auto_refresh_handler', None)
        if callable(handler):
            try:
                handler({})
            except Exception:
                pass
    
    def _apply(self, record, is_redo):
        changes = record.get("changes", [])
        for ch in (changes if is_redo else reversed(changes)):
            self._process_change(ch, is_redo)
    
    def _process_change(self, ch, is_redo):
        ctype = ch.get("type")
        
        # ── 추가: 미라클 응답 카드 undo/redo 처리 ───────────────────────────────
        if ctype == 'miracle_response_card':
            try:
                app = getattr(self, 'app', None)
                mm = getattr(app, 'miracle_manager', None) if app else None
                if not mm:
                    return
                card_id = ch.get('card_id')
                text = ch.get('text', '') or ''
                mode = ch.get('mode', 'single')
                border = '#22c55e' if mode == 'batch' else '#3B82F6'
                if is_redo:
                    if hasattr(mm, 'tm_recreate_response_card'):
                        mm.tm_recreate_response_card(card_id, text, border_color=border)
                else:
                    if hasattr(mm, 'tm_remove_response_card'):
                        mm.tm_remove_response_card(card_id)
            except Exception as _e:
                print(f"[TM] miracle_response_card 처리 오류: {_e}")
            return
        image_name = str(ch.get("image", ""))
        
        # 이미지 경로 확인 및 변환
        image = None
        if image_name:
            # 1. 이미 전체 경로인지 확인 (데이터베이스에서 복원된 경우)
            if Path(image_name).exists():
                image = image_name
            else:
                # 2. 파일명만 있는 경우 - all_tags에서 찾기
                for img_path in self.app.all_tags.keys():
                    if Path(img_path).name == image_name:
                        image = img_path
                        break
                
                # 3. 못 찾으면 현재 이미지가 해당 파일명인지 확인
                if not image and hasattr(self.app, 'current_image'):
                    if Path(self.app.current_image).name == image_name:
                        image = self.app.current_image
                
                # 4. 문자열 키로 직접 매칭 시도
                if not image and image_name in self.app.all_tags:
                    image = image_name
        
        # 전역 타입들은 이미지가 없어도 처리해야 함
        GLOBAL_TYPES = {
            "global_tag_remove", "tag_replace", "bulk_tag_replace",
            "tag_position_change", "bulk_tag_position_change",
            "global_tag_stats_cleared", "clear_all_tags", "clear_all_tags_complete",
            "clear_all_metadata", "tag_delete", "tag_insert_relative", "tag_append_edge",
        }
        
        if not image and ctype not in GLOBAL_TYPES:
            print(f"[TM WARNING] 이미지를 찾을 수 없음: {image_name}")
            print(f"[TM DEBUG] all_tags 키들: {list(self.app.all_tags.keys())[:5]}...")
            return
        
        # 스타일시트 에디터 작업들은 별도 처리
        if ctype in ("tag_stylesheet_remove", "tag_stylesheet_reorder"):
            self._process_stylesheet_change(ch, is_redo)
            return
        
        # 전역 작업들은 별도 처리
        if ctype in ("global_tag_remove", "tag_replace", "bulk_tag_replace", "tag_position_change", "bulk_tag_position_change", "global_tag_stats_cleared", "clear_all_tags", "clear_all_tags_complete", "clear_all_metadata", "tag_delete", "tag_insert_relative", "tag_append_edge"):
            self._process_global_change(ch, is_redo)
            return
        
        # 미라클 배치 작업은 별도 처리 (전역 작업과 유사)
        if ctype == "miracle_batch_apply":
            # 미라클 배치 작업은 로그만 기록하고 실제 처리는 하지 않음
            # (개별 이미지별 처리는 batch_apply_per_image로 처리됨)
            return
        
        # 미라클 통합 작업 처리
        if ctype == "miracle_single_comprehensive":
            # all_tags 초기화 - all_tags 관리 플러그인 사용
            from all_tags_manager import get_tags_for_image
            tags = get_tags_for_image(self.app, image)
            
            # 이미지별 리무버 태그 저장소 초기화
            if not hasattr(self.app, 'image_removed_tags'):
                self.app.image_removed_tags = {}
            if image not in self.app.image_removed_tags:
                self.app.image_removed_tags[image] = []
            
            add_tags = ch.get("add", [])
            delete_tags = ch.get("delete", [])
            delete_from = ch.get("delete_from", {})  # 원래 위치 정보
            renames = ch.get("renames", [])
            moves = ch.get("moves", [])
            
            if is_redo:
                # 1. 태그 이름 변경 적용
                for rename in renames:
                    old_tag = rename.get('from')
                    new_tag = rename.get('to')
                    # 액티브 태그 처리
                    if old_tag and new_tag and old_tag in tags:
                        tags[tags.index(old_tag)] = new_tag
                        self._global_rename(image, old_tag, new_tag)
                    # 리무버 태그 처리
                    elif old_tag and new_tag and old_tag in self.app.image_removed_tags.get(image, []):
                        idx = self.app.image_removed_tags[image].index(old_tag)
                        self.app.image_removed_tags[image][idx] = new_tag
                        self._global_rename(image, old_tag, new_tag)  # 글로벌 태그도 업데이트
                        # 현재 이미지면 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags') and old_tag in self.app.removed_tags:
                                self.app.removed_tags[self.app.removed_tags.index(old_tag)] = new_tag
                
                # 2. 태그 삭제 적용 (완전 삭제)
                for tag in delete_tags:
                    original_location = delete_from.get(tag, "active")  # 정보 없으면 액티브로 가정
                    
                    if original_location == "active":
                        # 액티브에서 완전 삭제
                        if tag in tags:
                            tags.remove(tag)
                            self._global_remove(image, tag)
                    elif original_location == "removed":
                        # 리무버에서 완전 삭제
                        if tag in self.app.image_removed_tags.get(image, []):
                            self.app.image_removed_tags[image].remove(tag)
                            self._global_remove(image, tag)
                            # 현재 이미지인 경우 UI 동기화
                            if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                                if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                                    self.app.removed_tags.remove(tag)
                
                # 3. 태그 추가 적용
                for tag in add_tags:
                    if tag not in tags:
                        tags.append(tag)
                        self._global_add(image, tag)
                        # 상호 배타: 이미지별 리무버 태그에서 제거
                        if tag in self.app.image_removed_tags[image]:
                            self.app.image_removed_tags[image].remove(tag)
                        # 현재 이미지인 경우 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                                self.app.removed_tags.remove(tag)
                
                # 4. 태그 위치 조작 적용
                for move in moves:
                    tag_name = move.get('tag')
                    direction = move.get('direction')
                    steps = move.get('steps', 1)
                    # 액티브 태그 처리
                    if tag_name and tag_name in tags:
                        current_index = tags.index(tag_name)
                        new_index = current_index
                        if direction == 'up':
                            new_index = max(0, current_index - steps)
                        elif direction == 'down':
                            new_index = min(len(tags) - 1, current_index + steps)
                        if new_index != current_index:
                            tag = tags.pop(current_index)
                            tags.insert(new_index, tag)
                    # 리무버 태그 처리
                    elif tag_name and tag_name in self.app.image_removed_tags.get(image, []):
                        removed_list = self.app.image_removed_tags[image]
                        current_index = removed_list.index(tag_name)
                        new_index = current_index
                        if direction == 'up':
                            new_index = max(0, current_index - steps)
                        elif direction == 'down':
                            new_index = min(len(removed_list) - 1, current_index + steps)
                        if new_index != current_index:
                            tag = removed_list.pop(current_index)
                            removed_list.insert(new_index, tag)
                        # 현재 이미지면 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags'):
                                self.app.removed_tags = removed_list[:]
            else:
                # Undo: 반대 순서로 처리
                # 1. 태그 위치 조작 되돌리기
                for move in moves:
                    tag_name = move.get('tag')
                    direction = move.get('direction')
                    steps = move.get('steps', 1)
                    # 액티브 태그 처리
                    if tag_name and tag_name in tags:
                        current_index = tags.index(tag_name)
                        new_index = current_index
                        # 반대 방향으로 이동
                        if direction == 'up':
                            new_index = min(len(tags) - 1, current_index + steps)
                        elif direction == 'down':
                            new_index = max(0, current_index - steps)
                        if new_index != current_index:
                            tag = tags.pop(current_index)
                            tags.insert(new_index, tag)
                    # 리무버 태그 처리
                    elif tag_name and tag_name in self.app.image_removed_tags.get(image, []):
                        removed_list = self.app.image_removed_tags[image]
                        current_index = removed_list.index(tag_name)
                        new_index = current_index
                        # 반대 방향으로 이동
                        if direction == 'up':
                            new_index = min(len(removed_list) - 1, current_index + steps)
                        elif direction == 'down':
                            new_index = max(0, current_index - steps)
                        if new_index != current_index:
                            tag = removed_list.pop(current_index)
                            removed_list.insert(new_index, tag)
                        # 현재 이미지면 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags'):
                                self.app.removed_tags = removed_list[:]
                
                # 2. 태그 추가 되돌리기 (삭제) - add의 undo는 리무버로 보내지 않음
                for tag in add_tags:
                    if tag in tags:
                        tags.remove(tag)
                        self._global_remove(image, tag)
                
                # 3. 태그 삭제 되돌리기 (원래 위치로 복구)
                for tag in delete_tags:
                    original_location = delete_from.get(tag, "active")  # 정보 없으면 액티브로 가정
                    
                    if original_location == "active":
                        # 원래 액티브에 있었던 태그 → 액티브로 복구
                        if tag not in tags:
                            tags.append(tag)
                            self._global_add(image, tag)
                    elif original_location == "removed":
                        # 원래 리무버에 있었던 태그 → 리무버로 복구
                        if tag not in self.app.image_removed_tags.get(image, []):
                            self.app.image_removed_tags[image].append(tag)
                            # 현재 이미지인 경우 UI 동기화
                            if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                                if hasattr(self.app, 'removed_tags') and tag not in self.app.removed_tags:
                                    self.app.removed_tags.append(tag)
                
                # 4. 태그 이름 변경 되돌리기
                for rename in renames:
                    old_tag = rename.get('from')
                    new_tag = rename.get('to')
                    # 액티브 태그 처리
                    if old_tag and new_tag and new_tag in tags:
                        tags[tags.index(new_tag)] = old_tag
                        self._global_rename(image, new_tag, old_tag)
                    # 리무버 태그 처리
                    elif old_tag and new_tag and new_tag in self.app.image_removed_tags.get(image, []):
                        idx = self.app.image_removed_tags[image].index(new_tag)
                        self.app.image_removed_tags[image][idx] = old_tag
                        self._global_rename(image, new_tag, old_tag)  # 글로벌 태그도 복구
                        # 현재 이미지면 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags') and new_tag in self.app.removed_tags:
                                self.app.removed_tags[self.app.removed_tags.index(new_tag)] = old_tag
            
            # all_tags 업데이트 - all_tags 관리 플러그인 사용
            from all_tags_manager import set_tags_for_image
            set_tags_for_image(self.app, image, list(tags))
            
            # Sync current tags - miracle 작업 후에도 동기화
            if getattr(self.app, 'current_image', None) == image:
                self.app.current_tags = list(tags)
                print(f"[TM] miracle 작업 후 current_tags 동기화: {self.app.current_tags}")
                
                # UI 업데이트 강제 실행
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                    print(f"[TM] miracle 작업 후 UI 업데이트 완료")
            return
        
        # all_tags 초기화 - all_tags 관리 플러그인 사용
        from all_tags_manager import get_tags_for_image
        tags = get_tags_for_image(self.app, image)
        
        # Snapshot-based changes
        if ctype in ("batch_apply_per_image", "single_rename", "tag_reorder"):
            target = ch.get("after" if is_redo else "before", [])
            prev = list(tags)
            # all_tags 업데이트 - all_tags 관리 플러그인 사용
            from all_tags_manager import set_tags_for_image
            set_tags_for_image(self.app, image, list(target))
            self._global_apply_snapshot(image, prev, target)
            # 지역변수 tags 업데이트 (마지막 공통 동기화에서 올바른 값 사용)
            tags = list(target)
        
        # 배치 개별 작업 처리
        elif ctype == "batch_tag_rename":
            old_tag = ch.get("old_tag")
            new_tag = ch.get("new_tag")
            target_type = ch.get("target_type", "active")
            
            # 이미지별 리무버 태그 저장소 초기화
            if not hasattr(self.app, 'image_removed_tags'):
                self.app.image_removed_tags = {}
            if image not in self.app.image_removed_tags:
                self.app.image_removed_tags[image] = []
            
            if is_redo:
                # rename 적용
                if target_type == "active" and old_tag in tags:
                    tags[tags.index(old_tag)] = new_tag
                    self._global_rename(image, old_tag, new_tag)
                elif target_type == "removed" and old_tag in self.app.image_removed_tags.get(image, []):
                    idx = self.app.image_removed_tags[image].index(old_tag)
                    self.app.image_removed_tags[image][idx] = new_tag
                    self._global_rename(image, old_tag, new_tag)
            else:
                # rename 되돌리기
                if target_type == "active" and new_tag in tags:
                    tags[tags.index(new_tag)] = old_tag
                    self._global_rename(image, new_tag, old_tag)
                elif target_type == "removed" and new_tag in self.app.image_removed_tags.get(image, []):
                    idx = self.app.image_removed_tags[image].index(new_tag)
                    self.app.image_removed_tags[image][idx] = old_tag
                    self._global_rename(image, new_tag, old_tag)
            
            # all_tags 업데이트
            from all_tags_manager import set_tags_for_image
            set_tags_for_image(self.app, image, list(tags))
            
            # UI 동기화
            if getattr(self.app, 'current_image', None) == image:
                self.app.current_tags = list(tags)
                if hasattr(self.app, 'removed_tags'):
                    self.app.removed_tags = list(self.app.image_removed_tags.get(image, []))
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
        
        elif ctype == "batch_tag_add":
            tag = ch.get("tag")
            
            # 이미지별 리무버 태그 저장소 초기화
            if not hasattr(self.app, 'image_removed_tags'):
                self.app.image_removed_tags = {}
            if image not in self.app.image_removed_tags:
                self.app.image_removed_tags[image] = []
            
            if is_redo:
                # 태그 추가
                if tag not in tags:
                    tags.append(tag)
                    self._global_add(image, tag)
                    # 상호 배타: 이미지별 리무버 태그에서 제거
                    if tag in self.app.image_removed_tags[image]:
                        self.app.image_removed_tags[image].remove(tag)
                    # 현재 이미지인 경우 UI 동기화
                    if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                        if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                            self.app.removed_tags.remove(tag)
            else:
                # 태그 추가 취소 (단순 제거, 리무버로 보내지 않음)
                if tag in tags:
                    tags.remove(tag)
                    self._global_remove(image, tag)
        
        elif ctype == "batch_tag_delete":
            tag = ch.get("tag")
            target_type = ch.get("target_type", "active")
            
            # 이미지별 리무버 태그 저장소 초기화
            if not hasattr(self.app, 'image_removed_tags'):
                self.app.image_removed_tags = {}
            if image not in self.app.image_removed_tags:
                self.app.image_removed_tags[image] = []
            
            if is_redo:
                # 태그 완전 삭제
                if target_type == "active" and tag in tags:
                    tags.remove(tag)
                    self._global_remove(image, tag)
                elif target_type == "removed" and tag in self.app.image_removed_tags.get(image, []):
                    self.app.image_removed_tags[image].remove(tag)
                    self._global_remove(image, tag)
                    # 현재 이미지인 경우 UI 동기화
                    if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                        if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                            self.app.removed_tags.remove(tag)
            else:
                # 태그 삭제 취소 (원래 위치로 복구)
                if target_type == "active":
                    # 원래 액티브에 있었던 태그 → 액티브로 복구
                    if tag not in tags:
                        tags.append(tag)
                        self._global_add(image, tag)
                elif target_type == "removed":
                    # 원래 리무버에 있었던 태그 → 리무버로 복구
                    if tag not in self.app.image_removed_tags.get(image, []):
                        self.app.image_removed_tags[image].append(tag)
                        # 현재 이미지인 경우 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags') and tag not in self.app.removed_tags:
                                self.app.removed_tags.append(tag)
            
            # all_tags 업데이트
            from all_tags_manager import set_tags_for_image
            set_tags_for_image(self.app, image, list(tags))
            
            # UI 동기화
            if getattr(self.app, 'current_image', None) == image:
                self.app.current_tags = list(tags)
                if hasattr(self.app, 'removed_tags'):
                    self.app.removed_tags = list(self.app.image_removed_tags.get(image, []))
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
        
        elif ctype == "batch_tag_move":
            tag_name = ch.get("tag")
            direction = ch.get("direction")
            steps = ch.get("steps", 1)
            from_index = ch.get("from_index")
            to_index = ch.get("to_index")
            target_type = ch.get("target_type", "active")
            
            # 이미지별 리무버 태그 저장소 초기화
            if not hasattr(self.app, 'image_removed_tags'):
                self.app.image_removed_tags = {}
            if image not in self.app.image_removed_tags:
                self.app.image_removed_tags[image] = []
            
            if is_redo:
                # move 적용
                if target_type == "active" and tag_name in tags:
                    current_index = tags.index(tag_name)
                    new_index = current_index
                    if direction == 'up':
                        new_index = max(0, current_index - steps)
                    elif direction == 'down':
                        new_index = min(len(tags) - 1, current_index + steps)
                    if new_index != current_index:
                        tag = tags.pop(current_index)
                        tags.insert(new_index, tag)
                elif target_type == "removed" and tag_name in self.app.image_removed_tags.get(image, []):
                    removed_list = self.app.image_removed_tags[image]
                    current_index = removed_list.index(tag_name)
                    new_index = current_index
                    if direction == 'up':
                        new_index = max(0, current_index - steps)
                    elif direction == 'down':
                        new_index = min(len(removed_list) - 1, current_index + steps)
                    if new_index != current_index:
                        tag = removed_list.pop(current_index)
                        removed_list.insert(new_index, tag)
            else:
                # move 되돌리기 (반대 방향)
                if target_type == "active" and tag_name in tags:
                    current_index = tags.index(tag_name)
                    new_index = current_index
                    if direction == 'up':
                        new_index = min(len(tags) - 1, current_index + steps)
                    elif direction == 'down':
                        new_index = max(0, current_index - steps)
                    if new_index != current_index:
                        tag = tags.pop(current_index)
                        tags.insert(new_index, tag)
                elif target_type == "removed" and tag_name in self.app.image_removed_tags.get(image, []):
                    removed_list = self.app.image_removed_tags[image]
                    current_index = removed_list.index(tag_name)
                    new_index = current_index
                    if direction == 'up':
                        new_index = min(len(removed_list) - 1, current_index + steps)
                    elif direction == 'down':
                        new_index = max(0, current_index - steps)
                    if new_index != current_index:
                        tag = removed_list.pop(current_index)
                        removed_list.insert(new_index, tag)
            
            # all_tags 업데이트
            from all_tags_manager import set_tags_for_image
            set_tags_for_image(self.app, image, list(tags))
            
            # UI 동기화
            if getattr(self.app, 'current_image', None) == image:
                self.app.current_tags = list(tags)
                if hasattr(self.app, 'removed_tags'):
                    self.app.removed_tags = list(self.app.image_removed_tags.get(image, []))
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
        
        # Tag add/remove
        elif ctype in ("tag_add", "tag_remove", "tag_toggle_on", "tag_toggle_off"):
            tag = ch.get("tag")
            if not tag:
                return
            
            should_add = (ctype in ("tag_add", "tag_toggle_on"))
            if not is_redo:
                should_add = not should_add
            
            # 이미지별 리무버 태그 저장소 초기화
            if not hasattr(self.app, 'image_removed_tags'):
                self.app.image_removed_tags = {}
            if image not in self.app.image_removed_tags:
                self.app.image_removed_tags[image] = []
            
            if should_add and tag not in tags:
                tags.append(tag)
                self._global_add(image, tag)
                # 상호 배타: 이미지별 리무버 태그에서 제거
                if tag in self.app.image_removed_tags[image]:
                    self.app.image_removed_tags[image].remove(tag)
                # 현재 이미지인 경우 UI 동기화
                if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                    if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                        self.app.removed_tags.remove(tag)
            elif not should_add and tag in tags:
                tags.remove(tag)
                self._global_remove(image, tag)
                # 제거를 리무버에 반영하는 것은 실제 제거 계열인 경우에만
                if ctype in ("tag_remove", "tag_toggle_off") or (ctype == "tag_toggle_on" and not is_redo):
                    if tag not in self.app.image_removed_tags[image]:
                        self.app.image_removed_tags[image].append(tag)
                    if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                        if hasattr(self.app, 'removed_tags') and tag not in self.app.removed_tags:
                            self.app.removed_tags.append(tag)
            
            # UI 업데이트 (태그 토글은 현재 이미지에만 영향)
            if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
        
        # Tag edit
        elif ctype == "tag_edit":
            old, new = ch.get("old"), ch.get("new")
            if old and new:
                src, dst = (new, old) if not is_redo else (old, new)
                if src in tags:
                    tags[tags.index(src)] = dst
                    self._global_rename(image, src, dst)
        
        # Bulk add
        elif ctype == "bulk_add_per_image":
            tag = ch.get("tag")
            if tag:
                # 이미지별 리무버 태그 저장소 초기화
                if not hasattr(self.app, 'image_removed_tags'):
                    self.app.image_removed_tags = {}
                if image not in self.app.image_removed_tags:
                    self.app.image_removed_tags[image] = []
                
                if is_redo and tag not in tags:
                    tags.append(tag)
                    self._global_add(image, tag)
                    # 상호 배타: 이미지별 리무버 태그에서 제거
                    if tag in self.app.image_removed_tags[image]:
                        self.app.image_removed_tags[image].remove(tag)
                    # 현재 이미지인 경우 UI 동기화
                    if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                        if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                            self.app.removed_tags.remove(tag)
                elif not is_redo and tag in tags:
                    # bulk 추가의 UNDO는 단순 제거만 하고 리무버로 보내지 않음
                    tags.remove(tag)
                    self._global_remove(image, tag)
        
        # AI Tag Generation
        elif ctype == "ai_tag_generated":
            ai_tags = ch.get("tags", [])
            if ai_tags:
                # 이미지별 리무버 태그 저장소 초기화
                if not hasattr(self.app, 'image_removed_tags'):
                    self.app.image_removed_tags = {}
                if image not in self.app.image_removed_tags:
                    self.app.image_removed_tags[image] = []
                
                if is_redo:
                    # AI 태그들을 추가
                    for tag in ai_tags:
                        if tag not in tags:
                            tags.append(tag)
                            self._global_add(image, tag)
                            # 상호 배타: 이미지별 리무버 태그에서 제거
                            if tag in self.app.image_removed_tags[image]:
                                self.app.image_removed_tags[image].remove(tag)
                            # 현재 이미지인 경우 UI 동기화
                            if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                                if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                                    self.app.removed_tags.remove(tag)
                else:
                    # AI 추가의 UNDO는 단순 제거만 하고 리무버로 보내지 않음
                    for tag in ai_tags:
                        if tag in tags:
                            tags.remove(tag)
                            self._global_remove(image, tag)
        
        # Miracle Single Apply (태그 추가/삭제)
        elif ctype == "miracle_single_apply":
            add_tags = ch.get("add", [])
            delete_tags = ch.get("delete", [])
            
            # 이미지별 리무버 태그 저장소 초기화
            if not hasattr(self.app, 'image_removed_tags'):
                self.app.image_removed_tags = {}
            if image not in self.app.image_removed_tags:
                self.app.image_removed_tags[image] = []
            
            if is_redo:
                # 태그 추가
                for tag in add_tags:
                    if tag not in tags:
                        tags.append(tag)
                        self._global_add(image, tag)
                        # 상호 배타: 이미지별 리무버 태그에서 제거
                        if tag in self.app.image_removed_tags[image]:
                            self.app.image_removed_tags[image].remove(tag)
                        # 현재 이미지인 경우 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                                self.app.removed_tags.remove(tag)
                # 태그 삭제
                for tag in delete_tags:
                    if tag in tags:
                        tags.remove(tag)
                        self._global_remove(image, tag)
                        # 상호 배타: 이미지별 리무버 태그에 추가
                        if tag not in self.app.image_removed_tags[image]:
                            self.app.image_removed_tags[image].append(tag)
                        # 현재 이미지인 경우 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags') and tag not in self.app.removed_tags:
                                self.app.removed_tags.append(tag)
            else:
                # 태그 삭제 (undo) - add의 undo는 리무버로 보내지 않음
                for tag in add_tags:
                    if tag in tags:
                        tags.remove(tag)
                        self._global_remove(image, tag)
                # 태그 추가 (undo)
                for tag in delete_tags:
                    if tag not in tags:
                        tags.append(tag)
                        self._global_add(image, tag)
                        # 상호 배타: 이미지별 리무버 태그에서 제거
                        if tag in self.app.image_removed_tags[image]:
                            self.app.image_removed_tags[image].remove(tag)
                        # 현재 이미지인 경우 UI 동기화
                        if hasattr(self.app, 'current_image') and str(image) == str(self.app.current_image):
                            if hasattr(self.app, 'removed_tags') and tag in self.app.removed_tags:
                                self.app.removed_tags.remove(tag)
        
        # Miracle Single Tag Moves (태그 위치 조작)
        elif ctype == "miracle_single_moves":
            moves = ch.get("moves", [])
            if moves:
                if is_redo:
                    # 태그 위치 조작 적용
                    for move in moves:
                        tag_name = move.get('tag')
                        direction = move.get('direction')
                        steps = move.get('steps', 1)
                        if tag_name and tag_name in tags:
                            current_index = tags.index(tag_name)
                            new_index = current_index
                            if direction == 'up':
                                new_index = max(0, current_index - steps)
                            elif direction == 'down':
                                new_index = min(len(tags) - 1, current_index + steps)
                            if new_index != current_index:
                                tag = tags.pop(current_index)
                                tags.insert(new_index, tag)
                else:
                    # 태그 위치 조작 되돌리기 (반대 방향으로)
                    for move in moves:
                        tag_name = move.get('tag')
                        direction = move.get('direction')
                        steps = move.get('steps', 1)
                        if tag_name and tag_name in tags:
                            current_index = tags.index(tag_name)
                            new_index = current_index
                            # 반대 방향으로 이동
                            if direction == 'up':
                                new_index = min(len(tags) - 1, current_index + steps)
                            elif direction == 'down':
                                new_index = max(0, current_index - steps)
                            if new_index != current_index:
                                tag = tags.pop(current_index)
                                tags.insert(new_index, tag)
        
        
        
        
        # Tag Rename (from image tagging module)
        elif ctype == "tag_rename":
            old_tag = ch.get("old_tag")
            new_tag = ch.get("new_tag")
            if old_tag and new_tag:
                src, dst = (new_tag, old_tag) if not is_redo else (old_tag, new_tag)
                if src in tags:
                    tags[tags.index(src)] = dst
                    self._global_rename(image, src, dst)
        
        # Miracle Single Rename (태그 이름 변경)
        elif ctype == "miracle_single_rename":
            renames = ch.get("renames", [])
            if renames:
                if is_redo:
                    # 태그 이름 변경 적용
                    for rename in renames:
                        old_tag = rename.get('from')
                        new_tag = rename.get('to')
                        if old_tag and new_tag and old_tag in tags:
                            tags[tags.index(old_tag)] = new_tag
                            self._global_rename(image, old_tag, new_tag)
                else:
                    # 태그 이름 변경 되돌리기
                    for rename in renames:
                        old_tag = rename.get('from')
                        new_tag = rename.get('to')
                        if old_tag and new_tag and new_tag in tags:
                            tags[tags.index(new_tag)] = old_tag
                            self._global_rename(image, new_tag, old_tag)
        
        
        # Sync current tags - 모든 변경 타입에 대해 일관되게 적용
        if getattr(self.app, 'current_image', None) == image:
            self.app.current_tags = list(tags)
            print(f"[TM] current_tags 동기화: {self.app.current_tags}")
            
            # UI 업데이트 강제 실행
            if hasattr(self.app, 'update_current_tags_display'):
                self.app.update_current_tags_display()
                print(f"[TM] UI 업데이트 완료")

    def _process_stylesheet_change(self, ch, is_redo):
        """스타일시트 에디터 작업 처리"""
        ctype = ch.get("type")
        
        if not hasattr(self.app, 'tag_stylesheet_editor') or not self.app.tag_stylesheet_editor:
            return
        
        if ctype == "tag_stylesheet_remove":
            tag = ch.get("tag")
            if tag:
                if is_redo:
                    # 태그를 제거
                    if tag in self.app.tag_stylesheet_editor.selected_tags:
                        self.app.tag_stylesheet_editor.selected_tags.remove(tag)
                        # UI 업데이트
                        self.app.tag_stylesheet_editor.schedule_update()
                else:
                    # 태그를 복구
                    before_tags = ch.get("before", [])
                    if tag in before_tags and tag not in self.app.tag_stylesheet_editor.selected_tags:
                        self.app.tag_stylesheet_editor.selected_tags.append(tag)
                        # UI 업데이트
                        self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype == "tag_stylesheet_reorder":
            if is_redo:
                # 순서 변경 적용
                after_tags = ch.get("after", [])
                self.app.tag_stylesheet_editor.selected_tags = after_tags.copy()
                # UI 업데이트
                self.app.tag_stylesheet_editor.rebuild_flow_layout()
            else:
                # 순서 복구
                before_tags = ch.get("before", [])
                self.app.tag_stylesheet_editor.selected_tags = before_tags.copy()
                # UI 업데이트
                self.app.tag_stylesheet_editor.rebuild_flow_layout()
    
    def _process_global_change(self, ch, is_redo):
        """전역 작업 처리"""
        ctype = ch.get("type")
        
        if ctype == "global_tag_remove":
            tag = ch.get("tag")
            if tag:
                if is_redo:
                    # 전역 태그 삭제 적용
                    self.app.all_tags = ch.get("after_all_tags", {}).copy()
                    self.app.current_tags = ch.get("after_current_tags", []).copy()
                    self.app.removed_tags = ch.get("after_removed_tags", []).copy()
                    self.app.global_tag_stats = ch.get("after_global_tag_stats", {}).copy()
                else:
                    # 전역 태그 삭제 복구
                    self.app.all_tags = ch.get("before_all_tags", {}).copy()
                    self.app.current_tags = ch.get("before_current_tags", []).copy()
                    self.app.removed_tags = ch.get("before_removed_tags", []).copy()
                    self.app.global_tag_stats = ch.get("before_global_tag_stats", {}).copy()
                
                # 전역 작업이므로 UI 업데이트
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
                if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                    self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype in ("tag_replace", "bulk_tag_replace"):
            old_tags = ch.get("old_tags", [])
            new_tag = ch.get("new_tag", "")
            target_images = ch.get("target_images", [])
            if old_tags and new_tag:
                if is_redo:
                    # 태그 교체 적용
                    self.app.all_tags = ch.get("after_all_tags", {}).copy()
                    if hasattr(self.app, 'manual_tag_info'):
                        self.app.manual_tag_info = ch.get("after_manual_tag_info", {}).copy()
                else:
                    # 태그 교체 복구
                    self.app.all_tags = ch.get("before_all_tags", {}).copy()
                    if hasattr(self.app, 'manual_tag_info'):
                        self.app.manual_tag_info = ch.get("before_manual_tag_info", {}).copy()
                
                # 개별 이미지별로 current_tags 동기화
                if target_images and hasattr(self.app, 'current_image'):
                    for img_path in target_images:
                        if str(img_path) == str(self.app.current_image):
                            # 현재 이미지인 경우 current_tags 동기화
                            if str(img_path) in self.app.all_tags:
                                self.app.current_tags = self.app.all_tags[str(img_path)].copy()
                                print(f"[TM] 태그 교체 후 current_tags 동기화: {self.app.current_tags}")
                            break
                
                # 전역 작업이므로 UI 업데이트
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
                if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                    self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype == "tag_delete":
            old_tag = ch.get("old_tag", "")
            target_images = ch.get("target_images", [])
            if old_tag:
                if is_redo:
                    # 태그 삭제 적용
                    self.app.all_tags = ch.get("after_all_tags", {}).copy()
                else:
                    # 태그 삭제 복구
                    self.app.all_tags = ch.get("before_all_tags", {}).copy()
                
                # 개별 이미지별로 current_tags 동기화
                if target_images and hasattr(self.app, 'current_image'):
                    for img_path in target_images:
                        if str(img_path) == str(self.app.current_image):
                            # 현재 이미지인 경우 current_tags 동기화
                            if str(img_path) in self.app.all_tags:
                                self.app.current_tags = self.app.all_tags[str(img_path)].copy()
                                print(f"[TM] 태그 삭제 후 current_tags 동기화: {self.app.current_tags}")
                            break
                
                # 전역 작업이므로 UI 업데이트
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
                if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                    self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype == "tag_insert_relative":
            new_tag = ch.get("new_tag", "")
            target_images = ch.get("target_images", [])
            if new_tag:
                if is_redo:
                    # 태그 삽입 적용
                    self.app.all_tags = ch.get("after_all_tags", {}).copy()
                else:
                    # 태그 삽입 복구
                    self.app.all_tags = ch.get("before_all_tags", {}).copy()
                
                # 개별 이미지별로 current_tags 동기화
                if target_images and hasattr(self.app, 'current_image'):
                    for img_path in target_images:
                        if str(img_path) == str(self.app.current_image):
                            # 현재 이미지인 경우 current_tags 동기화
                            if str(img_path) in self.app.all_tags:
                                self.app.current_tags = self.app.all_tags[str(img_path)].copy()
                                print(f"[TM] 태그 삽입 후 current_tags 동기화: {self.app.current_tags}")
                            break
                
                # 전역 작업이므로 UI 업데이트
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
                if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                    self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype in ("tag_position_change", "bulk_tag_position_change"):
            move_tags = ch.get("move_tags", [])
            position_type = ch.get("position_type", "")
            target_images = ch.get("target_images", [])
            if move_tags and position_type:
                if is_redo:
                    # 태그 위치 변경 적용
                    self.app.all_tags = ch.get("after_all_tags", {}).copy()
                else:
                    # 태그 위치 변경 복구
                    self.app.all_tags = ch.get("before_all_tags", {}).copy()
                
                # 개별 이미지별로 current_tags 동기화
                if target_images and hasattr(self.app, 'current_image'):
                    for img_path in target_images:
                        if str(img_path) == str(self.app.current_image):
                            # 현재 이미지인 경우 current_tags 동기화
                            if str(img_path) in self.app.all_tags:
                                self.app.current_tags = self.app.all_tags[str(img_path)].copy()
                                print(f"[TM] 태그 위치 변경 후 current_tags 동기화: {self.app.current_tags}")
                            break
                
                # 전역 작업이므로 UI 업데이트
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
                if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                    self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype == "global_tag_stats_cleared":
            before_stats = ch.get("before", {})
            if before_stats:
                if is_redo:
                    # Redo: 전역 태그 통계 클리어
                    self.app.global_tag_stats.clear()
                else:
                    # Undo: 전역 태그 통계 복구
                    self.app.global_tag_stats = dict(before_stats)
                
                # 전역 작업이므로 UI 업데이트
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
                if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                    self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype == "tag_append_edge":
            new_tag = ch.get("new_tag", "")
            target_images = ch.get("target_images", [])
            if new_tag:
                if is_redo:
                    # 태그 가장자리 추가 적용
                    self.app.all_tags = ch.get("after_all_tags", {}).copy()
                else:
                    # 태그 가장자리 추가 복구
                    self.app.all_tags = ch.get("before_all_tags", {}).copy()
                
                # 개별 이미지별로 current_tags 동기화
                if target_images and hasattr(self.app, 'current_image'):
                    for img_path in target_images:
                        if str(img_path) == str(self.app.current_image):
                            # 현재 이미지인 경우 current_tags 동기화
                            if str(img_path) in self.app.all_tags:
                                self.app.current_tags = self.app.all_tags[str(img_path)].copy()
                                print(f"[TM] 태그 가장자리 추가 후 current_tags 동기화: {self.app.current_tags}")
                            break
                
                # 전역 작업이므로 UI 업데이트
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
                if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                    self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype == "clear_all_metadata":
            # 메타데이터 복원/적용
            if is_redo:
                # Redo: 메타데이터 클리어
                if hasattr(self.app, 'manual_tag_info'):
                    self.app.manual_tag_info = ch.get("after_manual_tag_info", {}).copy()
                if hasattr(self.app, 'tag_confidence'):
                    self.app.tag_confidence = ch.get("after_tag_confidence", {}).copy()
                if hasattr(self.app, 'llava_tag_info'):
                    self.app.llava_tag_info = ch.get("after_llava_tag_info", {}).copy()
            else:
                # Undo: 메타데이터 복구
                if hasattr(self.app, 'manual_tag_info'):
                    self.app.manual_tag_info = ch.get("before_manual_tag_info", {}).copy()
                if hasattr(self.app, 'tag_confidence'):
                    self.app.tag_confidence = ch.get("before_tag_confidence", {}).copy()
                if hasattr(self.app, 'llava_tag_info'):
                    self.app.llava_tag_info = ch.get("before_llava_tag_info", {}).copy()
        
        elif ctype == "clear_all_tags_complete":
            # 전체 상태를 한 번에 복원/적용
            if is_redo:
                # Redo: 클리어올 적용 (모든 상태를 비움)
                self.app.all_tags = ch.get("after", {}).get("all_tags", {}).copy()
                self.app.current_tags = ch.get("after", {}).get("current_tags", []).copy()
                self.app.removed_tags = ch.get("after", {}).get("removed_tags", []).copy()
                self.app.global_tag_stats = ch.get("after", {}).get("global_tag_stats", {}).copy()
                
                # 추가 상태들도 복원
                if hasattr(self.app, 'tag_confidence'):
                    self.app.tag_confidence = ch.get("after", {}).get("tag_confidence", {}).copy()
                if hasattr(self.app, 'manual_tag_info'):
                    self.app.manual_tag_info = ch.get("after", {}).get("manual_tag_info", {}).copy()
                if hasattr(self.app, 'llava_tag_info'):
                    self.app.llava_tag_info = ch.get("after", {}).get("llava_tag_info", {}).copy()
            else:
                # Undo: 클리어올 복구 (이전 상태로 복원)
                self.app.all_tags = ch.get("before", {}).get("all_tags", {}).copy()
                self.app.current_tags = ch.get("before", {}).get("current_tags", []).copy()
                self.app.removed_tags = ch.get("before", {}).get("removed_tags", []).copy()
                self.app.global_tag_stats = ch.get("before", {}).get("global_tag_stats", {}).copy()
                
                # 추가 상태들도 복원
                if hasattr(self.app, 'tag_confidence'):
                    self.app.tag_confidence = ch.get("before", {}).get("tag_confidence", {}).copy()
                if hasattr(self.app, 'manual_tag_info'):
                    self.app.manual_tag_info = ch.get("before", {}).get("manual_tag_info", {}).copy()
                if hasattr(self.app, 'llava_tag_info'):
                    self.app.llava_tag_info = ch.get("before", {}).get("llava_tag_info", {}).copy()
            
            # UI 업데이트
            if hasattr(self.app, 'update_current_tags_display'):
                self.app.update_current_tags_display()
            if hasattr(self.app, 'update_tag_stats'):
                self.app.update_tag_stats()
            if hasattr(self.app, 'update_tag_tree'):
                self.app.update_tag_tree()
            if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                self.app.tag_stylesheet_editor.schedule_update()
        
        elif ctype == "clear_all_tags":
            image_name = ch.get("image", "")
            before_tags = ch.get("before", [])
            before_image_removed_tags = ch.get("before_image_removed_tags", [])
            if before_tags and image_name:
                # 이미지 경로 복원 (파일명 -> 전체 경로)
                image = None
                if Path(image_name).exists():
                    image = image_name
                else:
                    # all_tags에서 파일명으로 찾기 (클리어올 후에는 비어있을 수 있음)
                    for img_path in self.app.all_tags.keys():
                        if Path(img_path).name == image_name:
                            image = img_path
                            break
                    
                    # all_tags에서 못 찾으면 현재 이미지와 비교
                    if not image and hasattr(self.app, 'current_image') and self.app.current_image:
                        if Path(self.app.current_image).name == image_name:
                            image = self.app.current_image
                    
                    # 여전히 못 찾으면 문자열 키로 직접 매칭 시도
                    if not image and image_name in self.app.all_tags:
                        image = image_name
                
                if not image:
                    print(f"[TM WARNING] clear_all_tags: 이미지를 찾을 수 없음: {image_name}")
                    print(f"[TM DEBUG] all_tags 키들: {list(self.app.all_tags.keys())[:5]}...")
                    return
                
                # all_tags 관리 플러그인 사용
                from all_tags_manager import get_tags_for_image, set_tags_for_image
                
                # 클리어올 후에는 all_tags에 이미지가 없을 수 있으므로 먼저 추가
                if image not in self.app.all_tags:
                    self.app.all_tags[image] = []
                
                tags = get_tags_for_image(self.app, image)
                
                if is_redo:
                    # Redo: 클리어올 적용 (모든 태그를 제거)
                    for tag in before_tags:
                        if tag in tags:
                            tags.remove(tag)
                            self._global_remove(image, tag)
                    set_tags_for_image(self.app, image, tags)
                    # 클리어올 시 이미지별 리무버 태그도 비움
                    if hasattr(self.app, 'image_removed_tags'):
                        try:
                            self.app.image_removed_tags[image] = []
                        except Exception:
                            pass
                else:
                    # Undo: 클리어올 복구 (이전 태그들을 복원)
                    for tag in before_tags:
                        if tag not in tags:
                            tags.append(tag)
                            self._global_add(image, tag)
                    set_tags_for_image(self.app, image, tags)
                    # 이미지별 리무버 태그도 복구
                    if hasattr(self.app, 'image_removed_tags'):
                        try:
                            self.app.image_removed_tags[image] = list(before_image_removed_tags)
                        except Exception:
                            pass
                
                # 현재 이미지인 경우 current_tags 및 removed_tags/UI 보정
                if getattr(self.app, 'current_image', None) == image:
                    self.app.current_tags = list(tags)
                    # UI 일관성: 현재 이미지의 removed_tags를 이미지별 값으로 동기화
                    if hasattr(self.app, 'removed_tags'):
                        try:
                            self.app.removed_tags = list(self.app.image_removed_tags.get(image, []))
                        except Exception:
                            self.app.removed_tags = []
                
                # 전역 작업이므로 UI 업데이트
                if hasattr(self.app, 'update_current_tags_display'):
                    self.app.update_current_tags_display()
                if hasattr(self.app, 'update_tag_stats'):
                    self.app.update_tag_stats()
                if hasattr(self.app, 'update_tag_tree'):
                    self.app.update_tag_tree()
                if hasattr(self.app, 'tag_stylesheet_editor') and self.app.tag_stylesheet_editor:
                    self.app.tag_stylesheet_editor.schedule_update()

    # ── Global Tag Stats helpers (image-level sync with all_tags) ───────────────────────
    # 이제 글로벌 태그 관리 플러그인을 사용하므로 헬퍼 함수들은 제거됨

    def _global_add(self, image: str, tag: str):
        if not tag:
            return
        # 글로벌 태그 관리 플러그인 사용
        from global_tag_manager import add_global_tag
        add_global_tag(self.app, tag, False)

    
    def _global_remove(self, image: str, tag: str):
        if not tag:
            return
        # 글로벌 태그 관리 플러그인 사용
        from global_tag_manager import remove_global_tag
        remove_global_tag(self.app, tag)
    
    def _global_rename(self, image: str, src: str, dst: str):
        if not src or not dst or src == dst:
            return
        # 글로벌 태그 관리 플러그인 사용
        from global_tag_manager import edit_global_tag
        edit_global_tag(self.app, src, dst)
    
    def _global_apply_snapshot(self, image: str, before_list, after_list):
        try:
            before = set(before_list or [])
            after = set(after_list or [])
            # 글로벌 태그 관리 플러그인 사용
            from global_tag_manager import add_global_tag, remove_global_tag
            for t in (after - before):
                add_global_tag(self.app, str(t), False)
            for t in (before - after):
                remove_global_tag(self.app, str(t))
        except Exception:
            pass
    
    # UI Components
    def __del__(self):
        if TM:
            try:
                h = getattr(self, "_tm_handler", None)
                if h: TM.unsubscribe(h)
            except Exception:
                pass


class Avatar(QWidget):
    def __init__(self, initial, color, size=28, parent=None):
        super().__init__(parent)
        self.initial = initial[:1]
        self.color = QColor(color)
        self.setFixedSize(size, size)
    
    def set_color(self, color):
        """Update avatar color dynamically"""
        self.color = QColor(color)
        self.update()
    
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self.color)
        p.drawEllipse(self.rect())
        p.setPen(Qt.white)
        p.setFont(QFont("Inter", 10, QFont.DemiBold))
        p.drawText(self.rect(), Qt.AlignCenter, self.initial.upper())

class EventCard(QFrame):
    action_clicked = Signal(int)
    branch_switched = Signal(int, int)  # (record_index, branch_idx)
    
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.index = data.get("index", 0)
        self.is_applied = data.get("status") == "Applied"
        self.branches_info = data.get("branches", [])
        self.operation_type = data.get("operation_type", "system")
        self.operation_color = data.get("operation_color", "#9C27B0")
        
        # 태그 정보 저장 (상태 텍스트에 표시용)
        self.tag_info = ""
        if "status" in data and isinstance(data["status"], str) and " " in data["status"]:
            # status에 태그 정보가 포함된 경우 (예: "적용됨 태그추가: 'tag'")
            parts = data["status"].split(" ", 1)
            if len(parts) > 1:
                self.tag_info = parts[1]  # "태그추가: 'tag'" 부분
        
        bg_color = COLORS['card_bg'] if self.is_applied else COLORS['card_bg_undone']
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border: 1px solid transparent;
                border-radius: 8px;
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(6)
        
        # Main card content
        card_row = QHBoxLayout()
        card_row.setSpacing(10)
        
        # Avatar - 작업 유형별 색상 적용
        avatar_color = self.operation_color if self.is_applied else "#999999"
        self.avatar = Avatar(data.get("who", "S")[:1], avatar_color)
        card_row.addWidget(self.avatar, 0, Qt.AlignTop)
        
        # Content
        content = QVBoxLayout()
        content.setSpacing(4)
        
        # Title row with action button
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        title = QLabel(f"<b>{data.get('who', '')}</b> {data.get('body', '')}")
        title.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 12px;")
        title.setWordWrap(True)
        title_row.addWidget(title, 1)
        
        # Action button
        self.action_btn = QPushButton("↶ Undo" if self.is_applied else "↷ Redo")
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['btn_undo'] if self.is_applied else COLORS['btn_redo']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        self.action_btn.setFixedHeight(24)
        self.action_btn.clicked.connect(lambda: self.action_clicked.emit(self.index))
        title_row.addWidget(self.action_btn, 0, Qt.AlignTop)
        
        content.addLayout(title_row)
        
        # Status
        self.status = QLabel(data.get("status", ""))
        self.status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        content.addWidget(self.status)
        
        card_row.addLayout(content, 1)
        main_layout.addLayout(card_row)
        
        # Branch navigator (only if multiple branches exist at this position)
        if len(self.branches_info) > 1:
            branch_nav = CardBranchNavigator(self.index, self.branches_info)
            branch_nav.branch_changed.connect(self._on_branch_changed)
            self.branch_navigator = branch_nav
            
            # Add separator and branch nav
            separator = QFrame()
            separator.setFixedHeight(1)
            separator.setStyleSheet(f"""
                QFrame {{
                    background-color: #E1E7EE;
                    border: none;
                    margin: 10px 20px;
                }}
            """)
            main_layout.addWidget(separator)
            
            branch_container = QHBoxLayout()
            branch_container.setContentsMargins(0, 4, 0, 0)
            branch_label = QLabel("Branches:")
            branch_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            branch_container.addWidget(branch_label)
            branch_container.addWidget(branch_nav)
            branch_container.addStretch()
            main_layout.addLayout(branch_container)
        else:
            self.branch_navigator = None
        
        self.adjustSize()
    
    def _on_branch_changed(self, record_index, branch_idx):
        self.branch_switched.emit(record_index, branch_idx)
    
    def update_branch_navigator(self, current_branch_idx):
        """Update the branch navigator to reflect the current branch"""
        if self.branch_navigator:
            self.branch_navigator.set_current_branch(current_branch_idx)
    
    def update_state(self, is_applied, is_active_branch=True):
        self.is_applied = is_applied
        bg_color = COLORS['card_bg'] if is_applied else COLORS['card_bg_undone']
        
        # Update background
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border: 1px solid transparent;
                border-radius: 8px;
            }}
        """)
        
        # Update button
        self.action_btn.setText("↶ Undo" if is_applied else "↷ Redo")
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['btn_undo'] if is_applied else COLORS['btn_redo']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
        """)
        
        # Undo 버튼은 활성 분기에서만 표시 (Redo는 모든 분기에서 표시)
        if is_applied:  # Undo 버튼
            self.action_btn.setVisible(is_active_branch)
            self.action_btn.setEnabled(is_active_branch)
        else:  # Redo 버튼
            self.action_btn.setVisible(True)
            self.action_btn.setEnabled(True)
        
        # Update avatar color - 작업 유형별 색상 유지
        avatar_color = self.operation_color if is_applied else "#999999"
        self.avatar.set_color(avatar_color)
        
        # Update status text with tag info
        status_text = "(적용됨)" if is_applied else "(취소됨)"
        
        # 태그 정보가 있으면 추가
        if hasattr(self, 'tag_info') and self.tag_info:
            status_text += f" {self.tag_info}"
        
        self.status.setText(status_text)

class Timeline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = []  # [(label, y, is_applied)]
        self.setFixedWidth(20)  # 라인만 그리므로 좁게
    
    def set_entries(self, entries):
        self.entries = entries
        self.update()
    
    def paintEvent(self, e):
        if not self.entries:
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Draw lines
        for i in range(len(self.entries)-1):
            _, y1, is_applied1 = self.entries[i]
            _, y2, is_applied2 = self.entries[i+1]
            
            pen = QPen(QColor(COLORS['line_gray']), 2)
            if not is_applied1 or not is_applied2:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawLine(QPoint(10, y1), QPoint(10, y2))
        
        # Draw dots
        for label, y, is_applied in self.entries:
            dot_color = QColor(COLORS['dot_blue'] if is_applied else COLORS['dot_gray'])
            p.setBrush(dot_color)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPoint(10, y), 5, 5)

class TimeLabels(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = []  # [(label, y, is_applied)]
        self.setFixedWidth(160)  # 시간 라벨용 - 새로운 포맷에 맞게 증가
    
    def set_entries(self, entries):
        self.entries = entries
        self.update()
    
    def paintEvent(self, e):
        if not self.entries:
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Draw time labels
        for label, y, is_applied in self.entries:
            p.setPen(QColor(COLORS['text_muted']))
            p.setFont(QFont("Consolas", 10))  # 고정폭 폰트로 변경
            p.drawText(QRect(0, y-10, 160, 20), Qt.AlignCenter | Qt.AlignVCenter, label)
class TimeMachinePanel(QWidget):
    def __init__(self, tm_instance, parent=None):
        super().__init__(parent)
        self.tm = tm_instance
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(0)
        
        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        layout.addWidget(self.scroll, 1)
        
        # Viewport - 이 안에 timeline, time_labels, cards를 모두 넣기
        self.viewport = QWidget()
        self.scroll.setWidget(self.viewport)
        
        # Viewport layout - 가로로 배치
        viewport_layout = QHBoxLayout(self.viewport)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(8)
        
        # Timeline (라인만)
        self.timeline = Timeline()
        viewport_layout.addWidget(self.timeline)
        
        # Time Labels (시간 레이블)
        self.time_labels = TimeLabels()
        viewport_layout.addWidget(self.time_labels)
        
        # Cards container
        cards_container = QWidget()
        self.stack = QVBoxLayout(cards_container)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.stack.setSpacing(12)
        self.stack.addStretch()
        viewport_layout.addWidget(cards_container, 1)
        
        self.cards = []  # [(card_widget, data)]
        
        # Auto-refresh on scroll and resize
        self.scroll.verticalScrollBar().valueChanged.connect(self._refresh)
        self.viewport.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if obj == self.viewport and event.type() in (QEvent.Resize, QEvent.Show):
            QTimer.singleShot(50, self._refresh)
        return super().eventFilter(obj, event)
    
    def clear_cards(self):
        while self.stack.count() > 0:
            item = self.stack.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self.cards.clear()
        self.stack.addStretch()
        QApplication.processEvents()
        QTimer.singleShot(50, self._refresh)
    
    def remove_cards_from(self, from_index):
        """Remove all cards from a specific index onward"""
        to_remove = []
        for card_widget, data in self.cards:
            if data["index"] >= from_index:
                to_remove.append((card_widget, data))
        
        for card_widget, data in to_remove:
            self.cards.remove((card_widget, data))
            self.stack.removeWidget(card_widget)
            card_widget.setParent(None)
        
        QApplication.processEvents()
        QTimer.singleShot(50, self._refresh)
    
    def add_card(self, data):
        # Remove stretch
        if self.stack.count() > 0:
            self.stack.takeAt(self.stack.count()-1)
        
        card = EventCard(data)
        card.action_clicked.connect(
            lambda _=None, rec=data["record"]: self.tm.jump_to(self.tm._timeline.index(rec))
        )
        card.branch_switched.connect(self._on_branch_switched)
        
        self.cards.append((card, data))
        self.stack.addWidget(card)
        self.stack.addStretch()
        
        QApplication.processEvents()
        QTimer.singleShot(100, self._refresh)
    
    def _on_branch_switched(self, record_index, branch_idx):
        """Handle branch switch from a card"""
        self.tm.switch_to_branch_at_position(record_index, branch_idx)
    
    def update_states(self, current_index):
        """Update all cards' states based on current timeline position"""
        is_active_branch = (self.tm._viewing_branch == self.tm._active_branch)
        for card_widget, data in self.cards:
            try:
                card_index = self.tm._timeline.index(data["record"])
            except ValueError:
                continue
            
            # 분기 전환 시 올바른 상태 계산
            is_applied = card_index <= current_index
            card_widget.update_state(is_applied, is_active_branch)
            # Update branch navigator to show current VIEWING branch
            card_widget.update_branch_navigator(self.tm._viewing_branch)
        self._refresh()
    
    def update_states_with_branch_point(self, current_index, branch_point):
        """Update card states considering branch point - 분기점 이전은 모두 활성화"""
        is_active_branch = (self.tm._viewing_branch == self.tm._active_branch)
        for card_widget, data in self.cards:
            try:
                card_index = self.tm._timeline.index(data["record"])
            except ValueError:
                continue
            
            # 분기점 이전의 카드들은 모두 활성화, 이후는 현재 인덱스에 따라
            if card_index < branch_point:
                is_applied = True  # 분기점 이전은 모두 활성화
            else:
                is_applied = card_index <= current_index  # 분기점 이후는 현재 진행 상태에 따라
            
            card_widget.update_state(is_applied, is_active_branch)
            # Update branch navigator to show current VIEWING branch
            card_widget.update_branch_navigator(self.tm._viewing_branch)
        self._refresh()
    
    def _refresh(self):
        if not self.cards:
            return
        
        entries = []
        for card_widget, data in self.cards:
            pos = card_widget.pos()
            height = card_widget.height()
            center_y = pos.y() + height // 2
            
            time_label = data.get("time", "")
            is_applied = card_widget.is_applied
            entries.append((time_label, center_y, is_applied))
        
        self.timeline.set_entries(entries)
        self.time_labels.set_entries(entries)