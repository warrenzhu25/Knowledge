import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, datetime, timedelta

language = 'en'

site_url = 'https://zxi.mytechroad.com'

title = 'LeetcodeHua'

#categories = {'google':32,'facebook':28,'twitter':9,'amazon':26}
#categories = {'horizontal-scaling':7,'key-value-store':17,'map-reduce':16,'performance':37,'sharding':16,'database':44}
# categories = {'example':222}

class HighScalability(BasicNewsRecipe):
    title = title

    language = language

    simultaneous_downloads = 10

    max_articles_per_feed = 1000
    
    no_stylesheets = True
    
    keep_only_tags = [ { 'class': 'main' } ]

    remove_tags_after = [
        { 'id': 'pryc-wp-acctp-bottom' }
    ]

    def parse_index(self):
        print '>>> Starting parse items'
        count = 0
        index = []
        
        item_list = []
        
        for i in range(1, 2):
            url = site_url + '/blog/page/' + i
            root = self.index_to_soup(url)
        
            for div in root.findAll('div', { 'class': 'post-header' }):
                li = div.a
                item = {}
                item['title'] = "".join(str(item) for item in li.contents)
                item['url'] = site_url + li['href']
                item['description'] = item['title']
                item['date'] = datetime.today()
                print '>>> Item parsed: ', item
                item_list.append(item)

        index.append((key, item_list))
        
        return index
        
    