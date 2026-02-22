import requests
import json
import re
from datetime import datetime

# ============================================
# বাংলাদেশ টেলিভিশন চ্যানেল লিংক জেনারেটর
# ============================================

BASE_URL = "https://www.btvlive.gov.bd"
USER_COUNTRY = "BD"
BUILD_ID = "wr5BMimBGS-yN5Rc2tmam"

CHANNELS = [
    {"id": "BTV", "name": "BTV", "group": "BTV"},
    {"id": "BTV World", "name": "BTV World", "group": "BTV"},
    {"id": "Sangsad Television", "name": "সংসদ টেলিভিশন", "group": "Parliament"},
    {"id": "BTV Chattogram", "name": "BTV চট্টগ্রাম", "group": "BTV"}
]

def fetch_channel_data(channel):
    """একটি চ্যানেলের ডাটা API থেকে ফেচ করে"""
    
    channel_id = channel["id"].replace(" ", "%20")
    api_url = f"{BASE_URL}/_next/data/{BUILD_ID}/channel/{channel_id}.json?id={channel['id']}"
    
    print(f"📡 {channel['name']} থেকে ডাটা নিচ্ছি...")
    print(f"   URL: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=10)
        
        if response.status_code != 200:
            print(f"  ⚠️  স্ট্যাটাস {response.status_code} - স্কিপ")
            return None
        
        data = response.json()
        
        # সম্পূর্ণ JSON ডিবাগের জন্য (প্রথম 500 ক্যারেক্টার)
        json_str = json.dumps(data)[:500]
        # print(f"  📄 JSON: {json_str}...")
        
        # identifier খোঁজা
        identifier = find_value(data, "identifier")
        if not identifier:
            print(f"  ❌ identifier পাওয়া যায়নি")
            return None
        
        print(f"  ✅ identifier: {identifier}")
        
        # userId খোঁজা - বিভিন্ন নামে খোঁজা
        user_id = find_value(data, "userId")
        if not user_id:
            user_id = find_value(data, "uid")
        if not user_id:
            user_id = find_value(data, "id", path=["streams", "0"])
        if not user_id:
            user_id = find_value(data, "streamId")
        
        if not user_id:
            print(f"  ❌ userId পাওয়া যায়নি")
            # userId না পেলে, আমরা identifier-ই userId হিসেবে ব্যবহার করব?
            # এটা একটা সমাধান হতে পারে
            user_id = identifier
            print(f"  ⚠️  identifier-কেই userId হিসেবে ব্যবহার করা হচ্ছে")
        else:
            print(f"  ✅ userId: {user_id}")
        
        # লোগো খোঁজা
        logo = find_value(data, "logo")
        if logo:
            if logo.startswith("/"):
                logo = f"{BASE_URL}{logo}"
            print(f"  ✅ লোগো: {logo[:50]}...")
        else:
            # ডিফল্ট লোগো
            logo = f"{BASE_URL}/images/{channel['id'].lower().replace(' ', '-')}-logo.png"
            print(f"  ℹ️  ডিফল্ট লোগো ব্যবহার করা হবে")
        
        return {
            "name": channel["name"],
            "group": channel["group"],
            "identifier": identifier,
            "user_id": user_id,
            "logo": logo
        }
            
    except Exception as e:
        print(f"  ❌ এরর: {str(e)[:100]}")
        return None

def find_value(obj, key, path=None):
    """JSON-এ key খুঁজে বের করে - উন্নত ভার্সন"""
    
    if isinstance(obj, dict):
        # সরাসরি key থাকলে
        if key in obj:
            return obj[key]
        
        # সব key চেক করা (case insensitive)
        for k, v in obj.items():
            if k.lower() == key.lower():
                return v
        
        # নেস্টেড সার্চ
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                result = find_value(v, key)
                if result:
                    return result
    
    elif isinstance(obj, list):
        # লিস্টের প্রথম আইটেমে সার্চ
        for item in obj:
            if isinstance(item, (dict, list)):
                result = find_value(item, key)
                if result:
                    return result
    
    # স্পেসিফিক পাথ দেওয়া থাকলে (যেমন: ["streams", 0, "id"])
    if path:
        try:
            current = obj
            for p in path:
                if isinstance(p, int):
                    current = current[p]
                else:
                    current = current[p]
            return current
        except:
            pass
    
    return None

def find_value_regex(data, pattern):
    """Regex ব্যবহার করে value খোঁজা (যখন key জানা নেই)"""
    json_str = json.dumps(data)
    match = re.search(pattern, json_str)
    if match:
        return match.group(1)
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
    
    channels_data = []
    for channel in CHANNELS:
        data = fetch_channel_data(channel)
        if data:
            channels_data.append(data)
        print()  # খালি লাইন
    
    if not channels_data:
        print("❌ কোনো চ্যানেলের ডাটা পাওয়া যায়নি")
        return
    
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
    print("✅ btv_channels.m3u8  - M3U8 প্লেলিস্ট")
    print("✅ btv_channels.json   - JSON ডাটা")
    print("=" * 60)
    
    if channels_data:
        print("\n📺  সফল চ্যানেলসমূহ:")
        for i, ch in enumerate(channels_data, 1):
            print(f"   {i}. {ch['name']} (ID: {ch['user_id'][:8]}...)")

if __name__ == "__main__":
    main()
