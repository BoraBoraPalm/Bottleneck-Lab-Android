// Bottleneck Lab · Kurs auf Knopfdruck (Cloudflare Worker, Gratis-Tarif)
// Liefert ausschließlich abgeschlossene Yahoo-Tagesschlusskurse für ein
// Börsensymbol, im selben Format wie docs/charts/<TICKER>.json. Kein offener
// Proxy: feste Zieladresse, strenge Symbolprüfung, Browserzugriff nur von der
// Website. "expires" sagt, bis wann sich kein neuer Schlusskurs ergeben kann;
// so lange darf die App die Antwort wiederverwenden. "context" enthält Trend-,
// Crash- und ATR-Werte nach denselben Regeln wie scripts/trade_guidance.py.
const SITE = "https://boraborapalm.github.io";
const SYMBOL = /^[A-Z0-9][A-Z0-9.\-]{0,19}$/;
const SETTLE = 1800; // Sekunden nach Handelsschluss, bis der Schlusskurs als final gilt
export const VERSION = "2026-11-04.4"; // /version zeigt, welche Fassung Cloudflare ausliefert
const LOG_DAYS = 45, LOG_SIZE = 500;

// Merkt sich, welche Aktien in der Suche geladen wurden (Durable Object mit
// SQLite, Gratis-Tarif). Der GitHub-Datenlauf liest /requested und prüft diese
// Aktien zuerst vollständig, mit Fundamentaldaten. Nur Börsensymbole, keine
// Personen- oder Gerätedaten.
export class RequestLog {
  constructor(ctx) {
    this.sql = ctx.storage.sql;
    this.sql.exec("CREATE TABLE IF NOT EXISTS requested (symbol TEXT PRIMARY KEY, last INTEGER NOT NULL, hits INTEGER NOT NULL)");
  }
  async fetch(request) {
    const url = new URL(request.url), now = Date.now();
    if (url.pathname === "/add") {
      const symbol = url.searchParams.get("symbol") || "";
      if (!SYMBOL.test(symbol)) return new Response("symbol", { status: 400 });
      this.sql.exec("INSERT INTO requested (symbol, last, hits) VALUES (?, ?, 1) ON CONFLICT(symbol) DO UPDATE SET last = excluded.last, hits = hits + 1", symbol, now);
      this.sql.exec("DELETE FROM requested WHERE last < ?", now - LOG_DAYS * 86400000);
      this.sql.exec("DELETE FROM requested WHERE symbol NOT IN (SELECT symbol FROM requested ORDER BY last DESC LIMIT ?)", LOG_SIZE);
      return new Response("ok");
    }
    if (url.pathname === "/list") {
      const rows = this.sql.exec("SELECT symbol, last, hits FROM requested ORDER BY last DESC LIMIT ?", LOG_SIZE).toArray();
      return Response.json({ version: 1, days: LOG_DAYS,
        symbols: rows.map(r => ({ symbol: r.symbol, last: new Date(r.last).toISOString(), hits: r.hits })) });
    }
    return new Response("path", { status: 404 });
  }
}

const requestLog = env => env && env.REQUESTS ? env.REQUESTS.get(env.REQUESTS.idFromName("search-log")) : null;

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin");
    if (origin && origin !== SITE) return reply({ error: "origin" }, 403, null);
    const cors = origin ? SITE : null;
    if (request.method === "OPTIONS") return reply(null, 204, cors);
    if (request.method !== "GET") return reply({ error: "method" }, 405, cors);
    const url = new URL(request.url);
    if (url.pathname === "/version")
      return reply({ version: VERSION, features: ["context", "turnover", "expires"].concat(requestLog(env) ? ["requested"] : []) }, 200, cors);
    if (url.pathname === "/requested") {
      const log = requestLog(env);
      if (!log) return reply({ version: 1, symbols: [] }, 200, cors);
      const listed = await log.fetch("https://log/list");
      return reply(await listed.json(), listed.status, cors);
    }
    if (url.pathname !== "/quote") return reply({ error: "path" }, 404, cors);
    const symbol = (url.searchParams.get("symbol") || "").toUpperCase();
    if (!SYMBOL.test(symbol)) return reply({ error: "symbol" }, 400, cors);
    let status = "unavailable";
    for (const host of ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]) {
      try {
        const upstream = await fetch(
          `https://${host}/v8/finance/chart/${encodeURIComponent(symbol)}?range=10y&interval=1d`,
          { headers: { "User-Agent": "Mozilla/5.0 (compatible; BottleneckLab/1.0)", Accept: "application/json" } });
        if (!upstream.ok) { status = "upstream_" + upstream.status; continue; }
        const chart = convert(symbol, await upstream.json(), Date.now() / 1000);
        if (chart) {
          const log = requestLog(env);
          if (log && ctx) ctx.waitUntil(log.fetch("https://log/add?symbol=" + encodeURIComponent(symbol)).catch(() => null));
          return reply(chart, 200, cors, chart.max_age);
        }
        status = "no_data";
      } catch (error) {
        status = "upstream_error";
      }
    }
    return reply({ error: status }, 502, cors);
  }
};

const isoDay = (epoch, offset) => new Date((epoch + offset) * 1000).toISOString().slice(0, 10);

