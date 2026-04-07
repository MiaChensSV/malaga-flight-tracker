// Dashboard logic for Malaga Flight Tracker

const SB_URL_KEY = 'mft_supabase_url';
const SB_KEY_KEY = 'mft_supabase_key';

let db = null;
let allPrices = [];
let allSettings = [];
let activeRoute = null;
let currentMonth = new Date();
let priceChart = null;

// --- Supabase client ---

function initClient() {
    const url = localStorage.getItem(SB_URL_KEY);
    const key = localStorage.getItem(SB_KEY_KEY);
    if (!url || !key) return false;
    db = supabase.createClient(url, key);
    return true;
}

// --- Data loading ---

async function loadData() {
    if (!initClient()) {
        document.getElementById('calendar-title').textContent = 'Configure Supabase in Settings';
        return;
    }

    try {
        const [settingsRes, pricesRes] = await Promise.all([
            db.from('settings').select('*').order('id'),
            db.from('prices').select('*').order('departure_date'),
        ]);

        if (settingsRes.error) throw settingsRes.error;
        if (pricesRes.error) throw pricesRes.error;

        allSettings = settingsRes.data;
        allPrices = pricesRes.data;

        if (!activeRoute && allSettings.length > 0) {
            activeRoute = allSettings[0].route_from;
        }

        renderRouteTabs();
        renderStatusBar();
        renderCalendar();
        loadPriceHistory();
    } catch (err) {
        console.error('Failed to load data:', err);
        document.getElementById('calendar-title').textContent = 'Error loading data';
    }
}

// --- Route tabs ---

function renderRouteTabs() {
    const container = document.getElementById('route-tabs');
    container.innerHTML = '';

    const routes = [...new Set(allSettings.map(s => s.route_from))];
    routes.forEach(route => {
        const tab = document.createElement('div');
        tab.className = 'route-tab' + (route === activeRoute ? ' active' : '');
        tab.textContent = `${route} → AGP`;
        tab.addEventListener('click', () => {
            activeRoute = route;
            renderRouteTabs();
            renderCalendar();
            renderStatusBar();
            loadPriceHistory();
        });
        container.appendChild(tab);
    });
}

// --- Status bar ---

function renderStatusBar() {
    const routePrices = allPrices.filter(p => p.route_from === activeRoute);
    const today = new Date().toISOString().slice(0, 10);

    if (routePrices.length === 0) {
        document.getElementById('cheapest-price').textContent = '--';
        document.getElementById('cheapest-route').textContent = activeRoute || '--';
        document.getElementById('last-checked').textContent = '--';
        return;
    }

    // Find cheapest upcoming flight
    const upcoming = routePrices.filter(p => p.departure_date >= today && p.price != null);
    upcoming.sort((a, b) => a.price - b.price);

    if (upcoming.length > 0) {
        const cheapest = upcoming[0];
        document.getElementById('cheapest-price').textContent = `${cheapest.price} ${cheapest.currency}`;
        document.getElementById('cheapest-route').textContent = `${cheapest.route_from} → ${cheapest.route_to}`;
    } else {
        document.getElementById('cheapest-price').textContent = '--';
        document.getElementById('cheapest-route').textContent = activeRoute || '--';
    }

    // Last checked
    const checked = routePrices.filter(p => p.checked_at).map(p => new Date(p.checked_at));
    if (checked.length > 0) {
        const latest = new Date(Math.max(...checked));
        document.getElementById('last-checked').textContent = formatRelativeTime(latest);
    }
}

