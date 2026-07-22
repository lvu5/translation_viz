import { RorOrganization, searchAffiliations } from './api';

export type AffiliationMode = 'ror' | 'independent' | 'other';

export class AffiliationPicker {
    private readonly input: HTMLInputElement;
    private readonly results: HTMLElement;
    private readonly status: HTMLElement;
    private selected: RorOrganization | null = null;
    private organizations: RorOrganization[] = [];
    private activeIndex = -1;
    private debounceTimer: number | undefined;
    private requestController: AbortController | null = null;
    private mode: AffiliationMode = 'ror';
    private readonly optionIdPrefix: string;

    constructor(input: HTMLInputElement, results: HTMLElement, status: HTMLElement) {
        this.input = input;
        this.results = results;
        this.status = status;
        this.optionIdPrefix = `${input.id}-option`;

        input.addEventListener('input', () => this.handleInput());
        input.addEventListener('keydown', (event) => this.handleKeydown(event));
        input.addEventListener('blur', () => window.setTimeout(() => this.closeResults(), 150));
        input.addEventListener('focus', () => {
            if (this.organizations.length > 0 && !this.selected) this.openResults();
        });
    }

    setValue(name: string, rorId?: string | null): void {
        this.input.value = name;
        this.selected = rorId ? {
            ror_id: rorId,
            name,
            name_variants: [],
            locations: [],
            organization_types: [],
            domains: [],
            website: '',
        } : null;
        this.renderStatus();
    }

    getRorId(): string | null {
        return this.selected?.ror_id ?? null;
    }

    getName(): string {
        return this.input.value.trim();
    }

    getMode(): AffiliationMode {
        return this.mode;
    }

    setMode(mode: AffiliationMode): void {
        this.mode = mode;
        this.selected = null;
        this.organizations = [];
        this.requestController?.abort();
        window.clearTimeout(this.debounceTimer);
        this.closeResults();

        if (mode === 'independent') {
            this.input.value = 'Independent researcher';
            this.input.disabled = true;
            this.input.placeholder = '';
        } else {
            this.input.value = '';
            this.input.disabled = false;
            this.input.placeholder = mode === 'ror'
                ? 'Search university, institute, or company'
                : 'Enter your organization name';
        }
        this.renderStatus();
    }

    destroy(): void {
        this.requestController?.abort();
        window.clearTimeout(this.debounceTimer);
    }

    private handleInput(): void {
        this.selected = null;
        this.renderStatus();
        window.clearTimeout(this.debounceTimer);
        this.requestController?.abort();

        if (this.mode !== 'ror') {
            this.organizations = [];
            this.closeResults();
            return;
        }

        const query = this.input.value.trim();
        if (query.length < 2) {
            this.organizations = [];
            this.closeResults();
            return;
        }

        this.debounceTimer = window.setTimeout(() => this.search(query), 300);
    }

    private async search(query: string): Promise<void> {
        this.requestController = new AbortController();
        this.status.textContent = 'Searching organizations…';
        try {
            const response = await searchAffiliations(query, this.requestController.signal);
            if (this.input.value.trim() !== query) return;
            this.organizations = response.items;
            this.activeIndex = -1;
            this.renderResults();
            this.status.textContent = this.organizations.length
                ? 'Choose the matching organization from ROR.'
                : 'No match found. Select “Other / not listed in ROR” to enter it manually.';
        } catch (error) {
            if (error === 'abort') return;
            this.organizations = [];
            this.closeResults();
            this.status.textContent = 'Organization search is unavailable. Select “Other / not listed in ROR” to enter it manually.';
        }
    }

    private renderResults(): void {
        this.results.replaceChildren();
        if (!this.organizations.length) {
            this.closeResults();
            return;
        }

        this.organizations.forEach((organization, index) => {
            const option = document.createElement('button');
            option.type = 'button';
            option.className = 'affiliation-option';
            option.id = `${this.optionIdPrefix}-${index}`;
            option.setAttribute('role', 'option');
            option.setAttribute('aria-selected', 'false');

            const name = document.createElement('strong');
            name.textContent = organization.name;
            option.appendChild(name);

            const details = document.createElement('span');
            const places = organization.locations
                .map((location) => [location.city, location.country].filter(Boolean).join(', '))
                .filter(Boolean);
            const rawType = organization.organization_types[0] ?? '';
            const type = rawType
                ? rawType.charAt(0).toUpperCase() + rawType.slice(1).replace(/_/g, ' ')
                : '';
            details.textContent = [...places.slice(0, 2), type].filter(Boolean).join(' · ');
            if (details.textContent) option.appendChild(details);

            const variants = document.createElement('small');
            variants.textContent = organization.name_variants.slice(0, 3).join(' · ');
            if (variants.textContent) option.appendChild(variants);

            option.addEventListener('mousedown', (event) => event.preventDefault());
            option.addEventListener('click', () => this.select(index));
            this.results.appendChild(option);
        });

        this.openResults();
    }

    private handleKeydown(event: KeyboardEvent): void {
        if (this.results.hidden || !this.organizations.length) return;

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            this.setActiveIndex(Math.min(this.activeIndex + 1, this.organizations.length - 1));
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            this.setActiveIndex(Math.max(this.activeIndex - 1, 0));
        } else if (event.key === 'Enter' && this.activeIndex >= 0) {
            event.preventDefault();
            this.select(this.activeIndex);
        } else if (event.key === 'Escape') {
            event.preventDefault();
            this.closeResults();
        }
    }

    private setActiveIndex(index: number): void {
        this.activeIndex = index;
        const options = Array.from(this.results.querySelectorAll<HTMLElement>('[role="option"]'));
        options.forEach((option, optionIndex) => {
            const active = optionIndex === index;
            option.setAttribute('aria-selected', String(active));
            if (active) option.scrollIntoView({ block: 'nearest' });
        });
        this.input.setAttribute('aria-activedescendant', `${this.optionIdPrefix}-${index}`);
    }

    private select(index: number): void {
        this.selected = this.organizations[index];
        this.input.value = this.selected.name;
        this.closeResults();
        this.renderStatus();
    }

    private renderStatus(): void {
        if (this.mode === 'independent') {
            this.status.textContent = 'No organization or map location will be attached to your profile.';
            return;
        }
        if (this.mode === 'other') {
            this.status.textContent = 'This affiliation will be saved without a ROR link or automatic map location.';
            return;
        }
        if (!this.selected) {
            this.status.textContent = 'Start typing, then choose the matching organization from ROR.';
            return;
        }
        const place = this.selected.locations[0];
        const location = place ? [place.city, place.country].filter(Boolean).join(', ') : '';
        this.status.textContent = `Selected from ROR${location ? ` · ${location}` : ''}`;
    }

    private openResults(): void {
        this.results.hidden = false;
        this.input.setAttribute('aria-expanded', 'true');
    }

    private closeResults(): void {
        this.results.hidden = true;
        this.activeIndex = -1;
        this.input.setAttribute('aria-expanded', 'false');
        this.input.removeAttribute('aria-activedescendant');
    }
}
