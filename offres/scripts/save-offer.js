#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const HOME = process.env.HOME || '/Users/albus';
const DATA_DIR = path.join(HOME, '.tuneps_data');
const DOCUMENTS_DIR = path.join(DATA_DIR, 'documents');
const ANALYSES_DIR = path.join(DATA_DIR, 'analyses');
const DB_PATH = path.join(DATA_DIR, 'db', 'tenders.db');
const WORKSPACE_OFFRES_DIR = path.join(HOME, '.openclaw/workspace/offres');
const TEMPLATES_DIR = path.join(WORKSPACE_OFFRES_DIR, 'templates');

const args = process.argv.slice(2);
if (args.length < 1) {
  console.log('Usage: node save-offer.js <tender-ref> [--cctp <path>] [--ccap <path>] [--buyer <name>] [--object <text>]');
  console.log('Example: node save-offer.js 20260600060 --cctp ./cctp.pdf --buyer "Export Promotion Centre"');
  process.exit(1);
}

const tenderRef = args[0];
const opts = {};
for (let i = 1; i < args.length; i++) {
  if (args[i] === '--cctp' && args[i + 1]) opts.cctp = args[++i];
  else if (args[i] === '--ccap' && args[i + 1]) opts.ccap = args[++i];
  else if (args[i] === '--buyer' && args[i + 1]) opts.buyer = args[++i];
  else if (args[i] === '--object' && args[i + 1]) opts.object = args[++i];
}

const today = new Date().toISOString().split('T')[0];
const docDir = path.join(DOCUMENTS_DIR, tenderRef);
const anaDir = path.join(ANALYSES_DIR, tenderRef);
[docDir, anaDir, path.dirname(DB_PATH)].forEach(d => fs.mkdirSync(d, { recursive: true }));

// Extracts PDF text.
function extractPdfText(pdfPath, txtPath) {
  const py = `
import sys, fitz
pdf, out = sys.argv[1], sys.argv[2]
doc = fitz.open(pdf)
text = ''
for page in doc:
    text += page.get_text()
with open(out, 'w', encoding='utf-8') as f:
    f.write(text)
`;
  const res = spawnSync('python3', ['-c', py, pdfPath, txtPath], { encoding: 'utf8' });
  if (res.status !== 0) throw new Error((res.stderr || res.stdout || '').trim());
}

// Copies a tender document.
function copyDocument(src, docType) {
  const ext = path.extname(src) || '.pdf';
  const dst = path.join(docDir, `${docType}${ext.toLowerCase()}`);
  if (!fs.existsSync(src)) {
    console.log(`  ${docType.toUpperCase()} file not found: ${src}`);
    return null;
  }
  fs.copyFileSync(src, dst);
  console.log(` ${docType.toUpperCase()} copied: ${dst}`);

  if (ext.toLowerCase() === '.pdf') {
    try {
      const txtDst = path.join(docDir, `${docType}.txt`);
      extractPdfText(dst, txtDst);
      console.log(` ${docType.toUpperCase()} text extracted: ${txtDst}`);
    } catch (e) {
      console.log(`  ${docType.toUpperCase()} text extraction failed: ${e.message}`);
    }
  }
  upsertDocument(docType, dst);
  return dst;
}

// Runs SQLite commands.
function sqlite(sql, params = []) {
  if (!fs.existsSync(DB_PATH)) initDb();
  const escapedSql = sql;
  const res = spawnSync('sqlite3', [DB_PATH, escapedSql], { encoding: 'utf8' });
  if (res.status !== 0) {
    console.log(`  SQLite failed: ${(res.stderr || res.stdout || '').trim()}`);
  }
  return res.stdout;
}

// Runs a SQLite query.
function q(value) {
  if (value === null || value === undefined) return 'NULL';
  return `'${String(value).replace(/'/g, "''")}'`;
}

