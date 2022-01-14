import json
import os
import datetime


from django.core.management import BaseCommand
from progress.bar import Bar

import pandas as pd

from scrape.management.util.json_serialiser import serialise_array
from scrape.management.util.taumahi import Taumahi

current_dir = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.split(__file__)[1][0:-3]
dir_parts = current_dir.split(os.path.sep)
cache_dir = os.path.join(os.path.sep.join(dir_parts[0:dir_parts.index('management')]), 'cache', script_name)


class Command(BaseCommand):

    def __init__(self):
        super().__init__()
        self.taumahi = Taumahi()

    def add_arguments(self, parser):
            parser.add_argument('--file', action='store', dest='file_loc', required=True)

    def process_row(self, doc, docs):
        text_raw = doc['content_with_emojis']
        # published_date = datetime.datetime.fromisoformat(doc['date'])
        maori_count, ambiguous_count, english_count, total_count, percentage = self.taumahi.tiki_ōrau(text_raw)

        doct_dict = dict(
            Source='RmtCorpus',
            Date_Publication={'$date': doc['date']},
            Text_Raw=text_raw,
            URL=doc['url'],
            Percent_Maori_Original=doc['percent_maori'] * 100,
            Num_Words_Maori_Original=doc['num_maori_words'],
            Num_Words_Total_Original=doc['total_words'],
            Percent_Maori=percentage,
            Num_Words_Maori=maori_count,
            Num_Words_Ambi=ambiguous_count,
            Num_Words_Other=english_count,
            Num_Words_Total=total_count
        )

        docs.append(doct_dict)

    def handle(self, *args, **options):
        file_loc = options['file_loc']
        if not os.path.isfile(file_loc):
            raise FileNotFoundError('File {} not found'.format(file_loc))

        df = pd.read_csv(file_loc)
        docs = []
        bar = Bar('Processing', max=df.shape[0])

        for i, row in df.iterrows():
            self.process_row(row, docs)
            bar.next()
        bar.finish()

        output_file = 'rmtcorpus.json'
        print('Writing to file: {}'.format(output_file))
        with open(output_file, 'w') as f:
            json.dump(docs, f)


