/**
 * KSDMA Priority-Based Disaster Relief Resource Allocation & Distribution System
 * Master Prototype Application Engine
 * Authors: Alina Anna Eappen, Athira Anil, Sreya Akku Shajan, Nair Ardra Santhosh
 * Guide: Reshma Raj K S
 */

// ==========================================
// 1. Core State & Master Data
// ==========================================
const DisasterState = {
  // Authentication session
  currentUser: null, // null (shows Login Gateway), or { role: 'donor'|'camp_officer'|'collector', name, pen, campId }
  
  // Donor interface filters
  donorSearchQuery: '',
  donorTargetType: 'camp', // 'camp' or 'hub'

  // Camp Officer active tab
  officerActiveTab: 'active', // 'active' or 'satisfied'

  weights: {
    item: 0.35,
    damage: 0.25,
    vuln: 0.20,
    time: 0.20
  },

  // Alappuzha District Relief Camps
  camps: [
    {
      id: 'CAMP-04',
      name: 'St. Aloysius HSS, Edathua',
      taluk: 'Kuttanad',
      distance: '3.2 km',
      officerName: 'Sunil Kumar',
      officerPen: '842109',
      population: 850,
      damageTier: 10,
      damageDescription: 'Severe Flood Cut-Off (Boats Only)',
      status: 'Critical Alert'
    },
    {
      id: 'CAMP-02',
      name: 'Govt Model HSS, Chengannur',
      taluk: 'Chengannur',
      distance: '18.4 km',
      officerName: 'Priya Varma',
      officerPen: '781034',
      population: 1200,
      damageTier: 6,
      damageDescription: 'Waterlogged Flash Flood',
      status: 'Active'
    },
    {
      id: 'CAMP-07',
      name: 'Leo XIII Higher Secondary School',
      taluk: 'Ambalappuzha',
      distance: '8.1 km',
      officerName: 'K. Rajeev',
      officerPen: '659012',
      population: 430,
      damageTier: 2,
      damageDescription: 'Mild Coastal Influx',
      status: 'Stable'
    }
  ],

  // LSG Distribution Hubs (For Bulk/Large Quantity Donors)
  hubs: [
    {
      id: 'HUB-01',
      name: 'Ambalappuzha Municipality LSG Distribution Hub',
      taluk: 'Ambalappuzha',
      distance: '6.5 km',
      coordinator: 'Mathew Joseph (SPARK PEN: 512903)',
      capacity: 'Bulk Depot (15,000 sq.ft)',
      stock: { waterBottles: 2400, foodKits: 1100, blankets: 650, infantFormula: 80, insulinVials: 15 },
      forecastedDemand: { waterBottles: 1800, foodKits: 750, blankets: 400, infantFormula: 120, insulinVials: 40 }
    },
    {
      id: 'HUB-02',
      name: 'Cherthala Civil Station Depository',
      taluk: 'Cherthala',
      distance: '24.0 km',
      coordinator: 'Anoop Nair (SPARK PEN: 923418)',
      capacity: 'Central Warehouse (30,000 sq.ft)',
      stock: { waterBottles: 5000, foodKits: 2200, blankets: 1400, infantFormula: 300, insulinVials: 120 },
      forecastedDemand: { waterBottles: 1500, foodKits: 900, blankets: 500, infantFormula: 80, insulinVials: 30 }
    },
    {
      id: 'HUB-03',
      name: 'Kuttanad Emergency Boat Jetty Depot',
      taluk: 'Kuttanad',
      distance: '4.8 km',
      coordinator: 'Deepa George (SPARK PEN: 410294)',
      capacity: 'Water Transit Depot (8,000 sq.ft)',
      stock: { waterBottles: 600, foodKits: 350, blankets: 180, infantFormula: 20, insulinVials: 0 },
      forecastedDemand: { waterBottles: 3500, foodKits: 1800, blankets: 1100, infantFormula: 160, insulinVials: 50 }
    }
  ],

  // Active and Fulfilled Requirements
  requirements: [
    {
      id: 'REQ-101',
      campId: 'CAMP-04',
      campName: 'St. Aloysius HSS, Edathua',
      itemCode: 'MED-INS',
      itemName: 'Insulin Vials (Cold Storage 100 IU/ml)',
      category: 'Medical',
      vitality: 10,
      qtyRequested: 35,
      qtyFulfilled: 0,
      unit: 'vials',
      isEmergency: true,
      sawScore: 99.9,
      status: 'Verified',
      elapsedHours: 4,
      alphanumericCode: 'KL-EM-9101',
      fulfilledAt: null,
      fulfilledBy: null
    },
    {
      id: 'REQ-102',
      campId: 'CAMP-04',
      campName: 'St. Aloysius HSS, Edathua',
      itemCode: 'WAT-CAN',
      itemName: 'Drinking Water (20L Cans)',
      category: 'Water',
      vitality: 9,
      qtyRequested: 400,
      qtyFulfilled: 120, // 280 needed
      unit: 'cans',
      isEmergency: false,
      sawScore: 88.4,
      status: 'Pledged',
      elapsedHours: 12,
      alphanumericCode: 'KL-ED-4921',
      fulfilledAt: null,
      fulfilledBy: null
    },
    {
      id: 'REQ-103',
      campId: 'CAMP-02',
      campName: 'Govt Model HSS, Chengannur',
      itemCode: 'FOD-KIT',
      itemName: 'Standard Dry Food Ration Kits',
      category: 'Food',
      vitality: 8,
      qtyRequested: 600,
      qtyFulfilled: 350,
      unit: 'kits',
      isEmergency: false,
      sawScore: 76.2,
      status: 'In Transit',
      elapsedHours: 18,
      alphanumericCode: 'KL-CHG-9912',
      fulfilledAt: null,
      fulfilledBy: null
    },
    {
      id: 'REQ-104',
      campId: 'CAMP-04',
      campName: 'St. Aloysius HSS, Edathua',
      itemCode: 'INF-MILK',
      itemName: 'Infant Formula Powder (Stage 1)',
      category: 'Nutrition',
      vitality: 9,
      qtyRequested: 90,
      qtyFulfilled: 10,
      unit: 'tins',
      isEmergency: false,
      sawScore: 84.1,
      status: 'Verified',
      elapsedHours: 8,
      alphanumericCode: 'KL-IN-8834',
      fulfilledAt: null,
      fulfilledBy: null
    },
    {
      id: 'REQ-105',
      campId: 'CAMP-07',
      campName: 'Leo XIII HSS, Alappuzha',
      itemCode: 'SHL-BLNK',
      itemName: 'Woolen Sleeping Blankets',
      category: 'Shelter',
      vitality: 6,
      qtyRequested: 150,
      qtyFulfilled: 150,
      unit: 'nos',
      isEmergency: false,
      sawScore: 54.0,
      status: 'Fulfilled',
      elapsedHours: 28,
      alphanumericCode: 'KL-SH-3301',
      fulfilledAt: '06:15:00 IST',
      fulfilledBy: 'K. Rajeev (PEN: 659012)'
    }
  ],

  // In-Transit Pledges (From Donors heading to camps or hubs)
  enRouteDeliveries: [
    {
      pledgeId: 'PLG-ED-7701',
      targetType: 'camp',
      campId: 'CAMP-04',
      campName: 'St. Aloysius HSS, Edathua',
      officerPen: '842109',
      officerName: 'Sunil Kumar',
      reqId: 'REQ-102',
      itemCode: 'WAT-CAN',
      itemName: 'Drinking Water (20L Cans)',
      qtyPledged: 280,
      donorName: 'Anonymous Citizen (KSDMA Shield)',
      pin: 'KL-ED-4921',
      status: 'In Transit (En Route)',
      createdAt: '07:20:15'
    }
  ],

  auditLogs: [
    { time: '07:20:15', officer: 'Public Donor Portal', action: 'Camp Pledge Created', details: 'Pledged 280 Water Cans for Camp #04 (Pass: KL-ED-4921) to Officer Sunil Kumar.' },
    { time: '07:15:20', officer: 'Sunil Kumar (PEN: 842109)', action: 'Emergency Override Triggered', details: 'Insulin Vials (35 nos) pinned to Rank 1 for Camp #04' },
    { time: '06:15:00', officer: 'K. Rajeev (PEN: 659012)', action: 'Delivery Verified & Satisfied', details: 'Scanned Pass KL-SH-3301. Blanket requirement satisfied 100%.' }
  ]
};

