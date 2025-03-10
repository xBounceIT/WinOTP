import ttkbootstrap as ttk
from tkinter import messagebox
import tkinter.font as tkFont
import pyotp
from datetime import datetime
from models.token import Token

class TOTPFrame(ttk.Frame):
    def __init__(self, master, issuer, secret, token_name, delete_token_callback):
        # Use normal Frame without height constraint
        super().__init__(master)
        
        # Make sure the frame spans the full width of its container
        self.configure(width=480)
        
        self.issuer = issuer
        self.secret = secret
        self.totp = pyotp.TOTP(self.secret)
        self.code = ttk.StringVar(value=self.totp.now())
        self.time_remaining = ttk.StringVar(value=self.get_time_remaining())

        # Update issuer label with a larger font
        self.issuer_label = ttk.Label(self, text=self.issuer, font="Calibri 16 bold")
        
        # Fix: The correct way to access the main window from TOTPFrame
        main_window = self.winfo_toplevel()
        
        # Store the original delete callback
        self.original_delete_callback = delete_token_callback
        
        # Update delete button to use icon if available
        if hasattr(main_window, 'delete_icon') and main_window.delete_icon:
            self.delete_btn = ttk.Button(
                self, 
                image=main_window.delete_icon, 
                command=self.confirm_delete,
                bootstyle="primary"
            )
        else:
            self.delete_btn = ttk.Button(
                self, 
                text="×", 
                command=self.confirm_delete,
                bootstyle="primary"
            )
        
        # Add hover bindings for the delete button
        self.delete_btn.bind("<Enter>", self.on_delete_hover_enter)
        self.delete_btn.bind("<Leave>", self.on_delete_hover_leave)

        # New: Add token name label with truncation and dark grey foreground
        self.full_name = token_name
        self.name_label = ttk.Label(self, text="", font="Calibri 12", foreground="#A9A9A9")
        self.name_font = tkFont.Font(family="Calibri", size=12)  # Create a Font object

        # Create a container frame for the code and copy button to ensure constant distance
        self.code_frame = ttk.Frame(self)
        self.code_label = ttk.Label(self.code_frame, textvariable=self.code, font="Calibri 30 bold", width=8)  # Added fixed width to ensure code is fully visible
        self.code_label.pack(side="left", fill="x", expand=True)
        
        # Update copy button to use icon if available - also use main_window
        if hasattr(main_window, 'copy_icon') and main_window.copy_icon:
            # Use bootstyle instead of style for better color control
            self.copy_btn = ttk.Button(
                self.code_frame, 
                image=main_window.copy_icon, 
                command=self.copy_totp,
                bootstyle="primary"
            )
            # Store the confirmation icon for later use
            self.copy_confirm_icon = main_window.copy_confirm_icon if hasattr(main_window, 'copy_confirm_icon') else None
            self.original_copy_icon = main_window.copy_icon
        else:
            self.copy_btn = ttk.Button(
                self.code_frame, 
                text="Copy", 
                command=self.copy_totp,
                bootstyle="primary"
            )
        self.copy_btn.pack(side="left", padx=10)
        
        # Store original style and initialize after_id for animation
        self.original_style = "primary"
        self.after_id = None  # Use a single after_id instead of a list

        self.time_remaining_label = ttk.Label(self, textvariable=self.time_remaining, font="Calibri 16")
        
        # COMPLETELY REDESIGNED LAYOUT
        # Use a 3-column grid for maximum width utilization
        # Column 0: Main content (issuer, name, code) - expandable
        # Column 1: Center spacer - expandable
        # Column 2: Right content (delete button, countdown) - fixed width
        
        # Row 0: Issuer and delete button
        self.issuer_label.grid(row=0, column=0, sticky='w', padx=20, pady=(10, 0))
        self.delete_btn.grid(row=0, column=2, sticky='e', padx=20, pady=(10, 0))
        
        # Row 1: Name label
        self.name_label.grid(row=1, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 5))
        
        # Row 2: TOTP code and countdown
        self.code_frame.grid(row=2, column=0, sticky="w", padx=20, pady=(5, 15))
        self.time_remaining_label.grid(row=2, column=2, sticky='e', padx=20, pady=(0, 10))
        
        # Configure columns for proper expansion
        # First column takes minimal space needed for content
        self.columnconfigure(0, weight=0, minsize=250)
        # Middle column expands to fill available space
        self.columnconfigure(1, weight=1)
        # Right column takes minimal space needed for content
        self.columnconfigure(2, weight=0, minsize=50)
        
        # Disable grid propagation to ensure the frame maintains its size
        self.grid_propagate(False)
        
        # Set a minimum height
        self.configure(height=130)  # Increased from 100 to 130

        # Bind to configure event to handle resizing
        self.bind('<Configure>', self.on_resize)
        self.update_name_truncation()

    def update(self):
        self.code.set(self.totp.now())
        self.time_remaining.set(self.get_time_remaining())

    def get_time_remaining(self):
        return int(self.totp.interval - datetime.now().timestamp() % self.totp.interval)

    def copy_totp(self):
        # First copy to clipboard
        self.master.master.clipboard_clear()
        self.master.master.clipboard_append(self.code.get())
        
        # Then show visual feedback
        self.animate_copy_confirmation()
    
    def animate_copy_confirmation(self):
        # Cancel any pending reset operations to avoid timing conflicts
        if hasattr(self, 'after_id') and self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None
        
        try:
            # Store the original command and temporarily prevent clicking by removing it
            self.original_command = self.copy_btn['command']
            self.copy_btn.configure(command=lambda: None)  # Empty command instead of disabling
            
            # Change to success style using bootstyle instead of style
            self.copy_btn.configure(bootstyle="success")
            
            # Change icon if available
            if hasattr(self, 'copy_confirm_icon') and self.copy_confirm_icon:
                self.copy_btn.configure(image=self.copy_confirm_icon)
            elif not hasattr(self, 'original_copy_icon'):  # If using text instead of icon
                self.copy_btn.configure(text="✓")
            
            # Store the after ID so we can cancel it if needed
            self.after_id = self.after(1500, self.reset_copy_button)
        except Exception as e:
            print(f"Animation error: {e}")
            # Ensure we reset the button even if animation fails
            self.reset_copy_button()
    
    def reset_copy_button(self):
        try:
            # Restore original style using bootstyle
            self.copy_btn.configure(bootstyle=self.original_style)
            
            # Restore original icon or text
            if hasattr(self, 'original_copy_icon') and self.original_copy_icon:
                self.copy_btn.configure(image=self.original_copy_icon)
            elif not hasattr(self, 'original_copy_icon'):  # If using text instead of icon
                self.copy_btn.configure(text="Copy")
            
            # Restore the original command
            if hasattr(self, 'original_command'):
                self.copy_btn.configure(command=self.original_command)
        except Exception as e:
            print(f"Reset button error: {e}")
        
        # Clear the after_id
        self.after_id = None

    def update_name_truncation(self):
        # Always set text content first to ensure it's displayed
        self.name_label.configure(text=self.full_name)
        
        # Make sure the widget is actually visible before trying truncation
        if not self.winfo_ismapped() or self.winfo_width() <= 1:
            # Schedule another attempt after initial layout
            self.after(200, self.update_name_truncation)
            return
        
        # Hard-code a simple truncation approach - show up to 30 chars + ellipsis
        if len(self.full_name) > 30:
            truncated = self.full_name[:30] + "..."
            self.name_label.configure(text=truncated)
        else:
            self.name_label.configure(text=self.full_name)

    def on_resize(self, event):
        self.after(50, self.update_name_truncation)  # Debounce the resize event
        # Also update frame width to match parent
        self.update_frame_width()

    def update_frame_width(self):
        """Update frame width to match parent container width"""
        if self.master and self.master.winfo_exists():
            parent_width = self.master.winfo_width()
            if parent_width > 10:  # Only adjust if parent has a meaningful width
                # Set width while preserving other dimensions
                self.configure(width=parent_width - 20)  # Account for padx

    def on_delete_hover_enter(self, event):
        """Change delete button style to red on hover"""
        self.delete_btn.configure(bootstyle="danger")
    
    def on_delete_hover_leave(self, event):
        """Restore delete button style when mouse leaves"""
        self.delete_btn.configure(bootstyle="primary")
    
    def confirm_delete(self):
        """Show a confirmation dialog before deleting the token"""
        issuer_name = self.issuer
        result = messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to delete the token for '{issuer_name}'?",
            icon=messagebox.WARNING
        )
        if result:
            # User confirmed deletion, proceed with original callback
            self.original_delete_callback() 