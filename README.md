# Mister initial installation script

This is a simple installation script for mister, that simplifies the installation and configuration of the different scripts using a simple text based graphical interface.

An internet connection is the only requirement.

The following functionalities are available.
    * Perform initial mister update
    * Install Update_all script
    * Configure timezone
    * Cifs script download
    * Audio normalization scripts
    * BGM configuration
    * Download PSX Mempacks

Comand line execution is still needed, but the text based interface helps with the installation and configuration process, making it all easier.

## Installation

1. Configure networking, 
    You can connect mister to your network using a network cable permanently, or temporally if you are planning to use the wifi.
    
    (Network configuration howto is provided here:) [https://mister-devel.github.io/MkDocs_MiSTer/setup/requirements/]

2. Connect to mister ssh as root 
    
    Your mister's IP address is displayed in the Mister menu, once networking is configured there.

    For **Windows** users:
        To connect via ssh to Mister you can use the free putty program, available at:
         (Putty:) [https://www.putty.org/].

        Once donwloaded, configure the host using your mister IP as the hostname, and "root" as the user name. 
        
    For **Linux** users: 
    If you are using linux from the terminal just use the command:
        $  ssh root@MyMisterIp
    
    The mister root password at the moment is "1".

3. Once the network is up, copy and run the following command:

```console
$ curl -s https://raw.githubusercontent.com/devilschile2/retro-scripts/main/install_mister_scripts.sh | bash /dev/stdin
```

4. Wait for the process to end, and You are done. 

Enjoy!!!

## TODO list
 * Divide Installation in steps that are reboot aware
 * Integrate savegame backup system
 * Integrate mounting of an external Hard Drive
 

## Credits
This code uses functionality from other mister community members, which really does all the heavy lifting.

Thanks everyone at Mister_devel, theypsilon for the amazing update_all script, Mister addons, Pezz82 for the Psx mampacks, and of course every one at this amazing community.



