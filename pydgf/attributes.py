import re
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject

class Attributes:
    def __init__(self, attr_word=0):
        self.attr_word = attr_word

    def __str__(self):
        attr_string = ''
        # Attributes/Characteristics
        if self.attr_word & 0x8000 > 0: attr_string += 'R' # ATTR: Read Protected
        if self.attr_word & 0x4000 > 0: attr_string += 'A' # ATTR: Change Attribute Protected
        if self.attr_word & 0x2000 > 0: attr_string += 'S' # ATTR: Saved File
        if self.attr_word & 0x1000 > 0: attr_string += 'L' # CHAR: Link Entry
        if self.attr_word & 0x0800 > 0: attr_string += 'T' # CHAR: Partition Entry
        if self.attr_word & 0x0400 > 0: attr_string += 'Y' # CHAR: Directory Entry
        if self.attr_word & 0x0200 > 0: print("WARNING: Unsupported Attribute 0x0200 (Link Resolution)") # Temporary Link Resolution (Doesn't have a display char)
        if self.attr_word & 0x0100 > 0: attr_string += 'N' # ATTR: No Resolution (Cannot link to this)
        if self.attr_word & 0x0080 > 0: attr_string += 'I'; print("WARNING: Unsupported Attribute 0x0080 (Direct I/O ONLY)") # CHAR: Direct I/O ONLY ('019-000048-04' says this is an 'I')
        if self.attr_word & 0x0040 > 0: attr_string += '&' # ATTR: User1
        if self.attr_word & 0x0020 > 0: attr_string += '?' # ATTR: User2
        if self.attr_word & 0x0010 > 0: print("WARNING: Unsupported Attribute 0x0010 (?UNKNOWN?)") # (Doesn't have a display char)
        if self.attr_word & 0x0008 > 0: attr_string += 'C' # CHAR: Contiguous File
        if self.attr_word & 0x0004 > 0: attr_string += 'D' # CHAR: Random File
        if self.attr_word & 0x0002 > 0: attr_string += 'P' # ATTR: Permanent File
        if self.attr_word & 0x0001 > 0: attr_string += 'W' # ATTR: Write Protected
        if attr_string.__contains__("C") and attr_string.__contains__("D"): print("WARNING: Impossible attribute combination!")
        if attr_string.__contains__("L") and attr_string.__contains__("C"): print("WARNING: Impossible attribute combination!")
        if attr_string.__contains__("L") and attr_string.__contains__("D"): print("WARNING: Impossible attribute combination!")
        return attr_string

    @classmethod
    def from_string(cls, attr_string):
        attr_string = attr_string.upper()
        attr_word = 0
        if attr_string.__contains__('R'): attr_word += 0x8000
        if attr_string.__contains__('A'): attr_word += 0x4000
        if attr_string.__contains__('S'): attr_word += 0x2000
        if attr_string.__contains__('L'): attr_word += 0x1000
        if attr_string.__contains__('T'): attr_word += 0x0800
        if attr_string.__contains__('Y'): attr_word += 0x0400
        #
        if attr_string.__contains__('N'): attr_word += 0x0100
        if attr_string.__contains__('I'): attr_word += 0x0080
        if attr_string.__contains__('&'): attr_word += 0x0040
        if attr_string.__contains__('?'): attr_word += 0x0020
        #
        if attr_string.__contains__('C'): attr_word += 0x0008
        if attr_string.__contains__('D'): attr_word += 0x0004
        if attr_string.__contains__('P'): attr_word += 0x0002
        if attr_string.__contains__('W'): attr_word += 0x0001
        invalid_string = re.sub("[RASLTYNI&?CDPW]", "", attr_string)
        if len(invalid_string) > 0: print(f"WARNING: Attempted to create a Attrbiutes with invalid data({invalid_string}) {attr_string}")

        return cls(attr_word)

    def is_file(self):
        if self.is_dir() or self.is_link() or self.__str__().__contains__("T"): return False
        return True

    def is_dir(self):
        return self.__str__().__contains__("Y")

    def is_link(self):
        return self.__str__().__contains__("L")

    def is_contiguous(self):
        return self.__str__().__contains__("C")

    def is_random(self):
        return self.__str__().__contains__("D")

    def is_sequential(self):
        if self.is_random(): return False
        if self.is_contiguous(): return False
        return True

    def is_permanent(self):
        return self.__str__().__contains__("P")

class CellEditableAttributes(Gtk.ListBox, Gtk.CellEditable):
    __gtype_name__ = 'CellEditableAttributes'
    __gproperties__ = {'editing-canceled' : (bool, '', '', False, GObject.PARAM_READWRITE)}

    def __init__(self, *args):
        super().__init__()
        self.attr = Attributes()
        letters = [
                "R: Read Protected",
                "A: Change Attribute Protected",
                "S: Saved File",
                "L: Link Entry",
                "T: Partition Entry",
                "Y: Directory Entry",
                # " : Link Resolution (Can't set this)",
                "N: No Resolution",
                "I: Direct I/O",
                "&: User1",
                "?: User2",
                # " : UNKNOWN (Can't set this)",
                "C: Contiguous File",
                "D: Random File",
                "P: Permanent File",
                "W: Write Protected",
            ]
        self.checkboxes = []
        for index, attr_letter in enumerate(letters):
            cb = Gtk.CheckButton(attr_letter, False)
            self.checkboxes.append(cb)
            self.add(self.checkboxes[index])

    def do_editing_done(self):
        attr_string = ""
        for index in range(len(self.checkboxes)):
            if self.checkboxes[index].get_active():
                attr_string += self.checkboxes[index].get_label()[0:1]
        self.model[self.path][self.column] = attr_string
        self.remove_widget()
    
    def do_start_editing(self, event): pass
    def do_remove_widget(self): pass

    def get_text(self): return self.attr.__str__()
    def set_text(self, attr_string):
        for index in range(len(self.checkboxes)):
            if attr_string.__contains__(self.checkboxes[index].get_label()[0:1]):
                self.checkboxes[index].set_active(True)

class CellRendererAttributes(Gtk.CellRendererText):
    __gtype_name__ = 'CellRendererAttributes'
    def __init__(self, column, editable = True):
        super().__init__(editable = editable)
        self.column = column
    def do_start_editing(self, event, treeview, path, background_area, cell_area, flags):
        if not self.get_property('editable'): return
        editor = CellEditableAttributes()
        editor.set_text(self.props.text)
        editor.model = treeview.get_model()
        editor.path = path
        editor.column = self.column
        editor.show_all()
        return editor