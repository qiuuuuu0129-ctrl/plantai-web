// static/js/app.js
window.$ = (sel)=> document.querySelector(sel);

async function getJSON(url) { const r = await fetch(url); return r.json(); }
async function postJSON(url, data) {
  const r = await fetch(url, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data||{})});
  return r.json();
}

window.addEventListener("DOMContentLoaded", async ()=>{
  const themeSelect = $("#themeSelect");
  if (themeSelect) {
    themeSelect.addEventListener("change", async ()=>{
      await postJSON("/api/settings", { theme: themeSelect.value });
      document.documentElement.setAttribute("data-theme", themeSelect.value);
    });
  }

  switch (location.pathname) {
    case "/": initDashboard(); break;
    case "/history": initHistory(); break;
    case "/control": initControl(); break;
    case "/camera": initCamera(); break;
    case "/settings": initSettings(); break;
    case "/reports": initReports(); break;
  }
});

// ========== 仪表盘 ==========
let miniChart;
async function initDashboard() {
  const ctx = $("#miniChart").getContext("2d");
  miniChart = new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [
      { label: "温度°C", data: [], borderColor:"#ff6b6b", tension:0.2 },
      { label: "湿度%", data: [], borderColor:"#4dabf7", tension:0.2 },
      { label: "光照lux", data: [], borderColor:"#ffd43b", tension:0.2, yAxisID:'y1' },
      { label: "土壤湿度%", data: [], borderColor:"#69db7c", tension:0.2 }
    ]},
    options:{ responsive:true, maintainAspectRatio:false, scales:{
      y: { beginAtZero:true, position:'left'},
      y1:{ beginAtZero:true, position:'right', grid:{drawOnChartArea:false}}
    }, plugins:{ legend:{ position:'bottom' } } }
  });

  const refresh = async ()=>{
    const d = await getJSON("/api/sensors");
    $("#cards").innerHTML = `
      <div class="card">🌡 温度 <b>${fmt(d.temperature_c)}℃</b></div>
      <div class="card">💧 湿度 <b>${fmt(d.humidity_pct)}%</b></div>
      <div class="card">💡 光照 <b>${fmt(d.light_lux)} lux</b></div>
      <div class="card">🌱 土壤 <b>${fmt(d.soil_moisture_pct)}%</b></div>
      <div class="card">🟩 CO₂ <b>${fmt(d.eCO2_ppm)}</b></div>
      <div class="card">🟦 TVOC <b>${fmt(d.TVOC_ppb)}</b></div>
    `;
    $("#lastUpdate").textContent = "最近刷新：" + new Date().toLocaleString();

    const t = new Date((d.timestamp || Date.now()/1000)*1000).toLocaleTimeString();
    miniChart.data.labels.push(t);
    miniChart.data.datasets[0].data.push(d.temperature_c||0);
    miniChart.data.datasets[1].data.push(d.humidity_pct||0);
    miniChart.data.datasets[2].data.push(d.light_lux||0);
    miniChart.data.datasets[3].data.push(d.soil_moisture_pct||0);
    if (miniChart.data.labels.length>60){ miniChart.data.labels.shift(); miniChart.data.datasets.forEach(ds=>ds.data.shift()); }
    miniChart.update();
  };

  await refresh();
  setInterval(refresh, 5000);
}

function fmt(v){
  if (v===null || v===undefined) return "--";
  const n=Number(v); return isFinite(n)? n.toFixed(1) : "--";
}

