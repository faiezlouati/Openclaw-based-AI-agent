require('dotenv').config();
const https = require('https');
const fs   = require('fs');

//config 
const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const GROQ_MODEL   = "llama-3.3-70b-versatile";

// Output helpers — detect TTY vs non-TTY for bold + line width
const IS_TTY = process.stdout.isTTY;
const BOLD   = IS_TTY ? (text) => `\x1b[1m${text}\x1b[0m` : (text) => `**${text}**`;
const WIDTH  = (process.stdout.columns && process.stdout.columns > 10) ? process.stdout.columns : 35;
const LINE  = (char = '─') => char.repeat(WIDTH);

function today() {
  return new Date().toISOString().slice(0,10);
}

// Cache config
const CACHE_DIR   = '/tmp/tuneps_cache';
const CACHE_TTL_MS = 30 * 24 * 60 * 60 * 1000; // 1 month

function getCacheKey() {
  const crypto = require('crypto');
  const key = [DATE_FROM, DATE_TO, BUYER_FILTER, DEADLINE_DAYS].join('|');
  return crypto.createHash('md5').update(key).digest('hex');
}

function cacheGet(key) {
  try {
    const file = `${CACHE_DIR}/${key}.json`;
    if (!require('fs').existsSync(file)) return null;
    const stat = require('fs').statSync(file);
    if (Date.now() - stat.mtimeMs > CACHE_TTL_MS) return null;
    return require(file);
  } catch { return null; }
}

function cacheSet(key, data) {
  try {
    require('fs').mkdirSync(CACHE_DIR, { recursive: true });
    require('fs').writeFileSync(`${CACHE_DIR}/${key}.json`, JSON.stringify(data, null, 2));
  } catch {}
}

const DATE_FROM     = process.argv[2] || today();
const DATE_TO       = process.argv[3] || DATE_FROM;
const BUYER_FILTER  = process.argv[4] || "";
const DEADLINE_DAYS = parseInt(process.argv[5]) || 0;

// Handle --output flag: redirects stdout to a file instead of terminal
let outputFile = null;
const remainingArgs = process.argv.slice(6);
const outputIdx = remainingArgs.indexOf('--output');
if (outputIdx !== -1 && remainingArgs[outputIdx + 1]) {
  outputFile = remainingArgs[outputIdx + 1];
}

// If outputFile set, override console.log to write synchronously to file
if (outputFile) {
  const ffs = require('fs');
  ffs.writeFileSync(outputFile, ''); // clear file first
  console.log = (...args) => ffs.appendFileSync(outputFile, args.join(' ') + '\n');
  console.error = (...args) => ffs.appendFileSync(outputFile, args.join(' ') + '\n');
}

//company profile

const COMPANY_PROFILE = `You are a bid analyst for a premium ICT infrastructure provider.
The company ONLY bids on:

CORE BUSINESS (ALWAYS RELEVANT):
- IP networks (core routers, aggregation switches, access switches)
- Telecom infrastructure (4G/5G RAN, microwave transmission, fiber optics, GPON/EPON)
- Cloud & Data Center (private cloud, public cloud, hyper-converged infrastructure, storage arrays)
- Compute & Hosting platforms (servers, virtualization, platform infrastructure, application hosting)
- Cybersecurity (firewalls, IPS/IDS, anti-DDoS, zero-trust solutions)
- Enterprise communication (IPT, UC, contact centers)
- AI platforms and computing infrastructure (AI servers, GPU clusters)

NOT RELEVANT (DO NOT BID):
- Standard computers (PCs, laptops, desktops, workstations)
- Printers, scanners, photocopiers
- Office furniture or supplies
- Medical equipment of any kind
- Food, catering, cleaning services
- Construction materials or civil works
- Vehicles (cars, trucks, buses, motorcycles)
- White goods (air conditioners, refrigerators, unless industrial)
- Simple cabling or electrical works (unless part of a network project)
- CCTV cameras (unless part of a smart city or network project)

EXCEPTION: A tender that includes "network infrastructure", "IT infrastructure", "telecom infrastructure",
"cloud infrastructure", or "data center infrastructure" is ALWAYS RELEVANT, even if it also
includes other items.

Tenders for "computer equipment" or "bureautique" are NOT RELEVANT.

Return ONLY a JSON array of the numbers of relevant tenders.
Example: [1, 3, 5] or [] if none. Only the array. Nothing else.`;

// http helpers

