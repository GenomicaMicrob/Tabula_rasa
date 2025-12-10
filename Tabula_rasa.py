import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QPushButton, QColorDialog, QFileDialog, QSlider, QLabel, 
                             QSizePolicy, QButtonGroup, QToolButton, QMessageBox)
from PyQt6.QtGui import (QPainter, QPen, QPixmap, QImage, QPainterPath, QAction, 
                         QIcon, QCursor, QBrush, QPainterPath, QColor)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal, QEvent, QTimer
from PyQt6.QtWidgets import QScrollArea
from collections import deque
from resource_path import resource_path

class RulerWidget(QWidget):
    def __init__(self, canvas: 'Canvas', orientation: Qt.Orientation):
        super().__init__()
        self.canvas = canvas
        self.orientation = orientation
        
        # Set minimum size instead of fixed size to allow growing
        if orientation == Qt.Orientation.Horizontal:
            self.setMinimumSize(100, 24)
            self.setMaximumHeight(24)
        else:
            self.setMinimumSize(24, 100)
            self.setMaximumWidth(24)
        
        # Connect zoom changes to update the ruler
        canvas.zoomChanged.connect(self.update)
        
        # Use a timer to delay scrollbar connections until after canvas is fully initialized
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._connect_scrollbars)
    
    def _connect_scrollbars(self):
        if hasattr(self.canvas, '_scroll_area') and self.canvas._scroll_area:
            hbar = self.canvas._scroll_area.horizontalScrollBar()
            vbar = self.canvas._scroll_area.verticalScrollBar()
            hbar.valueChanged.connect(self.update)
            vbar.valueChanged.connect(self.update)

    def paintEvent(self, event):
        p = QPainter(self)
        # Force white ruler background (not theme-dependent)
        p.fillRect(self.rect(), QColor(255, 255, 255))
        p.setPen(QPen(QColor(229, 231, 235)))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))

        zoom = getattr(self.canvas, 'zoom_factor', 1.0)
        if zoom <= 0:
            zoom = 1.0
            
        hbar = self.canvas._scroll_area.horizontalScrollBar() if self.canvas._scroll_area else None
        vbar = self.canvas._scroll_area.verticalScrollBar() if self.canvas._scroll_area else None
        offset_x = hbar.value() if hbar else 0
        offset_y = vbar.value() if vbar else 0

        # Dynamic tick steps: choose a "nice" major step aiming for ~80 device px between majors
        def nice_step(raw: float) -> int:
            if raw <= 0:
                return 1
            import math
            exp = math.floor(math.log10(raw))
            frac = raw / (10 ** exp)
            if frac < 1.5:
                nice = 1
            elif frac < 3.5:
                nice = 2
            elif frac < 7.5:
                nice = 5
            else:
                nice = 10
            return max(1, int(nice * (10 ** exp)))

        # Adjust target screen pixels based on zoom level
        target_screen_px = 80.0 / zoom  # Adjust target based on zoom
        major_step_px = nice_step(target_screen_px)
        minor_step_px = max(1, major_step_px // 5)

        if self.orientation == Qt.Orientation.Horizontal:
            width = self.width()
            start_img_px = offset_x / zoom
            end_img_px = start_img_px + (width / zoom)
            
            # Draw ticks
            p.setPen(QPen(QColor(120, 120, 120)))
            start_major = (int(start_img_px // major_step_px) - 1) * major_step_px
            
            for i in range(start_major, int(end_img_px) + major_step_px, minor_step_px):
                if i < 0:
                    continue
                x = int(i * zoom - offset_x)
                if x < 0 or x > width:
                    continue
                    
                is_major = (i % major_step_px == 0)
                tick_h = 12 if is_major else 6
                p.drawLine(x, 24 - tick_h, x, 24)
                
                if is_major and i >= 0:  # Only draw labels for positive coordinates
                    p.drawText(x + 2, 12, str(i))
        else:
            height = self.height()
            start_img_py = offset_y / zoom
            end_img_py = start_img_py + (height / zoom)
            
            p.setPen(QPen(QColor(120, 120, 120)))
            start_major = (int(start_img_py // major_step_px) - 1) * major_step_px
            
            for i in range(start_major, int(end_img_py) + major_step_px, minor_step_px):
                if i < 0:
                    continue
                y = int(i * zoom - offset_y)
                if y < 0 or y > height:
                    continue
                    
                is_major = (i % major_step_px == 0)
                tick_w = 12 if is_major else 6
                p.drawLine(24 - tick_w, y, 24, y)
                
                if is_major and i >= 0:  # Only draw labels for positive coordinates
                    p.drawText(2, y + 4, str(i))

class Canvas(QWidget):
    zoomChanged = pyqtSignal(float)
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StaticContents)
        self.image = QImage(1600, 1200, QImage.Format.Format_ARGB32)
        self.image.fill(Qt.GlobalColor.white)
        self.drawing = False
        self.brush_size = 5
        self.brush_color = QColor(Qt.GlobalColor.black.value)
        self.last_point = QPoint()
        self.zoom_factor = 1.0
        self.current_tool = "pointer"
        self.last_image = None
        self.history = deque(maxlen=100)  # For undo/redo
        self.redo_stack = deque(maxlen=100)
        self._scroll_area = None
        self._panning = False
        self._pan_last_global = QPoint()
        self._line_preview = None  # for line tool temporary preview end point
        self._square_start = None  # for square tool start position
        self._circle_start = None  # for circle tool start position
        self.modified = False
        self.save_state()
        # Start with default arrow cursor (pointer)
        # Ensure size reflects current zoom for scrollbars
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(self.sizeHint())
        
    def set_brush_size(self, size):
        self.brush_size = size
        
    def set_brush_color(self, color):
        if isinstance(color, QColor):
            self.brush_color = color
        else:
            self.brush_color = QColor(color)
    
    def get_pixel_color(self, pos):
        if 0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height():
            return self.image.pixelColor(pos)
        return None
    
    def save_state(self):
        self.history.append(self.image.copy())
        self.redo_stack.clear()
    
    def undo(self):
        if len(self.history) > 1:
            self.redo_stack.append(self.history.pop())
            self.image = self.history[-1].copy()
            self.update()
    
    def redo(self):
        if self.redo_stack:
            self.image = self.redo_stack.pop()
            self.history.append(self.image.copy())
            self.update()
    
    def clear_canvas(self):
        self.image.fill(Qt.GlobalColor.white)
        self.save_state()
        self.setFixedSize(self.sizeHint())
        self.update()
        self.modified = True
    
    def open_image(self, file_name):
        if file_name:
            tmp = QImage()
            if tmp.load(file_name):
                self.image = tmp.convertToFormat(QImage.Format.Format_ARGB32)
            self.save_state()
            self.setFixedSize(self.sizeHint())
            self.update()
            self.modified = False
    
    def save_image(self, file_name):
        if file_name:
            self.image.save(file_name)
    
    def flood_fill(self, pos, target_color, fill_color):
        if target_color == fill_color:
            return
            
        image = self.image
        width, height = image.width(), image.height()
        x, y = pos.x(), pos.y()
        
        if not (0 <= x < width and 0 <= y < height):
            return
            
        if image.pixelColor(x, y) != target_color:
            return
        
        # Use a queue for BFS flood fill and limit the maximum fill area
        from collections import deque
        queue = deque([(x, y)])
        image.setPixelColor(x, y, fill_color)
        
        # Maximum pixels to fill (to prevent hanging on large areas)
        max_fill = width * height  # Never exceed image size
        filled = 1
        
        while queue and filled < max_fill:
            x, y = queue.popleft()
            
            # Check 4 neighbors
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                
                # Check bounds
                if 0 <= nx < width and 0 <= ny < height:
                    # Check if pixel matches target color
                    if image.pixelColor(nx, ny) == target_color:
                        image.setPixelColor(nx, ny, fill_color)
                        queue.append((nx, ny))
                        filled += 1
                        
                        # Safety check - if we're filling too much, stop
                        if filled >= max_fill:
                            break
        self.modified = True

    def make_color_transparent(self, target_color: QColor):
        # Remove background by setting alpha to 0 where RGB matches target
        r_t, g_t, b_t = target_color.red(), target_color.green(), target_color.blue()
        width, height = self.image.width(), self.image.height()
        transparent = QColor(0, 0, 0, 0)
        for y in range(height):
            for x in range(width):
                c = self.image.pixelColor(x, y)
                if c.red() == r_t and c.green() == g_t and c.blue() == b_t:
                    self.image.setPixelColor(x, y, transparent)
        self.modified = True
    
    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw the scaled image
        scaled_image = self.image.scaled(
            int(self.image.width() * self.zoom_factor),
            int(self.image.height() * self.zoom_factor),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        painter.drawImage(QPoint(0, 0), scaled_image)
        
        # Draw line preview if in line mode and drawing
        if (self.current_tool == "line" and hasattr(self, '_line_preview') and 
            self._line_preview is not None and self.drawing and hasattr(self, '_line_start')):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(self.brush_color, 
                      max(1, int(self.brush_size * self.zoom_factor)), 
                      Qt.PenStyle.SolidLine, 
                      Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
            start_x = int(self._line_start.x() * self.zoom_factor)
            start_y = int(self._line_start.y() * self.zoom_factor)
            end_x = int(self._line_preview.x() * self.zoom_factor)
            end_y = int(self._line_preview.y() * self.zoom_factor)
            
            painter.drawLine(QPoint(start_x, start_y), QPoint(end_x, end_y))
        
        # Square preview
        elif (self.current_tool == "square" and hasattr(self, '_square_start') and 
              self._line_preview is not None and self.drawing):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(self.brush_color, 
                      max(1, int(self.brush_size * self.zoom_factor)), 
                      Qt.PenStyle.SolidLine, 
                      Qt.PenCapStyle.SquareCap)
            painter.setPen(pen)
            
            start_x = int(self._square_start.x() * self.zoom_factor)
            start_y = int(self._square_start.y() * self.zoom_factor)
            end_x = int(self._line_preview.x() * self.zoom_factor)
            end_y = int(self._line_preview.y() * self.zoom_factor)
            
            rect = QRect(QPoint(start_x, start_y), QPoint(end_x, end_y)).normalized()
            painter.drawRect(rect)
        
        # Circle preview
        elif (self.current_tool == "circle" and hasattr(self, '_circle_start') and 
              self._line_preview is not None and self.drawing):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(self.brush_color, 
                      max(1, int(self.brush_size * self.zoom_factor)), 
                      Qt.PenStyle.SolidLine, 
                      Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
            start_x = int(self._circle_start.x() * self.zoom_factor)
            start_y = int(self._circle_start.y() * self.zoom_factor)
            end_x = int(self._line_preview.x() * self.zoom_factor)
            end_y = int(self._line_preview.y() * self.zoom_factor)
            
            rect = QRect(QPoint(start_x, start_y), QPoint(end_x, end_y)).normalized()
            painter.drawEllipse(rect)
        
        # Draw cursor/overlay preview
        if self.underMouse() and hasattr(self, 'current_tool'):
            pos = self.mapFromGlobal(QCursor.pos())
            if self.current_tool in ["brush", "line", "square", "circle", "eraser"]:
                # Only draw cursor if not currently drawing a shape
                if not (self.current_tool in ["line", "square", "circle"] and self.drawing):
                    painter.setPen(QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.DotLine))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    brush_size = max(1, int(self.brush_size * self.zoom_factor))
                    x = int(pos.x() - brush_size / 2)
                    y = int(pos.y() - brush_size / 2)
                    painter.drawEllipse(x, y, brush_size, brush_size)
    
    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            # Start panning with middle or right mouse button
            self._panning = True
            self._pan_last_global = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            canvas_pos = self.mapToCanvas(pos)
            
            if self.current_tool == "bucket":
                self.save_state()
                target_color = self.image.pixelColor(canvas_pos.x(), canvas_pos.y())
                self.flood_fill(canvas_pos, target_color, self.brush_color)
                self.update()
                self.modified = True
            elif self.current_tool == "removebg":
                self.save_state()
                target_color = self.image.pixelColor(canvas_pos.x(), canvas_pos.y())
                self.make_color_transparent(target_color)
                self.drawing = False
                self.update()
                self.modified = True
            elif self.current_tool == "line":
                # Store the starting point in image coordinates
                self._line_start = canvas_pos
                self._line_preview = canvas_pos
                self.drawing = True
                self.update()
            elif self.current_tool == "square":
                # Store the starting point for square
                self._square_start = canvas_pos
                self._line_preview = canvas_pos  # Reuse for preview
                self.drawing = True
                self.update()
            elif self.current_tool == "circle":
                # Store the starting point for circle
                self._circle_start = canvas_pos
                self._line_preview = canvas_pos  # Reuse for preview
                self.drawing = True
                self.update()
            elif self.current_tool in ["brush", "eraser"]:
                self.drawing = True
                self.last_point = canvas_pos
                self.save_state()
    
    def mouseMoveEvent(self, event):
        if self._panning and self._scroll_area is not None and event.buttons() & (Qt.MouseButton.MiddleButton | Qt.MouseButton.RightButton):
            # Calculate delta from last position
            curr = event.globalPosition().toPoint()
            delta = curr - self._pan_last_global
            self._pan_last_global = curr
            
            # Get scrollbars
            hbar = self._scroll_area.horizontalScrollBar()
            vbar = self._scroll_area.verticalScrollBar()
            
            # Directly update scrollbar values
            hbar.setValue(hbar.value() - delta.x())
            vbar.setValue(vbar.value() - delta.y())
            
            event.accept()
            return
            
        current_point = self.mapToCanvas(event.position().toPoint())
        
        if not (event.buttons() & Qt.MouseButton.LeftButton) or not self.drawing:
            return
            
        if self.current_tool == "brush":
            painter = QPainter(self.image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            width = self.brush_size
            pen = QPen(self.brush_color, width,
                      Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_point, current_point)
            painter.end()
            self.last_point = current_point
            self.update()
            self.modified = True
            
        elif self.current_tool == "line":
            # Update preview endpoint and repaint overlay
            self._line_preview = current_point
            self.update()
            return  # Don't update last_point for line tool

        elif self.current_tool == "square":
            self._line_preview = current_point  # Reuse for preview
            self.update()
            return

        elif self.current_tool == "circle":
            self._line_preview = current_point  # Reuse for preview
            self.update()
            return

        elif self.current_tool == "eraser":
            painter = QPainter(self.image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(Qt.GlobalColor.white, self.brush_size, 
                      Qt.PenStyle.SolidLine, 
                      Qt.PenCapStyle.RoundCap, 
                      Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_point, current_point)
            painter.end()
            self.last_point = current_point
            self.update()
            self.modified = True
    
    def mouseReleaseEvent(self, event):
        if self._panning and event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._panning = False
            # Restore cursor to tool cursor
            self.set_tool_cursor(self.current_tool)
            event.accept()
            return
            
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            if self.current_tool == "line" and hasattr(self, '_line_start'):
                # Commit the line to the image
                end_point = self.mapToCanvas(event.position().toPoint())
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                pen = QPen(self.brush_color, self.brush_size,
                          Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(self._line_start, end_point)
                painter.end()
                self.modified = True
                self.save_state()
            elif self.current_tool == "square" and hasattr(self, '_square_start'):
                # Commit the square to the image
                end_point = self.mapToCanvas(event.position().toPoint())
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                pen = QPen(self.brush_color, self.brush_size,
                          Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.SquareCap)
                painter.setPen(pen)
                # Calculate rectangle from start and end points
                rect = QRect(self._square_start, end_point).normalized()
                painter.drawRect(rect)
                painter.end()
                self.modified = True
                self.save_state()
            elif self.current_tool == "circle" and hasattr(self, '_circle_start'):
                # Commit the circle to the image
                end_point = self.mapToCanvas(event.position().toPoint())
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                pen = QPen(self.brush_color, self.brush_size,
                          Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                # Calculate rectangle that bounds the circle
                rect = QRect(self._circle_start, end_point).normalized()
                painter.drawEllipse(rect)
                painter.end()
                self.modified = True
                self.save_state()
            
            # Clean up
            if hasattr(self, '_line_preview'):
                self._line_preview = None
            self.drawing = False
            self.update()
    
    def mapToCanvas(self, point):
        # Map widget coords to image pixel coords considering zoom
        x = max(0, min(int(point.x() / self.zoom_factor), self.image.width() - 1))
        y = max(0, min(int(point.y() / self.zoom_factor), self.image.height() - 1))
        return QPoint(x, y)
    
    def wheelEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            # Get the cursor position relative to the canvas
            cursor_pos = event.position().toPoint()
            # Get the current scrollbar positions
            hbar = self._scroll_area.horizontalScrollBar()
            vbar = self._scroll_area.verticalScrollBar()
            
            # Calculate the position in image coordinates before zooming
            old_x = (cursor_pos.x() + hbar.value()) / self.zoom_factor
            old_y = (cursor_pos.y() + vbar.value()) / self.zoom_factor
            
            # Calculate new zoom factor
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_factor = min(8.0, self.zoom_factor * 1.1)
            else:
                self.zoom_factor = max(0.1, self.zoom_factor / 1.1)
            
            # Calculate new size and set it
            new_size = QSize(int(self.image.width() * self.zoom_factor), 
                            int(self.image.height() * self.zoom_factor))
            self.setFixedSize(new_size)
            
            # Calculate new scrollbar positions to keep the same point under cursor
            new_x = old_x * self.zoom_factor - cursor_pos.x()
            new_y = old_y * self.zoom_factor - cursor_pos.y()
            
            # Set the new scrollbar positions
            hbar.setValue(int(new_x))
            vbar.setValue(int(new_y))
            
            # Update the display
            self.update()
            self.zoomChanged.emit(self.zoom_factor)
            
            if self.current_tool in ["brush", "pencil", "eraser"]:
                self.set_tool_cursor(self.current_tool)
        else:
            # Regular scrolling
            if self._scroll_area:
                # Use pixelDelta for high-resolution scrolling (trackpads)
                pixel_delta = event.pixelDelta()
                if not pixel_delta.isNull():
                    dx = pixel_delta.x()
                    dy = pixel_delta.y()
                else:
                    # Fallback for regular mouse wheels
                    delta = event.angleDelta()
                    dx = delta.x()
                    dy = delta.y()
                    # Scale down the delta for smoother scrolling
                    dx = dx * 2
                    dy = dy * 2
                    
                    # Handle horizontal scrolling with shift key
                    if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                        dx, dy = dy, dx  # Swap x and y for horizontal scrolling
                
                # Apply the scroll
                hbar = self._scroll_area.horizontalScrollBar()
                vbar = self._scroll_area.verticalScrollBar()
                
                # Check if we need to scroll horizontally or vertically
                # If both deltas are non-zero, prefer the larger one
                if abs(dx) > abs(dy):
                    hbar.setValue(hbar.value() - dx)
                else:
                    vbar.setValue(vbar.value() - dy)
                
                event.accept()
            else:
                event.ignore()

    def sizeHint(self):
        return QSize(int(self.image.width() * self.zoom_factor), int(self.image.height() * self.zoom_factor))

    def set_scroll_area(self, sa: QScrollArea):
        self._scroll_area = sa

    def set_tool_cursor(self, tool: str):
        # Pointer uses default arrow
        if tool == "pointer":
            self.unsetCursor()
            return

        # Determine cursor visual based on tool and brush size
        d = max(1, int(self.brush_size * self.zoom_factor))
        size = max(24, d + 8)
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(Qt.GlobalColor.black, 2)
        p.setPen(pen)

        hotspot = QPoint(size // 2, size // 2)

        if tool in ["brush", "line", "eraser"]:
            # Circle matching current size
            x = (size - d) // 2
            y = (size - d) // 2
            p.drawEllipse(x, y, d, d)
        elif tool == "bucket":
            p.drawRect(6, 6, size - 12, (size // 2) - 6)
            p.drawLine(6, 6, 4, 10)
            p.drawEllipse(size - 7, size - 8, 4, 6)
        elif tool == "removebg":
            margin = 5
            p.drawLine(margin, margin, size - margin, size - margin)
            p.drawLine(size - margin, margin, margin, size - margin)
        else:
            p.drawRect(5, 5, size - 10, size - 10)

        p.end()
        self.setCursor(QCursor(pix, hotspot.x(), hotspot.y()))

class PaintBrushApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tabula Rasa")
        self.setGeometry(100, 100, 900, 700)
        self.assets_dir = resource_path("assets")
        self.current_file_path = None
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        
        # Create canvas inside a scroll area
        self.canvas = Canvas()
        self.canvas.setMouseTracking(True)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        # Use ScrollBarAsNeeded to show scrollbars only when content exceeds viewport
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Style the scroll area with minimal styling to preserve native scrollbars
        self.scroll.setStyleSheet("""
            QScrollArea {
                background: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
        """)
        
        self.canvas.set_scroll_area(self.scroll)
        
        # Create tool buttons
        self.tool_group = QButtonGroup(self)
        
        # Tool buttons
        self.brush_btn = self.create_tool_button("Brush", "brush")
        self.line_btn = self.create_tool_button("Line", "line")
        self.square_btn = self.create_tool_button("Square", "square")
        self.circle_btn = self.create_tool_button("Circle", "circle")
        self.bucket_btn = self.create_tool_button("Bucket", "bucket")
        self.eraser_btn = self.create_tool_button("Eraser", "eraser")
        self.removebg_btn = self.create_tool_button("Remove BG", "removebg")

        # Zoom buttons (not part of toggle group)
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setToolTip("Zoom In")
        zoomin_path = os.path.join(self.assets_dir, "zoomin.svg")
        if os.path.exists(zoomin_path):
            self.zoom_in_btn.setIcon(QIcon(zoomin_path))
            self.zoom_in_btn.setIconSize(QSize(24, 24))
        else:
            self.zoom_in_btn.setText("Zoom +")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setToolTip("Zoom Out")
        zoomout_path = os.path.join(self.assets_dir, "zoomout.svg")
        if os.path.exists(zoomout_path):
            self.zoom_out_btn.setIcon(QIcon(zoomout_path))
            self.zoom_out_btn.setIconSize(QSize(24, 24))
        else:
            self.zoom_out_btn.setText("Zoom −")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        
        # No default drawing tool selected (pointer by default)
        
        # Undo/Redo buttons
        self.undo_btn = QToolButton()
        self.undo_btn.setToolTip("Undo (Ctrl+Z)")
        undo_path = os.path.join(self.assets_dir, "undo.svg")
        if os.path.exists(undo_path):
            self.undo_btn.setIcon(QIcon(undo_path))
            self.undo_btn.setIconSize(QSize(24, 24))
        self.undo_btn.clicked.connect(self.canvas.undo)
        
        self.redo_btn = QToolButton()
        self.redo_btn.setToolTip("Redo (Ctrl+Y)")
        redo_path = os.path.join(self.assets_dir, "redo.svg")
        if os.path.exists(redo_path):
            self.redo_btn.setIcon(QIcon(redo_path))
            self.redo_btn.setIconSize(QSize(24, 24))
        self.redo_btn.clicked.connect(self.canvas.redo)
        
        # Color button
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(32, 32)
        self.color_btn.clicked.connect(self.choose_color)
        
        # Brush size horizontal slider (compact)
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(50)
        self.size_slider.setValue(5)
        self.size_slider.setFixedWidth(120)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(5)
        self.size_slider.valueChanged.connect(self.update_brush_size)
        
        # No size label; slider alone indicates size
        
        # Clear button
        clear_btn = QToolButton()
        clear_btn.setToolTip("Clear")
        clear_path = os.path.join(self.assets_dir, "clear.svg")
        if os.path.exists(clear_path):
            clear_btn.setIcon(QIcon(clear_path))
            clear_btn.setIconSize(QSize(24, 24))
        else:
            clear_btn.setText("Clear")
        clear_btn.clicked.connect(self.canvas.clear_canvas)
        
        open_btn = QToolButton()
        open_btn.setToolTip("Open")
        open_path = os.path.join(self.assets_dir, "open.svg")
        if os.path.exists(open_path):
            open_btn.setIcon(QIcon(open_path))
            open_btn.setIconSize(QSize(24, 24))
        else:
            open_btn.setText("Open")
        open_btn.clicked.connect(self.open_file_dialog)
        
        save_path = os.path.join(self.assets_dir, "save.svg")
        save_as_btn = QToolButton()
        save_as_btn.setToolTip("Save As (Ctrl+Shift+S)")
        if os.path.exists(save_path):
            save_as_btn.setIcon(QIcon(save_path))
            save_as_btn.setIconSize(QSize(24, 24))
        else:
            save_as_btn.setText("Save As")
        save_as_btn.clicked.connect(self.save_file_dialog)
        
        # Create single unified top toolbar
        top_toolbar = QHBoxLayout()
        # File actions
        top_toolbar.addWidget(open_btn)
        top_toolbar.addWidget(save_as_btn)
        top_toolbar.addWidget(clear_btn)
        top_toolbar.addSpacing(8)
        # Undo/Redo
        top_toolbar.addWidget(self.undo_btn)
        top_toolbar.addWidget(self.redo_btn)
        top_toolbar.addSpacing(12)
        # Tools
        top_toolbar.addWidget(self.brush_btn)
        top_toolbar.addWidget(self.line_btn)
        top_toolbar.addWidget(self.square_btn)
        top_toolbar.addWidget(self.circle_btn)
        top_toolbar.addWidget(self.bucket_btn)
        top_toolbar.addWidget(self.eraser_btn)
        top_toolbar.addWidget(self.removebg_btn)
        top_toolbar.addSpacing(12)
        # Zoom
        top_toolbar.addWidget(self.zoom_in_btn)
        top_toolbar.addWidget(self.zoom_out_btn)
        top_toolbar.addSpacing(12)
        # Options: color and size
        top_toolbar.addWidget(self.color_btn)
        top_toolbar.addSpacing(6)
        top_toolbar.addWidget(self.size_slider)
        
        top_toolbar.addStretch()
        
        # Add single toolbar (wrapped in widget for styling) and work area (rulers + scroll) to main layout
        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("TopToolbar")
        toolbar_widget.setLayout(top_toolbar)
        toolbar_widget.setStyleSheet(
            "#TopToolbar { background: #F3F4F6; border-bottom: 1px solid #D1D5DB; }"
            "#TopToolbar QToolButton { background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 4px; }"
            "#TopToolbar QToolButton:hover { background: #F9FAFB; border-color: #D1D5DB; }"
            "#TopToolbar QToolButton:checked { background: #E5E7EB; border-color: #9CA3AF; }"
            "#TopToolbar QSlider::groove:horizontal { background: #D1D5DB; height: 6px; border-radius: 3px; }"
            "#TopToolbar QSlider::handle:horizontal { background: #374151; border: 2px solid #FFFFFF; height: 14px; width: 14px; margin: -4px -5px; border-radius: 7px; }"
        )
        layout.addWidget(toolbar_widget)
        work_area = QWidget()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        work_area.setLayout(grid)
        # Corner spacer with matching background
        corner = QWidget()
        corner.setFixedSize(24, 24)
        corner.setStyleSheet("background: #f0f0f0; border: 1px solid #d0d0d0;")
        
        # Rulers with proper styling
        h_ruler = RulerWidget(self.canvas, Qt.Orientation.Horizontal)
        v_ruler = RulerWidget(self.canvas, Qt.Orientation.Vertical)
        
        # Set ruler styles
        h_ruler.setStyleSheet("""
            QWidget {
                background: #f0f0f0;
                border-bottom: 1px solid #d0d0d0;
                border-right: 1px solid #d0d0d0;
            }
        """)
        
        v_ruler.setStyleSheet("""
            QWidget {
                background: #f0f0f0;
                border-right: 1px solid #d0d0d0;
                border-bottom: 1px solid #d0d0d0;
            }
        """)
        
        # Add widgets to grid
        grid.addWidget(corner, 0, 0)
        grid.addWidget(h_ruler, 0, 1)
        grid.addWidget(v_ruler, 1, 0)
        grid.addWidget(self.scroll, 1, 1)
        
        # Set grid row/column stretch factors
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(1, 1)
        
        # Sync rulers with scroll and zoom
        self.scroll.horizontalScrollBar().valueChanged.connect(h_ruler.update)
        self.scroll.verticalScrollBar().valueChanged.connect(v_ruler.update)
        self.canvas.zoomChanged.connect(h_ruler.update)
        self.canvas.zoomChanged.connect(v_ruler.update)
        
        # Ensure initial update of rulers
        QTimer.singleShot(100, lambda: [h_ruler.update(), v_ruler.update()])
        layout.addWidget(work_area, 1)
        
        # Initialize with black color
        self.current_color = QColor(Qt.GlobalColor.black.value)
        self.canvas.set_brush_color(self.current_color)
        self.update_color_button()
        self.update_title()
        
        # Set the layout to the main widget
        main_widget.setLayout(layout)
        # Force a light background and dark text for the app to avoid dark mode palette conflicts
        self.setStyleSheet("""
            QWidget {
                background: #FFFFFF;
                color: #111827;
            }
            QScrollArea, QScrollArea > QWidget, QScrollArea QWidget {
                background: #f0f0f0;
            }
            QScrollArea {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
        """)
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        # No theme-dependent icon styling (icons use fixed strokes)
        
    def create_tool_button(self, text, tool_name):
        btn = QToolButton()
        btn.setCheckable(True)
        btn.setToolTip(text)
        btn.setMinimumHeight(36)
        # Set SVG icon if present
        icon_map = {
            "brush": "brush.svg",
            "line": "line.svg",
            "bucket": "bucket.svg",
            "eraser": "eraser.svg",
            "removebg": "remove_background.svg",
            # "eyedrop": "eyedrop.svg",  # add if tool is added to UI
        }
        fname = icon_map.get(tool_name)
        icon_set = False
        if fname:
            fpath = os.path.join(self.assets_dir, fname)
            if os.path.exists(fpath):
                btn.setIcon(QIcon(fpath))
                btn.setIconSize(QSize(24, 24))
                icon_set = True
        if not icon_set:
            # Fallback to programmatically drawn icon
            btn.setIcon(self.make_tool_icon(tool_name))
            btn.setIconSize(QSize(24, 24))
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        btn.clicked.connect(lambda checked, t=tool_name: self.set_tool(t))
        self.tool_group.addButton(btn)
        return btn
        
    def set_tool(self, tool_name):
        # Uncheck all buttons first
        for btn in self.tool_group.buttons():
            btn.setChecked(False)
            
        # Set the current tool in the canvas
        self.canvas.current_tool = tool_name
        
        # Update cursor to reflect selected tool
        self.canvas.set_tool_cursor(tool_name)
        
        # Clear any in-progress line preview when switching tools
        if hasattr(self.canvas, '_line_preview'):
            self.canvas._line_preview = None
            
        # Update the UI to show which tool is selected
        tool_buttons = {
            'brush': self.brush_btn,
            'line': self.line_btn,
            'square': self.square_btn,
            'circle': self.circle_btn,
            'bucket': self.bucket_btn,
            'eraser': self.eraser_btn,
            'removebg': self.removebg_btn
        }
        if tool_name in tool_buttons:
            tool_buttons[tool_name].setChecked(True)
        
    def setup_shortcuts(self):
        # Undo/Redo
        self.undo_shortcut = QAction(self)
        self.undo_shortcut.setShortcut("Ctrl+Z")
        self.undo_shortcut.triggered.connect(self.canvas.undo)
        self.addAction(self.undo_shortcut)
        
        self.redo_shortcut = QAction(self)
        self.redo_shortcut.setShortcut("Ctrl+Y")
        self.redo_shortcut.triggered.connect(self.canvas.redo)
        self.addAction(self.redo_shortcut)
        
        # Tool shortcuts
        shortcuts = {
            "B": "brush",
            "L": "line",
            "F": "bucket",
            "E": "eraser",
            "R": "removebg",
        }
        
        for key, tool in shortcuts.items():
            action = QAction(self)
            action.setShortcut(key)
            action.triggered.connect(lambda checked, t=tool: self.set_tool(t))
            self.addAction(action)

        # Save As only
        save_as_action = QAction(self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_dialog)
        self.addAction(save_as_action)

    def make_tool_icon(self, tool: str) -> QIcon:
        # Draw a simple 24x24 icon for each tool
        size = 24
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(Qt.GlobalColor.black, 2)
        p.setPen(pen)

        if tool == "brush":
            # Circle brush tip and short handle
            p.drawEllipse(5, 12, 8, 8)
            p.drawLine(12, 16, 19, 7)
        elif tool == "pencil":
            # Diagonal pencil
            p.drawLine(5, 18, 18, 5)
            p.drawLine(16, 7, 19, 4)  # tip
        elif tool == "line":
            p.drawLine(5, 18, 18, 5)
            # Add small perpendicular lines at ends for clarity
            p.drawLine(5, 18, 7, 16)
            p.drawLine(18, 5, 16, 7)
        elif tool == "square":
            p.drawRect(5, 5, 14, 14)
        elif tool == "circle":
            p.drawEllipse(5, 5, 14, 14)
        elif tool == "bucket":
            p.drawRect(6, 6, 10, 8)
            p.drawLine(6, 6, 4, 10)
            p.drawEllipse(17, 16, 4, 6)
        elif tool == "eraser":
            p.drawRect(6, 10, 12, 8)
            p.drawLine(6, 14, 18, 14)
        elif tool == "eyedrop":
            p.drawEllipse(5, 6, 6, 6)
            p.drawLine(10, 10, 18, 18)
        elif tool == "removebg":
            # Scissors icon for remove background
            p.drawLine(6, 6, 12, 12)
            p.drawLine(18, 6, 12, 12)
            p.drawLine(6, 18, 12, 12)
            p.drawLine(18, 18, 12, 12)
        else:
            # Fallback generic tool
            p.drawRect(5, 5, 14, 14)

        p.end()
        return QIcon(pix)
    
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_color = color
            self.canvas.set_brush_color(color)
            self.update_color_button()
            
    def update_brush_size(self, size):
        self.canvas.set_brush_size(size)
        if self.canvas.current_tool in ["brush", "line", "eraser"]:
            self.canvas.set_tool_cursor(self.canvas.current_tool)
    
    
        
    def update_color_button(self):
        color_name = self.current_color.name() if hasattr(self.current_color, 'name') else '#000000'
        self.color_btn.setStyleSheet(
            """
            QPushButton {
                background-color: %s;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 4px;
            }
            QPushButton:hover {
                border-color: #9CA3AF;
            }
            QPushButton:pressed {
                background-color: %s;
                border-color: #6B7280;
            }
            """ % (color_name, color_name)
        )

    def zoom_in(self):
        self.canvas.zoom_factor = min(8.0, self.canvas.zoom_factor * 1.1)
        self.canvas.update()
        if self.canvas.current_tool in ["brush", "pencil", "eraser"]:
            self.canvas.set_tool_cursor(self.canvas.current_tool)

    def zoom_out(self):
        self.canvas.zoom_factor = max(0.1, self.canvas.zoom_factor / 1.1)
        self.canvas.update()
        if self.canvas.current_tool in ["brush", "pencil", "eraser"]:
            self.canvas.set_tool_cursor(self.canvas.current_tool)

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", 
            "Images (*.png *.xpm *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if file_name:
            self.canvas.open_image(file_name)
            self.current_file_path = file_name
            self.update_title()
    
    def save_file_dialog(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", 
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;All Files (*)"
        )
        if file_name:
            self.canvas.save_image(file_name)
            self.current_file_path = file_name
            self.canvas.modified = False
            self.update_title()

    def update_title(self):
        name = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled"
        star = "*" if getattr(self.canvas, 'modified', False) else ""
        self.setWindowTitle(f"Tabula Rasa - {name}{star}")

    def closeEvent(self, event):
        # Prompt to save if there are unsaved changes
        if getattr(self.canvas, 'modified', False):
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Unsaved Changes")
            msg.setText("You have unsaved changes.")
            msg.setInformativeText("Do you want to save your changes?")
            msg.setStandardButtons(QMessageBox.StandardButton.Save |
                                   QMessageBox.StandardButton.Discard |
                                   QMessageBox.StandardButton.Cancel)
            msg.setDefaultButton(QMessageBox.StandardButton.Save)
            # Ensure readable text/buttons on forced light background
            msg.setStyleSheet(
                "QMessageBox { background: #FFFFFF; }"
                "QLabel { color: #111827; }"
                "QPushButton { color: #111827; background: #F3F4F6; border: 1px solid #D1D5DB; border-radius: 6px; padding: 4px 10px; }"
                "QPushButton:hover { background: #F9FAFB; }"
            )
            # Explicitly set button texts and remove icons to avoid icon-only rendering
            for sb, text in [
                (QMessageBox.StandardButton.Save, "Save"),
                (QMessageBox.StandardButton.Discard, "Discard"),
                (QMessageBox.StandardButton.Cancel, "Cancel"),
            ]:
                btn = msg.button(sb)
                if btn is not None:
                    btn.setText(text)
                    btn.setIcon(QIcon())
            ret = msg.exec()
            if ret == QMessageBox.StandardButton.Save:
                self.save_file_dialog()
                if getattr(self.canvas, 'modified', False):
                    # Save was canceled or failed
                    event.ignore()
                    return
                event.accept()
            elif ret == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    # No plain Save; use Save As only

def main():
    app = QApplication(sys.argv)
    window = PaintBrushApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
