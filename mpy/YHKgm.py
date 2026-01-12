import asyncio
import gc

import aioble
import bluetooth

# Constants
PRINTER_NAME = "YHK-4118"
_UART_SERVICE_UUID = bluetooth.UUID("49535343-FE7D-4AE5-8FA9-9FAFD205E455")
_UART_RX_CHAR_UUID = bluetooth.UUID("49535343-8841-43F4-A8D4-ECBE34729BB3")


class RawBitmapPrinter:
    def __init__(self):
        self.connection = None
        self.rx_char = None
        self.mtu = 20
        # GS v 0 [m] [xL xH yL yH]
        # We define header for 1 line (yL=1, yH=0) and 48 bytes wide (xL=48, xH=0)
        self.raster_header = bytes([0x1D, 0x76, 0x30, 0x00, 48, 0x00, 0x01, 0x00])

    async def connect(self):
        print("🔍 Locating printer...")
        async with aioble.scan(5000) as scanner:
            async for result in scanner:
                if result.name() == PRINTER_NAME:
                    print("Locaed Printer!")
                    try:
                        self.connection = await result.device.connect(timeout_ms=5000)
                        # Ask for max MTU to speed up the JS data transfer
                        self.mtu = await self.connection.exchange_mtu(123) - 3
                        service = await self.connection.service(_UART_SERVICE_UUID)
                        self.rx_char = await service.characteristic(_UART_RX_CHAR_UUID)
                        print(f"✅ Connected (MTU: {self.mtu})")
                        return True
                    except Exception as e:
                        print(f"❌ Connection failed: {e}")
        return False

    async def send_payload(self, data):
        """Reliable chunked sender with EALREADY prevention"""
        mv = memoryview(data)
        for i in range(0, len(mv), self.mtu):
            chunk = mv[i : i + self.mtu]
            while True:
                try:
                    # Use response=True for reliability with large bitmaps
                    await self.rx_char.write(chunk, response=True)
                    break
                except OSError as e:
                    if e.errno == 114:  # EALREADY
                        await asyncio.sleep_ms(5)
                    else:
                        raise e

    async def print_bitmap(self, bitmap_data):
        """
        bitmap_data should be a pre-inverted bytearray from JS.
        Assumes 48 bytes per line.
        """
        num_lines = len(bitmap_data) // 48
        print(f"🖨️ Printing {num_lines} lines...")

        mv = memoryview(bitmap_data)

        for y in range(num_lines):
            line_start = y * 48
            line_data = mv[line_start : line_start + 48]

            # Combine header + line and blast it
            await self.send_payload(self.raster_header + line_data)

            # Every 10 lines, brief pause to let the printer hardware keep up
            if y % 10 == 0:
                await asyncio.sleep_ms(10)
                gc.collect()

        # Final feed
        await self.send_payload(b"\x0a\x0a\x0a")
        print("✅ Finished")


async def run_print(data_from_js):
    p = RawBitmapPrinter()
    if await p.connect():
        await p.print_bitmap(data_from_js)
        await p.connection.disconnect()


def generate_mock_bitmap(lines=20):
    """
    Generates a bytearray of alternating black and white lines.
    48 bytes per line (384 pixels).
    """
    data = bytearray()
    black_line = bytes([0xFF] * 48)  # 48 bytes of 11111111
    white_line = bytes([0x00] * 48)  # 48 bytes of 00000000

    for i in range(lines):
        if i % 2 == 0:
            data.extend(black_line)
        else:
            data.extend(white_line)

    return data


# Run the program
try:
    asyncio.run(run_print(generate_mock_bitmap(200)))
except KeyboardInterrupt:
    print("Stopped")
