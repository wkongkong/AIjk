from flask import Blueprint, request, jsonify, current_app, render_template, send_file
from werkzeug.utils import secure_filename
from app.parser import APIDocParser
from app.dify_client import DifyClient
from datetime import datetime
import uuid
import traceback
import io
import os

api_bp = Blueprint('api', __name__, url_prefix='/api')
web_bp = Blueprint('web', __name__)

@api_bp.route('/upload', methods=['POST'])
def upload_document():
    """
    上传并解析 API 文档
    
    请求:
        - file: multipart/form-data 文件上传
        
    响应:
        - 201: 上传成功
        - 400: 请求错误
        - 500: 服务器错误
    """
    try:
        # 检查文件是否存在
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '未找到文件，请使用 multipart/form-data 上传'
            }), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            }), 400
        
        # 验证文件类型
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in ['json', 'yaml', 'yml', 'md', 'markdown']:
            return jsonify({
                'success': False,
                'error': '不支持的文件格式，仅支持 .json, .yaml, .yml, .md, .markdown'
            }), 400
        
        # 读取文件内容
        content = file.read().decode('utf-8')
        
        # 解析文档
        parsed_doc = APIDocParser.parse_document(content, file_ext)
        
        # 存储到持久化存储
        storage = current_app.config['STORAGE']
        collection_id = storage.add_collection(parsed_doc)
        
        return jsonify({
            'success': True,
            'collection_id': collection_id,
            'title': parsed_doc['title'],
            'description': parsed_doc['description'],
            'version': parsed_doc['version'],
            'base_url': parsed_doc['base_url'],
            'interface_count': len(parsed_doc['interfaces'])
        }), 201
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"上传文档失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@api_bp.route('/collections', methods=['GET'])
def get_collections():
    """
    获取所有文档集合列表
    
    响应:
        - 200: 成功返回集合列表
    """
    storage = current_app.config['STORAGE']
    collections = storage.get_all_collections()
    
    result = []
    for cid, doc in collections.items():
        # 计算模块数量（从接口的tags中提取唯一模块）
        modules = set()
        for interface in doc['interfaces']:
            if interface.get('tags'):
                for tag in interface['tags']:
                    modules.add(tag)
        
        result.append({
            'collection_id': cid,
            'title': doc['title'],
            'description': doc['description'],
            'version': doc['version'],
            'base_url': doc['base_url'],
            'interface_count': len(doc['interfaces']),
            'module_count': len(modules)
        })
    
    return jsonify({
        'success': True,
        'collections': result,
        'total': len(result)
    }), 200

@api_bp.route('/collection/<collection_id>', methods=['GET'])
def get_collection(collection_id):
    """
    获取指定集合的详细信息
    
    参数:
        - collection_id: 集合 ID
        
    响应:
        - 200: 成功
        - 404: 集合不存在
    """
    storage = current_app.config['STORAGE']
    doc = storage.get_collection(collection_id)
    
    if not doc:
        return jsonify({
            'success': False,
            'error': '集合不存在'
        }), 404
    
    # 计算模块数量
    modules = set()
    for interface in doc['interfaces']:
        if interface.get('tags'):
            for tag in interface['tags']:
                modules.add(tag)
    
    return jsonify({
        'success': True,
        'collection': {
            'collection_id': collection_id,
            'title': doc['title'],
            'description': doc['description'],
            'version': doc['version'],
            'base_url': doc['base_url'],
            'interface_count': len(doc['interfaces']),
            'module_count': len(modules)
        }
    }), 200

@api_bp.route('/collection/<collection_id>/interfaces', methods=['GET'])
def get_collection_interfaces(collection_id):
    """
    获取指定集合的所有接口概要
    
    参数:
        - collection_id: 集合 ID
        
    响应:
        - 200: 成功
        - 404: 集合不存在
    """
    storage = current_app.config['STORAGE']
    doc = storage.get_collection(collection_id)
    
    if not doc:
        return jsonify({
            'success': False,
            'error': '集合不存在'
        }), 404
    
    interfaces = []
    
    for interface in doc['interfaces']:
        interfaces.append({
            'interface_id': interface['id'],
            'method': interface['method'],
            'path': interface['path'],
            'summary': interface['summary'],
            'description': interface['description'],
            'tags': interface['tags'],
            'deprecated': interface.get('deprecated', False)
        })
    
    return jsonify({
        'success': True,
        'collection_id': collection_id,
        'title': doc['title'],
        'base_url': doc['base_url'],
        'interfaces': interfaces,
        'total': len(interfaces)
    }), 200

@api_bp.route('/interface/<collection_id>/<interface_id>', methods=['GET'])
def get_interface(collection_id, interface_id):
    """
    获取特定接口的完整详细信息
    
    参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    响应:
        - 200: 成功
        - 404: 集合或接口不存在
    """
    storage = current_app.config['STORAGE']
    doc = storage.get_collection(collection_id)
    
    if not doc:
        return jsonify({
            'success': False,
            'error': '集合不存在'
        }), 404
    
    interface = next((i for i in doc['interfaces'] if i['id'] == interface_id), None)
    
    if not interface:
        return jsonify({
            'success': False,
            'error': '接口不存在'
        }), 404
    
    return jsonify({
        'success': True,
        'interface': interface,
        'collection_info': {
            'id': collection_id,
            'title': doc['title'],
            'version': doc['version']
        }
    }), 200

