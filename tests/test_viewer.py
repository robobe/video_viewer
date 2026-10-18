import time

import numpy as np
import zmq
from bullet_msgs.shm import FrameWriter, topic_prefix
from video_viewer.main import ViewerReceiver


def poll(receiver):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = receiver.poll()
        if result is not None:
            return result
        time.sleep(0.01)
    raise AssertionError('no frame received')


def test_tcp_viewer_receives_private_bgr_pixels_and_reconnects():
    with zmq.Context() as context, context.socket(zmq.XPUB) as publisher:
        publisher.setsockopt(zmq.LINGER, 0)
        publisher.bind_to_random_port('tcp://127.0.0.1')
        receiver = ViewerReceiver(publisher.getsockopt_string(zmq.LAST_ENDPOINT), 'camera/front/image')
        try:
            assert publisher.poll(5000)
            assert publisher.recv() == b'\x01' + topic_prefix('camera/front/image')
            with FrameWriter(2, 1) as writer:
                publisher.send(writer.write('camera/front/image', bytes([1,2,3,4,5,6])))
                metadata, image = poll(receiver)
                assert metadata['sequence'] == 1
                assert image.tolist() == [[[3,2,1],[6,5,4]]]
            with FrameWriter(2, 1, 'bgr8', step=8) as writer:
                publisher.send(writer.write('camera/front/image', bytes([7,8,9,10,11,12,0,0])))
                _, padded = poll(receiver)
                assert padded.tolist() == [[[7,8,9],[10,11,12]]]
                assert image.tolist() == [[[3,2,1],[6,5,4]]]
        finally:
            receiver.close()
