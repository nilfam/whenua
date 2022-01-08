__all__ = ['tables', 'actions']

tables = \
    {
        "pages-info": {
            "class": "scrape.Paragraph",
            "getter": "scrape.bulk_get_paragraph_info",
            "columns": [
                {
                    "name": "Publication",
                    "slug": "publication",
                    "type": "SHORT_TEXT",
                    "is_attribute": False
                },
                {
                    "name": "Published date",
                    "slug": "published_date",
                    "type": "DATE",
                    "is_attribute": False
                },
                {
                    "name": "Volume",
                    "slug": "volume",
                    "type": "INTEGER",
                    "is_attribute": False
                },
                {
                    "name": "Article title",
                    "slug": "article_title",
                    "type": "SHORT_TEXT",
                    "is_attribute": False
                },
                {
                    "name": "% Maori",
                    "slug": "percentage_maori",
                    "type": "FLOAT",
                    "is_attribute": True,
                },
                {
                    "name": "Content",
                    "slug": "content",
                    "type": "LONG_TEXT",
                    "is_attribute": True,
                    "editable": True,
                },
                {
                    "name": "URL",
                    "slug": "url",
                    "type": "SHORT_TEXT",
                    "is_attribute": True
                }
            ]
        },
    }

actions = \
    {
        "reorder-columns": {
            "name": "Arrange row",
            "type": "INTEGER",
            "target": "VALUES_GRID"
        },
        "set-column-width": {
            "name": "Set Column Width",
            "type": "FLOAT",
            "target": "VALUES_GRID"
        }
    }
