// API文档解析服务 - 前端JavaScript

let currentCollection = null;
let allInterfaces = [];
let currentInterface = null;
let currentYAMLContent = '';
let currentPythonCode = '';
let allCollections = [];
let testcaseStatusCache = new Map(); // 测试用例状态缓存
let displayMode = 'list'; // 显示模式：'list' 列表模式，'module' 模块分组模式
let autoGenerateEnabled = localStorage.getItem('autoGenerateEnabled') === 'true'; // 自动AI生成用例开关
let generationQueue = []; // 生成队列
let activeGenerations = 0; // 当前活跃的生成任务数
const MAX_CONCURRENT_GENERATIONS = 5; // 最大并发数
const MAX_RETRY_TIMES = 3; // 最大重试次数
const GENERATION_TIMEOUT = 120000; // 生成超时时间（120秒）

// DOM元素
const homeSection = document.getElementById('homeSection');
const uploadSection = document.getElementById('uploadSection');
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const loading = document.getElementById('loading');
const alert = document.getElementById('alert');
const resultSection = document.getElementById('resultSection');
const collectionInfo = document.getElementById('collectionInfo');
const searchInput = document.getElementById('searchInput');
const interfacesList = document.getElementById('interfacesList');
const collectionsList = document.getElementById('collectionsList');
const emptyState = document.getElementById('emptyState');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadCollections();
    initAutoGenerateSwitch(); // 初始化自动生成开关状态
    
    // 检查URL参数，支持刷新后恢复状态
    const urlParams = new URLSearchParams(window.location.search);
    const collectionId = urlParams.get('collection_id') || urlParams.get('show_collection');
    
    if (collectionId) {
        // 延迟执行，确保collections已加载
        setTimeout(() => {
            viewCollection(collectionId);
        }, 500);
    }
});

// 监听浏览器前进/后退按钮
window.addEventListener('popstate', (event) => {
    const urlParams = new URLSearchParams(window.location.search);
    const collectionId = urlParams.get('collection_id');
    
    if (collectionId) {
        // 有collection_id参数，显示接口列表
        viewCollection(collectionId);
    } else {
        // 没有参数，显示首页
        showHomeSection();
    }
});

function initEventListeners() {
    // 上传区域点击
    if (uploadArea) {
        uploadArea.addEventListener('click', () => fileInput.click());
    }
    
    // 文件选择
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                uploadBtn.disabled = false;
                const firstP = uploadArea.querySelector('p');
                if (firstP) {
                    firstP.textContent = `已选择: ${e.target.files[0].name}`;
                }
            }
        });
    }
    
    // 拖拽上传
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                uploadBtn.disabled = false;
                const firstP = uploadArea.querySelector('p');
                if (firstP) {
                    firstP.textContent = `已选择: ${files[0].name}`;
                }
            }
        });
    }
    
    // 上传按钮
    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadFile);
    }
    
    // 搜索功能
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterInterfaces(e.target.value);
        });
    }
}

// 页面切换函数
function showHomeSection() {
    homeSection.style.display = 'block';
    uploadSection.style.display = 'none';
    resultSection.style.display = 'none';
    loadCollections();
    
    // 清除URL参数，返回首页
    window.history.pushState({}, '', window.location.pathname);
}

function showUploadSection() {
    homeSection.style.display = 'none';
    uploadSection.style.display = 'block';
    resultSection.style.display = 'none';
    
    // 重置上传表单
    if (fileInput) {
        fileInput.value = '';
    }
    if (uploadBtn) {
        uploadBtn.disabled = true;
    }
    const firstP = uploadArea?.querySelector('p');
    if (firstP) {
        firstP.textContent = '拖拽文件到此处，或点击选择文件';
    }
}

function showResultSection() {
    homeSection.style.display = 'none';
    uploadSection.style.display = 'none';
    resultSection.style.display = 'block';
}

// 加载所有集合列表
async function loadCollections() {
    try {
        const response = await fetch('/api/collections');
        const data = await response.json();

        if (response.ok) {
            allCollections = data.collections || [];
            displayCollections(allCollections);
        } else {
            showError(`❌ 加载失败: ${data.error}`);
        }
    } catch (error) {
        console.error('加载集合列表失败:', error);
        displayCollections([]);
    }
}

// 显示集合列表
function displayCollections(collections) {
    if (collections.length === 0) {
        collectionsList.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';
    collectionsList.innerHTML = collections.map(col => `
        <div class="collection-card" onclick="handleCollectionClick('${col.collection_id}')">
            <div class="collection-header" style="cursor: pointer;">
                <h3>${col.title}</h3>
                <span class="collection-version">v${col.version}</span>
            </div>
            <div class="collection-stats">
                <div class="stat-item">
                    <span class="stat-icon">📡</span>
                    <span class="stat-value">${col.interface_count}</span>
                    <span class="stat-label">接口</span>
                </div>
                <div class="stat-item">
                    <span class="stat-icon">📦</span>
                    <span class="stat-value">${col.module_count || 0}</span>
                    <span class="stat-label">模块</span>
                </div>
            </div>
            <div class="collection-actions" onclick="event.stopPropagation()">
                <button class="btn btn-small btn-primary" onclick="viewCollection('${col.collection_id}')">
                    查看接口
                </button>
                <button class="btn btn-small" onclick="deleteCollection('${col.collection_id}', '${col.title}')">
                    🗑️ 删除
                </button>
            </div>
        </div>
    `).join('');
}

// 处理集合卡片点击事件 - 预加载测试用例状态
async function handleCollectionClick(collectionId) {
    console.log(`🔍 预加载集合 ${collectionId} 的测试用例状态...`);
    
    try {
        // 先获取该集合的所有接口
        const interfacesResponse = await fetch(`/api/collection/${collectionId}/interfaces`);
        if (!interfacesResponse.ok) {
            console.error('获取接口列表失败');
            return;
        }
        
        const interfacesData = await interfacesResponse.json();
        const interfaces = interfacesData.interfaces || [];
        
        if (interfaces.length === 0) {
            console.log('该集合没有接口');
            viewCollection(collectionId);
            return;
        }
        
        // 提取所有接口ID
        const interfaceIds = interfaces.map(iface => iface.interface_id);
        
        console.log(`📋 找到 ${interfaceIds.length} 个接口，开始批量查询测试用例状态...`);
        
        // 批量查询测试用例状态
        const statusResponse = await fetch('/api/batch-testcase-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                collection_id: collectionId,
                interface_ids: interfaceIds
            })
        });
        
        if (statusResponse.ok) {
            const statusData = await statusResponse.json();
            console.log(`✅ 成功预加载 ${statusData.has_testcase_count}/${statusData.total_count} 个测试用例状态`);
            
            // 将状态缓存到全局变量
            if (statusData.status_map) {
                Object.entries(statusData.status_map).forEach(([interfaceId, hasTestcase]) => {
                    const cacheKey = `${collectionId}_${interfaceId}`;
                    testcaseStatusCache.set(cacheKey, hasTestcase);
                });
            }
        } else {
            console.warn('批量查询测试用例状态失败');
        }
    } catch (error) {
        console.error('预加载测试用例状态出错:', error);
    }
    
    // 无论预加载是否成功，都继续查看集合
    viewCollection(collectionId);
}

// 查看集合详情
async function viewCollection(collectionId) {
    try {
        const response = await fetch(`/api/collection/${collectionId}`);
        const data = await response.json();

        if (response.ok) {
            currentCollection = {
                collection_id: collectionId,
                ...data.collection
            };
            await loadInterfaces(collectionId);
            showResultSection();
            
            // 更新URL，添加collection_id参数，支持刷新
            const newUrl = `${window.location.pathname}?collection_id=${collectionId}`;
            window.history.pushState({ collectionId }, '', newUrl);
        } else {
            showError(`❌ 加载失败: ${data.error}`);
        }
    } catch (error) {
        showError(`❌ 加载失败: ${error.message}`);
    }
}

