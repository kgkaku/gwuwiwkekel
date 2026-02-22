import requests
import json
from datetime import datetime

# ============================================
# বাংলাদেশ টেলিভিশন চ্যানেল লিংক জেনারেটর
# ============================================

# কনফিগারেশন
BASE_URL = "https://www.btvlive.gov.bd"
USER_COUNTRY = "BD"
BUILD_ID = "wr5BMimBGS-yN5Rc2tmam"  # আপনার দেওয়া বিল্ড আইডি

# চ্যানেলের তালিকা
CHANNELS = [
    {"id": "BTV", "name": "BTV", "group": "BTV"},
    {"id": "BTV World", "name": "BTV World", "group": "BTV"},
    {"id": "Sangsad Television", "name": "সংসদ টেলিভিশন", "group": "Parliament"},
    {"id": "BTV Chattogram", "name": "BTV চট্টগ্রাম", "group": "BTV"}
]

# ডিফল্ট লোগো URL (যদি API থেকে না আসে)
DEFAULT_LOGOS = {
    "BTV": "https://www.btvlive.gov.bd/images/btv-logo.png",
    "BTV World": "https://www.btvlive.gov.bd/images/btv-world-logo.png",
    "Sangsad Television": "https://www.btvlive.gov.bd/images/sangsad-logo.png",
    "BTV Chattogram": "https://www.btvlive.gov.bd/images/btv-chattogram-logo.png"
}

def fetch_channel_data(channel):
    """একটি চ্যানেলের ডাটা API থেকে ফেচ করে"""
    
    # URL তৈরি (স্পেস এনকোডিং)
    channel_id = channel["id"].replace(" ", "%20")
    api_url = f"{BASE_URL}/_next/data/{BUILD_ID}/channel/{channel_id}.json?id={channel['id']}"
    
    print(f"📡 {channel['name']} থেকে ডাটা নিচ্ছি...")
    
    try:
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            print(f"  ⚠️  স্ট্যাটাস {response.status_code} - স্কিপ")
            return None
        
        data = response.json()
        
        # JSON থেকে identifier এবং userId খোঁজা
        result = extract_ids(data)
        
        if result:
            print(f"  ✅ identifier: {result['identifier']}")
            print(f"  ✅ userId: {result['user_id']}")
            
            # লোগো খোঁজা
            logo = extract_logo(data)
            if not logo:
                logo = DEFAULT_LOGOS.get(channel["id"], "")
                print(f"  ℹ️  ডিফল্ট লোগো ব্যবহার করা হবে")
            
            return {
                "name": channel["name"],
                "group": channel["group"],
                "identifier": result["identifier"],
                "user_id": result["user_id"],
                "logo": logo
            }
        else:
            print(f"  ❌ identifier/userId পাওয়া যায়নি")
            return None
            
    except Exception as e:
        print(f"  ❌ এরর: {str(e)[:50]}")
        return None

def extract_ids(data):
    """JSON থেকে identifier এবং userId খুঁজে বের করে"""
    
    # স্ট্রিং-এ সার্চ করার জন্য JSON স্ট্রিং বানানো
    json_str = json.dumps(data)
    
    result = {}
    
    # identifier খোঁজা
    import re
    identifier_match = re.search(r'"identifier"\s*:\s*"([^"]+)"', json_str)
    if identifier_match:
        result["identifier"] = identifier_match.group(1)
    
    # userId খোঁজা
    userid_match = re.search(r'"userId"\s*:\s*"([^"]+)"', json_str)
    if userid_match:
        result["user_id"] = userid_match.group(1)
    
    # দুইটাই পাওয়া গেলে রিটার্ন
    if "identifier" in result and "user_id" in result:
        return result
    
    # নাহলে ডিকশনারি ট্রাভার্স করে খোঁজা
    return traverse_dict(data)

def traverse_dict(obj, depth=0):
    """ডিকশনারি ট্রাভার্স করে identifier/userId খোঁজে"""
    if depth > 10:
        return None
    
    result = {}
    
    if isinstance(obj, dict):
        # সরাসরি খোঁজা
        if "identifier" in obj and isinstance(obj["identifier"], str):
            result["identifier"] = obj["identifier"]
        if "userId" in obj and isinstance(obj["userId"], (str, int)):
            result["user_id"] = str(obj["userId"])
        
        if "identifier" in result and "user_id" in result:
            return result
        
        # নেস্টেড খোঁজা
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                nested = traverse_dict(value, depth + 1)
                if nested:
                    result.update(nested)
                    if "identifier" in result and "user_id" in result:
                        return result
    
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                nested = traverse_dict(item, depth + 1)
                if nested:
                    result.update(nested)
                    if "identifier" in result and "user_id" in result:
                        return result
    
    return result if result else None

