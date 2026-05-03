
package com.atakmap.android.hellobuildings.opengl.examples;

import java.nio.FloatBuffer;
import java.util.Collection;
import java.util.LinkedList;

import android.opengl.Matrix;

import com.atakmap.map.layer.feature.geometry.opengl.GLGeometry;
import com.atakmap.map.opengl.GLMapRenderable2;
import com.atakmap.map.opengl.GLMapView;
import com.atakmap.opengl.GLES20FixedPipeline;
import com.atakmap.opengl.GLRenderBatch2;

public class GLBuildingRenderBatch implements GLMapRenderable2 {
    private GLRenderBatch2 impl;
    Collection<GLExtrudingPolygon> polys;

    public void release() {
        // if allocated during a render pump, release the render batch resources
        if (this.impl != null) {
            this.impl.dispose();
            this.impl = null;
        }
    }

    public void draw(GLMapView view, int renderPass) {
        if (renderPass != GLMapView.RENDER_PASS_SPRITES)
            return;

        if (impl == null)
            impl = new GLRenderBatch2();

        final int terrainVersion = view.terrain.getTerrainVersion();

        GLES20FixedPipeline.glEnable(GLES20FixedPipeline.GL_BLEND);
        GLES20FixedPipeline.glBlendFunc(GLES20FixedPipeline.GL_SRC_ALPHA,
                GLES20FixedPipeline.GL_ONE_MINUS_SRC_ALPHA);

        // specify any applicable hints to the render batch to allow for
        // optimization through specificity
        impl.begin(GLRenderBatch2.HINT_UNTEXTURED);

        // set the Projection and Model-View matrices that should be used for
        // the vertex data

        GLES20FixedPipeline.glGetFloatv(GLES20FixedPipeline.GL_PROJECTION,
                view.scratch.matrixF, 0);
        impl.setMatrix(GLES20FixedPipeline.GL_PROJECTION, view.scratch.matrixF,
                0);

        // the Model-View matrix will be set to the 'sceneModelForwardMatrix',
        // which defines the model coordinate space as the Map Projection
        // coordinate space. This allows us to specify vertices in the Map
        // Projection and GPU transform from there. Due to limitations in
        // precision this may cause "jitter" effects at higher resolutions 
        // (see GLMapView::hardwareTransformResolutionThreshold for the computed
        // limit). We can further take advantage of this coordinate space by
        // applying the elevation scale factor and offset to the matrix and
        // avoid taking those into account in vertex computation
        System.arraycopy(view.sceneModelForwardMatrix, 0, view.scratch.matrixF,
                0, 16);
        Matrix.scaleM(view.scratch.matrixF, 0, 1f, 1f,
                (float) view.elevationScaleFactor);
        Matrix.translateM(view.scratch.matrixF, 0, 0f, 0f,
                (float) view.elevationOffset);
        impl.setMatrix(GLES20FixedPipeline.GL_MODELVIEW, view.scratch.matrixF,
                0);

        for (GLExtrudingPolygon p : polys) {
            // 
            if (!p.validate(view, GLGeometry.VERTICES_PROJECTED,
                    terrainVersion))
                continue;

            // upload the vertex data and indices for the extruded polygon to
            // the batch renderer
            impl.batch(-1, // texture ID; untextured
                    GLES20FixedPipeline.GL_TRIANGLES, // indexed triangles
                    3, // components per vertex; x,y,z --> 3
                    0, p.vertices, // stride and vertex buffer 
                    0, null, // stride and texture buffer; untextured
                    p.indices, // indices
                    p.r, p.g, p.b, p.a); // color
        }

        // end the batch and flush the content to the display
        impl.end();

        GLES20FixedPipeline.glDisable(GLES20FixedPipeline.GL_BLEND);
    }

    @Override
    public int getRenderPass() {
        // content for this renderable should only be drawn during a "sprites"
        // pass
        return GLMapView.RENDER_PASS_SPRITES;
    }
}
