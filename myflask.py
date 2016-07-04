#!/usr/bin/env python

from studentagency import Studentagency
from flask import Flask
from json import dumps, load
from threading import Thread
from time import sleep

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True


class ConfigLoader(Thread):
    def __init__(self):
        super(ConfigLoader, self).__init__()
        self.cfg = load(open('config.json'))

    def run(self):
        while True:
            self.cfg = load(open('config.json'))
            sleep(3)


agency = Studentagency()
config_loader = ConfigLoader()
config_loader.start()


@app.route('/<src>/<dst>/<date>', methods=['GET'])
def get_data(src, dst, date):
    return dumps(agency.find_departure(src, dst, date))


@app.route('/all', methods=['GET'])
def get_all():
    print config_loader.cfg
    return apply_config(agency.read_redis())


@app.route('/<start>/<end>', methods=['GET'])
def get_fromto(start, end):
    return apply_config(agency.read_redis(start, end))


def apply_config(data):
    cfgfile = config_loader.cfg
    if cfgfile["status"] == 0:
        return "api currently offline"
    else:
        try:
            for i in data:
                i["price"] = config_loader.cfg["margin"] * int(i["price"])
        except TypeError as e:
            pass

    return dumps(data)
    # return data


if __name__ == '__main__':
    app.debug = True
    app.run()
