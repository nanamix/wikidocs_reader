from wikidocs_reader import SearchService
class Gateway:
 def __init__(self):self.calls=0
 def search_public_books(self,q,page=1):self.calls+=1;return [{'title':q}]
class Cache:
 def __init__(self):self.d={}
 def get(self,k):return self.d.get(k)
 def set(self,k,v,ttl):self.d[k]=v
 def purge(self):pass
 def purge_to_size(self,n):pass
def test_search_service_caches():
 g=Gateway();s=SearchService(g,Cache());assert s.search('파이썬')==[{'title':'파이썬'}];assert s.search('파이썬')==[{'title':'파이썬'}];assert g.calls==1

def test_desktop_reader_arrow_navigation_handler():
    from pathlib import Path
    script = Path(__file__).resolve().parents[1] / 'script.js'
    source = script.read_text()
    assert "'ArrowLeft','ArrowRight','ArrowUp','ArrowDown','PageUp','PageDown','Home','End'" in source
    assert "e.key==='Home'||e.key==='End'" in source
    assert "content.scrollTo({top:e.key==='Home'?0:content.scrollHeight" in source
    assert "this.index+(e.key==='ArrowLeft'?-1:1)" in source
    assert "e.preventDefault()" in source

def test_desktop_reader_vertical_scroll_keyboard_handler():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'script.js').read_text()
    assert "'ArrowUp','ArrowDown','PageUp','PageDown'" in source
    assert "content.scrollBy({top:" in source
    assert "content.clientHeight" in source
