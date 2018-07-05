import sys
import signal
import pickle
import time
import json
from urllib.request import urlopen
from urllib import error
from collections import deque

from bs4 import BeautifulSoup

from util import get_date_format, get_page_addr, get_snapshot_number

MAX_DEPTH_FROM_HOME = 2
MAX_TRIES = 5

seen_pages = set()
url_queue = deque()


class AccessInfo:
  """
  year: year to search for
  month: month to start from
  dat: day of month to start from
  no_days: number of days from day to search for
  end_date: string in format yyyymmdd
  url:
  get_page_info: method to get info about page
  save_article: method to save article
  """

  def __init__(self, year, month, day, no_days, end_date, url, domain_name,
               get_page_info, save_article):
    self.year = year
    self.month = month
    self.day = day
    self.no_days = no_days

    self.start_date = int(get_date_format(year, month, day))
    self.end_date = end_date

    self.url = url

    self.domain_name = domain_name

    # self.is_proper_page = is_proper_page
    # self.is_article = is_article
    # get_pub_date

    self.get_page_info = get_page_info
    self.save_article = save_article


class ArticleInfo:
  """
  used for saving the article

  pyear:
  pmonth:
  pday:
  title:
  surl: url specific to this article
  scat: specific category of this article
  """

  def __init__(self, pyear, pmonth, pday, title, surl, scat=None):
    self.pyear = pyear
    self.pmonth = pmonth
    self.pday = pday

    self.title = title

    self.surl = surl

    self.scat = scat


def traverse_calendar(data, access_info):
  """
  data: list obtained from json data of calendar
  access_info

  """

  home_page_url = "https://web.archive.org/web/{}/" + access_info.url

  seen_days = 0
  skip_days = 0
  id_dict = {}
  for m in range(access_info.month - 1, len(data)):
    cur_day = 1
    for week in data[m]:
      for day in week:
        # day is None when that day is not in clendar month
        if day is None:
          continue

        # skipping the days till we reach the start day
        if skip_days + 1 < access_info.day:
          cur_day += 1
          skip_days += 1
          continue

        # check for empty dictionary
        if day:
          id_dict[get_date_format(access_info.year, (m + 1), cur_day)] = [
              home_page_url.format(x) for x in day['ts']
          ]

        cur_day += 1
        seen_days += 1
        if seen_days >= access_info.no_days:
          return id_dict


def get_home_page_urls(access_info):
  main_url = "https://web.archive.org/__wb/calendarcaptures?url={}&selected_year={}".format(
      access_info.url, access_info.year)

  response = urlopen(main_url)

  print('response code', response.code)
  page = response.read().decode('utf-8')

  data = json.loads(page)
  id_dict = traverse_calendar(data, access_info)
  return id_dict


# Returns: page, snap if obtained else None, None
def get_page(url):
  tries = 0
  code = None
  while (tries < MAX_TRIES):
    try:
      response = urlopen(url)
    except error.HTTPError as h:
      print('url: {} got HttpError, error: {}'.format(url, h))
      return None, None
    except error.URLError as u:
      print('url: {} got URLError, error: {}'.format(url, u))
      return None, None
    except Exception as e:
      print('url: {} got error, error: {}'.format(e))
      return None, None

    if (response.getcode() == 200):
      r_url = response.geturl()

      # check whether response url is pointing to a valid page
      # one way is to check for yyyymmddhhmmss/ format in url
      r_snap = get_snapshot_number(r_url)

      # url will always have snap because url is added only if it has snap
      # look at traverse_page and when queue is loaded first time
      snap = get_snapshot_number(url)
      if r_snap is None or r_snap != snap:
        print('response url is different {}'.format(r_url))
        print('snap:', snap, 'r_snap', r_snap)
        return None, None

      try:
        page = response.read().decode('utf-8', 'ignore')
        return page, snap
      except UnicodeDecodeError as e:
        print('error decoding page at url: {}, error: {}'.format(url, e))
        input()
        return None, None
      except Exception as e:
        print('error: {}'.format(e))
        return None, None

    code = response.getcode()
    tries += 1

  # log here about url and response
  print("{}: response code: {}".format(url, code))
  return None, None


