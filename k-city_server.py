from aiohttp import web
import socketio
import os

# Increased timeouts to prevent accidental disconnects on mobile
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=25
)

app = web.Application()
sio.attach(app)

# { 'sid': { 'name': 'MyCam', 'viewers': set() } }
broadcasters = {} 

async def index(request):
    filename = 'k-city_index.html'
    if not os.path.exists(filename):
        return web.Response(text="Error: HTML file not found.", status=404)
    return web.FileResponse(filename)

app.router.add_get('/', index)

# --- Events ---

async def broadcast_list():
    """Send updated list to everyone immediately"""
    camera_list = []
    for sid, data in broadcasters.items():
        camera_list.append({'id': sid, 'name': data['name'], 'viewers': len(data['viewers'])})
    await sio.emit('camera_list_update', camera_list)

@sio.event
async def connect(sid, environ):
    print(f"🔌 Connected: {sid}")

@sio.event
async def register_broadcaster(sid, name):
    print(f"✅ Camera Registered: {name}")
    broadcasters[sid] = {'name': name, 'viewers': set()}
    await broadcast_list() 

@sio.event
async def get_cameras(sid):
    await broadcast_list()

@sio.event
async def join_stream(sid, target_id):
    if target_id in broadcasters:
        broadcasters[target_id]['viewers'].add(sid)
        print(f"🔗 Connecting {sid} -> {target_id}")
        # Tell Camera to call this Viewer
        await sio.emit('watcher_joined', sid, room=target_id)
        await broadcast_list()
    else:
        # Crucial: Tell viewer this camera is dead (Ghost ID)
        await sio.emit('error', "Camera unavailable (refreshing list...)", room=sid)
        await broadcast_list()

@sio.event
async def disconnect(sid):
    if sid in broadcasters:
        # Camera disconnects
        print(f"❌ Camera {broadcasters[sid]['name']} left")
        del broadcasters[sid]
        await broadcast_list()
    else:
        # Viewer disconnects
        for cam_id, data in broadcasters.items():
            if sid in data['viewers']:
                data['viewers'].remove(sid)
                await sio.emit('viewer_left', sid, room=cam_id)
                if len(data['viewers']) == 0:
                    await sio.emit('stop_broadcasting', room=cam_id)
                await broadcast_list()

# --- WebRTC Pass-through ---
@sio.event
async def offer(sid, target_id, msg):
    await sio.emit('offer', (sid, msg), room=target_id)

@sio.event
async def answer(sid, target_id, msg):
    await sio.emit('answer', (sid, msg), room=target_id)

@sio.event
async def candidate(sid, target_id, msg):
    await sio.emit('candidate', (sid, msg), room=target_id)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=9005)