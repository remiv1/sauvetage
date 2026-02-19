#! /bin/bash

echo -e "-----------------------------------" > logs.log
echo -e "Logs app-back" >> logs.log
echo -e "-----------------------------------\n" >> logs.log

podman compose logs app-back >> logs.log 2>&1

echo -e "\n\n-----------------------------------" >> logs.log
echo -e "Logs app-front" >> logs.log
echo -e "-----------------------------------\n" >> logs.log

podman compose logs app-front >> logs.log 2>&1

echo -e "\n\n-----------------------------------" >> logs.log
echo -e "Logs db-main" >> logs.log
echo -e "-----------------------------------\n" >> logs.log

podman compose logs db-main >> logs.log 2>&1