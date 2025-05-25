# --- Display a message to inform the user that some libraries must be installed before running the script ---
print("Before running this script, make sure you have installed the required libraries:")

# --- Provide the user with instructions on how to install the necessary libraries ---
print("To install the necessary libraries, run:")

# --- Show the exact pip command to install OpenCV and Pillow ---
print("'pip install opencv-python' and 'pip install pillow'")

# --- Import necessary libraries ---
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np

# --- Constants for Image Processing and UI Configuration ---
WINDOW_TITLE = "Photo Editor Pro"                                               # Title of the application window
WINDOW_WIDTH = 1500                                                             # Width of the window
WINDOW_HEIGHT = 800                                                             # Height of the window
CROP_RECT_COLOR = "blue"                                                        # Color of the cropping rectangle
CROP_RECT_WIDTH = 2                                                             # Thickness of the cropping rectangle
MIN_RESIZE_PERCENT = 5                                                          # Minimum resize scale
MAX_RESIZE_PERCENT = 300                                                        # Maximum resize scale
DEFAULT_RESIZE_PERCENT = 100                                                    # Default resize scale
SAVE_FILETYPES = [("PNG", "*.png"), ("JPEG", "*.jpg"), ("All Files", "*.*")]    # File types for saving
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
        self.original = img.copy()
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
            # Limit history size to prevent memory issues
            if len(self.history) > 20:
                self.history.pop(0)

    def crop(self, coords):
        x1, y1, x2, y2 = coords
        h, w = self.current.shape[:2]
        x1, x2 = max(0, min(x1, x2)), min(w, max(x1, x2))
        y1, y2 = max(0, min(y1, y2)), min(h, max(y1, y2))
        if x2 <= x1 or y2 <= y1:
            raise ValueError("Invalid crop area.")
        self.push_history()
        self.current = self.current[y1:y2, x1:x2].copy()
        self.resize_base = self.current.copy()

    def resize(self, percent):
        if self.resize_base is None:
            return
        self.push_history()
        w = max(1, int(self.resize_base.shape[1] * percent / 100))
        h = max(1, int(self.resize_base.shape[0] * percent / 100))
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
            return True
        return False

    def redo(self):
        if self.redo_stack:
            self.history.append(self.current.copy())
            self.current = self.redo_stack.pop()
            self.resize_base = self.current.copy()
            return True
        return False

    def reset(self):
        if self.original is not None:
            self.current = self.original.copy()
            self.resize_base = self.current.copy()
            self.history.clear()
            self.redo_stack.clear()
            return True
        return False

