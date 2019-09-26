#!/bin/bash

# bash s2-ard.sh S2B_MSIL1C_20190908T154809_N0208_R054_T18TUK_20190908T192723 /data/2019/Regen.Network/ard/config.yml /data/2019/Regen.Network/ard/aoi.geojson

# docker pull s2-ard

docker run --name s2-ard -dit s2-ard

if [ -z "$2" ]
then
      echo "no config.yml file copied"
else
      echo "config.yml file copied"
      docker cp $2 s2-ard:app
fi

if [ -z "$3" ]
then
      echo "no aoi.geojson file copied"
else
      echo "aoi.geojson file copied"
      docker cp $3 s2-ard:app
fi

# echo "docker run -it -v $(pwd):/output --rm s2-ard --tile "$1""

docker exec -it s2-ard bash -c "python /app/ard.py --tile "$1""
