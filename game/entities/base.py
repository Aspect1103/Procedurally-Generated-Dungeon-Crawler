from __future__ import annotations

# Builtin
import logging
from typing import TYPE_CHECKING

# Pip
import arcade

# Custom
from game.constants.entity import (
    ARMOUR_REGEN_AMOUNT,
    ARMOUR_REGEN_WAIT,
    SPRITE_SCALE,
    EntityID,
)
from game.constants.generation import TileType
from game.entities.attack import AttackBase
from game.textures import pos_to_pixel

if TYPE_CHECKING:
    from game.constants.entity import (
        AreaOfEffectAttackData,
        AttackData,
        BaseData,
        EnemyData,
        EntityData,
        MeleeAttackData,
        PlayerData,
        RangedAttackData,
        UpgradeData,
    )
    from game.entities.player import Player
    from game.views.game import Game

# Get the logger
logger = logging.getLogger(__name__)


class IndicatorBar:
    """
    Represents a bar which can display information about an entity.

    Parameters
    ----------
    owner: Entity
        The owner of this indicator bar.
    position: tuple[float, float]
        The initial position of the bar.
    full_color: arcade.Color
        The color of the bar.
    background_color: arcade.Color
        The background color of the bar.
    width: int
        The width of the bar.
    height: int
        The height of the bar.
    border_size: int
        The size of the bar's border.
    """

    def __init__(
        self,
        owner: Entity,
        position: tuple[float, float] = (0, 0),
        full_color: arcade.Color = arcade.color.GREEN,
        background_color: arcade.Color = arcade.color.BLACK,
        width: int = 50,
        height: int = 4,
        border_size: int = 4,
    ) -> None:
        # Store the reference to the owner
        self.owner: Entity = owner

        # Set the needed size variables
        self._box_width: int = width
        self._box_height: int = height
        self._half_box_width: int = self._box_width // 2
        self._center_x: float = 0.0
        self._center_y: float = 0.0
        self._fullness: float = 0.0

        # Create the boxes needed to represent the indicator bar
        self._background_box: arcade.SpriteSolidColor = arcade.SpriteSolidColor(
            self._box_width + border_size,
            self._box_height + border_size,
            background_color,
        )
        self._full_box: arcade.SpriteSolidColor = arcade.SpriteSolidColor(
            self._box_width,
            self._box_height,
            full_color,
        )
        self.owner.game.indicator_bar_sprites.append(self._background_box)
        self.owner.game.indicator_bar_sprites.append(self._full_box)

        # Set the fullness and position of the bar
        self.fullness: float = 1.0
        self.position: tuple[float, float] = position

    def __repr__(self) -> str:
        return f"<IndicatorBar (Owner={self.owner})>"

    @property
    def background_box(self) -> arcade.SpriteSolidColor:
        """Returns the background box of the indicator bar."""
        return self._background_box

    @property
    def full_box(self) -> arcade.SpriteSolidColor:
        """Returns the full box of the indicator bar."""
        return self._full_box

    @property
    def fullness(self) -> float:
        """Returns the fullness of the bar."""
        return self._fullness

    @fullness.setter
    def fullness(self, new_fullness: float) -> None:
        """
        Sets the fullness of the bar.

        Parameters
        ----------
        new_fullness: float
            The new fullness of the bar

        Raises
        ------
        ValueError
            The fullness must be between 0.0 and 1.0.
        """
        # Check if new_fullness if valid
        if not (0.0 <= new_fullness <= 1.0):
            raise ValueError(
                f"Got {new_fullness}, but fullness must be between 0.0 and 1.0."
            )

        # Set the size of the bar
        self._fullness = new_fullness
        if new_fullness == 0.0:
            # Set the full_box to not be visible since it is not full anymore
            self.full_box.visible = False
        else:
            # Set the full_box to be visible incase it wasn't then update the bar
            self.full_box.visible = True
            self.full_box.width = self._box_width * new_fullness
            self.full_box.left = self._center_x - (self._box_width // 2)

    @property
    def position(self) -> tuple[float, float]:
        """Returns the current position of the bar."""
        return self._center_x, self._center_y

    @position.setter
    def position(self, new_position: tuple[float, float]) -> None:
        """
        Sets the new position of the bar.

        Parameters
        ----------
        new_position: tuple[float, float]
            The new position of the bar.
        """
        # Check if the position has changed. If so, change the bar's position
        if new_position != self.position:
            self._center_x, self._center_y = new_position
            self.background_box.position = new_position
            self.full_box.position = new_position

            # Make sure full_box is to the left of the bar instead of the middle
            self.full_box.left = self._center_x - (self._box_width // 2)


class Entity(arcade.Sprite):
    """
    Represents an entity in the game.

    Parameters
    ----------
    game: Game
        The game view. This is passed so the entity can have a reference to it.
    x: int
        The x position of the entity in the game map.
    y: int
        The y position of the entity in the game map.

    Attributes
    ----------
    attack_algorithms: list[AttackBase]
        A list of the entity's attack algorithms.
    current_attack_index: int
        The index of the currently selected attack.
    direction: float
        The angle the entity is facing.
    facing: int
        The direction the entity is facing. 0 is right and 1 is left.
    time_since_last_attack: float
        The time since the last attack.
    time_out_of_combat: float
        The time since the entity was last in combat.
    time_since_armour_regen: float
        The time since the entity last regenerated armour.
    """

    # Class variables
    entity_id: EntityID = EntityID.ENTITY
    entity_type: BaseData | None = None

    def __init__(
        self,
        game: Game,
        x: int,
        y: int,
    ) -> None:
        super().__init__(scale=SPRITE_SCALE)
        self.game: Game = game
        self.center_x, self.center_y = pos_to_pixel(x, y)
        self.texture: arcade.Texture = self.entity_data.textures["idle"][0][0]
        self.attack_algorithms: list[AttackBase] = [
            algorithm.attack_type.value(self, algorithm.attack_cooldown)
            for algorithm in self.attacks
        ]
        self._entity_state: dict[str, int | float] = {
            "health": self.upgrade_data[0].level_one,
            "max health": self.upgrade_data[0].level_one,
            "armour": self.upgrade_data[1].level_one,
            "max armour": self.upgrade_data[1].level_one,
            "max velocity": self.upgrade_data[2].level_one,
            "armour regen cooldown": self.upgrade_data[3].level_one,
            "bonus attack cooldown": 0,
        }
        self.current_attack_index: int = 0
        self.direction: float = 0
        self.facing: int = 0
        self.time_since_last_attack: float = 0
        self.time_out_of_combat: float = 0
        self.time_since_armour_regen: float = self.armour_regen_cooldown

    def __repr__(self) -> str:
        return f"<Entity (Position=({self.center_x}, {self.center_y}))>"

    @property
    def entity_data(self) -> EntityData:
        """
        Gets the general entity data.

        Returns
        -------
        EntityData
            The general entity data.
        """
        # Make sure the entity type is valid
        assert self.entity_type is not None

        # Return the entity data
        return self.entity_type.entity_data

    @property
    def player_data(self) -> PlayerData:
        """
        Gets the player data if it exists.

        Returns
        -------
        PlayerData
            The player data.
        """
        # Make sure the entity type is valid
        assert self.entity_type is not None
        assert self.entity_type.player_data is not None

        # Return the player data
        return self.entity_type.player_data

    @property
    def enemy_data(self) -> EnemyData:
        """
        Gets the enemy data if it exists.

        Returns
        -------
        EnemyData
            The enemy data.
        """
        # Make sure the entity type is valid
        assert self.entity_type is not None
        assert self.entity_type.enemy_data is not None

        # Return the enemy data
        return self.entity_type.enemy_data

    @property
    def attacks(self) -> list[AttackData]:
        """
        Gets all the attacks the entity has.

        Returns
        -------
        list[AttackData]
            The entity's attacks.
        """
        # Make sure the entity type is valid
        assert self.entity_type is not None

        # Return the enemy data
        return self.entity_type.get_all_attacks()

    @property
    def ranged_attack_data(self) -> RangedAttackData:
        """
        Gets the ranged attack data if the entity has the attack.

        Returns
        -------
        RangedAttackData
            The ranged attack data.
        """
        # Make sure the entity type is valid
        assert self.entity_type is not None
        assert self.entity_type.ranged_attack_data is not None

        # Return the ranged attack data
        return self.entity_type.ranged_attack_data

    @property
    def melee_attack_data(self) -> MeleeAttackData:
        """
        Gets the melee attack data if the entity has the attack.

        Returns
        -------
        MeleeAttackData
            The melee attack data.
        """
        # Make sure the entity type is valid
        assert self.entity_type is not None
        assert self.entity_type.melee_attack_data is not None

        # Return the melee attack data
        return self.entity_type.melee_attack_data

    @property
    def area_of_effect_attack_data(self) -> AreaOfEffectAttackData:
        """
        Gets the area of effect attack data if the entity has the attack.

        Returns
        -------
        AreaOfEffectAttackData
            The area of effect attack data.
        """
        # Make sure the entity type is valid
        assert self.entity_type is not None
        assert self.entity_type.area_of_effect_attack_data is not None

        # Return the area of effect attack data
        return self.entity_type.area_of_effect_attack_data

    @property
    def current_attack(self) -> AttackBase:
        """
        Gets the currently selected attack algorithm.

        Returns
        -------
        AttackBase
            The currently selected attack algorithm.
        """
        return self.attack_algorithms[self.current_attack_index]

    @property
    def upgrade_data(self) -> list[UpgradeData]:
        """
        Gets the upgrades that are available to the entity.

        Returns
        -------
        list[UpgradeData]
            The upgrades that are available to the entity.
        """
        return list(self.entity_data.upgrade_data)

    @property
    def health(self) -> int:
        """
        Gets the entity's health.

        Returns
        -------
        int
            The entity's health
        """
        return int(self._entity_state["health"])

    @health.setter
    def health(self, value: int) -> None:
        """
        Sets the entity's health.

        Parameters
        ----------
        value: int
            The new health value.
        """
        self._entity_state["health"] = value

    @property
    def max_health(self) -> int:
        """
        Gets the player's maximum health.

        Returns
        -------
        int
            The player's maximum health.
        """
        return int(self._entity_state["max health"])

    @max_health.setter
    def max_health(self, value: int) -> None:
        """
        Sets the player's maximum health.


        Parameters
        ----------
        value: int
            The new maximum health value.
        """
        self._entity_state["max health"] = value

    @property
    def armour(self) -> int:
        """
        Gets the entity's armour.

        Returns
        -------
        int
            The entity's armour.
        """
        return int(self._entity_state["armour"])

    @armour.setter
    def armour(self, value: int) -> None:
        """
        Sets the entity's armour.

        Parameters
        ----------
        value: int
            The new armour value.
        """
        self._entity_state["armour"] = value

    @property
    def max_armour(self) -> int:
        """
        Gets the player's maximum armour.

        Returns
        -------
        int
            The player's maximum armour
        """
        return int(self._entity_state["max armour"])

    @max_armour.setter
    def max_armour(self, value: int) -> None:
        """
        Sets the player's maximum armour.

        Parameters
        ----------
        value: int
            The new maximum armour value.
        """
        self._entity_state["max armour"] = value

    @property
    def max_velocity(self) -> float:
        """
        Gets the entity's max velocity.

        Returns
        -------
        float
            The entity's max velocity.
        """
        return self._entity_state["max velocity"]

    @max_velocity.setter
    def max_velocity(self, value: float) -> None:
        """
        Sets the entity's max velocity.

        Parameters
        ----------
        value: float
            The new max velocity value.
        """
        self._entity_state["max velocity"] = value
        self.pymunk.max_velocity = value

    @property
    def armour_regen_cooldown(self) -> float:
        """
        Gets the entity's armour regen cooldown

        Returns
        -------
        float
            The entity's armour regen cooldown.
        """
        return self._entity_state["armour regen cooldown"]

    @armour_regen_cooldown.setter
    def armour_regen_cooldown(self, value: float) -> None:
        """
        Sets the entity's armour regen cooldown.

        Parameters
        ----------
        value: float
            The new armour regen cooldown value.
        """
        self._entity_state["armour regen cooldown"] = value

    @property
    def bonus_attack_cooldown(self) -> float:
        """
        Gets the entity's bonus attack cooldown

        Returns
        -------
        float
            The entity's bonus attack cooldown.
        """
        return self._entity_state["bonus attack cooldown"]

    @bonus_attack_cooldown.setter
    def bonus_attack_cooldown(self, value: float) -> None:
        """
        Sets the entity's bonus attack cooldown.

        Parameters
        ----------
        value: float
            The new bonus attack cooldown.
        """
        self._entity_state["bonus attack cooldown"] = value

    def on_update(self, delta_time: float = 1 / 60) -> None:
        """
        Processes movement and game logic.

        Parameters
        ----------
        delta_time: float
            Time interval since the last time the function was called.

        Raises
        ------
        NotImplementedError
            The function is not implemented.
        """
        raise NotImplementedError

    def deal_damage(self, damage: int) -> None:
        """
        Deals damage to an entity.

        Parameters
        ----------
        damage: int
            The amount of health to take away from the entity.
        """
        # Check if the entity still has armour
        if self.armour > 0:
            # Damage the armour
            self.armour -= damage
            if self.armour < 0:
                # Damage exceeds armour so damage health
                self.health += self.armour
                self.armour = 0
        else:
            # Damage the health
            self.health -= damage
        self.update_indicator_bars()
        logger.debug(f"Dealing {damage} to {self}")

        # Check if the entity should be killed
        if self.health <= 0:
            self.remove_from_sprite_lists()
            self.remove_indicator_bars()
            logger.info(f"Killed {self}")

    def check_armour_regen(self, delta_time: float) -> None:
        """
        Checks if the entity can regenerate armour.

        Parameters
        ----------
        delta_time:
            Time interval since the last time the function was called.
        """
        # Check if the entity has been out of combat for ARMOUR_REGEN_WAIT seconds
        if self.time_out_of_combat >= ARMOUR_REGEN_WAIT:
            # Check if enough has passed since the last armour regen
            if self.time_since_armour_regen >= self.armour_regen_cooldown:
                # Regen armour
                self.armour += ARMOUR_REGEN_AMOUNT
                self.time_since_armour_regen = 0
                self.update_indicator_bars()
                logger.debug(f"Regenerated armour for {self}")
            else:
                # Increment the counter since not enough time has passed
                self.time_since_armour_regen += delta_time
        else:
            # Increment the counter since not enough time has passed
            self.time_out_of_combat += delta_time

    def update_indicator_bars(self) -> None:
        """Updates the entity's indicator bars."""
        raise NotImplementedError

    def remove_indicator_bars(self) -> None:
        """Removes the indicator bars after the entity is killed."""
        raise NotImplementedError

    def attack(self) -> None:
        """
        Runs the entity's current attack algorithm.

        Raises
        ------
        NotImplementedError
            The function is not implemented.
        """
        raise NotImplementedError


class Tile(arcade.Sprite):
    """
    Represents a tile in the game.

    Parameters
    ----------
    x: int
        The x position of the tile in the game map.
    y: int
        The y position of the tile in the game map.

    Attributes
    ----------
    center_x: float
        The x position of the tile on the screen.
    center_y: float
        The y position of the tile on the screen.
    texture: arcade.Texture
        The sprite which represents this tile.
    """

    # Class variables
    raw_texture: arcade.Texture | None = None
    is_static: bool = False

    def __init__(
        self,
        x: int,
        y: int,
    ) -> None:
        super().__init__(scale=SPRITE_SCALE)
        self.center_x, self.center_y = pos_to_pixel(x, y)
        self.texture: arcade.Texture = self.raw_texture

    def __repr__(self) -> str:
        return f"<Tile (Position=({self.center_x}, {self.center_y}))>"


class Item(Tile):
    """
    Represents an item in the game.

    Parameters
    ----------
    game: Game
        The game view. This is passed so the item can have a reference to it.
    x: int
        The x position of the item in the game map.
    y: int
        The y position of the item in the game map.
    """

    # Class variables
    item_id: TileType = TileType.NONE
    item_text: str = "Press R to activate"

    def __init__(
        self,
        game: Game,
        x: int,
        y: int,
    ) -> None:
        super().__init__(x, y)
        self.game: Game = game

    def __repr__(self) -> str:
        return f"<Item (Position=({self.center_x}, {self.center_y}))>"

    @property
    def player(self) -> Player:
        """
        Gets the player object for ease of access.

        Returns
        -------
        Player
            The player object.
        """
        # Make sure the player object is valid
        assert self.game.player is not None

        # Return the player object
        return self.game.player

    def item_activate(self) -> bool:
        """
        Called when the item is activated by the player. Override this to add item
        activate functionality.

        Returns
        -------
        bool
            Whether the item activation was successful or not.
        """
        return False


class Collectible(Item):
    """
    Represents a collectible in the game.

    Parameters
    ----------
    game: Game
        The game view. This is passed so the collectible can have a reference to it.
    x: int
        The x position of the collectible in the game map.
    y: int
        The y position of the collectible in the game map.
    """

    # Class variables
    item_text: str = "Press E to pick up and R to activate"

    def __init__(
        self,
        game: Game,
        x: int,
        y: int,
    ) -> None:
        super().__init__(game, x, y)

    def item_pick_up(self) -> bool:
        """
        Called when the collectible is picked up by the player.

        Returns
        -------
        bool
            Whether the collectible pickup was successful or not.
        """
        # Try and add the item to the player's inventory
        if self.player.add_item_to_inventory(self):
            # Add successful
            self.remove_from_sprite_lists()

            # Activate was successful
            logger.info(f"Picked up collectible {self}")
            return True
        else:
            # Add not successful. TODO: Probably give message to user
            logger.info(f"Can't pick up collectible {self}")
            return False
