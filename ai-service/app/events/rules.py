from app.detection.schemas import BoundingBox
from app.events.schemas import Point, RestrictedZone


def bbox_centroid(bbox: BoundingBox) -> Point:
    return Point(x=bbox.x1 + bbox.width / 2, y=bbox.y1 + bbox.height / 2)


def point_in_polygon(point: Point, polygon: tuple[Point, ...]) -> bool:
    inside = False
    j = len(polygon) - 1

    for i, current in enumerate(polygon):
        previous = polygon[j]
        intersects = (current.y > point.y) != (previous.y > point.y)
        if intersects:
            x_intersection = (previous.x - current.x) * (point.y - current.y) / (
                previous.y - current.y
            ) + current.x
            if point.x < x_intersection:
                inside = not inside
        j = i

    return inside


def containing_zones(bbox: BoundingBox, zones: tuple[RestrictedZone, ...]) -> list[RestrictedZone]:
    centroid = bbox_centroid(bbox)
    return [zone for zone in zones if point_in_polygon(centroid, zone.polygon)]

