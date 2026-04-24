const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const state = {
  projects: [],
  downloads: [],
  providers: [],
  translations: [],
  activeProject: null,
  currentTab: "projects",
};

// ---------- API helpers ----------
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data && data.detail) msg = data.detail;
    } catch (_) {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

const toast = (msg) => {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), 2400);
};

// ---------- Tabs ----------
$$(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const name = tab.dataset.tab;
    $$(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    $$(".view").forEach((v) =>
      v.classList.toggle("hidden", v.dataset.view !== name)
    );
    state.currentTab = name;
    if (name === "projects") refreshProjects();
    if (name === "downloads") refreshDownloads();
    if (name === "translate") refreshTranslations();
    if (name === "providers") refreshProviders();
  });
});

// ---------- Projects ----------
async function refreshProjects() {
  state.projects = await api("/api/projects");
  renderProjects();
  populateProjectSelectors();
}

function renderProjects() {
  const list = $("#project-list");
  if (!state.projects.length) {
    list.innerHTML = `<p class="hint">Chưa có dự án nào. Bấm "+ Dự án mới" để tạo.</p>`;
    return;
  }
  list.innerHTML = state.projects
    .map(
      (p) => `
    <article class="card" data-id="${p.id}">
      <h3>${escapeHtml(p.title)}</h3>
      <div class="meta">
        ${p.source_language || "?"} → ${p.target_language || "?"}
        · ${new Date(p.updated_at).toLocaleDateString()}
      </div>
      ${p.description ? `<div class="meta">${escapeHtml(p.description)}</div>` : ""}
      ${p.provider ? `<span class="lang-pair">${p.provider}</span>` : ""}
      <div class="actions">
        <button class="btn small" data-act="edit">Sửa</button>
        <button class="btn small" data-act="download">Tải</button>
        <button class="btn small" data-act="translate">Dịch</button>
        <button class="btn small danger" data-act="delete">Xóa</button>
      </div>
    </article>`
    )
    .join("");

  list.querySelectorAll(".card").forEach((card) => {
    const id = Number(card.dataset.id);
    card.querySelector('[data-act="edit"]').onclick = () => openProjectDialog(id);
    card.querySelector('[data-act="delete"]').onclick = async () => {
      if (!confirm("Xóa dự án này?")) return;
      await api(`/api/projects/${id}`, { method: "DELETE" });
      toast("Đã xóa");
      refreshProjects();
    };
    card.querySelector('[data-act="translate"]').onclick = () => {
      state.activeProject = id;
      switchTab("translate");
      $("#translate-project").value = String(id);
      refreshTranslations();
    };
    card.querySelector('[data-act="download"]').onclick = () => {
      state.activeProject = id;
      openDownloadDialog(id);
    };
  });
}

function populateProjectSelectors() {
  const options =
    `<option value="">-- chọn dự án --</option>` +
    state.projects.map((p) => `<option value="${p.id}">${escapeHtml(p.title)}</option>`).join("");
  $("#translate-project").innerHTML = options;
  const dl = $("#form-download [name=project_id]");
  dl.innerHTML = state.projects
    .map((p) => `<option value="${p.id}">${escapeHtml(p.title)}</option>`)
    .join("");
  if (state.activeProject) dl.value = String(state.activeProject);
}

// ---------- Project dialog ----------
$("#btn-new-project").onclick = () => openProjectDialog(null);

async function openProjectDialog(id) {
  const dlg = $("#dialog-project");
  const form = $("#form-project");
  $("#project-dialog-title").textContent = id ? "Sửa dự án" : "Dự án mới";
  form.reset();

  const providerSelect = form.querySelector('[name=provider]');
  providerSelect.innerHTML =
    `<option value="">-- auto --</option>` +
    state.providers
      .map((p) => `<option value="${p.key}">${p.name}${p.enabled ? "" : " (chưa bật)"}</option>`)
      .join("");

  if (id) {
    const p = state.projects.find((x) => x.id === id);
    if (p) {
      for (const key of [
        "title",
        "description",
        "source_url",
        "source_language",
        "target_language",
        "provider",
      ]) {
        if (form.elements[key] && p[key] != null) form.elements[key].value = p[key];
      }
    }
  }

  dlg.returnValue = "";
  dlg.showModal();
  dlg.addEventListener(
    "close",
    async () => {
      if (dlg.returnValue !== "ok") return;
      const data = Object.fromEntries(new FormData(form));
      for (const k of Object.keys(data)) if (data[k] === "") data[k] = null;
      try {
        if (id) {
          await api(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) });
        } else {
          await api("/api/projects", { method: "POST", body: JSON.stringify(data) });
        }
        toast("Đã lưu");
        refreshProjects();
      } catch (e) {
        toast("Lỗi: " + e.message);
      }
    },
    { once: true }
  );
}

