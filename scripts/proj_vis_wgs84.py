from pathlib import Path
from typing import List

import click as click
import shapefile

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
    name = 'proj-vis-wgs84.png'

    bg_color = (59/255, 130/255, 246/255)
    land_color = (255/255, 255/255, 255/255)

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
    width = Cu.from_px(1800)
    height = width / 2
    canvas_builder.set_size(
        width,
        height
    )
    canvas = canvas_builder.build()

    # Now let's sort out the projection system
    crs = CRS.from_epsg(4326)
    geo_to_canvas_scale = GeoCanvasScale(
        1,
        width / 360
    )
    origin_for_geo = GeoCoordinate(0, 0, crs)
    origin_x = Cu.from_px(0)
    origin_y = Cu.from_px(0)
    origin_for_canvas = CanvasCoordinate(origin_x, origin_y)
    wgs84_to_canvas = build_transformer(
        crs=crs,
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

    # Todo: Replace this by adding `canvas_yx=True` to the build_transformer
    # when it has been added.
    land_shapes_canvas = ops.transform(
        lambda x, y: (-y + width.pt / 2, -x + height.pt / 2),
        land_shapes_canvas
    )

    polygon_drawer = PolygonDrawer()
    polygon_drawer.fill_color = land_color
    polygon_drawer.geoms = [land_shapes_canvas]
    polygon_drawer.draw(canvas)

    canvas.close()


if __name__ == '__main__':
    render()
