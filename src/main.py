import asyncio
import json
import nc_client
import microdot
import YHK
from microdot.microdot import Request, send_file, redirect
import time
import network
from machine import Pin

from wifi import connect_and_configure_wifi,wlan

from fonts import big_font ,small_font

app = microdot.Microdot()
printer = YHK.YHKPrinter()

led = Pin("LED",Pin.OUT)

# Increase max body size to 100KB (adjust as needed)
Request.max_content_length = 1024 * 1024



@app.get("/")
def index(request):
    return send_file("/www/index.html")

@app.get("/tareas")
def index(request):
    return send_file("/www/tareas.html")

# async def keep_alive():
#     while True:
#         await asyncio.sleep(5)
#         led.on()
#         await printer.print_bitmap(b'')
#         led.off()

@app.post("/text")
async def print_text(request:Request):
    print(request.form)
    font = big_font if "bold" in request.form.keys() else small_font
    await printer.print_text(request.form["text_content"],font)
    await printer.feed_lines(3)
    redirect ("/text")



@app.post("/print")
async def print_bitmap(request):
    if printer.connection is None:
        await printer.connect()
    if printer.connection:
        await printer.print_bitmap(bytearray(request.body))
        return {"success": True}
    else:
        return {"error": "Failed to connect"}, 500


@app.post("/feed")
async def feed(req):
    await printer.feed_lines(3)
    return

@app.get("/<file>")
def www_resources(request, file):
    return send_file(f"www/{file}")


async def main():
    asyncio.create_task(connect_and_configure_wifi())
    asyncio.create_task(printer.connect())
    asyncio.create_task(nc_client.serve(printer))
    try:
        # The 'run' function was undefined. Microdot applications are started
        # asynchronously using `app.start_server` when integrated into an
        # existing asyncio event loop.
        await app.start_server(port=80, debug=True)
    finally:
        # Ensure the printer disconnects when the main application loop finishes,
        # whether due to a graceful shutdown or an unhandled exception.
        await printer.disconnect()

try:
    # `app.run()` is typically used to start a Microdot server and its own
    # asyncio loop. When `main()` is intended to orchestrate multiple
    # async tasks including the server, `asyncio.run(main())` is the
    # appropriate way to execute the main coroutine.
    asyncio.run(main())
except:
    # The printer disconnection is now handled in the `finally` block of `main()`,
    # so this `except` block can be empty or log the exception.
    pass
