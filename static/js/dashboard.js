
function confirmLogOut() {
    let overlay = document.createElement("div");
    overlay.style = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:999;";

    let divMain = document.createElement("div");
    divMain.id = "LogOutBox";
    divMain.innerHTML = "<p>Terminate session and return to orbit?</p>";

    let yes = document.createElement("button");
    yes.className = "btn-yes";
    yes.innerText = "Exit Nexus";

    let no = document.createElement("button");
    no.className = "btn-no";
    no.innerText = "Stay";

    yes.onclick = () => window.location.href = "/logout/";
    no.onclick = () => { divMain.remove(); overlay.remove(); };

    divMain.appendChild(yes);
    divMain.appendChild(no);
    document.body.appendChild(overlay);
    document.body.appendChild(divMain);
}
