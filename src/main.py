import os
import requests
import datetime
import re

# Seasonal theme switcher
def get_theme():
    month = datetime.datetime.now().month
    if 3 <= month <= 5: # Spring
        return {
            "low": "#1a332a", 
            "med": "#2d8c63", 
            "high": "#10b981", 
            "empty": "#1e1e1e"
        }
    if 6 <= month <= 8: # Summer
        return {
            "low": "#3d3014",
            "med": "#b45309", 
            "high": "#f59e0b",
            "empty": "#1e1e1e"
        }
    if 9 <= month <= 11: # Autumn
        return {
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
        } # Winter
    
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
            weeks { contributionDays { contributionCount } }
          }
        }
        repositories(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
      }
    }
    """
    response = requests.post(url, json={'query': query, 'variables': {'login': username, 'from': start_of_month}}, headers=headers)
    res_data = response.json()['data']['user']
    
    weeks = res_data['contributionsCollection']['contributionCalendar']['weeks']
    daily_counts = [day['contributionCount'] for week in weeks for day in week['contributionDays']]
    
    lang_stats = {}
    for repo in res_data['repositories']['nodes']:
        for edge in repo['languages']['edges']:
            name = edge['node']['name']
            lang_stats[name] = lang_stats.get(name, 0) + edge['size']
    
    total_size = sum(lang_stats.values())
    sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)[:3]
    
    formatted_langs = []
    for name, size in sorted_langs:
        p = round((size / total_size) * 100) if total_size > 0 else 0
        formatted_langs.append({"name": name, "percent": p})
        
    other_p = 100 - sum(l["percent"] for l in formatted_langs)
    if other_p > 0:
        formatted_langs.append({"name": "Other", "percent": other_p})

    return {
        "daily": daily_counts[:31],
        "total": res_data['contributionsCollection']['contributionCalendar']['totalContributions'],
        "langs": formatted_langs
    }

def update_svg(data):
    theme = get_theme()
    with open('src/template.svg', 'r') as f:
        svg = f.read()

    # Update Heart Colors
    for i, count in enumerate(data['daily']):
        color = theme['empty']
        if count > 0:
            color = theme['low'] if count < 3 else (theme['med'] if count < 7 else theme['high'])
        svg = re.sub(f'(id="day_{i+1}".*?fill=")#1e1e1e"', f'\\1{color}"', svg)

    # Update Languages (Multipler set to 2.2 for 220px bars)
    for i, lang in enumerate(data['langs']):
        idx = i + 1
        svg = re.sub(fr'(id="lang_{idx}_bar".*?)\s+width="\d+"', fr'\1 width="{int(lang["percent"] * 2.2)}"', svg)
        svg = re.sub(fr'(id="lang_{idx}_percent".*?>)[\d%]+(<)', fr'\1{lang["percent"]}% \2', svg)
        svg = re.sub(fr'(id="lang_{idx}_name".*?>)[^<]+(<)', fr'\1{lang["name"]}\2', svg)

    # Update Total Count (target specific ID)
    svg = re.sub(r'id="total_count".*?>0</text>', f'id="total_count">{data["total"]}</text>', svg)
    svg = svg.replace("March 2026", datetime.datetime.now().strftime("%B %Y"))

    with open('heart.svg', 'w') as f:
        f.write(svg)

if __name__ == "__main__":
    TOKEN = os.getenv("GH_TOKEN")
    USER = os.getenv("GH_USERNAME")
    update_svg(fetch_github_data(TOKEN, USER))