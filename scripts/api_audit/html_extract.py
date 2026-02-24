from bs4 import BeautifulSoup


def extract_script(html: str) -> str:
    """Extract concatenated <script> content from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all('script')
    parts = [s.string or '' for s in scripts]
    return '\n'.join(parts).strip()
