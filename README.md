# FYP
This is a setup guidelines of our FYP.
## Requirement
  * A Raspberry Pi
  * A RC522 module
  * Some dupont wire w/ female-to-female
  * A micro SD card
  * Some IC card

## Setup
### Setup the OS installer.
  * Download the Rapberry Pi Imager from <https://www.raspberrypi.org/downloads/>.
  * Choose the corresponding version of you plaform.
  * Follow the instruction of the program, select the Operating System as **RASPBERRY PI OS (32-BIT)** and you SD Card.
  * Wait until it finish.
  
### Setup the Rasberry Pi
  * Incert the SD Card into the Rasberry Pi.
  * Connect the Keyboard, power cable and the HDMI cable into the RPi, once the power is on, the RPi will boot automatacally. (It may take many time for the first boot up)
  * Follow the instruction in the configuration, choose the country and password if you like, choose either LAN or WIFI connection
  * Recommand to update the RPi in the configuration. (It may take ~30 min)
  * Type the following command to setup remote control of the RPi.  
  <pre>sudo apt-get install xrdp</pre>
  * Get the IP adress from moving the mouse on the internet icon that locate at the right-hand upper corner in the desktop
  * Reboot the RPi and remove the HDMI cable
  
### Remote control from Windows
  * Open **Remote Desktop Connection (遠端桌面連線)** in the Windoes.
  * Input the IP adress of RPi to the RDC
  * Select **Xorg** as Session, input the username and password of your RPi. (Default ac: pi pw: raspberry)
  
### RC522 Setup
  * The connection of wire and pre-requirment refer to this markdown <https://github.com/mxgxw/MFRC522-python/blob/master/README.md>.
  * Open RPi Configuration at the left-upper corner.
  * Enable SPI and I2C in Interfaces window.
  * Install SPI-Py with the following command
  <pre>
  git clone https://github.com/lthiery/SPI-Py.git
  cd /home/pi/SPI-Py
  sudo python3 setup.py install</pre>
  * Clone this repository
  <pre>git clone https://github.com/murasakiakari/FYP-Gp3_8</pre>
  * Please enjoy
