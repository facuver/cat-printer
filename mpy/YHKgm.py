import asyncio, struct, aioble, bluetooth

# Constants
PRINTER_NAME = "YHK-4118"
WIDTH_BYTES = 48  # 384 px / 8
BATCH_LINES = 20  # Send 20 lines per command (960 bytes) to reduce overhead





class YHKPrinter:
    def __init__(self):
        self.device = None
        self.connection = None
        self.rx = None
        self.mtu = 23  # Default BLE MTU

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

    async def connect(self):
        """Scan, Connect, and Negotiate MTU"""
        print(f"🔍 Scanning for {PRINTER_NAME}...")
        self.device = await self.scan()
        if not self.device: return False

        print("🔗 Connecting...")
        self.connection = await self.device.connect(timeout_ms=10000)

        # 1. OPTIMIZATION: Exchange MTU to get max packet size (usually ~247 on ESP32)
        self.mtu = await self.connection.exchange_mtu(247) - 3
        print(f"⚡ MTU set to: {self.mtu}")

        service = await self.connection.service(bluetooth.UUID("49535343-FE7D-4AE5-8FA9-9FAFD205E455"))
        self.rx = await service.characteristic(bluetooth.UUID("49535343-8841-43F4-A8D4-ECBE34729BB3"))

        # Init printer
        await self.send_raw(b"\x1b\x40\x1d\x49\xf0\x19")
        return True

    async def send_raw(self, data):
        """Split data into MTU-sized chunks and send"""
        mv = memoryview(data)
        sent = 0
        while sent < len(mv):
            chunk = mv[sent : sent + self.mtu]
            await self.rx.write(chunk, response=True)
            sent += len(chunk)
            await asyncio.sleep_ms(5) # Yield to BLE stack

    async def print_bitmap(self, buf):
        """2. OPTIMIZATION: Send multiple lines in one command"""
        total_lines = len(buf) // WIDTH_BYTES
        mv = memoryview(buf)
        bytes_per_batch = WIDTH_BYTES * BATCH_LINES

        print(f"🖨️ Printing {total_lines} lines...")

        for i in range(0, len(mv), bytes_per_batch):
            # Calculate actual lines in this batch (handling the last chunk)
            chunk = mv[i : i + bytes_per_batch]
            lines = len(chunk) // WIDTH_BYTES

            # Command: GS v 0 | width(48,0) | height(lines, 0)
            # This header tells printer "Here comes X lines at once"
            header = struct.pack("<4s2B2B", b'\x1d\x76\x30\x00', WIDTH_BYTES, 0, lines, 0)

            await self.send_raw(header + chunk)
            await asyncio.sleep_ms(20) # Allow printer buffer to process

        print("✅ Done")

    async def feed_lines(self,lines=3):
        await self.send_raw(b"\x0a"*lines) # Feed

    async def disconnect(self):
        if self.connection: await self.connection.disconnect()
