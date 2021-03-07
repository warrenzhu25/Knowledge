import re
import datetime
from calibre.ebooks.BeautifulSoup import NavigableString

lintcode_url = ['http://articles.leetcode.com/']

class DaiziMini(BasicNewsRecipe):
    title = u'Leetcode.Article'
    auto_cleanup = True
    remove_tags_before = { 'class' : 'site-content' }
    remove_tags_after  = { 'class' : 'ratingblock ' }
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

        for url in lintcode_url:

            soup = self.index_to_soup(url)
            questions = soup.findAll('h1', { 'class' : "entry-title" })

            count = 0
            for question in questions:
                article = {}
                if question.a is None: continue
                title = question.a.contents
                article['title'] = "".join(str(item) for item in title)
                article['url'] = question.a["href"]
                article['date'] =  datetime.datetime.now()      
                article['description'] = article['title']

                articles_list.append(article)

                print article

            newlist = sorted(articles_list, key=lambda k: k['title']) 
            index.append(('Leetcode', newlist))

        return index 




