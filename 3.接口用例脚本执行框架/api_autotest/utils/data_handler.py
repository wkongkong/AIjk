import pandas as pd
import yaml
import os
import json
from typing import List, Dict, Any, Union


class DataHandler:
    @staticmethod
    def load_test_cases(file_path: str) -> List[Dict[str, Any]]:
        """
        加载测试用例数据，支持CSV和YAML格式
        
        Args:
            file_path: 测试用例文件路径（.csv 或 .yaml/.yml）
            
        Returns:
            测试用例列表
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"测试用例文件不存在: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.csv':
            return DataHandler._load_csv(file_path)
        elif file_ext in ['.yaml', '.yml']:
            return DataHandler._load_yaml(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}，仅支持 .csv, .yaml, .yml")
    
    @staticmethod
    def _load_csv(csv_path: str) -> List[Dict[str, Any]]:
        """加载CSV格式的测试用例"""
        df = pd.read_csv(csv_path, encoding='utf-8')
        test_cases = df.to_dict("records")
        
        # 处理CSV中的JSON字符串字段
        for test_case in test_cases:
            for key in ['headers', 'request_data', 'expected_response']:
                if key in test_case and isinstance(test_case[key], str):
                    try:
                        test_case[key] = json.loads(test_case[key])
                    except (json.JSONDecodeError, ValueError):
                        # 如果解析失败，保持原值
                        pass
            
            # 处理tags字段（CSV中可能是逗号分隔的字符串）
            if 'tags' in test_case and isinstance(test_case['tags'], str):
                test_case['tags'] = [tag.strip() for tag in test_case['tags'].split(',')]
        
        return test_cases
    
    @staticmethod
    def _load_yaml(yaml_path: str) -> List[Dict[str, Any]]:
        """加载YAML格式的测试用例"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # YAML文件应该包含test_cases键
        if isinstance(data, dict) and 'test_cases' in data:
            return data['test_cases']
        elif isinstance(data, list):
            # 如果直接是列表格式
            return data
        else:
            raise ValueError(f"YAML文件格式错误，应包含 'test_cases' 键或直接为列表格式")
    
    @staticmethod
    def load_all_test_cases_from_dir(directory: str, file_pattern: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        从目录加载所有测试用例文件
        
        Args:
            directory: 测试用例目录路径
            file_pattern: 文件名模式（可选），如 'test_*.csv'
            
        Returns:
            字典，key为文件名（不含扩展名），value为测试用例列表
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        all_test_cases = {}
        
        # 支持的文件扩展名
        supported_extensions = ['.csv', '.yaml', '.yml']
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # 跳过目录和README文件
            if os.path.isdir(file_path) or filename.lower() == 'readme.md':
                continue
            
            # 检查文件扩展名
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in supported_extensions:
                continue
            
            # 如果指定了文件模式，进行匹配
            if file_pattern:
                import fnmatch
                if not fnmatch.fnmatch(filename, file_pattern):
                    continue
            
            try:
                # 加载测试用例
                test_cases = DataHandler.load_test_cases(file_path)
                file_key = os.path.splitext(filename)[0]
                all_test_cases[file_key] = test_cases
            except Exception as e:
                print(f"警告: 加载文件 {filename} 失败: {e}")
        
        return all_test_cases

    @staticmethod
    def group_by_module(test_cases: Union[pd.DataFrame, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """按模块分组测试用例"""
        # 如果是DataFrame，转换为字典列表
        if isinstance(test_cases, pd.DataFrame):
            test_cases = test_cases.to_dict("records")
        
        # 按模块或api_name分组
        grouped = {}
        for test_case in test_cases:
            key = test_case.get('module') or test_case.get('api_name', 'default')
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(test_case)
        
        return grouped
