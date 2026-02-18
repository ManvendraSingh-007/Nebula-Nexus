function togglePassword(passwordId) {
    const input = document.getElementById(passwordId);
    const optionText = document.getElementById('glyph-text');
    const symbol = document.getElementById('symbol');

    if (!input || input.value.length === 0) return;

    if (input.type === 'password') {
        input.type = 'text';
        input.classList.add('revealed-coordinates');
        optionText.innerText = 'HIDE ACCESS KEY';
        symbol.innerText = '←';
    } else {
        input.type = 'password';
        input.classList.remove('revealed-coordinates');
        optionText.innerText = 'SHOW ACCESS KEY';
        symbol.innerText = '→';
    }
}

document.querySelector('form').onsubmit = function () {
    setTimeout(() => {
        this.reset();
    }, 100);
};

function togglePasswords() {
    const newPass = document.getElementById('newPassword');
    const confirmPass = document.getElementById('confirmPassword');
    const optionText = document.getElementById('glyph-text');
    const symbol = document.getElementById('symbol');

    if (!newPass || !confirmPass) return;
    if (newPass.value.length === 0 && confirmPass.value.length === 0) return;

    if (newPass.type === 'password') {
        newPass.type = 'text';
        confirmPass.type = 'text';
        newPass.classList.add('revealed-coordinates');
        confirmPass.classList.add('revealed-coordinates');
        optionText.innerText = 'HIDE ACCESS KEYS';
        symbol.innerText = '←';
    } else {
        newPass.type = 'password';
        confirmPass.type = 'password';
        newPass.classList.remove('revealed-coordinates');
        confirmPass.classList.remove('revealed-coordinates');
        optionText.innerText = 'SHOW ACCESS KEYS';
        symbol.innerText = '→';
    }
}

const form = document.getElementById('resetForm');
const newPassword = document.getElementById('newPassword');
const confirmPassword = document.getElementById('confirmPassword');
const errorMsg = document.getElementById('errorMsg');

form.addEventListener('submit', function (e) {
    if (newPassword.value !== confirmPassword.value) {
        e.preventDefault();
        errorMsg.classList.add('show');
        confirmPassword.focus();
        return false;
    }
    errorMsg.classList.remove('show');
});

confirmPassword.addEventListener('input', () => {
    if (confirmPassword.value === newPassword.value) {
        errorMsg.classList.remove('show');
    }
});