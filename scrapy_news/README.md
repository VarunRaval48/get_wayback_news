
# Get Wayback news using Scrapy
Uses [Middleware by sangaline](https://github.com/sangaline/scrapy-wayback-machine)

This is a scrapy project. This project searches for news articles of a given domain for a date range.

To run this project, go to scrapy_news/spiders and run command `scrapy crawl articles`.

Update the class variables of class NytimesSpider to set the date range.

For this project, I have used [middle-ware of scrapy for Wayback machine](https://github.com/sangaline/scrapy-wayback-machine).
This middle-ware converts links to the wayback machine url by itself.