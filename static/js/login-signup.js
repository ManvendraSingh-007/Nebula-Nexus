function togglePass(passwordId) {
    var x = document.getElementById(passwordId);
    let option = document.getElementById("glyph-text");
    let symbol = document.getElementById("symbol");

    // 1. Check if the field is empty
    if (x.value.length === 0) {
        console.log("Transmission empty: No coordinates to reveal.");
        return; // Exit the function if nothing is typed
    }

    // 2. Toggle logic
    if (x.type === "password") {
        x.type = "text";
        x.classList.add("revealed-coordinates"); // Apply the mono styling
        option.innerText = "HIDE COORDINATES";
        symbol.innerText = "< -";
    } else {
        x.type = "password";
        x.classList.remove("revealed-coordinates"); // Remove the styling
        option.innerText = "SHOW COORDINATES";
        symbol.innerText = "- >";
    }
}