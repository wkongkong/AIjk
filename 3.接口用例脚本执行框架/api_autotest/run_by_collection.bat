@echo off
chcp 65001 >nul
echo ============================================================
echo API 测试用例执行脚本 - 按集合ID筛选
echo ============================================================
echo.

REM 获取参数（从环境变量或命令行参数）
if "%COLLECTION_ID%"=="" (
    if "%1"=="" (
        set COLLECTION_ID=*
    ) else (
        set COLLECTION_ID=%1
    )
)

if "%EXECUTE_ALL%"=="" set EXECUTE_ALL=false
if "%DATA_DIR%"=="" set DATA_DIR=data_yaml

echo 环境变量:
echo   COLLECTION_ID: %COLLECTION_ID%
echo   EXECUTE_ALL: %EXECUTE_ALL%
echo   DATA_DIR: %DATA_DIR%
echo.

REM 检查数据目录
if not exist "%DATA_DIR%" (
    echo ❌ 错误：数据目录不存在: %DATA_DIR%
    exit /b 1
)

REM 构建搜索模式
if "%COLLECTION_ID%"=="*" (
    set PATTERN=%DATA_DIR%\test_cases_*.yaml
    echo 📋 执行模式：所有测试用例
) else if "%EXECUTE_ALL%"=="true" (
    set PATTERN=%DATA_DIR%\test_cases_*.yaml
    echo 📋 执行模式：所有测试用例
) else (
    set PATTERN=%DATA_DIR%\test_cases_%COLLECTION_ID%_*.yaml
    echo 📋 执行模式：集合 %COLLECTION_ID% 的测试用例
)

echo 🔍 搜索模式：%PATTERN%
echo.

REM 检查是否有匹配的文件
dir /b "%PATTERN%" >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到匹配的测试用例文件
    echo    搜索模式：%PATTERN%
    echo    数据目录：%CD%\%DATA_DIR%
    echo.
    echo 💡 提示：
    echo    1. 检查测试用例文件是否已从SVN更新
    echo    2. 检查文件命名是否符合规范：test_cases_{COLLECTION_ID}_{INTERFACE_ID}.yaml
    echo    3. 检查COLLECTION_ID参数是否正确
    exit /b 1
)

REM 列出匹配的文件
echo ✅ 找到以下测试用例文件：
dir /b "%PATTERN%"
echo.

REM 执行测试
echo ============================================================
echo 开始执行测试...
echo ============================================================
echo.

python -m pytest testcases/test_common.py ^
    --data-dir=%DATA_DIR% ^
    -v ^
    --alluredir=./allure-results ^
    --clean-alluredir

set TEST_RESULT=%ERRORLEVEL%

echo.
echo ============================================================
if %TEST_RESULT%==0 (
    echo ✅ 测试执行完成
) else (
    echo ❌ 测试执行失败 ^(退出码: %TEST_RESULT%^)
)
echo ============================================================
echo.

REM 生成Allure报告（可选）
if exist "allure-2.35.1\bin\allure.bat" (
    echo 生成Allure报告...
    allure-2.35.1\bin\allure.bat generate allure-results -o allure-report --clean
    echo.
    echo 报告已生成到: allure-report
)

exit /b %TEST_RESULT%
