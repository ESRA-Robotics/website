import {matchesEvent,compareEvents} from './event-matching.mjs'
const $=s=>document.querySelector(s)
const catalog=await fetch('/events/catalog.json').then(r=>r.json())
const mail=await fetch('/events/mail-config.json').then(r=>r.json()).catch(()=>({endpoint:''}))
function node(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e}
function status(form,text){form.querySelector('.form-status').textContent=text}
async function mailRequest(path,data,access){
  if(!mail.endpoint)throw Error('Email signup and organiser access are being connected. Please try again soon.')
  const url=new URL(mail.endpoint);if(url.protocol!=='https:'||url.username||url.password)throw Error('Email service is not configured correctly.')
  const headers={'Content-Type':'application/json'};if(access)headers.Authorization='Bearer '+access
  const response=await fetch(mail.endpoint.replace(/\/$/,'')+path,{method:'POST',headers,body:JSON.stringify(data),referrerPolicy:'no-referrer'})
  const result=await response.json();if(!response.ok)throw Error(result.error||'Please try again later.');return result
}
const dialog=$('#newsletter-dialog')
for(const button of document.querySelectorAll('[data-open-newsletter]'))button.addEventListener('click',()=>{dialog.showModal();dialog.querySelector('input[type=email]').focus()})
$('[data-close-newsletter]')?.addEventListener('click',()=>dialog.close())
$('#newsletter-form')?.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.currentTarget,button=form.querySelector('[type=submit]');button.disabled=true
  try{const result=await mailRequest('/subscribe',{email:form.elements.email.value,consent:form.elements.consent.checked,website:form.elements.website.value});status(form,result.message);form.reset()}
  catch(error){status(form,error.message)}finally{button.disabled=false}
})
for(const select of [$('#submission-type')].filter(Boolean))for(const type of catalog.types){const option=node('option',type);option.value=type;select.append(option)}
if($('#listing-types')){
  for(const type of catalog.types){const label=node('label',null,'check'),input=document.createElement('input');input.type='checkbox';input.value=type;input.checked=true;label.append(input,document.createTextNode(type));$('#listing-types').append(label)}
  let period='upcoming',shown=25
  const more=node('button','Load more events','button mono');more.type='button';more.hidden=true;$('#community-events').after(more)
  const params=new URLSearchParams(location.search),requested=params.getAll('type').filter(t=>catalog.types.includes(t))
  if(requested.length||params.getAll('type').includes('none'))for(const box of document.querySelectorAll('#listing-types input'))box.checked=requested.includes(box.value)
  if(['all','original','community'].includes(params.get('network')))$('#origin-filter').value=params.get('network')
  $('#club-filter').value=(params.get('club')||'').slice(0,100)
  if(['upcoming','current','past'].includes(params.get('period')))period=params.get('period')
  const fmt=new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeZone:'UTC'})
  function render(){
    const types=[...document.querySelectorAll('#listing-types input:checked')].map(e=>e.value),origin=$('#origin-filter').value,club=$('#club-filter').value.trim().toLowerCase()
    const matching=catalog.events.filter(e=>matchesEvent(e,{types,origin,club,period})).sort(compareEvents(period)),community=matching.filter(e=>!e.original),selected=matching.filter(e=>e.original).concat(community.slice(0,shown))
    more.hidden=community.length<=shown;$('#china-feature').hidden=!selected.some(e=>e.id==='china-trip-2027')
    const container=$('#community-events');container.replaceChildren()
    for(const event of selected.filter(e=>e.id!=='china-trip-2027')){
      const card=node('article',null,'event-card'),title=node('h2',event.title),link=node('a','View event ↗','button mono')
      link.href=event.url;link.rel='noopener'
      card.append(node('span',event.original?'ESRA Original':event.organiser,'status mono'),title,node('p',event.type+' · '+event.location,'mono'),node('p',fmt.format(new Date(event.start))+' – '+fmt.format(new Date(event.end))),node('p',event.description),link);container.append(card)
    }
    const planning=(catalog.planned||[]).filter(e=>period==='upcoming'&&types.includes(e.type)&&(origin==='all'||e.original===(origin==='original'))&&(!club||e.organiser.toLowerCase().includes(club)))
    $('#planned-events').hidden=!planning.length;$('#empty-events').hidden=selected.length>0||planning.length>0
    $('#result-count').textContent=matching.length+' scheduled'+(planning.length?' · '+planning.length+' in planning':'')
    $('#period-heading').textContent={upcoming:'Upcoming events',current:'Happening now',past:'Past events'}[period]
    for(const button of document.querySelectorAll('[data-period]'))button.setAttribute('aria-pressed',String(button.dataset.period===period))
    const search=new URLSearchParams({network:origin,period});for(const type of types)search.append('type',type);if(!types.length)search.append('type','none');if(club)search.set('club',club)
    history.replaceState(null,'',location.pathname+'?'+search)
  }
  const changed=()=>{shown=25;render()}
  for(const id of ['#listing-types','#origin-filter','#club-filter'])$(id).addEventListener('input',changed)
  for(const button of document.querySelectorAll('[data-period]'))button.addEventListener('click',()=>{period=button.dataset.period;changed()})
  more.addEventListener('click',()=>{shown+=25;render()});render()
  if(params.get('subscribed')==='confirmed'){dialog.showModal();status($('#newsletter-form'),'Email confirmed. Welcome to the European robotics network.')}
}
let organiserAccess=new URLSearchParams(location.hash.slice(1)).get('access')
if(organiserAccess){history.replaceState(null,'',location.pathname+location.search);try{await mailRequest('/organiser/verify',{},organiserAccess);$('#submission-form').hidden=false;$('#organiser-login').hidden=true;$('#organiser-state').textContent='ESRA email verified. Your submission will be reviewed before publication.'}catch(error){organiserAccess=null;$('#organiser-state').textContent=error.message}}
$('#organiser-login')?.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.currentTarget,email=form.elements.email.value.trim().toLowerCase(),button=form.querySelector('button')
  if(!/^[^\s@]+@esrarobotics\.eu$/.test(email)){status(form,'Use your @esrarobotics.eu address.');return}
  button.disabled=true;try{status(form,(await mailRequest('/organiser/request-link',{email})).message)}catch(error){status(form,error.message)}finally{button.disabled=false}
})
$('#submission-form')?.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.currentTarget,button=form.querySelector('[type=submit]');button.disabled=true
  try{const data=Object.fromEntries(new FormData(form));data.rules=form.elements.rules.checked;data.start=new Date(data.start).toISOString();data.end=new Date(data.end).toISOString();const result=await mailRequest('/organiser/submit',data,organiserAccess);status(form,result.message);form.reset()}
  catch(error){status(form,error.message)}finally{button.disabled=false}
})

const participantForm=$('#participant-form')
if(participantForm){
  if(mail.applicationsOpen&&mail.endpoint){participantForm.querySelector('[type=submit]').disabled=false;$('#application-availability').textContent='Apply below. ESRA will review your application before confirming any place.'}
  participantForm.addEventListener('submit',async event=>{
    event.preventDefault();const button=participantForm.querySelector('[type=submit]');button.disabled=true
    try{
      if(!mail.applicationsOpen)throw Error('Applications are not open yet. Please check back for updates.')
      const data=Object.fromEntries(new FormData(participantForm));data.consent=participantForm.elements.consent.checked
      const result=await mailRequest('/applications/china',data);status(participantForm,result.message);participantForm.reset()
    }catch(error){status(participantForm,error.message)}finally{button.disabled=!mail.applicationsOpen}
  })
}
