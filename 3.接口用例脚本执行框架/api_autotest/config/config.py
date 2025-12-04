import os
import yaml
from typing import Dict, Any


class Config:
    _instance = None
    _config_data: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._config_data:
            self.load_config()

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config_data = yaml.safe_load(f)

    @property
    def base_url(self) -> str:
        env = os.getenv('TEST_ENV', 'test')
        return self._config_data['env'][env]['base_url']

    @property
    def headers(self) -> Dict[str, str]:
        return self._config_data['headers']

    @property
    def global_headers(self) -> Dict[str, str]:
        """获取全局请求头（兼容性属性）"""
        return self._config_data['headers']

    @property
    def timeout(self) -> int:
        env = os.getenv('TEST_ENV', 'test')
        return self._config_data['env'][env]['timeout']

    @property
    def login_url(self) -> str:
        """获取登录接口URL"""
        login_config = self._config_data.get('login', {})
        login_url = login_config.get('url', '')
        if login_url and not login_url.startswith('http'):
            # 如果是相对路径，拼接base_url
            env = os.getenv('TEST_ENV', 'test')
            base_url = self._config_data['env'][env]['base_url']
            return f"{base_url}{login_url}"
        return login_url

    @property
    def login_data(self) -> Dict[str, Any]:
        """获取登录请求数据"""
        login_config = self._config_data.get('login', {})
        return login_config.get('data', {})

    @property
    def auth_header(self) -> str:
        """获取认证头字段名"""
        login_config = self._config_data.get('login', {})
        return login_config.get('auth_header', 'Authorization')

    @property
    def token_path(self) -> str:
        """获取token在响应中的路径"""
        login_config = self._config_data.get('login', {})
        return login_config.get('token_path', 'token')

    @property
    def token(self) -> str:
        """获取直接配置的token值"""
        login_config = self._config_data.get('login', {})
        return login_config.get('token', '')

    @property
    def captcha_enabled(self) -> bool:
        """是否启用验证码（固定返回True，使用万能验证码方案）"""
        return True

    @property
    def captcha_field_name(self) -> str:
        """获取验证码字段名"""
        return "captcha"

    @property
    def fixed_captcha_value(self) -> str:
        """获取固定验证码值（万能验证码）"""
        return "8888"
