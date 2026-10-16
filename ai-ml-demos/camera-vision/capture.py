# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import numpy as np
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo

Gst.init(None)


class VideoCapture:
    """Own each BGR frame and distinguish actual EOS from a pipeline failure."""

    def __init__(self, description):
        self.pipeline = Gst.parse_launch(description)
        self.sink = self.pipeline.get_by_name('frames')
        self.bus = self.pipeline.get_bus()
        self.closed = False
        self.last_pts = None
        if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.release()
            raise RuntimeError('Could not start the video pipeline')

    def read(self):
        sample = self.sink.emit('try-pull-sample', 2 * Gst.SECOND)
        if sample is None:
            message = self.bus.pop_filtered(Gst.MessageType.ERROR |
                                            Gst.MessageType.EOS)
            if message and message.type == Gst.MessageType.ERROR:
                error, debug = message.parse_error()
                raise RuntimeError(f'Video pipeline failed: {error}: {debug}')
            if self.sink.get_property('eos'):
                return False, None
            raise RuntimeError('Video pipeline timed out before end of stream')
        info = GstVideo.VideoInfo.new_from_caps(sample.get_caps())
        if info.finfo.name != 'BGR':
            raise RuntimeError(f'Expected BGR, received {info.finfo.name}')
        buffer = sample.get_buffer()
        self.last_pts = buffer.pts
        pixels = buffer.extract_dup(0, buffer.get_size())
        meta = GstVideo.buffer_get_video_meta(buffer)
        stride = meta.stride[0] if meta else info.stride[0]
        offset = meta.offset[0] if meta else info.offset[0]
        required = offset + (info.height - 1) * stride + info.width * 3
        if stride < info.width * 3 or required > len(pixels):
            raise RuntimeError('Video buffer is smaller than its image layout')
        # Accelerated converters can pad both rows and the bottom of a frame.
        # Interpret its actual layout instead of reshaping the whole allocation.
        frame = np.ndarray((info.height, info.width, 3), dtype=np.uint8,
                           buffer=pixels, offset=offset, strides=(stride, 3, 1))
        return True, frame.copy()

    def set_paused(self, paused):
        state = Gst.State.PAUSED if paused else Gst.State.PLAYING
        if self.pipeline.set_state(state) == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError('Could not change video pipeline state')

    def release(self):
        if not self.closed:
            self.closed = True
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_state(2 * Gst.SECOND)
