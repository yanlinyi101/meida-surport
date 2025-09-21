/**
 * 美大客服支持中心 - 前端交互脚本
 */

// 当文档加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 搜索功能
    initSearch();
    
    // 表单验证
    initFormValidation();
});

/**
 * 初始化搜索功能
 */
function initSearch() {
    // 产品搜索
    const productSearch = document.getElementById('product-search');
    if (productSearch) {
        const productCards = document.querySelectorAll('.product-card');
        const noResults = document.getElementById('no-results');
        
        productSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            let hasResults = false;
            
            productCards.forEach(card => {
                const productName = card.getAttribute('data-name').toLowerCase();
                const productPinyin = card.getAttribute('data-pinyin').toLowerCase();
                
                if (productName.includes(searchTerm) || productPinyin.includes(searchTerm)) {
                    card.style.display = '';
                    hasResults = true;
                } else {
                    card.style.display = 'none';
                }
            });
            
            // 显示或隐藏无结果提示
            if (noResults) {
                if (hasResults || searchTerm === '') {
                    noResults.classList.remove('show');
                } else {
                    noResults.classList.add('show');
                }
            }
        });
    }
    
    // 问题搜索
    const issueSearch = document.getElementById('issue-search');
    if (issueSearch) {
        const issueCards = document.querySelectorAll('.issue-card');
        const noResults = document.getElementById('no-results');
        
        issueSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            let hasResults = false;
            
            issueCards.forEach(card => {
                const issueTitle = card.getAttribute('data-title').toLowerCase();
                
                if (issueTitle.includes(searchTerm)) {
                    card.style.display = '';
                    hasResults = true;
                } else {
                    card.style.display = 'none';
                }
            });
            
            // 显示或隐藏无结果提示
            if (noResults) {
                if (hasResults || searchTerm === '') {
                    noResults.classList.remove('show');
                } else {
                    noResults.classList.add('show');
                }
            }
        });
    }
}

/**
 * 初始化表单验证
 */
function initFormValidation() {
    const serviceForm = document.getElementById('service-form');
    if (serviceForm) {
        const errorMessage = document.getElementById('error-message');
        const successMessage = document.getElementById('success-message');
        const errorText = document.getElementById('error-text');
        
        // 如果页面中没有错误和成功消息元素，则使用alert作为后备
        const useAlert = !errorMessage || !successMessage || !errorText;
        
        // 隐藏提示消息的函数
        function hideMessages() {
            if (!useAlert) {
                errorMessage.classList.add('hidden');
                successMessage.classList.add('hidden');
            }
        }
        
        // 显示错误消息的函数
        function showError(message) {
            if (useAlert) {
                alert(message);
            } else {
                hideMessages();
                errorText.textContent = message;
                errorMessage.classList.remove('hidden');
                errorMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        // 显示成功消息的函数
        function showSuccess() {
            if (useAlert) {
                alert('预约成功！我们的客服将尽快与您联系确认详情。');
            } else {
                hideMessages();
                successMessage.classList.remove('hidden');
                successMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        // 清除输入框错误状态的函数
        function clearFieldError(field) {
            field.classList.remove('border-red-500');
            field.classList.add('border-gray-300');
        }
        
        // 设置输入框错误状态的函数
        function setFieldError(field) {
            field.classList.remove('border-gray-300');
            field.classList.add('border-red-500');
            field.focus();
        }
        
        // 为所有输入框添加输入事件监听器，清除错误状态
        const inputs = serviceForm.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                clearFieldError(this);
                hideMessages();
            });
        });
        
        serviceForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 清除之前的错误状态
            inputs.forEach(input => clearFieldError(input));
            hideMessages();
            
            // 验证姓名
            const nameInput = document.getElementById('name');
            if (!nameInput.value.trim()) {
                showError('请输入您的姓名');
                setFieldError(nameInput);
                return;
            }
            
            // 验证电话
            const phoneInput = document.getElementById('phone');
            const phoneValue = phoneInput.value.trim();
            if (!phoneValue) {
                showError('请输入联系电话');
                setFieldError(phoneInput);
                return;
            }
            if (!/^1[3-9]\d{9}$/.test(phoneValue)) {
                showError('请输入有效的11位手机号码');
                setFieldError(phoneInput);
                return;
            }
            
            // 验证地址
            const addressInput = document.getElementById('address');
            if (!addressInput.value.trim()) {
                showError('请输入您的地址');
                setFieldError(addressInput);
                return;
            }
            
            // 验证日期
            const dateInput = document.getElementById('date');
            if (!dateInput.value) {
                showError('请选择预约日期');
                setFieldError(dateInput);
                return;
            }
            
            // 验证日期是否为今天或未来日期
            const selectedDate = new Date(dateInput.value);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            if (selectedDate < today) {
                showError('预约日期不能早于今天');
                setFieldError(dateInput);
                return;
            }
            
            // 提交成功
            showSuccess();
            
            // 延迟清空表单，让用户看到成功消息
            setTimeout(() => {
                serviceForm.reset();
                hideMessages();
            }, useAlert ? 0 : 3000);
        });
    }
} 