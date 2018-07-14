import os
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
from util import PrintingThread, MyDeque, LIFO_QUEUE, FIFO_QUEUE

# depth to search for
MAX_DEPTH_FROM_HOME = 2

# maximum number of tries when response code is not 200
MAX_TRIES = 5

# number of threads to run
MAX_THREADS = 7

TYPE_QUEUE = LIFO_QUEUE

# path to save the log file
LOG_FILE = './logs'

empty_threads = 0

seen_pages = set()

# saved pages is needed because different url may be pointing to same page
# because of different snapshots
# pages are remembered using publication date
saved_pages = set()

# format of queue is (url, snapshot (string), page_address, depth)
url_queue = MyDeque(type_queue=TYPE_QUEUE)

seen_page_lock = threading.Lock()
saved_page_lock = threading.Lock()

print_queue = Queue()
log_file = open(LOG_FILE, "a+")


def signal_handler(signal, frame):
  print('pressed CTRL-C')
  save_data_struc()

  while not print_queue.empty():
    log_file.write(print_queue.get())

  log_file.close()
  sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


class AccessInfo:
  """
  year: year to search for
  month: month to start from
  day: day of month to start from
  no_days: number of days from day to search for
  end_date: string in format yyyymmdd
  url:
  domain_name:
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

  Returns: r_url (response url), snap, addr, page if obtained else None
  """

  tries = 0
  code = None
  response = None
  while (tries < MAX_TRIES):
    try:
      print_thread("urlopen {}".format(url), debug=True)
      response = urlopen(url)
    except error.HTTPError as h:
      print_thread(
          'url: {} got HttpError, error: {}'.format(url, h), error=True)
      return None
    except error.URLError as u:
      print_thread('url: {} got URLError, error: {}'.format(url, u), error=True)
    except Exception as e:
      print_thread('url: {} got error, error: {}'.format(url, e), error=True)
    finally:
      tries += 1
      if response is not None:
        code = response.getcode()

    if (response is not None and code == 200):
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

        with seen_page_lock:
          if u_addr in seen_pages:
            print_thread('response url is already seen: {}'.format(r_url))

          seen_pages.add(u_addr)

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

  # log here about url and response
  print_thread("{}: response code: {}".format(url, code), error=True)
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

  soup, is_proper_page, pub_date_home, is_article, pub_date = access_info.get_page_info(
      page, url)
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
    # check for publication dateget_page_info
    if pub_date < access_info.start_date or pub_date > access_info.end_date:
      return

    # remove string after ? in address (they indicate sections)
    # TODO check here whether things after ? change pages
    r_addr = r_addr.split("?")[0]

    article_name = '{}_{}'.format(pub_date, r_addr)

    with saved_page_lock:
      if article_name not in saved_pages:
        saved_pages.add(article_name)
        access_info.save_article(page, str(pub_date), r_addr, article_name)

    return

  if depth is None:
    depth = MAX_DEPTH_FROM_HOME

  if pub_date_home is not None:
    if pub_date_home < access_info.start_date or pub_date_home > access_info.end_date:
      return

  # look at all the urls
  # add to list: url that are article with depth 0
  #              url that are other with depth depth - 1

  # soup = BeautifulSoup(page, 'html5lib')

  all_as = soup.find_all('a', href=True)

  with seen_page_lock:

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


def crawl(access_info):
  while url_queue.length() > 0:
    href, snap, addr, depth = url_queue.pop()
    print('traversing url: {}'.format(href))
    traverse_page(href, snap, addr, access_info, depth)


class MultipleCrawls(threading.Thread):
  """
  access_info:

  """

  def __init__(self, access_info):
    threading.Thread.__init__(self)
    self.access_info = access_info
    self.empty_count = 0

  def run(self):
    # TODO empty_threads is a global variable, it needs a lock also
    # TODO change how to know crawler is done
    global empty_threads
    while True:
      try:
        seen_page_lock.acquire()
        if url_queue.length() > 0:
          if self.empty_count == 1:
            empty_threads -= 1
            self.empty_count = 0

          href, snap, addr, depth = url_queue.pop()

          seen_page_lock.release()

          print_thread('traversing url: {}'.format(href), debug=True)
          traverse_page(href, snap, addr, self.access_info, depth)
        else:
          if self.empty_count == 0:
            self.empty_count = 1
            empty_threads += 1

          if empty_threads >= MAX_THREADS:
            seen_page_lock.release()
            break
          seen_page_lock.release()
      except Exception as e:
        print_thread(e, error=True)


def save_article(page, pub_date, addr, article_name):
  """
  page: is an article
  pub_date: (string)
  addr:
  article_name:

  """
  # save article

  # print(article_name)
  # os.makedirs(os.path.dirname(article_name), exist_ok=True)
  with open('./articles/{}'.format(article_name), 'w+') as f:
    # TODO write only the story of the page
    f.write(page)


