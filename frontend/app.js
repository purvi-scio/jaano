
function responseEvidenceBlock(item) {
  const status = (item.status || item.result || "").toLowerCase();
  const page = item.page || item.response_page || "";
  const quote = item.quote || item.response_quote || item.evidence || "";
  const label = status.includes("unanswered") || status.includes("not") ? "Evidence checked" : "Response evidence";
  return `<div class="response-evidence">
    <div class="response-evidence-label">${label}${page ? ` · Page ${esc(page)}` : ""}</div>
    ${quote ? `<div class="response-quote">“${esc(String(quote).replace(/^["“]+|["”]+$/g,''))}”</div>` : `<div class="response-no-evidence">No supporting passage found in the response.</div>`}
    <button type="button" class="response-evidence-toggle">View evidence details →</button>
    <div class="response-evidence-detail" hidden>Jaano checked the simulated response evidence associated with this request. ${page ? `Page ${esc(page)} was reviewed.` : ""}</div>
  </div>`;
}


function evidenceSourceDetails(item) {
  const id = item.id || item.source_id || item.evidence_id || "";
  const title = item.title || item.source_title || "Government record";
  const date = item.date || item.source_date || "";
  const page = item.page ? `Page ${item.page}` : "";
  if (!id) return "";
  return `<div class="evidence-source" data-evidence-id="${esc(id)}">
    <div class="evidence-source-meta">${esc(title)}${date ? ` · ${esc(date)}` : ""}${page ? ` · ${page}` : ""}</div>
    <button type="button" class="source-toggle" data-source-id="${esc(id)}">View source →</button>
    <div class="source-detail" id="source-${esc(id)}" hidden>
      <div><strong>${esc(title)}</strong></div>
      <div class="source-detail-line">${date ? esc(date) : "Government record"}${page ? ` · ${esc(page)}` : ""}</div>
      <div class="source-detail-id">Evidence ID: ${esc(id)}</div>
      <div class="source-detail-copy">${esc(item.text || item.excerpt || item.content || "Source record retrieved from the prototype government corpus.")}</div>
    </div>
  </div>`;
}

let state={};
const PROFILE_KEY='jaano.sessionProfile';
const $=s=>document.querySelector(s);

function getSessionProfile(){
  try{return JSON.parse(sessionStorage.getItem(PROFILE_KEY)||'null')||null}catch(e){return null}
}
function saveSessionProfile(profile){
  const clean={name:profile.name||'',email:(profile.email||'').trim().toLowerCase(),address:profile.address||'',citizen:!!profile.citizen};
  sessionStorage.setItem(PROFILE_KEY,JSON.stringify(clean));
  console.log('[Jaano] Session profile created/updated',{email_present:!!clean.email,citizen:clean.citizen});
  return clean;
}
function hydrateDetailsFromSession(){
  const p=getSessionProfile();
  if(!p) return false;
  $('#savedProfileSummary').innerHTML=`<b>${esc(p.name)}</b><span>${esc(p.email)}</span><span>${esc(p.address).replace(/\n/g,' · ')}</span><span>Indian citizen confirmed</span>`;
  $('#savedProfileCard').classList.remove('hidden');
  $('#detailsFields').classList.add('hidden');
  console.log('[Jaano] Session profile reused',{email_present:!!p.email});
  return true;
}
function showEditableDetails(){
  const p=getSessionProfile();
  if(p){$('#name').value=p.name;$('#email').value=p.email;$('#address').value=p.address;$('#citizenCheck').checked=!!p.citizen;}
  $('#savedProfileCard').classList.add('hidden');
  $('#detailsFields').classList.remove('hidden');
}
function enterDetails(){hydrateDetailsFromSession();go('details');}

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function logUiClick(el){
  const id=el.id||'(no-id)';
  const text=(el.innerText||el.getAttribute('aria-label')||'').replace(/\s+/g,' ').trim();
  const screen=document.querySelector('.screen.active')?.id||'(none)';
  const event={id,text,screen};
  console.log('[Jaano] UI click',event);
  // Best-effort server-side logging so terminal output shows every UI action.
  fetch('/api/log',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(event),keepalive:true}).catch(()=>{});
}

// Centralized click instrumentation: every button plus the Jaano home link is logged.
document.addEventListener('click',e=>{
  const el=e.target.closest('button, a.brand');
  if(el) logUiClick(el);
});

