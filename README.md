# API文档解析服务平台

## 📋 项目概述

基于Flask的API文档解析服务，集成Dify AI平台，实现从API文档解析到测试用例生成、SVN提交、Jenkins执行的完整自动化测试流程。

**核心特性**：
- 📤 API文档解析（OpenAPI/Swagger、YAML、Markdown）
- 🤖 AI自动生成测试用例（JSON/YAML格式）
- 📝 测试用例审核和编辑
- 🔄 自动提交到SVN仓库
- 🚀 Jenkins自动执行测试
- 📊 Allure测试报告展示

---

## 🚀 快速开始

### 方法一：一键启动（推荐）

在Windows系统上，可以直接运行`start.bat`脚本完成所有初始化和启动工作：

```bash
start.bat
```

该脚本会自动完成以下操作：
1. 检查Python环境（需要Python 3.7或更高版本）
2. 自动安装所需依赖包
3. 检查.env配置文件
4. 创建必要的目录结构
5. 启动Flask服务

### 方法二：手动启动

如果需要手动控制安装过程，可以按以下步骤操作：

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量

复制配置模板：
```bash
copy .env.example .env
```

编辑 `.env` 文件：
```env
# Dify AI配置（必需）
DIFY_API_KEY_YAML=your-dify-api-key
DIFY_WORKFLOW_YAML_URL=http://your-dify-server/v1/chat-messages

# SVN配置（可选）
SVN_REPO_URL=svn://your-svn-server/repo
SVN_USERNAME=your_username
SVN_PASSWORD=your_password
SVN_TARGET_PATH=/path/to/yaml_cases

# 测试报告配置（可选）
TEST_REPORT_URL=http://your-jenkins-server/job/your-job/allure/
```

#### 3. 启动服务

```bash
python run.py
```

访问：http://localhost:5000

---

### 新电脑部署指南

如果是在新电脑上首次部署项目，推荐使用以下步骤：

1. 确保已安装Python 3.7或更高版本
2. 直接运行`start.bat`脚本，它会自动处理所有依赖和配置
3. 根据提示配置.env文件中的Dify API密钥（必需）
4. 如需SVN和Jenkins集成，配置相应的SVN和Jenkins参数
5. 重新运行`start.bat`启动服务

**注意**：start.bat脚本已针对新电脑部署进行了优化，会自动检查并安装所需依赖，创建必要的目录结构，无需手动干预。

---

## ✨ 核心功能

### 1. API文档解析

**支持格式**：
- OpenAPI/Swagger (JSON/YAML)
- Markdown

**功能**：
- 自动解析接口信息
- 展示接口列表和详情
- 搜索和过滤
- 编辑和保存

### 2. AI生成测试用例

**生成方式**：
- 单个接口生成
- 批量生成（支持多接口）

**输出格式**：
- JSON格式（推荐）
- YAML格式

**生成内容**：
```json
{
  "test_case_id": "TC001",
  "test_case_name": "测试登录成功",
  "method": "POST",
  "url": "/api/login",
  "headers": {"Content-Type": "application/json"},
  "request_data": {"username": "admin", "password": "123456"},
  "expected_status_code": 200,
  "expected_response": {"code": "200"},
  "test_type": "positive",
  "priority": "high"
}
```

### 3. 测试用例审核

**功能**：
- 查看生成的测试用例
- 在线编辑用例字段
- 批量审核（通过/拒绝）
- 批量删除
- 名称去重
- 下载YAML文件

**审核状态**：
- 待审核（pending）
- 已通过（approved）
- 已拒绝（rejected）

### 4. 执行用例（SVN提交 + Jenkins触发）

**工作流程**：
```
点击"执行用例" 
  ↓
转换为YAML格式
  ↓
提交到SVN服务器（调试/正式目录）
  ↓
自动触发Jenkins构建
  ↓
获取Jenkins构建号
  ↓
显示执行结果和报告链接
```

