# --- Display a message to inform the user that some libraries must be installed before running the script ---
print("Before running this script, make sure you have installed the required libraries:")
print("To install the necessary libraries, run:")
print("'pip install opencv-python' and 'pip install pillow'")

# --- Import necessary libraries ---
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2

# --- Application Constants ---
WINDOW_TITLE = "Photo Editor Pro"                                           # Title of the main window
WINDOW_WIDTH = 1500                                                         # Width of the window in pixels
WINDOW_HEIGHT = 800                                                         # Height of the window in pixels
CROP_RECT_COLOR = "blue"                                                    # Color of the crop rectangle outline
CROP_RECT_WIDTH = 2                                                         # Line width of the crop rectangle
MIN_RESIZE_PERCENT = 5                                                      # Minimum resize percentage
MAX_RESIZE_PERCENT = 300                                                    # Maximum resize percentage
DEFAULT_RESIZE_PERCENT = 100                                                # Default resize percentage on load/reset
SAVE_FILETYPES = [("PNG", "*.png"),("JPEG", "*.jpg"),("All Files", "*.*")]  # File type filters for saving
PREVIEW_SIZE = 200                                                          # Size (px) of the preview canvases (square)
BLUR_KERNEL = (9, 9)                                                        # Kernel size for Gaussian blur

# --- Image Manager Class ---
class ImageManager:
    """Handles image operations (load, save, crop, resize, effects)
    and maintains history for undo/redo functionality."""

    def __init__(self):
        """Initialize empty state for images and history stacks."""
        self.original = None       # The original image loaded (unchanged)
        self.current = None        # The current working image
        self.resize_base = None    # Base image for resize operations
        self.history = []          # Stack of previous states for undo
        self.redo_stack = []       # Stack of undone states for redo

    def load(self, path):
        """Load an image from disk into original/current/resize_base, clear history."""
        img = cv2.imread(path)
        if img is None:
            raise ValueError("Failed to load image.")
        # Copy into all three buffers to start fresh
        self.original = img.copy()
        self.current = img.copy()
        self.resize_base = img.copy()
        self.history.clear()
        self.redo_stack.clear()

    def save(self, path):
        """Save the current image to disk; raise error if save fails."""
        if self.current is None:
            raise ValueError("No image to save.")
        # cv2.imwrite returns False on failure
        if not cv2.imwrite(path, self.current):
            raise ValueError("Failed to save image.")

    def push_history(self):
        """Push current state onto history stack and clear redo stack.
        Limit history size to prevent excessive memory use."""
        if self.current is not None:
            self.history.append(self.current.copy())
            self.redo_stack.clear()
            # Keep only the last 20 states
            if len(self.history) > 20:
                self.history.pop(0)

    def crop(self, coords):
        """Crop current image to the rectangle defined by coords (x1,y1,x2,y2)."""
        x1, y1, x2, y2 = coords
        h, w = self.current.shape[:2]
        # Clamp coordinates to image bounds and order correctly
        x1, x2 = max(0, min(x1, x2)), min(w, max(x1, x2))
        y1, y2 = max(0, min(y1, y2)), min(h, max(y1, y2))
        if x2 <= x1 or y2 <= y1:
            raise ValueError("Invalid crop area.")
        # Save for undo
        self.push_history()
        # Perform crop and reset resize base
        self.current = self.current[y1:y2, x1:x2].copy()
        self.resize_base = self.current.copy()

    def resize(self, percent):
        """Resize the image based on percent, scaling the resize_base image."""
        if self.resize_base is None:
            return
        self.push_history()
        # Compute new dimensions, ensure at least 1px
        w = max(1, int(self.resize_base.shape[1] * percent / 100))
        h = max(1, int(self.resize_base.shape[0] * percent / 100))
        self.current = cv2.resize(self.resize_base, (w, h), interpolation=cv2.INTER_AREA)

    def grayscale(self):
        """Convert current image to grayscale and back to BGR color for consistency."""
        if self.current is not None:
            self.push_history()
            gray = cv2.cvtColor(self.current, cv2.COLOR_BGR2GRAY)
            self.current = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    def blur(self):
        """Apply Gaussian blur to the current image."""
        if self.current is not None:
            self.push_history()
            self.current = cv2.GaussianBlur(self.current, BLUR_KERNEL, 0)

    def undo(self):
        """Revert to previous state if available; return True if undone."""
        if self.history:
            self.redo_stack.append(self.current.copy())
            self.current = self.history.pop()
            self.resize_base = self.current.copy()
            return True
        return False

    def redo(self):
        """Restore state from redo stack if available; return True if redone."""
        if self.redo_stack:
            self.history.append(self.current.copy())
            self.current = self.redo_stack.pop()
            self.resize_base = self.current.copy()
            return True
        return False

    def reset(self):
        """Reset current image to the original; clear history stacks."""
        if self.original is not None:
            self.current = self.original.copy()
            self.resize_base = self.current.copy()
            self.history.clear()
            self.redo_stack.clear()
            return True
        return False

