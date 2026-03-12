
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

        function handleDragStart(event, taskId) {
            // Store the ID of the task being dragged
            event.dataTransfer.setData("taskId", taskId);
        }

        function allowDrop(event) {
            // Necessary to allow a drop
            event.preventDefault();
        }

        async function handleDrop(event, newStatus) {
            event.preventDefault();
            const taskId = event.dataTransfer.getData("taskId");

            // 1. Find the task in local state
            const task = state.tasks.find(t => t.id === taskId);
            if (!task || task.status === newStatus) return;

            // 2. Optimistic Update: Update UI immediately for "Pro" feel
            const oldStatus = task.status;
            task.status = newStatus;
            renderTasks();

            try {
                // 3. API Call to update status in FastAPI backend
                const response = await fetch(`/tasks/${taskId}/status`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify({ status: newStatus })
                });

                if (!response.ok) throw new Error("Failed to update status");

                showToast(`Moved to ${newStatus}`, 'success');
            } catch (error) {
                // Rollback if server fails
                task.status = oldStatus;
                renderTasks();
                showToast('Sync failed. Task moved back.', 'error');
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
            const data = await res.json();
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
            state.token = null;
            state.refreshToken = null;
            state.user = null;
            localStorage.removeItem('tf_token');
            localStorage.removeItem('tf_refresh');
            document.getElementById('app').style.display = 'none';
            document.getElementById('auth-screen').style.display = 'flex';
        }

        // ===================================================
        // LOAD APP
        // ===================================================
        
        async function loadApp() {
            try {
                state.user = await api('GET', '/auth/me');
            } catch {
                doLogout(); return;
            }
            document.getElementById('auth-screen').style.display = 'none';
            document.getElementById('app').style.display = 'flex';

            // Set nav user info
            document.getElementById('nav-avatar').textContent = initials(state.user.name);
            document.getElementById('nav-name').textContent = state.user.name;

            // Load ONLY the organizations first
            await loadOrgs();
            const savedProjectId = localStorage.getItem('tf_last_project');
            if (savedProjectId) {
                await openProjectDetail(savedProjectId);
            } else {
                showView('dashboard');
                renderDashboard();
            }
        }

        // ===================================================
        // VIEWS
        // ===================================================
        function showView(name) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(`view-${name}`).classList.add('active');
            event.target.classList.add('active');
            if (name === 'dashboard') renderDashboard();
            if (name === 'orgs') renderOrgs();
            if (name === 'projects') renderProjects();
            if (name === 'tasks') renderTasks();
            if (name === 'members') renderMembers();
            if (name === 'profile') renderProfile();
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

                // 3. Escape strings for the onclick event to prevent errors with quotes
                const escapedName = o.name.replace(/'/g, "\\'");
                const escapedDesc = (o.description || "").replace(/'/g, "\\'");

                return `
            <div class="card" 
                 onclick="enterOrganization('${o.id}', '${escapedName}', '${escapedDesc}')" 
                 style="cursor:pointer">
                
                <div class="card-title">
                    ${o.name}
                    <span style="font-size: 10px; color: var(--text-dim);">#${o.id.substring(0, 8)}</span>
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
            const columns = {
                'Pending': document.getElementById('tasks-pending'),
                'In-Progress': document.getElementById('tasks-progress'),
                'Completed': document.getElementById('tasks-completed')
            };

            Object.values(columns).forEach(col => { if (col) col.innerHTML = ''; });

            (state.tasks || []).forEach(task => {
                const taskHtml = `
            <div class="task-card" 
                 draggable="true" 
                 ondragstart="handleDragStart(event, '${task.id}')"
                 style="background: #131924; padding: 12px; border-radius: 8px; border-left: 4px solid ${getStatusColor(task.status)}; cursor: grab;">
                <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">${task.title}</div>
                <div style="font-size: 12px; color: #9ca3af; margin-bottom: 10px;">${task.description || ''}</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 10px; background: #1f2937; padding: 2px 6px; border-radius: 4px;">${task.priority}</span>
                    <button class="btn-sm" onclick="deleteTask('${task.id}', '${task.title}')" style="background:none; border:none; color:#ef4444; cursor:pointer;">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;

                const column = columns[task.status];
                if (column) column.insertAdjacentHTML('beforeend', taskHtml);
            });
        }

        function getStatusColor(status) {
            switch (status) {
                case 'Pending': return '#9ca3af';
                case 'In-Progress': return '#fbbf24';
                case 'Completed': return '#10b981';
                default: return '#4f46e5';
            }
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
        function renderDashboard() {
            updateStats();
            // Recent tasks
            const el = document.getElementById('dash-tasks');
            const recent = [...state.tasks].slice(-5).reverse();
            if (!recent.length) {
                el.innerHTML = `<div class="empty-state"><div class="empty-icon">✅</div><div class="empty-title">No Tasks Yet</div><div class="empty-sub">Go to Tasks to create your first task</div></div>`;
                return;
            }
            el.innerHTML = `<div class="tasks-list">${recent.map(t => `
    <div class="task-item">
      <div class="task-info">
        <div class="task-title-row">
          <span class="task-name">${escHtml(t.title)}</span>
          ${badge(t.status)} ${badge(t.priority)}
        </div>
        ${t.description ? `<div class="task-desc">${escHtml(t.description)}</div>` : ''}
      </div>
    </div>
  `).join('')}</div>`;
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
            if (state.token) {
                await loadApp();
            }
        })();
