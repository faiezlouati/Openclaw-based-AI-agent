#!/usr/bin/env python3
"""
Build CCTP Relevance Analysis — Mutuelle Armée Nationale
Generates a styled .docx matching the provided template format.
"""

from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
import copy

# ── Palette ──────────────────────────────────────────────
NAVY        = RGBColor(0x1F, 0x38, 0x64)   # #1F3864 – title / headings / table headers
ACCENT_BLUE = RGBColor(0x2E, 0x75, 0xB6)   # #2E75B6 – sub-accent
HIGH_RED    = RGBColor(0xC0, 0x00, 0x00)   # Risk: High
MED_ORANGE  = RGBColor(0xFF, 0x66, 0x00)   # Risk: Medium
LOW_GREEN   = RGBColor(0x37, 0x56, 0x23)   # Risk: Low
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
BLACK       = RGBColor(0x00, 0x00, 0x00)
BODY_GREY   = RGBColor(0x40, 0x40, 0x40)   # slightly softened body text

# ── Helpers ────────────────────────────────────────────────

def set_cell_fill(cell, hex_color: str):
    """Fill a table cell with a solid hex colour."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  hex_color.upper().replace('#',''))
    tcPr.append(shd)

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side, val in [('top', top), ('bottom', bottom),
                      ('left', left), ('right', right)]:
        if val is not None:
            b = OxmlElement(f'w:{side}')
            b.set(qn('w:val'),   'single')
            b.set(qn('w:sz'),    '4')
            b.set(qn('w:space'), '0')
            b.set(qn('w:color'),  val)
            tcBorders.append(b)
    tcPr.append(tcBorders)

def add_run(para, text, bold=False, color=None, size_pt=None, underline=False):
    run = para.add_run(text)
    run.bold = bold
    if underline:
        run.underline = True
    if color:
        run.font.color.rgb = color
    if size_pt:
        run.font.size = Pt(size_pt)
    return run

def set_para_spacing(para, before_emu=None, after_emu=None):
    pf = para.paragraph_format
    if before_emu is not None:
        pf.space_before = before_emu
    if after_emu is not None:
        pf.space_after = after_emu

def shade_cell(cell, hex_color):
    """Apply background shading to a cell."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    # remove any existing shd
    for existing in tcPr.findall(qn('w:shd')):
        tcPr.remove(existing)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  hex_color.upper().replace('#',''))
    tcPr.append(shd)

def cell_para_text(cell, text, bold=False, color=None, size=9,
                   align=WD_ALIGN_PARAGRAPH.LEFT, shade_hex=None):
    """Helper: clear cell, add a styled paragraph."""
    cell.text = ''
    para = cell.paragraphs[0]
    para.alignment = align
    para.paragraph_format.space_before = Pt(2)
    para.paragraph_format.space_after  = Pt(2)
    run = para.add_run(text)
    run.bold = bold
    if color:
        run.font.color.rgb = color
    run.font.size = Pt(size)
    if shade_hex:
        shade_cell(cell, shade_hex)

def add_table_row(table, values, header=False, shade_hex='1F3864',
                 risk_col=None, row_idx=0):
    """Add a row to a table. risk_col = index of severity cell (0-based)."""
    row = table.add_row()
    for ci, val in enumerate(values):
        cell = row.cells[ci]
        is_severity = (risk_col is not None and ci == risk_col)
        cell.text = ''

        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        para.paragraph_format.space_before = Pt(2)
        para.paragraph_format.space_after  = Pt(2)

        run = para.add_run(val)
        run.font.size = Pt(9)

        if header:
            run.bold = True
            run.font.color.rgb = NAVY
            shade_cell(cell, shade_hex)
        elif is_severity:
            run.bold = True
            v = val.strip().upper()
            if 'HIGH' in v:
                run.font.color.rgb = HIGH_RED
            elif 'MEDIUM' in v:
                run.font.color.rgb = MED_ORANGE
            elif 'LOW' in v:
                run.font.color.rgb = LOW_GREEN
        else:
            run.font.color.rgb = BLACK
            shade_cell(cell, 'FFFFFF')
    return row

# ── Document setup ────────────────────────────────────────

doc = Document()

# Page margins: top/bottom 1.5 cm, left/right 1.8 cm
for section in doc.sections:
    section.top_margin    = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin   = Cm(1.8)
    section.right_margin  = Cm(1.8)

# ── Styles ────────────────────────────────────────────────

