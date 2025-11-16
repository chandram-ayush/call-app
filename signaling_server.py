from aiohttp import web
import socketio
from datetime import datetime

devices = {}
active_streams = {}

DEVICE_WHITELIST = {
    'receiver_device_001': ['caller_device_001'],
    'caller_device_001': ['receiver_device_001']
}

sio = socketio.AsyncServer(
    cors_allowed_origins='*',
    async_mode='aiohttp',
    max_http_buffer_size=10000000  # 10MB for video frames
)
app = web.Application()
sio.attach(app)

async def index(request):
    html = f"""
    <html>
    <head><title>Video Server</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body {{font-family: Arial; padding: 20px; background: #1a1a1a; color: white;}}
        .card {{background: #2d2d2d; padding: 20px; margin: 15px 0; border-radius: 10px;}}
        .status {{color: #4CAF50; font-size: 24px;}}
    </style>
    </head>
    <body>
        <h1>📹 Video Server</h1>
        <div class="card">
            <div class="status">● RUNNING</div>
            <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Address: http://192.168.0.6:8080</p>
        </div>
        <div class="card">
            <h2>Connected: {len(devices)}</h2>
            {('<br>'.join([f'📱 {d}' for d in devices.keys()]) if devices else 'None')}
        </div>
        <div class="card">
            <h2>Active Streams: {len(active_streams)}</h2>
            {('<br>'.join([f'🎬 {s} → {v}' for s,v in active_streams.items()]) if active_streams else 'None')}
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

app.router.add_get('/', index)

@sio.event
async def connect(sid, environ):
    print(f'✅ Connected: {sid[:8]}... from {environ.get("REMOTE_ADDR")}')

@sio.event
async def disconnect(sid):
    print(f'❌ Disconnected: {sid[:8]}...')
    device_id = None
    for dev_id, dev_sid in devices.items():
        if dev_sid == sid:
            device_id = dev_id
            break
    if device_id:
        devices.pop(device_id, None)
        if device_id in active_streams:
            viewer = active_streams.pop(device_id)
            if viewer in devices:
                await sio.emit('stream_stopped', {}, room=devices[viewer])
        print(f'   Removed: {device_id}')

@sio.event
async def register_device(sid, data):
    device_id = data.get('device_id')
    device_type = data.get('type', 'unknown')
    if not device_id:
        await sio.emit('error', {'message': 'Device ID required'}, room=sid)
        return
    devices[device_id] = sid
    print(f'📱 Registered: {device_id} ({device_type}) - Total: {len(devices)}')
    await sio.emit('registered', {'device_id': device_id, 'type': device_type}, room=sid)
    if device_type == 'receiver' and 'caller_device_001' in devices:
        await sio.emit('receiver_online', {'receiver_id': device_id}, room=devices['caller_device_001'])

@sio.event
async def request_stream(sid, data):
    caller_id = data.get('caller_id')
    receiver_id = data.get('receiver_id')
    if caller_id not in DEVICE_WHITELIST.get(receiver_id, []):
        await sio.emit('error', {'message': 'Not authorized'}, room=sid)
        return
    if receiver_id not in devices:
        await sio.emit('error', {'message': 'Receiver offline'}, room=sid)
        return
    receiver_sid = devices[receiver_id]
    await sio.emit('start_streaming', {'viewer_id': caller_id}, room=receiver_sid)
    active_streams[receiver_id] = caller_id
    print(f'🎬 Stream: {receiver_id} → {caller_id}')

@sio.event
async def video_frame(sid, data):
    sender_id = data.get('sender_id')
    frame_data = data.get('frame')
    if sender_id and sender_id in active_streams:
        viewer_id = active_streams[sender_id]
        if viewer_id in devices:
            await sio.emit('video_frame', {'frame': frame_data, 'from': sender_id}, room=devices[viewer_id])

@sio.event
async def stop_viewing(sid, data):
    caller_id = data.get('caller_id')
    for receiver_id, viewer_id in list(active_streams.items()):
        if viewer_id == caller_id:
            if receiver_id in devices:
                await sio.emit('stop_streaming', {}, room=devices[receiver_id])
            active_streams.pop(receiver_id, None)
            print(f'⏹️  Stopped: {receiver_id} → {caller_id}')
@sio.event
async def change_quality(sid, data):
    """Relay quality change request to receiver"""
    receiver_id = data.get('receiver_id')
    quality = data.get('quality')
    
    if receiver_id in devices:
        receiver_sid = devices[receiver_id]
        await sio.emit('change_quality', {'quality': quality}, room=receiver_sid)
        print(f'🎨 Quality changed to {quality} for {receiver_id}')


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    
    print('=' * 70)
    print('📹 VIDEO SERVER - Cloud')
    print('=' * 70)
    print(f'Running on port {port}')
    print('=' * 70)
    
    web.run_app(app, host='0.0.0.0', port=port)
