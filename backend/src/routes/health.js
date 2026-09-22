'use strict';

const express = require('express');
const { checkHealth } = require('../services/mlClient');

const router = express.Router();

/**
 * GET /api/health
 * Aggregated health of this API and the downstream ML service.
 */
router.get('/', async (_req, res, next) => {
  try {
    const ml = await checkHealth();
    const healthy = ml === 'ok';

    res.status(healthy ? 200 : 503).json({
      status: healthy ? 'ok' : 'degraded',
      services: {
        ml,
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
