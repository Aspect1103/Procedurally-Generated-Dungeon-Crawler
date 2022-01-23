from __future__ import annotations

# Pip
import arcade
from constants import SPRITE_SCALE

# Custom
from textures.textures import calculate_position, tile_textures


class Tile(arcade.Sprite):
    """
    Represents a single immovable tile in the game.

    Parameters
    ----------
    x: int
        The x position of the tile in the game map.
    y: int
        The y position of the tile in the game map.
    tile_type: int
        The numeric ID of the tile.

    Attributes
    ----------
    texture: arcade.Texture
        The sprite which represents this tile.
    center_x: float
        The x position of the tile on the screen.
    center_y: float
        The y position of the tile on the screen.
    """

    def __init__(self, x: int, y: int, tile_type: int) -> None:
        super().__init__(scale=SPRITE_SCALE)
        self.tile_type: int = tile_type
        self.texture: arcade.Texture = tile_textures[tile_type - 1]
        self.center_x, self.center_y = calculate_position(x, y)

    def __repr__(self) -> str:
        return (
            f"<Tile (Tile ID={self.tile_type}) (Position=({self.center_x},"
            f" {self.center_y}))>"
        )