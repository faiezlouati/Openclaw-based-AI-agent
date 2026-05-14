#!/usr/bin/env node


const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const OFFRES_DIR = path.join(process.env.HOME || '/Users/albus', '.openclaw/workspace/offres');
const TEMPLATES_DIR = path.join(OFFRES_DIR, 'templates');
const INDEX_FILE = path.join(OFFRES_DIR, 'index.md');

// Parse arguments
const args = process.argv.slice(2);
if (args.length < 1) {
  console.log('Usage: node save-offer.js <offre-id> [--cctp <path>] [--ccap <path>] [--buyer <name>] [--object <text>]');
  console.log('Example: node save-offer.js mutuelle-armee-datacenter-2026-05 --cctp ./cctp.pdf --buyer "Mutuelle Armée"');
  process.exit(1);
}

const offreId = args[0];
const opts = {};
for (let i = 1; i < args.length; i++) {
  if (args[i] === '--cctp' && args[i + 1]) opts.cctp = args[++i];
  else if (args[i] === '--ccap' && args[i + 1]) opts.ccap = args[++i];
  else if (args[i] === '--buyer' && args[i + 1]) opts.buyer = args[++i];
  else if (args[i] === '--object' && args[i + 1]) opts.object = args[++i];
}

const today = new Date().toISOString().split('T')[0];

// Create directories
const docDir = path.join(OFFRES_DIR, 'documents', offreId);
const anaDir = path.join(OFFRES_DIR, 'analyses', offreId);
[docDir, anaDir].forEach(d => {
  if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
});

// Copy CCTP
if (opts.cctp) {
  const src = opts.cctp;
  const dst = path.join(docDir, 'cctp.pdf');
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dst);
    console.log(`✅ CCTP copied: ${dst}`);
    // Extract text
    try {
      const txtDst = path.join(docDir, 'cctp.txt');
      execSync(`python3 -c "
import fitz
doc = fitz.open('${dst}')
text = ''
for page in doc:
    text += page.get_text()
print(text)
" > "${txtDst}"`, { stdio: 'pipe' });
      console.log(`✅ CCTP text extracted: ${txtDst}`);
    } catch (e) {
      console.log(`⚠️  CCTP text extraction failed: ${e.message}`);
    }
  } else {
    console.log(`⚠️  CCTP file not found: ${src}`);
  }
}

// Copy CCAP
if (opts.ccap) {
  const src = opts.ccap;
  const dst = path.join(docDir, 'ccap.pdf');
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dst);
    console.log(` CCAP copied: ${dst}`);
    try {
      const txtDst = path.join(docDir, 'ccap.txt');
      execSync(`python3 -c "
import fitz
doc = fitz.open('${dst}')
text = ''
for page in doc:
    text += page.get_text()
print(text)
" > "${txtDst}"`, { stdio: 'pipe' });
      console.log(`CCAP text extracted: ${txtDst}`);
    } catch (e) {
      console.log(` CCAP text extraction failed: ${e.message}`);
    }
  } else {
    console.log(`  CCAP file not found: ${src}`);
  }
}

// Create analysis files from templates
const cctpTemplate = path.join(TEMPLATES_DIR, 'cctp_analyse_template.md');
const ccapTemplate = path.join(TEMPLATES_DIR, 'ccap_analyse_template.md');

const buyer = opts.buyer || '[ACHETEUR]';
const obj = opts.object || '[OBJET]';

function fillTemplate(templatePath, destPath, vars) {
  if (fs.existsSync(templatePath)) {
    let content = fs.readFileSync(templatePath, 'utf8');
    content = content.replace(/\[OFFRE ID\]/g, offreId);
    content = content.replace(/\[ACHETEUR\]/g, vars.buyer);
    content = content.replace(/\[OBJET\]/g, vars.object);
    content = content.replace(/\[DATE\]/g, today);
    fs.writeFileSync(destPath, content);
    console.log(` Created: ${destPath}`);
  }
}

fillTemplate(cctpTemplate, path.join(anaDir, 'cctp_analyse.md'), { buyer, object: obj });
fillTemplate(ccapTemplate, path.join(anaDir, 'ccap_analyse.md'), { buyer, object: obj });

// Create combined rapport
const rapportPath = path.join(anaDir, 'rapport_final.md');
const rapportContent = `# Rapport Final — ${offreId}
## Acheteur : ${buyer}
## Objet : ${obj}
## Date : ${today}
## Status : Documenté, analyse en attente

---

*Ce rapport combine l'analyse CCTP et CCAP de l'offre "${offreId}".*
*Référez-vous aux fichiers cctp_analyse.md et ccap_analyse.md pour les analyses détaillées.*

---

## Documents sources

| Document | Chemin |
|----------|--------|
| CCTP | documents/${offreId}/cctp.pdf |
| CCAP | documents/${offreId}/ccap.pdf |

---

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

// Update index
const dateStr = new Date().toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
const newLine = `| ${offreId} | ${buyer} | ${obj} | ${dateStr} | Documenté |`;

// Simple append to index if entry doesn't exist
let indexContent = '';
if (fs.existsSync(INDEX_FILE)) {
  indexContent = fs.readFileSync(INDEX_FILE, 'utf8');
}

if (!indexContent.includes(offreId)) {
  // Find the table body and add the line before the closing separator
  const lines = indexContent.split('\n');
  const insertAt = lines.findIndex(l => l.includes('| ---'));
  if (insertAt > 0) {
    lines.splice(insertAt, 0, newLine);
    fs.writeFileSync(INDEX_FILE, lines.join('\n'));
    console.log(`Index updated: ${INDEX_FILE}`);
  }
}

console.log(`\n Offre "${offreId}" créée avec succès.`);
console.log(`📂 Documents: ${docDir}`);
console.log(`📋 Analyses: ${anaDir}`);
