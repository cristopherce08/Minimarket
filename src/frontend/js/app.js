/**
 * MiniMarket Cloud — Lógica Cliente Frontend (Vanilla JS)
 * Diseñado para integrarse transparentemente con ventas-api (8000) y reportes-api (8001).
 */
 
// ------------------------------------------------------------------
// Configuración de URLs de API
// ------------------------------------------------------------------
const isSameOriginProxy = window.location.port === "8080" || window.location.port === "80";
 
const API_VENTAS_BASE = isSameOriginProxy ? "" : "http://localhost:8000";
const API_REPORTES_BASE = isSameOriginProxy ? "" : "http://localhost:8001";
 
// Estado global de la aplicación
const AppState = {
  currentView: "inicio",
  products: [],
  cart: [], // Array de { product_id, name, price, stock, quantity, subtotal }
  filtroBajoStockActivo: false,
  inventoryFilter: "all",
  backendOnline: false,
};
 
// ------------------------------------------------------------------
// Inicialización
// ------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  checkBackendHealth();
  setInterval(checkBackendHealth, 10000); // Polling cada 10s
  
  const initialHash = window.location.hash.replace("#", "");
  if (["inicio", "productos", "venta", "inventario", "reportes"].includes(initialHash)) {
    navigateTo(initialHash);
  } else {
    loadDashboardData();
  }
});
 
// ------------------------------------------------------------------
// Verificación de Salud de los Microservicios
// ------------------------------------------------------------------
async function checkBackendHealth() {
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
 
  try {
    const res = await fetch(`${API_VENTAS_BASE}/health`, { method: "GET" });
    if (res.ok) {
      dot.className = "status-dot online";
      text.textContent = "Conectado (PostgreSQL)";
      AppState.backendOnline = true;
    } else {
      throw new Error("Estado no OK");
    }
  } catch (err) {
    dot.className = "status-dot offline";
    text.textContent = "Sin conexión al Backend";
    AppState.backendOnline = false;
  }
}
 
// ------------------------------------------------------------------
// Navegación entre Vistas
// ------------------------------------------------------------------
function navigateTo(viewId) {
  AppState.currentView = viewId;
 
  // Actualizar botones de navbar
  document.querySelectorAll(".nav-btn").forEach((btn) => btn.classList.remove("active"));
  const activeBtn = document.getElementById(`nav-${viewId}`);
  if (activeBtn) activeBtn.classList.add("active");
 
  // Mostrar sección activa
  document.querySelectorAll(".view-section").forEach((sec) => sec.classList.remove("active"));
  const activeSec = document.getElementById(`view-${viewId}`);
  if (activeSec) activeSec.classList.add("active");
 
  // Carga reactiva de datos según vista
  switch (viewId) {
    case "inicio":
      loadDashboardData();
      break;
    case "productos":
      loadProducts();
      break;
    case "venta":
      loadPosCatalog();
      break;
    case "inventario":
      loadInventoryView();
      break;
    case "reportes":
      loadReportsView();
      break;
  }
}
 
// ------------------------------------------------------------------
// VISTA 1: Panel General (Inicio)
// ------------------------------------------------------------------
async function loadDashboardData() {
  try {
    // 1. Cargar productos
    const resProds = await fetch(`${API_VENTAS_BASE}/api/v1/productos`);
    if (!resProds.ok) throw new Error("Error al obtener productos");
    const products = await resProds.json();
    AppState.products = products;
 
    // 2. Cargar resumen de inventario
    const resInv = await fetch(`${API_VENTAS_BASE}/api/v1/inventario/resumen`);
    const invData = resInv.ok ? await resInv.json() : null;
 
    // 3. Cargar ventas de hoy desde reportes-api
    let ventasHoy = { total_ventas: 0, total_ingresos: "0.00" };
    try {
      const resRep = await fetch(`${API_REPORTES_BASE}/api/v1/reportes/ventas-hoy`);
      if (resRep.ok) ventasHoy = await resRep.json();
    } catch (_) {}
 
    // Actualizar KPIs
    document.getElementById("kpi-ventas-hoy").textContent = ventasHoy.total_ventas;
    document.getElementById("kpi-ingresos-hoy").textContent = `S/. ${parseFloat(ventasHoy.total_ingresos).toFixed(2)}`;
    document.getElementById("kpi-total-productos").textContent = products.length;
 
    const alertasCount = invData ? (invData.productos_agotados + invData.productos_stock_bajo) : 0;
    document.getElementById("kpi-alertas-stock").textContent = alertasCount;
 
    // Renderizar tabla de alertas críticas
    renderDashboardAlerts(products);
  } catch (err) {
    console.error("Error al cargar dashboard:", err);
    showToast("No se pudo cargar la información del panel.", "error");
  }
}
 
