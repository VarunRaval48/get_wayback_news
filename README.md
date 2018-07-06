
# Get WayBack News

`crawl.py` contains the crawler to search for articles of given domain on [Wayback Machine](https://web.archive.org)

The task of program `crawl.py` is to search for articles on any given news website within any given date range in the past. For example, search for news articles appeared on website nytimes.com during London Olympics 2012 (27 July to 12 August 2012).

### To search for articles of a given domain
  1. Initialize global variables at the top of file `crawl.py` (variables in capital)
  2. Make an instance of class `AccessInfo` with required information
  3. Pass that object of `AccessInfo` to the method `start_crawl`
  4. AccessInfo asks for a method that parses given html page and provide page info (Look at `nytimes_page_info`). Reason for that is given below.

### Output:
  1. Messages will be printed on the standard output regarding url being traversed and any errors
  2. All the logs will be printed in the provided log file
  3. All the articles will be saved in articles directory in current folder
  4. The name of the article will start with its publication date *yyyymmdd* followed by path of the page in the url of the page (path after domain name). Look for an example in **articles** directory.
  5. When crawler shuts down by sending singal (CTRL-C) or because queue of url is empty, it saves the current state of the crawler. Current state of the crawler includes the pages that are seen, the pages that are saved and the current url queue. The next time when crawler runs, and these saved files are present, the crawler uses them to initialize data structures.

### About Crawler:

Wayback machine stores snapshots of any given website on any given day in the past.

Provided a domain name and a date range, we can have all snapshots of given domain taken by Wayback machine on given date range (look at `get_home_page_urls` method)

I have used [Beautifulsoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) to parse html page.
Given a home page (snapshot of home page of domain name), I look at all the `a` tags and extract urls and maintain a queue of the urls to request.

Task to detect whether a page is an article is different for each domain. For example, for articles on nytimes.com, almost all the articles has `meta` tag with attributes `name=PT` and `content=Article`. For theguardian.com, this may be different. Hence, class `AccessInfo` asks for a methods that identifies whether a page is a proper page, is article and publication date of the article (if an article). Look at method `nytimes_page_info` for an example.

### Results
I ran this crawler on nytimes.com for 7 hours for date range 1 January 2010 - 31 January 2010, and retrieved 2084 articles. I shutdown the crawler after this and pickled the data structures. One can run this crawler from the current state and can find more articles.