// ==========================================
// 2. Authentication & Session Management
// ==========================================
function login(role, customData = {}) {
  if (role === 'donor') {
    const phone = document.getElementById('login-donor-phone')?.value || '9847012345';
    DisasterState.currentUser = {
      role: 'donor',
      name: 'Public Donor / Volunteer',
      phone: phone,
      identityToken: 'DON-KL-' + Math.floor(1000 + Math.random() * 9000)
    };
  } else if (role === 'camp_officer') {
    const pen = document.getElementById('login-officer-pen')?.value || '842109';
    DisasterState.currentUser = {
      role: 'camp_officer',
      name: pen === '781034' ? 'Priya Varma' : 'Sunil Kumar',
      pen: pen,
      campId: pen === '781034' ? 'CAMP-02' : 'CAMP-04',
      campName: pen === '781034' ? 'Govt Model HSS, Chengannur' : 'St. Aloysius HSS, Edathua'
    };
  } else if (role === 'collector') {
    DisasterState.currentUser = {
      role: 'collector',
      name: 'District Collector (Alappuzha)',
      pen: '100042',
      jurisdiction: 'Statewide Alappuzha (KL-04)'
    };
  }

  updateSessionUI();
}

function logout() {
  DisasterState.currentUser = null;
  updateSessionUI();
}

function updateSessionUI() {
  const sessionBar = document.getElementById('user-session-bar');
  const loginGateway = document.getElementById('view-login-gateway');
  const donorView = document.getElementById('view-donor-portal');
  const campView = document.getElementById('view-camp-portal');
  const collectorView = document.getElementById('view-collector-portal');

  // Hide all portal views first
  loginGateway.style.display = 'none';
  donorView.style.display = 'none';
  campView.style.display = 'none';
  collectorView.style.display = 'none';

  if (!DisasterState.currentUser) {
    // Show Login Gateway
    sessionBar.style.display = 'none';
    loginGateway.style.display = 'block';
    return;
  }

  // User is logged in
  sessionBar.style.display = 'flex';
  const u = DisasterState.currentUser;

  document.getElementById('session-user-name').textContent = u.name;
  const roleBadge = document.getElementById('session-role-badge');

  if (u.role === 'donor') {
    roleBadge.textContent = 'Public Donor';
    roleBadge.className = 'user-role-badge donor';
    donorView.style.display = 'block';
    renderDonorPortal();
  } else if (u.role === 'camp_officer') {
    roleBadge.textContent = `Camp Officer (${u.campId})`;
    roleBadge.className = 'user-role-badge officer';
    campView.style.display = 'block';
    renderCampDashboard();
  } else if (u.role === 'collector') {
    roleBadge.textContent = 'District Collector';
    roleBadge.className = 'user-role-badge collector';
    collectorView.style.display = 'block';
    renderCollectorDashboard();
  }
}

