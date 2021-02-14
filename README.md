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
  * Clone these repository
  <pre>
  git clone https://github.com/murasakiakari/MFRC522-python3.git
  git clone https://github.com/murasakiakari/FYP.git</pre>
  * Move MFRClib.py in /home/pi/MFRC522-python3 to /home/pi/FYP
  * Please enjoy

### Install PyQt
  * Install PyQt with the following command
  <pre>
  sudo apt-get install python3-pyqt5</pre>

### Install Database System
  * Install Database system with the following command
  <pre>
  sudo apt-get install mariadb-server-10.0 -y
  sudo mysql_secure_installation
  sudo mysql -u root -p</pre>
  * Inside Mariadb
  <pre>
  CREATE DATABASE historyrecordsystem;
  CREATE USER 'recordadmin'@'localhost' IDENTIFIED BY 'fyp123';
  GRANT ALL PRIVILEGES ON historyrecordsystem.* TO 'recordadmin'@'localhost';
  use HISTORY_RECORD_SYSTEM;
  create table USER(
  ID INT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE,
  STUDENT_ID VARCHAR(8) NOT NULL,
  STUDENT_NAME VARCHAR(255) NOT NULL,
  UID VARCHAR(15) NOT NULL,
  INITIALIZATION_TIME TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (STUDENT_ID)
  );
  exit</pre>
  * In console
  <pre>
  sudo pip3 install mysql-connector-python</pre>