function renderDashboardAlerts(products) {
  const tbody = document.getElementById("tabla-alertas-inicio");
  const critical = products.filter((p) => p.stock <= 5);
 
  if (critical.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state" style="color:var(--primary-green-text); padding:2rem;">🎉 ¡Excelente! Todo el catálogo cuenta con existencias suficientes.</td></tr>`;
    return;
  }
 
  tbody.innerHTML = critical
    .map(
      (p) => `
    <tr>
      <td>#${p.id}</td>
      <td><strong>${escapeHtml(p.name)}</strong></td>
      <td>S/. ${parseFloat(p.price).toFixed(2)}</td>
      <td><span style="font-weight:700; color:${p.stock === 0 ? 'var(--danger-red)' : 'var(--warning-amber)'};">${p.stock} uds.</span></td>
      <td>
        <span class="badge ${p.stock === 0 ? 'badge-red' : 'badge-amber'}">
          ${p.stock === 0 ? 'Agotado' : 'Stock Bajo'}
        </span>
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openProductModal(${p.id})">Editar / Reponer</button>
      </td>
    </tr>
  `
    )
    .join("");
}
 
// ------------------------------------------------------------------
// VISTA 2: Catálogo de Productos
// ------------------------------------------------------------------
async function loadProducts() {
  const tbody = document.getElementById("tabla-productos-body");
  tbody.innerHTML = `<tr><td colspan="6" class="empty-state">Cargando catálogo...</td></tr>`;
 
  try {
    const url = AppState.filtroBajoStockActivo
      ? `${API_VENTAS_BASE}/api/v1/productos?solo_bajo_stock=true`
      : `${API_VENTAS_BASE}/api/v1/productos`;
 
    const res = await fetch(url);
    if (!res.ok) throw new Error("Error al consultar productos");
    const products = await res.json();
    AppState.products = products;
    renderProductsTable(products);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state" style="color:var(--danger-red);">Error al conectar con ventas-api. Comprueba que el microservicio esté en ejecución.</td></tr>`;
  }
}
 
