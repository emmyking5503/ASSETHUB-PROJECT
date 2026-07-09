/**
 * Login page JavaScript
 * Password toggle functionality only - validation handled by Django
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get all password toggle buttons
    const toggleButtons = document.querySelectorAll('.password-toggle');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Find the password input in the same parent
            const passwordField = this.previousElementSibling;
            
            if (passwordField && passwordField.type === 'password') {
                passwordField.type = 'text';
                this.querySelector('i').classList.remove('fa-eye');
                this.querySelector('i').classList.add('fa-eye-slash');
            } else if (passwordField) {
                passwordField.type = 'password';
                this.querySelector('i').classList.remove('fa-eye-slash');
                this.querySelector('i').classList.add('fa-eye');
            }
        });
    });
    
    // Add floating animation variations for products
    const products = document.querySelectorAll('.floating-product');
    
    products.forEach((product, index) => {
        // Random slight variations to animation timing
        const duration = 7 + (index * 0.5);
        product.style.animationDuration = `${duration}s`;
    });
    
    // Parallax effect on mouse move for floating products (desktop only)
    if (window.innerWidth > 900) {
        const showcaseSide = document.querySelector('.showcase-side');
        
        showcaseSide.addEventListener('mousemove', (e) => {
            const rect = showcaseSide.getBoundingClientRect();
            const mouseX = (e.clientX - rect.left) / rect.width - 0.5;
            const mouseY = (e.clientY - rect.top) / rect.height - 0.5;
            
            products.forEach((product, index) => {
                const speed = (index + 1) * 15;
                const x = mouseX * speed;
                const y = mouseY * speed;
                
                product.style.transform = `translate(${x}px, ${y}px) scale(1)`;
            });
        });
        
        showcaseSide.addEventListener('mouseleave', () => {
            products.forEach(product => {
                product.style.transform = '';
            });
        });
    }
    
    // Add focus effects for form inputs
    const formInputs = document.querySelectorAll('.form-input');
    
    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });
    
    // Social login buttons (demo only)
    const socialButtons = document.querySelectorAll('.social-btn');
    
    socialButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            // In production, this would trigger OAuth flow
            console.log('Social login clicked:', this.classList.contains('google') ? 'Google' : 'Apple');
        });
    });
    
    // Smooth scroll to form on mobile if URL has hash
    if (window.location.hash === '#login' && window.innerWidth <= 900) {
        setTimeout(() => {
            document.querySelector('.form-side').scrollIntoView({ 
                behavior: 'smooth' 
            });
        }, 100);
    }
    
    // Add animation on form submit (visual feedback only)
    const loginForm = document.querySelector('.login-form');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            // Don't prevent default - let Django handle it
            // Just add a loading animation to the button
            const submitBtn = this.querySelector('.submit-btn');
            const btnText = submitBtn.querySelector('span');
            const btnIcon = submitBtn.querySelector('i');
            
            btnText.textContent = 'Signing in...';
            btnIcon.className = 'fas fa-circle-notch fa-spin';
            
            // In production, the form will submit normally
            // This is just visual feedback
        });
    }
});