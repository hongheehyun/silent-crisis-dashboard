/* app.js — The Silent Crisis v2.0 대시보드 메인 로직 */

// ── 데이터 로드 & 초기화 ─────────────────────────────────
let DATA = null;

async function init() {
  try {
    const res = await fetch('dashboard_data_v2.json');
    DATA = await res.json();
    setupNav();
    animateCounters();
    buildMap();
    buildFactorsCharts();
    buildScatter();
    buildTop5();
    buildCohensD();
    buildQuartileHeatmap();
    buildA2Charts();
    buildPolicyCards();
    setupReveal();
    document.getElementById('kpi-max-country').textContent = "잠비아"; // Zambia
  } catch(e) {
    console.error('데이터 로드 실패:', e);
  }
}

// ── NAV 스크롤 효과 ──────────────────────────────────────
function setupNav() {
  const nav = document.getElementById('nav');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 50);
  });
}

// ── 카운터 애니메이션 ─────────────────────────────────────
function animateCounters() {
  document.querySelectorAll('.counter').forEach(el => {
    const target = parseFloat(el.dataset.target);
    const suffix = el.dataset.suffix || '';
    const duration = 1800;
    const start = performance.now();
    function update(now) {
      const t = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - t, 4);
      el.textContent = (target * ease).toFixed(target % 1 === 0 ? 0 : 1) + suffix;
      if (t < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  });
}

// ── 세계 지도 (D3.js) ────────────────────────────────────
async function buildMap() {
  const container = document.getElementById('map-container');
  const W = container.clientWidth, H = 520;

  const svg = d3.select('#map-container').append('svg')
    .attr('width', W).attr('height', H);

  // 파랑(안전) -> 노랑(중간) -> 빨강(위기)
  const colorScale = d3.scaleSequential()
    .domain([0, 100])
    .interpolator(d3.interpolateRgbBasis(['#38bdf8', '#fde047', '#fb7185']));

  const countryMap = {};
  DATA.countries.forEach(c => { if (c.iso3) countryMap[c.iso3] = c; });

  const projection = d3.geoNaturalEarth1()
    .scale(W / 6.3).translate([W / 2, H / 2]);
  const path = d3.geoPath().projection(projection);

  const defs = svg.append('defs');
  defs.append('radialGradient').attr('id','map-bg-grad')
    .selectAll('stop').data([
      {offset:'0%', color:'rgba(13,18,48,1)'},
      {offset:'100%', color:'rgba(8,12,30,1)'}
    ]).join('stop').attr('offset', d=>d.offset).attr('stop-color', d=>d.color);

  svg.append('rect').attr('width', W).attr('height', H)
    .attr('fill', 'url(#map-bg-grad)');

  const tooltip = document.getElementById('map-tooltip');

  try {
    const world = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
    const countries = topojson.feature(world, world.objects.countries);

    const numToAlpha = await fetch('https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/master/all/all.json')
      .then(r=>r.json()).catch(()=>[]);
    const numMap = {};
    numToAlpha.forEach(d => { numMap[d['country-code']] = d['alpha-3']; });

    svg.append('g')
      .selectAll('path')
      .data(countries.features)
      .join('path')
      .attr('d', path)
      .attr('fill', d => {
        const iso3 = numMap[String(d.id).padStart(3,'0')];
        const c = iso3 && countryMap[iso3];
        return c && c.lp != null ? colorScale(c.lp) : '#2d3748';
      })
      .attr('stroke', '#0d1230').attr('stroke-width', 0.5)
      .attr('class', 'country-path')
      .on('mouseover', function(event, d) {
        const iso3 = numMap[String(d.id).padStart(3,'0')];
        const c = iso3 && countryMap[iso3];
        if (!c) return;
        d3.select(this).attr('stroke', '#fff').attr('stroke-width', 1.5);
        tooltip.innerHTML = `<strong>${c.name}</strong><br>학습 위기율: <strong>${c.lp != null ? c.lp.toFixed(1)+'%' : '데이터 없음'}</strong>`;
        tooltip.classList.remove('hidden');
        positionTooltip(event, tooltip);
      })
      .on('mousemove', function(event) { positionTooltip(event, tooltip); })
      .on('mouseout', function() {
        d3.select(this).attr('stroke', '#0d1230').attr('stroke-width', 0.5);
        tooltip.classList.add('hidden');
      })
      .on('click', function(event, d) {
        const iso3 = numMap[String(d.id).padStart(3,'0')];
        const c = iso3 && countryMap[iso3];
        if (c) showCountryPanel(c);
      });

    svg.append('path').datum(topojson.mesh(world, world.objects.countries, (a,b)=>a!==b))
      .attr('d', path).attr('fill','none').attr('stroke','#0d1230').attr('stroke-width', 0.3);

  } catch(e) {
    console.warn('TopoJSON 로드 실패');
  }

  document.getElementById('panel-close').addEventListener('click', () => {
    document.getElementById('country-panel').classList.add('hidden');
  });
}

function positionTooltip(event, el) {
  const x = event.clientX + 14, y = event.clientY - 40;
  el.style.left = Math.min(x, window.innerWidth - 220) + 'px';
  el.style.top  = y + 'px';
  el.style.position = 'fixed';
}

function showCountryPanel(c) {
  const panel = document.getElementById('country-panel');
  document.getElementById('panel-country').textContent = c.name;

  const badge = document.getElementById('panel-lp-badge');
  const lp = c.lp != null ? c.lp.toFixed(1) : '데이터 없음';
  badge.textContent = lp + (c.lp != null ? '%' : '');
  const color = c.lp > 70 ? '#fb7185' : c.lp > 40 ? '#fde047' : '#38bdf8';
  badge.style.background = color + '22';
  badge.style.color = color;

  const stats = [
    ['1인당 소득(GDP)', c.gdp != null ? '$' + Math.round(c.gdp).toLocaleString() : '정보 없음'],
    ['국가 투명성/시스템 점수', c.governance != null ? c.governance.toFixed(2) : '정보 없음'],
    ['의사 수 (1000명당)', c.physicians != null ? c.physicians.toFixed(2) + '명' : '정보 없음'],
    ['10대 소녀 출산율', c.teen_birth != null ? c.teen_birth.toFixed(1) : '정보 없음'],
    ['선생님 1명당 학생 수', c.pupil_teacher != null ? Math.round(c.pupil_teacher) + '명' : '정보 없음'],
    ['전기 보급률', c.electricity != null ? c.electricity.toFixed(1) + '%' : '정보 없음'],
  ];
  document.getElementById('panel-stats').innerHTML = stats.map(([k, v]) =>
    `<div class="panel-stat-row"><span class="panel-stat-label">${k}</span><span class="panel-stat-val">${v}</span></div>`
  ).join('');

  panel.classList.remove('hidden');
}

// ── v1.0 vs v2.0 요인 비교 차트 ─────────────────────────
function buildFactorsCharts() {
  const v1Labels = ['10대 출산율','유아 사망률','전기 보급률','의사 수','초등 수료율'];
  const v1Values = [0.837, 0.879, 0.795, 0.733, 0.648];

  new Chart(document.getElementById('factorsV1Chart'), {
    type: 'bar',
    data: {
      labels: v1Labels,
      datasets: [{ label: '단순 연관성 점수', data: v1Values,
        backgroundColor: '#7f8c8d', borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      scales: {
        x: { min: 0, max: 1, ticks: { color: '#a8b5d0' }, grid: { color: 'rgba(255,255,255,0.06)' } },
        y: { ticks: { color: '#a8b5d0', font:{size:11} }, grid: { display: false } }
      }
    }
  });

  const sig = DATA.a1_factors.filter(f => f.p_value < 0.05).slice(0, 5);
  const v2Labels = sig.map(f => f.label);
  const v2Values = sig.map(f => Math.abs(f.cohens_d));

  new Chart(document.getElementById('factorsV2Chart'), {
    type: 'bar',
    data: {
      labels: v2Labels,
      datasets: [{ label: "실질 중요도 점수", data: v2Values,
        backgroundColor: '#4f8ef7', borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      scales: {
        x: { min: 0, max: 1.5, ticks: { color: '#a8b5d0' }, grid: { color: 'rgba(255,255,255,0.06)' } },
        y: { ticks: { color: '#a8b5d0', font:{size:11} }, grid: { display: false } }
      }
    }
  });
}

// ── 산점도 (D3.js) ────────────────────────────────────
function buildScatter() {
  const el = document.getElementById('scatter-container');
  const W = el.clientWidth, H = 440;
  const margin = {top:20, right:30, bottom:50, left:50};
  const iW = W - margin.left - margin.right;
  const iH = H - margin.top - margin.bottom;

  const svg = d3.select('#scatter-container').append('svg')
    .attr('width', W).attr('height', H)
    .append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const valid = DATA.countries.filter(c => c.log_gdp != null && c.lp != null);

  const xScale = d3.scaleLinear().domain(d3.extent(valid, d=>d.log_gdp)).nice().range([0, iW]);
  const yScale = d3.scaleLinear().domain([0, 105]).range([iH, 0]);

  const xMean = d3.mean(valid, d=>d.log_gdp);
  const yMean = d3.mean(valid, d=>d.lp);
  const num = d3.sum(valid, d=>(d.log_gdp - xMean)*(d.lp - yMean));
  const den = d3.sum(valid, d=>(d.log_gdp - xMean)**2);
  const slope = num/den, intercept = yMean - slope*xMean;
  const xExt = d3.extent(valid, d=>d.log_gdp);
  
  // 회귀선
  svg.append('line')
    .attr('x1', xScale(xExt[0])).attr('y1', yScale(intercept + slope*xExt[0]))
    .attr('x2', xScale(xExt[1])).attr('y2', yScale(intercept + slope*xExt[1]))
    .attr('stroke', '#4f8ef7').attr('stroke-width', 1.5).attr('stroke-dasharray','6,4').attr('opacity',0.6);

  const colorOf = g => g==='positive' ? '#38bdf8' : g==='negative' ? '#fb7185' : '#4a5568';

  const korNameMap = {
    'Sri Lanka': '스리랑카',
    'Viet Nam': '베트남',
    'Albania': '알바니아',
    'Benin': '베냉',
    'Serbia': '세르비아',
    'Bangladesh': '방글라데시',
    'Kenya': '케냐',
    'Philippines': '필리핀'
  };

  svg.selectAll('circle').data(valid).join('circle')
    .attr('cx', d=>xScale(d.log_gdp)).attr('cy', d=>yScale(d.lp))
    .attr('r', d=>d.deviance_group!=='middle' ? 6 : 4)
    .attr('fill', d=>colorOf(d.deviance_group))
    .attr('opacity', d=>d.deviance_group!=='middle' ? 0.9 : 0.4)
    .attr('stroke', d=>d.deviance_group!=='middle' ? 'white' : 'none')
    .attr('stroke-width', 1)
    .on('mouseover', function(event, d) {
      d3.select(this).attr('r', 9);
      const tt = document.getElementById('map-tooltip');
      const korName = korNameMap[d.name] || d.name;
      tt.innerHTML = `<strong>${korName}</strong><br>학습 위기율: ${d.lp?.toFixed(1)}%<br>1인당 소득: $${Math.round(d.gdp||0).toLocaleString()}`;
      tt.classList.remove('hidden');
      positionTooltip(event, tt);
    })
    .on('mouseout', function(event, d) {
      d3.select(this).attr('r', d.deviance_group!=='middle' ? 6 : 4);
      document.getElementById('map-tooltip').classList.add('hidden');
    });

  const top5Names = (DATA.top_deviants||[]).map(d=>d.country);
  valid.filter(c=>top5Names.includes(c.name)).forEach(c => {
    svg.append('text')
      .attr('x', xScale(c.log_gdp)+8).attr('y', yScale(c.lp)+4)
      .attr('fill','#38bdf8').attr('font-size',11).attr('font-weight','700')
      .text(korNameMap[c.name] || c.name);
  });

  svg.append('g').attr('transform', `translate(0,${iH})`)
    .call(d3.axisBottom(xScale).ticks(0))
    .selectAll('text').remove();
  svg.append('g').call(d3.axisLeft(yScale).ticks(6).tickFormat(d=>d+'%'))
    .selectAll('text').style('fill','#a8b5d0').style('font-size','10px');
  svg.selectAll('.domain, .tick line').attr('stroke','rgba(255,255,255,0.1)');

  svg.append('text').attr('x', iW/2).attr('y', iH+25)
    .attr('text-anchor','middle').attr('fill','#6b7a99').attr('font-size',11)
    .text('국가 경제력(소득) 증가 방향 ➡');
  svg.append('text').attr('transform','rotate(-90)').attr('x', -iH/2).attr('y', -38)
    .attr('text-anchor','middle').attr('fill','#6b7a99').attr('font-size',11)
    .text('학습 위기율 (%)');
}

// ── TOP 5 카드 ───────────────────────────────────────────
function buildTop5() {
  const container = document.getElementById('top5-cards');
  if (!DATA.top_deviants) return;
  const korNames = {
    'Sri Lanka': '스리랑카',
    'Viet Nam': '베트남',
    'Albania': '알바니아',
    'Benin': '베냉',
    'Serbia': '세르비아'
  };

  container.innerHTML = DATA.top_deviants.map(d => `
    <div class="top5-card">
      <div class="top5-rank">#${d.rank}</div>
      <div class="top5-info">
        <div class="top5-country">${korNames[d.country] || d.country}</div>
        <div class="top5-detail">비슷한 경제력 국가들보다 약 ${Math.abs(d.residual).toFixed(0)}% 더 좋은 성과</div>
      </div>
    </div>
  `).join('');
}

// ── 막대 차트 (영향력 - 일반인 친화적) ──────────────────────────────────
function buildCohensD() {
  const factors = [...DATA.a1_factors].sort((a,b) => Math.abs(a.cohens_d) - Math.abs(b.cohens_d));
  const labels = factors.map(f=>f.label);
  const vals   = factors.map(f=>Math.abs(f.cohens_d)); // 절대값 처리로 우측으로만 막대가 뻗게 함
  const colors = factors.map(f => f.significant ? '#4f8ef7' : '#7f8c8d'); // 중요한 것은 파란색, 아니면 회색

  new Chart(document.getElementById('cohensDChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: "중요도", data: vals,
        backgroundColor: colors, borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const f = factors[ctx.dataIndex];
              return f.significant ? `매우 중요 (점수: ${Math.abs(f.cohens_d).toFixed(2)})` : `영향 미미`;
            }
          }
        }
      },
      scales: {
        x: {
          min: 0, max: 1.5,
          ticks: { color: '#a8b5d0', font:{size:11} },
          grid: { color: 'rgba(255,255,255,0.06)' }
        },
        y: { ticks: { color: '#a8b5d0', font:{size:11} }, grid: { display: false } }
      }
    }
  });
}

