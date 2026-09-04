let DB={commentators:[],statements:[]};
const view=document.getElementById('view'), modal=document.getElementById('modal'), modalContent=document.getElementById('modalContent');
const cmap=()=>Object.fromEntries(DB.commentators.map(c=>[c.id,c]));
const fmt=d=>new Intl.DateTimeFormat('tr-TR',{day:'numeric',month:'short'}).format(new Date(d+'T12:00:00'));
const sentimentLabel=s=>s==='positive'?'Olumlu':s==='negative'?'Eleştirel':'Nötr';
function statementCard(s){const c=cmap()[s.commentator];return `<article class="statement" data-statement="${s.id}"><div class="statement-top"><div class="avatar">${c.avatar}</div><div style="flex:1"><h3>${s.summary}</h3><div class="statement-meta"><b>${c.name}</b><span class="dot"></span><span>${fmt(s.date)}</span><span class="dot"></span><span>${s.source}</span><span class="sentiment ${s.sentiment}">${sentimentLabel(s.sentiment)}</span></div><div class="badge-row" style="margin-top:9px"><span class="badge">${s.team}</span>${s.players.map(p=>`<span class="badge">${p}</span>`).join('')}<span class="badge">${s.topic}</span></div></div></div></article>`}
function feature(){let s=[...DB.statements].sort((a,b)=>b.strength-a.strength)[0],c=cmap()[s.commentator];return `<div class="feature-card"><div class="badge-row"><span class="badge hot">İDDİALI SÖZ</span><span class="badge">${s.team}</span>${s.players.slice(0,1).map(p=>`<span class="badge">${p}</span>`).join('')}</div><div class="quote">${s.summary}</div><div class="byline"><div class="who"><div class="avatar">${c.avatar}</div><div><b>${c.name}</b><small>${s.source} · ${fmt(s.date)}</small></div></div><div class="score">${s.strength}/10</div></div></div>`}
function gundem(){const latest=[...DB.statements].sort((a,b)=>b.date.localeCompare(a.date));view.innerHTML=`${feature()}<div class="section-title"><h2>Son yorumlar</h2><span>${DB.statements.length} kayıt</span></div><div class="feed">${latest.slice(0,8).map(statementCard).join('')}</div><div class="source-note">V1 pilot veri seti gerçek, kamuya açık A Spor yazar içeriklerinden yapılandırılmıştır. Kaynak bağlantıları kayıtların içinde tutulur.</div>`;bindStatementClicks()}
function rank(field){const m={};DB.statements.forEach(s=>{let keys=field==='team'?[s.team]:s.players;keys.forEach(k=>{if(k)m[k]=(m[k]||0)+1})});return Object.entries(m).sort((a,b)=>b[1]-a[1])}
function teams(){const r=rank('team');view.innerHTML=`<div class="section-title"><h2>En çok konuşulan takımlar</h2><span>Pilot veri</span></div><div class="rank-list">${r.map(([n,v],i)=>`<div class="rank-item"><div class="rank-no">${String(i+1).padStart(2,'0')}</div><div><div class="rank-name">${n}</div><div class="rank-sub">Toplanan yorum kayıtları</div></div><div class="rank-value">${v}</div></div>`).join('')}</div>`}
function players(){const r=rank('players');view.innerHTML=`<div class="section-title"><h2>En çok konuşulan oyuncular</h2><span>Pilot veri</span></div><div class="rank-list">${r.map(([n,v],i)=>`<div class="rank-item"><div class="rank-no">${String(i+1).padStart(2,'0')}</div><div><div class="rank-name">${n}</div><div class="rank-sub">Kimler konuştuğunu görmek için aç</div></div><div class="rank-value">${v}</div></div>`).join('')}</div>`}
function commentators(){view.innerHTML=`<div class="section-title"><h2>Yorumcular</h2><span>V1 pilot</span></div><div class="commentator-grid">${DB.commentators.map(c=>{let arr=DB.statements.filter(s=>s.commentator===c.id);return `<div class="commentator-card" data-commentator="${c.id}"><div class="avatar">${c.avatar}</div><h3>${c.name}</h3><p>${c.primarySource}</p><div class="metric">${arr.length} kayıt</div></div>`}).join('')}</div>`;document.querySelectorAll('[data-commentator]').forEach(el=>el.onclick=()=>openProfile(el.dataset.commentator))}
function openProfile(id){const c=cmap()[id],arr=DB.statements.filter(s=>s.commentator===id),teams={};arr.forEach(s=>teams[s.team]=(teams[s.team]||0)+1);const topTeam=Object.entries(teams).sort((a,b)=>b[1]-a[1])[0]?.[0]||'-';const hot=arr.filter(s=>s.strength>=8).length;modalContent.innerHTML=`<div class="profile-hero"><div class="avatar">${c.avatar}</div><h2>${c.name}</h2><p>${c.role} · ${c.primarySource}</p></div><div class="metrics"><div class="metric-box"><b>${arr.length}</b><small>YORUM</small></div><div class="metric-box"><b>${hot}</b><small>İDDİALI</small></div><div class="metric-box"><b>${topTeam}</b><small>EN ÇOK</small></div></div><div class="section-title"><h2>Son yorumlar</h2></div><div class="feed">${[...arr].sort((a,b)=>b.date.localeCompare(a.date)).map(statementCard).join('')}</div>`;modal.classList.add('show');bindStatementClicks()}
function bindStatementClicks(){document.querySelectorAll('[data-statement]').forEach(el=>el.onclick=()=>{let s=DB.statements.find(x=>x.id==el.dataset.statement),c=cmap()[s.commentator];modalContent.innerHTML=`<div class="profile-hero" style="text-align:left"><div class="eyebrow">${s.type.toUpperCase()} · GÜVEN ${s.confidence}/100</div><h2 style="margin-top:8px">${s.summary}</h2><p>${c.name} · ${fmt(s.date)} · ${s.source}</p></div><div class="badge-row">${[s.team,...s.players,s.topic].map(x=>`<span class="badge">${x}</span>`).join('')}</div><p class="source-note">Bu kayıt, kaynak metnin birebir kopyası değil; Saha Dışı veri modeline dönüştürülmüş kısa bir özet kaydıdır.</p><p><a href="${s.url}" target="_blank" style="color:var(--green);font-weight:800;text-decoration:none">Kaynağa git ↗</a></p>`;modal.classList.add('show')})}
function render(v){document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active',b.dataset.view===v));({gundem,takimlar:teams,oyuncular:players,yorumcular:commentators}[v]||gundem)()}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>render(b.dataset.view));
document.getElementById('closeModal').onclick=()=>modal.classList.remove('show');
modal.onclick=e=>{if(e.target===modal)modal.classList.remove('show')};
document.getElementById('searchBtn').onclick=()=>{
  modalContent.innerHTML=`<div class="section-title"><h2>Arama</h2></div><input class="searchbox" id="q" placeholder="Yorumcu, takım veya oyuncu ara…"><div id="results"></div>`;
  modal.classList.add('show');
  setTimeout(()=>{
    const q=document.getElementById('q');
    const r=document.getElementById('results');
    q.focus();
    q.oninput=()=>{
      const t=q.value.toLocaleLowerCase('tr-TR');
      if(!t){r.innerHTML='';return;}
      const hits=DB.statements.filter(s=>{
        const c=cmap()[s.commentator];
        return [c.name,s.team,...s.players,s.topic,s.summary].join(' ').toLocaleLowerCase('tr-TR').includes(t);
      });
      r.innerHTML=`<div class="feed">${hits.slice(0,10).map(statementCard).join('')||'<div class="empty">Sonuç yok.</div>'}</div>`;
      bindStatementClicks();
    };
  },50);
};
fetch('data/seed.json').then(r=>r.json()).then(d=>{DB=d;render('gundem')}).catch(()=>view.innerHTML='<div class="empty">Veri yüklenemedi. Projeyi yerel bir HTTP sunucusu ile açın.</div>');
