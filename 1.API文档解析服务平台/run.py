#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API 文档解析服务启动脚本
"""
import os
from app import create_app
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 打印环境变量状态用于调试
print("环境变量检查:")
print(f"DIFY_API_KEY_YAML: {'已设置' if os.getenv('DIFY_API_KEY_YAML') else '未设置'}")
print(f"DIFY_WORKFLOW_YAML_URL: {'已设置' if os.getenv('DIFY_WORKFLOW_YAML_URL') else '未设置'}")
print(f"DIFY_API_KEY_PYTHON: {'已设置' if os.getenv('DIFY_API_KEY_PYTHON') else '未设置'}")
print(f"DIFY_WORKFLOW_PYTHON_URL: {'已设置' if os.getenv('DIFY_WORKFLOW_PYTHON_URL') else '未设置'}")

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("API 文档解析服务启动中...")
    print("服务地址: http://0.0.0.0:5000")
    print("健康检查: http://0.0.0.0:5000/api/health")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
