import datetime
import json
import os

import pandas as pd
from django.conf import settings
from django.core.management import BaseCommand
from progress.bar import Bar

from scrape.models import Paragraph

current_dir = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.split(__file__)[1][0:-3]
dir_parts = current_dir.split(os.path.sep)
cache_dir = os.path.join(os.path.sep.join(dir_parts[0:dir_parts.index('management')]), 'cache', script_name)


class Command(BaseCommand):

    def __init__(self):
        super().__init__()
        self.export_file_name = os.path.join(cache_dir, 'export.tsv')

    def add_arguments(self, parser):
            parser.add_argument('--format', action='store', dest='format', default='csv')
                
    def handle(self, *args, **options):
        format = options['format']
        rows = []
        # db_paras = Paragraph.objects.filter(article__publication_id=1)
        db_paras = Paragraph.objects.all()
        bar = Bar('Reading from database', max=db_paras.count())
        paras = db_paras \
            .order_by('article__publication__id', 'article__publication__published_date',
                      'article__publication__volume', 'article__index', 'index')

        for p in paras:
            row = [p.article.publication.newspaper.name,
                   p.article.publication.published_date.strftime(settings.DATE_INPUT_FORMAT),
                   p.article.publication.volume,
                   p.article.publication.number,
                   p.article.title,
                   p.article.index,
                   p.index,
                   p.content,
                   p.article.url,
                   p.percentage_maori,
                   p.maori_word_count,
                   p.ambiguous_word_count,
                   p.other_word_count,
                   p.total_word_count]
            rows.append(row)
            bar.next()
        bar.finish()

        if format == 'csv':
            row_ind = 0
            headers = ['Newspaper', 'Date_Publication', 'Volume', 'Number', 'Article_Title', 'Article_Number', 'Paragraph_Number',
                       'Text_Raw', 'URL', 'Percent_Maori', 'Num_Words_Maori', 'Num_Words_Ambi',
                       'Num_Words_Other',
                       'Num_Words_Total']
            df = pd.DataFrame(columns=headers)

            bar = Bar('Writing to {} file'.format(format), max=db_paras.count())
            for row in rows:
                df.loc[row_ind] = row
                row_ind += 1
                bar.next()
            bar.finish()

            output_file = 'nzdl.csv'
            print('Writing to file: {}'.format(output_file))
            df.to_json(output_file)

        elif format == 'json':
            json_rows = []
            for row in rows:
                date = datetime.datetime.strptime(row[1], settings.DATE_INPUT_FORMAT)
                json_row = dict(
                    Source='NZDL',
                    Newspaper=row[0],
                    Date_Publication={'$date': date.strftime('%Y-%m-%dT%H:%M:%SZ')},
                    Volume=row[2],
                    Number=row[3],
                    Article_Title=row[4],
                    Article_Number=row[5],
                    Paragraph_Number=row[6],
                    Text_Raw=row[7],
                    URL=row[8],
                    Percent_Maori=row[9],
                    Num_Words_Maori=row[10],
                    Num_Words_Ambi=row[11],
                    Num_Words_Other=row[12],
                    Num_Words_Total=row[13]
                )
                json_rows.append(json_row)

            output_file = 'nzdl.json'
            print('Writing to file: {}'.format(output_file))
            with open (output_file, 'w') as f:
                json.dump(json_rows, f)
