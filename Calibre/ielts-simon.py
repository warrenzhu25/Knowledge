import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, datetime, timedelta

language = 'en'

site_url = 'http://ielts-simon.com/ielts-help-and-english-pr/ielts-speaking/'

title = 'ielts-simon'

#categories = {'google':32,'facebook':28,'twitter':9,'amazon':26}
#categories = {'horizontal-scaling':7,'key-value-store':17,'map-reduce':16,'performance':37,'sharding':16,'database':44}
#categories = {'example':222}

class HighScalability(BasicNewsRecipe):
    title = title

    language = language

    simultaneous_downloads = 10

    max_articles_per_feed = 1000
    
    no_stylesheets = True
    
    keep_only_tags = [ { 'class': 'entry-body' } ]

    remove_tags_after = [
        { 'class': 'entry-footer' }
    ]

    simultaneous_downloads = 10

    def parse_index(self):
        print '>>> Starting parse items'
        index = []
        
        item_list = []
        url = site_url
        for i in range(1, 11):
            print '>>> Page:', i
            if(i == 1):
                root = self.index_to_soup(url)
            else:
                root = self.index_to_soup(url + '/page/' + str(i))  
        
            ## content_id = root.find('a', { 'id': 'content' })
            for li in root.findAll('h3', { 'class': 'entry-header' }):
                item = {}
                item['title'] = "".join(str(item) for item in li.a.contents)
                item['url'] = li.a['href']
                item['description'] = item['title']
                item['date'] = datetime.today()
                print '>>> Item parsed: ', item
                item_list.append(item)

        item_list.reverse()
        index.append(("ielts", item_list))
        
        return index
        
    