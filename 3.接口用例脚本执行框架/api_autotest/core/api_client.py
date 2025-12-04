import requests
from typing import Dict, Any, Optional
from core.logger import logger
from config.config import Config


class ApiClient:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.auth_token = ""
        self.is_authenticated = False
        
        # 设置全局请求头
        if config.global_headers:
            self.session.headers.update(config.global_headers)
        
        # 如果配置了直接token，优先使用
        if config.token:
            self.auth_token = config.token
            self.is_authenticated = True
            logger.info("使用配置的token进行认证")

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """发送HTTP请求"""
        # 如果URL已经是完整URL，直接使用；否则拼接base_url
        if url.startswith('http://') or url.startswith('https://'):
            full_url = url
        else:
            full_url = f"{self.config.base_url}{url}"
        
        merged_headers = {**self.session.headers, **(headers or {})}

        logger.info(f"Sending {method} request to {full_url}")
        logger.debug(f"Headers: {merged_headers}")
        logger.debug(f"Data: {data}")

        response = self.session.request(
            method=method,
            url=full_url,
            headers=merged_headers,
            json=data,
            timeout=self.config.timeout,
            **kwargs
        )

        logger.info(f"Response status: {response.status_code}")
        logger.debug(f"Response body: {response.text}")

        return response

    def login(self, captcha_value: str = None) -> bool:
        """执行登录操作并获取认证token"""
        # 如果已经配置了token，直接返回成功
        if self.is_authenticated and self.auth_token:
            logger.info("已配置token，跳过登录过程")
            return True
            
        # 使用配置的登录接口
        login_url = self.config.login_url
        login_data = self.config.login_data.copy()
        
        if not login_url or not login_data:
            logger.warning("登录配置不完整，跳过登录")
            return False
        
        # 处理验证码
        if self.config.captcha_enabled:
            if captcha_value:
                # 使用传入的验证码
                login_data[self.config.captcha_field_name] = captcha_value
            else:
                # 使用固定验证码
                login_data[self.config.captcha_field_name] = self.config.fixed_captcha_value
        
        logger.info(f"尝试登录到: {login_url}")
        if self.config.captcha_enabled:
            logger.info(f"使用验证码: {login_data.get(self.config.captcha_field_name, '未设置')}")
        
        try:
            response = self.request(
                method="POST",
                url=login_url,
                data=login_data
            )
            
            if response.status_code == 200:
                # 解析登录响应，提取token
                response_data = response.json()
                
                # 根据配置的token路径提取token
                token_path = self.config.token_path
                token = self._extract_token_by_path(response_data, token_path)
                
                if token:
                    self.auth_token = token
                    self.is_authenticated = True
                    # 更新session的认证头
                    auth_header = self.config.auth_header
                    self.session.headers.update({auth_header: f"Bearer {token}"})
                    logger.info("登录成功，已设置认证token")
                    return True
                else:
                    logger.error(f"登录响应中未找到token，token路径: {token_path}")
                    logger.debug(f"响应数据: {response_data}")
                    return False
            else:
                logger.error(f"登录失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"登录过程中发生错误: {e}")
            return False
    
    def set_auth_token(self, token: str):
        """手动设置认证token"""
        self.auth_token = token
        self.is_authenticated = True
        auth_header = self.config.auth_header or "Authorization"
        self.session.headers.update({auth_header: f"Bearer {token}"})
        logger.info("已手动设置认证token")
    
    def _extract_token_by_path(self, data: dict, path: str) -> str:
        """根据路径从数据中提取token"""
        if not path:
            return ""
        
        # 支持点分隔符的路径
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return ""
        
        return str(current) if current else ""

    def get_captcha_image(self) -> bytes:
        """获取验证码图片"""
        if not self.config.captcha_image_url:
            logger.warning("未配置验证码图片URL")
            return b""
        
        try:
            response = self.session.get(self.config.captcha_image_url)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"获取验证码图片失败: {response.status_code}")
                return b""
        except Exception as e:
            logger.error(f"获取验证码图片异常: {e}")
            return b""

    def recognize_captcha(self, image_data: bytes) -> str:
        """识别验证码"""
        service_type = self.config.captcha_recognition_service
        
        if service_type == "ocr":
            return self._recognize_captcha_with_ocr(image_data)
        elif service_type == "third_party":
            return self._recognize_captcha_with_service(image_data)
        else:
            # 默认返回固定验证码
            return self.config.fixed_captcha_value

    def _recognize_captcha_with_ocr(self, image_data: bytes) -> str:
        """使用OCR识别验证码"""
        try:
            # 需要安装pytesseract和Pillow
            import pytesseract
            from PIL import Image
            from io import BytesIO
            
            image = Image.open(BytesIO(image_data))
            captcha_text = pytesseract.image_to_string(image)
            
            # 清理识别结果
            captcha_text = captcha_text.strip().replace(' ', '').replace('\n', '')
            
            if captcha_text:
                logger.info(f"OCR识别验证码: {captcha_text}")
                return captcha_text
            else:
                logger.warning("OCR未能识别验证码，使用固定值")
                return self.config.fixed_captcha_value
                
        except ImportError:
            logger.warning("未安装OCR依赖，使用固定验证码")
            return self.config.fixed_captcha_value
        except Exception as e:
            logger.error(f"OCR识别验证码失败: {e}")
            return self.config.fixed_captcha_value

    def _recognize_captcha_with_service(self, image_data: bytes) -> str:
        """使用第三方验证码识别服务"""
        # 这里需要根据实际使用的第三方服务实现
        # 示例：超级鹰、图鉴等
        logger.info("使用第三方验证码识别服务（需要具体实现）")
        return self.config.fixed_captcha_value

    def login_with_captcha(self) -> bool:
        """使用万能验证码登录"""
        try:
            # 构建登录数据，包含万能验证码
            login_data = self.config.login_data.copy()
            login_data["captcha"] = "8888"  # 万能验证码
            
            # 发送登录请求
            response = self.request(
                method="POST",
                url=self.config.login_url,
                data=login_data
            )
            
            if response.status_code == 200:
                # 提取token
                response_data = response.json()
                token_path = self.config.token_path
                token = self._extract_token_by_path(response_data, token_path)
                if token:
                    self.auth_token = token
                    self.is_authenticated = True
                    auth_header = self.config.auth_header
                    self.session.headers.update({auth_header: f"Bearer {token}"})
                    logger.info("万能验证码登录成功")
                    return True
                else:
                    logger.error("登录响应中未找到token")
                    return False
            else:
                logger.error(f"万能验证码登录失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"万能验证码登录异常: {str(e)}")
            return False

    def clear_auth(self):
        """清除认证信息"""
        self.auth_token = None
        self.is_authenticated = False
        # 移除认证头
        auth_header = self.config.auth_header
        if auth_header in self.session.headers:
            del self.session.headers[auth_header]
        logger.info("已清除认证信息")

    def set_low_permission_token(self, token: str = None):
        """设置低权限token，用于测试权限不足场景"""
        if token:
            # 使用指定的低权限token
            self.set_auth_token(token)
        else:
            # 如果没有指定token，使用配置中的固定token（假设这是低权限token）
            config = Config()
            if config.token:
                self.set_auth_token(config.token)
                logger.info("使用配置中的固定token作为低权限token")
            else:
                logger.warning("配置中未设置token，无法设置低权限token")

    def set_no_permission_mode(self):
        """设置无权限模式，移除所有认证信息"""
        self.clear_auth()
        logger.info("已设置为无权限模式")
