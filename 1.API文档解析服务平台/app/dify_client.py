"""
Dify API客户端
用于调用Dify工作流生成测试用例和Python脚本
"""
import requests
import json
import logging
import re
import tempfile
import os
from typing import Dict, Any, Optional
from app.dify_parser import parse_dify_testcase_file

logger = logging.getLogger(__name__)


class DifyClient:
    """Dify API客户端"""
    
    def __init__(self, api_key_yaml: str, workflow_yaml_url: str, api_key_python: str, workflow_python_url: str):
        """
        初始化Dify客户端
        
        Args:
            api_key_yaml: YAML测试用例生成工作流的API密钥
            workflow_yaml_url: 生成YAML测试用例的工作流URL
            api_key_python: Python脚本生成工作流的API密钥
            workflow_python_url: 生成Python脚本的工作流URL
        """
        self.api_key_yaml = api_key_yaml
        self.workflow_yaml_url = workflow_yaml_url
        self.api_key_python = api_key_python
        self.workflow_python_url = workflow_python_url
        
        # 为每个工作流创建独立的headers
        self.headers_yaml = {
            "Authorization": f"Bearer {api_key_yaml}",
            "Content-Type": "application/json"
        }
        self.headers_python = {
            "Authorization": f"Bearer {api_key_python}",
            "Content-Type": "application/json"
        }
    
    def generate_json_testcases(self, interface_details: Dict[str, Any], user_id: str = "default") -> Dict[str, Any]:
        """
        调用Dify工作流生成JSON格式测试用例
        
        Args:
            interface_details: 接口详情信息
            user_id: 用户ID
            
        Returns:
            包含解析结果的响应字典
            {
                "success": True/False,
                "json_content": "JSON内容",
                "test_cases": "解析后的测试用例列表",
                "error": "错误信息"
            }
        """
        try:
            # 提取接口ID和集合ID
            interface_id = interface_details.get('interface', {}).get('id', '')
            collection_id = interface_details.get('collection_info', {}).get('id', '')
            
            logger.info(f"[Dify客户端] 开始生成测试用例")
            logger.info(f"[Dify客户端] 接口ID: {interface_id}")
            logger.info(f"[Dify客户端] 集合ID: {collection_id}")
            logger.info(f"[Dify客户端] API端点: {self.workflow_yaml_url}")
            
            # 准备接口信息作为query参数
            interface_info = {
                "interface_id": interface_id,
                "collection_id": collection_id,
                "interface": interface_details.get('interface', {}),
                "collection_info": interface_details.get('collection_info', {})
            }
            
            # 准备请求数据 - 对话工作流格式
            payload = {
                "inputs": {
                    "kid": interface_id,
                    "jihe": collection_id
                },
                "query": f"请根据以下接口信息生成JSON格式的测试用例，要求返回标准的JSON数组格式，每个测试用例包含test_case_id、test_case_name、api_name、method、url、headers、request_data、expected_status_code、expected_response、test_type、priority、description、preconditions、postconditions、tags等字段。请确保返回的是纯JSON格式，不要包含任何markdown代码块标记:\n{json.dumps(interface_info, ensure_ascii=False, indent=2)}",
                "response_mode": "blocking",
                "user": user_id
            }
            
            logger.info(f"[Dify客户端] 请求payload: inputs.kid={interface_id}, inputs.jihe={collection_id}")
            
            # 发送请求
            logger.info(f"[Dify客户端] 发送POST请求到: {self.workflow_yaml_url}")
            response = requests.post(
                self.workflow_yaml_url,
                headers=self.headers_yaml,
                json=payload,
                timeout=60
            )
            
            logger.info(f"[Dify客户端] 响应状态码: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.info(f"[Dify客户端] 响应数据类型: {type(result)}, 包含字段: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            
            # 解析响应 - 支持内部Dify服务的不同响应格式
            json_content = ""
            
            if "data" in result:
                # 官方Dify格式
                if result.get("data", {}).get("status") == "succeeded":
                    json_content = result.get("data", {}).get("outputs", {}).get("text", "")
                else:
                    error_msg = result.get("data", {}).get("error", "工作流执行失败")
                    logger.error(f"Dify工作流执行失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            elif "outputs" in result:
                # 内部Dify格式
                json_content = result.get("outputs", {}).get("text", "")
            elif "answer" in result:
                # 流式响应格式（包含event: message）
                json_content = result.get("answer", "")
            else:
                # 未知格式
                logger.error(f"未知的Dify响应格式: {result}")
                return {
                    "success": False,
                    "error": f"未知的响应格式: {result}"
                }
            
            # 使用精准解析器解析JSON内容
            parse_result = parse_dify_testcase_file(json_content)
            
            if parse_result["success"]:
                clean_json_content = parse_result["json_content"]
                test_cases = parse_result["test_cases"]
                logger.info(f"精准解析器成功解析{len(test_cases)}个测试用例")
            else:
                # 如果精准解析失败，打印详细调试信息并使用备选方案
                logger.warning(f"精准解析器解析失败，错误信息: {parse_result.get('error', '未知错误')}")
                logger.warning(f"完整的Dify返回值: {result}")
                logger.warning(f"提取的JSON内容: {json_content}")
                logger.warning("使用备选方案进行解析")
                clean_json_content = self._extract_json_content(json_content)
                test_cases = self._parse_json_testcases(clean_json_content)
            
            return {
                "success": True,
                "json_content": clean_json_content,
                "test_cases": test_cases,
                "original_content": json_content,  # 保留原始内容用于调试
                "workflow_id": result.get("workflow_run_id")
            }
                
        except requests.exceptions.Timeout:
            logger.error("Dify API请求超时")
            return {
                "success": False,
                "error": "请求超时，请稍后重试"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Dify API请求失败: {str(e)}")
            return {
                "success": False,
                "error": f"请求失败: {str(e)}"
            }
        except Exception as e:
            logger.error(f"生成JSON测试用例失败: {str(e)}")
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }
    
    def generate_python_script(self, yaml_content: str, user_id: str = "default") -> Dict[str, Any]:
        """
        调用Dify工作流生成Python测试脚本
        
        Args:
            yaml_content: YAML测试用例内容
            user_id: 用户ID
            
        Returns:
            包含Python代码的响应字典
            {
                "success": True/False,
                "python_code": "Python代码",
                "error": "错误信息"
            }
        """
        try:
            # 准备请求数据 - 对话工作流格式
            payload = {
                "inputs": {},
                "query": f"请根据以下YAML测试用例生成Python自动化测试脚本:\n{yaml_content}",
                "response_mode": "blocking",
                "user": user_id
            }
            
            logger.info("调用Dify生成Python测试脚本")
            logger.info(f"API端点: {self.workflow_python_url}")
            
            # 发送请求
            response = requests.post(
                self.workflow_python_url,
                headers=self.headers_python,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应 - 支持内部Dify服务的不同响应格式
            if "data" in result:
                # 官方Dify格式
                if result.get("data", {}).get("status") == "succeeded":
                    python_code = result.get("data", {}).get("outputs", {}).get("text", "")
                    
                    # 自动修复常见错误
                    python_code = self._fix_common_errors(python_code)
                    
                    return {
                        "success": True,
                        "python_code": python_code,
                        "workflow_id": result.get("workflow_run_id")
                    }
                else:
                    error_msg = result.get("data", {}).get("error", "工作流执行失败")
                    logger.error(f"Dify工作流执行失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            elif "outputs" in result:
                # 内部Dify格式
                python_code = result.get("outputs", {}).get("text", "")
                
                # 自动修复常见错误
                python_code = self._fix_common_errors(python_code)
                
                return {
                    "success": True,
                    "python_code": python_code,
                    "workflow_id": result.get("workflow_run_id")
                }
            else:
                # 未知格式
                logger.error(f"未知的Dify响应格式: {result}")
                return {
                    "success": False,
                    "error": f"未知的响应格式: {result}"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Dify API请求超时")
            return {
                "success": False,
                "error": "请求超时，请稍后重试"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Dify API请求失败: {str(e)}")
            return {
                "success": False,
                "error": f"请求失败: {str(e)}"
            }
        except Exception as e:
            logger.error(f"生成Python脚本失败: {str(e)}")
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }

    def generate_python_script_with_yaml(self, yaml_content: str, user_id: str = "default") -> Dict[str, Any]:
        """
        调用Dify工作流生成Python测试脚本（使用YAML文件上传）
        
        Args:
            yaml_content: YAML测试用例内容
            user_id: 用户ID
            
        Returns:
            包含Python代码的响应字典
            {
                "success": True/False,
                "python_code": "Python代码",
                "error": "错误信息"
            }
        """
        try:
            # 创建临时YAML文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
                f.write(yaml_content)
                temp_file_path = f.name
            
            try:
                # 第一步：调用/v1/files/upload接口上传文件获取file_id
                logger.info("=== 第一步：调用/v1/files/upload接口上传文件获取file_id ===")
                
                with open(temp_file_path, 'rb') as file:
                    # 正确设置文件上传参数
                    files = {
                        'file': (os.path.basename(temp_file_path), file, 'application/yaml')
                    }
                    
                    # 准备表单数据
                    data = {
                        'user': user_id,
                        'file': os.path.basename(temp_file_path)  # 添加file字段参数
                    }
                    
                    # 构造正确的上传URL
                    upload_url = self.workflow_python_url.replace('/v1/chat-messages', '/v1/files/upload')
                    logger.info(f"文件上传接口: {upload_url}")
                    logger.info(f"上传请求数据: {data}")
                    logger.info(f"上传文件: {os.path.basename(temp_file_path)}")
                    
                    # 上传文件获取file_id
                    upload_response = requests.post(
                        upload_url,
                        headers={'Authorization': self.headers_python['Authorization']},
                        files=files,
                        data=data,
                        timeout=60
                    )
                    
                    logger.info(f"上传响应状态码: {upload_response.status_code}")
                    logger.info(f"上传响应内容: {upload_response.text}")
                    
                    upload_response.raise_for_status()
                    upload_result = upload_response.json()
                    file_id = upload_result.get('id')
                    
                    if not file_id:
                        logger.error(f"文件上传失败，响应: {upload_result}")
                        return {
                            "success": False,
                            "error": "文件上传失败，无法获取文件ID"
                        }
                    
                    logger.info(f"文件上传成功，file_id: {file_id}")
                    
                    # 第二步：使用file_id调用/v1/chat-messages接口
                    logger.info("=== 第二步：使用file_id调用/v1/chat-messages接口 ===")
                    
                    payload = {
                        "inputs": {
                           "yaml_wj": {
                           "transfer_method": "local_file",
                           "upload_file_id": file_id
                    # 注意：这里不需要 "type" 字段，因为工作流已经定义了文件类型
                }
                        },
                        "query": "请根据上传的YAML测试用例文件生成Python自动化测试脚本，要求代码规范、可执行，并包含必要的错误处理。",
                        "response_mode": "blocking",
                        "user": user_id
                        
                    }
                    
                    logger.info(f"chat-messages接口: {self.workflow_python_url}")
                    logger.info(f"chat-messages请求数据: {payload}")
                    
                    # 发送chat-messages请求
                    response = requests.post(
                        self.workflow_python_url,
                        headers=self.headers_python,
                        json=payload,
                        timeout=120
                    )
                    
                    logger.info(f"chat-messages响应状态码: {response.status_code}")
                    logger.info(f"chat-messages响应内容: {response.text}")
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    # 记录完整的响应结构，便于调试
                    logger.info(f"Dify响应完整结构: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    
                    # 解析响应并提取Python代码
                    python_code = self._extract_python_code_from_response(result)
                    
                    if python_code:
                        logger.info(f"成功提取Python代码，长度: {len(python_code)} 字符")
                        
                        # 自动修复常见错误
                        python_code = self._fix_common_errors(python_code)
                        
                        # 检查代码块数量
                        code_blocks_count = self._count_code_blocks(python_code)
                        
                        return {
                            "success": True,
                            "python_code": python_code,
                            "workflow_id": result.get("workflow_run_id"),
                            "code_blocks_count": code_blocks_count
                        }
                    else:
                        logger.error(f"未能从Dify响应中提取Python代码")
                        logger.error(f"响应内容: {result}")
                        return {
                            "success": False,
                            "error": "未能从Dify响应中提取Python代码"
                        }
                    
            finally:
                # 确保删除临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                
        except requests.exceptions.Timeout:
            logger.error("Dify API请求超时")
            return {
                "success": False,
                "error": "请求超时，请稍后重试"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Dify API请求失败: {str(e)}")
            return {
                "success": False,
                "error": f"请求失败: {str(e)}"
            }
        except Exception as e:
            logger.error(f"生成Python脚本失败: {str(e)}")
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }

    def _extract_python_code_from_response(self, result: Dict[str, Any]) -> str:
        """
        从Dify响应中提取Python代码，支持多种格式和标识符
        
        Args:
            result: Dify API响应
            
        Returns:
            提取的Python代码
        """
        # 记录响应结构，便于调试
        logger.info(f"开始解析Dify响应，响应类型: {type(result)}")
        
        # 解析响应 - 支持多种Dify响应格式
        text_content = ""
        
        # 方法1: 官方Dify格式 (data字段)
        if "data" in result:
            logger.info("检测到官方Dify格式 (data字段)")
            data = result.get("data", {})
            if data.get("status") == "succeeded":
                outputs = data.get("outputs", {})
                text_content = outputs.get("text", "")
                logger.info(f"从data.outputs.text提取内容，长度: {len(text_content)}")
        
        # 方法2: 内部Dify格式 (outputs字段)
        elif "outputs" in result:
            logger.info("检测到内部Dify格式 (outputs字段)")
            outputs = result.get("outputs", {})
            text_content = outputs.get("text", "")
            logger.info(f"从outputs.text提取内容，长度: {len(text_content)}")
        
        # 方法3: 流式响应格式 (answer字段)
        elif "answer" in result:
            logger.info("检测到流式响应格式 (answer字段)")
            text_content = result.get("answer", "")
            logger.info(f"从answer提取内容，长度: {len(text_content)}")
        
        # 方法4: 直接文本格式
        elif "text" in result:
            logger.info("检测到直接文本格式 (text字段)")
            text_content = result.get("text", "")
            logger.info(f"从text提取内容，长度: {len(text_content)}")
        
        # 方法5: 未知格式，尝试直接获取文本
        else:
            logger.info("使用未知格式，尝试直接获取文本")
            text_content = str(result)
            logger.info(f"直接转换响应为文本，长度: {len(text_content)}")
        
        if not text_content:
            logger.warning("未找到任何文本内容")
            return ""
        
        # 使用多种标识符提取Python代码
        marker_pairs = [
            ("Py脚本输出开始", "Py脚本输出结束"),
            ("Python代码开始", "Python代码结束"),
            ("```python", "```"),
            ("def ", "if __name__"),
        ]
        
        for start_marker, end_marker in marker_pairs:
            start_index = text_content.find(start_marker)
            if start_index != -1:
                logger.info(f"找到开始标识符: {start_marker}")
                
                # 查找结束标识符
                if end_marker == "```":
                    # 对于代码块，查找下一个```
                    end_index = text_content.find(end_marker, start_index + len(start_marker))
                else:
                    end_index = text_content.find(end_marker, start_index + len(start_marker))
                
                if end_index != -1:
                    # 提取标识符之间的内容
                    python_code = text_content[start_index + len(start_marker):end_index].strip()
                    
                    # 清理代码块标记
                    if start_marker == "```python":
                        python_code = python_code.strip()
                        # 移除可能的多余```
                        python_code = python_code.replace("```", "")
                    
                    logger.info(f"使用标识符对 '{start_marker}' -> '{end_marker}' 成功提取Python代码，长度: {len(python_code)} 字符")
                    return python_code
        
        # 如果没有找到标识符，尝试其他提取方法
        # 方法1: 查找Python代码块标记 (更精确的匹配)
        code_blocks = re.findall(r'```python\s*\n(.*?)\n```', text_content, re.DOTALL)
        if code_blocks:
            logger.info(f"使用正则表达式提取Python代码块，找到 {len(code_blocks)} 个代码块")
            
            # 如果只有一个代码块，返回它
            if len(code_blocks) == 1:
                python_code = code_blocks[0].strip()
                logger.info(f"提取单个代码块，长度: {len(python_code)} 字符")
                return python_code
            else:
                # 如果有多个代码块，合并它们并添加适当的注释
                logger.info(f"检测到多个Python代码块，尝试合并处理")
                
                # 合并所有代码块，添加分隔注释
                merged_code = []
                for i, code_block in enumerate(code_blocks, 1):
                    code_block = code_block.strip()
                    if code_block:
                        merged_code.append(f"# 代码块 {i}")
                        merged_code.append(code_block)
                        merged_code.append("")
                
                python_code = '\n'.join(merged_code).strip()
                logger.info(f"合并 {len(code_blocks)} 个代码块，总长度: {len(python_code)} 字符")
                return python_code
        
        # 方法2: 查找Python导入语句和函数定义
        if 'import ' in text_content or 'def ' in text_content:
            logger.info("检测到Python代码特征，尝试智能提取")
            
            # 查找第一个import或def
            import_index = text_content.find('import ')
            def_index = text_content.find('def ')
            
            start_index = min(import_index, def_index) if import_index != -1 and def_index != -1 else max(import_index, def_index)
            if start_index == -1:
                start_index = max(import_index, def_index)
            
            if start_index != -1:
                # 提取从第一个Python特征到文件结尾的内容
                python_code = text_content[start_index:].strip()
                
                # 尝试找到合理的结束点
                # 查找最后一个函数定义后的合理结束点
                lines = python_code.split('\n')
                cleaned_lines = []
                
                for i, line in enumerate(lines):
                    cleaned_lines.append(line)
                    # 如果遇到空行且后面没有def语句，可能是一个合理的结束点
                    if line.strip() == "" and i + 1 < len(lines):
                        if not lines[i+1].strip().startswith('def '):
                            break
                
                python_code = '\n'.join(cleaned_lines).strip()
                logger.info(f"使用Python特征提取代码，长度: {len(python_code)} 字符")
                return python_code
        
        # 方法3: 返回整个文本内容（作为最后的手段）
        logger.info(f"使用完整文本作为Python代码，长度: {len(text_content)} 字符")
        return text_content.strip()

    def _count_code_blocks(self, python_code: str) -> int:
        """
        统计Python代码中的代码块数量
        
        Args:
            python_code: Python代码字符串
            
        Returns:
            代码块数量
        """
        if not python_code:
            return 0
        
        # 方法1: 通过注释标记统计
        import re
        
        # 统计"# 代码块 X"格式的注释
        code_block_comments = re.findall(r'^#\s*代码块\s*\d+', python_code, re.MULTILINE)
        if code_block_comments:
            logger.info(f"通过注释标记检测到 {len(code_block_comments)} 个代码块")
            return len(code_block_comments)
        
        # 方法2: 通过函数定义统计
        function_defs = re.findall(r'^def\s+\w+\s*\(', python_code, re.MULTILINE)
        if function_defs:
            logger.info(f"通过函数定义检测到 {len(function_defs)} 个代码块")
            return len(function_defs)
        
        # 方法3: 通过类定义统计
        class_defs = re.findall(r'^class\s+\w+', python_code, re.MULTILINE)
        if class_defs:
            logger.info(f"通过类定义检测到 {len(class_defs)} 个代码块")
            return len(class_defs)
        
        # 方法4: 通过导入语句和逻辑分隔统计
        import_statements = re.findall(r'^import\s+\w+|^from\s+\w+\s+import', python_code, re.MULTILINE)
        
        # 如果没有明显的分隔，但代码较长，可能包含多个逻辑块
        lines = python_code.strip().split('\n')
        if len(lines) > 50:
            # 通过空行分隔统计代码块
            empty_line_count = python_code.count('\n\n')
            if empty_line_count > 0:
                logger.info(f"通过空行分隔检测到 {empty_line_count + 1} 个代码块")
                return empty_line_count + 1
        
        # 默认情况下，认为是一个代码块
        logger.info("检测到1个代码块（默认）")
        return 1

    def _fix_common_errors(self, python_code: str) -> str:
        """
        自动修复Python代码中的常见错误
        
        Args:
            python_code: 原始Python代码
            
        Returns:
            修复后的Python代码
        """
        if not python_code:
            return python_code
        
        # 修复1: 确保有正确的导入语句
        if 'import requests' not in python_code and 'import requests' in python_code.lower():
            # 如果requests导入存在但大小写错误，修复它
            python_code = re.sub(r'import requests', 'import requests', python_code, flags=re.IGNORECASE)
        
        if 'import requests' not in python_code:
            # 添加requests导入
            python_code = "import requests\n" + python_code
        
        # 修复2: 确保有正确的main函数调用保护
        if 'if __name__ == "__main__":' not in python_code:
            # 在文件末尾添加main函数调用保护
            lines = python_code.strip().split('\n')
            # 查找最后一个函数定义
            last_function_index = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('def '):
                    last_function_index = i
            
            if last_function_index != -1:
                # 在最后一个函数后添加main调用
                lines.insert(last_function_index + 1, "")
                lines.insert(last_function_index + 2, "if __name__ == \"__main__\":")
                lines.insert(last_function_index + 3, "    main()")
                python_code = '\n'.join(lines)
        
        # 修复3: 确保缩进正确
        # 检查是否有混合的缩进
        if '\t' in python_code and '    ' in python_code:
            # 将制表符转换为4个空格
            python_code = python_code.replace('\t', '    ')
        
        # 修复4: 移除多余的空白行
        python_code = re.sub(r'\n{3,}', '\n\n', python_code)
        
        logger.info(f"自动修复Python代码完成，长度: {len(python_code)} 字符")
        return python_code
    
    def _extract_yaml_table(self, ai_response: str) -> str:
        """
        从AI响应中提取测试用例数据，支持多种格式
        
        Args:
            ai_response: AI返回的完整响应文本
            
        Returns:
            纯表格格式的YAML数据
        """
        if not ai_response:
            return ""
        
        # 首先尝试提取JSON格式的测试用例数据
        json_data = self._extract_json_testcases(ai_response)
        if json_data:
            logger.info("成功提取JSON格式测试用例数据")
            # 将JSON转换为YAML格式
            return self._convert_json_to_yaml(json_data)
        
        # 如果没有找到JSON格式，尝试原来的表格提取方法
        lines = ai_response.split('\n')
        yaml_lines = []
        
        # 定义多种可能的标识符模式
        markers = [
            ("开始生成表格测试用例", "表格测试用例输出结束"),  # 旧格式
            ("开始生成测试用例", "测试用例输出结束"),        # 简化格式
            ("测试用例表格开始", "测试用例表格结束"),        # 新格式
            ("表格开始", "表格结束"),                        # 更简化的格式
        ]
        
        # 尝试每种标识符模式
        for start_marker, end_marker in markers:
            yaml_lines = self._extract_with_markers(ai_response, start_marker, end_marker)
            if yaml_lines:
                logger.info(f"使用标识符模式 '{start_marker}' -> '{end_marker}' 成功提取表格")
                break
        
        # 如果没有找到标识符，尝试直接检测表格格式
        if not yaml_lines:
            yaml_lines = self._extract_direct_table(ai_response)
            if yaml_lines:
                logger.info("使用直接表格检测方法成功提取表格")
        
        # 如果仍然没有找到，使用备选方法
        if not yaml_lines:
            logger.info("使用备选方法提取表格")
            return self._extract_table_fallback(ai_response)
        
        # 清理表格数据，确保每行有相同的列数
        cleaned_lines = self._clean_table_lines(yaml_lines)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_with_markers(self, ai_response: str, start_marker: str, end_marker: str) -> list:
        """使用指定的开始和结束标识符提取表格"""
        lines = ai_response.split('\n')
        yaml_lines = []
        in_table = False
        
        for i, line in enumerate(lines):
            # 检测开始标识符
            if start_marker in line:
                in_table = True
                logger.info(f"找到开始标识符 '{start_marker}'，行 {i}")
                continue
            
            # 检测结束标识符
            if end_marker in line:
                in_table = False
                logger.info(f"找到结束标识符 '{end_marker}'，行 {i}")
                break
            
            # 如果在表格区域内，处理表格行
            if in_table:
                # 跳过空行和表格分隔线
                if not line.strip() or '---' in line.replace(' ', ''):
                    continue
                    
                # 处理Markdown表格行（包含管道符）
                if '|' in line:
                    # 移除行首和行尾的管道符
                    line = line.strip().strip('|').strip()
                    
                    # 分割列并清理每个单元格
                    columns = [col.strip() for col in line.split('|')]
                    
                    # 移除空列
                    columns = [col for col in columns if col]
                    
                    # 如果列数合理（至少2列），则认为是有效的表格行
                    if len(columns) >= 2:
                        # 将列转换为YAML格式
                        yaml_line = ','.join(columns)
                        yaml_lines.append(yaml_line)
                        logger.info(f"提取表格行 {len(yaml_lines)}: {yaml_line}")
                
                # 处理纯表格行（包含逗号分隔）
                elif ',' in line and len(line.split(',')) >= 2:
                    # 直接使用表格格式的行
                    yaml_lines.append(line.strip())
                    logger.info(f"提取表格行 {len(yaml_lines)}: {line.strip()}")
        
        return yaml_lines
    
    def _extract_direct_table(self, ai_response: str) -> list:
        """直接检测表格格式内容"""
        lines = ai_response.split('\n')
        yaml_lines = []
        
        # 检测表头行（包含测试用例相关字段）
        header_fields = ['test_case_id', 'test_case_name', 'api_name', 'method', 'url', 
                        'expected_status_code', '测试用例id', '测试用例名称', 'api名称']
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # 如果行中包含表头字段，认为是表格开始
            if any(field in line_lower for field in header_fields):
                # 检查这一行是否是有效的表格格式
                if ',' in line and len(line.split(',')) >= 2:
                    yaml_lines.append(line.strip())
                    logger.info(f"找到表头行: {line.strip()}")
                    
                    # 继续提取后续的数据行
                    for j in range(i+1, min(i+50, len(lines))):  # 最多提取50行数据
                        data_line = lines[j].strip()
                        if data_line and ',' in data_line and len(data_line.split(',')) >= 2:
                            yaml_lines.append(data_line)
                            logger.info(f"提取数据行 {len(yaml_lines)}: {data_line}")
                        elif not data_line:
                            # 空行可能表示表格结束
                            continue
                        else:
                            # 非表格内容，结束提取
                            break
                    break
        
        return yaml_lines
    
    def _clean_table_lines(self, yaml_lines: list) -> list:
        """清理表格行数据，确保格式一致"""
        if not yaml_lines:
            return []
        
        # 确保第一行是有效的表格表头
        if len(yaml_lines) > 0:
            header_line = yaml_lines[0].lower()
            header_fields = ['test_case_id', 'test_case_name', 'api_name', 'method', 'url', 
                           'expected_status_code', '测试用例id', '测试用例名称', 'api名称']
            
            if not any(field in header_line for field in header_fields):
                # 尝试使用第一行数据作为表头
                if len(yaml_lines) > 1:
                    yaml_lines = yaml_lines[1:]
                else:
                    return []
        
        # 如果表格行数太少，返回空
        if len(yaml_lines) <= 1:
            return []
        
        # 清理表格数据，确保每行有相同的列数
        cleaned_lines = []
        if yaml_lines:
            # 使用第一行作为参考列数
            reference_cols = len(yaml_lines[0].split(','))
            
            for line in yaml_lines:
                cols = line.split(',')
                # 如果列数不匹配，尝试清理
                if len(cols) != reference_cols:
                    # 合并或拆分列以匹配参考列数
                    if len(cols) < reference_cols:
                        # 添加空列
                        cols.extend([''] * (reference_cols - len(cols)))
                    else:
                        # 合并多余的列
                        cols = cols[:reference_cols]
                cleaned_lines.append(','.join(cols))
        
        return cleaned_lines
    
    def _extract_json_testcases(self, ai_response: str) -> dict:
        """从AI响应中提取JSON格式的测试用例数据"""
        import json
        
        # 定义多种可能标识符模式
        marker_patterns = [
            ("开始生成表格测试用例", "表格测试用例输出结束"),  # 旧格式
            ("开始生成测试用例", "测试用例输出结束"),        # 简化格式
            ("测试用例生成开始", "测试用例生成结束"),        # 变体格式
            ("JSON测试用例开始", "JSON测试用例结束"),        # JSON格式标识符
            ("```json", "```"),                            # Markdown代码块
        ]
        
        # 首先尝试查找JSON代码块
        json_str = None
        
        # 方法1: 查找Markdown代码块
        code_block_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', ai_response, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1).strip()
            logger.info("找到Markdown代码块格式的JSON数据")
        
        # 方法2: 尝试各种标识符模式
        if not json_str:
            for start_marker, end_marker in marker_patterns:
                if start_marker in ai_response and end_marker in ai_response:
                    start_idx = ai_response.find(start_marker) + len(start_marker)
                    end_idx = ai_response.find(end_marker)
                    if start_idx < end_idx:
                        json_str = ai_response[start_idx:end_idx].strip()
                        logger.info(f"找到标识符模式: {start_marker} - {end_marker}")
                        break
        
        # 方法3: 尝试在整个响应中查找JSON对象
        if not json_str:
            # 查找第一个{和最后一个}
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = ai_response[start_idx:end_idx+1].strip()
                logger.info("在整个响应中找到可能的JSON数据")
        
        # 方法4: 尝试查找数组格式的测试用例
        if not json_str:
            start_idx = ai_response.find('[')
            end_idx = ai_response.rfind(']')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = ai_response[start_idx:end_idx+1].strip()
                logger.info("找到数组格式的测试用例数据")
        
        if not json_str:
            logger.info("未找到JSON格式的测试用例数据")
            return None
        
        # 清理JSON字符串
        json_str = self._clean_json_string(json_str)
        
        # 尝试解析JSON
        try:
            data = json.loads(json_str)
            
            # 检查数据格式
            if isinstance(data, dict) and 'test_cases' in data:
                logger.info("成功解析JSON测试用例数据（字典格式）")
                return data
            elif isinstance(data, list) and len(data) > 0:
                # 如果是数组格式，转换为标准格式
                logger.info("成功解析JSON测试用例数据（数组格式）")
                return {'test_cases': data}
            else:
                logger.info("JSON数据格式不符合要求")
                return None
                
        except json.JSONDecodeError as e:
            logger.info(f"JSON解析失败: {e}")
            # 尝试修复常见的JSON格式错误
            fixed_json = self._fix_json_errors(json_str)
            if fixed_json:
                try:
                    data = json.loads(fixed_json)
                    if isinstance(data, dict) and 'test_cases' in data:
                        logger.info("修复JSON错误后成功解析")
                        return data
                    elif isinstance(data, list):
                        logger.info("修复JSON错误后成功解析（数组格式）")
                        return {'test_cases': data}
                except Exception:
                    pass
            
            return None
        except Exception as e:
            logger.info(f"JSON解析异常: {e}")
            return None
    
    def _clean_json_string(self, json_str: str) -> str:
        """清理JSON字符串，移除多余的空格和换行"""
        # 移除多余的空格和换行
        json_str = re.sub(r'\s+', ' ', json_str)
        # 修复常见的JSON格式问题
        json_str = re.sub(r',\s*\}', '}', json_str)  # 修复尾随逗号
        json_str = re.sub(r',\s*\]', ']', json_str)  # 修复数组尾随逗号
        return json_str.strip()
    
    def _fix_json_errors(self, json_str: str) -> str:
        """尝试修复常见的JSON格式错误"""
        try:
            # 修复不完整的JSON对象
            if json_str.count('{') > json_str.count('}'):
                json_str += '}' * (json_str.count('{') - json_str.count('}'))
            elif json_str.count('}') > json_str.count('{'):
                json_str = '{' * (json_str.count('}') - json_str.count('{')) + json_str
            
            # 修复不完整的JSON数组
            if json_str.count('[') > json_str.count(']'):
                json_str += ']' * (json_str.count('[') - json_str.count(']'))
            elif json_str.count(']') > json_str.count('['):
                json_str = '[' * (json_str.count(']') - json_str.count('[')) + json_str
            
            # 修复引号不匹配
            json_str = re.sub(r'(?<!\\)"(?!\s*[:,\]}])', '"', json_str)
            
            return json_str
        except Exception:
            return json_str
    
    def _extract_json_content(self, ai_response: str) -> str:
        """
        从AI响应中精准提取JSON内容（备选方案）
        
        Args:
            ai_response: AI返回的完整响应文本
            
        Returns:
            纯JSON格式的内容
        """
        if not ai_response:
            return ""
        
        json_str = None
        
        # 精准解析方案: 查找JSON测试用例开始和结束标识
        start_marker = "表格测试用例输出开始"
        end_marker = "表格测试用例输出结束"
        
        if start_marker in ai_response and end_marker in ai_response:
            start_idx = ai_response.find(start_marker) + len(start_marker)
            end_idx = ai_response.find(end_marker)
            
            if start_idx < end_idx:
                json_str = ai_response[start_idx:end_idx].strip()
                logger.info("备选方案：找到精准标识符格式的JSON数据")
        
        if not json_str:
            logger.info("备选方案：未找到精准格式的JSON测试用例数据")
            return ""
        
        # 清理JSON字符串
        json_str = self._clean_json_string(json_str)
        
        return json_str
    
    def _parse_json_testcases(self, json_content: str) -> list:
        """
        解析JSON内容为测试用例列表
        
        Args:
            json_content: JSON格式的测试用例内容
            
        Returns:
            测试用例列表
        """
        import json
        
        if not json_content:
            return []
        
        try:
            data = json.loads(json_content)
            
            # 检查数据格式
            if isinstance(data, dict) and 'test_cases' in data:
                logger.info("成功解析JSON测试用例数据（字典格式）")
                return data['test_cases']
            elif isinstance(data, list) and len(data) > 0:
                # 如果是数组格式，直接返回
                logger.info("成功解析JSON测试用例数据（数组格式）")
                return data
            else:
                logger.info("JSON数据格式不符合要求")
                return []
                
        except json.JSONDecodeError as e:
            logger.info(f"JSON解析失败: {e}")
            # 尝试修复常见的JSON格式错误
            fixed_json = self._fix_json_errors(json_content)
            if fixed_json:
                try:
                    data = json.loads(fixed_json)
                    if isinstance(data, dict) and 'test_cases' in data:
                        logger.info("修复JSON错误后成功解析")
                        return data['test_cases']
                    elif isinstance(data, list):
                        logger.info("修复JSON错误后成功解析（数组格式）")
                        return data
                except Exception:
                    pass
            
            return []
        except Exception as e:
            logger.info(f"JSON解析异常: {e}")
            return []
    
    def _convert_json_to_yaml(self, json_data: dict) -> str:
        """将JSON格式的测试用例数据转换为YAML格式"""
        import yaml
        
        if not json_data or 'test_cases' not in json_data:
            return ""
        
        test_cases = json_data['test_cases']
        if not test_cases:
            return ""
        
        # 转换为YAML格式
        try:
            yaml_content = yaml.dump(
                {
                    'test_cases': test_cases,
                    '_metadata': {
                        'generated_at': self._get_current_time(),
                        'test_case_count': len(test_cases),
                        'format': 'yaml'
                    }
                },
                allow_unicode=True,
                indent=2,
                default_flow_style=False
            )
            
            logger.info(f"成功将{len(test_cases)}个测试用例转换为YAML格式")
            return yaml_content
            
        except Exception as e:
            logger.error(f"YAML转换失败: {e}")
            return ""
    
    def _convert_yaml_to_json(self, yaml_content: str) -> dict:
        """将YAML格式的测试用例数据转换为JSON格式"""
        import yaml
        
        if not yaml_content:
            return {}
        
        try:
            data = yaml.safe_load(yaml_content)
            
            # 确保返回标准的测试用例格式
            if isinstance(data, dict):
                if 'test_cases' in data:
                    return data
                else:
                    # 如果YAML中没有test_cases键，尝试包装为测试用例格式
                    return {'test_cases': data if isinstance(data, list) else [data]}
            elif isinstance(data, list):
                return {'test_cases': data}
            else:
                return {'test_cases': []}
                
        except Exception as e:
            logger.error(f"YAML转JSON失败: {e}")
            return {'test_cases': []}
    
    def _fix_common_errors(self, python_code: str) -> str:
        """
        修复Python代码中的常见错误
        
        Args:
            python_code: 原始Python代码
            
        Returns:
            修复后的Python代码
        """
        if not python_code:
            logger.warning("传入的Python代码为空")
            return ""
        
        logger.info(f"开始修复常见错误，原始代码长度: {len(python_code)} 字符")
        
        lines = python_code.split('\n')
        fixed_lines = []
        
        # 修复1: 导入语句问题
        import_fixed = False
        for i, line in enumerate(lines):
            original_line = line
            
            # 修复常见的导入错误
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # 确保导入语句格式正确
                if 'import' in line and ' as ' not in line:
                    # 检查是否有不规范的导入
                    if 'import' in line and line.count('import') > 1:
                        # 修复重复import
                        parts = line.split('import')
                        line = 'import'.join([parts[0], parts[-1]])
                        import_fixed = True
            
            # 修复2: main函数调用保护
            if line.strip() == 'if __name__ == "__main__":':
                # 确保main函数调用保护格式正确
                line = 'if __name__ == "__main__":'
            
            # 修复3: 字符串引号问题
            if '"' in line or "'" in line:
                # 检查引号配对问题
                quote_count = line.count('"') + line.count("'")
                if quote_count % 2 != 0:
                    # 尝试修复不匹配的引号
                    if line.count('"') % 2 != 0:
                        line = line.replace('"', "'")
                    elif line.count("'") % 2 != 0:
                        line = line.replace("'", '"')
            
            # 修复4: 缩进问题
            if line.strip() and not line.startswith(' '):
                # 检查是否有缺少缩进的行（在函数内部）
                if i > 0 and fixed_lines and fixed_lines[-1].endswith(':'):
                    # 上一行以冒号结束，这一行应该有缩进
                    line = '    ' + line
            
            # 修复5: 语法错误
            if line.strip().endswith(':') and not line.strip().startswith('#'):
                # 确保冒号后面有内容（除了注释）
                if i + 1 < len(lines) and not lines[i+1].strip():
                    # 下一行是空行，添加pass语句
                    fixed_lines.append(line)
                    fixed_lines.append('    pass')
                    continue
            
            if original_line != line:
                logger.info(f"修复行 {i+1}: '{original_line}' -> '{line}'")
            
            fixed_lines.append(line)
        
        # 修复6: 确保有必要的导入
        has_imports = any(line.strip().startswith(('import ', 'from ')) for line in fixed_lines)
        if not has_imports:
            # 添加基本的导入
            fixed_lines.insert(0, 'import requests')
            fixed_lines.insert(1, 'import json')
            fixed_lines.insert(2, 'import os')
            fixed_lines.insert(3, '')
            logger.info("添加了必要的导入语句")
        
        # 修复7: 确保main函数调用保护
        has_main_guard = any('if __name__ == "__main__":' in line for line in fixed_lines)
        if not has_main_guard:
            # 检查是否有可执行的代码
            executable_lines = [line for line in fixed_lines if line.strip() and 
                              not line.strip().startswith(('#', 'import', 'from', 'def ', 'class '))]
            if executable_lines:
                # 添加main函数调用保护
                fixed_lines.append('')
                fixed_lines.append('if __name__ == "__main__":')
                fixed_lines.append('    # 执行测试')
                fixed_lines.append('    pass')
                logger.info("添加了main函数调用保护")
        
        # 修复缩进和空白行
        fixed_code = '\n'.join(fixed_lines)
        
        # 确保代码以换行符结束
        if not fixed_code.endswith('\n'):
            fixed_code += '\n'
        
        # 修复8: 移除多余的空行
        lines = fixed_code.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            if line.strip() == "":
                if not prev_empty:
                    cleaned_lines.append(line)
                    prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        
        fixed_code = '\n'.join(cleaned_lines)
        
        logger.info(f"修复常见错误完成，修复后代码长度: {len(fixed_code)} 字符")
        return fixed_code
    
    def validate_python_syntax(self, python_code: str) -> Dict[str, Any]:
        """
        验证Python代码语法，提供详细的错误信息
        
        Args:
            python_code: Python代码
            
        Returns:
            验证结果字典
        """
        logger.info(f"开始验证Python代码语法，代码长度: {len(python_code)} 字符")
        
        if not python_code.strip():
            return {"valid": False, "message": "Python代码为空"}
        
        try:
            # 使用Python的compile函数验证语法
            compile(python_code, '<string>', 'exec')
            logger.info("Python代码语法验证通过")
            return {"valid": True, "message": "Python代码语法正确"}
        except SyntaxError as e:
            error_info = {
                "valid": False,
                "message": f"Python代码语法错误",
                "error_type": "SyntaxError",
                "error_msg": str(e),
                "line_number": e.lineno if hasattr(e, 'lineno') else None,
                "offset": e.offset if hasattr(e, 'offset') else None,
                "text": e.text if hasattr(e, 'text') else None
            }
            
            # 提供更友好的错误信息
            if error_info["line_number"]:
                lines = python_code.split('\n')
                if error_info["line_number"] <= len(lines):
                    error_line = lines[error_info["line_number"] - 1]
                    error_info["error_line"] = error_line
                    error_info["suggestion"] = self._get_syntax_error_suggestion(e, error_line)
            
            logger.error(f"Python代码语法错误: {error_info}")
            return error_info
        except Exception as e:
            error_info = {
                "valid": False,
                "message": f"验证过程中发生错误: {str(e)}",
                "error_type": type(e).__name__
            }
            logger.error(f"Python代码验证异常: {error_info}")
            return error_info
    
    def _get_syntax_error_suggestion(self, error: SyntaxError, error_line: str) -> str:
        """
        根据语法错误提供修复建议
        
        Args:
            error: 语法错误对象
            error_line: 错误行内容
            
        Returns:
            修复建议
        """
        error_msg = str(error).lower()
        
        if "unexpected indent" in error_msg:
            return "检查缩进是否正确，确保使用4个空格进行缩进"
        elif "expected an indented block" in error_msg:
            return "在冒号后面需要添加缩进的代码块"
        elif "invalid syntax" in error_msg:
            if "=" in error_line and "==" not in error_line:
                return "检查是否使用了赋值操作符=而不是比较操作符=="
            elif "(" in error_line and ")" not in error_line:
                return "检查括号是否配对"
            elif "[" in error_line and "]" not in error_line:
                return "检查方括号是否配对"
            elif "{" in error_line and "}" not in error_line:
                return "检查花括号是否配对"
            elif "'" in error_line or '"' in error_line:
                return "检查字符串引号是否配对"
        elif "unterminated string literal" in error_msg:
            return "字符串没有正确结束，检查引号配对"
        elif "missing parentheses" in error_msg:
            return "函数调用缺少括号"
        elif "can't assign to" in error_msg:
            return "不能对字面量或表达式进行赋值"
        
        return "请检查代码语法，确保符合Python语法规范"
