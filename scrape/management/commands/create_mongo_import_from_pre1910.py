import json
import os
import re

from bs4 import BeautifulSoup
from django.core.management import BaseCommand
from progress.bar import Bar

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
            parser.add_argument('--dir', action='store', dest='directory', required=True)

    def process_file(self, category, article, file, docs):
        with open(file, 'r', encoding='utf-16') as f:
            content = f.read()
        soup = BeautifulSoup(content, 'html5lib')
        texts = []

        for i, p in enumerate(soup.select('p'), 1):
            text = p.text.strip()
            text = re.sub('\n+', ' ', text)
            texts.append(text)

        text_raw = '. '.join(texts)
        text_raw = re.sub('\.+', ' ', text_raw)

        maori_count, ambiguous_count, english_count, total_count, percentage = self.taumahi.tiki_ōrau(text_raw)

        doct_dict = dict(
            Source='Pre1910',
            Category=category,
            Article_Title=article,
            Text_Raw=text_raw,
            Percent_Maori=percentage,
            Num_Words_Maori=maori_count,
            Num_Words_Ambi=ambiguous_count,
            Num_Words_Other=english_count,
            Num_Words_Total=total_count
        )
        docs.append(doct_dict)

    def handle(self, *args, **options):
        directory = options['directory']
        if not os.path.isdir(directory):
            raise FileNotFoundError('Directory {} not found'.format(directory))

        files_count = 0
        subdirs = os.listdir(directory)
        for subdir in subdirs:
            subdir_path = os.path.join(directory, subdir)
            if os.path.isdir(subdir_path):
                files = os.listdir(subdir_path)
                for file in files:
                    if file.endswith('.txt'):
                        files_count += 1

        docs = []
        i = 0
        bar = Bar('Processing files...', max=files_count)
        for subdir in subdirs:
            subdir_path = os.path.join(directory, subdir)
            if os.path.isdir(subdir_path):
                files = os.listdir(subdir_path)
                for file in files:
                    if file.endswith('.txt'):
                        filename = file[:-4]
                        file_path = os.path.join(subdir_path, file)
                        self.process_file(subdir, filename, file_path, docs)
                        bar.next()
                        # i += 1
                        #
                        # if i > 10:
                        #     break
            # if i > 10:
            #     break
        bar.finish()

        output_file = 'pre1910.json'
        print('Writing to file: {}'.format(output_file))
        with open(output_file, 'w') as f:
            json.dump(docs, f)