// ========== 历史 ==========
let historyChart;
async function initHistory() {
  const ctx = $("#historyChart").getContext("2d");
  historyChart = new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [
      { label: "温度°C", data: [], borderColor:"#ff6b6b", tension:0.2 },
      { label: "湿度%", data: [], borderColor:"#4dabf7", tension:0.2 },
      { label: "光照lux", data: [], borderColor:"#ffd43b", tension:0.2 },
      { label: "土壤湿度%", data: [], borderColor:"#69db7c", tension:0.2 }
    ]},
    options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{position:'bottom'} } }
  });

  const fetchHistory = async ()=>{
    const s = $("#since").value, u = $("#until").value;
    const qs = []; if (s) qs.push("since="+s); if(u) qs.push("until="+u);
    const url = "/api/history" + (qs.length? "?"+qs.join("&"):"");
    const res = await getJSON(url);
    const items = res.items || [];

    const tbody = $("#histTable tbody");
    tbody.innerHTML = "";
    items.forEach(r=>{
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r["时间"]||""}</td>
        <td>${r["温度°C"]||""}</td>
        <td>${r["湿度%"]||""}</td>
        <td>${r["光照lux"]||""}</td>
        <td>${r["CO₂ ppm"]||""}</td>
        <td>${r["TVOC ppb"]||""}</td>
        <td>${r["土壤湿度%"]||""}</td>
      `;
      tbody.appendChild(tr);
    });

    historyChart.data.labels = items.map(i=>i["时间"]);
    historyChart.data.datasets[0].data = items.map(i=> Number(i["温度°C"]||0));
    historyChart.data.datasets[1].data = items.map(i=> Number(i["湿度%"]||0));
    historyChart.data.datasets[2].data = items.map(i=> Number(i["光照lux"]||0));
    historyChart.data.datasets[3].data = items.map(i=> Number(i["土壤湿度%"]||0));
    historyChart.update();
  };

  $("#btnQuery").addEventListener("click", fetchHistory);
  $("#btnPdf").addEventListener("click", ()=>{
    const s = $("#since").value, u = $("#until").value;
    const qs = []; if (s) qs.push("since="+s); if(u) qs.push("until="+u);
    const url = "/api/reports/pdf"+(qs.length? "?"+qs.join("&"):"");
    window.open(url, "_blank");
  });
  await fetchHistory();
}

// ========== 控制 ==========
async function initControl() {
  window.sendControl = async (payload)=>{
    const r = await postJSON("/api/control", payload);
    $("#ctrlResult").innerHTML = `<pre>${escapeHtml(JSON.stringify(r,null,2))}</pre>`;
  };
}
function escapeHtml(s){ return (s||"").replace(/[<>&"]/g, c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c])); }

// ========== 摄像头 ==========
async function initCamera() {
  $("#btnStart").addEventListener("click", async ()=>{
    const r = await getJSON("/camera/start");
    if (r.ok) $("#stream").src = "/video_feed?ts="+Date.now();
    else alert("启动失败："+(r.error||""));
  });
  $("#btnStop").addEventListener("click", async ()=>{
    await getJSON("/camera/stop");
    $("#stream").src = "";
  });
}

// ========== 设置 ==========
async function initSettings() {
  const cfg = await getJSON("/api/settings");
  $("#setTheme").value = cfg.theme || "auto";
  $("#setInterval").value = cfg.log_interval_min || 30;

  const ac = cfg.auto_control || {};
  $("#acEnabled").value = String(!!ac.enabled);
  $("#acQuiet").value = (ac.quiet_hours||[23,7]).join(",");
  $("#acSoil").value = ac.soil_low_threshold || 35;
  $("#acPump").value = ac.pump_duration_s || 3;
  $("#acLux").value = ac.light_target_lux || 350;
  $("#acBri").value = ac.normal_light_brightness || 70;
  const ws = ac.ws2812 || {};
  $("#acWsEn").value = String(!!ws.enabled);
  $("#acWsMode").value = ws.mode || "white";
  $("#acWsBri").value = ws.brightness || 128;
  $("#acWsDur").value = ws.duration_s || 10;

  $("#btnSaveBasic").addEventListener("click", async ()=>{
    const r = await postJSON("/api/settings", {
      theme: $("#setTheme").value,
      log_interval_min: Number($("#setInterval").value)
    });
    $("#saveResult").innerHTML = `<pre>${escapeHtml(JSON.stringify(r,null,2))}</pre>`;
  });

  $("#btnSaveAC").addEventListener("click", async ()=>{
    const quiet = $("#acQuiet").value.split(",").map(x=> Number(x.trim())).filter(x=> !isNaN(x));
    const r = await postJSON("/api/settings", {
      auto_control: {
        enabled: $("#acEnabled").value==="true",
        quiet_hours: quiet.length===2? quiet : [23,7],
        soil_low_threshold: Number($("#acSoil").value),
        pump_duration_s: Number($("#acPump").value),
        light_target_lux: Number($("#acLux").value),
        normal_light_brightness: Number($("#acBri").value),
        ws2812: {
          enabled: $("#acWsEn").value==="true",
          mode: $("#acWsMode").value,
          brightness: Number($("#acWsBri").value),
          duration_s: Number($("#acWsDur").value)
        }
      }
    });
    $("#saveResult").innerHTML = `<pre>${escapeHtml(JSON.stringify(r,null,2))}</pre>`;
  });
}
