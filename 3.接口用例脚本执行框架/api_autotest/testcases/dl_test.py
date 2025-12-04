"""
独立测试脚本 - dl_test.yaml
对应测试用例文件：data_yaml/dl_test.yaml

使用方式：
    pytest testcases/dl_test.py -v
"""

import pytest
import json
import allure
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.api_client import ApiClient
from core.assertions import ApiAssertions
from config.config import Config
from utils.data_handler import DataHandler


# 加载测试用例数据
TEST_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_yaml", "dl_test.yaml")
test_cases = DataHandler.load_test_cases(TEST_DATA_FILE)


@allure.feature("角色报表管理")
@allure.story("getRoleReportTree接口测试")
class TestDlTest:
    """dl_test.yaml 独立测试类"""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """API客户端fixture"""
        config = Config()
        return ApiClient(config)
    
    @pytest.mark.parametrize("test_case", test_cases, ids=[tc.get('test_case_id', 'unknown') for tc in test_cases])
    def test_api(self, test_case, api_client):
        """
        独立API测试方法
        
        Args:
            test_case: 测试用例数据（从dl_test.yaml加载）
            api_client: API客户端fixture
        """
        # 添加Allure报告信息
        if 'test_case_id' in test_case:
            allure.dynamic.title(f"{test_case['test_case_id']}: {test_case.get('test_case_name', '')}")
        
        if 'description' in test_case:
            allure.dynamic.description(test_case['description'])
        
        if 'priority' in test_case:
            allure.dynamic.severity(self._map_priority(test_case['priority']))
        
        if 'tags' in test_case:
            tags = test_case['tags']
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',')]
            for tag in tags:
                allure.dynamic.tag(tag)
        
        # 1. 处理前置条件（认证）
        self._handle_preconditions(test_case, api_client)
        
        # 2. 准备请求参数
        method = test_case.get('method', 'GET').upper()
        url = test_case.get('url', '')
        headers = test_case.get('headers', {})
        request_data = test_case.get('request_data', {})
        
        # 确保headers和request_data是字典类型
        if isinstance(headers, str):
            headers = json.loads(headers) if headers else {}
        if isinstance(request_data, str):
            request_data = json.loads(request_data) if request_data else {}
        
        # 3. 发送请求
        with allure.step(f"发送 {method} 请求到 {url}"):
            allure.attach(json.dumps(request_data, ensure_ascii=False, indent=2), 
                         "请求数据", allure.attachment_type.JSON)
            
            response = api_client.request(
                method=method,
                url=url,
                headers=headers,
                data=request_data
            )
        
        # 4. 记录响应
        with allure.step("记录响应结果"):
            allure.attach(f"状态码: {response.status_code}", "响应状态码", allure.attachment_type.TEXT)
            allure.attach(json.dumps(response.json(), ensure_ascii=False, indent=2), 
                         "响应数据", allure.attachment_type.JSON)
        
        # 5. 执行断言
        self._perform_assertions(test_case, response)
        
        # 6. 处理后置条件
        self._handle_postconditions(test_case, response)
    
    def _handle_preconditions(self, test_case, api_client):
        """处理前置条件"""
        preconditions = test_case.get('preconditions', '')
        
        if not preconditions or preconditions == '-':
            return
        
        # 检查是否需要token认证
        token_keywords = ['token', 'Token', 'TOKEN', '认证', '登录', '已登录', '拥有']
        if any(keyword in preconditions for keyword in token_keywords):
            with allure.step("执行认证"):
                if not api_client.is_authenticated:
                    # 尝试登录
                    if hasattr(api_client, 'login_with_captcha'):
                        api_client.login_with_captcha()
                    else:
                        api_client.login()
        
        # 检查是否需要权限不足场景
        permission_keywords = ['权限不足', '无权限', '低权限']
        if any(keyword in preconditions for keyword in permission_keywords):
            with allure.step("设置低权限场景"):
                if hasattr(api_client, 'set_low_permission_token'):
                    api_client.set_low_permission_token()
        
        # 检查是否需要未认证场景
        no_auth_keywords = ['未登录', '未认证', '无token', '未进行任何身份认证']
        if any(keyword in preconditions for keyword in no_auth_keywords):
            with allure.step("清除认证信息"):
                if hasattr(api_client, 'set_no_permission_mode'):
                    api_client.set_no_permission_mode()
    
    def _perform_assertions(self, test_case, response):
        """执行断言"""
        # 断言状态码
        expected_status_code = test_case.get('expected_status_code')
        if expected_status_code:
            with allure.step(f"验证状态码为 {expected_status_code}"):
                ApiAssertions.assert_status_code(response, int(expected_status_code))
        
        # 断言响应内容
        expected_response = test_case.get('expected_response')
        if expected_response:
            # 确保expected_response是字典类型
            if isinstance(expected_response, str):
                expected_response = json.loads(expected_response) if expected_response else {}
            
            response_json = response.json()
            
            # 逐个字段断言
            for key, expected_value in expected_response.items():
                with allure.step(f"验证响应字段 {key} = {expected_value}"):
                    assert key in response_json, f"响应中缺少键 {key}"
                    if expected_value is not None and expected_value != "":
                        assert response_json[key] == expected_value, \
                            f"键 {key} 的值不匹配，期望 {expected_value}, 实际 {response_json[key]}"
    
    def _handle_postconditions(self, test_case, response):
        """处理后置条件"""
        postconditions = test_case.get('postconditions', '')
        
        if not postconditions or postconditions == '-':
            return
        
        # 这里可以添加后置条件处理逻辑
        # 例如：清理测试数据、重置状态等
        pass
    
    @staticmethod
    def _map_priority(priority):
        """映射优先级到Allure严重级别"""
        priority_map = {
            'critical': allure.severity_level.CRITICAL,
            'high': allure.severity_level.CRITICAL,
            'medium': allure.severity_level.NORMAL,
            'normal': allure.severity_level.NORMAL,
            'low': allure.severity_level.MINOR,
            'trivial': allure.severity_level.TRIVIAL
        }
        return priority_map.get(str(priority).lower(), allure.severity_level.NORMAL)
