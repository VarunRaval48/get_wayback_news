import json

from urllib.request import urlopen

from util import get_page_addr, get_snapshot_number, get_date_format


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
