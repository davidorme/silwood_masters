## Turn on signed tables
db._common_fields.append(auth.signature)


db.define_table('wikimedia',
                Field('slug','string', unique=True, requires=IS_SLUG(check=True)),
                Field('mediafile','upload'))


db.define_table('wikicontent',
                Field('slug', 'string', unique=True, requires=IS_SLUG(check=True)),
                Field('wikicontent','text'),
                Field('toc_slug','string'))

