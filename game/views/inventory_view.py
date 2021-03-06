"""Displays the player's inventory graphically."""
from __future__ import annotations

# Builtin
import logging
from typing import TYPE_CHECKING

# Pip
import arcade.gui

# Custom
from game.constants.general import INVENTORY_HEIGHT, INVENTORY_WIDTH
from game.game_objects.base import UsableTile
from game.views.base_view import BaseView

if TYPE_CHECKING:
    from game.game_objects.base import CollectibleTile
    from game.game_objects.player import Player
    from game.window import Window

__all__ = ("InventoryView",)

# Get the logger
logger = logging.getLogger(__name__)


class InventoryBox(arcade.gui.UITextureButton):
    """Represents an individual box showing an item in the player's inventory."""

    # Class variables
    item_ref: CollectibleTile | UsableTile | None = None

    def __repr__(self) -> str:
        """Return a human-readable representation of this object."""
        return (
            f"<InventoryBox (Position=({self.center_x}, {self.center_y}))"
            f" (Width={self.width}) (Height={self.height})>"
        )

    def on_click(self, _) -> None:
        """Use an item in the player's inventory."""
        # Stop slots being clicked on if they're empty
        if not self.item_ref:
            return

        # Check if the item can be used or not
        if issubclass(type(self.item_ref), UsableTile):
            # Use it
            if not self.item_ref.item_use():
                # Use was not successful
                logger.info("Item use for %r not successful", self.item_ref)
                return

            # Get the current window, current view and game view
            window: Window = arcade.get_window()
            current_view: InventoryView = window.current_view  # noqa

            # Remove the item from the player's inventory and clear the item ref and the
            # inventory box texture
            current_view.player.inventory.remove(self.item_ref)
            self.item_ref = self.texture = None

            # Update the grid
            current_view.update_grid()

            # Render the changes. This is needed because the view is only updated when
            # the user exits
            self.trigger_full_render()

            logger.info("Item use for %r successful", self.item_ref)


class InventoryView(BaseView):
    """Displays the player's inventory allowing them to manage it and equip items.

    Parameters
    ----------
    player: Player
        The player object used for accessing the inventory.

    Attributes
    ----------
    vertical_box: arcade.gui.UIBoxLayout
        The arcade box layout responsible for organising the different ui elements.
    """

    def __init__(self, player: Player) -> None:
        super().__init__()
        self.player: Player = player
        self.vertical_box: arcade.gui.UIBoxLayout = arcade.gui.UIBoxLayout()

        # Create the inventory grid
        for _ in range(INVENTORY_HEIGHT):
            horizontal_box = arcade.gui.UIBoxLayout(vertical=False)
            for _ in range(INVENTORY_WIDTH):
                horizontal_box.add(
                    InventoryBox(width=64, height=64).with_border(width=4)
                )
            self.vertical_box.add(horizontal_box)

        # Create the back button
        self.add_back_button(self.vertical_box)

        # Register the UI elements
        self.ui_manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="center_x", anchor_y="center_y", child=self.vertical_box
            )
        )

    def __repr__(self) -> str:
        """Return a human-readable representation of this object."""
        return f"<InventoryView (Current window={self.window})>"

    def on_draw(self) -> None:
        """Render the screen."""
        # Clear the screen
        self.clear()

        # Draw the UI elements
        self.ui_manager.draw()

    def update_grid(self) -> None:
        """Update the inventory grid with the player's current inventory."""
        result = [0, 0]
        for row_count, box_layout in enumerate(self.vertical_box.children):
            for column_count, ui_border_obj in enumerate(box_layout.children):
                # Check if the current object is the back button
                if not ui_border_obj.children:
                    continue

                # Get the inventory array position
                array_pos = column_count + row_count * 3

                # Set the inventory box object to the inventory item
                inventory_box_obj: InventoryBox = ui_border_obj.children[0]  # noqa
                try:
                    item = self.player.inventory[array_pos]
                    inventory_box_obj.item_ref = item
                    inventory_box_obj.texture = item.texture
                    result[0] += 1
                except IndexError:
                    inventory_box_obj.texture = None
                    result[1] += 1
        logger.info(
            "Updated inventory grid with %d item textures and %d empty textures",
            *result,
        )