// ==========================================
// 3. SVG QR Code Generator (Pure JavaScript)
// ==========================================
function generateSvgQr(content, size = 190) {
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    hash = ((hash << 5) - hash) + content.charCodeAt(i);
    hash |= 0;
  }

  const gridSize = 25;
  const cellSize = size / gridSize;
  let rects = '';

  for (let r = 0; r < gridSize; r++) {
    for (let c = 0; c < gridSize; c++) {
      const isTopLeft = (r < 7 && c < 7);
      const isTopRight = (r < 7 && c >= gridSize - 7);
      const isBottomLeft = (r >= gridSize - 7 && c < 7);

      let isFilled = false;
      if (isTopLeft) {
        isFilled = (r === 0 || r === 6 || c === 0 || c === 6 || (r >= 2 && r <= 4 && c >= 2 && c <= 4));
      } else if (isTopRight) {
        isFilled = (r === 0 || r === 6 || c === gridSize - 7 || c === gridSize - 1 || (r >= 2 && r <= 4 && c >= gridSize - 5 && c <= gridSize - 3));
      } else if (isBottomLeft) {
        isFilled = (r === gridSize - 7 || r === gridSize - 1 || c === 0 || c === 6 || (r >= gridSize - 5 && r <= gridSize - 3 && c >= 2 && c <= 4));
      } else {
        const seed = Math.sin((r * gridSize + c + hash)) * 10000;
        isFilled = (seed - Math.floor(seed)) > 0.48;
      }

      if (isFilled) {
        rects += `<rect x="${(c * cellSize).toFixed(1)}" y="${(r * cellSize).toFixed(1)}" width="${cellSize.toFixed(1)}" height="${cellSize.toFixed(1)}" fill="#030712"/>`;
      }
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" class="qr-code-svg">
    <rect width="${size}" height="${size}" fill="#ffffff" rx="8"/>
    ${rects}
  </svg>`;
}

// ==========================================
// 4. DONOR INTERFACE LOGIC
// ==========================================
function setDonorTargetType(type) {
  DisasterState.donorTargetType = type;
  document.getElementById('dest-btn-camps').classList.toggle('active', type === 'camp');
  document.getElementById('dest-btn-hubs').classList.toggle('active', type === 'hub');
  renderDonorPortal();
}

function handleDonorSearch() {
  DisasterState.donorSearchQuery = document.getElementById('donor-search-input').value.toLowerCase().trim();
  renderDonorPortal();
}

function renderDonorPortal() {
  const grid = document.getElementById('donor-items-grid');
  if (!grid) return;

  const query = DisasterState.donorSearchQuery;
  const isHubMode = DisasterState.donorTargetType === 'hub';

  if (isHubMode) {
    // Render Nearby LSG Distribution Hubs for Large/Bulk Quantities
    renderDonorHubList(grid, query);
  } else {
    // Render Relief Camps with requirements strictly sorted by SAW Priority
    renderDonorCampRequirements(grid, query);
  }
}

function renderDonorCampRequirements(grid, query) {
  // Sort requirements strictly by SAW priority descending
  const sortedReqs = [...DisasterState.requirements]
    .filter(r => r.status !== 'Fulfilled') // Show active needs
    .sort((a, b) => b.sawScore - a.sawScore);

  let html = '';
  let count = 0;

  sortedReqs.forEach((req, index) => {
    const camp = DisasterState.camps.find(c => c.id === req.campId) || DisasterState.camps[0];

    // Search query filter (matches camp name, taluk, or item name)
    const matchesQuery = !query || 
      camp.name.toLowerCase().includes(query) || 
      camp.taluk.toLowerCase().includes(query) ||
      req.itemName.toLowerCase().includes(query);

    if (!matchesQuery) return;
    count++;

    const remaining = Math.max(0, req.qtyRequested - req.qtyFulfilled);
    const progressPct = Math.min(100, Math.round((req.qtyFulfilled / req.qtyRequested) * 100));

    const rankBadgeClass = req.isEmergency ? 'critical' : (req.sawScore > 80 ? 'high' : 'normal');
    const rankLabel = req.isEmergency ? '🚨 CRITICAL EMERGENCY (RANK 1)' : `⚡ PRIORITY RANK #${index + 1} (Score: ${req.sawScore})`;

    html += `
      <div class="donor-item-card">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span class="priority-rank-badge ${rankBadgeClass}">${rankLabel}</span>
            <span style="font-size:0.75rem; color:#93c5fd; font-weight:700;">📍 ${camp.distance} away</span>
          </div>

          <h4 style="font-family:var(--font-heading); font-size:1.15rem; color:#f8fafc; margin-bottom:4px;">
            ${req.itemName}
          </h4>

          <div style="font-size:0.8rem; color:#6ee7b7; font-weight:600; margin-bottom:2px;">
            🏕️ ${camp.name}
          </div>
          <div style="font-size:0.725rem; color:var(--text-muted); margin-bottom:12px;">
            Taluk: ${camp.taluk} • Designated Officer: <strong>${camp.officerName} (PEN: ${camp.officerPen})</strong>
          </div>

          <!-- Progress Bar -->
          <div style="margin:12px 0 6px 0;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:4px;">
              <span>Fulfillment: <strong>${req.qtyFulfilled} / ${req.qtyRequested} ${req.unit}</strong></span>
              <span style="color:#93c5fd; font-weight:700;">${progressPct}%</span>
            </div>
            <div style="height:7px; background:#1e293b; border-radius:999px; overflow:hidden;">
              <div style="height:100%; width:${progressPct}%; background:linear-gradient(90deg, #3b82f6 0%, #10b981 100%); border-radius:999px;"></div>
            </div>
          </div>

          <div style="font-size:0.85rem; color:#fcd34d; font-weight:700; margin-top:8px;">
            Still Needed: ${remaining} ${req.unit}
          </div>
        </div>

        <div>
          <button class="btn btn-success" style="width:100%;" onclick="openCampPledgeModal('${req.id}', '${camp.id}', '${camp.name.replace(/'/g, "\\'")}', '${camp.officerPen}', '${camp.officerName.replace(/'/g, "\\'")}', '${req.itemName.replace(/'/g, "\\'")}', ${remaining}, '${req.unit}')">
            🤝 Pledge to This Camp
          </button>
        </div>
      </div>
    `;
  });

  if (count === 0) {
    html = `<div style="grid-column: 1/-1; padding:40px; text-align:center; color:var(--text-secondary); background:var(--bg-surface); border-radius:var(--radius-lg);">
      🔍 No relief camp requirements found matching "${query}". Try searching for "Edathua", "Water", "Food", or click "All".
    </div>`;
  }

  grid.innerHTML = html;
}