def extract_logo(data):
    """JSON থেকে লোগো URL খুঁজে বের করে"""
    
    json_str = json.dumps(data)
    
    # লোগো খোঁজা
    import re
    logo_match = re.search(r'"logo"\s*:\s*"([^"]+)"', json_str)
    
    if logo_match:
        logo = logo_match.group(1)
        # relative path হলে base_url যোগ
        if logo.startswith("/"):
            logo = f"{BASE_URL}{logo}"
        return logo
    
    return None

def create_m3u8_playlist(channels_data):
    """M3U8 প্লেলিস্ট তৈরি করে"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    m3u8 = "#EXTM3U\n"
    m3u8 += f"#PLAYLIST: বাংলাদেশ টেলিভিশন চ্যানেল\n"
    m3u8 += f"#UPDATED: {timestamp}\n"
    m3u8 += f"#SOURCE: {BASE_URL}\n"
    m3u8 += f"#TOTAL CHANNELS: {len(channels_data)}\n\n"
    
    for ch in channels_data:
        if ch:
            m3u8_url = f"{BASE_URL}/live/{ch['identifier']}/{USER_COUNTRY}/{ch['user_id']}/index.m3u8"
            
            # EXTINF লাইন
            m3u8 += f'#EXTINF:-1 tvg-id="{ch["identifier"]}" '
            m3u8 += f'tvg-name="{ch["name"]}" '
            m3u8 += f'tvg-logo="{ch["logo"]}" '
            m3u8 += f'group-title="{ch["group"]}",{ch["name"]}\n'
            m3u8 += f"{m3u8_url}\n\n"
    
    return m3u8

def create_json_output(channels_data):
    """JSON আউটপুট তৈরি করে"""
    
    output = {
        "last_updated": datetime.now().isoformat(),
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
                "user_id": ch["user_id"],
                "logo": ch["logo"],
                "url": f"{BASE_URL}/live/{ch['identifier']}/{USER_COUNTRY}/{ch['user_id']}/index.m3u8"
            })
    
    return output

def main():
    """মেইন ফাংশন"""
    
    print("=" * 60)
    print("🇧🇩  বাংলাদেশ টেলিভিশন চ্যানেল লিংক জেনারেটর")
    print("=" * 60)
    print(f"📅 সময়: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 বিল্ড আইডি: {BUILD_ID}")
    print(f"🌍 দেশ: {USER_COUNTRY}")
    print("=" * 60)
    
    print(f"\n📡 {len(CHANNELS)} টি চ্যানেল থেকে ডাটা সংগ্রহ করা হচ্ছে...\n")
    
    # সব চ্যানেলের ডাটা সংগ্রহ
    channels_data = []
    for channel in CHANNELS:
        data = fetch_channel_data(channel)
        if data:
            channels_data.append(data)
        print()  # খালি লাইন
    
    # M3U8 প্লেলিস্ট তৈরি
    m3u8_content = create_m3u8_playlist(channels_data)
    
    # JSON আউটপুট তৈরি
    json_output = create_json_output(channels_data)
    
    # ফাইল সেভ করা
    with open("btv_channels.m3u8", "w", encoding="utf-8") as f:
        f.write(m3u8_content)
    
    with open("btv_channels.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    # রিপোর্ট
    print("=" * 60)
    print("📊  রিপোর্ট:")
    print(f"    মোট চ্যানেল: {len(CHANNELS)}")
    print(f"    সফল: {len(channels_data)}")
    print(f"    ব্যর্থ: {len(CHANNELS) - len(channels_data)}")
    print("=" * 60)
    print("✅ btv_channels.m3u8  - M3U8 প্লেলিস্ট (VLC-তে খুলুন)")
    print("✅ btv_channels.json   - JSON ডাটা")
    print("=" * 60)
    
    # সফল চ্যানেলের তালিকা
    if channels_data:
        print("\n📺  সফল চ্যানেলসমূহ:")
        for i, ch in enumerate(channels_data, 1):
            print(f"   {i}. {ch['name']}")

if __name__ == "__main__":
    main()
