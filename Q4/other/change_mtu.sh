#!/bin/bash
sleep 60
sudo ip link set eth0 down
sudo ip link set eth0 mtu 9000
sudo ip link set eth0 up
