from aiohttp import web
import socketio
import os

# Socket.IO server with mobile-friendly keepalive
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=25
)

app = web.Application()
sio.attach(app)

# STATE - Track multiple broadcasters
# Format: { 'sid': { 'name': 'Camera Name', 'viewers': set() } }
broadcasters = {} 

async def index(request):
    filename = 'k-city_index.html'
    if not os.path.exists(filename):
        return web.Response(text="Error: HTML file not found.", status=404)
    return web.FileResponse(filename)

app.router.add_get('/', index)

# --- Helper Functions ---
async def broadcast_camera_list():
    """Sends the list of available cameras to everyone (or just viewers)"""
    camera_list = []
    for sid, data in broadcasters.items():
        camera_list.append({
            'id': sid,
            'name': data['name'],
            'viewers': len(data['viewers'])
        })
    # Emit to everyone so viewers can update their lists
    await sio.emit('camera_list_update', camera_list)

# --- Socket.IO Events ---

@sio.event
async def connect(sid, environ):
    print(f"🔌 Client connected: {sid}")

@sio.event
async def register_broadcaster(sid, name):
    """Called when a user wants to be a camera"""
    print(f"✅ New Camera Registered: {name} ({sid})")
    broadcasters[sid] = {'name': name, 'viewers': set()}
    await sio.emit('broadcaster_ready', skip_sid=sid)
    await broadcast_camera_list()

@sio.event
async def get_cameras(sid):
    """Called by viewers to get the initial list"""
    await broadcast_camera_list()

@sio.event
async def join_stream(sid, target_broadcaster_id):
    """Called when a viewer selects a specific camera"""
    print(f"👀 Viewer {sid} wants to watch {target_broadcaster_id}")
    
    if target_broadcaster_id in broadcasters:
        # Add viewer to that broadcaster's set
        broadcasters[target_broadcaster_id]['viewers'].add(sid)
        
        # Notify that specific broadcaster to send an offer to this viewer
        await sio.emit('watcher_joined', sid, room=target_broadcaster_id)
        
        # Update counts for everyone
        await broadcast_camera_list()
    else:
        await sio.emit('error', "Camera not found or offline", room=sid)

@sio.event
async def disconnect(sid):
    # Case 1: A Broadcaster disconnected
    if sid in broadcasters:
        print(f"❌ Camera {broadcasters[sid]['name']} disconnected")
        
        # Notify all viewers watching this specific camera
        for viewer_sid in broadcasters[sid]['viewers']:
            await sio.emit('broadcaster_left', room=viewer_sid)
        
        del broadcasters[sid]
        await broadcast_camera_list() # Update list for remaining viewers

    # Case 2: A Viewer disconnected
    else:
        # We need to find which broadcaster they were watching to remove them from the count
        found_camera = False
        for cam_id, data in broadcasters.items():
            if sid in data['viewers']:
                data['viewers'].remove(sid)
                print(f"👋 Viewer {sid} left camera {data['name']}")
                
                # Notify that specific broadcaster
                await sio.emit('viewer_left', sid, room=cam_id)
                
                # Check if camera should go to standby (0 viewers)
                if len(data['viewers']) == 0:
                    await sio.emit('all_viewers_left', room=cam_id)
                
                found_camera = True
                break
        
        if found_camera:
            await broadcast_camera_list()

# --- WebRTC Signaling (Relays between specific IDs) ---
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
    print("🚀 K-City Server (Multi-Camera) running on http://0.0.0.0:9005")
    web.run_app(app, host='0.0.0.0', port=9005)