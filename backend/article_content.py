"""Extract attributable quotes from article bodies, excluding index cards."""
from html.parser import HTMLParser
import json
import re

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.stack=[]; self.parts=[]; self.date=''; self.structured=[]; self.script=None

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='meta':
            key=(attrs.get('property') or attrs.get('name') or '').lower()
            if key in {'article:published_time','datepublished','pubdate'}:self.date=attrs.get('content','')
        if tag=='script' and attrs.get('type')=='application/ld+json':self.script=[]
        marker=' '.join([attrs.get('itemprop',''),attrs.get('class',''),attrs.get('id','')]).lower()
        body=bool(re.search(r'articlebody|article-body|article__body|news-content|news-detail-content|entry-content',marker))
        parent=self.stack[-1] if self.stack else ('',False,False)
        blocked=parent[2] or tag in {'nav','aside','footer','script','style','figure'} or bool(re.search(r'related|recommend|breadcrumb',marker))
        if tag not in {'meta','img','br','hr','input','link','source','wbr'}:self.stack.append((tag,parent[1] or body,blocked))
        if tag in {'p','blockquote','div','h2'}:self.parts.append('\n')

    def handle_endtag(self,tag):
        if tag=='script' and self.script is not None:
            try:self.structured.append(json.loads(''.join(self.script)))
            except ValueError:pass
            self.script=None
        for index in range(len(self.stack)-1,-1,-1):
            if self.stack[index][0]==tag:
                del self.stack[index:];break
        if tag in {'p','blockquote','div'}:self.parts.append('\n')

    def handle_data(self,data):
        if self.script is not None:self.script.append(data)
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:self.parts.append(data)

def article_content(doc):
    parser=ArticleParser();parser.feed(doc)
    def nodes(value):
        if isinstance(value,dict):
            yield value
            for v in value.values():yield from nodes(v)
        elif isinstance(value,list):
            for v in value:yield from nodes(v)
    for node in nodes(parser.structured):
        if node.get('articleBody') and node.get('datePublished'):
            return str(node['articleBody']),str(node['datePublished'])
    return '\n'.join(' '.join(x.split()) for x in ''.join(parser.parts).splitlines() if x.strip()),parser.date

def attributed_quotes(text,name):
    pattern=re.compile(re.escape(name)+r'\s*(?:[:,：]|(?:şunları söyledi|dedi|ifadelerini kullandı)\s*:)\s*[“"]([^”"]{20,1600})[”"]',re.I)
    result=[]
    for match in pattern.finditer(text):
        quote=' '.join(match.group(1).split())
        if len(quote)>420:quote=re.split(r'(?<=[.!?])\s+',quote)[0]
        if 20<=len(quote)<=420:result.append((quote,match.group(0)))
    return result
