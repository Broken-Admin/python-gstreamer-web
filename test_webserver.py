from flask import Flask, Response
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import numpy as np

app = Flask(__name__)

class CameraStreamHost:
    def __init__(self, port):
        self.port = port
        self.pipeline = None

    def start(self):
        # Initialize GStreamer
        Gst.init(None)

        # Create pipeline
        self.pipeline = Gst.Pipeline.new("camera-stream-pipeline")

        # Create elements
        v4l2src = Gst.ElementFactory.make("v4l2src", "v4l2src")
        v4l2src.set_property("device", "/dev/video0")  # Specify the camera device
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        caps = Gst.Caps.from_string("video/x-raw,width=640,height=480,framerate=30/1")
        capsfilter.set_property("caps", caps)
        x264enc = Gst.ElementFactory.make("x264enc", "x264enc")
        h264parse = Gst.ElementFactory.make("h264parse", "h264parse")

        # RSTP
        # rtph264pay = Gst.ElementFactory.make("rtph264pay", "rtph264pay")
        # udpsink = Gst.ElementFactory.make("udpsink", "udpsink")
        # udpsink.set_property("host", "127.0.0.1")  # Set host to localhost
        # udpsink.set_property("port", self.port)

        # autovideosink
        autovideosink = Gst.ElementFactory.make("autovideosink", "autovideosink")


        # Add elements to the pipeline
        self.pipeline.add(v4l2src)
        self.pipeline.add(capsfilter)
        self.pipeline.add(x264enc)
        self.pipeline.add(h264parse)

        # RSTP
        # self.pipeline.add(rtph264pay)
        # self.pipeline.add(udpsink)

        # autovideosink
        self.pipeline.add(autovideosink)

        # Link elements
        v4l2src.link(capsfilter)
        capsfilter.link(x264enc)
        x264enc.link(h264parse)

        # RSTP
        # h264parse.link(rtph264pay)
        # rtph264pay.link(udpsink)

        # Set pipeline state to playing
        self.pipeline.set_state(Gst.State.PLAYING)
        print("Camera stream host started.")

    def stop(self):
        if self.pipeline:
            # Set pipeline state to NULL
            self.pipeline.set_state(Gst.State.NULL)
            print("Camera stream host stopped.")

camera_stream_host = CameraStreamHost(port=5000)
camera_stream_host.start()

@app.route('/stream')
def stream():
    def generate():
        while True:
            yield pull_frame_from_camera_stream()

    return Response(generate(), mimetype='image/jpeg')

def pull_frame_from_camera_stream():
    # Initialize GStreamer
    Gst.init(None)

    # Create a pipeline with a videotestsrc generating test video frames
    pipeline = Gst.parse_launch("v4l2src device=/dev/video0 ! videoconvert ! videoscale ! video/x-raw,width=640,height=480 ! appsink name=sink")
    pipeline.set_state(Gst.State.PLAYING)

    # Retrieve the appsink element
    sink = pipeline.get_by_name('sink')

    # Pull a frame from the camera stream
    sample = sink.emit('pull-sample')
    buf = sample.get_buffer()
    result, mapinfo = buf.map(Gst.MapFlags.READ)
    data = mapinfo.data
    size = mapinfo.size
    frame = np.ndarray((size,), buffer=data, dtype=np.uint8)
    buf.unmap(mapinfo)

    # Stop the pipeline
    pipeline.set_state(Gst.State.NULL)

    return frame.tobytes()

if __name__ == '__main__':
    app.run(debug=True)
