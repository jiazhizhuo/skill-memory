#!/usr/bin/env python3
"""
Qdrant 健康检查与自动启动模块

功能：
1. 检查 Qdrant 是否运行
2. 如果未运行，自动启动
3. 启动失败时提供清晰的错误信息
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple


class QdrantMonitor:
    """Qdrant 健康检查与自动启动"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化
        
        Args:
            config_path: Qdrant 配置文件路径，默认使用 ~/.qdrant/config/production.yaml
        """
        self.config_path = config_path or str(Path.home() / ".qdrant" / "config" / "production.yaml")
        self.qdrant_binary = str(Path.home() / "bin" / "qdrant")
        self.log_path = str(Path.home() / "qdrant.log")
        self.host = "localhost"
        self.port = 6333
        
    def check_health(self) -> bool:
        """
        检查 Qdrant 是否健康运行
        
        Returns:
            True if Qdrant is running and healthy
        """
        import urllib.request
        import urllib.error
        
        url = f"http://{self.host}:{self.port}/health"
        
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, Exception):
            return False
    
    def is_process_running(self) -> bool:
        """检查 Qdrant 进程是否在运行"""
        try:
            result = subprocess.run(
                ["pgrep", "-x", "qdrant"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False
    
    def start_qdrant(self) -> Tuple[bool, str]:
        """
        启动 Qdrant 服务
        
        Returns:
            (success, message) tuple
        """
        # 检查二进制文件是否存在
        if not os.path.exists(self.qdrant_binary):
            return False, f"Qdrant binary not found at {self.qdrant_binary}"
        
        # 检查配置文件是否存在
        if not os.path.exists(self.config_path):
            return False, f"Config file not found at {self.config_path}"
        
        try:
            # 使用 nohup 后台启动
            cmd = [
                "nohup",
                self.qdrant_binary,
                "--config-path",
                self.config_path
            ]
            
            # 重定向输出到日志文件
            with open(self.log_path, "a") as log_file:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=log_file,
                    start_new_session=True,
                    cwd=str(Path.home())
                )
            
            # 等待启动（逐步检查，最多等待 15 秒）
            print(f"⏳ Waiting for Qdrant to start (PID: {process.pid})...", file=sys.stderr)
            for i in range(15):
                time.sleep(1)
                if self.check_health():
                    return True, f"Qdrant started successfully (PID: {process.pid})"
                
                # 检查进程是否还在运行
                if not self.is_process_running():
                    return False, "Qdrant process failed to start (check logs)"
            
            # 超时但进程还在运行
            if self.is_process_running():
                return False, "Qdrant is starting but needs more time (wait manually)"
            else:
                return False, "Qdrant process disappeared during startup"
                    
        except PermissionError:
            return False, f"Permission denied: cannot execute {self.qdrant_binary}"
        except FileNotFoundError:
            return False, f"Command not found: {self.qdrant_binary}"
        except Exception as e:
            return False, f"Failed to start Qdrant: {str(e)}"
    
    def ensure_running(self, auto_start: bool = True) -> Tuple[bool, str]:
        """
        确保 Qdrant 正在运行
        
        Args:
            auto_start: 如果未运行，是否自动启动
            
        Returns:
            (success, message) tuple
        """
        # 先检查健康状态
        if self.check_health():
            return True, "Qdrant is running and healthy"
        
        # 检查进程是否存在（可能端口还未开放）
        if self.is_process_running():
            # 进程在运行但健康检查失败，等待重试
            for i in range(3):
                time.sleep(2)
                if self.check_health():
                    return True, "Qdrant is running (delayed health check passed)"
            return False, "Qdrant process exists but health check failed"
        
        # Qdrant 未运行
        if not auto_start:
            return False, "Qdrant is not running (auto-start disabled)"
        
        # 尝试自动启动
        print("⚠️  Qdrant is not running, attempting to start...", file=sys.stderr)
        success, message = self.start_qdrant()
        
        if success:
            print(f"✓ {message}", file=sys.stderr)
        else:
            print(f"✗ {message}", file=sys.stderr)
            print("\n📝 Troubleshooting tips:", file=sys.stderr)
            print("  1. Check if port 6333 is already in use", file=sys.stderr)
            print("  2. Verify Qdrant binary exists and is executable", file=sys.stderr)
            print("  3. Check logs at:", self.log_path, file=sys.stderr)
            print("  4. Try manual start:", f"`{self.qdrant_binary} --config-path {self.config_path}`", file=sys.stderr)
        
        return success, message


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Qdrant health check and auto-start")
    parser.add_argument("--config", type=str, help="Path to Qdrant config file")
    parser.add_argument("--no-auto-start", action="store_true", help="Disable auto-start")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    monitor = QdrantMonitor(config_path=args.config)
    success, message = monitor.ensure_running(auto_start=not args.no_auto_start)
    
    if args.json:
        import json
        print(json.dumps({
            "status": "ok" if success else "error",
            "message": message
        }))
    else:
        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
            sys.exit(1)


if __name__ == "__main__":
    main()