# --- Main Application Class ---
class PhotoEditorApp:
    """GUI application using Tkinter to interact with ImageManager."""

    def __init__(self, root):
        """Initialize the main window, UI elements, and bind shortcuts."""
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Image and cropping state
        self.img_mgr = ImageManager()
        self.crop_start = None
        self.crop_rectangle = None
        self.cropping_mode = False

        # UI element references
        self.buttons = {}
        self.resize_var = tk.IntVar(value=DEFAULT_RESIZE_PERCENT)
        self.resize_slider = None

        # Build UI, bind keys, disable buttons until image loaded
        self._build_ui()
        self._bind_shortcuts()
        self._set_buttons_state("disabled")

    def _build_ui(self):
        """Create and arrange all frames and panels in the main window."""
        # PanedWindow splits horizontally: tools | main image | previews
        self.main_frame = ttk.PanedWindow(self.root, orient='horizontal')
        self.main_frame.pack(fill='both', expand=True)

        # Left tools panel
        self.left_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.left_frame, weight=0)
        # Center main canvas
        self.center_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.center_frame, weight=1)
        # Right preview panel
        self.right_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.right_frame, weight=0)

        # Build sub-panels
        self._build_tool_panel()
        self._build_main_canvas()
        self._build_preview_panels()
        self._build_status_bar()

    def _build_tool_panel(self):
        """Create tool buttons for File, Edit, Effects, and Resize."""
        ttk.Label(self.left_frame, text="Tools", font=('Arial', 12, 'bold')).pack(pady=10)

        # File operations
        file_frame = ttk.LabelFrame(self.left_frame, text="File")
        file_frame.pack(fill='x', padx=5, pady=5)
        self._create_button(file_frame, "Open", self.open_image, "Ctrl+O")
        self._create_button(file_frame, "Save", self.save_image, "Ctrl+S")

        # Edit operations
        edit_frame = ttk.LabelFrame(self.left_frame, text="Edit")
        edit_frame.pack(fill='x', padx=5, pady=5)
        self._create_button(edit_frame, "Crop", self.activate_crop, "Ctrl+C")
        self._create_button(edit_frame, "Undo", self.undo, "Ctrl+Z")
        self._create_button(edit_frame, "Redo", self.redo, "Ctrl+Y")
        self._create_button(edit_frame, "Reset", self.reset_image, "Ctrl+R")

        # Effects
        effects_frame = ttk.LabelFrame(self.left_frame, text="Effects")
        effects_frame.pack(fill='x', padx=5, pady=5)
        self._create_button(effects_frame, "Grayscale", self.apply_grayscale, "Ctrl+G")
        self._create_button(effects_frame, "Blur", self.apply_blur, "Ctrl+B")

        # Resize slider
        resize_frame = ttk.LabelFrame(self.left_frame, text="Resize")
        resize_frame.pack(fill='x', padx=5, pady=5)
        self.resize_slider = ttk.Scale(
            resize_frame, from_=MIN_RESIZE_PERCENT, to=MAX_RESIZE_PERCENT,
            variable=self.resize_var, orient="horizontal",
            command=self.resize_image
        )
        self.resize_slider.pack(fill='x', padx=5, pady=5)
        self.resize_label = ttk.Label(resize_frame, text=f"{DEFAULT_RESIZE_PERCENT}%")
        self.resize_label.pack(pady=2)

    def _build_main_canvas(self):
        """Create main canvas with scrollbars for image display."""
        canvas_frame = ttk.Frame(self.center_frame)
        canvas_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Horizontal and vertical scrollbars
        h_scroll = ttk.Scrollbar(canvas_frame, orient='horizontal')
        v_scroll = ttk.Scrollbar(canvas_frame, orient='vertical')
        self.edit_canvas = tk.Canvas(
            canvas_frame, bg="lightgray", scrollregion=(0,0,0,0),
            xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set
        )
        h_scroll.config(command=self.edit_canvas.xview)
        v_scroll.config(command=self.edit_canvas.yview)
        # Pack scrollbars and canvas
        h_scroll.pack(side='bottom', fill='x')
        v_scroll.pack(side='right', fill='y')
        self.edit_canvas.pack(side='left', fill='both', expand=True)

    def _build_preview_panels(self):
        """Create two small canvases to preview original and current images."""
        ttk.Label(self.right_frame, text="Original", font=('Arial',10,'bold')).pack(pady=5)
        self.original_canvas = tk.Canvas(self.right_frame, width=PREVIEW_SIZE, height=PREVIEW_SIZE, bg="lightgray")
        self.original_canvas.pack(pady=5)

        ttk.Label(self.right_frame, text="Current", font=('Arial',10,'bold')).pack(pady=5)
        self.current_canvas = tk.Canvas(self.right_frame, width=PREVIEW_SIZE, height=PREVIEW_SIZE, bg="lightgray")
        self.current_canvas.pack(pady=5)

    def _build_status_bar(self):
        """Create a status bar at the bottom for user feedback."""
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status_bar.pack(side='bottom', fill='x')
        self.set_status("Welcome! Load an image to start.")

    def _create_button(self, parent, text, command, shortcut=""):
        """Helper to create a button with optional shortcut label."""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=2)
        btn = ttk.Button(frame, text=text, command=command)
        btn.pack(side='left', padx=5)
        if shortcut:
            ttk.Label(frame, text=shortcut, font=('Arial', 8)).pack(side='right')
        self.buttons[text] = btn

    def _bind_shortcuts(self):
        """Bind keyboard shortcuts to commands for quick access."""
        keys = {
            '<Control-o>': self.open_image,
            '<Control-s>': self.save_image,
            '<Control-c>': self.activate_crop,
            '<Control-z>': self.undo,
            '<Control-y>': self.redo,
            '<Control-r>': self.reset_image,
            '<Control-g>': self.apply_grayscale,
            '<Control-b>': self.apply_blur,
            '<Escape>': self.cancel_crop
        }
        for k, f in keys.items():
            self.root.bind(k, lambda e, func=f: func())

    def _set_buttons_state(self, state):
        """Enable or disable buttons (except Open) and the resize slider."""
        for name, btn in self.buttons.items():
            btn['state'] = 'normal' if name == "Open" else state
        if self.resize_slider:
            self.resize_slider.state(['!disabled'] if state == 'normal' else ['disabled'])

    def set_status(self, msg):
        """Update status bar text and force UI refresh."""
        self.status_var.set(msg)
        self.root.update_idletasks()

    def open_image(self):
        """Open file dialog, load image, update UI, and enable controls."""
        filetypes = [
            ("Image Files", "*.png *.jpg *.jpeg *.bmp *.tiff *.gif"),
            ("All Files", "*.*")
        ]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if not path:
            return
        try:
            self.img_mgr.load(path)
            self._update_all_displays()
            self._set_buttons_state("normal")
            self.set_status(f"Loaded: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.set_status("Load failed.")

    def save_image(self):
        """Save current image via Save As dialog."""
        if self.img_mgr.current is None:
            messagebox.showwarning("No Image", "No image to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=SAVE_FILETYPES)
        if not path:
            return
        try:
            self.img_mgr.save(path)
            self.set_status(f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def activate_crop(self):
        """Enable cropping mode and bind mouse events."""
        if self.img_mgr.current is None:
            messagebox.showwarning("No Image", "Load before cropping.")
            return
        self.cropping_mode = True
        self.set_status("Drag to crop, Esc to cancel.")
        self.edit_canvas.bind("<ButtonPress-1>", self._start_crop)
        self.edit_canvas.bind("<B1-Motion>", self._update_crop)
        self.edit_canvas.bind("<ButtonRelease-1>", self._finish_crop)

    def cancel_crop(self):
        """Cancel cropping mode, clear rectangle and unbind events."""
        if not self.cropping_mode:
            return
        self.cropping_mode = False
        self._clear_crop_rectangle()
        self._unbind_crop_events()
        self.set_status("Crop cancelled.")

    def _start_crop(self, event):
        """Record starting point and clear old rectangle."""
        if not self.cropping_mode:
            return
        self.crop_start = (event.x, event.y)
        self._clear_crop_rectangle()

    def _update_crop(self, event):
        """Draw a rectangle as the mouse is dragged."""
        if not self.cropping_mode or not self.crop_start:
            return
        self._clear_crop_rectangle()
        x0, y0 = self.crop_start
        self.crop_rectangle = self.edit_canvas.create_rectangle(
            x0, y0, event.x, event.y,
            outline=CROP_RECT_COLOR, width=CROP_RECT_WIDTH
        )

    def _finish_crop(self, event):
        """Calculate actual crop coords, perform crop, then cleanup."""
        if not self.cropping_mode or not self.crop_start:
            return
        try:
            x1, y1 = self.crop_start
            x2, y2 = event.x, event.y
            # Get bounding box of image on canvas
            if hasattr(self, 'current_image_item'):
                bbox = self.edit_canvas.bbox(self.current_image_item)
                if bbox:
                    ix1, iy1, ix2, iy2 = bbox
                    img_w, img_h = ix2 - ix1, iy2 - iy1
                    # Convert canvas coords to relative [0..1]
                    rx1 = max(0, (x1 - ix1) / img_w)
                    ry1 = max(0, (y1 - iy1) / img_h)
                    rx2 = min(1, (x2 - ix1) / img_w)
                    ry2 = min(1, (y2 - iy1) / img_h)
                    # Map to actual image pixel coords
                    ch, cw = self.img_mgr.current.shape[:2]
                    cx1 = int(rx1 * cw); cy1 = int(ry1 * ch)
                    cx2 = int(rx2 * cw); cy2 = int(ry2 * ch)
                    # Perform the crop if valid
                    if cx2 > cx1 and cy2 > cy1:
                        self.img_mgr.crop((cx1, cy1, cx2, cy2))
                        self._update_all_displays()
                        self.set_status("Cropped.")
                    else:
                        messagebox.showwarning("Invalid", "Select valid area.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.cropping_mode = False
            self._clear_crop_rectangle()
            self._unbind_crop_events()

    def _clear_crop_rectangle(self):
        """Remove the crop rectangle overlay from canvas."""
        if self.crop_rectangle:
            self.edit_canvas.delete(self.crop_rectangle)
            self.crop_rectangle = None

    def _unbind_crop_events(self):
        """Unbind all mouse events related to cropping."""
        self.edit_canvas.unbind("<ButtonPress-1>")
        self.edit_canvas.unbind("<B1-Motion>")
        self.edit_canvas.unbind("<ButtonRelease-1>")

    def resize_image(self, value=None):
        """Resize image to given percent from slider, update UI."""
        if self.img_mgr.current is None:
            return
        try:
            percent = int(float(value)) if value is not None else self.resize_var.get()
            self.resize_label.config(text=f"{percent}%")
            self.img_mgr.resize(percent)
            self._update_all_displays()
            self.set_status(f"Resized to {percent}%.")
        except Exception as e:
            messagebox.showerror("Resize Error", str(e))

    def apply_grayscale(self):
        """Apply grayscale effect and refresh UI."""
        if self.img_mgr.current is None:
            messagebox.showwarning("No Image", "Load before effect.")
            return
        try:
            self.img_mgr.grayscale()
            self._update_all_displays()
            self.set_status("Grayscale applied.")
        except Exception as e:
            messagebox.showerror("Effect Error", str(e))

    def apply_blur(self):
        """Apply blur effect and refresh UI."""
        if self.img_mgr.current is None:
            messagebox.showwarning("No Image", "Load before effect.")
            return
        try:
            self.img_mgr.blur()
            self._update_all_displays()
            self.set_status("Blur applied.")
        except Exception as e:
            messagebox.showerror("Effect Error", str(e))

    def undo(self):
        """Perform undo via ImageManager and refresh UI."""
        if self.img_mgr.undo():
            self._update_all_displays()
            self.set_status("Undo.")
        else:
            messagebox.showinfo("Undo", "Nothing to undo.")

    def redo(self):
        """Perform redo via ImageManager and refresh UI."""
        if self.img_mgr.redo():
            self._update_all_displays()
            self.set_status("Redo.")
        else:
            messagebox.showinfo("Redo", "Nothing to redo.")

    def reset_image(self):
        """Reset image to original state and refresh UI."""
        if self.img_mgr.original is None:
            messagebox.showwarning("No Image", "Load before reset.")
            return
        self.img_mgr.reset()
        self._update_all_displays()
        # Reset slider and label
        self.resize_var.set(DEFAULT_RESIZE_PERCENT)
        self.resize_label.config(text=f"{DEFAULT_RESIZE_PERCENT}%")
        self.set_status("Reset to original.")

    def _update_all_displays(self):
        """Refresh both main canvas and preview canvases."""
        self._update_main_canvas()
        self._update_preview_canvases()

    def _update_main_canvas(self):
        """Draw the current image on the main canvas with scrollregion update."""
        self.edit_canvas.delete("all")
        if self.img_mgr.current is not None:
            tk_img = self._opencv_to_tkinter(self.img_mgr.current)
            self.current_image_item = self.edit_canvas.create_image(
                0, 0, anchor="nw", image=tk_img
            )
            # Keep reference to prevent garbage collection
            self.edit_canvas.image = tk_img
            # Update scrollable region to image bounds
            self.edit_canvas.configure(scrollregion=self.edit_canvas.bbox("all"))

    def _update_preview_canvases(self):
        """Update the small preview canvases for original and current images."""
        if self.img_mgr.original is not None:
            self._update_canvas_with_image(self.original_canvas, self.img_mgr.original)
        if self.img_mgr.current is not None:
            self._update_canvas_with_image(self.current_canvas, self.img_mgr.current)

    def _update_canvas_with_image(self, canvas, cv_image):
        """Helper to draw a resized cv_image into a square preview canvas."""
        canvas.delete("all")
        if cv_image is None:
            return
        h, w = cv_image.shape[:2]
        scale = min(PREVIEW_SIZE / w, PREVIEW_SIZE / h)
        nw, nh = int(w * scale), int(h * scale)
        resized = cv2.resize(cv_image, (nw, nh), interpolation=cv2.INTER_AREA)
        tk_img = self._opencv_to_tkinter(resized)
        canvas.create_image(PREVIEW_SIZE//2, PREVIEW_SIZE//2, anchor="center", image=tk_img)
        canvas.image = tk_img

    def _opencv_to_tkinter(self, cv_image):
        """Convert an OpenCV BGR or grayscale image to Tkinter PhotoImage."""
        if len(cv_image.shape) == 3:
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        return ImageTk.PhotoImage(Image.fromarray(cv_image))

# --- Run the application ---
if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoEditorApp(root)
    root.mainloop()
