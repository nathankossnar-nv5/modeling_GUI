import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
import yaml
from pathlib import Path
import subprocess
import sys
import threading
import glob
import os
import shutil
from datetime import datetime
from PIL import Image
import random
import json
import signal
import tkinter as tk

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent
    
    return base_path / relative_path


def get_config_path(config_filename):
    """Get path for config files from the scripts directory (read-only source)"""
    scripts_dir = Path(r"W:\Tools\GUIs\Land_Cover_Script_Interface\scripts")
    return scripts_dir / config_filename


def get_config_writable_path(config_filename):
    """Get writable path for config files (user's AppData)"""
    return get_writable_path(config_filename)


def get_effective_config_path(config_filename):
    """Get the effective config path - always use scripts directory (W:\ drive)"""
    # Always use the W:\ scripts directory since it's always mapped
    return get_config_path(config_filename)


def get_writable_path(relative_path):
    """Get path for writable files (configs, history). 
    When running as exe, use user's AppData folder instead of temp _MEIPASS"""
    try:
        # Check if running as PyInstaller bundle
        _ = sys._MEIPASS
        # Use user's AppData folder for writable files
        app_data = Path(os.environ.get('APPDATA', os.path.expanduser('~')))
        writable_dir = app_data / 'ModelingGUI'
        writable_dir.mkdir(parents=True, exist_ok=True)
        return writable_dir / relative_path
    except Exception:
        # Running as script, use normal path
        base_path = Path(__file__).parent
        return base_path / relative_path


class SplashScreen(tk.Toplevel):
    """Splash screen to display while the GUI is loading"""
    def __init__(self, parent):
        super().__init__(parent)
        
        # Configure splash window
        self.overrideredirect(True)  # Remove window decorations
        
        # Set splash size
        splash_width = 400
        splash_height = 300
        
        # Center on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - splash_width) // 2
        y = (screen_height - splash_height) // 2
        self.geometry(f"{splash_width}x{splash_height}+{x}+{y}")
        
        # Create frame with border
        self.configure(bg='#1a1a1a')
        frame = tk.Frame(self, bg='#1a1a1a', highlightbackground='#3b8ed0', highlightthickness=2)
        frame.pack(expand=True, fill='both')
        
        # Load and display logo
        logo_path = get_resource_path("img") / "logo-nv5-white-no-tagline.png"
        if logo_path.exists():
            try:
                logo_image = Image.open(logo_path)
                # Resize logo for splash screen
                aspect_ratio = logo_image.width / logo_image.height
                new_height = 120
                new_width = int(new_height * aspect_ratio)
                logo_image = logo_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage for tkinter
                self.logo_photo = tk.PhotoImage(data=self._pil_to_png_data(logo_image))
                
                logo_label = tk.Label(frame, image=self.logo_photo, bg='#1a1a1a')
                logo_label.pack(pady=(50, 20))
            except Exception as e:
                print(f"Could not load splash logo: {e}")
        
        # Loading text
        loading_label = tk.Label(
            frame,
            text="Land Cover Script Interface",
            font=("Segoe UI", 16, "bold"),
            bg='#1a1a1a',
            fg='white'
        )
        loading_label.pack(pady=10)
        
        status_label = tk.Label(
            frame,
            text="Initializing...",
            font=("Segoe UI", 11),
            bg='#1a1a1a',
            fg='#a0a0a0'
        )
        status_label.pack(pady=5)
        
        # Ensure splash is visible
        self.update()
    
    def _pil_to_png_data(self, pil_image):
        """Convert PIL image to PNG data for PhotoImage"""
        import io
        import base64
        
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        png_data = buffer.getvalue()
        return base64.b64encode(png_data)
    
    def destroy_splash(self):
        """Destroy the splash screen"""
        self.destroy()


