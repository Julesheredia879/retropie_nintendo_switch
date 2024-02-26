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






