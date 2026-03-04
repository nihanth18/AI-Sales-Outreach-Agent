// ============================================================
// AI Sales Outreach Agent - Dashboard Application
// ============================================================

const API_BASE = "/api";
const REFRESH_INTERVAL = 5000; // 5 seconds

let allProspects = [];
let allCampaigns = [];

// ============================================================
// Tab Navigation
// ============================================================

document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        const tabName = btn.dataset.tab;
        switchTab(tabName);
    });
});

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll(".tab-content").forEach(tab => {
        tab.classList.remove("active");
    });

    // Deactivate all buttons
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("active");
    });

    // Show selected tab
    document.getElementById(tabName).classList.add("active");
    document.querySelector(`[data-tab="${tabName}"]`).classList.add("active");

    // Load tab specific data
    if (tabName === "dashboard") loadStatus();
    if (tabName === "prospects") loadProspects();
    if (tabName === "campaigns") loadCampaigns();
    if (tabName === "analytics") loadAnalytics();
}

// ============================================================
// Dashboard - System Status
// ============================================================

async function loadStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        
        const statusDisplay = document.getElementById("status-display");
        statusDisplay.innerHTML = `
            <div class="status-item">
                <div class="status-label">System Status</div>
                <div class="status-value status-ok">✓ Running</div>
            </div>
            <div class="status-item">
                <div class="status-label">Environment</div>
                <div class="status-value">${data.environment}</div>
            </div>
            <div class="status-item">
                <div class="status-label">OpenAI API</div>
                <div class="status-value ${data.services.openai === 'configured' ? 'status-ok' : 'status-error'}">
                    ${data.services.openai === 'configured' ? '✓ Configured' : '✗ Missing'}
                </div>
            </div>
            <div class="status-item">
                <div class="status-label">Tavily API</div>
                <div class="status-value ${data.services.tavily === 'configured' ? 'status-ok' : 'status-error'}">
                    ${data.services.tavily === 'configured' ? '✓ Configured' : '✗ Missing'}
                </div>
            </div>
            <div class="status-item">
                <div class="status-label">Gmail Integration</div>
                <div class="status-value ${data.services.gmail === 'configured' ? 'status-ok' : 'status-error'}">
                    ${data.services.gmail === 'configured' ? '✓ Configured' : '✗ Missing'}
                </div>
            </div>
            <div class="status-item">
                <div class="status-label">Airtable CRM</div>
                <div class="status-value ${data.services.airtable === 'configured' ? 'status-ok' : 'status-error'}">
                    ${data.services.airtable === 'configured' ? '✓ Configured' : '✗ Missing'}
                </div>
            </div>
        `;
    } catch (error) {
        console.error("Failed to load status:", error);
        document.getElementById("status-display").innerHTML = `<div class="status-item status-error">Error loading status</div>`;
    }
}

// ============================================================
// Prospects Management
// ============================================================

