/**
 * Password toggle functionality only
 * No validation - handled by Django backend
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
    
    // Add floating animation on scroll for products
    const products = document.querySelectorAll('.floating-product');
    
    products.forEach((product, index) => {
        // Random slight variations to animation timing
        const duration = 7 + (index * 0.5);
        product.style.animationDuration = `${duration}s`;
    });
    
    // Parallax effect on mouse move for floating products (desktop only)
    if (window.innerWidth > 900) {
        document.querySelector('.showcase-side').addEventListener('mousemove', (e) => {
            const mouseX = e.clientX / window.innerWidth - 0.5;
            const mouseY = e.clientY / window.innerHeight - 0.5;
            
            products.forEach((product, index) => {
                const speed = (index + 1) * 20;
                const x = mouseX * speed;
                const y = mouseY * speed;
                
                product.style.transform = `translate(${x}px, ${y}px) scale(1)`;
            });
        });
        
        document.querySelector('.showcase-side').addEventListener('mouseleave', () => {
            products.forEach(product => {
                product.style.transform = '';
            });
        });
    }
});