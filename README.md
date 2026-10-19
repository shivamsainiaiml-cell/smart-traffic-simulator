# Smart Traffic Simulator

## Quick start (new dashboard)
- **Windows:** double-click `run.bat` (or run it in Command Prompt).
- **macOS / Linux:** `./run.sh`
- Then open http://127.0.0.1:5000 . Needs Python 3.9+ and an internet connection (Tailwind, Chart.js and fonts load from CDNs).
- Run it from inside this folder: `app.py` imports the `simulation/` package next to it.
- Old frontend files are kept in `_old_frontend/` and are not used any more.

---

# Smart Traffic Signal Simulator

An **educational** simulator of a four-way intersection that compares a conventional **fixed-timing** signal with a rule-based **adaptive** signal. It is a simplified model. It does not connect to, control, or claim to control real traffic signals, and it makes no claim of real-world or scientifically verified improvement.

## Problem statement
Traffic signals that give every road the same green time regardless of demand can leave long queues on busy roads while empty roads keep their green. This project lets students experiment with that trade-off and measure it.

## Objectives
- Simulate a four-way intersection second by second with reproducible (seeded) traffic.
- Implement a fixed-timing baseline and an understandable adaptive controller.
- Compare both on the *same* vehicle arrivals using clearly defined metrics.
- Visualise signals, queues and vehicles, and explain every adaptive decision in plain language.

## Key features
- Python simulation engine (separate, reusable package) with deterministic seeds
- Fixed and adaptive strategies, both obeying yellow and all-red safety intervals
- Metrics: average waiting time, average queue length, throughput, total delay, maximum queue, vehicles remaining
- Fair comparison table (difference and % improvement with correct direction) plus Chart.js charts and trend lines
- Dashboard with start / pause / resume / reset, speed control, timeline scrubbing, custom per-direction traffic
- Automated tests (unittest) for the engine and the API

## Architecture
```
smart-traffic-simulator/
  app.py                    Flask app + JSON API
  simulation/
    config.py               ALL tunable defaults/limits, config validation
    traffic.py              seeded arrival generation, schedule fingerprint
    strategies.py           FixedStrategy, AdaptiveStrategy (decision rules)
    engine.py               1-second simulation loop, comparison runner
    metrics.py              metric definitions, comparison rows
  templates/index.html      dashboard page
  static/css/style.css
  static/js/app.js          API calls, playback, controls, panels
  static/js/visualization.js canvas intersection drawing
  static/js/charts.js       Chart.js charts
  tests/test_simulation.py
  requirements.txt  README.md  .gitignore
```
The backend computes a complete timeline (one frame per second). The browser only plays those frames back; nothing on screen is invented by the frontend.

## Tech stack
Python 3.9+, Flask, vanilla JavaScript, HTML5 canvas, CSS, Chart.js (loaded from the jsDelivr CDN, so charts need an internet connection).

## Installation
### Windows (PowerShell or Command Prompt)
1. Install Python 3.9 or newer from python.org (tick "Add Python to PATH").
2. Open a terminal in the project folder and run:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
3. Open http://127.0.0.1:5000 in your browser.

(PowerShell may block activation scripts. If so, run `Set-ExecutionPolicy -Scope Process RemoteSigned` first, or use Command Prompt.)

### macOS / Linux
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## How to use
1. Pick a strategy to watch (Adaptive or Fixed), a traffic density (Low / Medium / High / Custom), a duration and a seed.
2. **Start** calculates the run on the server and plays it. **Pause**, **Resume**, **Reset** and the speed selector work during playback; drag the timeline to jump around.
3. **New** creates a new random seed (a new scenario). The same seed always reproduces the same arrivals.
4. **Run comparison** runs both strategies on one shared arrival schedule and fills the comparison table and charts. After a comparison, **Start** replays either strategy on that same scenario.
5. Custom density lets you set vehicles per minute for each direction (for example heavy North-South, light East-West).

## Simulation rules (the model)
- 1-second steps; four approaches; phase NS (north+south) and phase EW (east+west) never overlap.
- Each second every approach gets at most one new vehicle with probability equal to its arrival rate. Presets (vehicles/s per approach): low 0.05, medium 0.10, high 0.16.
- A green approach discharges 0.5 vehicles/s (one vehicle every 2 s); yellow and all-red discharge nothing.
- Runs start with empty queues and North-South green, for both strategies.
- Defaults (in `simulation/config.py`): 300 s, yellow 3 s, all-red 1 s, adaptive min green 8 s, max green 30 s, max red 28 s, fixed greens 15 s / 15 s.

## Fixed strategy
Each phase gets a configured green time (15 s by default), then yellow, then all-red, then the other phase. Demand is ignored.

