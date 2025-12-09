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



# STATE - Track multiple viewers

broadcaster_sid = None

watchers = set()  # Track ALL active viewers



async def index(request):

    filename = 'k-city_index.html'

    if not os.path.exists(filename):

        print(f"❌ ERROR: Could not find {filename}")

        print(f"   Current folder: {os.getcwd()}")

        return web.Response(text="Error: HTML file not found.", status=404)

    return web.FileResponse(filename)



app.router.add_get('/', index)



# --- Socket.IO Events ---



@sio.event

async def connect(sid, environ):

    print(f"🔌 Client connected: {sid}")



@sio.event

async def broadcaster(sid):

    global broadcaster_sid

    broadcaster_sid = sid

    print(f"✅ Broadcaster registered: {sid}")

    await sio.emit('broadcaster_ready', skip_sid=sid)



@sio.event

async def watcher(sid):

    global broadcaster_sid

    print(f"👀 Viewer {sid} joined (Total: {len(watchers)+1})")

   

    if broadcaster_sid:

        watchers.add(sid)  # Add to active viewers

        print(f"📊 Active viewers: {len(watchers)}")

        await sio.emit('watcher', sid, room=broadcaster_sid)  # Notify broadcaster

    else:

        print("❌ No broadcaster available")

        await sio.emit('no_broadcaster', room=sid)



@sio.event

async def disconnect(sid):

    global broadcaster_sid

   

    if sid == broadcaster_sid:

        print("❌ Broadcaster disconnected")

        broadcaster_sid = None

        watchers.clear()

        await sio.emit('broadcaster_left')

        print("🔄 All viewers cleared")

    elif sid in watchers:

        watchers.remove(sid)

        print(f"👋 Viewer {sid} left (Remaining: {len(watchers)})")

       

        # Only notify broadcaster if it still exists

        if broadcaster_sid and len(watchers) > 0:

            await sio.emit('viewer_left', sid, room=broadcaster_sid)

        elif broadcaster_sid and len(watchers) == 0:

            # LAST viewer left - tell broadcaster to go to standby

            await sio.emit('all_viewers_left', room=broadcaster_sid)

            print("🏠 LAST viewer left - broadcaster to standby")



# --- WebRTC Signaling (1:1 per viewer) ---

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

    print("🚀 K-City Server (Multi-Viewer) running on http://0.0.0.0:9005")

    web.run_app(app, host='0.0.0.0', port=9005)