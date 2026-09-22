'use strict';

const express = require('express');
const { z } = require('zod');
const { getProducts, getCatalogStats } = require('../services/mlClient');

const router = express.Router();

const productsQuerySchema = z.object({
  limit: z
    .string()
    .optional()
    .transform((v) => {
      if (v === undefined || v === '') return 40;
      const n = Number.parseInt(v, 10);
      if (Number.isNaN(n) || n < 1 || n > 200) {
        throw new z.ZodError([
          {
            code: 'custom',
            path: ['limit'],
            message: 'limit must be an integer between 1 and 200',
          },
        ]);
      }
      return n;
    }),
  gender: z.string().trim().max(64).optional(),
  slot: z.string().trim().max(64).optional(),
});

/**
 * GET /api/catalog/products?limit=&gender=&slot=
 * Proxies to ML /catalog/products
 */
router.get('/products', async (req, res, next) => {
  try {
    const parsed = productsQuerySchema.parse(req.query ?? {});

    const params = {
      limit: parsed.limit,
      ...(parsed.gender ? { gender: parsed.gender } : {}),
      ...(parsed.slot ? { slot: parsed.slot } : {}),
    };

    const data = await getProducts(params);

    // Normalize to a stable list shape without leaking internals
    if (Array.isArray(data)) {
      return res.status(200).json({ products: data, count: data.length });
    }

    if (data && typeof data === 'object') {
      const products = Array.isArray(data.products)
        ? data.products
        : Array.isArray(data.items)
          ? data.items
          : [];
      return res.status(200).json({
        products,
        count: typeof data.count === 'number' ? data.count : products.length,
      });
    }

    return res.status(200).json({ products: [], count: 0 });
  } catch (err) {
    next(err);
  }
});

/**
 * GET /api/catalog/stats
 * Proxies to ML /catalog/stats — catalog counts.
 */
router.get('/stats', async (_req, res, next) => {
  try {
    const data = await getCatalogStats();
    const stats = data && typeof data === 'object' ? data : {};

    res.status(200).json({
      total: stats.total ?? stats.count ?? 0,
      by_gender: stats.by_gender ?? stats.byGender ?? {},
      by_slot: stats.by_slot ?? stats.bySlot ?? {},
      ...(stats.extra && typeof stats.extra === 'object' ? { extra: stats.extra } : {}),
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
