import time
import json
from urllib.request import urlopen

from bs4 import BeautifulSoup


MAX_DEPTH_FROM_HOME = 2

class AccessInfo:
  """
  year: year to search for
  month: month to start from
  dat: day of month to start from
  no_days: number of days from day to search for
  url:
  get_page_info: method to get info about page
  save_article: method to save article
  """

  def __init__(self, year, month, day, no_days, url):
    self.year = year
    self.month = month
    self.day = day
    self.no_days = no_days

    self.url = url

    # self.is_proper_page = is_proper_page
    # self.is_article = is_article
    # get_pub_date

    self.get_page_info = page_info
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
  id_dict = {}
  for m in range(int(access_info.month) - 1, len(data)):
    cur_day = 1
    for week in data[m]:
      for day in week:
        # check for empty and None dictionary
        # check if we reached the day we want to start from
        if day and (seen_days + 1) >= access_info.day:
          id_dict['{}_{}_{}'.format(access_info.year, (m + 1), cur_day)] = [
              home_page_url.format(x) for x in day['ts']
          ]

        if day is not None:
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


def traverse_page(url, access_info, depth=None):
  if depth is not None and depth == 0:
    # look for article

    # check whether this page is article

    # save article

  if depth is None:
    depth = MAX_DEPTH_FROM_HOME

    # look at all the urls
    # add to list: url that are article with depth 0
    #              url that are other with depth depth - 1


# page: is an article
def save_article(page):
  # save article


# page: page on the web
# Returns: whether it is nytimes page, whether it is article, publication date 
def nytimes_page_info(page):



if __name__ == '__main__':

  year, month, day, url, no_days = "2010", "01", "01", "http://nytimes.com", 31
  nytimes_info = AccessInfo(year, month, day, no_days, url)

  nytimes_home_pages = get_home_page_urls(nytimes_info)
