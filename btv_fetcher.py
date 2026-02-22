import requests
import json
import re
from datetime import datetime

# ============================================
# বাংলাদেশ টেলিভিশন চ্যানেল লিংক জেনারেটর
# ============================================

BASE_URL = "https://www.btvlive.gov.bd"
USER_COUNTRY = "BD"

# চ্যানেলের তালিকা
CHANNELS = [
    {"name": "BTV", "api_name": "BTV", "group": "BTV", "api_id": "BTV"},
    {"name": "BTV News", "api_name": "BTV", "group": "BTV", "api_id": "BTV"},
    {"name": "BTV Chattogram", "api_name": "BTV-Chattogram", "group": "BTV", "api_id": "BTV-Chattogram"},
    {"name": "Sangsad Television", "api_name": "Sangsad-Television", "group": "Parliament", "api_id": "Sangsad-Television"}
]

def get_build_id():
    """মূল ওয়েবসাইট থেকে buildId বের করে"""
    print("🔍 Build ID খোঁজা হচ্ছে...")
    
    try:
        response = requests.get(BASE_URL, timeout=10)
        response.raise_for_status()
        
        # বিভিন্ন প্যাটার্নে buildId খোঁজা
        patterns = [
            r'"buildId":"([^"]+)"',
            r'buildId":\s*"([^"]+)"',
            r'nextData.+?buildId[=:"]+([^"&\s]+)',
            r'/_next/data/([^/]+)/'  # URL প্যাটার্ন
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                build_id = match.group(1)
                print(f"✅ Build ID পাওয়া গেছে: {build_id}")
                return build_id
        
        # যদি কিছু না পাওয়া যায়, তাহেছে ডিফল্ট ইউজ করার অপশন
        print("⚠️ Build ID পাওয়া যায়নি, ডিফল্ট ব্যবহার করা হবে")
        return "wr5BMimBGS-yN5Rc2tmam"  # আপনার দেওয়া ডিফল্ট
            
    except Exception as e:
        print(f"❌ Build ID খুঁজতে এরর: {e}")
        print("⚠️ ডিফল্ট Build ID ব্যবহার করা হবে")
        return "wr5BMimBGS-yN5Rc2tmam"

def fetch_channel_data(build_id, channel):
    """একটি চ্যানেলের ডাটা API থেকে ফেচ করে"""
    
    api_url = f"{BASE_URL}/_next/data/{build_id}/channel/{channel['api_name']}.json?id={channel['api_id']}"
    
    print(f"📡 {channel['name']} থেকে ডাটা নিচ্ছি...")
    print(f"   URL: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=15)
        
        if response.status_code == 404:
            print(f"  ⚠️  API পাওয়া যায়নি (404)। Build ID পরিবর্তন হতে পারে।")
            return None
        elif response.status_code != 200:
            print(f"  ⚠️  স্ট্যাটাস {response.status_code} - স্কিপ")
            return None
        
        data = response.json()
        
        # identifier বের করা
        try:
            identifier = data['pageProps']['currentChannel']['channel_details']['identifier']
            print(f"  ✅ identifier: {identifier}")
        except (KeyError, TypeError) as e:
            print(f"  ❌ identifier খুঁজে পাওয়া যায়নি: {e}")
            return None
        
        # লোগো বের করা (poster থেকে)
        logo = None
        try:
            poster = data['pageProps']['currentChannel']['channel_details'].get('poster', '')
            if poster:
                if poster.startswith('http'):
                    logo = poster
                elif poster.startswith('cms/'):
                    logo = f"https://d38ll44lbmt52p.cloudfront.net/{poster}"
                else:
                    logo = f"{BASE_URL}/{poster.lstrip('/')}"
                print(f"  ✅ লোগো: {logo[:60]}...")
        except:
            pass
        
        if not logo:
            # otherChannelList-এ খোঁজা
            try:
                for other in data.get('pageProps', {}).get('otherChannelList', []):
                    if other.get('urlname') == channel['api_name']:
                        poster = other.get('poster', '')
                        if poster:
                            logo = poster if poster.startswith('http') else f"{BASE_URL}/{poster.lstrip('/')}"
                            break
            except:
                pass
        
        if not logo:
            logo = f"https://d38ll44lbmt52p.cloudfront.net/cms/channel_poster/default.png"
            print(f"  ℹ️  ডিফল্ট লোগো ব্যবহার করা হবে")
        
        return {
            "name": channel['name'],
            "group": channel['group'],
            "identifier": identifier,
            "user_id": identifier,
            "logo": logo
        }
            
    except Exception as e:
        print(f"  ❌ এরর: {str(e)[:100]}")
        return None

def create_m3u8_playlist(channels_data, build_id):
    """M3U8 প্লেলিস্ট তৈরি করে"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    m3u8 = "#EXTM3U\n"
    m3u8 += f"#PLAYLIST: বাংলাদেশ টেলিভিশন চ্যানেল\n"
    m3u8 += f"#UPDATED: {timestamp}\n"
    m3u8 += f"#BUILD ID: {build_id}\n"
    m3u8 += f"#SOURCE: {BASE_URL}\n"
    m3u8 += f"#TOTAL CHANNELS: {len(channels_data)}\n\n"
    
    for ch in channels_data:
        if ch:
            m3u8_url = f"{BASE_URL}/live/{ch['identifier']}/{USER_COUNTRY}/{ch['user_id']}/index.m3u8"
            
            m3u8 += f'#EXTINF:-1 tvg-id="{ch["identifier"][:8]}" '
            m3u8 += f'tvg-name="{ch["name"]}" '
            m3u8 += f'tvg-logo="{ch["logo"]}" '
            m3u8 += f'group-title="{ch["group"]}",{ch["name"]}\n'
            m3u8 += f"{m3u8_url}\n\n"
    
    return m3u8

def create_json_output(channels_data, build_id):
    """JSON আউটপুট তৈরি করে"""
    
    output = {
        "last_updated": datetime.now().isoformat(),
        "build_id": build_id,
        "country": USER_COUNTRY,
        "total_channels": len(channels_data),
        "channels": []
    }
    
    for ch in channels_data:
        if ch:
            output["channels"].append({
                "name": ch["name"],
                "group": ch["group"],
                "identifier": ch["identifier"],
                "logo": ch["logo"],
                "url": f"{BASE_URL}/live/{ch['identifier']}/{USER_COUNTRY}/{ch['user_id']}/index.m3u8"
            })
    
    return output

def main():
    """মূল প্রোগ্রাম"""
    
    print("=" * 70)
    print("🇧🇩  বাংলাদেশ টেলিভিশন (BTV) চ্যানেল লিংক জেনারেটর")
    print("=" * 70)
    
    # Build ID অটো ডিটেক্ট
    build_id = get_build_id()
    print(f"📡 ব্যবহৃত Build ID: {build_id}")
    print(f"🌍 দেশ: {USER_COUNTRY}")
    print("=" * 70)
    
    print(f"\n📡 {len(CHANNELS)} টি চ্যানেল থেকে ডাটা সংগ্রহ করা হচ্ছে...\n")
    
    channels_data = []
    for channel in CHANNELS:
        data = fetch_channel_data(build_id, channel)
        if data:
            channels_data.append(data)
        print("-" * 50)
    
    if not channels_data:
        print("\n❌ কোনো চ্যানেলের ডাটা পাওয়া যায়নি।")
        return
    
    # ফাইল তৈরি
    m3u8_content = create_m3u8_playlist(channels_data, build_id)
    json_output = create_json_output(channels_data, build_id)
    
    with open("btv_channels.m3u8", "w", encoding="utf-8") as f:
        f.write(m3u8_content)
    
    with open("btv_channels.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    # রিপোর্ট
    print("\n" + "=" * 70)
    print("📊  রিপোর্ট:")
    print(f"    মোট চ্যানেল: {len(CHANNELS)}")
    print(f"    সফল: {len(channels_data)}")
    print(f"    ব্যর্থ: {len(CHANNELS) - len(channels_data)}")
    print("=" * 70)
    print("✅ btv_channels.m3u8  - M3U8 প্লেলিস্ট")
    print("✅ btv_channels.json   - JSON ডাটা")
    print("=" * 70)
    
    print("\n📺  সফল চ্যানেলসমূহ:")
    for i, ch in enumerate(channels_data, 1):
        print(f"   {i}. {ch['name']}")

if __name__ == "__main__":
    main()
