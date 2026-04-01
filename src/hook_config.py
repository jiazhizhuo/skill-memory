#!/usr/bin/env python3
"""
Hook 配置加载器
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, List, Optional


class HookConfig:
    """Hook 配置类"""

    DEFAULT_CONFIG = {
        "hook": {
            "mode": "auto",
        },
        "filter": {
            "min_length": "30",
            "max_per_round": "5",
            "skip_patterns": "thanks,thank you,goodbye,bye,/stop,/help",
        },
        "memory": {
            "tier": "auto",
            "promotion_threshold": "0.75",
            "auto_categorize": "true",
        },
        "logging": {
            "level": "info",
            "verbose": "false",
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config = configparser.ConfigParser()

        if config_path:
            self.config_path = Path(config_path)
        else:
            # 默认路径
            skill_root = Path(__file__).parent.parent
            self.config_path = skill_root / "config" / "hook.toml"

        self._load()

    def _load(self):
        """加载配置文件"""
        if self.config_path.exists():
            self.config.read(self.config_path, encoding="utf-8")
        else:
            # 使用默认配置
            for section, options in self.DEFAULT_CONFIG.items():
                self.config[section] = options

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """获取配置值"""
        try:
            value = self.config.get(section, key)
            return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """获取整数配置"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """获取布尔配置"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_list(self, section: str, key: str, fallback: List[str] = None, separator: str = ",") -> List[str]:
        """获取列表配置"""
        value = self.get(section, key)
        if value is None:
            return fallback or []
        # 去掉首尾引号
        value = value.strip().strip('"').strip("'")
        return [item.strip() for item in value.split(separator) if item.strip()]

    @property
    def hook_mode(self) -> str:
        """获取 hook 模式"""
        return self.get("hook", "mode", "auto")

    @property
    def min_length(self) -> int:
        """获取最小内容长度"""
        return self.get_int("filter", "min_length", 30)

    @property
    def max_per_round(self) -> int:
        """获取每轮最大保存条数"""
        return self.get_int("filter", "max_per_round", 5)

    @property
    def skip_patterns(self) -> List[str]:
        """获取跳过模式列表"""
        return self.get_list("filter", "skip_patterns", ["thanks", "thank you"])

    @property
    def memory_tier(self) -> str:
        """获取记忆层级"""
        return self.get("memory", "tier", "auto")

    @property
    def promotion_threshold(self) -> float:
        """获取晋升阈值"""
        return self.get_float("memory", "promotion_threshold", 0.75)

    @property
    def auto_categorize(self) -> bool:
        """获取自动分类设置"""
        return self.get_bool("memory", "auto_categorize", True)

    @property
    def log_level(self) -> str:
        """获取日志级别"""
        return self.get("logging", "level", "info")

    @property
    def verbose(self) -> bool:
        """获取详细输出设置"""
        return self.get_bool("logging", "verbose", False)

    @verbose.setter
    def verbose(self, value: bool):
        """设置详细输出"""
        if "logging" not in self.config:
            self.config["logging"] = {}
        self.config["logging"]["verbose"] = "true" if value else "false"


# 全局配置实例
_config: Optional[HookConfig] = None


def load_hook_config(config_path: Optional[str] = None) -> HookConfig:
    """加载 hook 配置"""
    global _config
    if _config is None or config_path is not None:
        _config = HookConfig(config_path)
    return _config


if __name__ == "__main__":
    # 测试配置加载
    config = load_hook_config()
    print(f"Hook mode: {config.hook_mode}")
    print(f"Min length: {config.min_length}")
    print(f"Skip patterns: {config.skip_patterns}")
    print(f"Promotion threshold: {config.promotion_threshold}")
#!/usr/bin/env python3
"""
Hook 配置加载器
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, List, Optional


class HookConfig:
    """Hook 配置类"""

    DEFAULT_CONFIG = {
        "hook": {
            "mode": "auto",
        },
        "filter": {
            "min_length": "30",
            "max_per_round": "5",
            "skip_patterns": "thanks,thank you,goodbye,bye,/stop,/help",
        },
        "memory": {
            "tier": "auto",
            "promotion_threshold": "0.75",
            "auto_categorize": "true",
        },
        "logging": {
            "level": "info",
            "verbose": "false",
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config = configparser.ConfigParser()

        if config_path:
            self.config_path = Path(config_path)
        else:
            # 默认路径
            skill_root = Path(__file__).parent.parent
            self.config_path = skill_root / "config" / "hook.toml"

        self._load()

    def _load(self):
        """加载配置文件"""
        if self.config_path.exists():
            self.config.read(self.config_path, encoding="utf-8")
        else:
            # 使用默认配置
            for section, options in self.DEFAULT_CONFIG.items():
                self.config[section] = options

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """获取配置值"""
        try:
            value = self.config.get(section, key)
            return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """获取整数配置"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """获取布尔配置"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_list(self, section: str, key: str, fallback: List[str] = None, separator: str = ",") -> List[str]:
        """获取列表配置"""
        value = self.get(section, key)
        if value is None:
            return fallback or []
        # 去掉首尾引号
        value = value.strip().strip('"').strip("'")
        return [item.strip() for item in value.split(separator) if item.strip()]

    @property
    def hook_mode(self) -> str:
        """获取 hook 模式"""
        return self.get("hook", "mode", "auto")

    @property
    def min_length(self) -> int:
        """获取最小内容长度"""
        return self.get_int("filter", "min_length", 30)

    @property
    def max_per_round(self) -> int:
        """获取每轮最大保存条数"""
        return self.get_int("filter", "max_per_round", 5)

    @property
    def skip_patterns(self) -> List[str]:
        """获取跳过模式列表"""
        return self.get_list("filter", "skip_patterns", ["thanks", "thank you"])

    @property
    def memory_tier(self) -> str:
        """获取记忆层级"""
        return self.get("memory", "tier", "auto")

    @property
    def promotion_threshold(self) -> float:
        """获取晋升阈值"""
        return self.get_float("memory", "promotion_threshold", 0.75)

    @property
    def auto_categorize(self) -> bool:
        """获取自动分类设置"""
        return self.get_bool("memory", "auto_categorize", True)

    @property
    def log_level(self) -> str:
        """获取日志级别"""
        return self.get("logging", "level", "info")

    @property
    def verbose(self) -> bool:
        """获取详细输出设置"""
        return self.get_bool("logging", "verbose", False)

    @verbose.setter
    def verbose(self, value: bool):
        """设置详细输出"""
        if "logging" not in self.config:
            self.config["logging"] = {}
        self.config["logging"]["verbose"] = "true" if value else "false"


