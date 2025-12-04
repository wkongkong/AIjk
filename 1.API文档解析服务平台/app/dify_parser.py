"""
Dify返回测试用例数据的精准解析器
专门用于解析Dify返回的JSON格式测试用例数据
"""
import json
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def parse_dify_testcase_file(file_content: str) -> Dict[str, Any]:
    """
    精准解析Dify返回的测试用例数据文件
    
    Args:
        file_content: 文件内容字符串
        
    Returns:
        包含测试用例数据的字典
        {
            "success": True/False,
            "test_cases": 测试用例列表,
            "json_content": 原始JSON内容,
            "error": 错误信息
        }
    """
    try:
        # 方法1: 尝试解析为完整的JSON响应
        if file_content.strip().startswith('{'):
            try:
                data = json.loads(file_content)
                if 'answer' in data:
                    # 提取answer字段中的JSON内容
                    return _extract_from_answer(data['answer'])
                elif 'test_cases' in data:
                    # 直接返回测试用例数据
                    return {
                        "success": True,
                        "test_cases": data['test_cases'],
                        "json_content": json.dumps(data, ensure_ascii=False, indent=2)
                    }
            except json.JSONDecodeError:
                pass
        
        # 方法2: 从文本中精准提取JSON内容
        json_content = _extract_json_precisely(file_content)
        if json_content:
            return _parse_json_content(json_content)
        
        return {
            "success": False,
            "error": "未找到有效的JSON测试用例数据"
        }
        
    except Exception as e:
        logger.error(f"解析Dify测试用例文件失败: {e}")
        return {
            "success": False,
            "error": f"解析失败: {str(e)}"
        }


def _extract_from_answer(answer_content: str) -> Dict[str, Any]:
    """从answer字段中提取测试用例数据"""
    
    # 精准提取方案1: 查找表格测试用例输出标识
    start_marker = "表格测试用例输出开始"
    end_marker = "表格测试用例输出结束"
    
    if start_marker in answer_content and end_marker in answer_content:
        start_idx = answer_content.find(start_marker) + len(start_marker)
        end_idx = answer_content.find(end_marker)
        
        if start_idx < end_idx:
            json_str = answer_content[start_idx:end_idx].strip()
            logger.info("找到精准标识符格式的JSON数据")
            return _parse_json_content(json_str)
    
    # 精准提取方案2: 查找Markdown代码块
    code_block_match = re.search(r'```json\s*\n(.*?)\n```', answer_content, re.DOTALL)
    if code_block_match:
        json_str = code_block_match.group(1).strip()
        logger.info("找到Markdown代码块格式的JSON数据")
        return _parse_json_content(json_str)
    
    return {
        "success": False,
        "error": "未找到精准格式的JSON测试用例数据"
    }


def _extract_json_precisely(content: str) -> Optional[str]:
    """精准提取JSON内容"""
    
    # 查找最外层的大括号对
    brace_count = 0
    start_idx = -1
    
    for i, char in enumerate(content):
        if char == '{':
            brace_count += 1
            if start_idx == -1:
                start_idx = i
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                # 找到完整的JSON对象
                json_str = content[start_idx:i+1].strip()
                
                # 验证是否为有效的JSON
                try:
                    data = json.loads(json_str)
                    if 'test_cases' in data or isinstance(data, list) and len(data) > 0:
                        return json_str
                except json.JSONDecodeError:
                    pass
                
                # 重置搜索
                start_idx = -1
                brace_count = 0
    
    return None


def _parse_json_content(json_content: str) -> Dict[str, Any]:
    """解析JSON内容为测试用例数据"""
    
    try:
        data = json.loads(json_content)
        
        # 处理不同的数据格式
        if isinstance(data, dict):
            if 'test_cases' in data:
                # 标准格式：包含test_cases字段
                test_cases = data['test_cases']
            elif 'answer' in data:
                # 嵌套格式：answer字段包含测试用例
                return _extract_from_answer(data['answer'])
            else:
                # 尝试将整个字典作为测试用例
                test_cases = [data]
        elif isinstance(data, list):
            # 数组格式：直接作为测试用例列表
            test_cases = data
        else:
            return {
                "success": False,
                "error": "JSON格式不符合要求"
            }
        
        # 确保test_cases是列表类型
        if not isinstance(test_cases, list):
            logger.error(f"test_cases不是列表类型: {type(test_cases)}")
            return {
                "success": False,
                "error": f"测试用例数据格式错误，期望列表类型，实际为{type(test_cases)}"
            }
        
        # 验证测试用例格式
        validated_cases = _validate_test_cases(test_cases)
        
        return {
            "success": True,
            "test_cases": validated_cases,
            "json_content": json.dumps({"test_cases": validated_cases}, ensure_ascii=False, indent=2)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return {
            "success": False,
            "error": f"JSON解析失败: {str(e)}"
        }


def _validate_test_cases(test_cases: List[Dict]) -> List[Dict]:
    """验证测试用例格式并标准化"""
    
    # 确保传入的是列表类型
    if not isinstance(test_cases, list):
        logger.error(f"_validate_test_cases期望列表类型，实际为{type(test_cases)}")
        return []
    
    validated_cases = []
    
    for i, test_case in enumerate(test_cases):
        # 确保每个测试用例是字典类型
        if not isinstance(test_case, dict):
            logger.warning(f"跳过非字典类型的测试用例: {type(test_case)}")
            continue
            
        # 确保测试用例有基本字段
        standardized_case = {
            "test_case_id": test_case.get("test_case_id", f"TC{i+1:03d}"),
            "test_case_name": test_case.get("test_case_name", f"测试用例{i+1}"),
            "api_name": test_case.get("api_name", "未知接口"),
            "method": test_case.get("method", "GET"),
            "url": test_case.get("url", "/"),
            "headers": test_case.get("headers", {}),
            "request_data": test_case.get("request_data", {}),
            "expected_status_code": test_case.get("expected_status_code", 200),
            "expected_response": test_case.get("expected_response", {}),
            "test_type": test_case.get("test_type", "positive"),
            "priority": test_case.get("priority", "medium"),
            "description": test_case.get("description", ""),
            "preconditions": test_case.get("preconditions", ""),
            "postconditions": test_case.get("postconditions", ""),
            "tags": test_case.get("tags", [])
        }
        
        validated_cases.append(standardized_case)
    
    return validated_cases


def save_testcases_to_file(test_cases: List[Dict], file_path: str) -> bool:
    """将测试用例保存到文件"""
    
    try:
        import os
        from datetime import datetime
        
        # 准备数据格式
        data = {
            "_metadata": {
                "testcase_count": len(test_cases),
                "generated_at": datetime.now().isoformat(),
                "source": "dify_parser"
            },
            "testcases": test_cases
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"成功保存{len(test_cases)}个测试用例到文件: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"保存测试用例文件失败: {e}")
        return False


if __name__ == "__main__":
    # 测试解析器
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            result = parse_dify_testcase_file(content)
            print(f"解析结果: {result['success']}")
            if result['success']:
                print(f"找到{len(result['test_cases'])}个测试用例")
                for i, test_case in enumerate(result['test_cases']):
                    print(f"{i+1}. {test_case['test_case_name']} ({test_case['test_case_id']})")
            else:
                print(f"错误: {result['error']}")
        
        except Exception as e:
            print(f"文件读取失败: {e}")
    else:
        print("用法: python dify_parser.py <文件路径>")
        print("示例: python dify_parser.py dify返回的测试用例数据.txt")