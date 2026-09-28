import asyncio
import network


wlan = network.WLAN(network.STA_IF)


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
