import type { AffiliationMapPlace } from './api';
import { initializeAffiliationMap } from './affiliation-map';

import './assets/pages-dashboard.css';

interface StaticDashboardData {
    generated_at: string;
    source: string;
    total_submissions: number;
    total_authors: number;
    affiliation_places: AffiliationMapPlace[];
}

function requiredElement<T extends HTMLElement>(selector: string): T {
    const element = document.querySelector<T>(selector);
    if (!element) throw new Error(`Missing page element: ${selector}`);
    return element;
}

function formatSnapshotTime(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Public dashboard snapshot';
    return `Data updated ${new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
    }).format(date)}`;
}

async function loadDashboard(): Promise<void> {
    const loading = requiredElement<HTMLElement>('#affiliation-map-loading');
    const snapshotStatus = requiredElement<HTMLElement>('#snapshot-status');

    try {
        const response = await fetch('./data/dashboard.json', {
            headers: { Accept: 'application/json' },
        });
        if (!response.ok) {
            throw new Error(`Dashboard snapshot returned HTTP ${response.status}.`);
        }

        const dashboard = await response.json() as StaticDashboardData;
        if (!Array.isArray(dashboard.affiliation_places)) {
            throw new Error('Dashboard snapshot is missing affiliation locations.');
        }

        snapshotStatus.textContent = formatSnapshotTime(dashboard.generated_at);
        initializeAffiliationMap(
            dashboard.affiliation_places,
            dashboard.total_submissions,
            dashboard.total_authors,
        );
    } catch (error) {
        loading.classList.add('is-error');
        loading.textContent = 'The public dashboard snapshot could not be loaded. Please try again shortly.';
        snapshotStatus.textContent = 'Dashboard data unavailable';
        console.error(error);
    }
}

if (new URLSearchParams(window.location.search).get('embed') === '1') {
    document.documentElement.classList.add('is-embedded');
}

void loadDashboard();