**执行模式**：
- 🔧 **调试模式**：提交到 `/jiaoben/jk/data_yaml_debug/`，触发 `AI-jk-debug` Job
- 🚀 **正式模式**：提交到 `/jiaoben/jk/data_yaml/`，触发 `AI-jk` Job

**执行结果**：
- ✅ 提交时间
- 🔖 SVN版本号（如：r367）
- 📝 用例数量
- 🔢 Jenkins构建号（如：#100）
- 🔗 Allure报告链接（可直接点击）

**文件命名**：
```
test_cases_{collection_id}_{interface_id}.yaml
```

### 5. 查看报告

**自动生成报告链接**：
- 执行成功后自动显示报告URL
- 格式：`http://jenkins-server/job/{job_name}/{build_number}/allure/`
- 点击即可查看Allure测试报告

**报告URL示例**：
- 正式：`http://172.16.9.XXX:8082/job/AI-jk/100/allure/`
- 调试：`http://172.16.9.XXX:8082/job/AI-jk-debug/50/allure/`

---

## 📁 项目结构

```
1.API文档解析服务平台/
├── app/
│   ├── __init__.py              # Flask应用初始化
│   ├── routes.py                # API路由
│   ├── parser.py                # OpenAPI解析器
│   ├── md_parser.py             # Markdown解析器
│   ├── dify_client.py           # Dify AI客户端
│   ├── svn_client.py            # SVN客户端（命令行）
│   ├── svn_client_http.py       # SVN客户端（HTTP降级）
│   ├── storage.py               # 数据存储
│   ├── static/
│   │   └── app.js               # 前端JS
│   └── templates/
│       ├── index_enhanced.html  # 首页
│       └── review_testcases.html # 用例审核页面
├── .env                         # 环境变量配置
├── .env.example                 # 配置模板
├── run.py                       # 启动脚本
├── start.bat                    # Windows一键启动脚本
├── requirements.txt             # 依赖包
├── test_svn_connection.py       # SVN连接测试
├── test_jenkins_integration.py  # Jenkins集成测试
└── README.md                    # 本文件
```

---

## 🔧 配置说明

### Dify AI配置（必需）

1. 获取Dify API Key和Workflow URL
2. 配置到 `.env` 文件
3. 重启服务

**验证配置**：
启动日志显示：
```
✅ Dify客户端已初始化
```

### SVN配置（可选）

**前提条件**：
- 安装SVN命令行工具（TortoiseSVN）
- 添加到系统PATH

**配置步骤**：
1. 填写SVN仓库信息到 `.env`：
   ```env
   SVN_REPO_URL=svn://172.16.9.XXX/repo
   SVN_USERNAME=your_username
   SVN_PASSWORD=your_password
   SVN_TARGET_PATH=/jiaoben/jk/data_yaml          # 正式目录
   SVN_DEBUG_PATH=/jiaoben/jk/data_yaml_debug     # 调试目录
   ```
2. 运行测试脚本：
   ```bash
   python test_jenkins_integration.py
   ```
3. 验证连接和提交

**不配置SVN的影响**：
- 可以正常生成和审核测试用例
- 点击"执行用例"会保存到本地
- 显示警告：SVN未配置

### Jenkins配置（可选）

**配置步骤**：
1. 填写Jenkins信息到 `.env`：
   ```env
   JENKINS_URL=http://172.16.9.XXX:8082
   JENKINS_USERNAME=                               # 可选
   JENKINS_PASSWORD=                               # 可选
   JENKINS_JOB_NAME=AI-jk                         # 正式Job
   JENKINS_DEBUG_JOB_NAME=AI-jk-debug             # 调试Job
   ```
2. 运行测试脚本验证连接

**Jenkins Job要求**：
- 监听SVN目录变更
- 执行pytest测试
- 生成Allure报告

**不配置Jenkins的影响**：
- SVN提交正常
- 不会自动触发构建
- 需要手动触发Jenkins Job

### 测试报告配置（可选）

