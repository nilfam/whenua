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

    def process_row(self, row, docs):
        text_raw = row['text']
        text_raw = text_raw.replace('"', '')
        url = row['url']
        date_str = row['date2']
        creator = row['speaker']
        num_maori_original = row['reo']
        num_ambi_original = row['ambiguous']
        num_other_original = row['other']
        percent_original = row['percent']
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        date_iso_format = date.strftime('%Y-%m-%dT%H:%M:%SZ')
        maori_count, ambiguous_count, english_count, total_count, percentage = self.taumahi.tiki_ōrau(text_raw)

        doct_dict = dict(
            Source='Hansard',
            Creator=creator,
            Date_Publication={'$date': date_iso_format},
            Text_Raw=text_raw,
            URL=url,
            Percent_Maori_Original=percent_original,
            Num_Words_Maori_Original=num_maori_original,
            Num_Words_Other_Original=num_other_original,
            Num_Words_Ambi_Original=num_ambi_original,
            Percent_Maori=percentage,
            Num_Words_Maori=maori_count,
            Num_Words_Ambi=ambiguous_count,
            Num_Words_Other=english_count,
            Num_Words_Total=total_count
        )

        if pd.isna(creator):
            del doct_dict['Creator']

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

        output_file = 'hansard.json'
        print('Writing to file: {}'.format(output_file))
        with open(output_file, 'w') as f:
            json.dump(docs, f)