# Returns: None
def traverse_page(url, u_addr, access_info, depth=None):
  page, snap = get_page(url)
  if page is None:
    return

  is_proper_page, is_article, pub_date = access_info.get_page_info(page, url)
  print('page {} is_proper_page: {}, is_article: {}, pub_date: {}'.format(
      url, is_proper_page, is_article, pub_date))
  input()

  if (is_proper_page and is_article) or (depth is not None and depth == 0):
    # look for article
    if not is_article:
      return

    # save article if appropriate
    # check for publication date
    if pub_date < access_info.start_date or pub_date > access_info.end_date:
      return

    access_info.save_article(page, u_addr, pub_date)

  if depth is None:
    depth = MAX_DEPTH_FROM_HOME

  # look at all the urls
  # add to list: url that are article with depth 0
  #              url that are other with depth depth - 1

  soup = BeautifulSoup(page, 'html5lib')

  all_as = soup.find_all('a', href=True)

  for a_tag in all_as:
    href = str(a_tag['href'])

    addr = get_page_addr(href, access_info.domain_name)

    snap_new = get_snapshot_number(href)
    if snap_new is None:
      continue

    snap_date = int(snap_new[:8])
    if snap_date < access_info.start_date or snap_date > access_info.end_date:
      continue

    if addr is not None:
      addr = snap_new[:8] + '_' + addr

    # check whether url is in the set using page specific url name
    if addr is None or addr in seen_pages:
      continue

    seen_pages.add(addr)
    url_queue.append((addr, href, depth - 1))


def crawl(access_info):
  while url_queue:
    u_addr, href, depth = url_queue.popleft()
    print('traversing url: {}'.format(href))
    traverse_page(href, u_addr, access_info, depth)


# page: is an article
# pub_date:
def save_article(page, u_addr, pub_date):
  # save article

  pub_date = str(pub_date)
  y = pub_date[:4]
  m = pub_date[4:6]
  d = pub_date[6:]

  with open('./articles/{}'.format(u_addr), 'w+') as f:
    f.write(page)


# page: page on the web
# url
# Returns: whether it is nytimes page (true or false), whether it is article (true or false),
#          publication date (None or date)
def nytimes_page_info(page, url):
  is_proper_page = False
  is_article = False
  pub_date = None

  soup = BeautifulSoup(page, "html5lib")

  # check for page is proper or not
  # necessary because if page does not exist, wayback will lead to different page even if
  # url contains nytimes as substring

  if soup.title is not None:
    title = str(soup.title.string).lower()
    print(title)

    find = ['nytimes.com', 'the new york times']
    for name in find:
      if name in title:
        is_proper_page = True
        break

  if not is_proper_page:
    meta_cre_tag = soup.find('meta', attrs={'name': 'cre'})
    if meta_cre_tag is not None:
      is_proper_page = 'the new york times' in meta_cre_tag['content'].lower()

  if not is_proper_page:
    print('page {} is not proper'.format(url))
    return False, False, None

  meta_articleid_tag = soup.find('meta', attrs={'name': 'articleid'})
  if meta_articleid_tag is not None:
    is_article = True

  if not is_article:
    meta_pt_tag = soup.find('meta', attrs={'name': 'PT'})
    if meta_pt_tag is not None and meta_pt_tag['content'].lower() == 'article':
      is_article = True

  # date = soup.find('div', id='date')
  # if date is None:
  #   date = soup.find('div', class_='timestamp')

  if is_article:
    meta_pdate_tag = soup.find('meta', attrs={'name': 'pdate'})
    if meta_pdate_tag is not None:
      pub_date = int(meta_pdate_tag['content'])
    else:
      is_article = False
      print('{} is not article (does not have pdate)'.format(url))

  if is_article:
    return is_proper_page, is_article, pub_date
  else:
    print('url {} is not article'.format(url))
    return is_proper_page, is_article, None


def save_data_struc():
  with open("seen_pages.p", "wb") as f:
    pickle.dump(seen_pages, f)

  with open("url_queue.p", "wb") as f:
    pickle.dump(url_queue, f)


def load_data_struc():
  try:
    with open("seen_pages.p", "rb") as f:
      seen_pages = pickle.load(f)
      print(seen_pages)

    with open("url_queue.p", "rb") as f:
      url_queue = pickle.load(f)
      print(url_queue)

  except FileNotFoundError:
    print('data structures not yet pickled')
    seen_pages = set()
    url_queue = deque()


def signal_handler(signal, frame):
  print('pressed CTRL-C')
  save_data_struc()
  sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':

  year, month, day = 2010, 1, 1
  url, domain_name = "http://www.nytimes.com/", "nytimes.com"
  no_days = 31
  end_date = 20100131
  nytimes_info = AccessInfo(year, month, day, no_days, end_date, url,
                            domain_name, nytimes_page_info, save_article)

  nytimes_home_pages = get_home_page_urls(nytimes_info)
  print(nytimes_home_pages)

  load_data_struc()

  try:
    for key, value in nytimes_home_pages.items():
      addr = key + '_'
      if addr not in seen_pages:
        seen_pages.add(addr)
        url_queue.append((addr, value[-1], MAX_DEPTH_FROM_HOME))
        break

    crawl(nytimes_info)

  except Exception as e:
    print(e)
    save_data_struc()