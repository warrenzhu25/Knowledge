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

    max_articles_per_feed = 1000
    
    remove_tags = [
        { 'id': 'python' },
        { 'id': 'cpp' },
    ]

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

            articles_list.append(article)

            print article

        newlist = sorted(articles_list, key=lambda k: k['title']) 
        index.append(('Leetcode', newlist))

        return index 




