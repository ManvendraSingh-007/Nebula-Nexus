function toggleMenu() {
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');
    hamburger.classList.toggle('active');
    navLinks.classList.toggle('active');
}

// Close menu when clicking outside
document.addEventListener('click', function(e) {
    const nav = document.querySelector('.navigation');
    const navLinks = document.querySelector('.nav-links');
    const hamburger = document.querySelector('.hamburger');
    
    if (nav && navLinks && hamburger && !nav.contains(e.target) && navLinks.classList.contains('active')) {
        hamburger.classList.remove('active');
        navLinks.classList.remove('active');
    }
});