配置Jenkins Allure报告地址：
```env
TEST_REPORT_URL=http://172.16.9.XXX:8082/job/AI-jk/allure/              # 正式报告
TEST_REPORT_DEBUG_URL=http://172.16.9.XXX:8082/job/AI-jk-debug/allure/  # 调试报告
TEST_REPORT_URL_TEMPLATE={base_url}/{build_number}/allure/
```

---

## 🎯 完整工作流程

### 流程图

```
1. 上传API文档
   ↓
2. 解析接口信息
   ↓
3. 选择接口生成测试用例（AI）
   ↓
4. 审核和编辑测试用例
   ↓
5. 点击"执行用例"
   ↓
6. 自动提交到SVN
   ↓
7. Jenkins检测SVN变更
   ↓
8. Jenkins执行测试（pytest + allure）
   ↓
9. 生成Allure报告
   ↓
10. 点击"查看报告"查看结果
```

### 详细步骤

**步骤1：上传API文档**
- 访问首页
- 拖拽或选择API文档文件
- 自动解析并显示接口列表

**步骤2：生成测试用例**
- 点击接口的"生成测试用例"按钮
- AI自动生成测试用例
- 或使用"批量生成"功能

**步骤3：审核测试用例**
- 进入用例审核页面
- 查看和编辑用例字段
- 批量审核通过/拒绝
- 删除不需要的用例

**步骤4：执行用例**
- 点击"▶️ 执行用例"按钮
- 系统自动：
  - 转换为YAML格式
  - 提交到SVN服务器
  - 显示提交结果

**步骤5：查看报告**
- 等待Jenkins执行完成
- 点击"📊 查看报告"按钮
- 查看Allure测试报告

---

## 📊 API接口

### 基础接口

```bash
# 上传文档
POST /api/upload

# 获取集合列表
GET /api/collections

# 获取接口列表
GET /api/collection/{collection_id}/interfaces

# 获取接口详情
GET /api/interface/{collection_id}/{interface_id}

# 搜索接口
GET /api/search?q=关键词
```

### AI生成接口

```bash
# 生成JSON测试用例
POST /api/generate-json/{collection_id}/{interface_id}

# 批量生成测试用例
POST /api/batch-generate

# 检查批量生成状态
GET /api/batch-generate-status/{task_id}
```

### 测试用例管理

```bash
# 保存测试用例
POST /api/save-testcases

# 获取测试用例
GET /api/testcase?collection_id=xxx&interface_id=xxx

# 删除测试用例
DELETE /api/delete-testcase/{collection_id}/{interface_id}

# 下载YAML文件
POST /api/download-yaml
```

### 执行和报告

```bash
# 执行测试用例（提交到SVN并触发Jenkins）
POST /api/execute-testcases
# 请求体：
# {
#   "collection_id": "xxx",
#   "interface_id": "yyy",
#   "yaml_content": "...",
#   "testcases": [],
#   "is_debug": false  // true=调试模式, false=正式模式
# }
# 响应：
# {
#   "success": true,
#   "svn_revision": "12345",
#   "build_number": 100,
#   "report_url": "http://jenkins/job/AI-jk/100/allure/",
#   "jenkins_triggered": true
# }

# 获取报告URL
GET /api/get-report-url?build_number=100&is_debug=false

# 获取Jenkins构建状态
GET /api/get-build-status?job_name=AI-jk&build_number=100
```

---

## 🐳 Docker部署

```bash
# 构建镜像
docker build -t api-parser .

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 🔍 测试

### 测试SVN和Jenkins集成

```bash
# 测试SVN和Jenkins连接
python test_jenkins_integration.py

# 旧版SVN测试（仍可用）
python test_svn_connection.py
```

### 测试API端点

```bash
# 健康检查
curl http://localhost:5000/api/health

