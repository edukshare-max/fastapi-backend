// ============================================
// SASU Admin Panel - JavaScript
// ============================================

// Configuración
const API_BASE_URL = 'https://fastapi-backend-o7ks.onrender.com';
let authToken = null;
let currentUser = null;

// ============================================
// GESTIÓN DE AUTENTICACIÓN
// ============================================

// Verificar si hay sesión activa al cargar
document.addEventListener('DOMContentLoaded', () => {
    authToken = localStorage.getItem('auth_token');
    const userData = localStorage.getItem('user_data');
    
    if (authToken && userData) {
        try {
            currentUser = JSON.parse(userData);
            showDashboard();
        } catch (e) {
            showLogin();
        }
    } else {
        showLogin();
    }
});

function showLogin() {
    document.getElementById('login-screen').classList.add('active');
    document.getElementById('dashboard-screen').classList.remove('active');
}

function showDashboard() {
    document.getElementById('login-screen').classList.remove('active');
    document.getElementById('dashboard-screen').classList.add('active');
    
    // Actualizar UI con info del usuario
    updateUserInfo();
    
    // Cargar vista inicial (usuarios)
    showView('users');
}

function updateUserInfo() {
    if (!currentUser) return;
    
    document.getElementById('user-name').textContent = currentUser.nombre_completo;
    document.getElementById('user-role').textContent = getRoleLabel(currentUser.rol);
    document.getElementById('user-campus').textContent = getCampusLabel(currentUser.campus);
    
    // Iniciales para avatar
    const initials = currentUser.nombre_completo
        .split(' ')
        .map(n => n[0])
        .join('')
        .substring(0, 2)
        .toUpperCase();
    document.getElementById('user-initials').textContent = initials;
}

// ============================================
// LOGIN
// ============================================

document.getElementById('login-btn').addEventListener('click', async () => {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const campus = document.getElementById('login-campus').value;
    
    if (!username || !password) {
        showError('login-error', 'Por favor complete todos los campos');
        return;
    }
    
    const btn = document.getElementById('login-btn');
    const spinner = btn.querySelector('.spinner');
    const span = btn.querySelector('span');
    
    btn.disabled = true;
    spinner.style.display = 'block';
    span.style.display = 'none';
    hideError('login-error');
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, campus })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error al iniciar sesión');
        }
        
        const data = await response.json();
        
        // Verificar que sea admin
        if (data.user.rol !== 'admin') {
            throw new Error('Solo administradores pueden acceder al panel');
        }
        
        // Guardar sesión
        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('auth_token', authToken);
        localStorage.setItem('user_data', JSON.stringify(currentUser));
        
        // Mostrar dashboard
        showDashboard();
        
    } catch (error) {
        showError('login-error', error.message);
    } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
        span.style.display = 'block';
    }
});

// Enter para login
document.getElementById('login-password').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('login-btn').click();
    }
});

// ============================================
// LOGOUT
// ============================================

document.getElementById('logout-btn').addEventListener('click', () => {
    if (confirm('¿Está seguro que desea cerrar sesión?')) {
        authToken = null;
        currentUser = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
        showLogin();
    }
});

// ============================================
// NAVEGACIÓN ENTRE VISTAS
// ============================================

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const view = item.dataset.view;
        showView(view);
        
        // Actualizar navegación activa
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
    });
});

function showView(viewName) {
    // Ocultar todas las vistas
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    
    // Mostrar la vista seleccionada
    document.getElementById(`${viewName}-view`).classList.add('active');
    
    // Cargar datos según la vista
    if (viewName === 'users') {
        loadUsers();
    } else if (viewName === 'audit') {
        loadAuditLogs();
    } else if (viewName === 'settings') {
        loadSettings();
    }
}

// ============================================
// GESTIÓN DE USUARIOS
// ============================================