// ---------- Downloads ----------
$("#btn-new-download").onclick = () => openDownloadDialog(null);

async function openDownloadDialog(projectId) {
  if (!state.projects.length) {
    toast("Hãy tạo một dự án trước.");
    return;
  }
  const dlg = $("#dialog-download");
  const form = $("#form-download");
  form.reset();

  const provSelect = form.querySelector('[name=provider]');
  provSelect.innerHTML =
    `<option value="">-- auto --</option>` +
    state.providers
      .map((p) => `<option value="${p.key}">${p.name}${p.enabled ? "" : " (chưa bật)"}</option>`)
      .join("");

  if (projectId) form.elements.project_id.value = String(projectId);

  dlg.returnValue = "";
  dlg.showModal();
  dlg.addEventListener(
    "close",
    async () => {
      if (dlg.returnValue !== "ok") return;
      const data = Object.fromEntries(new FormData(form));
      data.project_id = Number(data.project_id);
      if (!data.provider) delete data.provider;
      try {
        await api("/api/downloads", { method: "POST", body: JSON.stringify(data) });
        toast("Đã thêm vào hàng chờ");
        switchTab("downloads");
        refreshDownloads();
      } catch (e) {
        toast("Lỗi: " + e.message);
      }
    },
    { once: true }
  );
}

async function refreshDownloads() {
  state.downloads = await api("/api/downloads");
  renderDownloads();
}

function renderDownloads() {
  const list = $("#download-list");
  if (!state.downloads.length) {
    list.innerHTML = `<p class="hint">Chưa có bản tải nào.</p>`;
    return;
  }
  list.innerHTML = state.downloads
    .map((d) => {
      const project = state.projects.find((p) => p.id === d.project_id);
      const pct = Math.round((d.progress || 0) * 100);
      return `
      <div class="download-item" data-id="${d.id}">
        <div class="row1">
          <div>
            <div class="title">${escapeHtml(project ? project.title : "?")}</div>
            <div class="meta">${escapeHtml(d.url)}</div>
          </div>
          <span class="status ${d.status}">${d.status}</span>
        </div>
        <div class="progress"><span style="width:${pct}%"></span></div>
        <div class="meta">${pct}%${d.file_size ? " · " + fmtBytes(d.file_size) : ""} · ${d.provider}</div>
        ${d.error_message ? `<div class="error">${escapeHtml(d.error_message)}</div>` : ""}
        <div class="actions">
          ${d.status === "completed" ? `<a class="btn small primary" href="/api/downloads/${d.id}/file" download>Lưu về máy</a>` : ""}
          ${["pending", "downloading"].includes(d.status) ? `<button class="btn small" data-act="cancel">Huỷ</button>` : ""}
          ${["failed", "cancelled"].includes(d.status) ? `<button class="btn small" data-act="retry">Thử lại</button>` : ""}
          <button class="btn small danger" data-act="delete">Xóa</button>
        </div>
      </div>`;
    })
    .join("");

  list.querySelectorAll(".download-item").forEach((item) => {
    const id = Number(item.dataset.id);
    const cancel = item.querySelector('[data-act="cancel"]');
    const retry = item.querySelector('[data-act="retry"]');
    const del = item.querySelector('[data-act="delete"]');
    if (cancel)
      cancel.onclick = async () => {
        await api(`/api/downloads/${id}/cancel`, { method: "POST" });
        refreshDownloads();
      };
    if (retry)
      retry.onclick = async () => {
        await api(`/api/downloads/${id}/retry`, { method: "POST" });
        refreshDownloads();
      };
    if (del)
      del.onclick = async () => {
        if (!confirm("Xóa bản tải này?")) return;
        await api(`/api/downloads/${id}`, { method: "DELETE" });
        refreshDownloads();
      };
  });
}

// poll while on downloads tab
setInterval(() => {
  if (state.currentTab === "downloads") refreshDownloads();
}, 2000);

