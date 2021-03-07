import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, datetime, timedelta
title = 'Jeff.Zhao'
language = 'zh'

site_url = 'http://blog.zhaojie.me/2009/12/valuable-posts-index.html'

title_prefix = 'Jeff.Zhao'
   
def find_by_class(tag, name, cls):
    for c in tag.findAll(name):
        c_cls = c.get('class')
        if not c_cls: continue
        if cls not in c_cls: continue
        
        yield c

class CoolShell(BasicNewsRecipe):
    title = 'Jeff.Zhao'
    language = language
    
    no_stylesheets = True
    
    keep_only_tags = [ { 'id': 'content' } ]
    
    remove_tags = [
        { 'id': 'noOfComments' },
        { 'class': 'share_this' },
        { 'class': 'article_page_right' }
    ]
    
    def parse_index(self):
        print '>>> Starting parse items'
        index = []
        item_list = []
        root = self.index_to_soup(site_url)
        content_id = root.find('div', { 'id': 'content' })
        post_div = content_id.find('div', { 'class': 'post' })
        for li in post_div.findAll('li'):
            item = {}
            item['title'] = li.a.string
            item['url'] = li.a['href']
            if 'blog.zhaojie.me' not in li.a['href']: continue
            item['description'] = li.a.string
            item['date'] = datetime.today()
            item_list.append(item)
            print '>>> Item parsed: ', item
            
        index.append((title_prefix, item_list))
        return index
    