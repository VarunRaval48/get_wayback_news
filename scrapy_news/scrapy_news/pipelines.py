# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html


class ScrapyNewsPipeline(object):
  def process_item(self, item, spider):
    return item


class SavepagePipeline(object):
  def __init__(self):
    self.saved_pages = set()

  def process_item(self, item, spider):

    pub_date = item['pub_date']
    access_info = item['access_info']
    r_addr = item['addr']
    page = item['page']

    # save article if appropriate
    # check for publication dateget_page_info
    if pub_date < access_info.start_date or pub_date > access_info.end_date:
      return

    # remove string after ? in address (they indicate sections)
    # TODO check here whether things after ? change pages
    r_addr = r_addr.split("?")[0]

    article_name = '{}_{}'.format(pub_date, r_addr)

    if article_name not in self.saved_pages:
      self.saved_pages.add(article_name)
      access_info.save_article(page, str(pub_date), r_addr, article_name)