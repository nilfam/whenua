import os
import re
import sys


oropuare = "aāeēiīoōuū"
orokati = "hkmnprtwŋƒ"
no_tohutō = ''.maketrans({'ā': 'a', 'ē': 'e', 'ī': 'i', 'ō': 'o', 'ū': 'u'})
arapū = "AaĀāEeĒēIiĪīOoŌōUuŪūHhKkMmNnPpRrTtWwŊŋƑƒ-"


class Taumahi:
    def __init__(self, verbose=False):
        self.verbose = verbose
        try:
            root = __file__
            if os.path.islink(root):
                root = os.path.realpath(root)
            dirpath = os.path.dirname(os.path.abspath(root)) + '/taumahi_tūtira'
        except:
            print("I'm sorry, but something is wrong.")
            print("There is no __file__ variable. Please contact the author.")
            sys.exit()

        # Reads the file lists of English and ambiguous words into list variables
        kōnae_pākehā = open(dirpath + "/kupu_kino_kūare_tohutō.txt", "r")
        kōnae_rangirua = open(dirpath + "/kupu_rangirua_kūare_tohutō.txt", "r")
        self.kupu_pākehā = kōnae_pākehā.read().split()
        self.kupu_rangirua = kōnae_rangirua.read().split()
        self.kupu_pākehā = self.hōputu(self.kupu_pākehā)
        self.kupu_rangirua = self.hōputu(self.kupu_rangirua)

        kōnae_pākehā.close(), kōnae_rangirua.close()

    def whakatakitahi(self, tauriterite):
        # If passed the appropriate letters, return the corresponding symbol
        oro = tauriterite.group(0)
        if oro == 'ng':
            return 'ŋ'
        elif oro == 'w\'' or oro == 'w’' or oro == 'wh':
            return 'ƒ'
        elif oro == 'Ng' or oro == 'NG':
            return 'Ŋ'
        else:
            return 'Ƒ'

    def whakatakirua(self, tauriterite):
        # If passed the appropriate symbol, return the corresponding letters
        oro = tauriterite.group(0)
        if oro == 'ŋ':
            return 'ng'
        elif oro == 'ƒ':
            return 'wh'
        elif oro == 'Ŋ':
            return 'Ng'
        else:
            return 'Wh'

    def hōputu(self, kupu, hōputu_takitahi=True):
        # Replaces ng and wh, w', w’ with ŋ and ƒ respectively, since Māori
        # consonants are easier to deal with in unicode format
        # The Boolean variable determines whether it's encoding or decoding
        # (set False if decoding)
        if isinstance(kupu, list):
            if hōputu_takitahi:
                return [re.sub(r'(w\')|(w’)|(wh)|(ng)|(W\')|(W’)|(Wh)|(Ng)|(WH)|(NG)', self.whakatakitahi, whakatomo) for
                        whakatomo in kupu]
            else:
                return [re.sub(r'(ŋ)|(ƒ)|(Ŋ)|(Ƒ)', self.whakatakirua, whakatomo) for whakatomo in kupu]
        elif isinstance(kupu, dict):
            if hōputu_takitahi:
                return [re.sub(r'(w\')|(w’)|(wh)|(ng)|(W\')|(W’)|(Wh)|(Ng)|(WH)|(NG)', self.whakatakitahi, whakatomo) for
                        whakatomo in kupu.keys()]
            else:
                return [re.sub(r'(ŋ)|(ƒ)|(Ŋ)|(Ƒ)', self.whakatakirua, whakatomo) for whakatomo in kupu.keys()]
        else:
            if hōputu_takitahi:
                return re.sub(r'(w\')|(w’)|(wh)|(ng)|(W\')|(W’)|(Wh)|(Ng)|(WH)|(NG)', self.whakatakitahi, kupu)
            else:
                return re.sub(r'(ŋ)|(ƒ)|(Ŋ)|(Ƒ)', self.whakatakirua, kupu)

    def kōmiri_kupu(self, kupu_tōkau):
        # Removes words that contain any English characters from the string above,
        # returns dictionaries of word counts for three categories of Māori words:
        # Māori, ambiguous, non-Māori (Pākehā)
        # Set kūare_tohutō = True to become sensitive to the presence of macrons when making the match

        # Splits the raw text along characters that a
        kupu_hou = re.findall('(?!-)(?!{p}*--{p}*)({p}+)(?<!-)'.format(
            p='[a-zāēīōū\-’\']'), kupu_tōkau, flags=re.IGNORECASE)

        if self.verbose:
            print('Words are: {}'.format(', '.join(kupu_hou)))

        # Setting up the dictionaries in which the words in the text will be placed
        raupapa_māori, raupapa_rangirua, raupapa_pākehā = {}, {}, {}

        kupu_hou = self.hōputu(kupu_hou)
        if self.verbose:
            print('After replacing character groups: {}'.format(', '.join(kupu_hou)))

        # Puts each word through tests to determine which word frequency dictionary
        # it should be referred to. Goes to the ambiguous dictionary if it's in the
        # ambiguous list, goes to the Māori dictionary if it doesn't have consecutive
        # consonants, doesn't end in a consnant, doesn't have any english letters
        # and isn't one of the provided stop words. Otherwise it goes to the non-Māori
        # dictionary. If this word hasn't been added to the dictionary, it does so,
        # and adds a count for every time the corresponding word gets passed to the
        # dictionary.

        for kupu in kupu_hou:
            if kupu.lower() in self.kupu_rangirua:
                if self.verbose:
                    if self.kupu_rangirua:
                        print('"{}" is an ambiguous word'.format(kupu))
                kupu = self.hōputu(kupu, False)
                if kupu not in raupapa_rangirua:
                    raupapa_rangirua[kupu] = 0
                raupapa_rangirua[kupu] += 1
                continue
            else:
                has_consecutive_consonants = re.compile("[{o}][{o}]".format(o=orokati)).search(kupu.lower())
                ends_in_consonant = kupu[-1].lower() in orokati
                has_english_letter = any(pūriki not in arapū for pūriki in kupu.lower())
                is_stop_word = kupu.lower() in self.kupu_pākehā

                if has_consecutive_consonants or ends_in_consonant or has_english_letter or is_stop_word:
                    if self.verbose:
                        if has_consecutive_consonants:
                            print('"{}" is an English word because it has consecutive consonants'.format(kupu))
                        if ends_in_consonant:
                            print('"{}" is an English word because it ends in a consonant'.format(kupu))
                        if has_english_letter:
                            print('"{}" is an English word because it has an English letter'.format(kupu))
                        if is_stop_word:
                            print('"{}" is an English word because it is a stop word'.format(kupu))
                    kupu = self.hōputu(kupu, False)
                    if kupu not in raupapa_pākehā:
                        raupapa_pākehā[kupu] = 0
                    raupapa_pākehā[kupu] += 1
                    continue
                else:
                    if self.verbose:
                        print('"{}" is a Maori word'.format(kupu))
                    kupu = self.hōputu(kupu, False)
                    if kupu not in raupapa_māori:
                        raupapa_māori[kupu] = 0
                    raupapa_māori[kupu] += 1

        return raupapa_māori, raupapa_rangirua, raupapa_pākehā

    def tiki_ōrau(self, kōwae):
        # Uses the kōmiri_kupu function from the taumahi module to estimate how
        # Much of the text is Māori. Input is a string of text, output is a percentage string

        # Gets the word frequency dictionaries for the input text
        raupapa_maori, raupapa_rangirua, raupapa_pakeha = self.kōmiri_kupu(kōwae)

        # Calculates how many words of the maori and English dictionary there are
        tatau_maori = sum(raupapa_maori.values())
        tatau_rangirua = sum(raupapa_rangirua.values())
        tatau_pakeha = sum(raupapa_pakeha.values())
        tatau_kapa = tatau_maori + tatau_pakeha
        tatau_tapeke = tatau_kapa + tatau_rangirua

        # Provided there are some words that are categorised as maori or English,
        # It calculates how many maori words there are compared to the sum, and
        # Returns the percentage as a string
        orau = 0.00 if (not tatau_kapa != 0) else round((tatau_maori / tatau_kapa) * 100, 2)

        return tatau_maori, tatau_rangirua, tatau_pakeha, tatau_tapeke, orau


if __name__ == '__main__':
    taumahi = Taumahi(verbose=True)
    maori_count, ambi_count, eng_count, total_count, pc = taumahi.tiki_ōrau('The thing is')
    print('Maori count: {}'.format(maori_count))
    print('Ambiguous count: {}'.format(ambi_count))
    print('English count: {}'.format(eng_count))
    print('Total count: {}'.format(total_count))
    print('Percentage: {}'.format(pc))
