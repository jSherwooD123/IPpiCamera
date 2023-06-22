from django.shortcuts import render
from django.http.response import StreamingHttpResponse
import cv2, time, threading
from picamera.array import PiRGBArray
from picamera import PiCamera

def index(request):
    return render(request, 'live.html')

class VideoFeed(object):
    def __init__(self, resolution=(1280, 720), framerate=60,):

        # Initialize the PiCamera object
        self.camera = PiCamera()
        self.camera.resolution = resolution
        self.camera.framerate = framerate

        '''Initialize the PiRGBArray for capturing frames. It acts as a buffer being able
        to hold multiple frames, each time a new frame is captured the oldest is automatically 
        disguarded.'''
        self.rawFrames = PiRGBArray(self.camera, size=resolution)

        ''' Start the camera stream. It allows the camera to continuously capture frames and store them in 
        self.rawFrames buffer'''
        self.stream = self.camera.capture_continuous(self.rawCapture,
                                                     format="bgr", use_video_port=True)

        # Initialize the frame and stopped flag
        self.frame = None
        self.stopped = False

        # Delay to allow camera stream to initialize
        time.sleep(2)


    #  Starts a separate thread to continuously update the frame from the camera stream.
    def start(self):
        t = threading.Thread(target=self.update)
        t.daemon = True
        t.start()
        return self

    def update(self):

        # Iterates through the frames captured
        for f in self.stream:
            # The most recent frame store in self.frame 
            self.frame = f.array

            # Clears the buffer
            self.rawFrames.truncate(0)

            # Closes everything down when self.stopped it turned to true
            if self.stopped:
                self.stream.close()
                self.rawFrames.close()
                self.camera.close()
                return

    def get_frame(self):
        return self.frame

    def stop(self):
        self.stopped = True

def video_feed(request):
    def generate(camera):
        while True:
            frame = camera.get_frame()
            if frame:
                _, jpeg = cv2.imencode('.jpg', frame)
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n'

    cam = VideoFeed().start()
    return StreamingHttpResponse(generate(cam), content_type='multipart/x-mixed-replace; boundary=frame')

