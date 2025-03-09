#!/bin/bash

# FIXME: must run from this dir in checkout out version

#./10-prepare-raspi.sh # FIXME
#./20-prepare-python.sh # FIXME
#./30-install-services.sh # FIXME

echo "Applying patch to bluez for iPhone"
sudo sed -i '/ExecStart/ c ExecStart=/usr/lib/bluetooth/bluetoothd -P battery' /usr/lib/systemd/system/bluetooth.service


#echo "Install application"
#test -d moonboard || git clone https://github.com/8cH9azbsFifZ/moonboard.git
#cd moonboard
#git pull



#printf " Restarting" # FIXME
#sudo shutdown -r now
