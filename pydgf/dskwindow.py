import os
import pickle
import re
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GObject

# https://stackoverflow.com/questions/5977576/is-there-a-convenient-way-to-map-a-file-uri-to-os-path
try:
    from urllib.parse import urlparse, unquote
    from urllib.request import url2pathname
except ImportError:
    from urlparse import urlparse
    from urllib import unquote, url2pathname
def uri_to_path(uri):
    parsed = urlparse(uri)
    host = "{0}{0}{mnt}{0}".format(os.path.sep, mnt=parsed.netloc)
    return os.path.normpath(os.path.join(host, url2pathname(unquote(parsed.path))))

from .disk import Disk
from .ufd import UFD
from .hexview import Hexview
from .attributes import Attributes, CellRendererAttributes
from .magtape import Magtape
from .dumpfile import Dumpfile

# Tree Model Indexes
MOD_NAME = 0
MOD_ATTR = 1
MOD_LINK_ATTR = 2
MOD_DATA = 3
MOD_DCTLINK = 4
MOD_MODIFIED = 5
MOD_ACCESSED = 6

# Device Codes
DEV_SECONDARY_MASK = 0o40
DEV_TTI = 0o10 # TELETYPE/CONSOLE/KEYBOARD INPUT
DEV_TTI1 = DEV_TTI | DEV_SECONDARY_MASK
DEV_TTO = 0o11 # TELETYPE/CONSOLE/CRT OUTPUT
DEV_TTO1 = DEV_TTO | DEV_SECONDARY_MASK
DEV_TTP = 0o11 # TELETYPE PUNCH
DEV_TTP1 = DEV_TTP | DEV_SECONDARY_MASK
DEV_PTR = 0o12 # PAPER TAPE READER
DEV_PTR1 = DEV_PTR | DEV_SECONDARY_MASK
DEV_PTP = 0o13 # PAPER TAPE PUNCH
DEV_PTP1 = DEV_PTP | DEV_SECONDARY_MASK
DEV_RTC = 0o14 # REAL TIME CLOCK
DEV_RTC1 = DEV_RTC | DEV_SECONDARY_MASK
DEV_PLT = 0o15 # INCREMENTAL PLOTTER
DEV_PLT1 = DEV_PLT | DEV_SECONDARY_MASK
DEV_CDR = 0o16 # CARD READER
DEV_CDR1 = DEV_CDR | DEV_SECONDARY_MASK
DEV_LPT = 0o17 # LINE PRINTER
DEV_LPT1 = DEV_LPT | DEV_SECONDARY_MASK
DEV_MTB = 0o22 # MAGTAPE
DEV_MTB1 = DEV_MTB | DEV_SECONDARY_MASK
DEV_DPF = 0o27 # Zebra Drives
DEV_DPF1 = DEV_DPF | DEV_SECONDARY_MASK
DEV_DKP = 0o33 # Moving Head Disc
DEV_DKP1 = DEV_DKP | DEV_SECONDARY_MASK
# DEV_TTR = ? # 
# DEV_TTR1= ? # 
# DEV_DPI = ? # DUAL PROCESSOR INPUT
# DEV_DPO = ? # DUAL PROCESSOR OUTPUT

# List of common extentions
DG_EXTENTIONS = {
    'SR': 'Assembly',
    'CB': 'Cobol',
    'FR': 'Fortran',
    # '': 'Basic',
    'AL': 'Algol',
    'JB': 'Batch Job',
    'BU': 'Back Up',
    'SC': 'Scratch',
    'LS': 'Listing',
    'RB': 'Relocatable Binary',
    'OL': 'Overlay',
    'OR': 'Overlay Replacement',
    'LB': 'Library',
    'LM': 'Relocatable Load Map',
    'SV': 'Save',
    'AB': 'Absolute',
    'DR': 'Directory',
    'CM': 'Command',
    'KS': 'Keysheet',
    'MC': 'Macro',
    'PF': 'Patch',
    'TU': 'Tuning',
    'SW': 'Swap',
    'ID': 'Valid LOGON ID',
    'AF': 'Accounting',
    'VL': 'Volume',
    'IX': 'Index',
}

class CellRendererDataSize(Gtk.CellRendererText):
    __gtype_name__ = 'CellRendererDataSize'
    __gproperties__ = {'model-data' : (object, '', '', GObject.PARAM_READWRITE)}

    def __init__(self):
        super().__init__()
        super().set_alignment(1.0, 0)

    def do_set_property(self, prop, value):
        if prop.name == "model-data":
            super().set_property("text", "" if value is None else f"{len(value)}")
    
    @classmethod
    def compare(cls, model, a, b, user_data):
        sort_column, _ = model.get_sort_column_id()
        a_data = model[a][sort_column]
        b_data = model[b][sort_column]
        if a_data is None and b_data is None: return 0
        if a_data is None: return -1
        if b_data is None: return 1
        a_len = len(a_data)
        b_len = len(b_data)
        if a_len < b_len: return -1
        if a_len > b_len: return 1
        return 0

