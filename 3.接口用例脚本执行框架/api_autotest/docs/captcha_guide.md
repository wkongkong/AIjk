# 图形验证码处理指南

## 概述

本指南介绍如何在接口自动化测试框架中处理需要图形验证码的登录场景。框架提供了多种验证码处理方案，可以根据实际需求选择合适的方法。

## 验证码处理方案

### 1. 开发环境绕过方案（推荐）

在测试环境中，通常可以配置固定的验证码值或禁用验证码验证。

**配置示例：**
```yaml
login:
  url: "http://api.example.com/login"
  test_url: "http://test-api.example.com/login"  # 测试环境登录接口
  data:
    username: "${USERNAME}"
    password: "${PASSWORD}"
  captcha:
    enabled: false  # 禁用验证码
    field_name: "captcha"
    fixed_value: "8888"  # 固定验证码值
```

### 2. 验证码识别方案

#### 2.1 OCR识别

使用OCR技术自动识别验证码图片。

**依赖安装：**
```bash
pip install pytesseract pillow
```

**配置示例：**
```yaml
login:
  captcha:
    enabled: true
    field_name: "captcha"
    image_url: "http://api.example.com/captcha"
    recognition_service: "ocr"
```

#### 2.2 第三方验证码识别服务

集成第三方验证码识别服务（如超级鹰、图鉴等）。

**配置示例：**
```yaml
login:
  captcha:
    enabled: true
    field_name: "captcha"
    image_url: "http://api.example.com/captcha"
    recognition_service: "third_party"
```

### 3. 自动化获取方案

通过自动化工具获取验证码。

**配置示例：**
```yaml
login:
  captcha:
    enabled: true
    field_name: "captcha"
    image_url: "http://api.example.com/captcha"
    # 需要实现自动化获取逻辑
```

### 4. Mock方案

在测试环境中Mock验证码验证逻辑。

**配置示例：**
```yaml
login:
  captcha:
    enabled: true
    field_name: "captcha"
    fixed_value: "mock_code"  # Mock验证码值
```

## 配置说明

### 验证码相关配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | boolean | `false` | 是否启用验证码 |
| `field_name` | string | `"captcha"` | 验证码字段名 |
| `fixed_value` | string | `"8888"` | 固定验证码值 |
| `image_url` | string | `""` | 验证码图片URL |
| `recognition_service` | string | `""` | 验证码识别服务类型 |

### 完整配置示例

```yaml
# config.yaml
base_url: "http://api.example.com"

login:
  url: "${base_url}/login"
  test_url: "http://test-api.example.com/login"
  data:
    username: "${USERNAME}"
    password: "${PASSWORD}"
  auth_header: "Authorization"
  token_path: "data.token"
  
  captcha:
    enabled: true
    field_name: "captcha"
    fixed_value: "8888"
    image_url: "${base_url}/captcha"
    recognition_service: "ocr"
```

## 使用方法

### 1. 基本使用

框架会自动根据配置处理验证码登录：

```python
# 在测试用例中，框架会自动处理验证码登录
@pytest.mark.parametrize("test_case", test_data)
def test_api_with_captcha(authenticated_api_client, test_case):
    # 如果配置了验证码，框架会自动处理
    response = authenticated_api_client.request(
        method=test_case["method"],
        url=test_case["url"],
        data=test_case["request_data"]
    )
    # 断言响应
    assert response.status_code == 200
```

### 2. 手动处理验证码

如果需要手动控制验证码处理：

```python
def test_manual_captcha_login(api_client):
    # 手动获取验证码图片
    image_data = api_client.get_captcha_image()
    
    # 手动识别验证码
    captcha_value = api_client.recognize_captcha(image_data)
    
    # 使用验证码登录
    if api_client.login(captcha_value):
        # 登录成功，执行测试
        response = api_client.request(...)
        assert response.status_code == 200
```

### 3. 测试用例中的验证码处理

在CSV测试数据中标记验证码需求：

```csv
test_case_id,preconditions,method,url,request_data,expected_status
TC001,"需要登录和验证码","POST","/user/info","{}",200
TC002,"无需认证","GET","/public/data","",200
```

## 最佳实践

### 1. 环境区分
- **开发环境**：使用固定验证码或禁用验证码
- **测试环境**：根据实际情况选择合适的方案
- **生产环境**：谨慎使用，确保符合安全要求

### 2. 错误处理
- 验证码识别失败时应有降级方案
- 记录验证码识别的成功率
- 设置合理的重试机制

### 3. 性能考虑
- 验证码识别会增加测试执行时间
- 考虑使用缓存机制减少重复识别
- 批量测试时注意验证码获取频率限制

### 4. 安全考虑
- 不要在生产环境中硬编码验证码
- 保护验证码识别服务的API密钥
- 遵守目标系统的使用条款

## 常见问题

### Q: 验证码识别准确率低怎么办？
A: 可以尝试以下方法：
- 使用更高质量的验证码图片
- 调整OCR识别参数
- 使用专业的第三方验证码识别服务
- 增加图像预处理步骤

### Q: 验证码接口有频率限制怎么办？
A: 可以：
- 降低测试执行频率
- 使用验证码缓存机制
- 在测试环境中配置无限制的验证码接口

### Q: 如何测试验证码错误的情况？
A: 可以：
- 手动设置错误的验证码值
- 使用专门的错误测试用例
- 模拟验证码识别失败的情况

## 扩展开发

如果需要自定义验证码处理逻辑，可以继承`APIClient`类：

```python
from core.api_client import APIClient

class CustomAPIClient(APIClient):
    def recognize_captcha(self, image_data: bytes) -> str:
        # 实现自定义验证码识别逻辑
        # 例如调用自定义的AI识别服务
        return "custom_captcha"
```

然后更新conftest.py中的fixture使用自定义客户端。