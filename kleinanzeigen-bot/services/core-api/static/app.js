/* ═══════════════════════════════════════════════════════
   Kleinanzeigen Bot — Review UI Application Logic
   ═══════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;

// State
let listings = [];
let selectedListingId = null;
let selectedDetail = null;

// ── Initialization ──────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadListings();

    // Filter change
    document.getElementById('filter-status').addEventListener('change', loadListings);

    // Action buttons
    document.getElementById('btn-approve').addEventListener('click', () => approveCurrentListing());
    document.getElementById('btn-skip').addEventListener('click', () => skipToNext());
    document.getElementById('btn-reject').addEventListener('click', () => rejectCurrentListing());
    document.getElementById('btn-bulk-approve').addEventListener('click', bulkApproveHigh);
    document.getElementById('btn-start-posting').addEventListener('click', startPosting);

    // Title character counter
    document.getElementById('edit-title').addEventListener('input', (e) => {
        document.getElementById('title-char-count').textContent = `${e.target.value.length}/120`;
    });

    // Auto-save on field blur
    ['edit-title', 'edit-description', 'edit-price', 'edit-condition', 'edit-zip', 'edit-strategy'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', autoSave);
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeypress);
});


// ── API Calls ───────────────────────────────────────────

async function apiGet(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
    return res.json();
}

async function apiPatch(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`PATCH ${path}: ${res.status}`);
    return res.json();
}

async function apiPost(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
    return res.json();
}


// ── Load Listings ───────────────────────────────────────

async function loadListings() {
    const status = document.getElementById('filter-status').value;
    const query = status ? `?status=${status}&limit=200` : '?limit=200';

    try {
        const data = await apiGet(`/api/listings${query}`);
        listings = data.items;
        renderCardList();
        updateHeaderStats(data.total);

        // If we had a selected listing, try to keep it
        if (selectedListingId) {
            const still = listings.find(l => l.id === selectedListingId);
            if (still) {
                renderCard(still, true);
            } else {
                clearDetail();
            }
        }
    } catch (e) {
        showToast('Failed to load listings: ' + e.message, 'error');
    }
}


// ── Render Card List ────────────────────────────────────

function renderCardList() {
    const container = document.getElementById('cards-container');
    container.innerHTML = '';

    listings.forEach(listing => {
        const card = document.createElement('div');
        card.className = `card-item${listing.id === selectedListingId ? ' active' : ''}`;
        card.dataset.id = listing.id;

        const price = listing.final_price || listing.recommended_price;
        const conf = listing.price_confidence || 'none';
        const thumbSrc = listing.thumbnail_url || '';

        card.innerHTML = `
            <img class="card-thumb" src="${thumbSrc}" alt=""
                 onerror="this.style.display='none'">
            <div class="card-info">
                <div class="card-title">${escapeHtml(listing.title || listing.item_name || 'Untitled')}</div>
                <div class="card-meta">
                    <span class="card-price">${price ? `€${Number(price).toFixed(0)}` : '—'}</span>
                    <span class="card-confidence ${conf}"></span>
                    <span>${listing.image_count} 📷</span>
                </div>
            </div>
        `;

        card.addEventListener('click', () => selectListing(listing.id));
        container.appendChild(card);
    });
}

function updateHeaderStats(total) {
    document.getElementById('header-stats').textContent = `${total} item${total !== 1 ? 's' : ''}`;
}


// ── Select & Load Detail ────────────────────────────────

async function selectListing(id) {
    selectedListingId = id;

    // Highlight active card
    document.querySelectorAll('.card-item').forEach(c => {
        c.classList.toggle('active', c.dataset.id === id);
    });

    try {
        selectedDetail = await apiGet(`/api/listings/${id}`);
        renderDetail(selectedDetail);
    } catch (e) {
        showToast('Failed to load listing detail', 'error');
    }
}

function clearDetail() {
    selectedListingId = null;
    selectedDetail = null;
    document.getElementById('detail-empty').style.display = 'flex';
    document.getElementById('detail-content').style.display = 'none';
}


// ── Render Detail Panel ─────────────────────────────────

function renderDetail(listing) {
    document.getElementById('detail-empty').style.display = 'none';
    document.getElementById('detail-content').style.display = 'block';

    // Images
    const images = listing.images || [];
    const mainImg = document.getElementById('gallery-main-image');
    if (images.length > 0) {
        mainImg.src = images[0].file_url;
        mainImg.style.display = 'block';
    } else {
        mainImg.style.display = 'none';
    }

    const thumbContainer = document.getElementById('gallery-thumbs');
    thumbContainer.innerHTML = '';
    images.forEach((img, i) => {
        const thumb = document.createElement('img');
        thumb.src = img.thumb_url || img.file_url;
        thumb.alt = `Photo ${i + 1}`;
        if (i === 0) thumb.classList.add('active');
        thumb.addEventListener('click', () => {
            mainImg.src = img.file_url;
            thumbContainer.querySelectorAll('img').forEach(t => t.classList.remove('active'));
            thumb.classList.add('active');
        });
        thumbContainer.appendChild(thumb);
    });

    // Form fields
    document.getElementById('edit-title').value = listing.title || '';
    document.getElementById('title-char-count').textContent =
        `${(listing.title || '').length}/120`;
    document.getElementById('edit-description').value = listing.description || '';
    document.getElementById('edit-price').value =
        listing.final_price || listing.recommended_price || '';
    document.getElementById('edit-condition').value = listing.item_condition || 'good';
    document.getElementById('edit-zip').value = listing.ka_location_zip || '';
    document.getElementById('edit-strategy').value = listing.price_strategy || 'competitive';

    // Confidence badge
    const conf = listing.price_confidence || 'none';
    const badge = document.getElementById('price-confidence-badge');
    badge.className = `confidence-badge ${conf}`;
    const confLabels = { high: 'HIGH', medium: 'MEDIUM', low: 'LOW', none: 'NO DATA' };
    badge.querySelector('.badge-text').textContent =
        `${confLabels[conf] || conf.toUpperCase()} (${listing.comp_count || 0} comps)`;

    // Pricing info
    const pricingInfo = document.getElementById('pricing-info');
    if (listing.median_price) {
        pricingInfo.innerHTML = `
            Range: €${Number(listing.price_range_low || 0).toFixed(0)} – 
            €${Number(listing.price_range_high || 0).toFixed(0)} 
            (median €${Number(listing.median_price).toFixed(0)})<br>
            <em>${escapeHtml(listing.price_reasoning || '')}</em>
        `;
        pricingInfo.style.display = 'block';
    } else {
        pricingInfo.style.display = 'none';
    }

    // Comparables
    const compSection = document.getElementById('comparables-section');
    const compList = document.getElementById('comparables-list');
    const comparables = (listing.pricing_candidates || []).filter(c => c.is_comparable);
    if (comparables.length > 0) {
        compSection.style.display = 'block';
        compList.innerHTML = comparables.map(c => `
            <div class="comp-item">
                <div class="comp-title">
                    ${c.source_url ? `<a href="${c.source_url}" target="_blank">${escapeHtml(c.source_title || '—')}</a>` : escapeHtml(c.source_title || '—')}
                </div>
                <span class="comp-price">${c.source_price ? `€${Number(c.source_price).toFixed(0)}` : '—'}</span>
                <span class="comp-score">${c.similarity_score ? `${(c.similarity_score * 100).toFixed(0)}%` : ''}</span>
            </div>
        `).join('');
    } else {
        compSection.style.display = 'none';
    }
}


// ── Actions ─────────────────────────────────────────────

async function autoSave() {
    if (!selectedListingId) return;

    const body = {
        title: document.getElementById('edit-title').value,
        description: document.getElementById('edit-description').value,
        final_price: parseFloat(document.getElementById('edit-price').value) || null,
        item_condition: document.getElementById('edit-condition').value,
        ka_location_zip: document.getElementById('edit-zip').value,
    };

    try {
        await apiPatch(`/api/listings/${selectedListingId}`, body);
    } catch (e) {
        console.error('Auto-save failed:', e);
    }
}

async function approveCurrentListing() {
    if (!selectedListingId) return;
    await autoSave();

    try {
        await apiPatch(`/api/listings/${selectedListingId}`, { status: 'approved' });
        showToast('✅ Listing approved', 'success');
        await loadListings();
        selectNextListing();
    } catch (e) {
        showToast('Failed to approve: ' + e.message, 'error');
    }
}

async function rejectCurrentListing() {
    if (!selectedListingId) return;

    try {
        await apiPatch(`/api/listings/${selectedListingId}`, { status: 'rejected' });
        showToast('🗑️ Listing rejected', 'info');
        await loadListings();
        selectNextListing();
    } catch (e) {
        showToast('Failed to reject: ' + e.message, 'error');
    }
}

function skipToNext() {
    selectNextListing();
}

function selectNextListing() {
    if (listings.length === 0) {
        clearDetail();
        return;
    }

    const currentIdx = listings.findIndex(l => l.id === selectedListingId);
    const nextIdx = (currentIdx + 1) % listings.length;
    if (listings[nextIdx]) {
        selectListing(listings[nextIdx].id);
    } else {
        clearDetail();
    }
}

async function bulkApproveHigh() {
    try {
        const result = await apiPost('/api/listings/bulk-approve', {
            filter: { status: 'draft_ready', min_price_confidence: 'high' },
        });
        showToast(`✅ Approved ${result.approved_count} high-confidence listings`, 'success');
        await loadListings();
    } catch (e) {
        showToast('Bulk approve failed: ' + e.message, 'error');
    }
}

async function startPosting() {
    try {
        const result = await apiPost('/api/posting/start', {});
        showToast(`🚀 ${result.queued_count} listings queued for posting`, 'success');
        await loadListings();
    } catch (e) {
        showToast('Failed to start posting: ' + e.message, 'error');
    }
}


// ── Keyboard Shortcuts ──────────────────────────────────

function handleKeypress(e) {
    // Don't trigger when typing in an input
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

    switch (e.key.toLowerCase()) {
        case 'a': approveCurrentListing(); break;
        case 's': skipToNext(); break;
        case 'r': rejectCurrentListing(); break;
        case 'arrowleft': selectPrevListing(); break;
        case 'arrowright': selectNextListing(); break;
    }
}

function selectPrevListing() {
    if (listings.length === 0) return;
    const currentIdx = listings.findIndex(l => l.id === selectedListingId);
    const prevIdx = currentIdx <= 0 ? listings.length - 1 : currentIdx - 1;
    selectListing(listings[prevIdx].id);
}


// ── Utilities ───────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