function go(id){
  const target=document.getElementById(id);
  if(!target){
    console.error('[Jaano] Navigation failed: screen not found',id);
    return;
  }
  document.querySelectorAll('.screen').forEach(x=>x.classList.remove('active'));
  target.classList.add('active');
  window.scrollTo({top:0,behavior:'smooth'});
  console.log('[Jaano] Navigation',id);
}

async function post(path,data){
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(!r.ok)throw new Error(`Request failed: ${r.status}`);
  return r.json();
}

function renderIntent(){const i=state.intent;const aiLabel=state.ai?.mode==='live'?`Live AI · ${esc(state.ai.model)}`:'Demo AI fallback';$('#aiBadge').textContent=aiLabel;$('#intentCard').innerHTML=`<div class="card intent-grid"><div><span>We heard</span><b>${esc(state.question)}</b></div><div><span>Topic</span><b>${esc(i.topic)}</b></div><div><span>You appear to need</span><b>${esc(i.requirements.slice(0,3).join(', '))}</b></div><div><span>Our next step</span><b>Check public information before asking for it again</b></div><div><span>AI mode</span><b>${aiLabel}</b></div></div>`}
function renderFind(){const f=$('#found'),m=$('#missing');const ev=state.evidence||[];f.innerHTML=state.documents.flatMap(d=>d.facts.map(x=>`<div class="found-row"><div><b>${esc(x)}</b><div class="source">${esc(d.title)} · ${esc(d.date)} · <button class="source-link evidence-btn" data-evidence="${esc(d.document_id||'')}">View source</button></div></div><span class="pill">Source found</span></div>`)).join('');m.innerHTML=`<h3 class="missing-title">Still missing</h3>`+state.missing.map(x=>`<div class="missing-row"><div><b>${esc(x)}</b><div class="why-missing">Not found in the connected public-information sources.</div></div><span class="pill bad">Not found</span></div>`).join('');$('#gapSummary').innerHTML=`<b>${state.missing.length} information gap${state.missing.length===1?'':'s'} identified.</b><span>We'll ask only for what's still missing.</span>`;document.querySelectorAll('.evidence-btn').forEach(b=>b.onclick=()=>{const d=ev.find(x=>x.id===b.dataset.evidence);if(d) alert(`${d.title}\n${d.department}\n${d.date} · Page ${d.page}\n\n${d.text}`)})}
function renderRequest(){const a=state.intent.authority;$('#authority').innerHTML=`<div class="authority"><div><div class="label">LIKELY PUBLIC AUTHORITY</div><h3>${esc(a.name)}</h3><div class="muted">${esc(a.parent)}</div><div class="source">${esc(a.reason)}</div></div><div class="confidence"><div class="label">MATCH</div><b>${a.confidence}%</b><small>AI recommendation</small></div></div>`;$('#requestItems').innerHTML=state.request_items.map((x,i)=>`<li><span>${esc(x)}</span></li>`).join('');$('#mapping').innerHTML=state.mappings.map(m=>`<div class="mapping-row"><div class="mapping-from">“${esc(String(m.from).replace(/^["“]+|["”]+$/g,''))}”</div><div class="mapping-arrow">→</div><div><b>${esc(m.to)}</b><span>${esc(m.why)}</span></div></div>`).join('')}
function renderReview(){const a=state.intent.authority;$('#reviewAuthorityCard').innerHTML=`<div class="authority"><div><div class="label">PUBLIC AUTHORITY</div><h3>${esc(a.name)}</h3><div class="muted">${esc(a.parent)}</div></div><div class="confidence"><div class="label">MATCH</div><b>${a.confidence}%</b></div></div>`;$('#reviewItems').innerHTML=state.request_items.map((x,i)=>`<li><b>${esc(x)}</b></li>`).join('')}
function openEdit(){ $('#editFields').innerHTML=state.request_items.map((x,i)=>`<label>Request ${i+1}<textarea data-edit-index="${i}" rows="3">${esc(x)}</textarea></label>`).join('');$('#editModal').classList.remove('hidden') }
function closeEdit(){$('#editModal').classList.add('hidden')}


