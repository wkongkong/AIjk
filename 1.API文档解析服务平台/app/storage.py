"""
数据持久化存储模块
使用JSON文件存储解析的API文档数据，确保服务重启后数据不丢失
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class JSONStorage:
    """JSON文件存储管理器"""
    
    def __init__(self, storage_dir: str = "data"):
        """
        初始化存储管理器
        
        Args:
            storage_dir: 存储目录路径
        """
        self.storage_dir = storage_dir
        self.data_file = os.path.join(storage_dir, "collections.json")
        self.testcases_file = os.path.join(storage_dir, "testcases.json")
        self._ensure_storage_dir()
        
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            logger.info(f"创建存储目录: {self.storage_dir}")
    
    def load_collections(self) -> Dict[str, Any]:
        """
        从文件加载所有集合数据
        
        Returns:
            集合数据字典
        """
        if not os.path.exists(self.data_file):
            logger.info("数据文件不存在，返回空字典")
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 返回collections字段的内容，而不是整个数据结构
                collections = data.get('collections', {})
                logger.info(f"成功加载 {len(collections)} 个集合")
                return collections
        except Exception as e:
            logger.error(f"加载数据文件失败: {e}")
            return {}
    
    def save_collections(self, collections: Dict[str, Any]) -> bool:
        """
        保存集合数据到文件
        
        Args:
            collections: 集合数据字典
            
        Returns:
            保存是否成功
        """
        try:
            # 添加时间戳和元数据
            data_to_save = {
                "_metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "collection_count": len(collections)
                },
                "collections": collections
            }
            
            # 写入文件
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(collections)} 个集合到文件")
            return True
            
        except Exception as e:
            logger.error(f"保存数据文件失败: {e}")
            return False
    
    def add_collection(self, collection_data: Dict[str, Any]) -> str:
        """
        添加新的集合
        
        Args:
            collection_data: 集合数据
            
        Returns:
            集合ID
        """
        collections = self.load_collections()
        collection_id = str(uuid.uuid4())
        
        # 添加创建时间
        collection_data["_created_at"] = datetime.now().isoformat()
        collection_data["_id"] = collection_id
        
        collections[collection_id] = collection_data
        
        if self.save_collections(collections):
            logger.info(f"成功添加集合: {collection_id}")
            return collection_id
        else:
            raise Exception("保存集合失败")
    
    def get_collection(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定集合
        
        Args:
            collection_id: 集合ID
            
        Returns:
            集合数据，如果不存在返回None
        """
        collections = self.load_collections()
        return collections.get(collection_id)
    
    def update_collection(self, collection_id: str, collection_data: Dict[str, Any]) -> bool:
        """
        更新集合数据
        
        Args:
            collection_id: 集合ID
            collection_data: 新的集合数据
            
        Returns:
            更新是否成功
        """
        collections = self.load_collections()
        
        if collection_id not in collections:
            logger.warning(f"集合不存在: {collection_id}")
            return False
        
        # 保留创建时间和ID
        collection_data["_created_at"] = collections[collection_id].get("_created_at")
        collection_data["_id"] = collection_id
        collection_data["_updated_at"] = datetime.now().isoformat()
        
        collections[collection_id] = collection_data
        
        return self.save_collections(collections)
    
    def delete_collection(self, collection_id: str) -> bool:
        """
        删除集合
        
        Args:
            collection_id: 集合ID
            
        Returns:
            删除是否成功
        """
        collections = self.load_collections()
        
        if collection_id not in collections:
            logger.warning(f"集合不存在: {collection_id}")
            return False
        
        del collections[collection_id]
        
        return self.save_collections(collections)
    
    def get_all_collections(self) -> Dict[str, Any]:
        """
        获取所有集合
        
        Returns:
            所有集合数据
        """
        return self.load_collections()
    
    def collection_exists(self, collection_id: str) -> bool:
        """
        检查集合是否存在
        
        Args:
            collection_id: 集合ID
            
        Returns:
            是否存在
        """
        collections = self.load_collections()
        return collection_id in collections

    def load_testcases(self) -> Dict[str, Any]:
        """
        从文件加载所有测试用例数据
        
        Returns:
            测试用例数据字典
        """
        if not os.path.exists(self.testcases_file):
            logger.info("测试用例文件不存在，返回空字典")
            return {}
        
        try:
            with open(self.testcases_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                testcases = data.get('testcases', {})
                
                # 处理不同的数据格式
                if isinstance(testcases, list):
                    # 如果是数组格式，转换为字典格式
                    logger.info(f"检测到数组格式的测试用例数据，包含 {len(testcases)} 个测试用例")
                    # 创建一个空的字典，因为数组格式无法直接用于键值存储
                    return {}
                elif isinstance(testcases, dict):
                    logger.info(f"成功加载 {len(testcases)} 个接口的测试用例")
                    return testcases
                else:
                    logger.warning(f"未知的测试用例格式: {type(testcases)}")
                    return {}
                    
        except Exception as e:
            logger.error(f"加载测试用例文件失败: {e}")
            return {}

    def save_testcases(self, testcases: Dict[str, Any]) -> bool:
        """
        保存测试用例数据到文件
        
        Args:
            testcases: 测试用例数据字典
            
        Returns:
            保存是否成功
        """
        try:
            # 添加时间戳和元数据
            data_to_save = {
                "_metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "testcase_count": len(testcases)
                },
                "testcases": testcases
            }
            
            # 写入文件
            with open(self.testcases_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(testcases)} 个接口的测试用例到文件")
            return True
            
        except Exception as e:
            logger.error(f"保存测试用例文件失败: {e}")
            return False

    def save_testcase(self, collection_id: str, interface_id: str, yaml_content: str = None, json_content: str = None, workflow_id: str = None) -> bool:
        """
        保存测试用例
        
        Args:
            collection_id: 集合ID
            interface_id: 接口ID
            yaml_content: YAML内容（可选）
            json_content: JSON内容（可选）
            workflow_id: 工作流ID（可选）
            
        Returns:
            保存是否成功
        """
        testcases = self.load_testcases()
        
        # 创建测试用例键
        testcase_key = f"{collection_id}_{interface_id}"
        
        testcases[testcase_key] = {
            "collection_id": collection_id,
            "interface_id": interface_id,
            "yaml_content": yaml_content or "",
            "json_content": json_content or "",
            "workflow_id": workflow_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        return self.save_testcases(testcases)

    def get_testcase(self, collection_id: str, interface_id: str) -> Optional[Dict[str, Any]]:
        """
        获取测试用例
        
        Args:
            collection_id: 集合ID
            interface_id: 接口ID
            
        Returns:
            测试用例数据，如果不存在返回None
        """
        testcases = self.load_testcases()
        testcase_key = f"{collection_id}_{interface_id}"
        return testcases.get(testcase_key)

    def has_testcase(self, collection_id: str, interface_id: str) -> bool:
        """
        检查是否存在测试用例
        
        Args:
            collection_id: 集合ID
            interface_id: 接口ID
            
        Returns:
            是否存在测试用例
        """
        testcases = self.load_testcases()
        testcase_key = f"{collection_id}_{interface_id}"
        return testcase_key in testcases

    def delete_testcase(self, collection_id: str, interface_id: str) -> bool:
        """
        删除测试用例
        
        Args:
            collection_id: 集合ID
            interface_id: 接口ID
            
        Returns:
            删除是否成功
        """
        testcases = self.load_testcases()
        testcase_key = f"{collection_id}_{interface_id}"
        
        if testcase_key not in testcases:
            logger.warning(f"测试用例不存在: {testcase_key}")
            return False
        
        del testcases[testcase_key]
        return self.save_testcases(testcases)

    def save_python_script(self, collection_id: str, interface_id: str, python_code: str, workflow_id: str = None) -> bool:
        """
        保存Python脚本到文件系统，确保重启服务后仍可访问
        
        Args:
            collection_id: 集合ID
            interface_id: 接口ID
            python_code: Python代码内容
            workflow_id: 工作流ID（可选）
            
        Returns:
            保存是否成功
        """
        try:
            # 创建Python脚本存储目录
            python_scripts_dir = os.path.join(self.storage_dir, "python_scripts")
            if not os.path.exists(python_scripts_dir):
                os.makedirs(python_scripts_dir)
                logger.info(f"创建Python脚本存储目录: {python_scripts_dir}")
            
            # 生成Python脚本文件名
            script_filename = f"{collection_id}_{interface_id}.py"
            script_filepath = os.path.join(python_scripts_dir, script_filename)
            
            # 写入Python脚本文件
            with open(script_filepath, 'w', encoding='utf-8') as f:
                f.write(python_code)
            
            # 同时更新测试用例数据中的Python脚本信息
            testcases = self.load_testcases()
            testcase_key = f"{collection_id}_{interface_id}"
            
            if testcase_key not in testcases:
                testcases[testcase_key] = {}
            
            testcases[testcase_key].update({
                "collection_id": collection_id,
                "interface_id": interface_id,
                "python_code": python_code,
                "python_script_path": script_filepath,
                "python_workflow_id": workflow_id,
                "python_generated_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
            
            # 保存更新后的测试用例数据
            success = self.save_testcases(testcases)
            
            if success:
                logger.info(f"成功保存Python脚本: {script_filepath} (代码长度: {len(python_code)})")
                return True
            else:
                logger.error(f"保存Python脚本元数据失败")
                return False
                
        except Exception as e:
            logger.error(f"保存Python脚本失败: {e}")
            return False

    def get_python_script(self, collection_id: str, interface_id: str) -> Optional[Dict[str, Any]]:
        """
        获取已保存的Python脚本
        
        Args:
            collection_id: 集合ID
            interface_id: 接口ID
            
        Returns:
            Python脚本信息字典，包含代码、文件路径等信息
        """
        testcases = self.load_testcases()
        testcase_key = f"{collection_id}_{interface_id}"
        
        if testcase_key not in testcases:
            return None
        
        testcase_data = testcases[testcase_key]
        
        # 检查是否已有Python脚本
        if "python_code" in testcase_data:
            return testcase_data
        
        # 如果测试用例数据中有Python脚本路径，尝试从文件读取
        if "python_script_path" in testcase_data:
            script_path = testcase_data["python_script_path"]
            if os.path.exists(script_path):
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        python_code = f.read()
                    
                    # 更新数据
                    testcase_data["python_code"] = python_code
                    return testcase_data
                except Exception as e:
                    logger.error(f"读取Python脚本文件失败: {e}")
        
        return None

    def has_python_script(self, collection_id: str, interface_id: str) -> bool:
        """
        检查是否存在已保存的Python脚本
        
        Args:
            collection_id: 集合ID
            interface_id: 接口ID
            
        Returns:
            是否存在Python脚本
        """
        script_info = self.get_python_script(collection_id, interface_id)
        return script_info is not None and "python_code" in script_info

    def delete_python_script(self, collection_id: str, interface_id: str) -> bool:
        """
        删除Python脚本
        
        Args:
            collection_id: 集合ID
            interface_id: 接口ID
            
        Returns:
            删除是否成功
        """
        try:
            testcases = self.load_testcases()
            testcase_key = f"{collection_id}_{interface_id}"
            
            if testcase_key not in testcases:
                return False
            
            testcase_data = testcases[testcase_key]
            
            # 删除Python脚本文件
            if "python_script_path" in testcase_data:
                script_path = testcase_data["python_script_path"]
                if os.path.exists(script_path):
                    os.remove(script_path)
                    logger.info(f"删除Python脚本文件: {script_path}")
            
            # 清除Python脚本相关字段
            python_fields = ["python_code", "python_script_path", "python_workflow_id", "python_generated_at"]
            for field in python_fields:
                if field in testcase_data:
                    del testcase_data[field]
            
            # 保存更新后的数据
            return self.save_testcases(testcases)
            
        except Exception as e:
            logger.error(f"删除Python脚本失败: {e}")
            return False


# 全局存储实例
storage = JSONStorage()