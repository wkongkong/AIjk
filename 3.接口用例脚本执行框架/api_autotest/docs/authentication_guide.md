# 接口自动化测试框架 - 登录认证配置指南

## 概述

本框架现已支持需要登录认证的接口测试。通过配置认证参数和更新测试用例，可以自动处理认证流程，支持Bearer Token、JWT等多种认证方式。

## 配置说明

### 1. 配置文件 (config.yaml)

在`config.yaml`中添加登录认证配置：

```yaml
# 登录认证配置
login:
  # 登录接口URL（相对路径或完整URL）
  url: "/api/login"
  
  # 登录请求数据
  data:
    username: "test_user"
    password: "test_password"
  
  # 认证头字段名（默认：Authorization）
  auth_header: "Authorization"
  
  # token在响应中的路径（支持点分隔符）
  token_path: "data.token"
```

### 2. 配置参数说明

- **url**: 登录接口URL，可以是相对路径（自动拼接base_url）或完整URL
- **data**: 登录请求参数，根据实际API调整
- **auth_header**: 认证头字段名，默认为"Authorization"
- **token_path**: token在响应中的JSON路径，支持嵌套结构（如"data.user.token"）

## 使用方法

### 1. 直接Token认证（推荐）

对于长有效期的token，可以直接在配置中设置：

```yaml
# config.yaml
login:
  token: "${AUTH_TOKEN}"  # 直接配置token值
  auth_header: "Authorization"
```

**环境变量设置：**
```bash
# Windows
set AUTH_TOKEN=your_long_lived_token_here

# Linux/Mac
export AUTH_TOKEN=your_long_lived_token_here
```

**优势：**
- 无需登录过程，测试执行更快
- 适合长有效期的token
- 避免登录接口不稳定影响测试

### 2. 使用认证fixture

框架提供两种认证fixture：

```python
# 使用已认证的API客户端
def test_with_auth(authenticated_api_client, test_case):
    # authenticated_api_client已自动登录
    response = authenticated_api_client.request(...)

# 获取认证token
def test_get_token(auth_token, api_client, test_case):
    if auth_token:
        # 手动设置认证头
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = api_client.request(..., headers=headers)
```

### 2. 自动认证处理

在测试用例的CSV文件中，通过`preconditions`字段指定认证需求：

```csv
test_case_id,test_case_name,preconditions
TC001,需要认证的接口,需要登录token
TC002,公开接口,无前置条件
```

框架会自动检测preconditions中的关键词（登录、token、auth），并自动处理认证。

### 3. 手动认证控制

```python
# 手动登录
if api_client.login():
    print("登录成功")

# 手动设置token
api_client.set_auth_token("your_token_here")

# 清除认证
api_client.clear_auth()
```

## 测试用例示例

### 认证接口测试用例

创建`test_auth_example.csv`文件：

```csv
test_case_id,test_case_name,api_name,method,url,headers,request_data,expected_status_code,expected_response,test_type,priority,description,preconditions,postconditions,tags,requires_auth,auth_type
TC_AUTH_001,登录接口测试,用户登录,POST,/api/login,"{}""Content-Type"": ""application/json""}","{""username"": ""test_user"", ""password"": ""test_password""}",200,"{""code"": 200, ""message"": ""登录成功""}",positive,high,验证正常登录功能,无前置条件,获取认证token,"auth, login",false,login
TC_AUTH_002,获取用户信息（需要认证）,用户信息查询,GET,/api/user/info,"{}""Content-Type"": ""application/json""}",{},200,"{""code"": 200, ""message"": ""成功""}",positive,high,验证需要认证的接口,需要登录token,返回用户信息,"auth, user",true,bearer
```

## 常见问题

### 1. 登录失败处理

如果登录失败，框架会：
- 记录错误日志
- 继续使用未认证状态执行测试
- 在allure报告中标记认证状态

### 2. Token过期处理

框架目前不支持自动刷新token。如果token过期，需要：
1. 调用`api_client.clear_auth()`清除认证
2. 重新调用`api_client.login()`登录

### 3. 自定义认证方式

如需支持其他认证方式，可扩展`ApiClient`类：

```python
class CustomApiClient(ApiClient):
    def custom_auth(self, auth_data):
        # 实现自定义认证逻辑
        pass
```

## 最佳实践

1. **环境隔离**: 为不同环境配置不同的认证参数
2. **安全考虑**: 不要在代码中硬编码敏感信息，使用环境变量
3. **错误处理**: 为认证失败的情况添加适当的断言和错误处理
4. **测试覆盖**: 包含认证成功、失败、过期等多种场景的测试用例

## 配置示例

### 生产环境配置

```yaml
login:
  url: "/api/v1/auth/login"
  data:
    username: "${PROD_USERNAME}"
    password: "${PROD_PASSWORD}"
  auth_header: "X-Auth-Token"
  token_path: "result.access_token"
```

### 测试环境配置

```yaml
login:
  url: "/api/test/login"
  data:
    username: "test_user"
    password: "test123"
  auth_header: "Authorization"
  token_path: "data.token"
```

通过以上配置，框架可以灵活支持各种认证场景的接口测试。