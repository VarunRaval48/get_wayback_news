import os
import sys
import time

import scrapy

from .util import get_date_format, get_page_addr, get_snapshot_number
from .wayback_util import get_home_page_urls, get_unique_addr, is_url_proper
from .newssite_util import nytimes_page_info, save_article, AccessInfo, nytimes_url
from ..items import PageItem


class NytimesSpider(scrapy.Spider):
  name = "articles"
  year, month, day = 2010, 1, 1
  url, domain_name = "http://www.nytimes.com/", "nytimes.com"
  no_days = 31
  end_date = 20100131

  def __init__(self, *args, **kwargs):
    scrapy.Spider.__init__(self, *args, **kwargs)
    self.access_info = AccessInfo(
        NytimesSpider.year, NytimesSpider.month, NytimesSpider.day,
        NytimesSpider.no_days, NytimesSpider.end_date, NytimesSpider.url,
        NytimesSpider.domain_name, nytimes_page_info, nytimes_url, save_article)
    self.seen_pages = set()

  def start_requests(self):
    home_pages = get_home_page_urls(self.access_info)
    for snap, urls in home_pages.items():
      u_addr = get_unique_addr(snap, '')
      if u_addr not in self.seen_pages:
        self.seen_pages.add(u_addr)
        yield scrapy.Request(url=urls[-1], callback=self.parse)

  def parse(self, response):
    url = response.request.url
    r_url = response.url
    snap = get_snapshot_number(r_url)
    addr = get_page_addr(r_url, self.access_info.domain_name)

    if is_url_proper(url, r_url, self.access_info):
      if url != r_url:
        self.seen_pages.add(get_unique_addr(snap, addr))

      page = response.body.decode('utf-8', 'ignore')
      soup, is_proper_page, pub_date_home, is_article, pub_date = \
        self.access_info.get_page_info(page, r_url)

      if not is_proper_page:
        return

      if is_article:
        yield PageItem(
            url=r_url,
            snap=snap,
            addr=addr,
            page=page,
            pub_date=pub_date,
            access_info=self.access_info)
      else:
        if pub_date_home is not None:
          if pub_date_home < self.access_info.start_date or pub_date_home > self.access_info.end_date:
            return

        all_as = soup.find_all('a', href=True)

        for a_tag in all_as:
          href = str(a_tag['href'])

          if not self.access_info.check_url(href):
            continue

          addr = get_page_addr(href, self.access_info.domain_name)

          snap_new = get_snapshot_number(href)
          if snap_new is None:
            continue

          snap_date = int(snap_new[:8])

          # TODO check if second condition will ever happen
          if snap_date < self.access_info.start_date or snap_date > self.access_info.end_date:
            continue

          if addr is not None:
            u_addr = get_unique_addr(snap_new[:8], addr)

          # check whether url is in the set using page specific url name
          if addr is None or u_addr in self.seen_pages:
            continue

          self.seen_pages.add(u_addr)
          yield scrapy.Request(href, callback=self.parse)
