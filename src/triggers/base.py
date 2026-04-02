"""
Trigger Mechanism Abstraction

支持多种触发方式：
- stdin: 从 stdin 读取 JSON 数据（Qoder Hook 风格）
- file: 监控文件变化
- api: HTTP API 触发（OpenClaw）
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
import json
import sys

# 添加 src 到路径
from pathlib import Path
_src_path = Path(__file__).parent.parent
if _src_path not in __import__('sys').path:
    __import__('sys').path.insert(0, str(_src_path))

from platforms.base import MemoryEvent


class Trigger(ABC):
    """触发器基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """触发器名称"""
        pass
    
    @abstractmethod
    def listen(self, callback: Callable[[List[MemoryEvent]], None]) -> None:
        """监听事件，触发回调
        
        Args:
            callback: 事件回调函数，接收事件列表
        """
        pass
    
    def stop(self) -> None:
        """停止监听"""
        pass


class StdinTrigger(Trigger):
    """stdin 触发器
    
    从 stdin 读取 JSON 数据，适用于 Qoder Hook
    """
    
    def __init__(self, timeout: Optional[float] = None):
        self.timeout = timeout
        self._running = False
    
    @property
    def name(self) -> str:
        return "stdin"
    
    def listen(self, callback: Callable[[List[MemoryEvent]], None]) -> None:
        """从 stdin 读取并触发回调"""
        self._running = True
        
        try:
            # 读取 stdin
            if self.timeout:
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("stdin read timeout")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(self.timeout))
            
            input_data = sys.stdin.read()
            
            if self.timeout:
                signal.alarm(0)  # 取消超时
            
            if input_data.strip():
                events = self._parse_input(input_data)
                if events:
                    callback(events)
                    
        except TimeoutError:
            raise
        except Exception as e:
            print(f"StdinTrigger error: {e}", file=sys.stderr)
            raise
    
    def _parse_input(self, input_data: str) -> List[MemoryEvent]:
        """解析 stdin 输入"""
        events = []
        
        # 尝试解析 JSON
        try:
            data = json.loads(input_data)
            events.extend(self._json_to_events(data))
        except json.JSONDecodeError:
            # 尝试 JSONL 格式
            for line in input_data.strip().split("\n"):
                if line.strip():
                    try:
                        data = json.loads(line)
                        events.extend(self._json_to_events(data))
                    except:
                        pass
        
        return events
    
    def _json_to_events(self, data: Dict[str, Any]) -> List[MemoryEvent]:
        """将 JSON 数据转换为事件"""
        events = []
        
        # Qoder Hook 格式
        if "prompt" in data:
            events.append(MemoryEvent(
                event_type="user_message",
                content=data["prompt"],
                session_id=data.get("session_id"),
                metadata={"source": "stdin", "format": "qoder"},
                raw_data=data
            ))
        
        # transcript 格式
        if "type" in data:
            msg_type = data.get("type")
            if msg_type == "user":
                content = self._extract_text(data.get("message", {}))
                if content:
                    events.append(MemoryEvent(
                        event_type="user_message",
                        content=content,
                        session_id=data.get("sessionId"),
                        timestamp=data.get("timestamp"),
                        metadata={"source": "stdin", "format": "transcript"},
                        raw_data=data
                    ))
            elif msg_type == "assistant":
                content = self._extract_text(data.get("message", {}))
                if content:
                    events.append(MemoryEvent(
                        event_type="assistant_message",
                        content=content,
                        session_id=data.get("sessionId"),
                        timestamp=data.get("timestamp"),
                        metadata={"source": "stdin", "format": "transcript"},
                        raw_data=data
                    ))
        
        return events
    
    def _extract_text(self, message: Dict) -> str:
        """从消息中提取文本"""
        content = message.get("content", [])
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
                elif isinstance(item, str):
                    texts.append(item)
            return " ".join(texts)
        return ""


class FileWatcherTrigger(Trigger):
    """文件监控触发器
    
    监控文件变化，适用于 OpenClaw transcript 文件
    """
    
    def __init__(
        self,
        file_path: str,
        poll_interval: float = 1.0,
    ):
        self.file_path = file_path
        self.poll_interval = poll_interval
        self._running = False
        self._last_position = 0
    
    @property
    def name(self) -> str:
        return "file_watcher"
    
    def listen(self, callback: Callable[[List[MemoryEvent]], None]) -> None:
        """监控文件变化"""
        import time
        
        self._running = True
        
        while self._running:
            try:
                events = self._check_file()
                if events:
                    callback(events)
            except Exception as e:
                print(f"FileWatcher error: {e}", file=sys.stderr)
            
            time.sleep(self.poll_interval)
    
    def _check_file(self) -> List[MemoryEvent]:
        """检查文件变化"""
        events = []
        
        try:
            with open(self.file_path, "r") as f:
                # 跳到上次读取位置
                f.seek(self._last_position)
                
                # 读取新内容
                new_content = f.read()
                self._last_position = f.tell()
                
                # 解析新行
                for line in new_content.strip().split("\n"):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            events.append(MemoryEvent(
                                event_type="file_update",
                                content=str(data),
                                metadata={"source": "file", "path": self.file_path},
                                raw_data=data
                            ))
                        except:
                            pass
        except FileNotFoundError:
            pass
        
        return events
    
    def stop(self) -> None:
        self._running = False


class APITrigger(Trigger):
    """HTTP API 触发器
    
    提供 HTTP API 接口，适用于 OpenClaw 或其他系统集成
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        endpoint: str = "/memory",
    ):
        self.host = host
        self.port = port
        self.endpoint = endpoint
        self._server = None
    
    @property
    def name(self) -> str:
        return "api"
    
    def listen(self, callback: Callable[[List[MemoryEvent]], None]) -> None:
        """启动 HTTP 服务"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import threading
            
            trigger = self
            events_callback = callback
            
            class RequestHandler(BaseHTTPRequestHandler):
                def do_POST(self):
                    if self.path == trigger.endpoint:
                        content_length = int(self.headers.get("Content-Length", 0))
                        body = self.rfile.read(content_length)
                        
                        try:
                            data = json.loads(body)
                            events = trigger._parse_request(data)
                            
                            if events:
                                # 在后台线程中处理回调
                                threading.Thread(
                                    target=events_callback,
                                    args=(events,)
                                ).start()
                            
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "ok"}).encode())
                            
                        except Exception as e:
                            self.send_response(400)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": str(e)}).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    pass  # 禁用日志
            
            self._server = HTTPServer((self.host, self.port), RequestHandler)
            print(f"APITrigger listening on http://{self.host}:{self.port}{self.endpoint}")
            self._server.serve_forever()
            
        except ImportError:
            raise RuntimeError("HTTP server not available")
    
    def _parse_request(self, data: Dict) -> List[MemoryEvent]:
        """解析 HTTP 请求"""
        events = []
        
        if "content" in data:
            events.append(MemoryEvent(
                event_type="api_request",
                content=data["content"],
                session_id=data.get("session_id"),
                metadata={"source": "api"},
                raw_data=data
            ))
        elif "messages" in data:
            for msg in data["messages"]:
                events.append(MemoryEvent(
                    event_type=msg.get("type", "message"),
                    content=msg.get("content", ""),
                    session_id=data.get("session_id"),
                    metadata={"source": "api"},
                    raw_data=msg
                ))
        
        return events
    
    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
