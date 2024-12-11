import os
import tkinter as tk
from tkinter import ttk
import sys
import threading
import sv_ttk
import darkdetect
from notifypy import Notify
from PIL import Image, ImageTk

from scraper_backend import run


class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, string):
        self.widget.insert(tk.END, string)
        self.widget.see(tk.END)  # Auto-scroll to the end

    def flush(self):
        pass  # Required for compatibility with some libraries


def handle_button_click(icon_path):
    username = str(username_var.get())
    password = str(password_var.get())
    course_url = str(url_var.get())
    converted_to_pdf = str(converted_var.get())

    # Clear the message display area
    message_display.delete(1.0, tk.END)

    # Perform some processing and print messages to the GUI
    def download():
        try:
            run(username, password, course_url, converted_to_pdf)
            notification = Notify()
            notification.title = "StudySnatcher"
            notification.message = "All files downloaded"
            notification.icon = icon_path
            notification.send()
        except Exception as e:
            print(f"Error: {e}")

    threading.Thread(target=download).start()


if __name__ == "__main__":
    # Get path to app icon file
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    elif __file__:
        application_path = os.path.dirname(__file__)

    icon_path = os.path.join(application_path, 'icon.ico')

    # Create the main window
    root = tk.Tk()
    root.title("StudySnatcher")

    log = Image.open(icon_path)
    logo = ImageTk.PhotoImage(log)
    root.tk.call('wm', 'iconphoto', root._w, logo)

    # Create variables to store user inputs
    username_var = tk.StringVar()
    password_var = tk.StringVar()
    url_var = tk.StringVar()
    converted_var = tk.BooleanVar()

    # Create widgets with updated fonts
    ttk.Label(root, text="Username:").grid(
        row=0, column=0, padx=10, pady=5)
    ttk.Entry(root, textvariable=username_var).grid(
        row=0, column=1, padx=10, pady=5)

    ttk.Label(root, text="Password:").grid(
        row=1, column=0, padx=10, pady=5)
    ttk.Entry(root, textvariable=password_var, show="*").grid(
        row=1, column=1, padx=10, pady=5)

    ttk.Label(root, text="URL of StudyDrive course:").grid(
        row=2, column=0, padx=10, pady=5)
    ttk.Entry(root, textvariable=url_var).grid(
        row=2, column=1, padx=10, pady=5)

    ttk.Checkbutton(root, text="Convert all files to PDF", variable=converted_var, style="TCheckbutton").grid(
        row=3, column=0, columnspan=2, pady=5)

    ttk.Button(root, text="Download", command=lambda: handle_button_click(icon_path), style="TButton").grid(
        row=4, column=0, columnspan=2, pady=10)

    # Text widget to display messages
    message_display = tk.Text(root, height=10, width=50)
    message_display.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

    # Redirect print output to the Text widget
    sys.stdout = TextRedirector(message_display)

    # Start the GUI main loop
    sv_ttk.set_theme(darkdetect.theme())
    root.mainloop()
