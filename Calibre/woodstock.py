import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, datetime, timedelta

language = 'en'

site_url = 'http://okckd.github.io/blog/archives/'

title = 'woodstock'
   
def find_by_class(tag, name, cls):
    for c in tag.findAll(name):
        c_cls = c.get('class')
        if not c_cls: continue
        if cls not in c_cls: continue
        
        yield c

class WoodStock(BasicNewsRecipe):
    title = title

    language = language
    
    no_stylesheets = True
    
    keep_only_tags = [ { 'class': 'journal-entry-text' } ]
    
    remove_tags = [
        { 'id': 'comments' },
        { 'class': 'jiathis_style' },
    ]

    remove_tags_after = [
        { 'id': 'comments' },
        { 'class': 'jiathis_style' }
    ]

    simultaneous_downloads = 10

    def parse_index(self):
        print '>>> Starting parse items'
        count = 0
        index = []
        item_list = []
        root = self.index_to_soup(site_url)
        content_id = root.find('div', { 'id': 'blog-archives' })
        for li in content_id.findAll('article'):
            item = {}
            item['title'] = unicode(li.h1.a.string)
            item['url'] = li.h1.a['href']
            item['description'] = item['title']
            item['date'] = datetime.today()
            print '>>> Item parsed: ', item
            item_list.append(item)

        index.append((title, item_list))
        return index
        
    