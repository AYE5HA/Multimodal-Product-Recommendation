'use strict';

require('dotenv').config();

const config = {
  port: Number(process.env.PORT) || 4000,
  mlServiceUrl: (process.env.ML_SERVICE_URL || 'http://ml:8000').replace(/\/$/, ''),
  openRouterApiKey: process.env.OPENROUTER_API_KEY || '',
  corsOrigin: process.env.CORS_ORIGIN || '*',
  nodeEnv: process.env.NODE_ENV || 'development',
};

module.exports = config;
