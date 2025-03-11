import ttkbootstrap as ttk
import os
from PIL import Image, ImageTk
from tkinter import PhotoImage
import base64

class SearchBar(ttk.Frame):
    def __init__(self, master, add_token_callback, search_callback, sort_callback, app=None):
        super().__init__(master)
        # Use pack instead of grid for the frame itself
        self.pack(fill="x", padx=20, pady=20)
        
        # Store the app reference for accessing methods
        self.app = app
        
        # Create a container frame for the search elements
        self.container = ttk.Frame(self)
        self.container.pack(fill="x")
        
        # Create custom button style with padding - remove borderradius
        self.button_style = ttk.Style()
        self.button_style.configure("Custom.TButton", padding=6)
        # These are standard ttk style options that should work
        self.button_style.configure("Custom.TButton", relief="flat")

        # Create a frame for the search input
        self.search_frame = ttk.Frame(self.container)
        self.search_frame.pack(side="left", fill="x", expand=True)
        
        self.search_input = ttk.Entry(self.search_frame)
        self.search_input.pack(side="left", fill="x", expand=True)
        self.search_input.bind("<KeyRelease>", lambda event: search_callback(self.search_input.get()))
        
        # Load icons after initialization
        self.load_fixed_size_icons()

        # Initialize buttons with text fallbacks first
        # Sort button
        self.sort_btn = ttk.Button(
            self.container, 
            text="↑↓",
            command=sort_callback,
            style="Custom.TButton"
        )
        self.sort_btn.pack(side="left", padx=5)
        
        # Add button
        self.add_btn = ttk.Button(
            self.container, 
            text="+",
            command=add_token_callback,
            style="Custom.TButton"
        )
        self.add_btn.pack(side="left", padx=5)
        
        # Create settings button with a text symbol
        self.settings_btn = ttk.Button(
            self.container, 
            text="⚙",
            command=self.show_settings,
            style="Custom.TButton"
        )
        self.settings_btn.pack(side="right", padx=5)
        
        # Update buttons with icons after packing
        self.after(100, self.update_buttons_with_icons)

    def load_fixed_size_icons(self):
        """Load all icons with a fixed size of 16px"""
        # Fixed size of 16px for all icons
        icon_size = 16
        print(f"Loading all icons with fixed size of {icon_size}px")
        
        # Load plus icon
        try:
            path = "icons/plus.png"
            if os.path.exists(path):
                img = Image.open(path)
                img = img.resize((icon_size, icon_size), Image.LANCZOS)
                self.plus_icon = ImageTk.PhotoImage(img)
                print(f"Loaded plus icon at {icon_size}px")
            else:
                print(f"Plus icon file not found: {path}")
                self.plus_icon = None
        except Exception as e:
            print(f"Failed to load plus icon: {e}")
            self.plus_icon = None
            
        # Load sort icons
        try:
            # Sort ascending
            path = "icons/sort_asc.png"
            if os.path.exists(path):
                img = Image.open(path)
                img = img.resize((icon_size, icon_size), Image.LANCZOS)
                self.sort_asc_icon = ImageTk.PhotoImage(img)
                print(f"Loaded sort_asc icon at {icon_size}px")
            else:
                print(f"Sort asc icon file not found: {path}")
                self.sort_asc_icon = None
                
            # Sort descending
            path = "icons/sort_desc.png"
            if os.path.exists(path):
                img = Image.open(path)
                img = img.resize((icon_size, icon_size), Image.LANCZOS)
                self.sort_desc_icon = ImageTk.PhotoImage(img)
                print(f"Loaded sort_desc icon at {icon_size}px")
            else:
                print(f"Sort desc icon file not found: {path}")
                self.sort_desc_icon = None
        except Exception as e:
            print(f"Failed to load sort icons: {e}")
            self.sort_asc_icon = None
            self.sort_desc_icon = None
            
        # Load settings icon
        try:
            path = "icons/settings.png"
            if os.path.exists(path):
                # Open and convert to RGBA to ensure transparency is handled
                img = Image.open(path).convert("RGBA")
                img = img.resize((icon_size, icon_size), Image.LANCZOS)
                # Create a PhotoImage with transparency
                self.settings_icon = ImageTk.PhotoImage(img)
                print(f"Loaded settings icon at {icon_size}px")
            else:
                print(f"Settings icon file not found: {path}")
                self.settings_icon = None
        except Exception as e:
            print(f"Failed to load settings icon: {e}")
            self.settings_icon = None

    def update_buttons_with_icons(self):
        """Update buttons with the loaded icons"""
        # Update add button
        if hasattr(self, 'plus_icon') and self.plus_icon:
            self.add_btn.configure(image=self.plus_icon)
            print("Updated add button with plus icon")
        
        # Update sort button
        if hasattr(self, 'sort_asc_icon') and self.sort_asc_icon:
            self.sort_btn.configure(image=self.sort_asc_icon)
            print("Updated sort button with sort_asc icon")
        
        # Update settings button
        if hasattr(self, 'settings_icon') and self.settings_icon:
            self.settings_btn.configure(image=self.settings_icon)
            print("Updated settings button with settings icon")

    # Method to delegate to the app's show_settings method
    def show_settings(self):
        if self.app and hasattr(self.app, 'show_settings'):
            self.app.show_settings()
        else:
            print("Settings functionality not available")

    # Update method to handle icon switching
    def update_sort_button(self, ascending):
        if hasattr(self, 'sort_asc_icon') and hasattr(self, 'sort_desc_icon'):
            self.sort_btn.configure(image=self.sort_asc_icon if ascending else self.sort_desc_icon)
        else:
            self.sort_btn.configure(text="A→Z" if ascending else "Z→A") 