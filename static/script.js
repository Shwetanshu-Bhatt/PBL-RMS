console.log("SCRIPT LOADED");
const startBtn = document.getElementById("startBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resetBtn = document.getElementById("resetBtn");
const modeSelect = document.getElementById("modeSelect");
const simulationModeLabel = document.getElementById("simulationModeLabel");
const logArea = document.getElementById("logMessages");

function logMessage(msg) {
    const t = new Date().toLocaleTimeString();
    const e = document.createElement("div");
    e.textContent = `[${t}] ${msg}`;
    logArea.appendChild(e);
    logArea.scrollTop = logArea.scrollHeight;
}

let controlInFlight = false;

startBtn.onclick = async () => {
    if (controlInFlight) return;
    controlInFlight = true;
    startBtn.disabled = true;
    try {
        await fetch("/start", { method: "POST" });
        logMessage("Simulation started");
    } catch (e) {
        logMessage("Start failed");
    } finally {
        controlInFlight = false;
    }
};

pauseBtn.onclick = async () => {
    if (controlInFlight) return;
    controlInFlight = true;
    pauseBtn.disabled = true;
    try {
        await fetch("/pause", { method: "POST" });
        logMessage("Simulation paused");
    } catch (e) {
        logMessage("Pause failed");
    } finally {
        controlInFlight = false;
    }
};

resetBtn.onclick = async () => {
    if (controlInFlight) return;
    controlInFlight = true;
    resetBtn.disabled = true;
    try {
        await fetch("/reset", { method: "POST" });
        logMessage("Simulation reset");
        logArea.innerHTML = "";
    } catch (e) {
        logMessage("Reset failed");
    } finally {
        controlInFlight = false;
        resetBtn.disabled = false;
    }
};

modeSelect.onchange = async () => {
    if (controlInFlight) return;
    controlInFlight = true;
    try {
        const mode = modeSelect.value === "centralized" ? "centralized" : "ordered";
        await fetch("/mode", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode }) });
        const modeText = mode === "centralized" ? "Centralized Controller" : "Ordered Locking";
        simulationModeLabel.textContent = `Simulation Mode: ${modeText}`;
        logMessage("Mode changed to " + mode);
    } catch (e) {
        logMessage("Mode change failed");
    } finally {
        controlInFlight = false;
    }
};

function moveTrainSprite(t) {
    const elem = document.getElementById("train" + t.id);
    if (!elem) return;
    const x = 50 + t.pos * 500;
    const y = { A: 350, B: 200, C: 50 }[t.track] || 350;
    if (elem.tagName === "circle") {
        elem.setAttribute("cx", x);
        elem.setAttribute("cy", y);
    } else {
        elem.setAttribute("x", x - 12);
        elem.setAttribute("y", y - 12);
    }
}

function updateTrackIndicators(trackStatus) {
    for (const track in trackStatus) {
        const blocks = trackStatus[track].split(",");
        const indicator = document.getElementById("track" + track + "Indicator");
        const waitingOnTrack = Array.from(document.querySelectorAll("[id^='statusT']")).some(el => {
            const tid = el.id.replace("status", "");
            const trEl = document.getElementById("track" + tid);
            return trEl && trEl.textContent.includes(track) && (el.textContent === "waiting" || el.textContent === "waiting_end");
        });
        if (waitingOnTrack) indicator.setAttribute("stroke", "red");
        else if (blocks.every(b => b === "free")) indicator.setAttribute("stroke", "green");
        else indicator.setAttribute("stroke", "yellow");
    }
}

function updateMetrics(data) {
    document.getElementById("deadlocks").textContent = data.deadlocks;
    let w = 0;
    data.trains.forEach(t => w += (t.waiting_time || 0));
    document.getElementById("waitingTime").textContent = w.toFixed(2) + "s";
    document.getElementById("throughput").textContent = (data.completed_rotations || (data.trains.length * 4 - data.deadlocks));
}

function updateTrains(tr) {
    tr.forEach(t => {
        const trackEl = document.getElementById("track" + t.id);
        const statusEl = document.getElementById("status" + t.id);
        if (trackEl) trackEl.textContent = "Track " + t.track;
        if (statusEl) statusEl.textContent = t.status;
        moveTrainSprite(t);
    });
}

let polling = false;
async function poll() {
    if (polling) return;
    polling = true;
    try {
        const res = await fetch("/state");
        if (!res.ok) throw new Error();
        const data = await res.json();
        updateTrains(data.trains || []);
        updateTrackIndicators(data.trackStatus || {});
        updateMetrics(data || {});
        if (data.running) {
            startBtn.disabled = true;
            pauseBtn.disabled = false;
        } else {
            startBtn.disabled = false;
            pauseBtn.disabled = true;
        }
    } catch (e) {
        logMessage("backend offline");
    } finally {
        polling = false;
    }
}

setInterval(poll, 250);
window.onload = () => {
    logMessage("UI loaded");
    poll();
};
