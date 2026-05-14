require('dotenv').config();
const https = require('https');

//config 
const GROQ_API_KEY = process.env.GROQ_API_KEY || "";
const GROQ_MODEL   = "llama-3.3-70b-versatile";

function today() {
  return new Date().toISOString().slice(0,10);
}

const DATE_FROM     = process.argv[2] || today();
const DATE_TO       = process.argv[3] || DATE_FROM;
const BUYER_FILTER  = process.argv[4] || "";
const DEADLINE_DAYS = parseInt(process.argv[5]) || 0;

//company profile

const COMPANY_PROFILE = `You are a bid analyst for a premium ICT infrastructure provider.
The company ONLY bids on:

CORE BUSINESS (ALWAYS RELEVANT):
- IP networks (core routers, aggregation switches, access switches)
- Telecom infrastructure (4G/5G RAN, microwave transmission, fiber optics, GPON/EPON)
- Cloud & Data Center (private cloud, public cloud, hyper-converged infrastructure, storage arrays)
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

EXCEPTION: A tender that includes "network", "infrastructure", "cloud", "data center",
"telecom", "IP", "routing", "switching", "fiber", "5G", "4G", "cybersecurity", "firewall"
is ALWAYS RELEVANT, even if it also includes other items.

Tenders for "IT equipment" without specifying "network" or "infrastructure" are NOT RELEVANT.
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
        { key: "publicDt", value: DATE_TO,    specificSearch: "<=" }
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

// STEP 4: DISPLAY RESULTS 
function displayResults(relevant, details, totalFetched, executionTime) {
  const date = new Date().toLocaleDateString('fr-TN');

  console.log();
  console.log('TUNEPS TENDER INTELLIGENCE REPORT');
  console.log(`Period  : ${DATE_FROM}  to  ${DATE_TO}`);
  if (BUYER_FILTER)  console.log(`Buyer   : ${BUYER_FILTER}`);
  if (DEADLINE_DAYS) console.log(`Deadline: ${DEADLINE_DAYS > 0 ? `next ${DEADLINE_DAYS} days` : `expired last ${Math.abs(DEADLINE_DAYS)} days`}`);
  console.log(`Scanned : ${totalFetched} tender(s) fetched `);
  console.log(`Date    : ${date}`);
  console.log(`Results : ${relevant.length} relevant tender(s) identified`);
  console.log();

  if (relevant.length === 0) {
    console.log('No relevant tenders found for the specified period and criteria.');
    console.log();
    return;
  }

  relevant.forEach((t, idx) => {
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
    const url = `https://www.tuneps.tn/portail/offres/details/${t.epBidMasterId}/${t.bidNo}`;
    const guarantees = d._guarantees || [];

    console.log(`${'─'.repeat(40)}`);
    console.log(`  TENDER ${String(idx + 1).padStart(2, '0')}  /  Ref: ${ref}`);
    console.log(`${'─'.repeat(40)}`);
    console.log();
    console.log(`  Title              : ${title}`);
    console.log(`  Authority          : ${authority}`);
    console.log(`  Publication Date   : ${pubDate}`);
    console.log(`  Submission Deadline: ${deadline}`);
    console.log(`  Procedure          : ${procedure}`);
    console.log(`  Evaluation Method  : ${evaluation}`);
    console.log(`  Consortium Allowed : ${consortium}`);
    console.log(`  International Bid  : ${intl}`);

    if (guarantees.length > 0) {
      console.log();
      console.log(`  Guarantees (Cautionnement provisoire):`);
      guarantees.forEach((g, i) => {
        console.log(`    Lot ${i + 1} : ${g}`);
      });
    }

    console.log();
    console.log(`  URL : ${url}`);
    console.log();
  });

  console.log(`${'─'.repeat(40)}`);
  console.log(`  ${relevant.length} tender(s) displayed  |  Execution time: ${executionTime}s`);
  console.log(`${'─'.repeat(40)}`);
  console.log();
}

// MAIN 
async function main() {
  if (!GROQ_API_KEY) {
    console.error("ERROR: GROQ_API_KEY not set. Add to .env file: GROQ_API_KEY=your-key");
    process.exit(1);
  }

  const start = Date.now();

  // Step 1 — fetch ALL tenders (no page limit)
  const apiTenders = await fetchTenders();
  const totalFetched = apiTenders.length;

  // Step 1b — apply code filters (buyer + deadline, independent)
  const tenders = applyFilters(apiTenders);

  if (tenders.length === 0) {
    console.log();
    console.log('TUNEPS TENDER INTELLIGENCE REPORT');
    console.log(`Period  : ${DATE_FROM}  to  ${DATE_TO}`);
    if (BUYER_FILTER)  console.log(`Buyer   : ${BUYER_FILTER}`);
    if (DEADLINE_DAYS) console.log(`Deadline: ${DEADLINE_DAYS > 0 ? `next ${DEADLINE_DAYS} days` : `expired last ${Math.abs(DEADLINE_DAYS)} days`}`);
    console.log(`Scanned : ${totalFetched} tender(s) fetched from API`);
    console.log(`Date    : ${new Date().toLocaleDateString('fr-TN')}`);
    console.log(`Results : 0 relevant tender(s) identified`);
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
    console.log(`Period  : ${DATE_FROM}  to  ${DATE_TO}`);
    if (BUYER_FILTER)  console.log(`Buyer   : ${BUYER_FILTER}`);
    if (DEADLINE_DAYS) console.log(`Deadline: ${DEADLINE_DAYS > 0 ? `next ${DEADLINE_DAYS} days` : `expired last ${Math.abs(DEADLINE_DAYS)} days`}`);
    console.log(`Scanned : ${totalFetched} tender(s) fetched from API`);
    console.log(`Date    : ${new Date().toLocaleDateString('fr-TN')}`);
    console.log(`Results : 0 relevant tender(s) identified`);
    console.log();
    console.log('No relevant tenders found for the specified period and criteria.');
    console.log();
    console.log(`${'─'.repeat(40)}`);
    console.log(`  0 tender(s) displayed  |  Execution time: ${executionTime}s`);
    console.log(`${'─'.repeat(40)}`);
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
  displayResults(aiRelevant, details, totalFetched, executionTime);
}

main().catch(e => {
  console.error("\nFatal error:", e.message);
  process.exit(1);
});
