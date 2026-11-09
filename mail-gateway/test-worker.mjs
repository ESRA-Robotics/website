import test from 'node:test'
import assert from 'node:assert/strict'
import worker,{sign,verify} from './worker.mjs'
const secret='test-only-secret-with-more-than-32-characters'
const env={EMAIL_ENABLED:'true',SITE_ORIGIN:'https://esrarobotics.eu',BREVO_API_KEY:'stub',BREVO_LIST_ID:'3',BREVO_DOI_TEMPLATE_ID:'4',EMAIL_FROM:'events@esrarobotics.eu',ACCESS_SECRET:secret,EVENT_SUBMISSION_SECRET:secret,GITHUB_TOKEN:'stub',RATE_LIMITER:{limit:async()=>({success:true})}}
const request=(path,data,token,origin=env.SITE_ORIGIN)=>new Request('https://mail.example'+path,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(data)})
test('signup requires consent, allowed origin and enabled service; sends provider double opt-in only',async t=>{
 const calls=[];t.mock.method(globalThis,'fetch',async(url,options)=>{calls.push({url,body:JSON.parse(options.body)});return new Response('{}',{status:201})})
 assert.equal((await worker.fetch(request('/subscribe',{email:'a@example.com'}),env)).status,400)
 assert.equal((await worker.fetch(request('/subscribe',{email:'a@example.com',consent:true},null,'https://bad.example'),env)).status,403)
 assert.equal((await worker.fetch(request('/subscribe',{}),{...env,EMAIL_ENABLED:'false'})).status,503)
 assert.equal(calls.length,0)
 assert.equal((await worker.fetch(request('/subscribe',{email:'a@example.com',consent:true}),env)).status,202)
 assert.equal(calls[0].url,'https://api.brevo.com/v3/contacts/doubleOptinConfirmation')
 assert.deepEqual(calls[0].body.includeListIds,[3]);assert.equal(calls[0].body.contactPixelTrackingConsent,false)
})
test('provider failure and rate limiting never return a saved-subscription success',async t=>{
 t.mock.method(globalThis,'fetch',async()=>new Response('{}',{status:500}))
 assert.equal((await worker.fetch(request('/subscribe',{email:'a@example.com',consent:true}),env)).status,400)
 assert.equal((await worker.fetch(request('/subscribe',{}),{...env,RATE_LIMITER:{limit:async()=>({success:false})}})).status,429)
})
test('initial organiser proposal is signed, explicitly unverified and never grants Original privilege',async t=>{
 let issue;t.mock.method(globalThis,'fetch',async(url,options)=>{assert.match(url,/api.github.com/);issue=JSON.parse(options.body);return new Response('{}',{status:201})})
 const event={title:'Robot workshop',organiser:'Member club',location:'Munich',description:'A practical student robotics workshop with technical exchange.',relevance:'Connect student robotics teams across Europe.',type:'Workshops',url:'https://example.com/event',start:'2027-04-02T12:00:00Z',end:'2027-04-02T14:00:00Z',rules:true,original:true,email:'private@esrarobotics.eu'}
 assert.equal((await worker.fetch(request('/organiser/submit',event),env)).status,202)
 assert.ok(!issue.body.includes('private@'))
 const proof=await verify(issue.body.split('### ESRA verification\n\n')[1],secret,'event-submission')
 assert.equal(proof.verification,'self-declared');assert.match(issue.body,/inbox ownership is not verified/);assert.equal(proof.domain,'esrarobotics.eu');assert.equal(proof.event.original,undefined);assert.equal(proof.event.rules,undefined)
})


test('event form checks exact ESRA email domain without requiring sign-in',async t=>{
 let calls=0;t.mock.method(globalThis,'fetch',async()=>{calls++;return new Response('{}',{status:201})})
 for(const address of ['a@example.com','a@esrarobotics.eu.attacker.com','a@attacker-esrarobotics.eu'])assert.equal((await worker.fetch(request('/organiser/submit',{email:address}),env)).status,400)
 assert.equal(calls,0)
 assert.equal((await worker.fetch(request('/applications/china',{}),env)).status,404)
 assert.equal((await worker.fetch(request('/organiser/request-link',{}),env)).status,404)
})
