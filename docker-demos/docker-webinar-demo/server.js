'use strict';

const express = require('express');

// Constants
const PORT = 8080;
const HOST = '0.0.0.0';

// App
const app = express();
const { exec } = require("child_process");

app.get('/led_on', (req, res) => {
  res.send('LED was turned on');
  exec("echo 'on' | socat - UNIX-CONNECT:uds_socket")
});

app.get('/led_off', (req, res) => {
  res.send('LED was turned off');
  exec("echo 'off' | socat - UNIX-CONNECT:uds_socket")
});

app.listen(PORT, HOST, () => {
  console.log(`Running on http://${HOST}:${PORT}`);
});