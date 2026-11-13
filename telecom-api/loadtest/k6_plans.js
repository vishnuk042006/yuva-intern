// Simulated IPL-season traffic against the busiest read endpoint (GET /api/v1/plans).
//
//   RATE_LIMIT_PER_MINUTE=1000000 docker compose up -d --build     # lift the per-IP limit
//   k6 run loadtest/k6_plans.js                                    # BASE_URL defaults to localhost:8000
//
// Pass criteria (matches the brief): 200 req/s sustained, p95 < 300 ms, <1% errors.
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
  scenarios: {
    steady_200rps: {
      executor: 'constant-arrival-rate',
      rate: 200, timeUnit: '1s', duration: '2m',
      preAllocatedVUs: 100, maxVUs: 400,
    },
    ipl_match_spike: {            // toss-time surge: 200 -> 400 rps
      executor: 'ramping-arrival-rate',
      startTime: '2m10s', startRate: 200, timeUnit: '1s',
      preAllocatedVUs: 200, maxVUs: 800,
      stages: [
        { target: 400, duration: '30s' },
        { target: 400, duration: '30s' },
        { target: 0, duration: '10s' },
      ],
    },
  },
  thresholds: {
    'http_req_failed{scenario:steady_200rps}': ['rate<0.01'],
    'http_req_duration{scenario:steady_200rps}': ['p(95)<300'],
    'http_req_duration{scenario:ipl_match_spike}': ['p(99)<1000'],   // informational headroom check
    checks: ['rate>0.99'],
  },
};

// A realistic mix: a few hot filter combinations (cache hits) plus some long-tail searches.
const QUERIES = [
  '?sort_by=price_inr',
  '?is_5g=true&sort_by=price_inr',
  '?min_data_gb=2&max_price=400',
  '?q=IPL',
  '?validity_days=28&sort_by=data_gb_per_day&order=desc',
  '?max_price=300&size=10',
  '?circle_id=1&is_5g=true',
];

export default function () {
  const longTail = Math.random() < 0.1
    ? `?min_price=${Math.floor(Math.random() * 300)}&size=${5 + Math.floor(Math.random() * 20)}`
    : null;
  const qs = longTail || QUERIES[Math.floor(Math.random() * QUERIES.length)];
  const res = http.get(`${BASE}/api/v1/plans${qs}`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'no server error': (r) => r.status < 500,
    'json items present': (r) => Array.isArray(r.json('items')),
  });
}
