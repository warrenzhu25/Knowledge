import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, datetime, timedelta

language = 'zh'

site_url = 'http://coolshell.cn/'

title = 'CoolShell.Month'
   
def find_by_class(tag, name, cls):
    for c in tag.findAll(name):
        c_cls = c.get('class')
        if not c_cls: continue
        if cls not in c_cls: continue
        
        yield c

class CoolShell(BasicNewsRecipe):
    title = title

    language = language
    
    no_stylesheets = True

    max_articles_per_feed = 1000
    
    keep_only_tags = [ { 'class': 'post' } ]
    
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
        westsidebar_id = root.find('div', { 'id': 'westsidebar' })
        for li in westsidebar_id.findAll('li'):
            month_url = li.a['href']
            month_page = int(li.contents[1].replace("(","").replace(")","").strip())/10 + 2
            for page_num in range(1, month_page):
                month_root = {}
                if page_num == 1: 
                    month_root = self.index_to_soup(month_url)
                    print '>>> Fetching', month_url
                if page_num > 1: 
                    month_page_url = month_url + "/page/" + str(page_num)
                    month_root = self.index_to_soup(month_page_url)
                    print '>>> Fetching', month_page_url
                for post in month_root.findAll('div', { 'class': 'post'}):
                    item = {}
                    item['title'] = unicode(post.h2.a.string)
                    item['url'] = post.h2.a['href']
                    item['description'] = item['title']
                    item['date'] = datetime.today()
                    print '>>> Item parsed: ', item
                    if count > 330 : 
                        index.append((title, item_list))
                        return index
                    item_list.append(item)
                    count = count + 1
        
    