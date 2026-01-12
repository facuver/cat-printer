"""
YHK-0E50 BLE Thermal Printer - MicroPython Implementation
Using aioble for ESP32/RP2040 with RASTER GRAPHICS support
Now with FrameBuffer for text rendering!

Requires:
- MicroPython with aioble support
- ESP32 or RP2 Pico W
"""

import asyncio

import aioble
import bluetooth
import framebuf

# Printer Configuration
PRINTER_NAME = "YHK-4118"
PRINTER_WIDTH = 384  # pixels (48 bytes)

# Microchip Transparent UART Service UUIDs
_UART_SERVICE_UUID = bluetooth.UUID("49535343-FE7D-4AE5-8FA9-9FAFD205E455")
_UART_TX_CHAR_UUID = bluetooth.UUID("49535343-1E4D-4BD9-BA61-23C647249616")  # Notify
_UART_RX_CHAR_UUID = bluetooth.UUID("49535343-8841-43F4-A8D4-ECBE34729BB3")  # Write

# Printer Commands
CMD_INIT = b"\x1b\x40"  # ESC @ - Initialize
CMD_START_PRINT = b"\x1d\x49\xf0\x19"  # Start print sequence
CMD_FEED = b"\x0a"  # Line feed


class YHKPrinter:
    def __init__(self):
        self.device = None
        self.connection = None
        self.rx_char = None
        self.tx_char = None

    async def scan(self, timeout_ms=10000):
        """Scan for the printer"""
        print(f"🔍 Scanning for {PRINTER_NAME}...")

        async with aioble.scan(
            timeout_ms, interval_us=30000, window_us=30000, active=True
        ) as scanner:
            async for result in scanner:
                if result.name() == PRINTER_NAME:
                    print(f"✅ Found: {result.name()}")
                    return result.device

        print("❌ Printer not found")
        return None

    async def connect(self, device=None, timeout_ms=10000):
        """Connect to the printer"""
        if device is None:
            device = await self.scan()
            if device is None:
                return False

        self.device = device

        print(f"🔗 Connecting to {PRINTER_NAME}...")
        try:
            self.connection = await device.connect(timeout_ms=timeout_ms)
            self.mtu = await self.connection.exchange_mtu(512) - 3
            print("✅ Connected!")

            service = await self.connection.service(_UART_SERVICE_UUID)
            self.rx_char = await service.characteristic(_UART_RX_CHAR_UUID)

            try:
                self.tx_char = await service.characteristic(_UART_TX_CHAR_UUID)
            except:
                self.tx_char = None

            # Initialize printer
            print("📤 Initializing printer...")
            await self.rx_char.write(CMD_INIT, response=True)
            await asyncio.sleep_ms(300)

            # Send magic start command (REQUIRED!)
            await self.rx_char.write(CMD_START_PRINT, response=True)
            await asyncio.sleep_ms(300)

            print("✅ Ready to print!")
            return True

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from printer"""
        if self.connection:
            await self.connection.disconnect()
            self.connection = None
            print("👋 Disconnected")

    async def write(self, data):
        """Write data to printer"""
        if not self.rx_char:
            raise RuntimeError("Not connected")

        # Split into chunks if needed (BLE MTU limitation)
        chunk_size = self.mtu
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            await self.rx_char.write(chunk, response=False)
            await asyncio.sleep_ms(10)

    async def print_raster_image(self, bitmap_data, width=384, height=None):
        """
        Print a raster bitmap image

        Args:
            bitmap_data: List of bytes where each byte represents 8 pixels
                        0xFF = black, 0x00 = white (inverted!)
            width: Image width in pixels (must be 384)
            height: Image height in lines (calculated from bitmap_data if None)
        """
        if width != 384:
            raise ValueError("Width must be 384 pixels")

        width_bytes = width // 8  # 48 bytes

        if height is None:
            height = len(bitmap_data) // width_bytes

        print(f"🖨️  Printing {height} lines...")

        # GS v 0 command header (prints 1 line at a time)
        # Format: 1D 76 30 00 [xL xH yL yH] [data...]
        header = bytes([0x1D, 0x76, 0x30, 0x00, width_bytes, 0x00, 0x01, 0x00])

        # Send each line - NO LINE FEEDS! (GS v 0 auto-advances)
        for i in range(height):
            line_start = i * width_bytes
            line_data = bitmap_data[line_start : line_start + width_bytes]

            # Send header + line data
            await self.write(header + bytes(line_data))
            await asyncio.sleep_ms(30)
            # Progress indicator
            if (i + 1) % 50 == 0 or i == height - 1:
                pct = (i + 1) / height * 100
                print(f"   {i + 1}/{height} ({pct:.0f}%)")

        # Feed paper at the end to eject
        # await self.write(b"\x0a\x0a\x0a\x0a")
        # await asyncio.sleep_ms(100)
        print("✅ Print complete!")

    async def print_framebuffer(self, fb, invert=True):
        """
        Print a FrameBuffer directly

        Args:
            fb: FrameBuffer object (must be 384 pixels wide)
            invert: If True, invert colors (framebuf 1=white, printer needs 1=black)
        """
        # if fb.width != 384:
        #     raise ValueError("FrameBuffer width must be 384 pixels")

        # Get the raw buffer datab)
        buf = bytearray(fb)

        # Invert if needed (framebuf: 1=white, printer: 0xFF=black)
        if invert:
            for i in range(len(buf)):
                buf[i] = ~buf[i] & 0xFF

        await self.print_raster_image(buf, width=384, height=10)
        # if fb.width != 384:
        #     raise ValueError("FrameBuffer width must be 384 pixels")
        # if fb.width != 384:
        #     raise ValueError("FrameBuffer width must be 384 pixels")

    async def feed_lines(self, lines=1):
        """Feed paper"""
        await self.write(CMD_FEED * lines)
