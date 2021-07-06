# OBECA - Open Broadcast Edge Cache Appliance
# GUI 
#
# Copyright (C) 2021 Österreichische Rundfunksender GmbH & Co KG
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import gi
import os
gi.require_version('Gtk', '3.0') 
from gi.repository import Gtk, Gdk, GLib
import sys
import math
import requests
import threading
import time
import struct
import psutil
import vlc
import webbrowser

rp_api_url = 'http://localhost:3010/rp-api/'
gw_api_url = 'http://localhost:3020/gw-api/'

gain_step = 2.0

main_loop = GLib.MainLoop()

class OfrWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="OFR")
        self.sr = self.fc = 0
        self.mode = 'rp';
        self.state = 'searching'
        self.mch_info = {}
        self.selected_mch = 0
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_property("hexpand", True)
        self.set_property("vexpand", True)

        self.files_store = Gtk.ListStore(int, str, int)
        self.files_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.add( self.main_box )
        self.add_top_box(self.main_box)
        self.rp_screen = self.add_receiver_screen()
        self.gw_screen = self.add_gateway_screen()
        self.rp_screen.hide()
        self.gw_screen.hide()
        self.main_box.add( self.rp_screen )
        self.main_box.add( self.gw_screen )

    def gain_down( self, foo, bar ):
        print("Decrease gain")
        requests.put(rp_api_url + 'sdr_params', json = 
            {
                'gain': self.gain_val - gain_step,
                'frequency': self.fc,
                'antenna': self.antenna_val,
                'sample_rate': self.sr,
                'filter_bw': self.filter_bw_val
            }, verify=False)
    def gain_up( self, foo, bar ):
        print("Increase gain")
        requests.put(rp_api_url + 'sdr_params', json = 
            {
                'gain': self.gain_val + gain_step,
                'frequency': self.fc,
                'antenna': self.antenna_val,
                'sample_rate': self.sr,
                'filter_bw': self.filter_bw_val
            }, verify=False)

    def play_service( self, widget, service ):
        print("play " + service["service_tmgi"]);
        if service["stream_type"] == "UDP":
            player = vlc.MediaPlayer("rtp://@"+service["stream_mcast"])
            player.play() 
        else:
            webbrowser.open("http://localhost/application?s="+service["stream_tmgi"])

    def select_mode( self, widget, data ):
        self.mode = data
        if self.mode == 'rp':
            self.rp_screen.show()
            self.gw_screen.hide()
        elif self.mode == 'gw':
            self.rp_screen.hide()
            self.gw_screen.show()

    def select_mch_constellation( self, widget, data ):
        self.selected_mch = data

    def close_window( self, foo, bar ):
        self.destroy()
        main_loop.quit()

    def add_top_box( self, main_box ):
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        image = Gtk.Image(stock=Gtk.STOCK_DISCARD)
        close_btn = Gtk.Button(label="X")
        close_btn.set_property("height-request", 50)
        close_btn.set_property("width-request", 50)
        close_btn.connect("clicked", self.close_window, None)
        top_box.pack_start(close_btn, False, False, 0)
        title_label = Gtk.Label()
        title_label.set_markup("<big><b>OBECA </b></big><small>Open Broadcast Edge Cache Appliance</small>")
        title_label.set_margin_left(20)
        title_label.set_margin_right(20)
        top_box.pack_start(title_label, False, False, 10)

        app_btn = Gtk.Button(label="")
        app_label = app_btn.get_child()
        app_version = "<b>APPLICATION</b>"
        app_label.set_markup(app_version)
        app_btn.set_property("height-request", 50)
        top_box.pack_end(app_btn, False, True, 0)
        
        gw_btn = Gtk.Button(label="")
        gw_label = gw_btn.get_child()
        gw_version = "<b>GATEWAY   </b><small>" + os.popen('gw --version').read().rstrip() + "</small>"
        gw_label.set_markup(gw_version)
        gw_btn.set_property("height-request", 50)
        gw_btn.connect("clicked", self.select_mode, "gw");
        top_box.pack_end(gw_btn, False, True, 0)
        
        rec_btn = Gtk.Button(label="")
        rec_label = rec_btn.get_child()
        rec_version = "<b>RECEIVER   </b><small>" + os.popen('rp --version').read().rstrip() + "</small>"
        rec_label.set_markup(rec_version)
        rec_btn.set_property("height-request", 50)
        rec_btn.connect("clicked", self.select_mode, "rp");
        top_box.pack_end(rec_btn, False, True, 0)
        main_box.pack_start( top_box, False, False, 0 )

    def add_control( self, grid, row, label_text, value_control, unit_text, span = 1 ):
        label = Gtk.Label(label=label_text, xalign=0)
        grid.attach(label, 0, row, 1, 1)
        value_control.set_property("hexpand", True)
        value_control.set_property("valign", 3)
        grid.attach(value_control, 1, row, span, 1)
        unitlabel = Gtk.Label(label=unit_text, xalign=0)
        grid.attach(unitlabel, 2, row, 1, 1)

    def channel_box( self, label, sublabel ):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("box")
        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label.get_style_context().add_class("box-header")
        label_box.pack_start(label, True, True, 0)
        sublabel.get_style_context().add_class("box-header-right")
        box.sublabel = sublabel
        label_box.pack_start(sublabel, True, True, 0)
        box.pack_start(label_box, False, False, 0)
        box.constellation = Gtk.DrawingArea()
        box.constellation.connect("draw", self.draw_constellation)
        box.constellation.set_size_request(120, 160)
        box.constellation.pmch_data = ()
        box.pack_start(box.constellation, False, False, 0)
        controls = Gtk.Grid()
        controls.set_property("hexpand", True)
        controls.set_column_spacing(10)
        controls.set_row_spacing(5)
        vals_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vals_box.get_style_context().add_class("mt-1")
        pmch_bler_label = Gtk.Label(label="BLER", xalign=0)
        vals_box.pack_start(pmch_bler_label, True, True, 0)
        box.pmch_bler = Gtk.Label(label="-", xalign=1)
        box.pmch_bler.get_style_context().add_class("control-value-ber")
        vals_box.pack_start(box.pmch_bler, True, True, 0)
        pmch_ber_label = Gtk.Label(label="BER", xalign=0)
        vals_box.pack_start(pmch_ber_label, True, True, 0)
        box.pmch_ber = Gtk.Label(label="-", xalign=1)
        box.pmch_ber.get_style_context().add_class("control-value")
        vals_box.pack_start(box.pmch_ber, True, True, 0)
        box.pack_start(vals_box, False, False, 0)

        vals2_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.mcs = Gtk.Label(label="MCS -", xalign=0)
        vals2_box.pack_start(box.mcs, True, True, 0)
        rate = Gtk.Label(label="-", xalign=1)
        vals2_box.pack_start(rate, True, True, 0)
        box.pack_start(vals2_box, False, False, 0)
        return box


    def system_box( self ):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_property("hexpand", True)
        box.get_style_context().add_class("box")

        label = Gtk.Label(label="SYSTEM", xalign=0)
        label.get_style_context().add_class("box-header")
        box.pack_start(label, False, False, 0)

        controls = Gtk.Grid()
        controls.set_property("hexpand", True)
        controls.set_column_spacing(10)
        controls.set_row_spacing(5)
        ctrl_row = 0

        self.cpu_load = Gtk.ProgressBar()
        self.cpu_load.get_style_context().add_class(".buffer-fill-level")
        label = Gtk.Label(label="CPU", xalign=0)
        controls.attach(label, 0, ctrl_row, 1, 1)
        self.cpu_load.set_property("hexpand", True)
        self.cpu_load.set_property("valign", 3)
        controls.attach(self.cpu_load, 1, ctrl_row, 1, 1)
        self.cpu_load_label = Gtk.Label(label="-%", xalign=1)
        self.cpu_load_label.set_property("width-request", 48)
        controls.attach(self.cpu_load_label, 2, ctrl_row, 1, 1)
        ctrl_row += 1

        self.mem_level = Gtk.ProgressBar()
        self.mem_level.get_style_context().add_class(".buffer-fill-level")
        label = Gtk.Label(label="Mem", xalign=0)
        controls.attach(label, 0, ctrl_row, 1, 1)
        self.mem_level.set_property("hexpand", True)
        self.mem_level.set_property("valign", 3)
        controls.attach(self.mem_level, 1, ctrl_row, 1, 1)
        self.mem_level_label = Gtk.Label(label="-%", xalign=1)
        controls.attach(self.mem_level_label, 2, ctrl_row, 1, 1)
        ctrl_row += 1

        self.net_stats_label = Gtk.Label(label="-", xalign=1)
        self.net_stats_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Net", self.net_stats_label, "", 2)
        ctrl_row += 1


        self.cpu_temp_label = Gtk.Label(label="-", xalign=1)
        self.cpu_temp_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Core temp", self.cpu_temp_label, "°C")
        ctrl_row += 1

        box.pack_start(controls, True, True, 0)

        return box

    def sync_box( self ):
        sync_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sync_box.set_property("hexpand", True)
        sync_box.get_style_context().add_class("box")

        sync_label = Gtk.Label(label="SYNC", xalign=0)
        sync_label.get_style_context().add_class("box-header")
        sync_box.pack_start(sync_label, False, False, 0)

        controls = Gtk.Grid()
        controls.set_property("hexpand", True)
        controls.set_column_spacing(10)
        controls.set_row_spacing(5)
        ctrl_row = 0

        self.sync_status_label = Gtk.Label(label="Searching...", xalign=1)
        self.sync_status_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Status", self.sync_status_label, "")
        ctrl_row += 1

        self.cfo_label = Gtk.Label(label="-", xalign=1)
        self.cfo_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "CFO", self.cfo_label, "kHz")
        ctrl_row += 1

        self.cell_id_label = Gtk.Label(label="-", xalign=1)
        self.cell_id_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Cell ID", self.cell_id_label, "")
        ctrl_row += 1

        self.prb_label = Gtk.Label(label="-", xalign=1)
        self.prb_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "PRB", self.prb_label, "")
        ctrl_row += 1

        self.width_label = Gtk.Label(label="-", xalign=1)
        self.width_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Width", self.width_label, "MHz")
        ctrl_row += 1

        self.subc_label = Gtk.Label(label="-", xalign=1)
        self.subc_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Δf", self.subc_label, "kHz")
        ctrl_row += 1

        self.cinr_label = Gtk.Label(label="-", xalign=1)
        self.cinr_label.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "CINR", self.cinr_label, "dB")
        ctrl_row += 1

        sync_box.pack_start(controls, True, True, 0)

        return sync_box

    def add_gateway_screen( self ):
        grid = Gtk.Grid()
        grid.set_property("hexpand", True)

        self.gw_ser_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.gw_ser_box.set_property("hexpand", True)
        self.gw_ser_box.set_property("vexpand", True)
        self.gw_ser_box.get_style_context().add_class("box")
        ser_label = Gtk.Label(label="SERVICES", xalign=0)
        ser_label.get_style_context().add_class("box-header")
        self.gw_ser_box.pack_start(ser_label, False, False, 0)

        grid.attach(self.gw_ser_box, 0, 0, 1, 1)

        fil_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        fil_box.set_property("hexpand", True)
        fil_box.set_property("vexpand", True)
        fil_box.get_style_context().add_class("box")
        fil_label = Gtk.Label(label="FILES", xalign=0)
        fil_label.get_style_context().add_class("box-header")
        fil_box.pack_start(fil_label, False, False, 0)
        list_view = Gtk.TreeView(model=self.files_store)
        col1r = Gtk.CellRendererText()
        col1 = Gtk.TreeViewColumn("Age (s)", col1r, text=0)
        col1.set_sort_column_id(0)
        list_view.append_column(col1)
        col2r = Gtk.CellRendererText()
        col2 = Gtk.TreeViewColumn("Location", col2r, text=1)
        list_view.append_column(col2)
        col4r = Gtk.CellRendererText()
        col4 = Gtk.TreeViewColumn("Size", col4r, text=2)
        list_view.append_column(col4)
        fil_box.pack_start(list_view, True, True, 0)
        
        grid.attach(fil_box, 1, 0, 2, 1)
        return grid;

    def add_receiver_screen( self ):
        grid = Gtk.Grid()
        grid.set_property("hexpand", True)
        sdr_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sdr_box.set_property("hexpand", True)
        sdr_box.get_style_context().add_class("box")

        sdr_label = Gtk.Label(label="SDR", xalign=0)
        sdr_label.get_style_context().add_class("box-header")
        sdr_box.pack_start(sdr_label, False, False, 0)

        controls = Gtk.Grid()
        controls.set_property("hexpand", True)
        controls.set_column_spacing(10)
        controls.set_row_spacing(5)
        ctrl_row = 0


        self.fcen = Gtk.Label(label="-", xalign=1)
        self.fcen.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Frequency", self.fcen, "MHz")
        ctrl_row += 1

        self.gain = Gtk.Label(label="-", xalign=1)
        self.gain.get_style_context().add_class("control-value")
        self.gain_val_label = Gtk.Label(label="Gain", xalign=0)
        controls.attach(self.gain_val_label, 0, ctrl_row, 1, 1)
        self.gain.set_property("hexpand", True)
        self.gain.set_property("valign", 3)
        controls.attach(self.gain, 1, ctrl_row, 1, 1)
        self.gain_unit_label = Gtk.Label(label="dB", xalign=0)
        controls.attach(self.gain_unit_label, 2, ctrl_row, 1, 1)
        ctrl_row += 1

        gain_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        gain_down_button = Gtk.Button(label="− {:.0f} dB".format(gain_step))
        gain_down_button.set_property("height-request", 40)
        gain_down_button.set_property("width-request", 147)
        gain_down_button.connect("clicked", self.gain_down, None)
        gain_box.pack_start(gain_down_button, False, False, 0)
        gain_up_button = Gtk.Button(label="+ {:.0f} dB".format(gain_step))
        gain_up_button.set_property("height-request", 40)
        gain_up_button.set_property("width-request", 147)
        gain_up_button.connect("clicked", self.gain_up, None)
        gain_box.pack_start(gain_up_button, False, False, 0)
        controls.attach(gain_box, 0, ctrl_row, 3, 1)
        ctrl_row += 1

        self.antenna = Gtk.Label(label="-", xalign=1)
        self.antenna.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Antenna", self.antenna, "")
        ctrl_row += 1

        self.sample_rate = Gtk.Label(label="-", xalign=1)
        self.sample_rate.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Sample Rate", self.sample_rate, "MHz")
        ctrl_row += 1

        self.filter_bw = Gtk.Label(label="-", xalign=1)
        self.filter_bw.get_style_context().add_class("control-value")
        self.add_control( controls, ctrl_row, "Filter BW", self.filter_bw, "MHz")
        ctrl_row += 1

        self.buffer_level = Gtk.ProgressBar()
        self.buffer_level.get_style_context().add_class(".buffer-fill-level")
        self.add_control( controls, ctrl_row, "Buffer Level", self.buffer_level, "", 2)
        ctrl_row += 1

        sdr_box.pack_start(controls, True, True, 0)

        self.spectrum = Gtk.DrawingArea()
        self.spectrum.connect("draw", self.draw_spectrum)
        self.spectrum.set_property("hexpand", True)
        self.spectrum.set_size_request(0, 80)
        self.ce_vals = ()

        sdr_box.pack_start(self.spectrum, True, True, 0)

        grid.attach(sdr_box, 0, 0, 1, 2)

        grid.attach(self.system_box(), 0, 2, 1, 1)


        self.channel_grid = Gtk.Grid()


        pdsch_label = Gtk.Label(label="PDSCH", xalign=0)
        pdsch_sublabel = Gtk.Label(label="", xalign=1)
        self.pdsch_box = self.channel_box(pdsch_label, pdsch_sublabel)
        self.channel_grid.attach( self.pdsch_box, 0, 0, 1, 1)
        self.pdsch_box.attached = True

        self.channel_grid.attach(self.sync_box(), 0, 1, 1, 1)

        pmch_label = Gtk.Label(label="PMCH", xalign=0)
        pmch_sublabel = Gtk.Label(label="MCCH", xalign=1)
        self.mcch_box = self.channel_box(pmch_label, pmch_sublabel)
        self.channel_grid.attach( self.mcch_box, 1, 0, 1, 1)
        self.mcch_box.attached = True

        pmch_label = Gtk.Label(label="PMCH", xalign=0)
        pmch_sublabel = Gtk.Label(label="MCH 0", xalign=1)
        self.pmch0_box = self.channel_box(pmch_label, pmch_sublabel)
        self.channel_grid.attach( self.pmch0_box, 2, 0, 1, 1)


        self.channels_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.channels_box.set_property("hexpand", True)
        self.channels_box.get_style_context().add_class("box")
        channels_label = Gtk.Label(label="SERVICES", xalign=0)
        channels_label.get_style_context().add_class("box-header")
        self.channels_box.pack_start(channels_label, False, False, 0)

        self.channel_grid.attach( self.channels_box, 1, 1, 2, 1)

        self.channel_grid.set_property("expand", True)
        self.channel_grid.set_property("column-homogeneous", True)
        self.channel_grid.set_property("row-homogeneous", True)

        grid.attach(self.channel_grid, 1, 0, 2, 3)

        grid.set_property("expand", True)
        grid.set_property("column-homogeneous", True)
        grid.set_property("row-homogeneous", True)
        return grid;

    def draw_spectrum( self, darea, cr):
        w = darea.get_allocated_width()
        h = darea.get_allocated_height()
        
        cnt = math.floor(len(self.ce_vals)/4)

        if (cnt == 0): 
            return
        cr.set_line_width(1)
        cr.set_font_size(15)

        cr.set_source_rgba(0.8, 0.8, 0.8, 1.0)

        ftext = "{:.1f} MHz".format(self.fc/1000000.0)
        (tx, ty, tw, th, tdx, tdy) = cr.text_extents(ftext)
        cr.move_to(w/2 - tw/2, h)
        cr.show_text(ftext)

        ftext = "-{:.1f}".format(self.prb*0.1)
        cr.move_to(50, h)
        cr.show_text(ftext)

        ftext = "+{:.1f}".format(self.prb*0.1)
        (tx, ty, tw, th, tdx, tdy) = cr.text_extents(ftext)
        cr.move_to(w - tw - 50, h)
        cr.show_text(ftext)

        cr.set_source_rgba(0, 0.8, 0.0, 1.0)


        h -= 20
        if self.state == 'synchronized':
            step = cnt/w
            vals = struct.unpack('f'*cnt, self.ce_vals)
            for x in range(20, w-20):
                cr.move_to(x, h)
                cr.line_to(x, h-1-(vals[math.floor(x*step)]*2.5))
            cr.stroke()
            ce_vals = ()

    def draw_constellation( self, darea, cr):
        w = darea.get_allocated_width()
        h = darea.get_allocated_height()
        cr.set_line_width(1)
        cr.set_source_rgba(0, 1, 1, 1)
        cr.move_to(0, h/2)
        cr.line_to(w, h/2)
        cr.move_to(w/2, 0)
        cr.line_to(w/2, h)
        cr.stroke()

        cr.set_source_rgba(0, 0.8, 0.0, 1.0)
        for p in range(0, int(len(darea.pmch_data)/8), 5):
            [i,q] = struct.unpack_from('ff', darea.pmch_data, p*8)
            cr.arc(w/2+i*w/2.5, h/2+q*h/2.5, 2, 0, 2*math.pi)
            cr.fill()

    def gw_not_running(self):
        self.files_store.clear()

    def update_gw_files(self, files):
        self.files_store.clear()
        for f in files:
            self.files_store.append([f["age"], f["location"], f["content_length"]])

    def update_gw_services(self, services):
        for s in self.gw_ser_box.get_children():
            self.gw_ser_box.remove(s)
        
        services_label = Gtk.Label(label="SERVICES", xalign=0)
        services_label.get_style_context().add_class("box-header")
        self.gw_ser_box.pack_start(services_label, False, False, 0)
        for s in services:
            info = ""
            mtch_idx = 0
            info += "  <b>"+s["service_name"]+"</b>\n  SA TMGI: <b>" + ("0x%x" % int(s["service_tmgi"],16)) + "</b>\n" \
                "  Stream type: <b>" + s["stream_type"] + "</b>\n" \
                "  Stream m'cast: <b>" + s["stream_mcast"] + "</b>\n"
            if s["stream_type"] == "FLUTE/UDP":
                info += "  Stream TMGI: <b>" + ("0x%x" % int(s["stream_tmgi"],16)) + "</b>"

            ch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            play_btn = Gtk.Button(label="▷")
            play_btn.get_style_context().add_class("select-const-btn")
            play_btn.set_property("height-request", 50)
            play_btn.set_property("width-request", 50)
            play_btn.connect("clicked", self.play_service, s)
            ch_box.pack_start(play_btn, False, False, 0)
            ch_label = Gtk.Label(label="", xalign=0)
            ch_label.set_markup(info.rstrip())
            ch_box.pack_start(ch_label, False, False, 0)
            self.gw_ser_box.pack_start(ch_box, False, False, 0)
            self.gw_ser_box.show_all()


    def rp_not_running(self):
        self.state = 'stopped'
        self.sync_status_label.set_text("Stopped")
        self.fcen.set_text("-")
        self.gain.set_text("-")
        self.antenna.set_text("-")
        self.sample_rate.set_text("-")
        self.filter_bw.set_text("-")
        self.prb_label.set_text("-")
        self.cell_id_label.set_text("-")
        self.subc_label.set_text("-")
        self.cinr_label.set_text("-")
        self.cfo_label.set_text("-")
        self.width_label.set_text("-")
        self.buffer_level.set_fraction(0)
        self.spectrum.queue_draw()
        self.clear_values(self.pdsch_box)
        self.clear_values(self.mcch_box)
        self.clear_values(self.pmch0_box)
        self.pmch0_box.hide()
        for ch in self.channels_box.get_children():
            self.channels_box.remove(ch)
        return False

    def update_ce_graph(self, ce):
        self.ce_vals = ce
        self.spectrum.queue_draw()

    def clear_values(self, box):
        box.constellation.pmch_data = ()
        box.pmch_bler.set_text("-")
        box.pmch_ber.set_text("-")
        box.mcs.set_text("-")

    def update_constellation(self, box, data):
        box.constellation.pmch_data = data
        box.constellation.queue_draw()

    def update_pmch_status(self, box, status, sublabel_text):
        if status['present'] == True:
            box.show()
        if status['present'] == False:
            box.hide()
        box.sublabel.set_text(sublabel_text)#"MCH {:d}".format(self.selected_mch))
        box.pmch_bler.set_text("{:.3f}".format(status['bler']))
        if status['ber'] != "-":
            box.pmch_ber.set_text("{:.3f}".format(status['ber']))
        box.mcs.set_text("MCS {:d}".format(status['mcs']))

    def update_state(self, status, sdr):
        self.state = status['state']
        self.prb = status['nof_prb']
        if self.state == 'synchronized':
            self.prb_label.set_text("{:d}".format(status['nof_prb']))
            self.cell_id_label.set_text("{:d}".format(status['cell_id']))
            self.width_label.set_text("{:.0f}".format(status['nof_prb']*0.2))
            self.subc_label.set_text("{:.2f}".format(status['subcarrier_spacing']))
            self.cinr_label.set_text("{:.2f}".format(status['cinr_db']))
            self.cfo_label.set_text("{:.3f}".format(status['cfo']/1000.0))
        else:
            self.prb_label.set_text("-")
            self.width_label.set_text("-")
            self.cell_id_label.set_text("-")
            self.cfo_label.set_text("-")
        if self.state == 'searching':
            self.sync_status_label.set_text("Search")
        elif self.state == 'syncing':
            self.sync_status_label.set_text("Syncing")
        else:
            self.sync_status_label.set_text("Synced")
        self.fc = sdr['frequency']
        self.fcen.set_text("{:.2f}".format(sdr['frequency']/1000000.0))
        self.gain_val = sdr['gain']
        self.gain.set_text("{:.2f}".format(sdr['gain']))
        self.gain_val_label.set_text("Gain ({:.0f}..{:.0f})".format(sdr['min_gain'],sdr['max_gain']))
        self.antenna.set_text(sdr['antenna'])
        self.antenna_val = sdr['antenna']
        self.sr = sdr['sample_rate']
        self.sample_rate.set_text("{:.2f}".format(sdr['sample_rate']/1000000.0))
        self.filter_bw.set_text("{:.2f}".format(sdr['filter_bw']/1000000.0))
        self.filter_bw_val = sdr['filter_bw']
        self.buffer_level.set_fraction(sdr["buffer_level"])
        return False

    def update_sys_stats(self, cpu, mem, temp, down_mbps, up_mbps):
        self.cpu_load.set_fraction(cpu/100.0)
        self.cpu_load_label.set_text("{:.1f}%".format(cpu))
        self.mem_level.set_fraction(mem.percent/100.0)
        self.mem_level_label.set_text("{:.1f}%".format(mem.percent))
        self.cpu_temp_label.set_text("{:.1f}".format(temp["coretemp"][0].current))
        self.net_stats_label.set_text("↓{:.2f} ↑{:.2f} Mbit/s".format(down_mbps, up_mbps))

    def update_services(self, mch_info):
        if self.mch_info == mch_info:
          return
        self.mch_info = mch_info
        mch_idx = 0

        for ch in self.channels_box.get_children():
            self.channels_box.remove(ch)
        
        channels_label = Gtk.Label(label="SERVICES", xalign=0)
        channels_label.get_style_context().add_class("box-header")
        self.channels_box.pack_start(channels_label, False, False, 0)
        for mch in mch_info:
            info = ""
            mtch_idx = 0
            info += " <b>MCH " + str(mch_idx) + "</b> (MCS " + str(mch["mcs"])  + "):\n"
            for mtch in mch["mtchs"]:
                info += "  LCID " + str(mtch["lcid"]) + ", 0x" + mtch["tmgi"] + ", " + mtch["dest"] + "\n"

            ch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            const_btn = Gtk.Button(label="⸬")
            const_btn.get_style_context().add_class("select-const-btn")
            const_btn.set_property("height-request", 50)
            const_btn.set_property("width-request", 50)
            const_btn.connect("clicked", self.select_mch_constellation, mch_idx)
            ch_box.pack_start(const_btn, False, False, 0)
            ch_label = Gtk.Label(label="", xalign=0)
            ch_label.set_markup(info.rstrip())
            ch_box.pack_start(ch_label, False, False, 0)
            self.channels_box.pack_start(ch_box, False, False, 0)
            self.channels_box.show_all()

            mch_idx += 1

    def get_status(self):
        self.last_net = psutil.net_io_counters()
        self.last_net_time = time.time()
        while True:
            if self.mode == "rp":
                self.get_rp_status()
            elif self.mode == "gw":
                self.get_gw_status()
            time.sleep(0.2)

    def get_gw_status(self):
        try:
            response = requests.get(gw_api_url + "services", verify=False)
            services = response.json()
            GLib.idle_add(self.update_gw_services, services)
            response = requests.get(gw_api_url + "files", verify=False)
            files = response.json()
            GLib.idle_add(self.update_gw_files, files)
        except:
            GLib.idle_add(self.gw_not_running)

    def get_rp_status(self):
        try:
            cpu = psutil.cpu_percent(0, False)
            mem = psutil.virtual_memory()
            temp = psutil.sensors_temperatures()
            this_net = psutil.net_io_counters()
            now = time.time()
            down_bytes = this_net.bytes_recv - self.last_net.bytes_recv
            up_bytes = this_net.bytes_sent - self.last_net.bytes_sent
            GLib.idle_add(self.update_sys_stats, cpu, mem, temp, 
                    (down_bytes/(now-self.last_net_time)*8.0/1000000.0), (up_bytes/(now-self.last_net_time)*8.0/1000000.0))
            last_net = psutil.net_io_counters()
            self.last_net_time = time.time()
            response = requests.get(rp_api_url + "status", verify=False)
            rj = response.json()
            response = requests.get(rp_api_url + "sdr_params", verify=False)
            sj = response.json()
            GLib.idle_add(self.update_state, rj, sj)
            response = requests.get(rp_api_url + "ce_values", verify=False)
            ce = response.content
            GLib.idle_add(self.update_ce_graph, ce)
            response = requests.get(rp_api_url + "pdsch_data", verify=False)
            GLib.idle_add(self.update_constellation, self.pdsch_box, response.content)
            response = requests.get(rp_api_url + "pdsch_status", verify=False)
            GLib.idle_add(self.update_pmch_status, self.pdsch_box, response.json(), "")
            response = requests.get(rp_api_url + "mch_info", verify=False)
            GLib.idle_add(self.update_services, response.json())
            response = requests.get(rp_api_url + "mcch_data", verify=False)
            GLib.idle_add(self.update_constellation, self.mcch_box, response.content)
            response = requests.get(rp_api_url + "mcch_status", verify=False)
            GLib.idle_add(self.update_pmch_status, self.mcch_box, response.json(), "MCCH")
            response = requests.get(rp_api_url + "mch_status/" + str(self.selected_mch), verify=False)
            GLib.idle_add(self.update_pmch_status, self.pmch0_box, response.json(), "MCH {:d}".format(self.selected_mch))
            response = requests.get(rp_api_url + "mch_data/" + str(self.selected_mch), verify=False)
            GLib.idle_add(self.update_constellation, self.pmch0_box, response.content)
        except:
            GLib.idle_add(self.rp_not_running)



settings = Gtk.Settings.get_default()
settings.set_property("gtk-application-prefer-dark-theme", True)

cssProvider = Gtk.CssProvider()
cssProvider.load_from_path('./obeca-gui.css')
#cssProvider.load_from_path('/usr/share/obeca/obeca-gui.css')
screen = Gdk.Screen.get_default()
styleContext = Gtk.StyleContext()
styleContext.add_provider_for_screen(screen, cssProvider,
                                     Gtk.STYLE_PROVIDER_PRIORITY_USER)

window = OfrWindow()
window.show_all()
window.pmch0_box.hide()

window.set_property("hexpand", False)
window.fullscreen()
window.set_resizable(False)
window.set_default_size(1024,600)
window.set_size_request(1024,600)

thread = threading.Thread(target=window.get_status)
thread.daemon = True
thread.start()


try:
    main_loop.run()
except KeyboardInterrupt:
    print("Exiting")
