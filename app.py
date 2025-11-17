from flask import Flask, render_template, jsonify, request
from simulation.simulator import Simulator
import threading
import time
import os

app = Flask(__name__, template_folder="templates", static_folder="static")

sim = Simulator()
sim_lock = threading.Lock()
sim_thread_stop = False

def runner():
    while not sim_thread_stop:
        with sim_lock:
            sim.step()
        time.sleep(sim.TICK)

t = threading.Thread(target=runner, daemon=True)
t.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/state", methods=["GET"])
def state():
    with sim_lock:
        st = sim.export()
        st["running"] = sim.running
    return jsonify(st)

@app.route("/start", methods=["POST"])
def start():
    with sim_lock:
        sim.running = True
    return jsonify({"ok": True, "running": True})

@app.route("/pause", methods=["POST"])
def pause():
    with sim_lock:
        sim.running = False
    return jsonify({"ok": True, "running": False})

@app.route("/reset", methods=["POST"])
def reset():
    with sim_lock:
        sim.reset()
        sim.running = False
    return jsonify({"ok": True, "running": False})

@app.route("/mode", methods=["POST"])
def mode():
    data = request.get_json() or {}
    mode = data.get("mode", "centralized")
    with sim_lock:
        sim.set_controller(mode)
    return jsonify({"ok": True, "mode": mode})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=False)
