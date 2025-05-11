# Wind VFD Controller

Raspberry Pi system for monitoring wind speed and controlling VFD

## Features
- Wind speed monitoring via 3001-FS sensor
- VFD frequency control via Modbus RTU
- Current sensing with SCT-013
- Email/SMS alerts
- Remote access via Cloudflare tunnel

## Hardware
- Raspberry Pi
- ADS1115 ADC
- 3001-FS wind sensor
- Ironhorse VFD
- DSD TECH SH-U10 RS485 converter
- SCT-013 current sensor

## Installation
1. Clone repository: `git clone https://github.com/mjbiggze/wind-vfd-controller.git`
2. Install dependencies: `pip3 install -r requirements.txt`
