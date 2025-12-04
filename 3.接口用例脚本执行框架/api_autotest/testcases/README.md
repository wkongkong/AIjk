# testcases - 通用测试脚本目录

## 📋 说明

这是**通用测试脚本**目录，提供统一的测试执行入口，自动解析执行 `data_csv` 和 `data_yaml` 目录下的测试用例文件。

## 🎯 核心特性

- ✅ **双格式支持**：自动识别并解析 CSV 和 YAML 格式的测试用例
- ✅ **自动扫描**：自动扫描 data_csv 和 data_yaml 目录下的所有测试用例文件
- ✅ **灵活执行**：支持执行所有用例、指定文件、指定目录
- ✅ **智能认证**：根据前置条件自动处理认证逻辑
- ✅ **Allure报告**：自动生成详细的测试报告

## 📁 目录结构

```
api_autotest/
├── data_csv/              # CSV格式测试用例（共享）
│   ├── test_1.csv
│   └── test_login.csv
├── data_yaml/             # YAML格式测试用例（共享）
│   ├── test_example.yaml
│   └── test_api.yaml
└── testcases/             # 通用测试脚本 ⭐
    ├── conftest.py        # pytest配置（自动加载测试用例）
    ├── test_common.py     # 通用测试脚本
    └── README.md          # 本文档
```

## 🚀 使用方式

### 方式1：执行所有测试用例（推荐）

自动扫描 `data_csv` 和 `data_yaml` 目录下的所有测试用例文件：

```bash
# 执行所有测试用例
pytest testcases/test_common.py -v

# 生成Allure报告
pytest testcases/test_common.py --alluredir=allure-results
allure serve allure-results
```

### 方式2：执行指定文件的测试用例

```bash
# 执行CSV文件
pytest testcases/test_common.py --data-file=data_csv/test_1.csv -v

# 执行YAML文件
pytest testcases/test_common.py --data-file=data_yaml/test_example.yaml -v

# 使用绝对路径
pytest testcases/test_common.py --data-file=D:/project/data_csv/test_1.csv -v
```

### 方式3：执行指定目录的测试用例

```bash
# 只执行CSV目录下的测试用例
pytest testcases/test_common.py --data-dir=data_csv -v

# 只执行YAML目录下的测试用例
pytest testcases/test_common.py --data-dir=data_yaml -v
```

### 方式4：按标签过滤执行

```bash
# 执行带有login标签的测试用例
pytest testcases/test_common.py -v -m "login"

# 执行带有smoke标签的测试用例
pytest testcases/test_common.py -v -m "smoke"
```

## 📝 测试用例格式

### CSV格式示例

```csv
test_case_id,test_case_name,api_name,method,url,headers,request_data,expected_status_code,expected_response,test_type,priority,description,preconditions,postconditions,tags
TC001,获取用户应用,获取用户应用,POST,/user/getUserApplication,"{""Content-Type"": ""application/json""}","{""terminalCode"":""d_web""}",200,"{""code"":""1""}",positive,high,验证正常返回,token,-,"login,smoke"
```

### YAML格式示例

```yaml
test_cases:
  - test_case_id: "TC001"
    test_case_name: "获取用户应用"
    api_name: "获取用户应用"
    method: "POST"
    url: "/user/getUserApplication"
    headers:
      Content-Type: "application/json"
    request_data:
      terminalCode: "d_web"
    expected_status_code: 200
    expected_response:
      code: "1"
    test_type: "positive"
    priority: "high"
    description: "验证正常返回"
    preconditions: "token"
    postconditions: "-"
    tags:
      - "login"
      - "smoke"
```

## 🔧 前置条件处理

通用测试脚本会根据 `preconditions` 字段自动处理认证：

| 前置条件关键词 | 处理方式 |
|--------------|---------|
| token / 认证 / 登录 | 自动登录获取token |
| 权限不足 / 无权限 / 低权限 | 使用低权限token |
| 未登录 / 未认证 / 无token | 清除认证信息 |
| - 或空 | 不做特殊处理 |

## 📊 测试报告

### 生成Allure报告

```bash
# 1. 执行测试并生成报告数据
pytest testcases/test_common.py --alluredir=allure-results -v

# 2. 启动Allure服务查看报告
allure serve allure-results
```

### 报告内容

- 测试用例ID和名称
- 测试描述
- 优先级标签
- 请求和响应详情
- 断言结果
- 执行时间

## ⚙️ 配置说明

### conftest.py

- 自动扫描测试用例文件
- 动态生成pytest参数化
- 支持命令行参数配置

### test_common.py

- 通用测试执行逻辑
- 自动处理认证
- 统一断言处理
- Allure报告集成

## 💡 最佳实践

1. **文件命名**：测试用例文件建议以 `test_` 开头，便于识别
2. **用例ID**：每个测试用例应有唯一的 `test_case_id`
3. **格式选择**：
   - 简单用例 → CSV格式
   - 复杂用例 → YAML格式
4. **标签使用**：合理使用tags进行用例分类和过滤

## 🔍 故障排查

### 问题1：找不到测试用例

```bash
# 检查文件路径是否正确
ls data_csv/
ls data_yaml/

# 检查文件格式是否正确
file data_csv/test_1.csv
```

### 问题2：JSON解析错误

- CSV文件中的JSON字段需要转义双引号（`""`）
- YAML文件中的JSON字段直接使用字典格式

### 问题3：认证失败

- 检查 `config/config.yaml` 中的认证配置
- 确认前置条件字段是否正确

---

**更新时间**：2024-11-28
