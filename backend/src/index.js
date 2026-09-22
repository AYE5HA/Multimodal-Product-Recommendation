'use strict';

const app = require('./app');
const config = require('./config');

const server = app.listen(config.port, () => {
  // eslint-disable-next-line no-console
  console.log(`API listening on port ${config.port}`);
  // eslint-disable-next-line no-console
  console.log(`ML service: ${config.mlServiceUrl}`);
});

function shutdown(signal) {
  // eslint-disable-next-line no-console
  console.log(`${signal} received — shutting down`);
  server.close(() => {
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10_000).unref();
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
