from html.parser import HTMLParser


## --------------------------------------------------------------------------------
## WIKI FUNCTIONS
## --------------------------------------------------------------------------------

class FoldingTOC(HTMLParser):
    """
    This parser scans html and inserts ids, classes and spans to turn
    <ul> or <ol> into a click to expand table of contents tree. The
    layout_wiki.html file contains JS and CSS to make it work.
    """
    
    def __init__(self):
        super().__init__()
        self.content = []
        self.depth = 0
        self.last_li_index = 0

    def handle_starttag(self, tag, attrs): 

        if tag in ['ul', 'ol']:
            if self.depth == 0:
                self.content.append(f'<{tag.upper()} id="root">')
            else:
                self.content.append(f'<{tag.upper()} class="nested">')
                self.content[self.last_li_index] = '<LI><SPAN class="caret"></SPAN>'
            self.depth += 1
        
        elif tag == 'li':
            self.content.append('<LI><SPAN class="end"></SPAN>')
            self.last_li_index = len(self.content) - 1
        
        else:
            self.content.append(self.get_starttag_text())
        
    def handle_data(self, data): 
        self.content.append(data)
    
    def handle_endtag(self, tag):
        if tag in ['ul', 'ol']:
            self.depth -= 1
        
        self.content.append(f'</{tag.upper()}>')
    
    def get_toc(self):
        
        return ''.join(self.content)