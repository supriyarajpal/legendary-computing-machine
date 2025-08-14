"""
MouseAgent WebSocket server
- Captures mouse move events via pynput
- Keeps a sliding window (e.g., 5s) of recent events
- Every 2 seconds computes features and streams them to connected WebSocket clients

Features computed:
- mean_speed (pixels/sec)
- std_speed
- jitter (std of short-delta magnitudes)
- direction_changes (count of large angle changes)
- sample_count

Run: python agent.py
"""

import asyncio
import json
import math
import time
from collections import deque
from threading import Thread

import websockets
from pynput import mouse

# sliding window length (seconds)
WINDOW_S = 5.0
SEND_INTERVAL = 2.0

# store (ts, x, y)
events = deque()

# thread-safe append from listener

def on_move(x, y):
    ts = time.time()
    events.append((ts, x, y))
    # trim older than WINDOW_S
    cutoff = ts - WINDOW_S
    while events and events[0][0] < cutoff:
        events.popleft()


def start_mouse_listener():
    listener = mouse.Listener(on_move=on_move)
    listener.start()
    return listener


def compute_features():
    # copy events to local list
    ev = list(events)
    n = len(ev)
    if n < 2:
        return None

    speeds = []
    deltas = []
    angles = []

    for i in range(1, n):
        t0, x0, y0 = ev[i - 1]
        t1, x1, y1 = ev[i]
        dt = t1 - t0 if (t1 - t0) > 0 else 1e-6
        dx = x1 - x0
        dy = y1 - y0
        dist = math.hypot(dx, dy)
        speed = dist / dt
        speeds.append(speed)
        deltas.append(dist)
        angle = math.atan2(dy, dx)
        angles.append(angle)

    # mean and std speed
    mean_speed = sum(speeds) / len(speeds)
    var_speed = sum((s - mean_speed) ** 2 for s in speeds) / len(speeds)
    std_speed = math.sqrt(var_speed)

    # jitter: std of small deltas
    mean_delta = sum(deltas) / len(deltas)
    var_delta = sum((d - mean_delta) ** 2 for d in deltas) / len(deltas)
    jitter = math.sqrt(var_delta)

    # count large direction changes
    dir_changes = 0
    for i in range(1, len(angles)):
        # difference in angle normalized to [-pi,pi]
        diff = angles[i] - angles[i - 1]
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        if abs(diff) > math.radians(30):
            dir_changes += 1

    features = {
        'timestamp': time.time(),
        'sample_count': n,
        'mean_speed': mean_speed,
        'std_speed': std_speed,
        'jitter': jitter,
        'direction_changes': dir_changes,
    }
    return features


async def ws_handler(websocket):
    print(f'Client connected: {websocket.remote_address}')

    await websocket.send(json.dumps({
        'timestamp': int(time.time() * 1000),
        'status': 'connected',
        'message': 'Hello from Python agent — waiting for mouse activity'
    }))
    
    try:
        while True:
            features = compute_features()
            if features is not None:
                features['timestamp'] = int(features['timestamp'] * 1000)
                await websocket.send(json.dumps(features))
            await asyncio.sleep(SEND_INTERVAL)
    except websockets.exceptions.ConnectionClosed:
        print('Client disconnected')


async def start_server():
    server = await websockets.serve(ws_handler, 'localhost', 8765)
    print('WebSocket server started on ws://localhost:8765')
    await server.wait_closed()


if __name__ == '__main__':
    # Start mouse listener in non-blocking thread
    start_mouse_listener()
    # Start asyncio event loop for websocket server
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print('Shutting down')