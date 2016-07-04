#!/usr/bin/env python

from redis import StrictRedis
from grab import Grab
import argparse
from datetime import datetime
import json

g = Grab()
url = "http://jizdenky.studentagency.cz"

redis_config = json.load(open('rconfig.json'))

class Studentagency(object):
    def __init__(self):
        self.redis = StrictRedis(**redis_config)
        g.go(url, method="GET")
        self.result = []
        self.city_dict = {}
        self.data = {
            "ide58_hf_0": "",
            "returnTicket": "radio17",
            "fromStation": 10204002,
            "departure:dateField": "25.8.16",
            "toStation": 17902020,
            "travellers": 0,
            "passengers:passengersView:0:tarif": 0,

        }

    def find_departure(self, src, dst, dep):
        self.data["departure"] = dep
        if not self.city_dict:
            self.create_dictionary()

        if src in self.city_dict:
            self.data["fromStation"] = self.city_dict[src]

        if dst in self.city_dict:
            self.data["toStation"] = self.city_dict[dst]

        g.go("https://jizdenky.studentagency.cz/?0-1.IFormSubmitListener-formPanel-searchPanel-form", post=self.data)

        url2 = g.response.url + "-1.IBehaviorListener.0-mainPanel-routesPanel&_=1467466117140"
        g.go(url2, headers={"X-Requested-With": "XMLHttpRequest"})

        for i in g.css_list(".routeSummary"):
            ary = {"arrival": i.cssselect(".col_arival")[0].text,
                   "free_seats": i.cssselect(".col_space")[0].text.strip(),
                   "price": i.cssselect(".col_price > span")[0].text.strip(u"\xa0CZK"),
                   "departure": i.cssselect(".col_depart")[0].text,
                   "fromStation": self.data["fromStation"],
                   "toStation": self.data["toStation"],
                   "date": self.data["departure:dateField"],
                   }

            self.result.append(ary)
        return self.result

    def make_key(self, row):
        date = datetime.strptime(row["date"], '%d.%m.%y').strftime('%y%m%d')
        return '{}_{}_{}_{}'.format(row["fromStation"], row["toStation"], date, row["departure"])

    def push_redis(self):
        for row in self.result:
            key = self.make_key(row)
            self.redis.set(key, {k: row[k] for k in ('arrival', 'free_seats', 'price')})

    def create_dictionary(self):
        city_dict = g.css_list(".ss-city")
        for i in city_dict:
            self.city_dict[i.text] = i.attrib.get("value")

        return self.city_dict

    def read_redis(self, start=None, end=None):
        p = self.redis.pipeline()
        res_ary = []
        if start and end:
            for i in range(int(start), int(end) + 1, 1):
                selected_keys = self.redis.keys(pattern='*_*_' + str(i) + '*')
                for key in selected_keys:
                    p.get(key)
                for h in p.execute():
                    h = Studentagency.eval_json(h)
                    res_ary.append(h)
            return res_ary

        else:
            all_keys = self.redis.keys(pattern='*_*2016*')
            for key in all_keys:
                p.get(key)
            return map(Studentagency.eval_json, p.execute())

    @staticmethod
    def eval_json(string):
        try:
            h = json.loads(string)
        except Exception as e:
            h = eval(string)
        return h


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=str, help="path to source")
    parser.add_argument("--to", type=str, help="path to to")
    parser.add_argument("--dpt", type=str, help="path to departure")
    args = parser.parse_args()

    SA = Studentagency()
    SA.find_departure(args.src, args.to, args.dpt)
    SA.push_redis()
