import datetime
import os
import pathlib
import pickle
import re
import zipfile

from bs4 import BeautifulSoup as bs
from django.core.management import BaseCommand

from scrape.management.util.browser_wrapper import BrowserWrapper
from scrape.management.util.taumahi import tiki_ōrau
from scrape.models import Newspaper, Publication, Page

current_dir = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.split(__file__)[1][0:-3]
dir_parts = current_dir.split(os.path.sep)
cache_dir = os.path.join(os.path.sep.join(dir_parts[0:dir_parts.index('management')]), 'cache', script_name)
cache_html_dir = os.path.join(cache_dir, 'html')
cache_zip_dir = os.path.join(cache_dir, 'zip')

pathlib.Path(cache_dir).mkdir(parents=True, exist_ok=True)
pathlib.Path(cache_html_dir).mkdir(parents=True, exist_ok=True)
pathlib.Path(cache_zip_dir).mkdir(parents=True, exist_ok=True)


pae_tukutuku = 'http://www.nzdl.org'
pae_tukutuku_haurua = '{}{}'.format(pae_tukutuku, '/gsdlmod?gg=text&e=p-00000-00---off-0niupepa--00-0----0-10-0---0---0direct-10---4-------0-1l--11-en-50---20-about---00-0-1-00-0-0-11-1-0utfZz-8-00-0-0-11-10-0utfZz-8-00&a=d&c=niupepa&cl=CL1')


NEWSPAPER_NAME_MATCHER = re.compile(r'(.*?) \d\d\d\d.*')
NEWSPAPER_VOL_MATCHER = re.compile(r'(.*?) \d\d\d\d.*?Volume (\d+).*')
NEWSPAPER_NO_MATCHER = re.compile(r'(.*?) \d\d\d\d.*?No. (\d+).*')


class AutoSaveCache:
    def __init__(self, filename: str, save_freq: int):
        self.filename = filename
        self.filename_bak = filename + '.bak'
        self.save_freq = save_freq

        if os.path.isfile(self.filename):
            with open(self.filename, 'rb') as f:
                self.db_storage = pickle.load(f)
        else:
            self.db_storage = {}

        self.item_count = len(self.db_storage)

    def get_index(self, url):
        index = self.db_storage.get(url, None)
        if index is None:
            return self.item_count + 1, True
        return index, False

    def __setitem__(self, key, value):
        if key in self.db_storage:
            raise Exception('Key {} already exists'.format(key))
        self.item_count += 1
        self.db_storage[key] = self.item_count

        if self.item_count % self.save_freq == 0:
            with open(self.filename_bak, 'wb') as f:
                pickle.dump(self.db_storage, f)

            os.rename(self.filename_bak, self.filename)
            print('Saved cache')

    def save(self):
        with open(self.filename_bak, 'wb') as f:
            pickle.dump(self.db_storage, f)

        os.rename(self.filename_bak, self.filename)
        print('Saved final cache')


class UrlQuerier:
    def __init__(self, cache, browser_wrapper):
        self.cache = cache
        self.browser_wrapper = browser_wrapper

    def _query(self, url, cache_file_path_zip):
        query_finished = False
        response = None
        while not query_finished:
            try:
                response = self.browser_wrapper.make_query_retrial_if_fail(url)
                query_finished = True
            except Exception as e:
                self.browser_wrapper.reload()

        zf = zipfile.ZipFile(cache_file_path_zip, mode='w', compression=zipfile.ZIP_DEFLATED)
        try:
            zf.writestr('content.html', response)
        finally:
            zf.close()
        return response

    def _load(self, cache_file_path_zip):
        zf = zipfile.ZipFile(cache_file_path_zip, 'r')
        response = zf.read('content.html').decode('utf-8')
        return response

    def query_or_load(self, url):
        # if replace:
        #     url = url.replace('&c=niupepa', '').replace('&cl=CL1.1', '&cl=CL2.1').replace('/library', '/library.cgi').replace('/library.cgi.cgi', '/library.cgi')
        cache_index, is_new = self.cache.get_index(url)
        cache_file_path_zip = os.path.join(cache_zip_dir, '{}.zip'.format(cache_index))

        if is_new:
            content = self._query(url, cache_file_path_zip)
        else:
            content = self._load(cache_file_path_zip)

        if is_new:
            self.cache[url] = cache_index

        return content