class App(TkinterDnD.Tk):   # IMPORTANT: use TkinterDnD root
    def __init__(self, show_splash=True):
        super().__init__()

        self.title("NV5 Script GUI")
        self.geometry("700x1160")
        
        # Hide window during initialization if splash is shown
        if show_splash:
            self.withdraw()
            self.splash = SplashScreen(self)
            # Initialize components after splash is displayed
            self.after(10, self._initialize_components)
        else:
            self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all GUI components"""

        # Font configuration (moved to initialization)
        if not hasattr(self, 'label_font'):
            self.label_font = ("Segoe UI", 14)
            self.entry_font = ("Segoe UI", 13)
            self.button_font = ("Segoe UI", 13, "bold")
            self.title_font = ("Segoe UI", 22, "bold")

        # CustomTkinter frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Title with logo
        title_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        title_frame.pack(pady=(15, 20))
        
        # Load and display logo
        logo_path = get_resource_path("img") / "logo-nv5-white-no-tagline.png"
        if logo_path.exists():
            try:
                logo_image = Image.open(logo_path)
                # Resize logo to fit title (height ~55 pixels)
                aspect_ratio = logo_image.width / logo_image.height
                new_height = 55
                new_width = int(new_height * aspect_ratio)
                logo_image = logo_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logo_ctk = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(new_width, new_height))
                
                logo_label = ctk.CTkLabel(title_frame, image=logo_ctk, text="")
                logo_label.pack(side="left", padx=(0, 10))
            except Exception as e:
                print(f"Could not load logo: {e}")
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="Land Cover Script Interface",
            font=self.title_font
        )
        title_label.pack(side="left")
        
        # Help button
        self.help_button = ctk.CTkButton(
            title_frame,
            text="ℹ",
            command=self.show_help_popup,
            width=35,
            height=35,
            font=("Segoe UI", 20),
            fg_color=["#9E9E9E", "#616161"],
            hover_color=["#BDBDBD", "#757575"],
            corner_radius=6,
            anchor="center"
        )
        self.help_button.pack(side="left", padx=(10, 0))

        # Script selector dropdown at top
        self.script_label = ctk.CTkLabel(self.main_frame, text="Select Script:", font=self.label_font)
        self.script_label.pack(pady=(10, 5))
        
        # Get all Python files from the scripts directory
        script_dir = Path(r"W:\Tools\GUIs\Land_Cover_Script_Interface\scripts")
        python_files = [f.name for f in script_dir.glob('*.py') if f.name != 'drag_drop.py']
        
        self.script_dropdown = ctk.CTkComboBox(
            self.main_frame,
            values=python_files if python_files else ["No scripts found"],
            width=400,
            height=40,
            command=self.on_script_selected,
            font=self.entry_font
        )
        if python_files:
            self.script_dropdown.set(python_files[0])
        self.script_dropdown.pack(pady=5)

        # Runtime Mode Selector - Pill Toggle
        self.mode_label = ctk.CTkLabel(self.main_frame, text="Python Runtime:", font=self.label_font)
        self.mode_label.pack(pady=(10, 5))
        
        # Create horizontal frame for toggle and conda dropdown
        self.runtime_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.runtime_frame.pack(pady=5)
        
        self.runtime_mode = ctk.CTkSegmentedButton(
            self.runtime_frame,
            values=["Bundled Python", "Conda Environment"],
            width=300,
            height=40,
            font=self.entry_font,
            command=self._on_runtime_mode_change
        )
        self.runtime_mode.set("Bundled Python")
        self.runtime_mode.pack(side="left", padx=(0, 10))

        # Get conda environments
        conda_envs = self.get_conda_environments()
        
        # Conda environment selector (initially hidden)
        self.env_dropdown = ctk.CTkComboBox(
            self.runtime_frame,
            values=conda_envs if conda_envs else ["No conda environments found"],
            width=300,
            height=40,
            font=self.entry_font
        )
        # Set default placeholder text
        self.env_dropdown.set("Select Conda Environment")
        # Don't pack initially - will be shown when Conda mode is selected

        # View documentation button
        self.doc_button = ctk.CTkButton(
            self.main_frame,
            text="📄 View Documentation",
            command=self.show_documentation_window,
            width=200,
            height=35,
            font=self.entry_font
        )
        self.doc_button.pack(pady=10)

        # Scrollable frame for dynamic fields
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.main_frame,
            width=600,
            height=300
        )
        self.scroll_frame.pack(pady=10, fill="both", expand=True)

        # Dictionary to store field widgets
        self.field_entries = {}
        
        # Current config file (determined by script selection)
        self.current_config_file = None
        
        # Script execution state
        self.script_is_running = False
        
        # History file path
        self.history_file = get_writable_path("run_history.json")
        self._ensure_history_file()

        # Button frame for all buttons
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(pady=10)

        # Run script button
        self.wait_button = ctk.CTkButton(
            button_frame,
            text=f"Run {self.script_dropdown.get()}",
            command=self.run_wait_script,
            width=200,
            height=40,
            font=self.button_font
        )
        self.wait_button.pack(side="left", padx=5)

        # Stop button
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹ Stop",
            command=self.stop_script,
            width=100,
            height=40,
            font=self.button_font,
            fg_color=["#D32F2F", "#B71C1C"],  # Red color
            hover_color=["#F44336", "#D32F2F"]
        )
        # Don't pack initially - will show when script runs

        # Clear button
        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear",
            command=self.clear_fields,
            width=100,
            height=40,
            font=self.button_font
        )
        self.clear_button.pack(side="left", padx=5)
        
        # History button
        self.history_button = ctk.CTkButton(
            button_frame,
            text="📜 History",
            command=self.show_history_browser,
            width=120,
            height=40,
            font=self.button_font,
            fg_color=["#9C27B0", "#7B1FA2"],  # Purple color
            hover_color=["#BA68C8", "#9C27B0"]
        )
        self.history_button.pack(side="left", padx=5)

        # Output section label
        self.output_label = ctk.CTkLabel(self.main_frame, text="Script Output:", font=self.label_font)
        self.output_label.pack(pady=(10, 5))
        
        self.output_textbox = ctk.CTkTextbox(
            self.main_frame,
            width=400,
            height=150,
            font=self.entry_font
        )
        self.output_textbox.pack(pady=(5, 5))
        
        # Expand button below output box
        self.expand_output_button = ctk.CTkButton(
            self.main_frame,
            text="🔍 Expand Output",
            command=self.show_expanded_output,
            width=150,
            height=30,
            font=("Segoe UI", 10),
            fg_color=["#9E9E9E", "#616161"],  # Gray color
            hover_color=["#BDBDBD", "#757575"]  # Lighter gray hover
        )
        self.expand_output_button.pack(pady=(5, 20))

        # Hover area for Pet Tax button at bottom (invisible frame)
        self.random_button_hover_area = ctk.CTkFrame(
            self.main_frame,
            width=140,
            height=35,
            fg_color="transparent"
        )
        self.random_button_hover_area.pack(pady=(10, 10))
        
        # Random image button (hidden until hover)
        self.random_img_button = ctk.CTkButton(
            self.random_button_hover_area,
            text="Pet Tax!",
            command=self.open_random_image,
            width=140,
            height=35,
            font=("Segoe UI", 11, "bold"),
            fg_color=["#F9F9FA", "#2B2B2B"],  # Match background
            text_color=["#F9F9FA", "#2B2B2B"],  # Match background
            border_width=0
        )
        self.random_img_button.place(relx=0.5, rely=0.5, anchor="center")  # Always visible
        
        # Bind hover events to both hover area and button
        self.random_button_hover_area.bind("<Enter>", self._show_random_button)
        self.random_button_hover_area.bind("<Leave>", self._hide_random_button)
        self.random_img_button.bind("<Enter>", self._show_random_button)
        self.random_img_button.bind("<Leave>", self._hide_random_button)

        # Load initial config based on first script (after all widgets created)
        if python_files:
            self.on_script_selected(python_files[0])
        
        # Check if bundled Python is available when running as exe
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            python_exe = exe_dir / 'python.exe'
            if not python_exe.exists():
                # Running as exe but no bundled Python found - likely onefile mode
                print("WARNING: Bundled Python not found. 'Bundled Python' mode may not work.")
                print(f"Expected python.exe at: {python_exe}")
                print("If this is a onefile build, please rebuild using onedir mode for bundled Python support.")
        
        # If splash was shown, close it and show main window
        if hasattr(self, 'splash'):
            self.after(100, self._finish_initialization)
    
    def _finish_initialization(self):
        """Finish initialization by closing splash and showing main window"""
        if hasattr(self, 'splash'):
            self.splash.destroy_splash()
            del self.splash
        self.deiconify()  # Show the main window

    def _on_runtime_mode_change(self, choice):
        """Handle runtime mode change"""
        if choice == "Conda Environment":
            # Show conda environment selector next to toggle
            self.env_dropdown.pack(side="left", padx=(0, 0))
        else:
            # Hide conda environment selector
            self.env_dropdown.pack_forget()
    
    def _get_bundled_python_executable(self):
        """Get the correct Python executable for bundled mode (Python 3.x only)"""
        # Check if running as PyInstaller bundle
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            # First priority: Look for python.exe in the same directory as the exe (onedir mode)
            exe_dir = Path(sys.executable).parent
            python_exe = exe_dir / 'python.exe'
            
            self.after(0, self._update_output, f"Debug: Looking for bundled Python at: {python_exe}\n")
            
            if python_exe.exists():
                self.after(0, self._update_output, f"Debug: Found bundled Python!\n")
                return str(python_exe)
            else:
                self.after(0, self._update_output, f"Debug: Bundled Python not found. Exe directory: {exe_dir}\n")
                # List files in exe directory for debugging
                try:
                    files = list(exe_dir.iterdir())
                    self.after(0, self._update_output, f"Debug: Files in exe dir: {', '.join(f.name for f in files[:10])}\n")
                except:
                    pass
            
            # Second priority: Try to find python.exe in the extracted _MEIPASS directory
            if hasattr(sys, '_MEIPASS'):
                # Look for python executable in common locations within bundle
                possible_paths = [
                    Path(sys._MEIPASS) / 'python.exe',
                    Path(sys._MEIPASS) / 'Scripts' / 'python.exe',
                ]
                
                for python_path in possible_paths:
                    if python_path.exists() and self._is_python3(str(python_path)):
                        return str(python_path)
            
            # If no bundled python.exe found, look for system Python 3.x
            # Try common Python installation paths
            import winreg
            
            # Collect all Python installations with version info
            python_candidates = []
            
            try:
                # Try to find Python from registry (HKEY_LOCAL_MACHINE)
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Python\PythonCore")
                for i in range(20):  # Check up to 20 versions
                    try:
                        version_key = winreg.EnumKey(key, i)
                        # Skip Python 2.x versions
                        if version_key.startswith('2.'):
                            continue
                        
                        version_path = winreg.OpenKey(key, version_key + r"\InstallPath")
                        install_path = winreg.QueryValue(version_path, None)
                        python_exe = Path(install_path) / "python.exe"
                        
                        if python_exe.exists() and self._is_python3(str(python_exe)):
                            # Parse version for sorting (prefer higher versions)
                            try:
                                version_parts = version_key.split('.')
                                version_tuple = tuple(int(p) for p in version_parts)
                                python_candidates.append((version_tuple, str(python_exe)))
                            except:
                                python_candidates.append(((3, 0), str(python_exe)))
                        
                        winreg.CloseKey(version_path)
                    except WindowsError:
                        continue
                winreg.CloseKey(key)
            except WindowsError:
                pass
            
            # Also check HKEY_CURRENT_USER
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Python\PythonCore")
                for i in range(20):
                    try:
                        version_key = winreg.EnumKey(key, i)
                        if version_key.startswith('2.'):
                            continue
                        
                        version_path = winreg.OpenKey(key, version_key + r"\InstallPath")
                        install_path = winreg.QueryValue(version_path, None)
                        python_exe = Path(install_path) / "python.exe"
                        
                        if python_exe.exists() and self._is_python3(str(python_exe)):
                            try:
                                version_parts = version_key.split('.')
                                version_tuple = tuple(int(p) for p in version_parts)
                                python_candidates.append((version_tuple, str(python_exe)))
                            except:
                                python_candidates.append(((3, 0), str(python_exe)))
                        
                        winreg.CloseKey(version_path)
                    except WindowsError:
                        continue
                winreg.CloseKey(key)
            except WindowsError:
                pass
            
            # Return the highest version Python 3.x found
            if python_candidates:
                python_candidates.sort(reverse=True)  # Sort by version, highest first
                self.after(0, self._update_output, f"Debug: Found system Python: {python_candidates[0][1]}\n")
                return python_candidates[0][1]
            
            # Last resort: try 'python3' or 'python' command
            for cmd in ['python3', 'python']:
                if self._is_python3(cmd):
                    self.after(0, self._update_output, f"Debug: Using command: {cmd}\n")
                    return cmd
            
            # If all else fails, show error
            error_msg = (
                "ERROR: Python interpreter not found!\n\n"
                "For 'Bundled Python' mode to work, you need to:\n"
                "1. Rebuild the exe using 'onedir' mode (see drag_drop.spec)\n"
                "2. Distribute the entire folder (not just the .exe)\n\n"
                "OR switch to 'Conda Environment' mode and select an environment.\n"
            )
            self.after(0, self._update_output, error_msg)
            raise FileNotFoundError("No Python interpreter found for bundled mode. Please rebuild with onedir mode or use Conda Environment mode.")
        else:
            # Running as script, use current Python
            return sys.executable
    
    def _is_python3(self, python_path):
        """Check if the given python executable is Python 3.x"""
        try:
            result = subprocess.run(
                [python_path, '-c', 'import sys; print(sys.version_info[0])'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return version == '3'
        except:
            pass
        return False
    
    def get_conda_environments(self):
        """Get list of available conda environments"""
        try:
            # Try different conda commands for Windows
            conda_commands = ['conda', 'conda.exe']
            
            for conda_cmd in conda_commands:
                try:
                    result = subprocess.run(
                        [conda_cmd, 'env', 'list'],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=True  # Use shell on Windows
                    )
                    
                    if result.returncode == 0:
                        # Store the working conda command for later use
                        self.conda_executable = conda_cmd
                        
                        # Try to find the full path to conda
                        try:
                            which_result = subprocess.run(
                                ['where', conda_cmd] if sys.platform == 'win32' else ['which', conda_cmd],
                                capture_output=True,
                                text=True,
                                shell=True
                            )
                            if which_result.returncode == 0:
                                # Get first line (primary conda path)
                                conda_path = which_result.stdout.strip().split('\n')[0]
                                if conda_path:
                                    self.conda_full_path = conda_path
                        except:
                            self.conda_full_path = None
                        
                        envs = []
                        for line in result.stdout.split('\n'):
                            # Skip comments and empty lines
                            if line.strip() and not line.startswith('#'):
                                # Extract environment name (first word)
                                parts = line.split()
                                if parts:
                                    env_name = parts[0]
                                    if env_name and env_name != 'conda':
                                        envs.append(env_name)
                        if envs:
                            return envs
                except FileNotFoundError:
                    continue
                    
        except Exception as e:
            print(f"Error getting conda environments: {e}")
        
        # If we get here, conda wasn't found
        self.conda_executable = None
        self.conda_full_path = None
        return []

    def open_random_image(self):
        """Open a random image from the pet_tax folder"""
        img_dir = Path(r"W:\Tools\GUIs\Land_Cover_Script_Interface\pet_tax")
        if not img_dir.exists():
            print("pet_tax folder not found")
            return
        
        # Get all image files
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.tiff']
        image_files = []
        for ext in image_extensions:
            image_files.extend(img_dir.glob(ext))
            image_files.extend(img_dir.glob(ext.upper()))
        
        if not image_files:
            print("No images found in img folder")
            return
        
        # Select random image
        random_image = random.choice(image_files)
        
        # Open in default image viewer
        try:
            os.startfile(str(random_image))
        except Exception as e:
            print(f"Error opening image: {e}")
    
    def _show_random_button(self, event):
        """Show the random image button on hover"""
        self.random_img_button.configure(
            fg_color=["#4CAF50", "#388E3C"],  # Green
            text_color=["white", "white"]
        )
    
    def _hide_random_button(self, event):
        """Hide the random image button when not hovering"""
        self.random_img_button.configure(
            fg_color=["#F9F9FA", "#2B2B2B"],  # Match background
            text_color=["#F9F9FA", "#2B2B2B"]  # Match background
        )
    
    def get_script_docstring(self, script_name):
        """Extract the module-level docstring from a Python script"""
        script_dir = Path(r"W:\Tools\GUIs\Land_Cover_Script_Interface\scripts")
        script_path = script_dir / script_name
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to extract docstring using ast module for reliable parsing
            import ast
            try:
                tree = ast.parse(content)
                docstring = ast.get_docstring(tree)
                if docstring:
                    return docstring.strip()
            except:
                pass
            
            return "No documentation available for this script."
        except Exception as e:
            return f"Error reading script documentation: {e}"

    def show_documentation_window(self):
        """Display script documentation in an overlay within the main window"""
        script_name = self.script_dropdown.get()
        if script_name == "No scripts found":
            return
        
        docstring = self.get_script_docstring(script_name)
        
        # Create overlay frame (semi-transparent background)
        self.doc_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.doc_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.doc_overlay.bind("<Button-1>", lambda e: self.close_documentation())
        
        # Create documentation frame (centered)
        doc_frame = ctk.CTkFrame(
            self.doc_overlay,
            width=600,
            height=450,
            corner_radius=10
        )
        doc_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on doc_frame from closing the overlay
        doc_frame.bind("<Button-1>", lambda e: "break")
        
        # Add title label
        title_label = ctk.CTkLabel(
            doc_frame,
            text=f"Documentation for {script_name}",
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=15)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add textbox with docstring
        doc_textbox = ctk.CTkTextbox(
            doc_frame,
            width=560,
            height=330,
            font=("Segoe UI", 12)
        )
        doc_textbox.pack(pady=10, padx=20)
        doc_textbox.insert("1.0", docstring)
        doc_textbox.configure(state="disabled")  # Make read-only
        doc_textbox.bind("<Button-1>", lambda e: "break")
        
        # Add close button
        close_button = ctk.CTkButton(
            doc_frame,
            text="Close",
            command=self.close_documentation,
            width=100,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        close_button.pack(pady=10)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def close_documentation(self):
        """Close the documentation overlay"""
        if hasattr(self, 'doc_overlay'):
            self.doc_overlay.destroy()
            del self.doc_overlay
    
    def show_env_selection_popup(self):
        """Display conda environment selection popup"""
        # Create overlay frame (semi-transparent background)
        self.env_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.env_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.env_overlay.bind("<Button-1>", lambda e: self.close_env_selection_popup())
        
        # Create environment selection frame (centered)
        env_frame = ctk.CTkFrame(
            self.env_overlay,
            width=500,
            height=300,
            corner_radius=10
        )
        env_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on env_frame from closing the overlay
        env_frame.bind("<Button-1>", lambda e: "break")
        
        # Add title label
        title_label = ctk.CTkLabel(
            env_frame,
            text="⚠️ Conda Environment Required",
            font=("Segoe UI", 16, "bold"),
            text_color=("#E57373", "#EF5350")  # Red color for warning
        )
        title_label.pack(pady=20)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add instruction label
        instruction_label = ctk.CTkLabel(
            env_frame,
            text="Please select a Conda environment to run the script:",
            font=("Segoe UI", 12)
        )
        instruction_label.pack(pady=10)
        instruction_label.bind("<Button-1>", lambda e: "break")
        
        # Get conda environments
        conda_envs = self.get_conda_environments()
        
        # Add environment dropdown
        popup_env_dropdown = ctk.CTkComboBox(
            env_frame,
            values=conda_envs if conda_envs else ["No conda environments found"],
            width=400,
            height=40,
            font=("Segoe UI", 11)
        )
        popup_env_dropdown.set("Select Conda Environment")
        popup_env_dropdown.pack(pady=15, padx=20)
        popup_env_dropdown.bind("<Button-1>", lambda e: "break")
        
        # Button frame
        button_frame = ctk.CTkFrame(env_frame, fg_color="transparent")
        button_frame.pack(pady=20)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Add confirm button
        def confirm_selection():
            selected = popup_env_dropdown.get()
            if selected and selected != "Select Conda Environment" and selected != "No conda environments found":
                # Update main dropdown
                self.env_dropdown.set(selected)
                self.close_env_selection_popup()
                
                # Check for null/empty parameters before running
                null_params = []
                for key, entry in self.field_entries.items():
                    value = entry.get().strip()
                    if not value:
                        null_params.append(key)
                
                if null_params:
                    # Show popup warning about null parameters
                    self.show_null_params_warning(null_params)
                else:
                    # All parameters are filled, proceed with run
                    self._proceed_with_run()
            else:
                # Flash the dropdown to indicate selection is required
                popup_env_dropdown.configure(border_color="red", border_width=2)
                self.after(1000, lambda: popup_env_dropdown.configure(border_color=("#979DA2", "#565B5E"), border_width=2))
        
        confirm_button = ctk.CTkButton(
            button_frame,
            text="Confirm and Run",
            command=confirm_selection,
            width=150,
            height=35,
            font=("Segoe UI", 11, "bold"),
            fg_color=("#4CAF50", "#388E3C")  # Green color
        )
        confirm_button.pack(side="left", padx=5)
        confirm_button.bind("<Button-1>", lambda e: "break")
        
        # Add cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.close_env_selection_popup,
            width=100,
            height=35,
            font=("Segoe UI", 11, "bold"),
            fg_color=("#757575", "#616161")  # Gray color
        )
        cancel_button.pack(side="left", padx=5)
        cancel_button.bind("<Button-1>", lambda e: "break")
    
    def close_env_selection_popup(self):
        """Close the environment selection overlay"""
        if hasattr(self, 'env_overlay'):
            self.env_overlay.destroy()
            del self.env_overlay
    
    def show_null_params_warning(self, null_params):
        """Display warning popup for null/empty parameters"""
        # Create overlay frame (semi-transparent background)
        self.params_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.params_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.params_overlay.bind("<Button-1>", lambda e: self.close_params_warning())
        
        # Create warning frame (centered, taller for scrolling if needed)
        params_frame = ctk.CTkFrame(
            self.params_overlay,
            width=550,
            height=min(500, 200 + len(null_params) * 35),  # Dynamic height based on number of params
            corner_radius=10
        )
        params_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on params_frame from closing the overlay
        params_frame.bind("<Button-1>", lambda e: "break")
        
        # Add title label
        title_label = ctk.CTkLabel(
            params_frame,
            text="⚠️ Missing Parameters",
            font=("Segoe UI", 16, "bold"),
            text_color=("#E57373", "#EF5350")  # Red color for warning
        )
        title_label.pack(pady=20)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add instruction label
        instruction_label = ctk.CTkLabel(
            params_frame,
            text="The following parameters are empty and need values:",
            font=("Segoe UI", 12)
        )
        instruction_label.pack(pady=(5, 10))
        instruction_label.bind("<Button-1>", lambda e: "break")
        
        # Create scrollable frame for parameter list
        scroll_frame = ctk.CTkScrollableFrame(
            params_frame,
            width=480,
            height=min(250, len(null_params) * 35 + 20),
            fg_color=("gray90", "gray17")
        )
        scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)
        scroll_frame.bind("<Button-1>", lambda e: "break")
        
        # List each null parameter
        for param in null_params:
            param_label = ctk.CTkLabel(
                scroll_frame,
                text=f"• {param.replace('_', ' ').title()}",
                font=("Segoe UI", 11),
                anchor="w"
            )
            param_label.pack(pady=3, padx=10, anchor="w")
            param_label.bind("<Button-1>", lambda e: "break")
        
        # Button frame
        button_frame = ctk.CTkFrame(params_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Add "Fill Parameters" button
        fill_button = ctk.CTkButton(
            button_frame,
            text="Fill Parameters",
            command=self.close_params_warning,
            width=150,
            height=35,
            font=("Segoe UI", 11, "bold"),
            fg_color=("#1976D2", "#1565C0")  # Blue color
        )
        fill_button.pack(side="left", padx=5)
        fill_button.bind("<Button-1>", lambda e: "break")
        
        # Add "Run Anyway" button (in case user wants to proceed with nulls)
        def run_anyway():
            self.close_params_warning()
            self._proceed_with_run()
        
        run_anyway_button = ctk.CTkButton(
            button_frame,
            text="Run Anyway",
            command=run_anyway,
            width=120,
            height=35,
            font=("Segoe UI", 11, "bold"),
            fg_color=("#FF9800", "#F57C00")  # Orange color for caution
        )
        run_anyway_button.pack(side="left", padx=5)
        run_anyway_button.bind("<Button-1>", lambda e: "break")
    
    def close_params_warning(self):
        """Close the null parameters warning overlay"""
        if hasattr(self, 'params_overlay'):
            self.params_overlay.destroy()
            del self.params_overlay
    
    def show_help_popup(self):
        """Show help popup explaining the app's functionality"""
        # Create overlay frame (like history browser)
        self.help_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.help_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.help_overlay.bind("<Button-1>", lambda e: self._close_help_popup())
        
        # Create help frame (centered)
        help_frame = ctk.CTkFrame(
            self.help_overlay,
            width=650,
            height=750,
            corner_radius=10
        )
        help_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on help_frame from closing the overlay
        help_frame.bind("<Button-1>", lambda e: "break")
        
        # Title
        title_label = ctk.CTkLabel(
            help_frame,
            text="❓ How to Use This Application",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=15)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Help content
        help_text = """Welcome to the Land Cover Script Interface!

This application provides a user-friendly way to run geospatial land cover analysis scripts with custom parameters.

MAIN FEATURES:

1. Script Selection
   • Choose from available Python scripts in the dropdown menu
   • Upload .py/.yml to W:\\Tools\\GUIs\\Land_Cover_Script_Interface\\scripts

2. Conda Environment
   • Select the Python environment to run your script
   • Lists all conda envs installed on your system

3. Dynamic Parameters
   • The interface automatically loads parameters for the selected script
   • Parameters are defined in YAML config files with comments for descriptions
   • Drag and drop files/folders into path fields for convenience

4. Configuration Management
   • Load previously saved configurations

5. Documentation
   • Click "View Documentation" to see scripts docstrings in an overlay

6. Run History
   • Access your previous script runs
   • Review past configurations and results
   • Reload settings from history
   • All history data is stored in run_history.json in your AppData folder

DRAG & DROP:

You can drag and drop files or folders from Windows Explorer directly into any path field. This makes it easy to specify input/output locations without typing long paths.
"""
        
        # SOP content for adding new scripts
        sop_text = """Adding New Scripts

=================================================================
OVERVIEW
=================================================================
This tool automatically discovers Python scripts from the network drive and generates UI fields based on YAML configuration files.

Key Concepts:
• Scripts Location: W:\\Tools\\GUIs\\Land_Cover_Script_Interface\\scripts
• Auto-Discovery: Scripts detected via *.py file scanning
• Config-Driven UI: Parameter fields generated from *_config.yml files
• Conda Integration: Scripts run in user-selected conda environments

=================================================================
QUICK STEPS
=================================================================

1. PREPARE YOUR PYTHON SCRIPT
   • Add docstring explaining purpose (shown in View Documentation)
   • Accept command-line arguments using argparse
   • Print progress updates to stdout (appears in GUI output)
   • Handle errors gracefully with clear messages

   Example:
   ``````````````````````
   import argparse
   
   parser = argparse.ArgumentParser()
   parser.add_argument('--input_folder', required=True)
   parser.add_argument('--output_folder', required=True)
   args = parser.parse_args()
   ```````````````````````
2. CREATE CONFIG YAML FILE
   • Name it: [script_name]_config.yml
   • Example: my_script.py → my_script_config.yml
   • Add parameters with comments (comments become placeholder text)
   
   Example config file:
   ```````````````````````
   # Drag and drop input folder here
   input_folder: null
   
   # Path to trained model file
   model_path: null
   
   # Output directory for results
   output_folder: null
   
   # Confidence threshold (0.0 to 1.0)
   threshold: 0.8
    ```````````````````````
3. UPLOAD FILES
   • Copy both .py and .yml files to:
     W:\\Tools\\GUIs\\Land_Cover_Script_Interface\\scripts\\
   • Files must be in the same directory

4. TEST IN GUI
   • Restart GUI (or just reselect script)
   • Your script appears in dropdown automatically
   • Parameter fields generate from your YAML file
   • Comments from YAML show as placeholder text
   • Test drag-and-drop on path fields
   • Click "View Documentation" to see your docstring
   • Select appropriate conda environment
   • Run and verify output

=================================================================
IMPORTANT DETAILS
=================================================================

NAMING REQUIREMENTS:
• Script: my_script.py
• Config: my_script_config.yml (exact name match required)

COMMAND-LINE MAPPING:
Your YAML parameters are passed as command-line arguments:
• input_folder: null → --input_folder "path/to/folder"
• threshold: 0.8 → --threshold 0.8
• use_gpu: true → --use_gpu (flag passed)
• use_gpu: false → (flag omitted)

PLACEHOLDER TEXT:
Comments above YAML parameters become field placeholder text:
# This text appears in the GUI field
input_folder: null


=================================================================
COMPLETE EXAMPLE
=================================================================

File: classify_landcover.py
---
\"\"\"Land Cover Classification Script

Classifies satellite imagery using a trained model.

INPUTS:
- imagery_folder: GeoTIFF images
- model_file: Trained PyTorch model (.pth)
- output_folder: Results directory

OUTPUTS:
- Classified raster files
- Confidence maps
\"\"\"

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--imagery_folder', required=True)
parser.add_argument('--model_file', required=True)
parser.add_argument('--output_folder', required=True)
parser.add_argument('--batch_size', type=int, default=16)
parser.add_argument('--use_gpu', action='store_true')
args = parser.parse_args()

print("Starting classification...")
# Your code here
print("Complete!")
---

File: classify_landcover_config.yml
---
# Drag and drop folder with GeoTIFF imagery
imagery_folder: null

# Path to trained PyTorch model file (.pth)
model_file: null

# Output directory for classification results
output_folder: null

# Number of images to process simultaneously
batch_size: 16

# Enable GPU acceleration for faster processing
use_gpu: true
---

Both files uploaded to W:\\Tools\\GUIs\\Land_Cover_Script_Interface\\scripts

Result: Script appears in dropdown with 5 auto-generated input fields!
"""
        
        help_content = ctk.CTkTextbox(
            help_frame,
            width=610,
            height=620,
            font=("Segoe UI", 12),
            wrap="word"
        )
        help_content.pack(pady=10, padx=20, fill="both", expand=True)
        help_content.insert("1.0", help_text)
        help_content.configure(state="disabled")  # Make read-only
        help_content.bind("<Button-1>", lambda e: "break")
        
        # Store references for toggling
        self.help_textbox = help_content
        self.help_text_content = help_text
        self.sop_text_content = sop_text
        self.showing_help = True
        
        # Button frame for Close and Toggle SOP
        button_frame = ctk.CTkFrame(help_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Toggle SOP button
        self.toggle_sop_button = ctk.CTkButton(
            button_frame,
            text="How to add new scripts",
            command=self.toggle_sop_view,
            width=160,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=["#2E7D32", "#1B5E20"],  # Green color
            hover_color=["#4CAF50", "#2E7D32"]
        )
        self.toggle_sop_button.pack(side="left", padx=5)
        self.toggle_sop_button.bind("<Button-1>", lambda e: "break")
        
        # Close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_help_popup,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def toggle_sop_view(self):
        """Toggle between Help and SOP content in the help window"""
        if self.showing_help:
            # Switch to SOP
            self.help_textbox.configure(state="normal")
            self.help_textbox.delete("1.0", "end")
            self.help_textbox.insert("1.0", self.sop_text_content)
            self.help_textbox.configure(state="disabled")
            self.toggle_sop_button.configure(text="← Back to Help")
            self.showing_help = False
        else:
            # Switch back to Help
            self.help_textbox.configure(state="normal")
            self.help_textbox.delete("1.0", "end")
            self.help_textbox.insert("1.0", self.help_text_content)
            self.help_textbox.configure(state="disabled")
            self.toggle_sop_button.configure(text="📋 View SOP")
            self.showing_help = True
    
    def _close_help_popup(self):
        """Close the help popup overlay"""
        if hasattr(self, 'help_overlay'):
            self.help_overlay.destroy()
            del self.help_overlay
    
    def show_expanded_output(self):
        """Show output in an expanded pop-out window"""
        output_content = self.output_textbox.get("1.0", "end-1c")
        if not output_content.strip():
            output_content = "(No output yet)"
        
        # Create separate window instead of overlay
        output_window = ctk.CTkToplevel(self)
        output_window.title("Script Output (Expanded)")
        output_window.geometry("800x600")
        
        # Position window to the right of main window
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        
        # Place popup to the right of main window with 20px gap
        new_x = main_x + main_width + 20
        new_y = main_y
        output_window.geometry(f"800x600+{new_x}+{new_y}")
        
        # Store reference to window so we can detect when it's closed
        self.expanded_output_window = output_window
        output_window.protocol("WM_DELETE_WINDOW", self._on_expanded_output_close)
        
        # Add title label
        title_label = ctk.CTkLabel(
            output_window,
            text="Script Output (Expanded)",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=15)
        
        # Add textbox with output
        output_textbox = ctk.CTkTextbox(
            output_window,
            width=760,
            height=480,
            font=("Consolas", 11)
        )
        output_textbox.pack(pady=10, padx=20)
        output_textbox.insert("1.0", output_content)
        
        # Store reference to expanded textbox for live updates
        self.expanded_output_textbox = output_textbox
        
        # Store output for copying
        self.current_expanded_output = output_content
        
        # Button frame
        button_frame = ctk.CTkFrame(output_window, fg_color="transparent")
        button_frame.pack(pady=15)
        
        # Add copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy Output",
            command=self._copy_expanded_output,
            width=150,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        copy_button.pack(side="left", padx=5)
        
        # Add close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._on_expanded_output_close,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        close_button.pack(side="left", padx=5)
    
    def _on_expanded_output_close(self):
        """Handle closing of expanded output window"""
        if hasattr(self, 'expanded_output_window'):
            self.expanded_output_window.destroy()
            del self.expanded_output_window
        if hasattr(self, 'expanded_output_textbox'):
            del self.expanded_output_textbox
    
    def _copy_expanded_output(self):
        """Copy the expanded output to clipboard"""
        if hasattr(self, 'current_expanded_output'):
            self.clipboard_clear()
            self.clipboard_append(self.current_expanded_output)
            self.update()
            print("Output copied to clipboard")

    def get_config_filename(self, script_name):
        """Determine config filename from script name"""
        # Remove .py extension and add _config.yml
        base_name = script_name.rsplit('.py', 1)[0]
        config_filename = f"{base_name}_config.yml"
        return config_filename

    def on_script_selected(self, script_name):
        """Handle script selection - load corresponding config and update button"""
        # Update button text if button exists
        if hasattr(self, 'wait_button'):
            self.wait_button.configure(text=f"Run {script_name}")
        
        # Determine config file
        config_filename = self.get_config_filename(script_name)
        config_path = get_config_path(config_filename)
        
        # Create config file if it doesn't exist
        if not config_path.exists():
            # Create default config
            default_data = {'folder': None, 'model_path': None, 'out_dir': None}
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                yaml.dump(default_data, f, default_flow_style=False)
        
        # Store current config file
        self.current_config_file = config_filename
        
        # Load the config
        self.load_config_and_rebuild(config_filename)

    def extract_yaml_descriptions(self, config_filename):
        """Extract parameter descriptions from YAML comments"""
        config_path = get_config_path(config_filename)
        descriptions = {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_comment = ""
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Collect comments
                if stripped.startswith('#'):
                    comment = stripped[1:].strip()
                    current_comment = comment
                # When we hit a parameter line, associate the comment with it
                elif ':' in stripped and not stripped.startswith('#'):
                    param_name = stripped.split(':')[0].strip()
                    if current_comment and param_name:
                        descriptions[param_name] = current_comment
                    current_comment = ""  # Reset for next parameter
        except Exception as e:
            print(f"Error extracting descriptions: {e}")
        
        return descriptions
    
    def load_config_and_rebuild(self, config_filename):
        """Load config file and rebuild the drag/drop fields dynamically"""
        # Use effective path (writable if exists, otherwise scripts dir)
        config_path = get_effective_config_path(config_filename)
        
        # Clear existing fields
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.field_entries.clear()
        
        # Extract parameter descriptions from YAML comments (always from scripts dir)
        descriptions = self.extract_yaml_descriptions(config_filename)
        
        # Load config values from effective path
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config: {e}")
            config_data = {}
        
        # Create fields dynamically based on config keys
        for key, value in config_data.items():
            # Create label
            label = ctk.CTkLabel(self.scroll_frame, text=f"{key.replace('_', ' ').title()}:", font=self.label_font)
            label.pack(pady=(10, 5))
            
            # Use description as placeholder text if available, otherwise use default
            placeholder_text = descriptions.get(key, f"Drag {key} here")
            
            # Create entry
            entry = ctk.CTkEntry(
                self.scroll_frame,
                placeholder_text=placeholder_text,
                height=40,
                font=self.entry_font
            )
            entry.pack(pady=5, fill="x", padx=10)
            
            # Set existing value if any
            if value:
                entry.insert(0, str(value))
            
            # Enable drag and drop
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind("<<Drop>>", lambda e, k=key: self.drop(e, k))
            
            # Store reference
            self.field_entries[key] = entry

    def drop(self, event, field_name):
        file_path = event.data.strip("{}")  # handles spaces in paths
        
        if field_name in self.field_entries:
            entry = self.field_entries[field_name]
            entry.delete(0, "end")
            entry.insert(0, file_path)
            print(f"{field_name}:", file_path)
    
    def clear_fields(self):
        """Clear all entry fields and reload descriptions from yaml"""
        # Extract descriptions from the current config file
        descriptions = {}
        if self.current_config_file:
            descriptions = self.extract_yaml_descriptions(self.current_config_file)
        
        # Clear fields and restore placeholder text with descriptions
        for key, entry in self.field_entries.items():
            entry.delete(0, "end")
            # Update placeholder text with description if available
            placeholder_text = descriptions.get(key, f"Drag {key} here")
            entry.configure(placeholder_text=placeholder_text)
        
        print("All fields cleared")

    def save_config(self):
        # Get values from all dynamic entry widgets
        config_data = {}
        for key, entry in self.field_entries.items():
            value = entry.get()
            config_data[key] = value if value else None
        
        config_filename = self.current_config_file
        if not config_filename:
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", "Error: No config file selected\n")
            return
            
        # Save to writable location (not the scripts directory)
        config_path = get_config_writable_path(config_filename)
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            print(f"Configuration saved to {config_path}")
            print(f"Saved values: {config_data}")
            
            # Read back and display the saved config
            with open(config_path, 'r') as f:
                config_contents = f.read()
            
            # Display in output textbox
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", "Configuration saved successfully!\n\n")
            self.output_textbox.insert("end", f"Contents of {config_filename}:\n")
            self.output_textbox.insert("end", "-" * 40 + "\n")
            self.output_textbox.insert("end", config_contents)
            self.output_textbox.insert("end", "-" * 40 + "\n")
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", f"Error saving configuration: {e}\n")
    
    def _check_values_match(self):
        """Check if GUI values match the saved yml values"""
        if not self.current_config_file:
            return True
        
        config_path = get_effective_config_path(self.current_config_file)
        try:
            with open(config_path, 'r') as f:
                saved_values = yaml.safe_load(f) or {}
        except:
            return True  # If can't read file, allow to proceed
        
        # Get current GUI values
        gui_values = {}
        for key, entry in self.field_entries.items():
            value = entry.get()
            gui_values[key] = value if value else None
        
        # Compare values
        return gui_values == saved_values
    
    def _show_mismatch_warning(self):
        """Show warning popup when GUI values don't match yml values"""
        # Get saved and GUI values
        config_path = get_effective_config_path(self.current_config_file)
        with open(config_path, 'r') as f:
            saved_values = yaml.safe_load(f) or {}
        
        gui_values = {}
        for key, entry in self.field_entries.items():
            value = entry.get()
            gui_values[key] = value if value else None
        
        # Build comparison message with prominent confirmation text
        message = "⚠️ CONFIGURATION MISMATCH DETECTED ⚠️\n\n"
        message += "="*60 + "\n"
        message += "CONFIRM YOU WANT TO RUN PROCESS WITH:\n"
        message += "="*60 + "\n\n"
        
        # Show YAML (saved) values first
        message += "📄 SAVED YAML VALUES:\n"
        message += "-"*60 + "\n"
        for key in sorted(saved_values.keys()):
            saved_val = saved_values.get(key, "(not set)")
            message += f"  {key}: {saved_val}\n"
        
        message += "\n" + "="*60 + "\n"
        message += "COMPARISON WITH CURRENT GUI VALUES:\n"
        message += "="*60 + "\n\n"
        
        all_keys = set(list(saved_values.keys()) + list(gui_values.keys()))
        for key in sorted(all_keys):
            saved_val = saved_values.get(key, "(not set)")
            gui_val = gui_values.get(key, "(not set)")
            
            message += f"{key}:\n"
            message += f"  Saved in YML:  {saved_val}\n"
            message += f"  Current in GUI: {gui_val}\n"
            if saved_val != gui_val:
                message += f"  >>> MISMATCH <<<\n"
            message += "\n"
        
        message += "\n⚠️  Click 'Save & Run' to use the current GUI values.\n"
        message += "⚠️  Or manually save your configuration before running.\n"
        
        # Create overlay frame (orange semi-transparent background)
        self.warning_overlay = ctk.CTkFrame(
            self,
            fg_color=("#FFE0B2", "#E65100"),  # Light orange / Dark orange
            bg_color="transparent"
        )
        self.warning_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.warning_overlay.bind("<Button-1>", lambda e: self._close_warning_popup())
        
        # Create warning frame (centered)
        warning_frame = ctk.CTkFrame(
            self.warning_overlay,
            width=700,
            height=500,
            corner_radius=10,
            fg_color=("#FFF3E0", "#F57C00")  # Light orange / Orange
        )
        warning_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on warning_frame from closing the overlay
        warning_frame.bind("<Button-1>", lambda e: "break")
        
        # Add warning icon and title
        title_label = ctk.CTkLabel(
            warning_frame,
            text="⚠️ CONFIGURATION MISMATCH ⚠️",
            font=("Segoe UI", 18, "bold"),
            text_color=("#E65100", "#FFF3E0")  # Dark orange / Light orange
        )
        title_label.pack(pady=20)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add message textbox
        warning_textbox = ctk.CTkTextbox(
            warning_frame,
            width=660,
            height=330,
            font=("Segoe UI", 10),
            fg_color=("white", "#FF6F00"),
            text_color=("#E65100", "#FFF3E0")
        )
        warning_textbox.pack(pady=10, padx=20)
        warning_textbox.insert("1.0", message)
        warning_textbox.bind("<Button-1>", lambda e: "break")
        
        # Store message for copying
        self.current_warning_message = message
        
        # Button frame
        button_frame = ctk.CTkFrame(warning_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Add save and run button
        save_button = ctk.CTkButton(
            button_frame,
            text="💾 Save & Run",
            command=self._save_and_run,
            width=180,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#4CAF50", "#388E3C"),
            hover_color=("#66BB6A", "#43A047")
        )
        save_button.pack(side="left", padx=5)
        save_button.bind("<Button-1>", lambda e: "break")
        
        # Add copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy Details",
            command=self._copy_warning_to_clipboard,
            width=150,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#FF9800", "#F57C00"),
            hover_color=("#FFB74D", "#FB8C00")
        )
        copy_button.pack(side="left", padx=5)
        copy_button.bind("<Button-1>", lambda e: "break")
        
        # Add close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_warning_popup,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#FF6F00", "#E65100"),
            hover_color=("#FB8C00", "#BF360C")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _close_warning_popup(self):
        """Close the warning popup overlay"""
        if hasattr(self, 'warning_overlay'):
            self.warning_overlay.destroy()
            del self.warning_overlay
    
    def _save_and_run(self):
        """Save configuration, close warning popup, and run the script"""
        self.save_config()
        self._close_warning_popup()
        # Now run the script (skip validation since we just saved)
        self._proceed_with_run()
    
    def _copy_warning_to_clipboard(self):
        """Copy the warning message to clipboard"""
        if hasattr(self, 'current_warning_message'):
            self.clipboard_clear()
            self.clipboard_append(self.current_warning_message)
            self.update()
            print("Warning details copied to clipboard")

    def run_wait_script(self):
        selected_script = self.script_dropdown.get()
        if selected_script == "No scripts found":
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", "No scripts available to run\n")
            return
        
        # Prevent multiple simultaneous executions
        if self.script_is_running:
            self.output_textbox.insert("end", "\nA script is already running. Please wait...\n")
            return
        
        # Check runtime mode and environment selection
        runtime_mode = self.runtime_mode.get()
        if runtime_mode == "Conda Environment":
            # Check if conda environment is selected
            selected_env = self.env_dropdown.get()
            if not selected_env or selected_env == "Select Conda Environment" or selected_env == "No conda environments found":
                # Show popup to select environment
                self.show_env_selection_popup()
                return
        
        # Check for null/empty parameters
        null_params = []
        for key, entry in self.field_entries.items():
            value = entry.get().strip()
            if not value:
                null_params.append(key)
        
        if null_params:
            # Show popup warning about null parameters
            self.show_null_params_warning(null_params)
            return
        
        # Proceed directly with run - values will be saved to AppData automatically
        self._proceed_with_run()
    
    def _proceed_with_run(self):
        """Execute the script (called after validation passes)"""
        selected_script = self.script_dropdown.get()
        
        # Set running state
        self.script_is_running = True
        self.current_process = None  # Will be set when subprocess starts
        
        # Update button to show running state
        self.wait_button.configure(
            text=f"⏳ Running {selected_script}...",
            fg_color=["#4CAF50", "#388E3C"],  # Green color for running
            state="disabled"
        )
        
        # Show stop button
        self.stop_button.pack(side="left", padx=5)
        
        # Store script context for error reporting
        self.current_script_name = selected_script
        self.script_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Store runtime mode and conda environment (if applicable)
        runtime_mode = self.runtime_mode.get()
        if runtime_mode == "Conda Environment":
            self.current_conda_env = self.env_dropdown.get()  # Store conda environment
        else:
            self.current_conda_env = "Bundled Python"  # Indicate bundled mode
        
        self.current_command = None  # Will be set when subprocess starts
        
        # Save current GUI values to AppData config file for this run
        config_file_path = None
        self.current_config_values = {}
        if self.current_config_file:
            # Get values from all dynamic entry widgets
            config_data = {}
            for key, entry in self.field_entries.items():
                value = entry.get()
                config_data[key] = value if value else None
            
            # Save to AppData (writable location)
            config_file_path = get_config_writable_path(self.current_config_file)
            try:
                config_file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False)
                config_file_path = str(config_file_path)
                self.current_config_values = config_data
                print(f"Runtime config saved to {config_file_path}")
            except Exception as e:
                print(f"Error saving runtime config: {e}")
                config_file_path = None
            
        # Get script path from scripts directory
        script_dir = Path(r"W:\Tools\GUIs\Land_Cover_Script_Interface\scripts")
        script_path = script_dir / selected_script
        
        self.output_textbox.delete("1.0", "end")
        self.output_textbox.insert("1.0", f"Starting {selected_script}...\n")
        
        # Run in a separate thread to avoid blocking GUI
        thread = threading.Thread(target=self._execute_script, args=(script_path, config_file_path))
        thread.daemon = True
        thread.start()

    def _execute_script(self, script_path, config_file_path=None):
        try:
            # Check runtime mode
            runtime_mode = self.runtime_mode.get()
            
            # Set environment variables for unbuffered output
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            # Determine which Python to use based on runtime mode
            if runtime_mode == "Bundled Python":
                # Use bundled Python (from exe or current Python)
                self.after(0, self._update_output, f"Using bundled Python interpreter\n")
                
                # When running as PyInstaller exe, sys.executable points to the exe itself
                # We need to find the actual Python interpreter
                try:
                    python_exe = self._get_bundled_python_executable()
                except FileNotFoundError as e:
                    # No Python found - show helpful error
                    self.after(0, self._update_output, f"\n{str(e)}\n")
                    self.after(0, self._show_bundled_python_error)
                    self.after(0, self._set_button_error)
                    self.after(0, self._restore_button_state)
                    return
                
                command = [python_exe, '-u', str(script_path)]
                if config_file_path:
                    command.extend(['--config', config_file_path])
                use_shell = False
            else:
                # Use conda environment
                selected_env = self.env_dropdown.get()
                
                # Build command based on whether conda env is selected
                # Check if a valid conda environment is selected (not placeholder or error text)
                if (selected_env and 
                    selected_env not in ["No conda environments found", "Select Conda Environment"]):
                    # Use conda run to execute in selected environment
                    # Use full path if available, otherwise use command name
                    conda_cmd = getattr(self, 'conda_full_path', None) or getattr(self, 'conda_executable', 'conda') or 'conda'
                    
                    # For .bat files, we need to build a proper command string with escaped quotes
                    if conda_cmd.endswith('.bat'):
                        # Escape the paths properly for cmd
                        # Use ^ to escape special characters in cmd
                        script_path_safe = str(script_path).replace('!', '^!')
                        config_path_safe = str(config_file_path).replace('!', '^!') if config_file_path else None
                        
                        # Build command with proper quoting
                        command = f'"{conda_cmd}" run --no-capture-output -n {selected_env} python -u "{script_path_safe}"'
                        if config_path_safe:
                            command += f' --config "{config_path_safe}"'
                        use_shell = True
                    else:
                        # Regular conda executable - build as a list
                        command = [conda_cmd, 'run', '--no-capture-output', '-n', selected_env, 
                                  'python', '-u', str(script_path)]
                        if config_file_path:
                            command.extend(['--config', str(config_file_path)])
                        use_shell = False
                    
                    self.after(0, self._update_output, f"Using conda environment: {selected_env}\n")
                    if isinstance(command, list):
                        command_display = ' '.join(f'"{c}"' if ' ' in str(c) else str(c) for c in command)
                    else:
                        command_display = command
                    self.after(0, self._update_output, f"Command: {command_display}\n")
                else:
                    # No valid conda environment selected but conda mode is chosen
                    self.after(0, self._update_output, f"Warning: No valid conda environment selected, using bundled Python instead\n")
                    python_exe = self._get_bundled_python_executable()
                    command = [python_exe, '-u', str(script_path)]
                    if config_file_path:
                        command.extend(['--config', config_file_path])
                    use_shell = False
            
            try:
                # Execute with appropriate shell setting
                # Hide console window on Windows
                creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=0,
                    shell=use_shell,
                    env=env,
                    creationflags=creation_flags
                )
            except FileNotFoundError as e:
                # If conda command fails, fall back to system Python
                if selected_env and selected_env != "No conda environments found":
                    self.after(0, self._update_output, f"Warning: Could not activate conda environment '{selected_env}', using system Python instead.\n")
                    command = [sys.executable, '-u', str(script_path)]
                    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=0,
                        env=env,
                        creationflags=creation_flags
                    )
                else:
                    raise
            
            # Store process reference for stop button
            self.current_process = process
            
            # Store command for execution details
            if isinstance(command, list):
                self.current_command = ' '.join(str(c) for c in command)
            else:
                self.current_command = command
            
            # Read output line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.after(0, self._update_output, line)
                if process.poll() is not None:
                    # Process finished, read any remaining output
                    remaining = process.stdout.read()
                    if remaining:
                        self.after(0, self._update_output, remaining)
                    break
            
            process.wait()
            
            if process.returncode == 0:
                self.after(0, self._update_output, "\nScript completed successfully!\n")
                self.after(0, self._save_run_to_history, True)  # Save successful run
                self.after(0, self._set_button_success)
                self.after(0, self._restore_button_state)
                self.after(0, self._show_success_popup)
            else:
                # Error already captured in stdout (stderr was redirected to stdout)
                self.after(0, self._update_output, f"\nScript exited with error code {process.returncode}\n")
                # Get the full output from the textbox for history and error popup
                def save_failed_run_with_output():
                    output_content = self.output_textbox.get("1.0", "end-1c")
                    self._save_run_to_history(False, output_content)  # Save failed run with output
                    self._show_error_popup(output_content, include_context=True)
                self.after(0, save_failed_run_with_output)
                self.after(0, self._set_button_success)
                self.after(0, self._restore_button_state)
                
        except Exception as e:
            error_msg = str(e)
            self.after(0, self._update_output, f"\nError running script: {e}\n")
            # Get the full output from the textbox for history
            def save_exception_with_output():
                output_content = self.output_textbox.get("1.0", "end-1c")
                self._save_run_to_history(False, output_content)  # Save failed run with output
                self._show_error_popup(error_msg, include_context=True)
            self.after(0, save_exception_with_output)
            self.after(0, self._set_button_success)
            self.after(0, self._restore_button_state)

    def _set_button_success(self):
        """Set button color to default (success state)"""
        self.wait_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])  # Default blue

    def _set_button_error(self):
        """Set button color to red (error state)"""
        self.wait_button.configure(fg_color=["#D32F2F", "#B71C1C"])  # Red color
    
    def _restore_button_state(self):
        """Restore button to normal state after script execution"""
        self.script_is_running = False
        self.current_process = None
        selected_script = self.script_dropdown.get()
        self.wait_button.configure(
            text=f"Run {selected_script}",
            state="normal"
        )
        # Hide stop button
        self.stop_button.pack_forget()

    def stop_script(self):
        """Stop the currently running script"""
        if self.current_process and self.script_is_running:
            try:
                if sys.platform == 'win32':
                    # On Windows, use taskkill to terminate the entire process tree
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(self.current_process.pid)],
                        capture_output=True,
                        timeout=5
                    )
                    self._update_output("\n⏹ Script and all child processes terminated.\n")
                else:
                    # On Unix-like systems, send SIGTERM to process group
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                    self._update_output("\n⏹ Script termination requested...\n")
                    self.after(1000, self._force_kill_if_needed)  # Force kill after 1 second if still running
            except Exception as e:
                self._update_output(f"\nError stopping script: {e}\n")
    
    def _force_kill_if_needed(self):
        """Force kill the process if it didn't terminate gracefully"""
        if self.current_process and self.current_process.poll() is None:
            try:
                if sys.platform == 'win32':
                    # Already handled by taskkill above
                    pass
                else:
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGKILL)
                    self._update_output("\n⏹ Script forcefully terminated.\n")
            except:
                pass

    def _show_bundled_python_error(self):
        """Show error popup for missing bundled Python"""
        error_msg = """Bundled Python Not Available

This executable was built in "onefile" mode and doesn't include 
a usable Python interpreter for running external scripts.

OPTIONS:

1. REBUILD THE EXE (Recommended for distribution)
   • The build configuration has already been updated
   • Run: pyinstaller drag_drop.spec
   • This will create a folder with python.exe included
   • Distribute the entire folder (not just the .exe)

2. USE CONDA ENVIRONMENT MODE (Quick fix)
   • Switch to "Conda Environment" mode
   • Select an environment with Python 3.x
   • Scripts will run using your system's Python

See REBUILD_INSTRUCTIONS.md for detailed steps."""
        
        # Create overlay frame
        overlay = ctk.CTkFrame(
            self,
            fg_color=("#FFE0B2", "#E65100"),  # Orange warning colors
            bg_color="transparent"
        )
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Create message frame
        msg_frame = ctk.CTkFrame(overlay, fg_color=("#FFFFFF", "#2B2B2B"), corner_radius=15)
        msg_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7, relheight=0.6)
        
        # Title
        title = ctk.CTkLabel(
            msg_frame,
            text="⚠️ Bundled Python Not Found",
            font=("Segoe UI", 20, "bold"),
            text_color=("#E65100", "#FF9800")
        )
        title.pack(pady=(20, 10))
        
        # Error message
        msg_text = ctk.CTkTextbox(
            msg_frame,
            font=("Segoe UI", 12),
            wrap="word",
            fg_color=("gray90", "gray20")
        )
        msg_text.pack(pady=10, padx=20, fill="both", expand=True)
        msg_text.insert("1.0", error_msg)
        msg_text.configure(state="disabled")
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(msg_frame, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        # Switch to Conda mode button
        switch_btn = ctk.CTkButton(
            btn_frame,
            text="Switch to Conda Mode",
            command=lambda: [overlay.destroy(), self.runtime_mode.set("Conda Environment"), self._on_runtime_mode_change("Conda Environment")],
            fg_color=("#4CAF50", "#388E3C"),
            width=180,
            height=40
        )
        switch_btn.pack(side="left", padx=5)
        
        # Close button
        close_btn = ctk.CTkButton(
            btn_frame,
            text="Close",
            command=overlay.destroy,
            fg_color=("#757575", "#424242"),
            width=120,
            height=40
        )
        close_btn.pack(side="left", padx=5)

    def _show_error_popup(self, error_message, include_context=False):
        """Display error popup overlay with red background"""
        # Build full error message with context
        full_message = error_message if error_message.strip() else "An unknown error occurred."
        
        if include_context:
            context_info = "\n" + "="*60 + "\n"
            context_info += "EXECUTION CONTEXT:\n"
            context_info += "="*60 + "\n"
            context_info += f"Script: {getattr(self, 'current_script_name', 'Unknown')}\n"
            context_info += f"Conda Environment: {getattr(self, 'current_conda_env', 'Unknown')}\n"
            context_info += f"Command: {getattr(self, 'current_command', 'Unknown')}\n"
            context_info += f"Started: {getattr(self, 'script_start_time', 'Unknown')}\n"
            context_info += f"\nConfig File ({getattr(self, 'current_config_file', 'Unknown')}):\n"
            context_info += "-"*60 + "\n"
            
            config_values = getattr(self, 'current_config_values', {})
            if config_values:
                for key, value in config_values.items():
                    context_info += f"  {key}: {value}\n"
            else:
                context_info += "  (No configuration values)\n"
            
            full_message = full_message + context_info
        # Create overlay frame (red semi-transparent background)
        self.error_overlay = ctk.CTkFrame(
            self,
            fg_color=("#FFCDD2", "#B71C1C"),  # Light red / Dark red
            bg_color="transparent"
        )
        self.error_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.error_overlay.bind("<Button-1>", lambda e: self._close_error_popup())
        
        # Create error frame (centered)
        error_frame = ctk.CTkFrame(
            self.error_overlay,
            width=600,
            height=450,
            corner_radius=10,
            fg_color=("#FFEBEE", "#C62828")  # Light red / Red
        )
        error_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on error_frame from closing the overlay
        error_frame.bind("<Button-1>", lambda e: "break")
        
        # Add warning icon and title
        title_label = ctk.CTkLabel(
            error_frame,
            text="⚠️ SCRIPT FAILED ⚠️",
            font=("Segoe UI", 18, "bold"),
            text_color=("#B71C1C", "#FFEBEE")  # Dark red / Light red
        )
        title_label.pack(pady=20)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add error message textbox
        error_textbox = ctk.CTkTextbox(
            error_frame,
            width=560,
            height=250,
            font=("Segoe UI", 10),
            fg_color=("white", "#D32F2F"),
            text_color=("#B71C1C", "#FFEBEE")
        )
        error_textbox.pack(pady=10, padx=20)
        error_textbox.insert("1.0", full_message)
        # Keep in normal state to allow text selection and copying
        error_textbox.bind("<Button-1>", lambda e: "break")
        
        # Store error message for copying
        self.current_error_message = full_message
        
        # Button frame for Copy and Close buttons
        button_frame = ctk.CTkFrame(error_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Add copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_error_to_clipboard,
            width=180,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#EF6C00", "#E65100"),
            hover_color=("#E65100", "#BF360C")
        )
        copy_button.pack(side="left", padx=5)
        copy_button.bind("<Button-1>", lambda e: "break")
        
        # Add close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_error_popup,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#D32F2F", "#B71C1C"),
            hover_color=("#C62828", "#8B0000")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _close_error_popup(self):
        """Close the error popup overlay"""
        if hasattr(self, 'error_overlay'):
            self.error_overlay.destroy()
            del self.error_overlay
    
    def _show_success_popup(self):
        """Display success popup overlay with green background"""
        # Build context info
        context_info = "="*60 + "\n"
        context_info += "EXECUTION DETAILS:\n"
        context_info += "="*60 + "\n"
        context_info += f"Script: {getattr(self, 'current_script_name', 'Unknown')}\n"
        context_info += f"Conda Environment: {getattr(self, 'current_conda_env', 'Unknown')}\n"
        context_info += f"Command: {getattr(self, 'current_command', 'Unknown')}\n"
        context_info += f"Started: {getattr(self, 'script_start_time', 'Unknown')}\n"
        context_info += f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        context_info += f"\nConfig File ({getattr(self, 'current_config_file', 'Unknown')}):\n"
        context_info += "-"*60 + "\n"
        
        config_values = getattr(self, 'current_config_values', {})
        if config_values:
            for key, value in config_values.items():
                context_info += f"  {key}: {value}\n"
        else:
            context_info += "  (No configuration values)\n"
        
        # Create overlay frame (green semi-transparent background)
        self.success_overlay = ctk.CTkFrame(
            self,
            fg_color=("#C8E6C9", "#2E7D32"),  # Light green / Dark green
            bg_color="transparent"
        )
        self.success_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.success_overlay.bind("<Button-1>", lambda e: self._close_success_popup())
        
        # Create success frame (centered)
        success_frame = ctk.CTkFrame(
            self.success_overlay,
            width=600,
            height=450,
            corner_radius=10,
            fg_color=("#E8F5E9", "#388E3C")  # Light green / Green
        )
        success_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on success_frame from closing the overlay
        success_frame.bind("<Button-1>", lambda e: "break")
        
        # Add success icon and title
        title_label = ctk.CTkLabel(
            success_frame,
            text="✓ SCRIPT COMPLETED SUCCESSFULLY ✓",
            font=("Segoe UI", 18, "bold"),
            text_color=("#1B5E20", "#E8F5E9")  # Dark green / Light green
        )
        title_label.pack(pady=20)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add context textbox
        context_textbox = ctk.CTkTextbox(
            success_frame,
            width=560,
            height=250,
            font=("Segoe UI", 10),
            fg_color=("white", "#2E7D32"),
            text_color=("#1B5E20", "#E8F5E9")
        )
        context_textbox.pack(pady=10, padx=20)
        context_textbox.insert("1.0", context_info)
        context_textbox.bind("<Button-1>", lambda e: "break")
        
        # Store context for copying
        self.current_success_context = context_info
        
        # Button frame for Copy and Close buttons
        button_frame = ctk.CTkFrame(success_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Add copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy Details",
            command=self._copy_success_to_clipboard,
            width=150,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#66BB6A", "#43A047"),
            hover_color=("#4CAF50", "#388E3C")
        )
        copy_button.pack(side="left", padx=5)
        copy_button.bind("<Button-1>", lambda e: "break")
        
        # Add close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_success_popup,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#388E3C", "#2E7D32"),
            hover_color=("#2E7D32", "#1B5E20")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _close_success_popup(self):
        """Close the success popup overlay"""
        if hasattr(self, 'success_overlay'):
            self.success_overlay.destroy()
            del self.success_overlay
    
    def _copy_success_to_clipboard(self):
        """Copy the success context to clipboard"""
        if hasattr(self, 'current_success_context'):
            self.clipboard_clear()
            self.clipboard_append(self.current_success_context)
            self.update()  # Required to finalize clipboard content
            print("Success details copied to clipboard")
    
    def _copy_error_to_clipboard(self):
        """Copy the error message to clipboard"""
        if hasattr(self, 'current_error_message'):
            self.clipboard_clear()
            self.clipboard_append(self.current_error_message)
            self.update()  # Required to finalize clipboard content
            print("Error message copied to clipboard")

    def _update_output(self, text):
        self.output_textbox.insert("end", text)
        self.output_textbox.see("end")
        
        # Also update expanded output window if it's open
        if hasattr(self, 'expanded_output_textbox'):
            try:
                self.expanded_output_textbox.insert("end", text)
                self.expanded_output_textbox.see("end")
            except:
                # Window might have been closed
                if hasattr(self, 'expanded_output_textbox'):
                    del self.expanded_output_textbox
    
    def _ensure_history_file(self):
        """Ensure history file exists"""
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump([], f)
    
    def _save_run_to_history(self, success, output=None):
        """Save current run configuration and results to history"""
        try:
            # Read existing history
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            # Create new history entry
            entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'script': getattr(self, 'current_script_name', 'Unknown'),
                'conda_env': getattr(self, 'current_conda_env', 'Unknown'),
                'config_file': getattr(self, 'current_config_file', 'Unknown'),
                'config_values': getattr(self, 'current_config_values', {}),
                'success': success,
                'command': getattr(self, 'current_command', 'Unknown')
            }
            
            # Add output/traceback for failed runs
            if not success and output:
                entry['output'] = output
            
            # Add to beginning of history
            history.insert(0, entry)
            
            # Keep only last 100 runs
            history = history[:100]
            
            # Save back to file
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            print(f"Error saving to history: {e}")
    
    def show_history_browser(self):
        """Display history browser window"""
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            history = []
        
        if not history:
            # Show message if no history
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", "No run history available yet.\n")
            return
        
        # Create overlay frame
        self.history_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.history_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.history_overlay.bind("<Button-1>", lambda e: self._close_history_browser())
        
        # Create history frame (centered, larger)
        history_frame = ctk.CTkFrame(
            self.history_overlay,
            width=560,
            height=600,
            corner_radius=10
        )
        history_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on history_frame from closing the overlay
        history_frame.bind("<Button-1>", lambda e: "break")
        
        # Add title label
        title_label = ctk.CTkLabel(
            history_frame,
            text="📜 Run History",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=15)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add search bar
        search_frame = ctk.CTkFrame(history_frame, fg_color="transparent")
        search_frame.pack(pady=(0, 10), padx=20, fill="x")
        search_frame.bind("<Button-1>", lambda e: "break")
        
        search_label = ctk.CTkLabel(
            search_frame,
            text="🔍 Search:",
            font=("Segoe UI", 12)
        )
        search_label.pack(side="left", padx=(0, 10))
        search_label.bind("<Button-1>", lambda e: "break")
        
        self.history_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Filter by script name, environment, or config...",
            font=("Segoe UI", 11),
            height=35
        )
        self.history_search_entry.pack(side="left", fill="x", expand=True)
        
        # Add scrollable frame for history items
        scroll_frame = ctk.CTkScrollableFrame(
            history_frame,
            width=560,
            height=400
        )
        scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)
        scroll_frame.bind("<Button-1>", lambda e: "break")
        
        # Store full history and scroll frame for filtering
        self.current_history = history
        self.history_scroll_frame = scroll_frame
        
        # Display each history entry
        for i, entry in enumerate(history):
            self._create_history_entry_widget(scroll_frame, entry, i)
        
        # Bind search to filter results
        self.history_search_entry.bind("<KeyRelease>", lambda e: self._filter_history_entries())
        
        # Add close button
        close_button = ctk.CTkButton(
            history_frame,
            text="Close",
            command=self._close_history_browser,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        close_button.pack(pady=15)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _create_history_entry_widget(self, parent, entry, index):
        """Create a widget for a single history entry"""
        # Determine icon based on success/failure
        if entry.get('success', False):
            status_icon = "✅"  # Green checkmark for success
        else:
            status_icon = "❌"  # Red X for failure
        
        # Use default background color for all entries
        bg_color = ("#F0F0F0", "#2B2B2B")  # Light gray / Dark gray (default)
        
        # Create frame for this entry
        entry_frame = ctk.CTkFrame(
            parent,
            fg_color=bg_color,
            corner_radius=8
        )
        entry_frame.pack(pady=5, padx=5, fill="x")
        entry_frame.bind("<Button-1>", lambda e: "break")
        
        # Create inner frame for better layout
        inner_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
        inner_frame.pack(pady=10, padx=10, fill="x")
        inner_frame.bind("<Button-1>", lambda e: "break")
        
        # Header with timestamp and status
        header_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        header_frame.pack(fill="x")
        header_frame.bind("<Button-1>", lambda e: "break")
        
        timestamp_label = ctk.CTkLabel(
            header_frame,
            text=f"{status_icon} {entry.get('timestamp', 'Unknown')} - {entry.get('script', 'Unknown')}",
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )
        timestamp_label.pack(side="left")
        timestamp_label.bind("<Button-1>", lambda e: "break")
        
        # Environment and config info
        info_label = ctk.CTkLabel(
            inner_frame,
            text=f"Environment: {entry.get('conda_env', 'Unknown')} | Config: {entry.get('config_file', 'Unknown')}",
            font=("Segoe UI", 10),
            anchor="w"
        )
        info_label.pack(fill="x", pady=(5, 0))
        info_label.bind("<Button-1>", lambda e: "break")
        
        # Configuration values
        config_values = entry.get('config_values', {})
        if config_values:
            config_text = "Settings: "
            config_items = [f"{k}={v}" for k, v in list(config_values.items())[:3]]
            config_text += ", ".join(config_items)
            if len(config_values) > 3:
                config_text += f" (+{len(config_values)-3} more)"
            
            config_label = ctk.CTkLabel(
                inner_frame,
                text=config_text,
                font=("Segoe UI", 9),
                anchor="w",
                wraplength=600
            )
            config_label.pack(fill="x", pady=(2, 0))
            config_label.bind("<Button-1>", lambda e: "break")
        
        # Button frame
        button_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        button_frame.pack(pady=(10, 0))
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Load button
        load_button = ctk.CTkButton(
            button_frame,
            text="📥 Load Settings",
            command=lambda: self._load_history_entry(entry),
            width=140,
            height=32,
            font=("Segoe UI", 10, "bold"),
            fg_color=("#2196F3", "#1976D2"),
            hover_color=("#42A5F5", "#1565C0")
        )
        load_button.pack(side="left", padx=5)
        load_button.bind("<Button-1>", lambda e: "break")
        
        # View details button
        details_button = ctk.CTkButton(
            button_frame,
            text="📋 View Details",
            command=lambda: self._show_history_details(entry),
            width=140,
            height=32,
            font=("Segoe UI", 10, "bold"),
            fg_color=("#757575", "#616161"),
            hover_color=("#9E9E9E", "#757575")
        )
        details_button.pack(side="left", padx=5)
        details_button.bind("<Button-1>", lambda e: "break")
    
    def _load_history_entry(self, entry):
        """Load configuration from a history entry"""
        try:
            # Switch to the script from history
            script_name = entry.get('script', '')
            if script_name and script_name in self.script_dropdown.cget('values'):
                self.script_dropdown.set(script_name)
                self.on_script_selected(script_name)
            
            # Switch to the conda environment from history
            conda_env = entry.get('conda_env', '')
            if conda_env and conda_env in self.env_dropdown.cget('values'):
                self.env_dropdown.set(conda_env)
            
            # Load configuration values
            config_values = entry.get('config_values', {})
            for key, value in config_values.items():
                if key in self.field_entries:
                    self.field_entries[key].delete(0, "end")
                    if value:
                        self.field_entries[key].insert(0, str(value))
            
            # Close history browser
            self._close_history_browser()
            
            # Show confirmation message
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", f"✓ Loaded settings from {entry.get('timestamp', 'previous run')}\n\n")
            self.output_textbox.insert("end", "Configuration loaded successfully!\n")
            self.output_textbox.insert("end", "-" * 40 + "\n")
            for key, value in config_values.items():
                self.output_textbox.insert("end", f"{key}: {value}\n")
            
        except Exception as e:
            print(f"Error loading history entry: {e}")
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", f"Error loading history entry: {e}\n")
    
    def _show_history_details(self, entry):
        """Show detailed information about a history entry"""
        details = "="*60 + "\n"
        details += "RUN DETAILS\n"
        details += "="*60 + "\n"
        details += f"Timestamp: {entry.get('timestamp', 'Unknown')}\n"
        details += f"Script: {entry.get('script', 'Unknown')}\n"
        details += f"Conda Environment: {entry.get('conda_env', 'Unknown')}\n"
        details += f"Config File: {entry.get('config_file', 'Unknown')}\n"
        details += f"Status: {'✓ Success' if entry.get('success', False) else '✗ Failed'}\n"
        details += f"Command: {entry.get('command', 'Unknown')}\n"
        details += "\nConfiguration Values:\n"
        details += "-"*60 + "\n"
        
        config_values = entry.get('config_values', {})
        if config_values:
            for key, value in config_values.items():
                details += f"  {key}: {value}\n"
        else:
            details += "  (No configuration values)\n"
        
        # Add traceback/output for failed runs
        if not entry.get('success', False) and entry.get('output'):
            details += "\nOutput/Traceback:\n"
            details += "="*60 + "\n"
            details += entry.get('output', '')
            details += "\n" + "="*60 + "\n"
        
        # Create overlay for details
        self.details_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.details_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.details_overlay.bind("<Button-1>", lambda e: self._close_details_overlay())
        
        # Create details frame
        details_frame = ctk.CTkFrame(
            self.details_overlay,
            width=600,
            height=500,
            corner_radius=10
        )
        details_frame.place(relx=0.5, rely=0.5, anchor="center")
        details_frame.bind("<Button-1>", lambda e: "break")
        
        # Title
        title_label = ctk.CTkLabel(
            details_frame,
            text="📋 Run Details",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=15)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Details textbox
        details_textbox = ctk.CTkTextbox(
            details_frame,
            width=560,
            height=350,
            font=("Segoe UI", 11)
        )
        details_textbox.pack(pady=10, padx=20)
        details_textbox.insert("1.0", details)
        details_textbox.bind("<Button-1>", lambda e: "break")
        
        # Store details for copying
        self.current_details = details
        
        # Button frame
        button_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy",
            command=self._copy_details_to_clipboard,
            width=120,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        copy_button.pack(side="left", padx=5)
        copy_button.bind("<Button-1>", lambda e: "break")
        
        # Close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_details_overlay,
            width=120,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _close_details_overlay(self):
        """Close the details overlay"""
        if hasattr(self, 'details_overlay'):
            self.details_overlay.destroy()
            del self.details_overlay
    
    def _copy_details_to_clipboard(self):
        """Copy details to clipboard"""
        if hasattr(self, 'current_details'):
            self.clipboard_clear()
            self.clipboard_append(self.current_details)
            self.update()
            print("Details copied to clipboard")
    
    def _filter_history_entries(self):
        """Filter history entries based on search text"""
        if not hasattr(self, 'history_scroll_frame') or not hasattr(self, 'current_history'):
            return
        
        search_text = self.history_search_entry.get().lower()
        
        # Clear current entries
        for widget in self.history_scroll_frame.winfo_children():
            widget.destroy()
        
        # Filter and display matching entries
        filtered_count = 0
        for i, entry in enumerate(self.current_history):
            # Search in script name, conda env, config file, and config values
            script = entry.get('script', '').lower()
            conda_env = entry.get('conda_env', '').lower()
            config_file = entry.get('config_file', '').lower()
            config_values = str(entry.get('config_values', {})).lower()
            
            if (search_text in script or 
                search_text in conda_env or 
                search_text in config_file or 
                search_text in config_values):
                self._create_history_entry_widget(self.history_scroll_frame, entry, i)
                filtered_count += 1
        
        # Show message if no results
        if filtered_count == 0:
            no_results_label = ctk.CTkLabel(
                self.history_scroll_frame,
                text="No matching entries found",
                font=("Segoe UI", 12),
                text_color="gray"
            )
            no_results_label.pack(pady=20)
    
    def _close_history_browser(self):
        """Close the history browser overlay"""
        if hasattr(self, 'history_overlay'):
            self.history_overlay.destroy()
            del self.history_overlay


def main():
    """Main entry point with splash screen"""
    # Create and run the main application with splash
    app = App(show_splash=True)
    app.mainloop()


if __name__ == "__main__":
    main()
