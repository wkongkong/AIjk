// ==================== 主题切换系统 ====================

/**
 * 主题管理器
 */
const ThemeManager = {
    // 可用主题列表
    themes: {
        default: {
            name: '默认主题',
            icon: '🎨',
            description: '现代渐变风格'
        },
        minimal: {
            name: '简约主题',
            icon: '⚡',
            description: '极简专业风格'
        },
        warm: {
            name: '时尚主题',
            icon: '✨',
            description: '深色科技风格'
        }
    },

    // 当前主题
    currentTheme: 'default',

    // 本地存储键名
    storageKey: 'app-theme-preference',

    /**
     * 初始化主题系统
     */
    init() {
        // 从本地存储加载主题偏好
        this.loadThemePreference();
        
        // 应用主题
        this.applyTheme(this.currentTheme);
        
        // 创建主题切换器UI
        this.createThemeSwitcher();
        
        console.log(`[主题系统] 初始化完成，当前主题: ${this.currentTheme}`);
    },

    /**
     * 从本地存储加载主题偏好
     */
    loadThemePreference() {
        try {
            const savedTheme = localStorage.getItem(this.storageKey);
            if (savedTheme && this.themes[savedTheme]) {
                this.currentTheme = savedTheme;
                console.log(`[主题系统] 加载保存的主题: ${savedTheme}`);
            } else {
                console.log(`[主题系统] 使用默认主题: default`);
            }
        } catch (error) {
            console.error('[主题系统] 加载主题偏好失败:', error);
        }
    },

    /**
     * 保存主题偏好到本地存储
     */
    saveThemePreference(theme) {
        try {
            localStorage.setItem(this.storageKey, theme);
            console.log(`[主题系统] 保存主题偏好: ${theme}`);
        } catch (error) {
            console.error('[主题系统] 保存主题偏好失败:', error);
        }
    },

    /**
     * 应用主题
     */
    applyTheme(theme) {
        if (!this.themes[theme]) {
            console.warn(`[主题系统] 未知主题: ${theme}，使用默认主题`);
            theme = 'default';
        }

        // 设置HTML元素的data-theme属性
        document.documentElement.setAttribute('data-theme', theme);
        
        // 更新当前主题
        this.currentTheme = theme;
        
        // 保存到本地存储
        this.saveThemePreference(theme);
        
        // 更新主题切换器UI
        this.updateThemeSwitcherUI();
        
        console.log(`[主题系统] 应用主题: ${theme} (${this.themes[theme].name})`);
    },

    /**
     * 切换主题
     */
    switchTheme(theme) {
        if (theme === this.currentTheme) {
            console.log(`[主题系统] 已经是当前主题: ${theme}`);
            return;
        }

        // 添加切换动画效果
        document.body.style.opacity = '0.95';
        
        setTimeout(() => {
            this.applyTheme(theme);
            document.body.style.opacity = '1';
        }, 150);
    },

    /**
     * 创建主题切换器UI（折叠式设计）
     */
    createThemeSwitcher() {
        // 检查是否已存在
        if (document.getElementById('themeSwitcher')) {
            return;
        }

        // 创建主题切换器容器
        const switcher = document.createElement('div');
        switcher.id = 'themeSwitcher';
        switcher.className = 'theme-switcher';
        
        // 创建触发按钮（显示当前主题图标）
        const triggerBtn = document.createElement('button');
        triggerBtn.className = 'theme-trigger-btn';
        triggerBtn.innerHTML = `${this.themes[this.currentTheme].icon} 主题`;
        triggerBtn.title = '切换主题';
        
        // 创建下拉面板
        const dropdown = document.createElement('div');
        dropdown.className = 'theme-dropdown';
        dropdown.style.display = 'none';
        
        // 为每个主题创建按钮
        Object.keys(this.themes).forEach(themeKey => {
            const theme = this.themes[themeKey];
            const button = document.createElement('button');
            button.className = 'theme-option-btn';
            button.dataset.theme = themeKey;
            button.innerHTML = `
                <span class="theme-icon">${theme.icon}</span>
                <span class="theme-info">
                    <span class="theme-name">${theme.name}</span>
                    <span class="theme-desc">${theme.description}</span>
                </span>
            `;
            
            // 添加点击事件
            button.addEventListener('click', () => {
                this.switchTheme(themeKey);
                dropdown.style.display = 'none'; // 选择后关闭下拉
            });
            
            dropdown.appendChild(button);
        });
        
        // 触发按钮点击事件
        triggerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
        });
        
        // 点击页面其他地方关闭下拉
        document.addEventListener('click', () => {
            dropdown.style.display = 'none';
        });
        
        // 阻止下拉面板内的点击事件冒泡
        dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        
        // 组装UI
        switcher.appendChild(triggerBtn);
        switcher.appendChild(dropdown);
        
        // 添加到页面
        document.body.appendChild(switcher);
        
        // 更新UI状态
        this.updateThemeSwitcherUI();
    },

    /**
     * 更新主题切换器UI状态
     */
    updateThemeSwitcherUI() {
        // 更新触发按钮
        const triggerBtn = document.querySelector('.theme-trigger-btn');
        if (triggerBtn) {
            triggerBtn.innerHTML = `${this.themes[this.currentTheme].icon} 主题`;
        }
        
        // 更新选项按钮状态
        const buttons = document.querySelectorAll('.theme-option-btn');
        buttons.forEach(button => {
            const theme = button.dataset.theme;
            if (theme === this.currentTheme) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
    },

    /**
     * 获取当前主题信息
     */
    getCurrentThemeInfo() {
        return {
            key: this.currentTheme,
            ...this.themes[this.currentTheme]
        };
    }
};

// 页面加载完成后初始化主题系统
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        ThemeManager.init();
    });
} else {
    ThemeManager.init();
}

// 导出到全局作用域（供其他脚本使用）
window.ThemeManager = ThemeManager;
