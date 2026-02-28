import requests
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ========== কনফিগারেশন ==========
HOME_API_URL = "https://www.btvlive.gov.bd/api/home"
CDN_BASE_URL = "https://d38ll44lbmt52p.cloudfront.net"

# সঠিক URLname এবং তাদের API URL (আপনার দেওয়া লিংক অনুযায়ী)
CHANNEL_API_CONFIG = {
    "BTV": {
        "urlname": "BTV",
        "api_url": "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/BTV.json?id=BTV"
    },
    "BTV News": {
        "urlname": "BTV-News",  # ইউআরএলে যা ব্যবহার হবে
        "api_url": "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/BTV-News.json?id=BTV-News"
    },
    "BTV Chattogram": {
        "urlname": "BTV-Chattogram",
        "api_url": "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/BTV-Chattogram.json?id=BTV-Chattogram"
    },
    "Sangsad Television": {
        "urlname": "Sangsad-Television",
        "api_url": "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/Sangsad-Television.json?id=Sangsad-Television"
    }
}

OUTPUT_FILE = "btv_channels.m3u"
# =================================

def fetch_json(url: str, timeout: int = 10) -> Optional[Dict]:
    """যে কোনো URL থেকে JSON ডেটা fetch করে"""
    try:
        print(f"📡 Fetching: {url}")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
        return None

def get_full_image_url(image_path: str) -> str:
    """ইমেজ পাথ থেকে সম্পূর্ণ URL তৈরি করে"""
    if not image_path:
        return ""
    if image_path.startswith('http://') or image_path.startswith('https://'):
        return image_path
    if image_path.startswith('cms/'):
        return f"{CDN_BASE_URL}/{image_path}"
    return image_path

def get_channels_from_home_api() -> Optional[Dict[str, Dict]]:
    """
    হোম API থেকে সব চ্যানেলের বেসিক তথ্য সংগ্রহ করে এবং
    channel_name এর ভিত্তিতে একটি ডিকশনারি তৈরি করে।
    """
    data = fetch_json(HOME_API_URL)
    if not data or 'channel_list' not in data:
        print("❌ No channel list found in home API response")
        return None

    channels_dict = {}
    for channel in data['channel_list']:
        channel_name = channel.get('channel_name')
        if channel_name:
            # লোগোর URL ঠিক করে সংরক্ষণ
            channel['poster'] = get_full_image_url(channel.get('poster', ''))
            channels_dict[channel_name] = channel

    print(f"✅ Found {len(channels_dict)} channels in home API")
    return channels_dict

def get_live_stream_details(urlname_key: str, api_url: str, home_channel_info: Dict) -> Optional[Dict]:
    """
    নির্দিষ্ট চ্যানেলের API থেকে userId এবং userCountry বের করে
    এবং হোম API থেকে পাওয়া তথ্যের সাথে মিশিয়ে একটি সম্পূর্ণ চ্যানেল তথ্য তৈরি করে।
    """
    print(f"\n🔍 Processing: {urlname_key}")

    data = fetch_json(api_url)
    if not data:
        print(f"  ❌ Failed to fetch API for {urlname_key}")
        return None

    try:
        page_props = data.get('pageProps', {})
        source_url = page_props.get('sourceURL', '')
        user_country = page_props.get('userCountry', 'BD')

        # sourceURL থেকে userId বের করা
        user_id = None
        # প্যাটার্ন: .../[userCountry]/[userId]/index.m3u8
        match = re.search(r'/[^/]+/([^/]+)/index\.m3u8$', source_url)
        if match:
            user_id = match.group(1)
            print(f"  ✓ Extracted userId: {user_id}")
        else:
            print(f"  ⚠️ Could not extract userId from sourceURL: {source_url}")

        if not user_id:
            print(f"  ❌ No userId found for {urlname_key}")
            return None

        # হোম API থেকে প্রাপ্ত তথ্যের সাথে একীভূত করা
        channel_info = home_channel_info.copy()
        channel_info.update({
            'user_id': user_id,
            'user_country': user_country,
            'api_urlname': urlname_key  # URL-এ ব্যবহৃত নাম
        })

        print(f"  ✅ Successfully processed: {channel_info.get('channel_name')}")
        return channel_info

    except Exception as e:
        print(f"  ❌ Error processing {urlname_key}: {e}")
        return None

