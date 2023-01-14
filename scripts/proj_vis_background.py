from pathlib import Path
from typing import List

import click as click
import shapefile

from pyproj import CRS

from shapely import ops
from shapely.geometry import shape, Polygon
from shapely.geometry.base import BaseGeometry

from map_engraver.data.geo.geo_coordinate import GeoCoordinate
from map_engraver.data.geo_canvas_ops.geo_canvas_scale import GeoCanvasScale
from map_engraver.data.geo_canvas_ops.geo_canvas_transformers import \
    build_crs_to_canvas_transformer

from map_engraver.drawable.geometry.polygon_drawer import PolygonDrawer

from map_engraver.canvas import CanvasBuilder
from map_engraver.canvas.canvas_coordinate import CanvasCoordinate
from map_engraver.canvas.canvas_unit import CanvasUnit as Cu


@click.command()
def render():
    name = 'proj-vis-background.svg'

    land_color = (59 / 255, 130 / 255, 246 / 255)

    # Extract shapefile data into multi-polygons
    data_path = Path(__file__).parent.parent.joinpath('data')
    land_shape_path = data_path.joinpath('ne_110m_land/ne_110m_land.shp')
    lake_shape_path = data_path.joinpath('ne_110m_lakes/ne_110m_lakes.shp')

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

    antarctica_filter = Polygon([
        (-62, -180),
        (-62, 180),
        (-90, 180),
        (-90, -180),
    ])

    land_shapes = transform_geoms_to_invert(land_shapes)
    lake_shapes = transform_geoms_to_invert(lake_shapes)
    land_shapes = ops.unary_union(land_shapes)
    lake_shapes = ops.unary_union(lake_shapes)
    land_shapes = land_shapes.difference(lake_shapes)
    land_shapes = land_shapes.difference(antarctica_filter)

    # Build the canvas
    Path(__file__).parent.parent.joinpath('output/') \
        .mkdir(parents=True, exist_ok=True)
    path = Path(__file__).parent.parent.joinpath('output/%s' % name)
    path.unlink(missing_ok=True)
    canvas_builder = CanvasBuilder()
    canvas_builder.set_path(path)
    width = Cu.from_px(1280)
    height = width / 3
    canvas_builder.set_size(
        width,
        height
    )
    canvas = canvas_builder.build()

    # Now let's sort out the projection system
    crs = CRS.from_epsg(4326)
    geo_to_canvas_scale = GeoCanvasScale(
        30000,
        Cu.from_px(1)
    )
    origin_for_geo = GeoCoordinate(0, 0, crs)
    origin_for_canvas = CanvasCoordinate(width / 2, width / 16)
    wgs84_to_canvas = build_crs_to_canvas_transformer(
        crs=CRS.from_proj4('+proj=aea +lat_1=-20 +lat_2=0 +lon_0=0 +lat_0=0 +x_0=0 +y_0=0'),
        data_crs=crs,
        scale=geo_to_canvas_scale,
        origin_for_geo=origin_for_geo,
        origin_for_canvas=origin_for_canvas
    )

    # Finally, let's get to rendering stuff!
    land_shapes_canvas = ops.transform(
        wgs84_to_canvas,
        land_shapes
    )

    polygon_drawer = PolygonDrawer()
    polygon_drawer.fill_color = land_color
    polygon_drawer.geoms = [land_shapes_canvas]
    polygon_drawer.draw(canvas)

    canvas.close()


if __name__ == '__main__':
    render()
