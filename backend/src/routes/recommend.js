'use strict';

const express = require('express');
const { z } = require('zod');
const { recommend } = require('../services/mlClient');

const router = express.Router();

const recommendSchema = z.object({
  query: z
    .string({ required_error: 'query is required' })
    .trim()
    .min(1, 'query must not be empty')
    .max(2000, 'query must be at most 2000 characters'),
  gender: z
    .string()
    .trim()
    .max(64)
    .optional(),
  occasion: z
    .string()
    .trim()
    .max(128)
    .optional(),
  budget: z
    .union([z.number(), z.string()])
    .optional()
    .transform((v) => {
      if (v === undefined || v === null || v === '') return undefined;
      const n = typeof v === 'number' ? v : Number(v);
      if (Number.isNaN(n) || n < 0) {
        throw new z.ZodError([
          {
            code: 'custom',
            path: ['budget'],
            message: 'budget must be a non-negative number',
          },
        ]);
      }
      return n;
    }),
  k: z
    .union([z.number().int(), z.string()])
    .optional()
    .transform((v) => {
      if (v === undefined || v === null || v === '') return 8;
      const n = typeof v === 'number' ? v : Number.parseInt(String(v), 10);
      if (Number.isNaN(n) || n < 1 || n > 50) {
        throw new z.ZodError([
          {
            code: 'custom',
            path: ['k'],
            message: 'k must be an integer between 1 and 50',
          },
        ]);
      }
      return n;
    }),
}).strict();

/**
 * Normalize ML recommend response into a stable public shape.
 * @param {object} data
 * @param {object} requestEcho
 */
function normalizeRecommendResponse(data, requestEcho) {
  const raw = data && typeof data === 'object' ? data : {};

  const outfits = Array.isArray(raw.outfits)
    ? raw.outfits
    : Array.isArray(raw.recommendations)
      ? raw.recommendations
      : Array.isArray(raw.items)
        ? raw.items
        : [];

  return {
    query: requestEcho.query,
    gender: requestEcho.gender ?? null,
    occasion: requestEcho.occasion ?? null,
    budget: requestEcho.budget ?? null,
    k: requestEcho.k,
    outfits,
    rationale: raw.rationale ?? raw.explanation ?? null,
    meta: {
      source: 'ml',
      ...(raw.meta && typeof raw.meta === 'object' ? raw.meta : {}),
    },
  };
}

/**
 * POST /api/recommend
 * Validate body, forward to ML /recommend, return normalized JSON.
 */
router.post('/', async (req, res, next) => {
  try {
    const parsed = recommendSchema.parse(req.body ?? {});

    const payload = {
      query: parsed.query,
      ...(parsed.gender !== undefined ? { gender: parsed.gender } : {}),
      ...(parsed.occasion !== undefined ? { occasion: parsed.occasion } : {}),
      ...(parsed.budget !== undefined ? { budget: parsed.budget } : {}),
      k: parsed.k,
    };

    const data = await recommend(payload);
    const normalized = normalizeRecommendResponse(data, payload);

    res.status(200).json(normalized);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
