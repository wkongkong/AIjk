import pytest
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.data_handler import DataHandler


def pytest_generate_tests(metafunc):
    """
    动态生成测试参数 - 支持CSV和YAML格式
    
    支持三种模式：
    1. 通用模式：test_common.py 自动扫描 data_csv 和 data_yaml 目录（排除 dl_ 开头的文件）
    2. 指定模式：通过命令行参数指定具体的测试用例文件
    3. 集合筛选模式：通过环境变量 COLLECTION_ID 筛选特定集合的测试用例
    
    注意：
    - 以 dl_ 开头的测试用例文件需要使用独立的测试脚本（1对1映射）
    - 独立测试脚本（dl_*.py）不使用此conftest的参数化功能
    """
    # 只对 test_common.py 生效，独立测试脚本自己处理参数化
    if metafunc.module.__name__ != 'testcases.test_common':
        return
    
    if "test_case" in metafunc.fixturenames:
        # 获取命令行参数
        data_file = metafunc.config.getoption("--data-file", None)
        data_dir_option = metafunc.config.getoption("--data-dir", None)
        
        # 获取环境变量 - 用于Jenkins集成
        collection_id_filter = os.getenv('COLLECTION_ID', '*')
        execute_all = os.getenv('EXECUTE_ALL', 'false').lower() == 'true'
        
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(__file__))
        
        test_cases = []
        test_ids = []
        
        # 模式1：指定具体的测试用例文件
        if data_file:
            if not os.path.isabs(data_file):
                data_file = os.path.join(project_root, data_file)
            
            try:
                cases = DataHandler.load_test_cases(data_file)
                test_cases.extend(cases)
                file_name = os.path.basename(data_file)
                test_ids.extend([f"{file_name}::{tc.get('test_case_id', 'unknown')}" for tc in cases])
            except Exception as e:
                pytest.skip(f"无法加载测试用例文件 {data_file}: {e}")
        
        # 模式2：扫描指定目录（默认扫描 data_csv 和 data_yaml，排除 dl_ 开头的文件）
        else:
            # 确定要扫描的目录
            if data_dir_option:
                scan_dirs = [data_dir_option]
            else:
                # 默认扫描 data_csv 和 data_yaml 目录
                scan_dirs = [
                    os.path.join(project_root, "data_csv"),
                    os.path.join(project_root, "data_yaml")
                ]
            
            # 打印筛选信息（用于Jenkins日志）
            if collection_id_filter != '*' and not execute_all:
                print(f"\n{'='*60}")
                print(f"🔍 按集合ID筛选测试用例")
                print(f"   COLLECTION_ID: {collection_id_filter}")
                print(f"   文件模式: test_cases_{collection_id_filter}_*.yaml")
                print(f"{'='*60}\n")
            elif execute_all:
                print(f"\n{'='*60}")
                print(f"📋 执行所有测试用例 (EXECUTE_ALL=true)")
                print(f"{'='*60}\n")
            else:
                print(f"\n{'='*60}")
                print(f"📋 执行所有测试用例 (COLLECTION_ID=*)")
                print(f"{'='*60}\n")
            
            # 从所有目录加载测试用例（排除 dl_ 开头的文件）
            for scan_dir in scan_dirs:
                if not os.path.exists(scan_dir):
                    continue
                
                try:
                    all_cases = DataHandler.load_all_test_cases_from_dir(scan_dir)
                    for file_key, cases in all_cases.items():
                        # 排除以 dl_ 开头的文件（这些文件使用独立测试脚本）
                        if file_key.startswith('dl_'):
                            continue
                        
                        # 根据集合ID筛选文件
                        if collection_id_filter != '*' and not execute_all:
                            # 检查文件名是否包含集合ID
                            # 文件名格式：test_cases_{COLLECTION_ID}_{INTERFACE_ID}.yaml
                            if f'_{collection_id_filter}_' not in file_key:
                                print(f"   ⏭️  跳过: {file_key} (不匹配集合ID)")
                                continue
                            else:
                                print(f"   ✅ 加载: {file_key} (匹配集合ID)")
                        
                        test_cases.extend(cases)
                        # 生成测试ID：文件名::用例ID
                        test_ids.extend([f"{file_key}::{tc.get('test_case_id', 'unknown')}" for tc in cases])
                except Exception as e:
                    print(f"警告: 扫描目录 {scan_dir} 失败: {e}")
            
            # 打印筛选结果
            if collection_id_filter != '*' and not execute_all:
                print(f"\n{'='*60}")
                print(f"📊 筛选结果: 找到 {len(test_cases)} 个测试用例")
                print(f"{'='*60}\n")
        
        # 如果没有找到测试用例，跳过测试
        if not test_cases:
            if collection_id_filter != '*' and not execute_all:
                pytest.skip(f"未找到匹配集合ID '{collection_id_filter}' 的测试用例")
            else:
                pytest.skip("未找到任何测试用例")
        
        # 参数化测试用例
        metafunc.parametrize("test_case", test_cases, ids=test_ids)


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--data-file",
        action="store",
        default=None,
        help="指定要执行的测试用例文件路径（支持CSV和YAML格式）"
    )
    parser.addoption(
        "--data-dir",
        action="store",
        default=None,
        help="指定要扫描的测试用例目录（默认扫描 data_csv 和 data_yaml）"
    )
