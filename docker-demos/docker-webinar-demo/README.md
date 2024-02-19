This is the demo source for the Variscite webinar "Enhancing Embedded Software Design With Docker". This demo was designed for the VAR-SOM-MX93 running on our Symphony development board.

https://www.variscite.com/services/training/webinar-enhancing-embedded-software-design-with-docker/

Note, by default, the LED GPIO is bound to the leds-gpio driver. Since we desire to use it directly as a GPIO, we will somehow need to unbind the driver first. The simplest way to do this is via the sysfs driver binding interface as follows:

```
echo leds > /sys/bus/platform/drivers/leds-gpio/unbind
```

Next, deploy the source of this repository to the board and build the container by running the following in the directory where you deployed the source:

```
make
```

Finally, run the application as follows:
```
docker run -p 49160:8080 -d --device=/dev/gpiochip4 $USER/demo-app
```

You should then be able to connect and control the LED via an HTTP GET request (via a browser or similar) as follows, subsituting the IP with your actual board IP address:

```
http://192.50.205:49160/led_on

http://192.50.205:49160/led_off
```
