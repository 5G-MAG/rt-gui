# Installation guide
Installation of OBECA GUI consits of 3 simple steps:
1. Install dependencies
2. Getting the source code
3. Building
> The *GUI* was tested and verified on Ubuntu 20.04 LTS (64 bit).

## Step 1: Install dependencies
````
sudo apt install python3-psutil vlc
sudo pip3 install python-vlc
````

## Step 2: Getting the source code
````
cd ~
git clone https://github.com/5G-MAG/obeca-gui.git
````

## Step 3: Building
````
cd obeca-gui/
mkdir build && cd build

cmake -DCMAKE_INSTALL_PREFIX=/usr -GNinja ..

sudo ninja install
````

After that, an OBECA GUI application has been installed. 
