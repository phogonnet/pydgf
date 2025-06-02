import sys
import argparse
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib

from .dskwindow import DskWindow

def main():
    app = Gtk.Application.new("net.phogon.pydgf", Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE)

    def on_activate(self):
        if len(self.get_windows()) < 1:
            self.add_window(DskWindow())
    app.connect("activate", on_activate)

    def on_open(self, files, *hints):
        for file in files:
            self.add_window(DskWindow(file.get_path()))
    app.connect("open", on_open)

    exit(app.run(sys.argv))