def clean_whitespace(paragraph):
    return re.sub(r'\s+', ' ', paragraph).strip()


# Punctuation that will be searched for, and stripped respectively. The former indicates the end of a paragraph if followed by a new line character.
tohutuhi = ".!?"
tohukī = "‘’\'\") "


class Perehitanga:
    # This class takes a row from the index file it reads and attributes it to a class object for readability
    def __init__(self, rārangi):
        self.niupepa = rārangi[0]
        if len(rārangi) == 3:
            self.perehitanga = rārangi[1]
            self.taukaea = rārangi[2]
        else:
            self.perehitanga = ''
            self.taukaea = rārangi[1]

        self.mātāmuri = False
        self.published_date = None


class Rārangi:
    # This information sets up all the information that will be written to the text csv file, apart from the time of retrieval, in a class object, to prevent the need for tuples, and for improved readability.
    # The input is a Perehitanga class object, and the url of the page the text is extracted from
    # The māori, rangirua, pākehā and tapeke attributes are updated per paragraph in the rārangi_kaituhituhi function.
    def __init__(self, url_querier: UrlQuerier, niupepa, taukaea):
        self.niupepa = niupepa.niupepa
        self.perehitanga = niupepa.perehitanga
        self.published_date = niupepa.published_date
        self.taukaea = taukaea
        # Extracts the soup of the issue's first page
        self.hupa = bs(url_querier.query_or_load(self.taukaea), 'html.parser')
        # Extracts the page number from the soup
        self.tau = self.hupa.find('b').text.split("page  ")[1]
        self.māori = 0
        self.rangirua = 0
        self.pākehā = 0
        self.tapeke = 0
        self.ōrau = 0.00
        # Extracts the text from the page's soup
        self.kupu = unu_kupu_tōkau(self.hupa, self.tau)
        self.urutau = ""
        self.mātāmuri_rārangi = niupepa.mātāmuri


class Tīmata_kōwae:
    # Sets up the 'left over paragraph' from the previous page in a class object for readability
    # The input is a Rārangi class object.
    def __init__(self, tāuru):
        self.tau = tāuru.tau
        self.kupu = tāuru.kupu
        self.taukaea = tāuru.taukaea


def kupu_moroki(tāuru, tīmata_kōwae):

    # It strips the text of any unnecessary trailing characters that could follow the end of the sentence, such as quotation marks
    mahuru_kupu = tāuru.kupu.strip(tohukī)
    # If there is anything left after these characters have been stripped (so as not to cause an error)
    if mahuru_kupu:
        # If the last character of the string is an acceptable "end of paragraph" character, and there are preceeding pages (i.e. it is not the last page of the issue since a paragraph will not continue over consecutive issues)
        if (mahuru_kupu[-1] not in tohutuhi) and (tāuru.hupa.select('div.navarrowsbottom')[0].find('td', align='right', valign='top').a):
            # Then this paragraph will be carried over to the next page (the next time this function is called) by using the global tīmata_kōwae variable

            # If there isn't already a paragraph being carried over, it stores the start of the paragraph's text, page number and url
            if not tīmata_kōwae:
                tīmata_kōwae = Tīmata_kōwae(tāuru)
            # Otherwise if there is a paragraph being carried over, it just adds the text to the rest of the paragraph, without changing the original page number and url
            else:
                tīmata_kōwae.kupu += tāuru.kupu
            # It then breaks, exiting out of the function, so the carried paragraph is not written until all the text in the paragraph has been collected

    return tīmata_kōwae


def mātītori_kupu(kupu):
    return re.findall(r'[\w\W]*?[{}][{}]*\n|[\w\W]+$'.format(tohutuhi, tohukī), kupu)


