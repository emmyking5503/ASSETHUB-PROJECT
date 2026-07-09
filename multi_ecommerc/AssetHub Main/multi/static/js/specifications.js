/**
 * Product Specifications Manager
 * Handles dynamic addition and removal of specification rows
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // DOM Elements
    // ==========================================
    const specificationsContainer = document.getElementById('specificationsContainer');
    const btnAddSpec = document.getElementById('btnAddSpec');
    const emptyState = document.getElementById('emptyState');
    
    // Specification counter
    let specCount = 0;
    
    // ==========================================
    // Add Specification Row
    // ==========================================
    btnAddSpec.addEventListener('click', function() {
        addSpecificationRow();
    });
    
    function addSpecificationRow(name = '', value = '') {
        // Hide empty state if it exists
        if (emptyState) {
            emptyState.style.display = 'none';
        }
        
        // Increment counter
        specCount++;
        
        // Create specification row
        const specRow = document.createElement('div');
        specRow.className = 'spec-row';
        specRow.dataset.index = specCount;
        
        // Specification Name Input
        const nameGroup = document.createElement('div');
        nameGroup.className = 'spec-input-group';
        
        const nameLabel = document.createElement('label');
        nameLabel.className = 'spec-label';
        nameLabel.textContent = 'Specification Name';
        
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.className = 'spec-input';
        nameInput.name = `spec_name_${specCount}`;
        nameInput.placeholder = 'e.g., Brand, Material, Size';
        nameInput.value = name;
        nameInput.required = true;
        
        nameGroup.appendChild(nameLabel);
        nameGroup.appendChild(nameInput);
        
        // Specification Value Input
        const valueGroup = document.createElement('div');
        valueGroup.className = 'spec-input-group';
        
        const valueLabel = document.createElement('label');
        valueLabel.className = 'spec-label';
        valueLabel.textContent = 'Specification Value';
        
        const valueInput = document.createElement('input');
        valueInput.type = 'text';
        valueInput.className = 'spec-input';
        valueInput.name = `spec_value_${specCount}`;
        valueInput.placeholder = 'e.g., Rolex, Cotton, Large';
        valueInput.value = value;
        valueInput.required = true;
        
        valueGroup.appendChild(valueLabel);
        valueGroup.appendChild(valueInput);
        
        // Remove Button
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn-remove-spec';
        removeBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
        removeBtn.title = 'Remove specification';
        
        removeBtn.addEventListener('click', function() {
            removeSpecificationRow(specRow);
        });
        
        // Assemble row
        specRow.appendChild(nameGroup);
        specRow.appendChild(valueGroup);
        specRow.appendChild(removeBtn);
        
        // Add to container
        specificationsContainer.appendChild(specRow);
        
        // Focus on name input
        nameInput.focus();
        
        // Update counter display
        updateSpecCounter();
        
        // Add entrance animation
        specRow.style.animation = 'none';
        setTimeout(() => {
            specRow.style.animation = 'slideIn 0.3s ease';
        }, 10);
    }
    
    // ==========================================
    // Remove Specification Row
    // ==========================================
    function removeSpecificationRow(row) {
        // Animate removal
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(20px)';
        
        setTimeout(() => {
            row.remove();
            
            // Show empty state if no rows left
            const remainingRows = specificationsContainer.querySelectorAll('.spec-row:not(.empty-state)');
            if (remainingRows.length === 0 && emptyState) {
                emptyState.style.display = 'block';
            }
            
            // Update counter
            updateSpecCounter();
        }, 300);
    }
    
    // ==========================================
    // Update Specification Counter
    // ==========================================
    function updateSpecCounter() {
        // Remove existing counter
        const existingCounter = specificationsContainer.querySelector('.spec-counter');
        if (existingCounter) {
            existingCounter.remove();
        }
        
        const rows = specificationsContainer.querySelectorAll('.spec-row:not(.empty-state)');
        
        if (rows.length > 0) {
            const counter = document.createElement('div');
            counter.className = 'spec-counter';
            counter.innerHTML = `
                <i class="fa-solid fa-list-check"></i>
                <span><span class="count">${rows.length}</span> specification${rows.length !== 1 ? 's' : ''} added</span>
            `;
            specificationsContainer.appendChild(counter);
        }
    }
    
    // ==========================================
    // Image Upload Preview
    // ==========================================
    const fileInput = document.getElementById('productImages');
    const previewGrid = document.getElementById('imagePreviewGrid');
    const uploadZone = document.getElementById('uploadZone');
    
    if (fileInput) {
        fileInput.addEventListener('change', handleImageSelect);
    }
    
    // Drag and drop
    if (uploadZone) {
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.style.borderColor = 'var(--primary)';
            uploadZone.style.backgroundColor = 'var(--primary-light)';
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.style.borderColor = '';
            uploadZone.style.backgroundColor = '';
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.style.borderColor = '';
            uploadZone.style.backgroundColor = '';
            
            const files = Array.from(e.dataTransfer.files).filter(file => file.type.startsWith('image/'));
            handleFiles(files);
        });
    }
    
    function handleImageSelect(e) {
        const files = Array.from(e.target.files);
        handleFiles(files);
    }
    
    function handleFiles(files) {
        files.forEach(file => {
            if (!file.type.startsWith('image/')) return;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                createPreviewItem(e.target.result);
            };
            reader.readAsDataURL(file);
        });
    }
    
    function createPreviewItem(src) {
        const item = document.createElement('div');
        item.className = 'preview-item';
        
        const img = document.createElement('img');
        img.src = src;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'preview-remove';
        removeBtn.innerHTML = '<i class="fa-solid fa-times"></i>';
        removeBtn.addEventListener('click', () => item.remove());
        
        item.appendChild(img);
        item.appendChild(removeBtn);
        previewGrid.appendChild(item);
    }
    
    // ==========================================
    // Mobile Menu Toggle
    // ==========================================
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const mobileOverlay = document.getElementById('mobileOverlay');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            mobileOverlay.classList.toggle('show');
        });
    }
    
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            mobileOverlay.classList.remove('show');
        });
    }
    
    // ==========================================
    // Form Submission
    // ==========================================
    const form = document.getElementById('addProductForm');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Collect specifications
        const specs = [];
        const specRows = specificationsContainer.querySelectorAll('.spec-row:not(.empty-state)');
        
        specRows.forEach(row => {
            const nameInput = row.querySelector('input[name^="spec_name"]');
            const valueInput = row.querySelector('input[name^="spec_value"]');
            
            if (nameInput.value.trim() && valueInput.value.trim()) {
                specs.push({
                    name: nameInput.value.trim(),
                    value: valueInput.value.trim()
                });
            }
        });
        
        // Log collected data (replace with actual API call)
        console.log('Product Data:', {
            name: document.getElementById('productName').value,
            category: document.getElementById('category').value,
            price: document.getElementById('price').value,
            specifications: specs
        });
        
        // Show success message
        const btn = form.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
        btn.disabled = true;
        
        setTimeout(() => {
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Saved!';
            btn.style.backgroundColor = 'var(--secondary)';
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.backgroundColor = '';
                btn.disabled = false;
            }, 1500);
        }, 1000);
    });
    
    // ==========================================
    // Add Sample Specifications (Demo)
    // ==========================================
    // Uncomment below to add sample specs on load
    /*
    addSpecificationRow('Brand', 'Apple');
    addSpecificationRow('Model', 'iPhone 14 Pro');
    addSpecificationRow('Color', 'Deep Purple');
    */
    
});