// 删除集合
async function deleteCollection(collectionId, title) {
    if (!confirm(`确定要删除"${title}"吗？此操作不可恢复。`)) {
        return;
    }

    try {
        const response = await fetch(`/api/collection/${collectionId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('✅ 删除成功');
            loadCollections();
        } else {
            showError(`❌ 删除失败: ${data.error}`);
        }
    } catch (error) {
        showError(`❌ 删除失败: ${error.message}`);
    }
}

async function uploadFile() {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    loading.style.display = 'block';
    alert.innerHTML = '';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            currentCollection = data;
            showSuccess('✅ 文档解析成功！');
            await loadInterfaces(data.collection_id);
            showResultSection();
        } else {
            showError(`❌ 解析失败: ${data.error}`);
        }
    } catch (error) {
        showError(`❌ 上传失败: ${error.message}`);
    } finally {
        loading.style.display = 'none';
    }
}

async function loadInterfaces(collectionId) {
    try {
        const response = await fetch(`/api/collection/${collectionId}/interfaces`);
        const data = await response.json();

        if (response.ok) {
            allInterfaces = data.interfaces;
            displayCollectionInfo();
            displayInterfaces(allInterfaces);
            
            // 如果开启了自动生成，则开始自动生成测试用例
            if (autoGenerateEnabled) {
                // 延迟1秒后开始，确保界面已渲染完成
                setTimeout(() => {
                    startAutoGeneration();
                }, 1000);
            }
        }
    } catch (error) {
        showError(`❌ 加载接口失败: ${error.message}`);
    }
}

function displayCollectionInfo() {
    // 更新页面标题为集合名称
    const collectionTitleElement = document.getElementById('collectionTitle');
    if (collectionTitleElement) {
        collectionTitleElement.textContent = `📋 ${currentCollection.title}`;
    }
    
    // 计算模块数量（从接口的tags中提取唯一模块）
    const modules = new Set();
    allInterfaces.forEach(iface => {
        if (iface.tags && iface.tags.length > 0) {
            iface.tags.forEach(tag => modules.add(tag));
        }
    });
    const moduleCount = modules.size;
    
    // 计算已有测试用例数量
    let testcaseCount = 0;
    allInterfaces.forEach(iface => {
        const cacheKey = `${currentCollection.collection_id}_${iface.interface_id}`;
        if (testcaseStatusCache.get(cacheKey)) {
            testcaseCount++;
        }
    });

    collectionInfo.innerHTML = `
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">集合 ID</div>
                <div class="info-value" style="font-size: 0.8em; word-break: break-all;">${currentCollection.collection_id}</div>
            </div>
            <div class="info-item">
                <div class="info-label">版本</div>
                <div class="info-value">${currentCollection.version}</div>
            </div>
            <div class="info-item">
                <div class="info-label">接口数量</div>
                <div class="info-value">${currentCollection.interface_count}</div>
            </div>
            <div class="info-item">
                <div class="info-label">模块数量</div>
                <div class="info-value">${moduleCount}</div>
            </div>
            <div class="info-item">
                <div class="info-label">已有测试用例数</div>
                <div class="info-value" id="testcaseCountValue">${testcaseCount}</div>
            </div>
        </div>
    `;
}

// 切换显示模式
function toggleDisplayMode(mode) {
    displayMode = mode;
    
    // 更新按钮状态
    const listBtn = document.getElementById('listModeBtn');
    const moduleBtn = document.getElementById('moduleModeBtn');
    
    if (listBtn && moduleBtn) {
        if (mode === 'list') {
            listBtn.classList.add('active');
            moduleBtn.classList.remove('active');
        } else {
            listBtn.classList.remove('active');
            moduleBtn.classList.add('active');
        }
    }
    
    // 重新显示接口列表
    displayInterfaces(allInterfaces);
}

async function displayInterfaces(interfaces) {
    if (interfaces.length === 0) {
        interfacesList.innerHTML = '<p style="text-align: center; color: #999;">未找到匹配的接口</p>';
        return;
    }

    // 添加批量操作工具栏和显示模式切换按钮
    const batchToolbar = `
        <div class="batch-toolbar" id="batchToolbar">
            <div class="batch-select-all">
                <input type="checkbox" id="selectAllCheckbox" onchange="toggleSelectAll(this.checked)">
                <label for="selectAllCheckbox">全选</label>
                <span id="selectedCount" style="margin-left: 10px; color: #666;">已选择: 0</span>
                <div class="display-mode-toggle" style="display: inline-flex; gap: 5px; margin-left: 15px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden;">
                    <button class="btn btn-small ${displayMode === 'list' ? 'active' : ''}" id="listModeBtn" onclick="toggleDisplayMode('list')" style="border-radius: 0; border: none;">
                        📋 列表模式
                    </button>
                    <button class="btn btn-small ${displayMode === 'module' ? 'active' : ''}" id="moduleModeBtn" onclick="toggleDisplayMode('module')" style="border-radius: 0; border: none;">
                        📁 模块分组
                    </button>
                    ${displayMode === 'module' ? `
                        <button class="btn btn-small" onclick="expandAllModules()" style="border-radius: 0; border: none; border-left: 1px solid #ddd;">
                            ⬇️ 展开全部
                        </button>
                        <button class="btn btn-small" onclick="collapseAllModules()" style="border-radius: 0; border: none; border-left: 1px solid #ddd;">
                            ⬆️ 折叠全部
                        </button>
                    ` : ''}
                </div>
            </div>
            <div class="batch-actions">
                <button class="btn btn-success" onclick="goToAddInterface()">
                    ➕ 新增接口
                </button>
                <button class="btn btn-primary" id="batchGenerateBtn" onclick="batchGenerateTestCases()" disabled>
                    🤖 批量生成用例
                </button>
                <button class="btn btn-warning" id="batchDeleteTestcaseBtn" onclick="batchDeleteTestCases()" disabled>
                    🗑️ 批量删除用例
                </button>
                <button class="btn btn-danger" id="batchDeleteInterfaceBtn" onclick="batchDeleteInterfaces()" disabled>
                    ❌ 批量删除接口
                </button>
            </div>
        </div>
    `;

    let interfacesHTML = '';
    
    if (displayMode === 'module') {
        // 按模块分组显示
        interfacesHTML = displayInterfacesByModule(interfaces);
    } else {
        // 列表模式显示
        interfacesHTML = displayInterfacesList(interfaces);
    }

    interfacesList.innerHTML = batchToolbar + interfacesHTML;
    
    // 优化：批量检查所有接口的测试用例状态，而不是逐个请求
    await batchCheckTestcaseStatus(interfaces.map(iface => iface.interface_id));
}

// 列表模式显示 - 一行显示全部信息
function displayInterfacesList(interfaces) {
    return interfaces.map(iface => `
        <div class="interface-card-oneline" data-interface-id="${iface.interface_id}">
            <div class="oneline-content">
                <input type="checkbox" class="interface-checkbox" data-interface-id="${iface.interface_id}" onchange="updateBatchButtons()">
                <span class="interface-id-badge-oneline">ID: ${iface.interface_id}</span>
                ${iface.tags && iface.tags.length > 0 ? `<span class="module-badge-oneline">${iface.tags[0]}</span>` : '<span class="module-badge-oneline">未分类</span>'}
                <span class="interface-name-oneline">${iface.summary || '无描述'}</span>
                <span class="method-badge method-${iface.method.toLowerCase()}">${iface.method}</span>
                <span class="interface-path-oneline">${iface.path}</span>
                <div class="card-actions-oneline" id="actions-${iface.interface_id}">
                    <button class="btn btn-small btn-icon" onclick="viewInterfaceDetails('${iface.interface_id}')" title="查看详情">
                        👁️ 详情
                    </button>
                    <button class="btn btn-small btn-primary btn-icon" onclick="generateTestCases('${iface.interface_id}')" title="生成测试用例">
                        🤖 生成
                    </button>
                    <button class="btn btn-small btn-danger btn-icon" onclick="deleteInterface('${iface.interface_id}')" title="删除接口">
                        🗑️ 删除
                    </button>
                </div>
            </div>
            <div class="interface-details" id="details-${iface.interface_id}"></div>
        </div>
    `).join('');
}

// 按模块分组显示 - 优化版（默认折叠，按接口数量排序）
function displayInterfacesByModule(interfaces) {
    // 按模块分组
    const moduleGroups = {};
    interfaces.forEach(iface => {
        const moduleName = (iface.tags && iface.tags.length > 0) ? iface.tags[0] : '未分类';
        if (!moduleGroups[moduleName]) {
            moduleGroups[moduleName] = [];
        }
        moduleGroups[moduleName].push(iface);
    });

    // 按接口数量排序（从多到少）
    const sortedModules = Object.entries(moduleGroups).sort((a, b) => b[1].length - a[1].length);

    // 生成分组HTML（默认折叠）
    const modulesHTML = sortedModules.map(([moduleName, moduleInterfaces]) => {
        // 统计各HTTP方法数量
        const methodStats = {};
        moduleInterfaces.forEach(iface => {
            const method = iface.method.toUpperCase();
            methodStats[method] = (methodStats[method] || 0) + 1;
        });
        
        const methodStatsHTML = Object.entries(methodStats)
            .map(([method, count]) => `<span class="method-stat method-stat-${method.toLowerCase()}">${method}: ${count}</span>`)
            .join('');

        return `
            <div class="module-group" data-module="${moduleName}">
                <div class="module-header-enhanced" onclick="toggleModuleGroup('${moduleName}')">
                    <div class="module-header-left">
                        <span class="module-toggle-icon" id="toggle-${moduleName}">▶</span>
                        <span class="module-icon">📁</span>
                        <span class="module-name">${moduleName}</span>
                        <span class="module-count-badge">[${moduleInterfaces.length}]</span>
                    </div>
                    <div class="module-header-right">
                        ${methodStatsHTML}
                        <button class="btn btn-mini" onclick="event.stopPropagation(); selectModuleAll('${moduleName}')" title="全选该模块">
                            ☑️
                        </button>
                        <button class="btn btn-mini btn-primary" onclick="event.stopPropagation(); batchGenerateModule('${moduleName}')" title="批量生成该模块">
                            🤖
                        </button>
                    </div>
                </div>
                <div class="module-content-enhanced" id="module-${moduleName}" style="display: none;">
                    <div class="module-interfaces-grid">
                        ${moduleInterfaces.map(iface => `
                            <div class="interface-card-compact" data-interface-id="${iface.interface_id}">
                                <div class="card-header-compact">
                                    <input type="checkbox" class="interface-checkbox" data-interface-id="${iface.interface_id}" onchange="updateBatchButtons()">
                                    <span class="interface-name-compact">${iface.summary || '无描述'}</span>
                                    <span class="interface-id-badge-compact">ID: ${iface.interface_id}</span>
                                </div>
                                <div class="card-method-path-compact">
                                    <span class="method-badge method-${iface.method.toLowerCase()}">${iface.method}</span>
                                    <span class="interface-path-compact">${iface.path}</span>
                                </div>
                                <div class="card-actions-compact" id="actions-${iface.interface_id}">
                                    <button class="btn btn-mini" onclick="viewInterfaceDetails('${iface.interface_id}')" title="查看详情">👁️</button>
                                    <button class="btn btn-mini btn-primary" onclick="generateTestCases('${iface.interface_id}')" title="生成测试用例">🤖</button>
                                    <button class="btn btn-mini btn-danger" onclick="deleteInterface('${iface.interface_id}')" title="删除接口">🗑️</button>
                                </div>
                                <div class="interface-details" id="details-${iface.interface_id}"></div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // 用容器包裹，实现2列布局
    return `<div class="module-groups-container">${modulesHTML}</div>`;
}

// 切换模块组的展开/收起 - 优化版
function toggleModuleGroup(moduleName) {
    const moduleContent = document.getElementById(`module-${moduleName}`);
    const toggleIcon = document.getElementById(`toggle-${moduleName}`);
    
    if (moduleContent.style.display === 'none') {
        moduleContent.style.display = 'block';
        if (toggleIcon) toggleIcon.textContent = '▼';
    } else {
        moduleContent.style.display = 'none';
        if (toggleIcon) toggleIcon.textContent = '▶';
    }
}

// 展开所有模块
function expandAllModules() {
    const moduleGroups = document.querySelectorAll('.module-group');
    moduleGroups.forEach(group => {
        const moduleName = group.dataset.module;
        const moduleContent = document.getElementById(`module-${moduleName}`);
        const toggleIcon = document.getElementById(`toggle-${moduleName}`);
        if (moduleContent) {
            moduleContent.style.display = 'block';
            if (toggleIcon) toggleIcon.textContent = '▼';
        }
    });
}

// 折叠所有模块
function collapseAllModules() {
    const moduleGroups = document.querySelectorAll('.module-group');
    moduleGroups.forEach(group => {
        const moduleName = group.dataset.module;
        const moduleContent = document.getElementById(`module-${moduleName}`);
        const toggleIcon = document.getElementById(`toggle-${moduleName}`);
        if (moduleContent) {
            moduleContent.style.display = 'none';
            if (toggleIcon) toggleIcon.textContent = '▶';
        }
    });
}

// 选中某个模块的所有接口
function selectModuleAll(moduleName) {
    const moduleGroup = document.querySelector(`[data-module="${moduleName}"]`);
    if (!moduleGroup) return;
    
    const checkboxes = moduleGroup.querySelectorAll('.interface-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(cb => {
        cb.checked = !allChecked;
    });
    
    updateBatchButtons();
}

// 批量生成某个模块的测试用例
async function batchGenerateModule(moduleName) {
    const moduleGroup = document.querySelector(`[data-module="${moduleName}"]`);
    if (!moduleGroup) return;
    
    const checkboxes = moduleGroup.querySelectorAll('.interface-checkbox');
    const interfaceIds = Array.from(checkboxes).map(cb => cb.dataset.interfaceId);
    
    if (interfaceIds.length === 0) {
        showError('❌ 该模块没有接口');
        return;
    }
    
    if (!confirm(`确定要为"${moduleName}"模块的 ${interfaceIds.length} 个接口生成测试用例吗？`)) {
        return;
    }
    
    // 先选中这些接口
    checkboxes.forEach(cb => cb.checked = true);
    updateBatchButtons();
    
    // 调用批量生成函数
    await batchGenerateTestCases();
}

async function checkAndUpdateButtonState(interfaceId) {
    if (!currentCollection || !currentCollection.collection_id) {
        return;
    }
    
    const hasTestcase = await checkTestcaseStatus(currentCollection.collection_id, interfaceId);
    updateButtonState(interfaceId, hasTestcase);
}

async function viewInterfaceDetails(interfaceId) {
    const detailsDiv = document.getElementById(`details-${interfaceId}`);
    const actionsDiv = document.getElementById(`actions-${interfaceId}`);
    const viewBtn = actionsDiv ? actionsDiv.querySelector('button:first-child') : null;
    
    // 找到接口卡片容器
    const interfaceCard = detailsDiv.closest('.interface-card-compact') || 
                         detailsDiv.closest('.interface-card-oneline') ||
                         detailsDiv.closest('.interface-item');
    
    if (detailsDiv.classList.contains('show')) {
        // 收起详情
        detailsDiv.classList.remove('show');
        
        // 移除展开状态的CSS类
        if (interfaceCard) {
            interfaceCard.classList.remove('details-expanded');
        }
        
        // 更新按钮文本和样式 - 恢复为"查看详情"
        if (viewBtn) {
            // 检查按钮原始文本，如果是图标则保持图标，否则显示文字
            const originalText = viewBtn.getAttribute('data-original-text') || '👁️ 详情';
            viewBtn.textContent = originalText;
            viewBtn.classList.remove('btn-info');
            viewBtn.style.background = '';
        }
        return;
    }

    // 保存按钮原始文本
    if (viewBtn && !viewBtn.getAttribute('data-original-text')) {
        viewBtn.setAttribute('data-original-text', viewBtn.textContent);
    }

    // 展开详情
    detailsDiv.innerHTML = '<div class="loading">加载中...</div>';
    detailsDiv.classList.add('show');
    
    // 添加展开状态的CSS类，让卡片占据整行
    if (interfaceCard) {
        interfaceCard.classList.add('details-expanded');
    }
    
    // 更新按钮文本和样式 - 改为"收起详情"
    if (viewBtn) {
        viewBtn.textContent = '👁️ 收起';
        viewBtn.classList.add('btn-info');
        viewBtn.style.background = 'linear-gradient(135deg, #17a2b8 0%, #138496 100%)';
    }

    try {
        const response = await fetch(`/api/interface/${currentCollection.collection_id}/${interfaceId}`);
        const data = await response.json();

        if (response.ok) {
            currentInterface = data.interface;
            detailsDiv.innerHTML = renderInterfaceDetails(data.interface);
        }
    } catch (error) {
        detailsDiv.innerHTML = `<p style="color: red;">加载失败: ${error.message}</p>`;
        
        // 加载失败时恢复按钮状态
        if (viewBtn) {
            viewBtn.textContent = '👁️';
            viewBtn.classList.remove('btn-info');
            viewBtn.style.background = '';
        }
        detailsDiv.classList.remove('show');
        
        // 移除展开状态的CSS类
        if (interfaceCard) {
            interfaceCard.classList.remove('details-expanded');
        }
    }
}

function renderInterfaceDetails(iface) {
    let html = '<div class="detail-content">';
    
    // 添加编辑按钮
    html += `
        <div class="detail-actions">
            <button class="btn btn-small" onclick="editInterface('${iface.id}')">✏️ 编辑接口信息</button>
        </div>
    `;

    // 基本信息
    html += `
        <div class="detail-section">
            <div class="detail-title">📌 基本信息</div>
            <table class="info-table">
                <tr><td><strong>接口ID:</strong></td><td>${iface.id}</td></tr>
                <tr><td><strong>模块名称:</strong></td><td><span class="module-badge">${iface.tags && iface.tags.length > 0 ? iface.tags[0] : '-'}</span></td></tr>
                <tr><td><strong>接口名称:</strong></td><td>${iface.summary || '-'}</td></tr>
                <tr><td><strong>请求方法:</strong></td><td><span class="method-badge method-${iface.method.toLowerCase()}">${iface.method}</span></td></tr>
                <tr><td><strong>接口路径:</strong></td><td><code>${iface.path}</code></td></tr>
                <tr><td><strong>操作ID:</strong></td><td>${iface.operation_id || '-'}</td></tr>
                <tr><td><strong>标签:</strong></td><td>${iface.tags && iface.tags.length > 0 ? iface.tags.join(', ') : '-'}</td></tr>
                <tr><td><strong>已废弃:</strong></td><td>${iface.deprecated ? '是' : '否'}</td></tr>
            </table>
        </div>
    `;

    // 描述
    if (iface.description) {
        html += `
            <div class="detail-section">
                <div class="detail-title">📝 描述</div>
                <p>${iface.description}</p>
            </div>
        `;
    }

    // 请求参数
    if (iface.parameters && iface.parameters.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-title">📋 请求参数 (${iface.parameters.length}个)</div>
                <table class="param-table">
                    <thead>
                        <tr>
                            <th>参数名称</th>
                            <th>参数说明</th>
                            <th>请求类型</th>
                            <th>是否必须</th>
                            <th>数据类型</th>
                            <th>schema</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${iface.parameters.map(param => `
                            <tr>
                                <td><code>${param.name}</code></td>
                                <td>${param.description || '-'}</td>
                                <td><span class="tag">${param.in}</span></td>
                                <td>${param.required ? '<span class="required-badge">必需</span>' : '<span class="optional-badge">可选</span>'}</td>
                                <td>${param.type || param.schema?.type || '-'}</td>
                                <td>${param.schema_ref || '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    // 请求体
    if (iface.request_body) {
        html += `
            <div class="detail-section">
                <div class="detail-title">📤 请求体</div>
                <table class="info-table">
                    <tr><td><strong>必需:</strong></td><td>${iface.request_body.required ? '是' : '否'}</td></tr>
                    ${iface.request_body.content_types ? `<tr><td><strong>Content-Type:</strong></td><td>${iface.request_body.content_types.join(', ')}</td></tr>` : ''}
                    ${iface.request_body.description ? `<tr><td><strong>描述:</strong></td><td>${iface.request_body.description}</td></tr>` : ''}
                    ${iface.request_body.schema_ref ? `<tr><td><strong>Schema:</strong></td><td><code>${iface.request_body.schema_ref}</code></td></tr>` : ''}
                </table>
                ${iface.request_body.example ? `
                    <div style="margin-top: 10px;">
                        <strong>示例:</strong>
                        <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;"><code>${JSON.stringify(iface.request_body.example, null, 2)}</code></pre>
                    </div>
                ` : ''}
            </div>
        `;
    }

    // 响应状态
    if (iface.responses && Object.keys(iface.responses).length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-title">📥 响应状态</div>
                <table class="param-table">
                    <thead>
                        <tr>
                            <th>状态码</th>
                            <th>说明</th>
                            <th>schema</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${Object.entries(iface.responses).map(([status, resp]) => `
                            <tr>
                                <td><span class="status-badge status-${status[0]}xx">${status}</span></td>
                                <td>${resp.description || '-'}</td>
                                <td>${resp.schema_ref || '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    // 响应参数（如果有详细的响应参数定义）
    if (iface.response_parameters && iface.response_parameters.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-title">📊 响应参数</div>
                <table class="param-table">
                    <thead>
                        <tr>
                            <th>参数名称</th>
                            <th>参数说明</th>
                            <th>类型</th>
                            <th>schema</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${iface.response_parameters.map(param => `
                            <tr>
                                <td><code>${param.name}</code></td>
                                <td>${param.description || '-'}</td>
                                <td>${param.type || '-'}</td>
                                <td>${param.schema || '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    // 安全性
    if (iface.security && iface.security.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-title">🔒 安全性</div>
                <ul>
                    ${iface.security.map(sec => `<li>${JSON.stringify(sec)}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    // 服务器
    if (iface.servers && iface.servers.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-title">🌐 服务器</div>
                <ul>
                    ${iface.servers.map(server => `<li><code>${server.url}</code> - ${server.description || ''}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    html += '</div>';
    return html;
}

async function generateTestCases(interfaceId) {
    // 防止重复点击
    const generateBtn = document.querySelector(`#actions-${interfaceId} .btn-primary`);
    if (generateBtn && generateBtn.disabled) {
        return;
    }
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.textContent = '生成中...';
    }
    
    showLoading('正在生成测试用例...');

    try {
        const response = await fetch(`/api/generate-json/${currentCollection.collection_id}/${interfaceId}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            // 清除该接口的缓存
            clearTestcaseStatusCache(interfaceId);
            
            // 更新缓存状态为已有测试用例
            const cacheKey = `${currentCollection.collection_id}_${interfaceId}`;
            testcaseStatusCache.set(cacheKey, true);
            
            // 更新按钮状态
            updateButtonState(interfaceId, true);
            
            // 更新已有测试用例数量显示
            updateTestcaseCount();
            
            // 跳转到测试用例审核页面，传递JSON内容
            const encodedJSON = encodeURIComponent(data.json_content);
            window.location.href = `/review-testcases?json_content=${encodedJSON}&collection_id=${currentCollection.collection_id}&interface_id=${interfaceId}`;
        } else {
            showError(`❌ 生成失败: ${data.error}`);
            // 恢复按钮状态
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.textContent = '🤖 生成';
            }
        }
    } catch (error) {
        showError(`❌ 生成失败: ${error.message}`);
        // 恢复按钮状态
        const generateBtn2 = document.querySelector(`#actions-${interfaceId} .btn-primary`);
        if (generateBtn2) {
            generateBtn2.disabled = false;
            generateBtn2.textContent = '🤖 生成';
        }
    } finally {
        hideLoading();
    }
}

function clearTestcaseStatusCache(interfaceId = null) {
    if (interfaceId) {
        // 清除特定接口的缓存
        const cacheKey = `${currentCollection.collection_id}_${interfaceId}`;
        testcaseStatusCache.delete(cacheKey);
    } else {
        // 清除所有缓存
        testcaseStatusCache.clear();
    }
}

// 更新已有测试用例数量显示
function updateTestcaseCount() {
    if (!currentCollection || !allInterfaces) return;
    
    // 计算已有测试用例数量
    let testcaseCount = 0;
    allInterfaces.forEach(iface => {
        const cacheKey = `${currentCollection.collection_id}_${iface.interface_id}`;
        if (testcaseStatusCache.get(cacheKey)) {
            testcaseCount++;
        }
    });
    
    // 更新显示
    const testcaseCountElement = document.getElementById('testcaseCountValue');
    if (testcaseCountElement) {
        testcaseCountElement.textContent = testcaseCount;
    }
}

function updateButtonState(interfaceId, hasTestcase) {
    // 找到对应的接口项
    const interfaceItem = document.querySelector(`[data-interface-id="${interfaceId}"]`);
    if (!interfaceItem) {
        console.warn(`未找到接口项: ${interfaceId}`);
        return;
    }
    
    // 找到按钮容器 - 支持多种选择器
    let actionsDiv = interfaceItem.querySelector('.card-actions-oneline');
    if (!actionsDiv) {
        actionsDiv = interfaceItem.querySelector('.card-actions-compact');
    }
    if (!actionsDiv) {
        actionsDiv = interfaceItem.querySelector('.interface-actions');
    }
    if (!actionsDiv) {
        actionsDiv = document.getElementById(`actions-${interfaceId}`);
    }
    
    if (!actionsDiv) {
        console.warn(`未找到按钮容器: ${interfaceId}`);
        return;
    }
    
    if (hasTestcase) {
        // 如果已有测试用例，隐藏"生成"按钮
        const generateBtn = actionsDiv.querySelector('.btn-primary');
        if (generateBtn) {
            generateBtn.style.display = 'none';
        }
        
        // 添加用例审核按钮（只有在有测试用例时才显示），插入到删除按钮之前
        if (!actionsDiv.querySelector('.btn-review')) {
            const reviewBtn = document.createElement('button');
            reviewBtn.className = 'btn btn-small btn-review';
            reviewBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
            reviewBtn.style.color = 'white';
            reviewBtn.textContent = '📝 审核';
            reviewBtn.title = '用例审核';
            reviewBtn.onclick = () => {
                // 保存当前接口详情页的URL到sessionStorage
                const currentUrl = window.location.href;
                sessionStorage.setItem('interfaceDetailUrl', currentUrl);
                window.location.href = `/review-testcases?collection_id=${currentCollection.collection_id}&interface_id=${interfaceId}`;
            };
            
            // 找到删除按钮，将用例审核按钮插入到删除按钮之前
            const deleteBtn = actionsDiv.querySelector('.btn-danger');
            if (deleteBtn) {
                actionsDiv.insertBefore(reviewBtn, deleteBtn);
            } else {
                actionsDiv.appendChild(reviewBtn);
            }
        }
    } else {
        // 如果没有测试用例，显示"生成"按钮
        const generateBtn = actionsDiv.querySelector('.btn-primary');
        if (generateBtn) {
            generateBtn.style.display = '';
            generateBtn.disabled = false;
            // 恢复按钮文本
            if (!generateBtn.textContent.includes('生成')) {
                generateBtn.textContent = '🤖 生成';
            }
        }
        
        // 移除用例审核按钮
        const reviewBtn = actionsDiv.querySelector('.btn-review');
        if (reviewBtn) {
            reviewBtn.remove();
        }
    }
}

async function checkTestcaseStatus(collectionId, interfaceId) {
    // 检查缓存
    const cacheKey = `${collectionId}_${interfaceId}`;
    if (testcaseStatusCache.has(cacheKey)) {
        return testcaseStatusCache.get(cacheKey);
    }
    
    try {
        const response = await fetch(`/api/testcase-status?collection_id=${collectionId}&interface_id=${interfaceId}`);
        const data = await response.json();
        
        if (response.ok) {
            // 缓存结果（5分钟有效期）
            testcaseStatusCache.set(cacheKey, data.has_testcase);
            setTimeout(() => {
                testcaseStatusCache.delete(cacheKey);
            }, 5 * 60 * 1000); // 5分钟
            
            return data.has_testcase;
        }
    } catch (error) {
        console.error('检查测试用例状态失败:', error);
    }
    
    // 如果请求失败，缓存false结果（1分钟有效期）
    testcaseStatusCache.set(cacheKey, false);
    setTimeout(() => {
        testcaseStatusCache.delete(cacheKey);
    }, 60 * 1000); // 1分钟
    
    return false;
}

// 批量检查测试用例状态（优化：一次请求获取所有接口的状态）
async function batchCheckTestcaseStatus(interfaceIds) {
    if (!currentCollection || !currentCollection.collection_id || !interfaceIds || interfaceIds.length === 0) {
        return;
    }
    
    console.log(`[批量检查] 开始检查 ${interfaceIds.length} 个接口的测试用例状态`);
    
    try {
        // 一次性请求所有接口的状态
        const response = await fetch(`/api/batch-testcase-status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                collection_id: currentCollection.collection_id,
                interface_ids: interfaceIds
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            const statusMap = data.status_map || {};
            
            console.log(`[批量检查] 成功获取 ${Object.keys(statusMap).length} 个接口的状态`);
            
            // 更新所有接口的按钮状态
            for (const interfaceId of interfaceIds) {
                const hasTestcase = statusMap[interfaceId] || false;
                
                // 更新缓存
                const cacheKey = `${currentCollection.collection_id}_${interfaceId}`;
                testcaseStatusCache.set(cacheKey, hasTestcase);
                
                // 更新按钮状态
                updateButtonState(interfaceId, hasTestcase);
            }
            
            // 更新已有测试用例数量显示
            updateTestcaseCount();
        } else {
            console.warn('[批量检查] 批量检查失败，回退到逐个检查');
            // 如果批量检查失败，回退到逐个检查
            for (const interfaceId of interfaceIds) {
                await checkAndUpdateButtonState(interfaceId);
            }
            // 更新已有测试用例数量显示
            updateTestcaseCount();
        }
    } catch (error) {
        console.error('[批量检查] 批量检查异常，回退到逐个检查:', error);
        // 如果出现异常，回退到逐个检查
        for (const interfaceId of interfaceIds) {
            await checkAndUpdateButtonState(interfaceId);
        }
        // 更新已有测试用例数量显示
        updateTestcaseCount();
    }
}

function showYAMLEditor(yamlContent, interfaceId) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>YAML测试用例编辑器</h2>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="editor-toolbar">
                    <button class="btn btn-small" onclick="regenerateYAML('${interfaceId}')">🔄 重新生成</button>
                    <button class="btn btn-small" onclick="saveYAML()">💾 保存</button>
                    <button class="btn btn-small" onclick="downloadYAML()">📥 下载YAML</button>
                    <button class="btn btn-small btn-primary" onclick="generatePythonFromYAML()">🐍 生成Python脚本</button>
                </div>
                <textarea id="yamlEditor" class="code-editor">${yamlContent}</textarea>
                <div class="editor-info">
                    <p>💡 提示：可以直接编辑YAML内容，确保格式正确（缩进、键值对格式）</p>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.remove();
    }
}

async function regenerateYAML(interfaceId) {
    if (!confirm('确定要重新生成测试用例吗？当前编辑的内容将丢失。')) {
        return;
    }
    closeModal();
    await generateTestCases(interfaceId);
}

function saveYAML() {
    const editor = document.getElementById('yamlEditor');
    currentYAMLContent = editor.value;
    showSuccess('✅ YAML内容已保存');
}

async function downloadYAML() {
    const editor = document.getElementById('yamlEditor');
    const yamlContent = editor.value;

    try {
        const response = await fetch('/api/download-yaml', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                yaml_content: yamlContent,
                filename: 'test_cases.yaml'
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'test_cases.yaml';
            a.click();
            showSuccess('✅ YAML文件下载成功');
        } else {
            showError('❌ 下载失败');
        }
    } catch (error) {
        showError(`❌ 下载失败: ${error.message}`);
    }
}

async function generatePythonFromYAML() {
    const editor = document.getElementById('yamlEditor');
    const yamlContent = editor.value;

    showLoading('正在生成Python脚本...');

    try {
        const response = await fetch('/api/generate-python', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                yaml_content: yamlContent
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentPythonCode = data.python_code;
            closeModal();
            showPythonEditor(data.python_code, data.syntax_valid, data.syntax_error);
            showSuccess('✅ Python脚本生成成功！');
        } else {
            showError(`❌ 生成失败: ${data.error}`);
        }
    } catch (error) {
        showError(`❌ 生成失败: ${error.message}`);
    } finally {
        hideLoading();
        // 恢复按钮状态
        const generateBtn = document.querySelector(`#actions-${interfaceId} .btn-primary`);
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.textContent = '生成测试用例';
        }
    }
}

function showPythonEditor(pythonCode, syntaxValid, syntaxError) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>Python测试脚本编辑器</h2>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="editor-toolbar">
                    <button class="btn btn-small" onclick="regeneratePython()">🔄 重新生成</button>
                    <button class="btn btn-small" onclick="savePython()">💾 保存</button>
                    <button class="btn btn-small" onclick="downloadPython()">📥 下载Python</button>
                    ${!syntaxValid ? `<span class="error-badge">⚠️ 语法错误: ${syntaxError}</span>` : '<span class="success-badge">✅ 语法正确</span>'}
                </div>
                <textarea id="pythonEditor" class="code-editor">${pythonCode}</textarea>
                <div class="editor-info">
                    <p>💡 提示：可以直接编辑Python代码，确保语法正确</p>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

async function regeneratePython() {
    if (!confirm('确定要重新生成Python脚本吗？当前编辑的内容将丢失。')) {
        return;
    }
    closeModal();
    await generatePythonFromYAML();
}

function savePython() {
    const editor = document.getElementById('pythonEditor');
    currentPythonCode = editor.value;
    showSuccess('✅ Python代码已保存');
}

async function downloadPython() {
    const editor = document.getElementById('pythonEditor');
    const pythonCode = editor.value;

    try {
        const response = await fetch('/api/download-python', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                python_code: pythonCode,
                filename: 'test_api.py'
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'test_api.py';
            a.click();
            showSuccess('✅ Python文件下载成功');
        } else {
            showError('❌ 下载失败');
        }
    } catch (error) {
        showError(`❌ 下载失败: ${error.message}`);
    }
}

function editInterface(interfaceId) {
    if (!currentInterface || currentInterface.id !== interfaceId) {
        showError('请先查看接口详情');
        return;
    }

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content modal-large">
            <div class="modal-header">
                <h2>编辑接口信息 - JSON格式</h2>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="editor-toolbar">
                    <button class="btn btn-small" onclick="formatJSON()">🔧 格式化JSON</button>
                    <button class="btn btn-small" onclick="validateJSON()">✅ 验证JSON</button>
                    <span id="jsonStatus" class="json-status"></span>
                </div>
                <div class="form-group">
                    <label>接口完整数据（JSON格式）</label>
                    <textarea id="interfaceJsonEditor" class="code-editor json-editor">${JSON.stringify(currentInterface, null, 2)}</textarea>
                </div>
                <div class="editor-info">
                    <p>💡 提示：直接编辑JSON数据，保存后会更新接口信息。请确保JSON格式正确。</p>
                    <p>⚠️ 注意：不要修改 <code>id</code> 字段，系统会自动保留原ID。</p>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn" onclick="closeModal()">取消</button>
                    <button type="button" class="btn btn-primary" onclick="saveInterfaceChanges('${interfaceId}')">保存更改</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

function formatJSON() {
    const editor = document.getElementById('interfaceJsonEditor');
    try {
        const json = JSON.parse(editor.value);
        editor.value = JSON.stringify(json, null, 2);
        showJSONStatus('✅ JSON格式化成功', 'success');
    } catch (error) {
        showJSONStatus('❌ JSON格式错误: ' + error.message, 'error');
    }
}

function validateJSON() {
    const editor = document.getElementById('interfaceJsonEditor');
    try {
        JSON.parse(editor.value);
        showJSONStatus('✅ JSON格式正确', 'success');
    } catch (error) {
        showJSONStatus('❌ JSON格式错误: ' + error.message, 'error');
    }
}

function showJSONStatus(message, type) {
    const statusEl = document.getElementById('jsonStatus');
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = `json-status ${type}`;
        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = 'json-status';
        }, 3000);
    }
}

async function saveInterfaceChanges(interfaceId) {
    const editor = document.getElementById('interfaceJsonEditor');
    
    let updatedInterface;
    try {
        updatedInterface = JSON.parse(editor.value);
    } catch (error) {
        showError(`❌ JSON格式错误: ${error.message}`);
        return;
    }

    // 确保保留原ID
    updatedInterface.id = interfaceId;

    showLoading('正在保存...');

    try {
        const response = await fetch(`/api/interface/${currentCollection.collection_id}/${interfaceId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                interface: updatedInterface
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentInterface = data.interface;
            closeModal();
            showSuccess('✅ 接口信息已更新');
            
            // 刷新接口详情显示
            const detailsDiv = document.getElementById(`details-${interfaceId}`);
            if (detailsDiv) {
                detailsDiv.innerHTML = renderInterfaceDetails(data.interface);
            }
            
            // 刷新接口列表
            await loadInterfaces(currentCollection.collection_id);
        } else {
            showError(`❌ 保存失败: ${data.error}`);
        }
    } catch (error) {
        showError(`❌ 保存失败: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function filterInterfaces(keyword) {
    if (!keyword.trim()) {
        displayInterfaces(allInterfaces);
        return;
    }

    const lowerKeyword = keyword.toLowerCase();
    
    // 检查是否是特殊筛选关键词
    if (lowerKeyword === '生成失败' || lowerKeyword === '失败') {
        // 筛选出生成失败的接口
        const filtered = allInterfaces.filter(iface => {
            const interfaceItem = document.querySelector(`[data-interface-id="${iface.interface_id}"]`);
            if (interfaceItem) {
                const failedBadge = interfaceItem.querySelector('.generation-status.failed');
                return failedBadge !== null;
            }
            return false;
        });
        displayInterfaces(filtered);
        return;
    }

    // 普通搜索：支持路径、名称、描述、标签、接口ID、模块名称
    const filtered = allInterfaces.filter(iface => {
        // 构建搜索文本，包含所有可搜索字段
        const searchFields = [
            iface.path || '',
            iface.summary || '',
            iface.description || '',
            iface.interface_id || '',
            iface.id || '',
            ...(iface.tags || [])
        ];
        
        const searchText = searchFields.join(' ').toLowerCase();
        return searchText.includes(lowerKeyword);
    });

    displayInterfaces(filtered);
}

function showSuccess(message) {
    alert.innerHTML = `<div class="alert alert-success">${message}</div>`;
    setTimeout(() => alert.innerHTML = '', 5000);
}

function showError(message) {
    alert.innerHTML = `<div class="alert alert-error">${message}</div>`;
}

function showInfo(message) {
    alert.innerHTML = `<div class="alert alert-info">${message}</div>`;
    setTimeout(() => alert.innerHTML = '', 5000);
}

function showLoading(message = '处理中...') {
    loading.innerHTML = `
        <div class="spinner"></div>
        <p>${message}</p>
    `;
    loading.style.display = 'block';
}

function hideLoading() {
    loading.style.display = 'none';
}


// ========== 批量操作功能 ==========

// 全选/取消全选
function toggleSelectAll(checked) {
    const checkboxes = document.querySelectorAll('.interface-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checked;
    });
    updateBatchButtons();
}

// 更新批量操作按钮状态
function updateBatchButtons() {
    const checkboxes = document.querySelectorAll('.interface-checkbox:checked');
    const count = checkboxes.length;
    const selectedCountSpan = document.getElementById('selectedCount');
    const batchGenerateBtn = document.getElementById('batchGenerateBtn');
    const batchDeleteBtn = document.getElementById('batchDeleteBtn');
    const batchDeleteInterfaceBtn = document.getElementById('batchDeleteInterfaceBtn');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    
    if (selectedCountSpan) {
        selectedCountSpan.textContent = `已选择: ${count}`;
    }
    
    if (batchGenerateBtn) {
        batchGenerateBtn.disabled = count === 0;
    }
    
    if (batchDeleteBtn) {
        batchDeleteBtn.disabled = count === 0;
    }
    
    if (batchDeleteInterfaceBtn) {
        batchDeleteInterfaceBtn.disabled = count === 0;
    }
    
    // 更新全选复选框状态
    if (selectAllCheckbox) {
        const allCheckboxes = document.querySelectorAll('.interface-checkbox');
        selectAllCheckbox.checked = allCheckboxes.length > 0 && count === allCheckboxes.length;
        selectAllCheckbox.indeterminate = count > 0 && count < allCheckboxes.length;
    }
}

// 批量生成测试用例
async function batchGenerateTestCases() {
    console.log('[批量生成] 函数被调用');
    
    // 检查currentCollection是否存在
    if (!currentCollection || !currentCollection.collection_id) {
        console.error('[批量生成] currentCollection未初始化:', currentCollection);
        showError('错误：当前集合信息未加载，请刷新页面重试');
        return;
    }
    
    const checkboxes = document.querySelectorAll('.interface-checkbox:checked');
    const interfaceIds = Array.from(checkboxes).map(cb => cb.dataset.interfaceId);
    
    if (interfaceIds.length === 0) {
        showError('❌ 请至少选择一个接口');
        return;
    }
    
    if (!confirm(`确定要为选中的 ${interfaceIds.length} 个接口生成测试用例吗？\n\n将使用智能队列机制：\n• 最多同时5个并发\n• 超时自动重试（最多3次）\n• 失败接口会标记`)) {
        return;
    }
    
    console.log(`🤖 [批量生成] 开始批量生成测试用例，共 ${interfaceIds.length} 个接口`);
    
    // 禁用批量生成按钮，防止重复点击
    const batchGenerateBtn = document.getElementById('batchGenerateBtn');
    const originalText = batchGenerateBtn.innerHTML;
    batchGenerateBtn.disabled = true;
    batchGenerateBtn.innerHTML = '⏳ 生成中...';
    
    // 显示进度条
    showGenerationProgress();
    
    // 构建生成任务列表
    const tasks = interfaceIds.map(interfaceId => {
        const iface = allInterfaces.find(i => i.interface_id === interfaceId);
        return {
            interfaceId: interfaceId,
            interfaceName: iface ? (iface.summary || iface.path) : interfaceId,
            retryCount: 0
        };
    });
    
    // 初始化队列
    generationQueue = [...tasks];
    activeGenerations = 0;
    
    // 记录开始时间
    const startTime = Date.now();
    
    // 开始处理队列
    await processBatchGenerationQueue();
    
    // 计算耗时
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    // 统计结果
    const successCount = interfaceIds.filter(interfaceId => {
        const cacheKey = `${currentCollection.collection_id}_${interfaceId}`;
        return testcaseStatusCache.get(cacheKey);
    }).length;
    
    const failedCount = interfaceIds.length - successCount;
    
    // 隐藏进度条
    hideGenerationProgress();
    
    // 显示结果
    if (failedCount === 0) {
        showSuccess(`🎉 批量生成完成！成功生成 ${successCount} 个接口的测试用例（耗时 ${duration}秒）`);
    } else {
        showSuccess(`⚠️ 批量生成完成！成功 ${successCount} 个，失败 ${failedCount} 个（耗时 ${duration}秒）`);
    }
    
    // 取消所有选择
    toggleSelectAll(false);
    
    // 恢复按钮状态
    batchGenerateBtn.disabled = false;
    batchGenerateBtn.innerHTML = originalText;
}

// 为单个接口生成测试用例（不跳转）
async function generateTestCasesForInterface(interfaceId) {
    const startTime = Date.now();
    console.log(`[批量生成] 开始生成接口 ${interfaceId}`);
    
    // 检查currentCollection
    if (!currentCollection || !currentCollection.collection_id) {
        console.error(`[批量生成] currentCollection未定义，无法生成接口 ${interfaceId}`);
        return { 
            success: false, 
            interfaceId, 
            error: 'currentCollection未定义', 
            duration: Date.now() - startTime 
        };
    }
    
    try {
        const url = `/api/generate-json/${currentCollection.collection_id}/${interfaceId}`;
        console.log(`[批量生成] 请求URL: ${url}`);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log(`[批量生成] 接口 ${interfaceId} 响应状态: ${response.status}`);
        
        const data = await response.json();
        const duration = Date.now() - startTime;
        
        if (response.ok && data.success) {
            console.log(`[批量生成] ✅ 接口 ${interfaceId} 生成成功 (耗时: ${duration}ms)`);
            return { success: true, interfaceId, data, duration };
        } else {
            console.error(`[批量生成] ❌ 接口 ${interfaceId} 生成失败:`, data.error);
            return { success: false, interfaceId, error: data.error || '未知错误', duration };
        }
    } catch (error) {
        const duration = Date.now() - startTime;
        console.error(`[批量生成] ❌ 接口 ${interfaceId} 生成异常:`, error);
        return { success: false, interfaceId, error: error.message || '请求异常', duration };
    }
}

// 显示警告消息
function showWarning(message) {
    const alertDiv = document.getElementById('alert');
    if (alertDiv) {
        alertDiv.innerHTML = `
            <div class="alert alert-warning">
                ${message}
            </div>
        `;
        alertDiv.style.display = 'block';
        setTimeout(() => {
            alertDiv.style.display = 'none';
        }, 5000);
    }
}

// 批量删除测试用例
async function batchDeleteTestCases() {
    console.log('[批量删除] 函数被调用');
    
    // 检查currentCollection是否存在
    if (!currentCollection || !currentCollection.collection_id) {
        console.error('[批量删除] currentCollection未初始化:', currentCollection);
        showError('错误：当前集合信息未加载，请刷新页面重试');
        return;
    }
    
    const checkboxes = document.querySelectorAll('.interface-checkbox:checked');
    console.log('[批量删除] 找到的复选框:', checkboxes.length);
    
    const interfaceIds = Array.from(checkboxes).map(cb => cb.dataset.interfaceId);
    console.log('[批量删除] 提取的接口ID:', interfaceIds);
    
    if (interfaceIds.length === 0) {
        showError('请至少选择一个接口');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${interfaceIds.length} 个接口的测试用例吗？此操作不可恢复！`)) {
        return;
    }
    
    // 禁用批量删除按钮，防止重复点击
    const batchDeleteBtn = document.getElementById('batchDeleteBtn');
    const originalText = batchDeleteBtn.innerHTML;
    batchDeleteBtn.disabled = true;
    batchDeleteBtn.innerHTML = '⏳ 删除中...';
    
    console.log('='.repeat(50));
    console.log('[批量删除] 开始批量删除测试用例');
    console.log(`[批量删除] 选中接口数量: ${interfaceIds.length}`);
    console.log(`[批量删除] 接口ID列表:`, interfaceIds);
    console.log(`[批量删除] 当前集合ID: ${currentCollection.collection_id}`);
    console.log('='.repeat(50));
    
    showInfo(`开始批量删除测试用例，共 ${interfaceIds.length} 个接口...`);
    
    // 并行请求删除测试用例
    const promises = interfaceIds.map(interfaceId => {
        console.log(`[批量删除] 创建Promise for 接口 ${interfaceId}`);
        return deleteTestCaseForInterface(interfaceId);
    });
    
    console.log(`[批量删除] 已创建 ${promises.length} 个Promise，开始并行执行...`);
    
    try {
        const results = await Promise.allSettled(promises);
        
        // 统计结果
        const successResults = results.filter(r => r.status === 'fulfilled' && r.value.success);
        const failResults = results.filter(r => r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.success));
        
        const successCount = successResults.length;
        const failCount = failResults.length;
        const totalCount = interfaceIds.length;
        
        // 显示详细结果
        console.log('='.repeat(50));
        console.log('[批量删除] 总结果:');
        console.log(`  需删除: ${totalCount} 个接口`);
        console.log(`  已删除: ${successCount} 个`);
        console.log(`  失败: ${failCount} 个`);
        console.log('='.repeat(50));
        console.log('[批量删除] 详细结果:', results);
        
        // 构建结果消息
        let resultMessage = `需删除 ${totalCount} 个接口，已删除 ${successCount} 个`;
        if (failCount > 0) {
            resultMessage += `，失败 ${failCount} 个`;
        }
        
        if (failCount === 0) {
            showSuccess(`✅ 批量删除完成！${resultMessage}`);
        } else {
            showWarning(`⚠️ 批量删除完成！${resultMessage}`);
        }
        
        // 更新成功删除的接口按钮状态
        console.log('[批量删除] 开始更新按钮状态...');
        const successInterfaceIds = successResults.map(r => r.value.interfaceId);
        
        for (const interfaceId of successInterfaceIds) {
            // 清除缓存
            clearTestcaseStatusCache(interfaceId);
            // 更新按钮状态为未生成
            updateButtonState(interfaceId, false);
            console.log(`[批量删除] 已更新接口 ${interfaceId} 的按钮状态`);
        }
        
        // 取消所有选择
        toggleSelectAll(false);
        
    } catch (error) {
        showError(`批量删除失败: ${error.message}`);
    } finally {
        // 恢复按钮状态
        batchDeleteBtn.disabled = false;
        batchDeleteBtn.innerHTML = originalText;
    }
}

// 为单个接口删除测试用例
async function deleteTestCaseForInterface(interfaceId) {
    const startTime = Date.now();
    console.log(`[批量删除] 开始删除接口 ${interfaceId} 的测试用例`);
    
    // 检查currentCollection
    if (!currentCollection || !currentCollection.collection_id) {
        console.error(`[批量删除] currentCollection未定义，无法删除接口 ${interfaceId}`);
        return { 
            success: false, 
            interfaceId, 
            error: 'currentCollection未定义', 
            duration: Date.now() - startTime 
        };
    }
    
    try {
        const url = `/api/delete-testcase/${currentCollection.collection_id}/${interfaceId}`;
        console.log(`[批量删除] 请求URL: ${url}`);
        
        const response = await fetch(url, {
            method: 'DELETE'
        });
        
        console.log(`[批量删除] 接口 ${interfaceId} 响应状态: ${response.status}`);
        
        const data = await response.json();
        const duration = Date.now() - startTime;
        
        if (response.ok && data.success) {
            console.log(`[批量删除] ✅ 接口 ${interfaceId} 删除成功 (耗时: ${duration}ms)`);
            return { success: true, interfaceId, data, duration };
        } else {
            console.error(`[批量删除] ❌ 接口 ${interfaceId} 删除失败:`, data.error);
            return { success: false, interfaceId, error: data.error || '未知错误', duration };
        }
    } catch (error) {
        const duration = Date.now() - startTime;
        console.error(`[批量删除] ❌ 接口 ${interfaceId} 删除异常:`, error);
        return { success: false, interfaceId, error: error.message || '请求异常', duration };
    }
}


// ==================== 正式用例执行和总测试报告功能 ====================

/**
 * 执行所有正式用例
 */
async function executeAllProductionTestCases() {
    if (!currentCollection) {
        showError('请先选择一个集合');
        return;
    }

    const confirmMessage = `🚀 确定要执行正式环境的所有用例吗？

📊 执行信息：
   • 集合：${currentCollection.title}
   • 执行范围：正式SVN目录下的所有用例
   • SVN路径：svn://172.16.9.XXX/repo/jiaoben/jk/data_yaml
   • Jenkins Job：AI-jk（正式环境）

⚠️ 注意：这将触发正式环境的完整测试！`;

    if (!confirm(confirmMessage)) {
        return;
    }

    try {
        showLoading('正在触发正式用例执行...');

        const response = await fetch(`/api/execute-all-testcases/${currentCollection.collection_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            const successMessage = `🎉 正式用例执行已触发！

📊 执行信息：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️ Jenkins Job：${data.job_name}
🔢 构建号：#${data.build_number}
📅 触发时间：${new Date().toLocaleString('zh-CN')}
📦 集合：${currentCollection.title}

📍 Jenkins地址：
   http://172.16.9.XXX:8082/view/AI-jiekou/job/AI-jk/

✅ 测试正在执行中，请稍后查看报告。`;

            showSuccess(successMessage);
        } else {
            showError('❌ 触发正式用例执行失败\n\n错误信息：' + data.error);
        }
    } catch (error) {
        showError('❌ 触发正式用例执行失败\n\n错误信息：' + error.message);
    } finally {
        hideLoading();
    }
}

/**
 * 查看总测试报告
 */
function viewProductionReport() {
    // 打开总测试报告页面 - 使用lastBuild获取最新构建号
    const jenkinsJobUrl = 'http://172.16.9.XXX:8082/job/AI-jk/';
    
    const confirmMessage = `📈 即将打开总测试报告

📍 报告地址：
   ${jenkinsJobUrl}

💡 提示：
   • 将打开最新构建的Allure报告
   • 如需查看特定构建，请访问Jenkins页面选择
   • 报告包含所有正式用例的执行结果

是否继续？`;

    if (confirm(confirmMessage)) {
        // 打开最新构建的Allure报告
        const reportUrl = `${jenkinsJobUrl}lastBuild/allure/`;
        window.open(reportUrl, '_blank');
    }
}

// ==================== 辅助函数 ====================

/**
 * 显示成功消息（支持多行格式）
 */
function showSuccess(message) {
    console.log('显示成功消息:', message);
    if (!alert) {
        console.error('找不到alert元素');
        return;
    }
    // 将换行符转换为<br>标签
    const formattedMessage = message.replace(/\n/g, '<br>');
    alert.innerHTML = `<div class="alert alert-success" style="white-space: pre-wrap; text-align: left; line-height: 1.6;">${formattedMessage}</div>`;
    alert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    // 10秒后自动消失
    setTimeout(() => alert.innerHTML = '', 10000);
}


// ==================== 新增接口功能 ====================

/**
 * 跳转到新增接口页面
 */
function goToAddInterface() {
    if (!currentCollection) {
        showError('请先选择一个集合');
        return;
    }
    
    // 跳转到新增接口页面，传递集合ID
    window.location.href = `/add-interface?collection_id=${currentCollection.collection_id}`;
}


// ==================== 批量删除接口功能 ====================

/**
 * 批量删除接口
 */
async function batchDeleteInterfaces() {
    const checkboxes = document.querySelectorAll('.interface-checkbox:checked');
    const interfaceIds = Array.from(checkboxes).map(cb => cb.dataset.interfaceId);
    
    if (interfaceIds.length === 0) {
        showError('请先选择要删除的接口');
        return;
    }
    
    const confirmMessage = `⚠️ 确定要删除选中的 ${interfaceIds.length} 个接口吗？

📋 删除信息：
   • 接口数量：${interfaceIds.length} 个
   • 集合：${currentCollection.title}

⚠️ 警告：
   • 删除接口后，相关的测试用例不会被删除
   • 此操作不可恢复！

是否继续？`;

    if (!confirm(confirmMessage)) {
        return;
    }
    
    console.log('='.repeat(50));
    console.log('[批量删除接口] 开始批量删除接口');
    console.log(`[批量删除接口] 选中接口数量: ${interfaceIds.length}`);
    console.log(`[批量删除接口] 接口ID列表:`, interfaceIds);
    console.log(`[批量删除接口] 当前集合ID: ${currentCollection.collection_id}`);
    console.log('='.repeat(50));
    
    showInfo(`开始批量删除接口，共 ${interfaceIds.length} 个...`);
    
    // 并行请求删除接口
    const promises = interfaceIds.map(interfaceId => {
        console.log(`[批量删除接口] 创建Promise for 接口 ${interfaceId}`);
        return deleteInterfaceById(interfaceId);
    });
    
    console.log(`[批量删除接口] 已创建 ${promises.length} 个Promise，开始并行执行...`);
    
    try {
        const results = await Promise.all(promises);
        
        console.log('[批量删除接口] 所有Promise已完成');
        console.log('[批量删除接口] 结果汇总:', results);
        
        // 统计结果
        const successCount = results.filter(r => r.success).length;
        const failCount = results.length - successCount;
        
        console.log(`[批量删除接口] 成功: ${successCount}, 失败: ${failCount}`);
        
        // 显示结果
        if (failCount === 0) {
            showSuccess(`✅ 批量删除接口成功！\n\n共删除 ${successCount} 个接口`);
        } else {
            showError(`⚠️ 批量删除接口部分失败\n\n成功: ${successCount} 个\n失败: ${failCount} 个`);
        }
        
        // 刷新接口列表
        console.log('[批量删除接口] 刷新接口列表...');
        await viewCollection(currentCollection.collection_id);
        
    } catch (error) {
        console.error('[批量删除接口] 批量删除接口失败:', error);
        showError(`批量删除接口失败: ${error.message}`);
    }
}

/**
 * 删除单个接口（用于批量操作）
 */
async function deleteInterfaceById(interfaceId) {
    const startTime = Date.now();
    console.log(`[批量删除接口] 开始删除接口 ${interfaceId}`);
    
    if (!currentCollection) {
        console.error(`[批量删除接口] ❌ currentCollection未定义`);
        return { 
            success: false, 
            interfaceId, 
            error: 'currentCollection未定义', 
            duration: Date.now() - startTime 
        };
    }
    
    try {
        const url = `/api/collection/${currentCollection.collection_id}/delete-interface/${interfaceId}`;
        console.log(`[批量删除接口] 请求URL: ${url}`);
        
        const response = await fetch(url, {
            method: 'DELETE'
        });
        
        console.log(`[批量删除接口] 接口 ${interfaceId} 响应状态: ${response.status}`);
        
        const data = await response.json();
        const duration = Date.now() - startTime;
        
        if (response.ok && data.success) {
            console.log(`[批量删除接口] ✅ 接口 ${interfaceId} 删除成功 (耗时: ${duration}ms)`);
            return { success: true, interfaceId, data, duration };
        } else {
            console.error(`[批量删除接口] ❌ 接口 ${interfaceId} 删除失败:`, data.error);
            return { success: false, interfaceId, error: data.error || '未知错误', duration };
        }
    } catch (error) {
        const duration = Date.now() - startTime;
        console.error(`[批量删除接口] ❌ 接口 ${interfaceId} 删除异常:`, error);
        return { success: false, interfaceId, error: error.message, duration };
    }
}

// ==================== 批量操作功能 ====================

/**
 * 全选/取消全选
 */
function toggleSelectAll(checked) {
    const checkboxes = document.querySelectorAll('.interface-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = checked;
    });
    updateBatchButtons();
}

/**
 * 批量生成测试用例
 */
async function batchGenerateTestCases() {
    const checkboxes = document.querySelectorAll('.interface-checkbox:checked');
    const selectedIds = Array.from(checkboxes).map(cb => cb.dataset.interfaceId);
    
    if (selectedIds.length === 0) {
        showError('❌ 请先选择要生成测试用例的接口');
        return;
    }
    
    if (!confirm(`确定要为选中的 ${selectedIds.length} 个接口生成测试用例吗？`)) {
        return;
    }
    
    showLoading(`正在批量生成测试用例 (0/${selectedIds.length})...`);
    
    let successCount = 0;
    let failCount = 0;
    const errors = [];
    
    // 逐个生成测试用例
    for (let i = 0; i < selectedIds.length; i++) {
        const interfaceId = selectedIds[i];
        
        // 更新进度
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            const loadingText = loadingDiv.querySelector('p');
            if (loadingText) {
                loadingText.textContent = `正在批量生成测试用例 (${i + 1}/${selectedIds.length})...`;
            }
        }
        
        try {
            const response = await fetch(`/api/generate-json/${currentCollection.collection_id}/${interfaceId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                successCount++;
                // 清除该接口的缓存
                clearTestcaseStatusCache(interfaceId);
                // 更新按钮状态
                updateButtonState(interfaceId, true);
            } else {
                failCount++;
                errors.push(`接口 ${interfaceId}: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            failCount++;
            errors.push(`接口 ${interfaceId}: ${error.message}`);
        }
    }
    
    hideLoading();
    
    // 显示结果
    if (successCount > 0 && failCount === 0) {
        showSuccess(`✅ 成功为 ${successCount} 个接口生成测试用例`);
    } else if (successCount > 0 && failCount > 0) {
        showWarning(`⚠️ 成功生成 ${successCount} 个，失败 ${failCount} 个\n${errors.join('\n')}`);
    } else {
        showError(`❌ 生成失败\n${errors.join('\n')}`);
    }
    
    // 取消选中
    const checkboxes2 = document.querySelectorAll('.interface-checkbox:checked');
    checkboxes2.forEach(cb => cb.checked = false);
    updateBatchButtons();
}

/**
 * 批量删除测试用例
 */
async function batchDeleteTestCases() {
    const checkboxes = document.querySelectorAll('.interface-checkbox:checked');
    const selectedIds = Array.from(checkboxes).map(cb => cb.dataset.interfaceId);
    
    if (selectedIds.length === 0) {
        showError('❌ 请先选择要删除测试用例的接口');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${selectedIds.length} 个接口的测试用例吗？此操作不可恢复。`)) {
        return;
    }
    
    showLoading(`正在批量删除测试用例 (0/${selectedIds.length})...`);
    
    let successCount = 0;
    let failCount = 0;
    const errors = [];
    
    // 逐个删除测试用例
    for (let i = 0; i < selectedIds.length; i++) {
        const interfaceId = selectedIds[i];
        
        // 更新进度
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            const loadingText = loadingDiv.querySelector('p');
            if (loadingText) {
                loadingText.textContent = `正在批量删除测试用例 (${i + 1}/${selectedIds.length})...`;
            }
        }
        
        try {
            const response = await fetch(`/api/delete-testcase/${currentCollection.collection_id}/${interfaceId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                successCount++;
                // 清除该接口的缓存
                clearTestcaseStatusCache(interfaceId);
                // 更新按钮状态
                updateButtonState(interfaceId, false);
            } else {
                failCount++;
                errors.push(`接口 ${interfaceId}: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            failCount++;
            errors.push(`接口 ${interfaceId}: ${error.message}`);
        }
    }
    
    hideLoading();
    
    // 显示结果
    if (successCount > 0 && failCount === 0) {
        showSuccess(`✅ 成功删除 ${successCount} 个测试用例`);
    } else if (successCount > 0 && failCount > 0) {
        showWarning(`⚠️ 成功删除 ${successCount} 个，失败 ${failCount} 个\n${errors.join('\n')}`);
    } else {
        showError(`❌ 删除失败\n${errors.join('\n')}`);
    }
    
    // 取消选中
    const checkboxes2 = document.querySelectorAll('.interface-checkbox:checked');
    checkboxes2.forEach(cb => cb.checked = false);
    updateBatchButtons();
}

/**
 * 更新批量操作按钮状态
 */
async function updateBatchButtons() {
    const checkboxes = document.querySelectorAll('.interface-checkbox');
    const checkedBoxes = Array.from(checkboxes).filter(cb => cb.checked);
    const selectedCount = checkedBoxes.length;
    
    // 更新选中数量显示
    const selectedCountSpan = document.getElementById('selectedCount');
    if (selectedCountSpan) {
        selectedCountSpan.textContent = `已选择: ${selectedCount}`;
    }
    
    // 更新全选复选框状态
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = selectedCount > 0 && selectedCount === checkboxes.length;
        selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < checkboxes.length;
    }
    
    // 更新批量生成用例按钮状态
    const batchGenerateBtn = document.getElementById('batchGenerateBtn');
    if (batchGenerateBtn) {
        batchGenerateBtn.disabled = selectedCount === 0;
    }
    
    // 更新批量删除用例按钮状态（需要检查选中的接口是否有测试用例）
    const batchDeleteTestcaseBtn = document.getElementById('batchDeleteTestcaseBtn');
    if (batchDeleteTestcaseBtn) {
        if (selectedCount === 0) {
            batchDeleteTestcaseBtn.disabled = true;
        } else {
            // 检查选中的接口中是否有测试用例
            const selectedIds = Array.from(checkedBoxes).map(cb => cb.dataset.interfaceId);
            let hasAnyTestcase = false;
            
            for (const interfaceId of selectedIds) {
                const cacheKey = `${currentCollection.collection_id}_${interfaceId}`;
                const hasTestcase = testcaseStatusCache.get(cacheKey);
                if (hasTestcase === true) {
                    hasAnyTestcase = true;
                    break;
                }
            }
            
            // 只有当选中的接口中至少有一个有测试用例时，才启用按钮
            batchDeleteTestcaseBtn.disabled = !hasAnyTestcase;
        }
    }
    
    // 更新批量删除接口按钮状态
    const batchDeleteInterfaceBtn = document.getElementById('batchDeleteInterfaceBtn');
    if (batchDeleteInterfaceBtn) {
        batchDeleteInterfaceBtn.disabled = selectedCount === 0;
    }
}

/**
 * 批量删除接口
 */
async function batchDeleteInterfaces() {
    const checkboxes = document.querySelectorAll('.interface-checkbox:checked');
    const selectedIds = Array.from(checkboxes).map(cb => cb.dataset.interfaceId);
    
    if (selectedIds.length === 0) {
        showError('❌ 请先选择要删除的接口');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${selectedIds.length} 个接口吗？此操作不可恢复。`)) {
        return;
    }
    
    showLoading(`正在删除 ${selectedIds.length} 个接口...`);
    
    let successCount = 0;
    let failCount = 0;
    const errors = [];
    
    // 逐个删除接口
    for (const interfaceId of selectedIds) {
        try {
            const response = await fetch(`/api/collection/${currentCollection.collection_id}/delete-interface/${interfaceId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                successCount++;
                // 从界面移除该接口
                const interfaceItem = document.querySelector(`[data-interface-id="${interfaceId}"]`);
                if (interfaceItem) {
                    interfaceItem.remove();
                }
                // 从allInterfaces数组中移除
                allInterfaces = allInterfaces.filter(iface => iface.interface_id !== interfaceId);
            } else {
                failCount++;
                errors.push(`接口 ${interfaceId}: ${data.error || '未知错误'}`);
            }
        } catch (error) {
            failCount++;
            errors.push(`接口 ${interfaceId}: ${error.message}`);
        }
    }
    
    hideLoading();
    
    // 显示结果
    if (successCount > 0 && failCount === 0) {
        showSuccess(`✅ 成功删除 ${successCount} 个接口`);
    } else if (successCount > 0 && failCount > 0) {
        showWarning(`⚠️ 成功删除 ${successCount} 个接口，失败 ${failCount} 个\n${errors.join('\n')}`);
    } else {
        showError(`❌ 删除失败\n${errors.join('\n')}`);
    }
    
    // 更新界面
    updateBatchButtons();
    
    // 如果所有接口都被删除了，显示空状态
    if (allInterfaces.length === 0) {
        interfacesList.innerHTML = '<p style="text-align: center; color: #999;">暂无接口</p>';
    }
}

/**
 * 删除单个接口
 */
async function deleteInterface(interfaceId) {
    if (!confirm('确定要删除此接口吗？此操作不可恢复。')) {
        return;
    }
    
    showLoading('正在删除接口...');
    
    try {
        const response = await fetch(`/api/collection/${currentCollection.collection_id}/delete-interface/${interfaceId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showSuccess('✅ 接口删除成功');
            
            // 从界面移除该接口
            const interfaceItem = document.querySelector(`[data-interface-id="${interfaceId}"]`);
            if (interfaceItem) {
                interfaceItem.remove();
            }
            
            // 从allInterfaces数组中移除
            allInterfaces = allInterfaces.filter(iface => iface.interface_id !== interfaceId);
            
            // 如果所有接口都被删除了，显示空状态
            if (allInterfaces.length === 0) {
                interfacesList.innerHTML = '<p style="text-align: center; color: #999;">暂无接口</p>';
            }
        } else {
            showError(`❌ 删除失败: ${data.error}`);
        }
    } catch (error) {
        showError(`❌ 删除失败: ${error.message}`);
    } finally {
        hideLoading();
    }
}

/**
 * 显示警告消息
 */
function showWarning(message) {
    const alertDiv = document.getElementById('alert');
    if (alertDiv) {
        alertDiv.innerHTML = `
            <div class="alert alert-warning">
                ${message.replace(/\n/g, '<br>')}
            </div>
        `;
        setTimeout(() => {
            alertDiv.innerHTML = '';
        }, 5000);
    }
}


// ==================== 自动生成测试用例功能 ====================

// 切换自动生成开关
function toggleAutoGenerate(enabled) {
    autoGenerateEnabled = enabled;
    localStorage.setItem('autoGenerateEnabled', enabled);
    
    if (enabled) {
        showSuccess('✅ 已开启自动AI生成用例');
    } else {
        showSuccess('⚠️ 已关闭自动AI生成用例');
    }
}

// 初始化自动生成开关状态
function initAutoGenerateSwitch() {
    const switchElement = document.getElementById('autoGenerateSwitch');
    if (switchElement) {
        switchElement.checked = autoGenerateEnabled;
    }
}

// 开始自动生成所有接口的测试用例
async function startAutoGeneration(manualTrigger = false) {
    // 手动触发时不检查开关状态
    if (!manualTrigger && !autoGenerateEnabled) {
        return;
    }
    
    if (!allInterfaces || allInterfaces.length === 0) {
        showError('❌ 没有可生成的接口');
        return;
    }
    
    console.log(`🤖 开始${manualTrigger ? '手动' : '自动'}生成测试用例，共 ${allInterfaces.length} 个接口`);
    
    // 显示进度条
    showGenerationProgress();
    
    // 过滤出还没有测试用例的接口
    const interfacesToGenerate = [];
    for (const iface of allInterfaces) {
        const cacheKey = `${currentCollection.collection_id}_${iface.interface_id}`;
        const hasTestcase = testcaseStatusCache.get(cacheKey);
        if (!hasTestcase) {
            interfacesToGenerate.push({
                interfaceId: iface.interface_id,
                interfaceName: iface.summary || iface.path,
                retryCount: 0
            });
        }
    }
    
    if (interfacesToGenerate.length === 0) {
        console.log('✅ 所有接口都已有测试用例');
        hideGenerationProgress();
        return;
    }
    
    console.log(`📋 需要生成测试用例的接口数量: ${interfacesToGenerate.length}`);
    
    // 初始化队列
    generationQueue = [...interfacesToGenerate];
    activeGenerations = 0;
    
    // 开始处理队列
    processGenerationQueue();
}

// 处理生成队列
async function processGenerationQueue() {
    while (generationQueue.length > 0 && activeGenerations < MAX_CONCURRENT_GENERATIONS) {
        const task = generationQueue.shift();
        activeGenerations++;
        
        // 异步处理任务
        generateTestCaseWithRetry(task).finally(() => {
            activeGenerations--;
            updateGenerationProgress();
            
            // 继续处理队列
            if (generationQueue.length > 0) {
                processGenerationQueue();
            } else if (activeGenerations === 0) {
                // 所有任务完成
                onAllGenerationsComplete();
            }
        });
    }
}

// 带重试的生成测试用例
async function generateTestCaseWithRetry(task) {
    const { interfaceId, interfaceName, retryCount } = task;
    
    try {
        // 更新界面状态
        updateInterfaceGenerationStatus(interfaceId, 'generating', retryCount);
        
        console.log(`🔄 [${interfaceId}] 开始生成测试用例 (尝试 ${retryCount + 1}/${MAX_RETRY_TIMES + 1})`);
        
        // 创建超时Promise
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('生成超时')), GENERATION_TIMEOUT);
        });
        
        // 创建生成Promise
        const generatePromise = fetch(`/api/generate-json/${currentCollection.collection_id}/${interfaceId}`, {
            method: 'POST'
        }).then(response => response.json());
        
        // 竞速：哪个先完成就用哪个
        const data = await Promise.race([generatePromise, timeoutPromise]);
        
        if (data.success) {
            console.log(`✅ [${interfaceId}] 生成成功`);
            
            // 更新缓存
            const cacheKey = `${currentCollection.collection_id}_${interfaceId}`;
            testcaseStatusCache.set(cacheKey, true);
            
            // 更新按钮状态
            updateButtonState(interfaceId, true);
            updateInterfaceGenerationStatus(interfaceId, 'success');
            
            return { success: true, interfaceId };
        } else {
            throw new Error(data.error || '生成失败');
        }
        
    } catch (error) {
        console.error(`❌ [${interfaceId}] 生成失败:`, error.message);
        
        // 检查是否需要重试
        if (retryCount < MAX_RETRY_TIMES) {
            console.log(`🔄 [${interfaceId}] 准备重试 (${retryCount + 1}/${MAX_RETRY_TIMES})`);
            
            // 更新重试状态
            updateInterfaceGenerationStatus(interfaceId, 'retrying', retryCount + 1);
            
            // 重新加入队列
            generationQueue.push({
                interfaceId,
                interfaceName,
                retryCount: retryCount + 1
            });
            
            return { success: false, interfaceId, retry: true };
        } else {
            console.error(`💥 [${interfaceId}] 重试次数已达上限，标记为失败`);
            
            // 标记为失败
            updateInterfaceGenerationStatus(interfaceId, 'failed');
            
            return { success: false, interfaceId, retry: false };
        }
    }
}

// 更新接口生成状态
function updateInterfaceGenerationStatus(interfaceId, status, retryCount = 0) {
    const interfaceItem = document.querySelector(`[data-interface-id="${interfaceId}"]`);
    if (!interfaceItem) return;
    
    // 移除旧的状态标记（除非是失败状态）
    const oldStatus = interfaceItem.querySelector('.generation-status');
    if (oldStatus) {
        // 如果旧状态是失败，且新状态不是成功，则保留失败标记
        if (oldStatus.classList.contains('failed') && status !== 'success') {
            return;
        }
        oldStatus.remove();
    }
    
    // 添加新的状态标记
    const statusBadge = document.createElement('span');
    statusBadge.className = `generation-status ${status}`;
    statusBadge.dataset.interfaceId = interfaceId; // 添加接口ID用于筛选
    
    let statusText = '';
    let statusIcon = '';
    
    switch (status) {
        case 'generating':
            statusIcon = '⏳';
            statusText = retryCount > 0 ? `生成中 (重试${retryCount})` : '生成中';
            break;
        case 'success':
            statusIcon = '✅';
            statusText = '生成成功';
            // 3秒后自动移除成功标记
            setTimeout(() => {
                if (statusBadge.parentNode) {
                    statusBadge.remove();
                }
            }, 3000);
            break;
        case 'failed':
            statusIcon = '❌';
            statusText = '生成失败';
            // 失败标记不自动移除，一直显示直到生成成功
            break;
        case 'retrying':
            statusIcon = '🔄';
            statusText = `重试中 (${retryCount}/${MAX_RETRY_TIMES})`;
            break;
    }
    
    statusBadge.innerHTML = `${statusIcon} ${statusText}`;
    
    const interfaceHeader = interfaceItem.querySelector('.interface-header');
    if (interfaceHeader) {
        interfaceHeader.appendChild(statusBadge);
    }
}

// 显示生成进度条
function showGenerationProgress() {
    let progressBar = document.querySelector('.generation-progress');
    if (!progressBar) {
        progressBar = document.createElement('div');
        progressBar.className = 'generation-progress';
        progressBar.innerHTML = '<div class="generation-progress-bar"></div>';
        document.body.appendChild(progressBar);
    }
    progressBar.classList.add('active');
    updateGenerationProgress();
}

// 更新生成进度
function updateGenerationProgress() {
    const progressBar = document.querySelector('.generation-progress-bar');
    if (!progressBar) return;
    
    const totalInterfaces = allInterfaces.length;
    const remainingInterfaces = generationQueue.length + activeGenerations;
    const completedInterfaces = totalInterfaces - remainingInterfaces;
    const progress = (completedInterfaces / totalInterfaces) * 100;
    
    progressBar.style.width = `${progress}%`;
    
    console.log(`📊 生成进度: ${completedInterfaces}/${totalInterfaces} (${progress.toFixed(1)}%)`);
}

// 隐藏生成进度条
function hideGenerationProgress() {
    const progressBar = document.querySelector('.generation-progress');
    if (progressBar) {
        setTimeout(() => {
            progressBar.classList.remove('active');
        }, 500);
    }
}

// 所有生成任务完成
function onAllGenerationsComplete() {
    console.log('🎉 所有自动生成任务已完成');
    hideGenerationProgress();
    
    // 统计结果
    const successCount = allInterfaces.filter(iface => {
        const cacheKey = `${currentCollection.collection_id}_${iface.interface_id}`;
        return testcaseStatusCache.get(cacheKey);
    }).length;
    
    const failedCount = allInterfaces.length - successCount;
    
    if (failedCount === 0) {
        showSuccess(`🎉 自动生成完成！成功生成 ${successCount} 个接口的测试用例`);
    } else {
        showSuccess(`⚠️ 自动生成完成！成功 ${successCount} 个，失败 ${failedCount} 个`);
    }
}


// 处理批量生成队列（与自动生成共享队列机制）
async function processBatchGenerationQueue() {
    const promises = [];
    
    while (generationQueue.length > 0 || activeGenerations > 0) {
        // 启动新任务直到达到最大并发数
        while (generationQueue.length > 0 && activeGenerations < MAX_CONCURRENT_GENERATIONS) {
            const task = generationQueue.shift();
            activeGenerations++;
            
            // 创建任务Promise
            const taskPromise = generateTestCaseWithRetry(task).finally(() => {
                activeGenerations--;
                updateGenerationProgress();
            });
            
            promises.push(taskPromise);
        }
        
        // 等待至少一个任务完成
        if (promises.length > 0) {
            await Promise.race(promises);
            // 移除已完成的Promise
            const completedPromises = promises.filter(p => {
                // 检查Promise是否已完成
                let isCompleted = false;
                p.then(() => { isCompleted = true; }).catch(() => { isCompleted = true; });
                return isCompleted;
            });
            completedPromises.forEach(p => {
                const index = promises.indexOf(p);
                if (index > -1) promises.splice(index, 1);
            });
        }
        
        // 如果队列为空且没有活跃任务，退出循环
        if (generationQueue.length === 0 && activeGenerations === 0) {
            break;
        }
        
        // 短暂延迟，避免CPU占用过高
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // 等待所有剩余任务完成
    await Promise.allSettled(promises);
}