function renderTimeline(timeline){return `<div class="timeline">${timeline.map(x=>`<div class="${x.done?'done':''}"><b>${esc(x.label)}</b><small>${esc(x.description||'')}</small></div>`).join('')}</div>`}
function renderRtiCard(r){return `<div class="rti-card"><div class="rti-card-top"><div><span class="label">RTI ID</span><b>${esc(r.registration_id)}</b></div><span class="status-pill">${esc(r.status)}</span></div><h3>${esc(r.subject||'Information request')}</h3><p class="muted">${esc(r.authority?.name||'Public Authority')}</p><div class="rti-meta"><span>Filed ${esc(r.filed_date||'29 Aug 2026')}</span><span>${esc(r.request_items?.length||0)} information requests</span></div>${renderTimeline(r.timeline||[])}<button class="text-button view-rti" data-rti-id="${esc(r.registration_id)}">View details →</button></div>`}
function renderDetail(r){$('#rtiDetailCard').innerHTML=`<div class="detail-hero"><div class="idbox"><span>RTI ID</span><b>${esc(r.registration_id)}</b></div><span class="status-pill">${esc(r.status)}</span></div><div class="detail-block"><div class="label">SUBJECT</div><h3>${esc(r.subject||'Information request')}</h3><p class="muted">${esc(r.authority?.name||'Public Authority')} · ${esc(r.authority?.parent||'')}</p></div><div class="detail-block"><div class="label">WHAT YOU ASKED FOR</div><ol>${(r.request_items||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ol></div><div class="detail-block"><div class="label">STATUS</div>${renderTimeline(r.timeline||[])}<p class="last-update"><b>Last update:</b> ${esc(r.last_update||'Request received and is being routed to the responsible desk.')}</p></div>`}
async function trackRti(id,email){
  const r=await post('/api/rtis/track',{registration_id:id.trim(),email:email.trim()});
  renderDetail(r);go('rtiDetail');
}
async function loadMyRtis(email){
  const normalizedEmail=email.trim();
  state.myRtisEmail=normalizedEmail;
  const r=await post('/api/rtis/list',{email:normalizedEmail});
  const list=$('#rtisList');
  if(!r.rtis.length){list.innerHTML='<div class="empty-card"><h3>No RTIs found</h3><p>We could not find a request filed with this email.</p></div>';return;}
  list.innerHTML=r.rtis.map(renderRtiCard).join('');
}

async function analyse(){
  state.question=$('#question').value.trim();
  if(!state.question){console.warn('[Jaano] Analyse blocked: empty question');return;}
  $('#analyse').disabled=true;
  try{
    console.log('[Jaano] Sending /api/analyse');
    state=Object.assign(state,await post('/api/analyse',{text:state.question}));
    console.log('[Jaano] Analyse successful', {aiMode: state.ai?.mode, model: state.ai?.model || 'fallback'});
    renderIntent();go('understand');
  }catch(e){console.error('[Jaano] Analyse failed',e);alert('Could not analyse the question. Please try again.')}
  finally{$('#analyse').disabled=false}
}

$('#analyse').onclick=analyse;
document.querySelectorAll('.examples button').forEach(b=>b.onclick=()=>{$('#question').value=b.dataset.q;analyse()});
$('#continueFind').onclick=()=>{renderFind();go('find')};
$('#continueRequest').onclick=()=>{renderRequest();go('request')};
$('#review').onclick=()=>{renderReview();go('reviewScreen')};
$('#editRequest').onclick=openEdit;
$('#editRequest2').onclick=openEdit;
$('#closeModal').onclick=closeEdit;
$('#saveEdit').onclick=()=>{const values=[...document.querySelectorAll('[data-edit-index]')].map(x=>x.value.trim()).filter(Boolean);if(values.length)state.request_items=values;closeEdit();renderRequest();renderReview();go('request')};
$('#continueDetails').onclick=enterDetails;
$('#citizenCheck').onchange=()=>{};
$('#bplCheck').onchange=()=>{const on=$('#bplCheck').checked;$('#bplUpload').classList.toggle('hidden',!on);$('#fee').textContent=on?'₹0':'₹10';$('#feeNote').textContent=on?'BPL fee exemption shown for the prototype.':'Simulated payment for the hackathon prototype.'};

