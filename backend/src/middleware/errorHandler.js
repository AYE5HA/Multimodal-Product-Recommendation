'use strict';

const { ZodError } = require('zod');
const config = require('../config');

/**
 * Map axios / upstream errors into a safe client-facing shape.
 * Never expose secrets, stack traces (in production), or raw upstream bodies
 * that might contain credentials.
 */
function errorHandler(err, _req, res, _next) {
  // Zod validation
  if (err instanceof ZodError) {
    return res.status(400).json({
      error: 'validation_error',
      message: 'Request validation failed',
      details: err.errors.map((e) => ({
        path: e.path.join('.'),
        message: e.message,
      })),
    });
  }

  // Explicit AppError
  if (err.status && err.code) {
    return res.status(err.status).json({
      error: err.code,
      message: err.message || 'Request failed',
    });
  }

  // Axios upstream errors from ML service
  if (err.isAxiosError) {
    if (err.code === 'ECONNABORTED' || err.code === 'ETIMEDOUT') {
      return res.status(504).json({
        error: 'ml_timeout',
        message: 'ML service did not respond in time',
      });
    }

    if (err.code === 'ECONNREFUSED' || err.code === 'ENOTFOUND' || !err.response) {
      return res.status(502).json({
        error: 'ml_unavailable',
        message: 'ML service is unavailable',
      });
    }

    const status = err.response.status >= 400 && err.response.status < 600
      ? err.response.status
      : 502;

    const upstreamMessage =
      (err.response.data &&
        typeof err.response.data === 'object' &&
        (err.response.data.detail || err.response.data.message || err.response.data.error)) ||
      'ML service returned an error';

    return res.status(status).json({
      error: 'ml_error',
      message: typeof upstreamMessage === 'string' ? upstreamMessage : 'ML service returned an error',
    });
  }

  // Fallback
  if (config.nodeEnv !== 'production') {
    // eslint-disable-next-line no-console
    console.error(err);
  }

  return res.status(500).json({
    error: 'internal_error',
    message: 'An unexpected error occurred',
  });
}

/**
 * Create a typed application error.
 * @param {number} status
 * @param {string} code
 * @param {string} message
 */
function createError(status, code, message) {
  const err = new Error(message);
  err.status = status;
  err.code = code;
  return err;
}

module.exports = { errorHandler, createError };