@api_bp.route('/interface/<collection_id>/<interface_id>', methods=['PUT'])
def update_interface(collection_id, interface_id):
    """
    更新接口信息
    
    参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    请求体:
        - interface: 更新后的接口信息
        
    响应:
        - 200: 更新成功
        - 404: 集合或接口不存在
        - 400: 请求参数错误
    """
    try:
        storage = current_app.config['STORAGE']
        doc = storage.get_collection(collection_id)
        
        if not doc:
            return jsonify({
                'success': False,
                'error': '集合不存在'
            }), 404
        
        interface_index = next((i for i, iface in enumerate(doc['interfaces']) if iface['id'] == interface_id), None)
        
        if interface_index is None:
            return jsonify({
                'success': False,
                'error': '接口不存在'
            }), 404
        
        data = request.get_json()
        if not data or 'interface' not in data:
            return jsonify({
                'success': False,
                'error': '缺少interface参数'
            }), 400
        
        # 更新接口信息（保留ID）
        updated_interface = data['interface']
        updated_interface['id'] = interface_id
        doc['interfaces'][interface_index] = updated_interface
        
        # 保存更新后的集合
        storage.update_collection(collection_id, doc)
        
        current_app.logger.info(f"接口信息已更新: {interface_id}")
        
        return jsonify({
            'success': True,
            'message': '接口信息已更新',
            'interface': updated_interface
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"更新接口信息失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@api_bp.route('/collection/<collection_id>/delete-interface/<interface_id>', methods=['DELETE'])
def delete_interface(collection_id, interface_id):
    """
    删除集合中的接口
    
    参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    响应:
        - 200: 删除成功
        - 404: 集合或接口不存在
        - 500: 服务器错误
    """
    try:
        storage = current_app.config['STORAGE']
        doc = storage.get_collection(collection_id)
        
        if not doc:
            return jsonify({
                'success': False,
                'error': '集合不存在'
            }), 404
        
        # 查找接口索引
        interface_index = next((i for i, iface in enumerate(doc['interfaces']) if iface['id'] == interface_id), None)
        
        if interface_index is None:
            return jsonify({
                'success': False,
                'error': '接口不存在'
            }), 404
        
        # 删除接口
        deleted_interface = doc['interfaces'].pop(interface_index)
        
        # 保存更新后的集合
        storage.update_collection(collection_id, doc)
        
        current_app.logger.info(f"接口已删除: {interface_id}")
        
        return jsonify({
            'success': True,
            'message': '接口已删除',
            'deleted_interface': deleted_interface
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"删除接口失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@api_bp.route('/collection/<collection_id>/add-interface', methods=['POST'])
def add_interface(collection_id):
    """
    添加新接口到集合
    
    参数:
        - collection_id: 集合 ID
        
    请求体:
        - interface: 新接口信息
        
    响应:
        - 200: 添加成功
        - 404: 集合不存在
        - 400: 请求参数错误
    """
    try:
        storage = current_app.config['STORAGE']
        doc = storage.get_collection(collection_id)
        
        if not doc:
            return jsonify({
                'success': False,
                'error': '集合不存在'
            }), 404
        
        data = request.get_json()
        if not data or 'interface' not in data:
            return jsonify({
                'success': False,
                'error': '缺少interface参数'
            }), 400
        
        # 获取新接口信息
        new_interface = data['interface']
        
        # 确保接口有ID
        if 'id' not in new_interface or not new_interface['id']:
            new_interface['id'] = str(uuid.uuid4())
        
        # 添加到接口列表
        doc['interfaces'].append(new_interface)
        
        # 保存更新后的集合
        storage.update_collection(collection_id, doc)
        
        current_app.logger.info(f"新接口已添加: {new_interface['id']}")
        
        return jsonify({
            'success': True,
            'message': '接口已添加',
            'interface': new_interface
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"添加接口失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@api_bp.route('/search', methods=['GET'])
def search_interfaces():
    """
    搜索接口
    
    查询参数:
        - q: 搜索关键词（必需）
        - collection_id: 限定搜索的集合 ID（可选）
        
    响应:
        - 200: 成功
        - 400: 缺少搜索关键词
    """
    keyword = request.args.get('q', '').strip().lower()
    collection_id = request.args.get('collection_id', '').strip()
    
    if not keyword:
        return jsonify({
            'success': False,
            'error': '搜索关键词不能为空'
        }), 400
    
    storage = current_app.config['STORAGE']
    collections = storage.get_all_collections()
    results = []
    
    # 确定搜索范围
    if collection_id:
        if not storage.collection_exists(collection_id):
            return jsonify({
                'success': False,
                'error': '指定的集合不存在'
            }), 404
        search_collections = {collection_id: collections[collection_id]}
    else:
        search_collections = collections
    
    # 搜索接口
    for cid, doc in search_collections.items():
        for interface in doc['interfaces']:
            # 在 summary, description, path, operation_id 中搜索
            searchable_text = ' '.join([
                interface['summary'].lower(),
                interface['description'].lower(),
                interface['path'].lower(),
                interface.get('operation_id', '').lower(),
                ' '.join(interface.get('tags', [])).lower()
            ])
            
            if keyword in searchable_text:
                results.append({
                    'collection_id': cid,
                    'collection_title': doc['title'],
                    'interface_id': interface['id'],
                    'method': interface['method'],
                    'path': interface['path'],
                    'summary': interface['summary'],
                    'description': interface['description'],
                    'tags': interface['tags']
                })
    
    return jsonify({
        'success': True,
        'keyword': keyword,
        'results': results,
        'total': len(results)
    }), 200

@api_bp.route('/collection/<collection_id>', methods=['DELETE'])
def delete_collection(collection_id):
    """
    删除指定的文档集合
    
    参数:
        - collection_id: 集合 ID
        
    响应:
        - 200: 删除成功
        - 404: 集合不存在
    """
    storage = current_app.config['STORAGE']
    
    if not storage.collection_exists(collection_id):
        return jsonify({
            'success': False,
            'error': '集合不存在'
        }), 404
    
    if storage.delete_collection(collection_id):
        return jsonify({
            'success': True,
            'message': '集合已删除'
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': '删除集合失败'
        }), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查端点
    
    响应:
        - 200: 服务正常
    """
    storage = current_app.config['STORAGE']
    collections = storage.get_all_collections()
    return jsonify({
        'status': 'healthy',
        'service': 'API Document Parser',
        'version': '1.0.0',
        'collections_count': len(collections)
    }), 200

@api_bp.route('/generate-yaml/<collection_id>/<interface_id>', methods=['POST'])
def generate_yaml_testcases(collection_id, interface_id):
    """
    生成YAML格式的测试用例
    
    参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    响应:
        - 200: 成功生成YAML
        - 404: 集合或接口不存在
        - 500: 生成失败
    """
    try:
        storage = current_app.config['STORAGE']
        
        # 检查集合是否存在
        doc = storage.get_collection(collection_id)
        if not doc:
            return jsonify({
                'success': False,
                'error': '集合不存在'
            }), 404
        
        interface = next((i for i in doc['interfaces'] if i['id'] == interface_id), None)
        
        # 检查接口是否存在
        if not interface:
            return jsonify({
                'success': False,
                'error': '接口不存在'
            }), 404
        
        # 准备接口详情
        interface_details = {
            'interface': interface,
            'collection_info': {
                'id': collection_id,
                'title': doc['title'],
                'base_url': doc['base_url'],
                'version': doc['version']
            }
        }
        
        # 调用Dify生成JSON测试用例
        dify_client = current_app.config.get('DIFY_CLIENT')
        if not dify_client:
            return jsonify({
                'success': False,
                'error': 'Dify客户端未配置'
            }), 500
        
        result = dify_client.generate_json_testcases(interface_details)
        
        if result['success']:
            # 保存测试用例到存储
            workflow_id = result.get('workflow_id')
            json_content = result['json_content']
            save_success = storage.save_testcase(collection_id, interface_id, json_content=json_content, workflow_id=workflow_id)
            
            if not save_success:
                current_app.logger.warning(f"测试用例生成成功但保存失败: {collection_id}_{interface_id}")
                
            return jsonify({
                'success': True,
                'json_content': json_content,
                'original_content': result.get('original_content', ''),  # 原始AI响应内容
                'workflow_id': workflow_id,
                'saved': save_success
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"生成YAML测试用例失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@api_bp.route('/generate-json/<collection_id>/<interface_id>', methods=['POST'])
def generate_json_testcases(collection_id, interface_id):
    """
    生成JSON格式的测试用例
    
    参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    响应:
        - 200: 成功生成JSON
        - 404: 集合或接口不存在
        - 500: 生成失败
    """
    try:
        storage = current_app.config['STORAGE']
        
        # 检查集合是否存在
        doc = storage.get_collection(collection_id)
        if not doc:
            return jsonify({
                'success': False,
                'error': '集合不存在'
            }), 404
        
        interface = next((i for i in doc['interfaces'] if i['id'] == interface_id), None)
        
        # 检查接口是否存在
        if not interface:
            return jsonify({
                'success': False,
                'error': '接口不存在'
            }), 404
        
        # 准备接口详情
        interface_details = {
            'interface': interface,
            'collection_info': {
                'id': collection_id,
                'title': doc['title'],
                'base_url': doc['base_url'],
                'version': doc['version']
            }
        }
        
        # 调用Dify生成JSON
        dify_client = current_app.config.get('DIFY_CLIENT')
        if not dify_client:
            return jsonify({
                'success': False,
                'error': 'Dify客户端未配置'
            }), 500
        
        result = dify_client.generate_json_testcases(interface_details)
        
        if result['success']:
            # 保存测试用例到存储
            workflow_id = result.get('workflow_id')
            json_content = result['json_content']
            save_success = storage.save_testcase(collection_id, interface_id, json_content=json_content, workflow_id=workflow_id)
            
            if not save_success:
                current_app.logger.warning(f"测试用例生成成功但保存失败: {collection_id}_{interface_id}")
                
            return jsonify({
                'success': True,
                'json_content': json_content,
                'original_content': result.get('original_content', ''),  # 原始AI响应内容
                'workflow_id': workflow_id,
                'saved': save_success
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"生成JSON测试用例失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@api_bp.route('/generate-python', methods=['POST'])
def generate_python_script():
    """
    生成Python测试脚本
    
    请求体:
        - test_cases: JSON格式测试用例数据
        - yaml_content: YAML测试用例内容（兼容旧版本）
        
    响应:
        - 200: 成功生成Python脚本
        - 400: 请求参数错误
        - 500: 生成失败
    """
    try:
        data = request.get_json()
        
        # 优先使用JSON格式的测试用例数据
        test_cases = data.get('test_cases')
        yaml_content = data.get('yaml_content')
        
        if not test_cases and not yaml_content:
            return jsonify({
                'success': False,
                'error': '缺少test_cases或yaml_content参数'
            }), 400
        
        # 如果有JSON格式的测试用例，转换为YAML格式
        if test_cases:
            yaml_content = convert_testcases_to_yaml(test_cases)
        
        # 调用Dify生成Python脚本
        dify_client = current_app.config.get('DIFY_CLIENT')
        if not dify_client:
            return jsonify({
                'success': False,
                'error': 'Dify客户端未配置'
            }), 500
        
        result = dify_client.generate_python_script(yaml_content)
        
        if result['success']:
            # 验证Python语法
            validation = dify_client.validate_python_syntax(result['python_code'])
            
            return jsonify({
                'success': True,
                'python_code': result['python_code'],
                'workflow_id': result.get('workflow_id'),
                'syntax_valid': validation['valid'],
                'syntax_error': validation.get('error')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"生成Python脚本失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500


@api_bp.route('/download-yaml', methods=['POST'])
def download_yaml():
    """
    下载YAML文件
    
    请求体:
        - yaml_content: YAML内容
        - filename: 文件名（可选）
        
    响应:
        - 200: 返回YAML文件
        - 400: 请求参数错误
    """
    try:
        data = request.get_json()
        
        if not data or 'yaml_content' not in data:
            return jsonify({
                'success': False,
                'error': '缺少yaml_content参数'
            }), 400
        
        yaml_content = data['yaml_content']
        filename = data.get('filename', 'test_cases.yaml')
        
        # 确保文件名以.yaml结尾
        if not filename.endswith('.yaml') and not filename.endswith('.yml'):
            filename += '.yaml'
        
        # 创建内存文件对象
        yaml_bytes = yaml_content.encode('utf-8')
        yaml_io = io.BytesIO(yaml_bytes)
        
        return send_file(
            yaml_io,
            mimetype='application/x-yaml',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        current_app.logger.error(f"下载YAML文件失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'下载失败: {str(e)}'
        }), 500


@api_bp.route('/download-python', methods=['POST'])
def download_python():
    """
    下载Python文件
    
    请求体:
        - python_code: Python代码
        - filename: 文件名（可选）
        
    响应:
        - 200: 返回Python文件
        - 400: 请求参数错误
    """
    try:
        data = request.get_json()
        
        if not data or 'python_code' not in data:
            return jsonify({
                'success': False,
                'error': '缺少python_code参数'
            }), 400
        
        python_code = data['python_code']
        filename = data.get('filename', 'test_api.py')
        
        # 确保文件名以.py结尾
        if not filename.endswith('.py'):
            filename += '.py'
        
        # 创建内存文件对象
        python_bytes = python_code.encode('utf-8')
        python_io = io.BytesIO(python_bytes)
        
        return send_file(
            python_io,
            mimetype='text/x-python',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        current_app.logger.error(f"下载Python文件失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'下载失败: {str(e)}'
        }), 500

@api_bp.route('/testcase-status', methods=['GET'])
def get_testcase_status():
    """
    获取测试用例状态
    
    查询参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    响应:
        - 200: 成功
        - 400: 缺少参数
        - 500: 服务器错误
    """
    try:
        collection_id = request.args.get('collection_id')
        interface_id = request.args.get('interface_id')
        
        if not collection_id or not interface_id:
            return jsonify({
                'success': False,
                'error': '缺少collection_id或interface_id参数'
            }), 400
        
        storage = current_app.config['STORAGE']
        
        # 检查测试用例是否存在
        has_testcase = storage.has_testcase(collection_id, interface_id)
        
        # 检查Python脚本是否存在
        has_python_script = storage.has_python_script(collection_id, interface_id)
        python_script_info = None
        
        if has_python_script:
            python_script_info = storage.get_python_script(collection_id, interface_id)
            # 不返回完整的Python代码，只返回元数据
            if python_script_info and 'python_code' in python_script_info:
                python_script_info = {
                    'python_script_path': python_script_info.get('python_script_path'),
                    'python_workflow_id': python_script_info.get('python_workflow_id'),
                    'python_generated_at': python_script_info.get('python_generated_at'),
                    'code_length': len(python_script_info.get('python_code', '')),
                    'has_code': True
                }
        
        testcase_data = None
        if has_testcase:
            testcase_data = storage.get_testcase(collection_id, interface_id)
            # 移除YAML内容以减小响应大小，前端可以通过其他接口获取完整内容
            if testcase_data:
                testcase_data = {
                    'collection_id': testcase_data.get('collection_id'),
                    'interface_id': testcase_data.get('interface_id'),
                    'workflow_id': testcase_data.get('workflow_id'),
                    'created_at': testcase_data.get('created_at'),
                    'updated_at': testcase_data.get('updated_at')
                }
        
        return jsonify({
            'success': True,
            'has_testcase': has_testcase,
            'has_python_script': has_python_script,
            'python_script_info': python_script_info,
            'testcase': testcase_data,
            'message': '查询成功'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"查询测试用例状态失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'查询测试用例状态失败: {str(e)}'
        }), 500


@api_bp.route('/batch-testcase-status', methods=['POST'])
def batch_get_testcase_status():
    """
    批量获取测试用例状态（优化：一次请求获取多个接口的状态）
    
    请求体:
        - collection_id: 集合 ID
        - interface_ids: 接口 ID 列表
        
    响应:
        - 200: 成功
        - 400: 缺少参数
        - 500: 服务器错误
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求体数据'
            }), 400
        
        collection_id = data.get('collection_id')
        interface_ids = data.get('interface_ids', [])
        
        if not collection_id:
            return jsonify({
                'success': False,
                'error': '缺少collection_id参数'
            }), 400
        
        if not interface_ids or not isinstance(interface_ids, list):
            return jsonify({
                'success': False,
                'error': 'interface_ids必须是非空数组'
            }), 400
        
        storage = current_app.config['STORAGE']
        
        # 批量检查所有接口的测试用例状态
        status_map = {}
        
        for interface_id in interface_ids:
            has_testcase = storage.has_testcase(collection_id, interface_id)
            status_map[interface_id] = has_testcase
        
        current_app.logger.info(f"批量检查测试用例状态: collection_id={collection_id}, 接口数量={len(interface_ids)}, 已有测试用例数量={sum(status_map.values())}")
        
        return jsonify({
            'success': True,
            'collection_id': collection_id,
            'status_map': status_map,
            'total_count': len(interface_ids),
            'has_testcase_count': sum(status_map.values()),
            'message': '批量查询成功'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"批量查询测试用例状态失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'批量查询测试用例状态失败: {str(e)}'
        }), 500


@api_bp.route('/get-python-script', methods=['GET'])
def get_python_script():
    """
    获取已保存的Python脚本
    
    查询参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    响应:
        - 200: 成功返回Python脚本
        - 400: 缺少参数
        - 404: Python脚本不存在
        - 500: 服务器错误
    """
    try:
        collection_id = request.args.get('collection_id')
        interface_id = request.args.get('interface_id')
        
        if not collection_id or not interface_id:
            return jsonify({
                'success': False,
                'error': '缺少collection_id或interface_id参数'
            }), 400
        
        storage = current_app.config['STORAGE']
        
        # 获取Python脚本
        script_info = storage.get_python_script(collection_id, interface_id)
        
        if not script_info or 'python_code' not in script_info:
            return jsonify({
                'success': False,
                'error': 'Python脚本不存在'
            }), 404
        
        # 验证Python语法
        dify_client = current_app.config.get('DIFY_CLIENT')
        validation = dify_client.validate_python_syntax(script_info['python_code']) if dify_client else {'valid': False, 'error': 'Dify客户端未配置'}
        
        return jsonify({
            'success': True,
            'python_code': script_info['python_code'],
            'python_script_path': script_info.get('python_script_path'),
            'python_workflow_id': script_info.get('python_workflow_id'),
            'python_generated_at': script_info.get('python_generated_at'),
            'syntax_valid': validation['valid'],
            'syntax_error': validation.get('error'),
            'message': '获取Python脚本成功'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取Python脚本失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@api_bp.route('/testcase', methods=['GET'])
def get_testcase():
    """
    获取测试用例完整数据
    
    查询参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    响应:
        - 200: 成功
        - 400: 缺少参数
        - 404: 测试用例不存在
        - 500: 服务器错误
    """
    try:
        collection_id = request.args.get('collection_id')
        interface_id = request.args.get('interface_id')
        
        if not collection_id or not interface_id:
            return jsonify({
                'success': False,
                'error': '缺少collection_id或interface_id参数'
            }), 400
        
        storage = current_app.config['STORAGE']
        testcase_data = storage.get_testcase(collection_id, interface_id)
        
        if not testcase_data:
            return jsonify({
                'success': False,
                'error': '测试用例不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'testcase': testcase_data,
            'message': '获取测试用例成功'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取测试用例失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'获取测试用例失败: {str(e)}'
        }), 500


@api_bp.route('/delete-testcase/<collection_id>/<interface_id>', methods=['DELETE'])
def delete_testcase(collection_id, interface_id):
    """
    删除指定接口的测试用例
    
    参数:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        
    响应:
        - 200: 删除成功
        - 404: 测试用例不存在
        - 500: 服务器错误
    """
    try:
        storage = current_app.config['STORAGE']
        
        # 检查测试用例是否存在
        if not storage.has_testcase(collection_id, interface_id):
            return jsonify({
                'success': False,
                'error': '测试用例不存在'
            }), 404
        
        # 删除测试用例
        success = storage.delete_testcase(collection_id, interface_id)
        
        if success:
            current_app.logger.info(f"测试用例已删除: collection_id={collection_id}, interface_id={interface_id}")
            return jsonify({
                'success': True,
                'message': '测试用例已成功删除'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': '删除测试用例失败'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"删除测试用例失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'删除测试用例失败: {str(e)}'
        }), 500

@api_bp.route('/save-testcases', methods=['POST'])
def save_testcases():
    """
    保存测试用例数据
    
    请求体:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        - testcases: 测试用例数据数组
        
    响应:
        - 200: 成功
        - 400: 缺少参数
        - 500: 服务器错误
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求体数据'
            }), 400
        
        collection_id = data.get('collection_id')
        interface_id = data.get('interface_id')
        testcases = data.get('testcases')
        
        if not collection_id or not interface_id:
            return jsonify({
                'success': False,
                'error': '缺少collection_id或interface_id参数'
            }), 400
        
        if testcases is None:
            return jsonify({
                'success': False,
                'error': '缺少testcases参数'
            }), 400
        
        storage = current_app.config['STORAGE']
        
        # 将测试用例数据转换为JSON格式保存
        import json
        
        if len(testcases) > 0:
            # 准备JSON格式数据
            json_data = {
                "test_cases": testcases,
                "metadata": {
                    "collection_id": collection_id,
                    "interface_id": interface_id,
                    "created_at": datetime.now().isoformat(),
                    "testcase_count": len(testcases)
                }
            }
            
            json_content = json.dumps(json_data, ensure_ascii=False, indent=2)
        else:
            json_content = ''
        
        # 保存到存储
        save_success = storage.save_testcase(collection_id, interface_id, json_content=json_content)
        
        if save_success:
            return jsonify({
                'success': True,
                'message': '测试用例已成功保存',
                'testcase_count': len(testcases)
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': '保存测试用例失败'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"保存测试用例失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'保存测试用例失败: {str(e)}'
        }), 500


@web_bp.route('/')
def index():
    """
    Web 界面首页
    """
    return render_template('index_enhanced.html')

@web_bp.route('/review-testcases')
def review_testcases():
    """
    测试用例审核页面
    """
    return render_template('review_testcases.html')

@web_bp.route('/add-interface')
def add_interface_page():
    """
    新增接口页面
    """
    return render_template('add_interface.html')


def convert_testcases_to_yaml(test_cases):
    """
    将JSON格式的测试用例转换为YAML格式
    
    Args:
        test_cases: JSON格式的测试用例数据，可以是列表或包含test_cases字段的对象
        
    Returns:
        YAML格式的测试用例字符串
    """
    if not test_cases:
        return ""
    
    # 处理不同的数据格式
    # 如果test_cases是字典且包含test_cases字段，则提取测试用例列表
    if isinstance(test_cases, dict) and 'test_cases' in test_cases:
        test_cases_list = test_cases['test_cases']
    elif isinstance(test_cases, list):
        test_cases_list = test_cases
    else:
        # 如果格式不正确，返回空字符串
        return ""
    
    if not test_cases_list:
        return ""
    
    # 导入yaml模块
    import yaml
    
    # 构建YAML数据结构
    yaml_data = {
        'test_cases': test_cases_list,
        'metadata': {
            'testcase_count': len(test_cases_list),
            'generated_at': datetime.now().isoformat()
        }
    }
    
    # 转换为YAML格式
    yaml_content = yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False, indent=2)
    
    return yaml_content


@api_bp.route('/execute-testcases', methods=['POST'])
def execute_testcases():
    """
    执行测试用例（提交到SVN并触发Jenkins构建）
    
    请求体:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        - yaml_content: YAML测试用例内容
        - testcases: 测试用例数据
        - is_debug: 是否为调试模式（可选，默认false）
        
    响应:
        - 200: 成功
        - 400: 缺少参数
        - 500: 服务器错误
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求体数据'
            }), 400
        
        collection_id = data.get('collection_id')
        interface_id = data.get('interface_id')
        yaml_content = data.get('yaml_content')
        testcases = data.get('testcases', [])
        is_debug = data.get('is_debug', False)  # 新增：是否为调试模式
        
        if not collection_id or not interface_id:
            return jsonify({
                'success': False,
                'error': '缺少collection_id或interface_id参数'
            }), 400
        
        if not yaml_content:
            return jsonify({
                'success': False,
                'error': '缺少yaml_content参数'
            }), 400
        
        # 生成执行时间
        execution_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查SVN配置
        svn_repo_url = os.getenv('SVN_REPO_URL')
        svn_username = os.getenv('SVN_USERNAME')
        svn_password = os.getenv('SVN_PASSWORD')
        svn_target_path = os.getenv('SVN_TARGET_PATH')
        svn_debug_path = os.getenv('SVN_DEBUG_PATH')
        
        # 检查Jenkins配置
        jenkins_url = os.getenv('JENKINS_URL')
        jenkins_job_name = os.getenv('JENKINS_DEBUG_JOB_NAME' if is_debug else 'JENKINS_JOB_NAME')
        
        # 如果SVN配置完整，则提交到SVN
        if all([svn_repo_url, svn_username, svn_password, svn_target_path]):
            try:
                # 检查SVN命令行工具是否可用
                import subprocess
                svn_cmd_available = False
                try:
                    result = subprocess.run(['svn', '--version'], 
                                          capture_output=True, 
                                          timeout=2)
                    svn_cmd_available = (result.returncode == 0)
                except:
                    pass
                
                # 如果SVN命令行工具可用，优先使用命令行客户端
                if svn_cmd_available:
                    try:
                        from app.svn_client import SVNClient
                        svn_client = SVNClient(svn_repo_url, svn_username, svn_password, svn_target_path, svn_debug_path)
                        current_app.logger.info("使用命令行SVN客户端")
                    except ImportError:
                        from app.svn_client_http import SVNClientHTTP
                        svn_client = SVNClientHTTP(svn_repo_url, svn_username, svn_password, svn_target_path)
                        current_app.logger.info("使用HTTP SVN客户端（命令行客户端不可用）")
                else:
                    # SVN命令行工具不可用，使用HTTP客户端
                    from app.svn_client_http import SVNClientHTTP
                    svn_client = SVNClientHTTP(svn_repo_url, svn_username, svn_password, svn_target_path)
                    current_app.logger.info("使用HTTP SVN客户端（SVN命令行工具不可用）")
                
                # 提交YAML文件到SVN（根据is_debug选择目标路径）
                current_app.logger.info(f"准备提交SVN: is_debug={is_debug}, target_path={svn_target_path}, debug_path={svn_debug_path}")
                svn_result = svn_client.commit_yaml_file(yaml_content, collection_id, interface_id, is_debug)
                
                if svn_result['success']:
                    commit_info = svn_result.get('commit_info', {})
                    actual_path = commit_info.get('target_path', 'unknown')
                    current_app.logger.info(f"SVN提交成功: collection_id={collection_id}, interface_id={interface_id}, revision={svn_result['revision']}, is_debug={is_debug}, actual_path={actual_path}")
                    
                    # 如果Jenkins配置完整，触发Jenkins构建
                    build_number = None
                    jenkins_triggered = False
                    
                    if jenkins_url and jenkins_job_name:
                        try:
                            from app.jenkins_client import JenkinsClient
                            jenkins_username = os.getenv('JENKINS_USERNAME')
                            jenkins_password = os.getenv('JENKINS_PASSWORD')
                            
                            jenkins_client = JenkinsClient(jenkins_url, jenkins_username, jenkins_password)
                            
                            # 准备Jenkins构建参数
                            build_params = {
                                'COLLECTION_ID': collection_id,
                                'INTERFACE_ID': interface_id,
                                'TEST_FILE': f'test_cases_{collection_id}_{interface_id}.yaml'
                            }
                            
                            # 触发Jenkins构建（带参数）
                            jenkins_result = jenkins_client.trigger_build(jenkins_job_name, parameters=build_params, is_debug=is_debug)
                            
                            if jenkins_result['success']:
                                build_number = jenkins_result.get('build_number')
                                jenkins_triggered = True
                                current_app.logger.info(f"Jenkins构建已触发: job={jenkins_job_name}, build_number={build_number}")
                            else:
                                current_app.logger.warning(f"Jenkins构建触发失败: {jenkins_result.get('error')}")
                        except ImportError:
                            current_app.logger.warning("Jenkins客户端模块未找到")
                        except Exception as e:
                            current_app.logger.error(f"触发Jenkins构建异常: {traceback.format_exc()}")
                    
                    # 构建响应
                    response_data = {
                        'success': True,
                        'message': '测试用例已提交到SVN' + ('并触发Jenkins构建' if jenkins_triggered else ''),
                        'execution_time': execution_time,
                        'svn_revision': svn_result['revision'],
                        'testcase_count': len(testcases),
                        'filename': svn_result.get('filename', ''),
                        'is_debug': is_debug,
                        'commit_info': svn_result.get('commit_info'),
                        'jenkins_triggered': jenkins_triggered
                    }
                    
                    # 如果有构建号，添加到响应中
                    if build_number:
                        response_data['build_number'] = build_number
                        response_data['collection_id'] = collection_id
                        response_data['interface_id'] = interface_id
                        
                        # 生成报告URL（包含接口标识）
                        report_base_url = os.getenv('TEST_REPORT_DEBUG_URL' if is_debug else 'TEST_REPORT_URL', '')
                        if report_base_url:
                            # 方案1: 使用构建号 + 参数
                            report_url = f"{report_base_url}{build_number}/allure/"
                            response_data['report_url'] = report_url
                            
                            # 如果需要按接口隔离报告，可以使用：
                            # report_url = f"{report_base_url}{build_number}/allure/{collection_id}_{interface_id}/"
                    
                    return jsonify(response_data), 200
                else:
                    current_app.logger.error(f"SVN提交失败: {svn_result.get('error')}")
                    return jsonify({
                        'success': False,
                        'error': f"SVN提交失败: {svn_result.get('error')}"
                    }), 500
                    
            except ImportError:
                current_app.logger.warning("SVN客户端模块未找到")
                return jsonify({
                    'success': False,
                    'error': 'SVN客户端模块未安装'
                }), 500
            except Exception as e:
                current_app.logger.error(f"SVN提交异常: {traceback.format_exc()}")
                return jsonify({
                    'success': False,
                    'error': f'SVN提交异常: {str(e)}'
                }), 500
        else:
            # SVN未配置，返回提示信息
            current_app.logger.warning("SVN配置不完整，跳过SVN提交")
            
            return jsonify({
                'success': True,
                'message': '测试用例执行成功（SVN未配置）',
                'execution_time': execution_time,
                'svn_revision': '未配置SVN',
                'testcase_count': len(testcases),
                'warning': 'SVN配置不完整，请在.env文件中配置SVN相关参数'
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"执行测试用例失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'执行测试用例失败: {str(e)}'
        }), 500


@api_bp.route('/get-report-url', methods=['GET'])
def get_report_url():
    """
    获取测试报告URL
    
    查询参数:
        - build_number: Jenkins构建号（必需）
        - is_debug: 是否为调试模式（可选，默认false）
        
    响应:
        - 200: 成功
        - 400: 配置未设置或缺少参数
    """
    try:
        build_number = request.args.get('build_number', '')
        is_debug = request.args.get('is_debug', 'false').lower() == 'true'
        
        if not build_number:
            return jsonify({
                'success': False,
                'error': '缺少build_number参数'
            }), 400
        
        # 从环境变量读取配置
        report_base_url = os.getenv('TEST_REPORT_DEBUG_URL' if is_debug else 'TEST_REPORT_URL', '')
        
        if not report_base_url:
            return jsonify({
                'success': False,
                'error': '测试报告URL未配置',
                'message': '请在.env文件中配置TEST_REPORT_URL或TEST_REPORT_DEBUG_URL'
            }), 400
        
        # 构建完整的报告URL
        report_url = f"{report_base_url}{build_number}/allure/"
        
        return jsonify({
            'success': True,
            'report_url': report_url,
            'base_url': report_base_url,
            'build_number': build_number,
            'is_debug': is_debug
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取报告URL失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'获取报告URL失败: {str(e)}'
        }), 500


@api_bp.route('/get-build-status', methods=['GET'])
def get_build_status():
    """
    获取Jenkins构建状态
    
    查询参数:
        - job_name: Jenkins Job名称（必需）
        - build_number: 构建号（必需）
        
    响应:
        - 200: 成功
        - 400: 缺少参数或Jenkins未配置
        - 500: 服务器错误
    """
    try:
        job_name = request.args.get('job_name', '')
        build_number = request.args.get('build_number', '')
        
        if not job_name or not build_number:
            return jsonify({
                'success': False,
                'error': '缺少job_name或build_number参数'
            }), 400
        
        # 检查Jenkins配置
        jenkins_url = os.getenv('JENKINS_URL')
        
        if not jenkins_url:
            return jsonify({
                'success': False,
                'error': 'Jenkins未配置',
                'message': '请在.env文件中配置JENKINS_URL'
            }), 400
        
        try:
            from app.jenkins_client import JenkinsClient
            jenkins_username = os.getenv('JENKINS_USERNAME')
            jenkins_password = os.getenv('JENKINS_PASSWORD')
            
            jenkins_client = JenkinsClient(jenkins_url, jenkins_username, jenkins_password)
            
            # 获取构建信息
            build_info = jenkins_client.get_build_info(job_name, int(build_number))
            
            if build_info['success']:
                return jsonify({
                    'success': True,
                    'build_info': build_info
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': build_info.get('error')
                }), 500
                
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Jenkins客户端模块未安装'
            }), 500
        except Exception as e:
            current_app.logger.error(f"获取构建状态异常: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'获取构建状态异常: {str(e)}'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"获取构建状态失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'获取构建状态失败: {str(e)}'
        }), 500


@api_bp.route('/execute-all-testcases/<collection_id>', methods=['POST'])
def execute_all_testcases(collection_id):
    """
    执行集合下的所有正式测试用例
    
    参数:
        - collection_id: 集合 ID
        
    响应:
        - 200: 成功
        - 500: 服务器错误
    """
    try:
        # 检查Jenkins配置
        jenkins_url = os.getenv('JENKINS_URL')
        jenkins_job_name = os.getenv('JENKINS_JOB_NAME')  # AI-jk (正式Job)
        
        if not jenkins_url or not jenkins_job_name:
            return jsonify({
                'success': False,
                'error': 'Jenkins未配置'
            }), 500
        
        try:
            from app.jenkins_client import JenkinsClient
            jenkins_username = os.getenv('JENKINS_USERNAME')
            jenkins_password = os.getenv('JENKINS_PASSWORD')
            
            jenkins_client = JenkinsClient(jenkins_url, jenkins_username, jenkins_password)
            
            # 触发构建（不传参数，执行所有正式用例）
            # 或者传递collection_id作为参数
            build_params = {
                'COLLECTION_ID': collection_id,
                'EXECUTE_ALL': 'true'
            }
            
            jenkins_result = jenkins_client.trigger_build(jenkins_job_name, parameters=build_params, is_debug=False)
            
            if jenkins_result['success']:
                build_number = jenkins_result.get('build_number')
                
                # 生成报告URL
                report_base_url = os.getenv('TEST_REPORT_URL', '')
                report_url = f"{report_base_url}{build_number}/allure/" if build_number and report_base_url else None
                
                return jsonify({
                    'success': True,
                    'message': '已触发所有正式用例执行',
                    'build_number': build_number,
                    'job_name': jenkins_job_name,
                    'report_url': report_url,
                    'collection_id': collection_id
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': jenkins_result.get('error')
                }), 500
                
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Jenkins客户端模块未安装'
            }), 500
        except Exception as e:
            current_app.logger.error(f"触发Jenkins构建异常: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'触发构建异常: {str(e)}'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"执行所有用例失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'执行失败: {str(e)}'
        }), 500


