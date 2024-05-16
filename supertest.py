#!/usr/bin/python3
# @ made by d-rez / dark_skeleton
# Requires:
# - ADS1015 with Vbat on A0
# - pngview
# - a symbolic link to ic_battery_alert_red_white_36dp.png under
#   material_design_icons_master/device/drawable-mdpi/
# - an entry in crontab
# - material_design_icons_master github clone
# - some calibration, there's a lot of jitter
# - code comments. someday...

import time
import random
import subprocess
import os, sys
import re
import logging
import logging.handlers
from datetime import datetime
from statistics import median
from collections import deque
from enum import Enum

import serial
import RPi.GPIO as GPIO




pngview_path="/usr/local/bin/pngview"
pngview_call=[pngview_path, "-d", "0", "-b", "0x0000", "-n", "-l", "15000", "-y", "0", "-x"]

iconpath= "/home/pi/scripts/nintendo_retropie/overlay_icons/"
iconpath2 = os.path.dirname(os.path.realpath(__file__)) + "/overlay_icons/"
logfile = os.path.dirname(os.path.realpath(__file__)) + "/overlay.log"
dpi=36

env_icons = {
  "under-voltage": iconpath2+"flash.png",
  "freq-capped":   iconpath2+"thermometer.png",
  "throttled":     iconpath2+"thermometer-lines.png"
}
wifi_icons = {
  "connected": iconpath + "ic_network_wifi_white_"      + str(dpi) + "dp.png",
  "disabled":  iconpath + "ic_signal_wifi_off_white_"   + str(dpi) + "dp.png",
  "enabled":   iconpath + "ic_signal_wifi_0_bar_white_" + str(dpi) + "dp.png"
}
bt_icons = {
  "enabled":   iconpath + "ic_bluetooth_white_"           + str(dpi) + "dp.png",
  "connected": iconpath + "ic_bluetooth_connected_white_" + str(dpi) + "dp.png",
  "disabled":  iconpath + "ic_bluetooth_disabled_white_"  + str(dpi) + "dp.png"
}
icon_battery_critical_shutdown = iconpath2 + "alert-outline-red.png"

wifi_carrier = "/sys/class/net/wlan0/carrier" # 1 when wifi connected, 0 when disconnected and/or ifdown
wifi_linkmode = "/sys/class/net/wlan0/link_mode" # 1 when ifup, 0 when ifdown
bt_devices_dir="/sys/class/bluetooth"
env_cmd="vcgencmd get_throttled"

fbfile="tvservice -s"

#charging no load: 4.85V max (full bat)
#charging es load: 4.5V max

vmax = {"discharging": 100,
        "charging"   : 4.5 }
vmin = {"discharging": 2,
        "charging"   : 4.2 }
icons = { "discharging": [ "alert_red", "alert","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20","20", "30", "30", "30", "30","30", "30", "30", "30","30", "40", "40", "40", "40","40", "40", "40", "40", "50","50", "50","50",  "60","70","70", "70","70","80", "80","90","90", "full" , "full"],
          "charging"   : [ "charging_20", "charging_20", "charging_20",
                           "charging_30", "charging_30", "charging_50",
                           "charging_60", "charging_60", "charging_80",
                           "charging_90", "charging_full", "charging_full" ]}

class InterfaceState(Enum):
  DISABLED = 0
  ENABLED = 1
  CONNECTED = 2

# From my tests:
# over 4V => charging
# 4.7V => charging and charged 100%
# 3.9V => not charging, 100%
# 3.2V => will die in 10 mins under load, shut down
# 3.3V => warning icon?

#adc = Adafruit_ADS1x15.ADS1015()
# Choose a gain of 1 for reading voltages from 0 to 4.09V.
# Or pick a different gain to change the range of voltages that are read:
#  - 2/3 = +/-6.144V
#  -   1 = +/-4.096V
#  -   2 = +/-2.048V
#  -   4 = +/-1.024V
#  -   8 = +/-0.512V
#  -  16 = +/-0.256V
# See table 3 in the ADS1015i/ADS1115 datasheet for more info on gain.

def translate_bat(voltage):
  # Figure out how 'wide' each range is
  state =  "discharging"
  #print("estado: ",state)  
  leftSpan = vmax[state] - vmin[state]
  rightSpan = len(icons[state]) - 1

  # Convert the left range into a 0-1 range (float)
  valueScaled = float(voltage - vmin[state]) / float(leftSpan)

  # Convert the 0-1 range into a value in the right range.
  return icons[state][int(round(valueScaled * rightSpan))]

