# Mister first installation script

This is a simple installation script for mister, that simplifies the installation and configuration of the different scripts.

An internet connection is the only requirement, even though a very simple wifi configuration process is included.

It installes the following functionalities, and :


## Installation

1. Configure networking, 
    You can connect mister to your network using a network cable permanently, or temporally if you are planning to use the wifi.
    
    (Network configuration howto is provided here:) [https://mister-devel.github.io/MkDocs_MiSTer/setup/requirements/]

2. Connect to mister ssh as root 
    
    Your mister's IP address is displayed in the Mister menu, once networking is configured there.

    For **Windows** users:
        To connect via ssh to Mister you can use the free putty program, available at:
         https://www.putty.org/

        Once donwloaded, configure the host using your mister IP as the hostname, and "root" as the user name. 
        
    For **Linux** users: 
    If you are using linux from the terminal just use the command:
        $  ssh root@MyMisterIp
    
    The mister root password at the moment is "1".

3. Once the network is up, copy and run the following command:

```console
$ curl -s https://gitlab.com/asier.alkorta.formazioa/retro/-/raw/master/RomLibraryCuration/system/mister/install_mister_scripts.sh | bash /dev/stdin
'''

4. Wait for the process to end, and You are done. 

Enjoy!!!


## Credits
This code from other mister community members, who do all the real heavy lifting.

Thanks everyone at Mister_devel, retrodriven Wallpapers, theypsilon for the amazing update_all script, Mister addons, Pezz82 for the Psx mampacks, adn of course every one at this amazing community.
 

