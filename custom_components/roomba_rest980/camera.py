"""Camera platform for Roomba map visualization."""

import io
import logging
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Map rendering constants
MAP_WIDTH = 800
MAP_HEIGHT = 600
BACKGROUND_COLOR = (240, 240, 240)  # Light gray
WALL_COLOR = (50, 50, 50)  # Dark gray
ROOM_COLORS = [
    (173, 216, 230),  # Light blue
    (144, 238, 144),  # Light green
    (255, 182, 193),  # Light pink
    (255, 255, 224),  # Light yellow
    (221, 160, 221),  # Plum
    (175, 238, 238),  # Pale turquoise
    (255, 218, 185),  # Peach puff
    (230, 230, 250),  # Lavender
]
ROOM_BORDER_COLOR = (100, 100, 100)  # Gray
TEXT_COLOR = (0, 0, 0)  # Black

# Zone colors
KEEPOUT_ZONE_COLOR = (255, 0, 0, 100)  # Red with transparency
KEEPOUT_ZONE_BORDER = (200, 0, 0)  # Dark red
CLEAN_ZONE_COLOR = (0, 255, 0, 100)  # Green with transparency
CLEAN_ZONE_BORDER = (0, 150, 0)  # Dark green
OBSERVED_ZONE_COLOR = (255, 165, 0, 80)  # Orange with transparency
OBSERVED_ZONE_BORDER = (255, 140, 0)  # Dark orange


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Roomba map camera."""
    _LOGGER.debug("Setting up camera platform for entry %s", entry.entry_id)

    cloudCoordinator = hass.data[DOMAIN].get(entry.entry_id + "_cloud")

    if not cloudCoordinator:
        _LOGGER.warning("No cloud coordinator found for camera setup")
        return

    if not cloudCoordinator.data:
        _LOGGER.warning("Cloud coordinator has no data yet for camera setup")
        return

    entities = []
    blid = hass.data[DOMAIN].get(entry.entry_id + "_blid", "unknown")
    _LOGGER.debug("Using BLID: %s for camera setup", blid)

    if blid != "unknown" and blid in cloudCoordinator.data:
        cloud_data = cloudCoordinator.data[blid]
        _LOGGER.debug("Found cloud data for BLID %s", blid)

        if "pmaps" in cloud_data:
            _LOGGER.debug("Found %d pmaps in cloud data", len(cloud_data["pmaps"]))
            for pmap in cloud_data["pmaps"]:
                pmap_id = pmap.get("pmap_id", "unknown")
                umf_key = f"pmap_umf_{pmap_id}"
                _LOGGER.debug("Checking for UMF data key: %s", umf_key)

                if umf_key in cloud_data:
                    _LOGGER.info("Creating camera entity for pmap %s", pmap_id)
                    entities.append(
                        RoombaMapCamera(
                            cloudCoordinator, entry, pmap_id, cloud_data[umf_key]
                        )
                    )
                else:
                    _LOGGER.warning(
                        "No UMF data found for pmap %s (key: %s)", pmap_id, umf_key
                    )
        else:
            _LOGGER.warning("No pmaps found in cloud data")
    else:
        _LOGGER.warning("BLID %s not found in cloud data", blid)

    if entities:
        _LOGGER.info("Adding %d camera entities", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.warning("No camera entities created")


class RoombaMapCamera(Camera):
    """Camera entity that renders Roomba map data as an image."""

    def __init__(
        self, coordinator, entry, pmap_id: str, umf_data: dict[str, Any]
    ) -> None:
        """Initialize the map camera."""
        super().__init__()
        self._coordinator = coordinator
        self._entry = entry
        self._pmap_id = pmap_id
        self._umf_data = umf_data

        # Extract map info
        maps = umf_data.get("maps", [])
        if maps:
            map_data = maps[0]
            self._map_header = map_data.get("map_header", {})
            self._regions = map_data.get("regions", [])
            self._points2d = map_data.get("points2d", [])  # Coordinate points

            # Extract zone data
            self._keepout_zones = map_data.get("keepoutzones", [])
            self._clean_zones = map_data.get("zones", [])
            self._observed_zones = map_data.get("observed_zones", [])
        else:
            self._map_header = {}
            self._regions = []
            self._points2d = []
            self._keepout_zones = []
            self._clean_zones = []
            self._observed_zones = []

        # Camera attributes
        self._attr_name = f"Roomba Map - {self._map_header.get('name', 'Unknown')}"
        self._attr_unique_id = f"{entry.entry_id}_map_{pmap_id}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "iRobot",
        }

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return camera image."""
        try:
            return self._render_map()
        except Exception as e:
            _LOGGER.error("Error rendering map image: %s", e)
            return None

    def _render_map(self) -> bytes:
        """Render the map as a PNG image."""
        # Create image
        img = Image.new("RGB", (MAP_WIDTH, MAP_HEIGHT), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(img)

        if not self._points2d or not self._regions:
            # Draw "No Map Data" message
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except OSError:
                font = ImageFont.load_default()

            text = "No Map Data Available"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (MAP_WIDTH - text_width) // 2
            y = (MAP_HEIGHT - text_height) // 2
            draw.text((x, y), text, fill=TEXT_COLOR, font=font)

        else:
            # Calculate map bounds from points2d
            if self._points2d:
                # Extract all coordinates
                all_coords = [
                    point["coordinates"]
                    for point in self._points2d
                    if "coordinates" in point
                ]

                if all_coords:
                    # Find min/max coordinates
                    x_coords = [coord[0] for coord in all_coords if len(coord) >= 2]
                    y_coords = [coord[1] for coord in all_coords if len(coord) >= 2]

                    if x_coords and y_coords:
                        min_x, max_x = min(x_coords), max(x_coords)
                        min_y, max_y = min(y_coords), max(y_coords)

                        # Calculate scale to fit image
                        map_width = max_x - min_x
                        map_height = max_y - min_y

                        if map_width > 0 and map_height > 0:
                            scale_x = (
                                MAP_WIDTH - 40
                            ) / map_width  # Leave 20px margin on each side
                            scale_y = (MAP_HEIGHT - 40) / map_height
                            scale = min(scale_x, scale_y)

                            # Center the map
                            offset_x = (
                                MAP_WIDTH - map_width * scale
                            ) / 2 - min_x * scale
                            offset_y = (
                                MAP_HEIGHT - map_height * scale
                            ) / 2 - min_y * scale

                            # Draw rooms
                            self._draw_regions(draw, offset_x, offset_y, scale)

                            # Draw coordinate points (walls/obstacles)
                            self._draw_points(draw, offset_x, offset_y, scale)

                            # Draw zones (keepout, clean, observed)
                            self._draw_zones(draw, offset_x, offset_y, scale)

        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        return img_bytes.getvalue()

    def _draw_regions(
        self, draw: ImageDraw.ImageDraw, offset_x: float, offset_y: float, scale: float
    ) -> None:
        """Draw room regions on the map."""
        for i, region in enumerate(self._regions):
            if "geometry" not in region:
                continue

            geometry = region["geometry"]
            if geometry.get("type") != "polygon":
                continue

            # Get coordinates by ID references
            polygon_ids = geometry.get("ids", [])
            room_color = ROOM_COLORS[i % len(ROOM_COLORS)]

            for polygon_id_list in polygon_ids:
                if not isinstance(polygon_id_list, list):
                    continue

                # Find coordinates for this polygon
                polygon_coords = []
                for coord_id in polygon_id_list:
                    coord = self._find_coordinate_by_id(coord_id)
                    if coord:
                        # Transform coordinate to image space
                        x = coord[0] * scale + offset_x
                        y = MAP_HEIGHT - (coord[1] * scale + offset_y)  # Flip Y axis
                        polygon_coords.append((x, y))

                if len(polygon_coords) >= 3:  # Need at least 3 points for polygon
                    # Fill polygon
                    draw.polygon(
                        polygon_coords,
                        fill=room_color,
                        outline=ROOM_BORDER_COLOR,
                        width=2,
                    )

                    # Add room label
                    room_name = region.get("name", f"Room {i + 1}")
                    self._draw_room_label(draw, polygon_coords, room_name)

    def _draw_points(
        self, draw: ImageDraw.ImageDraw, offset_x: float, offset_y: float, scale: float
    ) -> None:
        """Draw coordinate points (walls, obstacles) on the map."""
        for point in self._points2d:
            coordinates = point.get("coordinates", [])
            if len(coordinates) >= 2:
                x = coordinates[0] * scale + offset_x
                y = MAP_HEIGHT - (coordinates[1] * scale + offset_y)  # Flip Y axis
                draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=WALL_COLOR)

    def _find_coordinate_by_id(self, coord_id: str) -> list[float] | None:
        """Find coordinate data by ID reference."""
        for point in self._points2d:
            if point.get("id") == coord_id:
                return point.get("coordinates")
        return None

    def _draw_room_label(
        self,
        draw: ImageDraw.ImageDraw,
        polygon_coords: list[tuple[float, float]],
        text: str,
    ) -> None:
        """Draw room name label in the center of the polygon."""
        if not polygon_coords:
            return

        # Calculate centroid
        x_sum = sum(coord[0] for coord in polygon_coords)
        y_sum = sum(coord[1] for coord in polygon_coords)
        centroid_x = x_sum / len(polygon_coords)
        centroid_y = y_sum / len(polygon_coords)

        # Draw text
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = centroid_x - text_width / 2
        y = centroid_y - text_height / 2

        # Draw text background
        draw.rectangle(
            [x - 2, y - 2, x + text_width + 2, y + text_height + 2],
            fill=(255, 255, 255, 180),
        )
        draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    def _draw_zones(
        self, draw: ImageDraw.ImageDraw, offset_x: float, offset_y: float, scale: float
    ) -> None:
        """Draw keepout zones, clean zones, and observed zones on the map."""

        # Draw keepout zones (red)
        for zone in self._keepout_zones:
            self._draw_zone_polygon(
                draw,
                zone,
                offset_x,
                offset_y,
                scale,
                KEEPOUT_ZONE_COLOR[:3],
                KEEPOUT_ZONE_BORDER,
                "KEEPOUT",
            )

        # Draw clean zones (green)
        for zone in self._clean_zones:
            zone_name = zone.get("name", "Clean Zone")
            self._draw_zone_polygon(
                draw,
                zone,
                offset_x,
                offset_y,
                scale,
                CLEAN_ZONE_COLOR[:3],
                CLEAN_ZONE_BORDER,
                zone_name,
            )

        # Draw observed zones (orange)
        for zone in self._observed_zones:
            zone_name = zone.get("name", "Observed")
            self._draw_zone_polygon(
                draw,
                zone,
                offset_x,
                offset_y,
                scale,
                OBSERVED_ZONE_COLOR[:3],
                OBSERVED_ZONE_BORDER,
                zone_name,
            )

    def _draw_zone_polygon(
        self,
        draw: ImageDraw.ImageDraw,
        zone: dict[str, Any],
        offset_x: float,
        offset_y: float,
        scale: float,
        fill_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
        label: str,
    ) -> None:
        """Draw a single zone polygon."""
        if "geometry" not in zone:
            return

        geometry = zone["geometry"]
        if geometry.get("type") != "polygon":
            return

        # Get coordinates by ID references
        polygon_ids = geometry.get("ids", [])

        for polygon_id_list in polygon_ids:
            if not isinstance(polygon_id_list, list):
                continue

            # Find coordinates for this polygon
            polygon_coords = []
            for coord_id in polygon_id_list:
                coord = self._find_coordinate_by_id(coord_id)
                if coord:
                    # Transform coordinate to image space
                    x = coord[0] * scale + offset_x
                    y = MAP_HEIGHT - (coord[1] * scale + offset_y)  # Flip Y axis
                    polygon_coords.append((x, y))

            if len(polygon_coords) >= 3:  # Need at least 3 points for polygon
                # Create a semi-transparent overlay for zones
                # Since PIL doesn't support alpha in polygon fill directly,
                # we'll use a dashed/dotted border style for zones

                # Draw polygon outline with dashes
                self._draw_dashed_polygon(draw, polygon_coords, border_color, 3)

                # Draw zone label
                if polygon_coords and label:
                    # Calculate centroid for label placement
                    x_sum = sum(coord[0] for coord in polygon_coords)
                    y_sum = sum(coord[1] for coord in polygon_coords)
                    centroid_x = x_sum / len(polygon_coords)
                    centroid_y = y_sum / len(polygon_coords)

                    self._draw_zone_label(
                        draw, centroid_x, centroid_y, label, border_color
                    )

    def _draw_dashed_polygon(
        self,
        draw: ImageDraw.ImageDraw,
        coords: list[tuple[float, float]],
        color: tuple,
        width: int,
    ) -> None:
        """Draw a dashed polygon outline."""
        if len(coords) < 3:
            return

        # Draw dashed lines between consecutive points
        for i in range(len(coords)):
            start = coords[i]
            end = coords[(i + 1) % len(coords)]

            # Calculate distance and draw dashed line
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            distance = (dx**2 + dy**2) ** 0.5

            if distance > 0:
                # Draw dashes every 10 pixels
                dash_length = 10
                gap_length = 5
                total_length = dash_length + gap_length

                steps = int(distance / total_length)
                for step in range(steps):
                    t1 = step * total_length / distance
                    t2 = min((step * total_length + dash_length) / distance, 1.0)

                    x1 = start[0] + t1 * dx
                    y1 = start[1] + t1 * dy
                    x2 = start[0] + t2 * dx
                    y2 = start[1] + t2 * dy

                    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

    def _draw_dashed_line(
        self,
        draw: ImageDraw.ImageDraw,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple[int, int, int],
        width: int = 2,
        dash_length: int = 10,
    ) -> None:
        """Draw a dashed line between two points."""
        x1, y1 = start
        x2, y2 = end

        # Calculate line length and direction
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5

        if length == 0:
            return

        # Normalize direction
        dx_norm = dx / length
        dy_norm = dy / length

        # Draw dashes
        current_pos = 0
        while current_pos < length:
            # Calculate dash start and end
            dash_start_x = x1 + dx_norm * current_pos
            dash_start_y = y1 + dy_norm * current_pos

            dash_end_pos = min(current_pos + dash_length, length)
            dash_end_x = x1 + dx_norm * dash_end_pos
            dash_end_y = y1 + dy_norm * dash_end_pos

            # Draw the dash
            draw.line(
                [(dash_start_x, dash_start_y), (dash_end_x, dash_end_y)],
                fill=color,
                width=width,
            )

            # Move to next dash (skip gap)
            current_pos += dash_length * 2

    def _draw_zone_label(
        self,
        draw: ImageDraw.ImageDraw,
        x: float,
        y: float,
        text: str,
        color: tuple[int, int, int],
    ) -> None:
        """Draw a zone label at the specified position."""
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text
        text_x = x - text_width / 2
        text_y = y - text_height / 2

        # Draw text background (semi-transparent white)
        draw.rectangle(
            [text_x - 2, text_y - 2, text_x + text_width + 2, text_y + text_height + 2],
            fill=(255, 255, 255, 200),
        )

        # Draw text
        draw.text((text_x, text_y), text, fill=color, font=font)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return camera attributes."""
        return {
            "pmap_id": self._pmap_id,
            "map_name": self._map_header.get("name", "Unknown"),
            "resolution": self._map_header.get("resolution", 0),
            "area": self._map_header.get("area", 0),
            "learning_percentage": self._map_header.get("learning_percentage", 0),
            "regions_count": len(self._regions),
            "keepout_zones_count": len(self._keepout_zones),
            "clean_zones_count": len(self._clean_zones),
            "observed_zones_count": len(self._observed_zones),
            "points_count": len(self._points2d),
            "calibration": self.calibration,
        }

    @property
    def calibration(self) -> list[dict[str, dict[str, int]]] | None:
        """Return calibration points for vacuum card integration."""
        if not self._points2d or not self._regions:
            return None

        # Calculate map bounds from points2d
        all_coords = [
            point["coordinates"]
            for point in self._points2d
            if "coordinates" in point and len(point["coordinates"]) >= 2
        ]

        if not all_coords:
            return None

        # Find min/max coordinates to determine map bounds
        x_coords = [coord[0] for coord in all_coords]
        y_coords = [coord[1] for coord in all_coords]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        map_width = max_x - min_x
        map_height = max_y - min_y

        if map_width <= 0 or map_height <= 0:
            return None

        # Calculate scale to fit image (same as in _render_map)
        scale_x = (MAP_WIDTH - 40) / map_width
        scale_y = (MAP_HEIGHT - 40) / map_height
        scale = min(scale_x, scale_y)

        # Center the map (same as in _render_map)
        offset_x = (MAP_WIDTH - map_width * scale) / 2 - min_x * scale
        offset_y = (MAP_HEIGHT - map_height * scale) / 2 - min_y * scale

        # Define calibration center and differential (similar to built-in method)
        # Use center of the vacuum coordinate space
        calibration_center_x = (min_x + max_x) / 2
        calibration_center_y = (min_y + max_y) / 2
        # Use a smaller differential for finer calibration (about 1/8 of the map size)
        calibration_diff_x = map_width / 8
        calibration_diff_y = map_height / 8

        # Create three calibration points (center, center+diff_x, center+diff_y)
        vacuum_points = [
            (calibration_center_x, calibration_center_y),
            (calibration_center_x + calibration_diff_x, calibration_center_y),
            (calibration_center_x, calibration_center_y + calibration_diff_y),
        ]

        calibration_points = []
        for vacuum_x, vacuum_y in vacuum_points:
            # Transform vacuum coordinates to image coordinates
            img_x = vacuum_x * scale + offset_x
            img_y = MAP_HEIGHT - (vacuum_y * scale + offset_y)  # Flip Y axis

            calibration_points.append(
                {
                    "vacuum": {"x": int(vacuum_x), "y": int(vacuum_y)},
                    "map": {"x": int(img_x), "y": int(img_y)},
                }
            )

        return calibration_points
