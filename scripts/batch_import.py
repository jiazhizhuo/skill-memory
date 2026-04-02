#!/usr/bin/env python3
"""
批量导入所有 session 对话到 skill-memory

功能：
1. 遍历所有 session 文件
2. 提取对话内容
3. 调用 hook 组件自动过滤和保存
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from hooks.mem0_memory_hook import Mem0MemoryHook
from src.mem0_client import Mem0Client


def extract_messages_from_session(session_file):
    """从 session 文件提取对话"""
    messages = []
    
    try:
        with open(session_file, 'r', errors='ignore') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    ts = data.get('timestamp', '')
                    if not ts:
                        continue
                    
                    # 解析 message 字段
                    msg_str = data.get('message', '')
                    if not msg_str:
                        continue
                    
                    msg_data = json.loads(msg_str) if isinstance(msg_str, str) else msg_str
                    role = msg_data.get('role', '')
                    content_list = msg_data.get('content', [])
                    
                    # 提取文本内容
                    text = ''
                    if isinstance(content_list, list):
                        for c in content_list:
                            if isinstance(c, dict) and c.get('type') == 'text':
                                text += c.get('text', '')
                    elif isinstance(content_list, str):
                        text = content_list
                    
                    if text and role in ('user', 'assistant'):
                        # 清理 workspace path 等元信息
                        text = clean_message(text)
                        messages.append({
                            'ts': ts,
                            'role': role,
                            'text': text,
                            'session': os.path.basename(session_file)
                        })
                except:
                    pass
    except Exception as e:
        print(f"  Error reading {session_file}: {e}")
    
    return messages


def clean_message(text):
    """清理消息中的元信息"""
    # 移除 workspace path 行
    lines = text.split('\n')
    cleaned_lines = []
    skip_next = False
    
    for line in lines:
        if 'Workspace Path:' in line:
            continue
        if 'You are operating in a worktree' in line:
            continue
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def batch_import():
    """批量导入所有 session"""
    
    # 初始化 hook
    print("初始化 skill-memory hook...")
    hook = Mem0MemoryHook()
    hook.hook_config.verbose = False
    
    # session 文件目录
    base_dir = Path.home() / "Library/Application Support/Qoder/SharedClientCache/cli/projects"
    
    # 收集所有 session 文件
    session_files = []
    for root, dirs, files in os.walk(base_dir):
        for fname in files:
            if fname.endswith('.session.execution.jsonl'):
                fpath = os.path.join(root, fname)
                # 跳过空文件
                if os.path.getsize(fpath) > 1000:
                    session_files.append(fpath)
    
    print(f"找到 {len(session_files)} 个 session 文件")
    print()
    
    # 统计
    total_messages = 0
    saved_count = 0
    skipped_count = 0
    error_count = 0
    
    # 处理每个 session
    for i, session_file in enumerate(session_files):
        session_name = os.path.basename(session_file)[:30]
        print(f"[{i+1}/{len(session_files)}] {session_name}...", end=" ")
        
        messages = extract_messages_from_session(session_file)
        
        if not messages:
            print("无对话")
            continue
        
        print(f"{len(messages)} 条消息...", end=" ")
        total_messages += len(messages)
        
        # 按 user-assistant 对组合
        paired_messages = pair_messages(messages)
        
        # 保存每对对话
        for user_msg, assistant_msg in paired_messages:
            try:
                event_data = {
                    "event": "AgentResponseComplete",
                    "user_message": user_msg['text'] if user_msg else "",
                    "assistant_message": assistant_msg['text'] if assistant_msg else "",
                    "session_key": user_msg['session'] if user_msg else assistant_msg['session'] if assistant_msg else "unknown",
                    "timestamp": user_msg['ts'] if user_msg else assistant_msg['ts'] if assistant_msg else ""
                }
                
                result = hook.run(event_data)
                saved_count += result.get('saved', 0)
                skipped_count += result.get('skipped', 0)
                
            except Exception as e:
                error_count += 1
        
        print(f"✓ saved={saved_count%100}")
    
    print()
    print("=" * 50)
    print(f"导入完成！")
    print(f"  总消息数: {total_messages}")
    print(f"  保存数: {saved_count}")
    print(f"  跳过数: {skipped_count}")
    print(f"  错误数: {error_count}")


def pair_messages(messages):
    """将 user 和 assistant 消息配对"""
    pairs = []
    current_user = None
    current_assistant = None
    
    for msg in messages:
        if msg['role'] == 'user':
            # 保存之前的配对
            if current_user is not None or current_assistant is not None:
                pairs.append((current_user, current_assistant))
            current_user = msg
            current_assistant = None
        elif msg['role'] == 'assistant':
            current_assistant = msg
    
    # 保存最后一对
    if current_user is not None or current_assistant is not None:
        pairs.append((current_user, current_assistant))
    
    return pairs


if __name__ == "__main__":
    batch_import()
