'use strict';

const axios = require('axios');
const config = require('../config');

const mlClient = axios.create({
  baseURL: config.mlServiceUrl,
  timeout: 120_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

/**
 * Check whether the ML service is reachable.
 * @returns {Promise<'ok'|'unavailable'>}
 */
async function checkHealth() {
  try {
    const res = await mlClient.get('/health', { timeout: 5_000 });
    if (res.status >= 200 && res.status < 300) {
      return 'ok';
    }
    return 'unavailable';
  } catch {
    return 'unavailable';
  }
}

/**
 * POST /recommend on the ML service.
 * @param {object} payload
 * @returns {Promise<object>}
 */
async function recommend(payload) {
  const res = await mlClient.post('/recommend', payload);
  return res.data;
}

/**
 * GET /catalog/products on the ML service.
 * @param {Record<string, string|number|undefined>} params
 * @returns {Promise<object>}
 */
async function getProducts(params) {
  const res = await mlClient.get('/catalog/products', { params });
  return res.data;
}

/**
 * GET /catalog/stats on the ML service.
 * @returns {Promise<object>}
 */
async function getCatalogStats() {
  const res = await mlClient.get('/catalog/stats');
  return res.data;
}

module.exports = {
  mlClient,
  checkHealth,
  recommend,
  getProducts,
  getCatalogStats,
};
