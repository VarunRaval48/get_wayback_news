# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ScrapyNewsItem(scrapy.Item):
  # define the fields for your item here like:
  # name = scrapy.Field()
  pass


class PageItem(scrapy.Item):
  url = scrapy.field()
  snap = scrapy.field()
  addr = scrapy.field()
  page = scrapy.field()
  pub_date = scrapy.field()
  access_info = scrapy.field()
