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
    headers = { "Authorization": f"Bearer {token}"}
    
    
    now = datetime.datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    query = """
    query($login:String!, $from:DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
              }
            }
          }
        }
        repositories(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name color }
              }
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
    sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)[:2] # Top 2
    
    formatted_langs = []
    for name, size in sorted_langs:
        percentage = round((size / total_size) * 100) if total_size > 0 else 0
        formatted_langs.append({"name": name, "percent": percentage})

    return {
        "daily": daily_counts[:31],
        "total": res_data['contributionsCollection']['contributionCalendar']['totalContributions'],
        "langs": formatted_langs
    }

def update_svg(data):
    theme = get_theme()
    with open('src/template.svg', 'r') as f:
        svg = f.read()

    for i, count in enumerate(data['daily']):
        day_id = f'id="day_{i+1}"'
        color = theme['empty']
        if count > 0:
            color = theme['low'] if count < 3 else (theme['med'] if count < 7 else theme['high'])
        
        svg = re.sub(f'({day_id}.*?fill=")#1e1e1e"', f'\\1{color}"', svg)

    for i, lang in enumerate(data['langs']):
        svg = svg.replace(f'JavaScript' if i==0 else 'Python', lang['name'])
        svg = re.sub(fr'(id="lang_{i+1}_bar".*?width=")\d+"', f'\\1{int(lang["percent"] * 1.8)}"', svg)
        svg = svg.replace('35%' if i==0 else '25%', f"{lang['percent']}%")

    svg = svg.replace('>0</text>', f">{data['total']}</text>")
    svg = svg.replace("March 2026", datetime.datetime.now().strftime("%B %Y"))

    with open('heart.svg', 'w') as f:
        f.write(svg)

if __name__ == "__main__":
    TOKEN = os.getenv("GH_TOKEN")
    USER = os.getenv("GH_USERNAME")
    github_data = fetch_github_data(TOKEN, USER)
    update_svg(github_data)