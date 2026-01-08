
// ============================================================
// FILE: register.js
// PURPOSE: Client-side validation for User Registration
// APPLICATION: FuelShare - Carpool Platform
// ============================================================

// ========== WAIT FOR DOM TO LOAD ==========
document.addEventListener('DOMContentLoaded', function() {
    
    // ========== GET FORM AND INPUT ELEMENTS ==========
    const registerForm = document.getElementById('registerForm');
    const fullNameInput = document.getElementById('fullName');
    const emailInput = document.getElementById('email');
    const mobileInput = document.getElementById('mobile');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const licenceInput = document.getElementById('licence');
    const termsCheckbox = document.getElementById('terms');

    // ========== UTILITY FUNCTIONS ==========
    
    /**
     * Shows error message for a specific field
     * @param {string} fieldId - ID of the input field
     * @param {string} message - Error message to display
     */
    function showError(fieldId, message) {
        const inputElement = document.getElementById(fieldId);
        const errorElement = document.getElementById(fieldId + 'Error');
        
        if (inputElement) {
            inputElement.classList.add('error');
            inputElement.classList.remove('success');
        }
        
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.add('show');
        }
    }

    /**
     * Hides error message for a specific field
     * @param {string} fieldId - ID of the input field
     */
    function hideError(fieldId) {
        const inputElement = document.getElementById(fieldId);
        const errorElement = document.getElementById(fieldId + 'Error');
        
        if (inputElement) {
            inputElement.classList.remove('error');
            inputElement.classList.add('success');
        }
        
        if (errorElement) {
            errorElement.classList.remove('show');
        }
    }

    /**
     * Clears all validation states
     */
    function clearAllErrors() {
        const allInputs = [fullNameInput, emailInput, mobileInput, 
                          passwordInput, confirmPasswordInput];
        
        allInputs.forEach(input => {
            if (input) {
                input.classList.remove('error', 'success');
            }
        });
        
        const allErrors = document.querySelectorAll('.error-message');
        allErrors.forEach(error => {
            error.classList.remove('show');
        });
    }

    // ========== VALIDATION FUNCTIONS ==========

    /**
     * Validates Full Name field
     * Rules: Required, Min 3 chars, Only alphabets and spaces
     * @returns {boolean} - true if valid, false otherwise
     */
    function validateFullName() {
        const fullName = fullNameInput.value.trim();
        
        // Check if empty
        if (fullName === '') {
            showError('fullName', 'Full name is required');
            return false;
        }
        
        // Check minimum length
        if (fullName.length < 3) {
            showError('fullName', 'Name must be at least 3 characters long');
            return false;
        }
        
        // Check for alphabets and spaces only
        const namePattern = /^[a-zA-Z\s]+$/;
        if (!namePattern.test(fullName)) {
            showError('fullName', 'Name can only contain alphabets and spaces');
            return false;
        }
        
        hideError('fullName');
        return true;
    }

    /**
     * Validates Email field
     * Rules: Required, Valid email format
     * @returns {boolean} - true if valid, false otherwise
     */
    function validateEmail() {
        const email = emailInput.value.trim();
        
        // Check if empty
        if (email === '') {
            showError('email', 'Email address is required');
            return false;
        }
        
        // Check email format using regex
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(email)) {
            showError('email', 'Please enter a valid email address');
            return false;
        }
        
        hideError('email');
        return true;
    }

    /**
     * Validates Mobile Number field
     * Rules: Required, Exactly 10 digits, Numbers only
     * @returns {boolean} - true if valid, false otherwise
     */
    function validateMobile() {
        const mobile = mobileInput.value.trim();
        
        // Check if empty
        if (mobile === '') {
            showError('mobile', 'Mobile number is required');
            return false;
        }
        
        // Check for exactly 10 digits
        const mobilePattern = /^[0-9]{10}$/;
        if (!mobilePattern.test(mobile)) {
            showError('mobile', 'Mobile number must be exactly 10 digits');
            return false;
        }
        
        hideError('mobile');
        return true;
    }

    /**
     * Validates Password field
     * Rules: Required, Minimum 6 characters
     * @returns {boolean} - true if valid, false otherwise
     */
    function validatePassword() {
        const password = passwordInput.value;
        
        // Check if empty
        if (password === '') {
            showError('password', 'Password is required');
            return false;
        }
        
        // Check minimum length
        if (password.length < 6) {
            showError('password', 'Password must be at least 6 characters long');
            return false;
        }
        
        hideError('password');
        return true;
    }

    /**
     * Validates Confirm Password field
     * Rules: Must match password field
     * @returns {boolean} - true if valid, false otherwise
     */
    function validateConfirmPassword() {
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        // Check if empty
        if (confirmPassword === '') {
            showError('confirmPassword', 'Please confirm your password');
            return false;
        }
        
        // Check if passwords match
        if (password !== confirmPassword) {
            showError('confirmPassword', 'Passwords do not match');
            return false;
        }
        
        hideError('confirmPassword');
        return true;
    }

    /**
     * Validates Driving Licence upload
     * Rules: Required, File types: JPG, PNG, PDF
     * @returns {boolean} - true if valid, false otherwise
     */
    function validateLicence() {
        const files = licenceInput.files;
        
        // Check if file is selected
        if (!files || files.length === 0) {
            showError('licence', 'Please upload your driving licence');
            return false;
        }
        
        const file = files[0];
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
        
        // Check file type
        if (!allowedTypes.includes(file.type)) {
            showError('licence', 'Only JPG, PNG, and PDF files are allowed');
            return false;
        }
        
        // Optional: Check file size (e.g., max 5MB)
        const maxSizeInBytes = 5 * 1024 * 1024; // 5MB
        if (file.size > maxSizeInBytes) {
            showError('licence', 'File size must be less than 5MB');
            return false;
        }
        
        hideError('licence');
        return true;
    }

    /**
     * Validates Terms & Conditions checkbox
     * Rules: Must be checked
     * @returns {boolean} - true if valid, false otherwise
     */
    function validateTerms() {
        if (!termsCheckbox.checked) {
            showError('terms', 'You must agree to the Terms & Conditions');
            return false;
        }
        
        hideError('terms');
        return true;
    }

    // ========== REAL-TIME VALIDATION (OPTIONAL) ==========
    // Validate fields when user leaves the input field (blur event)
    
    fullNameInput.addEventListener('blur', validateFullName);
    emailInput.addEventListener('blur', validateEmail);
    mobileInput.addEventListener('blur', validateMobile);
    passwordInput.addEventListener('blur', validatePassword);
    confirmPasswordInput.addEventListener('blur', validateConfirmPassword);
    licenceInput.addEventListener('change', validateLicence);
    termsCheckbox.addEventListener('change', validateTerms);

    // Allow only numbers in mobile field
    mobileInput.addEventListener('input', function() {
        this.value = this.value.replace(/[^0-9]/g, '');
    });

    // ========== FORM SUBMISSION HANDLER ==========
    registerForm.addEventListener('submit', function(event) {
        // Prevent default form submission
        event.preventDefault();
        
        // Run all validations
        const isFullNameValid = validateFullName();
        const isEmailValid = validateEmail();
        const isMobileValid = validateMobile();
        const isPasswordValid = validatePassword();
        const isConfirmPasswordValid = validateConfirmPassword();
        const isLicenceValid = validateLicence();
        const isTermsValid = validateTerms();
        
        // Check if all validations passed
        const isFormValid = isFullNameValid && 
                           isEmailValid && 
                           isMobileValid && 
                           isPasswordValid && 
                           isConfirmPasswordValid && 
                           isLicenceValid && 
                           isTermsValid;
        
        if (isFormValid) {
            // ========== ALL VALIDATIONS PASSED ==========
            console.log('✓ Form validation successful!');
            
            // Show success message
            alert('Registration successful! Your account is being created.');
            
            // ========== BACKEND INTEGRATION PLACEHOLDER ==========
            // TODO: Send form data to backend API
            /*
            const formData = new FormData();
            formData.append('fullName', fullNameInput.value.trim());
            formData.append('email', emailInput.value.trim());
            formData.append('mobile', mobileInput.value.trim());
            formData.append('password', passwordInput.value);
            formData.append('licence', licenceInput.files[0]);
            
            fetch('/api/register', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
                // Redirect to login page or dashboard
                window.location.href = '/login';
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Registration failed. Please try again.');
            });
            */
            
            // For demonstration: Log form data
            console.log({
                fullName: fullNameInput.value.trim(),
                email: emailInput.value.trim(),
                mobile: mobileInput.value.trim(),
                password: '******', // Never log actual password
                licence: licenceInput.files[0].name
            });
            
            // Uncomment to actually submit the form
            // registerForm.submit();
            
        } else {
            // ========== VALIDATION FAILED ==========
            console.log('✗ Form validation failed. Please check the errors.');
            
            // Scroll to first error
            const firstError = document.querySelector('.error-message.show');
            if (firstError) {
                firstError.parentElement.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
            }
        }
    });

    // ========== INITIALIZE ==========
    console.log('Registration validation initialized');
});

// ============================================================
// END OF register.js
// ============================================================