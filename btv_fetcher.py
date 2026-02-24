import requests
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ---------- কনফিগারেশন ----------
HOME_API_URL = "https://www.btvlive.gov.bd/api/home"
USERID_API_PATTERN = "https://www.btvlive.gov.bd/_next/data/wr5BMimBGS-yN5Rc2tmam/channel/{urlname}.json?id={urlname}"
OUTPUT_FILE = "btv_channels.m3u"

# সিডিএন বেস URL (যেখানে সব ইমেজ হোস্ট করা)
CDN_BASE_URL = "https://d38ll44lbmt52p.cloudfront.net"

# চ্যানেল-নির্দিষ্ট লোগো ফিক্স (যদি API ভুল ডেটা দেয়)
CHANNEL_LOGO_OVERRIDES = {
    "BTV News": f"{CDN_BASE_URL}/cms/channel_poster/1735648543857_Poster.jpg",
    "বিটিভি নিউজ": f"{CDN_BASE_URL}/cms/channel_poster/1735648543857_Poster.jpg",
}

# --------------------------------

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
    
    # যদি ইতিমধ্যে সম্পূর্ণ URL হয়
    if image_path.startswith('http://') or image_path.startswith('https://'):
        return image_path
    
    # যদি cms/ দিয়ে শুরু হয়
    if image_path.startswith('cms/'):
        return f"{CDN_BASE_URL}/{image_path}"
    
    # অন্য ক্ষেত্রে
    return image_path

def get_channels_from_home_api() -> Optional[List[Dict]]:
    """হোম API থেকে সব চ্যানেলের বেসিক তথ্য সংগ্রহ করে"""
    data = fetch_json(HOME_API_URL)
    if not data:
        return None
    
    channels = data.get('channel_list', [])
    if not channels:
        print("❌ No channels found in home API response")
        return None
    
    # প্রতিটি চ্যানেলের লোগো ঠিক করে দিই
    for channel in channels:
        channel_name = channel.get('channel_name', '')
        poster = channel.get('poster', '')
        
        # লোগো ওভাররাইড চেক
        if channel_name in CHANNEL_LOGO_OVERRIDES:
            channel['poster'] = CHANNEL_LOGO_OVERRIDES[channel_name]
            print(f"  🖼️ {channel_name}: Using overridden logo")
        else:
            # নইলে সম্পূর্ণ URL তৈরি করি
            channel['poster'] = get_full_image_url(poster)
    
    print(f"✅ Found {len(channels)} channels in home API")
    return channels

def get_user_id_from_channel_api(urlname: str, identifier: str) -> Tuple[Optional[str], Optional[str]]:
    """নির্দিষ্ট চ্যানেলের API থেকে সঠিক userId এবং userCountry বের করে"""
    api_url = USERID_API_PATTERN.format(urlname=urlname.replace(' ', '%20'))
    
    data = fetch_json(api_url)
    if not data:
        return None, None
    
    try:
        page_props = data.get('pageProps', {})
        source_url = page_props.get('sourceURL', '')
        user_country = page_props.get('userCountry', 'BD')
        
        # URL থেকে userId বের করার প্যাটার্ন
        patterns = [
            rf'/{identifier}/[^/]+/([^/]+)/index\.m3u8$',  # identifier সহ
            r'/undefined/[^/]+/([^/]+)/index\.m3u8$',      # undefined সহ
            r'/[^/]+/([^/]+)/index\.m3u8$',                # শুধু শেষ অংশ
        ]
        
        user_id = None
        for pattern in patterns:
            match = re.search(pattern, source_url)
            if match:
                user_id = match.group(1)
                break
        
        if user_id:
            print(f"  ✓ {urlname}: userId={user_id}")
            return user_id, user_country
        else:
            # শেষ চেষ্টা হিসেবে URL-এর শেষ অংশ নিই
            parts = source_url.split('/')
            if len(parts) >= 2 and 'index.m3u8' in parts[-1]:
                user_id = parts[-2]
                if user_id and user_id != 'undefined':
                    return user_id, user_country
            
            return identifier, user_country
            
    except Exception as e:
        print(f"  ❌ Error parsing {urlname} API: {e}")
        return None, None