def rāringa_kaituhituhi(tāuru, tīmata_kōwae, store_page):
    # This function splits the text from a given page into its constituent
    # Paragraphs, and writes them along with the page's information (date
    # Retrieved, newspaper name, issue name, page number, Māori word count,
    # Ambiguous word count, other word count, total word count, Māori word
    # Percentage, the raw text, and the url of the page). If it determines that
    # The paragraph carries on to the next page, and it is not the last page of
    # An issue, it carries the information that changes from page to page (text,
    # Page number, url) to the next time the function is called, i.e. the next
    # Page. It tries to find where the paragraph continues, and then writes it
    # To the text csv with the information of the page where it was first found.
    # If it can't, it will continue to loop this information forward until the
    # Last page of the issue. It takes a Rārangi class object, and a csv writer.

    if tāuru.kupu:  # Only writes the information if text was able to be extracted

        # Splits the text up into paragraphs
        kupu_tūtira = mātītori_kupu(tāuru.kupu)

        # Loops through the paragraphs
        for kupu in kupu_tūtira:

            # Strips leading and trailing white space
            tāuru.kupu = kupu.strip()

            # If the paragraph is the last paragraph on the page
            if kupu == kupu_tūtira[-1]:
                tīmata_kōwae = kupu_moroki(tāuru, tīmata_kōwae)

            # If there is leftover text from the previous page, Find the first paragraph that isn't in caps, i.e. isn't a title
            if tīmata_kōwae and not kupu.isupper():

                # Add the leftover text to the first paragraph that isn't entirely uppercase
                tāuru.kupu = tīmata_kōwae.kupu + tāuru.kupu
                # The page number and url that are to be written with the paragraph are from the original paragraph, so they are taken from the global variable and assigned to the variables that will be written
                whārangi_tau = tīmata_kōwae.tau
                whārangi_taukaea = tīmata_kōwae.taukaea
                # Then the global variable is cleared, because it is being written, so nothing is being carried over to the next call of the function
                tīmata_kōwae = None

            else:
                # If nothing is being added from a previous page, the page number and url that are to be written come from the current page, and are assigned to the variables which will be written
                whārangi_tau = tāuru.tau
                whārangi_taukaea = tāuru.taukaea

            # Replaces all white space with a space
            tāuru.kupu = clean_whitespace(tāuru.kupu)
            # If there is no text left after it has been stripped, there is no point writing it, so the function continues onto the next paragraph
            if not tāuru.kupu:
                continue

            tāuru.urutau = whakarauiri(tāuru.kupu)
            tāuru.urutau = tohutau(tāuru.urutau)
            # Gets the percentage of the text that is Māori
            tāuru.māori, tāuru.rangirua, tāuru.pākehā, tāuru.tapeke, tāuru.ōrau = tiki_ōrau(
                tāuru.urutau)
            # Prepares the row that is to be written to the csv

            # ['newspaper', 'issue', 'page', 'māori_words', 'ambiguous_words', 'other_words',
            #  'total_words', 'percent_māori', 'adapted_text', 'url', 'raw_text'])

            store_page(tāuru.niupepa, tāuru.perehitanga, tāuru.published_date, whārangi_tau, tāuru.māori, tāuru.rangirua, tāuru.pākehā,
                       tāuru.tapeke, tāuru.ōrau, tāuru.urutau, whārangi_taukaea, tāuru.kupu)

    return tīmata_kōwae


def rīwhi_tauriterite(kimikimi, taumahi_ingoa, kōwae):
    # Finds all matches to the input regex, in the input text, using the input string to determine what to replace the match with
    # The first argument is a regex expression, the second is a string containing a function name from the tau module, the third is the text that is to be modified
    ngā_whakataki_tūtira = re.compile(kimikimi).findall(kōwae)
    for ngā_whakataki in ngā_whakataki_tūtira:
        whakataki = ngā_whakataki[0].strip()
        kupu = " "
        if taumahi_ingoa == "rā_kupu":
            kupu += "<date>"
        elif taumahi_ingoa == "tāima_kupu":
            kupu += "<time>"
        else:
            kupu += "<number>"
        kupu += " "
        kōwae = kōwae.replace(whakataki, kupu)
    return kōwae


