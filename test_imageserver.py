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
        source = Gst.ElementFactory.make("videotestsrc", "source")
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        caps = Gst.Caps.from_string("video/x-raw,width=640,height=480,framerate=30/1")
        capsfilter.set_property("caps", caps)
        udpsink = Gst.ElementFactory.make("udpsink", "udpsink")
        udpsink.set_property("host", "127.0.0.1")  # Set host to localhost
        udpsink.set_property("port", self.port)

        # Add elements to the pipeline
        self.pipeline.add(source)
        self.pipeline.add(capsfilter)
        self.pipeline.add(udpsink)

        # Link elements
        source.link(capsfilter)
        capsfilter.link(udpsink)

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

def pull_frame_from_camera_stream():
    # Initialize GStreamer
    Gst.init(None)

    # Create a pipeline with a videotestsrc generating test video frames
    pipeline = Gst.parse_launch("videotestsrc ! videoconvert ! videoscale ! video/x-raw,width=640,height=480 ! jpegenc ! appsink name=sink")
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

# Test the function
if __name__ == "__main__":
    frame = pull_frame_from_camera_stream()
    print("Frame retrieved with size:", len(frame))

@app.route('/stream')
def stream():
    def generate():
        while True:
            # Pull frames from the camera stream and yield them as bytes
            frame = pull_frame_from_camera_stream()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
