/**
 * Nexus Marketplace - Buyer Dashboard
 * Shared JavaScript for all pages
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // Mobile Menu Toggle
    // ==========================================
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const mobileOverlay = document.getElementById('mobileOverlay');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
            mobileOverlay.classList.toggle('active');
        });
    }
    
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', function() {
            sidebar.classList.remove('open');
            mobileOverlay.classList.remove('active');
        });
    }
    
    // ==========================================
    // Profile Dropdown
    // ==========================================
    const btnProfile = document.getElementById('btnProfile');
    const profileDropdown = document.getElementById('profileDropdown');
    
    if (btnProfile && profileDropdown) {
        btnProfile.addEventListener('click', function(e) {
            e.stopPropagation();
            profileDropdown.classList.toggle('show');
        });
        
        // Close when clicking outside
        document.addEventListener('click', function() {
            profileDropdown.classList.remove('show');
        });
    }
    
    // ==========================================
    // Notification Dropdown
    // ==========================================
    const btnNotification = document.getElementById('btnNotification');
    const notificationDropdown = document.getElementById('notificationDropdown');
    
    if (btnNotification && notificationDropdown) {
        btnNotification.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationDropdown.classList.toggle('show');
        });
        
        document.addEventListener('click', function() {
            notificationDropdown.classList.remove('show');
        });
    }
    
    
    
    
    
    
    
    
     
});