# Display a message to inform the user that some libraries must be installed before running the script
print("Before running this script, make sure you have installed the required libraries:")
# Provide the user with instructions on how to install the necessary libraries
print("To install the necessary libraries, run:")
# Show the exact pip command to install OpenCV and Pillow
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
PREVIEW_SIZE = 200
BLUR_KERNEL = (9, 9)

# --- Image Manager Class ---
class ImageManager:
    """Handles all image operations and history for undo/redo."""
    def __init__(self):
        self.original = None
        self.current = None
        self.history = []
        self.redo_stack = []
        self.resize_base = None

    def load(self, path):
        img = cv2.imread(path)
        if img is None:
            raise ValueError("Failed to load image.")
        self.original = img
        self.current = img.copy()
        self.resize_base = img.copy()
        self.history.clear()
        self.redo_stack.clear()

    def save(self, path):
        if self.current is None:
            raise ValueError("No image to save.")
        if not cv2.imwrite(path, self.current):
            raise ValueError("Failed to save image.")

    def push_history(self):
        if self.current is not None:
            self.history.append(self.current.copy())
            self.redo_stack.clear()

    def crop(self, coords):
        x1, y1, x2, y2 = coords
        h, w = self.current.shape[:2]
        x1, x2 = sorted([max(0, x1), min(w, x2)])
        y1, y2 = sorted([max(0, y1), min(h, y2)])
        if x2 <= x1 or y2 <= y1:
            raise ValueError("Invalid crop area.")
        self.push_history()
        self.current = self.current[y1:y2, x1:x2]
        self.resize_base = self.current.copy()

    def resize(self, percent):
        if self.current is None or self.resize_base is None:
            return
        self.push_history()
        w = int(self.resize_base.shape[1] * percent / 100)
        h = int(self.resize_base.shape[0] * percent / 100)
        if w < 1 or h < 1:
            raise ValueError("Resize too small.")
        self.current = cv2.resize(self.resize_base, (w, h), interpolation=cv2.INTER_AREA)

    def grayscale(self):
        if self.current is not None:
            self.push_history()
            gray = cv2.cvtColor(self.current, cv2.COLOR_BGR2GRAY)
            self.current = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    def blur(self):
        if self.current is not None:
            self.push_history()
            self.current = cv2.GaussianBlur(self.current, BLUR_KERNEL, 0)

    def undo(self):
        if self.history:
            self.redo_stack.append(self.current.copy())
            self.current = self.history.pop()
            self.resize_base = self.current.copy()

    def redo(self):
        if self.redo_stack:
            self.history.append(self.current.copy())
            self.current = self.redo_stack.pop()
            self.resize_base = self.current.copy()

    def reset(self):
        if self.original is not None:
            self.current = self.original.copy()
            self.resize_base = self.current.copy()
            self.history.clear()
            self.redo_stack.clear()