async function loadProspects() {
    try {
        const response = await fetch(`${API_BASE}/prospects`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        allProspects = await response.json();
        renderProspectsList();
        updateProspectSelect();
    } catch (error) {
        console.error("Failed to load prospects:", error);
        document.getElementById("prospects-table").innerHTML = `<div class="status-error">Error loading prospects</div>`;
    }
}

function renderProspectsList() {
    const container = document.getElementById("prospects-table");
    
    if (allProspects.length === 0) {
        container.innerHTML = '<p style="text-align: center; opacity: 0.7;">No prospects yet. Add one to get started!</p>';
        return;
    }

    let html = '<div class="table-container"><table>';
    html += '<thead><tr><th>Name</th><th>Email</th><th>Company</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
    
    allProspects.forEach(prospect => {
        html += `
            <tr>
                <td><strong>${prospect.name}</strong></td>
                <td><a href="mailto:${prospect.email}" style="color: #64d4ff;">${prospect.email}</a></td>
                <td>${prospect.company}</td>
                <td><span style="background: rgba(100, 200, 255, 0.2); padding: 0.3rem 0.6rem; border-radius: 4px;">${prospect.status}</span></td>
                <td>
                    <button class="btn-secondary" onclick="deleteProspect('${prospect.id}')">Delete</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function updateProspectSelect() {
    const select = document.getElementById("campaign-prospect");
    select.innerHTML = '<option value="">Select Prospect...</option>';
    
    allProspects.forEach(prospect => {
        const option = document.createElement("option");
        option.value = prospect.id;
        option.textContent = `${prospect.name} (${prospect.company})`;
        select.appendChild(option);
    });
}

document.getElementById("prospect-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const prospectData = {
        name: document.getElementById("prospect-name").value,
        email: document.getElementById("prospect-email").value,
        company: document.getElementById("prospect-company").value,
        title: document.getElementById("prospect-title").value || "",
        linkedin_url: "",
        website: "",
        industry: "",
        company_size: "",
        tags: []
    };

    try {
        const response = await fetch(`${API_BASE}/prospects`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(prospectData)
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        alert("✓ Prospect added successfully!");
        document.getElementById("prospect-form").reset();
        await loadProspects();
    } catch (error) {
        alert("✗ Error adding prospect: " + error.message);
        console.error(error);
    }
});

async function deleteProspect(prospectId) {
    if (!confirm("Are you sure you want to delete this prospect?")) return;
    
    try {
        const response = await fetch(`${API_BASE}/prospects/${prospectId}`, {
            method: "DELETE"
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        alert("✓ Prospect deleted!");
        await loadProspects();
    } catch (error) {
        alert("✗ Error deleting prospect: " + error.message);
    }
}

// ============================================================
// Campaigns Management
// ============================================================

async function loadCampaigns() {
    try {
        const response = await fetch(`${API_BASE}/campaigns`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        allCampaigns = await response.json();
        renderCampaignsList();
        await loadProspects(); // Refresh prospects for campaign creation
    } catch (error) {
        console.error("Failed to load campaigns:", error);
        document.getElementById("campaigns-table").innerHTML = `<div class="status-error">Error loading campaigns</div>`;
    }
}

function renderCampaignsList() {
    const container = document.getElementById("campaigns-table");
    
    if (allCampaigns.length === 0) {
        container.innerHTML = '<p style="text-align: center; opacity: 0.7;">No campaigns yet. Create one to get started!</p>';
        return;
    }

    let html = '<div class="table-container"><table>';
    html += '<thead><tr><th>Name</th><th>Status</th><th>Sent</th><th>Replies</th><th>Actions</th></tr></thead><tbody>';
    
    allCampaigns.forEach(campaign => {
        const responseRate = campaign.emails_sent > 0 ? ((campaign.replies_received / campaign.emails_sent) * 100).toFixed(1) : 0;
        html += `
            <tr>
                <td><strong>${campaign.name}</strong></td>
                <td><span style="background: rgba(100, 200, 255, 0.2); padding: 0.3rem 0.6rem; border-radius: 4px;">${campaign.status}</span></td>
                <td>${campaign.emails_sent}/${campaign.total_prospects}</td>
                <td>${campaign.replies_received} (${responseRate}%)</td>
                <td>
                    ${campaign.status === 'draft' ? `<button class="btn-secondary" onclick="launchCampaign('${campaign.id}')">Launch</button>` : '<span style="opacity: 0.6;">Active</span>'}
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

document.getElementById("campaign-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const prospectId = document.getElementById("campaign-prospect").value;
    if (!prospectId) {
        alert("Please select a prospect");
        return;
    }

    const campaignData = {
        name: document.getElementById("campaign-name").value,
        description: document.getElementById("campaign-context").value,
        tone: "professional",
        prospect_ids: [prospectId]
    };

    try {
        const response = await fetch(`${API_BASE}/campaigns`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(campaignData)
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        alert("✓ Campaign created! Click 'Launch' to start sending emails.");
        document.getElementById("campaign-form").reset();
        await loadCampaigns();
    } catch (error) {
        alert("✗ Error creating campaign: " + error.message);
        console.error(error);
    }
});

async function launchCampaign(campaignId) {
    if (!confirm("Launch this campaign? This will start sending emails.")) return;
    
    try {
        const response = await fetch(`${API_BASE}/campaigns/${campaignId}/launch`, {
            method: "POST"
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        alert("✓ Campaign launched! Emails are being sent...");
        await loadCampaigns();
    } catch (error) {
        alert("✗ Error launching campaign: " + error.message);
    }
}

// ============================================================
// Analytics
// ============================================================

async function loadAnalytics() {
    try {
        const [overviewRes, performanceRes] = await Promise.all([
            fetch(`${API_BASE}/analytics/overview`),
            fetch(`${API_BASE}/analytics/campaign-performance`)
        ]);

        if (!overviewRes.ok || !performanceRes.ok) throw new Error("Failed to fetch analytics");

        const overview = await overviewRes.json();
        const performance = await performanceRes.json();

        // Update metric cards
        document.getElementById("total-prospects").textContent = overview.total_prospects || 0;
        document.getElementById("campaigns-sent").textContent = overview.emails_sent || 0;
        document.getElementById("open-rate").textContent = overview.open_rate ? overview.open_rate.toFixed(1) + "%" : "-";
        document.getElementById("reply-rate").textContent = overview.reply_rate ? overview.reply_rate.toFixed(1) + "%" : "-";

        // Render performance details
        renderAnalyticsDetails(performance);
    } catch (error) {
        console.error("Failed to load analytics:", error);
        document.getElementById("analytics-details").innerHTML = `<div class="status-error">Error loading analytics</div>`;
    }
}

function renderAnalyticsDetails(performance) {
    const container = document.getElementById("analytics-details");
    
    if (performance.length === 0) {
        container.innerHTML = '<p style="text-align: center; opacity: 0.7;">No campaign data yet.</p>';
        return;
    }

    let html = '<div class="table-container"><table>';
    html += '<thead><tr><th>Campaign</th><th>Status</th><th>Sent</th><th>Replies</th><th>Response Rate</th></tr></thead><tbody>';
    
    performance.forEach(camp => {
        html += `
            <tr>
                <td><strong>${camp.name}</strong></td>
                <td>${camp.status}</td>
                <td>${camp.sent}/${camp.total}</td>
                <td>${camp.replies}</td>
                <td>${camp.response_rate}%</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// ============================================================
// Auto-refresh and Initialization
// ============================================================

// Load status on page load
loadStatus();

// Auto-refresh based on active tab
setInterval(() => {
    const activeTab = document.querySelector(".tab-content.active").id;
    if (activeTab === "dashboard") loadStatus();
    if (activeTab === "prospects") loadProspects();
    if (activeTab === "campaigns") loadCampaigns();
    if (activeTab === "analytics") loadAnalytics();
}, REFRESH_INTERVAL);

console.log("✓ AI Sales Outreach Agent Dashboard loaded");