def wifi():
  global wifi_state, overlay_processes

  new_wifi_state = InterfaceState.DISABLED
  try:
    f = open(wifi_carrier, "r")
    carrier_state = int(f.read().rstrip())
    f.close()
    if carrier_state == 1:
      # ifup and connected to AP
      new_wifi_state = InterfaceState.CONNECTED
    elif carrier_state == 0:
      f = open(wifi_linkmode, "r")
      linkmode_state = int(f.read().rstrip())
      f.close()
      if linkmode_state == 1:
        # ifup but not connected to any network
        new_wifi_state = InterfaceState.ENABLED
        # else - must be ifdown
      
  except IOError:
    pass

  if new_wifi_state != wifi_state:
    if "wifi" in overlay_processes:
      overlay_processes["wifi"].kill()
      del overlay_processes["wifi"]

    if new_wifi_state == InterfaceState.ENABLED:
      overlay_processes["wifi"] = subprocess.Popen(pngview_call + [str(int(resolution[0]) - dpi * 2), wifi_icons["enabled"]])
    elif new_wifi_state == InterfaceState.DISABLED:
      overlay_processes["wifi"] = subprocess.Popen(pngview_call + [str(int(resolution[0]) - dpi * 2), wifi_icons["disabled"]])
    elif new_wifi_state == InterfaceState.CONNECTED:
      overlay_processes["wifi"] = subprocess.Popen(pngview_call + [str(int(resolution[0]) - dpi * 2), wifi_icons["connected"]])
  return new_wifi_state

def bluetooth():
  global bt_state, overlay_processes

  new_bt_state = InterfaceState.DISABLED
  try:
    p1 = subprocess.Popen('hciconfig', stdout = subprocess.PIPE)
    p2 = subprocess.Popen(['awk', 'FNR == 3 {print tolower($1)}'], stdin = p1.stdout, stdout=subprocess.PIPE)
    state=p2.communicate()[0].decode().rstrip()
    if state == "up":
      new_bt_state = InterfaceState.ENABLED
  except IOError:
    pass

  try:
    devices=os.listdir(bt_devices_dir)
    if len(devices) > 1:
      new_bt_state = InterfaceState.CONNECTED
  except OSError:
    pass

  if new_bt_state != bt_state:
    if "bt" in overlay_processes:
      overlay_processes["bt"].kill()
      del overlay_processes["bt"]

    if new_bt_state == InterfaceState.CONNECTED:
      overlay_processes["bt"] = subprocess.Popen(pngview_call + [str(int(resolution[0]) - dpi * 3), bt_icons["connected"]])
    elif new_bt_state == InterfaceState.ENABLED:
      overlay_processes["bt"] = subprocess.Popen(pngview_call + [str(int(resolution[0]) - dpi * 3), bt_icons["enabled"]])
    elif new_bt_state == InterfaceState.DISABLED:
      overlay_processes["bt"] = subprocess.Popen(pngview_call + [str(int(resolution[0]) - dpi * 3), bt_icons["disabled"]])
  return new_bt_state

def environment():
  global overlay_processes

  val=int(re.search("throttled=(0x\d+)", subprocess.check_output(env_cmd.split()).decode().rstrip()).groups()[0], 16)
  env = {
    "under-voltage": bool(val & 0x01),
    "freq-capped": bool(val & 0x02),
    "throttled": bool(val & 0x04)
  }
  for k,v in env.items():
    if v and not k in overlay_processes:
      overlay_processes[k] = subprocess.Popen(pngview_call + [str(int(resolution[0]) - dpi * (len(overlay_processes)+1)), env_icons[k]])
    elif not v and k in overlay_processes:
      overlay_processes[k].kill()
      del(overlay_processes[k])
  #return env # too much data
  return val

def battery(por_centaje):
  global battery_level, overlay_processes, battery_history
  #value = adc.read_adc(0, gain=2/3)
  value_v =por_centaje #round(random.uniform(20, 100),1)
  #print(value_v)
  battery_history.append(value_v)
  try:
    level_icon=translate_bat(median(battery_history))
  except IndexError:
    level_icon="unknown"


  if value_v <= 1:
    my_logger.warn("Battery voltage at or below 5%. Initiating shutdown within 1 minute BATTERY")
    subprocess.Popen(pngview_call + [str(int(resolution[0]) / 2 - 64), "-y", str(int(resolution[1]) / 2 - 64), icon_battery_critical_shutdown])
    os.system("sleep 60 && sudo poweroff &")

  if level_icon != battery_level:
    if "bat" in overlay_processes:
      overlay_processes["bat"].kill()
      del overlay_processes["bat"]

    icon='ic_battery_' + level_icon + "_white_" + str(dpi) + "dp.png"
    overlay_processes["bat"] = subprocess.Popen(pngview_call + [ str(int(resolution[0]) - dpi), iconpath + icon])
  return (level_icon, value_v)