# 上传文档
curl -X POST http://localhost:5000/api/upload -F "file=@api_doc.json"
```

---

## ⚠️ 注意事项

### 1. SVN配置

**必需条件**：
- 安装TortoiseSVN并勾选"command line client tools"
- 添加到系统PATH：`D:\Program Files\TortoiseSVN\bin`
- 验证：运行 `svn --version`

**不配置的影响**：
- 测试用例会保存到本地
- 需要手动提交到SVN

### 2. Dify配置

**必需配置**：
- 不配置Dify无法生成测试用例
- 需要有效的API Key和Workflow URL

### 3. 数据持久化

**当前实现**：
- 测试用例保存在 `data/testcases/` 目录
- 重启服务不会丢失数据

### 4. 安全性

**建议**：
- 不要将 `.env` 文件提交到Git
- 使用环境变量管理敏感信息
- 生产环境使用HTTPS

---

## 🐛 故障排查

### Q1: SVN提交失败

**检查**：
1. SVN命令行工具是否安装
2. 运行 `svn --version` 验证
3. 运行 `python test_svn_connection.py` 测试连接
4. 检查用户名密码是否正确

### Q2: Dify生成失败

**检查**：
1. API Key是否正确
2. Workflow URL是否正确
3. 网络是否可访问Dify服务器
4. 查看服务日志

### Q3: 批量生成卡住

**原因**：
- Dify服务器响应慢
- 接口数量太多

**解决**：
- 减少批量生成的接口数量
- 检查Dify服务器状态

### Q4: 中文乱码

**解决**：
- 确保文件使用UTF-8编码
- 检查浏览器编码设置

---

## 📚 相关项目

### 接口用例脚本执行框架

位置：`../3.接口用例脚本执行框架/`

**功能**：
- 执行YAML格式测试用例
- 生成Allure测试报告
- Jenkins集成

**使用**：
```bash
cd ../3.接口用例脚本执行框架/api_autotest
pytest testcases/ -v --alluredir=./allure-results
allure serve ./allure-results
```

**Jenkins集成**：
参考：`../3.接口用例脚本执行框架/Jenkins集成指南.md`

---

## 🔄 更新日志

### v3.2 (2025-06-18)
- ✅ 优化start.bat脚本，支持新电脑一键部署
- ✅ 自动检查Python环境和依赖包
- ✅ 自动创建必要的目录结构
- ✅ 添加配置文件检查功能
- ✅ 完善错误提示和引导信息

### v3.1 (2024-11-29)
- ✅ 实现Jenkins自动触发功能
- ✅ 支持调试/正式环境区分
- ✅ 自动获取Jenkins构建号
- ✅ 自动生成Allure报告链接
- ✅ 添加构建状态查询接口
- ✅ 完善SVN提交信息记录

### v3.0 (2024-11-29)
- ✅ 实现SVN自动提交功能
- ✅ 集成Jenkins Allure报告
- ✅ 支持命令行SVN客户端
- ✅ 添加HTTP SVN客户端降级方案
- ✅ 优化执行结果UI展示

### v2.0 (2024-11-28)
- ✅ 实现批量生成功能
- ✅ 添加用例审核页面
- ✅ 支持批量审核和删除
- ✅ 实现名称去重功能
- ✅ 优化前端交互

### v1.0 (2024-11-26)
- ✅ 基础文档解析功能
- ✅ 集成Dify AI生成测试用例
- ✅ 实现Web界面
- ✅ 支持多种文档格式

---

## 📞 技术支持

**文档**：
- 本README文件
- `.env.example` - 配置模板
- `test_svn_connection.py` - SVN测试工具

**问题排查**：
1. 查看服务启动日志
2. 运行测试脚本
3. 检查配置文件

---

**项目状态**：✅ 生产就绪  
**版本**：v3.2  
**更新时间**：2025-06-18

---

## 📖 更多文档

- [Jenkins集成说明](./Jenkins集成说明.md) - 详细的Jenkins集成配置和使用指南
- [部署运行说明](./部署运行说明.md) - 部署和运行相关说明
- [配置Dify说明](./配置Dify说明.md) - Dify配置详细说明
