
        // ===================================================
        // CONFIG
        // ===================================================
        const API = '';  // same origin — adjust if different host e.g. 'http://localhost:8000'

        // ===================================================
        // STATE
        // ===================================================
        let state = {
            token: localStorage.getItem('tf_token') || null,
            refreshToken: localStorage.getItem('tf_refresh') || null,
            user: null,
            orgs: [],
            projects: [],
            tasks: [],
            members: [],
            currentOrgId: null,      // Tracks the "Active Workspace"
            currentProjectId: null,  // Tracks the "Active Project"
            currentOrgName: null
        };
        async function confirmDeleteTask(taskId) {
            if (!confirm("Are you sure you want to delete this task?")) return;

            try {
                const response = await fetch(`http://127.0.0.px/tasks/${taskId}`, { // Update URL to your API base
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    showToast("Task deleted", "success");
                    // Automatically refresh the tasks for the current project
                    if (typeof loadProjectTasks === "function") {
                        loadProjectTasks(state.currentProjectId);
                    }
                } else {
                    const errorData = await response.json();
                    showToast(errorData.detail || "Delete failed", "error");
                }
            } catch (err) {
                console.error("Delete Error:", err);
                showToast("Connection error", "error");
            }
        }

        // Helper to show feedback (ensure this exists in your script)
        function showToast(message, type) {
            const toast = document.getElementById('toast');
            if (!toast) return;
            toast.textContent = message;
            toast.className = `show ${type}`;
            setTimeout(() => { toast.className = ''; }, 3000);
        }

        

        async function updateTaskStatus(taskId, newStatus) {
            try {
                // 1. UPDATE LOCAL STATE IMMEDIATELY (Optimistic UI)
                // This stops the "Failed" feeling because the data is already updated locally
                const task = state.tasks.find(t => t.id === taskId);
                if (task) {
                    task.status = newStatus;
                    renderTasks(); // Redraw the UI immediately
                }

                // 2. CALL API
                await api('PATCH', `tasks/${taskId}/status`, { status: newStatus });
                
                // 3. SHOW SUCCESS
                showToast(`Moved to ${newStatus}`, "success");

                // 4. SYNC (Optional)
                // We don't 'await' this or we do it quietly so it doesn't trigger the catch block
                openProjectDetail(state.currentProjectId).catch(err => console.error("Sync error:", err));

            } catch (e) {
                console.error("Drag Drop Error:", e);
                showToast("Server sync failed. Refreshing...", "error");
                // If it actually failed, reload to put the task back
                openProjectDetail(state.currentProjectId);
            }
        }

        // ===================================================
        // UTILS
        // ===================================================
        function showToast(msg, type = 'success') {
            const el = document.getElementById('toast');
            el.textContent = msg;
            el.className = `show ${type}`;
            clearTimeout(el._t);
            el._t = setTimeout(() => el.className = '', 3000);
        }

        function setLoading(id, loading) {
            const el = document.getElementById(id);
            if (!el) return;
            el.innerHTML = loading ? '<div class="loader"><div class="spinner"></div></div>' : '';
        }

        function badge(text) {
            if (!text) return '';
            const t = text.toLowerCase().replace(' ', '');
            const cls = t === 'pending' ? 'pending' : t === 'inprogress' ? 'progress' : t === 'done' ? 'done' : t === 'high' ? 'high' : t === 'medium' ? 'medium' : t === 'low' ? 'low' : 'default';
            return `<span class="badge badge-${cls}">${text}</span>`;
        }

        function fmtDate(d) {
            if (!d) return '';
            return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }

        function initials(name) {
            if (!name) return 'U';
            return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
        }

        // ===================================================
        // API CALLS
        // ===================================================
        async function api(method, path, body, skipAuth = false) {
            const headers = { 'Content-Type': 'application/json' };
            if (state.token && !skipAuth) headers['Authorization'] = `Bearer ${state.token}`;

            const res = await fetch(API + path, {
                method,
                headers,
                body: body ? JSON.stringify(body) : undefined,
            });

            if (res.status === 401 && !skipAuth) {
                // try refresh
                if (state.refreshToken) {
                    try {
                        const r = await fetch(API + `/auth/refresh?refresh_token=${encodeURIComponent(state.refreshToken)}`, { method: 'POST', headers });
                        if (r.ok) {
                            const t = await r.json();
                            setTokens(t);
                            headers['Authorization'] = `Bearer ${state.token}`;
                            const retry = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
                            if (!retry.ok) throw new Error((await retry.json()).detail || 'Request failed');
                            return retry.status === 204 ? null : await retry.json();
                        }
                    } catch { }
                }
                doLogout();
                throw new Error('Session expired');
            }

            if (res.status === 204) return null;
            // SAFE PARSING: Get text first to see if it's actually JSON
            const text = await res.text();
            let data;
            try {
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                // If it's not JSON, it's likely a server-side crash (HTML error page)
                throw new Error(`Server Error: ${res.status}. Please check backend logs.`);
            }

            if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
            return data;
        }

        function setTokens(t) {
            state.token = t.access_token;
            state.refreshToken = t.refresh_token;
            localStorage.setItem('tf_token', t.access_token);
            localStorage.setItem('tf_refresh', t.refresh_token);
        }

        // ===================================================
        // AUTH
        // ===================================================
        function switchTab(tab) {
            // 1. Clear errors
            const errorEl = document.getElementById('auth-error');
            if (errorEl) errorEl.style.display = 'none';

            // 2. Handle the "Active" tab styling safely
            document.querySelectorAll('.auth-tab').forEach(b => {
                b.classList.remove('active');
                // If this button matches the tab we are switching to, make it active
                if (b.innerText.toLowerCase().includes(tab)) {
                    b.classList.add('active');
                }
            });

            // 3. Toggle form visibility
            const loginForm = document.getElementById('login-form');
            const registerForm = document.getElementById('register-form');

            if (loginForm) loginForm.style.display = tab === 'login' ? 'block' : 'none';
            if (registerForm) registerForm.style.display = tab === 'register' ? 'block' : 'none';
        }
        function showAuthError(msg) {
            const el = document.getElementById('auth-error');
            el.textContent = msg;
            el.style.display = 'block';
        }

        async function doLogin() {
            const emailEl = document.getElementById('login-email');
            const passEl = document.getElementById('login-password');

            const email = emailEl.value.trim();
            const pass = passEl.value;

            if (!email || !pass) {
                return showAuthError('Please fill in all fields.');
            }

            try {
                // OAuth2 standard uses 'username' and 'password' fields
                const formData = new URLSearchParams();
                formData.append('username', email);
                formData.append('password', pass);

                const res = await fetch(API + '/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData.toString(),
                });

                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.detail || 'Login failed');
                }

                // IMPORTANT: Ensure setTokens saves the keys exactly as saveOrg expects
                setTokens(data);

                // Clear the form
                emailEl.value = '';
                passEl.value = '';

                await loadApp();

            } catch (e) {
                console.error("Login Error:", e);
                showAuthError(e.message);
            }
        }

        async function doRegister() {
            const name = document.getElementById('reg-name').value.trim();
            const email = document.getElementById('reg-email').value.trim();
            const pass = document.getElementById('reg-password').value;

            const errorEl = document.getElementById('auth-error'); // Make sure this ID exists

            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name,      // Python expects 'name' (from UserBase)
                        email: email,     // Python expects 'email' (from UserBase)
                        password: pass    // Python expects 'password' (from UserCreate)
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    // Detailed error handling to see EXACTLY why FastAPI rejected it
                    let msg = "Registration failed";
                    if (Array.isArray(data.detail)) {
                        // Shows which specific field failed (e.g., "password: string too short")
                        msg = data.detail.map(e => `${e.loc[1]}: ${e.msg}`).join(", ");
                    } else if (data.detail) {
                        msg = data.detail;
                    }
                    throw new Error(msg);
                }

                showToast('Account created! Please sign in.', 'success');

                // Clear form and switch
                document.getElementById('reg-name').value = '';
                document.getElementById('reg-email').value = '';
                document.getElementById('reg-password').value = '';

                switchTab('login');

            } catch (e) {
                console.error("Registration Error:", e.message);
                if (errorEl) {
                    errorEl.textContent = e.message;
                    errorEl.style.display = 'block';
                }
            }
        }
        function doLogout() {
    // 1. Clear memory state
    state.token = null;
    state.refreshToken = null;
    state.user = null;

    // 2. Clear ALL storage keys used by Team Flow
    localStorage.removeItem('tf_token');
    localStorage.removeItem('tf_refresh');
    localStorage.removeItem('tf_user'); // Add this if you save user info

    // 3. Reset UI visibility
    document.getElementById('app').style.display = 'none';
    document.getElementById('auth-screen').style.display = 'flex';
    
    // 4. Clear sensitive inputs (Optional but safer)
    document.getElementById('login-password').value = '';
    
    console.log("Logged out successfully.");
}

        // ===================================================
        // LOAD APP
        // ===================================================
        
        async function loadApp() {
    try {
        state.user = await api('GET', '/auth/me');
    } catch {
        doLogout(); 
        return;
    }

    // 1. Show the App UI first so elements are available for rendering
    document.getElementById('auth-screen').style.display = 'none';
    document.getElementById('app').style.display = 'flex';

    // 2. Set nav user info
    document.getElementById('nav-avatar').textContent = initials(state.user.name);
    document.getElementById('nav-name').textContent = state.user.name;

    // 3. REFRESH EVERYTHING: Organizations AND Invitations
    await loadOrgs(); 
    await checkInvitations(); // Ensure the "Invitations" section on the dashboard is updated

    const savedProjectId = localStorage.getItem('tf_last_project');
    
    if (savedProjectId) {
        // If we have a saved project, try to open it
        await openProjectDetail(savedProjectId);
    } else {
        // Default to dashboard
        showView('dashboard');
        // IMPORTANT: renderDashboard relies on state.tasks/state.projects 
        // which are usually loaded inside loadOrgs/loadProjects
        renderDashboard();
    }
}

        // ===================================================
        // VIEWS
        // ===================================================
        function showView(name) {
    // 1. Hide all views
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    
    // 2. Clear all nav buttons
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    // 3. Show the target view
    const target = document.getElementById(`view-${name}`);
    if (target) {
        target.classList.add('active');
    } else {
        console.error(`View "view-${name}" not found in HTML!`);
    }

    /* CRITICAL FIX: Check if 'event' exists and if the target is a nav-btn.
       This prevents the "Nothing happens" crash when calling from JS logic.
    */
    if (typeof event !== 'undefined' && event && event.target && event.target.classList.contains('nav-btn')) {
        event.target.classList.add('active');
    }

    // 4. Trigger Renders
    if (name === 'dashboard') renderDashboard();
    if (name === 'orgs') renderOrgs();
    if (name === 'projects') renderProjects(); // This ensures projects are drawn
    if (name === 'tasks') renderTasks();
    if (name === 'members') renderMembers();
    if (name === 'profile') renderProfile();
    if (name === 'org-settings') renderOrgSettings();
}

        // ===================================================
        // ORGS
        // ===================================================
        function enterOrganization(id, name, description) {
            // 1. Save to state
            state.currentOrgId = id;
            state.currentOrgName = name;
            state.currentOrgDescription = description || "No description available for this organization.";

            // 2. Update the UI Text
            document.getElementById('current-org-title').textContent = name;
            document.getElementById('current-org-description').textContent = state.currentOrgDescription;

            // 3. Switch view and load projects
            showView('projects');
            loadProjects(id);
        }

        async function loadOrgs() {
            try {
                const data = await api('GET', '/organizations/');
                state.orgs = data;

                // ADD THIS: If we are already "inside" an org, verify it still exists
                // or clear the context if it was deleted.
                if (state.orgs.length === 0) {
                    currentContext.orgId = null;
                }

                renderOrgs(); // Ensure you call render after updating state
            } catch (e) {
                console.error("Failed to load orgs:", e);
                state.orgs = [];
                renderOrgs();
            }
        }

        async function deleteOrg(id) {
            if (!confirm("Are you sure you want to delete this organization?")) return;

            try {
                // MATCHING THE BACKEND: /organizations/{id} (No trailing slash)
                const response = await fetch(`/organizations/${id}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${state.token}`
                    }
                });

                if (!response.ok) {
                    const result = await response.json();
                    throw new Error(result.detail || "Delete failed");
                }

                showToast("Organization deleted");
                await loadOrgs(); // Refresh the list
            } catch (err) {
                console.error("Delete error:", err);
                showToast(err.message, "error");
            }
        }

        function renderOrgs() {
    const grid = document.getElementById('orgs-grid');
    if (!grid) return;

    if (!state.orgs || state.orgs.length === 0) {
        grid.innerHTML = `<div class="empty-state">No organizations found.</div>`;
        return;
    }

    grid.innerHTML = state.orgs.map(o => {
        // 1. Format the Date
        const dateStr = o.created_at
            ? new Date(o.created_at).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            })
            : 'Unknown';

        // 2. Format Projects Badges
        const projectsHtml = o.projects && o.projects.length > 0
            ? o.projects.map(p => `<span class="badge badge-progress">${p.name}</span>`).join('')
            : '<span class="text-dim">No projects</span>';

        // 3. CRITICAL: Escape strings and REMOVE NEW LINES
        // We must remove \n (line breaks) because they break JavaScript onclick attributes
        const escapedName = o.name.replace(/'/g, "\\'");
        const escapedDesc = (o.description || "")
            .replace(/'/g, "\\'")             // Escape single quotes
            .replace(/\r?\n|\r/g, " ")        // Replace "Enter" keys with a space
            .replace(/"/g, "&quot;");         // Escape double quotes for safety

        return `
            <div class="card" 
                 onclick="enterOrganization('${o.id}', '${escapedName}', '${escapedDesc}')" 
                 style="cursor:pointer; position: relative;">
                
                <div class="card-title" style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        ${o.name}
                        <span style="font-size: 10px; color: var(--text-dim);">#${o.id.substring(0, 8)}</span>
                    </div>
                    
                    <i class="fas fa-cog" 
                       onclick="event.stopPropagation(); openOrgSettings('${o.id}')" 
                       style="cursor: pointer; opacity: 0.5; font-size: 14px; padding: 5px;"
                       onmouseover="this.style.opacity='1'" 
                       onmouseout="this.style.opacity='0.5'"
                       title="Organization Settings"></i>
                </div>
                
                <p style="font-size: 12px; color: var(--text-dim); margin: 8px 0; line-height: 1.4;">
                    ${o.description ? (o.description.substring(0, 60) + (o.description.length > 60 ? '...' : '')) : 'No description set.'}
                </p>

                <div style="margin: 12px 0; display: flex; flex-wrap: wrap; gap: 4px;">
                    ${projectsHtml}
                </div>

                <div class="card-meta" style="display: flex; flex-direction: column; gap: 4px;">
                    <span>Slug: <strong>${o.slug}</strong></span>
                    <span>Created: <strong>${dateStr}</strong></span> 
                </div>
                
                <div class="card-actions">
                    <button class="btn-sm btn-edit" onclick="event.stopPropagation(); editOrg('${o.id}')">Edit</button>
                    <button class="btn-sm btn-del" onclick="event.stopPropagation(); deleteOrg('${o.id}')">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

        function renderOrgSettings() {
    const rolesContainer = document.getElementById('role-list-container');
    const membersContainer = document.getElementById('org-members-list');
    const org = state.currentOrg; 

    if (!org) return;

    // --- 1. Render Roles ---
    if (org.custom_roles && rolesContainer) {
        rolesContainer.innerHTML = org.custom_roles.map(role => `
            <div class="role-row" style="display: flex; align-items: center; justify-content: space-between; padding: 12px; background: #374151; border-radius: 8px; margin-bottom: 8px;">
                <input type="text" value="${role.role_name}" id="input-role-${role.id}" 
                    style="background: transparent; border: 1px solid transparent; color: white; flex-grow: 1; padding: 5px; font-weight: 500;">
                <div style="display: flex; gap: 8px; margin-left: 10px;">
                    <button onclick="updateRoleName('${role.id}')" style="background: none; border: none; color: #10b981; cursor: pointer;">
                        <i class="fas fa-check"></i> Save
                    </button>
                    <button onclick="deleteRole('${role.id}')" style="background: none; border: none; color: #ef4444; cursor: pointer;">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }

    // --- 2. Render Members ---
const membersList = org.memberships || []; 

if (membersContainer) {
    console.log("Current Org State:", org); // DEBUG: Check this in F12 console

    if (membersList.length === 0) {
        membersContainer.innerHTML = '<div class="p-4 text-center text-muted">No members found.</div>';
    } else {
        membersContainer.innerHTML = membersList.map(m => {
            // 1. Safety check: Does the user object exist?
            if (!m.user) {
                console.warn("Membership found without user data:", m);
                return ''; 
            }

            // 2. Handle different naming conventions (name vs full_name)
            const name = m.user.full_name || m.user.name || m.user.username || "Unknown User";
            const email = m.user.email || "No Email";
            const initial = name.charAt(0).toUpperCase();

            return `
                <div class="member-row" style="display: flex; align-items: center; justify-content: space-between; padding: 12px; border-bottom: 1px solid #374151;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div class="avatar-sm" style="background: #4f46e5; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; color: white;">
                            ${initial}
                        </div>
                        <div>
                            <div style="font-weight: 500; color: white;">${name}</div>
                            <div style="font-size: 12px; color: #9ca3af;">${email}</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span class="badge" style="background: #1f2937; color: #818cf8; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-transform: uppercase;">
                            ${m.role}
                        </span>
                        ${m.user_id !== state.user.id ? `
                            <button onclick="removeMember('${m.user_id}')" title="Remove Member" style="background: none; border: none; color: #ef4444; cursor: pointer;">
                                <i class="fas fa-user-minus"></i>
                            </button>
                        ` : '<span style="font-size: 10px; color: #6b7280;">(You)</span>'}
                    </div>
                </div>
            `;
        }).join('');
    }
}
}

        async function openOrgSettings(orgId) {
            if (!orgId) return;

            try {
                // 1. Fetch the full organization data
                const org = await api('GET', `/organizations/${orgId}`);
                
                // 2. CRITICAL: Save to state so other functions can use it
                state.currentOrg = org;
                state.currentOrgId = org.id; 

                // 3. Populate the text fields
                document.getElementById('edit-org-name').value = org.name;
                document.getElementById('edit-org-desc').value = org.description || '';

                // 4. Show view and render lists
                showView('org-settings');
                renderOrgSettings();
                
            } catch (err) {
                showToast("Failed to load settings: " + err.message, "error");
            }
        }

        async function updateRoleName(roleId) {
            const newName = document.getElementById(`input-role-${roleId}`).value.trim();
            if (!newName) return showToast("Role name cannot be empty", "error");

            try {
                // We use the PUT route we designed
                const updatedOrg = await api('PUT', `/organizations/${state.currentOrg.id}/roles/${roleId}?role_name=${newName}`);
                
                // Update local state with the full fresh Org object returned by get_org_by_id
                state.currentOrg = updatedOrg; 
                showToast("Role updated successfully!");
                renderOrgSettings();
            } catch (e) {
                showToast("Failed to update role", "error");
            }
        }

        async function deleteRole(roleId) {
            if (!confirm("Are you sure? Users assigned to this role might be affected.")) return;

            try {
                await api('DELETE', `/organizations/${state.currentOrg.id}/roles/${roleId}`);
                
                // Remove from local state and re-render
                state.currentOrg.custom_roles = state.currentOrg.custom_roles.filter(r => r.id !== roleId);
                renderOrgSettings();
                showToast("Role deleted");
            } catch (e) {
                showToast(e.message || "Could not delete role", "error");
            }
        }

        async function addMemberToOrg() {
            const email = document.getElementById('new-member-email').value;
            try {
            const res = await api('POST', `/organizations/${orgId}/invite?email=${encodeURIComponent(email)}`);                showToast(response.message, "success");
            renderOrgSettings(); // Refresh the list
            } catch (err) {
                showToast(err.message, "error");
            }
        }
        async function renderInvites() {
            const invites = await api('GET', '/users/me/invites'); // You'll need this route
            const container = document.getElementById('invites-container');
            
            if (invites.length === 0) {
                container.innerHTML = '<p class="text-gray-500">No pending invitations.</p>';
                return;
            }

            container.innerHTML = invites.map(inv => `
                <div class="invite-card">
                    <span>Invite to <strong>${inv.organization_name}</strong></span>
                    <div class="actions">
                        <button onclick="handleInvite('${inv.id}', 'accept')">Accept</button>
                        <button class="text-red-500" onclick="handleInvite('${inv.id}', 'decline')">Decline</button>
                    </div>
                </div>
            `).join('');
        }

        async function handleInvite(id, action) {
            try {
                await api('POST', `/invitations/${id}/${action}`);
                showToast(`Invitation ${action}ed!`, "success");
                initApp(); // Refresh everything
            } catch (err) {
                showToast(err.message, "error");
            }
        }

                // 1. Fetch and Update the UI
        async function checkInvitations() {
    try {
        console.log("Checking for invites at: /organizations/me/invites");
        // This is the correct endpoint for your Organization invites
        const invites = await api('GET', '/organizations/me/invites'); 
        
        const badge = document.getElementById('invite-badge');
        const list = document.getElementById('invites-list');

        // Safety check: make sure these elements exist in your HTML
        if (!list) return;

        if (invites && invites.length > 0) {
            if (badge) {
                badge.innerText = invites.length;
                badge.style.display = 'block';
            }
            
            list.innerHTML = invites.map(inv => `
                <div class="p-3 border-bottom border-secondary d-flex justify-content-between align-items-center" style="background: #1f2937;">
                    <div>
                        <strong style="color: white; font-size: 0.9rem;">${inv.organization_name}</strong>
                        <p style="margin: 0; font-size: 0.75rem; color: #9ca3af;">Organization Invite</p>
                    </div>
                    <div class="d-flex gap-2">
                        <button onclick="processInvite('${inv.id}', 'accept')" class="btn btn-sm btn-success">Accept</button>
                        <button onclick="processInvite('${inv.id}', 'decline')" class="btn btn-sm btn-danger">✕</button>
                    </div>
                </div>
            `).join('');
        } else {
            if (badge) badge.style.display = 'none';
            list.innerHTML = `
                <div class="text-center py-4" style="color: #9ca3af;">
                    <i class="fas fa-envelope-open mb-2" style="font-size: 1.5rem; opacity: 0.3;"></i>
                    <p style="margin: 0; font-size: 0.85rem;">No pending invites</p>
                </div>`;
        }
    } catch (err) {
        console.error("Invitation Sync Error:", err);
        const list = document.getElementById('invites-list');
        if (list) list.innerHTML = `<p class="text-danger p-2" style="font-size: 0.7rem;">Connection error</p>`;
    }
}

        async function processInvite(id, action) {
            try {
                // action will be 'accept' or 'decline'
                // Endpoint: /organizations/invites/{id}/accept
                await api('POST', `/organizations/invites/${id}/${action}`);
                
                showToast(`Invitation ${action}ed!`, "success");
                
                // Refresh the organizations list in the sidebar
                await loadMyOrganizations(); 
                
                // Refresh the bell icon/notification list
                await checkInvitations(); 
                
            } catch (err) {
                showToast(err.message, "error");
            }
        }

        // 3. Toggle Dropdown Visibility
        document.getElementById('notifications-wrapper').addEventListener('click', (e) => {
            const dropdown = document.getElementById('notifications-dropdown');
            dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
            e.stopPropagation();
        });

        // Close dropdown if clicking outside
        window.addEventListener('click', () => {
            document.getElementById('notifications-dropdown').style.display = 'none';
        });


        async function inviteMemberToOrg() {
    const emailInput = document.getElementById('new-member-email');
    const msgArea = document.getElementById('invite-message');
    const email = emailInput.value.trim();

    if (!email) {
        msgArea.style.color = "#ef4444";
        msgArea.textContent = "Please enter a valid email.";
        return;
    }

    try {
        // FIX 1: Change '/members' to '/invite' to match your new FastAPI route
        // FIX 2: Added /organizations prefix (if your API helper doesn't add it)
        const result = await api('POST', `/organizations/${state.currentOrgId}/invite?email=${encodeURIComponent(email)}`);

        // Success
        msgArea.style.color = "#10b981";
        // Update the message to reflect it's an invite, not a direct add
        msgArea.textContent = `Invitation sent to ${email}!`;
        emailInput.value = ''; 
        
        // Note: We don't update state.currentOrg here anymore because 
        // the user isn't a member yet—they are just "pending."
        
    } catch (err) {
        msgArea.style.color = "#ef4444";
        msgArea.textContent = err.message;
    }
}

        async function removeMember(userId) {
            // Professional touch: always confirm before a destructive action
            if (!confirm("Are you sure you want to remove this member? They will lose access to all projects in this organization.")) {
                return;
            }

            try {
                // 1. Call the API
                const updatedOrg = await api('DELETE', `/organizations/${state.currentOrgId}/members/${userId}`);
                
                // 2. Update the local state with the new member list
                state.currentOrg = updatedOrg;
                
                // 3. Re-render the settings view
                renderOrgSettings();
                
                showToast("Member removed successfully", "success");
            } catch (err) {
                console.error("Removal failed:", err);
                showToast(err.message || "Failed to remove member", "error");
            }
        }

        async function cancelInvitation(inviteId) {
    if (!confirm("Cancel this pending invitation?")) return;

    try {
        // This hits the new invitation decline/cancel endpoint
        await api('POST', `/organizations/invites/${inviteId}/decline`);
        
        showToast("Invitation cancelled", "success");
        
        // Refresh the settings to update the "Pending" list
        renderOrgSettings(); 
    } catch (err) {
        showToast(err.message, "error");
    }
}
        function openModal(type) {
            if (type === 'org') {
                document.getElementById('org-modal-title').textContent = "New Organization";
                document.getElementById('org-edit-id').value = ""; // VERY IMPORTANT
                document.getElementById('org-name').value = "";
                document.getElementById('org-slug').value = "";
                document.getElementById('org-description').value = "";
            }
            if (type === 'project') {
                document.getElementById('project-modal-title').textContent = "New Project";
                document.getElementById('project-edit-id').value = "";
                document.getElementById('project-name').value = "";

                // Populate the read-only "Organization" field from state
                const displayOrgEl = document.getElementById('display-current-org');
                if (displayOrgEl) {
                    displayOrgEl.value = state.currentOrgName || "No Organization Selected";
                }
            }
            document.getElementById(`modal-${type}`).classList.add('active');
        }



        function closeModal(type) {
            const modal = document.getElementById(`modal-${type}`);
            if (modal) {
                // Remove 'active' or 'open' classes
                modal.classList.remove('active');
                modal.classList.remove('open');
            }

            // Crucial: Clear the edit ID so the modal resets for next time
            const editIdEl = document.getElementById('org-edit-id');
            if (editIdEl) editIdEl.value = "";

            // Clear error messages
            const errorEl = document.getElementById(`${type}-error`);
            if (errorEl) {
                errorEl.style.display = 'none';
                errorEl.textContent = "";
            }
        }
        function populateOrgSelect(selectId) {
            const sel = document.getElementById(selectId);
            sel.innerHTML = state.orgs.map(o => `<option value="${o.id}">${escHtml(o.name)}</option>`).join('') || '<option value="">No organizations</option>';
        }

        function populateProjectSelect(selectId) {
            const sel = document.getElementById(selectId);
            sel.innerHTML = state.projects.map(p => `<option value="${p.id}">${escHtml(p.name)}</option>`).join('') || '<option value="">No projects</option>';
        }

        function editOrg(id) {
            console.log("Edit button clicked for ID:", id); // Check if this shows in F12 console

            // Find the data in your local state
            const org = state.orgs.find(o => o.id === id);

            if (!org) {
                console.error("Organization not found in state for ID:", id);
                return;
            }

            // Populate the Modal Fields
            // Make sure these IDs ('org-name', etc.) match your HTML exactly!
            document.getElementById('org-modal-title').textContent = "Edit Organization";
            document.getElementById('org-edit-id').value = org.id;
            document.getElementById('org-name').value = org.name;
            document.getElementById('org-slug').value = org.slug;
            document.getElementById('org-description').value = org.description || "";

            // Show the Modal
            const modal = document.getElementById('modal-org');
            if (modal) {
                modal.classList.add('active');
                console.log("Modal should now be visible");
            } else {
                console.error("Could not find modal with ID 'modal-org'");
            }
        }
        function openEditOrgModal(org) {
            document.getElementById('org-modal-title').textContent = "Edit Organization";
            document.getElementById('org-edit-id').value = org.id;
            document.getElementById('org-name').value = org.name;
            document.getElementById('org-slug').value = org.slug;

            // Add this line to fill the description when editing
            document.getElementById('org-description').value = org.description || "";

            document.getElementById('modal-org').classList.add('active');
        }

        async function saveOrg() {
            console.log("Save process started...");

            const nameEl = document.getElementById('org-name');
            const slugEl = document.getElementById('org-slug');
            const descEl = document.getElementById('org-description');
            const editIdEl = document.getElementById('org-edit-id');
            const errorEl = document.getElementById('org-error');

            // 1. Validate elements exist
            if (!nameEl || !slugEl || !descEl || !errorEl) {
                console.error("Missing HTML elements!");
                return;
            }

            const name = nameEl.value.trim();
            const slug = slugEl.value.trim();
            const description = descEl.value.trim();
            const editId = editIdEl ? editIdEl.value : null;

            if (!name || !slug) {
                errorEl.textContent = "Name and Slug are required.";
                errorEl.style.display = 'block';
                return;
            }

            // 2. DEFINE URL AND METHOD HERE (Fixes the 'not defined' error)
            const method = editId ? 'PUT' : 'POST';
            const url = editId ? `/organizations/${editId}` : '/organizations/';
            const payload = { name, slug, description };

            console.log(`Sending ${method} to ${url}`);

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: JSON.stringify(payload)
                });

                // 3. Handle the response
                if (!response.ok) {
                    const result = await response.json();
                    throw new Error(result.detail || "Failed to save organization");
                }

                console.log("Save successful!");

                // 4. Close modal and refresh UI
                closeModal('org');

                if (typeof loadOrgs === 'function') {
                    await loadOrgs();
                } else {
                    window.location.reload();
                }

            } catch (err) {
                console.error("Save error:", err);
                errorEl.textContent = err.message;
                errorEl.style.display = 'block';
            }
        }
        // ===================================================
        // PROJECTS
        // ===================================================
        function renderProjects() {
            const grid = document.getElementById('projects-grid');
            if (!grid) return;

            const projects = state.projects || [];

            if (projects.length === 0) {
                grid.innerHTML = `<div class="empty-state">No projects found in this organization.</div>`;
                return;
            }

            grid.innerHTML = projects.map(p => {
                const dateObj = p.created_at ? new Date(p.created_at) : null;
                const dateStr = (dateObj && !isNaN(dateObj)) ? dateObj.toLocaleDateString() : "Pending...";

                return `
            <div class="card" onclick="openProjectDetail('${p.id}')" style="cursor:pointer">
                <div class="card-title">
                    ${p.name}
                    <span style="font-size: 10px; color: var(--text-dim);">#${p.id.substring(0, 8)}</span>
                </div>
                <div class="card-meta">
                    <p style="font-size: 12px; color: var(--text-dim); margin-bottom: 8px;">
                        ${p.description || "No description."}
                    </p>
                    <span>Created: <strong>${dateStr}</strong></span>
                </div>
                <div class="card-actions">
                    <button class="btn-sm btn-edit" onclick="event.stopPropagation(); openEditProject('${p.id}')">Edit</button>
                    <button class="btn-sm btn-danger" 
                            style="background: #dc3545; color: white; border: none; margin-left: 5px;" 
                            onclick="event.stopPropagation(); deleteProject('${p.id}', '${p.name.replace(/'/g, "\\'")}')">
                        Delete
                    </button>
                </div>
            </div>
        `;
            }).join('');
        }

        async function loadProjects(orgId) {
            try {
                // Fetch projects specifically for the open organization
                const projects = await api('GET', `/organizations/${orgId}/projects`);

                // Save to global state so other functions can access it
                state.projects = projects;

                // Now tell the UI to draw the cards
                renderProjects();
            } catch (e) {
                console.error(e);
                showToast('Error loading projects', 'error');
            }
        }


        async function saveProject() {
            const nameEl = document.getElementById('project-name');
            const name = nameEl.value.trim();

            // Automatically pull from state
            const orgId = state.currentOrgId;

            if (!name) return showModalError('project', 'Project name is required');
            if (!orgId) return showModalError('project', 'Please select an organization first');

            try {
                // Use the nested API path
                const url = `/organizations/${orgId}/projects`;
                await api('POST', url, { name });

                showToast(`Project created in ${state.currentOrgName}`);
                closeModal('project');

                // Reset and Refresh
                nameEl.value = '';
                loadProjects(orgId);
            } catch (e) {
                showModalError('project', e.message);
            }
        }

        function openEditProject(id) {
            const p = state.projects.find(x => x.id === id);
            if (!p) return;

            // Set hidden ID
            document.getElementById('project-edit-id').value = id;

            // Fill inputs
            document.getElementById('project-name').value = p.name;

            // Handle the description field
            const descEl = document.getElementById('project-description');
            if (descEl) descEl.value = p.description || "";

            // Set title and show modal
            document.getElementById('project-modal-title').textContent = 'Edit Project';

            // Update org display
            const displayOrgEl = document.getElementById('display-current-org');
            if (displayOrgEl) displayOrgEl.value = state.currentOrgName || "";

            document.getElementById('modal-project').classList.add('active');
        }

        async function saveProject() {
            const name = document.getElementById('project-name').value.trim();
            const description = document.getElementById('project-description').value.trim();
            const editId = document.getElementById('project-edit-id').value;

            if (!name) return alert("Name is required");

            const method = editId ? 'PUT' : 'POST';
            const url = editId ? `/projects/${editId}` : `/organizations/${state.currentOrgId}/projects`;

            try {
                // Send both name and description
                await api(method, url, { name, description });

                showToast(editId ? "Project updated" : "Project created");
                closeModal('project');
                loadProjects(state.currentOrgId);
            } catch (e) {
                console.error(e);
                alert(e.message);
            }
        }

        async function deleteProject(id, name) {
            if (!confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) {
                return;
            }

            try {
                // Calling your FastAPI DELETE route: /projects/{project_id}
                await api('DELETE', `/projects/${id}`);

                showToast("Project deleted successfully");

                // Refresh the list using the current organization ID in state
                if (state.currentOrgId) {
                    loadProjects(state.currentOrgId);
                }
            } catch (e) {
                console.error("Delete error:", e);
                alert("Failed to delete project: " + e.message);
            }
        }

        // ===================================================
        // TASKS
        // ===================================================
        async function openProjectDetail(projectId) {
    // 1. Find the project in our local state list
            const project = state.projects.find(p => p.id === projectId);
            
            // If the project isn't in state (e.g., after a refresh), 
            // we might need to fetch all projects first.
            if (!project) {
                await loadProjects(state.currentOrgId);
                const refetchedProject = state.projects.find(p => p.id === projectId);
                if (!refetchedProject) return;
            }

            // 2. Update Global State & Browser Memory (Persistence)
            state.currentProjectId = projectId;
            localStorage.setItem('tf_last_project', projectId); 

            // 3. Update UI Header
            const titleEl = document.getElementById('view-project-detail-title');
            const descEl = document.getElementById('view-project-detail-desc');
            
            if (titleEl) titleEl.textContent = project.name;
            if (descEl) descEl.textContent = project.description || "No description provided.";

            // 4. Switch View to the Project Detail board
            showView('project-detail');

            // 5. Loading State: Clear old tasks and show a loader
            state.tasks = [];
            const tasksGrid = document.getElementById('tasks-grid'); // Adjust ID if yours is different
            if (tasksGrid) {
                tasksGrid.innerHTML = '<div class="loader"><div class="spinner"></div></div>';
            }

            // 6. Fetch from FastAPI and Render
            try {
                // This calls: @router.get("/tasks/project/{project_id}")
                const tasks = await api('GET', `/tasks/project/${projectId}`);
                
                state.tasks = tasks || [];
                renderTasks(); // This function draws the Kanban columns/cards
                
            } catch (e) {
                console.error("Failed to load tasks:", e);
                if (tasksGrid) tasksGrid.innerHTML = ''; // Clear loader
                showToast("Error loading tasks. Please try again.", "error");
            }
        }
        async function searchAndAddToOrg() {
            const query = document.getElementById('org-user-search').value;
            const resultsContainer = document.getElementById('org-search-results');
            
            try {
                const users = await api('GET', `/users/search?q=${query}`);
                resultsContainer.innerHTML = users.map(user => `
                    <div class="search-row" style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span>${user.full_name || user.name}</span>
                        <button onclick="addMemberToOrg(${user.id})" class="btn-primary">Add to Org</button>
                    </div>
                `).join('');
            } catch (e) { console.error("Search failed", e); }
        }

        async function addMemberToOrg(targetUserId) {
            try {
                // This hits your /memberships/ endpoint
                await api('POST', '/memberships/', { 
                    user_id: targetUserId, 
                    organization_id: state.currentOrgId, 
                    role: 'member' 
                });
                showToast("User added to Organization!");
                loadOrgs(); // Refresh to show new circles
            } catch (e) { showToast("Error adding member", "error"); }
        }

        async function renderProjectInviteList() {
            const container = document.getElementById('project-invite-list');
            
            // 1. Get everyone in the current Org
            const orgMembers = await api('GET', `/organizations/${state.currentOrgId}/members`);
            
            // 2. Filter out people who are ALREADY in this project
            const candidates = orgMembers.filter(member => 
                !state.currentProjectMembers.some(pm => pm.id === member.id)
            );

            container.innerHTML = candidates.map(user => `
                <div class="member-row" style="display:flex; justify-content:space-between; padding:8px;">
                    <span>${user.full_name}</span>
                    <button onclick="sendInvite(${user.id})" class="btn-small">Add to Project</button>
                </div>
            `).join('');
        }

        function renderCircles(members) {
            if (!members || members.length === 0) return '<span style="color:#6b7280">No members</span>';
            
            const limit = 4;
            const shown = members.slice(0, limit);
            const extra = members.length - limit;

            return `
                <div class="member-group">
                    ${shown.map(m => `
                        <div class="member-circle" title="${m.full_name}">
                            ${initials(m.full_name)}
                        </div>
                    `).join('')}
                    ${extra > 0 ? `<div class="member-circle" style="background:#374151">+${extra}</div>` : ''}
                </div>
            `;
        }

        async function searchUsers() {
            const query = document.getElementById('user-search-input').value;
            const resultsContainer = document.getElementById('search-results');
            
            if (query.length < 2) return;

            try {
                // Matches your @router.get("/search")
                const users = await api('GET', `/users/search?q=${query}`);
                resultsContainer.innerHTML = '';

                users.forEach(user => {
                    const div = document.createElement('div');
                    div.style = "display: flex; justify-content: space-between; align-items: center; background: #374151; padding: 10px; border-radius: 8px;";
                    div.innerHTML = `
                        <span style="color: white;">${user.name} (${user.email})</span>
                        <button onclick="sendInvite(${user.id})" 
                                style="background: #4f46e5; color: white; border: none; padding: 5px 12px; border-radius: 4px; cursor: pointer;">
                            Invite
                        </button>
                    `;
                    resultsContainer.appendChild(div);
                });
            } catch (err) {
                console.error("Search failed", err);
            }
        }

        function initials(name) {
            if (!name) return '?';
            return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        }

        async function sendInvite(targetUserId) {
            if (!state.currentProjectId) {
                showToast("Please select a project first", "error");
                return;
            }

            try {
                // You'll need an endpoint like POST /projects/{id}/invite
                // Sending the targetUserId in the body
                await api('POST', `/projects/${state.currentProjectId}/invite`, { user_id: targetUserId });
                showToast("Invitation sent!", "success");
                document.getElementById('search-results').innerHTML = ''; // Clear results
            } catch (err) {
                showToast("Already invited or error occurred", "error");
            }
        }

        // async function handleInvite(action) {
        //     const overlay = document.getElementById('modal-invite-overlay');
        //     const inviteId = overlay.dataset.inviteId;

        //     try {
        //         // 1. Tell the backend the user accepted
        //         await api('POST', `/users/invitations/${inviteId}/respond?action=${action}`);
                
        //         if (action === 'accepted') {
        //             showToast("Joined project successfully!", "success");
        //             // 2. CRITICAL: Refresh the organizations list so the new org shows up
        //             await loadOrgs(); 
        //             renderOrgs();
        //         } else {
        //             showToast("Invitation declined", "info");
        //         }
        //     } catch (err) {
        //         console.error("Failed to respond:", err);
        //     } finally {
        //         // 3. Always hide the modal to prevent freezing
        //         overlay.style.display = 'none';
        //     }
        // }

        async function saveTask() {
            const title = document.getElementById('task-title').value;
            const projectId = state.currentProjectId; // Must be set when you enter a project view

            if (!title) return showToast("Title is required", "error");
            if (!projectId) return showToast("Project ID is missing", "error");

            // Get the date string from the input
            const dateValue = document.getElementById('task-due-date').value;

            const payload = {
                title: title,
                description: document.getElementById('task-desc').value,
                priority: document.getElementById('task-priority').value,
                status: document.getElementById('task-status-input').value || "Pending",
                project_id: projectId, // Matches your TaskCreate schema
                due_date: dateValue ? new Date(dateValue).toISOString() : null
            };

            try {
                // MATCHING THE ROUTE: /projects/{project_id}/tasks
                const response = await api('POST', `/projects/${projectId}/tasks`, payload);

                showToast("Task created successfully", "success");
                closeTaskModal();

                // Refresh your task list
                if (typeof loadTasks === 'function') loadTasks(projectId);
            } catch (err) {
                console.error("Task Creation Failed:", err);
                showToast("Failed to create task. Check console.", "error");
            }
        }

        async function loadTasks() {
            // Tasks are per-project; we load them from what we create/cache
            state.tasks = JSON.parse(sessionStorage.getItem('tf_tasks') || '[]');
        }

        function saveCachedTasks() {
            sessionStorage.setItem('tf_tasks', JSON.stringify(state.tasks));
        }

        function renderTasks() {
        // 1. Map the status strings to your HTML IDs
        // Since your modal saves status as 'Pending', 'In-Progress', etc., we use those keys.
        const columns = {
            'Pending': document.getElementById('tasks-Pending'),
            'In-Progress': document.getElementById('tasks-In-Progress'),
            'Completed': document.getElementById('tasks-Completed')
        };

        // 2. Clear columns
        Object.values(columns).forEach(col => { if (col) col.innerHTML = ''; });

        // 3. Loop and Append
        (state.tasks || []).forEach(task => {
            const taskHtml = `
                <div class="task-card" 
                    draggable="true" 
                    ondragstart="handleDragStart(event, '${task.id}')"
                    style="background: #131924; padding: 12px; border-radius: 8px; border-left: 4px solid ${getStatusColor(task.status)}; cursor: grab; margin-bottom:10px;">
                    <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color:white;">${task.title}</div>
                    <div style="font-size: 12px; color: #9ca3af; margin-bottom: 10px;">${task.description || ''}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 10px; background: #1f2937; padding: 2px 6px; border-radius: 4px; color:#818cf8;">${task.priority}</span>
                        <button onclick="confirmDeleteTask('${task.id}')" style="background:none; border:none; color:#ef4444; cursor:pointer;">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;

            const column = columns[task.status];
            if (column) {
                column.insertAdjacentHTML('beforeend', taskHtml);
            } else {
                // This will tell you in the F12 console if the name is wrong!
                console.error(`Missing column for status: "${task.status}"`);
            }
        });
    }

        // Ensure this helper exists so colors work
        function getStatusColor(status) {
            if (status === 'Pending') return '#6366f1';
            if (status === 'In-Progress') return '#f59e0b';
            if (status === 'Completed') return '#10b981';
            return '#4b5563';
        }

                // 1. When you start dragging a task card
        function handleDragStart(event, taskId) {
            event.dataTransfer.setData("text/plain", taskId);
            event.target.style.opacity = "0.5";
        }

        // 2. Needed to allow the browser to drop items into columns
        function allowDrop(event) {
            event.preventDefault(); // This is mandatory for drop to work
        }

        // 3. When the task is dropped into a new column
        async function handleDrop(event, newStatus) {
            event.preventDefault();
            const taskId = event.dataTransfer.getData("text/plain");
            
            // Reset opacity
            const draggedEl = document.querySelector(`[data-task-id="${taskId}"]`); 
            if (draggedEl) draggedEl.style.opacity = "1";

            // CALL THE OPTIMISTIC FUNCTION INSTEAD OF WRITING RAW LOGIC HERE
            await updateTaskStatus(taskId, newStatus);
        }
        
        function createTaskCard(task) {
            const priorityColor = task.priority === 'High' ? '#ff6584' : (task.priority === 'Low' ? '#43e97b' : '#ffc850');
            const displayDate = task.due_date ? new Date(task.due_date).toLocaleDateString() : "No date";

            return `
        <div class="task-card" 
             style="background: var(--surface2); 
                    border: 1px solid var(--border); 
                    padding: 16px; 
                    border-radius: 12px; 
                    margin-bottom: 12px; 
                    position: relative; 
                    transition: all 0.2s;">
            
            <button onclick="event.stopPropagation(); confirmDeleteTask('${task.id}')" 
                    title="Delete Task"
                    style="position: absolute; 
                           top: 10px; 
                           right: 10px; 
                           background: rgba(255, 101, 132, 0.1); 
                           border: 1px solid rgba(255, 101, 132, 0.2);
                           color: #ff6584; 
                           width: 26px; 
                           height: 26px; 
                           border-radius: 6px; 
                           cursor: pointer; 
                           display: flex; 
                           align-items: center; 
                           justify-content: center;
                           z-index: 10;">
                <i class="fas fa-trash-alt" style="font-size: 12px;"></i>
            </button>

            <div style="color: ${priorityColor}; font-size: 11px; font-weight: 800; text-transform: uppercase; margin-bottom: 4px;">
                ${task.priority}
            </div>
            
            <div style="font-weight: 600; color: white; margin-bottom: 8px; padding-right: 25px;">
                ${task.title}
            </div>

            <div style="font-size: 12px; color: var(--text-muted);">
                <i class="far fa-calendar" style="margin-right: 5px;"></i> ${displayDate}
            </div>
        </div>
    `;
        }

        // Add the Delete Functionality
        async function deleteTask(taskId) {
            if (!confirm("Are you sure you want to delete this task?")) return;

            try {
                // Replace '/tasks/' with your actual FastAPI endpoint route
                await api('DELETE', `/tasks/${taskId}`);
                showToast("Task deleted", "success");

                // Refresh the current view
                if (state.currentProjectId) {
                    openProjectDetail(state.currentProjectId);
                }
            } catch (err) {
                console.error("Delete Error:", err);
                showToast("Failed to delete task", "error");
            }
        }

        // Helper function to color-code the priority text and border
        function getPriorityColor(priority) {
            switch (priority) {
                case 'High': return '#ef4444';   // Red
                case 'Medium': return '#f59e0b'; // Orange/Amber
                case 'Low': return '#10b981';    // Green
                default: return '#9ca3af';      // Gray
            }
        }
        function openEditTask(id) {
            const t = state.tasks.find(x => x.id === id);
            if (!t) return;
            document.getElementById('task-edit-id').value = id;
            document.getElementById('task-title').value = t.title;
            document.getElementById('task-desc').value = t.description || '';
            populateProjectSelect('task-project');
            document.getElementById('task-project').value = t.project_id;
            document.getElementById('task-priority').value = t.priority || 'Medium';
            document.getElementById('task-status').value = t.status || 'Pending';
            document.getElementById('task-due').value = t.due_date ? t.due_date.slice(0, 16) : '';
            document.getElementById('task-assigned').value = t.assigned_to || '';
            document.getElementById('task-modal-title').textContent = 'Edit Task';
            document.getElementById('modal-task').classList.add('open');
        }

        // 1. Function to open the modal when + is clicked
        /**
 * Opens the task creation modal and pre-fills the status based on the column clicked.
 * @param {string} status - The status of the column ('Pending', 'In Progress', 'Completed')
 */
        // 1. Consolidated Modal Opener
        function openTaskModal(status = 'Pending') {
            const modalOverlay = document.getElementById('modal-task-overlay');

            if (!modalOverlay) {
                console.error("Modal overlay not found in DOM.");
                return;
            }

            // Set the status - this is crucial for your "Sync" to know which column to use
            const statusInput = document.getElementById('task-status-input');
            if (statusInput) {
                statusInput.value = status;
            }

            // Update the UI text
            const modalTitle = document.getElementById('task-modal-title');
            if (modalTitle) {
                modalTitle.textContent = `Create New Task (${status})`;
            }

            // Reset fields for a fresh entry
            const fields = ['task-title', 'task-desc', 'task-due-date'];
            fields.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = "";
            });

            const priorityEl = document.getElementById('task-priority');
            if (priorityEl) priorityEl.value = "Medium";

            // Show the modal
            modalOverlay.classList.add('active');
        }

        // 2. Simple Closer
        function closeTaskModal() {
            document.getElementById('modal-task-overlay').classList.remove('active');
        }

        // 3. Delete Task
        async function deleteTask(taskId) {
            if (!confirm("Are you sure you want to delete this task?")) return;

            try {
                await api('DELETE', `/tasks/${taskId}`);
                showToast("Task deleted", "success");

                if (state.currentProjectId) {
                    openProjectDetail(state.currentProjectId);
                }
            } catch (err) {
                console.error("Delete Error:", err);
                showToast("Failed to delete task", "error");
            }
        }
        // ===================================================
        // COMMENTS
        // ===================================================
        function openCommentModal(taskId) {
            document.getElementById('comment-task-id').value = taskId;
            document.getElementById('comment-content').value = '';
            document.getElementById('modal-comment').classList.add('open');
        }

        async function saveComment() {
            const task_id = parseInt(document.getElementById('comment-task-id').value);
            const content = document.getElementById('comment-content').value.trim();
            if (!content) return showModalError('comment', 'Content is required');
            try {
                await api('POST', '/comments/', { task_id, content });
                closeModal('comment');
                showToast('Comment posted!');
            } catch (e) {
                showModalError('comment', e.message);
            }
        }

        // ===================================================
        // MEMBERS
        // ===================================================
        function renderMembers() {
            const grid = document.getElementById('members-grid');
            if (!state.members.length) {
                grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">👥</div><div class="empty-title">No Members Added</div><div class="empty-sub">Add members to your organizations</div></div>`;
                return;
            }
            grid.innerHTML = state.members.map(m => `
    <div class="card">
      <div class="card-title">User #${m.user_id}</div>
      <div class="card-meta">
        <span>Org #${m.organization_id}</span>
        ${badge(m.role)}
      </div>
    </div>
  `).join('');
        }

        async function saveMember() {
            const user_id = parseInt(document.getElementById('member-user').value);
            const organization_id = parseInt(document.getElementById('member-org').value);
            const role = document.getElementById('member-role').value.trim();
            if (!user_id) return showModalError('member', 'User ID is required');
            if (!organization_id) return showModalError('member', 'Select an organization');
            if (!role) return showModalError('member', 'Role is required');
            try {
                const m = await api('POST', '/memberships/', { user_id, organization_id, role });
                state.members.push(m);
                closeModal('member');
                renderMembers();
                showToast('Member added!');
            } catch (e) {
                showModalError('member', e.message);
            }
        }

        // ===================================================
        // PROFILE
        // ===================================================
        function renderProfile() {
            if (!state.user) return;
            document.getElementById('profile-avatar').textContent = initials(state.user.name);
            document.getElementById('profile-name').value = state.user.name;
            document.getElementById('profile-email').value = state.user.email;
        }

        async function saveProfile() {
            const name = document.getElementById('profile-name').value.trim();
            const password = document.getElementById('profile-pass').value;
            const payload = {};
            if (name) payload.name = name;
            if (password) payload.password = password;
            try {
                const updated = await api('PUT', `/users/${state.user.id}`, payload);
                state.user = updated;
                document.getElementById('nav-avatar').textContent = initials(updated.name);
                document.getElementById('nav-name').textContent = updated.name;
                showToast('Profile saved!');
            } catch (e) {
                showToast(e.message, 'error');
            }
        }

        // ===================================================
        // DASHBOARD
        // ===================================================
        async function renderDashboard() {
            // 1. Update stats and load invitations first
            updateStats();
            await checkInvitations(); // This ensures invites show up regardless of task count

            // 2. Recent tasks logic
            const el = document.getElementById('dash-tasks');
            
            // Safety check for state.tasks
            const tasks = state.tasks || [];
            const recent = [...tasks].slice(-5).reverse();

            if (!recent.length) {
                el.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">✅</div>
                        <div class="empty-title">No Tasks Yet</div>
                        <div class="empty-sub">Go to Tasks to create your first task</div>
                    </div>`;
                return;
            }

            el.innerHTML = `
                <div class="tasks-list">
                    ${recent.map(t => `
                        <div class="task-item">
                            <div class="task-info">
                                <div class="task-title-row">
                                    <span class="task-name">${escHtml(t.title)}</span>
                                    ${badge(t.status)} ${badge(t.priority)}
                                </div>
                                ${t.description ? `<div class="task-desc">${escHtml(t.description)}</div>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>`;
        }

        function updateStats() {
            document.getElementById('stat-orgs').textContent = state.orgs.length;
            document.getElementById('stat-projects').textContent = state.projects.length;
            document.getElementById('stat-tasks').textContent = state.tasks.length;
            document.getElementById('stat-done').textContent = state.tasks.filter(t => t.status === 'Done').length;
        }

        // ===================================================
        // MODAL ERROR
        // ===================================================
        function showModalError(modal, msg) {
            const el = document.getElementById(`${modal}-error`);
            if (!el) return;
            el.textContent = msg;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 4000);
        }

        // ===================================================
        // SECURITY
        // ===================================================
        function escHtml(s) {
            if (!s) return '';
            return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        // ===================================================
        // CLOSE MODALS ON OVERLAY CLICK
        // ===================================================
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', e => {
                if (e.target === overlay) overlay.classList.remove('open');
            });
        });

        // ===================================================
        // INIT
        // ===================================================
        (async function init() {
    // Look for the specific 'tf_' keys you set in doLogout
    const savedToken = localStorage.getItem('tf_token');
    const savedRefresh = localStorage.getItem('tf_refresh');

    if (savedToken) {
        state.token = savedToken;
        state.refreshToken = savedRefresh;
        
        // If you save user object as a string, parse it back
        const savedUser = localStorage.getItem('tf_user');
        if (savedUser) state.user = JSON.parse(savedUser);

        try {
            // Switch UI before loading data for a faster feel
            document.getElementById('auth-screen').style.display = 'none';
            document.getElementById('app').style.display = 'flex';

            await Promise.all([
                loadMyOrganizations(),
                checkInvitations()
            ]);
            
            await loadApp();
            
        } catch (err) {
            console.error("Session expired or invalid:", err);
            doLogout(); 
        }
    } else {
        // No token? Show login
        document.getElementById('app').style.display = 'none';
        document.getElementById('auth-screen').style.display = 'flex';
    }
})();