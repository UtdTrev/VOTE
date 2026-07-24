const DEFAULT_STATE = {
  settings: {
    title: "Campus Icons Awards 2026",
    votePrice: 100,
    gateway: "Paystack",
    status: "open",
  },
  contestants: [
    {
      id: "c001",
      name: "Adaeze Nwosu",
      code: "CI-001",
      category: "Fashion",
      region: "University of Abuja",
      bio: "Style creator, campus ambassador, and student entrepreneur.",
      votes: 7420,
      gradient: "linear-gradient(135deg, #ff7a90, #8b5cf6)",
      createdAt: 1,
    },
    {
      id: "c002",
      name: "Tobi Akinwale",
      code: "CI-002",
      category: "Music",
      region: "Baze University",
      bio: "Afro-fusion vocalist building a loyal student fan base.",
      votes: 8950,
      gradient: "linear-gradient(135deg, #22d3ee, #2563eb)",
      createdAt: 2,
    },
    {
      id: "c003",
      name: "Zainab Bello",
      code: "CI-003",
      category: "Leadership",
      region: "Nile University",
      bio: "Volunteer coordinator and award-winning debate captain.",
      votes: 6410,
      gradient: "linear-gradient(135deg, #f59e0b, #ef4444)",
      createdAt: 3,
    },
    {
      id: "c004",
      name: "Chidera Okeke",
      code: "CI-004",
      category: "Tech",
      region: "Veritas University",
      bio: "Frontend developer and founder of a campus coding circle.",
      votes: 5125,
      gradient: "linear-gradient(135deg, #2ee59d, #0ea5e9)",
      createdAt: 4,
    },
    {
      id: "c005",
      name: "Musa Danladi",
      code: "CI-005",
      category: "Sports",
      region: "UniAbuja Sports Club",
      bio: "Team captain, fitness coach, and community mentor.",
      votes: 3860,
      gradient: "linear-gradient(135deg, #a3e635, #16a34a)",
      createdAt: 5,
    },
    {
      id: "c006",
      name: "Ifeoma Eze",
      code: "CI-006",
      category: "Media",
      region: "National Open University",
      bio: "Content producer and host of a student culture podcast.",
      votes: 4680,
      gradient: "linear-gradient(135deg, #ec4899, #f97316)",
      createdAt: 6,
    },
  ],
  payments: [
    {
      reference: "TVE-DEMO-001",
      voter: "Sandra U.",
      email: "sandra@example.com",
      phone: "08030000001",
      contestantId: "c002",
      votes: 120,
      amount: 10000,
      status: "verified",
      createdAt: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    },
    {
      reference: "TVE-DEMO-002",
      voter: "Michael O.",
      email: "michael@example.com",
      phone: "08030000002",
      contestantId: "c001",
      votes: 55,
      amount: 5000,
      status: "verified",
      createdAt: new Date(Date.now() - 1000 * 60 * 46).toISOString(),
    },
  ],
};

const PACKAGES = [
  { id: "basic", name: "Starter", votes: 5, amount: 500, tag: "Entry", description: "Quick support for any contestant." },
  { id: "bronze", name: "Bronze", votes: 10, amount: 1000, tag: "Popular", description: "Simple ₦100-per-vote bundle." },
  { id: "silver", name: "Silver", votes: 55, amount: 5000, tag: "Bonus", description: "Get 5 extra votes on this package." },
  { id: "gold", name: "Gold", votes: 120, amount: 10000, tag: "Best value", description: "High-impact voting for loyal supporters." },
];

const STORAGE_KEY = "trev_vote_engine_state_v1";
const API_BASE = window.TREV_VOTE_API_BASE || (window.location.protocol.startsWith("http") ? window.location.origin : "http://127.0.0.1:8000");
const ADMIN_SESSION_KEY = "trev_vote_admin_session_v1";
let backendConnected = false;
let adminSession = loadAdminSession();

let state = loadState();
let selectedContestantId = null;
let selectedPackage = PACKAGES[1];
let selectedVotes = selectedPackage.votes;
let selectedAmount = selectedPackage.amount;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function cloneDefaultState() {
  return JSON.parse(JSON.stringify(DEFAULT_STATE));
}

