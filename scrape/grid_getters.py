__all__ = ['bulk_get_paragraph_info']


def bulk_get_paragraph_info(paragraphs, extras):
    ids = []
    rows = []

    vl = paragraphs\
        .order_by('article__publication__id', 'article__publication__published_date', 'article__publication__volume')\
        .values_list('id', 'article__publication__newspaper__name', 'article__publication__published_date',
                     'article__publication__volume',
                     'article__publication__number', 'article__title', 'article__url', 'content', 'percentage_maori')

    for id, npp_name, date, volume, number, article_title, url, content, percentage_maori in vl:
        ids.append(id)
        rows.append({
            'id': id, 'publication': npp_name, 'published_date': date, 'volume': volume, 'article_title': article_title,
            'url': url, 'content': content, 'percentage_maori': percentage_maori
        })

    return ids, rows
