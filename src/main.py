import os, requests, datetime, re

def get_theme():
    # March to May Green Theme
    return {"low": "#1a332a", "med": "#2d8c63", "high": "#10b981", "empty": "#1e1e1e"}

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
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
      }
    }
    """
    response = requests.post(url, json={'query': query, 'variables': {'login': username, 'from': start_of_month}}, headers=headers)
    res_data = response.json()['data']['user']
    
    # Extract contribution counts
    weeks = res_data['contributionsCollection']['contributionCalendar']['weeks']
    daily = [d['contributionCount'] for w in weeks for d in w['contributionDays']]
    
    # Process Top 3 Languages + Other
    lang_stats = {}
    for repo in res_data['repositories']['nodes']:
        for e in repo['languages']['edges']:
            name = e['node']['name']
            lang_stats[name] = lang_stats.get(name, 0) + e['size']
    
    total_size = sum(lang_stats.values())
    sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)
    
    top_3 = sorted_langs[:3]
    other_size = sum(s for n, s in sorted_langs[3:])
    
    formatted = []
    for n, s in top_3:
        p = round((s / total_size) * 100) if total_size > 0 else 0
        formatted.append({"name": n, "percent": p})
    if other_size > 0:
        formatted.append({"name": "Other", "percent": round((other_size / total_size) * 100)})

    return {"daily": daily[:31], "total": res_data['contributionsCollection']['contributionCalendar']['totalContributions'], "langs": formatted}

def update_svg(data):
    theme = get_theme()
    with open('src/template.svg', 'r') as f:
        svg = f.read()

    # Fill heart with colors based on count
    for i, count in enumerate(data['daily']):
        color = theme['empty']
        if count > 0:
            color = theme['low'] if count < 3 else (theme['med'] if count < 7 else theme['high'])
        svg = re.sub(f'(id="day_{i+1}".*?fill=")#1e1e1e"', f'\\1{color}"', svg)

    # Dynamic language update (Max 4 slots in template)
    for i, lang in enumerate(data['langs'][:4]):
        idx = i + 1
        svg = re.sub(fr'(id="lang_{idx}_bar".*?)\s+width="\d+"', fr'\1 width="{int(lang["percent"] * 2.2)}"', svg)
        svg = re.sub(fr'(id="lang_{idx}_name".*?>)[^<]+(<)', fr'\1{lang["name"]}\2', svg)
        svg = re.sub(fr'(id="lang_{idx}_percent".*?>)[^<]+(<)', fr'\1{lang["percent"]}% \2', svg)

    # Update Total Counter
    svg = re.sub(r'id="total_count".*?>0</text>', f'id="total_count">{data["total"]}</text>', svg)
    
    # Update Footer Date
    svg = svg.replace("March 2026", datetime.datetime.now().strftime("%B %Y"))

    with open('heart.svg', 'w') as f:
        f.write(svg)

if __name__ == "__main__":
    TOKEN = os.getenv("GH_TOKEN")
    USER = os.getenv("GH_USERNAME")
    update_svg(fetch_github_data(TOKEN, USER))