def tohutau(kupu):
    # Formats text in a way suitable for the irstlm language model
    kupu = re.sub(r'w[”“"\'`‘’´]', 'wh', kupu.lower())
    kupu = re.sub(r'[—–]', '-', kupu)
    kupu = re.sub(r'([^A-Za-zĀĒĪŌŪāēīōū\s])', r' \1 ', kupu)
    kupu = re.sub(r'< (date|number|time) >', r'<\1>', kupu)
    kupu = re.sub(r'-', r'@-@', kupu)
    return "<s> " + clean_whitespace(kupu) + " </s>"


def unu_kupu_tōkau(hupa, tau):
    # Extracts the text for all pages of the issue it has been passed.
    # It takes a tuple and a list. The tuple has the newspaper name, issue name
    # And issue link. The list is of tuples containing each page of the issue's
    # Number, soup and url. It outputs a list of tuples, which contain each page
    # Of an issue's number, text and url.

    # Simplify the soup to the area we are interested in
    kupu_tōkau = hupa.select('div.documenttext')[0].find('td')

    # Must determine there is a div.documenttext, because .text will raise an error if it kupu_tōkau is None
    if kupu_tōkau != None:
        if kupu_tōkau.text:
            # If it can find text, it returns it
            return kupu_tōkau.text
        else:
            # If there is no text found, print an error
            print("Failed to extract text from page " + tau)
    else:
        print("Failed to extract text from page " + tau)

    return