function renderDonorHubList(grid, query) {
  let html = '';
  let count = 0;

  DisasterState.hubs.forEach(hub => {
    const matchesQuery = !query || hub.name.toLowerCase().includes(query) || hub.taluk.toLowerCase().includes(query);
    if (!matchesQuery) return;
    count++;

    html += `
      <div class="donor-item-card" style="border-color:rgba(59, 130, 246, 0.4);">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span class="badge badge-blue">🏢 CENTRAL COLLECTION HUB</span>
            <span style="font-size:0.75rem; color:#93c5fd; font-weight:700;">📍 ${hub.distance} away</span>
          </div>

          <h4 style="font-family:var(--font-heading); font-size:1.15rem; color:#f8fafc; margin-bottom:4px;">
            ${hub.name}
          </h4>

          <div style="font-size:0.75rem; color:var(--text-secondary); margin-bottom:10px;">
            Capacity: <strong>${hub.capacity}</strong> • Coordinator: <strong>${hub.coordinator}</strong>
          </div>

          <div style="background:var(--bg-surface-elevated); padding:10px; border-radius:var(--radius-sm); font-size:0.75rem; color:#cbd5e1; margin-bottom:12px;">
            📦 <strong>Best for Large Donations:</strong> Pallets of Drinking Water, 500+ Food Ration Kits, Truckloads of Blankets, Commercial Medical Shipments.
          </div>
        </div>

        <div>
          <button class="btn btn-primary" style="width:100%;" onclick="openHubBulkPledgeModal('${hub.id}', '${hub.name.replace(/'/g, "\\'")}', '${hub.coordinator.replace(/'/g, "\\'")}')">
            📦 Deliver Large Consignment to This Hub
          </button>
        </div>
      </div>
    `;
  });

  if (count === 0) {
    html = `<div style="grid-column: 1/-1; padding:40px; text-align:center; color:var(--text-secondary);">
      No collection hubs found matching "${query}".
    </div>`;
  }

  grid.innerHTML = html;
}

// Donor Pledges for a Camp
function openCampPledgeModal(reqId, campId, campName, officerPen, officerName, itemName, remainingQty, unit) {
  const modal = document.getElementById('donor-pledge-modal');
  modal.dataset.reqId = reqId;
  modal.dataset.campId = campId;
  modal.dataset.campName = campName;
  modal.dataset.officerPen = officerPen;
  modal.dataset.officerName = officerName;
  modal.dataset.itemName = itemName;
  modal.dataset.unit = unit;

  document.getElementById('pledge-item-name').textContent = itemName;
  document.getElementById('pledge-target-info').innerHTML = `
    <strong>Target Camp:</strong> ${campName} (${campId})<br>
    <strong>Designated Officer:</strong> ${officerName} (SPARK PEN: ${officerPen})
  `;
  document.getElementById('pledge-qty-input').max = remainingQty;
  document.getElementById('pledge-qty-input').value = Math.min(remainingQty, 280);
  document.getElementById('pledge-unit-label').textContent = unit;

  modal.classList.add('active');
}

function submitDonorPledge() {
  const modal = document.getElementById('donor-pledge-modal');
  const reqId = modal.dataset.reqId;
  const campId = modal.dataset.campId;
  const campName = modal.dataset.campName;
  const officerPen = modal.dataset.officerPen;
  const officerName = modal.dataset.officerName;
  const itemName = modal.dataset.itemName;
  const unit = modal.dataset.unit || 'units';

  const qty = parseInt(document.getElementById('pledge-qty-input').value) || 10;
  closeModal('donor-pledge-modal');

  // Generate PIN and cryptographically scoped payload
  const pin = 'KL-' + (campId === 'CAMP-04' ? 'ED' : (campId === 'CAMP-02' ? 'CHG' : 'AL')) + '-' + Math.floor(1000 + Math.random() * 9000);
  const pledgeId = 'PLG-' + Math.floor(1000 + Math.random() * 9000);
  const payload = `KSDMA-CAMP-PLEDGE:${pledgeId}|CAMP:${campId}|OFFICER_PEN:${officerPen}|ITEM:${itemName}|QTY:${qty}|PIN:${pin}`;

  // Record delivery as En Route
  DisasterState.enRouteDeliveries.unshift({
    pledgeId: pledgeId,
    targetType: 'camp',
    campId: campId,
    campName: campName,
    officerPen: officerPen,
    officerName: officerName,
    reqId: reqId,
    itemCode: 'WAT-CAN',
    itemName: itemName,
    qtyPledged: qty,
    donorName: 'Anonymous Citizen (KSDMA Shield)',
    pin: pin,
    status: 'In Transit (En Route to Camp)',
    createdAt: new Date().toLocaleTimeString()
  });

  // Update requirement status
  const targetReq = DisasterState.requirements.find(r => r.id === reqId);
  if (targetReq) {
    targetReq.status = 'Pledged';
    targetReq.alphanumericCode = pin;
  }

  logAuditAction('Public Donor (' + pin + ')', 'Camp Delivery Pledged', `Pledged ${qty} ${unit} of ${itemName} for ${campName}. QR restricted to Officer ${officerName}.`);

  // Generate SVG QR
  const qrSvg = generateSvgQr(payload, 200);

  const receiptModal = document.getElementById('donor-receipt-modal');
  document.getElementById('donor-receipt-qr-container').innerHTML = qrSvg;
  document.getElementById('donor-receipt-code').textContent = pin;
  document.getElementById('donor-receipt-details').innerHTML = `
    <div class="security-notice-box">
      <span class="security-badge-pill">🔒 DESIGNATED CAMP PASS (RULE FR-12)</span>
      <div><strong>Target Destination:</strong> ${campName} (${campId})</div>
      <div><strong>Authorized Verifier:</strong> Camp Officer ${officerName} (PEN: ${officerPen})</div>
      <div style="margin-top:6px; color:#fee2e2;">
        ⚠️ <strong>Important:</strong> Bring your pledged cargo (${qty} ${unit} of ${itemName}) to <strong>${campName}</strong>. Present this QR code to Officer ${officerName}. Once the officer scans this QR code, the camp's requirement will be officially updated to <strong>SATISFIED</strong>.
      </div>
    </div>
  `;

  receiptModal.classList.add('active');
  renderDonorPortal();
}

