import re
from bs4 import BeautifulSoup

from datetime import datetime

from .util import get_date_format, print_thread


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
               get_page_info, check_url, save_article):
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

    self.check_url = check_url


def nytimes_url(url):
  domain = "nytimes.com"
  accepted_sufs = ["pages/"]

  index = url.find(domain)
  if index == -1:
    return False

  while (index < len(url) and url[index] != '/'):
    index += 1

  if index + 1 >= len(url):
    return True

  path = url[index + 1:]
  for s in accepted_sufs:
    if path[:len(s)] == s:
      return True

  regexp_pre = ["aponline/"]
  for s in regexp_pre:
    if path[:len(s)] == s:
      path = path[len(s):]
      break

  regexp = r'\d{4}/\d{1,2}/\d{1,2}/*'
  if re.match(regexp, path):
    return True
  else:
    return False


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
    id_time = soup.find("div", id="date")
    if id_time is not None:
      p_tag = id_time.find('p')
      if p_tag:
        p_contents = p_tag.contents
        if p_contents:
          date = p_contents[0]
          if date is not None:
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