@api_bp.route('/archive-testcase', methods=['POST'])
def archive_testcase():
    """
    归档测试用例（将测试用例提交到正式SVN目录）
    
    请求体:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        - yaml_content: YAML测试用例内容（可选，如果不提供则从存储中获取）
        - testcases: 测试用例数据（可选）
        
    响应:
        - 200: 成功
        - 400: 缺少参数
        - 404: 测试用例不存在
        - 500: 服务器错误
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求体数据'
            }), 400
        
        collection_id = data.get('collection_id')
        interface_id = data.get('interface_id')
        yaml_content = data.get('yaml_content')  # 前端可以直接传递YAML内容
        testcases = data.get('testcases', [])
        
        if not collection_id or not interface_id:
            return jsonify({
                'success': False,
                'error': '缺少collection_id或interface_id参数'
            }), 400
        
        # 如果前端没有传递yaml_content，则从存储中获取并转换
        if not yaml_content:
            # 获取存储实例
            storage = current_app.config['STORAGE']
            
            # 获取测试用例数据
            testcase_data = storage.get_testcase(collection_id, interface_id)
            
            if not testcase_data:
                return jsonify({
                    'success': False,
                    'error': '测试用例不存在，请先生成测试用例'
                }), 404
            
            # 将JSON测试用例转换为YAML格式
            import yaml
            import json
            
            # 解析JSON测试用例数据
            if isinstance(testcase_data, dict) and 'json_content' in testcase_data:
                json_content = testcase_data['json_content']
                if isinstance(json_content, str):
                    try:
                        testcase_json = json.loads(json_content)
                    except json.JSONDecodeError:
                        return jsonify({
                            'success': False,
                            'error': '测试用例JSON数据格式不正确'
                        }), 400
                else:
                    testcase_json = json_content
            elif isinstance(testcase_data, str):
                try:
                    testcase_json = json.loads(testcase_data)
                except json.JSONDecodeError:
                    testcase_json = testcase_data
            else:
                testcase_json = testcase_data
            
            # 提取测试用例列表
            if isinstance(testcase_json, dict) and 'test_cases' in testcase_json:
                test_cases = testcase_json['test_cases']
            elif isinstance(testcase_json, list):
                test_cases = testcase_json
            else:
                return jsonify({
                    'success': False,
                    'error': '测试用例数据格式不正确'
                }), 400
            
            # 转换为YAML格式
            yaml_content = yaml.dump({
                'test_cases': test_cases,
                'metadata': {
                    'collection_id': collection_id,
                    'interface_id': interface_id,
                    'archived_at': datetime.now().isoformat(),
                    'testcase_count': len(test_cases)
                }
            }, allow_unicode=True, default_flow_style=False)
        
        # 获取SVN配置
        svn_repo_url = os.getenv('SVN_REPO_URL')
        svn_username = os.getenv('SVN_USERNAME')
        svn_password = os.getenv('SVN_PASSWORD')
        svn_target_path = os.getenv('SVN_TARGET_PATH')  # 正式目录
        svn_debug_path = os.getenv('SVN_DEBUG_PATH')  # 调试目录（用于初始化SVNClient）
        
        if not all([svn_repo_url, svn_username, svn_password, svn_target_path]):
            return jsonify({
                'success': False,
                'error': 'SVN配置不完整，请检查.env文件'
            }), 500
        
        # 使用SVN客户端提交到正式目录（参考execute-testcases的实现）
        try:
            # 检查SVN命令行工具是否可用
            import subprocess
            svn_cmd_available = False
            try:
                result = subprocess.run(['svn', '--version'], 
                                      capture_output=True, 
                                      timeout=2)
                svn_cmd_available = (result.returncode == 0)
            except:
                pass
            
            # 如果SVN命令行工具可用，优先使用命令行客户端
            if svn_cmd_available:
                try:
                    from app.svn_client import SVNClient
                    svn_client = SVNClient(svn_repo_url, svn_username, svn_password, svn_target_path, svn_debug_path)
                    current_app.logger.info("使用命令行SVN客户端进行归档")
                except ImportError:
                    from app.svn_client_http import SVNClientHTTP
                    svn_client = SVNClientHTTP(svn_repo_url, svn_username, svn_password, svn_target_path)
                    current_app.logger.info("使用HTTP SVN客户端进行归档（命令行客户端不可用）")
            else:
                # SVN命令行工具不可用，使用HTTP客户端
                from app.svn_client_http import SVNClientHTTP
                svn_client = SVNClientHTTP(svn_repo_url, svn_username, svn_password, svn_target_path)
                current_app.logger.info("使用HTTP SVN客户端进行归档（SVN命令行工具不可用）")
            
            # 提交到正式SVN（is_debug=False）
            current_app.logger.info(f"准备归档用例到正式SVN: collection_id={collection_id}, interface_id={interface_id}, target_path={svn_target_path}")
            svn_result = svn_client.commit_yaml_file(yaml_content, collection_id, interface_id, is_debug=False)
            
            if svn_result['success']:
                commit_info = svn_result.get('commit_info', {})
                actual_path = commit_info.get('target_path', 'unknown')
                current_app.logger.info(f"用例归档成功: collection_id={collection_id}, interface_id={interface_id}, revision={svn_result['revision']}, actual_path={actual_path}")
                
                return jsonify({
                    'success': True,
                    'message': '用例已成功归档到正式环境',
                    'filename': svn_result.get('filename', ''),
                    'revision': svn_result['revision'],
                    'commit_info': svn_result.get('commit_info'),
                    'testcase_count': len(testcases) if testcases else 0
                }), 200
            else:
                current_app.logger.error(f"SVN提交失败: {svn_result.get('error')}")
                return jsonify({
                    'success': False,
                    'error': f"SVN提交失败: {svn_result.get('error')}"
                }), 500
                
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'SVN客户端模块未安装'
            }), 500
        except Exception as e:
            current_app.logger.error(f"SVN提交异常: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'SVN提交异常: {str(e)}'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"归档用例失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'归档失败: {str(e)}'
        }), 500


@api_bp.route('/generate-python-yaml', methods=['POST'])
def generate_python_yaml():
    """
    基于YAML测试用例生成Python测试脚本（使用文件上传方式）
    
    请求体:
        - collection_id: 集合 ID
        - interface_id: 接口 ID
        - user_id: 用户ID（可选）
        
    响应:
        - 200: 成功
        - 400: 缺少参数
        - 404: 测试用例不存在
        - 500: 服务器错误
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求体数据'
            }), 400
        
        collection_id = data.get('collection_id')
        interface_id = data.get('interface_id')
        user_id = data.get('user_id', 'default')
        
        if not collection_id or not interface_id:
            return jsonify({
                'success': False,
                'error': '缺少collection_id或interface_id参数'
            }), 400
        
        # 获取存储实例
        storage = current_app.config['STORAGE']
        
        # 获取测试用例数据
        testcase_data = storage.get_testcase(collection_id, interface_id)
        
        if not testcase_data:
            return jsonify({
                'success': False,
                'error': '测试用例不存在'
            }), 404
        
        # 获取Dify客户端实例
        dify_client = current_app.config['DIFY_CLIENT']
        
        # 将测试用例数据转换为YAML格式
        import yaml
        
        # 解析JSON测试用例数据
        # 首先检查testcase_data是否包含json_content字段
        if isinstance(testcase_data, dict) and 'json_content' in testcase_data:
            # 从json_content字段中提取JSON字符串
            json_content = testcase_data['json_content']
            if isinstance(json_content, str):
                import json
                try:
                    testcase_json = json.loads(json_content)
                except json.JSONDecodeError:
                    return jsonify({
                        'success': False,
                        'error': '测试用例JSON数据格式不正确'
                    }), 400
            else:
                testcase_json = json_content
        elif isinstance(testcase_data, str):
            import json
            try:
                testcase_json = json.loads(testcase_data)
            except json.JSONDecodeError:
                # 如果已经是JSON对象，直接使用
                testcase_json = testcase_data
        else:
            testcase_json = testcase_data
        
        # 提取测试用例列表
        if isinstance(testcase_json, dict) and 'test_cases' in testcase_json:
            test_cases = testcase_json['test_cases']
        elif isinstance(testcase_json, list):
            test_cases = testcase_json
        else:
            return jsonify({
                'success': False,
                'error': '测试用例数据格式不正确，无法提取测试用例列表'
            }), 400
        
        # 转换为YAML格式
        yaml_content = yaml.dump({
            'test_cases': test_cases,
            'metadata': {
                'collection_id': collection_id,
                'interface_id': interface_id,
                'generated_at': datetime.now().isoformat(),
                'testcase_count': len(test_cases)
            }
        }, allow_unicode=True, default_flow_style=False)
        
        # 检查是否已存在Python脚本
        has_existing_script = storage.has_python_script(collection_id, interface_id)
        
        # 调用Dify客户端生成Python脚本
        result = dify_client.generate_python_script_with_yaml(yaml_content, user_id)
        
        if result['success']:
            # 验证Python语法
            validation = dify_client.validate_python_syntax(result['python_code'])
            
            # 检查是否包含多个代码块
            code_blocks_count = result.get('code_blocks_count', 1)
            
            # 持久化保存Python脚本到文件系统
            save_success = storage.save_python_script(
                collection_id, 
                interface_id, 
                result['python_code'], 
                result.get('workflow_id')
            )
            
            if not save_success:
                current_app.logger.warning(f"Python脚本持久化保存失败，但生成成功: {collection_id}_{interface_id}")
            
            return jsonify({
                'success': True,
                'python_code': result['python_code'],
                'workflow_id': result.get('workflow_id'),
                'syntax_valid': validation['valid'],
                'syntax_error': validation.get('error'),
                'saved_to_file': save_success,
                'had_previous_script': has_existing_script,
                'code_blocks_count': code_blocks_count,
                'message': f'Python脚本生成成功，检测到 {code_blocks_count} 个代码块' + ('（已覆盖之前的脚本）' if has_existing_script else '')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"生成Python脚本失败: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'生成Python脚本失败: {str(e)}'
        }), 500