def generate_m3u_content(channels: List[Dict]) -> str:
    """সব তথ্য একত্রিত করে M3U ফাইল জেনারেট করে"""
    
    content = "#EXTM3U\n"
    content += f"#PLAYLIST: Bangladesh Television Channels (Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
    content += "#STATUS: Active\n"
    content += "#LANGUAGE: bn\n\n"
    
    success_count = 0
    failed_channels = []
    
    print("\n📋 Channel List with Logos:")
    print("-" * 60)
    
    for channel in channels:
        channel_name = channel.get('channel_name', 'Unknown')
        urlname = channel.get('urlname', '')
        identifier = channel.get('identifier', '')
        poster = channel.get('poster', '')
        
        # লোগো দেখাই
        logo_display = poster[:50] + "..." if len(poster) > 50 else poster
        print(f"  {channel_name}:")
        print(f"    - Logo: {logo_display}")
        
        if not urlname or not identifier:
            print(f"    ⚠️ Missing urlname or identifier")
            failed_channels.append(channel_name)
            continue
        
        # userId সংগ্রহ
        user_id, user_country = get_user_id_from_channel_api(urlname, identifier)
        
        if not user_id:
            user_id = identifier
        
        # স্ট্রিম URL
        stream_url = f"https://www.btvlive.gov.bd/live/{identifier}/{user_country}/{user_id}/index.m3u8"
        
        # EXTINF লাইন - এখন সঠিক লোগো সহ
        content += f"#EXTINF:-1 tvg-id=\"{identifier}\" tvg-name=\"{channel_name}\" tvg-logo=\"{poster}\" tvg-country=\"BD\" group-title=\"Bangladesh TV\", {channel_name}\n"
        content += f"{stream_url}\n\n"
        
        print(f"    ✅ Generated URL")
        success_count += 1
    
    print("-" * 60)
    print(f"\n📊 Summary: {success_count} channels successful, {len(failed_channels)} failed")
    
    return content

def verify_logos(channels: List[Dict]) -> None:
    """লোগোগুলো ভেরিফাই করে (HTTP HEAD request)"""
    import requests
    
    print("\n🔍 Verifying logos...")
    for channel in channels:
        channel_name = channel.get('channel_name', '')
        poster = channel.get('poster', '')
        
        if not poster:
            print(f"  ⚠️ {channel_name}: No logo")
            continue
        
        try:
            response = requests.head(poster, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"  ✅ {channel_name}: Logo OK")
            else:
                print(f"  ❌ {channel_name}: Logo not accessible (HTTP {response.status_code})")
        except Exception as e:
            print(f"  ❌ {channel_name}: Logo check failed - {str(e)[:50]}")

def main():
    print("=" * 80)
    print(f"🚀 BTV M3U Playlist Generator (v2.1 - Fixed Logos) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # ধাপ ১: হোম API থেকে চ্যানেলের তথ্য
    print("\n📥 Step 1: Fetching channel list from home API...")
    channels = get_channels_from_home_api()
    if not channels:
        print("❌ Failed to get channel list. Exiting.")
        raise SystemExit(1)
    
    # লোগো ভেরিফিকেশন (ঐচ্ছিক)
    verify_logos(channels)
    
    # ধাপ ২: M3U জেনারেট
    print("\n🔍 Step 2: Generating M3U playlist...")
    m3u_content = generate_m3u_content(channels)
    
    # ধাপ ৩: ফাইল সেভ
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    
    # ধাপ ৪: ফাইনাল চেক
    print("\n" + "=" * 80)
    print(f"✅ SUCCESS! M3U file updated: {OUTPUT_FILE}")
    
    # M3U ফাইলের প্রথম কয়েক লাইন দেখাই
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"\n📄 M3U Preview (first 10 lines):")
        print("-" * 60)
        for line in lines[:10]:
            if line.startswith('#EXTINF'):
                # লোগো URL টা দেখাই
                logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                if logo_match:
                    logo = logo_match.group(1)
                    print(f"  {line[:50]}...")
                    print(f"    Logo: {logo[:70]}...")
                else:
                    print(f"  {line[:70]}...")
            else:
                print(f"  {line[:70]}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