def apply_heading_style(para, text):
    """Navy bold Heading 1 style."""
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after  = Pt(3)
    run = para.add_run(text)
    run.bold = True
    run.font.color.rgb = NAVY
    run.font.size = Pt(13)

def apply_body(doc, text, bold=False, size=10):
    """Add a plain body paragraph."""
    para = doc.add_paragraph(text)
    para.paragraph_format.space_before = Pt(2)
    para.paragraph_format.space_after  = Pt(4)
    for run in para.runs:
        run.bold = bold
        run.font.size = Pt(size)
        run.font.color.rgb = BODY_GREY
    return para

def apply_list_item(doc, text, size=10):
    """Add a List Paragraph item."""
    para = doc.add_paragraph(text, style='List Paragraph')
    para.paragraph_format.space_before = Pt(1)
    para.paragraph_format.space_after  = Pt(1)
    for run in para.runs:
        run.font.size = Pt(size)
        run.font.color.rgb = BODY_GREY
    return para

# ── TITLE ─────────────────────────────────────────────────
title_para = doc.add_paragraph()
title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
title_para.paragraph_format.space_before = Pt(0)
title_para.paragraph_format.space_after  = Pt(4)
run = title_para.add_run('CCTP RELEVANCE ANALYSIS')
run.bold = True
run.font.color.rgb = NAVY
run.font.size = Pt(16)

sub_para = doc.add_paragraph()
sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub_para.paragraph_format.space_before = Pt(0)
sub_para.paragraph_format.space_after  = Pt(8)
run = sub_para.add_run('Datacenter Modernization — Mutuelle de l\'Armée Nationale (Tunisia)')
run.font.color.rgb = ACCENT_BLUE
run.font.size = Pt(11)

# ─────────────────────────────────────────────────────────
# 1. EXTRACTION AND MAPPING
# ─────────────────────────────────────────────────────────
h1 = doc.add_paragraph()
apply_heading_style(h1, '1. Extraction and Mapping')

apply_body(doc,
    'Full datacenter refresh for the Mutuelle de l\'Armée Nationale '
    '(Ministry of Defence, Tunisia). Single contract, eight indissociable items, '
    '120-day execution after contract approval. Existing VMware vSphere 8 platform to be migrated.')

# Items table
items_intro = doc.add_paragraph()
items_intro.paragraph_format.space_before = Pt(2)
items_intro.paragraph_format.space_after  = Pt(2)
add_run(items_intro, 'Items summary:', bold=True, color=BODY_GREY, size_pt=10)

items_table = doc.add_table(rows=0, cols=4)
items_table.style = 'Table Grid'
add_table_row(items_table, ['#', 'Item', 'Qty', 'Category'], header=True)
add_table_row(items_table, ['1', 'Virtualization servers', '3', 'Compute'])
add_table_row(items_table, ['2', 'Virtualization software', '1', 'Hypervisor'])
add_table_row(items_table, ['3', 'Storage array', '1', 'Storage'])
add_table_row(items_table, ['4', 'Backup server', '1', 'Compute'])
add_table_row(items_table, ['5', 'Backup software', '1', 'Data protection'])
add_table_row(items_table, ['6', 'Datacenter switches', '2', 'Network'])
add_table_row(items_table, ['7', 'Firewall appliances', '2', 'Security'])
add_table_row(items_table, ['8', 'Rack cabinet 42U', '1', 'Infrastructure'])

doc.add_paragraph('')

# Included services
svc_para = doc.add_paragraph()
svc_para.paragraph_format.space_before = Pt(2)
svc_para.paragraph_format.space_after  = Pt(2)
add_run(svc_para, 'Included services:', bold=True, color=BODY_GREY, size_pt=10)

apply_list_item(doc, 'Installation, configuration, and live VM migration from VMware vSphere 8')
apply_list_item(doc, 'Two certifying trainings (5 days, 6 staff each) in an accredited center')
apply_list_item(doc, 'Complete documentation (French or English), knowledge transfer')
apply_list_item(doc, '2-year 24/7 manufacturer support, updates included')

doc.add_paragraph('')

# ─────────────────────────────────────────────────────────
# 2. QUALIFICATION REQUIREMENTS
# ─────────────────────────────────────────────────────────
h2 = doc.add_paragraph()
apply_heading_style(h2, '2. Qualification Requirements')

apply_body(doc,
    'Conditions a bidder must satisfy to be eligible. Failure on any line results '
    'in automatic disqualification.')

qual_table = doc.add_table(rows=0, cols=2)
qual_table.style = 'Table Grid'
add_table_row(qual_table, ['Category', 'Requirement'], header=True)

