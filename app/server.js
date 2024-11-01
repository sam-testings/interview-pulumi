'use strict';

const express = require('express');

// Constants
const PORT = 80;
const HOST = '0.0.0.0';

// App
const app = express();
const customValue = process.env.CUSTOM_VALUE || 'Hello World!';
app.get('/', (req, res) => {
  res.send(customValue);
});

app.listen(PORT, HOST);
console.log(customValue)
console.log(`Running on http://${HOST}:${PORT}`);
