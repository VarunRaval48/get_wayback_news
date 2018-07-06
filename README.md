
# Get WayBack News

`crawl.py` (python3) contains the crawler to search for articles of given domain on [Wayback Machine](https://web.archive.org)

The task of program `crawl.py` is to search for articles on any given news website within any given date range in the past. For example, search for news articles appeared on website nytimes.com during London Olympics 2012 (27 July to 12 August 2012).

### To search for articles of a given domain:
  1. Initialize global variables at the top of file `crawl.py` (variables in capital)
  2. Make an instance of class `AccessInfo` with required information
  3. Pass that object of `AccessInfo` to the method `start_crawl`
  4. AccessInfo asks for a method that parses given html page and provide page info (Look at `nytimes_page_info`). Reason for that is given below.
  5. Run the file using `path-to-python3-installation crawl.py`. (I have tested it on Linux)

### Output:
  1. Messages will be printed on the standard output regarding url being traversed and any errors
  2. All the logs will be printed in the provided log file
  3. All the articles will be saved in articles directory in current folder
  4. The name of the article will start with its publication date *yyyymmdd* followed by path of the page in the url of the page (path after domain name). Look for an example in **articles** directory.
  5. The articles are stored in form of their default html page. It is easy to write a function to extract only story content once we know that a page is an article. In addition to that, there can be other useful links on that page also like links to related pages, or links to images.
  6. When crawler shuts down by sending singal (CTRL-C) or because queue of url is empty, it saves the current state of the crawler. Current state of the crawler includes the pages that are seen, the pages that are saved and the current url queue. The next time when crawler runs, and these saved files are present, the crawler uses them to initialize data structures.

### About Crawler:

Wayback machine stores snapshots of any given website on any given day in the past.

Provided a domain name and a date range, we can have all snapshots of given domain taken by Wayback machine on given date range (look at `get_home_page_urls` method)

I have used [Beautifulsoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) to parse html page.
Given a home page (snapshot of home page of domain name), I look at all the `a` tags and extract urls and maintain a queue of the urls to request.

Task to detect whether a page is an article is different for each domain. For example, for articles on nytimes.com, almost all the articles has `meta` tag with attributes `name=PT` and `content=Article`. For theguardian.com, this may be different. Hence, class `AccessInfo` asks for a methods that identifies whether a page is a proper page, is article and publication date of the article (if an article). Look at method `nytimes_page_info` for an example.

Similarly, task to look for story content is also different for different domains. For nytimes.com, one can look for string in `p` tag within `div id='articleBody'` tag. This task is not included in `crawl.py`. This task can be done as a different process to reduce the overhead.

### Results:
I ran this crawler on nytimes.com for 5 hours for date range 1 January 2010 - 31 January 2010, and retrieved 2084 articles. I stopped the crawler after this and pickled the data structures. One can run this crawler from the current state and can find more articles.


### Uses of this crawler:
  1. News article of a country represent the view of that country. Also, news articles during a major event like G7 summit, in addition to what happened during the summit, also reflect what are the countries's views for other countries. Some news also contain people's opinions about events about to happen. Hence, we can analyze the news articles of different countries that are published before, during and after a major politics event and give a summary of that country's views on that topic.
  2. As a training set for **summarization** tool. Links to all the articles that are stories are present in a top level page. This top level page has a short description of this article with a title. This crawler can be modified to retrieve title and short description of the articles. Then, it can be used as a dataset for summarization tool. 
  3. The topic of the article can also be identified from the article url and meta information. Hence, one can generate dataset of articles and their topics. This can be used to categorize new articles.
  4. Most of the articles also contain links to *related articles*. The articles may not be related by topics but also by a place described in that article, or a person in that article. One can use this information to train a model that searches of similar articles for a given article from a given pool of articles. So, instead of human assigning similar articles to a given article, this task can be automated.