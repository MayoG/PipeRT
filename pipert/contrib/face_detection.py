import torch

from pipert.core.message import PredictionPayload
from pipert.utils.structures import Instances, Boxes
from pipert.core.component import BaseComponent
from queue import Queue, Empty
import argparse
from urllib.parse import urlparse
import zerorpc
import gevent
import signal
import time
import cv2
from pipert.core.routine import Routine
from pipert.core.mini_logics import Message2Redis, MessageFromRedis
from pipert.core.routine import Events
from pipert.core.handlers import tick, tock


class FaceDetLogic(Routine):

    def __init__(self, in_queue, out_queue):
        super().__init__()
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.face_cas = None

    def main_logic(self, *args, **kwargs):
        try:
            msg = self.in_queue.get(block=False)
            frame = msg.get_payload()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = self.face_cas.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(20, 20)
            )
            if len(faces):
                faces = torch.from_numpy(faces)
                faces[:, 2:] += faces[:, :2]
                # print(faces.size(), faces)
                new_instances = Instances(frame.shape[:2])
                new_instances.set("pred_boxes", Boxes(faces))
                new_instances.set("pred_classes", torch.zeros(faces.size(0)).int())
            else:
                new_instances = Instances(frame.shape[:2])
                new_instances.set("pred_classes", [])

            try:
                self.out_queue.get(block=False)
                self.state.dropped += 1
            except Empty:
                pass

            # Not sure if like should do this like that
            msg.payload = PredictionPayload(new_instances)
            # msg.update_payload(new_instances)
            self.out_queue.put(msg, block=False)
            return True

        except Empty:
            time.sleep(0)
            return False

    def setup(self, *args, **kwargs):
        casc_path = "pipert/contrib/face_detect/haarcascade_frontalface_default.xml"
        self.face_cas = cv2.CascadeClassifier(casc_path)
        self.state.dropped = 0

    def cleanup(self, *args, **kwargs):
        pass


class FaceDetComponent(BaseComponent):

    def __init__(self, endpoint, in_key, out_key, redis_url, maxlen=100, name="FaceDetection"):
        super().__init__(endpoint, name)
        # TODO: should queue maxsize be configurable?
        self.in_queue = Queue(maxsize=1)
        self.out_queue = Queue(maxsize=1)

        r_get = MessageFromRedis(in_key, redis_url, self.in_queue).as_thread()
        r_sort = FaceDetLogic(self.in_queue, self.out_queue).as_thread()
        r_upload_meta = Message2Redis(out_key, redis_url, self.out_queue, maxlen).as_thread()

        routines = [r_get, r_sort, r_upload_meta]
        for routine in routines:
            # routine.register_events(Events.BEFORE_LOGIC, Events.AFTER_LOGIC)
            # routine.add_event_handler(Events.BEFORE_LOGIC, tick)
            # routine.add_event_handler(Events.AFTER_LOGIC, tock)
            self.register_routine(routine)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input stream key name', type=str, default='camera:2')
    parser.add_argument('-o', '--output', help='Output stream key name', type=str, default='camera:3')
    parser.add_argument('-u', '--url', help='Redis URL', type=str, default='redis://127.0.0.1:6379')
    parser.add_argument('-z', '--zpc', help='zpc port', type=str, default='4248')
    parser.add_argument('--maxlen', help='Maximum length of output stream', type=int, default=100)
    # max_age: int = 1, min_hits: int = None, window_size: int = None, percent_seen
    opt = parser.parse_args()

    url = urlparse(opt.url)

    zpc = FaceDetComponent(f"tcp://0.0.0.0:{opt.zpc}", opt.input, opt.output, url, maxlen=opt.maxlen)
    print("run")
    zpc.run()
    print("Killed")
