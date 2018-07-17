import json

from urllib.request import urlopen
from urllib import error

from .util import get_page_addr, get_snapshot_number, get_date_format, print_thread


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


def get_unique_addr(snap, addr):
  """
  snap: yyyymmdd
  addr: path of page

  Returns: the format to save address
  """

  return '{}_{}'.format(snap, addr)


def is_url_proper(url, r_url, access_info):
  if url != r_url:

    if not access_info.check_url(r_url):
      return False

    # check whether response url is pointing to a valid page
    # one way is to check for yyyymmddhhmmss/ format in url
    r_snap = get_snapshot_number(r_url)

    # url will always have snap because url is added only if it has snap
    # (look at function traverse_page and when queue is loaded first time)

    if r_snap is None:
      print_thread('response url is different {}'.format(r_url))
      print_thread('snap:', snap, 'r_snap', r_snap)
      return False

    snap = r_snap[:8]
    snap_date = int(snap)

    # check whether redirected url's snapshot is before start date or after
    # only see if its after start date
    # TODO see if it has to be after cur snap
    if snap_date < access_info.start_date:
      print_thread("response url's snap is out of range {}".format(r_url))
      return False

    addr = get_page_addr(r_url, access_info.domain_name)
    if addr is None:
      print_thread('response url is invalid: {}'.format(r_url))
      return False

  return True
