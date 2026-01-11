import requests
import re
import json
import logging
import random
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("XHS_Scraper")

class XHSScraper:
    def __init__(self, cookies=None):
        self.session = requests.Session()
        self.cookie = cookies if cookies else ""
        self.ua_desktop = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        self.ua_mobile = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"

    def _get_headers(self, type="desktop"):
        headers = {
            "User-Agent": self.ua_mobile if type == "mobile" else self.ua_desktop,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if self.cookie: headers["Cookie"] = self.cookie
        return headers

    def resolve_redirects(self, url: str) -> str:
        if "xhslink.com" not in url: return url
        try:
            res = self.session.get(url, headers=self._get_headers("mobile"), allow_redirects=True, timeout=10)
            return res.url
        except: return url

    def extract_note_id(self, url: str) -> str:
        patterns = [r'/explore/([a-fA-F0-9]{24})', r'/discovery/item/([a-fA-F0-9]{24})', r'item/([a-fA-F0-9]{24})']
        for p in patterns:
            match = re.search(p, url)
            if match: return match.group(1)
        return None

    def get_data(self, raw_url: str):
        real_url = self.resolve_redirects(raw_url.strip())
        note_id = self.extract_note_id(real_url)
        if not note_id: return {"success": False, "message": f"Không tìm thấy ID. URL: {real_url}"}

        # Strategy 1: XHS Lib
        try:
            from xhs import XhsClient
            if self.cookie:
                client = XhsClient(cookie=self.cookie)
                note = client.get_note_by_id(note_id)
                if note: return self._format_response(note, "API Lib")
        except: pass

        # Strategy 2: HTML Desktop
        try:
            res = self.session.get(real_url, headers=self._get_headers("desktop"), timeout=10)
            data = self._parse_html_soup(res.text)
            if data: return data
        except: pass

        # Strategy 3: HTML Mobile
        try:
            res = self.session.get(real_url, headers=self._get_headers("mobile"), timeout=10)
            data = self._parse_html_soup(res.text)
            if data: return data
        except: pass

        return {"success": False, "message": "Không thể lấy dữ liệu (Captcha/Cookie Error)."}

    def _parse_html_soup(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and '__INITIAL_STATE__' in script.string:
                try:
                    json_text = script.string
                    start = json_text.find('{')
                    end = json_text.rfind('}') + 1
                    if start != -1:
                        json_str = json_text[start:end].replace("undefined", "null")
                        state = json.loads(json_str)
                        note_map = state.get("note", {}).get("noteDetailMap", {})
                        if note_map:
                            first_key = next(iter(note_map))
                            return self._format_response(note_map[first_key].get("note", {}), "HTML Soup")
                except: pass
        return None

    def _format_response(self, note, source):
        if not note: return None
        title = note.get('title', 'No Title')
        type_ = note.get('type', 'normal')
        files = []

        if type_ == 'video':
            video_node = note.get('video', {})
            url = video_node.get('media', {}).get('stream', {}).get('h264', [{}])[0].get('masterUrl')
            if not url: url = video_node.get('masterUrl')
            if not url: 
                url = video_node.get('consumer', {}).get('originVideoKey')
                if url and not url.startswith('http'): url = f"https://sns-video-bd.xhscdn.com/{url}"
            
            # FORCE HTTPS
            if url and url.startswith('http:'): url = url.replace('http:', 'https:')
            if url and url.startswith('//'): url = 'https:' + url

            if url:
                files.append({
                    "type": "video", 
                    "url": url, 
                    "cover": note.get('imageList', [{}])[0].get('urlDefault', ''),
                    "filename": f"{note.get('noteId')}.mp4"
                })
        else:
            for idx, img in enumerate(note.get('imageList', [])):
                url = img.get('urlOriginal') or img.get('urlDefault')
                # FORCE HTTPS
                if url and url.startswith('http:'): url = url.replace('http:', 'https:')
                if url and url.startswith('//'): url = 'https:' + url
                
                if url:
                    files.append({
                        "type": "image", 
                        "url": url, 
                        "filename": f"{note.get('noteId')}_{idx}.jpg"
                    })

        return {
            "success": True,
            "data": {
                "id": note.get('noteId'),
                "title": title,
                "author": {"name": note.get('user', {}).get('nickname'), "avatar": note.get('user', {}).get('avatar')},
                "files": files,
                "total": len(files),
                "source": source
            }
        }

def scrape_xhs(url, cookies=None):
    return XHSScraper(cookies).get_data(url)