async function loadUsers() {
    const loading = document.getElementById('users-loading');
    const tableContainer = document.getElementById('users-table-container');
    const empty = document.getElementById('users-empty');
    
    loading.style.display = 'block';
    tableContainer.style.display = 'none';
    empty.style.display = 'none';
    
    try {
        const campus = document.getElementById('filter-campus').value;
        const rol = document.getElementById('filter-role').value;
        
        let url = `${API_BASE_URL}/auth/users?`;
        if (campus) url += `campus=${campus}&`;
        if (rol) url += `rol=${rol}&`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Error al cargar usuarios');
        
        const users = await response.json();
        
        if (users.length === 0) {
            empty.style.display = 'block';
        } else {
            renderUsersTable(users);
            tableContainer.style.display = 'block';
        }
        
    } catch (error) {
        alert('Error al cargar usuarios: ' + error.message);
    } finally {
        loading.style.display = 'none';
    }
}

function renderUsersTable(users) {
    const tbody = document.getElementById('users-tbody');
    tbody.innerHTML = '';
    
    users.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${user.username}</strong></td>
            <td>${user.nombre_completo}</td>
            <td><span class="badge badge-primary">${getRoleLabel(user.rol)}</span></td>
            <td>${getCampusLabel(user.campus)}</td>
            <td>${user.departamento}</td>
            <td>
                <span class="badge ${user.activo ? 'badge-success' : 'badge-danger'}">
                    ${user.activo ? '✓ Activo' : '✗ Inactivo'}
                </span>
            </td>
            <td>${formatDate(user.ultimo_acceso)}</td>
            <td>
                <button class="btn-icon" onclick="editUser('${user.id}')" title="Editar">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
                <button class="btn-icon" onclick="toggleUserStatus('${user.id}', ${user.activo})" title="${user.activo ? 'Desactivar' : 'Activar'}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${user.activo ? 
                            '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>' :
                            '<polyline points="20 6 9 17 4 12"></polyline>'
                        }
                    </svg>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    // Aplicar búsqueda en tiempo real
    applyUserSearch();
}

// Filtros y búsqueda
document.getElementById('user-search').addEventListener('input', applyUserSearch);
document.getElementById('filter-campus').addEventListener('change', loadUsers);
document.getElementById('filter-role').addEventListener('change', loadUsers);
document.getElementById('refresh-users-btn').addEventListener('click', loadUsers);

function applyUserSearch() {
    const searchTerm = document.getElementById('user-search').value.toLowerCase();
    const rows = document.querySelectorAll('#users-tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

// ============================================
// CREAR/EDITAR USUARIO
// ============================================

document.getElementById('new-user-btn').addEventListener('click', () => {
    openUserModal();
});

function openUserModal(userId = null) {
    const modal = document.getElementById('user-modal');
    const form = document.getElementById('user-form');
    const title = document.getElementById('modal-title');
    const passwordSection = document.getElementById('password-section');
    
    // Limpiar formulario y estado
    form.reset();
    delete form.dataset.editingUserId;
    document.getElementById('form-username').disabled = false;
    hideError('form-error');
    
    if (userId) {
        title.textContent = 'Editar Usuario';
        passwordSection.style.display = 'none';
        document.getElementById('form-password').removeAttribute('required');
        // La función editUser() llenará los datos
    } else {
        title.textContent = 'Nuevo Usuario';
        passwordSection.style.display = 'block';
        document.getElementById('form-password').setAttribute('required', 'required');
    }
    
    modal.classList.add('active');
}

function closeUserModal() {
    document.getElementById('user-modal').classList.remove('active');
}

// Cerrar modal al hacer clic fuera
document.getElementById('user-modal').addEventListener('click', (e) => {
    if (e.target.id === 'user-modal') {
        closeUserModal();
    }
});

document.getElementById('user-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const form = e.target;
    const isEditing = form.dataset.editingUserId;
    
    const formData = {
        email: document.getElementById('form-email').value.trim(),
        nombre_completo: document.getElementById('form-nombre').value.trim(),
        rol: document.getElementById('form-rol').value,
        campus: document.getElementById('form-campus').value,
        departamento: document.getElementById('form-departamento').value.trim()
    };
    
    // Si no estamos editando, agregar username y password
    if (!isEditing) {
        formData.username = document.getElementById('form-username').value.trim();
        formData.password = document.getElementById('form-password').value;
    }
    
    // Validaciones
    if ((!isEditing && !formData.username) || !formData.email || !formData.nombre_completo || 
        !formData.rol || !formData.departamento) {
        showError('form-error', 'Todos los campos son obligatorios');
        return;
    }
    
    if (!isEditing && formData.password && formData.password.length < 8) {
        showError('form-error', 'La contraseña debe tener al menos 8 caracteres');
        return;
    }
    
    const btn = e.target.querySelector('button[type="submit"]');
    const spinner = btn.querySelector('.spinner');
    const span = btn.querySelector('span');
    
    btn.disabled = true;
    spinner.style.display = 'block';
    span.style.display = 'none';
    hideError('form-error');
    
    try {
        let response;
        
        if (isEditing) {
            // Editar usuario existente
            response = await fetch(`${API_BASE_URL}/auth/users/${isEditing}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(formData)
            });
        } else {
            // Crear nuevo usuario
            response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(formData)
            });
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Error al ${isEditing ? 'actualizar' : 'crear'} usuario`);
        }
        
        // Limpiar estado de edición
        delete form.dataset.editingUserId;
        document.getElementById('form-username').disabled = false;
        
        // Cerrar modal y recargar usuarios
        closeUserModal();
        loadUsers();
        
        // Mensaje de éxito
        alert(`✓ Usuario ${isEditing ? 'actualizado' : 'creado'} exitosamente`);
        
    } catch (error) {
        showError('form-error', error.message);
    } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
        span.style.display = 'block';
    }
});