class DskWindow(Gtk.ApplicationWindow):
    def __init__(self, filepath = None, fmt = None):
        title = "DGF"
        if filepath is not None: title += f" - {os.path.basename(filepath)}"
        super().__init__(title=title)

        self.modify_font(Pango.font_description_from_string("Monospace"))

        vbox = Gtk.VBox()
        hbox = Gtk.HBox()

        toolbar = Gtk.Toolbar()
        
        tb_new = Gtk.ToolButton(label="New", icon_name="document-new", tooltip_text="New")
        tb_new.connect("clicked", self.on_new_clicked)
        toolbar.insert(tb_new, -1)
        
        tb_open = Gtk.ToolButton(label="Open", icon_name="document-open", tooltip_text="Open")
        tb_open.connect("clicked", self.on_open_clicked)
        toolbar.insert(tb_open, -1)
        
        tb_save = Gtk.ToolButton(label="Save As", icon_name="document-save-as", tooltip_text="Save As")
        tb_save.connect("clicked", self.on_saveas_clicked)
        toolbar.insert(tb_save, -1)

        self.frame_size_control = Gtk.SpinButton(
            adjustment = Gtk.Adjustment(value=5, lower=1, upper=255, step_increment=1, page_increment=10, page_size=0), 
            climb_rate = 1,
            digits = 0,
            )
        self.frame_size_control.connect("value-changed", self.on_framesize_changed)
        self.frame_size_control.set_snap_to_ticks(True)
        tb_frame_size_control = Gtk.ToolItem()
        tb_vbox = Gtk.VBox()
        tb_vbox.pack_start(Gtk.Label(label="Frame Size"), True, True, 0)
        tb_vbox.pack_start(self.frame_size_control, True, True, 0)
        tb_frame_size_control.add(tb_vbox)
        toolbar.insert(tb_frame_size_control, -1)

        self.dsk_progress_6030 = Gtk.ProgressBar()
        tb_dsk_progress_6030 = Gtk.ToolItem()
        tb_dsk_progress_6030.add(self.dsk_progress_6030)
        toolbar.insert(tb_dsk_progress_6030, -1)

        self.dsk_progress_4048 = Gtk.ProgressBar()
        tb_dsk_progress_4048 = Gtk.ToolItem()
        tb_dsk_progress_4048.add(self.dsk_progress_4048)
        toolbar.insert(tb_dsk_progress_4048, -1)

        vbox.pack_start(toolbar, False, False, 0)
        vbox.pack_start(hbox, True, True, 0)
        
        # MOD_NAME, MOD_ATTR, MOD_LINK_ATTR, MOD_DATA, MOD_DCTLINK, MOD_MODIFIED, MOD_ACCESSED
        model = Gtk.TreeStore(str, str, str, object, int, str, str)
        model.connect('row-changed', self.on_row_changed)
        model.connect('row-inserted', self.on_row_inserted)
        model.connect('row-deleted', self.on_row_deleted)
        self.model = model # FOR SAVE ABILITY
        treeview = Gtk.TreeView(model=model)
        self.treeview = treeview # FIXME: FOR CONTEXT MENU REASONS
        treeview.connect('key-press-event', self.on_treeview_keypress)
        treeview.connect('button-press-event', self.on_treeview_buttonpress)
        
        self.treeview_context_menu = Gtk.Menu()
        treeview_context_menu_new_folder = Gtk.MenuItem("New Folder")
        treeview_context_menu_new_folder.connect("activate", self.on_new_folder)
        self.treeview_context_menu.append(treeview_context_menu_new_folder)
        treeview_context_menu_delete = Gtk.MenuItem("Delete")
        treeview_context_menu_delete.connect("activate", self.on_delete)
        self.treeview_context_menu.append(treeview_context_menu_delete)
        treeview_context_menu_swab = Gtk.MenuItem('"SWAB" file')
        treeview_context_menu_swab.connect("activate", self.on_swab)
        self.treeview_context_menu.append(treeview_context_menu_swab)

        targetentries_treeview = [
            # Gtk.TargetEntry.new("STRING", 0, 0),
            # Gtk.TargetEntry.new("TEXT", 0, 0),
            # Gtk.TargetEntry.new("ASCII", 0, 0),
            # Gtk.TargetEntry.new("UTF8_STRING", 0, 0),
            # Gtk.TargetEntry.new("text/plain", 0, 0),
            Gtk.TargetEntry.new("text/uri", Gtk.TargetFlags.OTHER_APP, 1),
            Gtk.TargetEntry.new("text/uri-list", Gtk.TargetFlags.OTHER_APP, 2),
            Gtk.TargetEntry.new("pydgf/treeview-same", Gtk.TargetFlags.SAME_WIDGET, 42069),
            Gtk.TargetEntry.new("pydgf/treeview-other", Gtk.TargetFlags.OTHER_WIDGET, 69420),
            ]
        treeview.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, targetentries_treeview, Gdk.DragAction.COPY)
        treeview.connect("drag-data-get", self.on_drag_data_get)
        treeview.enable_model_drag_dest(targetentries_treeview, Gdk.DragAction.COPY)
        treeview.connect("drag-data-received", self.on_drag_data_received)

        treeview.get_selection().connect("changed", self.on_tree_selection_changed)

        colrenderer_name_edit = Gtk.CellRendererText(editable=True)
        colrenderer_name_edit.connect('edited', self.on_name_edit)
        treeview.append_column(Gtk.TreeViewColumn("Name", colrenderer_name_edit, text=MOD_NAME))
        treeview.append_column(Gtk.TreeViewColumn("FileAttr", CellRendererAttributes(editable=True, column=MOD_ATTR), text=MOD_ATTR))
        treeview.append_column(Gtk.TreeViewColumn("LinkAttr", CellRendererAttributes(editable=True, column=MOD_LINK_ATTR), text=MOD_LINK_ATTR))
        treeview.append_column(Gtk.TreeViewColumn("Data Size", CellRendererDataSize(), model_data=MOD_DATA))
        model.set_sort_func(MOD_DATA, CellRendererDataSize.compare, None)
        dctlinkrenderer = Gtk.CellRendererText(editable=True)
        dctlinkrenderer.set_alignment(1.0, 0)
        dctlinkrenderer.connect('edited', self.on_dctlink_edit)
        treeview.append_column(Gtk.TreeViewColumn("DCT Link", dctlinkrenderer, text=MOD_DCTLINK))
        treeview.append_column(Gtk.TreeViewColumn("Modified", Gtk.CellRendererText(), text=MOD_MODIFIED))
        treeview.append_column(Gtk.TreeViewColumn("Accessed", Gtk.CellRendererText(), text=MOD_ACCESSED))
        treeview.append_column(Gtk.TreeViewColumn("", Gtk.CellRendererPixbuf()))
        scrolltree = Gtk.ScrolledWindow()
        scrolltree.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        scrolltree.add(treeview)

        for i, column in enumerate(treeview.get_columns()):
            if column.get_title() == "": continue
            column.set_clickable(True)
            column.set_sort_indicator(True)
            column.set_sort_column_id(i)
            column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            column.set_resizable(True)
            column.set_reorderable(True)

        fileview = Hexview()
        self.fileview = fileview
        hbox.pack_start(scrolltree, True, True, 0)
        hbox.pack_start(fileview, False, False, 0)

        if filepath is not None: self.populate_store_with_file(model, filepath, fmt)
        
        treeview.expand_all()
        treeview.columns_autosize()
        treeview.set_headers_clickable(True)
        # treeview.set_grid_lines(3)

        self.fileview.set_data(None)
        treeview.set_cursor(0)

        self.dsk_progress_6030.set_show_text(True)
        self.dsk_progress_4048.set_show_text(True)
        self.update_dsk_progress()

        self.add(vbox)
        self.set_default_size(1260, 700)
        self.show_all()

    def populate_store_with_file(self, store, filepath, fmt = None):
        test = Attributes.from_string("AC")
        if fmt is None:
            match filepath.split(".")[-1:][0].lower():
                case "dsk" | "img": fmt = "dsk"
                case "9trk": fmt = "9trk"
                case "dp": fmt = "dp"
        match fmt:
            case "dsk":
                disk_bytes = None
                with open(filepath, 'rb') as file:
                    disk_bytes = file.read()
                    if len(disk_bytes) % 512 != 0:
                        raise Exception("Unexpected disk length")
                dsk = Disk(disk_bytes)
                # Add special files
                boot_sector_data = dsk.disk_bytes[0:1024].tobytes()
                if len(boot_sector_data.replace(b'\x00', b'').replace(b'\xFF', b'')) > 0:
                    self.append_to_model(store, None, {
                        MOD_NAME: "[HIPBOOT]",
                        MOD_DATA: boot_sector_data
                    })
                for x in [2,3,5,7,8,9,10,11,12,13,14]:
                    data = dsk.disk_bytes[512*x:512*x+512].tobytes()
                    
                    if len(data.replace(b'\xDB\x6D', b'')) > 0 and len(data.replace(b'\x00\x00', b'')) > 0:
                        self.append_to_model(store, None, {
                            MOD_NAME: f"[BLOCK{x}]",
                            MOD_DATA: data
                        })
                
                # Attempt to setup frame_size
                diskinfo_frame_size = dsk.get_block_words(3)[6]
                other_frame_size = dsk.get_block_words(7)[17]
                if diskinfo_frame_size != 0:
                    if diskinfo_frame_size != other_frame_size:
                        print(f"WARNING: dsk frame_size(s) don't match! Using first one {diskinfo_frame_size} != {other_frame_size}")
                    self.frame_size_control.set_value(diskinfo_frame_size)
                elif other_frame_size != 0:
                    print(f"WARNING: dsk info frame_size is zero?!?")
                    self.frame_size_control.set_value(other_frame_size)
                else:
                    print(f"WARNING: dsk frame_size(s) are zero?!? Using 5.")
                    self.frame_size_control.set_value(5)
                
                # Add filesystem from "SYS.DR"
                self.populate_store_with_dsk(store, dsk)
            case "9trk":
                with open(filepath, 'rb') as file:
                    self.populate_store_with_9trk(store, Magtape(file.read()))
            case "dp":
                with open(filepath, 'rb') as file:
                    self.populate_store_with_dp(store, file.read())
            case _:
                print("WARNING: DIDNT LOAD FILE")

    def populate_store_with_9trk(self, store, magtape):
        for tape_id, tape_data in magtape.files.items():
            treeiter = self.append_to_model(store, None, {
                MOD_NAME: f"FILE{tape_id:02}",
                MOD_DATA: tape_data,
            })
            if tape_data[0] == 0xFF:
                # When this happens, it appears to be a DUMP file
                try:
                    df = Dumpfile(tape_data)
                    df_files = df.get_files()
                    treeiter = self.append_to_model(store, None, {
                        MOD_NAME: f"DUMPFILE{tape_id:02}.DR",
                        MOD_ATTR: "YD",
                    })
                    for ufd, data in df_files:
                        self.append_to_model(store, treeiter, {
                                MOD_NAME: ufd.get_safe_filename(),
                                MOD_ATTR: f"{ufd.get_file_attributes()}",
                                MOD_MODIFIED: f"{ufd.get_modified_datetime():%x %H:%M}",
                                MOD_ACCESSED: f"{ufd.get_accessed_datetime():%x}",
                                MOD_DATA: data,
                                MOD_DCTLINK: ufd.get_dct_link(),
                                MOD_LINK_ATTR: f"{ufd.get_link_attributes()}",
                        })
                except Exception as ex:
                    print(f"WARNING: Dumpfile decoding failed, was it really a dump? 9TKFILE {tape_id}: {ex}")
        pass

    def populate_store_with_dsk(self, store, dsk, directory=6, node=None):
        address = directory
        block_words = dsk.get_block_words(address)
        for i in range(256):
            if block_words[i] > 0:
                deb = dsk.get_block_words(block_words[i])
                entries = deb[0]
                if entries > 14: raise Exception("Unexpected number of entries")
                for e in range(entries):
                    ufd_start = (e*18)+1
                    ufd_end = ((e+1)*18)+1
                    ufd = UFD(deb[ufd_start:ufd_end])
                    if ufd.is_deleted(): continue
                    if ufd.get_safe_filename() == "SYS.DR": continue
                    if ufd.get_safe_filename() == "MAP.DR": continue
                    # Skip showing "SYSTEM" files like "Device links"
                    # if ufd.get_safe_filename()[0] == '$': continue
                    if (ufd.is_file() or ufd.is_dir()) and not ufd.is_link():
                        data = dsk.get_file_bytes(ufd)
                        treeiter = self.append_to_model(store, node, {
                                MOD_NAME : ufd.get_safe_filename(),
                                MOD_ATTR : f"{ufd.get_file_attributes()}",
                                MOD_MODIFIED : f"{ufd.get_modified_datetime():%x %H:%M}",
                                MOD_ACCESSED : f"{ufd.get_accessed_datetime():%x}",
                                MOD_DATA : data,
                                MOD_DCTLINK : ufd.get_dct_link(),
                                MOD_LINK_ATTR: f"{ufd.get_link_attributes()}",
                            })
                    # Prevent Recursion (ufd.get_address() != address)
                    if ufd.is_dir() and not ufd.is_link() and ufd.get_address() != address:
                        self.populate_store_with_dsk(store, dsk, ufd.get_address(), treeiter)

    def populate_store_with_dp(self, store, data_bytes):
        df = Dumpfile(data_bytes)
        files = df.get_files(True)
        for ufd, data in files:
            _ = self.append_to_model(store, None, {
                    MOD_NAME: ufd.get_safe_filename(),
                    MOD_ATTR: f"{ufd.get_file_attributes()}",
                    MOD_MODIFIED: f"{ufd.get_modified_datetime():%x %H:%M}",
                    MOD_ACCESSED: f"{ufd.get_accessed_datetime():%x}",
                    MOD_DATA: data,
                    MOD_DCTLINK: ufd.get_dct_link(),
                    MOD_LINK_ATTR: f"{ufd.get_link_attributes()}",
                })

    def on_new_clicked(self, widget): self.get_application().add_window(DskWindow())

    def on_open_clicked(self, widget):
        dialog = Gtk.FileChooserDialog("Open", self, Gtk.FileChooserAction.OPEN, (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, 
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
            ))

        def add_filter(name, patterns):
            file_filter = Gtk.FileFilter()
            file_filter.set_name(name)
            for p in patterns: file_filter.add_pattern(p)
            dialog.add_filter(file_filter)
        
        add_filter("All supported files", ["*.dsk", "*.DSK", "*.img", "*.IMG", "*.9trk", "*.9TRK", "*.dp", "*.DP"])
        add_filter("DSK files", ["*.dsk", "*.DSK", "*.img", "*.IMG"])
        add_filter("9TRK files", ["*.9trk", "*.9TRK"])
        add_filter("DumP files", ["*.dp", "*.DP"])
        add_filter("Any file AS DSK", ["*"])
        add_filter("Any file AS 9TRK", ["*"])
        add_filter("Any file AS DumP", ["*"])

        filename = None
        fmt = None
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            filter_name = dialog.get_filter().get_name()
            match filter_name:
                case "Any file AS DSK": fmt = "dsk"
                case "Any file AS 9TRK": fmt = "9trk"
                case "Any file AS DumP": fmt = "dp"
        dialog.destroy()
        
        if filename is not None:
            self.get_application().add_window(DskWindow(filename, fmt))

        return True

    def on_saveas_clicked(self, widget):
        dialog = Gtk.FileChooserDialog("Save As DSK", self, Gtk.FileChooserAction.SAVE, (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, 
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
            ))
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name(".dsk")

        def add_filter(name, patterns):
            file_filter = Gtk.FileFilter()
            file_filter.set_name(name)
            for p in patterns: file_filter.add_pattern(p)
            dialog.add_filter(file_filter)
        
        add_filter("6030 DSK", ["*.dsk", "*.DSK", "*.img", "*.IMG"])
        add_filter("4048 DSK", ["*.dsk", "*.DSK", "*.img", "*.IMG"])
        # add_filter("9TRK files", ["*.9trk", "*.9TRK"]) # 6026
        # add_filter("DumP files", ["*.dp", "*.DP"])

        filename = None
        fmt = None
        response = dialog.run()

        try:
            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename()
                filter_name = dialog.get_filter().get_name()
                dialog.destroy()
                match filter_name:
                    case "6030 DSK":
                        new_dsk = self.new_dsk_from_model(self.model, "6030")
                        new_dsk_bytes = new_dsk.disk_bytes.tobytes()
                        with open(filename, 'wb') as file: file.write(new_dsk_bytes)
                    case "4048 DSK":
                        new_dsk = self.new_dsk_from_model(self.model, "4048")
                        new_dsk_bytes = new_dsk.disk_bytes.tobytes()
                        with open(filename, 'wb') as file: file.write(new_dsk_bytes)
                    case _:
                        raise Exception("WHAT!?!")
                print(f"File Saved: {filename}")
        except Exception as e:
            print(f"Save Failed: {e}")
            msgbox = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=f"Save Failed:\n\n{e}")
            msgbox.run()
            msgbox.destroy()
        finally:
            dialog.destroy()

        return True
    
    def on_tree_selection_changed(self, widget):
        model, treeiter = widget.get_selected()
        if treeiter is not None:
            self.fileview.set_data(model[treeiter][MOD_DATA])

    def on_drag_data_get(self, widget, drag_context, data, info, time):
        model, treeiter = widget.get_selection().get_selected()
        
        def get_with_children(iter):
            parent_data = model[iter][:]
            children_data = []
            child_iter = model.iter_children(iter)
            while child_iter is not None:
                children_data.append(get_with_children(child_iter))
                child_iter = model.iter_next(child_iter)
            return (parent_data, children_data)

        match info:
            case 0: # STRING
                # if model[treeiter][MOD_DATA] is not None:
                #     s = model[treeiter][MOD_DATA].decode("utf8")
                #     data.set_text(s, len(s))
                pass
            case 1: # URI
                # ?
                pass
            case 2: # URIs
                # data.set_uris(["uri://1", "uri://2"])
                pass
            case 42069: # SAME_WIDGET
                pass
            case 69420: # OTHER_WIDGET
                data.set(data.get_target(), 8, pickle.dumps(get_with_children(treeiter)))
            case _:
                pass

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        def add_uri_file(uri, model, parent):
            path = uri_to_path(uri)
            data = None
            with open(path, 'rb') as file: data = file.read()
            self.append_to_model(model, parent, {
                MOD_NAME: os.path.basename(path).upper(),
                MOD_DATA: data,
            })
        match info:
            case 0: # STRING
                # print(f"STRING: {data.get_text()}")
                pass
            case 1 | 2: # URI, URIs
                # print(f"URIs: {data.get_uris()}")
                model = widget.get_model()
                bx, by = widget.convert_widget_to_bin_window_coords(x, y)
                path_at_pos = widget.get_path_at_pos(bx, by)
                parent = None
                if path_at_pos is not None:
                    parent = model.get_iter(path_at_pos[0])
                    attr = Attributes.from_string(model[parent][:][MOD_ATTR])
                    while attr.is_file() and parent is not None:
                        parent = model.iter_parent(parent)
                        if parent is None: break;
                        attr = Attributes.from_string(model[parent][:][MOD_ATTR])
                for uri in data.get_uris():
                    # FIXME!!! Check if uri is directory
                    add_uri_file(uri, model, parent)
                self.update_dsk_progress()
                return Gtk.drag_finish(drag_context, True, False, time)
            case 42069: # SAME_WIDGET
                model, treeiter = widget.get_selection().get_selected()

                bx, by = widget.convert_widget_to_bin_window_coords(x, y)
                path_at_pos = widget.get_path_at_pos(bx, by)

                parent = None
                if path_at_pos is not None:
                    selection_path = model.get_path(treeiter)
                    drop_path = path_at_pos[0]
                    
                    # Don't drop on self or children
                    if drop_path == selection_path or drop_path.is_descendant(selection_path):
                        return

                    parent = model.get_iter(drop_path)

                    attr = Attributes.from_string(model[parent][:][MOD_ATTR])
                    while attr.is_file() and parent is not None:
                        parent = model.iter_parent(parent)
                        if parent is None: break
                        attr = Attributes.from_string(model[parent][:][MOD_ATTR])

                def get_with_children(iter):
                    parent_data = model[iter][:]
                    children_data = []
                    child_iter = model.iter_children(iter)
                    while child_iter is not None:
                        children_data.append(get_with_children(child_iter))
                        child_iter = model.iter_next(child_iter)
                    return (parent_data, children_data)
                def load_drop_nodes(iter, result_tuple):
                    rt_data = result_tuple[0]
                    if rt_data is None: return
                    next_iter = model.append(iter, rt_data)
                    for next_tuple in result_tuple[1]:
                        load_drop_nodes(next_iter, next_tuple)
                load_drop_nodes(parent, get_with_children(treeiter))

                self.update_dsk_progress()
                return Gtk.drag_finish(drag_context, True, True, time)
            case 69420: # OTHER_WIDGET
                result = pickle.loads(data.get_data())
                model = widget.get_model()
                bx, by = widget.convert_widget_to_bin_window_coords(x, y)
                path_at_pos = widget.get_path_at_pos(bx, by)
                parent = None
                if path_at_pos is not None:
                    parent = model.get_iter(path_at_pos[0])
                    attr = Attributes.from_string(model[parent][:][MOD_ATTR])
                    while attr.is_file() and parent is not None:
                        parent = model.iter_parent(parent)
                        if parent is None: break;
                        attr = Attributes.from_string(model[parent][:][MOD_ATTR])

                def load_drop_nodes(iter, result_tuple):
                    rt_data = result_tuple[0]
                    if rt_data is None: return
                    next_iter = model.append(iter, rt_data)
                    for next_tuple in result_tuple[1]:
                        load_drop_nodes(next_iter, next_tuple)

                load_drop_nodes(parent, result)
                self.update_dsk_progress()
                return Gtk.drag_finish(drag_context, True, False, time)

    def on_row_changed(self, model, path, iter):
        self.update_dsk_progress()

    def on_row_inserted(self, model, path, iter):
        self.update_dsk_progress()

    def on_row_deleted(self, model, path):
        self.update_dsk_progress()

    def on_treeview_keypress(self, widget, event):
        state = event.get_state()
        ctrl_shift = Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK
        # DELETE
        if event.keyval == Gdk.KEY_Delete:
            self.on_delete()
            return True
        # NEW FOLDER
        if event.keyval == Gdk.KEY_N and (state & ctrl_shift) == ctrl_shift:
            self.on_new_folder()
            return True
        return False

    def on_treeview_buttonpress(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_SECONDARY:
            path_at_pos = widget.get_path_at_pos(event.x, event.y)
            if path_at_pos is not None: self.treeview.set_cursor(path_at_pos[0])
            else: self.treeview.get_selection().unselect_all()
            self.treeview_context_menu.show_all()
            self.treeview_context_menu.popup(None, None, None, None, Gdk.BUTTON_SECONDARY, event.time)
            return True

    def on_new_folder(self, *args):
        model, treeiter = self.treeview.get_selection().get_selected()
        while treeiter is not None:
            if Attributes.from_string(model[treeiter][:][MOD_ATTR]).is_dir():
                break
            else:
                treeiter = model.iter_parent(treeiter)
        treeiter = self.append_to_model(model, treeiter, {MOD_ATTR: "YD"})
        self.update_dsk_progress()
        # Select/Scroll to the new folder
        self.treeview.set_cursor(model.get_path(treeiter))
    
    def on_delete(self, *args):
        model, treeiter = self.treeview.get_selection().get_selected()
        if treeiter is not None:
            model.remove(treeiter)
            self.update_dsk_progress()

    def on_swab(self, *args):
        model, treeiter = self.treeview.get_selection().get_selected()
        if treeiter is not None:
            data = bytearray(model[treeiter][MOD_DATA])
            for i in range(len(data) // 2):
                tmp = data[i*2+0]
                data[i*2+0] = data[i*2+1]
                data[i*2+1] = tmp
            model[treeiter][MOD_DATA] = data
            self.fileview.set_data(data)
            self.update_dsk_progress()

    def on_name_edit(self, renderer, path, new_text):
        if len(new_text) > 1 and new_text[0] == "[":
            self.model[path][MOD_NAME] = new_text.upper()
        else:
            parts = new_text.upper().split('.')
            basename = "".join(re.findall("[A-Z\\$0-9]", parts[0]))[0:10]
            if len(basename) < 1: return # Can't allow empty file name
            self.model[path][MOD_NAME] = basename + "."
            if len(parts) > 1:
                exname = "".join(re.findall("[A-Z\\$0-9]", parts[1]))[0:2]
                self.model[path][MOD_NAME] = basename + "." + exname

    def on_dctlink_edit(self, renderer, path, new_text):
        # FIXME: VALIDATE INPUT BETTER
        self.model[path][MOD_DCTLINK] = int(new_text, base=0)

    def on_framesize_changed(self, widget):
        self.update_dsk_progress()

    def update_dsk_progress(self):
        frame_size = int(self.frame_size_control.get_value())
        dsk_progress_value = frame_size + 1
        
        def calculate(model, path, treeiter):
            nonlocal dsk_progress_value
            if len(model[treeiter][:][MOD_NAME]) > 0 and model[treeiter][:][MOD_NAME][0] == '[':
                return False # Skip "Reserved" pygdf file(s)
            if Attributes.from_string(model[treeiter][:][MOD_ATTR]).is_dir():
                dsk_progress_value += frame_size + 1
            else:
                data_size = len(model[treeiter][:][MOD_DATA]) if model[treeiter][:][MOD_DATA] is not None else 0
                dsk_progress_value += (data_size // 512)
            return False
        self.model.foreach(calculate)

        fraction_6030 = dsk_progress_value / (616-16)
        self.dsk_progress_6030.set_fraction(fraction_6030)
        self.dsk_progress_6030.set_text(f"6030 Disk Usage\nEstimate: ({dsk_progress_value}/{616-16})\n{fraction_6030:.0%}")

        fraction_4048 = dsk_progress_value / (12180-17)
        self.dsk_progress_4048.set_fraction(fraction_4048)
        self.dsk_progress_4048.set_text(f"4048 Disk Usage\nEstimate: ({dsk_progress_value}/{12180-17})\n{fraction_4048:.0%}")

    def new_dsk_from_model(self, model, dsk_type="6030"):
        match dsk_type:
            case "6030" | "4048": pass
            case _: Exception("Unexpected dsk type passed")
        
        dsk = None
        match dsk_type:
            case "6030": dsk = Disk(b'\x00'*512*616, 'big')
            case "4048": dsk = Disk(b'\x00'*512*12180, 'big')
            case _: raise Exception("Unexpected dsk type passed")

        # ADD RAW SYSTEM SECTORS AS NEEDED
        # Block 0,1 - HIPBOOT (BOOT SECTOR)
        # Block 2 - Unused
        # Block 3 - Pointers ("DiskInfo") (This will be modified slightly later)
        # Block 5 - Unused
        # Block 7 - SWAP FIB POINTERS
        # Block 8,9,10,11,12,13,14 - "UNUSED"
        treeiter = model.get_iter_first()
        while treeiter is not None:
            data = model[treeiter][MOD_DATA]
            if data is not None and len(data) > 0:
                if model[treeiter][MOD_NAME] == "[HIPBOOT]":
                    if len(data) <= 1024:
                        dsk.disk_bytes[0:len(data)] = data
                    else:
                        raise Exception("Special block is too big")
                else:
                    for i in range(2, 15):
                        if i == 4: continue
                        if model[treeiter][MOD_NAME] == f"[BLOCK{i}]":
                            if len(data) <= 512:
                                dsk.disk_bytes[(i*512)+0:(i*512)+len(data)] = data
                                if i >= 6: dsk.set_map_block_bit(i)
                            else:
                                raise Exception("Special block is too big")
            treeiter = model.iter_next(treeiter)
        
        # Block 3 - Pointers ("DiskInfo")
        dsk.set_word(3, 0, 2) # REV 5
        match dsk_type:
            case "6030":
                dsk.set_word(3, 2, 1) # Tracks
                dsk.set_word(3, 3, 8) # Sectors/Track
                dsk.set_word(3, 5, 610) # NumOfBlocks (Technically words 4+5)
                dsk.set_word(3, 7, 2) # DiskType
            case "4048":
                dsk.set_word(3, 2, 10) # Tracks
                dsk.set_word(3, 3, 6) # Sectors/Track
                dsk.set_word(3, 5, 12174) # NumOfBlocks (Technically words 4+5)
                dsk.set_word(3, 7, 0) # DiskType (Is this really 0?)
            case _: raise Exception("Unexpected dsk type passed")
        dsk.set_disk_frame_size(int(self.frame_size_control.get_value()))
        # set_disk_frame_size already fixes the checksum
        # dsk.fix_diskinfo_checksum()

        # Block 4 - Remap Area
        dsk.set_word(4, 0, 4)
        match dsk_type:
            case "6030": dsk.set_word(4, 2, 616)
            case "4048": dsk.set_word(4, 2, 12180)
            case _: raise Exception("Unexpected dsk type passed")

        # Block 6 - SYS.DR
        dsk.set_map_block_bit(6)
        
        # Block 7 - SWAP FIB POINTERS
        # FrameSize compat/mirror (word 17) is updated from Block3 set_disk_frame_size()

        # Block 15+ - MAP.DR (bigger disks need more then one block)
        for i in range((dsk.get_word(3, 5) // 8192) + 1):
            dsk.set_map_block_bit(15 + i)

        # ALLOCATE ROOT SYS.DR FRAMES
        dsk.add_frames_to_sysdr_block(6)

        def add_files_to_sysdr(sys_block_id, sysdr_iter):
            while sysdr_iter is not None:
                model_data = model[sysdr_iter][:]

                # Check for file exclusions
                if model_data[MOD_NAME][0] == '[':
                    pass # Skipping pydgf 'special' files
                else:
                    # Create UFD from model_data
                    ufd = UFD.new()
                    ufd.set_safe_filename(model_data[MOD_NAME])
                    ufd.set_file_attributes(model_data[MOD_ATTR])
                    ufd.set_modified_datetime_from_string(model_data[MOD_MODIFIED])
                    ufd.set_accessed_datetime_from_string(model_data[MOD_ACCESSED])
                    if model_data[MOD_DATA] is not None: ufd.set_total_byte_count(len(model_data[MOD_DATA]), model_data[MOD_ATTR])
                    ufd.set_dct_link(model_data[MOD_DCTLINK])

                    # Add file/directory data to disk
                    afrv = dsk.add_file(sys_block_id, ufd, model_data[MOD_DATA])

                    if ufd.is_dir():
                        newsysdr_iter = model.iter_children(sysdr_iter)
                        add_files_to_sysdr(afrv, newsysdr_iter)
                
                sysdr_iter = model.iter_next(sysdr_iter)

        # ADD FILES
        treeiter = model.get_iter_first()
        add_files_to_sysdr(6, treeiter)

        return dsk

    def append_to_model(self, model, parent, data):
        return model.append(parent, [
            data[MOD_NAME] if MOD_NAME in data else "",
            data[MOD_ATTR] if MOD_ATTR in data else "",
            data[MOD_LINK_ATTR] if MOD_LINK_ATTR in data else "",
            data[MOD_DATA] if MOD_DATA in data else None,
            data[MOD_DCTLINK] if MOD_DCTLINK in data else 0,
            data[MOD_MODIFIED] if MOD_MODIFIED in data else "",
            data[MOD_ACCESSED] if MOD_ACCESSED in data else "",
        ])