## Adaptive strategy (plain-language explanation)
Once per second, while a phase is green, the controller asks "should this green end now?" and checks these rules in order, using the first that applies:
1. **Minimum green:** keep the green until it has lasted `min_green` seconds.
2. **Maximum green:** end it at `max_green` seconds so no phase hogs the junction.
3. **Fairness:** if the other phase has vehicles waiting and has been non-green for `max_red` seconds, switch.
4. **Gap-out:** if the current phase has no queue but the other does, switch early.
5. **Queue pressure:** if the other phase's queue exceeds the current one by more than `switch_margin`, switch.
6. **Otherwise** extend the green (or hold it if nobody is waiting).

The engine, not the strategy, inserts yellow and all-red, so conflicting greens are impossible. The text in the "Controller decision" panel is the reason string returned by the rule that actually fired. This is a hand-written rule set: it is not AI or machine learning and is not claimed to be optimal. It is not guaranteed to beat fixed timing in every scenario, so always check the numbers for the scenario you ran.

## Metric definitions (same for both strategies)
- **Waiting time of a vehicle:** departure second minus arrival second; for a vehicle still queued at the end, duration minus arrival second.
- **Total delay (vehicle-seconds):** sum of all vehicles' waiting times (departed and still queued). It equals the sum over every second of the total queue length.
- **Average waiting time (s):** total delay / vehicles arrived (0 if none arrived). Vehicles still queued at the end are included, counted up to the end of the run.
- **Average queue length:** (sum of queue lengths over all seconds and all four approaches) / (duration x 4), in vehicles per approach.
- **Throughput:** vehicles that passed through. **Vehicles remaining:** arrived minus throughput. **Maximum queue:** largest queue on any approach at the end of any second.
- **Percentage improvement:** for lower-is-better metrics `(fixed - adaptive) / fixed x 100`; for throughput `(adaptive - fixed) / fixed x 100`. Shown as N/A when the fixed value is 0.

## API
All bodies are JSON. Errors return `{"error": "message"}` with status 400 (bad input), 404, 405 or 500.

`GET /api/config` returns defaults, limits, density presets and strategy names.

`POST /api/simulate` request (all fields optional):
```json
{"strategy": "adaptive", "density": "medium", "duration": 300, "seed": 42,
 "custom_rates": {"north": 12, "south": 12, "east": 4, "west": 4}}
```
`custom_rates` (vehicles/min, 0-60) is required only when `density` is `custom`. Optional timing overrides: `min_green, max_green, max_red, fixed_green_ns, fixed_green_ew, yellow, all_red, discharge_rate, switch_margin`. Omitting `seed` picks a random one (returned in `config.seed`).

Response: `{strategy, config, arrival_checksum, frames[], decisions[], metrics{}}`. Each frame has `t, signals, queues, arrived, departed, departed_total, phase, stage, stage_elapsed, next_transition, reason, rule, cum{}`.

`POST /api/compare` takes the same body (without `strategy`) and returns `{config, arrival_checksum, arrivals_total, fixed{}, adaptive{}, comparison[], series{}, note}`. Both results are produced from one arrival schedule.

## Testing
```
python -m unittest discover -s tests -v
```
The suite covers duration, reproducibility, identical arrivals in comparisons, no departures on red/yellow, no conflicting greens, yellow/all-red lengths, adaptive min/max green, fixed green lengths, the fairness bound, throughput limits, the no-traffic case, non-negative queues, no stale state, invalid configuration, the metric identity, comparison direction logic, and the API endpoints. The frontend (canvas, controls, charts) is not covered by automated tests and should be checked manually in a browser.

## Limitations
- Simplified single-intersection model: no turning movements, multiple lanes, pedestrians, vehicle acceleration, or detector noise.
- Results depend on the seed and settings; one run is one sample, not a statistical conclusion.
- Charts load Chart.js from a CDN and need internet access.
- Intended for demonstration, not for traffic engineering decisions.

## Future enhancements (not implemented)
Computer vision for traffic images, live CCTV, machine/reinforcement learning, multiple connected intersections, real-time sensors, database-backed analytics, user accounts, multi-run statistics.

## Example demonstration for a college presentation
1. Show the dashboard, explain the disclaimer, and Start an **Adaptive** run on Medium density; narrate the decision panel as the rules fire.
2. Pause on a yellow phase and point at the signal table and next-transition field.
3. Reset, choose **Custom** with North/South 12 and East/West 4, keep seed 42, and press **Run comparison**.
4. Walk through the table and charts, noting which strategy wins on each metric and why.
5. Switch to Medium (balanced) density and compare again; the gap is much smaller there. Try several seeds and settings to see whether adaptive always wins (it is not guaranteed to).
6. Change the seed (New) to show the result varies by scenario; reuse a seed to show reproducibility.

## Deploying / sharing a live demo
Nothing has been deployed. To share a demo, host it on a Python-capable service (for example Render, Railway or PythonAnywhere): push the folder to a Git repository, set the start command to `gunicorn app:app` (Linux hosts; `gunicorn` is in `requirements.txt` for non-Windows installs), and share the URL the host provides. On a local network you can instead run `python app.py` and edit the host in `app.py` to `0.0.0.0`.
