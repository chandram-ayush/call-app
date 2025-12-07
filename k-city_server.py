from aiohttp import web
import socketio
import os

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# STATE MANAGEMENT
broadcaster_sid = None
watchers = set() # Set to store unique viewer SIDs

# --- SERVE HTML ---
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
    # Reset watchers on new broadcast session
    watchers.clear()
    await sio.emit('broadcaster_ready', skip_sid=sid)

@sio.event
async def watcher(sid):
    global broadcaster_sid
    print(f"👀 New Viewer: {sid}")
    
    if broadcaster_sid:
        watchers.add(sid)
        # 1. Tell Broadcaster to connect to THIS specific viewer
        await sio.emit('watcher', sid, room=broadcaster_sid)
        # 2. Update everyone on the count
        await sio.emit('update_count', len(watchers))
    else:
        print("❌ No broadcaster available")

@sio.event
async def disconnect(sid):
    global broadcaster_sid
    
    # CASE 1: Broadcaster Disconnects
    if sid == broadcaster_sid:
        print("❌ Broadcaster disconnected")
        broadcaster_sid = None
        watchers.clear()
        await sio.emit('broadcaster_left')
        await sio.emit('update_count', 0)

    # CASE 2: Viewer Disconnects
    elif sid in watchers:
        print(f"Viewer {sid} left")
        watchers.remove(sid)
        
        # Update count for remaining viewers
        await sio.emit('update_count', len(watchers))
        
        # Tell Broadcaster to drop this specific connection
        if broadcaster_sid:
             await sio.emit('disconnectPeer', sid, room=broadcaster_sid)

# --- WebRTC Signaling Relay ---
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