import {matchesEvent,compareEvents,foldCalendarLines} from './event-matching.mjs'
// Static files only. No account database, API, SMTP credentials or tracking.
const $ = (s) => document.querySelector(s)
const catalog = await fetch('/events/catalog.json').then(r => r.json())
const feedIndex = await fetch('/events/feeds/index.json').then(r => r.json())
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
types($('#newsletter-types')); types($('#listing-types'))
if ($('#listing-types')) {
  const events = catalog.events
  let period = 'upcoming',shown=25
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
    const matching=events.filter(e=>matchesEvent(e,{types:chosen,origin,club,period},now)).sort(compareEvents(period))
    const community=matching.filter(e=>!e.original)
    const selected=matching.filter(e=>e.original).concat(community.slice(0,shown))
    moreButton.hidden=community.length<=shown
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
    $('#result-count').textContent=selected.length+' '+(selected.length===1?'event':'events')+(moreButton.hidden?' matching your filters':' shown · more available')
    $('#period-heading').textContent={upcoming:'Upcoming events',current:'Happening now',past:'Past events'}[period]
    for (const button of document.querySelectorAll('[data-period]')) button.setAttribute('aria-pressed',String(button.dataset.period===period))
    const search=new URLSearchParams({network:origin,period});for(const type of chosen)search.append('type',type);if(!chosen.length)search.append('type','none');if(club)search.set('club',club)
    history.replaceState(null,'',location.pathname+'?'+search)
  }
  const changed=()=>{shown=25;render()}
  for(const id of ['#listing-types','#origin-filter','#club-filter'])$(id).addEventListener('input',changed)
  moreButton.addEventListener('click',()=>{shown+=25;render()})
  for(const button of document.querySelectorAll('[data-period]'))button.addEventListener('click',()=>{period=button.dataset.period;changed()})
  $('#copy-filters').addEventListener('click',()=>{
    const chosen=[...document.querySelectorAll('#listing-types input:checked')].map(e=>e.value),form=$('#subscribe-form')
    for(const box of form.querySelectorAll('[name=types]'))box.checked=chosen.includes(box.value)
    form.elements.origin.value=$('#origin-filter').value;form.elements.club.value=$('#club-filter').value
    updateSubscriptions(form)
  })
  render()
}

function updateSubscriptions(form) {
  const selected=preferences(form),box=$('#subscription-links');box.replaceChildren()
  const add=(label,path)=>{const a=node('a',label);a.href=path;box.append(a)}
  const club=selected.club.trim().toLowerCase()
  if(club){
    const matches=feedIndex.clubs.filter(c=>c.name.toLowerCase().includes(club))
    for(const entry of matches){add(entry.name+' · RSS',entry.rss);add(entry.name+' · Calendar feed',entry.calendar)}
    if(!matches.length)box.append(node('p','No published club feed matches this organiser yet.'))
    box.append(node('p','Club feeds include all event types from that club. For multiple topics, follow the topic feeds below.','small'))
  }
  if(!club&&selected.types.length===catalog.types.length){const entry=feedIndex.networks[selected.origin];add('All selected events · RSS',entry.rss);add('All selected events · Calendar feed',entry.calendar)}
  else for(const type of selected.types){
    const entry=feedIndex.topics.find(f=>f.type===type&&f.origin===selected.origin)
    if(entry){add(type+' · RSS',entry.rss);add(type+' · Calendar feed',entry.calendar)}
  }
  if(!selected.types.length)box.append(node('p','Choose at least one event type.'))
  const events=catalog.events.filter(e=>matchesEvent(e,{...selected,period:'upcoming'})||matchesEvent(e,{...selected,period:'current'}))
  const cal=node('button','Download calendar for these filters','text-button');cal.type='button'
  cal.addEventListener('click',()=>{
    const esc=s=>String(s).replaceAll('\\','\\\\').replaceAll('\n','\\n').replaceAll(',','\\,').replaceAll(';','\\;')
    const date=s=>new Date(s).toISOString().replaceAll('-','').replaceAll(':','').replace(/\.\d{3}/,'')
    const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//ESRA//European Robotics Events//EN','CALSCALE:GREGORIAN']
    for(const e of events)lines.push('BEGIN:VEVENT','UID:'+esc(e.id)+'@esrarobotics.eu','DTSTAMP:'+date(new Date()),'DTSTART:'+date(e.start),'DTEND:'+date(e.end),'SUMMARY:'+esc(e.title),'LOCATION:'+esc(e.location),'DESCRIPTION:'+esc(e.organiser+' · '+e.description),'URL:'+new URL(e.url,location.origin).href,'END:VEVENT')
    lines.push('END:VCALENDAR')
    const url=URL.createObjectURL(new Blob([foldCalendarLines(lines).join('\r\n')+'\r\n'],{type:'text/calendar;charset=utf-8'})),a=node('a')
    a.href=url;a.download='esra-events.ics';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
  })
  box.append(cal,node('p','Calendar downloads are snapshots. RSS feeds update when approved listings are published.','small'))
}
const subscribeForm=$('#subscribe-form')
if(subscribeForm){subscribeForm.addEventListener('submit',e=>{e.preventDefault();updateSubscriptions(subscribeForm)});subscribeForm.addEventListener('change',()=>updateSubscriptions(subscribeForm));subscribeForm.addEventListener('input',()=>updateSubscriptions(subscribeForm));updateSubscriptions(subscribeForm)}
$('#submission-form')?.addEventListener('submit',event=>{
  event.preventDefault();const form=event.currentTarget,values=Object.fromEntries(new FormData(form))
  if(!form.elements.rules.checked)return
  if(new Date(values.end)<new Date(values.start)){status(form,'End must follow start.');return}
  const payload={title:values.title,organiser:values.organiser,location:values.location,type:values.type,start:new Date(values.start).toISOString(),end:new Date(values.end).toISOString(),url:values.url,description:values.description,relevance:values.relevance}
  const body='### Event details\n\n```json\n'+JSON.stringify(payload,null,2)+'\n```\n\n### Review acknowledgement\n\nI am authorised to submit this public event and agree to the ESRA event guidelines.'
  const url=new URL('https://github.com/ESRA-Robotics/website/issues/new')
  url.searchParams.set('title','[Event] '+values.title);url.searchParams.set('body',body)
  $('#prepared-event-json').value=JSON.stringify(payload,null,2)
  $('#github-submission').href=url.href.length<=7500?url.href:'https://github.com/ESRA-Robotics/website/issues/new?template=event.yml'
  $('#submission-next').hidden=false
  status(form,url.href.length<=7500?'Ready to review on GitHub. Nothing has been submitted yet. Check the details there and publish the issue yourself.':'Your description is too long to prefill a GitHub link. Copy the event JSON below into the GitHub event form. Nothing has been submitted yet.')
  $('#github-submission').focus()
})
