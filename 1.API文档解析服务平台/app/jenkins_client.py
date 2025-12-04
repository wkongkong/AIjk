"""
Jenkins客户端模块
用于触发Jenkins构建并获取构建号
"""
import requests
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class JenkinsClient:
    """Jenkins客户端"""
    
    def __init__(self, jenkins_url: str, username: str = None, password: str = None):
        """
        初始化Jenkins客户端
        
        Args:
            jenkins_url: Jenkins服务器地址，例如: http://172.16.9.XXX:8082
            username: Jenkins用户名（可选）
            password: Jenkins密码或API Token（可选）
        """
        self.jenkins_url = jenkins_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        
        if username and password:
            self.session.auth = (username, password)
        
        logger.info(f"Jenkins客户端初始化: url={jenkins_url}")
    
    def _get_crumb(self) -> Dict[str, str]:
        """
        获取Jenkins CSRF crumb token
        
        Returns:
            包含crumb header的字典
        """
        try:
            crumb_url = f"{self.jenkins_url}/crumbIssuer/api/json"
            response = self.session.get(crumb_url, timeout=5)
            
            if response.status_code == 200:
                crumb_data = response.json()
                crumb_field = crumb_data.get('crumbRequestField', 'Jenkins-Crumb')
                crumb_value = crumb_data.get('crumb', '')
                logger.info(f"获取到Jenkins crumb: {crumb_field}")
                return {crumb_field: crumb_value}
            else:
                logger.warning(f"无法获取Jenkins crumb: {response.status_code}")
                return {}
        except Exception as e:
            logger.warning(f"获取Jenkins crumb失败: {e}")
            return {}
    
    def trigger_build(self, job_name: str, parameters: Dict[str, str] = None, is_debug: bool = False) -> Dict[str, Any]:
        """
        触发Jenkins构建
        
        Args:
            job_name: Jenkins Job名称
            parameters: 构建参数（可选）
            is_debug: 是否为调试模式
            
        Returns:
            包含success, build_number, queue_id的字典
        """
        try:
            # 获取crumb token
            crumb_headers = self._get_crumb()
            
            # 构建触发URL
            if parameters:
                trigger_url = f"{self.jenkins_url}/job/{job_name}/buildWithParameters"
            else:
                trigger_url = f"{self.jenkins_url}/job/{job_name}/build"
            
            logger.info(f"触发Jenkins构建: job={job_name}, url={trigger_url}, params={parameters}")
            
            # 发送构建请求（带crumb header）
            response = self.session.post(
                trigger_url,
                params=parameters,
                headers=crumb_headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                # 从响应头获取队列ID
                queue_url = response.headers.get('Location')
                
                if queue_url:
                    logger.info(f"构建已加入队列: {queue_url}")
                    
                    # 等待构建开始并获取构建号
                    build_number = self._wait_for_build_number(queue_url)
                    
                    if build_number:
                        logger.info(f"Jenkins构建已启动: job={job_name}, build_number={build_number}")
                        
                        return {
                            'success': True,
                            'build_number': build_number,
                            'queue_url': queue_url,
                            'job_name': job_name,
                            'is_debug': is_debug
                        }
                    else:
                        logger.warning(f"无法获取构建号: job={job_name}")
                        return {
                            'success': True,
                            'build_number': None,
                            'queue_url': queue_url,
                            'job_name': job_name,
                            'is_debug': is_debug,
                            'message': '构建已触发但无法获取构建号'
                        }
                else:
                    logger.warning(f"响应头中未找到Location: job={job_name}")
                    return {
                        'success': True,
                        'build_number': None,
                        'job_name': job_name,
                        'is_debug': is_debug,
                        'message': '构建已触发但无法获取队列信息'
                    }
            else:
                logger.error(f"触发Jenkins构建失败: status={response.status_code}, response={response.text}")
                return {
                    'success': False,
                    'error': f'Jenkins返回错误: {response.status_code}'
                }
                
        except requests.Timeout:
            logger.error(f"触发Jenkins构建超时: job={job_name}")
            return {
                'success': False,
                'error': 'Jenkins请求超时'
            }
        except Exception as e:
            logger.error(f"触发Jenkins构建异常: {e}")
            return {
                'success': False,
                'error': f'触发构建异常: {str(e)}'
            }
    
    def _wait_for_build_number(self, queue_url: str, max_wait: int = 30) -> Optional[int]:
        """
        等待构建开始并获取构建号
        
        Args:
            queue_url: 队列URL
            max_wait: 最大等待时间（秒）
            
        Returns:
            构建号，如果超时则返回None
        """
        try:
            # 添加API后缀
            if not queue_url.endswith('/api/json'):
                queue_api_url = f"{queue_url}api/json"
            else:
                queue_api_url = queue_url
            
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    response = self.session.get(queue_api_url, timeout=5)
                    
                    if response.status_code == 200:
                        queue_data = response.json()
                        
                        # 检查是否已经开始构建
                        executable = queue_data.get('executable')
                        if executable:
                            build_number = executable.get('number')
                            if build_number:
                                return build_number
                    
                    # 等待1秒后重试
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"查询队列状态失败: {e}")
                    time.sleep(1)
            
            logger.warning(f"等待构建号超时: queue_url={queue_url}")
            return None
            
        except Exception as e:
            logger.error(f"获取构建号异常: {e}")
            return None
    
    def get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """
        获取构建信息
        
        Args:
            job_name: Jenkins Job名称
            build_number: 构建号
            
        Returns:
            包含构建信息的字典
        """
        try:
            build_url = f"{self.jenkins_url}/job/{job_name}/{build_number}/api/json"
            
            response = self.session.get(build_url, timeout=10)
            
            if response.status_code == 200:
                build_data = response.json()
                
                return {
                    'success': True,
                    'build_number': build_number,
                    'status': build_data.get('result', 'BUILDING'),
                    'building': build_data.get('building', False),
                    'url': build_data.get('url'),
                    'duration': build_data.get('duration'),
                    'timestamp': build_data.get('timestamp')
                }
            else:
                return {
                    'success': False,
                    'error': f'获取构建信息失败: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"获取构建信息异常: {e}")
            return {
                'success': False,
                'error': f'获取构建信息异常: {str(e)}'
            }
    
    def get_allure_report_url(self, job_name: str, build_number: int) -> str:
        """
        生成Allure报告URL
        
        Args:
            job_name: Jenkins Job名称
            build_number: 构建号
            
        Returns:
            Allure报告URL
        """
        return f"{self.jenkins_url}/job/{job_name}/{build_number}/allure/"
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试Jenkins连接
        
        Returns:
            包含success和message的字典
        """
        try:
            response = self.session.get(f"{self.jenkins_url}/api/json", timeout=10)
            
            if response.status_code == 200:
                logger.info("Jenkins连接测试成功")
                return {
                    'success': True,
                    'message': 'Jenkins连接正常'
                }
            else:
                return {
                    'success': False,
                    'error': f'Jenkins返回错误: {response.status_code}'
                }
                
        except requests.Timeout:
            return {
                'success': False,
                'error': 'Jenkins连接超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Jenkins连接异常: {str(e)}'
            }


def create_jenkins_client_from_env():
    """从环境变量创建Jenkins客户端"""
    import os
    
    jenkins_url = os.getenv('JENKINS_URL')
    jenkins_username = os.getenv('JENKINS_USERNAME')
    jenkins_password = os.getenv('JENKINS_PASSWORD')
    
    if not jenkins_url:
        logger.warning("Jenkins URL未配置，Jenkins功能将不可用")
        return None
    
    return JenkinsClient(jenkins_url, jenkins_username, jenkins_password)
