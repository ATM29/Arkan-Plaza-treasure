const css=`
body{font-family:Segoe UI,sans-serif;margin:0;background:#f6efe1;color:#2b2118}
header{background:#0a5f5f;color:#fff;padding:12px 16px;font-weight:800}
.wrap{max-width:820px;margin:0 auto;padding:12px}
.card{background:#fffdf7;border:1px solid #e7ddc7;border-radius:10px;padding:12px;margin-bottom:12px}
.card h2{margin:0 0 6px;color:#0a5f5f}
.t{background:#fff;border:1px solid #ece3cd;border-radius:8px;padding:8px;margin-bottom:6px}
.p{float:right;font-weight:900;font-size:20px;color:#0a5f5f}
.ltr{display:inline-block;width:18px;height:21px;margin:2px;border-radius:4px;text-align:center;font-weight:800;font-size:12px;background:#f1ece0;color:#bdb09a}
.ltr.g{background:#0f8a8a;color:#fff}
label{display:block;font-size:13px;font-weight:700;margin:6px 0 2px}
select,input{width:100%;padding:7px;border-radius:7px;border:1px solid #d8cba9}
.btn{width:100%;margin-top:6px;background:#0f8a8a;color:#fff;border:none;padding:10px;border-radius:8px;font-weight:800}
.e{background:#fff;border:1px solid #ece3cd;border-radius:8px;padding:6px;margin-bottom:5px}
.pos{color:#1c8a4a;font-weight:900}
.neg{color:#c0392b;font-weight:900}`;
const st=document.createElement('style');st.textContent=css;document.head.appendChild(st);
const root=document.getElementById('root');
root.innerHTML=`
<header>Arkan Plaza Live Scoreboard</header>
<div class='wrap'>
<div class='card'><h2>Leaderboard</h2><div id='lb'>Loading...</div><div style='font-size:12px;color:#7a6a4f'>Letters fill as stops clear. Word: GOLDENGELATO.</div></div>
<div class='card'><h2>Award Points</h2>
<label>Team</label><select id='team'></select>
<label>Stop</label><select id='stop'><option value=''>none</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option><option>11</option><option>12</option></select>
<label>Points</label><input id='pts' type='number' value='5'>
<label>Note</label><input id='note' type='text'>
<button class='btn' id='go'>Award Points</button>
</div>
<div class='card'><h2>Feed</h2><div id='feed'>Waiting...</div></div>
</div>`;
const U='https://wmpksflzlyamjuiqmgle.supabase.co',K='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtcGtzZmx6bHlhbWp1aXFtZ2xlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTU0NzQyODksImV4cCI6MjExMTA1MDI4OX0.lxkCKG9tdg_zCgGy29LGPAlkTQZCioy2fF3WQG-nosg';
const L={1:'G',2:'O',3:'L',4:'D',5:'E',6:'N',7:'G',8:'E',9:'L',10:'A',11:'T',12:'O'},N=12;
const c=supabase.createClient(U,K);let T=[],E=[];
async function load(){const[t,e]=await Promise.all([c.from('teams').select('*').order('name'),c.from('score_events').select('*').order('created_at',{ascending:false})]);T=t.data||[];E=e.data||[];draw();}
function draw(){const sel=document.getElementById('team');if(!sel.options.length)T.forEach(x=>{const o=document.createElement('option');o.value=x.id;o.textContent=x.name;sel.appendChild(o);});const m={};T.forEach(x=>m[x.id]={p:0,s:new Set()});E.forEach(v=>{if(!m[v.team_id])return;m[v.team_id].p+=v.points||0;if(v.stop_number)m[v.team_id].s.add(v.stop_number);});const rk=T.map(x=>({x,...m[x.id]})).sort((a,b)=>b.p-a.p);document.getElementById('lb').innerHTML=rk.map(r=>{let ls='';for(let n=1;n<=N;n++){const g=r.s.has(n);ls+=`<span class='ltr ${g?'g':''}'>${g?L[n]:''}</span>`;}return `<div class='t' style='border-left:6px solid ${r.x.color}'><b style='color:${r.x.color}'>${r.x.name}</b> <span class='p'>${r.p}</span><br><small>${r.x.god} · stops ${r.s.size}/${N}</small><div>${ls}</div></div>`;}).join('');document.getElementById('feed').innerHTML=E.slice(0,20).map(v=>{const t=T.find(x=>x.id===v.team_id);const col=t?t.color:'#999';const d=v.points>=0?'+'+v.points:v.points;return `<div class='e' style='border-left:6px solid ${col}'><b>${t?t.name:v.team_id}</b> ${v.description||''} <span class='${v.points>=0?'pos':'neg'}'>${d}</span></div>`;}).join('');}
document.getElementById('go').onclick=async()=>{const tid=document.getElementById('team').value,sp=document.getElementById('stop').value,pt=+document.getElementById('pts').value||0,nt=document.getElementById('note').value.trim();if(!tid){alert('Pick a team');return;}await c.from('score_events').insert({team_id:tid,stop_number:sp?+sp:null,points:pt,description:nt||null});};
try{c.channel('x').on('postgres_changes',{event:'*',schema:'public',table:'score_events'},load).on('postgres_changes',{event:'*',schema:'public',table:'teams'},load).subscribe();}catch(e){}
load();setInterval(load,5000);
