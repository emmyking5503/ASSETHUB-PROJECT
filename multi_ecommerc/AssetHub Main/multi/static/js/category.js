/**
 * Category Management - Seller Dashboard
 * Handles category creation, icon selection, color picking, and dynamic attributes
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // Icon Selection
    // ==========================================
    const iconOptions = document.querySelectorAll('.icon-option:not(.more)');
    const selectedIconInput = document.getElementById('selectedIcon');
    const previewIcon = document.getElementById('previewIcon');
    
    iconOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected from all
            iconOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected to clicked
            this.classList.add('selected');
            
            // Update hidden input
            const iconClass = this.dataset.icon;
            selectedIconInput.value = iconClass;
            
            // Update preview
            updatePreview();
        });
    });
    
    // More icons modal (simplified - would open icon picker)
    const moreIconsBtn = document.querySelector('.icon-option.more');
    if (moreIconsBtn) {
        moreIconsBtn.addEventListener('click', function() {
            alert('Icon picker modal would open here with 100+ icons');
        });
    }
    
    // ==========================================
    // Color Selection
    // ==========================================
    const colorOptions = document.querySelectorAll('.color-option:not(.custom)');
    const selectedColorInput = document.getElementById('selectedColor');
    const customColorInput = document.getElementById('customColor');
    
    colorOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected from all
            colorOptions.forEach(opt => opt.classList.remove('selected'));
            document.querySelector('.color-option.custom')?.classList.remove('selected');
            
            // Add selected to clicked
            this.classList.add('selected');
            
            // Update hidden input
            const color = this.dataset.color;
            selectedColorInput.value = color;
            
            // Update preview
            updatePreview();
        });
    });
    
    // Custom color picker
    if (customColorInput) {
        customColorInput.addEventListener('input', function() {
            document.querySelectorAll('.color-option').forEach(opt => opt.classList.remove('selected'));
            document.querySelector('.color-option.custom').classList.add('selected');
            selectedColorInput.value = this.value;
            updatePreview();
        });
    }
    
    // ==========================================
    // Live Preview Update
    // ==========================================
    const categoryNameInput = document.getElementById('categoryName');
    const categoryDescriptionInput = document.getElementById('categoryDescription');
    const parentCategorySelect = document.getElementById('parentCategory');
    
    function updatePreview() {
        const name = categoryNameInput.value || 'Category Name';
        const description = categoryDescriptionInput.value || 'Category description will appear here';
        const icon = selectedIconInput.value || 'fa-folder';
        const color = selectedColorInput.value || '#4F46E5';
        
        // Update preview card
        previewIcon.innerHTML = `<i class="fa-solid ${icon}"></i>`;
        previewIcon.style.backgroundColor = color + '20'; // 20% opacity
        previewIcon.style.color = color;
        
        document.getElementById('previewName').textContent = name;
        document.getElementById('previewDescription').textContent = description;
        
        // Update parent badge
        const parentText = parentCategorySelect.options[parentCategorySelect.selectedIndex].text;
        const parentBadge = document.getElementById('previewParent');
        if (parentCategorySelect.value) {
            parentBadge.innerHTML = `<i class="fa-solid fa-sitemap"></i> Parent: ${parentText}`;
            parentBadge.style.display = 'inline-flex';
        } else {
            parentBadge.style.display = 'none';
        }
    }
    
    // Attach live update listeners
    if (categoryNameInput) {
        categoryNameInput.addEventListener('input', updatePreview);
    }
    if (categoryDescriptionInput) {
        categoryDescriptionInput.addEventListener('input', updatePreview);
    }
    if (parentCategorySelect) {
        parentCategorySelect.addEventListener('change', updatePreview);
    }
    
    // ==========================================
    // Dynamic Attributes
    // ==========================================
    const btnAddAttribute = document.getElementById('btnAddAttribute');
    const attributesContainer = document.getElementById('attributesContainer');
    const attributesEmpty = document.getElementById('attributesEmpty');
    let attributeCount = 0;
    
    btnAddAttribute.addEventListener('click', function() {
        addAttributeRow();
    });
    
    function addAttributeRow(name = '', type = 'text') {
        // Hide empty state
        if (attributesEmpty) {
            attributesEmpty.style.display = 'none';
        }
        
        attributeCount++;
        
        const row = document.createElement('div');
        row.className = 'attribute-row';
        row.dataset.index = attributeCount;
        
        row.innerHTML = `
            <div class="attribute-input-group">
                <label class="attribute-label">Attribute Name</label>
                <input type="text" class="attribute-input" name="attr_name_${attributeCount}" 
                       placeholder="e.g., Brand, Size, Color" value="${name}" required>
            </div>
            <div class="attribute-input-group">
                <label class="attribute-label">Type</label>
                <select class="attribute-type-select" name="attr_type_${attributeCount}">
                    <option value="text" ${type === 'text' ? 'selected' : ''}>Text</option>
                    <option value="number" ${type === 'number' ? 'selected' : ''}>Number</option>
                    <option value="select" ${type === 'select' ? 'selected' : ''}>Dropdown</option>
                    <option value="checkbox" ${type === 'checkbox' ? 'selected' : ''}>Checkbox</option>
                    <option value="date" ${type === 'date' ? 'selected' : ''}>Date</option>
                </select>
            </div>
            <button type="button" class="btn-remove-attribute" onclick="removeAttributeRow(this)" title="Remove attribute">
                <i class="fa-solid fa-trash"></i>
            </button>
        `;
        
        attributesContainer.appendChild(row);
        
        // Focus on name input
        row.querySelector('input').focus();
    }
    
    // Global function for inline onclick
    window.removeAttributeRow = function(button) {
        const row = button.closest('.attribute-row');
        
        // Animate removal
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(20px)';
        
        setTimeout(() => {
            row.remove();
            
            // Show empty state if no rows
            const remaining = attributesContainer.querySelectorAll('.attribute-row');
            if (remaining.length === 0 && attributesEmpty) {
                attributesEmpty.style.display = 'block';
            }
        }, 300);
    };
    
    // ==========================================
    // Category Tree Toggle
    // ==========================================
    const treeToggles = document.querySelectorAll('.category-tree-toggle');
    
    treeToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const item = this.closest('.category-tree-item');
            const children = item.querySelector('.category-tree-children');
            
            if (children) {
                this.classList.toggle('expanded');
                children.classList.toggle('show');
            }
        });
    });
    
    // ==========================================
    // Form Submission
    // ==========================================
    const categoryForm = document.getElementById('categoryForm');
    
    categoryForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Collect attributes
        const attributes = [];
        const rows = attributesContainer.querySelectorAll('.attribute-row');
        rows.forEach(row => {
            const name = row.querySelector('input').value;
            const type = row.querySelector('select').value;
            if (name) {
                attributes.push({ name, type });
            }
        });
        
        // Simulate API call
        const submitBtn = categoryForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating...';
        
        setTimeout(() => {
            submitBtn.innerHTML = '<i class="fa-solid fa-check"></i> Created!';
            submitBtn.classList.remove('btn-primary');
            submitBtn.classList.add('btn-success');
            
            // Show success toast
            showToast('Category created successfully!');
            
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
                submitBtn.classList.remove('btn-success');
                submitBtn.classList.add('btn-primary');
                
                // Reset form or redirect
                // categoryForm.reset();
                // location.reload();
            }, 1500);
        }, 1000);
    });
    
    // ==========================================
    // Toast Notification
    // ==========================================
    function showToast(message) {
        const existing = document.querySelector('.toast-notification');
        if (existing) existing.remove();
        
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.innerHTML = `
            <i class="fa-solid fa-check-circle"></i>
            <span>${message}</span>
        `;
        
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--gray-800);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: var(--radius-lg);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 500;
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(style);
    
    // Initialize preview
    updatePreview();
});