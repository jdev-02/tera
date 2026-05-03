package com.atakmap.android.plugins.videomosaic;

import android.graphics.Bitmap;

import com.atakmap.android.plugins.videomosaic.tiles.MosaickingTileLayer;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.partech.pgscmedia.MediaException;

import java.util.concurrent.atomic.AtomicBoolean;

final class MosaicDataPipe implements MosaicDataProvider.VideoFrameListener, Runnable {
    interface FrameMosaickedListener {
        void onFrameMosaicked(MosaickingTileLayer sink, GeoPoint ul, GeoPoint ur, GeoPoint lr, GeoPoint ll);
    }

    MosaicDataProvider _source;
    MosaickingTileLayer _sink;
    AtomicBoolean _started = new AtomicBoolean(false);
    boolean _allowFrameDrop = false;
    boolean _processing = false;
    FrameMosaickedListener[] _listener = new FrameMosaickedListener[1];

    Frame _queued;

    MosaicDataPipe(MosaicDataProvider source, MosaickingTileLayer sink) {
        _source = source;
        _sink = sink;
    }

    public synchronized void start(boolean allowFrameDrop) {
        if(!_started.compareAndSet(false, true))
            return;

        _allowFrameDrop = allowFrameDrop;
        if(_allowFrameDrop) {
            Thread t = new Thread(this);
            t.setName("MosaicDataPipe");
            t.setPriority(Thread.NORM_PRIORITY);
            t.start();
        }

        _source.setVideoFrameListener(this);
        try {
            _source.start();
        } catch(MediaException ignored) {}
    }

    public synchronized void stop() {
        _source.stop();
        _source.setVideoFrameListener(null);

        _started.set(false);
    }

    public MosaicDataProvider source() {
        return _source;
    }

    public MosaickingTileLayer sink() {
        return _sink;
    }

    public void setListener(FrameMosaickedListener l) {
        synchronized (_listener) {
            _listener[0] = l;
        }
    }

    @Override
    public void videoFrame(Bitmap frame, GeoPoint upperLeft, GeoPoint upperRight, GeoPoint lowerRight, GeoPoint lowerLeft) {
        synchronized (_listener) {
            if (!_allowFrameDrop) {
                _sink.updateMosaic(upperLeft, upperRight, lowerRight, lowerLeft, frame);
                if (_listener[0] != null)
                    _listener[0].onFrameMosaicked(_sink, upperLeft, upperRight, lowerRight, lowerLeft);
            } else {
                _queued = new Frame();
                _queued.data = Bitmap.createBitmap(frame);
                _queued.upperLeft = new GeoPoint(upperLeft);
                _queued.upperRight = new GeoPoint(upperRight);
                _queued.lowerRight = new GeoPoint(lowerRight);
                _queued.lowerLeft = new GeoPoint(lowerLeft);

                _listener.notify();
            }
        }
    }

    @Override
    public void run() {
        while(true) {
            Frame data = null;
            synchronized(_listener) {
                if(!_started.get())
                    break;
                if(_queued == null) {
                    _processing = false;
                    try {
                        _listener.wait(1000);
                    } catch(InterruptedException ignored) {}
                    continue;
                }

                data = _queued;
                _queued = null;
                _processing = true;
            }

            _sink.updateMosaic(data.upperLeft, data.upperRight, data.lowerRight, data.lowerLeft, data.data);
            data.data.recycle();
            synchronized (_listener) {
                if(_listener[0] != null)
                    _listener[0].onFrameMosaicked(_sink, data.upperLeft, data.upperRight, data.lowerRight, data.lowerLeft);
            }
        }
    }

    final static class Frame {
        Bitmap data;
        GeoPoint upperLeft;
        GeoPoint upperRight;
        GeoPoint lowerLeft;
        GeoPoint lowerRight;
    }
}
