from django.shortcuts import render
from django.http.response import StreamingHttpResponse
import cv2, time, threading
from picamera.array import PiRGBArray
from picamera import PiCamera
from datetime import datetime

def index(request):
    return render(request, 'live.html')

class VideoFeed(object):
    def __init__(self, resolution=(704, 368), framerate=60,):

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
        self.stream = self.camera.capture_continuous(self.rawFrames,
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

# On server startup, create an instance of VideoFeed and start it
cam = VideoFeed().start()

def video_feed(request):


    def generate(camera):


        while True:
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontSize = 0.5
            colour = (0,0,255)
            thickness = 1

            # Read the frame from the camera
            frame = camera.get_frame()

            # Get date and time  to display on JPEG
            now = datetime.now()
            c_dt = now.strftime("%d/%m/%Y %H:%M:%S")


            # Check a frame has actually been returned
            if frame is not None:

                # Write the date and time onto the frame
                cv2.putText(frame, c_dt, (10, frame.shape[0] - 10),
                        font, fontSize, colour, thickness, cv2.LINE_AA)

                # Encode the frame as JPEG
                _, jpeg = cv2.imencode('.jpg', frame)

                cv2.putText(frame, c_dt, (10, frame.shape[0] - 10),
                        font, fontSize, colour, thickness, cv2.LINE_AA)
                

                # Yield the JPEG frame in the streaming response format
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n'

           


    # Return the streaming response with the generated frames
    response = StreamingHttpResponse(generate(cam), content_type='multipart/x-mixed-replace; boundary=frame')

    return response

