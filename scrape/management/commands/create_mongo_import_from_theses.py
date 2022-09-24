import datetime
import json
import os
import re

import pandas as pd
import regex
from django.core.management import BaseCommand
from progress.bar import Bar

from scrape.management.util.taumahi import Taumahi

current_dir = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.split(__file__)[1][0:-3]
dir_parts = current_dir.split(os.path.sep)
cache_dir = os.path.join(os.path.sep.join(dir_parts[0:dir_parts.index('management')]), 'cache', script_name)

transl_table = dict( [ (ord(x), ord(y)) for x,y in zip( u"‘’´“”–-",  u"'''\"\"--") ] )


def escape_text(text_raw):
    text_raw = text_raw.strip()
    text_raw = re.sub('\n+', ' ', text_raw)
    text_raw = regex.sub(r'[^\p{Latin} \p{posix_punct}]', u'', text_raw)
    text_raw = re.sub(' +', ' ', text_raw)
    text_raw = text_raw.translate(transl_table)
    return text_raw


class Command(BaseCommand):

    def __init__(self):
        super().__init__()
        self.taumahi = Taumahi()

    def add_arguments(self, parser):
            parser.add_argument('--excel-file', action='store', dest='excel_file', required=True)
            parser.add_argument('--theses-folder', action='store', dest='theses_folder', required=True)

    def process_row(self, row, txt_file, docs):
        """
        Notes	File Attachments	Link Attachments	Manual Tags	Automatic Tags

        """
        year = row['Publication Year']
        if year:
            date = datetime.date(year=int(year), month=1, day=1)
            date_iso_format = date.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            date_iso_format = None
        creator = row['Author']
        title = row['Title']
        url = row['Url']
        abstract_note = row['Abstract Note']
        publisher = row['Publisher']
        place = row['Place']
        languages = row['Language']
        copyright = row['Rights']
        type = row['Type']
        library_catalogue = row['Library Catalog']
        accepted = row['Extra']

        with open(txt_file, 'r', encoding='utf-8-sig') as f:
            text_raw = escape_text(f.read())

        maori_count, ambiguous_count, english_count, total_count, percentage = self.taumahi.tiki_ōrau(text_raw)

        doct_dict = dict(
            Source='Theses',
            Key=row['Key'],
            Creator=creator,
            Date_Publication={'$date': date_iso_format},
            Text_Raw=text_raw,
            URL=url,
            Title=title,
            Abstract_Note=escape_text(abstract_note),
            Publisher=publisher,
            Place=place,
            Languages=languages,
            Copyright=copyright,
            Thesis_Type=type,
            Library_Catalogue=library_catalogue,
            Accepted=accepted,
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
        excel_file = options['excel_file']
        theses_folder = options['theses_folder']

        if not os.path.isfile(excel_file):
            raise Exception('File {} does not exist'.format(excel_file))

        if not os.path.isdir(theses_folder):
            raise Exception('Folder {} does not exist'.format(theses_folder))

        df = pd.read_excel(excel_file)
        df = df.fillna('')
        docs = []
        bar = Bar('Processing file...', max=df.shape[0])
        for row_num, row in df.iterrows():
            # if row_num > 0:
            #     break
            key = row['Key']
            txt_file = os.path.join(theses_folder, '{}.txt'.format(key))

            if not os.path.isfile(txt_file):
                print('Text file {} does not exist'.format(txt_file))
                bar.next()
                continue

            self.process_row(row, txt_file, docs)
            bar.next()
        bar.finish()

        output_file = 'theses.json'
        print('Writing to file: {}'.format(output_file))
        with open(output_file, 'w', encoding='utf8') as f:
            json.dump(docs, f, ensure_ascii=False)