def whakarauiri(kupu):
    # The calls to these functions in tau don't need to be made for the irstlm language model, however replacements make the model more effective. Hence we use a string with the function of the tau module's name to represent the kind of object it is replacing.
    marama = '(Hanuere|Pepuere|Maehe|Apereira|Mei|Hune|Hurae|Akuhata|Hepetema|Oketopa|Noema|Nowema|Tihema)'
    # Comma separated pound values, ending with common representations for shillings and pounds
    kupu = rīwhi_tauriterite('((£?([1-9]\d{0,2}[,\/‘`´’\'\".][ ]?)(\d{3}[,\/‘`´’\'\".][ ]?)*\d{3}([.,]{2}\d{1,2}){1,2}))', "pakaru_moni", kupu)
    kupu = rīwhi_tauriterite('(?i)(£?[1-9]\d{0,2}[,\/‘`´’\'\".][ ]?(\d{3}[,\/‘`´’\'\".]?[ ]?)+ ?l\.? ?( ?\d+ ?[ds]\.? ?){0,2})', "pakaru_moni", kupu)
    # Non-comma separated pound values, with the same endings
    kupu = rīwhi_tauriterite('(£?([1-9]\d*([.,]{2}\d{1,2}){1,2}))', "pakaru_moni", kupu)
    kupu = rīwhi_tauriterite('(?i)((£?[1-9]\d*( ?\d+ ?[lsd]\.? ?){1,3}))', "pakaru_moni", kupu)
    # Typical date format xx/xx/xx
    kupu = rīwhi_tauriterite('((\d{1,2}\/){1,2}\d{2})', "rā_kupu", kupu)
    # Other common date formats that involve words - e.g. the (day) of (month), (year); or (month) (day) (year)
    kupu = rīwhi_tauriterite('(?i)((\b|\W|\s|^)(te )\d{1,2}( [,o])? ' + marama + ',? \d{4}(\b|\W|\s|\s|$|\W))', "rā_kupu", kupu)
    kupu = rīwhi_tauriterite('(?i)((\b|\W|\s|^)\d{1,2}( [,o])? ' + marama + ',? \d{4}(\b|\W|\s|\s|$|\W))', "rā_kupu", kupu)
    kupu = rīwhi_tauriterite('(?i)(' + marama + ',? \d{1,2},? \d{4}(\b|\W|\s|$))', "rā_kupu", kupu)
    kupu = rīwhi_tauriterite('(?i)((\b|\W|\s|^)\d{4},? ' + marama + ')', "rā_kupu", kupu)
    kupu = rīwhi_tauriterite('(?i)(' + marama + ',? \d{4}(\b|\W|\s|$))', "rā_kupu", kupu)
    kupu = rīwhi_tauriterite('(?i)((\b|\W|\s|^)(te )\d{1,2}( [,o])? ' + marama + '(\b|\W|\s|$))', "rā_kupu", kupu)
    kupu = rīwhi_tauriterite('(?i)((\b|\W|\s|^)\d{1,2}( [,o])? ' + marama + '(\b|\W|\s|$))', "rā_kupu", kupu)
    kupu = rīwhi_tauriterite('(?i)(' + marama + ',? \d{1,2}(\b|\W|\s|$))', "rā_kupu", kupu)
    # Comma separated pound values with no suffixes
    kupu = rīwhi_tauriterite('(£([1-9]\d{0,2}[,‘`´’\'\".][ ]?)(\d{3}[,\/‘`´’\'\".][ ]?)*\d{3})', "pakaru_moni", kupu)
    # Other comma separated values, not financial
    kupu = rīwhi_tauriterite('(([1-9]\d{0,2}[,‘`´’\'\".][ ]?)(\d{3}[,\/‘`´’\'\".][ ]?)*\d{3})', "hōputu_tau", kupu)
    # Finds times separated by punctuation (with or without a space), optionally followed by am/pm
    kupu = rīwhi_tauriterite('(?i)((\d{1,2}\. ){1,2}(\d{1,2}) ?[ap]\.?m\.?)', "tāima_kupu", kupu)
    kupu = rīwhi_tauriterite('(?i)((\d{1,2}[,.:]){0,2}(\d{1,2}) ?[ap]\.?m\.?)', "tāima_kupu", kupu)
    kupu = rīwhi_tauriterite('((\d{1,2}\. ?){1,2}\d{1,2})', "tāima_kupu", kupu)
    # Deals with any leftover slash-separated values that weren't accepted by "tāima_kupu" by replacing the slashes with words
    kupu = rīwhi_tauriterite('((\d{1,6}( \/ | \/|\/ |\/|\.)){1,5}\d{1,5})', "hautau_rānei_ira", kupu)
    # Finds all other monetary values
    kupu = rīwhi_tauriterite('(£(\d)+)', "pakaru_moni", kupu)
    # Finds all other numbers
    kupu = rīwhi_tauriterite('((\d)+)', "hōputu_tau", kupu)
    # Removes characters that aren't letters or spaces.
    kupu = re.sub(r'[^A-Za-zĀĒĪŌŪāēīōū!"#$%&\'()*+,./:;<=>?[\\]^_`‘’{|}-£´\s]', '', kupu)
    # Clears excess spaces
    return clean_whitespace(kupu)