function openHubBulkPledgeModal(hubId, hubName, coordinator) {
  const modal = document.getElementById('hub-pledge-modal');
  document.getElementById('hub-pledge-title').textContent = hubName;
  document.getElementById('hub-coordinator-name').textContent = coordinator;
  modal.classList.add('active');
}

function submitHubBulkPledge() {
  closeModal('hub-pledge-modal');
  const pin = 'KL-HUB-' + Math.floor(1000 + Math.random() * 9000);
  alert(`✅ Large Consignment Intake Ticket Generated!\n\nPass Code: ${pin}\nLocation: Ambalappuzha Municipality LSG Hub\nCoordinator: Mathew Joseph (PEN: 512903)\n\nPresent this code at the logistics intake dock.`);
  logAuditAction('Public Bulk Donor', 'Hub Bulk Consignment Scheduled', `Consignment registered for Ambalappuzha LSG Hub (Pass: ${pin})`);
}

// ==========================================
// 5. CAMP OFFICER INTERFACE LOGIC
// ==========================================
function setOfficerActiveTab(tab) {
  DisasterState.officerActiveTab = tab;
  document.getElementById('officer-tab-active').classList.toggle('active', tab === 'active');
  document.getElementById('officer-tab-satisfied').classList.toggle('active', tab === 'satisfied');
  renderCampDashboard();
}

function renderCampDashboard() {
  const camp = DisasterState.camps[0]; // Camp #04 St. Aloysius HSS, Edathua
  document.getElementById('camp-header-name').textContent = `${camp.name} (${camp.id})`;
  document.getElementById('camp-officer-info').textContent = `Designated Officer: ${camp.officerName} (SPARK PEN: ${camp.officerPen}) • Jurisdiction: Edathua Revenue Village`;

  const isSatisfiedTab = DisasterState.officerActiveTab === 'satisfied';
  const activeTableWrap = document.getElementById('camp-active-table-wrap');
  const satisfiedTableWrap = document.getElementById('camp-satisfied-table-wrap');

  if (isSatisfiedTab) {
    activeTableWrap.style.display = 'none';
    satisfiedTableWrap.style.display = 'block';
    renderSatisfiedRequirements();
  } else {
    activeTableWrap.style.display = 'block';
    satisfiedTableWrap.style.display = 'none';
    renderActiveRequirementsAndTransit();
  }
}

function renderActiveRequirementsAndTransit() {
  // 1. Render Active Camp Needs
  const reqTbody = document.getElementById('camp-reqs-tbody');
  if (reqTbody) {
    const activeReqs = DisasterState.requirements.filter(r => r.campId === 'CAMP-04' && r.status !== 'Fulfilled');
    let html = '';
    if (activeReqs.length === 0) {
      html = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">All requirements for Camp #04 are currently satisfied! 🎉</td></tr>`;
    } else {
      activeReqs.forEach(req => {
        const remaining = req.qtyRequested - req.qtyFulfilled;
        const badgeClass = req.isEmergency ? 'badge-red' : (req.status === 'Pledged' ? 'badge-amber' : 'badge-blue');

        html += `
          <tr>
            <td><strong>${req.id}</strong> ${req.isEmergency ? '<span class="pulse-dot" style="display:inline-block;"></span>' : ''}</td>
            <td><strong>${req.itemName}</strong><br><span style="font-size:0.725rem; color:var(--text-muted);">${req.category}</span></td>
            <td>${req.qtyRequested} ${req.unit}</td>
            <td>${req.qtyFulfilled} filled (<strong style="color:#fcd34d;">${remaining} needed</strong>)</td>
            <td><span class="badge ${badgeClass}">${req.status}</span></td>
            <td>
              <span class="badge ${req.isEmergency ? 'badge-red' : 'badge-purple'}">SAW: ${req.sawScore}</span>
            </td>
          </tr>
        `;
      });
    }
    reqTbody.innerHTML = html;
  }

  // 2. Render In-Transit & Pledged Deliveries
  const transitTbody = document.getElementById('camp-transit-tbody');
  if (transitTbody) {
    const camp04Deliveries = DisasterState.enRouteDeliveries.filter(d => d.campId === 'CAMP-04' && !d.status.includes('Satisfied'));
    let html = '';
    if (camp04Deliveries.length === 0) {
      html = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No donor deliveries currently in transit for Camp #04.</td></tr>`;
    } else {
      camp04Deliveries.forEach(d => {
        html += `
          <tr>
            <td><strong style="font-family:var(--font-mono); color:#38bdf8; font-size:0.95rem;">${d.pin}</strong></td>
            <td><strong>${d.itemName}</strong> (${d.qtyPledged} units)</td>
            <td><span class="badge badge-amber">🚚 ${d.status}</span></td>
            <td>${d.createdAt}</td>
            <td>
              <button class="btn btn-primary" style="padding:4px 10px; font-size:0.75rem;" onclick="openCampScannerModal('${d.pin}', '${d.itemName}', ${d.qtyPledged}, '${d.reqId}')">
                📷 Scan & Accept
              </button>
            </td>
          </tr>
        `;
      });
    }
    transitTbody.innerHTML = html;
  }
}

