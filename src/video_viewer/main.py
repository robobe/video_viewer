"""Show the latest complete local SHM image, independent of recorder speed."""
import argparse
import os
from pathlib import Path
import time

import cv2
import numpy as np
import zmq
from bullet_msgs import load_transport
from bullet_msgs.shm import FrameReader, MAX_MESSAGE_BYTES, topic_prefix


class ViewerReceiver:
    def __init__(self, endpoint, topic):
        self.reader = FrameReader(topic)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        try:
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.CONFLATE, 1)
            self.socket.setsockopt(zmq.MAXMSGSIZE, MAX_MESSAGE_BYTES)
            self.socket.setsockopt(zmq.SUBSCRIBE, topic_prefix(topic))
            self.socket.connect(endpoint)
        except BaseException:
            self.close()
            raise

    def poll(self):
        try:
            message = self.socket.recv(zmq.NOBLOCK)
        except zmq.Again:
            return None
        if self.socket.getsockopt(zmq.RCVMORE):
            raise ValueError('expected one image descriptor message')
        result = self.reader.read(message)
        if result is None:
            return None
        metadata, pixels = result
        rows = np.frombuffer(pixels, dtype=np.uint8).reshape(metadata['height'], metadata['step'])
        image = rows[:, :metadata['width'] * 3].reshape(metadata['height'], metadata['width'], 3)
        if metadata['encoding'] == 'rgb8':
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        else:
            image = image.copy()
        return metadata, image

    def close(self):
        self.reader.close()
        self.socket.close(linger=0)
        self.context.term()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport-config', type=Path, required=True)
    parser.add_argument('--topic', default='camera/front/image')
    args = parser.parse_args(argv)
    receiver = None
    window = f'Bullet camera: {args.topic} ({os.getpid()})'
    try:
        transport = load_transport(args.transport_config)
        receiver = ViewerReceiver(transport['image_endpoint'], args.topic)
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        started = last_report = time.monotonic()
        last_frame = None
        frames = sequence = 0
        fps = 0.0
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        print(f'Subscribed to {args.topic} on {transport["image_endpoint"]}, SHM pixels', flush=True)
        while True:
            result = receiver.poll()
            now = time.monotonic()
            if result is not None:
                metadata, image = result
                sequence = metadata['sequence']
                frames += 1
                last_frame = now
            if now - started >= 1:
                fps = frames / (now - started)
                frames = 0
                started = now
            status = 'Waiting for frames' if last_frame is None else ('Live' if now - last_frame < 1 else 'No frames')
            display = image.copy()
            text = f'{fps:.1f} FPS | {status} | Frame {sequence}'
            cv2.rectangle(display, (0, 0), (display.shape[1], 32), (20, 20, 20), -1)
            cv2.putText(display, text, (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 240, 100), 1, cv2.LINE_AA)
            cv2.imshow(window, display)
            if now - last_report >= 1:
                print(f'{text} | Skipped {receiver.reader.skipped}', flush=True)
                last_report = now
            if cv2.waitKey(10) & 0xff in (ord('q'), 27):
                break
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, zmq.ZMQError, cv2.error) as error:
        print(f'Viewer failed: {error}', flush=True)
        return 1
    finally:
        if receiver is not None:
            receiver.close()
        cv2.destroyAllWindows()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