# 全局配置实例
_config: Optional[HookConfig] = None


def load_hook_config(config_path: Optional[str] = None) -> HookConfig:
    """加载 hook 配置"""
    global _config
    if _config is None or config_path is not None:
        _config = HookConfig(config_path)
    return _config


if __name__ == "__main__":
    # 测试配置加载
    config = load_hook_config()
    print(f"Hook mode: {config.hook_mode}")
    print(f"Min length: {config.min_length}")
    print(f"Skip patterns: {config.skip_patterns}")
    print(f"Promotion threshold: {config.promotion_threshold}")
#!/usr/bin/env python3
"""
Hook 配置加载器
"""

import os
import configparser
from pathlib import Path
from typing import Dict, Any, List, Optional


class HookConfig:
    """Hook 配置类"""

    DEFAULT_CONFIG = {
        "hook": {
            "mode": "auto",
        },
        "filter": {
            "min_length": "30",
            "max_per_round": "5",
            "skip_patterns": "thanks,thank you,goodbye,bye,/stop,/help",
        },
        "memory": {
            "tier": "auto",
            "promotion_threshold": "0.75",
            "auto_categorize": "true",
        },
        "logging": {
            "level": "info",
            "verbose": "false",
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config = configparser.ConfigParser()

        if config_path:
            self.config_path = Path(config_path)
        else:
            # 默认路径
            skill_root = Path(__file__).parent.parent
            self.config_path = skill_root / "config" / "hook.toml"

        self._load()

    def _load(self):
        """加载配置文件"""
        if self.config_path.exists():
            self.config.read(self.config_path, encoding="utf-8")
        else:
            # 使用默认配置
            for section, options in self.DEFAULT_CONFIG.items():
                self.config[section] = options

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """获取配置值"""
        try:
            value = self.config.get(section, key)
            return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """获取整数配置"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """获取布尔配置"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_list(self, section: str, key: str, fallback: List[str] = None, separator: str = ",") -> List[str]:
        """获取列表配置"""
        value = self.get(section, key)
        if value is None:
            return fallback or []
        # 去掉首尾引号
        value = value.strip().strip('"').strip("'")
        return [item.strip() for item in value.split(separator) if item.strip()]

    @property
    def hook_mode(self) -> str:
        """获取 hook 模式"""
        return self.get("hook", "mode", "auto")

    @property
    def min_length(self) -> int:
        """获取最小内容长度"""
        return self.get_int("filter", "min_length", 30)

    @property
    def max_per_round(self) -> int:
        """获取每轮最大保存条数"""
        return self.get_int("filter", "max_per_round", 5)

    @property
    def skip_patterns(self) -> List[str]:
        """获取跳过模式列表"""
        return self.get_list("filter", "skip_patterns", ["thanks", "thank you"])

    @property
    def memory_tier(self) -> str:
        """获取记忆层级"""
        return self.get("memory", "tier", "auto")

    @property
    def promotion_threshold(self) -> float:
        """获取晋升阈值"""
        return self.get_float("memory", "promotion_threshold", 0.75)

    @property
    def auto_categorize(self) -> bool:
        """获取自动分类设置"""
        return self.get_bool("memory", "auto_categorize", True)

    @property
    def log_level(self) -> str:
        """获取日志级别"""
        return self.get("logging", "level", "info")

    @property
    def verbose(self) -> bool:
        """获取详细输出设置"""
        return self.get_bool("logging", "verbose", False)

    @verbose.setter
    def verbose(self, value: bool):
        """设置详细输出"""
        if "logging" not in self.config:
            self.config["logging"] = {}
        self.config["logging"]["verbose"] = "true" if value else "false"


# 全局配置实例
_config: Optional[HookConfig] = None


def load_hook_config(config_path: Optional[str] = None) -> HookConfig:
    """加载 hook 配置"""
    global _config
    if _config is None or config_path is not None:
        _config = HookConfig(config_path)
    return _config


if __name__ == "__main__":
    # 测试配置加载
    config = load_hook_config()
    print(f"Hook mode: {config.hook_mode}")
    print(f"Min length: {config.min_length}")
    print(f"Skip patterns: {config.skip_patterns}")
    print(f"Promotion threshold: {config.promotion_threshold}")
