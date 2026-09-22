'use strict';

const express = require('express');
const path = require('path');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const config = require('./config');
const { errorHandler } = require('./middleware/errorHandler');

const healthRouter = require('./routes/health');
const recommendRouter = require('./routes/recommend');
const catalogRouter = require('./routes/catalog');

const app = express();

app.use(helmet());
app.use(
  cors({
    origin: config.corsOrigin === '*' ? true : config.corsOrigin.split(',').map((s) => s.trim()),
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  })
);
app.use(morgan(config.nodeEnv === 'production' ? 'combined' : 'dev'));
app.use(express.json({ limit: '1mb' }));
app.use('/data', express.static(process.env.DATA_DIR || path.resolve(process.cwd(), '../data'), { fallthrough: false }));

app.get('/', (_req, res) => {
  res.json({
    name: 'multimodal-product-recommendation-api',
    version: '1.0.0',
  });
});

app.use('/api/health', healthRouter);
app.use('/api/recommend', recommendRouter);
app.use('/api/catalog', catalogRouter);

app.use((_req, res) => {
  res.status(404).json({
    error: 'not_found',
    message: 'Route not found',
  });
});

app.use(errorHandler);

module.exports = app;
