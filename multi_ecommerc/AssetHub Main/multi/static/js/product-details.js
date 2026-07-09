
    // Mobile Menu
    const mobileMenu = document.getElementById('mobileMenu');
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const closeMobileMenu = document.getElementById('closeMobileMenu');

    function toggleMenu() {
        mobileMenu.classList.toggle('active');
        document.body.style.overflow = mobileMenu.classList.contains('active') ? 'hidden' : '';
    }

    mobileMenuToggle.addEventListener('click', toggleMenu);
    closeMobileMenu.addEventListener('click', toggleMenu);
    mobileMenu.addEventListener('click', (e) => {
        if (e.target === mobileMenu) toggleMenu();
    });

    // Mobile Search Toggle
    const mobileSearchToggle = document.getElementById('mobileSearchToggle');
    const navSearch = document.getElementById('navSearch');
    
    mobileSearchToggle.addEventListener('click', () => {
        navSearch.classList.toggle('active');
        if (navSearch.classList.contains('active')) {
            navSearch.querySelector('input').focus();
        }
    });

    // Close search when clicking outside
    document.addEventListener('click', (e) => {
        if (!navSearch.contains(e.target) && !mobileSearchToggle.contains(e.target)) {
            navSearch.classList.remove('active');
        }
    });

    // Image Gallery
    const mainImage = document.getElementById('mainProductImage');
    const thumbnails = document.querySelectorAll('.thumbnail');
    const zoomBtn = document.getElementById('zoomBtn');
    let isZoomed = false;

    thumbnails.forEach(thumb => {
        thumb.addEventListener('click', function() {
            const newSrc = this.src.replace('w=200', 'w=800');
            mainImage.style.opacity = '0';
            setTimeout(() => {
                mainImage.src = newSrc;
                mainImage.style.opacity = '1';
            }, 200);
            
            thumbnails.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Zoom functionality
    zoomBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        isZoomed = !isZoomed;
        mainImage.classList.toggle('zoomed');
        this.querySelector('i').className = isZoomed ? 'fas fa-search-minus' : 'fas fa-search-plus';
    });

    document.getElementById('mainImageContainer').addEventListener('click', function() {
        if (window.innerWidth < 1024) {
            isZoomed = !isZoomed;
            mainImage.classList.toggle('zoomed');
            zoomBtn.querySelector('i').className = isZoomed ? 'fas fa-search-minus' : 'fas fa-search-plus';
        }
    });

    document.getElementById('mainImageContainer').addEventListener('mousemove', function(e) {
        if (!isZoomed) return;
        const rect = this.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        mainImage.style.transformOrigin = `${x}% ${y}%`;
    });

    // Reset zoom on mouse leave (desktop only)
    if (window.matchMedia('(hover: hover)').matches) {
        document.getElementById('mainImageContainer').addEventListener('mouseleave', function() {
            if (isZoomed) {
                isZoomed = false;
                mainImage.classList.remove('zoomed');
                zoomBtn.querySelector('i').className = 'fas fa-search-plus';
            }
        });
    }

    // Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            this.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
            
            history.pushState(null, null, `#${tabId}`);
        });
    });

    // Quantity Selector
    const quantityInput = document.getElementById('quantity');
    document.getElementById('incrementQty').addEventListener('click', () => {
        const val = parseInt(quantityInput.value);
        if (val < 10) quantityInput.value = val + 1;
    });
    document.getElementById('decrementQty').addEventListener('click', () => {
        const val = parseInt(quantityInput.value);
        if (val > 1) quantityInput.value = val - 1;
    });

    // Wishlist
    const wishlistBtns = document.querySelectorAll('.wishlist, .wishlist-card');
    wishlistBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            this.classList.toggle('active');
            const icon = this.querySelector('i');
            if (this.classList.contains('active')) {
                icon.className = 'fas fa-heart';
                showNotification('Added to wishlist!', 'success');
            } else {
                icon.className = 'far fa-heart';
                showNotification('Removed from wishlist', 'info');
            }
        });
    });

    // Carousel
    function scrollCarousel(trackId, direction) {
        const track = document.getElementById(trackId);
        const scrollAmount = 300;
        track.scrollBy({ left: direction * scrollAmount, behavior: 'smooth' });
    }

    // Scroll to Top
    const scrollBtn = document.getElementById('scrollToTop');
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollBtn.classList.add('visible');
        } else {
            scrollBtn.classList.remove('visible');
        }
    });
    scrollBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Notification System
    function showNotification(message, type = 'info') {
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = 'notification';
        
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        
        notification.innerHTML = `
            <i class="fas ${icons[type]}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }

    // Add to Cart
    document.getElementById('addToCart').addEventListener('click', function() {
        const btn = this;
        const originalContent = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
        btn.disabled = true;
        
        setTimeout(() => {
            btn.innerHTML = originalContent;
            btn.disabled = false;
            const cartCount = document.querySelector('.cart-count');
            cartCount.textContent = parseInt(cartCount.textContent) + parseInt(quantityInput.value);
            showNotification('Added to cart successfully!', 'success');
        }, 800);
    });

    // Buy Now
    document.getElementById('buyNow').addEventListener('click', function() {
        showNotification('Redirecting to checkout...', 'info');
    });

    // Newsletter
    document.getElementById('newsletterForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const btn = this.querySelector('button');
        const input = this.querySelector('input');
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        setTimeout(() => {
            btn.textContent = 'Subscribed!';
            input.value = '';
            showNotification('Successfully subscribed!', 'success');
            setTimeout(() => btn.textContent = 'Subscribe', 2000);
        }, 1000);
    });

    // Helpful buttons
    document.querySelectorAll('.helpful-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.classList.toggle('active');
            const icon = this.querySelector('i');
            if (this.classList.contains('active')) {
                icon.className = 'fas fa-thumbs-up';
            } else {
                icon.className = 'far fa-thumbs-up';
            }
        });
    });

    // Load more reviews
    document.querySelector('.load-more-btn')?.addEventListener('click', function() {
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        setTimeout(() => {
            this.innerHTML = 'Load more reviews <i class="fas fa-chevron-down"></i>';
            showNotification('More reviews loaded', 'success');
        }, 1000);
    });

    // Keyboard navigation for images
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            const activeThumb = document.querySelector('.thumbnail.active');
            const thumbs = Array.from(thumbnails);
            const currentIndex = thumbs.indexOf(activeThumb);
            
            if (e.key === 'ArrowLeft' && currentIndex > 0) {
                thumbs[currentIndex - 1].click();
            } else if (e.key === 'ArrowRight' && currentIndex < thumbs.length - 1) {
                thumbs[currentIndex + 1].click();
            }
        }
    });

    // Check URL hash for tabs
    if (window.location.hash) {
        const hash = window.location.hash.substring(1);
        const tab = document.querySelector(`[data-tab="${hash}"]`);
        if (tab) tab.click();
    }

    // Touch swipe for carousels
    let touchStartX = 0;
    let touchEndX = 0;

    document.querySelectorAll('.carousel-track').forEach(track => {
        track.addEventListener('touchstart', e => {
            touchStartX = e.changedTouches[0].screenX;
        }, {passive: true});

        track.addEventListener('touchend', e => {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe(track);
        }, {passive: true});
    });

    function handleSwipe(track) {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                track.scrollBy({ left: 300, behavior: 'smooth' });
            } else {
                track.scrollBy({ left: -300, behavior: 'smooth' });
            }
        }
    }