// Initializes the database.
function initDb() {
  fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
  const schema = `
CREATE TABLE IF NOT EXISTS tenders (
  ref TEXT PRIMARY KEY,
  authority TEXT,
  title TEXT,
  published TEXT,
  deadline TEXT,
  procedure TEXT,
  evaluation TEXT,
  consortium TEXT,
  international TEXT,
  guarantee TEXT,
  url TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tender_ref TEXT,
  doc_type TEXT,
  file_path TEXT,
  status TEXT DEFAULT 'uploaded',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(tender_ref, doc_type),
  FOREIGN KEY (tender_ref) REFERENCES tenders(ref)
);
CREATE TABLE IF NOT EXISTS analyses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tender_ref TEXT UNIQUE,
  relevance_score INTEGER,
  recommendation TEXT,
  matched_products TEXT,
  technical_requirements TEXT,
  analysis_json TEXT,
  status TEXT DEFAULT 'pending',
  analyzed_at TEXT,
  FOREIGN KEY (tender_ref) REFERENCES tenders(ref)
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tender_ref TEXT,
  status TEXT,
  input_path TEXT,
  output_path TEXT,
  started_at TEXT DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  error TEXT
);
CREATE TABLE IF NOT EXISTS exports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tender_ref TEXT,
  channel TEXT,
  recipient TEXT,
  file_path TEXT,
  status TEXT,
  exported_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_tender_doc_type ON documents(tender_ref, doc_type);
`;
  const res = spawnSync('sqlite3', [DB_PATH, schema], { encoding: 'utf8' });
  if (res.status !== 0) throw new Error(`Could not initialize DB: ${res.stderr}`);


  spawnSync('sqlite3', [DB_PATH, "ALTER TABLE tenders ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP;"], { encoding: 'utf8' });
}

// Upserts tender metadata.
function upsertTender() {
  const buyer = opts.buyer || '';
  const obj = opts.object || '';
  sqlite(`INSERT INTO tenders(ref, authority, title, updated_at)
          VALUES (${q(tenderRef)}, ${q(buyer)}, ${q(obj)}, CURRENT_TIMESTAMP)
          ON CONFLICT(ref) DO UPDATE SET
            authority=COALESCE(NULLIF(excluded.authority,''), tenders.authority),
            title=COALESCE(NULLIF(excluded.title,''), tenders.title),
            updated_at=CURRENT_TIMESTAMP;`);
}

// Upserts document metadata.
function upsertDocument(docType, filePath) {
  sqlite(`INSERT INTO documents(tender_ref, doc_type, file_path, status)
          VALUES (${q(tenderRef)}, ${q(docType)}, ${q(filePath)}, 'uploaded')
          ON CONFLICT(tender_ref, doc_type) DO UPDATE SET
            file_path=excluded.file_path,
            status='uploaded';`);
}

// Fills the analysis template.
function fillTemplate(templatePath, destPath, vars) {
  if (!fs.existsSync(templatePath)) return;
  let content = fs.readFileSync(templatePath, 'utf8');
  content = content.replace(/\[OFFRE ID\]/g, tenderRef);
  content = content.replace(/\[ACHETEUR\]/g, vars.buyer);
  content = content.replace(/\[OBJET\]/g, vars.object);
  content = content.replace(/\[DATE\]/g, today);
  fs.writeFileSync(destPath, content);
  console.log(` Created: ${destPath}`);
}

initDb();
upsertTender();

if (opts.cctp) copyDocument(opts.cctp, 'cctp');
if (opts.ccap) copyDocument(opts.ccap, 'ccap');

const buyer = opts.buyer || '[ACHETEUR]';
const obj = opts.object || '[OBJET]';
fillTemplate(path.join(TEMPLATES_DIR, 'cctp_analyse_template.md'), path.join(anaDir, 'cctp_analyse.md'), { buyer, object: obj });
fillTemplate(path.join(TEMPLATES_DIR, 'ccap_analyse_template.md'), path.join(anaDir, 'ccap_analyse.md'), { buyer, object: obj });

const rapportPath = path.join(anaDir, 'rapport_final.md');
const rapportContent = `# Rapport Final — ${tenderRef}
## Acheteur : ${buyer}
## Objet : ${obj}
## Date : ${today}
## Status : Documenté, analyse en attente

---

Storage root: ~/.tuneps_data

## Documents sources

| Document | Chemin |
|----------|--------|
| CCTP | documents/${tenderRef}/cctp.pdf |
| CCAP | documents/${tenderRef}/ccap.pdf |

## TODO

- [ ] Compléter l'analyse CCTP
- [ ] Compléter l'analyse CCAP
- [ ] Remplir la grille de conformité
- [ ] Valider les points critiques

---
*Rapport créé le ${today}*
`;
fs.writeFileSync(rapportPath, rapportContent);
console.log(` Created: ${rapportPath}`);

console.log(`\n Offer "${tenderRef}" saved in unified storage.`);
console.log(` Documents: ${docDir}`);
console.log(` Analyses: ${anaDir}`);
console.log(`  Database: ${DB_PATH}`);
