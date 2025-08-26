/**
 * 美大客服支持中心 - 前端交互脚本
 */

// 等待 DOM 加载完成
document.addEventListener('DOMContentLoaded', function() {
    // 产品搜索功能
    initProductSearch();
    
    // 故障代码搜索功能
    initIssueSearch();
    
    // 键盘导航
    initKeyboardNavigation();
    
    // 返回按钮
    initBackButton();

    // 预约表单处理
    initAppointmentForm();
});

/**
 * 初始化产品搜索功能
 */
function initProductSearch() {
    const searchInput = document.getElementById('product-search');
    if (!searchInput) return;
    
    const productsGrid = document.getElementById('products-grid');
    const productCards = document.querySelectorAll('.product-card');
    const noResults = document.getElementById('no-results');
    const resetButton = document.getElementById('reset-search');
    
    // 搜索功能
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.trim().toLowerCase();
        let hasResults = false;
        
        productCards.forEach(card => {
            const productName = card.getAttribute('data-name').toLowerCase();
            const pinyinInitials = getPinyinInitials(productName);
            
            // 匹配产品名称或拼音首字母
            if (productName.includes(searchTerm) || pinyinInitials.includes(searchTerm)) {
                card.classList.remove('hidden');
                hasResults = true;
            } else {
                card.classList.add('hidden');
            }
        });
        
        // 显示/隐藏无结果提示
        if (hasResults) {
            noResults.classList.add('hidden');
            productsGrid.classList.remove('hidden');
        } else {
            noResults.classList.remove('hidden');
            productsGrid.classList.add('hidden');
        }
    });
    
    // 重置搜索
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            searchInput.value = '';
            productCards.forEach(card => card.classList.remove('hidden'));
            noResults.classList.add('hidden');
            productsGrid.classList.remove('hidden');
            searchInput.focus();
        });
    }
}

/**
 * 获取中文字符的拼音首字母（简易实现）
 * 注意：这是一个简化版，只包含常见汉字
 */
function getPinyinInitials(text) {
    // 常见汉字首字母映射
    const pinyinMap = {
        '集': 'j', '成': 'c', '灶': 'z', '油': 'y', '烟': 'y', '机': 'j',
        '具': 'j', '消': 'x', '毒': 'd', '柜': 'g', '热': 'r', '水': 's', '器': 'q'
    };
    
    let initials = '';
    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        if (pinyinMap[char]) {
            initials += pinyinMap[char];
        }
    }
    
    return initials;
}

/**
 * 初始化故障代码搜索功能
 */
function initIssueSearch() {
    const searchInput = document.getElementById('issue-search');
    if (!searchInput) return;
    
    const issuesGrid = document.getElementById('issues-grid');
    const issueCards = document.querySelectorAll('.issue-card');
    
    // 搜索功能
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.trim().toLowerCase();
        let hasResults = false;
        
        issueCards.forEach(card => {
            const issueCode = card.getAttribute('data-issue-code').toLowerCase();
            const issueTitle = card.getAttribute('data-issue-title').toLowerCase();
            
            // 匹配故障代码或标题
            if (issueCode.includes(searchTerm) || issueTitle.includes(searchTerm)) {
                card.classList.remove('hidden');
                hasResults = true;
            } else {
                card.classList.add('hidden');
            }
        });
        
        // 显示/隐藏无结果提示
        if (hasResults) {
            // 如果有匹配结果，确保网格可见
            if (issuesGrid) {
                issuesGrid.classList.remove('hidden');
            }
            
            // 隐藏无结果提示（如果存在）
            if (document.getElementById('no-issue-results')) {
                document.getElementById('no-issue-results').classList.add('hidden');
            }
        } else {
            // 如果没有匹配结果，可以添加一个无结果提示
            if (issuesGrid && issueCards.length > 0) {
                // 只有在有卡片的情况下才考虑显示无结果提示
                if (!document.getElementById('no-issue-results')) {
                    const noResults = document.createElement('div');
                    noResults.id = 'no-issue-results';
                    noResults.className = 'text-center py-4 text-gray-500';
                    noResults.textContent = '未找到匹配的故障代码';
                    issuesGrid.parentNode.insertBefore(noResults, issuesGrid.nextSibling);
                } else {
                    document.getElementById('no-issue-results').classList.remove('hidden');
                }
                issuesGrid.classList.add('hidden');
            }
        }
    });
}

/**
 * 初始化键盘导航
 */
function initKeyboardNavigation() {
    // 产品卡片键盘导航
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach(card => {
        card.addEventListener('keydown', function(e) {
            // 回车键触发点击
            if (e.key === 'Enter') {
                e.preventDefault();
                this.click();
            }
        });
    });
    
    // 问题列表键盘导航
    const issueItems = document.querySelectorAll('[data-issue-code]');
    issueItems.forEach(item => {
        item.addEventListener('keydown', function(e) {
            // 回车键触发点击
            if (e.key === 'Enter') {
                e.preventDefault();
                this.click();
            }
        });
    });
}

