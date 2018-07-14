import pickle
import threading
from datetime import datetime

import threading

from collections import deque
from queue import Queue
import queue as queue

LIFO_QUEUE = 'LIFO'
FIFO_QUEUE = 'FIFO'

print_queue = Queue()


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

  return url[index + 1:].replace('/', '_')


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


def read_pickle(pickle_file):
  with open(pickle_file, "rb") as f:
    loaded = pickle.load(f)
    # print(loaded)
    print(len(loaded))


class PrintingThread(threading.Thread):
  def __init__(self, queue, saved_pages, file):
    threading.Thread.__init__(self)
    self.queue = queue
    self.saved_pages = saved_pages
    self.file = file
    self.stop = False

  def run(self):
    while True and not self.stop:
      print('number of saved pages: {}'.format(len(self.saved_pages)))
      try:
        self.file.write(self.queue.get(timeout=10))
      except queue.Empty:
        print('Queue empty')

  def stop_thread(self):
    self.stop = True


class MyDeque():
  def __init__(self, type_queue=LIFO_QUEUE, deq=None):
    if deq is None:
      self.deque = deque()
    else:
      self.deque = deq

    if type_queue == LIFO_QUEUE:
      self.append = self.deque.appendleft
      self.pop = self.deque.popleft
    else:
      self.append = self.deque.append
      self.pop = self.deque.popleft

  def length(self):
    return len(self.deque)


def print_thread(msg, error=False, debug=True):
  thread_name = threading.current_thread().name
  # print('{}: {}'.format(thread_name, msg))

  time = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")
  # print('number of articles saved: {}'.format(len(saved_pages)))

  if error:
    p_msg = '\nERROR\n{}_{}: {}\n'.format(thread_name, time, msg)
    print(p_msg)
    print_queue.put(p_msg)
  else:
    p_msg = '\n{}_{}: {}\n'.format(thread_name, time, msg)
    if debug:
      print(p_msg)
    print_queue.put(p_msg)


if __name__ == '__main__':
  # url = 'https://www.nytimes.com/a/1/2.html'
  # print(get_page_addr(url, 'nytimes.com'))

  read_pickle('seen_pages.p')