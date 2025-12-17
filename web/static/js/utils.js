/**
 * AutoGLM Console - Utility Functions
 * 通用工具函数模块
 */

// 去除ANSI颜色码
function stripAnsi(str) {
    if (!str) return '';
    // 匹配标准的ANSI转义序列：\x1b[...m
    // 同时匹配可能的不完整序列（以 [ 开始，以 m 结束）
    return str.replace(/\x1b\[[0-9;]*m/g, '');
}

// 格式化时间戳
function formatTimestamp(ts) {
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// 格式化持续时间 (毫秒 -> 可读字符串)
function formatDuration(ms) {
    if (ms < 1000) return `${ms}ms`;
    const seconds = (ms / 1000).toFixed(1);
    return `${seconds}s`;
}

// 生成唯一ID
function generateId(prefix = 'id') {
    return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
}

// 深拷贝对象
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 安全的JSON解析
function safeJsonParse(str, defaultValue = null) {
    try {
        return JSON.parse(str);
    } catch (e) {
        return defaultValue;
    }
}

// 复制到剪贴板
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            return true;
        } catch (e) {
            return false;
        } finally {
            document.body.removeChild(textarea);
        }
    }
}

// 滚动到底部
function scrollToBottom(element, smooth = true) {
    if (!element) return;
    element.scrollTo({
        top: element.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
    });
}

// 检查是否滚动到底部附近
function isNearBottom(element, threshold = 100) {
    if (!element) return false;
    return element.scrollHeight - element.scrollTop - element.clientHeight < threshold;
}

// 创建DOM元素的便捷函数
function createElement(tag, className = '', innerHTML = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (innerHTML) el.innerHTML = innerHTML;
    return el;
}

// 格式化Action显示信息
function formatActionForDisplay(actionName, details) {
    const name = (actionName || 'unknown').toLowerCase().replace(/_/g, ' ');
    let displayName = name.charAt(0).toUpperCase() + name.slice(1);
    let target = '';
    let icon = '⚡';
    let cssClass = 'action-default';
    
    // 解析details
    let d = {};
    try {
        d = typeof details === 'string' ? JSON.parse(details) : (details || {});
    } catch (e) {
        d = {};
    }
    
    // 尝试修正 unknown action
    if (name === 'unknown') {
        if (d._metadata === 'finish' || d.type === 'finish') {
            displayName = '完成';
            icon = '✅';
            cssClass = 'action-finish';
            target = d.message || '';
            // 强制覆盖 name 以便后续不进入 default
            // 但 switch 已经过了，所以直接返回
            return { name: displayName, target, icon, cssClass, rawDetails: d };
        }
        if (d.action) {
             // 尝试从 details 中获取 action
             const subName = d.action.toLowerCase();
             if (subName !== 'unknown') {
                 // 递归调用或者手动修正
                 return formatActionForDisplay(subName, details);
             }
        }
    }

    // 根据动作类型设置图标和目标
    switch (name) {
        case 'tap':
        case 'double tap':
        case 'double_tap':
            icon = '👆';
            cssClass = 'action-tap';
            const tapPos = d.element || d.position || [];
            if (Array.isArray(tapPos) && tapPos.length >= 2) {
                target = `(${tapPos[0]}, ${tapPos[1]})`;
            }
            break;
            
        case 'long press':
        case 'long_press':
            icon = '👇';
            cssClass = 'action-tap';
            const longPos = d.element || d.position || [];
            if (Array.isArray(longPos) && longPos.length >= 2) {
                target = `(${longPos[0]}, ${longPos[1]})`;
            }
            break;
            
        case 'swipe':
            icon = '👉';
            cssClass = 'action-swipe';
            const from = d.from || d.start || [];
            const to = d.to || d.end || [];
            if (from.length >= 2 && to.length >= 2) {
                target = `(${from[0]},${from[1]}) → (${to[0]},${to[1]})`;
            }
            break;
            
        case 'type':
            icon = '⌨️';
            cssClass = 'action-type';
            const txt = d.text || '';
            target = txt.length > 30 ? `"${txt.substring(0, 30)}..."` : `"${txt}"`;
            break;
            
        case 'launch':
            icon = '🚀';
            cssClass = 'action-launch';
            target = d.app || d.package || '';
            break;
            
        case 'wait':
            icon = '⏱️';
            cssClass = 'action-wait';
            target = d.duration ? `${d.duration}` : '';
            break;
            
        case 'back':
            icon = '◀️';
            cssClass = 'action-back';
            displayName = '返回';
            break;
            
        case 'home':
            icon = '🏠';
            cssClass = 'action-home';
            displayName = '主屏幕';
            break;
            
        case 'take over':
        case 'take_over':
            icon = '⚠️';
            cssClass = 'action-takeover';
            displayName = '请协助操作';
            target = d.message || '';
            break;
            
        case 'finish':
            icon = '✅';
            cssClass = 'action-finish';
            displayName = '完成';
            target = d.message || '';
            break;
            
        default:
            if (d.message) {
                target = d.message.length > 40 ? d.message.substring(0, 40) + '...' : d.message;
            }
    }
    
    return {
        name: displayName,
        target: target,
        icon: icon,
        cssClass: cssClass,
        rawDetails: d
    };
}

// 导出模块
window.Utils = {
    stripAnsi,
    formatTimestamp,
    formatDuration,
    generateId,
    deepClone,
    debounce,
    throttle,
    safeJsonParse,
    copyToClipboard,
    scrollToBottom,
    isNearBottom,
    createElement,
    formatActionForDisplay
};
