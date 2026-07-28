export interface AffiliationMapAuthor {
    name: string;
    accepted: number;
}

export interface AffiliationMapAffiliation {
    name: string;
    search_terms: string[];
    logo_domain: string;
    logo_file: string;
    accepted: number;
    authors: AffiliationMapAuthor[];
}

export interface AffiliationMapPlace {
    lat: number;
    lng: number;
    city: string;
    country: string;
    precision: 'exact' | 'city' | 'country';
    accepted: number;
    affiliations: AffiliationMapAffiliation[];
}