async function toggleUserStatus(userId, currentStatus) {
    const action = currentStatus ? 'desactivar' : 'activar';
    if (!confirm(`¿Está seguro que desea ${action} este usuario?`)) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/users/${userId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ activo: !currentStatus })
        });
        
        if (!response.ok) throw new Error('Error al actualizar usuario');
        
        loadUsers();
        alert(`✓ Usuario ${action} correctamente`);
        
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function editUser(userId) {
    try {
        // Cargar datos del usuario
        const response = await fetch(`${API_BASE_URL}/auth/users`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Error al cargar usuario');
        
        const users = await response.json();
        const user = users.find(u => u.id === userId);
        
        if (!user) {
            alert('Usuario no encontrado');
            return;
        }
        
        // Abrir modal y pre-llenar formulario
        const modal = document.getElementById('user-modal');
        const form = document.getElementById('user-form');
        const title = document.getElementById('modal-title');
        const passwordSection = document.getElementById('password-section');
        
        title.textContent = 'Editar Usuario';
        passwordSection.style.display = 'none';
        document.getElementById('form-password').removeAttribute('required');
        
        // Llenar campos
        document.getElementById('form-username').value = user.username;
        document.getElementById('form-username').disabled = true; // No se puede cambiar username
        document.getElementById('form-email').value = user.email;
        document.getElementById('form-nombre').value = user.nombre_completo;
        document.getElementById('form-rol').value = user.rol;
        document.getElementById('form-campus').value = user.campus;
        document.getElementById('form-departamento').value = user.departamento;
        
        // Guardar userId en el formulario para saber que estamos editando
        form.dataset.editingUserId = userId;
        
        modal.classList.add('active');
        
    } catch (error) {
        alert('Error al cargar usuario: ' + error.message);
    }
}

// ============================================
// AUDITORÍA
// ============================================

async function loadAuditLogs() {
    const loading = document.getElementById('audit-loading');
    const tableContainer = document.getElementById('audit-table-container');
    
    loading.style.display = 'block';
    tableContainer.style.display = 'none';
    
    try {
        const usuario = document.getElementById('audit-search').value.trim();
        const accion = document.getElementById('filter-action').value;
        
        let url = `${API_BASE_URL}/auth/audit-logs?limit=100`;
        if (usuario) url += `&usuario=${usuario}`;
        if (accion) url += `&accion=${accion}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Error al cargar logs');
        
        const logs = await response.json();
        renderAuditTable(logs);
        tableContainer.style.display = 'block';
        
    } catch (error) {
        alert('Error al cargar auditoría: ' + error.message);
    } finally {
        loading.style.display = 'none';
    }
}

function renderAuditTable(logs) {
    const tbody = document.getElementById('audit-tbody');
    tbody.innerHTML = '';
    
    logs.forEach(log => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDateTime(log.timestamp)}</td>
            <td><strong>${log.usuario}</strong></td>
            <td><span class="badge badge-info">${log.accion}</span></td>
            <td>${log.recurso || '-'}</td>
            <td>${log.detalles || '-'}</td>
            <td>${log.ip || '-'}</td>
        `;
        tbody.appendChild(tr);
    });
}

