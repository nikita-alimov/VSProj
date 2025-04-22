import requests
from bs4 import BeautifulSoup

url = "https://example.com"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Example: Extracting all links
links = [a['href'] for a in soup.find_all('a', href=True)]
print("Extracted links:", links)