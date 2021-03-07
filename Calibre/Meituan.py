import re
import datetime
from calibre.ebooks.BeautifulSoup import NavigableString

site_url = 'http://tech.meituan.com'
index_url = '/archives'


class DaiziMini(BasicNewsRecipe):
    title = u'美团'
    auto_cleanup = True
    remove_tags_before = { 'class' : 'MagazineStyle' }
    remove_tags_after  = { 'class' : 'tags' }
    no_stylesheets = True
    timeout = 1000.0

    def parse_index(self):
        #print self
        index = []
        articles_list = []

        soup = self.index_to_soup(site_url + index_url)
        questions = soup.findAll('a', { 'class' : "post-item__title" })

        for question in questions:
            article = {}
            article['title'] = "".join(str(item) for item in question.contents)
            article['url'] = site_url + question["href"]
            article['date'] =  datetime.datetime.now()      
            article['description'] = article['title']

            articles_list.append(article)

        index.append(('Default', articles_list))

        return index 




