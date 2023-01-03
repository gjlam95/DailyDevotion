import os
import logging
import urllib.parse
from telegram import Update
import urlfetch
import re
from bs4 import BeautifulSoup
from telegram.ext import CommandHandler, MessageHandler, Filters, ApplicationBuilder

# updater = Updater(os.environ.get('BOT_TOKEN'),
#                   use_context=True)
updater = ApplicationBuilder().token(os.environ.get('BOT_TOKEN')).build()

EMPTY = 'empty'


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hello! Type /help to see the commands available")


def help(update: Update, context: CallbackContext):
    update.message.reply_text("""Available Commands:
    /ymi - Access YMI Devotion Site
    /search John 3:16 - Get the passage from BibleGateway""")


def ymi_url(update: Update, context: CallbackContext):
    update.message.reply_text("YMI => https://ymi.today/devotionals/")


def unknown(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Sorry '%s' is not a valid command" % update.message.text)


def unknown_text(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Sorry I can't recognize you , you said '%s'" % update.message.text)


def search(update: Update, context: CallbackContext):
    update.message.reply_text(get_passage(
        str(context.args[0]) + " " + str(context.args[1])))


def strip_markdown(string):
    return string.replace('_', '\_').replace('`', '\`').replace('[', '\[')


def get_passage(passage, version='ESV', inline_details=False):
    def to_sup(text):
        sups = {u'0': u'\u2070',
                u'1': u'\xb9',
                u'2': u'\xb2',
                u'3': u'\xb3',
                u'4': u'\u2074',
                u'5': u'\u2075',
                u'6': u'\u2076',
                u'7': u'\u2077',
                u'8': u'\u2078',
                u'9': u'\u2079',
                u'-': u'\u207b'}
        return ''.join(sups.get(char, char) for char in text)

    BG_URL = 'https://www.biblegateway.com/passage/?search={}&version={}&interface=print'

    search = urllib.parse.quote(passage.lower().strip())
    url = BG_URL.format(search, version)
    try:
        logging.debug('Began fetching from remote')
        result = urlfetch.fetch(url, deadline=10)
        logging.debug('Finished fetching from remote')
    except urlfetch.Error as e:
        logging.warning('Error fetching passage:\n' + str(e))
        return None

    html = result.content
    start = html.find(b'<div class="passage-col')
    if start == -1:
        return EMPTY
    end = html.find(b'<!-- passage-box -->', start)
    passage_html = html[start:end]

    soup = BeautifulSoup(passage_html, 'lxml')

    title = soup.select_one('.bcv').text
    header = strip_markdown(title.strip()) + '(' + version + ')'

    passage_soup = soup.select_one('.passage-text')

    WANTED = 'bg-bot-passage-text'
    UNWANTED = '.passage-other-trans, .footnote, .footnotes, .crossreference, .crossrefs'

    for tag in passage_soup.select(UNWANTED):
        tag.decompose()

    for tag in passage_soup.select('h1, h2, h3, h4, h5, h6'):
        tag['class'] = WANTED
        text = tag.text.strip()
        if not inline_details:
            text = text.replace(' ', '\a')
        tag.string = '*' + strip_markdown(text) + '*'

    needed_stripping = False

    for tag in passage_soup.select('p'):
        tag['class'] = WANTED
        bad_strings = tag(text=re.compile('(\*|\_|\`|\[)'))
        for bad_string in bad_strings:
            stripped_text = strip_markdown(str(bad_string))
            bad_string.replace_with(stripped_text)
            needed_stripping = True

    if needed_stripping:
        logging.info('Stripped markdown')

    for tag in passage_soup.select('br'):
        tag.name = 'span'
        tag.string = '\n'

    for tag in passage_soup.select('.chapternum'):
        num = tag.text.strip()
        tag.string = '*' + strip_markdown(num) + '* '

    for tag in passage_soup.select('.versenum'):
        num = tag.text.strip()
        tag.string = to_sup(num)

    for tag in passage_soup.select('.text'):
        tag.string = tag.text.rstrip()

    final_text = header + '\n\n'
    for tag in passage_soup(class_=WANTED):
        final_text += tag.text.strip() + '\n\n'

    logging.debug('Finished BeautifulSoup processing')

    if not inline_details:
        return final_text.strip()
    else:
        start = html.find(b'data-osis="') + 11
        end = html.find(b'"', start)
        data_osis = html[start:end]
        qr_id = data_osis + '/' + version
        qr_title = title.strip() + ' (' + version + ')'
        content = final_text.split('\n', 1)[1].replace(
            '*', '').replace('_', '')
        content = ' '.join(content.split())
        qr_description = (
            content[:150] + '...') if len(content) > 153 else content
        return (final_text.strip(), qr_id, qr_title, qr_description)


updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('ymi', ymi_url))
updater.dispatcher.add_handler(CommandHandler('search', search))
updater.dispatcher.add_handler(CommandHandler('help', help))
updater.dispatcher.add_handler(MessageHandler(Filters.text, unknown))
updater.dispatcher.add_handler(MessageHandler(
    Filters.command, unknown))
updater.dispatcher.add_handler(MessageHandler(Filters.text, unknown_text))

updater.start_polling()
