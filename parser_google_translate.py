# -*- codeing = utf-8 -*-
# @Author : Wuzhaoqi
# @Software : PyCharm
import re
import math
import time
import nltk
import calendar
import requests
from faker import Faker

"""
zh-CN: 中文简体
zh-TW：中文繁体
en: 英语
fr: 法语
de: 德语
ja: 日语
ko: 韩语
ru: 俄语
es: 西班牙语
"""


class GoogleTranslate(object):
    """
    Google translate API: https://translate.google.cn/translate_a/single?
    How to calculate the token of sentence: self.calculate_text_token
    How to get the seed token: self.get_token_key_seed
    How to determine if it is Chinese: self.is_chinese
    How to translate：self.translate: self.translate
    """
    def __init__(self):
        self.SALT_1 = "+-a^+6"
        self.SALT_2 = "+-3^+b+-f"
        self.token_key = None
        self.template_url = "https://translate.google.cn/translate_a/single?client=t&sl={}&tl={}&hl=zh-CN" \
                            "&dt=at&dt=bd&dt=ex&dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&tk={}&q={}"

    """ Functions used by the token calculation algorithm """
    @staticmethod
    def rshift(val, n):
        return val >> n if val >= 0 else (val + 0x100000000) >> n

    def work_token(self, a, seed):
        for i in range(0, len(seed) - 2, 3):
            char = seed[i + 2]
            d = ord(char[0]) - 87 if char >= "a" else int(char)
            d = self.rshift(a, d) if seed[i + 1] == "+" else a << d
            a = a + d & 4294967295 if seed[i] == "+" else a ^ d
        return a

    """ Get the random user agent to crate the headers of http get """
    @staticmethod
    def get_random_user_agent():
        faker = Faker()
        return {'User-Agent': faker.user_agent(), }

    """ Determine whether the sentence is Chinese """
    @staticmethod
    def is_chinese(text):
        for w in text:
            if '\u4e00' <= w <= '\u9fa5':
                return True
        return False

    """ Get the current token """
    def get_token_key_seed(self):
        """
        :return: Current time token
        """
        if self.token_key is not None:
            return self.token_key

        headers = self.get_random_user_agent()
        response = requests.get("https://translate.google.com/", headers=headers)
        tkk_expr = re.search("(tkk:.*?),", response.text)
        if not tkk_expr:
            raise ValueError(
                "Unable to find token seed! Did https://translate.google.com change?"
            )
        # Record available ua
        with open("./ua.txt", "a") as f:
            f.write(headers['User-Agent'] + "\n")
        tkk_expr = tkk_expr.group(1)
        try:
            # Grab the token directly if already generated by function call
            result = re.search(r"\d{6}\.[0-9]+", tkk_expr).group(0)
        except AttributeError:
            # Generate the token using algorithm
            timestamp = calendar.timegm(time.gmtime())
            hours = int(math.floor(timestamp / 3600))
            a = re.search(r"a\\\\x3d(-?\d+);", tkk_expr).group(1)
            b = re.search(r"b\\\\x3d(-?\d+);", tkk_expr).group(1)

            result = str(hours) + "." + str(int(a) + int(b))

        self.token_key = result
        return result

    """ Calculate the token of sentencet """
    def calculate_text_token(self, sentence):
        """
        :param seed: the token seed in current time
        :param sentence: the text you want to calculate its token
        :return: the token of the text of input
        """
        if self.token_key is not None:
            seed = self.token_key
        else:
            seed = self.get_token_key_seed()

        [first_seed, second_seed] = seed.split(".")

        try:
            text_byte = bytearray(sentence.encode("UTF-8"))
        except UnicodeDecodeError:
            # This will probably only occur when d is actually a str containing UTF-8 chars, which means we don't need
            # to encode.
            text_byte = bytearray(sentence)
        # calculate
        a = int(first_seed)
        for value in text_byte:
            a += value
            a = self.work_token(a, self.SALT_1)
        a = self.work_token(a, self.SALT_2)
        a ^= int(second_seed)
        if 0 > a:
            a = (a & 2147483647) + 2147483648
        a %= 1E6
        a = int(a)
        return str(a) + "." + str(a ^ int(first_seed))

    """ Translate """
    def translate(self, text, tl=None, sl=None):
        """
        :param text: the text you want to translate
        :param tl: the target language
        :param sl: the source language
        :return: the text was transalated
        """
        if len(text) > 4891:
            raise RuntimeError('The length of text should be less than 4891...')
        # read the target language
        if tl is None:
            if not self.is_chinese(text):
                target_language = "zh-CN"
            else:
                target_language = "en"
        else:
            target_language = tl
        # read the source language
        if sl is None:
            source_language = "auto"
        else:
            source_language = sl
        # translate each sentence in the text
        sentence_list = nltk.sent_tokenize(text)
        translated_text = ''
        for sentence in sentence_list:
            sentence_token = self.calculate_text_token(sentence)
            target_url = self.template_url.format(source_language, target_language, sentence_token, sentence)
            headers = self.get_random_user_agent()
            try:
                response = requests.get(target_url, headers=headers)
            except Exception:
                raise Exception("HTTP Error")
            else:
                translated_text += response.json()[0][0][0]
        return translated_text


if __name__ == "__main__":
    """
    from parser_google_translate import GoogleTranslate
    t = GoogleTranslate()
    text = "once upon a time there was a mountain, on the mountain was a temple"
    print(t.translate(text)
    """
    # The text you want to translate
    test_text = "once upon a time there was a mountain, on the mountain was a temple, " \
                "in the temple was a young monk and a old monk. hi, faker."
    # Crate the translate object
    t = GoogleTranslate()
    # If you use the default parameters, all languages will be recognized and return Chinese
    text_cn = t.translate(test_text)
    print(text_cn)
    # You can set the param 'tl' to declare the target language and 'sl' to declare the source language of your text
    text_ja = t.translate(test_text, tl="ja", sl="en")
    print(text_ja)
