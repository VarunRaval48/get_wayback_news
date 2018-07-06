def get_date_format(y, m, d):
  """
  Returns: date in yyyymmdd format
  """

  s_m = str(m)
  if m < 10:
    s_m = '0' + s_m

  s_d = str(d)
  if d < 10:
    s_d = '0' + s_d

  return '{}{}{}'.format(y, s_m, s_d)


# url: the url containing the domain
def get_page_addr(url, domain):
  index = url.find(domain)

  if index == -1:
    return None

  index += len(domain)

  # move index to the nearest '/'
  while (index < len(url) and url[index] != '/'):
    index += 1

  return url[index + 1:].replace('/', '_').split("?")[0]


def get_snapshot_number(url):
  prefix = 'web.archive.org/web/'
  index = url.find(prefix)
  if index == -1:
    return None

  index += len(prefix)

  # get string in place of yyyymmsshhmmss
  snap_num = url[index:index + 14]
  if snap_num.isdecimal() and url[index + 14] == '/':
    return snap_num
  else:
    return None


if __name__ == '__main__':
  url = 'https://www.nytimes.com/a/1/2.html'
  print(get_page_addr(url, 'nytimes.com'))