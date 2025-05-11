print("Before running this script, make sure you have installed the required libraries:")
print("To install the necessary libraries, run:")
print("'pip install opencv-python' and 'pip install pillow'")

# Import necessary libraries
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np

# Constants for Image Processing and UI Configuration
WINDOW_TITLE = "Photo Editor Pro"                       # Title of the application window
WINDOW_WIDTH = 1500                                     # Width of the window
WINDOW_HEIGHT = 800                                     # Height of the window
CROP_RECT_COLOR = "blue"                                # Color of the cropping rectangle
CROP_RECT_WIDTH = 5                                     # Thickness of the cropping rectangle
MIN_RESIZE_PERCENT = 5                                  # Minimum resize scale (5%)
MAX_RESIZE_PERCENT = 300                                # Maximum resize scale (300%)
DEFAULT_RESIZE_PERCENT = 150                            # Default resize scale (150%)
SAVE_FILETYPES = [("PNG", "*.png"), ("JPEG", "*.jpg")]  # File types for saving

# Main application class
class PhotoEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")       # Using defined constants

        # Initialize image variables
        self.original_image = None          # Original image loaded from file
        self.edited_image = None            # Current working image
        self.cropped_image = None           # Cropped portion of the image
        self.tk_image = None                # Image formatted for Tkinter canvas
        self.crop_coords = (0, 0, 0, 0)     # Coordinates for cropping rectangle
        self.crop_rectangle = None          # Crop rectangle object on canvas

        # Undo and redo stacks
        self.image_history = []             # Stack for undo
        self.redo_stack = []                # Stack for redo

        # Build GUI and bind shortcuts
        self._build_ui()
        self._bind_shortcuts()

    # Build the entire user interface layout
    def _build_ui(self):
        # Create frames for layout: tools (left), canvas (center), previews (right)
        self.left_frame = ttk.Frame(self.root)
        self.left_frame.pack(side="left", fill="y", padx=10)

        self.center_frame = ttk.Frame(self.root)
        self.center_frame.pack(side="left", fill="both", expand=True)

        self.right_frame = ttk.Frame(self.root)
        self.right_frame.pack(side="right", fill="y", padx=10)

        # Tool buttons with optional shortcut labels
        ttk.Label(self.left_frame, text="Tools").pack(pady=5)
        self._create_button("Open Image", self.open_image, "Ctrl+O")
        self._create_button("Crop Image", self.activate_crop, "Ctrl+C")
        self._create_button("Save Image", self.save_image, "Ctrl+S")
        self._create_button("Grayscale", self.apply_grayscale, "")
        self._create_button("Blur", self.apply_blur, "")
        self._create_button("Undo", self.undo, "Ctrl+Z")
        self._create_button("Redo", self.redo, "Ctrl+Y")

        ttk.Label(self.left_frame, text="Resize (%)").pack(pady=5)
        self.resize_slider = ttk.Scale(
            self.left_frame, from_=MIN_RESIZE_PERCENT, to=MAX_RESIZE_PERCENT,
            command=self.resize_image, orient="horizontal")
        self.resize_slider.set(DEFAULT_RESIZE_PERCENT)
        self.resize_slider.pack()
        
        self.edit_canvas = tk.Canvas(self.center_frame, bg="gray")
        self.edit_canvas.pack(fill="both", expand=True)

        ttk.Label(self.right_frame, text="Original Image").pack(pady=5)
        self.original_canvas = tk.Canvas(self.right_frame, width=200, height=200, bg="lightgray")
        self.original_canvas.pack()

        ttk.Label(self.right_frame, text="Cropped Image").pack(pady=5)
        self.cropped_canvas = tk.Canvas(self.right_frame, width=200, height=200, bg="lightgray")
        self.cropped_canvas.pack()

    def _create_button(self, text, command, shortcut):
        frame = ttk.Frame(self.left_frame)
        frame.pack(pady=2, fill='x')
        ttk.Button(frame, text=text, command=command).pack(side='left', padx=5)
        ttk.Label(frame, text=shortcut).pack(side='right')

    def _bind_shortcuts(self):
        self.root.bind('<Control-o>', lambda e: self.open_image())
        self.root.bind('<Control-c>', lambda e: self.activate_crop())
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Control-s>', lambda e: self.save_image())

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self.original_image = cv2.imread(path)
            self.edited_image = self.original_image.copy()
            self.resize_base_image = self.edited_image.copy()
            self.image_history.clear()
            self.redo_stack.clear()
            self._update_original_canvas()
            self._update_edit_canvas()

    def activate_crop(self):
        if self.edited_image is not None:
            self.edit_canvas.bind("<ButtonPress-1>", self._on_mouse_press)
            self.edit_canvas.bind("<B1-Motion>", self._on_mouse_drag)
            self.edit_canvas.bind("<ButtonRelease-1>", self._on_mouse_release)

    def resize_image(self, value):
        if self.edited_image is None:
            return
        percent = int(float(value))
        w = int(self.resize_base_image.shape[1] * percent / 100)
        h = int(self.resize_base_image.shape[0] * percent / 100)
        resized = cv2.resize(self.resize_base_image, (w, h), interpolation=cv2.INTER_AREA)
        self.edited_image = resized
        self._update_edit_canvas()

    def save_image(self):
        if self.edited_image is not None:
            path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=SAVE_FILETYPES)
            if path:
                cv2.imwrite(path, self.edited_image)
                messagebox.showinfo("Saved", "Image saved successfully.")

    def apply_grayscale(self):
        if self.edited_image is not None:
            self.image_history.append(self.edited_image.copy())
            self.redo_stack.clear()
            gray = cv2.cvtColor(self.edited_image, cv2.COLOR_BGR2GRAY)
            self.edited_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            self._update_edit_canvas()

    def apply_blur(self):
        if self.edited_image is not None:
            self.image_history.append(self.edited_image.copy())
            self.redo_stack.clear()
            self.edited_image = cv2.GaussianBlur(self.edited_image, (9, 9), 0)
            self._update_edit_canvas()

    def undo(self):
        if self.image_history:
            self.redo_stack.append(self.edited_image.copy())
            self.edited_image = self.image_history.pop()
            self._update_edit_canvas()

    def redo(self):
        if self.redo_stack:
            self.image_history.append(self.edited_image.copy())
            self.edited_image = self.redo_stack.pop()
            self._update_edit_canvas()

    def _on_mouse_press(self, event):
        self.crop_coords = (event.x, event.y, event.x, event.y)

    def _on_mouse_drag(self, event):
        x0, y0, _, _ = self.crop_coords
        self.crop_coords = (x0, y0, event.x, event.y)
        self._update_edit_canvas()
        # Clear previous rectangle if it exists
        if self.crop_rectangle:
            self.edit_canvas.delete(self.crop_rectangle)
        self.crop_rectangle = self.edit_canvas.create_rectangle(
            x0, y0, event.x, event.y, outline=CROP_RECT_COLOR, width=CROP_RECT_WIDTH)

    def _on_mouse_release(self, event):
        x1, y1, x2, y2 = self.crop_coords
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])
        # Map canvas to image coordinates
        canvas_w = self.edit_canvas.winfo_width()
        canvas_h = self.edit_canvas.winfo_height()
        img_h, img_w = self.edited_image.shape[:2]
        scale_x = img_w / canvas_w
        scale_y = img_h / canvas_h
        ix1, ix2 = int(x1 * scale_x), int(x2 * scale_x)
        iy1, iy2 = int(y1 * scale_y), int(y2 * scale_y)
        if ix2 <= ix1 or iy2 <= iy1 or ix2 > img_w or iy2 > img_h:
            return
        self.image_history.append(self.edited_image.copy())
        self.redo_stack.clear()
        self.edited_image = self.edited_image[iy1:iy2, ix1:ix2]
        self.cropped_image = self.edited_image.copy()
        self.resize_base_image = self.edited_image.copy()
        self._update_edit_canvas()
        self._update_cropped_canvas()
        self.edit_canvas.unbind("<ButtonPress-1>")
        self.edit_canvas.unbind("<B1-Motion>")
        self.edit_canvas.unbind("<ButtonRelease-1>")

    def _update_original_canvas(self):
        self._draw_image_on_canvas(self.original_canvas, self.original_image, max_size=200)

    def _update_edit_canvas(self):
        self.edit_canvas.delete("all")
        if self.edited_image is not None:
            self.tk_image = self._get_tk_image(self.edited_image)
            self.edit_canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    def _update_cropped_canvas(self):
        if self.cropped_image is not None:
            self._draw_image_on_canvas(self.cropped_canvas, self.cropped_image, max_size=200)

    def _get_tk_image(self, image):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(rgb)
        return ImageTk.PhotoImage(image_pil)

    def _draw_image_on_canvas(self, canvas, image, max_size=200):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        scale = min(max_size / h, max_size / w)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        image_pil = Image.fromarray(resized)
        tk_image = ImageTk.PhotoImage(image_pil)
        canvas.config(width=new_w, height=new_h)
        canvas.create_image(0, 0, anchor="nw", image=tk_image)
        canvas.image = tk_image

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoEditorApp(root)
    root.mainloop()