def nytimes_page_info(page, url):
  """
  page: page on the web
  url:

  Returns: soup contents, whether it is nytimes page (true or false), 
           if not article publication date of page (int yyyymmdd) (None or date),
           whether it is article (true or false), 
           publication date of article (int yyyymmdd) (None or date)
  """

  is_proper_page = False
  pub_date_home = None
  is_article = False
  pub_date = None

  soup = BeautifulSoup(page, "lxml")

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
    return soup, False, None, False, None

  # check whether page is article
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

  # if it is an article, find publication date, if publication date is not found,
  # it is not article
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

    # make another try
    if pub_date is None:
      meta_pdate_tag = soup.find('meta', attrs={'name': 'pdate'})
      if meta_pdate_tag is not None:
        pub_date = int(meta_pdate_tag['content'])

    if pub_date is None:
      is_article = False
      print_thread('{} is not article (cannot find pub date)'.format(url))

  # check publish date of home page if it is proper page and not article
  if not is_article:
    id_time = soup.find("div", id="time")
    if id_time is not None:
      id_time_contents = id_time.contents
      if id_time_contents:
        p_tag = id_time_contents[0]
        p_contents = p_tag.contents
        if p_contents:
          date = p_contents[0]
          date = date.strip()
          try:
            pub_date_home = datetime.strptime(date, "%A, %B %d, %Y")
            pub_date_home = int(datetime.strftime(pub_date_home, '%Y%m%d'))
          except ValueError as e:
            print_thread('error parsing date {}'.format(e), error=True)
            pub_date_home = None

  if is_article:
    return soup, is_proper_page, pub_date_home, is_article, pub_date
  else:
    print_thread('url {} is not article'.format(url))
    return soup, is_proper_page, pub_date_home, is_article, None


def save_data_struc():
  with open("seen_pages.p", "wb") as f:
    pickle.dump(seen_pages, f)

  with open("url_queue.p", "wb") as f:
    pickle.dump(url_queue.deque, f)

  with open("saved_pages.p", "wb") as f:
    pickle.dump(saved_pages, f)


def load_data_struc():
  global seen_pages, url_queue, saved_pages
  try:
    with open("seen_pages.p", "rb") as f:
      seen_pages = pickle.load(f)
      print('number of seen pages', len(seen_pages))

    with open("url_queue.p", "rb") as f:
      url_queue = MyDeque(deq=pickle.load(f))
      print('length of url queue', url_queue.length())

    with open("saved_pages.p", "rb") as f:
      saved_pages = pickle.load(f)
      print('number of saved pages', len(saved_pages))

  except FileNotFoundError:
    print('data structures not yet pickled')
    seen_pages = set()
    url_queue = MyDeque(type_queue=TYPE_QUEUE)
    saved_pages = set()


def get_unique_addr(snap, addr):
  """
  snap: yyyymmdd
  addr: path of page

  Returns: the format to save address
  """

  return '{}_{}'.format(snap, addr)


def print_thread(msg, error=False, debug=False):
  thread_name = threading.current_thread().name
  # print('{}: {}'.format(thread_name, msg))

  time = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")
  # print('number of articles saved: {}'.format(len(saved_pages)))

  if error:
    p_msg = '\nERROR\n{}_{}: {}\n'.format(thread_name, time, msg)
    print(p_msg)
    print_queue.put(p_msg)
  else:
    p_msg = '\n{}_{}: {}\n'.format(thread_name, time, msg)
    if debug:
      print(p_msg)
    print_queue.put(p_msg)


def start_crawl(access_info):
  home_pages = get_home_page_urls(access_info)
  # print(home_pages)

  load_data_struc()

  threads = []
  for _ in range(MAX_THREADS):
    t = MultipleCrawls(access_info)
    threads.append(t)

  printing_thread = PrintingThread(print_queue, saved_pages, log_file)
  threads.append(printing_thread)

  try:
    for snap, urls in home_pages.items():
      u_addr = get_unique_addr(snap, '')
      if u_addr not in seen_pages:
        seen_pages.add(u_addr)
        url_queue.append((urls[-1], snap, '', MAX_DEPTH_FROM_HOME))

    for t in threads:
      t.start()

  except Exception as e:
    print(e)
  finally:
    for t in threads:
      t.join()

    log_file.close()
    save_data_struc()


if __name__ == '__main__':

  year, month, day = 2010, 1, 1
  url, domain_name = "http://www.nytimes.com/", "nytimes.com"
  no_days = 1
  end_date = 20100101
  nytimes_info = AccessInfo(year, month, day, no_days, end_date, url,
                            domain_name, nytimes_page_info, save_article)

  start_crawl(nytimes_info)