def lectura(serial_port):
    accumulated_data = ''  # Variable para acumular los datos recibidos

    while True:
        try:
            read_byte = serial_port.read().decode('utf-8')  # Decodifica el byte a una cadena UTF-8
            #print(read_byte, end='')  # Imprime el byte (opcional, solo para depuración)

            accumulated_data += read_byte

            if read_byte == '\n':
                # Encuentra un salto de línea, devuelve la cadena acumulada hasta ese punto
                return accumulated_data
        except serial.SerialException as e:
            #print("-")
            reconectar_serial(serial_port)
            #return None  # Puedes manejar la reconexión aquí o devolver un valor específico
            accumulated_data = ''

def reconectar_serial(serial_port):
    while True:
        try:
            serial_port.close()
            serial_port.open()
            #print("Reconnected to serial port.")
            break
        except serial.SerialException as e:
            print(".")


def verificar_estructura(data):
    pattern = re.compile(r'\$ SmartUPS (.*?),Vin (.*?),BATCAP (.*?),Vout (.*?) \$')
    matches = pattern.findall(data)
    if len(matches) == 1:
        version, vin, batcap, vout = matches[0]
        return True, version, vin, batcap, vout
    else:
        return False, None, None, None, None
class UPS2_IO:
    def __init__(self,bcm_io=18):
        self.shutdown_check_pin = bcm_io
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.shutdown_check_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(self.shutdown_check_pin, GPIO.FALLING, callback= self.RPI_shutdown,bouncetime=1000)


    def RPI_shutdown(self,channel):
        print("detect bat LOW, system will shutdown in 10s!")
        for i in range(10,0,-1):
            print(i,end = ' ',flush=True)
            time.sleep(1)

        my_logger.warn("Battery voltage at or below 2%. Initiating shutdown within 1 minute  UPS2_IO")
        subprocess.Popen(pngview_call + [str(int(resolution[0]) / 2 - 64), "-y", str(int(resolution[1]) / 2 - 64), icon_battery_critical_shutdown])
        os.system("sleep 60 && sudo poweroff &")

        print("\nexecute System shudown!\n")
        
        print("llegaron las puetas")
        os.system("sudo shutdown -t now")
        sys.exit()


    def cleanup():
        print("clean up GPIO.")
        GPIO.cleanup()


def seriarespuesta(ser):
    while True:
        dato =lectura(ser)
        if dato !=None:
            return dato
        #else:
        #    reconectar_serial(ser)


overlay_processes = {}
wifi_state = None
bt_state = None
battery_level = None
env = None
battery_history = deque(maxlen=5)

# Set up logging
my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=102400, backupCount=1)
my_logger.addHandler(handler)
console = logging.StreamHandler()
my_logger.addHandler(console)

# Get Framebuffer resolution
resolution=re.search("(\d{3,}x\d{3,})", subprocess.check_output(fbfile.split()).decode().rstrip()).group().split('x')
my_logger.info(resolution)





ser = serial.Serial("/dev/ttyAMA0", baudrate=9600)
dato=""
anterior="$ SmartUPS V3.2P,Vin NG,BATCAP 100,Vout 5178 $"
control=UPS2_IO()
batcap=2
numero_de_errores=0
#dato=lectura(ser)

while True:
  #(battery_level, value_v) = battery()
  try:
      #dato =lectura(ser)
      #dato=seriarespuest(ser)
      """if dato ==None:
          dato=anterior
          numero_de_errores=numero_de_errores+1 
          print(" error lee el anterior: ",numero_de_errores )
          #while(True):
          #numero_de_errores=numero_de_errores+1
          #reconectar_serial(ser)
      else:
          numero_de_errores=0

      if numero_de_errores==1:
          dato=seriarespuesta(ser)
          numero_de_errores=0
          print("se solicito otra vez")"""     
      while True:
          dato =lectura(ser)
          es_valido, version, vin, batcap, vout = verificar_estructura(dato)
          if es_valido:
              break
      #anterior=dato
      """else:
          print("Estructura no válida")
          print(" ")
          es_valido, version, vin, batcap, vout = verificar_estructura(anterior)"""
 

  except Exception as error:
      print("super error fatal")
      os.system("sudo reboot")
      #dato=anterior

  #print("voltaje inyectado a el sistema: ", batcap)
  (battery_level, value_v) = battery(int(batcap))
  wifi_state = wifi()
  bt_state = bluetooth()
  env = environment()
  """ my_logger.info("Bateria: %.2f, Array: %s, Icon: %s, WiFi: %s, Bt: %s" % (
    #datetime.now(),
    value_v,
    list(battery_history),
    battery_level,
    wifi_state.name,
    bt_state.name,
    #env
  ))"""
  time.sleep(60)
