// Simulation state & elements
const trains = [
    { id: "T1", elemId: "trainT1", color: "#e74c3c", speed: 30, currentTrack: "A", status: "Running", posPercent: 0 },
    { id: "T2", elemId: "trainT2", color: "#3498db", speed: 25, currentTrack: "B", status: "Running", posPercent: 0 },
    { id: "T3", elemId: "trainT3", color: "#f1c40f", speed: 35, currentTrack: "C", status: "Running", posPercent: 0 },
];

const trackIndicators = {
    A: document.getElementById("trackAIndicator"),
    B: document.getElementById("trackBIndicator"),
    C: document.getElementById("trackCIndicator")
};

const trainElements = {
    T1: document.getElementById("trainT1"),
    T2: document.getElementById("trainT2"),
    T3: document.getElementById("trainT3"),
};

let simulationTimer = null;
let simulationRunning = false;

const logArea = document.getElementById("logMessages");
const modeSelect = document.getElementById("modeSelect");
const simulationModeLabel = document.getElementById("simulationModeLabel");

// Utility to log messages with timestamp
function logMessage(msg) {
    const time = new Date().toLocaleTimeString();
    const messageElem = document.createElement("div");
    messageElem.textContent = `[${time}] ${msg}`;
    logArea.appendChild(messageElem);
    logArea.scrollTop = logArea.scrollHeight;
}

// Update train details in sidebar
function updateTrainDetails() {
    trains.forEach(train => {
        document.getElementById("speed" + train.id).textContent = train.speed + " km/h";
        document.getElementById("track" + train.id).textContent = "Track " + train.currentTrack;
        document.getElementById("status" + train.id).textContent = train.status;
    });
}

// Move trains along their current tracks (simple horizontal movement)
function moveTrains() {
    trains.forEach(train => {
        train.posPercent += (train.speed / 10);
        if (train.posPercent > 100) {
            // Switch track randomly for simulation
            const oldTrack = train.currentTrack;
            const tracks = ["A", "B", "C"];
            const newTrack = tracks[Math.floor(Math.random() * tracks.length)];
            train.currentTrack = newTrack;
            train.posPercent = 0;

            // Update train elements visually to new track (y coordinate varies by track)
            logMessage(`Train ${train.id} acquired Track ${newTrack}`);

            // Reset track indicators randomly for demo
            const colors = ["green", "red", "yellow"];
            tracks.forEach(t => {
                trackIndicators[t].setAttribute("stroke", colors[Math.floor(Math.random() * colors.length)]);
            });
        }

        // Update visual train position on SVG
        const trainElem = trainElements[train.id];
        if (!trainElem) return;

        let x = 50 + (5 * train.posPercent); // horizontal movement along the track line 50 to 550
        let y;
        switch (train.currentTrack) {
            case "A":
                y = 350;
                break;
            case "B":
                y = 200;
                break;
            case "C":
                y = 50;
                break;
            default:
                y = 350;
        }

        if (trainElem.tagName === "circle") {
            trainElem.setAttribute("cx", x);
            trainElem.setAttribute("cy", y);
        } else if (trainElem.tagName === "rect") {
            trainElem.setAttribute("x", x - 12);
            trainElem.setAttribute("y", y - 12);
        }
    });
    updateTrainDetails();
}

// Start simulation
function startSimulation() {
    if (!simulationRunning) {
        simulationTimer = setInterval(() => {
            moveTrains();
        }, 500);
        simulationRunning = true;
        document.getElementById("startBtn").disabled = true;
        document.getElementById("pauseBtn").disabled = false;
        logMessage("Simulation started");
    }
}

// Pause simulation
function pauseSimulation() {
    if (simulationRunning) {
        clearInterval(simulationTimer);
        simulationRunning = false;
        document.getElementById("startBtn").disabled = false;
        document.getElementById("pauseBtn").disabled = true;
        logMessage("Simulation paused");
    }
}

// Reset simulation to initial state
function resetSimulation() {
    pauseSimulation();
    trains.forEach(train => {
        train.posPercent = 0;
        // Reset tracks arbitrarily to initial
        if (train.id === "T1") train.currentTrack = "A";
        if (train.id === "T2") train.currentTrack = "B";
        if (train.id === "T3") train.currentTrack = "C";
        train.status = "Running";
    });
    // Reset train positions
    trains.forEach(train => {
        const trainElem = trainElements[train.id];
        if (!trainElem) return;
        let x = 50;
        let y;
        switch (train.currentTrack) {
            case "A":
                y = 350;
                break;
            case "B":
                y = 200;
                break;
            case "C":
                y = 50;
                break;
            default:
                y = 350;
        }
        if (trainElem.tagName === "circle") {
            trainElem.setAttribute("cx", x);
            trainElem.setAttribute("cy", y);
        } else if (trainElem.tagName === "rect") {
            trainElem.setAttribute("x", x - 12);
            trainElem.setAttribute("y", y - 12);
        }
    });

    // Reset track indicators to green (free)
    ["A", "B", "C"].forEach(t => {
        trackIndicators[t].setAttribute("stroke", "green");
    });

    // Reset metrics
    document.getElementById("throughput").textContent = "--";
    document.getElementById("waitingTime").textContent = "--";
    document.getElementById("deadlocks").textContent = "--";

    // Clear logs
    logArea.innerHTML = "";
    logMessage("Simulation reset");
    updateTrainDetails();
}

// Update mode label on dropdown change
modeSelect.addEventListener("change", (e) => {
    const mode = e.target.value === "centralized" ? "Centralized Controller" : "Ordered Locking";
    simulationModeLabel.textContent = `Simulation Mode: ${mode}`;
    logMessage(`Simulation mode changed to ${mode}`);
});

document.getElementById("startBtn").addEventListener("click", startSimulation);
document.getElementById("pauseBtn").addEventListener("click", pauseSimulation);
document.getElementById("resetBtn").addEventListener("click", resetSimulation);

// Initialize positions and states on page load
window.onload = () => {
    resetSimulation();
};
