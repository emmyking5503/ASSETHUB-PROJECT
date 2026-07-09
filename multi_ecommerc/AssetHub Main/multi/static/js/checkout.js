// checkout.js

document.addEventListener('DOMContentLoaded', function() {
    // ===== State Variables =====
    const serviceFeeRate = 0.025; // 2.5%
    
    // ===== DOM Elements =====
    const cartItems = document.querySelectorAll('.cart-item');
    const subtotalAmount = document.getElementById('subtotalAmount');
    const serviceFeeElement = document.getElementById('serviceFee');
    const totalAmount = document.getElementById('totalAmount');
    const subtotalItemCount = document.getElementById('subtotalItemCount');
    const itemCount = document.getElementById('itemCount');
    const hiddenItems = document.getElementById('hiddenItems');
    const hiddenTotal = document.getElementById('hiddenTotal');
    
    // ===== Initialize Quantity Controls =====
    function initializeQuantityControls() {
        cartItems.forEach(item => {
            const minusBtn = item.querySelector('.qty-minus');
            const plusBtn = item.querySelector('.qty-plus');
            const qtyInput = item.querySelector('.qty-input');
            
            if (minusBtn && plusBtn && qtyInput) {
                // Remove any existing listeners to prevent duplicates
                minusBtn.removeEventListener('click', handleMinusClick);
                plusBtn.removeEventListener('click', handlePlusClick);
                
                // Add fresh listeners
                minusBtn.addEventListener('click', handleMinusClick);
                plusBtn.addEventListener('click', handlePlusClick);
            }
        });
    }
    
    // ===== Event Handlers =====
    function handleMinusClick(e) {
        const btn = e.currentTarget;
        const item = btn.closest('.cart-item');
        const qtyInput = item.querySelector('.qty-input');
        const currentValue = parseInt(qtyInput.value) || 1;
        
        if (currentValue > 1) {
            qtyInput.value = currentValue - 1;
            animateButton(btn);
            updateItemSubtotal(item);
            updateCartTotals();
        }
    }
    
    function handlePlusClick(e) {
        const btn = e.currentTarget;
        const item = btn.closest('.cart-item');
        const qtyInput = item.querySelector('.qty-input');
        const currentValue = parseInt(qtyInput.value) || 1;
        const max = parseInt(qtyInput.getAttribute('max')) || 10;
        
        if (currentValue < max) {
            qtyInput.value = currentValue + 1;
            animateButton(btn);
            updateItemSubtotal(item);
            updateCartTotals();
        }
    }
    
    // ===== Animation Functions =====
    function animateButton(btn) {
        btn.style.transform = 'scale(0.9)';
        setTimeout(() => {
            btn.style.transform = 'scale(1)';
        }, 100);
    }
    
    function animatePrice(element) {
        element.classList.add('updating');
        setTimeout(() => {
            element.classList.remove('updating');
        }, 200);
    }
    
   
    
    // ===== Notification System =====
    function showNotification(message, type = 'info') {
        // Remove existing notification
        const existingNotification = document.querySelector('.checkout-notification');
        if (existingNotification) {
            existingNotification.remove();
        }
        
        // Create notification
        const notification = document.createElement('div');
        notification.className = `checkout-notification notification-${type}`;
        
        const icon = type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle';
        const bgColor = type === 'error' ? 'var(--error)' : 'var(--accent)';
        
        notification.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${message}</span>
        `;
        
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: ${bgColor};
            color: white;
            padding: 12px 24px;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-lg);
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 9999;
            animation: slideInRight 0.3s ease;
            font-family: var(--font-sans);
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
    
    // ===== Add CSS Animations =====
    function addAnimationStyles() {
        if (!document.querySelector('#checkout-animations')) {
            const style = document.createElement('style');
            style.id = 'checkout-animations';
            style.textContent = `
                @keyframes priceUpdate {
                    0% { transform: scale(1); color: var(--text-primary); }
                    50% { transform: scale(1.05); color: var(--accent); }
                    100% { transform: scale(1); color: var(--text-primary); }
                }
                
                @keyframes slideInRight {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                
                @keyframes slideOutRight {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
                
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                    20%, 40%, 60%, 80% { transform: translateX(5px); }
                }
                
                .summary-value.updating,
                .total-value.updating,
                .subtotal-amount.updating {
                    animation: priceUpdate 0.3s ease;
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    // ===== Initialize =====
    function init() {
        initializeQuantityControls();
        addAnimationStyles();
        
        // Initial cart totals calculation
        updateCartTotals();
        
        console.log('Checkout initialized with quantity controls');
    }
    
    // Start everything
    init();
});