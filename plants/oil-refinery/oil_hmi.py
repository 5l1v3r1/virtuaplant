#!/usr/bin/env python

# IMPORTS #
from PID import *
from gi.repository import GLib, Gtk, Gdk, GObject
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.exceptions import ConnectionException

import argparse
import os
import sys
import time

# Argument Parsing
class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

# Create argparser object to add command line args and help option
parser = MyParser(
	description = 'This Python script runs the SCADA HMI to control the PLC',
	epilog = '',
	add_help = True)

# Add a "-i" argument to receive a filename
parser.add_argument("-t", action = "store", dest="server_addr",
					help = "Modbus server IP address to connect the HMI to")

# Print help if no args are supplied
if len(sys.argv)==1:
	parser.print_help()
	sys.exit(1)

# Split and process arguments into "args"
args = parser.parse_args()

MODBUS_SLEEP=1

class HMIWindow(Gtk.Window):
    oil_processed_amount = 0
    oil_spilled_amount = 0
    #oil_flow_before_amount = 0
    oil_flow_after_amount = 0
    old_flow_amount = 0
    new_flow_amount = 0
    flow_rate = 0
    counter = 0
    tank_level_sensor_height = 500
    provessStarted = False
    #p = PID(0.3,0.04,0).setPoint(30)

    buttons = []

    def initModbus(self):
        # Create modbus connection to specified address and port
        self.modbusClient = ModbusClient(args.server_addr, port=5020)

    # Default values for the HMI labels
    def resetLabels(self):
        self.feed_pump__command_value.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.separator_value.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.level1_switch_value.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.level2_switch_value.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.process_status_value.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.connection_status_value.set_markup("<span weight='bold' foreground='red'>OFFLINE</span>")
        self.oil_processed_value.set_markup("<span weight='bold' foreground='green'>" + str(self.oil_processed_amount) + " Liters</span>")
        self.oil_spilled_value.set_markup("<span weight='bold' foreground='red'>" + str(self.oil_spilled_amount) + " Liters</span>")
        self.oil_flow_before_value.set_markup("<span weight='bold' foreground='green'>" + str(self.oil_flow_before_amount) + " Liters</span>")
        self.oil_flow_after_value.set_markup("<span weight='bold' foreground='green'>" + str(self.oil_flow_after_amount) + " Liters / seconds</span>")
        self.outlet_valve_value.set_markup("<span weight='bold' foreground='red'>N/A</span>")
        self.waste_value.set_markup("<span weight='bold' foreground='red'>N/A</span>")

    def __init__(self):
        # Window title
        Gtk.Window.__init__(self, title="Oil Refinery")
        self.set_border_width(100)

        #Create modbus connection
        self.initModbus()

        elementIndex = 0
        # Grid
        grid = Gtk.Grid()
        grid.set_row_spacing(15)
        grid.set_column_spacing(10)
        self.add(grid)

        # Main title label
        label = Gtk.Label()
        label.set_markup("<span weight='bold' size='xx-large' color='black'>Crude Oil Pretreatment Unit </span>")
        grid.attach(label, 4, elementIndex, 4, 1)
        elementIndex += 1

        # Crude Oil Feed Pump
        feed_pump__command_label = Gtk.Label("Process Runnng / Stopped?")
        feed_pump__command_value = Gtk.Label()

        auto_process_button = Gtk.Button("AUTO PROCESS")
        manual_process_button = Gtk.Button("MANUAL PROCESS")

        auto_process_button.connect("clicked", self.setPumpHelper, 1)
        manual_process_button.connect("clicked", self.setPumpHelper, 0)

        grid.attach(feed_pump__command_label, 4, elementIndex, 1, 1)
        grid.attach(feed_pump__command_value, 5, elementIndex, 1, 1)
        grid.attach(auto_process_button, 6, elementIndex, 1, 1)
        grid.attach(manual_process_button, 7, elementIndex, 1, 1)
        elementIndex += 1

        # Level Switch 1
        level1_switch_label = Gtk.Label("Crude Oil Tank 1 Level Switch")
        level1_switch_value = Gtk.Label()

        feed_pump_start_button = Gtk.Button("PUMP START")
        feed_pump_stop_button = Gtk.Button("PUMP STOP")
        self.buttons += feed_pump_start_button
        self.buttons += feed_pump_stop_button

        grid.attach(level1_switch_label, 4, elementIndex, 1, 1)
        grid.attach(level1_switch_value, 5, elementIndex, 1, 1)
        elementIndex += 1

        # Level Switch 2
        level2_switch_label = Gtk.Label("Separator Vessel Level Switch")
        level2_switch_value = Gtk.Label()

        grid.attach(level2_switch_label, 4, elementIndex, 1, 1)
        grid.attach(level2_switch_value, 5, elementIndex, 1, 1)
        elementIndex += 1

        #outlet valve
        outlet_valve_label = Gtk.Label("Outlet Valve")
        outlet_valve_value = Gtk.Label()

        outlet_vlave_open_button = Gtk.Button("OPEN")
        outlet_valve_close_button = Gtk.Button("CLOSE")

        outlet_vlave_open_button.connect("clicked", self.setOutletValveHelper, 1)
        outlet_valve_close_button.connect("clicked", self.setOutletValveHelper, 0)

        self.buttons += outlet_vlave_open_button
        self.buttons += outlet_valve_close_button

        grid.attach(outlet_valve_label, 4, elementIndex, 1, 1)
        grid.attach(outlet_valve_value, 5, elementIndex, 1, 1)
        grid.attach(outlet_vlave_open_button, 6, elementIndex, 1, 1)
        grid.attach(outlet_valve_close_button, 7, elementIndex, 1, 1)
        elementIndex += 1

        #Separator Vessel
        separator_label = Gtk.Label("Separator Vessel Valve")
        separator_value = Gtk.Label()

        separator_open_button = Gtk.Button("OPEN")
        separator_close_button = Gtk.Button("CLOSED")

        separator_open_button.connect("clicked", self.setSepValveHelper, 1)
        separator_close_button.connect("clicked", self.setSepValveHelper, 0)

        self.buttons += separator_open_button
        self.buttons += separator_close_button

        grid.attach(separator_label, 4, elementIndex, 1, 1)
        grid.attach(separator_value, 5, elementIndex, 1, 1)
        grid.attach(separator_open_button, 6, elementIndex, 1, 1)
        grid.attach(separator_close_button, 7, elementIndex, 1, 1)
        elementIndex += 1

        #Waste Water Valve
        waste_label = Gtk.Label("Waste Water Valve")
        waste_value = Gtk.Label()

        waste_open_button = Gtk.Button("OPEN")
        waste_close_button = Gtk.Button("CLOSED")

        waste_open_button.connect("clicked", self.setWasteValveHelper, 1)
        waste_close_button.connect("clicked", self.setWasteValveHelper, 0)

        self.buttons += waste_open_button
        self.buttons += waste_close_button

        grid.attach(waste_label, 4, elementIndex, 1, 1)
        grid.attach(waste_value, 5, elementIndex, 1, 1)
        grid.attach(waste_open_button, 6, elementIndex, 1, 1)
        grid.attach(waste_close_button, 7, elementIndex, 1, 1)
        elementIndex += 1

        # Process status
        process_status_label = Gtk.Label("Process Status")
        process_status_value = Gtk.Label()
        grid.attach(process_status_label, 4, elementIndex, 1, 1)
        grid.attach(process_status_value, 5, elementIndex, 1, 1)
        elementIndex += 1

        # Connection status
        connection_status_label = Gtk.Label("Connection Status")
        connection_status_value = Gtk.Label()
        grid.attach(connection_status_label, 4, elementIndex, 1, 1)
        grid.attach(connection_status_value, 5, elementIndex, 1, 1)
        elementIndex += 1

        # Oil Processed Status
        oil_processed_label = Gtk.Label("Oil Processed Status")
        oil_processed_value = Gtk.Label()
        grid.attach(oil_processed_label, 4, elementIndex, 1, 1)
        grid.attach(oil_processed_value, 5, elementIndex, 1, 1)
        elementIndex += 1

        # Oil Spilled Status
        oil_spilled_label = Gtk.Label("Oil Spilled Status")
        oil_spilled_value = Gtk.Label()
        grid.attach(oil_spilled_label, 4, elementIndex, 1, 1)
        grid.attach(oil_spilled_value, 5, elementIndex, 1, 1)
        elementIndex += 1

        # Oil Flow Before
        #oil_flow_before_label = Gtk.Label("Amount of Oil to Control Valve")
        #oil_flow_before_value = Gtk.Label()
        #grid.attach(oil_flow_before_label, 4, elementIndex, 1, 1)
        #grid.attach(oil_flow_before_value, 5, elementIndex, 1, 1)
        #elementIndex += 1

        # Oil Flow After
        oil_flow_after_label = Gtk.Label("Oil Flow After Control Valve")
        oil_flow_after_value = Gtk.Label()
        grid.attach(oil_flow_after_label, 4, elementIndex, 1, 1)
        grid.attach(oil_flow_after_value, 5, elementIndex, 1, 1)
        elementIndex += 1

        # Oil Flow Sensitivity
        #oil_flow_sens_label = Gtk.Label("Oil Flow Sensitivity")
        #oil_flow_sens_entry = Gtk.Entry()
        #oil_flow_sens_button = Gtk.Button("CHANGE")
        #grid.attach(oil_flow_sens_label, 4, elementIndex, 1, 1)
        #grid.attach(oil_flow_sens_value, 5, elementIndex, 1, 1)
        #grid.attach(oil_flow_sens_button, 6, elementIndex, 1, 1)

        #waste_open_button.connect("clicked", self.setOilFlowSensitivity)
        #elementIndex += 1

        # Control Valve Position
        control_valve_position_label = Gtk.Label("Control Valve Position")
        control_valve_position_value = Gtk.Label()
        grid.attach(control_valve_position_label, 4, elementIndex, 1, 1)
        grid.attach(control_valve_position_value, 5, elementIndex, 1, 1)
        elementIndex += 1


        # Oil Refienery branding
        virtual_refinery = Gtk.Label()
        virtual_refinery.set_markup("<span size='small'>Crude Oil Pretreatment Unit - HMI</span>")
        grid.attach(virtual_refinery, 4, elementIndex, 2, 1)

        # Attach Value Labels
        self.feed_pump__command_value = feed_pump__command_value
        self.process_status_value = process_status_value
        self.connection_status_value = connection_status_value
        self.separator_value = separator_value
        self.level1_switch_value = level1_switch_value
        self.level2_switch_value = level2_switch_value
        self.oil_processed_value = oil_processed_value
        self.oil_spilled_value = oil_spilled_value
        self.outlet_valve_value = outlet_valve_value
        self.oil_flow_before_value = oil_flow_before_value
        self.oil_flow_after_value = oil_flow_after_value

        self.control_valve_position_value = control_valve_position_value
        self.waste_value = waste_value

        # Set default label values
        self.resetLabels()
        self.setTankLevel(self.tank_level_sensor_height)
        GObject.timeout_add_seconds(MODBUS_SLEEP, self.update_status)

    #COMMAND FUNCTIONS:
    # The actual send functions have been wrapped into a helper function that handles
    # the parameters that are required for a button click
    # ONLY USED FOR FUNCTIONS WHERE MANUAL HANDLING IS ALLOWED

    # Control the feed pump register values
    def setPump(self, data):
        try:
            self.modbusClient.write_register(0x01, data)
        except:
            pass

    def setPumpHelper(self, widget, data=None):
        #self.setPump(data)
        self.processStarted = bool(data)

    # Control the tank level register values
    def setTankLevel(self, data):
        try:
            self.modbusClient.write_register(0x02, data)
        except:
            pass

    # Control the separator vessel level register values
    def setSepValve(self, data):
        try:
            self.modbusClient.write_register(0x04, data)
        except:
            pass

    def setSepValveHelper(self, widget, data=None):
        self.setSepValve(data)

    # Control the separator vessel level register values
    def setWasteValve(self, data):
        try:
            self.modbusClient.write_register(0x08, data)
        except:
            pass

    def setWasteValveHelper(self, widget, data=None):
        self.setWasteValve(data)

    def setOutletValve(self, data):
        try:
            self.modbusClient.write_register(0x03, data)
        except:
            pass

    def setOutletValveHelper(self, widget, data=None):
        self.setOutletValve(data)

    def sendMeasuredFlowrate(self, data):
        try:
            self.modbusClient.write_register(0x0A, data) #regs[9]
        except:
            pass

    def setOilFlowSensitivity(self, widget, data=None):
        try:
            self.modbusClient.write_register(0x0D, data) #regs[9]
        except:
            pass

    def update_status(self):

        self.counter += 1
        try:
            if self.processStarted:
                for button in self.buttons:
                    button.set_sensitive(False)
            else:
                for button in self.buttons:
                    button.set_sensitive(True)
            # Store the registers of the PLC in "rr"
            rr = self.modbusClient.read_holding_registers(1,16)
            regs = []

            # If we get back a blank response, something happened connecting to the PLC
            if not rr or not rr.registers:
                raise ConnectionException

            # Regs is an iterable list of register key:values
            regs = rr.registers

            if not regs or len(regs) < 16:
                raise ConnectionException

            # If the feed pump "0x01" is set to 1, then the pump is running
            if regs[0] == 1:
                self.feed_pump__command_value.set_markup("<span weight='bold' foreground='green'>RUNNING</span>")
            else:
                self.feed_pump__command_value.set_markup("<span weight='bold' foreground='red'>STOPPED</span>")

            # PLC_TANK1_LEVEL = 0x02
            # If the level sensor is ON, sequence of steps activated
            if regs[1] == 1:
                self.level1_switch_value.set_markup("<span weight='bold' foreground='green'>ON</span>")
                self.setPump(0)
                self.setOutletValve(1)
            else:
                self.level1_switch_value.set_markup("<span weight='bold' foreground='red'>OFF</span>")
                if self.processStarted:
                    self.setPump(1)

            # PLC_OUTLET_VALVE = 0x03
            # Outlet Valve status
            if regs[2] == 1:
                self.outlet_valve_value.set_markup("<span weight='bold' foreground='green'>OPEN</span>")
            else:
                self.outlet_valve_value.set_markup("<span weight='bold' foreground='red'>CLOSED</span>")

            # PLC_SEP_VALVE = 0x04
            # If the feed pump "0x04" is set to 1, separator valve is open
            if regs[3] == 1:
                self.separator_value.set_markup("<span weight='bold' foreground='green'>OPEN</span>")
                self.process_status_value.set_markup("<span weight='bold' foreground='green'>RUNNING </span>")
            else:
                self.separator_value.set_markup("<span weight='bold' foreground='red'>CLOSED</span>")
                self.process_status_value.set_markup("<span weight='bold' foreground='red'>STOPPED </span>")

            #PLC_TANK2_LEVEL = 0x05
            if regs[4] == 1:
                self.level2_switch_value.set_markup("<span weight='bold' foreground='green'>ON</span>")
                self.setSepValve(1)
                self.setWasteValve(1)
            else:
                self.level2_switch_value.set_markup("<span weight='bold' foreground='red'>OFF</span>")
                self.setSepValve(0)
                self.setWasteValve(0)
            # PLC_OIL_SPILL = 0x06
            # If the oil spilled tag gets set, increase the amount of oil we have spilled
            if regs[5]:
                self.oil_spilled_value.set_markup("<span weight='bold' foreground='red'>" + str(regs[5]) + " Liters</span>")

            #PLC_OIL_PROCESSED = 0x07
            if regs[6]:
                self.oil_processed_value.set_markup("<span weight='bold' foreground='green'>" + str(regs[6] + regs[8]) + " Liters</span>")


            # PLC_WASTE_VALVE = 0x08
            # Waste Valve status "0x08"
            if regs[7] == 1:
                self.waste_value.set_markup("<span weight='bold' foreground='green'>OPEN</span>")
            else:
                self.waste_value.set_markup("<span weight='bold' foreground='red'>CLOSED</span>")

            ### - FLOW RATE AND PID VALVE POSITION - ###
            #if regs[9]:
                #self.oil_flow_before_value.set_markup("<span weight='bold' foreground='black'>" + str(regs[9]) + " Liters</span>")
            if regs[10]:
                if self.new_flow_amount != 0:
                    #calculate flow rate
                    self.old_flow_amount = self.new_flow_amount
                    self.new_flow_amount = regs[10]
                    # If more than 300 liters have flown through after
                    # the PID valve, safe to say, level is not reached
                    if self.new_flow_amount % 100 <= 20:
                        self.setOutletValve(0)

                    self.flow_rate = (self.new_flow_amount - self.old_flow_amount) / self.counter
                    self.oil_flow_after_value.set_markup("<span weight='bold' foreground='black'>" + str(self.flow_rate) + " Liters / seconds</span>")
                    self.counter = 0
                    #When flow was calculated, send it to regs[9]
                    self.sendMeasuredFlowrate(self.flow_rate)

                else:
                    self.new_flow_amount = regs[10]

            if regs[11]:
                self.control_valve_position_value.set_markup("<span weight='bold' foreground='black'>" + str(regs[11]) + " % </span>")
            # If we successfully connect, then show that the HMI has contacted the PLC
            self.connection_status_value.set_markup("<span weight='bold' foreground='green'>ONLINE </span>")



        except ConnectionException:
            if not self.modbusClient.connect():
                self.resetLabels()
        except:
            raise
        finally:
            return True


def app_main():
    win = HMIWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()


if __name__ == "__main__":
    GObject.threads_init()
    app_main()
    Gtk.main()