qual_data = [
    ('Legal / administrative', 'Tunisian registration; TUNEPS registration; tax and social security clearance certificates'),
    ('Defence sector screening', 'National security screening for company and key personnel; nationality restrictions apply'),
    ('Manufacturer authorisation', 'MAF letter required for servers, storage array, and backup server'),
    ('Brand constraint', 'Servers (Lot 1), storage array (Lot 3), and backup server (Lot 4) must be from the same manufacturer'),
    ('Firewall (Gartner MQ)', 'Vendor must appear in the latest Gartner Magic Quadrant for Network Firewalls'),
    ('Product certifications', 'ISO 9001:2015 and EN 62368/55032/55035 on servers, storage, switches, firewall; '
                                'EAL 4+ or ICSA Labs for firewall'),
    ('Training capability', 'Accredited training centre; certified trainers (CVs submitted with bid)'),
    ('Financial guarantees', '5,000 TND provisional deposit; 3% final guarantee; 5% retention; bid validity 120 days'),
]
for cat, req in qual_data:
    add_table_row(qual_table, [cat, req])

doc.add_paragraph('')

# ─────────────────────────────────────────────────────────
# 3. TECHNICAL DEMAND SUMMARY
# ─────────────────────────────────────────────────────────
h3 = doc.add_paragraph()
apply_heading_style(h3, '3. Technical Demand Summary')

apply_body(doc,
    'What the CCTP asks for, item by item. This is a factual summary — no vendor, '
    'SKU, or product family is recommended.')

tech_table = doc.add_table(rows=0, cols=2)
tech_table.style = 'Table Grid'
add_table_row(tech_table, ['Item', 'Key Technical Demands'], header=True)

tech_data = [
    ('Virtualization servers (×3)',
     '2U rack, latest generation; 2×16-core @ 2.4 GHz, 72 MB cache, 64-bit, VT, HT; '
     '512 GB DDR5 RDIMM 6400 MT/s (extensible to 1 TB); 32 DIMM slots; 2×480 GB SSD PCIe OS; '
     '8×2.5" chassis; hardware RAID 0/1/5/6/10, 8 GB non-volatile cache; 6× PCIe 4.0 slots; '
     '4×1GbE + 4×10/25GbE; 2×hot-plug redundant PSU; IPMI; USB disable; intrusion detection; '
     'OS: Windows 2022 Hyper-V, VMware ESXi, Red Hat Virtualisation, Proxmox VE 8/9; '
     'ISO 9001:2015; 2-year 24/7 manufacturer support'),
    ('Virtualization software',
     'Bare-metal hypervisor; 3-node HA cluster (automatic VM restart); per-host/processor licensing '
     '(unlimited VMs); live migration, snapshots, dynamic resource balancing; '
     'boot on SAN (iSCSI/NFS); deduplication-aware storage; '
     'mandatory live migration from VMware vSphere 8; '
     'centralised web admin console; 2-year editor support included'),
    ('Storage array',
     'Same brand as Lot 1; max 2U; dual active/active controllers (2×10-core CPU); '
     '128 GB cache; iSCSI, FC, CIFS, NFS, FTP, HTTP, SMB; '
     '4×2 TB NVMe + 2×480 GB NVMe OS (RAID1); min 20 hot-swap disks; '
     'RAID 0/1/5/6/10 (active: RAID 5); thin provisioning, deduplication, compression, '
     '1000+ snapshots, auto-tiering, sync/async replication; '
     'battery backup (autonomy: non-disclosed); SNMP v3; same MAF required'),
    ('Backup server',
     'Same brand as Lot 1; 2U rack; 1×16-core @ 2.4 GHz; 128 GB DDR5; '
     '4×8 TB HDD (8×2.5" chassis); 4×1GbE + 4×10/25GbE SFP+; '
     'OS: Windows 2019/2022/2025, VMware vSphere 7/8, Red Hat, Ubuntu; 2-year manufacturer support'),
    ('Backup software',
     'Subscription for 15 VMs (2 years), agentless mandatory; image-based, SAN/LAN, hot VM backup; '
     'local + WAN deduplication; end-to-end encryption; '
     'full VM, per-VM file, individual object, app-aware restore (Oracle, MS SQL); '
     'self-service restore portal; image replication with auto-failover; '
     'real-time dashboard; native tape/LTO support; 2-year support'),
    ('Datacenter switches (×2)',
     'L3 Top-of-Rack, 19" rack-mount; 600 Gbps switching capacity; 650 Mpps IPv4 throughput; '
     '4 GB RAM; 4000 VLANs; 64,000 MAC addresses; '
     '16×1GbE PoE + 4×10GbE SFP+ (optical modules included); '
     'VLAN static/dynamic, LACP, LLDP; 8 queues/port, DSCP/CoS; '
     '802.1X, MAB, DHCP snooping, ARP inspection, anti-spoofing; '
     'SSHv2, SNMP v2/v3, syslog, port mirroring; '
     'IEEE 802.1x/w/s/D/p/Q, 802.3x/ad/z; 2-year warranty + licences'),
    ('Firewall (×2)',
     'Listed in latest Gartner Magic Quadrant for Network Firewalls; '
     '5 Gbps firewall throughput; 4 Gbps IPSec VPN; 1 Gbps threat prevention; '
     '1.2 Gbps SSL inspection; 700,000 TCP concurrent sessions; 80,000 new sessions/s; '
     '5×GE RJ45 + console + USB; App-ID, IPS, AV, sandboxing, web/DNS filtering; '
     'IPSec (200 site-to-site) + SSL (200 client-to-site); AES-128/256; '
     'LDAP/LDAPS, RADIUS, PKI; zone-based rules by IP, service, user, schedule; '
     'active/active + active/passive HA with state sync; '
     'graphical monitoring, SIEM integration; ISO 9001:2015, EAL4+ or ICSA Labs; 2-year licences'),
    ('Rack cabinet',
     '42U, 19"; reinforced steel; static load ≥1000 kg, dynamic ≥600 kg; '
     '4 adjustable rails with visible U numbering; perforated steel doors with locks; '
     'removable lockable panels; front-to-back cooling, 4 integrated fans, '
     'hot/cold aisle compatible; 2× intelligent vertical PDU, A/B redundancy; '
     'rated up to 45°C; 2-year warranty'),
]
for item, demand in tech_data:
    add_table_row(tech_table, [item, demand])

