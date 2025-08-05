"""
Component Canvas for Visual Design
Provides drag-and-drop visual design interface for ESPHome components.
"""

import logging
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsItem, QMenu, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QColor, QPen, QBrush, QPainter, QFont, QAction

from models.component import ESPHomeComponent

class ComponentItem(QGraphicsRectItem):
    """Visual representation of an ESPHome component on the canvas."""
    
    def __init__(self, component: ESPHomeComponent, x: float = 0, y: float = 0):
        super().__init__(0, 0, component.width, component.height)
        self.component = component
        self.setPos(x, y)
        self.setup_appearance()
        self.setup_behavior()
        
        # Add text label
        self.text_item = QGraphicsTextItem(self.component.name, self)
        self.text_item.setPos(5, 5)
        self.text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        # Add type label
        self.type_item = QGraphicsTextItem(f"({self.component.component_type})", self)
        self.type_item.setPos(5, 25)
        font = QFont("Arial", 8)
        font.setItalic(True)
        self.type_item.setFont(font)
        self.type_item.setDefaultTextColor(QColor(100, 100, 100))
        
        self.logger = logging.getLogger(__name__)
    
    def setup_appearance(self):
        """Set up the visual appearance of the component."""
        # Color coding based on component type
        color_map = {
            'sensor': QColor(100, 150, 255),
            'switch': QColor(255, 150, 100),
            'light': QColor(255, 255, 100),
            'binary_sensor': QColor(150, 255, 150),
            'climate': QColor(255, 150, 255),
            'cover': QColor(150, 255, 255),
            'fan': QColor(200, 200, 255),
            'text_sensor': QColor(255, 200, 150)
        }
        
        base_color = color_map.get(self.component.component_type, QColor(200, 200, 200))
        
        # Set up brush and pen
        brush = QBrush(base_color)
        pen = QPen(base_color.darker(150), 2)
        
        self.setBrush(brush)
        self.setPen(pen)
        
        # Make it selectable and movable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
    
    def setup_behavior(self):
        """Set up interaction behavior."""
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def hoverEnterEvent(self, event):
        """Handle mouse hover enter."""
        self.setPen(QPen(self.pen().color(), 3))
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave."""
        self.setPen(QPen(self.pen().color(), 2))
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)
    
    def itemChange(self, change, value):
        """Handle item changes (like position)."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Update component position
            new_pos = value
            self.component.set_position(int(new_pos.x()), int(new_pos.y()))
        
        return super().itemChange(change, value)
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu."""
        menu = QMenu()
        
        configure_action = QAction("Configure...", menu)
        configure_action.triggered.connect(self.configure_component)
        menu.addAction(configure_action)
        
        clone_action = QAction("Clone", menu)
        clone_action.triggered.connect(self.clone_component)
        menu.addAction(clone_action)
        
        menu.addSeparator()
        
        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(self.delete_component)
        menu.addAction(delete_action)
        
        # Convert scene coordinates to screen coordinates
        screen_pos = event.screenPos()
        menu.exec(screen_pos)
    
    def configure_component(self):
        """Trigger component configuration."""
        if self.scene():
            canvas = self.scene().parent()
            if hasattr(canvas, 'component_double_clicked'):
                canvas.component_double_clicked.emit(self.component)
    
    def clone_component(self):
        """Clone this component."""
        if self.scene():
            canvas = self.scene().parent()
            if hasattr(canvas, 'clone_component'):
                canvas.clone_component(self.component)
    
    def delete_component(self):
        """Delete this component."""
        if self.scene():
            canvas = self.scene().parent()
            if hasattr(canvas, 'remove_component'):
                canvas.remove_component(self.component)
    
    def update_display(self):
        """Update the visual display after component changes."""
        self.text_item.setPlainText(self.component.name)
        
        # Update size if changed
        current_rect = self.rect()
        if (current_rect.width() != self.component.width or 
            current_rect.height() != self.component.height):
            self.setRect(0, 0, self.component.width, self.component.height)
        
        self.update()

class ComponentCanvas(QGraphicsView):
    """Canvas for visual component design with drag-and-drop functionality."""
    
    # Signals
    component_selected = pyqtSignal(ESPHomeComponent)
    component_double_clicked = pyqtSignal(ESPHomeComponent)
    canvas_updated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Component tracking
        self.component_items: Dict[str, ComponentItem] = {}
        
        self.setup_canvas()
        self.setup_connections()
    
    def setup_canvas(self):
        """Set up the canvas appearance and behavior."""
        # Set scene size
        self.scene.setSceneRect(0, 0, 2000, 1500)
        
        # Canvas appearance
        self.setBackgroundBrush(QBrush(QColor(245, 245, 245)))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        # Enable smooth scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Grid setup
        self.show_grid = True
        self.grid_size = 20
    
    def setup_connections(self):
        """Set up signal connections."""
        self.scene.selectionChanged.connect(self.on_selection_changed)
    
    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw the canvas background with optional grid."""
        super().drawBackground(painter, rect)
        
        if self.show_grid:
            self.draw_grid(painter, rect)
    
    def draw_grid(self, painter: QPainter, rect: QRectF):
        """Draw a grid on the canvas."""
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.DotLine))
        
        # Convert rect coordinates to integers for consistent drawing
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        right = int(rect.right())
        bottom = int(rect.bottom())
        
        # Vertical lines
        x = left
        while x < right:
            painter.drawLine(x, top, x, bottom)
            x += self.grid_size
        
        # Horizontal lines
        y = top
        while y < bottom:
            painter.drawLine(left, y, right, y)
            y += self.grid_size
    
    def add_component(self, component: ESPHomeComponent, x: Optional[float] = None, y: Optional[float] = None):
        """Add a component to the canvas."""
        if component.instance_id in self.component_items:
            self.logger.warning(f"Component {component.instance_id} already exists on canvas")
            return
        
        # Position component
        if x is None or y is None:
            # Find a good position
            x, y = self.find_available_position()
        
        component.set_position(int(x), int(y))
        
        # Create visual item
        item = ComponentItem(component, x, y)
        self.scene.addItem(item)
        
        # Track the item
        self.component_items[component.instance_id] = item
        
        self.logger.info(f"Added component {component.name} to canvas at ({x}, {y})")
        self.canvas_updated.emit()
    
    def remove_component(self, component: ESPHomeComponent):
        """Remove a component from the canvas."""
        if component.instance_id in self.component_items:
            item = self.component_items[component.instance_id]
            self.scene.removeItem(item)
            del self.component_items[component.instance_id]
            
            self.logger.info(f"Removed component {component.name} from canvas")
            self.canvas_updated.emit()
    
    def clone_component(self, component: ESPHomeComponent):
        """Clone a component on the canvas."""
        cloned = component.clone()
        
        # Offset the clone position
        x, y = self.find_available_position(component.x_position + 50, component.y_position + 50)
        self.add_component(cloned, x, y)
        
        self.logger.info(f"Cloned component {component.name}")
    
    def find_available_position(self, start_x: float = 50, start_y: float = 50) -> tuple[float, float]:
        """Find an available position for a new component."""
        x, y = start_x, start_y
        step = 30
        
        while self.is_position_occupied(x, y):
            x += step
            if x > 1800:  # Wrap to next row
                x = start_x
                y += step * 2
            if y > 1200:  # Reset if we've gone too far down
                y = start_y
                break
        
        return x, y
    
    def is_position_occupied(self, x: float, y: float, tolerance: float = 50) -> bool:
        """Check if a position is occupied by another component."""
        for item in self.component_items.values():
            item_pos = item.pos()
            if (abs(item_pos.x() - x) < tolerance and 
                abs(item_pos.y() - y) < tolerance):
                return True
        return False
    
    def get_all_components(self) -> List[ESPHomeComponent]:
        """Get all components currently on the canvas."""
        return [item.component for item in self.component_items.values()]
    
    def clear_all_components(self):
        """Remove all components from the canvas."""
        for item in list(self.component_items.values()):
            self.scene.removeItem(item)
        
        self.component_items.clear()
        self.logger.info("Cleared all components from canvas")
        self.canvas_updated.emit()
    
    def has_components(self) -> bool:
        """Check if the canvas has any components."""
        return len(self.component_items) > 0
    
    def on_selection_changed(self):
        """Handle selection changes."""
        selected_items = self.scene.selectedItems()
        
        if selected_items:
            # Get the first selected component item
            for item in selected_items:
                if isinstance(item, ComponentItem):
                    self.component_selected.emit(item.component)
                    break
        else:
            self.component_selected.emit(None)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click events."""
        item = self.itemAt(event.pos())
        if isinstance(item, ComponentItem):
            self.component_double_clicked.emit(item.component)
        else:
            super().mouseDoubleClickEvent(event)
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        # Zoom with Ctrl+Wheel
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            
            # Get the mouse position in scene coordinates
            old_pos = self.mapToScene(event.position().toPoint())
            
            # Zoom
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor
            
            self.scale(zoom_factor, zoom_factor)
            
            # Get the new position
            new_pos = self.mapToScene(event.position().toPoint())
            
            # Move scene to keep mouse position
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
        else:
            super().wheelEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu on empty canvas."""
        item = self.itemAt(event.pos())
        if not item:
            menu = QMenu(self)
            
            clear_action = QAction("Clear All", menu)
            clear_action.triggered.connect(self.clear_all_components)
            menu.addAction(clear_action)
            
            menu.addSeparator()
            
            grid_action = QAction("Toggle Grid", menu)
            grid_action.setCheckable(True)
            grid_action.setChecked(self.show_grid)
            grid_action.triggered.connect(self.toggle_grid)
            menu.addAction(grid_action)
            
            menu.exec(event.globalPos())
        else:
            super().contextMenuEvent(event)
    
    def toggle_grid(self):
        """Toggle grid visibility."""
        self.show_grid = not self.show_grid
        self.viewport().update()
    
    def fit_all_components(self):
        """Fit all components in the view."""
        if self.component_items:
            self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def update_component_display(self, component: ESPHomeComponent):
        """Update the display of a specific component."""
        if component.instance_id in self.component_items:
            item = self.component_items[component.instance_id]
            item.update_display()
