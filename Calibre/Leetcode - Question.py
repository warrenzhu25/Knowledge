import re
import datetime
from calibre.ebooks.BeautifulSoup import NavigableString

lintcode_url = 'http://www.lintcode.com/en/problem/'
jiuzhang_url = 'http://www.jiuzhang.com'

class DaiziMini(BasicNewsRecipe):
    title = u'Leetcode.2'
    auto_cleanup = True
    remove_tags_before = { 'class' : 'pi-tabs-navigation pi-responsive-sm' }
    remove_tags_after  = { 'class' : 'pi-section-w pi-section-dark pi-border-top-light pi-border-bottom-strong-base' }
    no_stylesheets = True
    timeout = 1000.0

    def parse_index(self):
        #print self
        index = []
        articles_list = []

        soup = self.index_to_soup(lintcode_url)
        questions = soup.findAll('a', { 'class' : "list-group-item" })

        count = 0
        for question in questions:
            article = {}
            title = question.find('span', { 'class' : "difficulty_with_title hide" }).contents
            article['title'] = "".join(str(item) for item in title)
            article['url'] = jiuzhang_url + question["href"].replace("problem", "solutions")
            article['date'] =  datetime.datetime.now()      
            article['description'] = article['title']

            if count > 99: articles_list.append(article)
            count = count + 1
            print article

        index.append(('Default', articles_list))

        return index 




