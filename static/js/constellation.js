(function () {
    const CONFIG = {
        starCount: 150,
        spawnInterval: 4000,     // Time between new constellations
        fadeDuration: 8000,      // How long a constellation lasts
        maxDistance: 200,        // Max length of a line
        constellationSize: 6,    // Number of stars in a group
        lineAlphaMax: 0.6        // Max brightness of lines
    };

    let starsContainer, canvas, ctx;
    let stars = [];
    let activeConstellation = null;
    let lastSpawnTime = 0;

    function init() {
        starsContainer = document.getElementById('stars-container');
        canvas = document.getElementById('constellation-canvas');
        if (!starsContainer || !canvas) return;

        ctx = canvas.getContext('2d');
        handleResize();
        window.addEventListener('resize', handleResize);

        generateStars();
        requestAnimationFrame(renderLoop);
    }

    function handleResize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        if (stars.length > 0) generateStars();
    }

    function generateStars() {
        starsContainer.innerHTML = '';
        stars = [];
        for (let i = 0; i < CONFIG.starCount; i++) {
            const x = Math.random() * window.innerWidth;
            const y = Math.random() * window.innerHeight;
            const size = Math.random() * 2 + 1;

            const div = document.createElement('div');
            div.className = 'cosmic-star';
            div.style.cssText = `left:${x}px; top:${y}px; width:${size}px; height:${size}px;`;
            
            // Inner layer for independence from wrapper logic
            const inner = document.createElement('div');
            inner.className = 'twinkle-layer';
            inner.style.setProperty('--duration', (2 + Math.random() * 3) + 's');
            inner.style.setProperty('--base-opacity', (0.2 + Math.random() * 0.5));
            
            div.appendChild(inner);
            starsContainer.appendChild(div);

            stars.push({ x: x + size/2, y: y + size/2, element: div });
        }
    }

    // Connects stars using distance logic
    function getConnections(group) {
        let lines = [];
        // Simple strategy: Connect every star to its 2 nearest neighbors
        // This is faster than Prim's algorithm and looks just as good for small groups
        group.forEach((starA, i) => {
            let neighbors = [];
            group.forEach((starB, j) => {
                if (i === j) return;
                const dist = Math.hypot(starA.x - starB.x, starA.y - starB.y);
                if (dist < CONFIG.maxDistance) {
                    neighbors.push({ star: starB, dist: dist });
                }
            });
            // Sort by closest and pick top 2
            neighbors.sort((a, b) => a.dist - b.dist).slice(0, 2).forEach(n => {
                // Avoid duplicates (checking simplified)
                lines.push({ from: starA, to: n.star });
            });
        });
        return lines;
    }

    function spawnConstellation() {
        if (activeConstellation) return;

        // Pick random start
        const centerIdx = Math.floor(Math.random() * stars.length);
        const center = stars[centerIdx];

        // Find nearest stars to form a cluster
        const cluster = stars
            .map(s => ({ s, dist: Math.hypot(center.x - s.x, center.y - s.y) }))
            .sort((a, b) => a.dist - b.dist)
            .slice(0, CONFIG.constellationSize)
            .map(item => item.s);

        // Activate CSS on stars
        cluster.forEach(s => s.element.classList.add('active'));

        activeConstellation = {
            stars: cluster,
            lines: getConnections(cluster),
            startTime: performance.now()
        };
    }

    function renderLoop(now) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Spawn logic
        if (!activeConstellation && (now - lastSpawnTime > CONFIG.spawnInterval)) {
            spawnConstellation();
            lastSpawnTime = now;
        }

        if (activeConstellation) {
            const elapsed = now - activeConstellation.startTime;
            const progress = elapsed / CONFIG.fadeDuration;

            if (progress >= 1) {
                // Reset
                activeConstellation.stars.forEach(s => s.element.classList.remove('active'));
                activeConstellation = null;
            } else {
                // Calculate Smooth Fade using Sine Wave
                // 0 -> 1 -> 0 over the duration
                const alpha = Math.sin(progress * Math.PI) * CONFIG.lineAlphaMax;

                ctx.beginPath();
                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
                ctx.lineWidth = 1;
                
                // Optional: Subtle glow on lines
                ctx.shadowBlur = 8;
                ctx.shadowColor = `rgba(255, 255, 255, ${alpha * 0.5})`;

                activeConstellation.lines.forEach(line => {
                    ctx.moveTo(line.from.x, line.from.y);
                    ctx.lineTo(line.to.x, line.to.y);
                });
                
                ctx.stroke();
            }
        }

        requestAnimationFrame(renderLoop);
    }

    // Start
    if (document.readyState === 'complete') init();
    else window.addEventListener('load', init);
})();