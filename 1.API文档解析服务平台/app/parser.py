import yaml
import json
from typing import Dict, List, Any, Optional
from app.md_parser import MarkdownAPIParser

class APIDocParser:
    """OpenAPI/Swagger/Markdown 文档解析器"""
    
    @staticmethod
    def parse_document(content: str, file_type: str) -> Dict[str, Any]:
        """
        解析 API 文档内容
        
        Args:
            content: 文档内容字符串
            file_type: 文件类型 (json, yaml, yml, md, markdown)
            
        Returns:
            解析后的文档结构
            
        Raises:
            ValueError: 文档格式无效或解析失败
        """
        try:
            # Markdown 格式
            if file_type in ['md', 'markdown']:
                return MarkdownAPIParser.parse_document(content)
            
            # OpenAPI/Swagger 格式
            # 根据文件类型解析
            if file_type in ['yaml', 'yml']:
                doc = yaml.safe_load(content)
            else:
                doc = json.loads(content)
            
            # 验证文档格式
            version = doc.get('openapi') or doc.get('swagger')
            if not version:
                raise ValueError("无效的 API 文档格式，缺少 openapi 或 swagger 字段")
            
            # 提取文档信息
            info = doc.get('info', {})
            
            # 解析所有接口
            interfaces = APIDocParser._extract_interfaces(doc)
            
            return {
                'version': version,
                'title': info.get('title', 'Untitled API'),
                'description': info.get('description', ''),
                'base_url': APIDocParser._get_base_url(doc),
                'interfaces': interfaces,
                'raw_doc': doc
            }
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 解析失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {str(e)}")
        except Exception as e:
            raise ValueError(f"文档解析失败: {str(e)}")
    
    @staticmethod
    def _extract_interfaces(doc: Dict) -> List[Dict]:
        """提取所有接口信息"""
        interfaces = []
        paths = doc.get('paths', {})
        interface_counter = 100000  # 从 100000 开始，确保是 6 位数
        
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
                
            for method, details in methods.items():
                # 只处理 HTTP 方法
                if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']:
                    continue
                
                if not isinstance(details, dict):
                    continue
                
                # 生成 6 位数字 ID
                interface_id = str(interface_counter)
                interface_counter += 1
                
                # 保存原始路径和方法用于引用
                original_id = f"{method.upper()}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
                
                # 解析参数
                all_params = details.get('parameters', [])
                
                # 分离 body 参数和其他参数
                body_param = None
                other_params = []
                
                for param in all_params:
                    if isinstance(param, dict):
                        if param.get('in') == 'body':
                            body_param = param
                        else:
                            other_params.append(param)
                
                # 解析请求体（优先使用 requestBody，如果没有则使用 body 参数）
                request_body = None
                if 'requestBody' in details:
                    request_body = APIDocParser._parse_request_body(details.get('requestBody', {}))
                elif body_param:
                    request_body = APIDocParser._parse_request_body(body_param)
                
                interface = {
                    'id': interface_id,
                    'path': path,
                    'method': method.upper(),
                    'summary': details.get('summary', ''),
                    'description': details.get('description', ''),
                    'tags': details.get('tags', []),
                    'operation_id': details.get('operationId', ''),
                    'parameters': APIDocParser._parse_parameters(other_params),
                    'request_body': request_body,
                    'responses': APIDocParser._parse_responses(details.get('responses', {})),
                    'deprecated': details.get('deprecated', False),
                    'consumes': details.get('consumes', []),
                    'produces': details.get('produces', [])
                }
                interfaces.append(interface)
        
        return interfaces
    
    @staticmethod
    def _parse_parameters(params: List) -> List[Dict]:
        """解析参数列表"""
        result = []
        for param in params:
            if not isinstance(param, dict):
                continue
            
            # 跳过 body 类型的参数（这些在 request_body 中处理）
            if param.get('in') == 'body':
                continue
                
            # 获取参数类型
            param_type = param.get('type')
            if not param_type and 'schema' in param:
                schema = param.get('schema', {})
                param_type = schema.get('type', 'string')
                # 如果是数组类型，获取 items 信息
                if param_type == 'array' and 'items' in schema:
                    param_type = f"array<{schema['items'].get('type', 'string')}>"
            
            # 处理枚举值
            enum_values = param.get('enum', [])
            if not enum_values and 'schema' in param:
                enum_values = param.get('schema', {}).get('enum', [])
            
            param_info = {
                'name': param.get('name', ''),
                'in': param.get('in', ''),
                'required': param.get('required', False),
                'type': param_type or 'string',
                'description': param.get('description', ''),
                'example': param.get('example', param.get('schema', {}).get('example')),
                'default': param.get('default', param.get('schema', {}).get('default'))
            }
            
            # 添加枚举值
            if enum_values:
                param_info['enum'] = enum_values
            
            # 添加格式信息
            format_val = param.get('format') or param.get('schema', {}).get('format')
            if format_val:
                param_info['format'] = format_val
            
            result.append(param_info)
        return result
    
    @staticmethod
    def _parse_request_body(body: Dict) -> Optional[Dict]:
        """解析请求体（支持 OpenAPI 3.0 和 Swagger 2.0）"""
        if not body or not isinstance(body, dict):
            return None
        
        # OpenAPI 3.0 格式
        if 'content' in body:
            content = body.get('content', {})
            result = {
                'required': body.get('required', False),
                'description': body.get('description', ''),
                'content_types': list(content.keys()),
                'schema': {}
            }
            
            # 获取第一个 content type 的 schema
            if content:
                first_type = list(content.keys())[0]
                schema = content[first_type].get('schema', {})
                result['schema'] = schema
                result['example'] = content[first_type].get('example')
            
            return result
        
        # Swagger 2.0 格式（body 参数在 parameters 中）
        # 这种情况下 body 参数应该已经被过滤掉了
        # 但如果直接传入 body 参数对象，则处理它
        if body.get('in') == 'body':
            schema = body.get('schema', {})
            schema_ref = schema.get('$ref') or schema.get('originalRef')
            
            result = {
                'required': body.get('required', False),
                'description': body.get('description', ''),
                'content_types': ['application/json'],  # Swagger 2.0 默认
                'schema': schema,
                'schema_ref': schema_ref
            }
            
            return result
        
        return None
    
    @staticmethod
    def _parse_responses(responses: Dict) -> Dict:
        """解析响应定义"""
        result = {}
        for status, details in responses.items():
            if not isinstance(details, dict):
                continue
                
            response_data = {
                'description': details.get('description', ''),
                'content': {}
            }
            
            # 解析响应内容
            content = details.get('content', {})
            for content_type, content_details in content.items():
                response_data['content'][content_type] = {
                    'schema': content_details.get('schema', {}),
                    'example': content_details.get('example')
                }
            
            result[status] = response_data
        
        return result
    
    @staticmethod
    def _get_base_url(doc: Dict) -> str:
        """获取 API 基础 URL"""
        # OpenAPI 3.0
        servers = doc.get('servers', [])
        if servers and isinstance(servers, list) and len(servers) > 0:
            return servers[0].get('url', '')
        
        # Swagger 2.0
        host = doc.get('host', '')
        base_path = doc.get('basePath', '')
        schemes = doc.get('schemes', ['http'])
        
        if host:
            scheme = schemes[0] if schemes else 'http'
            return f"{scheme}://{host}{base_path}"
        
        return ''
