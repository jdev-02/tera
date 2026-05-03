
package com.atakmap.android.plugins.videomosaic;

import android.graphics.Bitmap;

import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import com.atakmap.map.layer.AbstractLayer;
import com.partech.pgscmedia.MediaException;
import com.partech.pgscmedia.MediaFormat;
import com.partech.pgscmedia.MediaProcessor;
import com.partech.pgscmedia.VideoMediaFormat;
import com.partech.pgscmedia.VideoMediaFormat.PixelFormat;
import com.partech.pgscmedia.consumers.KLVConsumer;
import com.partech.pgscmedia.consumers.VideoConsumer;
import com.partech.pgscmedia.frameaccess.DecodedMetadataItem;
import com.partech.pgscmedia.frameaccess.DecodedMetadataItem.MetadataItemIDs;
import com.partech.pgscmedia.frameaccess.KLVData;
import com.partech.pgscmedia.frameaccess.MediaMetadataDecoder;
import com.partech.pgscmedia.frameaccess.NativeIntArray;
import com.partech.pgscmedia.frameaccess.VideoFrameConverter;
import com.partech.pgscmedia.frameaccess.VideoFrameData;

/**
 * A map layer that renders video frames registered to the map.
 *  
 * @author Developer
 */
public class MosaicDataProvider implements VideoConsumer,
        KLVConsumer {

    private MediaProcessor proc;
    private String uri;

    private MediaMetadataDecoder metadataDecoder;
    private VideoFrameConverter frameConverter;

    private int[] frameRGB;

    private int frameWidth;
    private int frameHeight;

    private int converterOffset;
    private int converterStride;

    private GeoPoint upperLeft;
    private GeoPoint upperRight;
    private GeoPoint lowerRight;
    private GeoPoint lowerLeft;

    private VideoFrameListener listener;

    private boolean haveVideo;
    private boolean haveMeta;

    public MosaicDataProvider(String uri) {
        this.uri = uri;
        this.proc = null;

        this.upperLeft = GeoPoint.createMutable();
        this.upperRight = GeoPoint.createMutable();
        this.lowerRight = GeoPoint.createMutable();
        this.lowerLeft = GeoPoint.createMutable();
    }

    public String getUri() {
        return this.uri;
    }

    private void initNoSync() throws MediaException {
        // create a new MediaProcessor from the file
        this.proc = new MediaProcessor(this.uri);

        // Look at the format of all tracks and grab the ones we are
        // interested in. Here, for sake of simplicity,
        // we take just the first video track
        // and first klv metadata track if it exists.
        MediaFormat[] fmts = this.proc.getTrackInfo();
        boolean haveVid = false;
        boolean haveKLV = false;
        for (MediaFormat fmt : fmts) {
            if (!haveVid && fmt.type == MediaFormat.Type.FORMAT_VIDEO) {
                // create a frame convert with an output of RGB packed
                this.frameConverter = new VideoFrameConverter(
                        (VideoMediaFormat) fmt, PixelFormat.PIXELS_RGB_PACKED);
                // set this class as the video consumer
                this.proc.setVideoConsumer(fmt.trackNum, this);
                // set up the frame properties
                this.frameWidth = this.frameConverter.getScaleOutputWidth();
                this.frameHeight = this.frameConverter.getScaleOutputHeight();
                this.frameRGB = new int[this.frameWidth * this.frameHeight];
                this.converterOffset = this.frameConverter
                        .getOutputOffsets()[0];
                this.converterStride = this.frameConverter
                        .getOutputStrides()[0];
                haveVid = true;
            }
            if (!haveKLV && fmt.type == MediaFormat.Type.FORMAT_KLV) {
                // set this class as the KLV consumer
                this.proc.setKLVConsumer(fmt.trackNum, this);
                haveKLV = true;
            }
            if (haveKLV && haveVid)
                break;
        }

        if (this.frameConverter == null)
            throw new MediaException("No video track found.");

        // don't allow frame drops
        this.proc.setFrameDiscardEnabled(false);

        this.metadataDecoder = new MediaMetadataDecoder();

        this.haveVideo = false;
        this.haveMeta = false;
    }

    /**
     * Starts video playback.
     * 
     * @throws MediaException   If there is an error initializing the video.
     */
    public void start() throws MediaException {
        if (this.proc == null)
            this.initNoSync();
        this.proc.start();
    }

    /**
     * Stops video playback.
     */
    public void stop() {
        if (this.proc != null)
            this.proc.stop();
    }

    /**
     * Seeks the video to the specified timestamp.  This method should only be
     * invoked on a <I>stopped</I> video.
     * 
     * @param timestampMillis   The timestamp, in milliseconds
     */
    public void seek(long timestampMillis) {
        if (this.proc != null) {
            // clear the video/metadata flags
            this.haveVideo = false;
            this.haveMeta = false;
            // set the time
            this.proc.setTime(timestampMillis);
        }
    }

    public void nextFrame() throws MediaException {
        if (this.proc == null)
            this.initNoSync();
        if(this.proc != null) {
            this.proc.prefetch();
        }
    }

    public void dispose() {
        if (this.proc != null) {
            this.proc.destroy();
            this.proc = null;

            this.frameConverter = null;
            this.metadataDecoder = null;
        }
    }

    private void dispatchVideoFrameNoSync() {
        // obtain the corner coordinates
        this.getPoint(this.upperLeft,
                MetadataItemIDs.METADATA_ITEMID_CORNER_LATITUDE_POINT_1,
                MetadataItemIDs.METADATA_ITEMID_CORNER_LONGITUDE_POINT_1);
        this.getPoint(this.upperRight,
                MetadataItemIDs.METADATA_ITEMID_CORNER_LATITUDE_POINT_2,
                MetadataItemIDs.METADATA_ITEMID_CORNER_LONGITUDE_POINT_2);
        this.getPoint(this.lowerRight,
                MetadataItemIDs.METADATA_ITEMID_CORNER_LATITUDE_POINT_3,
                MetadataItemIDs.METADATA_ITEMID_CORNER_LONGITUDE_POINT_3);
        this.getPoint(this.lowerLeft,
                MetadataItemIDs.METADATA_ITEMID_CORNER_LATITUDE_POINT_4,
                MetadataItemIDs.METADATA_ITEMID_CORNER_LONGITUDE_POINT_4);

        // copy the video frame
        NativeIntArray rgb = (NativeIntArray) this.frameConverter
                .getOutputArray();
        if (this.converterStride == this.frameWidth) {
            System.arraycopy(rgb.intArray, rgb.offset + this.converterOffset,
                    this.frameRGB, 0, (this.frameWidth * this.frameHeight));
        } else {
            for (int i = 0; i < this.frameHeight; i++)
                System.arraycopy(rgb.intArray, rgb.offset
                        + this.converterOffset + (i * this.converterStride),
                        this.frameRGB, (i * this.frameWidth), this.frameWidth);
        }

        // if we have a listener installed and we've received both metadata and
        // video, dispatch the frame
        if (this.listener != null && this.haveMeta && this.haveVideo)
            this.listener.videoFrame(
                    Bitmap.createBitmap(this.frameRGB, this.frameWidth, this.frameHeight, Bitmap.Config.ARGB_8888),
                    this.upperLeft, this.upperRight,
                    this.lowerRight, this.lowerLeft);
    }

    private void getPoint(GeoPoint point, MetadataItemIDs latId,
            MetadataItemIDs lngId) {
        // obtain the latitude/longitude values
        DecodedMetadataItem latitude = this.metadataDecoder.getItem(latId);
        DecodedMetadataItem longitude = this.metadataDecoder.getItem(lngId);

        double lat = Double.NaN;
        if (latitude != null)
            lat = ((Number) latitude.getValue()).doubleValue();
        double lng = Double.NaN;
        if (longitude != null)
            lng = ((Number) longitude.getValue()).doubleValue();

        // update the point; respective components will be NaN if not defined
        point.set(lat, lng);
    }

    /**
     * Sets the current {@link VideoFrameListener}. If <code>null</code> the
     * current listener is cleared.
     * 
     * @param l A {@link VideoFrameListener} or <code>null</code>.
     */
    public synchronized void setVideoFrameListener(VideoFrameListener l) {
        this.listener = l;
    }

    public synchronized boolean getFrameBounds(GeoPoint ul,
            GeoPoint ur, GeoPoint lr, GeoPoint ll) {
        ul.set(this.upperLeft);
        ur.set(this.upperRight);
        lr.set(this.lowerRight);
        ll.set(this.lowerLeft);

        return (!Double.isNaN(ul.getLatitude()) && !Double.isNaN(ul
                .getLongitude()))
                &&
                (!Double.isNaN(ur.getLatitude()) && !Double.isNaN(ur
                        .getLongitude()))
                &&
                (!Double.isNaN(lr.getLatitude()) && !Double.isNaN(lr
                        .getLongitude()))
                &&
                (!Double.isNaN(ll.getLatitude()) && !Double.isNaN(ll
                        .getLongitude()));
    }

    /*************************************************************************/
    // KLV Consumer

    @Override
    public synchronized void mediaKLVData(KLVData arg0) {
        // decode the KLV metadata
        this.metadataDecoder.decode(arg0);
        // set the flag indicating we have metadata
        this.haveMeta = true;
        // dispatch a video frame to the listener
        this.dispatchVideoFrameNoSync();
    }

    /*************************************************************************/
    // Video Consumer

    @Override
    public synchronized void mediaVideoFrame(VideoFrameData arg0) {
        try {
            // convert the frame to RGB
            this.frameConverter.convert(arg0);
            // set flag indicating we have video
            this.haveVideo = true;
            // dispatch a video frame to the listener
            this.dispatchVideoFrameNoSync();
        } catch (MediaException e) {
            Log.w("VideoOverlayLayer",
                    "Failed to decode frame @ " + arg0.getTimestamp());
        }
    }

    /**************************************************************************/

    /**
     * Callback interface for receipt of frame with corner coordinates.
     */
    public static interface VideoFrameListener {

        /**
         * The video frame callback function. The listener is supplied with the
         * frame's data (as RGB pixels) and the corner coordinates. The values
         * for any of the corner coordinates may be {@link Double#NaN},
         * indicating that the information is not available.
         * 
         * <P><B>IMPORTANT:</B> The object contents are only valid during
         * invocation of the callback; if the frame data or any of the
         * coordinate objects are going to be used outside of the scope of the
         * callback copies must be created.
         * 
         * @param frame         The video frame data
         * @param upperLeft     The coordinate associated with the upper-left
         *                      corner of the frame; may not be
         *                      <code>null</code>. Either or both latitude and
         *                      longitude may be {@link Double#NaN} if the data
         *                      is not available.
         * @param upperRight    The coordinate associated with the upper-right
         *                      corner of the frame; may not be
         *                      <code>null</code>. Either or both latitude and
         *                      longitude may be {@link Double#NaN} if the data
         *                      is not available.
         * @param lowerRight    The coordinate associated with the lower-right
         *                      corner of the frame; may not be
         *                      <code>null</code>. Either or both latitude and
         *                      longitude may be {@link Double#NaN} if the data
         *                      is not available.
         * @param lowerLeft     The coordinate associated with the lower-left
         *                      corner of the frame; may not be
         *                      <code>null</code>. Either or both latitude and
         *                      longitude may be {@link Double#NaN} if the data
         *                      is not available.
         */
        public void videoFrame(Bitmap frame,
                               GeoPoint upperLeft, GeoPoint upperRight, GeoPoint lowerRight,
                               GeoPoint lowerLeft);
    } // VideoFrameListener
} // VideoOverlayLayer