// ---------- Translations ----------
$("#translate-project").addEventListener("change", (e) => {
  state.activeProject = e.target.value ? Number(e.target.value) : null;
  refreshTranslations();
});

$("#btn-add-line").onclick = async () => {
  if (!state.activeProject) {
    toast("Chọn một dự án trước.");
    return;
  }
  await api("/api/translations", {
    method: "POST",
    body: JSON.stringify({
      project_id: state.activeProject,
      order_index: state.translations.length,
    }),
  });
  refreshTranslations();
};

$("#btn-export-srt").onclick = async () => {
  if (!state.activeProject) return toast("Chọn dự án.");
  const url = `/api/translations/export/srt?project_id=${state.activeProject}`;
  const a = document.createElement("a");
  a.href = url;
  a.download = `project-${state.activeProject}.srt`;
  a.click();
};

async function refreshTranslations() {
  if (!state.activeProject) {
    $("#translation-list").innerHTML = `<p class="hint">Chọn một dự án để bắt đầu dịch.</p>`;
    state.translations = [];
    return;
  }
  state.translations = await api(
    `/api/translations?project_id=${state.activeProject}`
  );
  renderTranslations();
}

function renderTranslations() {
  const list = $("#translation-list");
  if (!state.translations.length) {
    list.innerHTML = `<p class="hint">Chưa có dòng dịch. Bấm "+ Dòng dịch".</p>`;
    return;
  }
  list.innerHTML = state.translations
    .map(
      (t, i) => `
    <div class="translation-row" data-id="${t.id}">
      <div class="time">
        <input type="number" step="0.1" data-field="start_time" value="${t.start_time ?? ""}" placeholder="bắt đầu (s)" />
        <input type="number" step="0.1" data-field="end_time" value="${t.end_time ?? ""}" placeholder="kết thúc (s)" />
        <select data-field="status">
          ${["draft","in_progress","reviewing","completed"].map((s)=>`<option value="${s}" ${t.status===s?"selected":""}>${s}</option>`).join("")}
        </select>
      </div>
      <textarea data-field="source_text" rows="2" placeholder="Lời thoại gốc...">${escapeHtml(t.source_text || "")}</textarea>
      <textarea data-field="translated_text" rows="2" placeholder="Bản dịch...">${escapeHtml(t.translated_text || "")}</textarea>
      <div class="col-actions">
        <button class="btn small" data-act="save">Lưu</button>
        <button class="btn small danger" data-act="del">Xóa</button>
      </div>
    </div>`
    )
    .join("");

  list.querySelectorAll(".translation-row").forEach((row) => {
    const id = Number(row.dataset.id);
    row.querySelector('[data-act="save"]').onclick = async () => {
      const payload = {};
      row.querySelectorAll("[data-field]").forEach((el) => {
        const k = el.dataset.field;
        let v = el.value;
        if (k === "start_time" || k === "end_time") v = v === "" ? null : Number(v);
        payload[k] = v;
      });
      await api(`/api/translations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      toast("Đã lưu dòng dịch");
    };
    row.querySelector('[data-act="del"]').onclick = async () => {
      if (!confirm("Xóa dòng này?")) return;
      await api(`/api/translations/${id}`, { method: "DELETE" });
      refreshTranslations();
    };
  });
}

// ---------- Providers ----------
async function refreshProviders() {
  state.providers = await api("/api/downloads/providers");
  const list = $("#provider-list");
  list.innerHTML = state.providers
    .map(
      (p) => `
    <div class="provider-card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <h3>${escapeHtml(p.name)}</h3>
        <span class="badge ${p.enabled ? "on" : "off"}">${p.enabled ? "sẵn sàng" : "chưa bật"}</span>
      </div>
      <p>${escapeHtml(p.description || "")}</p>
      <div class="meta" style="margin-top:8px;color:var(--muted);font-size:12px;">key: <code>${p.key}</code></div>
    </div>`
    )
    .join("");
}

// ---------- Utils ----------
function switchTab(name) {
  const tab = $$(".tab").find((t) => t.dataset.tab === name);
  if (tab) tab.click();
}

function escapeHtml(str) {
  if (str == null) return "";
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

function fmtBytes(n) {
  if (!n) return "";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(1)} ${units[i]}`;
}

// ---------- PWA ----------
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

// ---------- Boot ----------
(async function boot() {
  try {
    await refreshProviders();
    await refreshProjects();
  } catch (e) {
    toast("Không kết nối được server: " + e.message);
  }
})();
