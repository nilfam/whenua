import json
import os
import pathlib
import pickle
import re

from bs4 import BeautifulSoup
from django.core.management import BaseCommand
from progress.bar import Bar

from scrape.management.util.taumahi import Taumahi
import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.split(__file__)[1][0:-3]
dir_parts = current_dir.split(os.path.sep)
cache_dir = os.path.join(os.path.sep.join(dir_parts[0:dir_parts.index('management')]), 'cache', script_name)
doc_dir = os.path.join(cache_dir, 'doc')
json_dir = os.path.join(cache_dir, 'json')
pathlib.Path(doc_dir).mkdir(parents=True, exist_ok=True)
pathlib.Path(json_dir).mkdir(parents=True, exist_ok=True)

possible_format = ['%Y-%m-%d %H:%M', '%Y']

class Command(BaseCommand):

    def __init__(self):
        super().__init__()
        self.taumahi = Taumahi()

    def add_arguments(self, parser):
            parser.add_argument('--file', action='store', dest='file_loc', required=True)

    def process_doc(self, doc):
        docs = []
        soup = BeautifulSoup(doc, 'html5lib')
        doc = soup.find('doc')
        date = doc.get('crawl_date', '')
        i = 0
        success = False
        while i < len(possible_format) and not success:
            try:
                fmt = possible_format[i]
                date = datetime.datetime.strptime(date, fmt)
                success = True
            except ValueError:
                i += 1

        if not success:
            print('Invalid format {}'.format(date))

        title = doc.get('title', '')
        url = doc.attrs.get('url', '')

        for i, p in enumerate(doc.select('p'), 1):
            text = p.text.strip()
            text = re.sub('\n+', ' ', text)

            maori_count, ambiguous_count, english_count, total_count, percentage = self.taumahi.tiki_ōrau(text)

            doct_dict = dict(
                Source='Mitenten',
                Date_Publication={'$date': date.strftime('%Y-%m-%dT%H:%M:%SZ')},
                Article_Title=title,
                Paragraph_Number=i,
                Text_Raw=text,
                URL=url,
                Percent_Maori=percentage,
                Num_Words_Maori=maori_count,
                Num_Words_Ambi=ambiguous_count,
                Num_Words_Other=english_count,
                Num_Words_Total=total_count
            )
            docs.append(doct_dict)
        return docs

    def split_doc(self, file_loc):
        with open(file_loc, 'r') as f:
            content = f.read()

        doc_ind = 1
        bar = Bar('Splitting doc', max=len(content) / 1000)
        while True:
            start = content.find('<doc')
            doc_ind += 1
            if start == -1:
                break
            end = content.find('doc>')
            doc = content[start:end + 4]
            content = content[end + 4:]

            doc_file_name = os.path.join(doc_dir, '{}.doc'.format(doc_ind))
            with open(doc_file_name, 'w') as f:
                f.write(doc)
            bar.next(len(doc) / 1000)
        bar.finish()

    def export_jsons_from_cache(self):
        cache_file = os.path.join(cache_dir, 'progress.pkl')
        if not os.path.isfile(cache_file):
            return

        with open(cache_file, 'rb') as f:
            progress_cache = pickle.load(f)
            jsons = progress_cache['docs']

            bar = Bar('Saving json from cache...', max=len(jsons))
            for json_ind, doc in enumerate(jsons, 1):
                json_file_name = os.path.join(json_dir, '{}.json'.format(json_ind))
                with open(json_file_name, 'w') as f:
                    json_content = json.dumps(doc)
                    f.write(json_content)
                bar.next()
            bar.finish()

    def merge_jsons(self, output_file):
        json_files = os.listdir(json_dir)
        bar = Bar('Writing to file: {}'.format(output_file), max=len(json_files))
        contents = []

        for i, json_file in enumerate(json_files, 1):
            if not json_file.endswith('.json'):
                continue
            json_file_path = os.path.join(json_dir, json_file)
            with open(json_file_path, 'r') as jf:
                content = jf.read()
                contents.append(content)
                bar.next()
        bar.finish()

        with open(output_file, 'w') as f:
            contents = '[' + ','.join(contents) + ']'
            contents = contents.replace('}{', '},{').replace('},,{', '},{')
            f.write(contents)

    def handle(self, *args, **options):
        file_loc = options['file_loc']
        if not os.path.isfile(file_loc):
            raise FileNotFoundError('File {} not found'.format(file_loc))

        # self.split_doc(file_loc)

        # return
        # self.export_jsons_from_cache()
        # return

        doc_files = os.listdir(doc_dir)

        doc_inds_to_process = []

        for doc_file in doc_files:
            if doc_file.endswith('.doc'):
                doc_ind = doc_file[:-4]
                json_file = os.path.join(json_dir, '{}.json'.format(doc_ind))
                if not os.path.isfile(json_file):
                    doc_inds_to_process.append(doc_ind)

        bar = Bar('Processing', max=len(doc_inds_to_process))
        for doc_ind in doc_inds_to_process:
            doc_file = os.path.join(doc_dir, '{}.doc'.format(doc_ind))
            json_file = os.path.join(json_dir, '{}.json'.format(doc_ind))
            with open(doc_file, 'r') as f:
                json_dicts = self.process_doc(f.read())
                if len(json_dicts) == 0:
                    continue
            with open(json_file, 'w') as f:
                for ind, json_dict in enumerate(json_dicts):
                    json_content = json.dumps(json_dict)
                    f.write(json_content)
                    if ind < len(json_dict) - 1:
                        f.write(',')

            bar.next()
        bar.finish()

        output_file = 'mitenten20.json'
        self.merge_jsons(output_file)
