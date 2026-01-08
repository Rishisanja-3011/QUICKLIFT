
// ============================================================
// FILE: login.js
// PURPOSE: Client-side validation for User Login
// APPLICATION: FuelShare - Carpool Platform
// ============================================================

// ========== WAIT FOR DOM TO LOAD ==========
document.addEventListener('DOMContentLoaded', function() {
    
    // ========== GET FORM AND INPUT ELEMENTS ==========
    const loginForm = document.getElementById('loginForm');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');

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
        const allInputs = [emailInput, passwordInput];
        
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
     * Validates Password field
     * Rules: Required
     * @returns {boolean} - true if valid, false otherwise
     */
    function validatePassword() {
        const password = passwordInput.value;
        
        // Check if empty
        if (password === '') {
            showError('password', 'Password is required');
            return false;
        }
        
        hideError('password');
        return true;
    }

    // ========== REAL-TIME VALIDATION (OPTIONAL) ==========
    // Validate fields when user leaves the input field (blur event)
    
    emailInput.addEventListener('blur', validateEmail);
    passwordInput.addEventListener('blur', validatePassword);

    // Clear errors on input (when user starts typing)
    emailInput.addEventListener('input', function() {
        if (this.value.trim() !== '') {
            hideError('email');
        }
    });

    passwordInput.addEventListener('input', function() {
        if (this.value !== '') {
            hideError('password');
        }
    });

    // ========== KEYBOARD NAVIGATION ==========
    // Allow Enter key to move from email to password
    emailInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            passwordInput.focus();
        }
    });

    // Allow Enter key to submit form from password field
    passwordInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            loginForm.dispatchEvent(new Event('submit'));
        }
    });

    // ========== FORM SUBMISSION HANDLER ==========
    loginForm.addEventListener('submit', function(event) {
        // Prevent default form submission
        event.preventDefault();
        
        // Run all validations
        const isEmailValid = validateEmail();
        const isPasswordValid = validatePassword();
        
        // Check if all validations passed
        const isFormValid = isEmailValid && isPasswordValid;
        
        if (isFormValid) {
            // ========== ALL VALIDATIONS PASSED ==========
            console.log('✓ Login validation successful!');
            
            // Get form data
            const loginData = {
                email: emailInput.value.trim(),
                password: passwordInput.value
            };
            
            // Show success message
            alert('Login successful! Redirecting to dashboard...');
            
            // ========== BACKEND AUTHENTICATION PLACEHOLDER ==========
            // TODO: Send credentials to backend API for authentication
            /*
            fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(loginData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Login successful:', data);
                    
                    // Store authentication token
                    localStorage.setItem('authToken', data.token);
                    localStorage.setItem('userId', data.userId);
                    localStorage.setItem('userName', data.userName);
                    
                    // Redirect to dashboard
                    window.location.href = '/dashboard';
                } else {
                    // Handle authentication failure
                    console.error('Login failed:', data.message);
                    alert('Invalid email or password. Please try again.');
                    
                    // Clear password field for security
                    passwordInput.value = '';
                    passwordInput.focus();
                }
            })
            .catch(error => {
                console.error('Login error:', error);
                alert('An error occurred during login. Please try again.');
            });
            */
            
            // For demonstration: Log login attempt
            console.log({
                email: loginData.email,
                password: '******', // Never log actual password
                timestamp: new Date().toISOString()
            });
            
            // Simulate successful login (remove in production)
            setTimeout(() => {
                console.log('Redirecting to dashboard...');
                // window.location.href = '/dashboard'; // Uncomment for actual redirect
            }, 1500);
            
            // Uncomment to actually submit the form
            // loginForm.submit();
            
        } else {
            // ========== VALIDATION FAILED ==========
            console.log('✗ Login validation failed. Please check the errors.');
            
            // Focus on first invalid field
            if (!isEmailValid) {
                emailInput.focus();
            } else if (!isPasswordValid) {
                passwordInput.focus();
            }
            
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

    // ========== OPTIONAL: PASSWORD VISIBILITY TOGGLE ==========
    // If you have a toggle button with id="togglePassword"
    const togglePasswordButton = document.getElementById('togglePassword');
    if (togglePasswordButton) {
        togglePasswordButton.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Update button icon/text
            this.textContent = type === 'password' ? '👁️' : '🙈';
        });
    }

    // ========== OPTIONAL: REMEMBER ME FUNCTIONALITY ==========
    // If you have a "Remember Me" checkbox with id="rememberMe"
    const rememberMeCheckbox = document.getElementById('rememberMe');
    
    // Load saved email if "Remember Me" was checked previously
    if (rememberMeCheckbox) {
        const savedEmail = localStorage.getItem('rememberedEmail');
        if (savedEmail) {
            emailInput.value = savedEmail;
            rememberMeCheckbox.checked = true;
        }
        
        // Save email when "Remember Me" is checked
        loginForm.addEventListener('submit', function() {
            if (rememberMeCheckbox.checked) {
                localStorage.setItem('rememberedEmail', emailInput.value.trim());
            } else {
                localStorage.removeItem('rememberedEmail');
            }
        });
    }

    // ========== SECURITY: PREVENT PASSWORD AUTOCOMPLETE ISSUES ==========
    // Clear password field when page loads (optional security measure)
    passwordInput.value = '';

    // ========== INITIALIZE ==========
    console.log('Login validation initialized');
});

// ============================================================
// END OF login.js
// ============================================================