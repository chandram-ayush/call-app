from aiohttp import web
import socketio
import os

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# Global variable to track the broadcaster
broadcaster_sid = None

# --- Serve the HTML File (FIXED) ---
async def index(request):
    filename = 'k-city_index.html'
    
    # 1. Debugging: Show where we are looking
    if not os.path.exists(filename):
        print(f"❌ ERROR: Could not find {filename}")
        print(f"   Current folder: {os.getcwd()}")
        return web.Response(text="Error: HTML file not found.", status=404)

    # 2. FileResponse avoids the UnicodeDecodeError completely
    return web.FileResponse(filename)

app.router.add_get('/', index)

# --- Socket.IO Events ---

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
async def watcher(sid):
    global broadcaster_sid
    print(f"👀 Caller {sid} wants to watch")
    if broadcaster_sid:
        await sio.emit('watcher', sid, room=broadcaster_sid)
    else:
        print("❌ No broadcaster available")

@sio.event
async def disconnect(sid):
    global broadcaster_sid
    if sid == broadcaster_sid:
        print("❌ Broadcaster disconnected")
        broadcaster_sid = None
        await sio.emit('broadcaster_left')
    else:
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