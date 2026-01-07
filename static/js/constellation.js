(function () {
    const CONFIG = {
        starCount: 150,
        spawnInterval: 4000,
        fadeDuration: 8000,
        maxDistance: 300,
        constellationSize: 14
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
            const size = Math.random() * 1.5 + 0.5;

            const div = document.createElement('div');
            div.className = 'cosmic-star';
            div.style.cssText = `left:${x}px; top:${y}px; width:${size}px; height:${size}px; opacity:${0.2 + Math.random() * 0.4};`;
            
            const inner = document.createElement('div');
            inner.className = 'twinkle-layer';
            div.appendChild(inner);
            starsContainer.appendChild(div);

            stars.push({ x: x + size/2, y: y + size/2, element: div });
        }
    }

    /**
     * HYBRID LOGIC:
     * 1. Ensures all stars are connected (MST) for structure.
     * 2. Adds randomized nearest-neighbor branches for geometry.
     */
    function getConnections(group) {
        let lines = [];
        const seen = new Set();

        const addLine = (a, b) => {
            const key = [group.indexOf(a), group.indexOf(b)].sort().join('-');
            if (!seen.has(key)) {
                lines.push({ from: a, to: b });
                seen.add(key);
            }
        };

        // PART 1: ENSURE ALL CONNECT (Prim's MST)
        let reached = [group[0]];
        let unreached = group.slice(1);
        while (unreached.length > 0) {
            let record = { dist: Infinity, rIdx: 0, uIdx: 0 };
            reached.forEach((r, ri) => {
                unreached.forEach((u, ui) => {
                    const d = Math.hypot(r.x - u.x, r.y - u.y);
                    if (d < record.dist) record = { dist: d, rIdx: ri, uIdx: ui };
                });
            });
            if (record.dist < CONFIG.maxDistance) {
                addLine(reached[record.rIdx], unreached[record.uIdx]);
            }
            reached.push(unreached[record.uIdx]);
            unreached.splice(record.uIdx, 1);
        }

        // PART 2: NEAREST NEIGHBOR BRANCHES
        group.forEach((starA) => {
            let potential = group
                .map(starB => ({ star: starB, dist: Math.hypot(starA.x - starB.x, starA.y - starB.y) }))
                .filter(n => n.star !== starA && n.dist < CONFIG.maxDistance)
                .sort((a, b) => a.dist - b.dist);

            // Randomly add 1 extra neighbor for geometric variety
            if (potential.length > 0 && Math.random() > 0.5) {
                addLine(starA, potential[0].star);
            }
        });

        return lines;
    }

    function spawnConstellation() {
        if (activeConstellation) return;

        const centerIdx = Math.floor(Math.random() * stars.length);
        const center = stars[centerIdx];

        const cluster = stars
            .map(s => ({ s, dist: Math.hypot(center.x - s.x, center.y - s.y) }))
            .sort((a, b) => a.dist - b.dist)
            .slice(0, CONFIG.constellationSize)
            .map(item => item.s);

        activeConstellation = {
            stars: cluster,
            lines: getConnections(cluster),
            startTime: performance.now()
        };
    }

    function renderLoop(now) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!activeConstellation && (now - lastSpawnTime > CONFIG.spawnInterval)) {
            spawnConstellation();
            lastSpawnTime = now;
        }

        if (activeConstellation) {
            const elapsed = now - activeConstellation.startTime;
            const progress = elapsed / CONFIG.fadeDuration;

            if (progress >= 1) {
                activeConstellation = null;
            } else {
                const alpha = Math.sin(progress * Math.PI);
                ctx.beginPath();
                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.45})`;
                ctx.lineWidth = 0.8;
                
                activeConstellation.lines.forEach(line => {
                    ctx.moveTo(line.from.x, line.from.y);
                    ctx.lineTo(line.to.x, line.to.y);
                });
                ctx.stroke();
            }
        }
        requestAnimationFrame(renderLoop);
    }

    if (document.readyState === 'complete') init();
    else window.addEventListener('load', init);
})();