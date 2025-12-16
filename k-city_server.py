from aiohttp import web
import socketio
import os

sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*', ping_timeout=60)
app = web.Application()
sio.attach(app)

# State: { 'sid': { 'name': 'CamName', 'viewers': set() } }
broadcasters = {} 

async def index(request):
    filename = 'k-city_index.html'
    if not os.path.exists(filename):
        return web.Response(text="Error: HTML file not found.", status=404)
    return web.FileResponse(filename)

app.router.add_get('/', index)

# --- Helpers ---
async def broadcast_list():
    """Update camera list for everyone in the lobby"""
    data = [{'id': k, 'name': v['name'], 'viewers': len(v['viewers'])} for k, v in broadcasters.items()]
    await sio.emit('camera_list_update', data)

# --- Events ---
@sio.event
async def connect(sid, environ):
    print(f"🔌 Connected: {sid}")

@sio.event
async def register_broadcaster(sid, name):
    broadcasters[sid] = {'name': name, 'viewers': set()}
    print(f"✅ Camera Started (Standby): {name}")
    await broadcast_list()

@sio.event
async def stop_broadcast(sid):
    if sid in broadcasters:
        print(f"🛑 Camera Stopped: {broadcasters[sid]['name']}")
        # Notify all viewers to leave
        for viewer in broadcasters[sid]['viewers']:
            await sio.emit('broadcaster_left', room=viewer)
        del broadcasters[sid]
        await broadcast_list()

@sio.event
async def get_cameras(sid):
    await broadcast_list()

@sio.event
async def join_stream(sid, target_id):
    if target_id in broadcasters:
        broadcasters[target_id]['viewers'].add(sid)
        count = len(broadcasters[target_id]['viewers'])
        
        # Notify broadcaster that a watcher joined, SEND TOTAL COUNT
        await sio.emit('watcher_joined', (sid, count), room=target_id)
        
        await broadcast_list()
    else:
        await sio.emit('error', "Camera not found", room=sid)

@sio.event
async def leave_stream(sid):
    """Viewer manually leaves"""
    for cam_id, data in broadcasters.items():
        if sid in data['viewers']:
            data['viewers'].remove(sid)
            count = len(data['viewers'])
            
            # Notify broadcaster that a watcher left, SEND TOTAL COUNT
            await sio.emit('viewer_left', (sid, count), room=cam_id)
            
            await broadcast_list()
            break

@sio.event
async def disconnect(sid):
    # Handle unexpected disconnects
    if sid in broadcasters:
        await stop_broadcast(sid)
    else:
        await leave_stream(sid)

# --- WebRTC Signaling ---
@sio.event
async def offer(sid, target, msg): await sio.emit('offer', (sid, msg), room=target)
@sio.event
async def answer(sid, target, msg): await sio.emit('answer', (sid, msg), room=target)
@sio.event
async def candidate(sid, target, msg): await sio.emit('candidate', (sid, msg), room=target)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=9005)