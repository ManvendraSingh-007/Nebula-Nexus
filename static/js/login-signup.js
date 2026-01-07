function togglePass(passwordId) {
    var x = document.getElementById(passwordId);
    let option = document.getElementById("glyph-text");
    let symbol = document.getElementById("symbol");

    // 1. Exit if empty
    if (x.value.length === 0) return;

    // 2. Toggle based ONLY on the input type
    if (x.type === "password") {
        x.type = "text";
        x.classList.add("revealed-coordinates");
        
        // Update labels to your new theme
        option.innerText = "HIDE ACCESS KEY"; 
        symbol.innerText = "< -";
    } else {
        x.type = "password";
        x.classList.remove("revealed-coordinates");
        
        // Match the text exactly
        option.innerText = "SHOW ACCESS KEY"; 
        symbol.innerText = "- >";
    }
}