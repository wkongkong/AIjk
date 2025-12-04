#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根据集合ID筛选并执行测试用例

使用方式：
1. 执行所有用例：
   export COLLECTION_ID="*"
   python run_by_collection.py

2. 执行特定集合的用例：
   export COLLECTION_ID="07d2c7b2-482c-4c7b-a414-0d356682554d"
   python run_by_collection.py

3. Jenkins 集成：
   在Jenkins Job中配置COLLECTION_ID参数，然后执行此脚本
"""
import os
import sys
import glob
import subprocess
from datetime import datetime

def main():
    print('=' * 60)
    print('API 测试用例执行脚本 - 按集合ID筛选')
    print('=' * 60)
    print(f'执行时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # 获取环境变量
    collection_id = os.getenv('COLLECTION_ID', '*')
    execute_all = os.getenv('EXECUTE_ALL', 'false').lower() == 'true'
    data_dir = os.getenv('DATA_DIR', 'data_yaml')
    
    print(f'环境变量:')
    print(f'  COLLECTION_ID: {collection_id}')
    print(f'  EXECUTE_ALL: {execute_all}')
    print(f'  DATA_DIR: {data_dir}')
    print()
    
    # 检查数据目录是否存在
    if not os.path.exists(data_dir):
        print(f'❌ 错误：数据目录不存在: {data_dir}')
        sys.exit(1)
    
    # 构建文件匹配模式
    if collection_id == '*' or execute_all:
        pattern = f'{data_dir}/test_cases_*.yaml'
        print(f'📋 执行模式：所有测试用例')
    else:
        pattern = f'{data_dir}/test_cases_{collection_id}_*.yaml'
        print(f'📋 执行模式：集合 {collection_id} 的测试用例')
    
    print(f'🔍 搜索模式：{pattern}')
    print()
    
    # 查找匹配的文件
    test_files = glob.glob(pattern)
    
    if not test_files:
        print(f'❌ 错误：未找到匹配的测试用例文件')
        print(f'   搜索模式：{pattern}')
        print(f'   数据目录：{os.path.abspath(data_dir)}')
        print()
        print('💡 提示：')
        print('   1. 检查测试用例文件是否已从SVN更新')
        print('   2. 检查文件命名是否符合规范：test_cases_{COLLECTION_ID}_{INTERFACE_ID}.yaml')
        print('   3. 检查COLLECTION_ID参数是否正确')
        sys.exit(1)
    
    # 排序文件列表
    test_files.sort()
    
    print(f'✅ 找到 {len(test_files)} 个测试用例文件：')
    for i, f in enumerate(test_files, 1):
        file_size = os.path.getsize(f)
        print(f'   {i}. {os.path.basename(f)} ({file_size} bytes)')
    print()
    
    # 构建 pytest 命令
    cmd = [
        'python', '-m', 'pytest',
        'testcases/test_common.py',
        f'--data-dir={data_dir}',
        '-v',
        '--alluredir=./allure-results',
        '--clean-alluredir'
    ]
    
    print(f'🚀 执行命令：')
    print(f'   {" ".join(cmd)}')
    print()
    print('=' * 60)
    print('开始执行测试...')
    print('=' * 60)
    print()
    
    # 执行 pytest
    result = subprocess.run(cmd)
    
    print()
    print('=' * 60)
    if result.returncode == 0:
        print('✅ 测试执行完成')
    else:
        print(f'❌ 测试执行失败 (退出码: {result.returncode})')
    print('=' * 60)
    
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
