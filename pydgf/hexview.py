import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GdkPixbuf
import cairo

# FIXME: Pretty sure this view breaks on large files

class Hexview(Gtk.ScrolledWindow):
    def __init__(self):
        super().__init__()
        super().set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.mouse_position = None
        self.min_address_width = 4
        self.padding = 16

        self.hex_control = Gtk.DrawingArea()
        self.hex_control.connect("draw", self.on_draw)
        self.hex_control.add_events(
            # Gdk.EventMask.FOCUS_CHANGE_MASK
            # Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK 
            )
        self.hex_control.connect("button-press-event", self.on_button_press)
        self.hex_control.connect("motion-notify-event", self.on_motion_notify)
        self.hex_control.set_size_request(0, -1)

        self.context_menu = Gtk.Menu()
        cm_copy_hex = Gtk.MenuItem("Copy Hex String")
        cm_copy_hex.connect("activate", self.on_copy_hex)
        self.context_menu.append(cm_copy_hex)
        cm_copy_string = Gtk.MenuItem('Copy String (without NUL)')
        cm_copy_string.connect("activate", self.on_copy_string_without_nul)
        self.context_menu.append(cm_copy_string)

        super().add(self.hex_control)

    def get_glyph_size(self):
        fctx = super().get_pango_context()
        fontdesc = fctx.get_font_description()
        metrics = fctx.get_metrics(fontdesc)
        return (metrics.approximate_digit_width / Pango.SCALE), (metrics.height / Pango.SCALE)

    def on_draw(self, widget, context):
        clip_extents = context.clip_extents()

        style_context = widget.get_style_context()
        style_normal_color = style_context.get_color(Gtk.StateFlags.NORMAL)
        style_normal_background_color = style_context.get_background_color(Gtk.StateFlags.NORMAL)
        style_prelight_color = style_normal_background_color # style_context.get_color(Gtk.StateFlags.PRELIGHT)
        style_prelight_background_color = style_normal_color # style_context.get_background_color(Gtk.StateFlags.PRELIGHT)

        char_width, line_height = self.get_glyph_size()

        context.set_source_rgb(style_normal_background_color.red, style_normal_background_color.green, style_normal_background_color.blue)
        context.rectangle(*clip_extents)
        context.fill()

        fontdesc = super().get_pango_context().get_font_description()
        context.set_font_size(fontdesc.get_size() / Pango.SCALE)
        context.select_font_face(fontdesc.get_family(), cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

        def draw_line(str, y_offset):
            # Optimize with clip bounds
            if y_offset < clip_extents[1]: return
            if y_offset > clip_extents[3] + line_height: return
            # Draw each letter
            for i, c in enumerate(str):
                context.set_source_rgb(style_normal_color.red, style_normal_color.blue, style_normal_color.green)
                context.move_to(i * char_width + self.padding, y_offset)
                context.show_text(c)
                context.stroke()

        if self.data is None:
            self.hex_control.set_size_request(0, -1)
            return False
    

        address_width = len(hex(len(self.data) - 1)[2:])
        if address_width < self.min_address_width: address_width = self.min_address_width

        self.hex_control.set_size_request((char_width * (70 + address_width)) + self.padding*2, (len(self.data)//16 + 3) * line_height)
        y_offset = line_height
        draw_line(f"ADDR{' '*(address_width-4)} | 00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F | 0123456789ABCDEF", y_offset)
        y_offset += line_height
        draw_line(f"{'-'*address_width}-+--------------------------------------------------+-----------------", y_offset)
        for line in range(((len(self.data)-1)//16)+1):
            y_offset += line_height

            # Optimize with clip bounds
            if y_offset < clip_extents[1]: continue
            if y_offset > clip_extents[3] + line_height: continue

            addr = f"{(line * 16):0{address_width}X}"
            hex_str = " "
            ascii_str = ""
            for char_index in range(16):
                data_index = line * 16 + char_index
                if data_index < len(self.data):
                    hex_str += f"{(self.data[data_index]):02X} "
                    if self.data[data_index] == 0: ascii_str += ' '
                    else: ascii_str += chr(self.data[data_index])
                else:
                    hex_str += "   "
                    ascii_str += " "
                if char_index == 7:hex_str += " "

            draw_line(f"{addr} |{hex_str}| {ascii_str}", y_offset)

        # Draw mouse cursor
        # if self.mouse_position is not None:
        #     mc_x, mc_y = self.mouse_position
        #     mc_x -= mc_x % char_width
        #     mc_y -= mc_y % line_height
        #     context.set_source_rgb(1,0,1)
        #     context.rectangle(mc_x, mc_y, char_width, line_height)
        #     context.stroke()

        x_offsets = [
            [0,1,51], # 0
            [3,4,52], # 1
            [6,7,53], # 2
            [9,10,54], # 3
            [12,13,55], # 4
            [15,16,56], # 5
            [18,19,57], # 6
            [21,22,58], # 7
            [25,26,59], # 8
            [28,29,60], # 9
            [31,32,61], # A
            [34,35,62], # B
            [37,38,63], # C
            [40,41,64], # D
            [43,44,65], # E
            [46,47,66], # F
        ]

        # Draw prelight text
        if self.mouse_position is not None:
            mc_x, mc_y = self.mouse_position

            if mc_y >= line_height * 2:
                offset = (mc_x - self.padding - (address_width+3) * char_width) // char_width
                y = mc_y - (mc_y % line_height)
                data_y = int((y // line_height) - 2)
                for i, o in enumerate(x_offsets):
                    data_offset = data_y * 16 + i
                    if data_offset < len(self.data) and offset in o:
                        # Backgrounds of Hex/String
                        context.set_source_rgb(style_prelight_color.red, style_prelight_color.blue, style_prelight_color.green)
                        x = self.padding + (address_width + 3 + o[0])*char_width
                        context.rectangle(x, y, char_width*2, line_height)
                        x = self.padding + (address_width + 3 + o[2])*char_width
                        context.rectangle(x, y, char_width, line_height)
                        context.fill()
                        # Redo Data
                        data = self.data[data_offset]
                        # Redo Hex
                        context.set_source_rgb(style_prelight_background_color.red, style_prelight_background_color.blue, style_prelight_background_color.green)
                        x = self.padding + (address_width + 3 + o[0])*char_width
                        hex_str = f"{data:02X}"
                        context.move_to(x, y + line_height)
                        context.show_text(hex_str[0])
                        context.move_to(x + char_width, y + line_height)
                        context.show_text(hex_str[1])
                        # Redo Text
                        if data != 0:
                            x = self.padding + (address_width + 3 + o[2])*char_width
                            context.move_to(x, y + line_height)
                            context.show_text(chr(data))
                        context.stroke()

        return False
    
    def on_button_press(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_SECONDARY:
            self.context_menu.show_all()
            self.context_menu.popup(None, None, None, None, Gdk.BUTTON_SECONDARY, event.time)
            return True

    def on_motion_notify(self, widget, event):
        char_width, line_height = self.get_glyph_size()
        def invalidate(y): self.hex_control.queue_draw_area(0, y - (y % line_height) - line_height, char_width * 76 + self.padding * 2, line_height * 3)
        # Invalidate old position
        if self.mouse_position is not None: invalidate(self.mouse_position[1])
        # Update position
        self.mouse_position = event.x, event.y
        # Invalidate new position as well
        if self.mouse_position is not None: invalidate(self.mouse_position[1])

    def on_copy_hex(self, *args):
        if self.data is not None:
            txt = ""
            for i, c in enumerate(self.data):
                txt += f"{c:02X}"
                if i % 16 == 15: txt += '\n'
                else: txt += ' '
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(txt, len(txt))

    def on_copy_string_without_nul(self, *args):
        if self.data is not None:
            txt = ""
            for c in self.data:
                if c > 0: txt += chr(c)
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(txt, len(txt))

    def set_data(self, data):
        self.data = data
        self.hex_control.queue_draw()
