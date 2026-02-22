import requests
import json
import re
from datetime import datetime

# ============================================
# Bangladesh Television (BTV) Channel Link Generator
# ============================================

BASE_URL = "https://www.btvlive.gov.bd"
USER_COUNTRY = "BD"
HOME_API_URL = f"{BASE_URL}/api/home"

# API file mapping as per your instructions
API_FILE_MAP = {
    "BTV": "BTV",
    "BTV News": "BTV",  # Important: BTV News uses BTV.json
    "BTV Chattogram": "BTV-Chattogram",
    "Sangsad Television": "Sangsad-Television"
}

def get_build_id():
    """Fetch buildId from the main website (as fallback)"""
    print("🔍 Searching for Build ID...")
    try:
        response = requests.get(BASE_URL, timeout=10)
        response.raise_for_status()
        patterns = [
            r'"buildId":"([^"]+)"',
            r'/_next/data/([^/]+)/',
        ]
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                build_id = match.group(1)
                print(f"✅ Build ID found: {build_id}")
                return build_id
    except Exception as e:
        print(f"⚠️ Error finding Build ID: {e}")

    print("⚠️ Build ID not found, using default.")
    return "wr5BMimBGS-yN5Rc2tmam" # Your provided default

def fetch_home_api():
    """Step 1: Fetch channel list and basic info from /api/home"""
    print(f"📡 Step 1: Fetching channel list from Home API: {HOME_API_URL}")
    try:
        resp = requests.get(HOME_API_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Home API loaded successfully.")
        return data
    except Exception as e:
        print(f"❌ Failed to load Home API: {e}")
        return None

def extract_channel_list(home_data):
    """Extract important channels (from menu) from home data"""
    channels = []
    if home_data and 'menu' in home_data:
        for item in home_data['menu']:
            if item.get('type') == 'channel' and item.get('status') == 'active':
                urlname = item.get('urlname')
                if urlname:
                    channels.append({
                        "name": item.get('name', urlname),
                        "urlname": urlname,
                        "api_file": API_FILE_MAP.get(urlname, urlname.replace(" ", "-"))
                    })
        print(f"✅ Extracted {len(channels)} channels from menu.")
    else:
        print("⚠️ 'menu' not found in Home API data.")
    return channels

def fetch_channel_details(build_id, channel_info):
    """Step 2: Fetch identifier and poster for each channel from specific JSON API"""
    urlname = channel_info['urlname']
    api_file = channel_info['api_file']
    api_url = f"{BASE_URL}/_next/data/{build_id}/channel/{api_file}.json?id={api_file}"

    print(f"  📡 {channel_info['name']} ({urlname}) -> {api_file}.json")

    try:
        resp = requests.get(api_url, timeout=15)
        if resp.status_code != 200:
            print(f"  ⚠️  Status {resp.status_code} - Skipping")
            return None

        data = resp.json()

        # --- Correct path to extract identifier and poster ---
        identifier = None
        poster = None

        # 1️⃣ Try to get from currentChannel (first priority)
        try:
            current = data['pageProps']['currentChannel']['channel_details']
            identifier = current.get('identifier')
            # poster: usually relative path in current channel
            poster_path = current.get('poster')
            if poster_path and not poster_path.startswith('http'):
                # Build CDN URL
                poster = f"https://d38ll44lbmt52p.cloudfront.net/{poster_path}"
            else:
                poster = poster_path
        except (KeyError, TypeError):
            pass

        # 2️⃣ If identifier not found, search in otherChannelList
        if not identifier:
            try:
                for other in data.get('pageProps', {}).get('otherChannelList', []):
                    if other.get('urlname') == urlname:
                        identifier = other.get('identifier')
                        # In otherChannelList, poster is usually full CDN URL
                        poster = other.get('poster') or poster
                        break
            except (KeyError, TypeError):
                pass

        if identifier and poster:
            print(f"  ✅ identifier: {identifier[:8]}...")
            print(f"  ✅ poster: {poster[:60]}...")
            return {
                "name": channel_info['name'],
                "urlname": urlname,
                "identifier": identifier,
                "poster": poster
            }
        else:
            print(f"  ❌ identifier or poster not found")
            return None

    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")
        return None

def create_m3u8_playlist(channels_data):
    """Create M3U8 playlist"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    m3u8 = "#EXTM3U\n"
    m3u8 += f"#PLAYLIST: Bangladesh Television (BTV) - Live Channels\n"
    m3u8 += f"#UPDATED: {timestamp}\n"
    m3u8 += f"#SOURCE: {BASE_URL}\n"
    m3u8 += f"#TOTAL CHANNELS: {len(channels_data)}\n\n"

    for ch in channels_data:
        # M3U8 URL: identifier is used as userId
        m3u8_url = f"{BASE_URL}/live/{ch['identifier']}/{USER_COUNTRY}/{ch['identifier']}/index.m3u8"

        m3u8 += f'#EXTINF:-1 tvg-id="{ch["identifier"][:8]}" '
        m3u8 += f'tvg-name="{ch["name"]}" '
        m3u8 += f'tvg-logo="{ch["poster"]}" '
        m3u8 += f'group-title="BTV",{ch["name"]}\n'
        m3u8 += f"{m3u8_url}\n\n"

    return m3u8

def main():
    print("=" * 70)
    print("🇧🇩  Bangladesh Television (BTV) Channel Link Generator (Final Version)")
    print("=" * 70)

    # 1. Get Build ID
    build_id = get_build_id()
    print(f"📡 Using Build ID: {build_id}")
    print("=" * 70)

    # 2. Fetch channel list from Home API
    home_data = fetch_home_api()
    if not home_data:
        print("❌ Home API not available. Stopping.")
        return

    channel_list = extract_channel_list(home_data)
    if not channel_list:
        print("❌ No channels found.")
        return

    # 3. Fetch detailed info (identifier, poster) for each channel
    print("\n📡 Step 2: Fetching detailed info from channel-specific APIs:")
    successful_channels = []
    for channel in channel_list:
        details = fetch_channel_details(build_id, channel)
        if details:
            successful_channels.append(details)
        print("-" * 50)

    # 4. Create and save playlist
    if successful_channels:
        m3u8_content = create_m3u8_playlist(successful_channels)

        with open("btv_channels.m3u8", "w", encoding="utf-8") as f:
            f.write(m3u8_content)

        # JSON output for reference
        json_output = {
            "last_updated": datetime.now().isoformat(),
            "build_id": build_id,
            "country": USER_COUNTRY,
            "channels": successful_channels
        }
        with open("btv_channels.json", "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 70)
        print("✅ SUCCESS!")
        print(f"📊 Total Channels: {len(successful_channels)}")
        print("=" * 70)
        print("📁 btv_channels.m3u8  - M3U8 Playlist (Open in VLC)")
        print("📁 btv_channels.json   - JSON Data")
        print("=" * 70)

        print("\n📺 Successful Channels:")
        for i, ch in enumerate(successful_channels, 1):
            print(f"   {i}. {ch['name']}")
    else:
        print("\n❌ Could not fetch any channel data.")

if __name__ == "__main__":
    main()