$('#submit').onclick=async()=>{
  const btn=$('#submit'),err=$('#detailsError');
  err.classList.add('hidden');
  const name=$('#name').value.trim(),email=$('#email').value.trim(),address=$('#address').value.trim(),citizen=$('#citizenCheck').checked,bpl=$('#bplCheck').checked;
  console.log('[Jaano] Submit validation',{hasName:!!name,hasEmail:!!email,hasAddress:!!address,citizen,bpl});
  if(!name||!email||!address||!citizen){err.textContent='Please complete your name, email, address and citizenship confirmation.';err.classList.remove('hidden');console.warn('[Jaano] Submission blocked: required details missing');return}
  if(!/^\S+@\S+\.\S+$/.test(email)){err.textContent='Please enter a valid email address, for example name@example.com.';err.classList.remove('hidden');console.warn('[Jaano] Submission blocked: invalid email');$('#email').focus();return}
  if(bpl&&!$('#bplFile').files.length){err.textContent='Please upload your BPL certificate, or leave the BPL option unchecked.';err.classList.remove('hidden');console.warn('[Jaano] Submission blocked: BPL certificate missing');return}
  btn.disabled=true;const oldText=btn.innerHTML;btn.innerHTML='Submitting <span>…</span>';
  try{
    console.log('[Jaano] Sending /api/submit');
    const r=await post('/api/submit',{question:state.question,authority:state.intent.authority,request_items:state.request_items,name,email,address,citizen,bpl,bpl_certificate:bpl?$('#bplFile').files[0]?.name:null});
    console.log('[Jaano] Submission successful',r);
    saveSessionProfile({name,email,address,citizen});
    state.submission=Object.assign(r,{name,email,address,citizen});
    $('#rid').textContent=r.registration_id;go('submitted');
  }catch(e){console.error('[Jaano] Submission failed',e);err.textContent='We could not submit the request. Please try again.';err.classList.remove('hidden')}
  finally{btn.disabled=false;btn.innerHTML=oldText}
};

$('#showResponse').onclick=async()=>{
  try{
    console.log('[Jaano] Sending /api/response/analyse');
    const r=await post('/api/response/analyse',{request_items:state.request_items,scenario:state.intent.scenario});
    console.log('[Jaano] Response analysis successful',{answered:r.answered_count,total:r.results.length,aiMode:r.ai?.mode,model:r.ai?.model||'fallback'});
    state.response=r;$('#answeredCount').textContent=r.answered_count;$('#scoreText').textContent=`of ${r.results.length} requests answered`;$('#responseList').innerHTML=r.results.map((x,i)=>`<div class="resp-row ${x.status==='answered'?'answered':'unanswered'}"><div><div class="resp-top"><b>${i+1}. ${esc(x.question)}</b><span class="pill ${x.status==='answered'?'':'bad'}">${x.status==='answered'?'Answered':x.status==='partially_answered'?'Partially answered':'Not answered'}</span></div><div class="answer">${esc(x.answer)}</div><div class="response-reason">${esc(x.reason)}</div>${(x.evidence||[]).length?`<div class="source evidence-box"><b>Response evidence</b> · ${x.evidence.map(e=>`Page ${esc(e.page||'1')}: “${esc(e.quote||'')}”`).join(' ')}</div>`:`<div class="source evidence-box muted">No supporting passage found in the response.</div>`}</div></div>`).join('');
    if(r.unanswered.length){$('#nextStep').innerHTML=`<b>${r.unanswered.length} gap${r.unanswered.length===1?'':'s'} remain.</b><span>Jaano can turn the missing information into a suggested first-appeal draft.</span>`;$('#showAppeal').classList.remove('hidden')}else{$('#nextStep').innerHTML='<b>Your request was fully answered.</b><span>Jaano found a response for every information item you asked for.</span>';$('#showAppeal').classList.add('hidden')}
    go('response');
  }catch(e){console.error('[Jaano] Response analysis failed',e);alert('Could not load the response. Please try again.')}
};

$('#showAppeal').onclick=()=>{const r=state.response;if(!r){console.error('[Jaano] Appeal navigation blocked: response missing');return}$('#appealItems').innerHTML=r.unanswered.map(x=>`<div class="appeal-item"><span>Not answered</span><b>${esc(x.question)}</b><p>${esc(x.reason)}</p></div>`).join('');$('#appealDraft').textContent=r.appeal_draft;go('appeal')};
function restart(){
  console.log('[Jaano] Restarting flow');
  state={};
  $('#question').value='';
  ['trackId','trackEmail'].forEach(id=>{if($('#'+id))$('#'+id).value=''});
  const p=getSessionProfile();
  if(p){$('#name').value=p.name;$('#email').value=p.email;$('#address').value=p.address;$('#citizenCheck').checked=!!p.citizen;}
  else {['name','email','address'].forEach(id=>{if($('#'+id))$('#'+id).value=''});$('#citizenCheck').checked=false;}
  $('#bplCheck').checked=false;$('#bplUpload').classList.add('hidden');$('#bplFile').value='';$('#fee').textContent='₹10';
  $('#savedProfileCard').classList.add('hidden');$('#detailsFields').classList.remove('hidden');
  go('hero');
}
$('#restart').onclick=restart;
$('#restart2').onclick=restart;

