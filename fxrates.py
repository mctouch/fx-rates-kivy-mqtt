from mosquitto import Mosquitto
from time import sleep
import urllib2
from xml.dom.minidom import parseString
from argparse import ArgumentParser


parser = ArgumentParser()

parser.add_argument('hostname',
                    #name='hostname',
                    help='mosquitto server',
                    default='localhost',
                    type=str)

parser.add_argument('port',
                    #name='port',
                    help='port of the mosquitto server',
                    default=1883,
                    type=int)


SOURCE = 'http://rates.fxcm.com/RatesXML'
dates = {}


def getFXRate(mq):
    file = urllib2.urlopen(SOURCE)
    data = file.read()
    file.close()

    dom = parseString(data)
    rate = dom.getElementsByTagName('Rate')

    for node in rate:
        get = node.getElementsByTagName
        symbol = node.getAttribute('Symbol')

        collection = [
            get('Bid'),
            get('Ask'),
            get('High'),
            get('Low'),
            get('Direction'),
            get('Last'),
        ]

        message = '/'.join(
            (
                c[0].childNodes[0].nodeValue
                for c in collection
            )
        ).encode('utf-8')

        print message
        if dates.get(symbol, None) != collection[-1]:
            mq.publish(
                'rates/%s' % symbol,
                message,
                qos=1,
                retain=True)
            dates[symbol] = collection[-1]


if __name__ == '__main__':
    args = parser.parse_args()
    mq = Mosquitto('fxrates')
    mq.connect(args.hostname, args.port, 60)
    try:
        while True:
            sleep(.1)
            getFXRate(mq)
    except KeyboardInterrupt:
        print 'closing...'
        mq.disconnect()