class Command(BaseCommand):

    def __init__(self):
        super().__init__()
        cache_file = os.path.join(cache_dir, 'cache.pkl')
        self.cache = AutoSaveCache(cache_file, 10)

        self.browser_wrapper = BrowserWrapper(cache_dir)
        self.url_querier = UrlQuerier(self.cache, self.browser_wrapper)

        self.progress_cache_file = os.path.join(cache_dir, 'progress.pkl')
        if os.path.isfile(self.progress_cache_file):
            with open(self.progress_cache_file, 'rb') as f:
                self.progress_cache = pickle.load(f)
        else:
            self.progress_cache = dict()

    def store_page(self, npp_name, issue, published_date, page_number, maori_words, ambiguous_words, other_words, total_words,
                   percent_maori, adapted_text, url, raw_text):

        full_title = npp_name + ' ' + issue
        
        name_matcher = NEWSPAPER_NAME_MATCHER.match(full_title)
        if name_matcher is not None:
            newspaper_title = name_matcher.group(1)
        else:
            raise Exception('Malform publication title {}'.format(full_title))
        
        vol_matcher = NEWSPAPER_VOL_MATCHER.match(full_title)
        if vol_matcher is not None:
            volume = int(vol_matcher.group(2))
        else:
            volume = None

        no_matcher = NEWSPAPER_NO_MATCHER.match(full_title)
        if no_matcher is not None:
            number = int(no_matcher.group(2))
        else:
            number = None
            
        if len(published_date) == 8:
            datetime_format = '%Y%m%d'
        elif len(published_date) == 6:
            datetime_format = '%Y%m'
        elif len(published_date) == 4:
            datetime_format = '%Y'
        elif '-' in published_date:
            published_date = published_date[:published_date.index('-')]
            datetime_format = '%Y%m'
        else:
            raise ValueError('{} does not match any datetime format'.format(published_date))

        published_date = datetime.datetime.strptime(published_date, datetime_format).date()

        npp, _ = Newspaper.objects.get_or_create(name=newspaper_title)
        pub, _ = Publication.objects.get_or_create(newspaper=npp, published_date=published_date,
                                                volume=volume, number=number)

        pg, _ = Page.objects.get_or_create(publication=pub, page_number=page_number)
        pg.raw_text = raw_text
        pg.adapted_text = adapted_text
        pg.percentage_maori = percent_maori
        pg.url = url

        pg.maori_word_count = maori_words
        pg.ambiguous_word_count = ambiguous_words
        pg.other_word_count = other_words
        pg.total_word_count = total_words

        pg.save()

    def add_arguments(self, parser):
        parser.add_argument('--textfile', action='store', dest='textfile', required=False, type=str, default=None,
                            help="Output csv file where the date retrieved, newspaper names, issue names, page numbers,"
                                 " word counts, Māori percentage, page text and page urls are stored")

    def hātepe_perehitanga(self, niupepa):
        # This function extracts the text from every page of the newspaper issue it
        # Has been passed, and gives it to the text csv writing function. The input
        # Is a Perehitanga class object with the newspaper name, issue name and
        # Issue url as attributes, the csv writer, and a variable to determine if it
        # Should write the text from the first page of the issue it extracts.

        newspaper_progress_cache = self.progress_cache.get(niupepa.niupepa, None)
        if newspaper_progress_cache is None:
            newspaper_progress_cache = []
            self.progress_cache[niupepa.niupepa] = newspaper_progress_cache

        if niupepa.perehitanga in newspaper_progress_cache:
            print("Skip pages of " + niupepa.perehitanga + " in " + niupepa.niupepa + ":\n")
            return

        print("Collecting pages of " + niupepa.perehitanga + " in " + niupepa.niupepa + ":\n")

        # Passes the issue's information (Perehitanga class object) to the Rāringa class, as well as specifying which
        # page it should start from, as the process may have ended
        tāuru = Rārangi(self.url_querier, niupepa, niupepa.mātāmuri_taukaea if niupepa.mātāmuri else niupepa.taukaea)

        tīmata_kōwae = None

        # If it hasn't been told to ignore the first page, it passes the information to the writing function
        if not niupepa.mātāmuri:
            print("Extracted page " + tāuru.tau)
            rāringa_kaituhituhi(tāuru, tīmata_kōwae, self.store_page)
        else:
            tāuru.kupu = mātītori_kupu(tāuru.kupu)[-1]
            tīmata_kōwae = kupu_moroki(tāuru, tīmata_kōwae)
            # Loops, trying to find a next page. If it can't, the loop breaks.
        while True:
            # Simplifies the soup to where the next page link will be located
            taukaea_pinetohu = tāuru.hupa.select('div.navarrowsbottom')[
                0].find('td', align='right', valign='top')

            # If there is no next page button, the process ends and the list is returned
            if taukaea_pinetohu.a == None:
                print("\nFinished with " + niupepa.perehitanga +
                      " in " + niupepa.niupepa + "\n\n----------\n")

                newspaper_progress_cache.append(niupepa.perehitanga)
                return

            # If there is a link, its page number, soup and url are made into a tuple to be written to the csv
            elif taukaea_pinetohu.a['href']:

                tāuru = Rārangi(self.url_querier ,niupepa, pae_tukutuku + taukaea_pinetohu.a['href'])

                print("Extracted page " + tāuru.tau)

                # Passes the tuple and csv writer to the csv writing function
                tīmata_kōwae = rāringa_kaituhituhi(tāuru, tīmata_kōwae, self.store_page)

            # If there is some other option, the function ends, to prevent an infinite loop.
            else:
                print("\nError collecting all pages\n")
                print("Finished with " + niupepa.perehitanga +
                      " in " + niupepa.niupepa + "\n\n----------\n")
                newspaper_progress_cache.append(niupepa.perehitanga)
                return

    def tiki_niupepa(self):
        # Collects the urls and names of all the newspapers
        # Opens the archive page and fetches the soup

        hupa = bs(self.url_querier.query_or_load(pae_tukutuku_haurua), 'html.parser')

        # Gets a list of all tags where newspaper links are stored
        for tr in hupa.select('div.top')[0].find_all('tr', {'valign': 'top'}):
            for td in tr.find_all('td', {'valign': 'top'}):
                if td.a:
                    taukaea = pae_tukutuku + td.a['href']
                elif td.text:
                    ingoa = td.text[:td.text.index(" (")].strip()

            niupepa = Perehitanga([ingoa, taukaea])
            self.tiki_perehitanga(niupepa)

    def tiki_perehitanga(self, niupepa):
        # Collects the names and urls of each issue of a particular newspaper
        hupa = bs(self.url_querier.query_or_load(niupepa.taukaea), 'html.parser')
        print("\n\nCollecting issues of " +
              niupepa.niupepa + "\n\n\n----------------------------------------\n\n")

        # Finds all tags that contain links and issue names
        for tr in hupa.select('#group_top')[0].find_all('tr', {"valign": "top"}):
            for td in tr.find_all('td', {"valign": "top"}):
                if td.a:
                    # If there is a link, adds it to the link list. names and urls have the same index in their respective lists
                    niupepa.taukaea = pae_tukutuku + td.a['href']
                elif "No." in td.text or "Volume" in td.text or " " in td.text:
                    # Makes sure text meets criteria, as there is some unwanted text. the second bracket is a specific case that doesn't get picked up by the first bracket
                    niupepa.perehitanga = td.text.strip()
                    volumn_and_published_date = tr.text.strip()
                    if volumn_and_published_date.index(niupepa.perehitanga) != 0:
                        raise Exception('Volume row does not contain published date')
                    niupepa.published_date = volumn_and_published_date[len(niupepa.perehitanga):].strip()

                else:
                    pass

            # If commentary is in the tile, we don't want to extract this title or link
            if "commentary" in niupepa.perehitanga.lower():
                continue

            # If there is a carryover row from where the process stopped,
            if niupepa.mātāmuri:
                # And the current issue is not in the previously written row, then skip it until it is found
                if niupepa.perehitanga != niupepa.mātāmuri_perehitanga:
                    continue
                # If it is the same issue, it takes down the 'carryover row' flag, so it can go on to process the issue
                else:
                    niupepa.mātāmuri = False

            # Then processes the issue
            self.hātepe_perehitanga(niupepa)

    def matua(self):
        self.tiki_niupepa()

    def finalise(self):
        self.cache.save()
        with open(self.progress_cache_file, 'wb') as f:
            pickle.dump(self.progress_cache, f)

    def handle(self, textfile, *args, **options):
        self.browser_wrapper.auto_solve_captcha = True
        # self.populate()

        try:
            self.matua()
        finally:
            self.finalise()

    def make_query(self):
        self._query_or_populate(False)
    
    def populate(self):
        self._query_or_populate(True)