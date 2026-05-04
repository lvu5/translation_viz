import './style.css';
import $ from 'jquery';

import { getToken, getUsername, getMe } from './api';
import { setupInstructions } from './utils';

$(async () => {
    setupInstructions('all');

    $('#register-btn').on('click', () => {
        window.location.href = 'profile.html';
    });

    const token = getToken();
    const username = getUsername();
    if (token && username) {
        try {
            const user = await getMe();
            showRoleButtons(user.roles);
        } catch {
            $('#auth-error').show();
        }
    }
});

function showRoleButtons(roles: string[]): void {
    $('#register-btn').hide();
    $('#cta-info-unauth').hide();

    const search = window.location.search;
    const container = $('#role-buttons');

    if (roles.includes('contributor')) {
        container.append(`<a href="contribute${search}" class="btn btn-success">✍️ Contribute</a>`);
    }
    if (roles.includes('reviewer')) {
        container.append(`<a href="review${search}" class="btn btn-success">🔍 Review</a>`);
    }
    if (roles.includes('admin')) {
        container.append(`<a href="admin${search}" class="btn btn-success">⚙️ Admin</a>`);
    }

    container.css('display', 'flex');
}
