import sys
import signal
import pickle
import time
import json
from urllib.request import urlopen
from urllib import error
from datetime import datetime

from collections import deque
from queue import Queue

import threading

from bs4 import BeautifulSoup

from util import get_date_format, get_page_addr, get_snapshot_number
from util import PrintingThread

MAX_DEPTH_FROM_HOME = 2
MAX_TRIES = 5
MAX_THREADS = 4
LOG_FILE = './logs'

empty_threads = 0

seen_pages = set()

# saved pages is needed because different url may be pointing to same page
# because of different snapshots
# pages are remembered using publication date
saved_pages = set()

# format of queue is (url, snapshot (string), page_address, depth)
url_queue = deque()

seen_page_lock = threading.Lock()
saved_page_lock = threading.Lock()

print_queue = Queue()
log_file = open(LOG_FILE, "a+")


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


def get_page(url, snap, addr, access_info):
  """
  url: entire url of the page from wayback
  snap: (string) snapshot number yyyymmdd
  addr: address of the page in nytimes.com
  access_info:

  Returns: r_url, snap, addr, page if obtained else None
  """

  tries = 0
  code = None
  while (tries < MAX_TRIES):
    try:
      response = urlopen(url)
    except error.HTTPError as h:
      print_thread(
          'url: {} got HttpError, error: {}'.format(url, h), error=True)
      return None
    except error.URLError as u:
      print_thread('url: {} got URLError, error: {}'.format(url, u), error=True)
      return None
    except Exception as e:
      print_thread('url: {} got error, error: {}'.format(e), error=True)
      return None

    if (response.getcode() == 200):
      r_url = response.geturl()

      if url != r_url:
        # check whether response url is pointing to a valid page
        # one way is to check for yyyymmddhhmmss/ format in url
        r_snap = get_snapshot_number(r_url)

        # url will always have snap because url is added only if it has snap
        # (look at function traverse_page and when queue is loaded first time)

        if r_snap is None:
          print_thread('response url is different {}'.format(r_url))
          print_thread('snap:', snap, 'r_snap', r_snap)
          return None

        snap = r_snap[:8]
        snap_date = int(snap)
        # check whether redirected url's snapshot is before start date or after
        # only see if its after start date
        # TODO see if it has to be after cur snap
        if snap_date < access_info.start_date:
          print_thread("response url's snap is out of range {}".format(r_url))
          return None

        addr = get_page_addr(r_url, access_info.domain_name)
        if addr is None:
          print_thread('response url is invalid: {}'.format(r_url))
          return None

        u_addr = get_unique_addr(snap, addr)

        seen_page_lock.acquire()
        if u_addr in seen_pages:
          print_thread('response url is already seen: {}'.format(r_url))

        seen_pages.add(u_addr)

        seen_page_lock.release()

      try:
        page = response.read().decode('utf-8', 'ignore')
        return r_url, snap, addr, page
      except UnicodeDecodeError as e:
        print_thread(
            'error decoding page at url: {}, error: {}'.format(url, e),
            error=True)
        # input()
        return None
      except Exception as e:
        print_thread('error: {}'.format(e), error=True)
        return None

    code = response.getcode()
    tries += 1

  # log here about url and response
  print_thread("{}: response code: {}".format(url, code))
  return None


def traverse_page(url, snap, orig_addr, access_info, depth=None):
  """
  url: entire url of the page from wayback
  snap: (string) snapshot number yyyymmdd
  orig_addr: address of the page in nytimes.com
  access_info:
  depth:

  Returns: None
  """
  # url received from get_page may be different if page is redirected
  ret = get_page(url, snap, orig_addr, access_info)
  if ret is None:
    return

  url, snap, r_addr, page = ret

  is_proper_page, is_article, pub_date = access_info.get_page_info(page, url)
  print_thread(
      'page {} is_proper_page: {}, is_article: {}, pub_date: {}'.format(
          url, is_proper_page, is_article, pub_date))
  # input()

  if not is_proper_page:
    return

  if (is_proper_page and is_article) or (depth is not None and depth == 0):
    # look for article
    if not is_article:
      return

    # save article if appropriate
    # check for publication date
    if pub_date < access_info.start_date or pub_date > access_info.end_date:
      return

    # remove string after ? in address (they indicate sections)
    # TODO check here whether things after ? change pages
    r_addr = r_addr.split("?")[0]

    article_name = '{}_{}'.format(pub_date, r_addr)

    saved_page_lock.acquire()
    if article_name not in saved_pages:
      saved_pages.add(article_name)
      access_info.save_article(page, str(pub_date), r_addr, article_name)

    saved_page_lock.release()
    return

  if depth is None:
    depth = MAX_DEPTH_FROM_HOME

  # look at all the urls
  # add to list: url that are article with depth 0
  #              url that are other with depth depth - 1

  soup = BeautifulSoup(page, 'html5lib')

  all_as = soup.find_all('a', href=True)

  seen_page_lock.acquire()

  for a_tag in all_as:
    href = str(a_tag['href'])

    addr = get_page_addr(href, access_info.domain_name)

    snap_new = get_snapshot_number(href)
    if snap_new is None:
      continue

    snap_date = int(snap_new[:8])
    # TODO check if second condition will ever happen
    if snap_date < access_info.start_date or snap_date > access_info.end_date:
      continue

    if addr is not None:
      u_addr = get_unique_addr(snap_new[:8], addr)

    # check whether url is in the set using page specific url name
    if addr is None or u_addr in seen_pages:
      continue

    seen_pages.add(u_addr)
    url_queue.append((href, snap_new[:8], addr, depth - 1))

  seen_page_lock.release()


