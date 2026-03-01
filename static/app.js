/**
 * AI Sales Outreach Agent — Dashboard Application
 * Handles API calls, dynamic rendering, and real-time updates.
 */

const API_BASE = '';

// ────────────── State ──────────────

let currentPage = 'dashboard';
let prospects = [];
let campaigns = [];
let systemStatus = {};

// ────────────── Navigation ──────────────

function navigateTo(page) {
    currentPage = page;

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });

    // Show/hide pages
    document.querySelectorAll('.page').forEach(p => {
        p.classList.toggle('active', p.id === `page-${page}`);
    });

    // Load page data
    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'prospects': loadProspects(); break;
        case 'campaigns': loadCampaigns(); break;
        case 'pipeline': loadPipelineStatus(); break;
    }
}

// ────────────── API Helpers ──────────────

async function api(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

// ────────────── Dashboard ──────────────

async function loadDashboard() {
    try {
        const analytics = await api('/api/analytics/overview');

        document.getElementById('statProspects').textContent = analytics.total_prospects;
        document.getElementById('statEmails').textContent = analytics.emails_sent;
        document.getElementById('statReplies').textContent = analytics.replies_received;
        document.getElementById('statRate').textContent = `${analytics.response_rate}%`;

        // Animate stat values
        document.querySelectorAll('.stat-value').forEach(el => {
            el.style.animation = 'none';
            el.offsetHeight; // trigger reflow
            el.style.animation = 'fadeIn 0.5s ease';
        });

        // Load recent emails
        loadRecentEmails();

        // Load activity feed
        loadActivityFeed(analytics.recent_activity);

    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

async function loadRecentEmails() {
    try {
        const emails = await api('/api/analytics/recent-emails');
        const container = document.getElementById('recentEmails');

        if (emails.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-text">No emails sent yet</div>
                    <div class="empty-state-sub">Launch a campaign or use Quick Outreach</div>
                </div>`;
            return;
        }

        container.innerHTML = emails.slice(0, 5).map(email => `
            <div class="activity-item">
                <div class="activity-dot email"></div>
                <div>
                    <div class="activity-text">
                        <strong>${escapeHtml(email.prospect_name)}</strong>: "${escapeHtml(email.subject)}"
                        ${email.replied ? `<span class="badge badge-replied" style="margin-left:8px">Replied</span>` : ''}
                        ${email.sentiment ? `<span class="badge badge-${email.sentiment === 'positive' ? 'converted' : email.sentiment === 'negative' ? 'not_interested' : 'drafted'}" style="margin-left:4px">${email.sentiment}</span>` : ''}
                    </div>
                    <div class="activity-time">${email.sent_at ? formatTime(email.sent_at) : 'Draft'}</div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to load recent emails:', error);
    }
}

function loadActivityFeed(activities) {
    const feed = document.getElementById('activityFeed');

    if (!activities || activities.length === 0) {
        feed.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-text">No activity yet</div>
                <div class="empty-state-sub">Start by adding some prospects</div>
            </div>`;
        return;
    }

    feed.innerHTML = activities.slice(-10).reverse().map(a => {
        const dotClass = a.type.includes('prospect') ? 'prospect' :
            a.type.includes('campaign') ? 'campaign' :
                a.type.includes('email') || a.type.includes('status') ? 'status' : 'email';

        return `
            <li class="activity-item">
                <div class="activity-dot ${dotClass}"></div>
                <div>
                    <div class="activity-text">${escapeHtml(a.description)}</div>
                    <div class="activity-time">${formatTime(a.timestamp)}</div>
                </div>
            </li>`;
    }).join('');
}

async function refreshActivity() {
    try {
        const data = await api('/api/analytics/activity-feed');
        loadActivityFeed(data);
        showToast('Activity feed refreshed', 'info');
    } catch (error) {
        showToast('Failed to refresh activity', 'error');
    }
}

// ────────────── Prospects ──────────────

async function loadProspects() {
    try {
        prospects = await api('/api/prospects');
        renderProspectsTable();
    } catch (error) {
        console.error('Failed to load prospects:', error);
    }
}

function renderProspectsTable() {
    const tbody = document.getElementById('prospectsTable');

    if (prospects.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="6">
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <div class="empty-state-text">No prospects yet</div>
                    <div class="empty-state-sub">Click "Add Prospect" to get started</div>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = prospects.map(p => `
        <tr>
            <td><strong>${escapeHtml(p.name)}</strong></td>
            <td>${escapeHtml(p.company)}</td>
            <td style="color:var(--text-muted)">${escapeHtml(p.email)}</td>
            <td style="color:var(--text-secondary)">${escapeHtml(p.title || '—')}</td>
            <td><span class="badge badge-${p.status}">${formatStatus(p.status)}</span></td>
            <td>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-sm btn-secondary" onclick="runOutreachForProspect('${p.id}')" title="Run outreach pipeline">🚀</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteProspect('${p.id}')" title="Delete">🗑️</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function openAddProspectModal() {
    document.getElementById('addProspectModal').classList.add('active');
}

async function addProspect() {
    const name = document.getElementById('mpName').value.trim();
    const email = document.getElementById('mpEmail').value.trim();
    const company = document.getElementById('mpCompany').value.trim();
    const title = document.getElementById('mpTitle').value.trim();
    const industry = document.getElementById('mpIndustry').value.trim();
    const linkedin_url = document.getElementById('mpLinkedin').value.trim();

    if (!name || !email || !company) {
        showToast('Please fill in Name, Email, and Company', 'error');
        return;
    }

    try {
        await api('/api/prospects', {
            method: 'POST',
            body: JSON.stringify({ name, email, company, title, industry, linkedin_url }),
        });

        closeModal('addProspectModal');
        clearModalFields('mp');
        showToast(`Prospect "${name}" added!`, 'success');
        loadProspects();
        loadDashboard();
    } catch (error) {
        showToast(`Failed: ${error.message}`, 'error');
    }
}

async function deleteProspect(id) {
    if (!confirm('Delete this prospect?')) return;

    try {
        await api(`/api/prospects/${id}`, { method: 'DELETE' });
        showToast('Prospect deleted', 'info');
        loadProspects();
        loadDashboard();
    } catch (error) {
        showToast(`Failed: ${error.message}`, 'error');
    }
}

async function runOutreachForProspect(id) {
    const prospect = prospects.find(p => p.id === id);
    if (!prospect) return;

    showToast(`Starting outreach pipeline for ${prospect.name}...`, 'info');

    try {
        const result = await api(`/api/campaigns/quick-outreach?name=${encodeURIComponent(prospect.name)}&email=${encodeURIComponent(prospect.email)}&company=${encodeURIComponent(prospect.company)}&title=${encodeURIComponent(prospect.title || '')}&tone=professional&send=true`, {
            method: 'POST',
        });

        showToast(`Outreach complete for ${prospect.name}!`, 'success');
        loadProspects();
        loadDashboard();
    } catch (error) {
        showToast(`Pipeline failed: ${error.message}`, 'error');
    }
}

// ────────────── Campaigns ──────────────

async function loadCampaigns() {
    try {
        campaigns = await api('/api/campaigns');
        renderCampaigns();
    } catch (error) {
        console.error('Failed to load campaigns:', error);
    }
}

function renderCampaigns() {
    const container = document.getElementById('campaignsList');

    if (campaigns.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🚀</div>
                <div class="empty-state-text">No campaigns yet</div>
                <div class="empty-state-sub">Create a campaign to automate outreach to multiple prospects</div>
                <button class="btn btn-primary" onclick="openCreateCampaignModal()">Create Campaign</button>
            </div>`;
        return;
    }

    container.innerHTML = campaigns.map(c => `
        <div class="section-card" style="margin-bottom:16px">
            <div class="section-header">
                <div>
                    <span class="section-title">${escapeHtml(c.name)}</span>
                    <span class="badge badge-${c.status}" style="margin-left:12px">${formatStatus(c.status)}</span>
                </div>
                <div style="display:flex;gap:8px">
                    ${c.status === 'draft' ? `<button class="btn btn-sm btn-success" onclick="launchCampaign('${c.id}')">🚀 Launch</button>` : ''}
                    ${c.status === 'running' ? `<button class="btn btn-sm btn-secondary" onclick="pauseCampaign('${c.id}')">⏸ Pause</button>` : ''}
                </div>
            </div>
            ${c.description ? `<p style="color:var(--text-muted);font-size:13px;margin-bottom:16px">${escapeHtml(c.description)}</p>` : ''}
            <div class="stats-grid" style="margin-bottom:0">
                <div style="text-align:center;padding:12px">
                    <div style="font-size:24px;font-weight:700">${c.total_prospects}</div>
                    <div style="font-size:11px;color:var(--text-muted)">Prospects</div>
                </div>
                <div style="text-align:center;padding:12px">
                    <div style="font-size:24px;font-weight:700">${c.emails_sent}</div>
                    <div style="font-size:11px;color:var(--text-muted)">Sent</div>
                </div>
                <div style="text-align:center;padding:12px">
                    <div style="font-size:24px;font-weight:700">${c.replies_received}</div>
                    <div style="font-size:11px;color:var(--text-muted)">Replies</div>
                </div>
                <div style="text-align:center;padding:12px">
                    <div style="font-size:24px;font-weight:700;color:var(--success)">${c.positive_replies}</div>
                    <div style="font-size:11px;color:var(--text-muted)">Positive</div>
                </div>
            </div>
            ${c.emails_sent > 0 ? `
                <div class="progress-bar" style="margin-top:12px">
                    <div class="progress-fill" style="width:${Math.round(c.emails_sent / Math.max(c.total_prospects, 1) * 100)}%"></div>
                </div>
                <div style="text-align:right;font-size:11px;color:var(--text-muted);margin-top:4px">${Math.round(c.emails_sent / Math.max(c.total_prospects, 1) * 100)}% complete</div>
            ` : ''}
        </div>
    `).join('');
}

function openCreateCampaignModal() {
    // Populate prospect checkboxes
    const container = document.getElementById('campaignProspectCheckboxes');
    if (prospects.length === 0) {
        container.innerHTML = `<div class="empty-state" style="padding:16px"><div class="empty-state-sub">Add prospects first</div></div>`;
    } else {
        container.innerHTML = prospects.map(p => `
            <label style="display:flex;align-items:center;gap:8px;padding:6px 4px;cursor:pointer;font-size:13px;color:var(--text-secondary)">
                <input type="checkbox" value="${p.id}" class="campaign-prospect-cb">
                <strong>${escapeHtml(p.name)}</strong> — ${escapeHtml(p.company)}
            </label>
        `).join('');
    }

    document.getElementById('createCampaignModal').classList.add('active');
}

async function createCampaign() {
    const name = document.getElementById('mcName').value.trim();
    const description = document.getElementById('mcDesc').value.trim();
    const tone = document.getElementById('mcTone').value;
    const prospectIds = [...document.querySelectorAll('.campaign-prospect-cb:checked')].map(cb => cb.value);

    if (!name) {
        showToast('Please enter a campaign name', 'error');
        return;
    }

    try {
        await api('/api/campaigns', {
            method: 'POST',
            body: JSON.stringify({
                name,
                description,
                tone,
                prospect_ids: prospectIds,
            }),
        });

        closeModal('createCampaignModal');
        clearModalFields('mc');
        showToast(`Campaign "${name}" created!`, 'success');
        loadCampaigns();
    } catch (error) {
        showToast(`Failed: ${error.message}`, 'error');
    }
}

async function launchCampaign(id) {
    try {
        await api(`/api/campaigns/${id}/launch`, { method: 'POST' });
        showToast('Campaign launched! 🚀', 'success');
        loadCampaigns();
    } catch (error) {
        showToast(`Failed: ${error.message}`, 'error');
    }
}

async function pauseCampaign(id) {
    try {
        await api(`/api/campaigns/${id}/pause`, { method: 'POST' });
        showToast('Campaign paused', 'info');
        loadCampaigns();
    } catch (error) {
        showToast(`Failed: ${error.message}`, 'error');
    }
}

// ────────────── Quick Outreach ──────────────

async function runQuickOutreach(shouldSend) {
    const name = document.getElementById('qoName').value.trim();
    const email = document.getElementById('qoEmail').value.trim();
    const company = document.getElementById('qoCompany').value.trim();
    const title = document.getElementById('qoTitle').value.trim();
    const tone = document.getElementById('qoTone').value;

    if (!name || !email || !company) {
        showToast('Please fill in Name, Email, and Company', 'error');
        return;
    }

    // Show pipeline status
    const pipelineCard = document.getElementById('pipelineStatusCard');
    pipelineCard.style.display = 'block';
    animatePipeline('research');

    const btn = document.getElementById('qoRunBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running...';

    try {
        // Animate through steps
        setTimeout(() => animatePipeline('email'), 1500);
        setTimeout(() => animatePipeline('send'), 3000);
        setTimeout(() => animatePipeline('crm'), 4500);

        const result = await api(`/api/campaigns/quick-outreach?name=${encodeURIComponent(name)}&email=${encodeURIComponent(email)}&company=${encodeURIComponent(company)}&title=${encodeURIComponent(title)}&tone=${tone}&send=${shouldSend}`, {
            method: 'POST',
        });

        animatePipeline('track', true);

        // Show email preview
        if (result.email_subject) {
            showEmailPreview(result);
        }

        showToast(
            shouldSend ? `Email sent to ${name}! 🎉` : `Email drafted for ${name}`,
            'success'
        );

        // Refresh dashboard data
        loadDashboard();

    } catch (error) {
        animatePipeline('error');
        showToast(`Pipeline failed: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🚀 Research & Send';
    }
}

function animatePipeline(currentStep, allDone = false) {
    const steps = document.querySelectorAll('#pipelineSteps .pipeline-step');
    const stepOrder = ['research', 'email', 'send', 'crm', 'track'];
    const currentIdx = stepOrder.indexOf(currentStep);

    steps.forEach((step, i) => {
        const stepName = step.dataset.step;
        const stepIdx = stepOrder.indexOf(stepName);

        step.classList.remove('active', 'completed', 'error');

        if (currentStep === 'error') {
            step.classList.add('error');
        } else if (allDone || stepIdx < currentIdx) {
            step.classList.add('completed');
        } else if (stepIdx === currentIdx) {
            step.classList.add('active');
        }
    });
}

function showEmailPreview(result) {
    const container = document.getElementById('emailPreviewContainer');
    container.innerHTML = `
        <div class="email-preview">
            <div class="email-preview-header">
                <span style="font-size:20px">📧</span>
                <div>
                    <div class="email-preview-subject">${escapeHtml(result.email_subject || 'No subject')}</div>
                    <div style="font-size:12px;color:var(--text-muted)">Status: ${result.status || 'unknown'}</div>
                </div>
            </div>
            <div class="email-preview-body">Email generated and ${result.status === 'completed' ? 'sent' : 'drafted'} successfully! 
Check the Recent Emails section on the Dashboard for full details.</div>
        </div>
    `;
}

// ────────────── Pipeline Status ──────────────

async function loadPipelineStatus() {
    try {
        systemStatus = await api('/api/status');

        const container = document.getElementById('serviceCards');
        const services = systemStatus.services || {};

        container.innerHTML = Object.entries(services).map(([name, status]) => {
            const isConfigured = status === 'configured';
            const icons = { openai: '🧠', tavily: '🔍', gmail: '📧', notion: '📋' };
            const labels = { openai: 'OpenAI (LLM)', tavily: 'Tavily (Search)', gmail: 'Gmail (Send)', notion: 'Notion (CRM)' };

            return `
                <div class="stat-card">
                    <div class="stat-icon ${isConfigured ? 'green' : 'purple'}" style="font-size:24px">${icons[name] || '⚙️'}</div>
                    <div class="stat-value" style="font-size:20px;margin-top:8px">${labels[name] || name}</div>
                    <div class="stat-label" style="margin-top:4px">
                        <span class="badge ${isConfigured ? 'badge-converted' : 'badge-drafted'}">${isConfigured ? '✅ Connected' : '⚠️ Mock Mode'}</span>
                    </div>
                </div>`;
        }).join('');

        // Update sidebar badge
        const mockBadge = document.getElementById('mockBadge');
        if (systemStatus.mock_mode) {
            mockBadge.style.display = 'inline';
        }

    } catch (error) {
        console.error('Failed to load status:', error);
    }
}

// ────────────── Modals & Utils ──────────────

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

function clearModalFields(prefix) {
    document.querySelectorAll(`[id^="${prefix}"]`).forEach(el => {
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.value = '';
        if (el.tagName === 'SELECT') el.selectedIndex = 0;
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, 4000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatStatus(status) {
    return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatTime(isoString) {
    if (!isoString) return '';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return date.toLocaleDateString();
    } catch {
        return isoString;
    }
}

// ────────────── Init ──────────────

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadPipelineStatus();

    // Auto-refresh dashboard every 30 seconds
    setInterval(() => {
        if (currentPage === 'dashboard') loadDashboard();
    }, 30000);

    // Load prospects in background for campaign modal
    api('/api/prospects').then(p => prospects = p).catch(() => { });
});

// Close modals on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.remove('active');
    });
});

// Keyboard shortcut: Escape to close modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
    }
});
