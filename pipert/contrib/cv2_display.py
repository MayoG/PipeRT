from pipert.core.component import BaseComponent
from queue import Queue
import argparse
import redis
from urllib.parse import urlparse
import zerorpc
import gevent
import signal
from pipert.core.routine import Events
from pipert.core.mini_logics import MessageFromRedis, DisplayCV2
from pipert.core.handlers import tick, tock


class CV2VideoDisplay(BaseComponent):

    def __init__(self, endpoint, in_key, redis_url, field, name="CV2VideoDisplay"):
        super().__init__(endpoint, name)

        self.field = field  # .encode('utf-8')
        self.queue = Queue(maxsize=1)
        r_get = MessageFromRedis(in_key, redis_url, self.in_queue,
                                 name="get_frames", component_name=self.name).as_thread()
        r_draw = DisplayCV2(in_key, self.queue, name="draw_frames")

        routines = [r_get, r_draw]

        for routine in routines:
            routine.register_events(Events.BEFORE_LOGIC, Events.AFTER_LOGIC)
            routine.add_event_handler(Events.BEFORE_LOGIC, tick)
            routine.add_event_handler(Events.AFTER_LOGIC, tock)
            self.register_routine(routine)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input stream key name', type=str, default='camera:1')
    parser.add_argument('-u', '--url', help='Redis URL', type=str, default='redis://127.0.0.1:6379')
    parser.add_argument('-z', '--zpc', help='zpc port', type=str, default='4244')
    parser.add_argument('--field', help='Image field name', type=str, default='image')
    args = parser.parse_args()

    # Set up Redis connection
    url = urlparse(args.url)

    zpc = CV2VideoDisplay(f"tcp://0.0.0.0:{args.zpc}", args.input, url, args.field)
    print("run")
    zpc.run()
    print("Killed")
