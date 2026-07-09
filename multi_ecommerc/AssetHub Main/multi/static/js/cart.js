// cart.js

document.addEventListener('DOMContentLoaded', function() {
    // ===== DOM Elements =====
    const cartItems = document.querySelectorAll('.cart-item');
    const emptyCart = document.getElementById('emptyCart');
    const cartItemsContainer = document.getElementById('cartItems');
    
    // Service fee rate
    const SERVICE_FEE_RATE = 0.025; // 2.5%

    // ===== Initialize =====
    function init() {
        updateAllPrices();
        updateMinusButtons();
    }

    // ===== Quantity Controls =====
    document.querySelectorAll('.qty-btn.plus').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            const input = document.querySelector(`.qty-input[data-id="${id}"]`);
            const currentValue = parseInt(input.value);
            const max = parseInt(input.getAttribute('max') || 10);
            
            if (currentValue < max) {
                input.value = currentValue + 1;
                updateItemSubtotal(id);
                updateAllPrices();
                updateMinusButtons();
                
                // Animate the button
                animateButton(this);
            }
        });
    });

    document.querySelectorAll('.qty-btn.minus').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            const input = document.querySelector(`.qty-input[data-id="${id}"]`);
            const currentValue = parseInt(input.value);
            
            if (currentValue > 1) {
                input.value = currentValue - 1;
                updateItemSubtotal(id);
                updateAllPrices();
                updateMinusButtons();
                
                // Animate the button
                animateButton(this);
            }
        });
    });

    // ===== Update Minus Buttons State =====
    function updateMinusButtons() {
        document.querySelectorAll('.cart-item').forEach(item => {
            const id = item.dataset.id;
            const input = document.querySelector(`.qty-input[data-id="${id}"]`);
            const minusBtn = item.querySelector('.qty-btn.minus');
            
            if (input && minusBtn) {
                minusBtn.disabled = parseInt(input.value) <= 1;
            }
        });
    }

    // ===== Check if Cart is Empty =====
    function checkEmptyCart() {
        const items = document.querySelectorAll('.cart-item');
        
        if (items.length === 0) {
            cartItemsContainer.classList.add('hidden');
            emptyCart.classList.remove('hidden');
        } else {
            cartItemsContainer.classList.remove('hidden');
            emptyCart.classList.add('hidden');
        }
    }

    // ===== Animation Functions =====
    function animateButton(btn) {
        btn.style.transform = 'scale(0.9)';
        setTimeout(() => {
            btn.style.transform = 'scale(1)';
        }, 100);
    }

    function animateValue(element) {
        element.style.transform = 'scale(1.05)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }

    // ===== Notification System =====
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification`;
        
        const icon = type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
        const bgColor = type === 'success' ? '#059669' : '#2563eb';
        
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
            border-radius: 40px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 9999;
            animation: slideIn 0.3s ease;
            font-family: 'Inter', sans-serif;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideIn 0.3s reverse';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // ===== Promo Code (UI Demo) =====
    document.querySelector('.promo-btn').addEventListener('click', function() {
        const input = document.querySelector('.promo-input');
        if (input.value.trim()) {
            showNotification('Promo code applied! (Demo)', 'success');
            input.value = '';
        } else {
            showNotification('Please enter a promo code', 'info');
        }
    });

    // ===== Add Animation Styles =====
    function addAnimationStyles() {
        if (!document.querySelector('#cart-animations')) {
            const style = document.createElement('style');
            style.id = 'cart-animations';
            style.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // ===== Initialize Everything =====
    init();
    addAnimationStyles();
});