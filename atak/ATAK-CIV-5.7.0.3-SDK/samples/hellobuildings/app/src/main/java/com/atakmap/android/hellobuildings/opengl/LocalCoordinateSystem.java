
package com.atakmap.android.hellobuildings.opengl;

import com.atakmap.map.MapSceneModel;
import com.atakmap.map.projection.Projection;
import com.atakmap.math.Matrix;
import com.atakmap.math.Plane;
import com.atakmap.math.PointD;

public class LocalCoordinateSystem {
    public PointD origin;
    public Matrix forward;
    public float[] forwardF;
    public Projection proj;

    public LocalCoordinateSystem() {
        this.origin = new PointD(0d, 0d, 0d);
        this.forward = null;
        this.forwardF = null;
        this.proj = null;
    }

    public LocalCoordinateSystem(LocalCoordinateSystem other) {
        this.origin = new PointD(other.origin.x, other.origin.y,
                other.origin.z);
        this.forward = Matrix.getIdentity();
        this.forward.set(other.forward);
        this.forwardF = new float[16];
        System.arraycopy(other.forwardF, 0, this.forwardF, 0, 16);
        this.proj = other.proj;
    }

    public static void deriveFrom(MapSceneModel scene, PointD origin,
            LocalCoordinateSystem lcs) {
        lcs.origin = origin;

        lcs.proj = scene.mapProjection;
        if (lcs.forward == null)
            lcs.forward = Matrix.getIdentity();
        lcs.forward.set(scene.forward);

        lcs.forward.translate(lcs.origin.x, lcs.origin.y, lcs.origin.z);

        // fill the forward matrix for the Model-View
        if (lcs.forwardF == null)
            lcs.forwardF = new float[16];
        double[] matrixD = new double[16];
        lcs.forward.get(matrixD, Matrix.MatrixOrder.COLUMN_MAJOR);
        for (int i = 0; i < 16; i++)
            lcs.forwardF[i] = (float) matrixD[i];
    }

    public void apply(PointD proj, PointD lcs) {
        lcs.x = (proj.x - origin.x);
        lcs.y = (proj.y - origin.y);
        lcs.z = (proj.z - origin.z);
    }
}
