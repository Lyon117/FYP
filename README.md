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
  CREATE USER 'admin'@'localhost' IDENTIFIED BY 'adminpwflockersystem2021';
  GRANT ALL PRIVILEGES ON *.* TO 'admin'@'localhost';
  FLUSH PRIVILEGES;
  exit</pre>
  * In console
  <pre>
  sudo pip3 install mysql-connector-python</pre>
  
### Install NGINX
  * Install NGINX with the following command
  <pre>
  sudo apt-get remove apache2
  sudo apt-get install nginx
  sudo systemctl start nginx</pre>
  * Now you can browse the welcome page of NGINX with entering the IP adress in the browser
  * Install PHP with the following command
  <pre>
  sudo apt-get install php7.3-fpm php7.3-mbstring php7.3-mysql php7.3-
  sudo nano /etc/nginx/sites-enabled/default</pre>
  * In that file
  replace
  <pre>index index.html index.htm;</pre>
  by
  <pre>index index.php index.html index.htm;</pre>
  uncomment
  <pre>
  #location ~ \.php$ {
  # include snippets/fastcgi-php.conf;
  # # With php5-fpm:
  # fastcgi_pass unix:/var/run/php5-fpm.sock;
  #}</pre>
  * Save the file with Ctrl+x, then y, then ENTER
  * In console enter
  <pre>
  sudo systemctl reload nginx
  sudo nano /var/www/html/index.php</pre>
  * In that file
  write
  <pre><?php phpinfo(); ?\></pre>
  * Save the file with Ctrl+x, then y, then ENTER
  * Move the folder LockerSystemDatabase into /var/www/html
  * Download bootstrap.min.css and bootstrap.min.js from https://getbootstrap.com/docs/5.0/getting-started/download/
  * Move bootstrap.min.css and bootstrap.min.js under the folder LockerSystemDatabase
  * Open 127.0.0.1/LockerSystemDatabase from raspberry pi browser or {your_raspberry_adress}/LockerSystemDatabase from another computer in the same local network
  ### Done!
  
  ## Appendix
  ### Data Structure
|  Sector x |      Block 4x     |         Block 4x+1        |            Block 4x+2            |   Block 4x+3  |      Comment      | Universal Key |
|:---------:|:-----------------:|:-------------------------:|:--------------------------------:|:-------------:|:-----------------:|:-------------:|
|  Sector 0 |     Manufacturer Code     | AuthID w/ StudentID [0:6] |        StudentName [6:31]        |  Sector 0 Key |   Student Info    |      Yes      |
|  Sector 1 | sign [0] + Balance [0:15] |          [0] * 16         |             [0] * 16             |  Sector 1 Key |   Balance Sector  |       No      |
|  Sector 2 |         WriteFlat         |          StartFlat        |             [0] * 16             |  Sector 2 Key |      Indexing     |       No      |
|  Sector 3 |     SystemName [0:30]     |      LockerID [30:31]     | StartTime [0:8] + EndTime [8:15] |  Sector 3 Key |  Use History #1   |       No      |
|    ...    |            ...            |            ...            |                ...               |      ...      |  Use History #2-9 |       No      |
| Sector 12 |     SystemName [0:30]     |      LockerID [30:31]     | StartTime [0:8] + EndTime [8:15] | Sector 12 Key |  Use History #10  |       No      |
| Sector 13 |          [0] * 16         |          [0] * 16         |             [0] * 16             | Sector 13 Key |     Unplanned     |       No      |
| Sector 14 |          [0] * 16         |          [0] * 16         |             [0] * 16             | Sector 14 Key |     Unplanned     |       No      |
| Sector 15 |          [0] * 16         |          [0] * 16         |             [0] * 16             | Sector 15 Key |     Unplanned     |       No      |
