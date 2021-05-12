#!/bin/bash

#pull Regen Network Sentinel-2 ARD
#docker pull regennetwork/s2-ard

# run Regen Network Sentinel-2 ARD
#docker run --name s2-ard -dit ard
#docker run -dit -v "C:\Users\sambe\Documents\regen\grasslands_projects\s2-ard\src:/app/" --name s2-ard ard
docker restart s2-ard
start=$SECONDS

# parse named argument options --tile, --config and --aoi
while :; do
    case $1 in
        -t|--tiles)
                if [ "$2" ]; then
                        TILES=$2
			echo "Data Directory : $TILES"
                        shift
                else
                        echo 'ERROR: "--tile" requires a non-empty option argument.'
                        exit 1
                fi
                ;;
        -c|--config)
                if [ "$2" ]; then
                        CONFIG=$2
			echo "Config File : $CONFIG"
                        shift
                else
                        echo 'ERROR: "--config" requires a non-empty option argument.'
                        exit 1
                fi
                ;;
        -a|--aoi)
                if [ "$2" ]; then
                        AOI=$2
			echo "AOI File : $AOI"
                        shift
                else
                        echo 'ERROR: "--aoi" requires a non-empty option argument.'
                        exit 1
                fi
                ;;
        *)
                break
    esac

    shift
done

# copy config and aoi into running container
if [ -d $TILES ]
then
      echo "Copying data directory"
      docker cp $TILES s2-ard:work
      TILES="/work/"`basename "$TILES"`
else
      echo "Data directory invalid"
fi

if [ -z "$CONFIG" ]
then
      echo "No CONFIG file copied"
else
      echo "Copying config.yml file"
      docker cp $CONFIG s2-ard:app/config.yml
fi

if [ -z "$AOI" ]
then
      echo "No AOI file copied"
else
      echo "Copying AOI file"
      docker cp $AOI s2-ard:app/aoi.geojson
fi

# execute pre-processing of the data product (tile or batch)
docker exec -it s2-ard bash -c "python /app/ard.py --tiles "$TILES""

# copy output files/folders to host from s2-ard container
echo "Copying files from docker container"
docker cp s2-ard:output $PWD

# remove files/folder from work and output directory on container
docker exec s2-ard sh -c 'rm -rf /output/* /work/*'

docker stop s2-ard

duration=$((SECONDS-start))
minutes=$((duration/60))
echo "Time: $minutes minutes $((duration%60)) seconds"
