import './assets/style.css';
import $ from 'jquery';

import {
    getCookie,
    getMe,
    updateProfile,
    registerUser,
    recoverLink,
    renderRoleSwitcher,
    ProfileAffiliation,
} from './api';
import { AffiliationMode, AffiliationPicker } from './affiliation-picker';
import { renderHeaderStatus } from './utils';

interface AffiliationEditor {
    root: HTMLElement;
    modeSelect: HTMLSelectElement;
    picker: AffiliationPicker;
}

$(async () => {
    const affiliationEditors: AffiliationEditor[] = [];
    const maximumAffiliations = 5;
    let nextAffiliationId = 0;
    const isRegistrationMode = !getCookie('ltb_token');

    function showProfileError(message: string): void {
        $('#status-msg').removeClass('msg-ok').addClass('msg-err').text(message);
    }

    function refreshAffiliationEditors(): void {
        const hasIndependent = affiliationEditors.some(
            (editor) => editor.picker.getMode() === 'independent',
        );
        affiliationEditors.forEach((editor, index) => {
            editor.root.querySelector<HTMLElement>('.affiliation-entry-title')!.textContent =
                index === 0 ? 'Primary affiliation' : `Additional affiliation ${index}`;
            const removeButton = editor.root.querySelector<HTMLButtonElement>('.remove-affiliation')!;
            removeButton.hidden = index === 0;
            const independentOption = editor.modeSelect.querySelector<HTMLOptionElement>(
                'option[value="independent"]',
            )!;
            independentOption.disabled = index > 0 || affiliationEditors.length > 1;
        });
        $('#add-affiliation').prop(
            'disabled',
            hasIndependent || affiliationEditors.length >= maximumAffiliations,
        );
    }

    function removeAllAffiliationEditors(): void {
        for (const editor of affiliationEditors) {
            editor.picker.destroy();
            editor.root.remove();
        }
        affiliationEditors.length = 0;
    }

    function addAffiliationEditor(initial?: ProfileAffiliation): void {
        if (affiliationEditors.length >= maximumAffiliations) return;

        const instanceId = nextAffiliationId++;
        const root = document.createElement('section');
        root.className = 'affiliation-entry';
        root.innerHTML = `
            <div class="affiliation-entry-heading">
                <strong class="affiliation-entry-title"></strong>
                <button class="btn-underlined remove-affiliation" type="button">Remove</button>
            </div>
            <label for="affiliation-mode-${instanceId}">Affiliation type</label>
            <select id="affiliation-mode-${instanceId}" class="affiliation-mode-select">
                <option value="ror">Organization in ROR</option>
                <option value="other">Other / not listed in ROR</option>
                <option value="independent">Independent researcher</option>
            </select>
            <label for="affiliation-${instanceId}">Organization</label>
            <div class="affiliation-picker">
                <input
                    type="text"
                    id="affiliation-${instanceId}"
                    maxlength="200"
                    autocomplete="off"
                    role="combobox"
                    aria-autocomplete="list"
                    aria-controls="affiliation-results-${instanceId}"
                    aria-expanded="false"
                    aria-describedby="affiliation-status-${instanceId}"
                >
                <div
                    id="affiliation-results-${instanceId}"
                    class="affiliation-results"
                    role="listbox"
                    hidden
                ></div>
            </div>
            <p
                id="affiliation-status-${instanceId}"
                class="affiliation-status"
                aria-live="polite"
            ></p>
        `;
        document.querySelector<HTMLElement>('#affiliation-list')!.appendChild(root);

        const modeSelect = root.querySelector<HTMLSelectElement>('.affiliation-mode-select')!;
        const picker = new AffiliationPicker(
            root.querySelector<HTMLInputElement>('.affiliation-picker input')!,
            root.querySelector<HTMLElement>('.affiliation-results')!,
            root.querySelector<HTMLElement>('.affiliation-status')!,
        );
        const editor = { root, modeSelect, picker };
        affiliationEditors.push(editor);

        const initialMode = initial?.kind ?? 'ror';
        modeSelect.value = initialMode;
        picker.setMode(initialMode);
        if (initial && initialMode !== 'independent') {
            picker.setValue(initial.name, initial.ror_id);
        }

        modeSelect.addEventListener('change', () => {
            const requestedMode = modeSelect.value as AffiliationMode;
            if (requestedMode === 'independent' && affiliationEditors.length > 1) {
                modeSelect.value = picker.getMode();
                showProfileError('Independent researcher cannot be combined with other affiliations.');
                return;
            }
            picker.setMode(requestedMode);
            refreshAffiliationEditors();
        });

        root.querySelector<HTMLButtonElement>('.remove-affiliation')!.addEventListener(
            'click',
            () => {
                const index = affiliationEditors.indexOf(editor);
                if (index <= 0) return;
                picker.destroy();
                affiliationEditors.splice(index, 1);
                root.remove();
                refreshAffiliationEditors();
            },
        );
        refreshAffiliationEditors();
    }

    $('#add-affiliation').on('click', () => addAffiliationEditor());

    if (!isRegistrationMode) {
        try {
            const user = await getMe();
            if (user.name) $('#name').val(user.name);
            const savedAffiliations = user.affiliations?.length
                ? user.affiliations
                : user.affiliation
                    ? [{
                        name: user.affiliation,
                        ror_id: user.affiliation_ror_id ?? null,
                        kind: user.affiliation_ror_id
                            ? 'ror' as const
                            : user.affiliation.trim().toLowerCase() === 'independent researcher'
                                ? 'independent' as const
                                : 'other' as const,
                    }]
                    : [];
            for (const affiliation of savedAffiliations) addAffiliationEditor(affiliation);
            if (!affiliationEditors.length) addAffiliationEditor();
            if (user.email) $('#email').val(user.email);
            if (user.credit_consent) $('#credit-consent').prop('checked', true);
            if (user.notification_consent === false) $('#notification-consent').prop('checked', false);

            renderHeaderStatus(user);
            renderRoleSwitcher(user.roles);
        } catch {
            window.location.href = 'index.html';
            return;
        }
    } else {
        addAffiliationEditor();
        $('.profile-wrap h2').text('Register as Contributor');
        $('#registration-form .sub').text('Fill out your details to request an account (can be modified later).');
        $('#recover-link-container').show();
    }

    $('#save-btn').on('click', async () => {
        const name = String($('#name').val()).trim();
        const email = String($('#email').val()).trim();
        const credit_consent = Boolean($('#credit-consent').prop('checked'));
        const notification_consent = Boolean($('#notification-consent').prop('checked'));

        if (!name || !email) {
            showProfileError('Name and email are required.');
            return;
        }

        const affiliations: ProfileAffiliation[] = [];
        const seen = new Set<string>();
        for (const editor of affiliationEditors) {
            const kind = editor.picker.getMode();
            const affiliationName = editor.picker.getName();
            const rorId = editor.picker.getRorId();
            if (kind === 'ror' && !rorId) {
                showProfileError('Choose every ROR organization from the search results.');
                return;
            }
            if (!affiliationName) {
                showProfileError('Enter every affiliation name or remove the empty affiliation.');
                return;
            }
            const deduplicationKey = rorId ?? affiliationName.toLowerCase();
            if (seen.has(deduplicationKey)) {
                showProfileError('The same affiliation cannot be added twice.');
                return;
            }
            seen.add(deduplicationKey);
            affiliations.push({ name: affiliationName, ror_id: rorId, kind });
        }
        if (
            affiliations.some((affiliation) => affiliation.kind === 'independent')
            && affiliations.length > 1
        ) {
            showProfileError('Independent researcher cannot be combined with other affiliations.');
            return;
        }

        const primaryAffiliation = affiliations[0];
        $('#save-btn').prop('disabled', true);
        try {
            const profile = {
                name,
                affiliation: primaryAffiliation.name,
                affiliation_ror_id: primaryAffiliation.ror_id,
                affiliations,
                email,
                credit_consent,
                notification_consent,
            };
            if (isRegistrationMode) {
                await registerUser(profile);
                window.location.href = 'index.html?registered=1';
            } else {
                await updateProfile(profile);
                window.location.href = 'index.html';
            }
        } catch (error) {
            showProfileError(String(error));
            $('#save-btn').prop('disabled', false);
        }
    });

    $('#show-recover-btn').on('click', (event) => {
        event.preventDefault();
        $('#registration-form').hide();
        $('#recover-window').show();
        $('#recover-form-content').show();
        $('.profile-wrap h2').text('Recover Login Link');
        $('#recover-status-msg').text('').removeClass('msg-ok msg-err').css('color', '');
        $('#recover-email').prop('disabled', false).val('');
        $('#send-recover-btn').prop('disabled', false);
    });

    $('#back-to-register-btn').on('click', (event) => {
        event.preventDefault();
        $('#recover-window').hide();
        $('#registration-form').show();
        $('.profile-wrap h2').text('Register as Contributor');
    });

    $('#send-recover-btn').on('click', async () => {
        const email = String($('#recover-email').val()).trim();
        if (!email) {
            $('#recover-status-msg').removeClass('msg-ok').addClass('msg-err').text('Please enter your email.');
            return;
        }

        $('#send-recover-btn').prop('disabled', true);
        $('#recover-email').prop('disabled', true);
        try {
            await recoverLink(email);
            $('#recover-form-content').hide();
            $('#recover-status-msg').removeClass('msg-err msg-ok').css('color', 'inherit').text('If an account exists, a link has been sent.');
            $('#recover-email').val('');
        } catch {
            $('#recover-status-msg').removeClass('msg-ok').addClass('msg-err').text('Failed to process request.');
            $('#send-recover-btn').prop('disabled', false);
            $('#recover-email').prop('disabled', false);
        }
    });

    window.addEventListener('beforeunload', removeAllAffiliationEditors);
});
