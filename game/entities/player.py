from __future__ import annotations

# Builtin
from typing import TYPE_CHECKING

# Pip
import arcade

# Custom
from entities.entity import Entity, EntityID
from shaders.melee import MeleeShader

if TYPE_CHECKING:
    from views.game import Game


class Player(Entity):
    """
    Represents the player character in the game.

    Parameters
    ----------
    game: Game
        The game view. This is passed so the player can have a reference to it.
    x: int
        The x position of the player in the game map.
    y: int
        The y position of the player in the game map.
    texture_dict: dict[str, list[list[arcade.Texture]]]
        The textures which represent this player.
    health: int
        The health of this player.

    Attributes
    ----------
    melee_shader: MeleeShader
        The OpenGL shader used to find and attack any enemies within a specific distance
        around the player based on their direction.
    """

    # Class variables
    ID: EntityID = EntityID.PLAYER

    def __init__(
        self,
        game: Game,
        x: int,
        y: int,
        texture_dict: dict[str, list[list[arcade.Texture]]],
        health: int,
    ) -> None:
        super().__init__(game, x, y, texture_dict, health)
        self.melee_shader: MeleeShader = MeleeShader(self.game)

    def __repr__(self) -> str:
        return f"<Player (Position=({self.center_x}, {self.center_y}))>"

    def on_update(self, delta_time: float = 1 / 60) -> None:
        """
        Processes player logic.

        Parameters
        ----------
        delta_time: float
            Time interval since the last time the function was called.
        """
        # Update the player's time since last attack
        self.time_since_last_attack += delta_time

    def run_melee_shader(self) -> None:
        """Runs the melee shader to get all enemies within melee range of the player."""
        # Deal melee damage to any entity that the player can attack. This is determined
        # by the melee shader
        self.melee_attack(self.melee_shader.run_shader())