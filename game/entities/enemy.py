from __future__ import annotations

# Builtin
import math
from typing import TYPE_CHECKING

# Pip
import arcade

# Custom
from constants import (
    ATTACK_COOLDOWN,
    ENEMY_ATTACK_RANGE,
    ENEMY_VIEW_DISTANCE,
    SPRITE_WIDTH,
)
from entities.ai import FollowLineOfSight
from entities.entity import Entity, EntityID

if TYPE_CHECKING:
    from views.game import Game


class Enemy(Entity):
    """
    Represents a hostile character in the game.

    Parameters
    ----------
    game: Game
        The game view. This is passed so the enemy can have a reference to it.
    x: int
        The x position of the enemy in the game map.
    y: int
        The y position of the enemy in the game map.
    texture_dict: dict[str, list[list[arcade.Texture]]]
        The textures which represent this enemy.
    health: int
        The health of this enemy.
    ai: FollowLineOfSight
        The AI which this entity uses.

    Attributes
    ----------
    line_of_sight: bool
        Whether the enemy has line of sight with the player or not
    """

    # Class variables
    ID: EntityID = EntityID.ENEMY

    def __init__(
        self,
        game: Game,
        x: int,
        y: int,
        texture_dict: dict[str, list[list[arcade.Texture]]],
        health: int,
        ai: FollowLineOfSight,
    ) -> None:
        super().__init__(game, x, y, texture_dict, health)
        self.ai: FollowLineOfSight = ai
        self.ai.owner = self
        self.line_of_sight: bool = False

    def __repr__(self) -> str:
        return f"<Enemy (Position=({self.center_x}, {self.center_y}))>"

    def on_update(self, delta_time: float = 1 / 60) -> None:
        """
        Processes enemy logic.

        Parameters
        ----------
        delta_time: float
            Time interval since the last time the function was called.
        """
        # Check if the enemy should be killed
        if self.health <= 0:
            self.remove_from_sprite_lists()
            return

        # Update the enemy's time since last attack
        self.time_since_last_attack += delta_time

        # Check if the player is not within the max view distance
        if not self.line_of_sight:
            return

        # Player is within line of sight so get the force needed to move the enemy
        horizontal, vertical = self.ai.calculate_movement(
            self.game.player, self.game.wall_sprites
        )

        # Set the needed internal variables
        self.facing = 1 if horizontal < 0 else 0
        self.direction = math.degrees(math.atan2(vertical, horizontal))

        # Apply the force
        self.physics_engines[0].apply_force(self, (horizontal, vertical))

        # Check if the player is within the attack range and can attack
        x_diff_squared = (self.game.player.center_x - self.center_x) ** 2
        y_diff_squared = (self.game.player.center_y - self.center_y) ** 2
        hypot_distance = math.sqrt(x_diff_squared + y_diff_squared)
        if (
            hypot_distance <= ENEMY_ATTACK_RANGE * SPRITE_WIDTH
            and self.time_since_last_attack >= ATTACK_COOLDOWN
        ):
            # Enemy can attack so reset the counter and attack
            self.time_since_last_attack: float = 0  # Mypy is annoying
            self.ranged_attack(self.game.bullet_sprites)

    def check_line_of_sight(self) -> None:
        """Checks if the enemy has line of sight with the player"""
        # Check for line of sight
        self.line_of_sight = arcade.has_line_of_sight(
            (self.center_x, self.center_y),
            (self.game.player.center_x, self.game.player.center_y),
            self.game.wall_sprites,
            ENEMY_VIEW_DISTANCE * SPRITE_WIDTH,
        )