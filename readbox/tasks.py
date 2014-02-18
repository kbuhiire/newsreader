from __future__ import unicode_literals
from smtplib import SMTPRecipientsRefused
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError
from django.db.models import Q, Count
from evernote.edam.type.ttypes import Note
from manhattan.settings import safe
from readbox.models import Feed, UserFeeds, Article, UserEx, UserStars, UserReads
from bs4 import BeautifulSoup, Comment
from celery.task import task
from datetime import datetime
from django.utils.timezone import utc
from time import mktime
from readbox.stripper import strip_tags
from urllib2 import HTTPError
from bitly_api import bitly_api
from evernote.api.client import EvernoteClient
from django.conf import settings
from open_facebook.api import FacebookAuthorization
import lxml.html
import cld
import oauth2 as oauth
import subprocess
import tempfile
import feedparser
import urlparse
import requests
import json
import urllib

yql_url = 'http://query.yahooapis.com/v1/public/yql?q=select * from contentanalysis.analyze where url="{0}"&format=json'
yql_text = 'http://query.yahooapis.com/v1/public/yql?q=select * ' \
           'from contentanalysis.analyze where text="{0}"&format=json'
short = bitly_api.Connection(login='LOGIN HERE', api_key='API_KEY HERE')
read_url = 'https://readability.com/api/content/v1/parser?url={0}/&token=TOKEN_HERE'
readability_consumer_key = 'readbox'
readability_consumer_secret = 'READABILITY CONSUMER HERE'
readability_add_url = 'https://www.readability.com/api/rest/v1/bookmarks'
pocket_consumer_key = 'POCKET HERE'
pocket_add_url = 'https://getpocket.com/v3/add'


@task
def extend_access_tokens():
    for user in UserEx.objects.filter(facebook_id__isnull=False):
        results = FacebookAuthorization.extend_access_token(user.access_token)
        access_token = results['access_token']
        old_token = user.access_token
        token_changed = access_token != old_token
        if token_changed:
            user.access_token = access_token
            user.new_token_required = False
            user.save()


