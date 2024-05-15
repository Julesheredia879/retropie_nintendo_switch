# Retropie_nintendo_switch
Hi guys this repositori is how to make a retropie nintendo switch with a raspberry pi 4 
We will start donwloading a Tool to flash the raspberry with retropie 
https://www.raspberrypi.com/software/


then we will get the IOS image, RETROPIE 
https://retropie.org.uk/download/




 press ctl+shif+x



### after flash it, we will connect with SSH:
    ssh pi@192.168.3.xx



we will put the screen laptop 
http://www.lcdwiki.com/10.1inch_HDMI_Display-H


###  first commands 
    sudo nano /boot/config.tx
    sudo reboot 

### /boot/config.txt

    #over_voltage=6
    #arm_freq=2000
    #gpu_freq=750
    #force_turbo=1
    
    arm_freq=2300
    gpu_freq=750
    gpu_mem=32
    over_voltage=14
    force_turbo=1
    
    hdmi_force_edid_audio=1
    #max_usb_current=1
    hdmi_force_hotplug=1
    config_hdmi_boost=7
    hdmi_group=2
    hdmi_mode=87
    hdmi_drive=2
    display_rotate=0
    hdmi_timings=1024 1 50 18 50 600 1 15 3 15 0 0 0 60 0 40000000 3
    dtoverlay=gpio-shutdown
    #enable_uart=1
    enable_uart=1
    #dtoverlay=disable-bt
    dtoverlay=miniuart-bt
    dtoverlay=disable-wifi
    
    # Disable the PWR LED
    #dtparam=pwr_led_trigger=none
    dtparam=pwr_led_activelow=off
    # Disable the Activity LED
    dtparam=act_led_trigger=none
    dtparam=act_led_activelow=off
    # Disable ethernet port LEDs
    dtparam=eth_led0=4
    dtparam=eth_led1=4


we will update the retropie 
https://retropie.org.uk/docs/Updating-RetroPie/

     sudo ~/RetroPie-Setup/retropie_setup.sh



     
after the update we need to install the nintendo switch driver  this is the link:

https://retropie.org.uk/docs/Nintendo-Switch-Controllers/

Installation 
### First, you need to install dkms-hid-nintendo, a Nintendo HID kernel module:
     git clone https://github.com/nicman23/dkms-hid-nintendo
     cd dkms-hid-nintendo
     sudo dkms add .
     sudo dkms build nintendo -v 3.2
     sudo dkms install nintendo -v 3.2
NOTE : the module version may change, check the driver's page for the correct version to be used with the dkms commands above.

Then, you need joycond, a userspace driver which manages the controllers and exposes their motion inputs.

On a fresh install, you might need to install the libevdev library first:

### 
    sudo apt-get install libevdev-dev



### 1 UPS software https://github.com/Julesheredia879/nintendo_retropie
    git clone https://github.com/nicman23/dkms-hid-nintendo





