import re
import datetime
from calibre.ebooks.BeautifulSoup import NavigableString

site_url = 'http://www.ituring.com.cn'
index_url = '/minibook/787'


class DaiziMini(BasicNewsRecipe):
    title = u'待字闺中-编程'
    auto_cleanup = True
    remove_tags_before = { 'class' : 'MagazineStyle' }
    remove_tags_after  = { 'class' : 'MagazineStyle' }
    no_stylesheets = True
    timeout = 1000.0

    def parse_index(self):
        #print self
        index = []
        articles_list = []

        soup = self.index_to_soup(site_url + index_url)
        questions = soup.findAll('a', { 'class' : "question-hyperlink" })

        for question in questions:
            article = {}
            article['title'] = "".join(str(item) for item in question.contents)
            article['url'] = site_url + question["href"]
            article['date'] =  datetime.datetime.now()      
            article['description'] = article['title']

            articles_list.append(article)

        index.append(('Default', articles_list))

        return index 




