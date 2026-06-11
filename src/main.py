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
    
    query = """
    query($login:String!, $from:DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
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
        raise Exception(f"GitHub API error {response.status_code}: {response.text}")
    res_data = response.json()['data']['user']
    
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

    current_month = now.month
    current_year = now.year
    daily_counts = []
    for w in res_data['contributionsCollection']['contributionCalendar']['weeks']:
        for d in w['contributionDays']:
            date_obj = datetime.datetime.strptime(d['date'], "%Y-%m-%d")
            if date_obj.month == current_month and date_obj.year == current_year:
                daily_counts.append(d['contributionCount'])

    # Current streak: consecutive days with contributions working backwards
    today = now.day
    actual_days = daily_counts[:today]
    streak = 0
    for count in reversed(actual_days):
        if count > 0:
            streak += 1
        else:
            break

    return {
        "daily": daily_counts,
        "total": res_data['contributionsCollection']['contributionCalendar']['totalContributions'],
        "streak": streak,
        "langs": formatted
    }
    

def update_svg(data):
    theme = get_theme()
    now = datetime.datetime.now()
    
    with open('src/template.svg', 'r') as f:
        svg = f.read()

    for i in range(1, 32):
        count = data['daily'][i-1] if i-1 < len(data['daily']) else 0
        color = theme['empty']
        if count > 0:
            color = theme['low'] if count < 3 else (theme['med'] if count < 7 else theme['high'])
        svg = re.sub(f'(id="day_{i}".*?fill=")#1e1e1e"', r'\g<1>' + color + '"', svg)

    # Sync legend colors to current season
    svg = re.sub(r'(id="legend_empty".*?fill=")#[0-9a-fA-F]{6}"', r'\g<1>' + theme['empty'] + '"', svg)
    svg = re.sub(r'(id="legend_low".*?fill=")#[0-9a-fA-F]{6}"', r'\g<1>' + theme['low'] + '"', svg)
    svg = re.sub(r'(id="legend_med".*?fill=")#[0-9a-fA-F]{6}"', r'\g<1>' + theme['med'] + '"', svg)
    svg = re.sub(r'(id="legend_high".*?fill=")#[0-9a-fA-F]{6}"', r'\g<1>' + theme['high'] + '"', svg)

    for i, lang in enumerate(data['langs']):
        idx = i + 1
        width = int((lang["percent"] / 100) * 250) if lang["percent"] > 0 else 0
        
        svg = re.sub(fr'(id="lang_{idx}_name".*?>)[^<]*(</text>)', fr'\g<1>{lang["name"]}\g<2>', svg)
        svg = re.sub(fr'(id="lang_{idx}_percent".*?>)[^<]*(</text>)', fr'\g<1>{lang["percent"]}%\g<2>', svg)
        svg = re.sub(fr'(id="lang_{idx}_bar".*?width=")\d+(")', fr'\g<1>{width}\g<2>', svg)
        
    svg = re.sub(r'(id="total_count".*?>)\d+(</text>)', fr'\g<1>{data["total"]}\g<2>', svg)
    svg = re.sub(r'(id="streak_count".*?>)\d+(</text>)', fr'\g<1>{data["streak"]}\g<2>', svg)
    
    current_month = now.strftime('%B %Y')
    footer_text = f"Automated Dashboard • Resets Monthly: {current_month}"
    svg = re.sub(r'(id="footer_text".*?>)[^<]*(</text>)', fr'\g<1>{footer_text}\g<2>', svg)

    with open('heart.svg', 'w') as f:
        f.write(svg)

if __name__ == "__main__":
    TOKEN = os.getenv("GH_TOKEN")
    USER = os.getenv("GH_USERNAME")
    if TOKEN and USER:
        update_svg(fetch_github_data(TOKEN, USER))