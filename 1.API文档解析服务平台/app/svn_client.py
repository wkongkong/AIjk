"""
SVN客户端模块
用于提交测试用例到SVN仓库
"""
import subprocess
import os
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SVNClient:
    """SVN客户端"""
    
    def __init__(self, repo_url: str, username: str, password: str, target_path: str, debug_path: str = None):
        """
        初始化SVN客户端
        
        Args:
            repo_url: SVN仓库地址，例如: svn://192.168.1.100/testcases
            username: SVN用户名
            password: SVN密码
            target_path: 正式目标路径，例如: /jiaoben/jk/data_yaml
            debug_path: 调试目标路径，例如: /jiaoben/jk/data_yaml_debug
        """
        self.repo_url = repo_url
        self.username = username
        self.password = password
        self.target_path = target_path
        self.debug_path = debug_path or target_path
        # 使用不同的工作目录区分调试和正式环境
        self.workspace_dir = 'svn_workspace'
        self.debug_workspace_dir = 'svn_workspace_debug'
        
        logger.info(f"SVN客户端初始化: repo={repo_url}, path={target_path}, debug_path={debug_path}")
    
    def commit_yaml_file(self, yaml_content: str, collection_id: str, interface_id: str, is_debug: bool = False) -> Dict[str, Any]:
        """
        提交YAML文件到SVN
        
        Args:
            yaml_content: YAML内容
            collection_id: 集合ID
            interface_id: 接口ID
            is_debug: 是否为调试模式（提交到调试目录）
            
        Returns:
            包含success, revision, message, commit_info的字典
        """
        temp_file = None
        try:
            # 1. 根据is_debug选择目标路径和工作目录
            target_svn_path = self.debug_path if is_debug else self.target_path
            workspace_dir = self.debug_workspace_dir if is_debug else self.workspace_dir
            
            # 2. 生成文件名
            filename = f"test_cases_{collection_id}_{interface_id}.yaml"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 3. 创建临时文件
            temp_dir = 'temp'
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, filename)
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            
            logger.info(f"创建临时YAML文件: {temp_file}, 目标路径: {target_svn_path}, 工作目录: {workspace_dir}, 调试模式: {is_debug}")
            
            # 4. 确保SVN工作目录存在
            self._ensure_workspace(target_svn_path, workspace_dir)
            
            # 5. 更新SVN工作目录
            self._update_workspace(workspace_dir)
            
            # 6. 复制文件到SVN工作目录
            import shutil
            target_file = os.path.join(workspace_dir, filename)
            shutil.copy(temp_file, target_file)
            
            logger.info(f"复制文件到SVN工作目录: {target_file}")
            
            # 7. 添加文件到SVN（如果是新文件）
            self._add_file(target_file)
            
            # 8. 提交到SVN
            mode_label = "DEBUG" if is_debug else "PROD"
            commit_message = f"[{mode_label}] Update test cases for {collection_id}/{interface_id} at {timestamp}"
            
            try:
                revision = self._commit_file(target_file, commit_message)
            except subprocess.CalledProcessError as e:
                # 提交失败，记录详细错误信息
                error_detail = f"SVN commit failed: returncode={e.returncode}"
                if e.stderr:
                    error_detail += f", stderr={e.stderr}"
                if e.stdout:
                    error_detail += f", stdout={e.stdout}"
                logger.error(error_detail)
                
                # 尝试获取当前版本号（即使提交失败）
                try:
                    revision = self._get_file_revision(target_file)
                    logger.info(f"获取到当前文件版本号: {revision}")
                except:
                    revision = 'unknown'
                
                raise Exception(f"SVN提交失败: {e.stderr or e.stdout or str(e)}")
            
            # 9. 清理临时文件
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            
            logger.info(f"SVN提交成功: revision={revision}, mode={mode_label}")
            
            # 10. 构建提交信息
            commit_info = {
                'collection_id': collection_id,
                'interface_id': interface_id,
                'filename': filename,
                'revision': revision,
                'commit_message': commit_message,
                'timestamp': timestamp,
                'is_debug': is_debug,
                'target_path': target_svn_path
            }
            
            return {
                'success': True,
                'revision': revision,
                'message': '提交成功',
                'commit_message': commit_message,
                'filename': filename,
                'commit_info': commit_info,
                'is_debug': is_debug
            }
            
        except Exception as e:
            logger.error(f"SVN提交失败: {e}", exc_info=True)
            
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _ensure_workspace(self, target_svn_path: str = None, workspace_dir: str = None):
        """确保SVN工作目录存在"""
        if target_svn_path is None:
            target_svn_path = self.target_path
        if workspace_dir is None:
            workspace_dir = self.workspace_dir
            
        if not os.path.exists(workspace_dir):
            logger.info(f"检出SVN目录: {self.repo_url}{target_svn_path} -> {workspace_dir}")
            
            # 尝试使用svn命令
            svn_cmd = self._get_svn_command()
            
            subprocess.run([
                svn_cmd, 'checkout',
                f'{self.repo_url}{target_svn_path}',
                workspace_dir,
                '--username', self.username,
                '--password', self.password,
                '--non-interactive',
                '--trust-server-cert'
            ], check=True, capture_output=True, text=True)
            
            logger.info(f"SVN目录检出成功: {workspace_dir}")
    
    def _get_svn_command(self):
        """获取SVN命令路径"""
        # 尝试多个可能的SVN命令位置
        possible_paths = [
            'svn',  # 系统PATH中
            'D:\\Program Files\\TortoiseSVN\\bin\\svn.exe',
            'C:\\Program Files\\TortoiseSVN\\bin\\svn.exe',
        ]
        
        for cmd in possible_paths:
            try:
                result = subprocess.run([cmd, '--version'], 
                                      capture_output=True, 
                                      timeout=5)
                if result.returncode == 0:
                    logger.info(f"找到SVN命令: {cmd}")
                    return cmd
            except:
                continue
        
        # 如果都找不到，返回默认的svn
        logger.warning("未找到SVN命令，使用默认'svn'")
        return 'svn'
    
    def _update_workspace(self, workspace_dir: str = None):
        """更新SVN工作目录"""
        if workspace_dir is None:
            workspace_dir = self.workspace_dir
            
        logger.info(f"更新SVN工作目录: {workspace_dir}")
        
        result = subprocess.run([
            'svn', 'update', workspace_dir,
            '--username', self.username,
            '--password', self.password,
            '--non-interactive',
            '--trust-server-cert',
            '--accept', 'theirs-full'  # 自动接受服务器版本，避免冲突
        ], check=True, capture_output=True, text=True)
        
        logger.info(f"SVN更新成功: {result.stdout}")
        
        # 检查是否有冲突
        status_result = subprocess.run([
            'svn', 'status', workspace_dir
        ], capture_output=True, text=True)
        
        if 'C' in status_result.stdout:
            logger.warning(f"检测到冲突，尝试自动解决")
            # 解决所有冲突：接受本地版本
            subprocess.run([
                'svn', 'resolve', '--accept', 'working', '-R', workspace_dir
            ], capture_output=True, text=True)
            logger.info("冲突已自动解决")
    
    def _add_file(self, file_path: str):
        """添加文件到SVN"""
        try:
            # 先检查文件是否已经在SVN中
            status_result = subprocess.run([
                'svn', 'status', file_path
            ], capture_output=True, text=True)
            
            status = status_result.stdout.strip()
            logger.info(f"文件状态: {status}")
            
            # 检查是否有冲突（C标记）
            if 'C' in status or 'conflict' in status.lower():
                logger.warning(f"检测到SVN冲突，尝试解决: {file_path}")
                # 解决冲突：接受本地版本
                resolve_result = subprocess.run([
                    'svn', 'resolve', '--accept', 'working', file_path
                ], capture_output=True, text=True)
                logger.info(f"冲突解决结果: {resolve_result.stdout}")
            
            # 如果文件状态是 '?' (未版本控制)，则添加
            if status.startswith('?'):
                add_result = subprocess.run([
                    'svn', 'add', file_path,
                    '--force'
                ], capture_output=True, text=True, check=True)
                logger.info(f"文件已添加到SVN: {file_path}, 输出: {add_result.stdout}")
            elif status.startswith('M') or status.startswith('A'):
                logger.info(f"文件已在SVN中且有修改: {file_path}")
            elif status.startswith('!'):
                # 文件被标记为缺失，重新添加
                logger.warning(f"文件被标记为缺失，重新添加: {file_path}")
                add_result = subprocess.run([
                    'svn', 'add', file_path,
                    '--force'
                ], capture_output=True, text=True, check=True)
                logger.info(f"文件已重新添加到SVN: {file_path}")
            else:
                logger.info(f"文件已在SVN版本控制中: {file_path}")
                
        except subprocess.CalledProcessError as e:
            # 文件可能已经在SVN中，记录但不抛出异常
            logger.warning(f"添加文件到SVN时出错: {e.stderr if e.stderr else e.stdout}")
    
    def _commit_file(self, file_path: str, commit_message: str) -> str:
        """提交文件到SVN"""
        logger.info(f"提交文件到SVN: {file_path}")
        
        # 先检查文件状态
        try:
            status_result = subprocess.run([
                'svn', 'status', file_path
            ], capture_output=True, text=True)
            logger.info(f"文件SVN状态: {status_result.stdout}")
        except Exception as e:
            logger.warning(f"检查文件状态失败: {e}")
        
        # 提交文件
        result = subprocess.run([
            'svn', 'commit', file_path,
            '-m', commit_message,
            '--username', self.username,
            '--password', self.password,
            '--non-interactive',
            '--trust-server-cert'
        ], capture_output=True, text=True)
        
        # 检查提交结果
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            logger.error(f"SVN提交失败: returncode={result.returncode}, stderr={result.stderr}, stdout={result.stdout}")
            
            # 如果是"没有修改"的错误，不算失败
            if 'is up to date' in error_msg or '没有修改' in error_msg or 'no changes' in error_msg.lower():
                logger.info("文件没有修改，跳过提交")
                revision = self._get_file_revision(file_path)
                return revision
            
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        
        logger.info(f"SVN提交成功: {result.stdout}")
        
        # 获取版本号
        revision = self._get_file_revision(file_path)
        return revision
    
    def _get_file_revision(self, file_path: str) -> str:
        """获取文件的SVN版本号"""
        try:
            result = subprocess.run([
                'svn', 'info', file_path
            ], capture_output=True, text=True, check=True)
            
            # 解析版本号
            for line in result.stdout.split('\n'):
                if line.startswith('Revision:') or line.startswith('版本:'):
                    revision = line.split(':')[1].strip()
                    return revision
            
            return 'unknown'
            
        except Exception as e:
            logger.error(f"获取SVN版本号失败: {e}")
            return 'unknown'
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试SVN连接
        
        Returns:
            包含success和message的字典
        """
        try:
            result = subprocess.run([
                'svn', 'info',
                f'{self.repo_url}{self.target_path}',
                '--username', self.username,
                '--password', self.password,
                '--non-interactive',
                '--trust-server-cert'
            ], capture_output=True, text=True, check=True, timeout=10)
            
            logger.info("SVN连接测试成功")
            
            return {
                'success': True,
                'message': 'SVN连接正常',
                'info': result.stdout
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'SVN连接超时'
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'SVN连接失败: {e.stderr}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'SVN连接异常: {str(e)}'
            }


# 使用示例
def create_svn_client_from_env():
    """从环境变量创建SVN客户端"""
    repo_url = os.getenv('SVN_REPO_URL')
    username = os.getenv('SVN_USERNAME')
    password = os.getenv('SVN_PASSWORD')
    target_path = os.getenv('SVN_TARGET_PATH')
    debug_path = os.getenv('SVN_DEBUG_PATH')
    
    if not all([repo_url, username, password, target_path]):
        logger.warning("SVN配置不完整，SVN功能将不可用")
        return None
    
    return SVNClient(repo_url, username, password, target_path, debug_path)
