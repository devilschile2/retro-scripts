#!/bin/bash

source /media/fat/Scripts

# Check network connectivity

echo -e "GET http://google.com HTTP/1.0\n\n" | nc google.com 80 > /dev/null 2>&1

online=false

if [ $? -eq 0 ]; then
    echo "Online"
    online=true
else
    echo "Offline"
    online=false
fi


## Run installation

## Recheck internet connectivity

echo -e "GET http://google.com HTTP/1.0\n\n" | nc google.com 80 > /dev/null 2>&1

online=false

if [ $? -eq 0 ]; then
    echo "Online"
    online=true
else
    echo "Offline"
    online=false
fi

#if ["$online" == true]; then 
    echo "Now that we have network connection, let's install all the scripts!"

    echo "Download Mister installation download.sh script"

    wget https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/MiSTer_Downloader.zip


    unzip MiSTer_Downloader.zip

    # Update. Mister initial configuration.
    dialog --title "Perform initial update" \
        --backtitle "Perform initial update?" \
        --yesno "Do you want to Perform initial update?" 7 60

    response=$?
        case $response in
            0) 
                dialog --infobox "Updating the initial mister configuration." 0 0 ; sleep 4
                echo "Update mister installation ..."
                ./download.sh
                ;;
            1)
                echo "Skipping initial update"
                ;;
    esac

    # Update all Script
    dialog --title "Install and run update_all script" \
        --backtitle "Install and run update_all script?" \
        --yesno "Do you want to install and run update_all script?" 7 60

     response=$?
        case $response in
            0) 
                dialog --infobox "Installing and executing UpdateAll script." 0 0 ; sleep 4

                echo "Getting update_all script "
                wget https://raw.githubusercontent.com/theypsilon/Update_All_MiSTer/master/update_all.sh
                chmod +x update_all.sh

                echo "Executing update_all script. Please follow the onscreen instructions..."
                ./update_all.sh
                ;;
            1)
                echo "Skipping update all"
                ;;
        esac

    dialog --infobox "Now we will configure the rest of the setup." 0 0 ; sleep 4

    # Set correct timezone
    echo "Setting timezone..."
    timezone.sh

    # Cifs Download
    dialog --title "Cifs script download" \
        --backtitle "Do you want to install the Cifs (samba) scripts?" \
        --yesno "Do you want to install the Cifs (samba) scripts?" 7 60

    response=$?
    case $response in
        0) 
            echo "Download Cifs mount and umount scripts ..."
            wget https://raw.githubusercontent.com/MiSTer-devel/Scripts_MiSTer/master/cifs_mount.sh
            wget https://raw.githubusercontent.com/MiSTer-devel/Scripts_MiSTer/master/cifs_umount.sh
            ;;
        1)
            echo "Cifs scripts not installed"
            ;;

    esac

    # Retrodriven Wallpapers Now through update_all.sh
    '''
    dialog --title "Wallpapers" \
        --backtitle "Do you want to install the wallpapers from Retrodriven?" \
        --yesno "Do you want to install the wallpapers from Retrodriven?" 7 60

    response=$?
    case $response in
        0)
            # Wallpapers
            echo "Download wallpaper script from retrodriven"
            wget https://github.com/RetroDriven/MiSTerWallpapers/releases/download/1.1/MiSTer.Wallpapers.v1.1.zip -O MiSTer.Wallpapers.zip 
            unzip MiSTer.Wallpapers.zip
            rm MiSTer.Wallpapers.zip
    
            echo "Configuring background wallpaper..."
            chmod -x Update_MiSTerWallpapers.sh
            sed -i '/^SELF_MANAGED="False"/SELF_MANAGED="true"/' Update_MiSTerWallpapers.ini
            ./Update_MiSTerWallpapers.sh
            exit;;
        1)
            echo "Skipping wallpaper installation"
            exit;;
    esac
    '''
    
    # Audio normalization
    dialog --title "Audio normalization" \
        --backtitle "Do you want to install the Audio normalization scripts (make all the cores sound at the same volume)?" \
        --yesno "Do you want to install the Audio normalization scripts (make all the cores sound at the same volume)?" 7 60

    response=$?
    case $response in
        0)
            echo "Getting Mister normalize audio "
            wget https://raw.githubusercontent.com/misteraddons/normalize_audio_scripts/main/normalize_audio_%2B6dB.sh

            wget https://raw.githubusercontent.com/misteraddons/normalize_audio_scripts/main/normalize_audio_0dB.sh
            ;;
        1)
            echo "Skipping Audiuo normalization script installation"
            ;;
    esac

    # BGM configuraiton
     dialog --title "Background Music player" \
        --backtitle "Do you want to configure the Background Music player?" \
        --yesno "Do you want to configure the Background Music player?" 7 60

    response=$?
    case $response in
        0)
            echo "Configuring BGM..."

            echo "[playlist]" >>bgm.ini
            echo "NumberOfEntries=1" >>bgm.ini
            echo "NumberOfEntries=1" >>bgm.ini
            echo "File1=http://us3.internet-radio.com:8324/listen.pls" >> bgm.ini
            echo "Length1=-1" >>bgm.ini
            ;;
        1)
            echo "Skipping BGM player configuration"
            ;;
    esac


    # PSX mempacks
    dialog --title "PSX mempacks" \
        --backtitle "Do you want to download the PSX mempacks?" \
        --yesno "Do you want to download the PSX mempacks?" 7 60

    response=$?
    case $response in
        0 ) 
            echo "Downloading Mempack packs for PSX..."
            curl -o /media/fat/games/PSX/ https://github.com/Pezz82/MemCard-Pro-Packs/archive/refs/heads/main.zip 
            echo "Unzipping PSX Mempack..."
            unzip /media/fat/games/PSX/main.zip -d /media/fat/games/PSX/
            rm /media/fat/games/PSX/main.zip
            ;;
        1)
            echo "Non PSX mempack downloaded."
            ;;
    esac

    # Final completion message
    dialog --title "Installation Complete" --msgbox "Installation Complete" 0 0

# fi;
