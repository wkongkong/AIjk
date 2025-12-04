import pytest
import pandas as pd
import os
import logging
from typing import Dict, Any
from core.api_client import ApiClient
from config.config import Config

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def api_client():
    """API客户端fixture"""
    config = Config()
    return ApiClient(config)


@pytest.fixture(scope="session")
def test_data() -> pd.DataFrame:
    """加载测试数据（已废弃，保留用于兼容性）"""
    csv_path = os.path.join(os.path.dirname(__file__), "data", "test_cases.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path, encoding='utf-8')
    return pd.DataFrame()


@pytest.fixture
def authenticated_api_client(api_client, request):
    """已认证的API客户端fixture，根据测试用例前置条件选择认证方案"""
    # 获取当前测试用例的前置条件
    test_case_id = request.node.originalname if hasattr(request.node, 'originalname') else ""
    
    # 从测试用例数据中获取前置条件
    preconditions = ""
    if hasattr(request, 'param') and isinstance(request.param, dict):
        preconditions = request.param.get('preconditions', '')
    
    # 检查前置条件是否包含token相关内容
    token_keywords = ['token', 'Token', 'TOKEN', '认证', '登录']
    use_token_auth = any(keyword in preconditions for keyword in token_keywords)
    
    # 如果前置条件包含token相关内容，优先使用固定token方案（方案2）
    if use_token_auth:
        logger.info(f"测试用例 {test_case_id} 前置条件包含token，使用固定token认证方案（方案2）")
        # 如果已经配置了token，直接返回已认证的客户端
        if api_client.is_authenticated and api_client.auth_token:
            logger.info("使用配置的token进行认证")
            return api_client
        else:
            # 如果配置中没有token，尝试从全局请求头中获取
            config = Config()
            if config.token:
                api_client.set_auth_token(config.token)
                logger.info("使用配置中的固定token进行认证")
                return api_client
            else:
                logger.warning("配置中未设置token，将尝试万能验证码登录")
    else:
        logger.info(f"测试用例 {test_case_id} 前置条件不包含token，使用万能验证码登录方案（方案1）")
    
    # 尝试万能验证码登录
    if hasattr(api_client, 'login_with_captcha') and api_client.login_with_captcha():
        return api_client
    else:
        # 如果验证码登录失败，尝试普通登录
        if api_client.login():
            return api_client
        else:
            # 如果登录都失败，返回未认证的客户端
            logger.warning("登录失败，返回未认证的API客户端")
            return api_client

@pytest.fixture
def auth_token(api_client):
    """获取认证token的fixture"""
    # 如果客户端已认证，返回token
    if api_client.is_authenticated:
        return api_client.auth_token
    
    # 否则尝试登录获取token
    if api_client.login():
        return api_client.auth_token
    
    # 登录失败返回None
    return None


@pytest.fixture
def low_permission_api_client(api_client, request):
    """低权限API客户端fixture，用于测试权限不足场景"""
    # 获取当前测试用例的前置条件
    preconditions = ""
    if hasattr(request, 'param') and isinstance(request.param, dict):
        preconditions = request.param.get('preconditions', '')
    
    # 检查前置条件是否包含权限不足相关内容
    permission_keywords = ['权限不足', '无权限', '低权限', 'limited permission', 'no permission']
    use_low_permission = any(keyword in preconditions for keyword in permission_keywords)
    
    if use_low_permission:
        logger.info("测试用例需要权限不足场景，设置低权限token")
        # 使用低权限token
        api_client.set_low_permission_token()
    
    return api_client


@pytest.fixture
def no_permission_api_client(api_client, request):
    """无权限API客户端fixture，用于测试未认证场景"""
    # 获取当前测试用例的前置条件
    preconditions = ""
    if hasattr(request, 'param') and isinstance(request.param, dict):
        preconditions = request.param.get('preconditions', '')
    
    # 检查前置条件是否包含未认证相关内容
    no_auth_keywords = ['未登录', '未认证', '无token', 'no auth', 'unauthenticated']
    use_no_permission = any(keyword in preconditions for keyword in no_auth_keywords)
    
    if use_no_permission:
        logger.info("测试用例需要未认证场景，清除认证信息")
        # 清除认证信息
        api_client.set_no_permission_mode()
    
    return api_client