// ── 분위별 히트맵 (텍스트 기반) ─────────────────────────────────────────
function buildQuartileHeatmap() {
  const el = document.getElementById('quartile-heatmap');
  const data = DATA.a1_quartile || [];
  if (!data.length) return;

  const quarters = ['최하위 소득국','하위 소득국','중위 소득국','상위 소득국'];
  const data_quarters = ['Q1','Q2','Q3','Q4'];
  const labels = [...new Set(data.map(d=>d.label))];

  const lookup = {};
  data.forEach(d => { lookup[`${d.label}_${d.quartile}`] = d; });

  const thead = `<thead><tr><th>정책 요인</th>${quarters.map(q=>`<th>${q}</th>`).join('')}</tr></thead>`;
  const tbody = '<tbody>' + labels.map(label => {
    const cells = data_quarters.map(q => {
      const d = lookup[`${label}_${q}`];
      if (!d) return `<td class="heatmap-empty">—</td>`;
      
      const absVal = Math.abs(d.cohens_d);
      let text = '—';
      let bg = 'transparent';
      let color = '#a8b5d0';
      
      if (absVal > 1.0) {
        text = '매우 중요';
        bg = 'rgba(79,142,247,0.4)';
        color = '#fff';
      } else if (absVal > 0.5) {
        text = '중요';
        bg = 'rgba(79,142,247,0.15)';
        color = '#a8b5d0';
      }

      return `<td style="background:${bg}; color:${color}; padding:10px 6px;">${text}</td>`;
    });
    return `<tr><td class="heatmap-label" style="padding:10px; border-right:1px solid rgba(255,255,255,0.1);">${label}</td>${cells.join('')}</tr>`;
  }).join('') + '</tbody>';

  el.innerHTML = `<table class="heatmap-table" style="width:100%; border-collapse:collapse; text-align:center;">${thead}${tbody}</table>`;
}

