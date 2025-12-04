import json
from typing import Any, Dict
import allure
from requests import Response


class ApiAssertions:
    @staticmethod
    @allure.step("验证响应状态码")
    def assert_status_code(response: Response, expected_code: int):
        assert response.status_code == expected_code, \
            f"期望状态码 {expected_code}, 实际状态码 {response.status_code}"

    @staticmethod
    @allure.step("验证响应内容")
    def assert_response_content(response: Response, expected_response: Dict[str, Any]):
        try:
            actual_response = response.json()
        except json.JSONDecodeError:
            raise AssertionError(f"响应内容不是有效的JSON格式: {response.text}")
        
        expected = json.loads(expected_response) if isinstance(expected_response, str) else expected_response

        for key, value in expected.items():
            assert key in actual_response, f"响应中缺少键 {key}"
            if value is not None and value != "":
                assert actual_response[key] == value, \
                    f"键 {key} 的值不匹配，期望 {value}, 实际 {actual_response[key]}"

    @staticmethod
    @allure.step("验证响应包含指定字段")
    def assert_response_has_key(response: Response, key: str):
        actual_response = response.json()
        assert key in actual_response, f"响应中缺少键 {key}"
