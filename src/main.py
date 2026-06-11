import os
import requests
import datetime
import re

def get_theme():
    """Returns colors based on the current season."""
    month = datetime.datetime.now().month
    # March-May (Spring): Green | June-Aug (Summer): Amber | Sept-Nov (Autumn): Orange | Dec-Feb (Winter): Blue
    if 3 <= month <= 5: return {
        "low": "#1a332a", 
        "med": "#2d8c63", 
        "high": "#10b981", 
        "empty": "#1e1e1e"
        }
    if 6 <= month <= 8: return {
        "low": "#3d3014", 
        "med": "#b45309", 
        "high": "#f59e0b", 
        "empty": "#1e1e1e"
        }
    if 9 <= month <= 11: return {
        "low": "#3d1e14", 
        "med": "#9a3412", 
        "high": "#ea580c", 
        "empty": "#1e1e1e"
        }
    return {
        "low": "#1e293b", 
        "med": "#3b82f6", 
        "high": "#60a5fa", 
        "empty": "#1e1e1e"
        }

def fetch_github_data(token, username):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    print(f"🔍 DEBUG INFO:")
    print(f"   Current time: {now}")
    print(f"   Query start date: {start_of_month}")
    print(f"   Current month: {now.month}, Current year: {now.year}")
    
    query = """
    query($login:String!, $from:DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from) {
          contributionCalendar {
            totalContributions
            weeks { 
              contributionDays { 
                date
                contributionCount 
              } 
            }
          }
        }
        repositories(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
      }
    }
    """
    response = requests.post(url, json={'query': query, 'variables': {'login': username, 'from': start_of_month}}, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        print(f"   Response: {response.text}")
        raise Exception(f"GitHub API error: {response.status_code}")
    
    res_data = response.json()['data']['user']
    print(f"✅ API call succeeded")
    
    # Process Language Statistics
    lang_stats = {}
    for repo in res_data['repositories']['nodes']:
        for e in repo['languages']['edges']:
            name = e['node']['name']
            lang_stats[name] = lang_stats.get(name, 0) + e['size']

    html_css_sum = lang_stats.pop("HTML", 0) + lang_stats.pop("CSS", 0)
    if html_css_sum > 0:
        lang_stats["HTML/CSS"] = html_css_sum

    total_size = sum(lang_stats.values())
    priority_order = ["JavaScript", "TypeScript", "Python", "HTML/CSS"]
    
    raw_data = []
    for name in priority_order:
        size = lang_stats.pop(name, 0)
        raw_p = (size / total_size) * 100 if total_size > 0 else 0
        raw_data.append({"name": name, "raw": raw_p})
    
    remaining_size = sum(lang_stats.values())
    other_p = (remaining_size / total_size) * 100 if total_size > 0 else 0
    raw_data.append({"name": "Other", "raw": other_p})

    formatted = [{"name": d["name"], "raw": d["raw"], "percent": int(d["raw"]), "remainder": d["raw"] - int(d["raw"])} for d in raw_data]
    
    diff = 100 - sum(d["percent"] for d in formatted)
    formatted.sort(key=lambda x: x["remainder"], reverse=True)
    for i in range(diff):
        formatted[i]["percent"] += 1
        
    order_map = {name: i for i, name in enumerate(priority_order + ["Other"])}
    formatted.sort(key=lambda x: order_map[x["name"]])

    # Filter daily counts to only include current month's days
    current_month = now.month
    current_year = now.year
    daily_counts = []
    all_days_raw = []
    
    for week in res_data['contributionsCollection']['contributionCalendar']['weeks']:
        for day in week['contributionDays']:
            date_obj = datetime.datetime.strptime(day['date'], "%Y-%m-%d")
            all_days_raw.append((day['date'], day['contributionCount'], date_obj.month, date_obj.year))
            # Only include days from current month
            if date_obj.month == current_month and date_obj.year == current_year:
                daily_counts.append(day['contributionCount'])
    
    print(f"\n📊 CONTRIBUTION DATA:")
    print(f"   All days returned by API (first 10): {all_days_raw[:10]}")
    print(f"   Filtered to current month ({current_month}/{current_year}): {len(daily_counts)} days")
    print(f"   Daily counts: {daily_counts[:10]}... (showing first 10)")
    print(f"   Total contributions: {res_data['contributionsCollection']['contributionCalendar']['totalContributions']}")
    
    # Pad with zeros for days that haven't occurred yet
    days_in_current_month = (now.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
    days_in_current_month = days_in_current_month.day
    padded_daily = daily_counts + [0] * (days_in_current_month - len(daily_counts))
    print(f"   After padding: {len(padded_daily)} days (full month)")
    
    return {
        "daily": padded_daily,
        "total": res_data['contributionsCollection']['contributionCalendar']['totalContributions'],
        "langs": formatted
    }

def update_svg(data):
    theme = get_theme()
    now = datetime.datetime.now()
    
    print(f"\n🎨 UPDATING SVG:")
    print(f"   Theme: Spring (Green)" if 3 <= now.month <= 5 else f"   Theme: Current season")
    
    with open('src/template.svg', 'r') as f:
        svg = f.read()
    print(f"   ✓ Loaded template.svg ({len(svg)} bytes)")

    # Dynamically handle variable month lengths
    days_in_month = (now.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
    days_in_month = days_in_month.day
    print(f"   Days in current month: {days_in_month}")

    for i in range(1, days_in_month + 1):
        count = data['daily'][i-1] if i-1 < len(data['daily']) else 0
        color = theme['empty']
        if count > 0:
            color = theme['low'] if count < 3 else (theme['med'] if count < 7 else theme['high'])
        svg = re.sub(f'(id="day_{i}".*?fill=")#1e1e1e"', r'\g<1>' + color + '"', svg)

    for i, lang in enumerate(data['langs']):
        idx = i + 1
        width = int((lang["percent"] / 100) * 250) if lang["percent"] > 0 else 0
        
        svg = re.sub(fr'(id="lang_{idx}_name".*?>)[^<]*(</text>)', fr'\g<1>{lang["name"]}\g<2>', svg)
        svg = re.sub(fr'(id="lang_{idx}_percent".*?>)[^<]*(</text>)', fr'\g<1>{lang["percent"]}%\g<2>', svg)
        svg = re.sub(fr'(id="lang_{idx}_bar".*?width=")\d+(")', fr'\g<1>{width}\g<2>', svg)

    svg = re.sub(r'(id="total_count".*?>)0(</text>)', fr'\g<1>{data["total"]}\g<2>', svg)
    
    current_month = now.strftime('%B %Y')
    footer_text = f"Automated Dashboard • Resets Monthly: {current_month}"
    svg = re.sub(r'(id="footer_text".*?>)[^<]*(</text>)', fr'\g<1>{footer_text}\g<2>', svg)

    with open('heart.svg', 'w') as f:
        f.write(svg)
    
    print(f"   ✓ Wrote heart.svg ({len(svg)} bytes)")
    print(f"\n✅ SUCCESS! Dashboard updated for {current_month}")

if __name__ == "__main__":
    TOKEN = os.getenv("GH_TOKEN")
    USER = os.getenv("GH_USERNAME")
    print(f"🚀 Starting GitHub Heart Dashboard Update")
    print(f"   Username: {USER}")
    print(f"   Token present: {bool(TOKEN)}")
    if TOKEN and USER:
        try:
            update_svg(fetch_github_data(TOKEN, USER))
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n❌ ERROR: Missing GH_TOKEN or GH_USERNAME")