function renderProductsTable(products) {
  const tbody = document.getElementById("tabla-productos-body");
  if (products.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No se encontraron productos registrados.</td></tr>`;
    return;
  }
 
  tbody.innerHTML = products
    .map((p) => {
      let badge = '<span class="badge badge-green">Disponible</span>';
      if (p.stock === 0) {
        badge = '<span class="badge badge-red">Agotado</span>';
      } else if (p.stock <= 5) {
        badge = '<span class="badge badge-amber">Stock Bajo</span>';
      }
 
      return `
      <tr>
        <td>#${p.id}</td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td>S/. ${parseFloat(p.price).toFixed(2)}</td>
        <td><strong>${p.stock}</strong> unidades</td>
        <td>${badge}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openProductModal(${p.id})">✏️ Editar</button>
        </td>
      </tr>
    `;
    })
    .join("");
}
 
function filterProductsTable() {
  const q = document.getElementById("filtro-productos").value.toLowerCase().trim();
  const filtered = AppState.products.filter((p) => p.name.toLowerCase().includes(q));
  renderProductsTable(filtered);
}
 
function toggleFiltroBajoStock() {
  AppState.filtroBajoStockActivo = !AppState.filtroBajoStockActivo;
  const btn = document.getElementById("btn-filtro-bajo-stock");
  if (AppState.filtroBajoStockActivo) {
    btn.classList.add("btn-primary");
    btn.classList.remove("btn-secondary");
  } else {
    btn.classList.remove("btn-primary");
    btn.classList.add("btn-secondary");
  }
  loadProducts();
}
 
// Modal Crear/Editar Producto
function openProductModal(productId = null) {
  const modal = document.getElementById("modal-producto");
  const title = document.getElementById("modal-producto-title");
  const form = document.getElementById("form-producto");
  form.reset();
 
  if (productId) {
    title.textContent = "Editar Producto Existente";
    const prod = AppState.products.find((p) => p.id === productId);
    if (prod) {
      document.getElementById("prod-id").value = prod.id;
      document.getElementById("prod-nombre").value = prod.name;
      document.getElementById("prod-precio").value = parseFloat(prod.price).toFixed(2);
      document.getElementById("prod-stock").value = prod.stock;
    }
  } else {
    title.textContent = "Registrar Nuevo Producto";
    document.getElementById("prod-id").value = "";
  }
 
  modal.classList.add("active");
}
 
function closeProductModal() {
  document.getElementById("modal-producto").classList.remove("active");
}
 
async function saveProduct(event) {
  event.preventDefault();
  const id = document.getElementById("prod-id").value;
  const name = document.getElementById("prod-nombre").value.trim();
  const price = parseFloat(document.getElementById("prod-precio").value);
  const stock = parseInt(document.getElementById("prod-stock").value, 10);
 
  if (!name || isNaN(price) || price <= 0 || isNaN(stock) || stock < 0) {
    showToast("Por favor revisa los datos ingresados.", "warning");
    return;
  }
 
  const payload = { name, price, stock };
  const btn = document.getElementById("btn-save-product");
  btn.disabled = true;
  btn.textContent = "Guardando...";
 
  try {
    let res;
    if (id) {
      res = await fetch(`${API_VENTAS_BASE}/api/v1/productos/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      res = await fetch(`${API_VENTAS_BASE}/api/v1/productos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }
 
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Error al procesar producto");
    }
 
    showToast(`Producto '${name}' guardado correctamente.`, "success");
    closeProductModal();
    loadProducts();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Guardar Producto";
  }
}
 
// ------------------------------------------------------------------
// VISTA 3: Punto de Venta (Nueva Venta)
// ------------------------------------------------------------------
async function loadPosCatalog() {
  const container = document.getElementById("pos-catalog-grid");
  container.innerHTML = `<div class="empty-state">Cargando catálogo...</div>`;
 
  try {
    const res = await fetch(`${API_VENTAS_BASE}/api/v1/productos`);
    if (!res.ok) throw new Error("Error al obtener catálogo");
    const products = await res.json();
    AppState.products = products;
    renderPosCatalog(products);
    renderCart();
  } catch (err) {
    container.innerHTML = `<div class="empty-state" style="color:var(--danger-red);">Error al cargar productos para venta.</div>`;
  }
}
 
function renderPosCatalog(products) {
  const container = document.getElementById("pos-catalog-grid");
  if (products.length === 0) {
    container.innerHTML = `<div class="empty-state">No hay productos en catálogo.</div>`;
    return;
  }
 
  container.innerHTML = products
    .map((p) => {
      const isOut = p.stock === 0;
      return `
      <div class="product-item-card ${isOut ? 'disabled' : ''}" onclick="${isOut ? '' : `addToCart(${p.id})`}">
        <div>
          <h4 style="font-size:0.95rem; font-weight:700; margin-bottom:0.25rem;">${escapeHtml(p.name)}</h4>
          <span style="font-size:0.8rem; color:var(--text-muted);">Stock: <strong>${p.stock}</strong> uds.</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.75rem;">
          <span style="font-size:1.05rem; font-weight:700; color:var(--primary-green);">S/. ${parseFloat(p.price).toFixed(2)}</span>
          <button class="btn ${isOut ? 'btn-secondary' : 'btn-primary'} btn-sm" ${isOut ? 'disabled' : ''}>
            ${isOut ? 'Agotado' : '+ Agregar'}
          </button>
        </div>
      </div>
    `;
    })
    .join("");
}
 
function filterPosCatalog() {
  const q = document.getElementById("pos-search-input").value.toLowerCase().trim();
  const filtered = AppState.products.filter((p) => p.name.toLowerCase().includes(q));
  renderPosCatalog(filtered);
}
 
function addToCart(productId) {
  const product = AppState.products.find((p) => p.id === productId);
  if (!product || product.stock <= 0) {
    showToast("Este producto no cuenta con existencias disponibles.", "warning");
    return;
  }
 
  const existingItem = AppState.cart.find((item) => item.product_id === productId);
  if (existingItem) {
    if (existingItem.quantity + 1 > product.stock) {
      showToast(`No puedes superar el stock disponible (${product.stock} uds).`, "warning");
      return;
    }
    existingItem.quantity += 1;
    existingItem.subtotal = roundMoney(existingItem.quantity * existingItem.price);
  } else {
    AppState.cart.push({
      product_id: product.id,
      name: product.name,
      price: parseFloat(product.price),
      stock: product.stock,
      quantity: 1,
      subtotal: roundMoney(parseFloat(product.price)),
    });
  }
 
  renderCart();
}
 
function updateCartQty(productId, delta) {
  const item = AppState.cart.find((i) => i.product_id === productId);
  if (!item) return;
 
  const newQty = item.quantity + delta;
  if (newQty <= 0) {
    removeFromCart(productId);
    return;
  }
 
  if (newQty > item.stock) {
    showToast(`Stock máximo alcanzado (${item.stock} uds).`, "warning");
    return;
  }
 
  item.quantity = newQty;
  item.subtotal = roundMoney(item.quantity * item.price);
  renderCart();
}
 
function removeFromCart(productId) {
  AppState.cart = AppState.cart.filter((i) => i.product_id !== productId);
  renderCart();
}
 
function clearCart() {
  AppState.cart = [];
  renderCart();
}
 
function renderCart() {
  const container = document.getElementById("cart-items-container");
  const totalElem = document.getElementById("cart-total-amount");
 
  if (AppState.cart.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="padding:2.5rem 0;">
        <div class="empty-state-icon">🛒</div>
        <p>El carrito está vacío.<br>Haz clic en los productos para agregarlos.</p>
      </div>
    `;
    totalElem.textContent = "S/. 0.00";
    return;
  }
 
  let total = 0;
  container.innerHTML = AppState.cart
    .map((item) => {
      total += item.subtotal;
      return `
      <div class="cart-item-row">
        <div style="flex-grow:1; padding-right:0.5rem;">
          <strong style="font-size:0.9rem;">${escapeHtml(item.name)}</strong>
          <div style="font-size:0.8rem; color:var(--text-muted);">
            S/. ${item.price.toFixed(2)} c/u
          </div>
        </div>
 
        <div class="cart-qty-ctrl">
          <button class="cart-qty-btn" onclick="updateCartQty(${item.product_id}, -1)">-</button>
          <span style="font-weight:700; min-width:24px; text-align:center;">${item.quantity}</span>
          <button class="cart-qty-btn" onclick="updateCartQty(${item.product_id}, 1)">+</button>
        </div>
 
        <div style="min-width:75px; text-align:right; font-weight:700; color:var(--primary-green);">
          S/. ${item.subtotal.toFixed(2)}
        </div>
 
        <button onclick="removeFromCart(${item.product_id})" style="background:none; border:none; color:var(--danger-red); cursor:pointer; margin-left:0.5rem; font-size:1.1rem;">✕</button>
      </div>
    `;
    })
    .join("");
 
  totalElem.textContent = `S/. ${total.toFixed(2)}`;
}
 
async function submitSale() {
  if (AppState.cart.length === 0) {
    showToast("Agrega al menos un producto al carrito antes de confirmar.", "warning");
    return;
  }
 
  const btn = document.getElementById("btn-confirm-sale");
  btn.disabled = true;
  btn.textContent = "Procesando transacción atómica...";
 
  const payload = {
    items: AppState.cart.map((i) => ({
      product_id: i.product_id,
      quantity: i.quantity,
    })),
  };
 
  try {
    const res = await fetch(`${API_VENTAS_BASE}/api/v1/ventas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
 
    const data = await res.json();
 
    if (!res.ok) {
      throw new Error(data.detail || "Error al procesar la venta en base de datos");
    }
 
    // Venta exitosa
    showTicketModal(data);
    clearCart();
    loadPosCatalog(); // Recarga catálogo con stock actualizado inmediatamente
    showToast("Venta completada e inventario actualizado.", "success");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "✅ Confirmar y Registrar Venta";
  }
}
 
function showTicketModal(sale) {
  const modal = document.getElementById("modal-ticket");
  const body = document.getElementById("ticket-modal-body");
 
  const fechaFormat = new Date(sale.created_at).toLocaleString("es-PE");
 
  body.innerHTML = `
    <div style="font-family:monospace; font-size:0.88rem; background:#f8fafc; padding:1rem; border-radius:6px; border:1px solid #e2e8f0;">
      <div style="text-align:center; border-bottom:1px dashed #cbd5e1; padding-bottom:0.75rem; margin-bottom:0.75rem;">
        <h4 style="font-size:1.1rem; margin:0;">BODEGA MINIMARKET CLOUD</h4>
        <p style="margin:0.2rem 0; color:#64748b;">Comprobante de Venta Electrónica</p>
        <p style="margin:0; font-weight:700;">Ticket N°: #${sale.id.toString().padStart(6, '0')}</p>
        <p style="margin:0; color:#64748b; font-size:0.78rem;">Fecha: ${fechaFormat}</p>
      </div>
 
      <table style="width:100%; border-collapse:collapse; margin-bottom:0.75rem; font-size:0.85rem;">
        <thead>
          <tr style="border-bottom:1px solid #cbd5e1;">
            <th style="padding:0.3rem 0; text-align:left;">Cant.</th>
            <th style="padding:0.3rem 0; text-align:left;">Producto</th>
            <th style="padding:0.3rem 0; text-align:right;">P.Unit</th>
            <th style="padding:0.3rem 0; text-align:right;">Total</th>
          </tr>
        </thead>
        <tbody>
          ${sale.items
            .map(
              (it) => `
            <tr>
              <td style="padding:0.25rem 0;">${it.quantity}</td>
              <td style="padding:0.25rem 0;">${escapeHtml(it.product_name)}</td>
              <td style="padding:0.25rem 0; text-align:right;">S/. ${parseFloat(it.unit_price).toFixed(2)}</td>
              <td style="padding:0.25rem 0; text-align:right; font-weight:700;">S/. ${parseFloat(it.subtotal).toFixed(2)}</td>
            </tr>
          `
            )
            .join("")}
        </tbody>
      </table>
 
      <div style="border-top:1px dashed #cbd5e1; padding-top:0.75rem; display:flex; justify-content:space-between; font-size:1.15rem; font-weight:700; color:var(--primary-green);">
        <span>TOTAL COBRADO:</span>
        <span>S/. ${parseFloat(sale.total).toFixed(2)}</span>
      </div>
      <p style="text-align:center; margin-top:0.75rem; font-size:0.75rem; color:#64748b;">
        ¡Gracias por su compra en MiniMarket Cloud!
      </p>
    </div>
  `;
 
  modal.classList.add("active");
}
 
function closeTicketModal() {
  document.getElementById("modal-ticket").classList.remove("active");
}
 
// ------------------------------------------------------------------
// VISTA 4: Control de Inventario
// ------------------------------------------------------------------
async function loadInventoryView() {
  try {
    const resInv = await fetch(`${API_VENTAS_BASE}/api/v1/inventario/resumen`);
    if (!resInv.ok) throw new Error("Error al obtener resumen");
    const inv = await resInv.json();
 
    document.getElementById("inv-total-unidades").textContent = inv.total_unidades_en_stock;
    document.getElementById("inv-productos-disponibles").textContent =
      inv.total_productos - (inv.productos_agotados + inv.productos_stock_bajo);
    document.getElementById("inv-stock-bajo").textContent = inv.productos_stock_bajo;
    document.getElementById("inv-productos-agotados").textContent = inv.productos_agotados;
 
    // Obtener catálogo completo para la tabla detallada
    const resProds = await fetch(`${API_VENTAS_BASE}/api/v1/productos`);
    const prods = await resProds.json();
    AppState.products = prods;
 
    renderInventoryTable(filterInventoryData(prods, AppState.inventoryFilter));
  } catch (err) {
    showToast("No se pudo sincronizar el inventario desde PostgreSQL.", "error");
  }
}
 
function filterInventory(category) {
  AppState.inventoryFilter = category;
  ["all", "available", "low", "out"].forEach((c) => {
    const btn = document.getElementById(`btn-inv-filter-${c}`);
    if (btn) {
      if (c === category) {
        btn.classList.add("btn-primary");
        btn.classList.remove("btn-secondary");
      } else {
        btn.classList.remove("btn-primary");
        btn.classList.add("btn-secondary");
      }
    }
  });
 
  renderInventoryTable(filterInventoryData(AppState.products, category));
}
 
function filterInventoryData(products, filter) {
  switch (filter) {
    case "available":
      return products.filter((p) => p.stock > 5);
    case "low":
      return products.filter((p) => p.stock > 0 && p.stock <= 5);
    case "out":
      return products.filter((p) => p.stock === 0);
    default:
      return products;
  }
}
 
function renderInventoryTable(products) {
  const tbody = document.getElementById("tabla-inventario-body");
  if (products.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No hay registros para este filtro.</td></tr>`;
    return;
  }
 
  tbody.innerHTML = products
    .map((p) => {
      let badge = '<span class="badge badge-green">Saludable</span>';
      if (p.stock === 0) badge = '<span class="badge badge-red">Agotado</span>';
      else if (p.stock <= 5) badge = '<span class="badge badge-amber">Crítico</span>';
 
      return `
      <tr>
        <td>#${p.id}</td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td>S/. ${parseFloat(p.price).toFixed(2)}</td>
        <td><strong>${p.stock}</strong> unidades</td>
        <td>${badge}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="openProductModal(${p.id})">Reponer Stock</button>
        </td>
      </tr>
    `;
    })
    .join("");
}
 
function searchInventoryTable() {
  const q = document.getElementById("filtro-inventario").value.toLowerCase().trim();
  const subset = filterInventoryData(AppState.products, AppState.inventoryFilter);
  const filtered = subset.filter((p) => p.name.toLowerCase().includes(q));
  renderInventoryTable(filtered);
}
 
// ------------------------------------------------------------------
// VISTA 5: Reportes y Estadísticas
// ------------------------------------------------------------------
async function loadReportsView() {
  loadSparkResults();
  try {
    // 1. Reporte ventas hoy
    const resHoy = await fetch(`${API_REPORTES_BASE}/api/v1/reportes/ventas-hoy`);
    if (resHoy.ok) {
      const hoy = await resHoy.json();
      document.getElementById("rep-ingresos-hoy").textContent = `S/. ${parseFloat(hoy.total_ingresos).toFixed(2)}`;
      document.getElementById("rep-ventas-hoy-count").textContent = `${hoy.total_ventas} transacciones registradas hoy`;
      document.getElementById("rep-ticket-promedio").textContent = `S/. ${parseFloat(hoy.ticket_promedio).toFixed(2)}`;
    }
 
    // 2. Resumen general histórico
    const resGen = await fetch(`${API_REPORTES_BASE}/api/v1/reportes/resumen-general`);
    if (resGen.ok) {
      const gen = await resGen.json();
      document.getElementById("rep-ventas-historicas").textContent = gen.total_ventas_historicas;
      document.getElementById("rep-ingresos-historicos").textContent = `Total Acumulado: S/. ${parseFloat(
        gen.ingresos_totales_historicos
      ).toFixed(2)}`;
    }
 
    // 3. Productos más vendidos
    const resTop = await fetch(`${API_REPORTES_BASE}/api/v1/reportes/productos-top?limite=5`);
    const topTbody = document.getElementById("tabla-top-productos");
    if (resTop.ok) {
      const topItems = await resTop.json();
      if (topItems.length === 0) {
        topTbody.innerHTML = `<tr><td colspan="4" class="empty-state">Aún no se registran ventas para generar el ranking.</td></tr>`;
      } else {
        topTbody.innerHTML = topItems
          .map(
            (it) => `
          <tr>
            <td><strong>#${it.ranking}</strong></td>
            <td>${escapeHtml(it.product_name)}</td>
            <td><strong>${it.unidades_vendidas}</strong> uds.</td>
            <td style="color:var(--primary-green); font-weight:700;">S/. ${parseFloat(it.total_recaudado).toFixed(2)}</td>
          </tr>
        `
          )
          .join("");
      }
    }
 
    // 4. Ventas agrupadas por día
    const resDias = await fetch(`${API_REPORTES_BASE}/api/v1/reportes/ventas-agrupadas-dia?dias=7`);
    const diasTbody = document.getElementById("tabla-ventas-dias");
    if (resDias.ok) {
      const dias = await resDias.json();
      if (dias.length === 0) {
        diasTbody.innerHTML = `<tr><td colspan="3" class="empty-state">Sin ventas registradas en el periodo.</td></tr>`;
      } else {
        diasTbody.innerHTML = dias
          .map(
            (d) => `
          <tr>
            <td>${d.fecha}</td>
            <td><strong>${d.numero_ventas}</strong> ventas</td>
            <td style="color:var(--primary-green); font-weight:700;">S/. ${parseFloat(d.total_ingresos).toFixed(2)}</td>
          </tr>
        `
          )
          .join("");
      }
    }
  } catch (err) {
    showToast("Error al cargar reportes analíticos.", "error");
  }
}
 
// ------------------------------------------------------------------
// Resultados del procesamiento distribuido con Apache Spark
// ------------------------------------------------------------------
function formatMoneySpark(value) {
  return `S/. ${parseFloat(value).toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
 
function mostrarSparkVacio(mensaje) {
  document.getElementById("spark-contenido").style.display = "none";
  document.getElementById("spark-badge").style.display = "none";
  document.getElementById("spark-vacio").style.display = "block";
  document.getElementById("spark-vacio-texto").textContent = mensaje;
}
 
async function loadSparkResults() {
  try {
    const res = await fetch(`${API_REPORTES_BASE}/api/v1/reportes/spark?limite=10&dias=30`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
 
    if (!data.disponible) {
      mostrarSparkVacio("Aún no hay resultados de Spark. Ejecuta el job ventas-spark en Kubernetes.");
      return;
    }
 
    document.getElementById("spark-contenido").style.display = "block";
    document.getElementById("spark-badge").style.display = "";
    document.getElementById("spark-vacio").style.display = "none";
 
    document.getElementById("spark-total-ventas").textContent = Number(data.resumen.total_ventas).toLocaleString("es-PE");
    document.getElementById("spark-ingresos").textContent = formatMoneySpark(data.resumen.ingresos_totales);
    document.getElementById("spark-total-productos").textContent = data.resumen.total_productos;
 
    const procesado = new Date(data.procesado_en);
    document.getElementById("spark-procesado-en").textContent = isNaN(procesado)
      ? "Procesado con Spark"
      : `Procesado: ${procesado.toLocaleString("es-PE", { timeZone: "America/Lima" })}`;
 
    document.getElementById("spark-tabla-top").innerHTML = data.productos_top
      .map(
        (it) => `
      <tr>
        <td><strong>#${it.ranking}</strong></td>
        <td>${escapeHtml(it.product_name)}</td>
        <td><strong>${Number(it.unidades_vendidas).toLocaleString("es-PE")}</strong> uds.</td>
        <td style="color:var(--primary-green); font-weight:700;">${formatMoneySpark(it.total_recaudado)}</td>
      </tr>`
      )
      .join("");
 
    document.getElementById("spark-tabla-dias").innerHTML = data.ventas_por_dia
      .map(
        (d) => `
      <tr>
        <td>${escapeHtml(d.fecha)}</td>
        <td><strong>${Number(d.numero_ventas).toLocaleString("es-PE")}</strong> ventas</td>
        <td style="color:var(--primary-green); font-weight:700;">${formatMoneySpark(d.total_ingresos)}</td>
      </tr>`
      )
      .join("");
  } catch (err) {
    mostrarSparkVacio("No se pudieron cargar los resultados de Spark.");
    showToast("Error al cargar los resultados de Spark.", "error");
  }
}
 
// ------------------------------------------------------------------
// Utilidades UI (Toast, escapeHtml, roundMoney)
// ------------------------------------------------------------------
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
 
  const icon = type === "error" ? "❌" : type === "warning" ? "⚠️" : "✅";
  toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
 
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
 
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
 
function roundMoney(num) {
  return Math.round((num + Number.EPSILON) * 100) / 100;
}
 