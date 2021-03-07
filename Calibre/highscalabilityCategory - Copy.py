import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, datetime, timedelta

language = 'en'

site_url = 'http://highscalability.com'

title = 'highscalabilityCategory'

#categories = {'google':32,'facebook':28,'twitter':9,'amazon':26}
#categories = {'horizontal-scaling':7,'key-value-store':17,'map-reduce':16,'performance':37,'sharding':16,'database':44}
 categories = {'horizontal-scaling':7,'key-value-store':17,'map-reduce':16,'performance':37,'sharding':16,'database':44, 'bigdata':21, 'bigtable':9, 'mysql': 62, 'strategy': 325,
 'memcached': 29, 'google':32,'facebook':28,'twitter':9,'amazon':26, 'architecture':15,'cloud':49,'hadoop':19}

class HighScalability(BasicNewsRecipe):
    title = title

    language = language

    simultaneous_downloads = 10

    max_articles_per_feed = 1000
    
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
        
        for key, value in categories.iteritems():
            item_list = []
            url = site_url + '/blog/category/' + key
            for i in range(1, value/10+2):
                if(i == 1):
                    root = self.index_to_soup(url)
                else:
                    root = self.index_to_soup(url + '?currentPage=' + str(i))  
            
                ## content_id = root.find('a', { 'id': 'content' })
                for li in root.findAll('a', { 'class': 'journal-entry-navigation-current' }):
                    item = {}
                    item['title'] = "".join(str(item) for item in li.contents)
                    item['url'] = site_url + li['href']
                    item['description'] = item['title']
                    item['date'] = datetime.today()
                    print '>>> Item parsed: ', item
                    item_list.append(item)

            index.append((key, item_list))
        
        return index
        
    