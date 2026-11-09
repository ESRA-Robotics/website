/** Pure matching used for static fallback and tested independently of the DOM. */
export function matchesEvent(event, {types, origin='all', club='', period='upcoming'}, now=new Date()) {
  const start=new Date(event.start),end=new Date(event.end)
  const time=period==='past'?end<now:period==='current'?start<=now&&now<=end:start>now
  return time&&types.includes(event.type)&&(origin==='all'||event.original===(origin==='original'))&&(!club.trim()||event.organiser.toLowerCase().includes(club.trim().toLowerCase()))
}
export function compareEvents(period) {
  return (a,b)=>Number(b.original)-Number(a.original)||(period==='past'?new Date(b.start)-new Date(a.start):new Date(a.start)-new Date(b.start))
}
