import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, datetime, timedelta

language = 'zh'

url = 'http://www.themianjing.com/'

title = u'面经'

class Mianjing(BasicNewsRecipe):
    title = title

    language = language

    simultaneous_downloads = 10

    max_articles_per_feed = 1000
    
    no_stylesheets = True
    
    keep_only_tags = [ { 'class': 'entry clearfix' } ]
    
    remove_tags = [
        { 'id': 'comments' },
        { 'class': 'jiathis_style' },
    ]

    remove_tags_after = [
        { 'id': 'jiathis_style_32x32' },
        { 'class': 'jiathis_style' }
    ]

    simultaneous_downloads = 10

    def parse_index(self):
        print '>>> Starting parse items'
        count = 0
        index = []
        
        
        for j in range(0, 5):
            item_list = []
            for i in range(j*10 + 1, j*10 + 11):
                
                if(i == 1):
                    root = self.index_to_soup(url)
                else:
                    print url + 'page/' + str(i) + '/'
                    root = self.index_to_soup(url + 'page/' + str(i) + '/')  
            
                for li in root.findAll('h3', { 'class': 'post-title' }):
                    item = {}
                    item['title'] = "".join(str(item) for item in li.a.contents)
                    item['url'] = li.a['href']
                    item['description'] = item['title']
                    item['date'] = datetime.today()
                    print '>>> Item parsed: ', item
                    item_list.append(item)

            index.append((str(j*100), item_list))
        
        return index
        
    