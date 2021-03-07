import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, datetime, timedelta

language = 'en'

site_url = 'http://leetcode.com'


title = 'leetcode-article'

#categories = {'google':32,'facebook':28,'twitter':9,'amazon':26}
#categories = {'horizontal-scaling':7,'key-value-store':17,'map-reduce':16,'performance':37,'sharding':16,'database':44}
#categories = {'example':222}

class Article(BasicNewsRecipe):
    title = title

    language = language

    simultaneous_downloads = 2

    max_articles_per_feed = 1000
    
    no_stylesheets = True
    
    keep_only_tags = [ { 'class': 'container' } ]

    remove_tags_after = [
        { 'class': 'star-ratings' }
    ]

    remove_tags_before = [
        { 'class': 'container' }
    ]

    def parse_index(self):
        print '>>> Starting parse items'
        index = []
        
        item_list = []
        url = site_url
        for i in range(1, 8):
            
            cur = url + '/articles/?page=' + str(i)
            print '>>> Page:', cur
            root = self.index_to_soup(cur)
            container = root.find('div', { 'class': 'list-group' })
            if container is None:
                continue
            #print container
            ## content_id = root.find('a', { 'id': 'content' })
            for li in container.findChildren():
                #print '>>> Child:', li
                href = li.get('href', None)
                if href is None:
                    continue;
                item = {}
                item['title'] = href[10:-1]
                item['url'] = url + href
                item['description'] = item['title']
                item['date'] = datetime.today()
                print '>>> Item parsed: ', item
                item_list.append(item)

        index.append(("article", item_list))
        
        return index
        
    