doc.add_paragraph('')

# ─────────────────────────────────────────────────────────
# 4. MAIN TECHNICAL RISKS
# ─────────────────────────────────────────────────────────
h4 = doc.add_paragraph()
apply_heading_style(h4, '4. Main Technical Risks')

apply_body(doc,
    'Principal technical execution risks extracted from the CCTP. '
    'Contractual and financial risks (penalties, payment terms, guarantees) are '
    'excluded as they belong to the CCAP.')

risks_table = doc.add_table(rows=0, cols=3)
risks_table.style = 'Table Grid'
add_table_row(risks_table, ['Risk', 'CCTP Source', 'Severity'], header=True)

risks = [
    ('120-day execution window vs current OEM lead times on latest-generation servers',
     'CCTP §1.2 / CCAP Art. 22', 'High'),
    ('Live VM migration from VMware vSphere 8 to new hypervisor without production impact',
     'CCTP §1.2, Lot 2', 'High'),
    ('Same-brand constraint on servers + storage + backup server limits OEM options',
     'CCTP Lots 1, 3, 4', 'Medium'),
    ('Backup licence sized for 15 VMs only — actual production VM count likely higher',
     'CCTP Lot 5', 'Medium'),
    ('RAID 5 configured as the active RAID level on a enterprise storage array',
     'CCTP Lot 3 (storage array specs)', 'Medium'),
    ('Battery autonomy on storage array not quantified — risk of data loss on extended power failure',
     'CCTP Lot 3', 'Medium'),
    ('RPO/RTO targets not defined by the buyer — leaves soumissionnaire exposed on performance commitments',
     'CCTP Lot 2 (virtualisation)', 'Medium'),
    ('Boot-on-SAN dependency — FC direct-attach limits scalability beyond 2 hosts',
     'CCTP Lot 2 (Boot on SAN)', 'Low'),
]
for risk, source, severity in risks:
    row = risks_table.add_row()
    vals = [risk, source, severity]
    for ci, val in enumerate(vals):
        cell = row.cells[ci]
        cell.text = ''
        para = cell.paragraphs[0]
        para.paragraph_format.space_before = Pt(2)
        para.paragraph_format.space_after  = Pt(2)
        run = para.add_run(val)
        run.font.size = Pt(9)
        if ci == 2:
            run.bold = True
            v = val.strip().upper()
            if 'HIGH' in v:
                run.font.color.rgb = HIGH_RED
            elif 'MEDIUM' in v:
                run.font.color.rgb = MED_ORANGE
            elif 'LOW' in v:
                run.font.color.rgb = LOW_GREEN
        elif ci == 0:
            run.font.color.rgb = BLACK
        else:
            run.font.color.rgb = BLACK
        shade_cell(cell, 'FFFFFF')

