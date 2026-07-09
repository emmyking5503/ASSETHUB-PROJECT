
// Payment Method Toggle
const paymentMethod = document.getElementById('paymentMethod');
const bankFields = document.getElementById('bankFields');
const cardFields = document.getElementById('cardFields');
const cryptoFields = document.getElementById('cryptoFields');
const walletFields = document.getElementById('walletFields');

function togglePaymentFields() {
    const selectedMethod = paymentMethod.value;
    
    [bankFields, cardFields, cryptoFields, walletFields].forEach(field => {
        field.classList.remove('active');
    });
    
    switch(selectedMethod) {
        case 'bank': bankFields.classList.add('active'); break;
        case 'card': cardFields.classList.add('active'); break;
        case 'crypto': cryptoFields.classList.add('active'); break;
        case 'wallet': walletFields.classList.add('active'); break;
    }
}

paymentMethod.addEventListener('change', togglePaymentFields);

// Form Submission
const paymentForm = document.getElementById('paymentForm');
const submitBtn = document.getElementById('submitPayment');

paymentForm.addEventListener('submit', function(e){

    submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Processing...';
    submitBtn.disabled = true;

});



// Close Modal
function closeModal() {
    successModal.classList.remove('active');
    document.body.style.overflow = '';
}

document.querySelector('.modal-overlay').addEventListener('click', closeModal);
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && successModal.classList.contains('active')) {
        closeModal();
    }
});

// Copy Address
function copyAddress() {
    const addressCode = document.querySelector('.address-box code');
    if (addressCode) {
        navigator.clipboard.writeText(addressCode.textContent).then(() => {
            const btn = document.querySelector('.copy-btn');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i>';
            btn.style.color = 'var(--success)';
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.style.color = '';
            }, 2000);
        });
    }
}

// Input Formatting
const cardNumber = document.getElementById('cardNumber');
const expiry = document.getElementById('expiry');

if (cardNumber) {
    cardNumber.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\s/g, '').replace(/\D/g, '');
        if (value.length > 0) {
            value = value.match(/.{1,4}/g).join(' ');
        }
        e.target.value = value;
    });
}

if (expiry) {
    expiry.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length >= 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        e.target.value = value;
    });
}

// Real-time validation feedback
const inputs = document.querySelectorAll('input[required]');
inputs.forEach(input => {
    input.addEventListener('blur', function() {
        if (this.value.trim()) {
            this.style.borderColor = 'var(--success)';
            this.style.boxShadow = 'var(--shadow-success-glow)';
        } else {
            this.style.borderColor = 'var(--border-subtle)';
            this.style.boxShadow = 'none';
        }
    });
    
    input.addEventListener('input', function() {
        if (this.value.trim()) {
            this.style.borderColor = 'var(--accent)';
            this.style.boxShadow = 'var(--shadow-glow)';
        }
    });
});
