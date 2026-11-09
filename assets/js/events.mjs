import {matchesEvent,compareEvents} from './event-matching.mjs'
// Shared listing and newsletter vocabulary; no cookies, storage or tracking.
const $ = (s) => document.querySelector(s)
const catalog = await fetch('/events/catalog.json').then(r => r.json())
const config = await fetch('/events/config.json').then(r => r.json())
const apiBase = String(config.apiBase || '').replace(/\/$/, '')
if (apiBase && (!apiBase.startsWith('https://') || new URL(apiBase).pathname !== '/')) throw new Error('Use an HTTPS API origin')
let ready = false, connected = false
try { ready = Boolean((await request('/health')).ready);connected=true } catch { /* Static-only mode stays usable. */ }
async function request(path, data, token) {
  const headers = {Accept:'application/json'}
  if (data !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = 'Bearer ' + token
  const response = await fetch(apiBase + '/api' + path, {method:data === undefined ? 'GET' : 'POST', headers, body:data === undefined ? undefined : JSON.stringify(data), cache:'no-store', referrerPolicy:'no-referrer'})
  const result = await response.json()
  if (!response.ok) throw new Error(result.error || 'Unable to complete this request')
  return result
}
function node(tag, text, cls) { const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e }
function status(form, text) { form.querySelector('.form-status').textContent = text }
function types(fieldset, selected=catalog.types) {
  if (!fieldset) return
  for (const type of catalog.types) {
    const label=node('label',null,'check'), input=document.createElement('input')
    input.type='checkbox';input.name='types';input.value=type;input.checked=selected.includes(type)
    label.append(input,document.createTextNode(type));fieldset.append(label)
  }
}
function preferences(form) {
  const values=new FormData(form)
  return {types:values.getAll('types'),origin:values.get('origin'),club:values.get('club') || ''}
}
for (const select of [$('#submission-type')].filter(Boolean)) {
  for (const type of catalog.types) { const option=node('option',type);option.value=type;select.append(option) }
}
types($('#newsletter-types')); types($('#preference-types')); types($('#listing-types'))
for (const form of [$('#submission-form'),$('#subscribe-form')].filter(Boolean)) form.querySelector('[type=submit]').disabled=!ready
if ($('#service-state')) $('#service-state').textContent=ready ? 'Submissions are reviewed before publication. Newsletter sign-up requires email confirmation.' : 'This preview has no connected event service. Submissions and subscriptions will open when the service is deployed.'
if ($('#listing-types')) {
  let events = catalog.events, period = 'upcoming', nextCursor=null, version=0, loading=false
  const moreButton=node('button','Load more events','button mono');moreButton.type='button';moreButton.hidden=true
  $('#community-events').after(moreButton)
  const params=new URLSearchParams(location.search)
  const requestedTypes=params.getAll('type').filter(t=>catalog.types.includes(t))
  if(requestedTypes.length||params.getAll('type').includes('none'))for(const box of document.querySelectorAll('#listing-types input'))box.checked=requestedTypes.includes(box.value)
  if (['all','original','community'].includes(params.get('network'))) $('#origin-filter').value=params.get('network')
  $('#club-filter').value=(params.get('club') || '').slice(0,100)
  if (['upcoming','current','past'].includes(params.get('period'))) period=params.get('period')
  const fmt = new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeZone:'UTC'})
  function render() {
    const chosen=[...document.querySelectorAll('#listing-types input:checked')].map(e=>e.value),origin=$('#origin-filter').value,club=$('#club-filter').value.trim().toLowerCase(),now=new Date()
    const selected=events.filter(e=>matchesEvent(e,{types:chosen,origin,club,period},now)).sort(compareEvents(period))
    const china=selected.find(e=>e.id==='china-trip-2027')
    $('#china-feature').hidden=!china
    const container=$('#community-events');container.replaceChildren()
    for (const event of selected.filter(e=>e.id!=='china-trip-2027')) {
      const card=node('article',null,'event-card'),badge=node('span',event.original?'ESRA Original':event.organiser,'status mono')
      const h=node('h2',event.title),meta=node('p',event.type+' · '+event.location,'mono')
      const date=node('p',fmt.format(new Date(event.start))+' – '+fmt.format(new Date(event.end)))
      const description=node('p',event.description),link=node('a','View event ↗','button mono')
      const url=new URL(event.url,location.origin)
      if (!['https:'].includes(url.protocol) && !(url.origin===location.origin&&event.url.startsWith('/'))) continue
      link.href=url.href;link.rel='noopener'
      card.append(badge,h,meta,date,description,link);container.append(card)
    }
    $('#empty-events').hidden=selected.length>0
    $('#result-count').textContent=selected.length+' '+(selected.length===1?'event':'events')+(nextCursor?' shown · more available':' matching your filters')
    $('#period-heading').textContent={upcoming:'Upcoming events',current:'Happening now',past:'Past events'}[period]
    for (const button of document.querySelectorAll('[data-period]')) button.setAttribute('aria-pressed',String(button.dataset.period===period))
    const search=new URLSearchParams({network:origin,period});for(const type of chosen)search.append('type',type);if(!chosen.length)search.append('type','none');if(club)search.set('club',club)
    history.replaceState(null,'',location.pathname+'?'+search)
  }
  async function load(reset=true) {
    const current=++version
    const chosen=[...document.querySelectorAll('#listing-types input:checked')].map(e=>e.value)
    if(!connected||!chosen.length){events=chosen.length?catalog.events:[];nextCursor=null;moreButton.hidden=true;render();return}
    const search=new URLSearchParams({origin:$('#origin-filter').value,club:$('#club-filter').value,period,limit:'25'})
    for(const type of chosen)search.append('type',type)
    if(!reset&&nextCursor)search.set('cursor',nextCursor)
    loading=true;moreButton.disabled=true
    try {
      const live=await request('/events?'+search)
      if(current!==version)return
      events=reset?[...live.featured,...live.events]:[...events,...live.events]
      nextCursor=live.next_cursor;moreButton.hidden=!nextCursor;render()
    } catch(error) {
      if(current!==version)return
      if(reset)events=catalog.events
      nextCursor=null;moreButton.hidden=true;render()
      $('#result-count').textContent='Community listings are temporarily unavailable. Showing published ESRA events.'
    } finally {if(current===version){loading=false;moreButton.disabled=false}}
  }
  let filterTimer
  function changed(){version++;nextCursor=null;moreButton.hidden=true;render();clearTimeout(filterTimer);filterTimer=setTimeout(()=>load(),200)}
  for(const id of ['#listing-types','#origin-filter','#club-filter'])$(id).addEventListener('input',changed)
  for(const button of document.querySelectorAll('[data-period]'))button.addEventListener('click',()=>{period=button.dataset.period;changed()})
  moreButton.addEventListener('click',()=>{if(!loading)load(false)})
  $('#copy-filters').addEventListener('click',()=>{
    const chosen=[...document.querySelectorAll('#listing-types input:checked')].map(e=>e.value),form=$('#subscribe-form')
    for(const box of form.querySelectorAll('[name=types]'))box.checked=chosen.includes(box.value)
    form.elements.origin.value=$('#origin-filter').value;form.elements.club.value=$('#club-filter').value
    status(form,'Your listing filters have been copied. Newsletter updates cover upcoming and ongoing events; past events are excluded.')
  })
  render();load()
}
$('#submission-form')?.addEventListener('submit',async e=>{
  e.preventDefault();const form=e.currentTarget,values=Object.fromEntries(new FormData(form))
  values.rules=form.elements.rules.checked
  const button=form.querySelector('[type=submit]');button.disabled=true
  try {
    values.start=new Date(values.start).toISOString();values.end=new Date(values.end).toISOString()
    const result=await request('/submissions',values);status(form,result.message);form.reset()
  } catch(error){status(form,error.message)} finally {button.disabled=!ready}
})
$('#subscribe-form')?.addEventListener('submit',async e=>{
  e.preventDefault();const form=e.currentTarget,button=form.querySelector('[type=submit]');button.disabled=true
  try { const result=await request('/subscribe',{email:form.elements.email.value,consent:form.elements.consent.checked,...preferences(form)});status(form,result.message) }
  catch(error){status(form,error.message)} finally {button.disabled=!ready}
})
const fragment = new URLSearchParams(location.hash.slice(1))
let token=fragment.get('token')
if(token)history.replaceState(null,'',location.pathname+location.search)
if ($('#review-detail') && token) {
  try {
    const result=await request('/review',undefined,token),event=result.event,box=$('#review-detail');box.replaceChildren()
    box.append(node('h2',event.title),node('p','Status: '+result.status,'mono'))
    for(const key of ['organiser','location','type','start','end','description','relevance'])box.append(node('h3',key),node('p',event[key]))
    const link=node('a','Open organiser’s event ↗');link.href=event.url;link.rel='noopener';link.target='_blank';box.append(link,node('p','Private organiser contact: '+result.contact))
    if(result.status==='pending')$('#review-form').hidden=false
    if(fragment.get('action'))box.append(node('p','Requested action: '+fragment.get('action')+'. Review the details and confirm below.'))
  } catch(error){$('#review-detail').textContent=error.message}
}
$('#review-form')?.addEventListener('submit',async e=>{
  e.preventDefault();const form=e.currentTarget
  for(const b of form.querySelectorAll('button'))b.disabled=true
  try {const result=await request('/review',{action:e.submitter.value},token);status(form,result.message)}
  catch(error){status(form,error.message);for(const b of form.querySelectorAll('button'))b.disabled=false}
})
async function loadPreferences() {
  const result=await request('/preferences',undefined,token),form=$('#preferences-form')
  for(const box of form.querySelectorAll('[name=types]'))box.checked=result.types.includes(box.value)
  form.elements.origin.value=result.origin;form.elements.club.value=result.club
  form.hidden=false;$('#preferences-state').textContent='Preferences for '+result.email
  if(fragment.get('action')==='unsubscribe')$('#preferences-state').textContent+=' — confirm removal below.'
}
if($('#preferences-form')&&token){
  if(fragment.get('mode')==='confirm') {$('#confirm-subscription').hidden=false;$('#preferences-state').textContent='Confirm that you requested this newsletter subscription.'}
  else try{await loadPreferences()}catch(error){$('#preferences-state').textContent=error.message}
}
$('#confirm-subscription')?.addEventListener('click',async e=>{
  e.currentTarget.disabled=true
  try{const result=await request('/confirm',{},token);token=result.token;$('#confirm-subscription').hidden=true;await loadPreferences()}
  catch(error){$('#preferences-state').textContent=error.message;e.currentTarget.disabled=false}
})
$('#preferences-form')?.addEventListener('submit',async e=>{
  e.preventDefault();const form=e.currentTarget
  try{status(form,(await request('/preferences',preferences(form),token)).message)}catch(error){status(form,error.message)}
})
$('#unsubscribe')?.addEventListener('click',async()=>{
  try{const result=await request('/preferences',{unsubscribe:true},token);$('#preferences-form').hidden=true;$('#preferences-state').textContent=result.message}
  catch(error){status($('#preferences-form'),error.message)}
})
