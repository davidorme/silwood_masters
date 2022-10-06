import markdown # gluon provides MARKDOWN but lacks extensions
from wiki_functions import FoldingTOC

## --------------------------------------------------------------------------------
## Expose the wiki - see models/db.py for customisations and notes
## --------------------------------------------------------------------------------

def wiki():

    if not request.args:
        slug = 'index'
    else:
        slug = request.args[0]

    # Try and get the content page
    content_row = db(db.wikicontent.slug == slug).select().first()

    if content_row is not None:
        # Get the main page content
        content = XML(markdown.markdown(content_row.wikicontent, extensions=['extra']))

        # Get the ToC
        toc_row = db(db.wikicontent.slug == content_row.toc_slug).select().first()
        if toc_row is not None:
            toc = XML(markdown.markdown(toc_row.wikicontent, extensions=['extra']))
            ftoc = FoldingTOC()
            ftoc.feed(toc)
            toc = XML(ftoc.get_toc())
        else:
            toc = 'Unknown toc slug'

    else:
        content = 'Unknown wiki slug'
        toc = 'Unknown toc slug'

    return dict(toc=toc, content=content)


def wikimedia():
    """
    Simple controller to stream a file from the wikimedia table to a client
    """

    media = db(db.wikimedia.slug == request.args[0]).select().first()

    if media is not None:
        path = os.path.join(request.folder, 'uploads', media.mediafile)
        response.stream(path)


@auth.requires_membership('wiki_editor')
def manage_wikimedia():
    """
    SQLFORM.grid interface to the contents of the wikimedia table
    """

    db.wikimedia.id.readable = False
    grid = SQLFORM.grid(db.wikimedia, create=True, csv=False, details=False)

    return dict(grid=grid)


@auth.requires_membership('wiki_editor')
def manage_wikicontent():
    """
    SQLFORM.grid interface to the contents of the wikicontent table
    """

    db.wikicontent.slug.represent = lambda x, row: A(x, _href=URL('wiki','wiki', args=[x]))
    db.wikicontent.id.readable = False
    grid = SQLFORM.grid(db.wikicontent, create=True, csv=False, details=False)

    return dict(grid=grid)
