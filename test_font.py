import urllib.request
from bs4 import BeautifulSoup
url = 'https://www.arfonts.net/ready-designs/%D8%AA%D8%B5%D9%85%D9%8A%D9%85-%D8%B1%D8%AD%D9%85%D9%87-%D8%A7%D9%84%D9%84%D9%87-04028'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        print(f"Title: {html.split('<title>')[1].split('</title>')[0] if '<title>' in html else 'No title'}")
        
        # Check if the name 'ALAEM' is in the document
        if 'alaem' in html.lower():
            print("Found 'alaem' in html")
        
        blocks = html.split('<')
        for b in blocks:
            if 'alaem' in b.lower() or '?????' in b.lower():
                print("Snippet:", b[:50])
except Exception as e:
    print('Failed:', str(e))
