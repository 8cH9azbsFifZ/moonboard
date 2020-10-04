#!/bin/bash

sudo apt-get update
sudo apt-get -y upgrade
sudo apt-get -y install git vim python3-pip libatlas-base-dev

test -d moonboard || git clone https://github.com/8cH9azbsFifZ/moonboard.git
cd moonboard
git pull
pip3 install -r requirements.txt
pip3 install spidev python-periphery

cd services
sudo ./install_service.sh moonboard.service 
cd ..

echo "Make sure spi device enabled in /boot/config.txt"
grep dtparam=spi=on /boot/config.txt

echo "Make sure to have a good hostname"
cat /etc/hostname

echo "Install DBUS service"
sudo cp ble/com.moonboard.conf /etc/dbus-1/system.d
sudo cp ble/com.moonboard.service /usr/share/dbus-1/system-services/

echo "Start advertising stuff"
sudo hcitool -i hci0 cmd 0x08 0x0008  {adv: 32 byte 0-padded if necessary}
sudo hcitool -i hci0 cmd 0x08 0x0009 {adv: 32 byte 0-padded if necessary}
sudo hcitool -i hci0 cmd 0x08 0x0006 {min:2byte} {max:2byte} {connectable:1byte} 00 00 00 00 00 00 00 00 07 00
sudo hcitool -i hci0 cmd 0x08 0x000a 01


#python3 ./run.py --driver SimPixel --debug
