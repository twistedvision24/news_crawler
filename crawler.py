#!/usr/bin/python
import feedparser
import urllib2
import re
import sys
import signal
import cmd
import os
import webbrowser
from HTMLParser import HTMLParser
from pymongo import MongoClient
from urllib2 import HTTPError

def signal_handler(signal, frame):
    print('Ctrl+C caught')
    if os.path.isfile('article.html'):
        os.remove('article.html')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


class news_crawler(cmd.Cmd):
    search = False
    prompt = 'news_crawler>'
    art_list = []
    intro = """\nBy default the title and description is searched.
To change this behavior use `set search` to search the article.
Beware this can return articles that are unrelated due to adds or other non-article content.\n"""
    def get_db(self):
        client = MongoClient()
        db = client.cnn
        return db

    def emptyline(self):
        pass

    def get_rss_url(self, line):
        if 'cnn' in line:
            return "http://rss.cnn.com/rss/cnn_world.rss"
        elif "bbc" in line:
            return "http://feeds.bbci.co.uk/news/rss.xml?edition=int"
        elif "reuters" in line:
            return "http://www.reuters.com/tools/rss"
        else:
            return "http://rss.cnn.com/rss/cnn_world.rss"

    def do_update(self, line):
        """update
        updated the db with new articles and avoids duplicates"""
        d_filter = re.compile('.\.')
        url = self.get_rss_url(line)
        content = feedparser.parse(url)
        db = self.get_db()
        for entry in content['entries']:
            a = {}
            a['title'] = entry['title']
            try:
                response = urllib2.urlopen(entry['link'])
                a['article'] = response.read()
                a['description'] = entry['description'].split('.')[0]
                found = db.articles.find_one({"title": a['title']})
                if not found:
                    db.articles.insert(a)
                else:
                    print 'article with same title found'
            except HTTPError:
                pass

    def do_find(self, search_term):
        """find [search_term]
        looks for articles with the search_term in the title"""
        num = 0
        self.art_list = []
        db = self.get_db()
        _filter = re.compile('.'+search_term+'.', re.IGNORECASE)
        arts = db.articles.find({"title": _filter})
        for article in arts:
            print "[" + str(num) + "]: " + article['title']
            self.art_list.append(article['title'])
            num += 1

        helper_list = self.find_helper2(search_term, db, _filter)
        if self.search:
            helper_list2 = self.find_helper(search_term, db, _filter)
            helper_set = set(helper_list + helper_list2)
            helper_list = list(helper_set)

        for t in helper_list:
            if t not in self.art_list:
                print "[" + str(num) + "]" + str(t)
                self.art_list.append(t)
                num += 1

    def find_helper(self, search_term, db, filt):
        helper_list = []
        arts = db.articles.find({"article": filt})
        for article in arts:
            helper_list.append(article['title'])
        return helper_list
        
    def find_helper2(self, search_term, db, filt):
        helper_list = []
        arts = db.articles.find({"description": filt})
        for article in arts:
            helper_list.append(article['title'])
        return helper_list

    def do_test_find_helper(self, search_term):
        db = self.get_db()
        _filter = re.compile('.'+search_term+'.', re.IGNORECASE)
        self.find_helper(search_term, db, _filter)

    def do_open(self, title):
        """open [full title] or open [article number from search]
        opens the specified article in your default browser"""
        try:
            t = int(title)
            title = t
        except ValueError:
            pass
        if type(title) == int:
            title = self.art_list[title]

        print 'opening: ', title
        db = self.get_db()
        entry = db.articles.find_one({"title": title}, {"_id":0, "article":1})
        f = open('article.html', 'w')
        f.write(entry['article'].encode('utf-8'))
        f.close()
        path = "file://" + os.getcwd() + '/article.html'
        webbrowser.open(path)

    def do_set(self, option):
        """set [option]
           toggles an option on or off"""
        if 'search' in option:
            self.search = True if not self.search else False

    def do_options(self, option):
        """options [option]
           show options current setting"""
        if 'search' in option:
            print "search = " + str(self.search)

    def do_count(self, line):
        """count
        gives count of how many articles are in the database"""
        db = self.get_db()
        print db.articles.count()

    def do_EOF(self, line):
        print ""
        self.do_exit(line)

    def do_quit(self, line):
        """quit
        exits this shell"""
        self.do_exit(line)

    def do_exit(self, line):
        """quit
        exits this shell"""
        if os.path.isfile('article.html'):
            os.remove('article.html')
        exit(0)


if __name__ == "__main__":
    news_crawler().cmdloop()
