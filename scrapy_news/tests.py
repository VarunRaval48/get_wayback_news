from urllib.request import urlopen

from scrapy_news.spiders.newssite_util import nytimes_url, nytimes_page_info
from scrapy_news.spiders.util import get_page_addr, get_snapshot_number


def test_nytimes_url():
  true_tests = [
      'https://nytimes.com/pages/a/b/c.html',
      'https://www.nytimes.com/pages/a/b/c.html',
      'https://www.nytimes.com/2010/01/01/a.html',
      'https://www.nytimes.com/aponline/2010/01/01/a.html',
      'https://www.nytimes.com/aponline/2010/1/01/a.html',
      'https://www.nytimes.com/aponline/2010/1/1/a.html',
  ]

  false_tests = [
      'https://www.nytimes.com/pages', 'https://www.nytimes.com/201/1/1/a.html',
      'https://www.nytimes.com/interactive/a.html'
  ]

  print('testing test_nytimes_url')
  for test in true_tests:
    print(nytimes_url(test) == True)

  for test in false_tests:
    print(nytimes_url(test) == False)


def test_nytimes_page_info():

  print('testing nytimes_page_info')

  url = 'http://web.archive.org/web/20100101160117/http://nytimes.com/'
  response = urlopen(url)
  print(
      nytimes_page_info(response.read().decode('utf-8', 'ignore'), url)[1:] == (
          True, 20100101, False, None))

  url = 'http://web.archive.org/web/20091231025110/http://www.nytimes.com/pages/health/index.html'
  response = urlopen(url)
  print(
      nytimes_page_info(response.read().decode('utf-8', 'ignore'), url)[1:] == (
          True, 20091230, False, None))

  url = 'http://web.archive.org/web/20100105042000/http://www.nytimes.com:80/2010/01/01/world/asia/01khost.html?hp'
  response = urlopen(url)
  print(
      nytimes_page_info(response.read().decode('utf-8', 'ignore'), url)[1:] == (
          True, None, True, 20091231))

  url = 'http://web.archive.org/web/20091231034340/http://www.nytimes.com/glogin?URI=http://www.nytimes.com/2009/12/30/health/nutrition/30recipehealth.html&OQ=_rQ3D1Q26refQ3Dhealth&OP=67dc4632Q2FQ20pQ5EEQ20!)HQ7De))B5Q205ggPQ20-5Q20Q2FgQ20_Q5E@yB_Q20FnBeuBu)FQ20Q2FgeQ5EHumQ5E_Q5E@yB_X_BDy'
  response = urlopen(url)
  print(
      nytimes_page_info(response.read().decode('utf-8', 'ignore'), url)[1:] == (
          True, None, False, None))


def test_get_page_addr():
  domain = "nytimes.com"

  print('testing get_page_addr')

  print(
      get_page_addr("https://www.nytimes.com/pages/1.html", domain) ==
      'pages_1.html')
  print(
      get_page_addr("https://www.nytimes.com/2010/01/01/1.html", domain) ==
      '2010_01_01_1.html')
  print(
      get_page_addr("https://nytimes.com/2010/01/01/1.html", domain) ==
      '2010_01_01_1.html')

  print(get_page_addr("https://www.nytimes.com/", domain) == '')
  print(get_page_addr("https://www.nytimes.com", domain) == '')

  print(get_page_addr("https://www.nytimes.com:80/", domain) == '')
  print(get_page_addr("https://www.nytimes.com:80", domain) == '')

  print(get_page_addr("https://www.", domain) is None)


def test_get_snapshot_number():

  print('testing get_snapshot_number')

  print(
      get_snapshot_number(
          'https://web.archive.org/web/20100101000000/https://nytimes.com') ==
      '20100101000000')

  print(
      get_snapshot_number(
          'https://web.archive/web/20100101000000/https://nytimes.com') is None)

  print(
      get_snapshot_number(
          'https://web.archive.org/web/20100101000000id_/https://nytimes.com')
      is None)

  print(
      get_snapshot_number(
          'https://web.archive.org/web/20100101000000*/https://nytimes.com') is
      None)


if __name__ == '__main__':
  test_nytimes_url()
  test_get_page_addr()
  test_get_snapshot_number()
  test_nytimes_page_info()