# Main application class
class PhotoEditorApp:
    """Main GUI application for Photo Editor Pro."""
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
        self.resize_base_image = None  # Image used as base for resizing
        
        # Undo and redo stacks
        self.image_history = []             # Stack for undo
        self.redo_stack = []                # Stack for redo

        self.img_mgr = ImageManager()
        self.crop_start = None
        self.crop_preview = None

        # Build GUI and bind shortcuts
        self._build_ui()
        self._bind_shortcuts()
        self._set_buttons_state("disabled")  # Disable actions at startup

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
        self._create_button("Grayscale", self.apply_grayscale, "Ctrl+G"))
        self._create_button("Blur", self.apply_blur, "Ctrl+B"))
        self._create_button("Undo", self.undo, "Ctrl+Z")
        self._create_button("Redo", self.redo, "Ctrl+Y")
        self._create_button("Reset", self.reset_image, "Ctrl+R")

        # Resize slider
        ttk.Label(self.left_frame, text="Resize (%)").pack(pady=5)
        self.resize_slider = ttk.Scale(
            self.left_frame, from_=MIN_RESIZE_PERCENT, to=MAX_RESIZE_PERCENT,
            command=self.resize_image, orient="horizontal")
        self.resize_slider.set(DEFAULT_RESIZE_PERCENT)
        self.resize_slider.pack()

        # Canvas for displaying editable image
        self.edit_canvas = tk.Canvas(self.center_frame, bg="gray")
        self.edit_canvas.pack(fill="both", expand=True)

        # Canvases for displaying original and cropped images
        ttk.Label(self.right_frame, text="Original Image").pack(pady=5)
        self.original_canvas = tk.Canvas(self.right_frame, width=PREVIEW_SIZE, height=PREVIEW_SIZE, bg="lightgray")
        self.original_canvas.pack()
        ttk.Label(self.right_frame, text="Cropped Image").pack(pady=5)
        self.cropped_canvas = tk.Canvas(self.right_frame, width=PREVIEW_SIZE, height=PREVIEW_SIZE, bg="lightgray")
        self.cropped_canvas.pack()

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
        self.set_status("Welcome to Photo Editor Pro!")

    def _create_button(self, text, command, shortcut):
        # Helper to create a button and store it for state management
        frame = ttk.Frame(self.left_frame)
        frame.pack(pady=2, fill='x')
        btn = ttk.Button(frame, text=text, command=command)
        btn.pack(side='left', padx=5)
        ttk.Label(frame, text=shortcut).pack(side='right')
        if not hasattr(self, 'buttons'):
            self.buttons = {}
        self.buttons[text] = btn

    def _set_buttons_state(self, state):
        # Enable or disable tool buttons based on state
        for key in ["Crop Image", "Save Image", "Grayscale", "Blur", "Undo", "Redo", "Reset"]:
            if key in self.buttons:
                self.buttons[key]['state'] = state
        # Also enable/disable the resize slider
        if state == "normal":
            self.resize_slider.state(["!disabled"])
        else:
            self.resize_slider.state(["disabled"])

    def _bind_shortcuts(self):
        # Bind keyboard shortcuts to functions
        self.root.bind('<Control-O>', lambda e: self.open_image())
        self.root.bind('<Control-C>', lambda e: self.activate_crop())
        self.root.bind('<Control-Z>', lambda e: self.undo())
        self.root.bind('<Control-Y>', lambda e: self.redo())
        self.root.bind('<Control-S>', lambda e: self.save_image())
        self.root.bind('<Control-G>', lambda e: self.apply_grayscale())
        self.root.bind('<Control-B>', lambda e: self.apply_blur())
        self.root.bind('<Control-R>', lambda e: self.reset_image())

    def set_status(self, msg):
        self.status_var.set(msg)

    def open_image(self):
        # Open and load image from file and reset the editor state
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if not path:
            return
        try:
            self.img_mgr.load(path)
            self.original_image = self.img_mgr.original
            self.edited_image = self.img_mgr.current
            self.resize_base_image = self.img_mgr.resize_base
            self.image_history.clear()
            self.redo_stack.clear()
            self._update_original_canvas()
            self._update_edit_canvas()
            self.set_status("Image loaded.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.set_status("Failed to load image.")
        self._set_buttons_state("normal")  # Enable actions

    def save_image(self):
        # Save the current edited image
        if self.edited_image is None:
            messagebox.showwarning("No image", "No image to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=SAVE_FILETYPES)
        if not path:
            return
        try:
            self.img_mgr.save(path)
            self.set_status("Image saved.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.set_status("Failed to save image.")
 
    def activate_crop(self):
       # Enable cropping mode if an image is loaded
        if self.edited_image is None:
            messagebox.showwarning("No image", "Load an image before cropping.")
            return
        self.set_status("Draw a rectangle to crop.")
        self.edit_canvas.bind("<ButtonPress-1>", self._on_mouse_press)
        self.edit_canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.edit_canvas.bind("<ButtonRelease-1>", self._on_mouse_release)

    def _on_mouse_press(self, event):
        # Start crop rectangle
        self.crop_coords = (event.x, event.y, event.x, event.y)
        if self.crop_rectangle:
            self.edit_canvas.delete(self.crop_rectangle)
            self.crop_rectangle = None

        def _on_mouse_drag(self, event):
        # Draw cropping rectangle while dragging
        x0, y0, _, _ = self.crop_coords
        self.crop_coords = (x0, y0, event.x, event.y)
        self._update_edit_canvas()
        # Clear previous rectangle if it exists
        if self.crop_rectangle:
            self.edit_canvas.delete(self.crop_rectangle)
        self.crop_rectangle = self.edit_canvas.create_rectangle(
            x0, y0, event.x, event.y, outline=CROP_RECT_COLOR, width=CROP_RECT_WIDTH)

        def _on_mouse_release(self, event):
        # Finalize crop and update image
        if self.edited_image is None:
            return
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
            messagebox.showwarning("Invalid crop", "Please select a valid crop area.")
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
        if self.crop_rectangle:
            self.edit_canvas.delete(self.crop_rectangle)
            self.crop_rectangle = None
        try:
            self.img_mgr.crop((ix1, iy1, ix2, iy2))
            self._update_all_canvases()
            self.set_status("Image cropped.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.set_status("Crop failed.")
        self._set_buttons_state("normal")

    def resize_image(self, value):
        # Resize image based on slider value
        if self.edited_image is None or self.resize_base_image is None:
            return
        try:
            percent = int(float(value))
            w = int(self.resize_base_image.shape[1] * percent / 100)
            h = int(self.resize_base_image.shape[0] * percent / 100)
            if w < 1 or h < 1:
                raise ValueError("Resize too small.")
            resized = cv2.resize(self.resize_base_image, (w, h), interpolation=cv2.INTER_AREA)
            self.edited_image = resized
            self._update_edit_canvas()
            self.set_status(f"Image resized to {percent}%.")
        except Exception as e:
            messagebox.showerror("Error", f"Resize failed: {e}")
            self.set_status("Resize failed.")
        self._set_buttons_state("normal")

    def apply_grayscale(self):
        # Apply grayscale effect
        if self.edited_image is None:
            messagebox.showwarning("No image", "No image loaded.")
            return
        self.image_history.append(self.edited_image.copy())
        self.redo_stack.clear()
        self.edited_image = cv2.cvtColor(self.edited_image, cv2.COLOR_BGR2GRAY)
        self.edited_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        self._update_edit_canvas()
        self.set_status("Grayscale applied.")
        self._set_buttons_state("normal")

    def apply_blur(self):
         # Apply blur effect
        if self.edited_image is None:
            messagebox.showwarning("No image", "No image loaded.")
            return
        self.image_history.append(self.edited_image.copy())
        self.redo_stack.clear()
        self.edited_image = cv2.GaussianBlur(self.edited_image, BLUR_KERNEL, 0)
        self._update_edit_canvas()
        self.set_status("Blur applied.")
        self._set_buttons_state("normal")

    def undo(self):
        # Undo the last image operation
        if not self.image_history:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        self.redo_stack.append(self.edited_image.copy())
        self.edited_image = self.image_history.pop()
        self._update_edit_canvas()
        self.set_status("Undo.")
        self._set_buttons_state("normal")

    def redo(self):
        # Redo previously undone action
        if not self.redo_stack:
            messagebox.showinfo("Redo", "Nothing to redo.")
            return
        self.image_history.append(self.edited_image.copy())
        self.edited_image = self.redo_stack.pop()
        self._update_edit_canvas()
        self.set_status("Redo.")
        self._set_buttons_state("normal")

    def reset_image(self):
        # Reset the image to the original loaded state
        if self.original_image is not None:
            self.edited_image = self.original_image.copy()
            self.resize_base_image = self.edited_image.copy()
            self.cropped_image = None
            self.image_history.clear()
            self.redo_stack.clear()
            self._update_edit_canvas()
            self._update_cropped_canvas()
            self.set_status("Image reset.")
            self._set_buttons_state("disabled")
        else:
            self._set_buttons_state("disabled")   

    def _update_original_canvas(self):
        # Draw the original image in the preview canvas
        self._draw_image_on_canvas(self.original_canvas, self.original_image, max_size=PREVIEW_SIZE)

    def _update_edit_canvas(self):
        # Update editable canvas with the current working image
        self.edit_canvas.delete("all")
        if self.edited_image is not None:
            self.tk_image = self._get_tk_image(self.edited_image)
            self.edit_canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    def _update_cropped_canvas(self):
         # Update cropped image canvas
        if self.cropped_image is not None:
            self._draw_image_on_canvas(self.cropped_canvas, self.cropped_image, max_size=PREVIEW_SIZE)

    def _get_tk_image(self, image):
        # Convert OpenCV image to Tkinter-compatible image
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(rgb)
        return ImageTk.PhotoImage(image_pil)

    def _draw_image_on_canvas(self, canvas, image, max_size=200):
         # Draw any image onto a canvas and auto-resize to fit
        if image is None:
            return
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        scale = min(max_size / h, max_size / w)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        image_pil = Image.fromarray(resized)
        tk_image = ImageTk.PhotoImage(image_pil)
        canvas.config(width=new_w, height=new_h)
        canvas.create_image(0, 0, anchor="nw", image=tk_image)
        canvas.image = tk_image              # Prevent garbage collection

    def _update_all_canvases(self):
            self._update_canvas(self.edit_canvas, self.img_mgr.current, fit_to_canvas=True)
            self._update_canvas(self.original_canvas, self.img_mgr.original, max_size=PREVIEW_SIZE)
            self._update_canvas(self.cropped_canvas, self.img_mgr.current, max_size=PREVIEW_SIZE)
    
    def _update_canvas(self, canvas, image, max_size=None, fit_to_canvas=False):
        canvas.delete("all")
        if image is None:
            return
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        if fit_to_canvas:
            canvas_w, canvas_h = canvas.winfo_width(), canvas.winfo_height()
            scale = min(canvas_w / w, canvas_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
        elif max_size:
            scale = min(max_size / h, max_size / w)
            new_w, new_h = int(w * scale), int(h * scale)
        else:
            new_w, new_h = w, h
        resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        image_pil = Image.fromarray(resized)
        tk_image = ImageTk.PhotoImage(image_pil)
        canvas.config(width=new_w, height=new_h)
        canvas.create_image(0, 0, anchor="nw", image=tk_image)
        canvas.image = tk_image  # Prevent garbage collection

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoEditorApp(root)
    root.mainloop()