/**
 * 初始化返回按钮功能
 */
function initBackButton() {
    // 监听浏览器返回按钮
    window.addEventListener('popstate', function(event) {
        if (event.state && event.state.page) {
            // 可以在这里处理特定页面的返回逻辑
        }
    });
    
    // 问题页面的返回按钮
    const backToProducts = document.querySelector('a[href="/"]');
    if (backToProducts) {
        backToProducts.addEventListener('click', function(e) {
            // 如果需要特殊处理返回逻辑，可以在这里添加
        });
    }
}

/**
 * 初始化预约表单
 */
function initAppointmentForm() {
    const appointmentForm = document.getElementById('appointment-form');
    if (!appointmentForm) return;

    // 设置日期选择器最小日期为今天
    const dateInput = document.getElementById('date');
    if (dateInput) {
        // 日期选择器已经在服务端设置了 min 属性

        // 增强日期选择体验
        dateInput.addEventListener('change', function() {
            validateDate(this);
        });
    }

    // 表单提交处理
    appointmentForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 表单验证
        if (validateForm()) {
            // 收集表单数据
            const formData = {
                phone: document.getElementById('phone').value,
                name: document.getElementById('name').value,
                address: document.getElementById('address').value,
                date: document.getElementById('date').value,
                timeSlot: document.getElementById('time-slot').value,
                notes: document.getElementById('notes').value,
                productSlug: window.location.pathname.split('/')[2],
                issueCode: window.location.pathname.split('/')[3]
            };
            
            // 模拟表单提交
            console.log('预约信息：', formData);
            
            // 显示成功消息
            showSuccessMessage();
            
            // 清空表单
            appointmentForm.reset();
        }
    });

    // 电话号码输入验证
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function() {
            validatePhone(this);
        });
    }
}

/**
 * 验证表单
 */
function validateForm() {
    let isValid = true;
    
    // 验证手机号
    const phoneInput = document.getElementById('phone');
    if (!validatePhone(phoneInput)) {
        isValid = false;
    }
    
    // 验证地址
    const addressInput = document.getElementById('address');
    if (!addressInput.value.trim()) {
        showError(addressInput, '请输入地址');
        isValid = false;
    } else {
        clearError(addressInput);
    }
    
    // 验证日期
    const dateInput = document.getElementById('date');
    if (!validateDate(dateInput)) {
        isValid = false;
    }
    
    // 验证时间段
    const timeSlotInput = document.getElementById('time-slot');
    if (!timeSlotInput.value) {
        showError(timeSlotInput, '请选择时间段');
        isValid = false;
    } else {
        clearError(timeSlotInput);
    }
    
    return isValid;
}

/**
 * 验证手机号
 */
function validatePhone(input) {
    const phoneRegex = /^1[3-9]\d{9}$/;
    const value = input.value.trim();
    
    if (!value) {
        showError(input, '请输入手机号');
        return false;
    } else if (!phoneRegex.test(value)) {
        showError(input, '请输入有效的11位手机号');
        return false;
    } else {
        clearError(input);
        return true;
    }
}

/**
 * 验证日期
 */
function validateDate(input) {
    const selectedDate = new Date(input.value);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (!input.value) {
        showError(input, '请选择日期');
        return false;
    } else if (selectedDate < today) {
        showError(input, '请选择今天或之后的日期');
        return false;
    } else {
        clearError(input);
        return true;
    }
}

/**
 * 显示表单错误
 */
function showError(input, message) {
    // 清除可能存在的错误
    clearError(input);
    
    // 创建错误消息元素
    const errorDiv = document.createElement('div');
    errorDiv.className = 'text-red-500 text-sm mt-1 error-message';
    errorDiv.textContent = message;
    
    // 在输入框后插入错误消息
    input.parentNode.appendChild(errorDiv);
    
    // 添加错误样式
    input.classList.add('border-red-500');
    input.classList.add('focus:border-red-500');
    input.classList.add('focus:ring-red-500');
}

/**
 * 清除表单错误
 */
function clearError(input) {
    // 移除错误消息
    const parent = input.parentNode;
    const errorMessages = parent.querySelectorAll('.error-message');
    errorMessages.forEach(el => el.remove());
    
    // 移除错误样式
    input.classList.remove('border-red-500');
    input.classList.remove('focus:border-red-500');
    input.classList.remove('focus:ring-red-500');
}

/**
 * 显示成功消息
 */
function showSuccessMessage() {
    const successMessage = document.getElementById('success-message');
    if (successMessage) {
        // 显示成功消息
        successMessage.classList.remove('hidden');
        
        // 滚动到成功消息
        successMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // 5秒后隐藏成功消息
        setTimeout(() => {
            successMessage.classList.add('hidden');
        }, 5000);
    }
} 