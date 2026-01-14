import asyncio
import json

import microdot
import YHKgm as YHK
from microdot.microdot import Request, send_file
import time
import network


wlan = network.WLAN(network.STA_IF)
app = microdot.Microdot()
printer = YHK.YHKPrinter()

async def connect_and_configure_wifi():
    """
    Asynchronously connects to the Wi-Fi network and configures the device's hostname.
    This function encapsulates the Wi-Fi connection logic, including activation, connection,
    waiting for an IP address, and setting the hostname.
    It should be awaited from an asynchronous context, typically the main application task.
    """
    print("Activating WLAN interface...")
    wlan.active(True)

    # Credentials are hardcoded as in the original snippet.
    ssid = "La Casita"
    password = "elcuchitril"

    print(f"Attempting to connect to Wi-Fi network: '{ssid}'...")
    wlan.connect(ssid, password)

    # Asynchronously wait for connection with a timeout
    max_wait_seconds = 60 # Allow up to 60 seconds for connection
    status_messages = {
        0: "IDLE", 1: "CONNECTING", 2: "WRONG_PASSWORD",
        3: "NO_AP_FOUND", 4: "CONNECT_FAIL", 5: "GOT_IP"
    }

    for i in range(max_wait_seconds):
        if wlan.isconnected():
            break
        current_status = wlan.status()
        status_text = status_messages.get(current_status, f"UNKNOWN ({current_status})")
        print(f"Waiting for Wi-Fi connection... Status: {status_text} ({i+1}/{max_wait_seconds})")
        await asyncio.sleep(1) # Yield control to other tasks

    if wlan.isconnected():
        ip_address = wlan.ifconfig()[0]
        print(f"Wi-Fi connected successfully! IP: {ip_address}")
        wlan.config(hostname='ThermalPrinter')
        print("Hostname set to 'ThermalPrinter'.")
        return True
    else:
        print("Failed to connect to Wi-Fi within the timeout.")
        return False





# Increase max body size to 100KB (adjust as needed)
Request.max_content_length = 1024 * 1024



@app.get("/")
def index(request):
    return send_file("./index.html")




@app.post("/print")
async def print_bitmap(request):
    if not printer.connection:
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


async def main():
    asyncio.create_task(printer.connect())
    asyncio.create_task(connect_and_configure_wifi())
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
