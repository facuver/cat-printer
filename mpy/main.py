import asyncio
import json

import framebuf
import microdot
import network
import YHK
from microdot.microdot import Request, send_file

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("La Casita", "elcuchitril")

# Wait and check
import time

time.sleep(5)
print("IP:", wlan.ifconfig()[0] if wlan.isconnected() else "Not connected")

app = microdot.Microdot()


# Increase max body size to 100KB (adjust as needed)
Request.max_content_length = 1024 * 1024


# Or even larger if needed
# app.max_body_length = 500 * 1024  # 500KB
def create_graphics_framebuffer(w, h):
    return framebuf.FrameBuffer(bytearray((w * h) // 8), w, h, framebuf.MONO_HLSB)


@app.get("/test")
async def print_graphics_demo():
    """Print graphics using FrameBuffer drawing functions"""
    printer = YHK_claude.YHKPrinter()
    if await printer.connect():
        fb = create_graphics_framebuffer(384, 10)
        # Draw border
        fb.fill(1)
        fb.text("Hello", 0, 0, 0)
        await printer.print_framebuffer(fb)
        await printer.disconnect()


@app.get("/")
def index(request):
    return send_file("./index.html")


printer = YHK.YHKPrinter()


@app.post("/print")
async def create_customer(request):
    print(len(request.body))
    if printer.connection:
        await printer.print_raster_image(bytearray(request.body))

        return {"success": True}
    else:
        return {"error": "Failed to connect"}, 500


@app.post("/feed")
async def feed(req):
    await printer.feed_lines(3)
    return


try:
    asyncio.run(printer.connect())
    app.run(
        port=8000,
        debug=True,
    )
except:
    asyncio.run(printer.disconnect())
