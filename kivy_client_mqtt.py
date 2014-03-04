from kivy.app import App
#from kivy.graphics import Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridview import GridView, GridAdapter, GridCell, GridRow
from kivy.lang import Builder
from kivy.properties import ObjectProperty, ListProperty
from kivy.clock import Clock
from random import randint
from mosquitto import Mosquitto
from argparse import ArgumentParser
import time


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

kv = '''
RootWidget:
    orientation: 'vertical'
    textbox: textbox
    container: container
    ScrollView:
        id: container

    BoxLayout:
        orientation: 'vertical'
        TextInput:
            id: textbox
            readonly: True

        TextInput:
            on_text_validate:
                app.send(self.text)
                self.text = ''

            id: root.input

            size_hint_y: None
            #height: self.texture_size[1]
            multiline: False
            height: 100
'''


class RootWidget(BoxLayout):
    textbox = ObjectProperty(None)
    followed = ListProperty([])
    datasource = ObjectProperty(None)
    container = ObjectProperty(None)

def connect_cb(*args):
    print('connected', args)

def subscribe_cb(*args):
    print('subscribed', args)

def unsubscribe_cb(*args):
    print('unsubscribe', args)

def publish_cb(*args):
    print('published', args)

def message_cb(*args):
    print('message', args.payload)

def disconnect_cb(*args):
    print('disconnect', args)

def args_converter(record):
    return {
        'text': '',
        'size_hint_y': None,
        'height': '20pt',
        'cls_dicts': [
            {
                'cls': GridCell,
                'kwargs': {'text': record[x]}
            } for x in record
        ]
    }

class FxRatesMonitor(App):
    def __init__(self, **kw):
        super(FxRatesMonitor, self).__init__(**kw)
        self.clientname = 'client %s' % randint(1, 256)
        self.rates = {}

    def build(self, hostname=None, port=None):
        root = Builder.load_string(kv)

        self.textbox = root.textbox

        self.datasource = GridAdapter(
            col_keys=('tofrom', 'bid', 'ask', 'high', 'low', 'direction'),
            row_keys=self.rates.keys(),
            data=self.rates,
            args_converter=args_converter,
            selection_mode='single',
            cls=GridRow)

        self.gridview = GridView(adapter=self.datasource)
        root.container.add_widget(self.gridview)
        return root

    def setup(self, hostname, port):
        mq = Mosquitto(self.name)
        mq.connect(hostname, port, 60)
        mq.subscribe('chat')
        mq.subscribe('rates/AUDUSD')
        mq.subscribe('rates/USDCHF')
        mq.subscribe('rates/EURUSD')
        mq.subscribe('rates/PLNUSD')
        mq.subscribe('rates/GBPUSD')
        mq.on_message = self.message
        mq.on_connect = connect_cb
        mq.on_subscribe = subscribe_cb
        mq.on_unsubscribe = unsubscribe_cb
        mq.on_publish = publish_cb
        #mq.on_message = message_cb
        mq.on_disconnect = disconnect_cb

        self.mq = mq

        Clock.schedule_interval(lambda *x: mq.loop(), .01)

    def send(self, text):
        self.mq.publish('chat', self.clientname + ' ' + text.encode('utf-8'), qos=1)

    def message(self, bump, _, message):
        if message.topic == 'chat':
            self.textbox.text += '%s: %s' % (
                time.asctime(time.localtime()),
                message.payload + '\n')

        elif 'rates/' in message.topic:
            self.rates[message.topic.split('/')[1]] = {
                x: y for (x, y) in
                zip(self.datasource.col_keys,
                    message.payload.split('/'))
            }

            self.datasource.data = self.rates
            self.datasource.row_keys = self.rates.keys()

if __name__ == '__main__':
    args = parser.parse_args()
    fx = FxRatesMonitor()
    fx.setup(args.hostname, args.port)
    fx.run()