def generate_m3u_content(channels: List[Dict]) -> str:
    """সব তথ্য একত্রিত করে M3U ফাইল জেনারেট করে"""
    content = "#EXTM3U\n"
    content += f"#PLAYLIST: Bangladesh Television Channels (Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
    content += "#STATUS: Active\n"
    content += "#LANGUAGE: bn\n\n"

    for channel in channels:
        channel_name = channel.get('channel_name', 'Unknown')
        identifier = channel.get('identifier', '')
        poster = channel.get('poster', '')
        user_id = channel.get('user_id', identifier)
        user_country = channel.get('user_country', 'BD')

        # স্ট্রিম URL তৈরি
        stream_url = f"https://www.btvlive.gov.bd/live/{identifier}/{user_country}/{user_id}/index.m3u8"

        # EXTINF লাইন
        content += f"#EXTINF:-1 tvg-id=\"{identifier}\" tvg-name=\"{channel_name}\" tvg-logo=\"{poster}\" tvg-country=\"BD\" group-title=\"Bangladesh TV\", {channel_name}\n"
        content += f"{stream_url}\n\n"
        print(f"  ✅ Generated: {channel_name} -> {stream_url}")

    return content

def main():
    print("=" * 80)
    print(f"🚀 BTV M3U Playlist Generator (Final Corrected Version) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # ধাপ ১: হোম API থেকে সব চ্যানেলের বেসিক তথ্য নিন
    print("\n📥 Step 1: Fetching base channel info from home API...")
    home_channels = get_channels_from_home_api()
    if not home_channels:
        print("❌ Failed to get base channel list. Exiting.")
        raise SystemExit(1)

    # ধাপ ২: কনফিগার করা প্রতিটি চ্যানেলের জন্য পৃথক API কল করে userId সংগ্রহ
    print("\n🔍 Step 2: Fetching live stream details (userId) for each channel...")
    successful_channels = []
    failed_channels = []

    for display_name, config in CHANNEL_API_CONFIG.items():
        # হোম API-তে চ্যানেলটি খুঁজে বের করা (বাংলা এবং ইংরেজি নাম মেলানো)
        home_channel = home_channels.get(display_name)  # যেমন "BTV News" direct match
        if not home_channel:
            # বিকল্প নাম খোঁজার চেষ্টা (যদি প্রয়োজন হয়)
            for name, info in home_channels.items():
                if config['urlname'] in info.get('urlname', ''):
                    home_channel = info
                    break

        if not home_channel:
            print(f"⚠️ Could not find '{display_name}' in home API data. Skipping.")
            failed_channels.append(display_name)
            continue

        channel_details = get_live_stream_details(
            urlname_key=config['urlname'],
            api_url=config['api_url'],
            home_channel_info=home_channel
        )

        if channel_details:
            successful_channels.append(channel_details)
        else:
            failed_channels.append(display_name)

    # ধাপ ৩: M3U কন্টেন্ট জেনারেট করা
    if not successful_channels:
        print("\n❌ No channels could be processed. Exiting.")
        raise SystemExit(1)

    print(f"\n📊 Step 3: Generating M3U playlist with {len(successful_channels)} channels...")
    m3u_content = generate_m3u_content(successful_channels)

    # ধাপ ৪: ফাইল সেভ করা
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(m3u_content)

    # ফাইনাল রিপোর্ট
    print("\n" + "=" * 80)
    print(f"✅ SUCCESS! M3U file updated: {OUTPUT_FILE}")
    print(f"   Total channels in playlist: {len(successful_channels)}")
    if failed_channels:
        print(f"   Failed channels: {', '.join(failed_channels)}")

    # M3U ফাইলের প্রথম কয়েক লাইন দেখানো
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"\n📄 M3U Preview (first 5 lines):")
        print("-" * 60)
        for line in lines[:5]:
            print(f"  {line.strip()[:80]}")
    print("=" * 80)

if __name__ == "__main__":
    main()