export function convert(symbol, data, now) {
  const r = data && data.chart && data.chart.result && data.chart.result[0];
  const ts = r && r.timestamp;
  const q = r && r.indicators && r.indicators.quote && r.indicators.quote[0];
  const adj = r && r.indicators && r.indicators.adjclose && r.indicators.adjclose[0] && r.indicators.adjclose[0].adjclose;
  if (!Array.isArray(ts) || !q || !Array.isArray(q.close)) return null;
  const meta = r.meta || {};
  const offset = Number.isFinite(meta.gmtoffset) ? meta.gmtoffset : 0;
  const session = meta.currentTradingPeriod && meta.currentTradingPeriod.regular;
  const known = session && Number.isFinite(session.start) && Number.isFinite(session.end) && session.end > session.start;
  // While today's session is open (or just closed), its bar is not a final close.
  const settled = known ? session.end + SETTLE : null;
  const openDay = known && now < settled ? isoDay(session.start, offset) : null;
  const high = Array.isArray(q.high) ? q.high : [], low = Array.isArray(q.low) ? q.low : [];
  const volume = Array.isArray(q.volume) ? q.volume : [];
  const rows = [];
  for (let i = 0; i < ts.length; i++) {
    // Same bar filter as the pipeline: close, high and low positive and finite.
    const close = q.close[i], adjusted = Array.isArray(adj) ? adj[i] : close, h = high[i], l = low[i];
    if (!Number.isFinite(ts[i]) || ![close, adjusted, h, l].every(v => Number.isFinite(v) && v > 0)) continue;
    const day = isoDay(ts[i], offset);
    if (day === openDay) continue;
    // Yahoo may append a second bar for the same session: keep the latest.
    if (rows.length && rows[rows.length - 1][0] >= day) rows.pop();
    rows.push([day, close, adjusted, h, l, Number.isFinite(volume[i]) ? volume[i] : 0]);
  }
  if (rows.length < 30) return null;
  const last = rows[rows.length - 1], scale = last[1] / last[2];
  if (!Number.isFinite(scale) || scale <= 0) return null;
  // Valid until the next close can be final: today's settle time, otherwise
  // the same time on the next day. Without session data: one hour.
  let expires = now + 3600;
  if (known) {
    expires = settled;
    while (expires <= now) expires += 86400;
  }
  const maxAge = Math.round(Math.max(300, Math.min(86400, expires - now)));
  return {
    version: 1, ticker: symbol, currency: typeof meta.currency === "string" ? meta.currency : null,
    asof: last[0], close: last[1], exchange: typeof meta.exchangeName === "string" ? meta.exchangeName : null,
    source: "Yahoo Finance", basis: "adjusted close normalized to latest raw close", live: true,
    fetched: new Date(now * 1000).toISOString(), expires: new Date((now + maxAge) * 1000).toISOString(), max_age: maxAge,
    context: priceContext(rows), turnover: turnover(rows),
    points: rows.map(([day, , adjusted]) => [day, Math.round(adjusted * scale * 1e6) / 1e6])
  };
}

const round = (value, digits) => Math.round(value * 10 ** digits) / 10 ** digits;

// Port of trade_guidance.price_context: rows are [day, raw close, adjusted close, high, low, volume].
export function priceContext(rows) {
  if (rows.length < 253) return null;
  const prices = [], ohlc = [];
  for (const [, raw, adj, hi, lo] of rows) {
    if (hi < lo) return null;
    const factor = adj / raw;
    prices.push(adj);
    ohlc.push([hi * factor, lo * factor, adj]);
  }
  const n = prices.length, last = prices[n - 1];
  const sma = prices.slice(-200).reduce((a, b) => a + b, 0) / 200;
  if (!(sma > 0)) return null;
  const ret21 = last / prices[n - 22] - 1;
  const peak = Math.max(...prices.slice(-252));
  const drawdown = last / peak - 1;
  let sum = 0;
  for (let i = n - 14; i < n; i++) {
    const [hi, lo] = ohlc[i], prev = ohlc[i - 1][2];
    sum += Math.max(hi - lo, Math.abs(hi - prev), Math.abs(lo - prev));
  }
  const raw = rows[n - 1][1], atrRaw = sum / 14 / last * raw;
  if (!Number.isFinite(atrRaw) || atrRaw <= 0) return null;
  return {
    sma200_ratio: round(last / sma - 1, 7), sma200_native: round(sma / last * raw, 6),
    crash_21_level_native: round(.85 * prices[n - 22] / last * raw, 6),
    crash_peak_level_native: round(.75 * peak / last * raw, 6),
    return_21d: round(ret21, 7), drawdown_252d: round(drawdown, 7), atr14_native: round(atrRaw, 6),
    crash_warning: ret21 <= -0.15 || drawdown <= -0.25, correction_warning: ret21 <= -0.08 || drawdown <= -0.15,
    risk_reference_native: round(Math.max(0, raw - 2.5 * atrRaw), 6),
    context_basis: "Yahoo adjusted OHLC, signal after close"
  };
}

// Like build_snapshot.quote: mean raw close x volume of the last 20 sessions, at least 12 with volume.
export function turnover(rows) {
  const values = rows.slice(-20).filter(r => r[5] > 0).map(r => r[1] * r[5]);
  return values.length >= 12 ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null;
}

function reply(body, status, cors, maxAge = 0) {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": maxAge ? `public, max-age=${maxAge}` : "no-store",
    "X-Content-Type-Options": "nosniff", Vary: "Origin"
  };
  if (cors) {
    headers["Access-Control-Allow-Origin"] = cors;
    headers["Access-Control-Allow-Methods"] = "GET, OPTIONS";
  }
  return new Response(body === null ? null : JSON.stringify(body), { status, headers });
}