document.getElementById('audit-search').addEventListener('input', () => {
    clearTimeout(window.auditSearchTimeout);
    window.auditSearchTimeout = setTimeout(loadAuditLogs, 500);
});

document.getElementById('filter-action').addEventListener('change', loadAuditLogs);
document.getElementById('refresh-audit-btn').addEventListener('click', loadAuditLogs);

document.getElementById('export-audit-btn').addEventListener('click', () => {
    const table = document.getElementById('audit-table');
    const rows = Array.from(table.querySelectorAll('tr'));
    
    const csv = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        return cells.map(cell => `"${cell.textContent.trim()}"`).join(',');
    }).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `auditoria-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
});

// ============================================
// CONFIGURACIÓN
// ============================================

async function loadSettings() {
    document.getElementById('api-url').textContent = API_BASE_URL;
    
    try {
        // Cargar estadísticas
        const usersResponse = await fetch(`${API_BASE_URL}/auth/users`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const users = await usersResponse.json();
        document.getElementById('total-users').textContent = users.length;
        
        const auditResponse = await fetch(`${API_BASE_URL}/auth/audit-logs?limit=1000`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const audit = await auditResponse.json();
        document.getElementById('total-audit').textContent = audit.length;
        
    } catch (error) {
        console.error('Error al cargar estadísticas:', error);
    }
}

document.getElementById('clear-cache-btn').addEventListener('click', () => {
    if (confirm('¿Está seguro que desea limpiar el caché local?')) {
        localStorage.clear();
        alert('Caché limpiado. Por favor inicie sesión nuevamente.');
        showLogin();
    }
});

// ============================================
// UTILIDADES
// ============================================

function showError(elementId, message) {
    const errorDiv = document.getElementById(elementId);
    errorDiv.textContent = message;
    errorDiv.classList.add('show');
    errorDiv.style.display = 'block';
}

function hideError(elementId) {
    const errorDiv = document.getElementById(elementId);
    errorDiv.classList.remove('show');
    errorDiv.style.display = 'none';
}

function getRoleLabel(rol) {
    const labels = {
        'admin': 'Administrador',
        'medico': 'Médico',
        'nutricion': 'Nutrición',
        'psicologia': 'Psicología',
        'odontologia': 'Odontología',
        'enfermeria': 'Enfermería',
        'recepcion': 'Recepción',
        'servicios_estudiantiles': 'Servicios Estudiantiles',
        'lectura': 'Solo Lectura'
    };
    return labels[rol] || rol;
}

function getCampusLabel(campus) {
    const labels = {
        'llano-largo': 'Llano Largo',
        'acapulco': 'Acapulco',
        'chilpancingo': 'Chilpancingo',
        'taxco': 'Taxco',
        'iguala': 'Iguala',
        'zihuatanejo': 'Zihuatanejo'
    };
    return labels[campus] || campus;
}

function formatDate(dateString) {
    if (!dateString) return 'Nunca';
    const date = new Date(dateString);
    return date.toLocaleDateString('es-MX', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('es-MX', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

console.log('✅ SASU Admin Panel cargado correctamente');
console.log('🔐 API:', API_BASE_URL);
