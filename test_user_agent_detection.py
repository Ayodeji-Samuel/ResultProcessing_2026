"""
Test script to demonstrate enhanced user agent parsing and location detection
"""
from user_agents import parse as parse_ua

# Test various user agent strings
test_user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
]

print("=" * 80)
print("ENHANCED USER AGENT DETECTION TEST")
print("=" * 80)

for ua_string in test_user_agents:
    user_agent = parse_ua(ua_string)
    
    # Get device type
    if user_agent.is_mobile:
        device_type = f'Mobile ({user_agent.device.family})'
    elif user_agent.is_tablet:
        device_type = f'Tablet ({user_agent.device.family})'
    elif user_agent.is_pc:
        device_type = 'Desktop'
    elif user_agent.is_bot:
        device_type = 'Bot'
    else:
        device_type = 'Unknown'
    
    # Get browser with version
    browser = user_agent.browser.family
    if user_agent.browser.version_string:
        browser = f"{browser} {user_agent.browser.version_string}"
    
    # Get OS with version
    os = user_agent.os.family
    if user_agent.os.version_string:
        os = f"{os} {user_agent.os.version_string}"
    
    print(f"\nUser Agent: {ua_string[:80]}...")
    print(f"  Device: {device_type}")
    print(f"  Browser: {browser}")
    print(f"  OS: {os}")

print("\n" + "=" * 80)
print("LOCATION DETECTION TEST")
print("=" * 80)

import requests

# Test with a public IP (Google's DNS)
test_ips = [
    "8.8.8.8",  # Google DNS (Mountain View, CA)
    "127.0.0.1",  # Localhost
]

for ip in test_ips:
    print(f"\nTesting IP: {ip}")
    
    if ip in ['127.0.0.1', 'localhost', '::1']:
        print(f"  Location: Local Machine")
        continue
    
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                city = data.get('city', '')
                region = data.get('regionName', '')
                country = data.get('country', '')
                latitude = data.get('lat')
                longitude = data.get('lon')
                
                location_parts = [p for p in [city, region, country] if p]
                location = ', '.join(location_parts) if location_parts else 'Unknown'
                print(f"  Location: {location}")
                print(f"  Coordinates: {latitude}, {longitude}")
                print(f"  Google Maps: https://www.google.com/maps?q={latitude},{longitude}")
                print(f"  ISP: {data.get('isp', 'Unknown')}")
                print(f"  Timezone: {data.get('timezone', 'Unknown')}")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "=" * 80)
print("All tests completed successfully!")
print("=" * 80)
