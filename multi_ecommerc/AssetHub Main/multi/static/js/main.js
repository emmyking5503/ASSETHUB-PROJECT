// ============================================
// NEXUS SELLER DASHBOARD - MAIN JAVASCRIPT
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const mobileOverlay = document.getElementById('mobileOverlay');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
            mobileOverlay.classList.toggle('show');
        });
    }
    
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', function() {
            sidebar.classList.remove('open');
            mobileOverlay.classList.remove('show');
        });
    }
    
    // Profile Dropdown
    const profileBtn = document.getElementById('profileBtn');
    const profileDropdown = document.getElementById('profileDropdown');
    
    if (profileBtn) {
        profileBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            profileDropdown.classList.toggle('show');
        });
    }
    
    // Notification Dropdown
    const notifBtn = document.getElementById('notifBtn');
    const notifDropdown = document.getElementById('notifDropdown');
    
    if (notifBtn) {
        notifBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            notifDropdown.classList.toggle('show');
        });
    }
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function() {
        if (profileDropdown) profileDropdown.classList.remove('show');
        if (notifDropdown) notifDropdown.classList.remove('show');
    });
    
   
    
    // Product View Toggle (Grid/List)
    const btnGrid = document.getElementById('btnGrid');
    const btnList = document.getElementById('btnList');
    const productGrid = document.getElementById('productGrid');
    const productList = document.getElementById('productList');
    
    if (btnGrid && btnList) {
        btnGrid.addEventListener('click', function() {
            productGrid.style.display = 'grid';
            productList.style.display = 'none';
            btnGrid.classList.add('active');
            btnList.classList.remove('active');
        });
        
        btnList.addEventListener('click', function() {
            productGrid.style.display = 'none';
            productList.style.display = 'block';
            btnList.classList.add('active');
            btnGrid.classList.remove('active');
        });
    }
    
    // Order Status Updates
    window.updateOrderStatus = function(btn, newStatus) {
        const card = btn.closest('.order-card');
        const badge = card.querySelector('.badge');
        
        // Update badge
        badge.textContent = newStatus;
        badge.className = 'badge';
        
        switch(newStatus) {
            case 'Processing':
                badge.classList.add('badge-processing');
                btn.textContent = 'Mark as Shipped';
                btn.onclick = function() { updateOrderStatus(this, 'Shipped'); };
                break;
            case 'Shipped':
                badge.classList.add('badge-shipped');
                btn.textContent = 'Mark as Delivered';
                btn.onclick = function() { updateOrderStatus(this, 'Delivered'); };
                break;
            case 'Delivered':
                badge.classList.add('badge-awaiting');
                badge.textContent = 'Awaiting Confirmation';
                btn.remove();
                break;
            case 'Completed':
                badge.classList.add('badge-completed');
                btn.remove();
                break;
        }
    };
    
    // Review Reply Toggle
    window.toggleReply = function(btn) {
        const reviewCard = btn.closest('.review-card');
        const replyForm = reviewCard.querySelector('.reply-form');
        replyForm.classList.toggle('show');
    };
    
    // Submit Reply
    window.submitReply = function(btn) {
        const form = btn.closest('.reply-form');
        const textarea = form.querySelector('textarea');
        if (textarea.value.trim()) {
            alert('Reply submitted: ' + textarea.value);
            textarea.value = '';
            form.classList.remove('show');
        }
    };
    
    // Simulate Withdraw
    window.simulateWithdraw = function() {
        const amount = prompt('Enter amount to withdraw:');
        if (amount && !isNaN(amount)) {
            alert('Withdrawal request of $' + amount + ' submitted successfully!');
        }
    };
    
    
});