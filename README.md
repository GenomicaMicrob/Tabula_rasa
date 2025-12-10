
<img width="407" height="221" alt="icon_512x512" src="https://github.com/user-attachments/assets/358db3d8-c16a-4030-9b46-3abc1782dfc8" />

# Tabula Rasa

A simple paint application for Mac with basic drawing tools, image loading/saving, and zoom functionality.

It was designed to make it as simple as, primarily for retouching bitmap images, erasing unwanted parts, and making it possible to use colors transparent.

Creator: Bruno Gomez-Gil (bruno@ciad.mx)

Version: 0.1.0

## Features

- **Drawing Tools**:
  - Brush tool for freehand drawing
  - Line tool for drawing straight lines
  - Square tool for drawing rectangles/squares
  - Circle tool for drawing circles/ellipses
  - Bucket tool for flood fill areas
  - Eraser tool for removing content
  - Remove Background tool to make colors transparent
- **Adjustable Settings**:
  - Adjustable brush size and color
  - Zoom in/out functionality
  - Undo/Redo support
- **File Operations**:
  - Open and save images (PNG, JPEG)
  - Clear the canvas
- **Navigation**:
  - Scrollbars with arrows and draggable handles
  - Pan with middle or right mouse button
  - Rulers showing coordinates
- **Simple and intuitive interface**

## Requirements

- Python 3.7+
- PyQt6
- Pillow

## Installation

An app running on Mac Silicon is available (see `releases`).

- Download the zip file, unzip it, and run the app.
- You can move it to the Applications folder if you prefer.

Alternativly:

1. Clone this repository or download the files
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Run the application with:
  ```
  python Tabula_rasa.py
  ```

### Controls

#### Drawing Tools
- **Brush Tool**: Left-click and drag to draw freehand
- **Line Tool**: Click and drag to draw straight lines
- **Square Tool**: Click and drag to draw rectangles/squares (outline only)
- **Circle Tool**: Click and drag to draw circles/ellipses (outline only)
- **Bucket Tool**: Click to fill an area with the selected color
- **Eraser Tool**: Left-click and drag to erase content
- **Remove Background Tool**: Click to make the clicked color transparent

#### Canvas Navigation
- **Mouse Wheel**: Scroll vertically
- **Shift + Mouse Wheel**: Scroll horizontally
- **Middle/Right Mouse Button + Drag**: Pan around the canvas
- **Scrollbar Arrows**: Navigate in small increments
- **Scrollbar Handles**: Click and drag to scroll

#### Zoom Controls
- **Ctrl + Mouse Wheel**: Zoom in/out (keeps point under cursor fixed)
- **Zoom In/Out buttons**: Quick zoom controls

#### Settings
- **Color Button**: Change the brush/shape color
- **Brush Size Slider**: Adjust the brush/shape outline size
- **Undo/Redo buttons**: Revert or restore changes

#### File Operations
- **Open button**: Load an image file
- **Save As button**: Save your drawing to a new file
- **Clear button**: Clear the entire canvas

#### Keyboard Shortcuts
- **Ctrl + Z**: Undo
- **Ctrl + Y**: Redo
- **Ctrl + Shift + S**: Save As

## License

This project is open source and available under the MIT License.
