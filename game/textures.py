"""Pre-loads all the textures needed by the game and stores them for later use."""
from __future__ import annotations

# Builtin
import logging
import pathlib

# Pip
import arcade

# Custom
from game.constants.game_object import SPRITE_SIZE

__all__ = (
    "grid_pos_to_pixel",
    "moving_textures",
    "non_moving_textures",
)

# Get the logger
logger = logging.getLogger(__name__)


def grid_pos_to_pixel(x: float, y: float) -> tuple[float, float]:
    """Calculate the x and y position based on the game map or vector field position.

    Parameters
    ----------
    x: float
        The x position in the game map or vector field.
    y: float
        The x position in the game map or vector field.

    Returns
    -------
    tuple[float, float]
        The x and y position of a sprite on the screen.
    """
    # Calculate the position on screen
    return (
        x * SPRITE_SIZE + SPRITE_SIZE / 2,
        y * SPRITE_SIZE + SPRITE_SIZE / 2,
    )


# Create the texture path
texture_path = pathlib.Path(__file__).resolve().parent / "resources" / "textures"

# Create a dictionary to hold all the filenames for the non-moving textures
non_moving_filenames = {
    "tiles": [
        "floor.png",
        "wall.png",
    ],
    "items": [
        "health_potion.png",
        "armour_potion.png",
        "health_boost_potion.png",
        "armour_boost_potion.png",
        "speed_boost_potion.png",
        "fire_rate_boost_potion.png",
        "shop.png",
    ],
}

# Create a dictionary to hold all the filenames for the non-moving textures
moving_filenames = {
    "player": {
        "idle": ["player_idle.png"],
    },
    "enemy": {
        "idle": ["enemy_idle.png"],
    },
}

# Create the non-moving textures
non_moving_textures: dict[str, list[arcade.Texture]] = {
    key: [arcade.load_texture(texture_path.joinpath(filename)) for filename in value]
    for key, value in non_moving_filenames.items()
}
logger.info(
    "Created non moving texture dict with %d sections", len(non_moving_textures)
)

# Create the moving textures
moving_textures: dict[str, dict[str, list[list[arcade.Texture]]]] = {
    key: {
        animation_type: [
            arcade.load_texture_pair(texture_path.joinpath(filename))
            for filename in sublist
        ]
        for animation_type, sublist in value.items()
    }
    for key, value in moving_filenames.items()
}
logger.info("Created moving texture dict with %d sections", len(moving_textures))