function groqRequest(body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request({
      hostname: 'api.groq.com',
      path: '/openai/v1/chat/completions',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GROQ_API_KEY}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      }
    }, res => {
      let raw = '';
      res.on('data', c => raw += c);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(raw);
          resolve(parsed);
        } catch(e) {
          reject(new Error('JSON parse error'));
        }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function translateText(text) {
  if (!text || text === 'N/A' || text === 'Sans titre') return text;
  if (!GROQ_API_KEY) return text;
  try {
    const res = await groqRequest({
      model: GROQ_MODEL,
      messages: [{
        role: 'user',
        content: `Translate the following French text to English. Return ONLY the English translation, nothing else:\n\n"${text.replace(/"/g, '\\"')}"`
      }],
      max_tokens: 256,
      temperature: 0,
    });
    const en = res.choices?.[0]?.message?.content?.trim();
    return en || text;
  } catch {
    return text;
  }
}

function httpsPost(hostname, path, body, headers={}) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request({
      hostname, path, method: 'POST',
      rejectUnauthorized: false,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data),
        ...headers
      }
    }, res => {
      let raw = '';
      res.on('data', c => raw += c);
      res.on('end', () => {
        try { resolve(JSON.parse(raw)); }
        catch(e) { reject(new Error('JSON parse error')); }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function httpsGet(hostname, path) {
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname, path, method: 'GET',
      rejectUnauthorized: false,
      headers: { 'Content-Type': 'application/json' }
    }, res => {
      let raw = '';
      res.on('data', c => raw += c);
      res.on('end', () => {
        try { resolve(JSON.parse(raw)); }
        catch(e) { reject(new Error('JSON parse error')); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

//  filters

function applyFilters(tenders) {
  let filtered = tenders;

  // Filter 1 — by buyer name 
  if (BUYER_FILTER) {
    const buyers = BUYER_FILTER.toLowerCase().split('|').map(b => b.trim());
    filtered = filtered.filter(t => {
      const authority = (t.bidInstNm || "")
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
      return buyers.some(buyer => {
        const normalizedBuyer = buyer
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '');
        return authority.includes(normalizedBuyer);
      });
    });
  }

  // Filter 2 — by deadline 
  if (DEADLINE_DAYS !== 0) {
    const now = new Date();
    filtered = filtered.filter(t => {
      if (!t.bdRecvEndDt) return true;
      const deadline = new Date(t.bdRecvEndDt);
      if (DEADLINE_DAYS > 0) {
        const future = new Date();
        future.setDate(future.getDate() + DEADLINE_DAYS);
        return deadline >= now && deadline <= future;
      } else {
        const past = new Date();
        past.setDate(past.getDate() + DEADLINE_DAYS);
        return deadline >= past && deadline <= now;
      }
    });
  }

  return filtered;
}

//  STEP 1: FETCH ALL TENDE
async function fetchTenders() {
  const allTenders = [];
  let page = 0;

  while (true) {
    const body = {
      listSort: [], listCol: [],
      dataSearch: [
        { key: "publicYn", value: "Y",        specificSearch: "=" },
        { key: "publicDt", value: DATE_FROM,  specificSearch: ">=" },
        { key: "publicDt", value: DATE_TO,    specificSearch: "<=" },
        ...(
          BUYER_FILTER && !BUYER_FILTER.includes('|')
            ? [{ key: "bidInstNm", value: BUYER_FILTER, specificSearch: "like" }]
            : []
        )
      ],
      pagination: { limit: 50, offSet: page },
      sort: { nameCol: "publicDt", direction: "desc nulls last" }
    };

    const data = await httpsPost('www.tuneps.tn', '/api2/portail/bid/master/data', body);
    const list  = data?.payload?.data || data?.data || [];
    const total = data?.payload?.total || 0;

    if (!Array.isArray(list) || list.length === 0) break;
    allTenders.push(...list);

    // Stop when we have fetched all available tenders
    if (allTenders.length >= total || list.length < 50) break;

    page++;
  }

  return allTenders;
}

// STEP 2: AI FILTERI
async function filterWithLLM(tenders) {
  if (tenders.length === 0) return [];

  const BATCH_SIZE = 20;
  const relevant = [];

  for (let b = 0; b < tenders.length; b += BATCH_SIZE) {
    const batch = tenders.slice(b, b + BATCH_SIZE);

    const list = batch.map((t, i) => {
      const title = t.bidNmFr || t.bidNmEn || t.bidNmAr || "Sans titre";
      const org   = t.bidInstNm || "";
      return `${i+1}. ${title} | ${org}`;
    }).join("\n");

    const prompt = `${COMPANY_PROFILE}

Analyze these ${batch.length} tenders and return ONLY a JSON array with the numbers of relevant tenders.

Tenders list:
${list}

Return format example: [1, 3, 5] or [] if none.
Return ONLY the JSON array, nothing else.`;

    const body = {
      model: GROQ_MODEL,
      messages: [
        {
          role: "system",
          content: "You are a precise JSON output generator. Always respond with ONLY valid JSON arrays, no other text."
        },
        {
          role: "user",
          content: prompt
        }
      ],
      temperature: 0,
      max_tokens: 200
    };

    try {
      const response = await groqRequest(body);
      const text = response?.choices?.[0]?.message?.content || "";

      let arrayMatch = text.match(/\[[\s\d,]*\]/);
      if (!arrayMatch) {
        const numbers = text.match(/\d+/g);
        if (numbers && numbers.length > 0) {
          arrayMatch = [`[${numbers.join(', ')}]`];
        }
      }

      if (arrayMatch) {
        const indices = JSON.parse(arrayMatch[0]);
        const batchRelevant = indices
          .filter(i => i >= 1 && i <= batch.length)
          .map(i => batch[i - 1])
          .filter(Boolean);
        relevant.push(...batchRelevant);
      }

      if (b + BATCH_SIZE < tenders.length) {
        await delay(1000);
      }

    } catch(e) {
      await delay(3000);
    }
  }

  return relevant;
}

// STEP 3: FETCH DETAILS
async function fetchDetail(tender) {
  const id = tender.epBidMasterId || tender.bidNo;
  try {
    const data = await httpsGet(
      'www.tuneps.tn',
      `/api2/portail/bid/master/${id}`
    );

    const tenderData = data?.payload || data?.data || data || {};

    let lotInfo = [];
    try {
      const lotData = await httpsGet(
        'www.tuneps.tn',
        `/api2/portail/vBidCls/lot?bidNo=${tender.bidNo || id}`
      );
      lotInfo = lotData?.payload || [];
    } catch(e) {}

    const guarantees = lotInfo.map(lot => {
      let guarantee = null;
      if (lot.epBidMulCls) {
        guarantee = lot.epBidMulCls;
      } else if (lot.guaranteeAmount && lot.guaranteeAmount > 0) {
        guarantee = `${lot.guaranteeAmount.toLocaleString()} TND`;
      }
      return guarantee;
    }).filter(g => g !== null);

    tenderData._guarantees = guarantees;
    tenderData._lotCount   = guarantees.length;

    return tenderData;

  } catch(e) {
    return {};
  }
}

// STEP 4: DISPLAY RESULTS (TEXT)
async function displayResultsText(relevant, details, totalFetched, executionTime) {
  const date = new Date().toLocaleDateString('fr-TN');

  console.log();
  console.log('TUNEPS TENDER INTELLIGENCE REPORT');
  console.log(`${BOLD('Period')}  : ${DATE_FROM}  to  ${DATE_TO}`);
  if (BUYER_FILTER)  console.log(`${BOLD('Buyer')}   : ${BUYER_FILTER}`);
  if (DEADLINE_DAYS) console.log(`Deadline: ${DEADLINE_DAYS > 0 ? `next ${DEADLINE_DAYS} days` : `expired last ${Math.abs(DEADLINE_DAYS)} days`}`);
  console.log(`${BOLD('Scanned')} : ${totalFetched} tender(s) fetched `);
  console.log(`${BOLD('Date')}    : ${date}`);
  console.log(`${BOLD('Results')} : ${relevant.length} relevant tender(s) identified`);
  console.log();

  if (relevant.length === 0) {
    console.log('No relevant tenders found for the specified period and criteria.');
    console.log();
    return;
  }

  for (const [idx, t] of relevant.entries()) {
    const d   = details[idx] || {};
    const ref = t.bidNo || '-';

    const title      = t.bidNmFr || t.bidNmEn || t.bidNmAr || 'N/A';
    const authority  = t.bidInstNm || d.bidInstNm || 'N/A';
    const pubDate    = d.publicDt  || t.publicDt  || 'N/A';
    const deadline   = t.bdRecvEndDt || d.bdRecvEndDt || 'N/A';
    const procedure  = d.procedureTypeStrFr  || d.procedureTypeStrEn  || 'N/A';
    const evaluation = d.evalMethodStrFr     || d.evalMethodStrEn     || 'N/A';
    const consortium = d.consorYnStrFr       || (d.consorYn === 'Y' ? 'Oui' : 'Non');
    const intl       = d.internationalBidYnStrFr || (d.internationalBidYn === 'Y' ? 'Oui' : 'Non');
    const guarantees = d._guarantees || [];

    const titleEn      = await translateText(title);
    const authorityEn  = await translateText(authority);

    const PROC_MAP = {
      'Appel d\'offres ouvert':        'Open Tender',
      'Appel d\'offres restreint':      'Restricted Tender',
      'Appel d\'offres national':       'National Open Tender',
      'Appel d\'offres international': 'International Open Tender',
      'Consultation':                   'Request for Quotation',
      'Marché négocié':                'Negotiated Procurement',
    };
    const EVAL_MAP = {
      'Moins disant':         'Lowest Compliant Bid',
      'Moins-disants':        'Lowest Compliant Bids',
      'Prix le plus bas':     'Lowest Price',
      'Meilleure rapport qualité/prix': 'Best Value for Money',
    };
    const translate = (val, map) => map[val] || val;
    const procEn  = translate(procedure,  PROC_MAP);
    const CONS_MAP  = { 'Oui': 'Yes', 'Non': 'No' };
    const INTL_MAP   = {
      'Oui':                              'Yes',
      'Non':                              'No',
      'Appel d\'offres national (part dinar)': 'National (TND only)',
      'Appel d\'offres international':     'International',
    };
    const evalEn  = translate(evaluation, EVAL_MAP);
    const consEn  = translate(consortium,  CONS_MAP);
    const intlEn  = translate(intl,        INTL_MAP);

    console.log(`${LINE()}`);
    console.log(`  ${BOLD(`TENDER ${String(idx + 1).padStart(2, '0')}  /  Ref:`)} ${ref}`);
    console.log(`${LINE()}`);
    console.log();
    console.log(`  ${BOLD('Title')}              : ${titleEn}`);
    console.log(`  ${BOLD('Authority')}          : ${authorityEn}`);
    console.log(`  ${BOLD('Publication Date')}   : ${pubDate}`);
    console.log(`  ${BOLD('Submission Deadline')}: ${deadline}`);
    console.log(`  ${BOLD('Procedure')}          : ${procEn}`);
    console.log(`  ${BOLD('Evaluation Method')}  : ${evalEn}`);
    console.log(`  ${BOLD('Consortium Allowed')} : ${consEn}`);
    console.log(`  ${BOLD('International Bid')} : ${intlEn}`);

    if (guarantees.length > 0) {
      console.log();
      console.log(`  ${BOLD('Provisional Guarantee')}:`);
      guarantees.forEach((g, i) => {
        console.log(`    ${BOLD(`Lot ${i + 1}`)} : ${g}`);
      });
    }

    console.log();
    console.log(`  ${BOLD('URL')} : https://www.tuneps.tn/portail/offres/details/${t.epBidMasterId}/${ref}`);

  }

  console.log(`${LINE()}`);
  console.log(`  ${relevant.length} tender(s) displayed  |  Execution time: ${executionTime}s`);
  console.log(`${LINE()}`);
  console.log();
}

// STEP 4: DISPLAY RESULTS (JSON)
function displayResultsJSON(relevant, details, totalFetched, executionTime) {
  const tenders = relevant.map((t, idx) => {
    const d   = details[idx] || {};
    const ref = t.bidNo || '-';
    const title      = t.bidNmFr || t.bidNmEn || t.bidNmAr || 'N/A';
    const authority  = t.bidInstNm || d.bidInstNm || 'N/A';
    const pubDate    = d.publicDt  || t.publicDt  || null;
    const deadline   = t.bdRecvEndDt || d.bdRecvEndDt || null;
    const procedure  = d.procedureTypeStrFr  || d.procedureTypeStrEn  || 'N/A';
    const evaluation = d.evalMethodStrFr     || d.evalMethodStrEn     || 'N/A';
    const consortium = d.consorYn === 'Y' ? true : false;
    const intl       = d.internationalBidYn === 'Y' ? true : false;
    const guarantees = (d._guarantees || []).map((g, i) => ({ lot: i + 1, amount: g }));

    return {
      ref,
      authority,
      title,
      published: pubDate,
      deadline,
      procedure,
      evaluation,
      consortium,
      international: intl,
      guarantees,
      url: `https://www.tuneps.tn/portail/offres/details/${t.epBidMasterId}/${ref}`
    };
  });

  const result = {
    date: new Date().toISOString().slice(0,10),
    period: { from: DATE_FROM, to: DATE_TO },
    buyer: BUYER_FILTER || null,
    totalScanned: totalFetched,
    results: tenders.length,
    executionTimeSeconds: executionTime,
    tenders
  };

  console.log(JSON.stringify(result, null, 2));
}

// MAIN 
async function main() {
  if (!GROQ_API_KEY) {
    console.error("ERROR: GROQ_API_KEY not set. Add to .env file: GROQ_API_KEY=your-key");
    process.exit(1);
  }

  const start = Date.now();

  // Check cache first
  const cacheKey = getCacheKey();
  const cached = cacheGet(cacheKey);
  if (cached) {
    // Restore and display cached text directly
    if (outputFile) {
      require('fs').writeFileSync(outputFile, cached.text);
    } else {
      console.log(cached.text);
    }
    return;
  }

  // Step 1 — fetch ALL tenders (no page limit)
  const apiTenders = await fetchTenders();
  const totalFetched = apiTenders.length;

  // Step 1b — apply code filters (buyer + deadline, independent)
  const tenders = applyFilters(apiTenders);

  if (tenders.length === 0) {
    console.log();
    console.log('TUNEPS TENDER INTELLIGENCE REPORT');
    console.log(`${BOLD('Period')}  : ${DATE_FROM}  to  ${DATE_TO}`);
    if (BUYER_FILTER)  console.log(`${BOLD('Buyer')}   : ${BUYER_FILTER}`);
    if (DEADLINE_DAYS) console.log(`Deadline: ${DEADLINE_DAYS > 0 ? `next ${DEADLINE_DAYS} days` : `expired last ${Math.abs(DEADLINE_DAYS)} days`}`);
    console.log(`${BOLD('Scanned')} : ${totalFetched} tender(s) fetched from API`);
    console.log(`${BOLD('Date')}    : ${new Date().toLocaleDateString('fr-TN')}`);
    console.log(`${BOLD('Results')} : 0 relevant tender(s) identified`);
    console.log();
    console.log('No tenders matched the specified filters.');
    console.log();
    return;
  }

  // Step 2 — AI relevance filter
  const aiRelevant = await filterWithLLM(tenders);

  if (aiRelevant.length === 0) {
    const executionTime = ((Date.now() - start) / 1000).toFixed(1);
    console.log();
    console.log('TUNEPS TENDER INTELLIGENCE REPORT');
    console.log(`${BOLD('Period')}  : ${DATE_FROM}  to  ${DATE_TO}`);
    if (BUYER_FILTER)  console.log(`${BOLD('Buyer')}   : ${BUYER_FILTER}`);
    if (DEADLINE_DAYS) console.log(`Deadline: ${DEADLINE_DAYS > 0 ? `next ${DEADLINE_DAYS} days` : `expired last ${Math.abs(DEADLINE_DAYS)} days`}`);
    console.log(`${BOLD('Scanned')} : ${totalFetched} tender(s) fetched from API`);
    console.log(`${BOLD('Date')}    : ${new Date().toLocaleDateString('fr-TN')}`);
    console.log(`${BOLD('Results')} : 0 relevant tender(s) identified`);
    console.log();
    console.log('No relevant tenders found for the specified period and criteria.');
    console.log();
    console.log(`${LINE()}`);
    console.log(`  0 tender(s) displayed  |  Execution time: ${executionTime}s`);
    console.log(`${LINE()}`);
    console.log();
    return;
  }

  // Step 3 — fetch details for relevant only
  const details = [];
  for (const t of aiRelevant) {
    const d = await fetchDetail(t);
    details.push(d);
  }

  // Step 4 — display
  const executionTime = ((Date.now() - start) / 1000).toFixed(1);
  await displayResultsText(aiRelevant, details, totalFetched, executionTime);

  // Get the text that was just printed (read from the output file if set, otherwise already in buffer)
  let text = '';
  if (outputFile) {
    text = require('fs').readFileSync(outputFile, 'utf8');
  }

  // Cache the full output text
  cacheSet(cacheKey, { cachedAt: new Date().toISOString(), text });
}

main().catch(e => {
  console.error("\nFatal error:", e.message);
  process.exit(1);
});
