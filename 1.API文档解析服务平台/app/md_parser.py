"""
Markdown 格式 API 文档解析器
支持解析类似智康云系统接口文档的 Markdown 格式
"""
import re
from typing import Dict, List, Any, Optional


class MarkdownAPIParser:
    """Markdown 格式 API 文档解析器"""
    
    # 类变量用于生成接口 ID
    _interface_counter = 100000
    
    @staticmethod
    def parse_document(content: str) -> Dict[str, Any]:
        """
        解析 Markdown 格式的 API 文档
        
        Args:
            content: Markdown 文档内容
            
        Returns:
            解析后的文档结构
        """
        # 提取文档基本信息
        title = MarkdownAPIParser._extract_title(content)
        description = MarkdownAPIParser._extract_description(content)
        host = MarkdownAPIParser._extract_host(content)
        version = MarkdownAPIParser._extract_version(content)
        
        # 提取所有接口
        interfaces = MarkdownAPIParser._extract_interfaces(content)
        
        return {
            'version': version or '1.0',
            'title': title,
            'description': description,
            'base_url': f"http://{host}" if host else '',
            'interfaces': interfaces,
            'format': 'markdown'
        }
    
    @staticmethod
    def _extract_title(content: str) -> str:
        """提取文档标题"""
        # 匹配第一个一级标题
        match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return 'API 文档'
    
    @staticmethod
    def _extract_description(content: str) -> str:
        """提取文档描述"""
        # 查找 **简介**: 后的内容
        match = re.search(r'\*\*简介\*\*:\s*(.+?)(?:\n|$)', content)
        if match:
            return match.group(1).strip()
        return ''
    
    @staticmethod
    def _extract_host(content: str) -> str:
        """提取 HOST 地址"""
        match = re.search(r'\*\*HOST\*\*:\s*(.+?)(?:\n|$)', content)
        if match:
            return match.group(1).strip()
        return ''
    
    @staticmethod
    def _extract_version(content: str) -> str:
        """提取版本号"""
        match = re.search(r'\*\*Version\*\*:\s*(.+?)(?:\n|$)', content)
        if match:
            return match.group(1).strip()
        return ''
    
    @staticmethod
    def _extract_interfaces(content: str) -> List[Dict]:
        """提取所有接口信息"""
        interfaces = []
        
        # 先提取所有一级标题（模块分类）
        lines = content.split('\n')
        current_category = None
        current_section = []
        in_interface = False
        
        for line in lines:
            # 检查是否是一级标题（模块名称）
            if re.match(r'^#\s+[^#]', line):
                # 保存之前的接口
                if current_section and in_interface:
                    section_text = '\n'.join(current_section)
                    interface = MarkdownAPIParser._parse_interface_section(section_text, current_category)
                    if interface:
                        interfaces.append(interface)
                    current_section = []
                    in_interface = False
                
                # 提取模块名称（跳过文档标题）
                category = line.lstrip('#').strip()
                # 跳过文档标题（通常包含"文档"、"接口文档"等）
                if '文档' not in category or '服务' in category:
                    current_category = category
                continue
            
            # 检查是否是二级标题（接口名称）
            if re.match(r'^##\s+', line):
                # 保存之前的接口
                if current_section and in_interface:
                    section_text = '\n'.join(current_section)
                    interface = MarkdownAPIParser._parse_interface_section(section_text, current_category)
                    if interface:
                        interfaces.append(interface)
                
                # 开始新接口
                current_section = [line.lstrip('#').strip()]
                in_interface = True
                continue
            
            # 收集接口内容
            if in_interface:
                current_section.append(line)
        
        # 处理最后一个接口
        if current_section and in_interface:
            section_text = '\n'.join(current_section)
            interface = MarkdownAPIParser._parse_interface_section(section_text, current_category)
            if interface:
                interfaces.append(interface)
        
        return interfaces
    
    @staticmethod
    def _parse_interface_section(section: str, category: Optional[str] = None) -> Optional[Dict]:
        """解析单个接口块"""
        lines = section.split('\n')
        if not lines:
            return None
        
        # 第一行是接口名称
        summary = lines[0].strip()
        
        # 提取接口地址
        path_match = re.search(r'\*\*接口地址\*\*:\s*`(.+?)`', section)
        if not path_match:
            return None
        path = path_match.group(1).strip()
        
        # 提取请求方式
        method_match = re.search(r'\*\*请求方式\*\*:\s*`(.+?)`', section)
        method = method_match.group(1).strip().upper() if method_match else 'POST'
        
        # 提取请求数据类型
        request_type_match = re.search(r'\*\*请求数据类型\*\*:\s*`(.+?)`', section)
        request_content_type = request_type_match.group(1).strip() if request_type_match else 'application/json'
        
        # 提取响应数据类型
        response_type_match = re.search(r'\*\*响应数据类型\*\*:\s*`(.+?)`', section)
        response_content_type = response_type_match.group(1).strip() if response_type_match else '*/*'
        
        # 提取接口描述
        desc_match = re.search(r'\*\*接口描述\*\*:\s*(.+?)(?:\n|$)', section)
        description = desc_match.group(1).strip() if desc_match else ''
        
        # 生成 6 位数字接口 ID
        interface_id = str(MarkdownAPIParser._interface_counter)
        MarkdownAPIParser._interface_counter += 1
        
        # 提取请求示例
        request_example = MarkdownAPIParser._extract_code_block(section, '请求示例')
        
        # 提取请求参数表格
        parameters = MarkdownAPIParser._extract_parameters_table(section)
        
        # 提取响应参数表格
        response_params = MarkdownAPIParser._extract_response_table(section)
        
        # 提取响应示例
        response_example = MarkdownAPIParser._extract_code_block(section, '响应示例')
        
        # 提取响应状态码
        status_codes = MarkdownAPIParser._extract_status_codes(section)
        
        interface = {
            'id': interface_id,
            'path': path,
            'method': method,
            'summary': summary,
            'description': description,
            'tags': [category] if category else [],
            'operation_id': '',
            'parameters': parameters,
            'request_body': {
                'required': True,
                'description': '',
                'content_types': [request_content_type],
                'example': request_example
            } if request_example or method in ['POST', 'PUT', 'PATCH'] else None,
            'responses': {
                str(code): {
                    'description': desc,
                    'schema_ref': '响应消息体' if code == 200 else None
                } for code, desc in status_codes.items()
            },
            'response_parameters': response_params,  # 单独存储响应参数
            'response_example': response_example,
            'deprecated': False,
            'consumes': [request_content_type],
            'produces': [response_content_type]
        }
        
        return interface
    
    @staticmethod
    def _extract_code_block(section: str, block_title: str) -> Optional[str]:
        """提取代码块内容"""
        # 匹配 **标题**: 后的代码块
        pattern = rf'\*\*{block_title}\*\*:.*?```(?:javascript|json)?\s*\n(.*?)```'
        match = re.search(pattern, section, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    @staticmethod
    def _extract_parameters_table(section: str) -> List[Dict]:
        """提取请求参数表格"""
        parameters = []
        
        # 查找请求参数表格
        table_match = re.search(
            r'\*\*请求参数\*\*:.*?\n\n(.*?)(?:\n\n|\*\*响应|$)',
            section,
            re.DOTALL
        )
        
        if not table_match:
            return parameters
        
        table_content = table_match.group(1)
        
        # 解析表格行
        lines = table_content.split('\n')
        headers = []
        data_rows = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('|---'):
                continue
            
            if line.startswith('|'):
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if not headers:
                    headers = cells
                else:
                    data_rows.append(cells)
        
        # 解析参数行（包含嵌套参数）
        for row in data_rows:
            if len(row) < len(headers):
                continue
            
            param_name = row[0] if len(row) > 0 else ''
            
            # 跳过空行
            if not param_name:
                continue
            
            # 处理嵌套参数（移除 &emsp; 前缀，但保留参数）
            display_name = param_name
            is_nested = False
            if param_name.startswith('&emsp;'):
                # 移除所有 &emsp; 前缀
                display_name = re.sub(r'^(&emsp;)+', '', param_name)
                is_nested = True
            
            param_desc = row[1] if len(row) > 1 else ''
            param_in = row[2] if len(row) > 2 else 'body'
            param_required = row[3].lower() == 'true' if len(row) > 3 else False
            param_type = row[4] if len(row) > 4 else 'string'
            param_schema = row[5] if len(row) > 5 else ''
            
            # 处理数组类型
            if param_type == 'array' and param_schema:
                param_type = f"array<{param_schema}>"
            
            parameters.append({
                'name': display_name,
                'in': param_in,
                'required': param_required,
                'type': param_type,
                'description': param_desc,
                'schema_ref': param_schema if param_schema else None,
                'is_nested': is_nested,
                'example': None,
                'default': None
            })
        
        return parameters
    
    @staticmethod
    def _extract_response_table(section: str) -> List[Dict]:
        """提取响应参数表格"""
        response_params = []
        
        # 查找响应参数表格
        table_match = re.search(
            r'\*\*响应参数\*\*:.*?\n\n(.*?)(?:\n\n|\*\*响应示例|$)',
            section,
            re.DOTALL
        )
        
        if not table_match:
            return response_params
        
        table_content = table_match.group(1)
        
        # 解析表格行
        lines = table_content.split('\n')
        headers = []
        data_rows = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('|---'):
                continue
            
            if line.startswith('|'):
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if not headers:
                    headers = cells
                else:
                    data_rows.append(cells)
        
        # 解析响应字段（包含嵌套字段）
        for row in data_rows:
            if len(row) < 3:
                continue
            
            field_name = row[0] if len(row) > 0 else ''
            
            # 跳过空行
            if not field_name:
                continue
            
            # 处理嵌套字段（移除 &emsp; 前缀，但保留字段）
            display_name = field_name
            is_nested = False
            if field_name.startswith('&emsp;'):
                display_name = re.sub(r'^(&emsp;)+', '', field_name)
                is_nested = True
            
            field_desc = row[1] if len(row) > 1 else ''
            field_type = row[2] if len(row) > 2 else 'string'
            field_schema = row[3] if len(row) > 3 else ''
            
            response_params.append({
                'name': display_name,
                'description': field_desc,
                'type': field_type,
                'schema': field_schema if field_schema else None,
                'is_nested': is_nested
            })
        
        return response_params
    
    @staticmethod
    def _extract_status_codes(section: str) -> Dict[int, str]:
        """提取响应状态码"""
        status_codes = {}
        
        # 查找响应状态表格
        table_match = re.search(
            r'\*\*响应状态\*\*:.*?\n\n(.*?)(?:\n\n|\*\*响应参数|$)',
            section,
            re.DOTALL
        )
        
        if not table_match:
            # 默认返回 200
            return {200: 'OK'}
        
        table_content = table_match.group(1)
        
        # 解析表格行
        lines = table_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('|---') or '状态码' in line:
                continue
            
            if line.startswith('|'):
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if len(cells) >= 2:
                    try:
                        code = int(cells[0])
                        desc = cells[1]
                        status_codes[code] = desc
                    except ValueError:
                        continue
        
        return status_codes if status_codes else {200: 'OK'}
