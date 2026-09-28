import asyncio
import struct
import wifi
from YHK import YHKPrinter
# ... (your YHKPrinter class code here) ...

from fonts import big_font as font

async def handle_tcp_client(reader, writer, printer:YHKPrinter):

    print("💻 Linux/Windows connected to network port")
    print(reader.__dict__)
    try:
        while True:
            # Read a chunk of data from the network (CUPS/Windows)
            data = await reader.read(1024)
            if not data:
                break

            # Send the raw bytes (which already contain GS v 0 from the driver)
            # directly to the BLE printer
            text = data.decode("utf-8").strip()
            await printer.print_text(text,font)
            print("sending: ",text)

    except Exception as e:
        print(f"❌ Connection error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def serve(printer:YHKPrinter):

    # Start a TCP server on port 9100
    server = await asyncio.start_server(
        lambda r, w: handle_tcp_client(r, w, printer),
        "0.0.0.0", 9100
    )
    print("🚀 Bridge Active! Point Linux to port 9100")
    async with server:
        await asyncio.sleep(3600)
