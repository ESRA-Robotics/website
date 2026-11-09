import test from 'node:test'
import assert from 'node:assert/strict'
import {matchesEvent,compareEvents} from '../assets/js/event-matching.mjs'
const event={type:'Trips',original:false,organiser:'European Club',start:'2027-03-14T09:00:00+08:00',end:'2027-03-23T18:00:00+08:00'}
const filter={types:['Trips','Hackathons'],origin:'community',club:'EUROPEAN',period:'current'}
test('timezone-aware current boundaries and archive separation',()=>{
  assert(matchesEvent(event,filter,new Date(event.start)))
  assert(matchesEvent(event,filter,new Date(event.end)))
  assert(!matchesEvent(event,filter,new Date('2027-03-23T10:00:01Z')))
  assert(matchesEvent(event,{...filter,period:'past'},new Date('2027-03-23T10:00:01Z')))
})
test('multiple categories, origin, club and empty selections',()=>{
  const now=new Date(event.start)
  assert(matchesEvent(event,filter,now))
  for(const override of [{types:[]},{types:['Workshops']},{origin:'original'},{club:'Different Club'}])assert(!matchesEvent(event,{...filter,...override},now))
})
test('originals remain prominent and past dates are descending',()=>{
  const original={...event,original:true,start:'2027-01-01T00:00:00Z'}
  assert.equal([event,original].sort(compareEvents('upcoming'))[0],original)
  const newer={...event,start:'2027-04-01T00:00:00Z'}
  assert.equal([event,newer].sort(compareEvents('past'))[0],newer)
})