# --- Main Application Class ---
class PhotoEditorApp:
    """Main GUI application for Photo Editor Pro."""
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        
        # Initialize image manager
        self.img_mgr = ImageManager()
        
        # Crop state
        self.crop_start = None
        self.crop_rectangle = None
        self.cropping_mode = False
        
        # UI elements
        self.buttons = {}
        self.resize_slider = None
        
        self._build_ui()
        self._bind_shortcuts()
        self._set_buttons_state("disabled")

    def _build_ui(self):
        # Create main layout
        self.main_frame = ttk.PanedWindow(self.root, orient='horizontal')
        self.main_frame.pack(fill='both', expand=True)
        
        # Left panel for tools
        self.left_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.left_frame, weight=0)
        
        # Center panel for main image
        self.center_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.center_frame, weight=1)
        
        # Right panel for previews
        self.right_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.right_frame, weight=0)

        # Build tool panel
        self._build_tool_panel()
        
        # Build main canvas
        self._build_main_canvas()
        
        # Build preview panels
        self._build_preview_panels()
        
        # Build status bar
        self._build_status_bar()

    def _build_tool_panel(self):
        ttk.Label(self.left_frame, text="Tools", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # File operations
        file_frame = ttk.LabelFrame(self.left_frame, text="File")
        file_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_button(file_frame, "Open Image", self.open_image, "Ctrl+O")
        self._create_button(file_frame, "Save Image", self.save_image, "Ctrl+S")
        
        # Edit operations
        edit_frame = ttk.LabelFrame(self.left_frame, text="Edit")
        edit_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_button(edit_frame, "Crop Image", self.activate_crop, "Ctrl+X")
        self._create_button(edit_frame, "Undo", self.undo, "Ctrl+Z")
        self._create_button(edit_frame, "Redo", self.redo, "Ctrl+Y")
        self._create_button(edit_frame, "Reset", self.reset_image, "Ctrl+R")
        
        # Effects
        effects_frame = ttk.LabelFrame(self.left_frame, text="Effects")
        effects_frame.pack(fill='x', padx=5, pady=5)
        
        self._create_button(effects_frame, "Grayscale", self.apply_grayscale, "Ctrl+G")
        self._create_button(effects_frame, "Blur", self.apply_blur, "Ctrl+B")
        
        # Resize controls
        resize_frame = ttk.LabelFrame(self.left_frame, text="Resize")
        resize_frame.pack(fill='x', padx=5, pady=5)
        
        self.resize_var = tk.IntVar(value=DEFAULT_RESIZE_PERCENT)
        self.resize_slider = ttk.Scale(
            resize_frame, 
            from_=MIN_RESIZE_PERCENT, 
            to=MAX_RESIZE_PERCENT,
            variable=self.resize_var,
            orient="horizontal",
            command=self.resize_image
        )
        self.resize_slider.pack(fill='x', padx=5, pady=5)
        
        # Label to show current percentage
        self.resize_label = ttk.Label(resize_frame, text="100%")
        self.resize_label.pack(pady=2)

    def _build_main_canvas(self):
        canvas_frame = ttk.Frame(self.center_frame)
        canvas_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Add scrollbars
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient='horizontal')
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical')
        
        self.edit_canvas = tk.Canvas(
            canvas_frame, 
            bg="lightgray",
            scrollregion=(0, 0, 0, 0),
            xscrollcommand=h_scrollbar.set,
            yscrollcommand=v_scrollbar.set
        )
        
        h_scrollbar.config(command=self.edit_canvas.xview)
        v_scrollbar.config(command=self.edit_canvas.yview)
        
        # Pack scrollbars and canvas
        h_scrollbar.pack(side='bottom', fill='x')
        v_scrollbar.pack(side='right', fill='y')
        self.edit_canvas.pack(side='left', fill='both', expand=True)

    def _build_preview_panels(self):
        ttk.Label(self.right_frame, text="Original", font=('Arial', 10, 'bold')).pack(pady=5)
        self.original_canvas = tk.Canvas(
            self.right_frame, 
            width=PREVIEW_SIZE, 
            height=PREVIEW_SIZE, 
            bg="lightgray"
        )
        self.original_canvas.pack(pady=5)
        
        ttk.Label(self.right_frame, text="Current", font=('Arial', 10, 'bold')).pack(pady=5)
        self.preview_canvas = tk.Canvas(
            self.right_frame, 
            width=PREVIEW_SIZE, 
            height=PREVIEW_SIZE, 
            bg="lightgray"
        )
        self.preview_canvas.pack(pady=5)

    def _build_status_bar(self):
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief="sunken", 
            anchor="w"
        )
        self.status_bar.pack(side="bottom", fill="x")
        self.set_status("Welcome to Photo Editor Pro! Open an image to get started.")

    def _create_button(self, parent, text, command, shortcut=""):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=2)
        
        btn = ttk.Button(frame, text=text, command=command)
        btn.pack(side='left', padx=5)
        
        if shortcut:
            ttk.Label(frame, text=shortcut, font=('Arial', 8)).pack(side='right')
        
        self.buttons[text] = btn

    def _update_resize_label(self, value):
        percent = int(float(value))
        self.resize_label.config(text=f"{percent}%")

    def _set_buttons_state(self, state):
        enabled_always = ["Open Image"]
        
        for name, btn in self.buttons.items():
            if name in enabled_always:
                btn['state'] = 'normal'
            else:
                btn['state'] = state
        
        if self.resize_slider:
            if state == "normal":
                self.resize_slider.state(["!disabled"])
            else:
                self.resize_slider.state(["disabled"])

    def _bind_shortcuts(self):
        shortcuts = {
            '<Control-o>': self.open_image,
            '<Control-s>': self.save_image,
            '<Control-x>': self.activate_crop,
            '<Control-z>': self.undo,
            '<Control-y>': self.redo,
            '<Control-r>': self.reset_image,
            '<Control-g>': self.apply_grayscale,
            '<Control-b>': self.apply_blur,
            '<Escape>': self.cancel_crop
        }
        
        for key, func in shortcuts.items():
            self.root.bind(key, lambda e, f=func: f())

    def set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def open_image(self):
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
            self.set_status(f"Image loaded: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
            self.set_status("Failed to load image.")

    def save_image(self):
        if self.img_mgr.current is None:
            messagebox.showwarning("No Image", "No image to save.")
            return
        
        path = filedialog.asksaveasfilename(
            defaultextension=".png", 
            filetypes=SAVE_FILETYPES
        )
        if not path:
            return
        
        try:
            self.img_mgr.save(path)
            self.set_status(f"Image saved: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {str(e)}")

    def activate_crop(self):
        if self.img_mgr.current is None:
            messagebox.showwarning("No Image", "Load an image before cropping.")
            return
        
        self.cropping_mode = True
        self.set_status("Click and drag to select crop area. Press Escape to cancel.")
        
        # Bind mouse events for cropping
        self.edit_canvas.bind("<ButtonPress-1>", self._start_crop)
        self.edit_canvas.bind("<B1-Motion>", self._update_crop)
        self.edit_canvas.bind("<ButtonRelease-1>", self._finish_crop)

    def cancel_crop(self):
        if self.cropping_mode:
            self.cropping_mode = False
            self._clear_crop_rectangle()
            self._unbind_crop_events()
            self.set_status("Crop cancelled.")

    def _start_crop(self, event):
        if not self.cropping_mode:
            return
        
        self.crop_start = (event.x, event.y)
        self._clear_crop_rectangle()

    def _update_crop(self, event):
        if not self.cropping_mode or not self.crop_start:
            return
        
        self._clear_crop_rectangle()
        self.crop_rectangle = self.edit_canvas.create_rectangle(
            self.crop_start[0], self.crop_start[1], event.x, event.y,
            outline=CROP_RECT_COLOR, width=CROP_RECT_WIDTH
        )

    def _finish_crop(self, event):
        if not self.cropping_mode or not self.crop_start:
            return
        
        try:
            # Calculate crop coordinates relative to image
            x1, y1 = self.crop_start
            x2, y2 = event.x, event.y
            
            # Get image dimensions and canvas scroll position
            canvas_w = self.edit_canvas.winfo_width()
            canvas_h = self.edit_canvas.winfo_height()
            
            if hasattr(self, 'current_image_item'):
                # Get actual image position on canvas
                img_bbox = self.edit_canvas.bbox(self.current_image_item)
                if img_bbox:
                    img_x1, img_y1, img_x2, img_y2 = img_bbox
                    
                    # Convert canvas coordinates to image coordinates
                    img_w = img_x2 - img_x1
                    img_h = img_y2 - img_y1
                    
                    # Calculate relative positions
                    rel_x1 = max(0, (x1 - img_x1) / img_w)
                    rel_y1 = max(0, (y1 - img_y1) / img_h)
                    rel_x2 = min(1, (x2 - img_x1) / img_w)
                    rel_y2 = min(1, (y2 - img_y1) / img_h)
                    
                    # Convert to actual image coordinates
                    actual_h, actual_w = self.img_mgr.current.shape[:2]
                    crop_x1 = int(rel_x1 * actual_w)
                    crop_y1 = int(rel_y1 * actual_h)
                    crop_x2 = int(rel_x2 * actual_w)
                    crop_y2 = int(rel_y2 * actual_h)
                    
                    if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                        self.img_mgr.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                        self._update_all_displays()
                        self.set_status("Image cropped successfully.")
                    else:
                        messagebox.showwarning("Invalid Crop", "Please select a valid crop area.")
            
        except Exception as e:
            messagebox.showerror("Crop Error", f"Failed to crop image: {str(e)}")
        
        finally:
            self.cropping_mode = False
            self._clear_crop_rectangle()
            self._unbind_crop_events()

    def _clear_crop_rectangle(self):
        if self.crop_rectangle:
            self.edit_canvas.delete(self.crop_rectangle)
            self.crop_rectangle = None

    def _unbind_crop_events(self):
        self.edit_canvas.unbind("<ButtonPress-1>")
        self.edit_canvas.unbind("<B1-Motion>")
        self.edit_canvas.unbind("<ButtonRelease-1>")

    def resize_image(self, value=None):
        if self.img_mgr.current is None:
            return
        
        try:
            # Get percentage from slider
            if value is not None:
                percent = int(float(value))
            else:
                percent = self.resize_var.get()
            
            # Update label
            self.resize_label.config(text=f"{percent}%")
            
            # Apply resize
            self.img_mgr.resize(percent)
            self._update_all_displays()
            self.set_status(f"Image resized to {percent}%.")
        except Exception as e:
            messagebox.showerror("Resize Error", f"Failed to resize image: {str(e)}")

    def apply_grayscale(self):
        if self.img_mgr.current is None:
            messagebox.showwarning("No Image", "No image loaded.")
            return
        
        try:
            self.img_mgr.grayscale()
            self._update_all_displays()
            self.set_status("Grayscale effect applied.")
        except Exception as e:
            messagebox.showerror("Effect Error", f"Failed to apply grayscale: {str(e)}")

    def apply_blur(self):
        if self.img_mgr.current is None:
            messagebox.showwarning("No Image", "No image loaded.")
            return
        
        try:
            self.img_mgr.blur()
            self._update_all_displays()
            self.set_status("Blur effect applied.")
        except Exception as e:
            messagebox.showerror("Effect Error", f"Failed to apply blur: {str(e)}")

    def undo(self):
        if self.img_mgr.undo():
            self._update_all_displays()
            self.set_status("Undo successful.")
        else:
            messagebox.showinfo("Undo", "Nothing to undo.")

    def redo(self):
        if self.img_mgr.redo():
            self._update_all_displays()
            self.set_status("Redo successful.")
        else:
            messagebox.showinfo("Redo", "Nothing to redo.")

    def reset_image(self):
        if self.img_mgr.original is None:
            messagebox.showwarning("No Image", "No image loaded.")
            return
        
        self.img_mgr.reset()
        self._update_all_displays()
        self.resize_var.set(DEFAULT_RESIZE_PERCENT)
        self.set_status("Image reset to original.")

    def _update_all_displays(self):
        self._update_main_canvas()
        self._update_preview_canvases()

    def _update_main_canvas(self):
        self.edit_canvas.delete("all")
        if self.img_mgr.current is not None:
            tk_image = self._opencv_to_tkinter(self.img_mgr.current)
            self.current_image_item = self.edit_canvas.create_image(
                10, 10, anchor="nw", image=tk_image
            )
            self.edit_canvas.image = tk_image  # Keep reference
            
            # Update scroll region
            self.edit_canvas.configure(scrollregion=self.edit_canvas.bbox("all"))

    def _update_preview_canvases(self):
        # Update original preview
        if self.img_mgr.original is not None:
            self._update_canvas_with_image(self.original_canvas, self.img_mgr.original)
        
        # Update current preview
        if self.img_mgr.current is not None:
            self._update_canvas_with_image(self.preview_canvas, self.img_mgr.current)

    def _update_canvas_with_image(self, canvas, cv_image):
        canvas.delete("all")
        if cv_image is None:
            return
        
        # Resize image to fit preview
        h, w = cv_image.shape[:2]
        scale = min(PREVIEW_SIZE / w, PREVIEW_SIZE / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        resized = cv2.resize(cv_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        tk_image = self._opencv_to_tkinter(resized)
        
        canvas.create_image(
            PREVIEW_SIZE // 2, PREVIEW_SIZE // 2, 
            anchor="center", image=tk_image
        )
        canvas.image = tk_image  # Keep reference

    def _opencv_to_tkinter(self, cv_image):
        """Convert OpenCV image to Tkinter PhotoImage."""
        if len(cv_image.shape) == 3:
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = cv_image
        
        pil_image = Image.fromarray(rgb_image)
        return ImageTk.PhotoImage(pil_image)

# --- Run the application ---
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = PhotoEditorApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")
