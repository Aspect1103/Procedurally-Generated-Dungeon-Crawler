from __future__ import annotations

# Builtin
import logging
import math
import random
from typing import TYPE_CHECKING

# Pip
import arcade

# Custom
from game.constants.consumable import (
    ARMOUR_BOOST_POTION,
    ARMOUR_POTION,
    FIRE_RATE_BOOST_POTION,
    HEALTH_BOOST_POTION,
    HEALTH_POTION,
    SPEED_BOOST_POTION,
)
from game.constants.entity import (
    ENEMY1,
    FACING_LEFT,
    FACING_RIGHT,
    MOVEMENT_FORCE,
    PLAYER,
    SPRITE_SIZE,
)
from game.constants.general import (
    CONSUMABLE_LEVEL_MAX_RANGE,
    DAMPING,
    DEBUG_ATTACK_DISTANCE,
    DEBUG_VIEW_DISTANCE,
    ENEMY_LEVEL_MAX_RANGE,
    LEVEL_GENERATOR_INTERVAL,
)
from game.constants.generation import TileType
from game.entities.attack import AreaOfEffectAttack, MeleeAttack
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.entities.tile import Consumable, Floor, Item, Shop, Wall
from game.generation.map import Map
from game.physics import PhysicsEngine
from game.textures import pos_to_pixel
from game.views.base_view import BaseView
from game.views.inventory_view import InventoryView
from game.views.shop_view import ShopView

if TYPE_CHECKING:
    pass

# Get the logger
logger = logging.getLogger(__name__)


