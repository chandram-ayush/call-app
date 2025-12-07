from aiohttp import web
import socketio
import os

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# STATE
broadcaster_sid = None
watchers = set()

async def index(request):
    filename = 'k-city_index.html'
    if not os.path.exists(filename):
        return web.Response(text="Error: k-city_index.html not found!", status=404)
    return web.FileResponse(filename)

app.router.add_get('/', index)

# --- SOCKET EVENTS ---

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def broadcaster(sid):
    global broadcaster_sid
    broadcaster_sid = sid
    print(f"✅ Broadcaster registered: {sid}")
    await sio.emit('broadcaster_ready', skip_sid=sid)

@sio.event
async def heartbeat(sid):
    # Keep-alive signal from phone
    pass 

@sio.event
async def check_status(sid):
    # Viewer asks: Is camera online?
    is_online = broadcaster_sid is not None
    await sio.emit('status_response', is_online, room=sid)

@sio.event
async def watcher(sid):
    global broadcaster_sid
    print(f"👀 New Viewer: {sid}")
    if broadcaster_sid:
        watchers.add(sid)
        await sio.emit('watcher', sid, room=broadcaster_sid)
        await sio.emit('update_count', len(watchers))
    else:
        # Tell viewer immediately that camera is offline
        await sio.emit('status_response', False, room=sid)

@sio.event
async def disconnect(sid):
    global broadcaster_sid
    if sid == broadcaster_sid:
        print("❌ Broadcaster disconnected")
        broadcaster_sid = None
        watchers.clear()
        await sio.emit('broadcaster_left')
        await sio.emit('update_count', 0)
    elif sid in watchers:
        watchers.remove(sid)
        await sio.emit('update_count', len(watchers))
        if broadcaster_sid:
             await sio.emit('disconnectPeer', sid, room=broadcaster_sid)

# --- WebRTC Relay ---
@sio.event
async def offer(sid, target_id, message):
    await sio.emit('offer', (sid, message), room=target_id)

@sio.event
async def answer(sid, target_id, message):
    await sio.emit('answer', (sid, message), room=target_id)

@sio.event
async def candidate(sid, target_id, message):
    await sio.emit('candidate', (sid, message), room=target_id)

if __name__ == '__main__':
    print("🚀 Server running on http://0.0.0.0:9005")
    web.run_app(app, host='0.0.0.0', port=9005)