function formatRelativeTime(date) {
    const diff = Date.now() - date.getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

// --- Calendar ---

function renderCalendar() {
    const grid = document.getElementById('calendar-grid');
    grid.innerHTML = '';

    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const title = currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    document.getElementById('calendar-title').textContent = title;

    // Day labels
    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    dayNames.forEach(name => {
        const el = document.createElement('div');
        el.className = 'day-label';
        el.textContent = name;
        grid.appendChild(el);
    });

    // First day of month (0 = Sunday)
    const firstDay = new Date(year, month, 1).getDay();
    const startOffset = firstDay === 0 ? 6 : firstDay - 1; // Monday-based
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Build a price map for this route/month
    const setting = allSettings.find(s => s.route_from === activeRoute);
    const threshold = setting ? setting.price_threshold : null;
    const priceMap = {};
    allPrices
        .filter(p => p.route_from === activeRoute)
        .forEach(p => { priceMap[p.departure_date] = p; });

    // Empty cells for offset
    for (let i = 0; i < startOffset; i++) {
        const el = document.createElement('div');
        el.className = 'day empty';
        grid.appendChild(el);
    }

    // Day cells
    for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
        const el = document.createElement('div');
        const flight = priceMap[dateStr];

        let className = 'day';
        let priceText = '';

        if (flight && flight.price != null) {
            if (threshold && flight.price < threshold) {
                className += ' available';
            } else {
                className += ' expensive';
            }
            priceText = `${flight.price}`;
        } else {
            className += ' no-data';
        }

        el.className = className;
        el.innerHTML = `
            <span class="date-num">${d}</span>
            ${priceText ? `<span class="price-tag">${priceText}</span>` : ''}
        `;

        if (flight) {
            el.addEventListener('click', () => showFlightDetail(flight));
        }

        grid.appendChild(el);
    }
}

// --- Flight detail popup ---

function showFlightDetail(flight) {
    const detail = document.getElementById('flight-detail');
    const overlay = document.getElementById('overlay');

    document.getElementById('detail-title').textContent = `${flight.route_from} → ${flight.route_to}`;
    document.getElementById('detail-body').innerHTML = `
        <div class="detail-row"><span>Date</span><span>${flight.departure_date}</span></div>
        <div class="detail-row"><span>Price</span><span>${flight.price} ${flight.currency}</span></div>
        <div class="detail-row"><span>Airline</span><span>${flight.airline || 'N/A'}</span></div>
        <div class="detail-row"><span>Checked</span><span>${flight.checked_at ? new Date(flight.checked_at).toLocaleString() : 'N/A'}</span></div>
        ${flight.booking_link ? `<a href="${flight.booking_link}" target="_blank" rel="noopener" class="book-link">Book Flight</a>` : ''}
    `;

    detail.style.display = 'block';
    overlay.style.display = 'block';
}

function hideFlightDetail() {
    document.getElementById('flight-detail').style.display = 'none';
    document.getElementById('overlay').style.display = 'none';
}

document.getElementById('close-detail').addEventListener('click', hideFlightDetail);
document.getElementById('overlay').addEventListener('click', hideFlightDetail);

// --- Month navigation ---

document.getElementById('prev-month').addEventListener('click', () => {
    currentMonth.setMonth(currentMonth.getMonth() - 1);
    renderCalendar();
});

document.getElementById('next-month').addEventListener('click', () => {
    currentMonth.setMonth(currentMonth.getMonth() + 1);
    renderCalendar();
});

// --- Price history chart ---

async function loadPriceHistory() {
    if (!db || !activeRoute) return;

    try {
        const { data, error } = await db
            .from('price_history')
            .select('*')
            .eq('route_from', activeRoute)
            .eq('route_to', 'AGP')
            .order('checked_at', { ascending: true })
            .limit(500);

        if (error) throw error;
        renderChart(data);
    } catch (err) {
        console.error('Failed to load price history:', err);
    }
}

function renderChart(historyData) {
    const canvas = document.getElementById('price-chart');
    if (priceChart) priceChart.destroy();

    if (!historyData || historyData.length === 0) {
        priceChart = new Chart(canvas, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: 'No price history yet', color: '#94a3b8' },
                },
            },
        });
        return;
    }

    // Group by departure_date, show price over time (checked_at)
    const byDate = {};
    historyData.forEach(row => {
        if (!byDate[row.departure_date]) byDate[row.departure_date] = [];
        byDate[row.departure_date].push({ x: row.checked_at, y: row.price });
    });

    // Pick up to 5 departure dates to chart
    const dates = Object.keys(byDate).sort().slice(0, 5);
    const colors = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#a855f7'];

    const datasets = dates.map((d, i) => ({
        label: d,
        data: byDate[d].map(p => ({ x: new Date(p.x), y: p.y })),
        borderColor: colors[i % colors.length],
        backgroundColor: 'transparent',
        tension: 0.3,
        pointRadius: 3,
    }));

    priceChart = new Chart(canvas, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'day' },
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(148,163,184,0.1)' },
                },
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(148,163,184,0.1)' },
                },
            },
            plugins: {
                legend: {
                    labels: { color: '#f1f5f9' },
                },
            },
        },
    });
}

// --- Init ---
loadData();
