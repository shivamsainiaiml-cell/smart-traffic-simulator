"""Live API: one LiveJunction per browser tab, streamed to the dashboard with Server-Sent Events.

GET  /api/live/stream?sid=<id>   text/event-stream. Sends one "init" event (full scene), then one
                                 "frame" event per simulated second (paced by the chosen speed).
POST /api/live/control           JSON {sid, mode?, density?, speed?, paused?, manual_phase?,
                                 fixed_green?, override?, spawn?, reset?}  ->  current state

Sessions live in this process's memory, so run ONE worker process (threads are fine):
    gunicorn -w 1 -k gthread --threads 16 app:app
"""
import json
import re
import threading
import time

from flask import Blueprint, Response, jsonify, request, stream_with_context

from simulation.live import LiveJunction

live_bp = Blueprint("live", __name__)

SID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
MAX_SESSIONS = 200
IDLE_SECONDS = 30 * 60
_sessions = {}
_sessions_lock = threading.Lock()


class Session:
    def __init__(self):
        self.junction = LiveJunction()
        self.token = 0                 # only the newest stream for a session keeps ticking
        self.last_seen = time.monotonic()


def _get_session(sid):
    if not isinstance(sid, str) or not SID_RE.match(sid):
        raise ValueError("'sid' must be 8-64 characters: letters, digits, '-' or '_'.")
    now = time.monotonic()
    with _sessions_lock:
        for key in [k for k, s in _sessions.items() if now - s.last_seen > IDLE_SECONDS]:
            del _sessions[key]
        if sid not in _sessions:
            if len(_sessions) >= MAX_SESSIONS:
                raise ValueError("Too many active sessions. Try again later.")
            _sessions[sid] = Session()
        s = _sessions[sid]
        s.last_seen = now
        return s


def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


@live_bp.get("/api/live/stream")
def live_stream():
    s = _get_session(request.args.get("sid"))
    s.token += 1
    token = s.token

    @stream_with_context
    def generate():
        j = s.junction
        yield "retry: 1500\n\n"
        yield _sse("init", j.snapshot())
        next_at = time.monotonic()
        last_beat = next_at
        while s.token == token:
            now = time.monotonic()
            s.last_seen = now
            if j.paused:
                if now - last_beat > 15:
                    last_beat = now
                    yield ": keep-alive\n\n"
                time.sleep(0.1)
                next_at = time.monotonic()
                continue
            yield _sse("frame", j.tick())
            next_at += 1.0 / j.speed
            delay = next_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_at = time.monotonic()

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@live_bp.post("/api/live/control")
def live_control():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    s = _get_session(data.get("sid"))
    return jsonify(s.junction.apply_control({k: v for k, v in data.items() if k != "sid"}))
