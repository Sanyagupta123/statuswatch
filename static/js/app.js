const $ = (selector) => document.querySelector(selector);
const monitorList = $('#monitor-list');
const incidentList = $('#incident-list');
const addDialog = $('#add-dialog');
const detailDialog = $('#detail-dialog');
let chart;

function esc(value) { return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function timeAgo(value) {
  if (!value) return 'No checks yet';
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}
function showBanner(message, kind='error') { const el=$('#banner'); el.textContent=message; el.className=`banner ${kind}`; el.hidden=false; setTimeout(()=>{el.hidden=true;},5000); }
async function api(path, options={}) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json'}, ...options});
  const payload = await response.json().catch(()=>({}));
  if (!response.ok) throw new Error(payload.error?.message || 'The request could not be completed.');
  return payload;
}
async function loadDashboard() {
  try {
    const {monitors, summary} = await api('/api/monitors');
    $('#total-count').textContent=summary.total; $('#online-count').textContent=summary.online;
    $('#down-count').textContent=summary.down; $('#incident-count').textContent=summary.open_incidents;
    $('#nav-count').textContent=summary.total; $('#monitor-heading-count').textContent=summary.total;
    if (!monitors.length) monitorList.innerHTML='<div class="empty-state"><strong>No monitors yet</strong>Add an endpoint to start collecting real check history.</div>';
    else monitorList.innerHTML=monitors.map(m=>{
      const state=m.latest_success===null?'unknown':m.latest_success?'up':'down';
      const label=state==='unknown'?'Pending':state==='up'?'Operational':'Failing';
      return `<article class="monitor-row"><span class="status-indicator ${state}"></span><div class="monitor-info"><div class="monitor-name">${esc(m.name)}</div><div class="monitor-url">${esc(m.url)}</div></div><div class="monitor-meta"><span class="status-badge ${state}">${label}</span><div class="latency">${m.latest_latency_ms==null?'—':`${Math.round(m.latest_latency_ms)} ms`}</div></div><div class="row-actions"><button class="small-button" data-check="${m.id}">Check now</button><button class="small-button" data-details="${m.id}">Details</button></div></article>`;
    }).join('');
    const incidents=[];
    for (const monitor of monitors) {
      const result=await api(`/api/monitors/${monitor.id}/incidents`);
      for (const incident of result.incidents) incidents.push({...incident,monitor_name:monitor.name});
    }
    incidents.sort((a,b)=>new Date(b.started_at)-new Date(a.started_at));
    const latest=incidents.slice(0,10);
    incidentList.innerHTML=latest.length?latest.map(i=>`<div class="incident-row"><span class="incident-symbol ${i.resolved_at?'recovered':''}">${i.resolved_at?'✓':'!'}</span><div class="incident-body"><div class="incident-title">${esc(i.monitor_name)} ${i.resolved_at?'recovered':'went down'}</div><div class="incident-detail">${esc(i.reason)}</div></div><div class="incident-time">${timeAgo(i.resolved_at||i.started_at)}</div></div>`).join(''):'<div class="empty-state"><strong>No incidents recorded</strong>Recovery and outage events will appear here.</div>';
  } catch (error) { monitorList.innerHTML='<div class="empty-state">Could not load monitors.</div>'; showBanner(error.message); }
}
monitorList.addEventListener('click',async event=>{
  const check=event.target.closest('[data-check]'); const details=event.target.closest('[data-details]');
  try { if(check){check.disabled=true;check.textContent='Checking…';await api(`/api/monitors/${check.dataset.check}/check`,{method:'POST'});showBanner('Health check completed.','success');await loadDashboard();}
    if(details) await showDetails(Number(details.dataset.details)); }
  catch(error){showBanner(error.message);} finally {if(check){check.disabled=false;check.textContent='Check now';}}
});
async function showDetails(id) {
  const [{monitors},{analytics},{checks}] = await Promise.all([api('/api/monitors'),api(`/api/monitors/${id}/analytics`),api(`/api/monitors/${id}/checks`)]);
  const monitor=monitors.find(item=>item.id===id); if(!monitor) return;
  $('#detail-title').textContent=monitor.name; $('#detail-url').textContent=monitor.url;
  const a=analytics.analytics;
  $('#detail-metrics').innerHTML=`<div class="detail-metric"><span>Sampled success rate</span><strong>${a.sampled_success_rate_percent==null?'—':`${a.sampled_success_rate_percent}%`}</strong></div><div class="detail-metric"><span>Avg successful latency</span><strong>${a.latency_ms.average==null?'—':`${a.latency_ms.average} ms`}</strong></div><div class="detail-metric"><span>Minimum latency</span><strong>${a.latency_ms.minimum==null?'—':`${a.latency_ms.minimum} ms`}</strong></div><div class="detail-metric"><span>Maximum latency</span><strong>${a.latency_ms.maximum==null?'—':`${a.latency_ms.maximum} ms`}</strong></div>`;
  const points=[...checks.checks].reverse(); $('#detail-checks').innerHTML=points.length?points.slice(-20).reverse().map(c=>`<div class="check-row"><span class="${c.success?'pass':'fail'}">${c.success?'PASS':'FAIL'} · ${c.status_code??c.error??'Network error'}</span><span>${esc(new Date(c.checked_at).toLocaleString())}</span><span>${c.latency_ms==null?'—':`${c.latency_ms} ms`}</span></div>`).join(''):'<div class="empty-state">No checks have run yet.</div>';
  if(chart) chart.destroy();
  if(window.Chart) chart=new Chart($('#latency-chart'),{type:'line',data:{labels:points.map(c=>new Date(c.checked_at).toLocaleTimeString()),datasets:[{label:'Response time (ms)',data:points.map(c=>c.success?c.latency_ms:null),borderColor:'#9b8cff',backgroundColor:'#9b8cff22',fill:true,tension:.35,spanGaps:false,pointRadius:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#aab6c9',font:{size:10}}}},scales:{x:{ticks:{color:'#8290a8',maxTicksLimit:8},grid:{color:'#202b3d'}},y:{beginAtZero:true,ticks:{color:'#8290a8'},grid:{color:'#202b3d'}}}}});
  detailDialog.showModal();
}
$('#add-open').addEventListener('click',()=>addDialog.showModal()); $('#add-close').addEventListener('click',()=>addDialog.close()); $('#detail-close').addEventListener('click',()=>detailDialog.close());
$('#refresh-button').addEventListener('click',loadDashboard);
$('#add-form').addEventListener('submit',async event=>{event.preventDefault();const error=$('#form-error');error.hidden=true;const submit=event.currentTarget.querySelector('[type=submit]');submit.disabled=true;try{const form=new FormData(event.currentTarget);await api('/api/monitors',{method:'POST',body:JSON.stringify({name:form.get('name'),url:form.get('url'),interval_seconds:Number(form.get('interval_seconds'))})});event.currentTarget.reset();addDialog.close();showBanner('Monitor added successfully.','success');await loadDashboard();}catch(err){error.textContent=err.message;error.hidden=false;}finally{submit.disabled=false;}});
loadDashboard();