$('#trackFromHome').onclick=()=>go('track');
$('#myRtisFromHome').onclick=()=>{
  const p=getSessionProfile();
  if(p){
    $('#myRtisEmail').value=p.email;
    state.myRtisEmail=p.email;
    $('#myRtisLookup').classList.add('compact-hidden');
    $('#myRtisError').classList.add('hidden');
    go('myRtis');
    console.log('[Jaano] My RTIs auto-refresh',{email_present:!!p.email});
    loadMyRtis(p.email).catch(e=>console.error('[Jaano] My RTIs auto-refresh failed',e));
  } else {
    $('#myRtisLookup').classList.remove('compact-hidden');
    go('myRtis');
  }
};
$('#submittedMyRtis').onclick=()=>{
  const email=(state.submission?.email || getSessionProfile()?.email || '').trim();
  if(email){
    $('#myRtisEmail').value=email; state.myRtisEmail=email; $('#myRtisLookup').classList.add('compact-hidden');
    go('myRtis');
    console.log('[Jaano] My RTIs auto-refresh',{email_present:true});
    loadMyRtis(email).catch(e=>console.error('[Jaano] My RTIs load failed',e));
  } else { $('#myRtisLookup').classList.remove('compact-hidden'); go('myRtis'); }
};
$('#trackSubmit').onclick=async()=>{const id=$('#trackId').value.trim(),email=$('#trackEmail').value.trim(),err=$('#trackError');err.classList.add('hidden');if(!id||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){err.textContent='Enter a valid RTI ID and email address.';err.classList.remove('hidden');console.warn('[Jaano] Track blocked: invalid lookup');return}try{console.log('[Jaano] Tracking RTI',id);await trackRti(id,email);}catch(e){console.error('[Jaano] Track failed',e);err.textContent='We could not find an RTI matching that ID and email.';err.classList.remove('hidden');}};
$('#myRtisSubmit').onclick=async()=>{const email=$('#myRtisEmail').value.trim(),err=$('#myRtisError');err.classList.add('hidden');if(!/^\S+@\S+\.\S+$/.test(email)){err.textContent='Please enter a valid email address.';err.classList.remove('hidden');return}try{console.log('[Jaano] My RTIs auto-refresh',{email_present:true});await loadMyRtis(email);$('#myRtisLookup').classList.add('compact-hidden');}catch(e){console.error('[Jaano] My RTIs failed',e);err.textContent='Could not load your RTIs. Please try again.';err.classList.remove('hidden');}};

// Delegated RTI detail handler. Keep this in one click listener so dynamically rendered cards
// always navigate to the detail screen after the server-side email+ID check.
document.addEventListener('click',e=>{
  const b=e.target.closest('.view-rti');
  if(!b) return;
  e.preventDefault();
  const id=b.dataset.rtiId;
  const email=(state.myRtisEmail || getSessionProfile()?.email || $('#myRtisEmail').value || '').trim();
  console.log('[Jaano] View RTI',id,'email_present=',Boolean(email));
  if(!email){console.warn('[Jaano] View RTI blocked: email context missing');return;}
  trackRti(id,email).catch(err=>console.error('[Jaano] View RTI failed',err));
});
$('#editSavedProfile').onclick=showEditableDetails;
$('#detailMyRtis').onclick=()=>{
  if(state.myRtisEmail) $('#myRtisEmail').value=state.myRtisEmail;
  go('myRtis');
};

// All .back buttons use data-back. This fixes the final "Back to response" action.
document.querySelectorAll('.back').forEach(b=>b.onclick=()=>go(b.dataset.back));


document.addEventListener("click", (event) => {
  const btn = event.target.closest(".source-toggle");
  if (!btn) return;
  const id = btn.dataset.sourceId;
  const detail = document.getElementById(`source-${id}`);
  if (!detail) return;
  detail.hidden = !detail.hidden;
  btn.textContent = detail.hidden ? "View source →" : "Hide source ↑";
});