function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return cloneDefaultState();
  try {
    const parsed = JSON.parse(saved);
    return {
      ...cloneDefaultState(),
      ...parsed,
      settings: { ...DEFAULT_STATE.settings, ...(parsed.settings || {}) },
      contestants: parsed.contestants?.length ? parsed.contestants : DEFAULT_STATE.contestants,
      payments: parsed.payments || [],
    };
  } catch {
    return cloneDefaultState();
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function loadAdminSession() {
  try {
    return JSON.parse(localStorage.getItem(ADMIN_SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

function saveAdminSession(session) {
  adminSession = session;
  if (session) {
    localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(ADMIN_SESSION_KEY);
  }
}

function adminHeaders(extra = {}) {
  return {
    ...extra,
    ...(adminSession?.token ? { Authorization: `Bearer ${adminSession.token}` } : {}),
  };
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(amount || 0);
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-NG").format(value || 0);
}

function initials(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function totals() {
  const votes = state.contestants.reduce((sum, c) => sum + Number(c.votes || 0), 0);
  const revenue = state.payments
    .filter((p) => p.status === "verified")
    .reduce((sum, p) => sum + Number(p.amount || 0), 0);
  return { votes, revenue, transactions: state.payments.filter((p) => p.status === "verified").length };
}

function sortedContestants(mode = "rank") {
  const list = [...state.contestants];
  if (mode === "name") return list.sort((a, b) => a.name.localeCompare(b.name));
  if (mode === "recent") return list.sort((a, b) => Number(b.createdAt || 0) - Number(a.createdAt || 0));
  return list.sort((a, b) => Number(b.votes || 0) - Number(a.votes || 0));
}

function getRankMap() {
  return Object.fromEntries(sortedContestants("rank").map((c, index) => [c.id, index + 1]));
}

function getContestant(id) {
  return state.contestants.find((c) => c.id === id);
}

function renderPackages() {
  const packageGrid = $("#packageGrid");
  packageGrid.innerHTML = PACKAGES.map((pkg, index) => `
    <article class="package-card ${index === 2 ? "featured" : ""}">
      <span class="tag">${pkg.tag}</span>
      <h3>${pkg.name}</h3>
      <strong>${formatCurrency(pkg.amount)}</strong>
      <p>${formatNumber(pkg.votes)} votes. ${pkg.description}</p>
      <button class="secondary-btn" type="button" data-package-vote="${pkg.id}">Use package</button>
    </article>
  `).join("");

  $$(`[data-package-vote]`).forEach((button) => {
    button.addEventListener("click", () => {
      const pkg = PACKAGES.find((item) => item.id === button.dataset.packageVote);
      selectedPackage = pkg;
      selectedVotes = pkg.votes;
      selectedAmount = pkg.amount;
      const firstContestant = sortedContestants("rank")[0];
      openVoteModal(firstContestant.id);
    });
  });
}

function renderCategoryFilter() {
  const currentValue = $("#categoryFilter").value || "all";
  const categories = [...new Set(state.contestants.map((c) => c.category).filter(Boolean))].sort();
  $("#categoryFilter").innerHTML = `<option value="all">All categories</option>${categories
    .map((category) => `<option value="${category}">${category}</option>`)
    .join("")}`;
  $("#categoryFilter").value = categories.includes(currentValue) ? currentValue : "all";
}

function renderContestants() {
  renderCategoryFilter();
  const query = $("#searchInput").value.trim().toLowerCase();
  const category = $("#categoryFilter").value;
  const sortMode = $("#sortFilter").value;
  const rankMap = getRankMap();
  const maxVotes = Math.max(...state.contestants.map((c) => c.votes), 1);

  const filtered = sortedContestants(sortMode).filter((contestant) => {
    const matchesCategory = category === "all" || contestant.category === category;
    const haystack = `${contestant.name} ${contestant.code} ${contestant.category} ${contestant.region}`.toLowerCase();
    return matchesCategory && haystack.includes(query);
  });

  $("#contestantGrid").innerHTML = filtered.length
    ? filtered.map((contestant) => `
      <article class="contestant-card" style="--contestant-gradient: ${contestant.gradient}">
        <div class="contestant-visual">
          ${contestant.photoUrl ? `<img class="contestant-photo" src="${contestant.photoUrl}" alt="${contestant.name}">` : `<div class="contestant-avatar">${initials(contestant.name)}</div>`}
          <span class="rank-badge">#${rankMap[contestant.id]}</span>
        </div>
        <div class="contestant-body">
          <div class="contestant-meta">
            <span class="code-badge">${contestant.code}</span>
            <span class="category-pill">${contestant.category}</span>
          </div>
          <h3>${contestant.name}</h3>
          <p>${contestant.bio}</p>
          <div class="vote-line">
            <span>${contestant.region}</span>
            <strong>${formatNumber(contestant.votes)}</strong>
          </div>
          <div class="progress-track"><div class="progress-bar" style="width: ${Math.max(8, (contestant.votes / maxVotes) * 100)}%"></div></div>
          <button class="primary-btn" type="button" data-vote="${contestant.id}">Vote for ${contestant.name.split(" ")[0]}</button>
        </div>
      </article>
    `).join("")
    : `<div class="empty-state">No contestants match your search.</div>`;

  $$(`[data-vote]`).forEach((button) => {
    button.addEventListener("click", () => openVoteModal(button.dataset.vote));
  });
}

function renderLeaderboard() {
  const ranked = sortedContestants("rank");
  const maxVotes = Math.max(...ranked.map((c) => c.votes), 1);
  $("#leaderboardList").innerHTML = ranked.map((contestant, index) => `
    <div class="leaderboard-row">
      <div class="leaderboard-rank">${index + 1}</div>
      <div>
        <h4>${contestant.name}</h4>
        <p>${contestant.code} • ${contestant.category}</p>
        <div class="progress-track" style="margin-top: 10px;"><div class="progress-bar" style="width: ${Math.max(8, (contestant.votes / maxVotes) * 100)}%"></div></div>
      </div>
      <strong>${formatNumber(contestant.votes)} votes</strong>
    </div>
  `).join("");
  $("#leaderboardUpdated").textContent = `Updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function renderHeroAndMetrics() {
  const { votes, revenue, transactions } = totals();
  const leader = sortedContestants("rank")[0];

  $("#heroTotalRevenue").textContent = formatCurrency(revenue);
  $("#heroTotalVotes").textContent = formatNumber(votes);
  $("#heroTxCount").textContent = formatNumber(transactions);
  $("#reportTotalRevenue").textContent = formatCurrency(revenue);

  $("#heroLeaderCard").innerHTML = leader ? `
    <div class="leader-mini">
      <div class="avatar" style="background:${leader.gradient}">${initials(leader.name)}</div>
      <div>
        <small>Current leader</small>
        <h3>${leader.name}</h3>
        <p>${formatNumber(leader.votes)} votes • ${leader.code}</p>
      </div>
    </div>
  ` : "";

  const badge = $("#contestStatusBadge");
  badge.textContent = state.settings.status;
  badge.className = state.settings.status;
}

function renderAdminAuth() {
  const box = $("#adminAuthCard");
  if (!box) return;

  if (!adminSession?.token) {
    box.innerHTML = `
      <div class="admin-auth-inner">
        <div>
          <p class="eyebrow-text">Admin access</p>
          <h3>Login to manage contestants, photos, settings and exports.</h3>
          <p>Default local admin: <strong>admin@trevvote.local</strong> / <strong>admin12345</strong>. Change with ADMIN_EMAIL and ADMIN_PASSWORD in production.</p>
        </div>
        <form id="adminLoginForm" class="admin-login-form">
          <input id="adminEmail" type="email" placeholder="admin@trevvote.local" value="admin@trevvote.local" autocomplete="username">
          <input id="adminPassword" type="password" placeholder="Password" value="admin12345" autocomplete="current-password">
          <button class="primary-btn" type="submit">Login</button>
        </form>
      </div>
    `;
    $("#adminLoginForm")?.addEventListener("submit", handleAdminLogin);
    return;
  }

  box.innerHTML = `
    <div class="admin-auth-inner logged-in">
      <div>
        <p class="eyebrow-text">Admin session</p>
        <h3>${adminSession.admin?.email || "Admin"}</h3>
        <p>Role: <strong>${adminSession.admin?.role || "admin"}</strong>. Backend: <strong>${backendConnected ? "connected" : "checking"}</strong>.</p>
      </div>
      <div class="admin-auth-actions">
        <button class="secondary-btn" type="button" id="exportPaymentsBtn">Export payments CSV</button>
        <button class="secondary-btn" type="button" id="exportContestantsBtn">Export contestants CSV</button>
        <button class="ghost-btn" type="button" id="adminLogoutBtn">Logout</button>
      </div>
    </div>
  `;
  $("#exportPaymentsBtn")?.addEventListener("click", () => downloadReport("/api/admin/reports/payments.csv", "trevvote-payments.csv"));
  $("#exportContestantsBtn")?.addEventListener("click", () => downloadReport("/api/admin/reports/contestants.csv", "trevvote-contestants.csv"));
  $("#adminLogoutBtn")?.addEventListener("click", handleAdminLogout);
}

async function handleAdminLogin(event) {
  event.preventDefault();
  const email = $("#adminEmail").value.trim();
  const password = $("#adminPassword").value;
  try {
    const response = await fetch(`${API_BASE}/api/admin/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Login failed");
    saveAdminSession(result);
    backendConnected = true;
    await fetchRemoteState();
    renderAdmin();
    showToast("Admin login successful.", "success");
  } catch (error) {
    showToast(`Admin login failed: ${error.message}`, "error");
  }
}

async function handleAdminLogout() {
  try {
    await fetch(`${API_BASE}/api/admin/logout`, { method: "POST", headers: adminHeaders() });
  } catch {}
  saveAdminSession(null);
  renderAdmin();
  showToast("Logged out.", "success");
}

async function downloadReport(endpoint, filename) {
  if (!adminSession?.token) return showToast("Admin login required.", "error");
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, { headers: adminHeaders() });
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.error || "Export failed");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    showToast(`Export failed: ${error.message}`, "error");
  }
}

function renderAdmin() {
  renderAdminAuth();
  const { votes, revenue, transactions } = totals();
  const top = sortedContestants("rank")[0];
  $("#adminRevenue").textContent = formatCurrency(revenue);
  $("#adminVotes").textContent = formatNumber(votes);
  $("#adminTransactions").textContent = formatNumber(transactions);
  $("#adminTopContestant").textContent = top ? top.name.split(" ")[0] : "—";
  $("#contestantCount").textContent = `${state.contestants.length} total`;

  const maxVotes = Math.max(...state.contestants.map((c) => c.votes), 1);
  $("#voteBars").innerHTML = sortedContestants("rank").map((contestant) => `
    <div class="vote-bar-row">
      <span>${contestant.name}</span>
      <div class="progress-track"><div class="progress-bar" style="width: ${Math.max(6, (contestant.votes / maxVotes) * 100)}%"></div></div>
      <strong>${formatNumber(contestant.votes)}</strong>
    </div>
  `).join("");

  $("#adminContestantRows").innerHTML = state.contestants.map((contestant) => `
    <tr>
      <td><strong>${contestant.name}</strong><br><span>${contestant.region || "—"}</span></td>
      <td>${contestant.code}</td>
      <td>${contestant.category}</td>
      <td><strong>${formatNumber(contestant.votes)}</strong></td>
      <td>
        ${contestant.photoUrl ? `<img class="admin-photo-thumb" src="${contestant.photoUrl}" alt="${contestant.name}">` : `<span>—</span>`}
        <label class="upload-btn">Upload<input type="file" accept="image/png,image/jpeg,image/webp" data-photo="${contestant.id}" hidden></label>
      </td>
      <td><button class="delete-btn" type="button" data-delete="${contestant.id}">Remove</button></td>
    </tr>
  `).join("");

  $$(`[data-delete]`).forEach((button) => {
    button.addEventListener("click", () => deleteContestant(button.dataset.delete));
  });

  $$(`[data-photo]`).forEach((input) => {
    input.addEventListener("change", () => uploadContestantPhoto(input.dataset.photo, input.files?.[0]));
  });

  const paymentRows = [...state.payments]
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    .slice(0, 12);

  $("#paymentRows").innerHTML = paymentRows.length ? paymentRows.map((payment) => {
    const contestant = getContestant(payment.contestantId);
    return `
      <tr>
        <td><strong>${payment.reference}</strong></td>
        <td>${payment.voter}<br><span>${payment.phone || payment.email || "—"}</span></td>
        <td>${contestant ? contestant.name : "Deleted contestant"}</td>
        <td>${formatNumber(payment.votes)}</td>
        <td><strong>${formatCurrency(payment.amount)}</strong></td>
        <td><span class="status-pill">${payment.status}</span></td>
      </tr>
    `;
  }).join("") : `<tr><td colspan="6">No payments yet.</td></tr>`;

  $("#settingTitle").value = state.settings.title;
  $("#settingVotePrice").value = state.settings.votePrice;
  $("#settingGateway").value = state.settings.gateway;
  $("#settingStatus").value = state.settings.status;
  $("#summaryGateway").textContent = state.settings.gateway;
}

function renderAll() {
  renderPackages();
  renderContestants();
  renderLeaderboard();
  renderHeroAndMetrics();
  renderAdmin();
  updateSummary();
}

function openVoteModal(contestantId) {
  if (state.settings.status !== "open") {
    return showToast(`Voting is currently ${state.settings.status}.`, "error");
  }
  selectedContestantId = contestantId;
  const contestant = getContestant(contestantId);
  if (!contestant) return;

  $("#modalContestantName").textContent = contestant.name;
  $("#modalContestantCard").style.setProperty("--contestant-gradient", contestant.gradient);
  $("#modalContestantCard").innerHTML = `
    <div class="modal-contestant-inner">
      <div>
        <span class="code-badge" style="color:white;border-color:rgba(255,255,255,.35);background:rgba(255,255,255,.16)">${contestant.code}</span>
        <h3>${contestant.name}</h3>
        <p>${contestant.bio}</p>
      </div>
      <div>
        ${contestant.photoUrl ? `<img class="contestant-photo modal-photo" src="${contestant.photoUrl}" alt="${contestant.name}">` : `<div class="contestant-avatar">${initials(contestant.name)}</div>`}
        <p><strong>${formatNumber(contestant.votes)}</strong> verified votes so far</p>
      </div>
    </div>
  `;

  renderModalPackages();
  updateSummary();
  $("#voteModal").classList.add("active");
  $("#voteModal").setAttribute("aria-hidden", "false");
}

function closeVoteModal() {
  $("#voteModal").classList.remove("active");
  $("#voteModal").setAttribute("aria-hidden", "true");
}

function renderModalPackages() {
  $("#modalPackages").innerHTML = PACKAGES.map((pkg) => `
    <button class="modal-package-btn ${selectedPackage?.id === pkg.id ? "active" : ""}" type="button" data-modal-package="${pkg.id}">
      <strong>${formatCurrency(pkg.amount)}</strong>
      <span>${formatNumber(pkg.votes)} votes • ${pkg.name}</span>
    </button>
  `).join("");

  $$(`[data-modal-package]`).forEach((button) => {
    button.addEventListener("click", () => {
      const pkg = PACKAGES.find((item) => item.id === button.dataset.modalPackage);
      selectedPackage = pkg;
      selectedVotes = pkg.votes;
      selectedAmount = pkg.amount;
      $("#customVotes").value = "";
      renderModalPackages();
      updateSummary();
    });
  });
}

function updateSummary() {
  const votePrice = Number(state.settings.votePrice) || 100;
  if (!selectedAmount) selectedAmount = selectedVotes * votePrice;
  $("#summaryVotes").textContent = formatNumber(selectedVotes || 0);
  $("#summaryAmount").textContent = formatCurrency(selectedAmount || 0);
  $("#summaryGateway").textContent = state.settings.gateway;
}

function applyCustomVotes() {
  const customVotes = Number($("#customVotes").value);
  if (!Number.isInteger(customVotes) || customVotes < 1) {
    return showToast("Enter a valid number of votes.", "error");
  }
  selectedPackage = null;
  selectedVotes = customVotes;
  selectedAmount = customVotes * Number(state.settings.votePrice || 100);
  renderModalPackages();
  updateSummary();
}

function reference() {
  const random = Math.random().toString(36).slice(2, 8).toUpperCase();
  const stamp = Date.now().toString().slice(-7);
  return `TVE-${stamp}-${random}`;
}

function showProcessing(title, text) {
  $("#processingTitle").textContent = title;
  $("#processingText").textContent = text;
  $("#processingModal").classList.add("active");
}

function hideProcessing() {
  $("#processingModal").classList.remove("active");
}

async function processDemoPayment(event) {
  event.preventDefault();
  const contestant = getContestant(selectedContestantId);
  if (!contestant) return showToast("Please select a contestant first.", "error");

  const voter = $("#buyerName").value.trim();
  const email = $("#buyerEmail").value.trim();
  const phone = $("#buyerPhone").value.trim();
  const accepted = $("#termsCheckbox").checked;

  if (!voter) return showToast("Enter your name before payment.", "error");
  if (!email && !phone) return showToast("Enter email or phone for the receipt.", "error");
  if (!selectedVotes || selectedVotes < 1) return showToast("Choose a vote package.", "error");
  if (!accepted) return showToast("Please accept the payment verification note.", "error");

  closeVoteModal();
  showProcessing("Initializing secure checkout...", "Creating backend payment reference.");

  const paymentPayload = {
    contest_id: "campus-icons-2026",
    contestant_id: contestant.id,
    package_id: selectedPackage ? selectedPackage.id : null,
    votes: selectedVotes,
    voter_name: voter,
    voter_email: email || null,
    voter_phone: phone || null,
  };

  try {
    const response = await fetch(`${API_BASE}/api/payments/initialize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(paymentPayload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.error || "Payment initialization failed");
    }

    showProcessing(
      result.dev_mode ? "Local dev checkout ready" : "Redirecting to Paystack...",
      result.dev_mode ? "No Paystack key detected, using backend simulation." : "Paystack will verify and return after payment."
    );

    setTimeout(() => {
      window.location.href = result.authorization_url;
    }, 650);
  } catch (error) {
    hideProcessing();
    console.error(error);
    showToast(`Backend payment failed: ${error.message}`, "error");
  }
}

async function addContestant() {
  if (!adminSession?.token) return showToast("Admin login required.", "error");
  const name = $("#newContestantName").value.trim();
  const code = $("#newContestantCode").value.trim();
  const category = $("#newContestantCategory").value.trim() || "General";
  const region = $("#newContestantRegion").value.trim() || "Client campaign";
  const bio = $("#newContestantBio")?.value.trim() || "New contestant added from the admin dashboard.";
  if (!name) return showToast("Enter a contestant name.", "error");

  try {
    const response = await fetch(`${API_BASE}/api/admin/contestants`, {
      method: "POST",
      headers: adminHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ name, code, category, region, bio }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Could not add contestant");
    if (result.contest) {
      state = { ...state, ...result.contest };
      saveState();
    }
    ["#newContestantName", "#newContestantCode", "#newContestantCategory", "#newContestantRegion", "#newContestantBio"].forEach((id) => { if ($(id)) $(id).value = ""; });
    renderAll();
    showToast(`${name} added to the campaign.`, "success");
  } catch (error) {
    showToast(`Could not add contestant: ${error.message}`, "error");
  }
}

async function deleteContestant(contestantId) {
  if (!adminSession?.token) return showToast("Admin login required.", "error");
  if (state.contestants.length <= 1) return showToast("At least one contestant is required.", "error");
  const contestant = getContestant(contestantId);
  if (!confirm(`Remove ${contestant?.name || "this contestant"}?`)) return;
  try {
    const response = await fetch(`${API_BASE}/api/admin/contestants/${encodeURIComponent(contestantId)}`, {
      method: "DELETE",
      headers: adminHeaders(),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Could not remove contestant");
    if (result.contest) {
      state = { ...state, ...result.contest };
      saveState();
    }
    renderAll();
    showToast(`${contestant?.name || "Contestant"} removed.`, "success");
  } catch (error) {
    showToast(`Could not remove contestant: ${error.message}`, "error");
  }
}

async function uploadContestantPhoto(contestantId, file) {
  if (!file) return;
  if (!adminSession?.token) return showToast("Admin login required.", "error");
  if (!file.type.startsWith("image/")) return showToast("Please choose an image file.", "error");
  if (file.size > 4 * 1024 * 1024) return showToast("Photo must be under 4MB.", "error");

  try {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    const response = await fetch(`${API_BASE}/api/admin/contestants/${encodeURIComponent(contestantId)}/photo`, {
      method: "POST",
      headers: adminHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ filename: file.name, content_type: file.type, data: dataUrl }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Photo upload failed");
    if (result.contest) {
      state = { ...state, ...result.contest };
      saveState();
    }
    renderAll();
    showToast("Contestant photo uploaded.", "success");
  } catch (error) {
    showToast(`Photo upload failed: ${error.message}`, "error");
  }
}

async function saveSettings() {
  if (!adminSession?.token) return showToast("Admin login required.", "error");
  const votePrice = Number($("#settingVotePrice").value);
  if (!votePrice || votePrice < 50) return showToast("Vote price should be at least ₦50.", "error");
  const payload = {
    title: $("#settingTitle").value.trim() || DEFAULT_STATE.settings.title,
    votePrice,
    gateway: $("#settingGateway").value,
    status: $("#settingStatus").value,
  };
  try {
    const response = await fetch(`${API_BASE}/api/admin/settings`, {
      method: "POST",
      headers: adminHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Could not save settings");
    if (result.contest) {
      state = { ...state, ...result.contest };
      saveState();
    } else {
      state.settings = { ...state.settings, ...payload };
      saveState();
    }
    if (!selectedPackage) selectedAmount = selectedVotes * votePrice;
    renderAll();
    showToast("Campaign settings saved.", "success");
  } catch (error) {
    showToast(`Could not save settings: ${error.message}`, "error");
  }
}

function showToast(message, type = "success") {
  const toast = $("#toast");
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    toast.className = "toast";
  }, 4200);
}

async function fetchRemoteState({ notify = false } = {}) {
  try {
    const response = await fetch(`${API_BASE}/api/contest`, { headers: { "Accept": "application/json" } });
    if (!response.ok) throw new Error("Backend not ready");
    const payload = await response.json();
    backendConnected = true;
    state.settings = { ...state.settings, ...(payload.settings || {}) };
    state.contestants = payload.contestants?.length ? payload.contestants : state.contestants;
    state.payments = payload.payments || state.payments;
    saveState();
    renderAll();
    if (notify) showToast("Connected to backend database.", "success");
  } catch (error) {
    backendConnected = false;
    if (notify) showToast("Backend is offline. Start backend/server.py to use real payments.", "error");
  }
}

function resetDemo() {
  localStorage.removeItem(STORAGE_KEY);
  state = cloneDefaultState();
  selectedPackage = PACKAGES[1];
  selectedVotes = selectedPackage.votes;
  selectedAmount = selectedPackage.amount;
  renderAll();
  showToast("Demo data reset.", "success");
}

function wireEvents() {
  $("#searchInput").addEventListener("input", renderContestants);
  $("#categoryFilter").addEventListener("change", renderContestants);
  $("#sortFilter").addEventListener("change", renderContestants);
  $("#closeVoteModal").addEventListener("click", closeVoteModal);
  $("#voteModal").addEventListener("click", (event) => {
    if (event.target.id === "voteModal") closeVoteModal();
  });
  $("#applyCustomVotes").addEventListener("click", applyCustomVotes);
  $("#customVotes").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      applyCustomVotes();
    }
  });
  $("#voteForm").addEventListener("submit", processDemoPayment);
  $("#addContestantBtn").addEventListener("click", addContestant);
  $("#saveSettingsBtn").addEventListener("click", saveSettings);
  $("#demoResetBtn").addEventListener("click", resetDemo);

  $$(".admin-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".admin-tab").forEach((item) => item.classList.remove("active"));
      $$(".admin-pane").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      $(`#admin-${tab.dataset.tab}`).classList.add("active");
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeVoteModal();
  });
}

wireEvents();
renderAll();
fetchRemoteState();