// ── 정책 차트 (거버넌스 vs 예산) ────────────────────────────────
function buildA2Charts() {
  const coeffs = DATA.a2.coefficients;
  
  // 정확한 라벨 이름으로 필터링
  const budgetData = coeffs.find(c => c.label.includes('교육지출 β'));
  const govData = coeffs.find(c => c.label.includes('거버넌스 β'));

  if(!budgetData || !govData) return;

  // 개선 효과로 표현하기 위해, LP를 낮추는(음수) 효과를 양수(개선 효과)로 반전시킵니다.
  const labels = ['교육 예산 증액', '투명한 시스템(거버넌스) 구축'];
  const betas = [ -budgetData.beta, -govData.beta ]; // 예산: -0.08, 거버넌스: +16.6
  const colors = [ 'rgba(127,140,141,0.6)', '#38bdf8' ]; 

  new Chart(document.getElementById('a2CoeffChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: '개선 효과 크기', data: betas,
        backgroundColor: colors, borderRadius: 8 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              return ctx.dataIndex === 1 ? '매우 뛰어난 개선 효과' : '개선 효과 거의 없음';
            }
          }
        }
      },
      scales: {
        x: { ticks: { color:'#a8b5d0', font:{size:11} }, grid:{ color:'rgba(255,255,255,0.06)' } },
        y: { ticks: { color:'#a8b5d0', font:{size:12} }, grid:{ display:false } }
      }
    }
  });
}

// ── 정책 제언 카드 ────────────────────────────────────────
function buildPolicyCards() {
  const grid = document.getElementById('policy-grid');
  grid.innerHTML = DATA.policy_recommendations.map(p => `
    <div class="policy-card">
      <div class="policy-number">ACTION 0${p.id}</div>
      <div class="policy-icon">${p.icon}</div>
      <div class="policy-title">${p.title}</div>
      <div class="policy-subtitle">${p.subtitle}</div>
      <div class="policy-headline">${p.headline}</div>
      <div class="policy-evidence">📊 데이터 분석 결과: 핵심 성공 요인으로 입증됨</div>
      <div class="policy-actions">
        ${p.actions.map(a=>`<div class="policy-action">${a}</div>`).join('')}
      </div>
    </div>
  `).join('');
}

// ── 스크롤 reveal ─────────────────────────────────────────
function setupReveal() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

// ── 시작 ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