# Add a feed and send an async request to populate its collection
# noinspection PyBroadException
def add_feed(feed_url):
    try:
        this_feed = feedparser.parse(feed_url)
        if this_feed['items']:
            if 'link' not in this_feed.get('channel'):
                    if 'link' in this_feed['items'][0]:
                        parsed_url = urlparse.urlparse(this_feed['items'][0]['link'])
                        this_feed['channel']['link'] = urlparse.urlunparse(
                            (parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
                    else:
                        return None
            if 'title' and 'link' in this_feed.get('channel'):
                _new = Feed.objects.create(title=this_feed['channel']['title'],
                                           home=this_feed['channel']['link'],
                                           url=feed_url,
                                           favicon=get_favicon(this_feed['channel']['link']))
                refresh_feed.delay(_new.url, _new.id)
                return _new
            else:
                return None
    except IndexError:
        return None
    except Exception:
        return None


# Find a feed in home url
def find_feed_scraping(feed_url):
    parsed_url = urlparse.urlparse(feed_url)
    base_url = urlparse.urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
    doc = lxml.html.parse(base_url)
    feeds = doc.xpath('//link[@type="application/rss+xml"]/@href')
    res = []
    for x in feeds:
        if x.startswith('/'):
            res.append(base_url + x)
        else:
            res.append(x)
    return res


# First function to be called
def search_and_add_feed(feed, retry=0):
    try:
        feed = requests.get(feed).url
    except Exception:
        return None
    test = [feed]
    if feed.endswith('/'):
        test.append(feed[:-1])
    else:
        test.append(feed + '/')
    if 'www' not in feed:
        test.append('http://www.' + feed[7:])
    if 'www' in feed:
        test.append('http://' + feed[11:])
    if 'http://' in feed:
        for y in ['https://' + x[7:] for x in test]:
            test.append(y)
    elif 'https://' in feed:
        for y in ['http://' + x[8:] for x in test]:
            test.append(y)
    search = Feed.objects.filter(url__in=test)
    if len(search) == 0:  # If we don't have any results
        new_feed = add_feed(feed)
        if new_feed:
            return [new_feed]
        elif retry == 0:
            try:
                new = search_and_add_feed(find_feed_scraping(feed)[0], 1)
            except (IndexError, IOError):
                return None
            if new:
                return new
        return None
    else:
        return search


@task
def refresh_all_feeds():
    for e in Feed.objects.all().iterator():
        refresh_feed.delay(e.url, e.id, **{'summarize': e.summarize, 'top': e.top,
                                           'summarize_excerpt': e.summarize_excerpt})


@task
def refresh_feed(feed_url=None, feed_id=None, **kwargs):
    if feed_url is None or feed_id is None:
        feed_url = kwargs['feed_url']
        feed_id = kwargs['feed_id']
    try:
        this_feed = feedparser.parse(feed_url)
        for x in range(len(this_feed['items'])):
            get_full_article.delay(this_feed['items'][x], feed_id, **kwargs)
    except HTTPError:
        pass


@task(hard_time_limit=60)
def get_full_article(this_item, feed_id, **kwargs):
    if len(this_item['link']) > 200:
        this_item['link'] = short.shorten(this_item['link'])['url']
    if any(required not in this_item for required in ['title', 'link']):
        return
    try:
        Article.objects.values('id').get(Q(feed_id=feed_id, url=this_item['link']) |
                                         Q(feed_id=feed_id, title=this_item['title']))
        return
    except Article.DoesNotExist:
        pass
    except Article.MultipleObjectsReturned:
        return
    published_parsed = datetime.utcnow().replace(tzinfo=utc)
    if 'updated_parsed' not in this_item:
        if 'published_parsed' in this_item and datetime.utcfromtimestamp(
                mktime(this_item['published_parsed'])).replace(tzinfo=utc) < published_parsed:
            published_parsed = datetime.utcfromtimestamp(mktime(this_item['published_parsed'])).replace(tzinfo=utc)
    elif datetime.utcfromtimestamp(mktime(this_item['updated_parsed'])).replace(tzinfo=utc) < published_parsed:
        published_parsed = datetime.utcfromtimestamp(mktime(this_item['updated_parsed'])).replace(tzinfo=utc)
    if 'author' not in this_item:
        this_item['author'] = None
    if 'description' not in this_item:
        this_item['description'] = ''
    if len(this_item['title']) > 200:
        this_item['title'] = this_item['title'][:180] + '...'
    res = process_article(this_item['description'])
    this_item['excerpt'] = res['excerpt']
    this_item['word_count'] = res['word_count']
    this_item['description'] = res['content']
    media = res['image']
    full = None
    if not media:
        if 'media_content' in this_item and 'url' in this_item['media_content'][0]:
            media = this_item['media_content'][0]['url']
        else:
            full = get_article_readability(this_item)
            if full:
                res = full
                media = res['lead_image_url']
    if len(this_item['excerpt']) == 0:
        this_item['language'] = cld.detect(this_item['excerpt'].encode('ascii', 'ignore'))[1]
        if this_item['language'] == 'un':
            this_item['language'] = cld.detect(this_item['title'].encode('ascii', 'ignore'))[1]
    else:
        this_item['language'] = cld.detect(this_item['title'].encode('ascii', 'ignore'))[1]

    if kwargs.get('summarize_excerpt'):
        extend = {
            'content_ex': None,
            'summary': None
        }
        try:
            with tempfile.NamedTemporaryFile() as tmp:
                    tmp_path = tmp.name
                    tmp.write((strip_tags(res['content'].decode('ascii', 'ignore'))).strip())
                    tmp.flush()
                    extend['summary'] = subprocess.check_output(['ots', tmp_path]).strip().splitlines().pop().strip()
        except Exception:
            pass
    else:
        extend = extend_article(full, this_item['link'], **kwargs)

    obj, created = Article.objects.get_or_create(
        feed_id=feed_id, url=this_item['link'],
        defaults={'title': this_item['title'], 'content': this_item['description'],
                  'word_count': res['word_count'], 'url': this_item['link'], 'media': media,
                  'date_parsed': published_parsed, 'author': this_item['author'], 'excerpt': this_item['excerpt'],
                  'language': this_item['language'], 'summary': extend['summary'], 'content_ex': extend['content_ex']})
    if created:
        get_article_info(obj)


def extend_article(res, url, **kwargs):
    ex = {
        'summary': None,
        'content_ex': None
    }
    try:
        if not kwargs.get('summarize', None) and not kwargs.get('top', None):
            return ex
        if not res:
            request = requests.get(read_url.format(url))
            res = request.json()
            if request.status_code != 200 or ('error' in res and res['error']) or not res:
                return ex
        if kwargs.get('summarize', None):
            with tempfile.NamedTemporaryFile() as tmp:
                tmp_path = tmp.name
                tmp.write((strip_tags(res['content'].decode('ascii', 'ignore'))).strip())
                tmp.flush()
                ex['summary'] = subprocess.check_output(['ots', tmp_path]).strip().splitlines().pop().strip()
        if kwargs.get('top', None):
            ex['content_ex'] = res['content']
    except Exception:
        pass
    return ex


def get_article_readability(this_item):
    try:
        request = requests.get(read_url.format(this_item['link']), timeout=10)
        res = request.json()
        if request.status_code != 200 or ('error' in res and res['error']) or not res:
            return None
        if not res['lead_image_url']:
            processed = process_article(res['content'])
            res['lead_image_url'] = processed['image']
        return res
    except Exception:
        return None


def get_article_info(article):
    res = None
    try:
        res = requests.get(yql_text.format(article.excerpt.replace('"', r'\"')), timeout=5)
    except Exception:
        return None
    if res.status_code == 200:
        result = res.json().get('query', {}).get('results', None)
        if result:
            categories = result.get('yctCategories', {}).get('yctCategory', None)
            entity = result.get('entities', {}).get('entity', None)
            if entity and isinstance(entity, list) and len(entity) > 0:
                keywords = {x['text']['content']: float(x['score']) for x in entity}
                article.keywords.add(*keywords.keys())
            elif isinstance(entity, dict):
                article.keywords.add(entity['text']['content'])
            if categories and isinstance(categories, list):
                keywords = {x['content']: float(x['score']) for x in categories}
                article.keywords.add(*keywords.keys())
            elif isinstance(categories, dict):
                article.keywords.add(categories['content'])


@task
def compute_feed_keywords():
    for feed in Feed.objects.all():
        keywords = [x['keywords__name'] for x in
                    Article.objects.filter(feed_id=feed.id).values('keywords__name')
                    .annotate(a=Count('keywords__name')).order_by('-a')[:6] if x['keywords__name'] is not None]
        if len(keywords) > 0:
            feed.keywords.add(*keywords)


@task
def compute_feed_language():
    for feed in Feed.objects.all():
        languages = Article.objects.filter(feed_id=feed.id).values('language').annotate(a=Count('language'))\
            .order_by('-a')[:20]
        for x in languages:
            if x != 'un':
                feed.language = x['language']
                feed.save()
                break


def merge_feeds(source_id, destination_id):
    source = Feed.objects.get(id=source_id)
    destination = Feed.objects.get(id=destination_id)
    try:
        for user in UserFeeds.objects.filter(feed=source):
            user.feed = destination
    except IntegrityError:
        pass
    for stars in UserStars.objects.select_related('article').filter(article__feed_id=source.id):
        try:
            dest = Article.objects.get(title=stars.article.title, feed=destination)
            stars.article = dest
            stars.save()
        except Article.DoesNotExist:
            pass
        except IntegrityError:
            pass
    for reads in UserReads.objects.select_related('article').filter(article__feed_id=source.id):
        try:
            dest = Article.objects.get(title=reads.article.title, feed=destination)
            reads.article = dest
            reads.save()
        except Article.DoesNotExist:
            pass
        except IntegrityError:
            pass
    source.delete()


@task
def detect_articles_language():
    for x in Article.objects.all().iterator():
        x.language = cld.detect(x.excerpt.encode('ascii', 'ignore'))[1]
        x.save()


# This will get the favicon in a html based page
def get_favicon(url):
    try:
        html = requests.request('GET', url)
        soup = BeautifulSoup(html.text)
        icon = soup.find('link', rel='shortcut icon')
        if icon is None:
            icon = soup.find('link', type='image/x-icon')
        icon_href = None
        if hasattr(icon, 'href'):
            icon_href = str(icon['href'])
        if icon_href is None or icon_href.strip() == "":
            parsed_url = urlparse.urlparse(url)
            icon_href = urlparse.urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', '')) + '/favicon.ico'
            last_try = requests.request('GET', icon_href)
            if last_try.status_code == 200:
                return icon_href
            else:
                return None
        if "http://" not in icon_href:
            parsed_url = urlparse.urlparse(url)
            icon_href = urlparse.urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', '')) + icon_href
        last_try = requests.request('GET', icon_href)
        if last_try.status_code == 200:
            return icon_href
        else:
            return 'https://www.readbox.co/static/lightpng.png'
    except Exception:
        return 'https://www.readbox.co/static/lightpng.png'


EXCLUDED_IMAGES_HOST = ['feedburner.com', 'pixel.newscred.com', 'feedsportal.com', 'stats.wordpress.com',
                        'hits.theguardian.com', 'ad.doubleclick.net', 'share-buttons', 'rss.cnn.com',
                        'feedads.googleadservices.com', 'feedproxy.google.com', 'feeds.washingtonpost.com',
                        'fmpub.net/adserver', 'pheedo.com', 'feeds.wired.com', 'techmeme.com/img/pml.png',
                        'feeds.boston.com', 'a.fsdn.com', 'mf.gif']
EXCLUDED_DIV_CLASS = ['feedflare', 'share_submission', 'snap_preview', 'zemanta-pixie', 'cbw', 'snap_nopreview',
                      'cb_widget']
EXCLUDED_A = ['feedsportal.com', 'twitter.com/share?via=', 'www.facebook.com/sharer.php?u=', 'fmpub.net',
              'ad.doubleclick.net', 'addtoany.com', 'feeds.wordpress.com', 'doubleclick.net', 'eyewonderlabs.com',
              'abovethelaw.com', 'crunchbase.com/company', 'pheedo.com', 'api.tweetmeme.com',
              'mailto:yourfriend@email.com', 'https://twitter.com/share']
EXCLUDED_TAGS = ['br', 'hr', 'form', 'input', 'style', 'script', 'plaintext', 'xmp', 'meta', 'frame',
                 'frameset', 'iframe', 'listing', 'link', 'comment', 'font']
EXCLUDED_ATTR = ['class', 'id', 'style', 'width', 'height', 'clear', 'target', 'onclick', 'ondblclick',
                 'onmousedown', 'onmousemove', 'onmouseover', 'onmouseout', 'onmouseup', 'onkeydown',
                 'onkeypress', 'onkeyup', 'onabort', 'onerror', 'onload', 'onresize', 'onscroll',
                 'onunload', 'onblur', 'onchange', 'onfocus', 'onreset', 'onselect', 'onsubmit',
                 'width', 'height']


# Clean up the html
def process_article(html, full=True, replace=False):
    pos = 0
    src = None
    try:
        soup = BeautifulSoup(html)
    except UnicodeEncodeError:
        soup = BeautifulSoup(html.encode('utf-8', 'ignore'))
    media_found = False
    for tag in soup.find_all(True):
        if any(x == tag.name for x in EXCLUDED_TAGS) \
            or (tag.name == 'div' and 'class' in tag.attrs and any(div in tag.attrs['class'] for div in EXCLUDED_DIV_CLASS))\
            or ((not tag.contents and not tag.name == 'img' and (tag.string is None or not tag.string.strip()))
                or (tag.name == 'img' and 'src' in tag.attrs
                    and any(host in tag['src'] for host in EXCLUDED_IMAGES_HOST)))\
            or (tag.name == 'a' and 'href' in tag.attrs and any(host in tag.attrs['href'] for host in EXCLUDED_A))\
                or isinstance(tag, Comment):
                    if tag.parent and tag.parent.name == 'a':
                        tag.parent.decompose()
                    else:
                        tag.decompose()
                    continue
        for attr in EXCLUDED_ATTR:
            try:
                del tag[attr]
            except AttributeError:
                pass
        if not replace and not media_found and full:
            if tag.name != 'img' and tag.name != 'a' and pos > 12:
                media_found = True
            elif tag.name == 'img' and 'src' in tag.attrs:
                src = tag.attrs['src']
                if src:
                    o = urlparse.urlparse(src)
                    src = o.scheme + "://" + o.netloc + o.path
                if tag.parent and tag.parent.name == 'a':
                    tag.parent.decompose()
                else:
                    tag.decompose()
                media_found = True
            pos += 1
        if replace:
            if tag.name == 'img' and 'src' in tag.attrs and tag.attrs['src'] == replace:
                if tag.parent and tag.parent.name == 'a':
                    tag.parent.decompose()
                else:
                    tag.decompose()
    content = unicode(soup)
    if full:
        excerpt = (strip_tags(content)).strip()
        return {'content': content, 'image': src, 'word_count': len(excerpt.split()), 'excerpt': excerpt}
    else:
        return {'content': content, 'image': src}


def send_activation_email(user):
    email = user.email
    full_name = user.facebook_name
    email_token = safe.dumps(json.dumps({'email': email, 'created_at': datetime.utcnow()}, cls=DjangoJSONEncoder))
    email_message = 'Hi ' + full_name + ',\n\n' + 'To verify your email address, please follow this link \n' \
                                                  'http://readbox.co/confirm/?c=' + email_token + '\n' + \
                    "(If clicking on the link doesn't work, try copying and pasting it into your browser.)" + \
                    "\n\nIf you did not enter this address as your contact email, " \
                    "please disregard this message." + "\n\nThanks,\nThe Readbox Team"
    send_mail(subject='Readbox Email Verification', message=email_message, from_email="support@readbox.co",
              recipient_list=[email])


@task
def retry_activation_email():
    inactive = UserEx.objects.filter(is_active=0)
    for user in inactive.iterator():
        try:
            send_activation_email(user)
        except SMTPRecipientsRefused:
            pass


def get_evernote_client(token=None):
    if token:
        return EvernoteClient(token=token, sandbox=False)
    else:
        return EvernoteClient(
            consumer_key=settings.EVERNOTE_CONSUMER_KEY,
            consumer_secret=settings.EVERNOTE_CONSUMER_SECRET,
            sandbox=False
        )


def get_safe():
    return safe


@task
def share_pocket(user, article_url):
    requests.post(pocket_add_url, headers={'content-type': 'application/json', 'x-accept': 'application/json'},
                  data=json.dumps({'url': article_url, 'consumer_key': pocket_consumer_key,
                                   'access_token': user['extras']['pocket']}))


@task
def share_evernote(user, article):
    client = get_evernote_client(user['extras']['evernote'])
    note_store = client.get_note_store()
    note = Note()
    note.title = article.title
    note.content = '<?xml version="1.0" encoding="UTF-8"?>'
    note.content += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
    note.content += '<en-note>{0}<br /><a href="{1}">[Article Link]</a></en-note>'.format(article.excerpt, article.url)
    note_store.createNote(note)


@task
def share_readability(user, article_url):
    token = oauth.Token(user['extras']['readability']['oauth_token'], user['extras']['readability']['oauth_token_secret'])
    consumer = oauth.Consumer(readability_consumer_key, readability_consumer_secret)
    oauth_client = oauth.Client(consumer, token)
    params = urllib.urlencode({'url': article_url})
    oauth_client.request(readability_add_url, method='POST', body=params)