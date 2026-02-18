// Auto-focus and auto-advance OTP inputs
const inputs = document.querySelectorAll('.otp-input');

inputs.forEach((input, index) => {
    // Auto-advance to next input
    input.addEventListener('input', function (e) {
        if (this.value.length === 1 && index < inputs.length - 1) {
            inputs[index + 1].focus();
        }

        // Only allow single digit
        if (this.value.length > 1) {
            this.value = this.value.slice(0, 1);
        }
    });

    // Handle backspace to go to previous input
    input.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && this.value === '' && index > 0) {
            inputs[index - 1].focus();
        }
    });

    // Handle paste event
    input.addEventListener('paste', function (e) {
        e.preventDefault();
        const pastedData = e.clipboardData.getData('text').trim();

        if (/^\d{6}$/.test(pastedData)) {
            inputs.forEach((inp, i) => {
                inp.value = pastedData[i];
            });
            inputs[5].focus();
        }
    });
});

// Auto-focus first input on load
window.addEventListener('load', () => {
    inputs[0].focus();
});

// Resend OTP function
function resendOTP(event) {
    event.preventDefault();
    // Add your resend logic here
    alert('New code sent to your cosmic address!');
}

// Combine all inputs into one hidden field before submit
document.getElementById('otpForm').addEventListener('submit', function (e) {
    const otpValue = Array.from(inputs).map(input => input.value).join('');

    // Validate all 6 digits are filled
    if (otpValue.length !== 6) {
        e.preventDefault();
        alert('Please enter all 6 digits');
        return;
    }
    // disable the input so they dont get sent
    Array.from(inputs).forEach(input => input.disabled = true)
    // Set the combined OTP value to hidden input
    document.getElementById('otpValue').value = otpValue;
});