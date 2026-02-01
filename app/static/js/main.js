// Main JavaScript for ServCore

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initFlashMessages();
    initFormValidation();
    initConfirmations();
});

/**
 * Flash Message Auto-Dismiss
 */
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash');

    flashMessages.forEach(flash => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            fadeOut(flash);
        }, 5000);

        // Close button
        const closeBtn = flash.querySelector('.flash-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                fadeOut(flash);
            });
        }
    });
}

/**
 * Fade out element and remove from DOM
 */
function fadeOut(element) {
    element.style.opacity = '0';
    element.style.transition = 'opacity 0.3s ease-out';
    setTimeout(() => {
        element.remove();
    }, 300);
}

/**
 * Client-side Form Validation
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;

            // Check required fields
            const requiredFields = form.querySelectorAll('[required]');
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    showFieldError(field, 'This field is required');
                } else {
                    clearFieldError(field);
                }
            });

            // Email validation
            const emailFields = form.querySelectorAll('[type="email"]');
            emailFields.forEach(field => {
                if (field.value && !isValidEmail(field.value)) {
                    isValid = false;
                    showFieldError(field, 'Please enter a valid email address');
                }
            });

            // Password minimum length
            const passwordFields = form.querySelectorAll('[type="password"][minlength]');
            passwordFields.forEach(field => {
                const minLength = parseInt(field.getAttribute('minlength'));
                if (field.value && field.value.length < minLength) {
                    isValid = false;
                    showFieldError(field, `Password must be at least ${minLength} characters`);
                }
            });

            if (!isValid) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Show field error message
 */
function showFieldError(field, message) {
    field.classList.add('error');

    // Remove existing error message
    const existingError = field.parentElement.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }

    // Add new error message
    const errorSpan = document.createElement('span');
    errorSpan.className = 'error-message';
    errorSpan.textContent = message;
    field.parentElement.appendChild(errorSpan);
}

/**
 * Clear field error
 */
function clearFieldError(field) {
    field.classList.remove('error');
    const errorMessage = field.parentElement.querySelector('.error-message');
    if (errorMessage) {
        errorMessage.remove();
    }
}

/**
 * Validate email format
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Confirmation Dialogs
 */
function initConfirmations() {
    // Delete confirmations
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm-delete') || 'Are you sure you want to delete this?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Status change confirmations
    const statusButtons = document.querySelectorAll('[data-confirm-status]');
    statusButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm-status') || 'Are you sure you want to change the status?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Initialize Charts (for admin dashboard)
 */
function initCharts() {
    // Charts will be initialized in the admin dashboard template
    // using Chart.js with data passed from backend
    console.log('Charts initialization function ready');
}