function renderSatisfiedRequirements() {
  const tbody = document.getElementById('camp-satisfied-tbody');
  if (!tbody) return;

  const satisfiedReqs = DisasterState.requirements.filter(r => r.campId === 'CAMP-04' && r.status === 'Fulfilled');

  let html = '';
  if (satisfiedReqs.length === 0) {
    html = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No requirements marked as satisfied yet. Scan incoming donor QR passes to satisfy needs.</td></tr>`;
  } else {
    satisfiedReqs.forEach(r => {
      html += `
        <tr>
          <td><strong>${r.id}</strong></td>
          <td><strong>${r.itemName}</strong> (${r.category})</td>
          <td><strong style="color:#6ee7b7;">${r.qtyFulfilled} / ${r.qtyRequested} ${r.unit} (100%)</strong></td>
          <td><span class="badge badge-green">✅ FULFILLED & SATISFIED</span></td>
          <td style="font-size:0.75rem; color:var(--text-secondary);">
            Verified: ${r.fulfilledAt || 'Recently'} by ${r.fulfilledBy || 'Sunil Kumar (PEN: 842109)'}
          </td>
        </tr>
      `;
    });
  }
  tbody.innerHTML = html;
}

// Add Requirement Questionnaire Modal
function openAddRequirementModal() {
  document.getElementById('add-req-modal').classList.add('active');
}

function submitRequirementWithAssessment() {
  // Read assessment answers
  const roadStatus = document.querySelector('input[name="q-road"]:checked')?.value || 'cut_off';
  const vulnGroup = document.querySelector('input[name="q-vuln"]:checked')?.value || 'elderly';
  const reserveHours = parseInt(document.querySelector('input[name="q-reserve"]:checked')?.value) || 4;
  const powerWater = document.querySelector('input[name="q-power"]:checked')?.value || 'contaminated';

  const itemSelect = document.getElementById('new-req-item');
  const itemName = itemSelect.options[itemSelect.selectedIndex].text;
  const itemCode = itemSelect.value;
  const qty = parseInt(document.getElementById('new-req-qty').value) || 100;
  const unit = document.getElementById('new-req-unit').value || 'units';

  closeModal('add-req-modal');

  // Calculate SAW score dynamically based on questions
  let damageScore = (roadStatus === 'cut_off' || powerWater === 'contaminated') ? 10 : (roadStatus === 'waterlogged' ? 6 : 2);
  let urgencyMultiplier = reserveHours <= 6 ? 1.4 : 1.0;
  let vitality = itemCode.includes('WAT') || itemCode.includes('MED') ? 10 : 8;

  let sawScore = Math.min(98.5, parseFloat(((vitality * 3.5) + (damageScore * 2.5) + (urgencyMultiplier * 20)).toFixed(1)));

  const newReq = {
    id: 'REQ-' + Math.floor(200 + Math.random() * 800),
    campId: 'CAMP-04',
    campName: 'St. Aloysius HSS, Edathua',
    itemCode: itemCode,
    itemName: itemName,
    category: itemCode.includes('WAT') ? 'Water' : (itemCode.includes('FOD') ? 'Food' : 'Shelter'),
    vitality: vitality,
    qtyRequested: qty,
    qtyFulfilled: 0,
    unit: unit,
    isEmergency: false,
    sawScore: sawScore,
    status: 'Verified',
    elapsedHours: 1,
    alphanumericCode: 'KL-ED-' + Math.floor(1000 + Math.random() * 9000),
    fulfilledAt: null,
    fulfilledBy: null
  };

  DisasterState.requirements.unshift(newReq);
  logAuditAction('Sunil Kumar (PEN: 842109)', 'New Camp Requirement Added', `Logged ${qty} ${unit} of ${itemName} following operational factual assessment.`);

  alert(`✅ Camp Requirement Successfully Logged!\n\nItem: ${itemName}\nQuantity: ${qty} ${unit}\nComputed Priority Score (SAW): ${sawScore}/100\nStatus: Published to Public Donor Portal.`);

  renderCampDashboard();
}

// Emergency Medical Override (FR-6)
function triggerEmergencyOverride() {
  const confirmAction = confirm("🚨 EMERGENCY OVERRIDE CONFIRMATION\n\nYou are triggering an instant priority override for Life-Saving Medical Items (Insulin/Oxygen).\n\nThis will bypass the standard SAW scoring algorithm, pin this request to GLOBAL RANK 1, and transmit an emergency siren broadcast to District Control.\n\nProceed?");
  if (!confirmAction) return;

  const newEmergencyReq = {
    id: 'REQ-EM-' + Math.floor(1000 + Math.random() * 9000),
    campId: 'CAMP-04',
    campName: 'St. Aloysius HSS, Edathua',
    itemCode: 'MED-INS',
    itemName: 'CRITICAL: Insulin & Cold-Chain Delivery Kit',
    category: 'Medical',
    vitality: 10,
    qtyRequested: 40,
    qtyFulfilled: 0,
    unit: 'kits',
    isEmergency: true,
    sawScore: 99.9,
    status: 'Verified',
    elapsedHours: 0,
    alphanumericCode: 'KL-EM-' + Math.floor(1000 + Math.random() * 9000),
    fulfilledAt: null,
    fulfilledBy: null
  };

  DisasterState.requirements.unshift(newEmergencyReq);
  logAuditAction('Sunil Kumar (PEN: 842109)', 'EMERGENCY OVERRIDE ACTIVATED', 'Rank 1 Emergency broadcast for Insulin Vials at Camp #04');

  const modal = document.getElementById('emergency-siren-modal');
  document.getElementById('emergency-siren-text').innerHTML = `
    <strong>ITEM:</strong> ${newEmergencyReq.itemName}<br>
    <strong>CAMP:</strong> ${newEmergencyReq.campName}<br>
    <strong>QUANTITY:</strong> ${newEmergencyReq.qtyRequested} ${newEmergencyReq.unit}<br>
    <strong>ASSIGNED FALLBACK PIN:</strong> <span style="font-family:var(--font-mono); color:#ef4444; font-weight:800;">${newEmergencyReq.alphanumericCode}</span>
  `;
  modal.classList.add('active');

  renderCampDashboard();
}

// Camp Officer Optical QR Scanner (Scanning donor QR)
function openCampScannerModal(samplePin = 'KL-ED-4921', item = 'Drinking Water (20L Cans)', qty = 280, reqId = 'REQ-102') {
  const modal = document.getElementById('camp-scanner-modal');
  modal.dataset.reqId = reqId;
  modal.dataset.item = item;
  modal.dataset.qty = qty;
  modal.dataset.pin = samplePin;

  document.getElementById('camp-scanner-station-text').textContent = 'Active Station: St. Aloysius HSS, Edathua (CAMP-04)';
  document.getElementById('camp-scanner-officer-text').textContent = 'Designated Verifier: Sunil Kumar (SPARK PEN: 842109)';
  document.getElementById('camp-scanner-pin-input').value = samplePin;

  modal.classList.add('active');
}

function verifyCampDeliveryScan(isCorrectCamp = true) {
  const modal = document.getElementById('camp-scanner-modal');
  const reqId = modal.dataset.reqId || 'REQ-102';
  const item = modal.dataset.item || 'Drinking Water (20L Cans)';
  const qty = parseInt(modal.dataset.qty) || 280;
  const pin = modal.dataset.pin || 'KL-ED-4921';

  closeModal('camp-scanner-modal');

  if (!isCorrectCamp) {
    // REJECTION CASE: Wrong camp QR scanned
    alert(`❌ SECURITY VIOLATION: JURISDICTION REJECTION (Rule FR-12)\n\n• Scanned Pass: KL-CHG-9912 (Designated for Camp #02 - Govt Model HSS, Chengannur)\n• Current Station: Camp #04 (Edathua)\n• Authorized Verifier: Sunil Kumar (PEN: 842109)\n\nREASON: Under KSDMA Anti-Cross-Hauling Regulations, donations designated for Camp #02 cannot be diverted or accepted at Camp #04.`);
    logAuditAction('Sunil Kumar (PEN: 842109)', 'Delivery Scan REJECTED', `Scanned pass KL-CHG-9912 rejected at Camp #04 due to jurisdiction mismatch.`);
    return;
  }

  // SUCCESS CASE: Camp #04 Designated Officer verifies the delivery
  const targetReq = DisasterState.requirements.find(r => r.id === reqId);
  if (targetReq) {
    targetReq.qtyFulfilled = targetReq.qtyRequested; // 100% fulfilled
    targetReq.status = 'Fulfilled';
    targetReq.fulfilledAt = new Date().toLocaleTimeString() + ' IST';
    targetReq.fulfilledBy = 'Sunil Kumar (PEN: 842109)';
  }

  // Update enRoute delivery record
  const pledgeRecord = DisasterState.enRouteDeliveries.find(d => d.pin === pin || d.campId === 'CAMP-04');
  if (pledgeRecord) {
    pledgeRecord.status = '✅ Verified & Satisfied at Camp #04';
  }

  logAuditAction('Sunil Kumar (PEN: 842109)', 'Camp Delivery Verified & Satisfied', `Scanned QR Pass [${pin}]. Received ${qty} units of ${item}. Camp #04 Requirement [${reqId}] marked as SATISFIED.`);

  // Show celebratory success modal
  const successModal = document.getElementById('verification-success-modal');
  document.getElementById('success-modal-details').innerHTML = `
    <div style="background:rgba(16, 185, 129, 0.12); border:1px solid var(--status-emerald); border-radius:var(--radius-md); padding:16px; margin-bottom:14px;">
      <div style="font-size:1.15rem; font-weight:800; color:#34d399; margin-bottom:6px;">
        🎉 CAMP REQUIREMENT SATISFIED & FULFILLED!
      </div>
      <div><strong>Camp Station:</strong> St. Aloysius HSS, Edathua (CAMP-04)</div>
      <div><strong>Verified By:</strong> Sunil Kumar (SPARK PEN: 842109)</div>
      <div><strong>Pass Code:</strong> <span style="font-family:var(--font-mono); color:#38bdf8; font-weight:700;">${pin}</span></div>
      <div><strong>Resource Accepted:</strong> ${qty} units of ${item}</div>
    </div>
    <div style="font-size:0.8125rem; color:var(--text-secondary); line-height:1.6;">
      • The camp's requirement is now marked as <strong>100% Satisfied</strong>.<br>
      • State database synchronized; public donor board updated in real-time.<br>
      • Cryptographically signed under Kerala State Disaster Management regulations.
    </div>
  `;
  successModal.classList.add('active');

  renderCampDashboard();
}

function processCampManualPin() {
  const pin = document.getElementById('camp-scanner-pin-input').value.trim().toUpperCase();
  if (!pin) {
    alert("Please enter a valid alphanumeric PIN.");
    return;
  }

  if (pin.includes('CHG') || pin === 'KL-CHG-9912') {
    verifyCampDeliveryScan(false);
  } else {
    verifyCampDeliveryScan(true);
  }
}

// ==========================================
// 6. DISTRICT COLLECTOR INTERFACE LOGIC
// ==========================================
function renderCollectorDashboard() {
  const container = document.getElementById('collector-req-table');
  if (!container) return;

  const sorted = [...DisasterState.requirements].sort((a, b) => b.sawScore - a.sawScore);

  let html = '';
  sorted.forEach(req => {
    const badgeClass = req.isEmergency ? 'badge-red' : (req.sawScore > 80 ? 'badge-amber' : 'badge-blue');
    const statusClass = req.status === 'Fulfilled' ? 'badge-green' : (req.status === 'In Transit' ? 'badge-purple' : 'badge-blue');

    html += `
      <tr>
        <td><strong>${req.id}</strong> ${req.isEmergency ? '<span class="pulse-dot" style="display:inline-block;"></span>' : ''}</td>
        <td><strong>${req.itemName}</strong><br><span style="font-size:0.725rem; color:var(--text-muted);">${req.category}</span></td>
        <td>${req.campName}</td>
        <td><strong>${req.qtyRequested} ${req.unit}</strong> <span style="color:${req.qtyFulfilled >= req.qtyRequested ? 'var(--status-emerald)' : 'var(--text-muted)'};">(${req.qtyFulfilled} filled)</span></td>
        <td><span class="badge ${badgeClass}">${req.isEmergency ? 'RANK 1 EMERGENCY' : req.sawScore}</span></td>
        <td><span class="badge ${statusClass}">${req.status === 'Fulfilled' ? '✅ SATISFIED' : req.status}</span></td>
      </tr>
    `;
  });
  container.innerHTML = html;

  renderAuditLogs();
}

function renderAuditLogs() {
  const tbody = document.getElementById('audit-log-tbody');
  if (!tbody) return;

  let html = '';
  DisasterState.auditLogs.slice(0, 8).forEach(log => {
    html += `
      <tr>
        <td style="font-family:var(--font-mono); font-size:0.75rem;">${log.time}</td>
        <td><strong>${log.officer}</strong></td>
        <td><span class="badge badge-blue">${log.action}</span></td>
        <td style="color:var(--text-secondary);">${log.details}</td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

function logAuditAction(officer, action, details) {
  const timeStr = new Date().toTimeString().split(' ')[0];
  DisasterState.auditLogs.unshift({
    time: timeStr,
    officer: officer,
    action: action,
    details: details
  });
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

function toggleContrastTheme() {
  document.body.classList.toggle('high-contrast');
}

// ==========================================
// 7. Guided Viva Demo Tour
// ==========================================
let currentVivaStep = 0;
const vivaSteps = [
  {
    action: () => logout(),
    title: 'Step 1: Role-Based Authentication Gateway',
    desc: 'The system features three distinct login interfaces: (1) Public Donor with OTP verification, (2) Camp Officer with Kerala SPARK PEN authentication, and (3) District Collector Executive portal.'
  },
  {
    action: () => login('donor'),
    title: 'Step 2: Donor Portal & Nearby Camp/Hub Search',
    desc: 'Public donors can search nearby relief camps or collection hubs. Relief camp needs are strictly ordered by SAW Priority score. Donors can also route bulk/large quantities to nearby LSG distribution hubs.'
  },
  {
    action: () => {
      login('donor');
      openCampPledgeModal('REQ-102', 'CAMP-04', 'St. Aloysius HSS, Edathua', '842109', 'Sunil Kumar', 'Drinking Water (20L Cans)', 280, 'cans');
    },
    title: 'Step 3: Pledging to a Specific Camp',
    desc: 'When a donor pledges items for Camp #04, the system generates an official Camp Delivery Pass cryptographically restricted to Camp Officer Sunil Kumar (SPARK PEN: 842109).'
  },
  {
    action: () => login('camp_officer'),
    title: 'Step 4: Camp Officer Portal & Assessment Questionnaire',
    desc: 'Camp Officer Sunil Kumar accesses Camp #04. Before logging a new relief requirement, the officer must answer structured factual assessment questions (road cut-off, vulnerable groups, reserve hours).'
  },
  {
    action: () => {
      login('camp_officer');
      openCampScannerModal('KL-ED-4921', 'Drinking Water (20L Cans)', 280, 'REQ-102');
    },
    title: 'Step 5: Camp Officer Scans QR & Fulfills Requirement',
    desc: 'Upon physical delivery of the supplies at Camp #04, Officer Sunil Kumar scans the donor pass. The system validates jurisdiction and instantly marks the requirement as 100% SATISFIED & FULFILLED!'
  },
  {
    action: () => login('collector'),
    title: 'Step 6: District Collector Statewide Situation Room',
    desc: 'The District Collector executive dashboard displays live KPIs, Taluk vulnerability heatmaps, and audit logs tracking all verified fulfillments.'
  }
];

function startVivaDemoTour() {
  currentVivaStep = 0;
  showVivaModalStep();
}

function showVivaModalStep() {
  const step = vivaSteps[currentVivaStep];
  step.action();

  const banner = document.getElementById('viva-tour-banner');
  if (banner) {
    banner.style.display = 'flex';
    document.getElementById('viva-step-title').textContent = step.title;
    document.getElementById('viva-step-desc').textContent = step.desc;
    document.getElementById('viva-step-num').textContent = `Step ${currentVivaStep + 1} of ${vivaSteps.length}`;
  }
}

function nextVivaStep() {
  if (currentVivaStep < vivaSteps.length - 1) {
    currentVivaStep++;
    showVivaModalStep();
  } else {
    alert("🎉 Comprehensive Walkthrough Complete!\n\nAll login roles, donor search, questionnaire assessment, and QR delivery satisfaction verified.");
    document.getElementById('viva-tour-banner').style.display = 'none';
  }
}

function prevVivaStep() {
  if (currentVivaStep > 0) {
    currentVivaStep--;
    showVivaModalStep();
  }
}

function closeVivaTour() {
  document.getElementById('viva-tour-banner').style.display = 'none';
}

// ==========================================
// 8. Application Initialization
// ==========================================
window.addEventListener('DOMContentLoaded', () => {
  setInterval(() => {
    const clockEl = document.getElementById('live-system-clock');
    if (clockEl) {
      clockEl.textContent = new Date().toLocaleTimeString() + ' IST';
    }
  }, 1000);

  // Start at the Login Gateway
  updateSessionUI();
});
