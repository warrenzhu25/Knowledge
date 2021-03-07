import re, urlparse, itertools
from calibre.ebooks.BeautifulSoup import NavigableString, Tag
from datetime import date, timedelta

language = 'en'

site_url = 'http://www.infoq.com/'

title_prefix = 'InfoQ'


# the sections to download
sections = ['articles' ]

# do NOT touch the code below unless you know what to do

def get_text(tag):
    text = ''
    for c in tag.contents:
        if isinstance(c, NavigableString):
            text = text + str(c)
        else:
            text = text + get_text(c)
            
    return text.strip()
    
def find_by_class(tag, name, cls):
    for c in tag.findAll(name):
        c_cls = c.get('class')
        if not c_cls: continue
        if cls not in c_cls: continue
        
        yield c

_section_texts = {}
_section_item_classes = {
    'news': ['news_type_block'],
    'articles': ['news_type1', 'news_type2'],
    'interviews': ['news_type_video']
}
        
class InfoQ(BasicNewsRecipe):
    title = title_prefix
    
    language = language
    
    no_stylesheets = True

    max_articles_per_feed = 1000
    
    keep_only_tags = [ { 'id': 'content' } ]
    
    remove_tags = [
        { 'id': 'noOfComments' },
        { 'class': 'share_this' },
        { 'class': 'article_page_right' }
    ]
    
    def get_items(self, section):
        print '>>> Retrieving items for section: ', section
    
        text_retrieved = False
        count = 0

        while True:
            print '>>> Loading items from ' + section + '/' + str(count)

            root = self.index_to_soup(site_url + section + '/' + str(count))
            content_div = root.find('div', { 'id': 'content' })
            
            if not text_retrieved:
                text_retrieved = True
                text = content_div.h2.string.strip()
                _section_texts[section] = text
                print '>>> Text for section "' + section + '": ' + text
            
            if count > 1000: break;

            for item_class in _section_item_classes[section]:
                for item_div in find_by_class(content_div, 'div', item_class):
                    item = {}
                    link = item_div.h2.a
                    item['title'] = link.string.strip()
                    item['url'] = urlparse.urljoin(site_url, link['href'])
                    item['description'] = get_text(item_div.p)

                    author_span = item_div.find('span', { 'class': 'author' })
                    date_text = str(author_span.contents[-1])
                    
                    print '>>> Item parsed: ', item
                    count = count + 1
                    yield item
                    
    
    def parse_index(self):
    
        index = []
        
        for sec in sections:
            item_list = []
        
            for item in self.get_items(sec):

                item_list.append(item)
            
            index.append((sec, item_list))

        return index
    
    def postprocess_html(self, soup, first_fetch):
        author_general = soup.find('span', { 'class': 'author_general' })
        author_general.em.extract()
    
        # the complete content
        full_div = None
    
        transcript_div = soup.find('div', { 'id': 'transcript' })
        if transcript_div: # that's an interview
            # get all <div class="qa" />
            qa_div_list = list(find_by_class(transcript_div, 'div', 'qa'))
            for qa_div in qa_div_list:
                qa_div.extract()
                
                # replace all <a class="question_link">...</a> with <strong>...</strong>
                question_link = qa_div.find('a', { 'class': 'question_link' })
                question_strong = Tag(soup, 'strong')
                question_strong.append(question_link.string)
                question_link.replaceWith(question_strong)
            
            full_div = find_by_class(soup.find('div', { 'id': 'content' }), 'div', 'presentation_full').next()
            
            # clean the <h1 />
            full_div.h1.span.extract()
            title_div = full_div.h1.div
            title_div.replaceWith(title_div.string)
            
            # clear the presentation area
            for div in full_div.findAll('div'):
                div.extract()
            
            # add qa list back to presentation area
            for qa_div in qa_div_list:
                full_div.append(qa_div)
        else:
            # text only without title
            text_div = find_by_class(soup, 'div', 'text_info').next()
            text_div.extract()
            
            for other in text_div.findAll('div'):
                other.extract()
            
            # full_div contains title
            full_div = soup.find('div', { 'id': 'content' })
            for other in full_div.findAll('div'):
                other.extract()
            
            full_div.append(text_div)

        full_div.extract()
        
        nav_div = soup.body.div
        nav_div.extract()
        
        # keep nav_div and full_div in <body /> only
        for other in soup.body:
            other.extract()
        
        soup.body.append(nav_div)
        soup.body.append(full_div)

        return soup