def crawl(access_info):
  while url_queue:
    href, snap, addr, depth = url_queue.popleft()
    print('traversing url: {}'.format(href))
    traverse_page(href, snap, addr, access_info, depth)


class MultipleCrawls(threading.Thread):
  def __init__(self, access_info):
    threading.Thread.__init__(self)
    self.access_info = access_info
    self.empty_count = 0

  def run(self):
    global empty_threads
    while True:
      seen_page_lock.acquire()
      if url_queue:
        seen_page_lock.release()
        if self.empty_count == 1:
          empty_threads -= 1
          self.empty_count = 0

        seen_page_lock.acquire()

        href, snap, addr, depth = url_queue.popleft()

        seen_page_lock.release()

        print_thread('traversing url: {}'.format(href))
        print('{}: traversing url: {}'.format(threading.current_thread().name,
                                              href))
        traverse_page(href, snap, addr, self.access_info, depth)
      else:
        seen_page_lock.release()
        if self.empty_count == 0:
          self.empty_count = 1
          empty_threads += 1
          if empty_threads >= MAX_THREADS:
            break


def save_article(page, pub_date, addr, article_name):
  """
  page: is an article
  pub_date: (string)
  addr:
  article_name
  """
  # save article

  y = pub_date[:4]
  m = pub_date[4:6]
  d = pub_date[6:]

  with open('./articles/{}'.format(article_name), 'w+') as f:
    # TODO write only the story of the page
    f.write(page)


# page: page on the web
# url
# Returns: whether it is nytimes page (true or false), whether it is article (true or false),
#          publication date (int yyyymmdd) (None or date)
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
    print_thread(title)

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
    print_thread('page {} is not proper'.format(url))
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
    time_tag = soup.find('div', class_='timestamp')
    if time_tag is not None:
      date = time_tag.string.split(":")[-1].strip()
      try:
        pub_date = datetime.strptime(date, '%B %d, %Y')
        pub_date = int(datetime.strftime(pub_date, '%Y%m%d'))
      except ValueError as e:
        print_thread('error parsing date {}'.format(e), error=True)
        pub_date = None

    if pub_date is None:
      meta_pdate_tag = soup.find('meta', attrs={'name': 'pdate'})
      if meta_pdate_tag is not None:
        pub_date = int(meta_pdate_tag['content'])

    if pub_date is None:
      is_article = False
      print_thread('{} is not article (cannot find pub date)'.format(url))

  if is_article:
    return is_proper_page, is_article, pub_date
  else:
    print_thread('url {} is not article'.format(url))
    return is_proper_page, is_article, None


def save_data_struc():
  with open("seen_pages.p", "wb") as f:
    pickle.dump(seen_pages, f)

  with open("url_queue.p", "wb") as f:
    pickle.dump(url_queue, f)

  with open("saved_pages.p", "wb") as f:
    pickle.dump(saved_pages, f)


def load_data_struc():
  global seen_pages, url_queue, saved_pages
  try:
    with open("seen_pages.p", "rb") as f:
      seen_pages = pickle.load(f)
      print(seen_pages)

    with open("url_queue.p", "rb") as f:
      url_queue = pickle.load(f)
      print(url_queue)

    with open("saved_pages.p", "rb") as f:
      saved_pages = pickle.load(f)
      print(saved_pages)

  except FileNotFoundError:
    print('data structures not yet pickled')
    seen_pages = set()
    url_queue = deque()
    saved_pages = set()


# snap: yyyymmdd
# addr: path of page
def get_unique_addr(snap, addr):
  return '{}_{}'.format(snap, addr)


def print_thread(msg, error=False):
  thread_name = threading.current_thread().name
  # print('{}: {}'.format(thread_name, msg))
  time = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")
  if error:
    print_queue.put('\nERROR\n{}_{}: {}\n'.format(thread_name, time, msg))
  else:
    print_queue.put('\n{}_{}: {}\n'.format(thread_name, time, msg))


def signal_handler(signal, frame):
  print('pressed CTRL-C')
  save_data_struc()

  while not print_queue.empty():
    log_file.write(print_queue.get())

  log_file.close()
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
    for snap, urls in nytimes_home_pages.items():
      u_addr = get_unique_addr(snap, '')
      if u_addr not in seen_pages:
        seen_pages.add(u_addr)
        url_queue.append((urls[-1], snap, '', MAX_DEPTH_FROM_HOME))
        # break

    threads = []
    for _ in range(MAX_THREADS):
      t = MultipleCrawls(nytimes_info)
      threads.append(t)

    printing_thread = PrintingThread(print_queue, log_file)
    threads.append(printing_thread)

    for t in threads:
      t.start()

    for t in threads:
      t.join()

    # crawl(nytimes_info)

  except Exception as e:
    print(e)
  finally:
    save_data_struc()