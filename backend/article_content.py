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

_ATTR_VERBS=r'(?:dedi|söyledi|ifade etti|ifadelerini kullandı|kaydetti|belirtti|vurguladı|konuştu|açıkladı|değerlendirdi|şunları söyledi|diye konuştu)'

def attributed_quotes(text,name):
    esc=re.escape(name)
    # Each pattern keeps the speaker's name tightly bound to the quote (no sentence
    # boundary between them), covering the common Turkish attribution orders.
    patterns=[
        # Name[,: / verb] ... "quote"  — name introduces the quote in the same clause
        re.compile(esc+r'[^"“.!?]{0,60}?[“"]([^”"]{20,1600})[”"]',re.I),
        # "quote" ... verb ... Name    — quote first, attributed afterwards
        re.compile(r'[“"]([^”"]{20,1600})[”"][^"“]{0,50}?'+_ATTR_VERBS+r'[^"“]{0,25}?'+esc,re.I),
        # "quote" diyen Name
        re.compile(r'[“"]([^”"]{20,1600})[”"][^"“]{0,25}?diyen\s+'+esc,re.I),
    ]
    seen=set();result=[]
    for pattern in patterns:
        for match in pattern.finditer(text):
            quote=' '.join(match.group(1).split())
            if len(quote)>420:quote=re.split(r'(?<=[.!?])\s+',quote)[0]
            key=quote.casefold()
            if 20<=len(quote)<=420 and key not in seen:
                seen.add(key);result.append((quote,match.group(0)))
    return result