doc.add_paragraph('')

# ─────────────────────────────────────────────────────────
# 5. RELEVANCE SYNTHESIS
# ─────────────────────────────────────────────────────────
h5 = doc.add_paragraph()
apply_heading_style(h5, '5. Relevance Synthesis')

# Strengths
apply_body(doc, 'Strengths of this opportunity:', bold=True, size=10)
apply_list_item(doc, 'Defence sector reference — high strategic value for North African market credibility')
apply_list_item(doc, 'Full datacenter scope in a single contract — visibility across the full ICT portfolio')
apply_list_item(doc, 'Specs map to standard Tier-1 OEM portfolios — no exotic or non-standard requirements')
apply_list_item(doc, 'Professional procurement framework via TUNEPS with clear CCAP and CCTP')
apply_list_item(doc, '2-year bundled support contract generates predictable recurring revenue')

# Challenges
apply_body(doc, 'Challenges:', bold=True, size=10)
apply_list_item(doc, 'Tight 120-day execution window vs current OEM lead times on latest-generation hardware')
apply_list_item(doc, 'VMware migration is the critical-path risk item — live migration without production impact is mandatory')
apply_list_item(doc, 'Same-brand constraint requires early OEM commitment before contract award')
apply_list_item(doc, 'Defence security screening can disqualify a vendor late in the process')
apply_list_item(doc, 'FX exposure partially mitigated (capped at 2% price revision) — contracts in TND')

doc.add_paragraph('')

# Relevance table
apply_body(doc, 'Relevance by vendor profile:', bold=True, size=10)

rel_table = doc.add_table(rows=0, cols=2)
rel_table.style = 'Table Grid'
add_table_row(rel_table, ['Profile', 'Relevance'], header=True)

profiles = [
    ('Tier-1 OEM with strong North African channel (e.g., Huawei, Dell, HPE, Lenovo)',
     'Highly relevant — natural fit for full-stack datacenter scope'),
    ('Tier-2 OEM with limited local presence',
     'Moderately relevant — requires certified local partner or integrator'),
    ('Local integrator without OEM-level partnership',
     'Low relevance — MAF and brand constraint are blocking without OEM backing'),
    ('New entrant without local references',
     'Low relevance — defence screening and track-record requirements are disqualifying'),
]
for profile, relevance in profiles:
    add_table_row(rel_table, [profile, relevance])

doc.add_paragraph('')

# Final callout paragraph
callout = doc.add_paragraph()
callout.paragraph_format.space_before = Pt(4)
callout.paragraph_format.space_after  = Pt(6)
# light shading box — paragraph background
pPr = callout._p.get_or_add_pPr()
pBdr = OxmlElement('w:pBdr')
for side in ['top','left','bottom','right']:
    b = OxmlElement(f'w:{side}')
    b.set(qn('w:val'),   'single')
    b.set(qn('w:sz'),    '6')
    b.set(qn('w:space'), '4')
    b.set(qn('w:color'), '1F3864')
    pBdr.append(b)
pPr.append(pBdr)
shd2 = OxmlElement('w:shd')
shd2.set(qn('w:val'),  'clear')
shd2.set(qn('w:color'),'auto')
shd2.set(qn('w:fill'), 'EEF3FA')  # very light navy tint
pPr.append(shd2)

run1 = callout.add_run(
    'This tender is structurally relevant for any Tier-1 ICT vendor with a local presence or '
    'certified channel partner. The full-stack scope, professional procurement, and 2-year support '
    '捆绑 make it a strategic entry point into the Tunisian defence ICT ecosystem.\n\n'
)
run1.font.size = Pt(10)
run1.font.color.rgb = BODY_GREY

run2 = callout.add_run(
    'Management validation is required on three items before a binding offer is submitted: '
    '1) exact production VM count to confirm or upsize the 15-VM backup licence; '
    '2) acceptable maintenance window and downtime tolerance during live migration; '
    '3) current VMware vSphere 8 version, build, and VM inventory to size the migration track.'
)
run2.font.size = Pt(10)
run2.font.color.rgb = NAVY
run2.bold = True

# ── Save ─────────────────────────────────────────────────
out_path = '/Users/albus/.openclaw/workspace/offres/analyses/mutuelle-armee-datacenter-2026-05/CCTP_Analysis_Mutuelle_Armee.docx'
doc.save(out_path)
print(f'Saved: {out_path}')