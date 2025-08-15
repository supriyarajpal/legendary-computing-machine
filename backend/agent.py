import asyncio
import json
import math
import time
from collections import deque
from threading import Thread
import win32api  # pywin32

import websockets
from river import anomaly

WINDOW_S = 2.5
SEND_INTERVAL = 1.0
POLL_INTERVAL = 0.01  # seconds between position checks

events = deque()

hst = anomaly.HalfSpaceTrees(
    seed=42,
    n_trees=25,
    height=8,
    window_size=50
)

WARMUP_SAMPLES = 20
samples_seen = 0


def mouse_polling_loop():
    """Continuously poll the mouse position."""
    while True:
        x, y = win32api.GetCursorPos()
        ts = time.time()
        events.append((ts, x, y))

        cutoff = ts - WINDOW_S
        while events and events[0][0] < cutoff:
            events.popleft()

        time.sleep(POLL_INTERVAL)


def start_mouse_listener():
    """Start the mouse polling thread."""
    t = Thread(target=mouse_polling_loop, daemon=True)
    t.start()


def compute_features():
    ev = list(events)
    n = len(ev)
    if n < 2:
        return None

    speeds, deltas, angles = [], [], []

    for i in range(1, n):
        t0, x0, y0 = ev[i - 1]
        t1, x1, y1 = ev[i]
        dt = t1 - t0 if (t1 - t0) > 0 else 1e-6
        dx = x1 - x0
        dy = y1 - y0
        dist = math.hypot(dx, dy)
        speeds.append(dist / dt)
        deltas.append(dist)
        angles.append(math.atan2(dy, dx))

    mean_speed = sum(speeds) / len(speeds)
    std_speed = math.sqrt(sum((s - mean_speed) ** 2 for s in speeds) / len(speeds))
    mean_delta = sum(deltas) / len(deltas)
    jitter = math.sqrt(sum((d - mean_delta) ** 2 for d in deltas) / len(deltas))

    dir_changes = 0
    for i in range(1, len(angles)):
        diff = angles[i] - angles[i - 1]
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        if abs(diff) > math.radians(30):
            dir_changes += 1

    return {
        'timestamp': int(time.time() * 1000),
        'sample_count': n,
        'mean_speed': mean_speed,
        'std_speed': std_speed,
        'jitter': jitter,
        'direction_changes': dir_changes,
    }


async def ws_handler(websocket):
    global samples_seen
    print(f'Client connected: {websocket.remote_address}')

    await websocket.send(json.dumps({
        'timestamp': int(time.time() * 1000),
        'status': 'connected',
        'message': 'Hello from Python agent — waiting for mouse activity'
    }))

    try:
        while True:
            features = compute_features()
            if features:
                river_features = {
                    'mean_speed': features['mean_speed'] / 1000,
                    'std_speed': features['std_speed'] / 1000,
                    'jitter': features['jitter'] / 1000,
                    'direction_changes': features['direction_changes'] / 10,
                    'sample_count': features['sample_count'] / 100
                }

                if samples_seen < WARMUP_SAMPLES:
                    hst.learn_one(river_features)
                    features['anomaly_score'] = None
                    samples_seen += 1
                    print(f"Warming up model... ({samples_seen}/{WARMUP_SAMPLES})")
                else:
                    score = hst.score_one(river_features)
                    features['anomaly_score'] = score
                    hst.learn_one(river_features)
                    print(f"Anomaly score: {score:.4f}")

                await websocket.send(json.dumps(features))
            await asyncio.sleep(SEND_INTERVAL)
    except websockets.exceptions.ConnectionClosed:
        print('Client disconnected')


async def start_server():
    server = await websockets.serve(ws_handler, 'localhost', 8765)
    print('WebSocket server started on ws://localhost:8765')
    await server.wait_closed()


if __name__ == '__main__':
    start_mouse_listener()
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print('Shutting down')
