import json
import os
import pathlib
import pickle
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
            row = [p.article.publication.id,
                   p.article.url,
                   p.article.userid,
                   p.article.publication.date,
                   p.article.raw.content,
                   p.article.noemoji.content,
                   p.article.maori.words,
                   p.maori_word_count,
                   p.total_word_count,
                   p.percentage_maori,
                   ]
            rows.append(row)
            bar.next()
        bar.finish()

        if format == 'csv':
            row_ind = 0
            headers = ['Key_Value', 'URL','User_ID', 'Date_Publication',
                       'Text_Raw', 'Text_Adapted','List_Words_Maori','Num_Words_Maori',
                       'Num_Words_Total', 'Percent_Maori']
            df = pd.DataFrame(columns=headers)

            bar = Bar('Writing to {} file'.format(format), max=db_paras.count())
            for row in rows:
                df.loc[row_ind] = row
                row_ind += 1
                bar.next()
            bar.finish()

            output_file = 'rmtcorpus.csv'
            print('Writing to file: {}'.format(output_file))
            df.to_json(output_file)

        elif format == 'json':
            json_rows = []
            for row in rows:
                json_row = dict(
                    Key_Value=row[0],
                    URL=row[1],
                    User_ID=row[2],
                    Date_Publication=row[3],
                    Text_Raw=row[4],
                    Text_Adpated=row[5],
                    List_Words_MAori=row[6],
                    Num_Words_Maori=row[7],
                    Num_Words_Total=row[8],
                    Percent_Maori=row[9],
                )
                json_rows.append(json_row)

            output_file = 'rmt.json'
            print('Writing to file: {}'.format(output_file))
            with open(output_file, 'w') as f:
                json.dump(json_rows, f)