class EnemyConsumableLevelGenerator:
    """
    Represents generator that can be used to determine what level an enemy or consumable
    should be based on the current game level.

    Parameters
    ----------
    lower_bound: int
        The lower bound of the normal distribution function.
    upper_bound: int
        The upper bound of the normal distribution function.
    """

    __slots__ = (
        "lower_bound",
        "upper_bound",
        "random",
    )

    def __init__(
        self,
        lower_bound: int,
        upper_bound: int,
    ) -> None:
        self.lower_bound: int = lower_bound
        self.upper_bound: int = upper_bound

    def __repr__(self) -> str:
        return (
            f"<EnemyConsumableLevelGenerator (Lower bound={self.lower_bound}) (Upper"
            f" bound={self.upper_bound})>"
        )

    @classmethod
    def create_distribution(
        cls, game_level: int, max_range: int
    ) -> EnemyConsumableLevelGenerator:
        """
        Creates the boundaries and initialises the generator.

        Parameters
        ----------
        game_level: int
            The current level for the game.
        max_range: int
            The maximum difference between the lower and upper bounds.

        Returns
        -------
        EnemyConsumableLevelGenerator
            The initialised generator.
        """
        # Create the upper and lower bounds. They should both start at 1 then every
        # LEVEL_GENERATOR_INTERVAL levels, the upper bound should increase by 1.
        # Once the difference between the lower and upper bounds reaches max_range, then
        # we instead shift both of them along by 1
        upper = (game_level // LEVEL_GENERATOR_INTERVAL) + 1
        lower = 1 if upper - 1 < max_range else upper - max_range

        # Initialise the generator
        return cls(lower, upper)

    def get_level(self, level_limit: int) -> int:
        """
        Gets the level an enemy/consumable should be based on the current game level.

        Parameters
        ----------
        level_limit: int
            The maximum value that the level can be.

        Returns
        -------
        int
            The enemy/consumable level.
        """
        # Generate a random value using the generator
        random_level = random.randint(self.lower_bound, self.upper_bound)

        # Make sure the value is not over the level limit
        return min(random_level, level_limit)


class Game(BaseView):
    """
    Manages the game and its actions.

    Parameters
    ----------
    debug_mode: bool
        Whether to draw the various debug things or not.

    Attributes
    ----------
    game_map_shape: tuple[int, int] | None
        The height and width of the game map.
    player: Player | None
        The sprite for the playable character in the game.
    wall_sprites: arcade.SpriteList
        The sprite list for the wall sprites. This is only used for updating the melee
        shader.
    tile_sprites: arcade.SpriteList
        The sprite list for the tile sprites. This is used for drawing the different
        tiles.
    item_sprites: arcade.SpriteList
        The sprite list for the item sprites. This is only used for detecting player
        activity around the item.
    bullet_sprites: arcade.SpriteList
        The sprite list for the bullet sprites.
    enemy_sprites: arcade.SpriteList
        The sprite list for the enemy sprites.
    indicator_bar_sprites: arcade.SpriteList
        The sprite list for drawing the indicator bars.
    physics_engine: PhysicsEngine | None
        The physics engine which processes wall collision.
    game_camera: arcade.Camera | None
        The camera used for moving the viewport around the screen.
    gui_camera: arcade.Camera | None
        The camera used for visualising the GUI elements.
    player_status_text: arcade.Text
        The text object used for displaying the player's health and armour.
    nearest_item: game.entities.tile.Item | Consumable | None
        Stores the nearest item so the player can activate it.
    left_pressed: bool
        Whether the left key is pressed or not.
    right_pressed: bool
        Whether the right key is pressed or not.
    up_pressed: bool
        Whether the up key is pressed or not.
    down_pressed: bool
        Whether the down key is pressed or not.
    """

    def __init__(self, debug_mode: bool = False) -> None:
        super().__init__()
        self.debug_mode: bool = debug_mode
        self.background_color = arcade.color.BLACK
        self.game_map_shape: tuple[int, int] = (-1, -1)
        self.player: Player | None = None
        self.wall_sprites: arcade.SpriteList = arcade.SpriteList(use_spatial_hash=True)
        self.tile_sprites: arcade.SpriteList = arcade.SpriteList(use_spatial_hash=True)
        self.item_sprites: arcade.SpriteList = arcade.SpriteList(use_spatial_hash=True)
        self.bullet_sprites: arcade.SpriteList = arcade.SpriteList()
        self.enemy_sprites: arcade.SpriteList = arcade.SpriteList()
        self.indicator_bar_sprites: arcade.SpriteList = arcade.SpriteList()
        self.physics_engine: PhysicsEngine | None = None
        self.game_camera: arcade.Camera | None = None
        self.gui_camera: arcade.Camera | None = None
        self.player_status_text: arcade.Text = arcade.Text(
            "Health: 0  Armour: 0  Money: 0",
            10,
            10,
            arcade.color.WHITE,
            20,
        )
        self.nearest_item: Item | Consumable | None = None
        self.item_text: arcade.Text = arcade.Text(
            "",
            self.window.width / 2 - 150,
            self.window.height / 2 - 200,
            arcade.color.BLACK,
            20,
        )
        self.left_pressed: bool = False
        self.right_pressed: bool = False
        self.up_pressed: bool = False
        self.down_pressed: bool = False

    def __repr__(self) -> str:
        return f"<Game (Current window={self.window})>"

    def setup(self, level: int) -> None:
        """
        Sets up the game.

        Parameters
        ----------
        level: int
            The level to create a generation for. Each level should be more difficult
            than the last.
        """

        # Initialise the distribution generators that will determine the enemy and
        # consumable levels
        enemy_distribution = EnemyConsumableLevelGenerator.create_distribution(
            level, ENEMY_LEVEL_MAX_RANGE
        )
        consumable_distribution = EnemyConsumableLevelGenerator.create_distribution(
            level, CONSUMABLE_LEVEL_MAX_RANGE
        )

        # Create the game map and check that it is valid
        game_map = Map(level)
        assert game_map.grid is not None

        # Store the game map's width and height
        self.game_map_shape = game_map.grid.shape

        # Assign sprites to the game map
        for count_y, y in enumerate(game_map.grid):
            for count_x, x in enumerate(y):
                # Determine which type the tile is
                match x:
                    case TileType.FLOOR.value:
                        self.tile_sprites.append(Floor(count_x, count_y))
                    case TileType.WALL.value:
                        wall = Wall(count_x, count_y)
                        self.wall_sprites.append(wall)
                        self.tile_sprites.append(wall)
                    case TileType.PLAYER.value:
                        self.player = Player(
                            self,
                            count_x,
                            count_y,
                            PLAYER,
                        )
                        self.tile_sprites.append(Floor(count_x, count_y))
                    case TileType.ENEMY.value:
                        self.enemy_sprites.append(
                            Enemy(
                                self,
                                count_x,
                                count_y,
                                ENEMY1,
                                enemy_distribution.get_level(
                                    ENEMY1.entity_data.upgrade_level_limit
                                ),
                            )
                        )
                        self.tile_sprites.append(Floor(count_x, count_y))
                    case TileType.HEALTH_POTION.value:
                        self.tile_sprites.append(Floor(count_x, count_y))
                        health_potion = Consumable(
                            self,
                            count_x,
                            count_y,
                            HEALTH_POTION,
                            consumable_distribution.get_level(
                                HEALTH_POTION.level_limit
                            ),
                        )
                        self.tile_sprites.append(health_potion)
                        self.item_sprites.append(health_potion)
                    case TileType.ARMOUR_POTION.value:
                        self.tile_sprites.append(Floor(count_x, count_y))
                        armour_potion = Consumable(
                            self,
                            count_x,
                            count_y,
                            ARMOUR_POTION,
                            consumable_distribution.get_level(
                                HEALTH_POTION.level_limit
                            ),
                        )
                        self.tile_sprites.append(armour_potion)
                        self.item_sprites.append(armour_potion)
                    case TileType.HEALTH_BOOST_POTION.value:
                        self.tile_sprites.append(Floor(count_x, count_y))
                        health_boost_potion = Consumable(
                            self,
                            count_x,
                            count_y,
                            HEALTH_BOOST_POTION,
                            consumable_distribution.get_level(
                                HEALTH_POTION.level_limit
                            ),
                        )
                        self.tile_sprites.append(health_boost_potion)
                        self.item_sprites.append(health_boost_potion)
                    case TileType.ARMOUR_BOOST_POTION.value:
                        self.tile_sprites.append(Floor(count_x, count_y))
                        armour_boost_potion = Consumable(
                            self,
                            count_x,
                            count_y,
                            ARMOUR_BOOST_POTION,
                            consumable_distribution.get_level(
                                HEALTH_POTION.level_limit
                            ),
                        )
                        self.tile_sprites.append(armour_boost_potion)
                        self.item_sprites.append(armour_boost_potion)
                    case TileType.SPEED_BOOST_POTION.value:
                        self.tile_sprites.append(Floor(count_x, count_y))
                        speed_boost_potion = Consumable(
                            self,
                            count_x,
                            count_y,
                            SPEED_BOOST_POTION,
                            consumable_distribution.get_level(
                                HEALTH_POTION.level_limit
                            ),
                        )
                        self.tile_sprites.append(speed_boost_potion)
                        self.item_sprites.append(speed_boost_potion)
                    case TileType.FIRE_RATE_BOOST_POTION.value:
                        self.tile_sprites.append(Floor(count_x, count_y))
                        fire_rate_potion = Consumable(
                            self,
                            count_x,
                            count_y,
                            FIRE_RATE_BOOST_POTION,
                            consumable_distribution.get_level(
                                HEALTH_POTION.level_limit
                            ),
                        )
                        self.tile_sprites.append(fire_rate_potion)
                        self.item_sprites.append(fire_rate_potion)
                    case TileType.SHOP.value:
                        self.tile_sprites.append(Floor(count_x, count_y))
                        shop = Shop(self, count_x, count_y)
                        self.tile_sprites.append(shop)
                        self.item_sprites.append(shop)
        logger.debug(
            f"Created grid with height {len(game_map.grid)} and width"
            f" {len(game_map.grid[0])}"
        )

        # Make sure the player was actually created
        assert self.player is not None

        # Create the physics engine
        self.physics_engine = PhysicsEngine(DAMPING)
        self.physics_engine.setup(self.player, self.tile_sprites, self.enemy_sprites)

        # Set up the Camera
        self.game_camera = arcade.Camera(self.window.width, self.window.height)
        self.gui_camera = arcade.Camera(self.window.width, self.window.height)

        # Set up the melee shader
        self.player.melee_shader.setup_shader()

        # Check if any enemy has line of sight
        for enemy in self.enemy_sprites:
            enemy.check_line_of_sight()  # noqa

        # Set up the inventory view
        inventory_view = InventoryView(self.player)
        self.window.views["InventoryView"] = inventory_view
        logger.info("Initialised inventory view")

        # Set up the shop view
        shop_view = ShopView(self.player)
        self.window.views["ShopView"] = shop_view
        logger.info("Initialised shop view")

    def on_draw(self) -> None:
        """Render the screen."""
        # Make sure variables needed are valid
        assert self.game_camera is not None
        assert self.player is not None
        assert self.gui_camera is not None

        # Clear the screen
        self.clear()

        # Activate our Camera
        self.game_camera.use()

        # Draw the game map
        self.tile_sprites.draw(pixelated=True)
        self.bullet_sprites.draw(pixelated=True)
        self.enemy_sprites.draw(pixelated=True)
        self.player.draw(pixelated=True)

        # Draw the indicator bars
        self.indicator_bar_sprites.draw()

        # Draw the debug items
        if self.debug_mode:
            for enemy in self.enemy_sprites:
                # Draw the enemy's view distance
                arcade.draw_circle_outline(
                    enemy.center_x,
                    enemy.center_y,
                    enemy.enemy_data.view_distance * SPRITE_SIZE,  # noqa
                    DEBUG_VIEW_DISTANCE,
                )
                # Draw the enemy's attack distance
                arcade.draw_circle_outline(
                    enemy.center_x,
                    enemy.center_y,
                    enemy.current_attack.attack_range * SPRITE_SIZE,  # noqa
                    DEBUG_ATTACK_DISTANCE,
                )

            # Check if the player's current attack is a melee attack or an area of
            # effect attack
            if isinstance(self.player.current_attack, MeleeAttack):
                # Calculate the two boundary points for the player fov
                half_angle = self.player.player_data.melee_degree // 2
                low_angle = math.radians(self.player.direction - half_angle)
                high_angle = math.radians(self.player.direction + half_angle)
                point_low = (
                    self.player.center_x
                    + math.cos(low_angle)
                    * SPRITE_SIZE
                    * self.player.current_attack.attack_range,
                    self.player.center_y
                    + math.sin(low_angle)
                    * SPRITE_SIZE
                    * self.player.current_attack.attack_range,
                )
                point_high = (
                    self.player.center_x
                    + math.cos(high_angle)
                    * SPRITE_SIZE
                    * self.player.current_attack.attack_range,
                    self.player.center_y
                    + math.sin(high_angle)
                    * SPRITE_SIZE
                    * self.player.current_attack.attack_range,
                )
                # Draw both boundary lines for the player fov
                arcade.draw_line(
                    self.player.center_x,
                    self.player.center_y,
                    *point_low,
                    DEBUG_ATTACK_DISTANCE,
                )
                arcade.draw_line(
                    self.player.center_x,
                    self.player.center_y,
                    *point_high,
                    DEBUG_ATTACK_DISTANCE,
                )
                # Draw the arc between the two making sure to double the width and
                # height since the radius is calculated, but we want the diameter
                arcade.draw_arc_outline(
                    self.player.center_x,
                    self.player.center_y,
                    math.hypot(
                        point_high[0] - point_low[0], point_high[1] - point_low[1]
                    )
                    * 2,
                    self.player.current_attack.attack_range * SPRITE_SIZE * 2,
                    DEBUG_ATTACK_DISTANCE,
                    math.degrees(low_angle),
                    math.degrees(high_angle),
                    2,
                )
            elif isinstance(self.player.current_attack, AreaOfEffectAttack):
                # Draw the player's attack range
                arcade.draw_circle_outline(
                    self.player.center_x,
                    self.player.center_y,
                    self.player.current_attack.attack_range * SPRITE_SIZE,
                    DEBUG_ATTACK_DISTANCE,
                )

        # Draw the gui on the screen
        self.gui_camera.use()
        self.player_status_text.value = (
            f"Health: {self.player.health}  Armour: {self.player.armour}  Money:"
            f" {self.player.money}"
        )
        self.player_status_text.draw()
        if self.nearest_item:
            self.item_text.text = self.nearest_item.item_text
            self.item_text.draw()

    def on_update(self, delta_time: float) -> None:
        """
        Processes movement and game logic.

        Parameters
        ----------
        delta_time: float
            Time interval since the last time the function was called.
        """
        # Make sure variables needed are valid
        assert self.physics_engine is not None
        assert self.player is not None

        # Check if the game should end
        if self.player.health <= 0 or not self.enemy_sprites:
            arcade.exit()

        # Calculate the vertical velocity of the player based on the keys pressed
        update_enemies = False
        vertical_force = None
        if self.up_pressed and not self.down_pressed:
            vertical_force = (0, MOVEMENT_FORCE)
        elif self.down_pressed and not self.up_pressed:
            vertical_force = (0, -MOVEMENT_FORCE)
        if vertical_force:
            # Apply the vertical force
            self.physics_engine.apply_force(self.player, vertical_force)
            logger.debug(f"Applied vertical force {vertical_force} to player")

            # Set update_enemies
            update_enemies = True

        # Calculate the horizontal velocity of the player based on the keys pressed
        horizontal_force = None
        if self.left_pressed and not self.right_pressed:
            horizontal_force = (-MOVEMENT_FORCE, 0)
        elif self.right_pressed and not self.left_pressed:
            horizontal_force = (MOVEMENT_FORCE, 0)
        if horizontal_force:
            # Apply the horizontal force
            self.physics_engine.apply_force(self.player, horizontal_force)
            logger.debug(f"Applied horizontal force {horizontal_force} to player")

            # Set update_enemies
            update_enemies = True

        # Check if we need to update the enemy's line of sight
        if update_enemies:
            # Update the enemy's line of sight check
            for enemy in self.enemy_sprites:
                enemy.check_line_of_sight()  # noqa

        # Position the camera
        self.center_camera_on_player()

        # Check if the player is in combat
        self.player.in_combat = any(
            [enemy.line_of_sight for enemy in self.enemy_sprites]  # noqa
        )
        if self.player.in_combat:
            self.player.time_out_of_combat = 0

        # Process logic for the enemies
        self.enemy_sprites.on_update()

        # Process logic for the player
        self.player.on_update()

        # Process logic for the bullets
        self.bullet_sprites.on_update()

        # Update the physics engine
        self.physics_engine.step()

        # Check for any nearby items
        item_collision = arcade.check_for_collision_with_list(
            self.player, self.item_sprites
        )
        if item_collision:
            # Set nearest_item since we are colliding with an item
            self.nearest_item = item_collision[0]
            logger.debug(f"Grabbed nearest item {self.nearest_item}")
        else:
            # Reset nearest_item since we don't want to activate an item that the player
            # is not colliding with
            self.nearest_item = None

    def on_key_press(self, key: int, modifiers: int) -> None:
        """
        Called when the player presses a key.

        Parameters
        ----------
        key: int
            The key that was hit.
        modifiers: int
            Bitwise AND of all modifiers (shift, ctrl, num lock) pressed during this
            event.
        """
        # Make sure variables needed are valid
        assert self.player is not None

        # Find out what key was pressed
        logger.debug(f"Received key press with key {key}")
        match key:
            case arcade.key.W:
                self.up_pressed = True
            case arcade.key.S:
                self.down_pressed = True
            case arcade.key.A:
                self.left_pressed = True
            case arcade.key.D:
                self.right_pressed = True
            case arcade.key.E:
                if self.nearest_item:
                    try:
                        # Nearest item is a collectible
                        self.nearest_item.item_pick_up()
                    except AttributeError:
                        # Nearest item is an item
                        pass
            case arcade.key.R:
                if self.nearest_item:
                    self.nearest_item.item_activate()
            case arcade.key.F:
                self.window.show_view(self.window.views["InventoryView"])
            case arcade.key.C:
                self.player.current_attack_index += 1
                if self.player.current_attack_index == len(
                    self.player.attack_algorithms
                ):
                    self.player.current_attack_index -= 1
            case arcade.key.Z:
                self.player.current_attack_index -= 1
                if self.player.current_attack_index == -1:
                    self.player.current_attack_index = 0

    def on_key_release(self, key: int, modifiers: int) -> None:
        """
        Called when the player releases a key.

        Parameters
        ----------
        key: int
            The key that was hit.
        modifiers: int
            Bitwise AND of all modifiers (shift, ctrl, num lock) pressed during this
            event.
        """
        logger.debug(f"Received key release with key {key}")
        match key:
            case arcade.key.W:
                self.up_pressed = False
            case arcade.key.S:
                self.down_pressed = False
            case arcade.key.A:
                self.left_pressed = False
            case arcade.key.D:
                self.right_pressed = False

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        """
        Called when the player presses the mouse button.

        Parameters
        ----------
        x: float
            The x position of the mouse.
        y: float
            The y position of the mouse.
        button: int
            Which button was hit.
        modifiers: int
            Bitwise AND of all modifiers (shift, ctrl, num lock) pressed during this
            event.
        """
        # Make sure variables needed are valid
        assert self.player is not None

        # Test if the player can attack
        match button:
            case arcade.MOUSE_BUTTON_LEFT:
                # Make the player attack
                self.player.attack()

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        """
        Called when the mouse moves.

        Parameters
        ----------
        x: float
            The x position of the mouse.
        y: float
            The y position of the mouse.
        dx: float
            The change in the x position.
        dy: float
            The change in the y position.
        """
        # Make sure variables needed are valid
        assert self.player is not None
        assert self.game_camera is not None

        # Calculate the new angle in degrees
        camera_x, camera_y = self.game_camera.position
        vec_x, vec_y = (
            x - self.player.center_x + camera_x,
            y - self.player.center_y + camera_y,
        )
        angle = math.degrees(math.atan2(vec_y, vec_x))
        if angle < 0:
            angle += 360
        self.player.direction = angle
        self.player.facing = FACING_LEFT if 90 <= angle <= 270 else FACING_RIGHT

    def center_camera_on_player(self) -> None:
        """Centers the camera on the player."""
        # Make sure variables needed are valid
        assert self.game_camera is not None
        assert self.player is not None

        # Calculate the screen position centered on the player
        screen_center_x = self.player.center_x - (self.game_camera.viewport_width / 2)
        screen_center_y = self.player.center_y - (self.game_camera.viewport_height / 2)

        # Calculate the maximum width and height a sprite can be
        upper_x, upper_y = pos_to_pixel(
            self.game_map_shape[1] - 1, self.game_map_shape[0] - 1
        )

        # Calculate the maximum width and height the camera can be
        upper_camera_x, upper_camera_y = (
            upper_x
            - self.game_camera.viewport_width
            + (self.game_camera.viewport_width / SPRITE_SIZE),
            upper_y
            - self.game_camera.viewport_height
            + (self.game_camera.viewport_height / SPRITE_SIZE),
        )

        # Store the old position, so we can check if it has changed
        old_position = (self.game_camera.position[0], self.game_camera.position[1])

        # Make sure the camera doesn't extend beyond the boundaries
        if screen_center_x < 0:
            screen_center_x = 0
        elif screen_center_x > upper_camera_x:
            screen_center_x = upper_camera_x
        if screen_center_y < 0:
            screen_center_y = 0
        elif screen_center_y > upper_camera_y:
            screen_center_y = upper_camera_y
        new_position = screen_center_x, screen_center_y

        # Check if the camera position has changed
        if old_position != new_position:
            # Move the camera to the new position
            self.game_camera.move_to((screen_center_x, screen_center_y))  # noqa
            logger.debug(
                f"Changed camera position from {old_position} to {new_position}"
            )
