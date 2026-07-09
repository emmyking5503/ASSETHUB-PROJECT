// payment-options.js

document.addEventListener('DOMContentLoaded', function() {
    // ===== Get URL Parameters =====
    // function getUrlParams() {
    //     const params = new URLSearchParams(window.location.search);
    //     return {
    //         product: params.get('product') || 'Sony WH-1000XM4 Wireless Headphones',
    //         price: params.get('price') || '348.00',
    //         fullname: params.get('fullname') || 'John Doe',
    //         phone: params.get('phone') || '',
    //         sellerNumber: params.get('seller') || '1234567890' // Default demo seller number
    //     };
    // }

    // ===== Update Order Summary with URL Parameters =====
    function updateOrderSummary() {
        const params = getUrlParams();
        
        const productNameEl = document.getElementById('productName');
        const productPriceEl = document.getElementById('productPrice');
        const buyerNameEl = document.getElementById('buyerName');
        
        if (productNameEl) {
            productNameEl.textContent = decodeURIComponent(params.product);
        }
        
        if (productPriceEl) {
            // Format price with $ if not already
            const price = params.price.startsWith('$') ? params.price : `$${parseFloat(params.price).toFixed(2)}`;
            productPriceEl.textContent = price;
        }
        
        if (buyerNameEl) {
            buyerNameEl.textContent = decodeURIComponent(params.fullname);
        }
    }

    // ===== Generate WhatsApp Link =====
    function generateWhatsAppLink() {
        const params = getUrlParams();
        
        // Format price
        const formattedPrice = params.price.startsWith('$') ? params.price : `$${parseFloat(params.price).toFixed(2)}`;
        
        // Create the message
        const message = `Hello, I am interested in buying:%0A%0A` +
                       `*Product:* ${decodeURIComponent(params.product)}%0A` +
                       `*Price:* ${formattedPrice}%0A` +
                       `*My Name:* ${decodeURIComponent(params.fullname)}%0A%0A` +
                       `How can I proceed with payment and delivery?`;
        
        // In production, this would be the actual seller's WhatsApp number
        // For demo, we're using a placeholder that can be overridden via URL param
        const sellerNumber = params.sellerNumber.replace(/\D/g, ''); // Remove non-digits
        
        return `https://wa.me/${sellerNumber}?text=${message}`;
    }

    // ===== Set WhatsApp Button Link =====
    function setWhatsAppButton() {
        const whatsappButton = document.getElementById('whatsappButton');
        if (whatsappButton) {
            const whatsappLink = generateWhatsAppLink();
            whatsappButton.href = whatsappLink;
            whatsappButton.target = '_blank'; // Open in new tab
            whatsappButton.rel = 'noopener noreferrer'; // Security best practice
        }
    }

    // ===== Add Click Tracking (Optional) =====
    function addTracking() {
        const whatsappButton = document.getElementById('whatsappButton');
        const secureButton = document.querySelector('.secure-btn');
        
        if (whatsappButton) {
            whatsappButton.addEventListener('click', function(e) {
                console.log('WhatsApp payment option selected', {
                    product: getUrlParams().product,
                    price: getUrlParams().price,
                    timestamp: new Date().toISOString()
                });
                // In production, you might send this to analytics
            });
        }
        
        if (secureButton) {
            secureButton.addEventListener('click', function(e) {
                console.log('Secure P2P payment option selected', {
                    product: getUrlParams().product,
                    price: getUrlParams().price,
                    timestamp: new Date().toISOString()
                });
                // In production, you might send this to analytics
            });
        }
    }

    // ===== Add Hover Effects Enhancement =====
    function enhanceHoverEffects() {
        const cards = document.querySelectorAll('.payment-card');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                const icon = this.querySelector('.card-icon');
                if (icon) {
                    icon.style.transition = 'all 0.3s ease';
                }
            });
        });
    }

    // ===== Validate URL Parameters =====
    function validateParams() {
        const params = getUrlParams();
        const errors = [];
        
        if (!params.product || params.product === 'null') {
            errors.push('Product name is missing');
        }
        
        if (!params.price || params.price === 'null') {
            errors.push('Product price is missing');
        }
        
        if (!params.fullname || params.fullname === 'null') {
            errors.push('Buyer name is missing');
        }
        
        if (errors.length > 0) {
            console.warn('Missing checkout parameters:', errors);
            // Could show a subtle warning to the user
            const orderSummary = document.getElementById('orderSummary');
            if (orderSummary) {
                orderSummary.style.borderColor = 'var(--warning)';
                
                // Add a small tooltip or indicator
                const warningIcon = document.createElement('div');
                warningIcon.className = 'param-warning';
                warningIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                warningIcon.style.cssText = `
                    position: absolute;
                    top: -10px;
                    right: -10px;
                    background: var(--warning);
                    color: white;
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.8rem;
                `;
                orderSummary.style.position = 'relative';
                orderSummary.appendChild(warningIcon);
                
                // Remove after 3 seconds
                setTimeout(() => {
                    if (warningIcon.parentNode) {
                        warningIcon.remove();
                    }
                }, 3000);
            }
        }
    }

    // ===== Initialize Page =====
    function init() {
        console.log('Payment options page initialized');
        
        // Update order summary with URL params
        updateOrderSummary();
        
        // Generate and set WhatsApp link
        setWhatsAppButton();
        
        // Validate parameters (for debugging)
        validateParams();
        
        // Add tracking (optional)
        addTracking();
        
        // Enhance hover effects
        enhanceHoverEffects();
        
        // Log for demo purposes
        const params = getUrlParams();
        console.log('Checkout data received:', {
            product: decodeURIComponent(params.product),
            price: params.price,
            buyer: decodeURIComponent(params.fullname),
            whatsappLink: generateWhatsAppLink()
        });
    }

    // Start everything
    init();
});