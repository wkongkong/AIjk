from flask import Flask
from flask_cors import CORS
from app.dify_client import DifyClient
from app.storage import storage
import json
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # JSON 配置 - 中文不转义
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
    
    # 设置 JSON 编码器，确保中文不转义
    app.json.ensure_ascii = False
    
    # 持久化存储配置
    app.config['STORAGE'] = storage
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 最大文件大小
    
    # Dify配置
    dify_api_key_yaml = os.getenv('DIFY_API_KEY_YAML', '')
    dify_workflow_yaml_url = os.getenv('DIFY_WORKFLOW_YAML_URL', '')
    dify_api_key_python = os.getenv('DIFY_API_KEY_PYTHON', '')
    dify_workflow_python_url = os.getenv('DIFY_WORKFLOW_PYTHON_URL', '')
    
    if dify_api_key_yaml and dify_workflow_yaml_url and dify_api_key_python and dify_workflow_python_url:
        app.config['DIFY_CLIENT'] = DifyClient(
            api_key_yaml=dify_api_key_yaml,
            workflow_yaml_url=dify_workflow_yaml_url,
            api_key_python=dify_api_key_python,
            workflow_python_url=dify_workflow_python_url
        )
        app.logger.info("Dify客户端已初始化")
    else:
        app.config['DIFY_CLIENT'] = None
        app.logger.warning("Dify配置不完整，相关功能将不可用")
    
    # 注册蓝图
    from app.routes import api_bp, web_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)
    
    return app
