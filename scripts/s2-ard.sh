#!/bin/bash

# docker pull s2-ard / docker build -t s2-ard .

docker run --name s2-ard -dit s2-ard

# parse named argument options
while :; do
    case $1 in
        -t|--tile)
                if [ "$2" ]; then
                        TILE=$2
			echo "TILE : $TILE"
                        shift
                else
                        die 'ERROR: "--tile" requires a non-empty option argument.'
                fi
                ;;
        -c|--config)
                if [ "$2" ]; then
                        CONFIG=$2
			echo "Config : $CONFIG"
                        shift
                else
                        die 'ERROR: "--config" requires a non-empty option argument.'
                fi
                ;;
        -a|--aoi)
                if [ "$2" ]; then
                        AOI=$2
			echo "AOI : $AOI"
                        shift
                else
                        die 'ERROR: "--aoi" requires a non-empty option argument.'
                fi
                ;;
        *)
                break
    esac

    shift
done

if [ -d $TILE ];
then
      echo "Copying SAFE Directory"
      docker cp $TILE s2-ard:work
      TILE="/work/"`basename "$TILE"`
else
      echo "Not a SAFE Directory"
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

# execute pre-processing of the data product (tile)
docker exec -it s2-ard bash -c "python /app/ard.py --tile "$TILE""

# copy output files/folders to host from s2-ard container
docker cp s2-ard:output $PWD

# remove files/folder from work and output directory on container
docker exec s2-ard sh -c 'rm -rf /output/* /work/*'
