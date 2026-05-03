# Video Mosaic Demo

Demonstrates dynamic generation of a tiled, multi-resolution mosaic given a set of input frames. The plugin is implemented to accept MISB compliant FMV (with corner coordinates) as a source for mosaic data -- each imported video will produce a mosaic in real-time as the video plays.

The example code can be configured to enable or disable frame drop. When frame drop is enabled (default), the mosaicker will skip processing any frames if it is currently busy; when frame drop is disabled, every frame will be processed, which may delay video throughput.

Multi-resolution mosaicking is implemented by combining _foreground_ and _background_ representations generated at each resolution level. The _foreground_ is the composition of a given tile and all higher resolution descendents. The _background_ is the composition of a given tile's _parent_ and all ancestors. Maintaining separate representations of the foreground and background allows for the injection of new source data at any resolution while maintaining coherency.

## Project Organization

### `com.atakmap.android.plugins.support`

Contains various classes either present in ATAK Core or candidates for future inclusion in ATAK Core that are used in place of or in addition to current upstream offerings.

### `com.atakmap.android.plugins.videomosaic`

Plugin UX business logic and video handling.

### `com.atakmap.android.plugins.videomosaic.plugin`

ATAK plugin boilerplate.

### `com.atakmap.android.plugins.videomosaic.tiles`

The classes implementing the mosaicking feature. These classes are not coupled with video as an input source and may be re-used in other applications where a tiled, multi-resolution mosaic is being dynamically generated.

## Limitations

Because this is prototype code, there are some limitations. These limitations can be overcome by upstream improvements or by further refinement of the plugin implementation.

* `GLTileMatrixLayer` cannot be used directly as it does not reliably handle refresh requests. Use of this class would be preferred as it allows for generically described `TileMatrix` sources.
* `TileMatrixReader`
  * The implementation assumes a `TileMatrix` defined as a quadtree.
  * The implementation assumes a web mercator/slippy tile layout
* Tile mosaicking throughput is observed at ~5s on S9TE for 1920x1080 video. Note that 1920x1080 covers approximately 8x5 256x256 tiles if consumed at nominal resolution and orthagonal orientation. Smaller source data images should result in better throughput, larger source images are likely to result in worse throughput. Overhead comes in the form of both image processing as well as serialization.
