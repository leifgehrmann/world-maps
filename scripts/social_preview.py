from pathlib import Path
from typing import List

import click as click
import shapefile
from map_engraver.data.pango.layout import Layout
from map_engraver.drawable.text.pango_drawer import PangoDrawer
from pangocffi import Alignment

from pyproj import CRS

from shapely import ops
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from map_engraver.data.geo.geo_coordinate import GeoCoordinate
from map_engraver.data.geo_canvas_ops.geo_canvas_scale import GeoCanvasScale
from map_engraver.data.geo_canvas_ops.geo_canvas_transformers import \
    build_transformer

from map_engraver.drawable.layout.background import Background
from map_engraver.drawable.geometry.polygon_drawer import PolygonDrawer

from map_engraver.canvas import CanvasBuilder
from map_engraver.canvas.canvas_coordinate import CanvasCoordinate
from map_engraver.canvas.canvas_unit import CanvasUnit as Cu


@click.command()
def render():
    name = 'social-preview.png'

    bg_color = (28/255, 129/255, 88/255)
    land_color = (68/255, 239/255, 138/255)

    # Extract shapefile data into multi-polygons
    data_path = Path(__file__).parent.parent.joinpath('data')
    land_shape_path = data_path.joinpath('ne_50m_land/ne_50m_land.shp')
    lake_shape_path = data_path.joinpath('ne_50m_lakes/ne_50m_lakes.shp')

    # Read land/lake map shapefile data
    def parse_shapefile(shapefile_path: Path):
        shapefile_collection = shapefile.Reader(shapefile_path.as_posix())
        shapely_objects = []
        for shape_record in shapefile_collection.shapeRecords():
            shapely_objects.append(shape(shape_record.shape.__geo_interface__))
        return shapely_objects

    land_shapes = parse_shapefile(land_shape_path)
    lake_shapes = parse_shapefile(lake_shape_path)

    # Invert CRS for shapes, because shapefiles are store coordinates are
    # lon/lat, not according to the ISO-approved standard.
    # Todo: Replace this by adding `crs_yx=True` to the build_transformer when
    # it has been added.
    def transform_geoms_to_invert(geoms: List[BaseGeometry]):
        return list(map(
            lambda geom: ops.transform(lambda x, y: (y, x), geom),
            geoms
        ))

    land_shapes = transform_geoms_to_invert(land_shapes)
    lake_shapes = transform_geoms_to_invert(lake_shapes)
    land_shapes = ops.unary_union(land_shapes)
    lake_shapes = ops.unary_union(lake_shapes)
    land_shapes = land_shapes.difference(lake_shapes)

    # Build the canvas
    Path(__file__).parent.parent.joinpath('output/') \
        .mkdir(parents=True, exist_ok=True)
    path = Path(__file__).parent.parent.joinpath('output/%s' % name)
    path.unlink(missing_ok=True)
    canvas_builder = CanvasBuilder()
    canvas_builder.set_path(path)
    width = Cu.from_px(1280)
    height = width / 2
    canvas_builder.set_size(
        width,
        height
    )
    canvas = canvas_builder.build()

    # Now let's sort out the projection system
    crs = CRS.from_epsg(4326)
    geo_to_canvas_scale = GeoCanvasScale(
        35000,
        Cu.from_px(1)
    )
    origin_for_geo = GeoCoordinate(0, 0, crs)
    origin_for_canvas = CanvasCoordinate(width / 4, height / 2)
    wgs84_to_canvas = build_transformer(
        crs=CRS.from_proj4('+proj=rpoly'),
        data_crs=crs,
        scale=geo_to_canvas_scale,
        origin_for_geo=origin_for_geo,
        origin_for_canvas=origin_for_canvas
    )

    # Finally, let's get to rendering stuff!
    background = Background()
    background.color = bg_color
    background.draw(canvas)

    land_shapes_canvas = ops.transform(
        wgs84_to_canvas,
        land_shapes
    )

    polygon_drawer = PolygonDrawer()
    polygon_drawer.fill_color = land_color
    polygon_drawer.geoms = [land_shapes_canvas]
    polygon_drawer.draw(canvas)

    text_layout = Layout(canvas)
    text_layout.set_markup('<span face="SF Pro Rounded" weight="bold" font_size="90pt">world-maps</span>')
    text_layout.position = CanvasCoordinate(Cu(0), Cu.from_pt(height.pt / 2 - 70))
    text_layout.width = width
    text_layout.alignment = Alignment.CENTER
    text_layout.color = (1, 1, 1)

    text_drawer = PangoDrawer()
    text_drawer.pango_objects = [text_layout]
    text_drawer.draw(canvas)

    canvas.close()


if __name__ == '__main__':
    render()
